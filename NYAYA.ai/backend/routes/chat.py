"""POST /api/chat - the AI legal chat assistant."""
from fastapi import APIRouter, Depends, HTTPException

from database.db import db
from schemas.schemas import ChatIn
from services import ai_service, legal_service
from services.auth_service import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/ai/status")
def ai_status(user: dict = Depends(get_current_user)):
    """Is the AI provider reachable right now? (real check, never assumed)"""
    return ai_service.check_status()


@router.post("/chat")
def chat(body: ChatIn, user: dict = Depends(get_current_user)):
    category = legal_service.classify(body.message)

    # Load earlier messages of this conversation so follow-up questions work.
    history = []
    if body.conversation_id:
        with db() as conn:
            conv = conn.execute("SELECT id FROM conversations WHERE id=? AND user_id=?",
                                (body.conversation_id, user["id"])).fetchone()
            if not conv:
                raise HTTPException(404, "Conversation not found.")
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 10",
                (body.conversation_id,)).fetchall()
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # Get the answer FIRST. If the AI fails we save nothing and report the real error.
    if body.demo:
        answer = legal_service.demo_answer(body.message)
    else:
        try:
            answer = ai_service.answer_chat(
                history, body.message, body.language,
                legal_service.retrieve_context(body.message))
        except ai_service.AIServiceError as e:
            raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "message": str(e)})

    with db() as conn:
        conv_id = body.conversation_id
        if not conv_id:
            cur = conn.execute("INSERT INTO conversations (user_id, title) VALUES (?,?)",
                               (user["id"], body.message.strip()[:60]))
            conv_id = cur.lastrowid
        conn.execute("INSERT INTO messages (conversation_id, role, content, category) VALUES (?,?,?,?)",
                     (conv_id, "user", body.message, category))
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, category, is_demo) VALUES (?,?,?,?,?)",
            (conv_id, "assistant", answer, category, 1 if body.demo else 0))
        conn.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (conv_id,))
        msg_id = cur.lastrowid

    return {"conversation_id": conv_id, "message_id": msg_id, "answer": answer,
            "category": category, "demo": body.demo, "disclaimer": legal_service.DISCLAIMER}
