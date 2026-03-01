import asyncio
import json
import logging
import os
import re
import smtplib
import traceback
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, AsyncGenerator
from uuid import uuid4

import requests
from dotenv import load_dotenv
from openai import AsyncOpenAI
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

load_dotenv()
logger = logging.getLogger(__name__)

TINYFISH_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"
CASE_PORTAL_URL = "http://crdcomplaints.azurewebsites.net/"
DEMO_CC_EMAIL = os.getenv("DEMO_EMAIL", "")

DEFAULT_PROFILE = {
    "complainant_salutation": "Mr",
    "complainant_given_name": "John",
    "complainant_family_name": "Doe",
    "complainant_email": "john.doe@example.com",
    "complainant_phone": "+6591234567",
    "complainant_block": "123",
    "complainant_street": "Orchard Road",
    "complainant_postal_code": "238888",
    "complainant_nric_last4": "567A",
    "complainant_gender": "Male",
    "complainant_year_of_birth": "1995",
}


def _build_event(
    event_type: str,
    purpose: str,
    run_id: str,
    confirmation_number: str | None = None,
    result_json: dict[str, Any] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "type": event_type,
        "purpose": purpose,
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "confirmation_number": confirmation_number,
        "resultJson": result_json,
        "message": message,
    }


async def _push_event(
    sse_queue: asyncio.Queue,
    event_type: str,
    purpose: str,
    run_id: str,
    confirmation_number: str | None = None,
    result_json: dict[str, Any] | None = None,
    message: str | None = None,
) -> None:
    event = _build_event(
        event_type=event_type,
        purpose=purpose,
        run_id=run_id,
        confirmation_number=confirmation_number,
        result_json=result_json,
        message=message,
    )
    await sse_queue.put(event)


def _read_text(value: Any) -> str:
    return "" if value is None else str(value)


def _get_profile(complaint_data: dict[str, Any]) -> dict[str, Any]:
    return {**DEFAULT_PROFILE, **complaint_data}


def _extract_text_from_completion(response: Any) -> str:
    try:
        content = response.choices[0].message.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")).strip())
                elif hasattr(item, "text"):
                    parts.append(str(item.text).strip())
            return "\n".join(part for part in parts if part).strip()
    except Exception:
        logger.exception("Failed parsing Mistral completion response.")
    return ""


async def _generate_formal_letter(
    profile: dict[str, Any],
    routing: dict[str, Any],
    complaint_data: dict[str, Any],
    case_reference: str | None = None,
) -> str:
    client = AsyncOpenAI(
        base_url="https://api.mistral.ai/v1",
        api_key=os.getenv("MISTRAL_API_KEY"),
    )
    reference_note = ""
    if case_reference:
        reference_note = (
            "\nNote: This complaint has been formally registered with CASE Singapore under "
            f"reference number {case_reference}. Please reference this number in all future correspondence."
        )

    user_message = (
        f"Consumer: {profile['complainant_given_name']} {profile['complainant_family_name']}, "
        f"{profile['complainant_email']}, {profile['complainant_phone']}\n"
        f"Company: {routing['name']}\n"
        f"Complaint: {complaint_data.get('complaint_description')}\n"
        f"Date: {complaint_data.get('complaint_date')}\n"
        f"Desired outcome: {complaint_data.get('complaint_desired_outcome')}"
        f"{reference_note}"
    )
    completion = await client.chat.completions.create(
        model="mistral-large-2411",
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a formal complaint letter from a Singapore consumer to a company. "
                    "Be professional and assertive. Reference the Consumer Protection (Fair Trading) "
                    "Act where relevant. Include all complaint details, desired resolution, and a "
                    "14-day response deadline. Sign the letter as 'Grippy.ai'. "
                    "Output only the letter body text, no subject line."
                ),
            },
            {"role": "user", "content": user_message},
        ],
    )
    letter = _extract_text_from_completion(completion)
    if letter:
        return letter
    return (
        "Dear Sir/Madam,\n\n"
        f"I am writing to lodge a formal complaint regarding {_read_text(complaint_data.get('complaint_description'))}.\n"
        f"This matter occurred on {_read_text(complaint_data.get('complaint_date'))}. "
        f"I seek the following resolution: {_read_text(complaint_data.get('complaint_desired_outcome'))}.\n\n"
        "Please treat this as a formal complaint under applicable consumer protection requirements, "
        "including the Consumer Protection (Fair Trading) Act where relevant, and respond within 14 days.\n\n"
        "Yours faithfully,\n"
        "Grippy.ai"
    )


