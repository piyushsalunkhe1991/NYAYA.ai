# NYAYA.ai – AI Legal Adviser for Indian Citizens

A final-year project: an Indian legal **information** assistant with AI chat (Hindi/English), PDF document analysis,
a Know-Your-Rights library, a landmark-case finder, and user + admin dashboards.

> NYAYA.ai gives general legal information, **not legal advice**. Consult a qualified advocate.

## Tech stack
| Layer | Technology |
|---|---|
| Frontend | Plain HTML + CSS + JavaScript (no Node.js, no build step) |
| Backend | Python, FastAPI, Uvicorn, REST |
| AI | LLMFaucet OpenAI-compatible API (anonymous, no key), model `auto` |
| PDF | PyMuPDF |
| Database | SQLite (Python standard library) |

Only 5 Python packages: `fastapi`, `uvicorn`, `httpx`, `PyMuPDF`, `python-multipart`. No ML models, GPU, Docker, Redis or paid APIs.
FastAPI serves the frontend too, so you run **one** command.

## Install (Windows PowerShell)
Prerequisite: Python 3.10+ (`python --version`).

```powershell
cd NYAYA.ai\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
If activation is blocked: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then activate again.

## Run
```powershell
cd NYAYA.ai\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```
Open **http://127.0.0.1:8000** (landing page) → *Get Started*. API docs: http://127.0.0.1:8000/docs

The **first account registered with `admin@nyaya.ai`** becomes the Admin (change with `ADMIN_EMAIL` in `backend/.env`; see `.env.example`).

## Test
```powershell
cd NYAYA.ai\backend
python selftest.py
```
Tests every endpoint, auth, upload validation, error handling and ends with a **real** AI-provider check that reports honestly
whether LLMFaucet is reachable. Expected: all checks PASS; section 7 shows the live AI status.

## How the AI integration works
* All AI code is in `backend/services/ai_service.py` (OpenAI-compatible `POST {AI_BASE_URL}/chat/completions`, no API key).
* `AI_BASE_URL` / `AI_MODEL` (default `https://api.llmfaucet.dev/v1`, `auto`) are set in `backend/.env`. Keys, if you ever use one, stay on the server.
* A strict system prompt makes the model an Indian legal *information* assistant: simple language, Hindi/English, ask clarifying questions,
  never invent sections/citations/judgments, state uncertainty, recommend an advocate.
* Answers are **grounded**: relevant entries from `backend/data/rights.json` are injected as reference data.
* **Honest failure:** on timeout/network/HTTP error `ai_service` raises `AIServiceError`; the API returns `503 AI_UNAVAILABLE`; the UI shows the real error
  and nothing is saved. If the configured model is rejected, one retry is made with the first model from `/models`.
* **Demo mode** (checkbox in chat / button on error): answers come from the local knowledge base only and are labelled
  **"DEMO MODE – not AI generated"**.
* Dashboard → *AI service status* does a live `/models` check.

## API
| Endpoint | Purpose |
|---|---|
| `POST /api/chat` | AI legal chat (`demo:true` = local KB) |
| `POST /api/documents/analyze` | PDF upload → summary (PDF only, ≤10 MB, signature checked; scanned PDFs rejected) |
| `GET /api/legal/categories` | Know-Your-Rights data |
| `GET /api/legal/search?q=` | Landmark-case search |
| `GET /api/history` · `POST /api/history/save` | History / save answer |
| `GET /api/dashboard/stats` | User stats |
| `GET /api/admin/stats` | Admin stats (admin only) |
| `POST /api/auth/register|login|logout`, `GET/PATCH /api/auth/me`, `GET /api/ai/status` | Accounts & AI check |

## Project structure
```
NYAYA.ai/
  frontend/  index.html (landing) · app.html (dashboard) · css/styles.css · js/common.js · js/app.js
  backend/   main.py · config.py · selftest.py · requirements.txt
             routes/ services/ models/ schemas/ database/ data/ (rights.json, landmark_cases.json)
  README.md · .env.example · .gitignore
```

## Honesty about data
* **Know Your Rights** content is hand-curated with official source links (India Code, NCW, cybercrime.gov.in…). Section numbers are limited to a few
  well-known ones; confirm on indiacode.nic.in before relying on them.
* **Case search** uses a *small curated index* of well-known Supreme Court judgments (title, court, year, topics – no invented summaries). Source links are
  Indian Kanoon searches for the exact title, plus links to official portals. Unknown topics return **"No verified result found"**.
  Indian Kanoon's API needs a paid key, so full-database search is a documented future improvement.
* Scanned PDFs are not supported (no OCR). Document text is sent to the AI provider – don't upload sensitive files.

## Demo script (5 minutes)
1. Landing page → *Get Started* → register (use `admin@nyaya.ai` for the admin demo).
2. **Dashboard** → show *AI service status*.
3. **AI Legal Chat** → "What are my rights if police arrest me?" → follow-up → *Save answer* → ask in Hindi.
4. Show the error path: if the AI is down, point out the real error + *Use Demo mode* (labelled).
5. **Document Analyzer** → upload a text-based rent agreement PDF; then a scanned PDF to show the clear message.
6. **Know Your Rights** → open *Tenant Rights* → *Ask the AI about this*.
7. **Case Search** → "privacy" → source link; then "xyz" → "No verified result found".
8. **History & Saved**, **Profile**, and **Admin** (stats + most-searched categories).

## Troubleshooting
* *AI unavailable*: check internet; run `python selftest.py` section 7; the provider is free/anonymous and may rate-limit. Use Demo mode meanwhile.
* *Port busy*: use `--port 8001` and open that port.
* *Opened `app.html` from the file system*: it still works (calls `127.0.0.1:8000`) but use the URL above for best results.
