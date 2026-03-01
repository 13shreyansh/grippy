<div align="center">

# Grippy

### Just grip it.

**AI-powered consumer complaint filing for Singapore**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Mistral](https://img.shields.io/badge/Mistral-mistral--large--2411-0f172a)
![Browser Automation](https://img.shields.io/badge/Browser%20Use%20%2B%20Playwright-Automation-1d4ed8)
![License](https://img.shields.io/badge/License-MIT-16a34a)
![Open Source](https://img.shields.io/badge/Open%20Source-Yes-7c3aed)

[Problem](#the-problem) • [Solution](#the-solution) • [Demo](#demo) • [How It Works](#how-it-works) • [Architecture](#architecture) • [Quick Start](#quick-start) • [Tech Stack](#tech-stack) • [Vision](#vision)

</div>

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Demo](#demo)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Supported Companies](#supported-companies)
- [Supported Regulators](#supported-regulators)
- [Quick Start](#quick-start)
- [Tech Stack](#tech-stack)
- [Vision](#vision)
- [Team](#team)
- [License](#license)

## Demo

<div align="center">

### Watch Product Demo

[![Watch Product Demo](https://img.youtube.com/vi/fDRdVb2eFJA/maxresdefault.jpg)](https://youtu.be/fDRdVb2eFJA)

[▶ Watch on YouTube](https://youtu.be/fDRdVb2eFJA)

</div>

## The Problem

96% of consumers never formally complain.

The process is broken for ordinary people. Filing a complaint often means discovering the right portal, understanding complex forms, writing formal legal-style letters, and figuring out whether and how to escalate to a regulator. Most users give up before filing.

## The Solution

Talk to Grippy like a friend.

Three messages. One complaint. Zero forms.

Grippy handles intake conversationally, generates formal complaint letters that reference the Consumer Protection (Fair Trading) Act, files directly with companies through email or automation, and escalates to the right regulator automatically when needed.

## How It Works

1. **Chat**
Describe what happened in plain language. Grippy extracts the details naturally.

2. **File**
Grippy routes your case and files it automatically via email or browser automation.

3. **Escalate**
If needed, Grippy escalates in one tap to CASE, IMDA, MAS, or LTA.

## Architecture

```text
+------------------------+        +-----------------------------+
| Frontend               | <----> | FastAPI Backend             |
| Vanilla HTML/CSS/JS    |        | Routing + orchestration +   |
| Chat + verify + status |        | SSE progress streaming      |
+-----------+------------+        +--------------+--------------+
            |                                      |
            |                                      |
            v                                      v
+------------------------+            +----------------------------+
| Mistral AI             |            | Browser Use + Playwright   |
| mistral-large-2411     |            | Web form automation        |
| Conversation + letters |            +----------------------------+
+-----------+------------+                         |
            |                                      |
            v                                      v
+------------------------+            +----------------------------+
| Gmail SMTP             |            | Company + Regulator Portals|
| Email complaint filing |            | CASE / IMDA / MAS / LTA    |
+------------------------+            +----------------------------+

(Voice layer: ElevenLabs — coming soon)
```

- **Backend:** FastAPI
- **LLM engine:** Mistral AI (`mistral-large-2411`)
- **Web automation:** Browser Use + Playwright
- **Email filing:** Gmail SMTP
- **Frontend:** Vanilla HTML/CSS/JS
- **Voice (planned):** ElevenLabs

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

1. Clone

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
GRIPPY_EMAIL=your_sender_gmail_address
GRIPPY_EMAIL_APP_PASSWORD=your_gmail_app_password
```

5. Run

```bash
uvicorn app:app --port 8000 --reload
```

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend | FastAPI | API endpoints, orchestration, SSE streaming |
| AI Conversation | Mistral AI | Conversational complaint intake |
| AI Letter Writing | Mistral AI | Formal complaint letter generation |
| Browser Automation | Browser Use + Playwright | Automated web form filing |
| Email Filing | Gmail SMTP | Direct complaint delivery and CC |
| Voice | ElevenLabs (coming soon) | Voice-first complaint filing UX |
| Frontend | Vanilla HTML/CSS/JS | Chat, verify, and live status interfaces |

## Vision

Grippy is built for Singapore first, but the model is global.

Consumer protection is universal. Every country has consumer rights frameworks, and every consumer deserves a friend who knows how to use the system.

Roadmap:

- SingPass integration
- Persistent complaint tracking
- Phone call filing
- Multi-country expansion

## Team

Team: The CS Guy

## License

MIT — see [LICENSE](LICENSE).