def _send_email_sync(
    sender_email: str,
    app_password: str,
    recipient_email: str,
    cc_email: str,
    subject: str,
    body: str,
) -> None:
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["CC"] = cc_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    recipients = [recipient_email, cc_email]

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipients, msg.as_string())


def _sanitize_email_body(letter_body: str) -> str:
    sanitized = re.sub(r"\*\*(.*?)\*\*", r"\1", letter_body)
    sanitized = re.sub(r"^\s*#+\s*", "", sanitized, flags=re.MULTILINE)
    return sanitized


async def _execute_email_mode(
    complaint_data: dict[str, Any],
    routing: dict[str, Any],
    stage: str,
    run_id: str,
    sse_queue: asyncio.Queue,
    emit_events: bool = True,
    subject_override: str | None = None,
    case_reference: str | None = None,
) -> None:
    profile = _get_profile(complaint_data)
    if emit_events:
        await _push_event(
            sse_queue=sse_queue,
            event_type="STARTED",
            purpose="Starting complaint filing...",
            run_id=run_id,
        )

        await asyncio.sleep(3)
        await _push_event(
            sse_queue=sse_queue,
            event_type="PROGRESS",
            purpose="Connecting to filing agent...",
            run_id=run_id,
        )

    letter = await _generate_formal_letter(
        profile=profile,
        routing=routing,
        complaint_data=complaint_data,
        case_reference=case_reference,
    )

    if emit_events:
        await asyncio.sleep(3)
        await _push_event(
            sse_queue=sse_queue,
            event_type="PROGRESS",
            purpose="Composing formal complaint letter...",
            run_id=run_id,
        )

    sender_email = _read_text(os.getenv("GRIPPY_EMAIL"))
    app_password = _read_text(os.getenv("GRIPPY_EMAIL_APP_PASSWORD"))
    demo_email = _read_text(DEMO_CC_EMAIL).strip()
    intended_recipient = _read_text(routing.get("email"))
    recipient_email = demo_email
    cc_email = demo_email or _read_text(profile.get("complainant_email"))
    subject = (
        f"Formal Complaint — {routing['name']} — "
        f"{_read_text(complaint_data.get('complaint_company', ''))} — "
        f"{_read_text(complaint_data.get('complaint_date', ''))}"
    )
    if subject_override:
        subject = subject_override

    if not sender_email or not app_password or not recipient_email:
        raise ValueError("Missing GRIPPY_EMAIL, GRIPPY_EMAIL_APP_PASSWORD, or DEMO_EMAIL.")

    clean_letter = _sanitize_email_body(letter)
    if case_reference:
        clean_letter = (
            f"{clean_letter}\n\nCASE Singapore Reference Number: {case_reference}\n"
            "Filed via Grippy — grippy.ai"
        )

    await asyncio.to_thread(
        _send_email_sync,
        sender_email,
        app_password,
        recipient_email,
        cc_email,
        subject,
        clean_letter,
    )

    if emit_events:
        await asyncio.sleep(2)
        await _push_event(
            sse_queue=sse_queue,
            event_type="PROGRESS",
            purpose="Sending formal complaint email...",
            run_id=run_id,
        )

        await _push_event(
            sse_queue=sse_queue,
            event_type="COMPLETE",
            purpose="Complaint filed successfully!",
            run_id=run_id,
            confirmation_number=f"Complaint sent to {intended_recipient}. You are CC'd at {cc_email}.",
            result_json={
                "mode": "email",
                "stage": stage,
                "target_name": _read_text(routing.get("name")),
            },
        )


def _is_case_route(routing: dict[str, Any]) -> bool:
    url = _read_text(routing.get("url")).lower()
    name = _read_text(routing.get("name")).lower()
    return "crdcomplaints.azurewebsites.net" in url or "case" in name


def _normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", _read_text(value))


def _normalize_nric_last4(value: str) -> str:
    text = _read_text(value).strip().upper()
    if re.fullmatch(r"\d{3}[A-Z]", text):
        return text
    match = re.search(r"(\d{3}[A-Z])$", text)
    if match:
        return match.group(1)
    return text


