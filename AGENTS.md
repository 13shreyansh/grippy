# AGENTS.md — Grippy

## Stack
- Python 3.11, FastAPI, Mistral AI (`mistral-large-2411`), TinyFish API + Playwright scripts
- Frontend: plain HTML + CSS + vanilla JavaScript (no React, no framework)
- Templating: Jinja2 (built into FastAPI)

## Commands
- Install dependencies: pip install -r requirements.txt
- Install browser runtime: python -m playwright install chromium
- Run server: uvicorn app:app --reload --port 8000
- Run tests: pytest tests/ -v

## Project Structure
- app.py — FastAPI server, all routes
- agent/intake.py — Mistral chat logic for extracting complaint data
- agent/router.py — Maps complaint type to target portal URL
- agent/executor.py — TinyFish scouting + Playwright/email filing orchestration
- templates/ — HTML templates
- static/ — CSS and JS files
- tests/ — All test files
- Current deterministic Playwright coverage is CASE-first (`crdcomplaints.azurewebsites.net`); other web routes should use email mode in this repo.

## Code Style
- Type hints on all function signatures
- Functions under 40 lines
- Use f-strings for string formatting
- Async functions for all API calls

## NEVER do these
- NEVER hardcode API keys; always use environment variables
- NEVER add user authentication or login
- NEVER add a database
- NEVER add payment processing
- NEVER install React, Vue, or any frontend framework
- NEVER modify the TinyFish API endpoint URL
- NEVER add WebSocket connections; use SSE for streaming
