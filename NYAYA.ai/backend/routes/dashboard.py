"""GET /api/dashboard/stats (user) and GET /api/admin/stats (admin only)."""
from fastapi import APIRouter, Depends

from database.db import db
from services import legal_service
from services.auth_service import get_current_user, require_admin

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/stats")
def user_stats(user: dict = Depends(get_current_user)):
    uid = user["id"]
    with db() as conn:
        one = lambda sql: conn.execute(sql, (uid,)).fetchone()[0]
        recent = [dict(r) for r in conn.execute(
            "SELECT id, title, updated_at FROM conversations WHERE user_id=? "
            "ORDER BY updated_at DESC, id DESC LIMIT 5", (uid,)).fetchall()]
        return {
            "conversations": one("SELECT COUNT(*) FROM conversations WHERE user_id=?"),
            "saved_answers": one("SELECT COUNT(*) FROM saved_answers WHERE user_id=?"),
            "documents": one("SELECT COUNT(*) FROM document_analyses WHERE user_id=?"),
            "searches": one("SELECT COUNT(*) FROM search_history WHERE user_id=?"),
            "recent_conversations": recent,
        }


@router.get("/admin/stats")
def admin_stats(admin: dict = Depends(require_admin)):
    """Platform-wide numbers. 'Most searched categories' combines chat questions and case searches."""
    titles = {c["id"]: c["title"] for c in legal_service.get_categories()["categories"]}
    with db() as conn:
        one = lambda sql: conn.execute(sql).fetchone()[0]
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n FROM ("
            " SELECT category FROM messages WHERE role='user' AND category IS NOT NULL"
            " UNION ALL SELECT category FROM search_history WHERE category IS NOT NULL"
            ") GROUP BY category ORDER BY n DESC LIMIT 10").fetchall()
        return {
            "total_users": one("SELECT COUNT(*) FROM users"),
            "total_conversations": one("SELECT COUNT(*) FROM conversations"),
            "total_messages": one("SELECT COUNT(*) FROM messages WHERE role='user'"),
            "documents_analyzed": one("SELECT COUNT(*) FROM document_analyses"),
            "top_categories": [{"category": r["category"], "title": titles.get(r["category"], r["category"]),
                                "count": r["n"]} for r in rows],
        }