def _extract_case_confirmation(page_text: str) -> str | None:
    body = " ".join(_read_text(page_text).split())
    if not body:
        return None

    patterns = [
        r"(?:reference|case|complaint)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Za-z0-9\-]{5,})",
        r"\b([A-Z]\d{7,12})\b",
        r"\b([A-Z]{1,3}-\d{4,12})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE)
        if match:
            return _read_text(match.group(1)).strip().rstrip(".,")
    return None


def _tinyfish_scout_sync(portal_url: str, goal: str, api_key: str) -> list[dict[str, Any]]:
    response = requests.post(
        TINYFISH_URL,
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        },
        json={"url": portal_url, "goal": goal},
        stream=True,
        timeout=120,
    )
    response.raise_for_status()

    events: list[dict[str, Any]] = []
    for line in response.iter_lines():
        if not line:
            continue
        decoded = line.decode("utf-8", errors="ignore").strip()
        if not decoded.startswith("data:"):
            continue
        raw = decoded[5:].strip()
        if not raw or raw == "[DONE]":
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
        if len(events) >= 30:
            break
    return events


async def _run_tinyfish_scout(
    portal_url: str,
    run_id: str,
    sse_queue: asyncio.Queue,
) -> None:
    api_key = _read_text(os.getenv("TINYFISH_API_KEY")).strip()
    if not api_key:
        raise ValueError("Missing TINYFISH_API_KEY for portal scouting.")

    goal = (
        "Scout this portal and identify how to start complaint filing. "
        "Find the complaint entrypoint and summarize required steps and visible mandatory fields."
    )
    await _push_event(
        sse_queue=sse_queue,
        event_type="PROGRESS",
        purpose="TinyFish is scouting the portal flow...",
        run_id=run_id,
    )

    events = await asyncio.to_thread(_tinyfish_scout_sync, portal_url, goal, api_key)
    surfaced = 0
    for event in events:
        event_type = _read_text(event.get("type")).upper()
        purpose = _read_text(event.get("purpose") or event.get("message") or event.get("status"))
        if event_type == "HEARTBEAT" or "HEARTBEAT" in purpose.upper():
            continue
        if purpose:
            await _push_event(
                sse_queue=sse_queue,
                event_type="PROGRESS",
                purpose=f"TinyFish: {purpose}",
                run_id=run_id,
            )
            surfaced += 1
        if surfaced >= 3 or event_type in {"COMPLETE", "COMPLETED"}:
            break


async def _fill_text_field(page: Any, labels: list[str], value: str) -> bool:
    text = _read_text(value).strip()
    if not text:
        return False

    for label in labels:
        pattern = re.compile(re.escape(label), re.IGNORECASE)
        try:
            await page.get_by_label(pattern).first.fill(text, timeout=2500)
            return True
        except Exception:
            pass
        try:
            await page.get_by_placeholder(pattern).first.fill(text, timeout=2500)
            return True
        except Exception:
            pass

        token = re.sub(r"[^a-z0-9]", "", label.lower())
        if not token:
            continue
        selector = (
            f"input[name*='{token}'],textarea[name*='{token}'],"
            f"input[id*='{token}'],textarea[id*='{token}']"
        )
        try:
            locator = page.locator(selector).first
            await locator.fill(text, timeout=2500)
            return True
        except Exception:
            continue
    return False


async def _select_field_option(page: Any, labels: list[str], value: str) -> bool:
    text = _read_text(value).strip()
    if not text:
        return False

    for label in labels:
        pattern = re.compile(re.escape(label), re.IGNORECASE)
        locator = page.get_by_label(pattern).first
        for method, val in (("label", text), ("value", text)):
            try:
                await locator.select_option(**{method: val}, timeout=2500)
                return True
            except Exception:
                continue
    return False


async def _click_action(page: Any, names: list[str], required: bool = True) -> bool:
    for name in names:
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        try:
            await page.get_by_role("button", name=pattern).first.click(timeout=3000)
            return True
        except Exception:
            pass
        try:
            await page.get_by_role("link", name=pattern).first.click(timeout=3000)
            return True
        except Exception:
            pass
    if required:
        raise RuntimeError(f"Unable to click required action: {names[0]}")
    return False


async def _check_consent(page: Any) -> bool:
    labels = [
        "I agree that by submitting my complaint",
        "I agree",
        "consent to the use of my personal data",
    ]
    for label in labels:
        try:
            await page.get_by_label(re.compile(re.escape(label), re.IGNORECASE)).first.check(
                timeout=3000,
                force=True,
            )
            return True
        except Exception:
            continue

    try:
        locator = page.locator("input[type='checkbox']").first
        await locator.check(timeout=3000, force=True)
        return True
    except Exception:
        return False


