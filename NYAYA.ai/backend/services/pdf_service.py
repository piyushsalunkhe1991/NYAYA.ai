"""PDF text extraction with PyMuPDF. Scanned PDFs are rejected (no OCR)."""
import fitz  # PyMuPDF

MIN_TEXT_CHARS = 50


class PDFError(Exception):
    """Problem with the uploaded PDF; message is safe to show to the user."""


def extract_text(data: bytes) -> tuple:
    """Return (text, page_count). Raises PDFError for unreadable/scanned/protected files."""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise PDFError("This file could not be opened as a PDF. It may be corrupted.") from e
    try:
        if doc.needs_pass:
            raise PDFError("This PDF is password-protected. Remove the password and upload again.")
        pages = doc.page_count
        text = "\n".join(page.get_text() for page in doc).strip()
    finally:
        doc.close()
    if len(text) < MIN_TEXT_CHARS:
        raise PDFError(
            "This looks like a scanned or image-only PDF. NYAYA.ai cannot read scanned "
            "documents (OCR is not supported). Please upload a PDF with selectable text."
        )
    return text, pages
