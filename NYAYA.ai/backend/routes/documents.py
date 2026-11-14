"""POST /api/documents/analyze - upload a PDF, extract text, summarise with AI."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from config import MAX_DOC_CHARS_TO_AI, MAX_UPLOAD_MB
from database.db import db
from services import ai_service, pdf_service
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    # 1) Validate type and size BEFORE doing any work.
    name = file.filename or "document.pdf"
    if not name.lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files are supported.")
    data = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File is too large. Maximum size is {MAX_UPLOAD_MB} MB.")
    if not data.startswith(b"%PDF"):  # check the real file signature, not just the name
        raise HTTPException(415, "This file is not a valid PDF.")

    # 2) Extract text (PyMuPDF). Scanned PDFs get a clear message.
    try:
        text, pages = pdf_service.extract_text(data)
    except pdf_service.PDFError as e:
        raise HTTPException(422, str(e))

    # 3) Send (a limited amount of) text to the AI.
    truncated = len(text) > MAX_DOC_CHARS_TO_AI
    try:
        analysis = ai_service.analyze_document(text[:MAX_DOC_CHARS_TO_AI], truncated)
    except ai_service.AIServiceError as e:
        raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "message": str(e)})

    with db() as conn:
        cur = conn.execute(
            "INSERT INTO document_analyses (user_id, filename, pages, analysis) VALUES (?,?,?,?)",
            (user["id"], name[:200], pages, analysis))
    return {"id": cur.lastrowid, "filename": name, "pages": pages, "characters": len(text),
            "truncated": truncated, "analysis": analysis}
