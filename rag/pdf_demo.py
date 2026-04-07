from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from rag.chunk_schema import RagChunk
from rag.preclean import RawPage, chunk_document


class PdfExtractionError(RuntimeError):
    """Raised when a PDF cannot yield usable text for chunking."""


def extract_pdf_pages(
    pdf_path: str | Path,
    prefer_ocr: bool = True,
    ocr_language: str = "chi_sim+eng",
    dpi: int = 300,
) -> list[RawPage]:
    """
    Extract page text from a PDF.

    The demo prefers OCR first and falls back to embedded text extraction when
    OCR is unavailable or fails for a given page.
    """

    fitz = _resolve_fitz()
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(str(path))
    pages: list[RawPage] = []
    ocr_errors: list[str] = []
    try:
        for page_no, page in enumerate(doc, start=1):
            text = ""
            if prefer_ocr:
                text, ocr_error = _extract_page_text_via_ocr(page, ocr_language=ocr_language, dpi=dpi)
                if ocr_error:
                    ocr_errors.append(f"page {page_no}: {ocr_error}")
            if not text.strip():
                text = page.get_text("text") or ""
            pages.append(RawPage(page_no=page_no, text=text))
    finally:
        doc.close()

    if not any(page.text.strip() for page in pages):
        detail = "PDF contains no extractable text."
        if prefer_ocr:
            if ocr_errors:
                detail += " OCR attempt failed: " + "; ".join(ocr_errors)
            else:
                detail += " OCR produced no text."
        raise PdfExtractionError(detail)

    return pages


def chunk_pdf_document(
    pdf_path: str | Path,
    doc_id: int,
    title: str | None = None,
    max_chars: int = 1800,
    prefer_ocr: bool = True,
    ocr_language: str = "chi_sim+eng",
    dpi: int = 300,
) -> list[RagChunk]:
    """Run OCR/text extraction first, then route the result into local chunking."""

    path = Path(pdf_path)
    pages = extract_pdf_pages(
        pdf_path=path,
        prefer_ocr=prefer_ocr,
        ocr_language=ocr_language,
        dpi=dpi,
    )
    resolved_title = title or path.stem
    return chunk_document(
        doc_id=doc_id,
        title=resolved_title,
        pages=pages,
        max_chars=max_chars,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal PDF OCR+chunk demo for the local RAG module.")
    parser.add_argument("pdf_path", help="Path to the PDF file to chunk")
    parser.add_argument("--doc-id", type=int, default=1, help="Document id assigned during chunking")
    parser.add_argument("--title", default=None, help="Optional title override; defaults to PDF filename")
    parser.add_argument("--max-chars", type=int, default=1800, help="Maximum characters per chunk")
    parser.add_argument("--ocr-language", default="chi_sim+eng", help="OCR language string passed to PyMuPDF")
    parser.add_argument("--dpi", type=int, default=300, help="OCR render DPI")
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR and only use embedded PDF text extraction",
    )
    args = parser.parse_args()

    chunks = chunk_pdf_document(
        pdf_path=args.pdf_path,
        doc_id=args.doc_id,
        title=args.title,
        max_chars=args.max_chars,
        prefer_ocr=not args.no_ocr,
        ocr_language=args.ocr_language,
        dpi=args.dpi,
    )
    print(json.dumps([chunk.model_dump() for chunk in chunks], ensure_ascii=False, indent=2))
    return 0


def _extract_page_text_via_ocr(page: Any, ocr_language: str, dpi: int) -> tuple[str, str | None]:
    """
    Try OCR via PyMuPDF if the runtime supports it.

    PyMuPDF OCR requires a local Tesseract installation configured in the host
    environment. When OCR is unavailable, this returns an empty string so the
    caller can fall back to page text extraction.
    """

    get_textpage_ocr = getattr(page, "get_textpage_ocr", None)
    if get_textpage_ocr is None:
        return "", "PyMuPDF OCR API is unavailable"

    try:
        textpage = get_textpage_ocr(language=ocr_language, dpi=dpi, full=True)
    except Exception as exc:
        return "", str(exc)

    try:
        text = page.get_text("text", textpage=textpage) or ""
    except TypeError:
        text = page.get_text(textpage=textpage) or ""
    except Exception as exc:
        return "", str(exc)

    if not text.strip():
        return "", "OCR completed but returned empty text"
    return text, None


def _resolve_fitz():
    try:
        import fitz  # type: ignore

        return fitz
    except ImportError as exc:
        raise RuntimeError(
            "PDF chunking requires PyMuPDF (`fitz`). The current demo cannot run without it."
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())
