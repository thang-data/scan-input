import sys
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image


class ConversionError(Exception):
    pass


def _find_poppler() -> str | None:
    """Auto-detect bundled or system Poppler."""
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
        bundled = bundle_dir / "poppler"
        if bundled.is_dir():
            return str(bundled)
    return None


def pdf_to_images(pdf_path: Path, dpi: int = 300, poppler_path: str | None = None) -> list[Image.Image]:
    kwargs = {"dpi": dpi}
    path = poppler_path or _find_poppler()
    if path:
        kwargs["poppler_path"] = path
    try:
        return convert_from_path(str(pdf_path), **kwargs)
    except Exception as e:
        raise ConversionError(f"Failed to convert PDF '{pdf_path.name}': {e}") from e
