<div align="center">

# Grippy

### Just grip it.

**AI-powered consumer complaint filing for Singapore**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Mistral](https://img.shields.io/badge/Mistral-mistral--large--2411-black)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Stage-Hackathon%20to%20Startup-orange)

</div>

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Supported Companies](#supported-companies)
- [Supported Regulators](#supported-regulators)
- [Quick Start](#quick-start)
- [Tech Stack](#tech-stack)
- [Vision](#vision)
- [Team](#team)
- [License](#license)

## The Problem

96% of consumers never file a formal complaint.

Not because they do not care, but because the process is broken. People must figure out which portal to use, write formal legal-style complaint letters, fill long forms with strict formatting, and understand escalation paths across regulators. Most give up before submission.

## The Solution

Talk to Grippy like a friend.

Three messages. One complaint. Zero forms.

Grippy collects the facts conversationally, generates formal complaint letters citing the Consumer Protection (Fair Trading) Act, files directly with companies, and escalates to the right government regulator automatically.

## How It Works

### 1. Chat
Describe your issue naturally. No legal language, no templates, no forms.

### 2. File
Grippy routes and files automatically via email or browser automation.

### 3. Escalate
One tap to escalate to the correct regulator: CASE, IMDA, MAS, or LTA.

## Architecture

```text
+-----------------------+        +-----------------------------+
| Frontend              |        | FastAPI Backend             |
| Vanilla HTML/CSS/JS   | <----> | Orchestration + SSE Streams |
+-----------+-----------+        +--------------+--------------+
            |                                    |
            |                                    |
            v                                    v
+------------------------+          +----------------------------+
| Mistral AI             |          | Browser Use + Playwright   |
| mistral-large-2411     |          | Web form automation        |
| Conversation + letters |          +----------------------------+
+-----------+------------+                         |
            |                                      |
            v                                      v
+------------------------+          +----------------------------+
| Gmail SMTP             |          | Government / Company Portals|
| Complaint email filing |          | CASE / IMDA / MAS / LTA     |
+------------------------+          +----------------------------+

(Voice layer: ElevenLabs integration planned)
```

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

```bash
git clone https://github.com/<your-username>/grippy.git
cd grippy
pip install -r requirements.txt
python -m playwright install chromium
```

Create a `.env` file:

```env
MISTRAL_API_KEY=your_mistral_api_key
GRIPPY_EMAIL=your_sender_gmail_address
GRIPPY_EMAIL_APP_PASSWORD=your_gmail_app_password
```

Run:

```bash
uvicorn app:app --port 8000 --reload
```

## Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI |
| AI Conversation | Mistral AI |
| AI Letter Writing | Mistral AI |
| Browser Automation | Browser Use + Playwright |
| Email Filing | Gmail SMTP |
| Voice | ElevenLabs (coming soon) |
| Frontend | Vanilla HTML/CSS/JS |

## Vision

Built for Singapore, but the model works anywhere.

Every country has consumer protection laws. Every consumer deserves a friend who knows how to use them.

Roadmap:

- SingPass integration
- Persistent complaint tracking
- Phone call filing
- Multi-country expansion

## Team

Team: The CS Guy

## License

MIT
