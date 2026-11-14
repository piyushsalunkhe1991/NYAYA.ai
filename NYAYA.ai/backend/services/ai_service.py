"""All AI communication lives here (OpenAI-compatible chat completions).

Default provider: LLMFaucet (anonymous, no API key). Change AI_BASE_URL / AI_MODEL
in backend/.env to use another OpenAI-compatible endpoint.

Rules:
  * A failed request ALWAYS raises AIServiceError. We never return fake text.
  * Every request has a timeout.
"""
import httpx

from config import AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_TIMEOUT


class AIServiceError(Exception):
    """Raised whenever the AI provider cannot give a real answer."""


SYSTEM_PROMPT = """You are NYAYA.ai, an Indian legal INFORMATION assistant for ordinary citizens.

Rules you must follow:
1. Explain Indian law in simple, plain language. Define any legal term you use.
2. Reply in the language requested. If the user writes Hindi, reply in Hindi (Devanagari); if English, reply in English.
3. If the question is unclear or facts are missing (state, dates, parties, amounts), ask 1-3 short clarifying questions.
4. You give general legal information, NOT professional legal advice. For important matters, recommend consulting a qualified advocate, or free legal aid (NALSA, helpline 15100).
5. NEVER invent section numbers, Acts, case names, citations, court judgments or helpline numbers. If you are not sure, say plainly: "I could not verify this - please check India Code (indiacode.nic.in)."
6. Cite a section only when you are confident it is correct. Prefer naming the Act and topic over guessing a number.
7. India's criminal laws changed on 1 July 2024: Bharatiya Nyaya Sanhita (BNS) replaced the IPC, Bharatiya Nagarik Suraksha Sanhita (BNSS) replaced the CrPC, and Bharatiya Sakshya Adhiniyam (BSA) replaced the Indian Evidence Act. Mention old and new law carefully, and note that offences before that date are generally governed by the old laws.
8. Structure answers with short headings: **Summary**, **What the law says**, **What you can do** (practical steps), **Things to verify**. Keep it concise.
9. If "REFERENCE DATA" is provided, prefer it over your memory for Acts, Articles and helplines.
10. Decline to help with committing crimes or evading the law."""

DOC_PROMPT = """You are NYAYA.ai's legal document analyzer for Indian citizens. Analyse ONLY the document text provided. Do not invent facts that are not in it.

Reply in simple language with these headings:
**Document type** (what kind of document this appears to be)
**Summary** (5-8 lines)
**Parties** (names and roles, or "Not clearly stated")
**Important dates and amounts** (list, or "Not found")
**Key clauses explained** (each important clause in plain language)
**Difficult terms explained**
**Points to check carefully / possible risks** (things a non-lawyer should ask a lawyer about)
**Note** - recommend review by a qualified advocate before signing or acting.

If something is not in the text, say "Not found in the text". Never invent legal sections or case citations."""


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if AI_API_KEY:  # optional; LLMFaucet needs none
        h["Authorization"] = f"Bearer {AI_API_KEY}"
    return h


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(AI_TIMEOUT, connect=10.0)


def list_models() -> list:
    """Ask the provider which models it offers (GET /models)."""
    try:
        r = httpx.get(f"{AI_BASE_URL}/models", headers=_headers(), timeout=_timeout())
    except httpx.HTTPError as e:
        raise AIServiceError(f"Cannot reach the AI provider at {AI_BASE_URL}: {e.__class__.__name__}") from e
    if r.status_code != 200:
        raise AIServiceError(f"AI provider returned HTTP {r.status_code} for /models")
    try:
        return [m.get("id") for m in r.json().get("data", []) if m.get("id")]
    except ValueError as e:
        raise AIServiceError("AI provider returned an invalid /models response") from e


def check_status() -> dict:
    """Health check used by the dashboard. Reports the truth, never assumes success."""
    status = {"base_url": AI_BASE_URL, "model": AI_MODEL, "available": False,
              "models": [], "model_listed": None, "error": None}
    try:
        models = list_models()
        status["models"] = models[:30]
        status["model_listed"] = AI_MODEL in models
        status["available"] = True
    except AIServiceError as e:
        status["error"] = str(e)
    return status


def _post(model: str, messages: list, temperature: float) -> httpx.Response:
    try:
        return httpx.post(
            f"{AI_BASE_URL}/chat/completions",
            headers=_headers(),
            json={"model": model, "messages": messages, "temperature": temperature},
            timeout=_timeout(),
        )
    except httpx.TimeoutException as e:
        raise AIServiceError(f"The AI provider did not respond within {int(AI_TIMEOUT)} seconds.") from e
    except httpx.HTTPError as e:
        raise AIServiceError(f"Cannot reach the AI provider at {AI_BASE_URL} ({e.__class__.__name__}).") from e


def chat_completion(messages: list, temperature: float = 0.3) -> str:
    """Send messages to the AI and return the reply text, or raise AIServiceError."""
    r = _post(AI_MODEL, messages, temperature)

    # If the configured model is rejected, try the first model the provider lists (once).
    if r.status_code in (400, 404) and AI_MODEL:
        try:
            models = list_models()
        except AIServiceError:
            models = []
        alt = next((m for m in models if m != AI_MODEL), None)
        if alt:
            r = _post(alt, messages, temperature)

    if r.status_code != 200:
        raise AIServiceError(f"AI provider returned HTTP {r.status_code}: {r.text[:200]}")
    try:
        text = r.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise AIServiceError("AI provider returned an unexpected response format.") from e
    if not text or not text.strip():
        raise AIServiceError("AI provider returned an empty answer.")
    return text.strip()


def answer_chat(history: list, user_message: str, language: str, context: str) -> str:
    """Legal chat: system prompt + optional reference data + history + new question."""
    lang_rule = {
        "hi": "Reply in Hindi (Devanagari script).",
        "en": "Reply in English.",
    }.get(language, "Reply in the same language the user writes in (Hindi or English).")
    msgs = [{"role": "system", "content": SYSTEM_PROMPT + "\n\n" + lang_rule}]
    if context:
        msgs.append({"role": "system", "content": "REFERENCE DATA (curated, prefer this):\n" + context})
    msgs += history[-10:]
    msgs.append({"role": "user", "content": user_message})
    return chat_completion(msgs)


def analyze_document(text: str, truncated: bool) -> str:
    """Summarise a legal document's extracted text."""
    note = "\n\n[The document was long; only the first part is shown.]" if truncated else ""
    msgs = [
        {"role": "system", "content": DOC_PROMPT},
        {"role": "user", "content": "DOCUMENT TEXT:\n\"\"\"\n" + text + "\n\"\"\"" + note},
    ]
    return chat_completion(msgs, temperature=0.2)
