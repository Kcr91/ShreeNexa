"""FastAPI router: extract a draft StrategyIR from a strategy-description text or PDF.

Rule-based, offline, deterministic. No LLM calls. Accepts either:
- Raw text via JSON body at POST /api/v1/strategy/extract-from-text
- A PDF upload via multipart at POST /api/v1/strategy/extract-from-pdf (requires pypdf)
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.strategy.extraction import (
    ExtractionResult,
    extract_strategy_from_text,
    extract_text_from_pdf_bytes,
)

router = APIRouter(tags=["strategy-extract"])

_MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB
_MAX_TEXT_CHARS = 200_000


class ExtractFromTextRequest(BaseModel):
    """Raw strategy description. Does not reach any external service."""

    text: str = Field(min_length=1)
    name: str = Field(default="Extracted Strategy", max_length=120)


@router.post("/api/v1/strategy/extract-from-text", response_model=ExtractionResult)
def extract_from_text(req: ExtractFromTextRequest) -> ExtractionResult:
    """Run the rule-based parser on raw text and return a draft StrategyIR."""
    if len(req.text) > _MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=413, detail=f"Text exceeds {_MAX_TEXT_CHARS} characters."
        )
    return extract_strategy_from_text(req.text, name=req.name)


@router.post("/api/v1/strategy/extract-from-pdf", response_model=ExtractionResult)
async def extract_from_pdf(
    file: UploadFile = File(...),
    name: str = Form(default="Extracted Strategy"),
) -> ExtractionResult:
    """Extract text from an uploaded PDF, then run the rule-based parser.

    The PDF bytes are discarded immediately after extraction.
    """
    content_type = (file.content_type or "").lower()
    filename = file.filename or ""
    if "pdf" not in content_type and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted.")

    data = await file.read()
    try:
        if len(data) > _MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="PDF exceeds 10 MB size limit.")
        try:
            text = extract_text_from_pdf_bytes(data)
        except RuntimeError as exc:
            # pypdf not installed — surface a clear install hint, no silent degrade.
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        # Explicitly drop the buffer; FastAPI's UploadFile is temp-backed and
        # cleaned up on close, but be explicit about not retaining the bytes.
        data = b""
        await file.close()

    if not text:
        raise HTTPException(
            status_code=422, detail="Could not extract any text from the PDF (empty or image-only)."
        )
    if len(text) > _MAX_TEXT_CHARS:
        text = text[:_MAX_TEXT_CHARS]
    return extract_strategy_from_text(text, name=name)
