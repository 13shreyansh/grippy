import asyncio
import logging
import os
import traceback
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, AsyncOpenAI, AuthenticationError, RateLimitError

load_dotenv()

SYSTEM_PROMPT = """You are Grippy, a friendly and empathetic complaint assistant. You talk like a real friend — casual, warm, slightly informal. You use phrases like "that sucks," "let me handle this," "I've got you." You never sound robotic or corporate.

Your job: understand what happened, confirm the details, and then file the complaint.

Conversation flow:
1. Your first message is always exactly: "Hey! What happened?"
2. After the user describes their problem, respond with empathy in 1-2 sentences, then in the SAME message confirm: the company name, what went wrong, and what they want (refund/replacement/etc). Ask this as ONE natural question, not a list.
3. After the user confirms, say something like "Got it. I'm filing this right now. Sit tight." — then on a new line output ONLY a JSON block with no other text after it.

CRITICAL RULE: When you output the JSON block, it must be the LAST thing in your message. No text after the JSON.
Output ONLY a raw JSON object with no markdown, no backticks, no code fences — just the raw JSON starting with { and ending with }.
The JSON must have these exact fields:
{
  "complaint_company": "the company name",
  "complaint_description": "detailed description of what happened",
  "complaint_date": "YYYY-MM-DD or approximate like 2026-02-15",
  "complaint_desired_outcome": "what the user wants"
}"""

logger = logging.getLogger(__name__)


def _extract_completion_text(completion: Any) -> str:
    choices = getattr(completion, "choices", []) or []
    if not choices:
        return ""

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()

    segments: list[str] = []
    for part in content or []:
        text = part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
        if isinstance(text, str):
            segments.append(text)
    return "\n".join(segments).strip()


def _build_messages(message: str, history: list[dict[str, str]]) -> list[dict[str, str]]:
    safe_history: list[dict[str, str]] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str):
            safe_history.append({"role": role, "content": content})

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *safe_history,
    ]

    last_history_item = safe_history[-1] if safe_history else None
    message_already_in_history = (
        isinstance(last_history_item, dict)
        and last_history_item.get("role") == "user"
        and last_history_item.get("content") == message
    )
    if message.strip() and not message_already_in_history:
        messages.append({"role": "user", "content": message})

    return messages


async def process_message(message: str, history: list) -> str:
    if not message.strip() and not (history or []):
        return "Hey! What happened?"

    try:
        client = AsyncOpenAI(
            base_url="https://api.mistral.ai/v1",
            api_key=os.getenv("MISTRAL_API_KEY"),
        )

        completion = await client.chat.completions.create(
            model="mistral-large-2411",
            messages=_build_messages(message, history),
        )

        reply = _extract_completion_text(completion)
        return reply or "Hey! What happened?"
    except (AuthenticationError, RateLimitError, APIConnectionError):
        logger.exception("Mistral API call failed.")
        print(traceback.format_exc())
        return "I hit a temporary issue talking to Grippy right now. Please try again in a moment."
    except Exception:
        logger.exception("Unexpected error in intake processing.")
        print(traceback.format_exc())
        return "I hit a temporary issue talking to Grippy right now. Please try again in a moment."


if __name__ == "__main__":
    async def _smoke_test() -> None:
        result = await process_message("test", [])
        print(result)

    asyncio.run(_smoke_test())
