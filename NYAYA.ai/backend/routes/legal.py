"""GET /api/legal/categories and GET /api/legal/search."""
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from database.db import db
from services import legal_service
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/legal", tags=["legal"])


@router.get("/categories")
def categories():
    return legal_service.get_categories()


@router.get("/search")
def search(q: str = Query(min_length=2, max_length=200),
           authorization: Optional[str] = Header(default=None)):
    result = legal_service.search_cases(q)
    # Record search history if the caller is logged in (search itself works for guests).
    try:
        user = get_current_user(authorization)
        with db() as conn:
            conn.execute("INSERT INTO search_history (user_id, query, category) VALUES (?,?,?)",
                         (user["id"], q.strip(), result["category"]))
    except HTTPException:
        pass
    return result