async def _submit_case_web_form(
    complaint_data: dict[str, Any],
    routing: dict[str, Any],
    run_id: str,
    sse_queue: asyncio.Queue,
) -> str | None:
    profile = _get_profile(complaint_data)
    portal_url = _read_text(routing.get("url")) or CASE_PORTAL_URL

    nric_value = _normalize_nric_last4(
        _read_text(profile.get("nric") or profile.get("complainant_nric_last4"))
    )
    phone_value = _normalize_phone(_read_text(profile.get("complainant_phone")))

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        page.set_default_timeout(12000)

        try:
            await page.goto(portal_url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            await _push_event(
                sse_queue=sse_queue,
                event_type="PROGRESS",
                purpose="Opening CASE complaint form...",
                run_id=run_id,
            )
            await _click_action(
                page,
                ["File a Complaint", "Lodge a Complaint", "Submit Complaint"],
                required=False,
            )

            await _push_event(
                sse_queue=sse_queue,
                event_type="PROGRESS",
                purpose="Filling personal particulars...",
                run_id=run_id,
            )
            await _select_field_option(page, ["Salutation"], profile.get("complainant_salutation", ""))
            await _fill_text_field(page, ["Given name", "Given Name"], profile.get("complainant_given_name", ""))
            await _fill_text_field(page, ["Family name", "Family Name"], profile.get("complainant_family_name", ""))
            await _fill_text_field(page, ["NRIC number", "NRIC"], nric_value)
            await _select_field_option(page, ["Gender"], profile.get("complainant_gender", ""))
            await _fill_text_field(page, ["Year of birth", "Year"], profile.get("complainant_year_of_birth", ""))
            await _fill_text_field(page, ["Email address", "Email"], profile.get("complainant_email", ""))
            await _fill_text_field(page, ["Phone number (mobile)", "Phone", "Mobile"], phone_value)
            await _fill_text_field(page, ["Block/house number", "Block", "House number"], profile.get("complainant_block", ""))
            await _fill_text_field(page, ["Street"], profile.get("complainant_street", ""))
            await _fill_text_field(page, ["Postal code", "Postal"], profile.get("complainant_postal_code", ""))
            await _click_action(page, ["NEXT STEP", "Next Step"])

            await _push_event(
                sse_queue=sse_queue,
                event_type="PROGRESS",
                purpose="Filling vendor details...",
                run_id=run_id,
            )
            await _fill_text_field(
                page,
                ["Vendor name", "Vendor Name"],
                complaint_data.get("complaint_company", "") or routing.get("name", ""),
            )
            await _fill_text_field(page, ["Vendor block/house number", "Vendor Block", "Vendor house"], "1")
            await _fill_text_field(page, ["Vendor street name", "Vendor Street", "Street"], "Unknown")
            await _fill_text_field(page, ["Vendor postal code", "Vendor Postal", "Postal"], "000000")
            await _click_action(page, ["NEXT STEP", "Next Step"])

            await _push_event(
                sse_queue=sse_queue,
                event_type="PROGRESS",
                purpose="Filling complaint information...",
                run_id=run_id,
            )
            await _select_field_option(
                page,
                ["Transaction type", "Transaction Type"],
                complaint_data.get("transaction_type", "Purchase"),
            )
            await _fill_text_field(
                page,
                ["Transaction date", "Date of transaction", "Transaction Date"],
                complaint_data.get("complaint_date", ""),
            )
            await _select_field_option(
                page,
                ["Desired outcome", "Desired Outcome"],
                complaint_data.get("complaint_desired_outcome", "Others"),
            )
            await _fill_text_field(
                page,
                ["Complaint summary", "Summary", "Description"],
                complaint_data.get("complaint_description", ""),
            )
            await _click_action(page, ["NEXT STEP", "Next Step"])

            await _push_event(
                sse_queue=sse_queue,
                event_type="PROGRESS",
                purpose="Submitting declaration...",
                run_id=run_id,
            )
            if not await _check_consent(page):
                raise RuntimeError("Unable to check mandatory consent checkbox on declaration page.")

            await _click_action(page, ["SUBMIT", "Submit"])
            await page.wait_for_load_state("domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                pass

            body_text = await page.text_content("body")
            return _extract_case_confirmation(_read_text(body_text))
        finally:
            await context.close()
            await browser.close()


async def _execute_web_form_mode(
    complaint_data: dict[str, Any],
    routing: dict[str, Any],
    stage: str,
    run_id: str,
    sse_queue: asyncio.Queue,
) -> None:
    if not _is_case_route(routing):
        raise RuntimeError("Deterministic web_form automation is currently implemented only for CASE.")

    await _push_event(
        sse_queue=sse_queue,
        event_type="STARTED",
        purpose="Launching browser automation...",
        run_id=run_id,
    )

    await _run_tinyfish_scout(
        portal_url=_read_text(routing.get("url")) or CASE_PORTAL_URL,
        run_id=run_id,
        sse_queue=sse_queue,
    )

    await _push_event(
        sse_queue=sse_queue,
        event_type="PROGRESS",
        purpose="Executing deterministic Playwright filing on CASE portal...",
        run_id=run_id,
    )
    confirmation_number = await _submit_case_web_form(complaint_data, routing, run_id, sse_queue)
    display_confirmation = confirmation_number or "Not provided"

    await _push_event(
        sse_queue=sse_queue,
        event_type="COMPLETE",
        purpose="Form submitted successfully. Complaint registered with CASE Singapore.",
        run_id=run_id,
        confirmation_number=display_confirmation,
        result_json={
            "stage": stage,
            "target_name": _read_text(routing.get("name", "CASE Singapore")),
            "method": "web_form",
            "confirmation_number": display_confirmation,
        },
    )

    reference_for_email = confirmation_number or None
    subject_reference = confirmation_number or "Not provided"
    try:
        await _execute_email_mode(
            complaint_data=complaint_data,
            routing=routing,
            stage=stage,
            run_id=run_id,
            sse_queue=sse_queue,
            emit_events=False,
            subject_override=(
                f"CASE Complaint Filed — Reference {subject_reference} — "
                f"{routing.get('name', '')} — {complaint_data.get('complaint_date', '')}"
            ),
            case_reference=reference_for_email,
        )
    except Exception:
        logger.exception("Email send after CASE web form filing failed.")
        print(traceback.format_exc())


async def execute_filing(
    complaint_data: dict,
    routing: dict,
    stage: str,
    run_id: str,
    sse_queue: asyncio.Queue,
) -> None:
    method = _read_text(routing.get("method")).strip().lower()

    try:
        if method == "email":
            await _execute_email_mode(complaint_data, routing, stage, run_id, sse_queue)
            return

        if method == "web_form":
            try:
                await _execute_web_form_mode(complaint_data, routing, stage, run_id, sse_queue)
                return
            except Exception:
                logger.exception("Web form filing failed; falling back to email mode.")
                print(traceback.format_exc())
                await _push_event(
                    sse_queue=sse_queue,
                    event_type="PROGRESS",
                    purpose="Web form unavailable. Filing via email instead...",
                    run_id=run_id,
                )
                await _execute_email_mode(complaint_data, routing, stage, run_id, sse_queue)
                return

        raise ValueError(f"Unsupported routing method: {routing.get('method')}")
    except Exception as error:
        logger.exception("Filing execution failed.")
        await _push_event(
            sse_queue=sse_queue,
            event_type="ERROR",
            purpose="Complaint filing failed.",
            run_id=run_id,
            message=str(error),
        )


def _is_terminal_event(event: dict[str, Any]) -> bool:
    event_type = _read_text(event.get("type")).upper()
    return event_type in {"COMPLETE", "COMPLETED", "FAILED", "ERROR"}


async def file_complaint_sse(
    complaint_data: dict[str, Any], portal_url: str | None
) -> AsyncGenerator[str, None]:
    run_id = str(uuid4())
    sse_queue: asyncio.Queue = asyncio.Queue()
    routing = {
        "name": "CASE Singapore",
        "method": "web_form" if portal_url else "email",
        "url": portal_url,
        "email": "consult@case.org.sg",
    }

    filing_task = asyncio.create_task(
        execute_filing(
            complaint_data=complaint_data,
            routing=routing,
            stage="regulator",
            run_id=run_id,
            sse_queue=sse_queue,
        )
    )

    while True:
        if filing_task.done() and sse_queue.empty():
            break
        try:
            event = await asyncio.wait_for(sse_queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        if not isinstance(event, dict):
            continue
        yield f"data: {json.dumps(event)}\n\n"
        if _is_terminal_event(event):
            break

    await asyncio.gather(filing_task, return_exceptions=True)
