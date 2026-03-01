import asyncio
import base64
import binascii
import json
import uuid
from typing import Any, AsyncGenerator

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from agent.executor import execute_filing
from agent.intake import process_message
from agent.router import route_complaint

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
templates = Jinja2Templates(directory="templates")
active_runs: dict[str, asyncio.Queue] = {}


class ChatRequest(BaseModel):
    message: str = ""
    history: list[dict[str, str]] = Field(default_factory=list)


class ComplaintPayload(BaseModel):
    complainant_salutation: str = "Mr"
    complainant_given_name: str = "John"
    complainant_family_name: str = "Doe"
    complainant_gender: str = "Male"
    complainant_year_of_birth: str = "1995"
    complainant_email: str = "john.doe@example.com"
    complainant_phone: str = "+6591234567"
    complainant_block: str = "123"
    complainant_street: str = "Orchard Road"
    complainant_postal_code: str = "238888"
    complainant_nric_last4: str = "567A"
    complaint_company: str = ""
    complaint_description: str = ""
    complaint_date: str = ""
    complaint_desired_outcome: str = ""


class EscalatePayload(BaseModel):
    complaint_data: dict[str, Any]
    regulator: dict[str, Any]


def _is_terminal_event(event: dict[str, Any]) -> bool:
    return str(event.get("type", "")).upper() in {"COMPLETE", "ERROR", "FAILED"}


async def _status_event_stream(run_id: str) -> AsyncGenerator[str, None]:
    queue = active_runs.get(run_id)
    if queue is None:
        return

    saw_terminal = False
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield 'data: {"type":"HEARTBEAT"}\n\n'
                continue

            if not isinstance(event, dict):
                continue

            yield f"data: {json.dumps(event)}\n\n"
            if _is_terminal_event(event):
                saw_terminal = True
                return
    finally:
        if saw_terminal:
            active_runs.pop(run_id, None)


@app.get("/")
async def index(request: Request) -> object:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chat")
async def chat_page(request: Request) -> object:
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> dict[str, str]:
    reply = await process_message(payload.message, payload.history)
    return {"reply": reply}


@app.get("/verify")
async def verify(request: Request, data: str) -> object:
    try:
        decoded = base64.b64decode(data).decode("utf-8")
        complaint_data = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid complaint data") from error

    if not isinstance(complaint_data, dict):
        raise HTTPException(status_code=400, detail="Invalid complaint data")

    fields = {
        "complainant_name": complaint_data.get("complainant_name", ""),
        "complainant_email": complaint_data.get("complainant_email", ""),
        "complainant_phone": complaint_data.get("complainant_phone", ""),
        "complaint_against": complaint_data.get("complaint_against", ""),
        "complaint_type": complaint_data.get("complaint_type", ""),
        "incident_date": complaint_data.get("incident_date", ""),
        "incident_description": complaint_data.get("incident_description", ""),
        "desired_outcome": complaint_data.get("desired_outcome", ""),
        "reference_number": complaint_data.get("reference_number", ""),
        "nric": complaint_data.get("nric", ""),
    }
    return templates.TemplateResponse("verify.html", {"request": request, **fields})


@app.post("/api/file")
async def file_complaint(complaint_data: ComplaintPayload) -> dict[str, Any]:
    complaint_data_dict = complaint_data.dict()
    routing = await route_complaint(complaint_data_dict)

    run_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()
    active_runs[run_id] = queue

    company_route = routing.get("company", {}) if isinstance(routing, dict) else {}
    asyncio.create_task(
        execute_filing(complaint_data_dict, company_route, "company", run_id, queue)
    )
    return {"run_id": run_id, "routing": routing}


@app.get("/api/status/{run_id}")
async def api_status(run_id: str) -> StreamingResponse:
    if run_id not in active_runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return StreamingResponse(
        _status_event_stream(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/escalate")
async def escalate(payload: EscalatePayload) -> dict[str, str]:
    run_id = uuid.uuid4().hex
    queue: asyncio.Queue = asyncio.Queue()
    active_runs[run_id] = queue
    asyncio.create_task(
        execute_filing(payload.complaint_data, payload.regulator, "regulator", run_id, queue)
    )
    return {"run_id": run_id}


@app.get("/status")
async def status_page(request: Request) -> object:
    return templates.TemplateResponse("status.html", {"request": request})
