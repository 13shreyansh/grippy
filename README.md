<div align="center">

# Grippy

### Just grip it.

**AI-powered consumer complaint filing for Singapore**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Mistral](https://img.shields.io/badge/Mistral-mistral--large--2411-111827)
![Automation](https://img.shields.io/badge/Automation-TinyFish%20API%20%2B%20Playwright-2563eb)
![SSE](https://img.shields.io/badge/Realtime-SSE-7c3aed)
![License](https://img.shields.io/badge/License-MIT-16a34a)

[Demo](#demo) • [Executive Snapshot](#executive-snapshot) • [Problem](#the-problem) • [Solution](#the-solution) • [How It Works](#how-it-works) • [Architecture](#architecture) • [API](#api-surface) • [Quick Start](#quick-start) • [Tech Stack](#tech-stack) • [Vision](#vision)

</div>

---

## Table of Contents

- [Demo](#demo)
- [Why This Repo Is LLM-Evaluable](#why-this-repo-is-llm-evaluable)
- [Executive Snapshot](#executive-snapshot)
- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Automation Coverage](#automation-coverage)
- [API Surface](#api-surface)
- [Supported Companies](#supported-companies)
- [Supported Regulators](#supported-regulators)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Tech Stack](#tech-stack)
- [Operational Notes](#operational-notes)
- [Vision](#vision)
- [Team](#team)
- [License](#license)

## Demo

<div align="center">

### Watch Product Demo

[![Watch Product Demo](https://img.youtube.com/vi/fDRdVb2eFJA/maxresdefault.jpg)](https://youtu.be/fDRdVb2eFJA)

[▶ Watch on YouTube](https://youtu.be/fDRdVb2eFJA)

</div>

This demo shows a complete run from chat intake to filing execution to confirmation streaming in one flow.

## Why This Repo Is LLM-Evaluable

This repository is structured so a reviewer (human or LLM) can infer concrete product behavior quickly.

- **Traceable API surface:** Filing lifecycle is visible through explicit endpoints (`/api/chat`, `/api/file`, `/api/status/{run_id}`, `/api/escalate`).
- **Deterministic orchestration:** Intake, routing, execution, and status streaming are split into dedicated modules.
- **Execution transparency:** Status events stream over SSE with terminal states (`COMPLETE`, `ERROR`, `FAILED`).
- **Automation layering is explicit:** TinyFish API performs portal scouting/intelligence, Playwright scripts execute known filing paths.
- **Coverage boundaries are explicit:** Deterministic real web-form automation is currently CASE-first; other routes use email delivery.
- **Config-to-runtime clarity:** Required environment keys are documented and mapped to filing responsibilities.

## Executive Snapshot

- Grippy is an AI complaint filing product that removes the operational friction between a consumer and formal complaint channels.
- Users explain the issue conversationally; Grippy converts this into filing-ready data and executes submission.
- The system supports both direct company filing and regulator escalation for Singapore complaint workflows.
- Filing progress is streamed live so users can see what the agent is doing at each step.
- The architecture is Singapore-first and designed to extend to additional countries and regulators.

## The Problem

96% of consumers never formally complain.

The issue is not demand. The issue is process design.

Most people give up because formal complaint filing requires too many context switches:

- finding the right complaint destination,
- understanding form requirements,
- writing legally structured language,
- deciding which regulator to escalate to,
- and manually tracking filing status.

The result is predictable: unresolved consumer harm and low accountability.

## The Solution

Talk to Grippy like a friend.

**Three messages. One complaint. Zero forms.**

Grippy handles intake, drafting, filing, and escalation as one coherent workflow.

- **Natural-language intake:** Users describe what happened without learning legal or portal-specific terminology.
- **Formal complaint drafting:** The model generates structured complaint text suitable for official channels.
- **Automated filing paths:** The system routes to company or regulator paths and executes submission.
- **Built-in escalation:** If required, users can escalate without re-entering data.
- **Live execution visibility:** Users track progress through SSE events in real time.

## How It Works

### 1) Chat

- **User input:** A plain-language complaint description.
- **System action:** Mistral intake extracts and normalizes required fields.
- **Output:** Structured complaint payload.

### 2) File

- **User input:** Filing confirmation.
- **System action:**
  - Router chooses the filing path.
  - TinyFish API scouts the target portal and determines interaction strategy.
  - Playwright scripts execute deterministic form submission steps for the CASE portal.
  - Email filing path runs where email routing is selected.
- **Output:** Run ID + live status stream + completion event.

### 3) Escalate

- **User input:** One-tap escalation request.
- **System action:** Regulator filing run starts using the same complaint context.
- **Output:** Regulator submission status and completion result.

## Architecture

```text
+--------------------------+        +----------------------------------+
| Frontend                 | <----> | FastAPI Backend                  |
| Vanilla HTML/CSS/JS      |        | Routing + orchestration + SSE    |
| Chat + verify + status   |        | status streaming                 |
+------------+-------------+        +----------------+-----------------+
             |                                       |
             |                                       |
             v                                       v
+--------------------------+             +-------------------------------+
| Mistral AI               |             | TinyFish API                  |
| mistral-large-2411       |             | Scouting + portal intelligence|
| Intake + letter drafting |             +---------------+---------------+
+------------+-------------+                             |
             |                                           v
             |                              +-----------------------------+
             |                              | Playwright Scripts          |
             |                              | Deterministic form execution|
             |                              +---------------+-------------+
             |                                              |
             v                                              v
+--------------------------+             +-------------------------------+
| Gmail SMTP               |             | Company + Regulator Portals   |
| Email complaint filing   |             | CASE / IMDA / MAS / LTA       |
+--------------------------+             +-------------------------------+

(Voice: ElevenLabs — coming soon)
```

### Request Flow

1. Frontend sends complaint chat/file actions to FastAPI.
2. Backend intake + routing determine filing method and target.
3. TinyFish API scouts target website state and structure.
4. Playwright scripts execute known filing sequences.
5. Backend emits SSE progress events to the status page until terminal completion.

### Automation Coverage

- **Real web-form automation:** CASE portal (`http://crdcomplaints.azurewebsites.net/`) via TinyFish scouting + Playwright execution.
- **Other filing paths:** Email mode for unsupported web-form destinations in this repo version.
- **Escalation:** Uses the same run orchestration and SSE visibility model.

## API Surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/chat` | POST | Intake conversation turn handling |
| `/api/file` | POST | Start a complaint filing run |
| `/api/status/{run_id}` | GET (SSE) | Stream live filing status |
| `/api/escalate` | POST | Start regulator escalation run |

## Supported Companies

- Shopee
- Lazada
- Singtel
- StarHub
- M1
- DBS
- OCBC
- UOB
- SBS Transit
- SMRT
- FairPrice
- Grab

## Supported Regulators

- CASE (consumer disputes)
- IMDA (telecom)
- MAS (banking)
- LTA (transport)

## Quick Start

1. Clone repository

```bash
git clone https://github.com/13shreyansh/grippy.git
cd grippy
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Install browser runtime

```bash
python -m playwright install chromium
```

4. Create `.env`

```env
MISTRAL_API_KEY=your_mistral_api_key
TINYFISH_API_KEY=your_tinyfish_api_key
GRIPPY_EMAIL=your_sender_gmail_address
GRIPPY_EMAIL_APP_PASSWORD=your_gmail_app_password
DEMO_EMAIL=your_demo_or_cc_email
```

5. Run app

```bash
uvicorn app:app --port 8000 --reload
```

6. Open in browser

```text
http://127.0.0.1:8000
```

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `MISTRAL_API_KEY` | Yes | LLM conversation + drafting calls |
| `TINYFISH_API_KEY` | Yes | TinyFish API scouting/orchestration |
| `GRIPPY_EMAIL` | Yes | SMTP sender identity for complaint emails |
| `GRIPPY_EMAIL_APP_PASSWORD` | Yes | Gmail app password for SMTP auth |
| `DEMO_EMAIL` | Yes | Active outbound recipient in this repo mode (demo-safe delivery); UI still shows intended destination |

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | FastAPI | API orchestration, routing, SSE streaming |
| AI Conversation | Mistral AI (`mistral-large-2411`) | Intake and structured extraction |
| AI Letter Writing | Mistral AI (`mistral-large-2411`) | Formal complaint drafting |
| Browser Automation | TinyFish API + Playwright Scripts | Website scouting + deterministic form execution |
| Email Filing | Gmail SMTP | Company/regulator email submission |
| Voice | ElevenLabs (coming soon) | Planned voice-first filing UX |
| Frontend | Vanilla HTML/CSS/JS | Chat, verification, and live status UI |

## Operational Notes

- Filing runs stream progress using SSE; status UI reacts to STARTED/PROGRESS/COMPLETE/ERROR events.
- Routing controls whether execution is web-form automation or email submission.
- TinyFish provides portal-level intelligence; Playwright executes deterministic CASE form actions.
- Outbound SMTP is intentionally demo-routed to `DEMO_EMAIL` in this repository mode.
- Architecture intentionally separates intake logic from portal execution logic, making new portal adapters easy to add.

## Vision

Built for Singapore, designed to scale globally.

Consumer protection systems differ by country, but the friction pattern is universal: discovery, form complexity, legal language, and escalation uncertainty. Grippy is designed to be a reusable filing layer between citizens and complaint infrastructure.

Roadmap:

- SingPass integration
- Persistent complaint tracking
- Phone call filing
- Multi-country expansion

## Team

Team: The CS Guy

## License

MIT — see [LICENSE](LICENSE).
