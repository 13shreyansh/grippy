# AGENTS.md — Grippy

## Stack
- Python 3.11, FastAPI, OpenAI API (gpt-4o), TinyFish API
- Frontend: plain HTML + CSS + vanilla JavaScript (no React, no framework)
- Templating: Jinja2 (built into FastAPI)

## Commands
- Install dependencies: pip install -r requirements.txt
- Run server: uvicorn app:app --reload --port 8000
- Run tests: pytest tests/ -v

## Project Structure
- app.py — FastAPI server, all routes
- agent/intake.py — OpenAI chat logic for extracting complaint data
- agent/router.py — Maps complaint type to target portal URL
- agent/executor.py — TinyFish API call to file the complaint
- templates/ — HTML templates
- static/ — CSS and JS files
- tests/ — All test files

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
