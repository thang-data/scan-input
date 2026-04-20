"""Smart PDF reader — auto-detect scan vs text PDF."""

from pathlib import Path

import pdfplumber


def is_scan_pdf(pdf_path: Path, sample_pages: int = 3) -> bool:
    """Check if PDF is scanned (image-based) or has extractable text."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages_to_check = min(sample_pages, len(pdf.pages))
        total_chars = 0
        for i in range(pages_to_check):
            text = pdf.pages[i].extract_text() or ""
            total_chars += len(text.strip())
        # If average chars per page < 50, it's likely a scan
        return (total_chars / max(pages_to_check, 1)) < 50


def extract_text_pdf(pdf_path: Path) -> str:
    """Extract text from a text-based PDF using pdfplumber."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        parts = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n\n".join(parts)


def get_pdf_info(pdf_path: Path) -> dict:
    """Get PDF metadata."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        return {
            "pages": len(pdf.pages),
            "is_scan": is_scan_pdf(pdf_path),
            "metadata": pdf.metadata,
        }
