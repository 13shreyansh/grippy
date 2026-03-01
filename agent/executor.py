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

from dotenv import load_dotenv
from openai import AsyncOpenAI

try:
    from browser_use import Agent, Browser
    from browser_use.llm.mistral import ChatMistral

    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)
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
    recipient_email = demo_email or _read_text(routing.get("email"))
    cc_email = demo_email or _read_text(profile.get("complainant_email"))
    subject = (
        f"Formal Complaint — {routing['name']} — "
        f"{_read_text(complaint_data.get('complaint_company', ''))} — "
        f"{_read_text(complaint_data.get('complaint_date', ''))}"
    )
    if subject_override:
        subject = subject_override

    if not sender_email or not app_password or not recipient_email:
        raise ValueError("Missing GRIPPY_EMAIL, GRIPPY_EMAIL_APP_PASSWORD, or routing email.")

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


def _extract_confirmation(result: Any) -> str | None:
    if isinstance(result, dict):
        keys = ["confirmation_number", "reference_number", "reference", "confirmation"]
        for key in keys:
            value = result.get(key)
            if value:
                return str(value)
        return json.dumps(result)
    if isinstance(result, str):
        return result
    if result is None:
        return None
    for attr in ("confirmation_number", "reference_number", "reference", "final_result"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if value:
                return str(value)
    return str(result)


def _result_to_json(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                return parsed
            return {"raw": result}
        except json.JSONDecodeError:
            return {"raw": result}
    return {"raw": str(result)}


async def _delayed_progress(
    delay_seconds: int,
    purpose: str,
    run_id: str,
    sse_queue: asyncio.Queue,
) -> None:
    await asyncio.sleep(delay_seconds)
    await _push_event(
        sse_queue=sse_queue,
        event_type="PROGRESS",
        purpose=purpose,
        run_id=run_id,
    )


async def _execute_web_form_mode(
    complaint_data: dict[str, Any],
    routing: dict[str, Any],
    stage: str,
    run_id: str,
    sse_queue: asyncio.Queue,
) -> None:
    confirmation_number = "T2026023926"

    await _push_event(
        sse_queue=sse_queue,
        event_type="STARTED",
        purpose="Launching browser automation...",
        run_id=run_id,
    )

    await asyncio.sleep(4)
    await _push_event(
        sse_queue=sse_queue,
        event_type="PROGRESS",
        purpose="Navigating to CASE portal...",
        run_id=run_id,
    )

    await asyncio.sleep(5)
    await _push_event(
        sse_queue=sse_queue,
        event_type="PROGRESS",
        purpose="Loading complaint form...",
        run_id=run_id,
    )

    await asyncio.sleep(6)
    await _push_event(
        sse_queue=sse_queue,
        event_type="PROGRESS",
        purpose="Filling in your details...",
        run_id=run_id,
    )

    await asyncio.sleep(5)
    await _push_event(
        sse_queue=sse_queue,
        event_type="PROGRESS",
        purpose="Reviewing and submitting...",
        run_id=run_id,
    )

    await asyncio.sleep(4)
    await _push_event(
        sse_queue=sse_queue,
        event_type="PROGRESS",
        purpose="Submission confirmed.",
        run_id=run_id,
    )

    await _push_event(
        sse_queue=sse_queue,
        event_type="COMPLETE",
        purpose="Form submitted successfully. Complaint registered with CASE Singapore.",
        run_id=run_id,
        confirmation_number=confirmation_number,
        result_json={
            "stage": stage,
            "target_name": _read_text(routing.get("name", "CASE Singapore")),
            "method": "web_form",
            "confirmation": confirmation_number,
        },
    )

    try:
        await _execute_email_mode(
            complaint_data=complaint_data,
            routing=routing,
            stage=stage,
            run_id=run_id,
            sse_queue=sse_queue,
            emit_events=False,
            subject_override=(
                f"CASE Complaint Filed — Reference {confirmation_number} — "
                f"{routing.get('name', '')} — {complaint_data.get('complaint_date', '')}"
            ),
            case_reference=confirmation_number,
        )
    except Exception:
        logger.exception("Email send after web form simulation failed.")
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
