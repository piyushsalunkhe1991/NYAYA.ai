"""GET /api/history, POST /api/history/save and related history endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from database.db import db
from schemas.schemas import SaveIn
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def history(user: dict = Depends(get_current_user)):
    """Everything the user has done: conversations, saved answers, documents, searches."""
    uid = user["id"]
    with db() as conn:
        q = lambda sql: [dict(r) for r in conn.execute(sql, (uid,)).fetchall()]
        return {
            "conversations": q("SELECT id, title, created_at, updated_at FROM conversations "
                               "WHERE user_id=? ORDER BY updated_at DESC, id DESC LIMIT 100"),
            "saved": q("SELECT id, title, content, category, created_at FROM saved_answers "
                       "WHERE user_id=? ORDER BY id DESC LIMIT 100"),
            "documents": q("SELECT id, filename, pages, analysis, created_at FROM document_analyses "
                           "WHERE user_id=? ORDER BY id DESC LIMIT 100"),
            "searches": q("SELECT id, query, category, created_at FROM search_history "
                          "WHERE user_id=? ORDER BY id DESC LIMIT 100"),
        }


@router.post("/save")
def save_answer(body: SaveIn, user: dict = Depends(get_current_user)):
    with db() as conn:
        cur = conn.execute("INSERT INTO saved_answers (user_id, title, content, category) VALUES (?,?,?,?)",
                           (user["id"], body.title.strip(), body.content, body.category))
    return {"id": cur.lastrowid, "saved": True}


@router.delete("/saved/{item_id}")
def delete_saved(item_id: int, user: dict = Depends(get_current_user)):
    with db() as conn:
        cur = conn.execute("DELETE FROM saved_answers WHERE id=? AND user_id=?", (item_id, user["id"]))
    if cur.rowcount == 0:
        raise HTTPException(404, "Saved answer not found.")
    return {"deleted": True}


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: int, user: dict = Depends(get_current_user)):
    with db() as conn:
        conv = conn.execute("SELECT id, title FROM conversations WHERE id=? AND user_id=?",
                            (conv_id, user["id"])).fetchone()
        if not conv:
            raise HTTPException(404, "Conversation not found.")
        msgs = conn.execute("SELECT id, role, content, category, is_demo, created_at FROM messages "
                            "WHERE conversation_id=? ORDER BY id", (conv_id,)).fetchall()
    return {"id": conv["id"], "title": conv["title"], "messages": [dict(m) for m in msgs]}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int, user: dict = Depends(get_current_user)):
    with db() as conn:
        cur = conn.execute("DELETE FROM conversations WHERE id=? AND user_id=?", (conv_id, user["id"]))
    if cur.rowcount == 0:
        raise HTTPException(404, "Conversation not found.")
    return {"deleted": True}
