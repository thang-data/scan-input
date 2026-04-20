import os
import platform
import shutil
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

from src.io.pdf_converter import pdf_to_images
from src.ocr.preprocessor import prepare_paddle, prepare_tesseract

# Auto-detect Tesseract path (bundled exe or system install)
def _find_tesseract():
    # 1. Bundled with PyInstaller
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
        bundled = bundle_dir / "tesseract" / "tesseract.exe"
        if bundled.exists():
            return str(bundled)
    # 2. System install on Windows
    if platform.system() == "Windows":
        default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if Path(default).exists():
            return default
    return None

import sys
_tess_path = _find_tesseract()
if _tess_path:
    pytesseract.pytesseract.tesseract_cmd = _tess_path
    # Also set TESSDATA_PREFIX for bundled builds
    tessdata = Path(_tess_path).parent / "tessdata"
    if tessdata.is_dir():
        os.environ.setdefault("TESSDATA_PREFIX", str(tessdata.parent))

# Singletons
_paddle_ocr_instance = None
_easyocr_reader = None
_rapidocr_engine = None
_vietocr_predictor = None

CONFIDENCE_THRESHOLD = 0.80


# ── RapidOCR ──

def _get_rapidocr():
    global _rapidocr_engine
    if _rapidocr_engine is None:
        from rapidocr import RapidOCR
        _rapidocr_engine = RapidOCR()
    return _rapidocr_engine


# ── VietOCR ──

def _get_vietocr():
    global _vietocr_predictor
    if _vietocr_predictor is None:
        from vietocr.tool.predictor import Predictor
        from vietocr.tool.config import Cfg
        config = Cfg.load_config_from_name("vgg_transformer")
        config["device"] = "cpu"
        config["predictor"]["beamsearch"] = False  # faster
        _vietocr_predictor = Predictor(config)
    return _vietocr_predictor


# ── PaddleOCR ──

def _get_paddle_ocr(lang: str = "vi"):
    global _paddle_ocr_instance
    os.environ.setdefault("HUB_DATASET_ENDPOINT", "https://modelscope.cn/api/v1/datasets")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    from paddleocr import PaddleOCR

    paddle_lang = _to_paddle_lang(lang)
    if _paddle_ocr_instance is None or _paddle_ocr_instance._lang != paddle_lang:
        _paddle_ocr_instance = PaddleOCR(
            use_angle_cls=False, lang="ch",
            use_doc_orientation_classify=False, use_doc_unwarping=False,
        )
        _paddle_ocr_instance._lang = paddle_lang
    return _paddle_ocr_instance


def _to_paddle_lang(tesseract_lang: str) -> str:
    return {"vie": "vi", "eng": "en", "jpn": "japan",
            "vie+eng": "vi", "jpn+eng": "japan"}.get(tesseract_lang, tesseract_lang)


def _resize_for_paddle(img: np.ndarray, max_side: int = 1500) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) <= max_side:
        return img
    s = max_side / max(h, w)
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


# ── EasyOCR ──

def _get_easyocr(lang: str = "vie"):
    global _easyocr_reader
    import easyocr
    easy_langs = {"vie": ["vi"], "eng": ["en"], "jpn": ["ja"],
                  "vie+eng": ["vi", "en"], "jpn+eng": ["ja", "en"]}.get(lang, ["vi"])
    lang_key = "+".join(easy_langs)
    if _easyocr_reader is None or _easyocr_reader._lang_key != lang_key:
        _easyocr_reader = easyocr.Reader(easy_langs, gpu=False)
        _easyocr_reader._lang_key = lang_key
    return _easyocr_reader


# ── NLP normalize ──

def _nlp_normalize(text: str) -> str:
    """Use underthesea to normalize Vietnamese text."""
    try:
        from underthesea import text_normalize
        return text_normalize(text)
    except Exception:
        return text


# ── Check functions ──

def check_tesseract() -> tuple[bool, str]:
    cmd = pytesseract.pytesseract.tesseract_cmd
    if not shutil.which(cmd) and not Path(cmd).is_file():
        return False, (
            "Tesseract OCR not found.\n\n"
            "Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki\n"
            "Mac: brew install tesseract\n"
            "Linux: apt install tesseract-ocr"
        )
    try:
        langs = pytesseract.get_languages()
    except Exception as e:
        return False, f"Cannot query Tesseract languages: {e}"
    return True, f"Tesseract OK. Available languages: {', '.join(langs)}"


def check_paddle() -> tuple[bool, str]:
    try:
        os.environ.setdefault("HUB_DATASET_ENDPOINT", "https://modelscope.cn/api/v1/datasets")
        from paddleocr import PaddleOCR  # noqa: F401
        return True, "PaddleOCR OK"
    except Exception:
        return False, "PaddleOCR not available."


def check_easyocr() -> tuple[bool, str]:
    try:
        import easyocr  # noqa: F401
        return True, "EasyOCR OK"
    except Exception:
        return False, "EasyOCR not available."


# ── OCR per engine ──

def ocr_image_tesseract(image: Image.Image, lang: str = "vie") -> str:
    config = (r"--oem 3 --psm 3 "
              r"-c preserve_interword_spaces=1 "
              r"-c tessedit_do_invert=0")
    return pytesseract.image_to_string(image, lang=lang, config=config)


def ocr_image_paddle(image: Image.Image, lang: str = "vi") -> str:
    ocr = _get_paddle_ocr(lang)
    arr = _resize_for_paddle(np.array(image.convert("RGB")))
    lines = []
    for r in ocr.predict(arr):
        lines.extend(r.get("rec_texts", []))
    return "\n".join(lines)


def ocr_image_easyocr(image: Image.Image, lang: str = "vie") -> str:
    reader = _get_easyocr(lang)
    return "\n".join(reader.readtext(np.array(image.convert("RGB")), detail=0, paragraph=True))


def ocr_image_rapid(image: Image.Image) -> str:
    engine = _get_rapidocr()
    result = engine(np.array(image.convert("RGB")))
    return "\n".join(result.txts) if result.txts else ""


def ocr_image_hybrid(image: Image.Image, lang: str = "vie") -> str:
    """
    Hybrid pipeline:
      1. RapidOCR  — detect boxes + fast recognize
      2. VietOCR   — re-OCR low-confidence crops (transformer, Vietnamese diacritics)
      3. underthesea — NLP normalize
    """
    engine = _get_rapidocr()
    img_array = np.array(image.convert("RGB"))
    result = engine(img_array)

    if not result.txts:
        return ""

    vietocr = _get_vietocr()
    final_lines: list[str] = []

    for text, score, box in zip(result.txts, result.scores, result.boxes):
        if score < CONFIDENCE_THRESHOLD:
            # Crop the box region and feed to VietOCR
            try:
                x_coords = box[:, 0]
                y_coords = box[:, 1]
                x1 = max(0, int(min(x_coords)) - 3)
                x2 = int(max(x_coords)) + 3
                y1 = max(0, int(min(y_coords)) - 3)
                y2 = int(max(y_coords)) + 3
                crop = img_array[y1:y2, x1:x2]
                if crop.size > 0:
                    crop_pil = Image.fromarray(crop)
                    vi_text = vietocr.predict(crop_pil)
                    if vi_text.strip():
                        text = vi_text
            except Exception:
                pass  # keep RapidOCR text
        final_lines.append(text)

    # NLP normalize
    raw = "\n".join(final_lines)
    return _nlp_normalize(raw)


def ocr_image_vietocr_full(image: Image.Image, lang: str = "vie") -> str:
    """
    Full VietOCR pipeline:
      1. RapidOCR detect all boxes
      2. VietOCR recognize ALL boxes (not just low-conf)
      3. underthesea normalize
    """
    engine = _get_rapidocr()
    img_array = np.array(image.convert("RGB"))
    result = engine(img_array)

    if not result.txts:
        return ""

    vietocr = _get_vietocr()
    lines: list[str] = []

    for box in result.boxes:
        try:
            x_coords = box[:, 0]
            y_coords = box[:, 1]
            x1 = max(0, int(min(x_coords)) - 3)
            x2 = int(max(x_coords)) + 3
            y1 = max(0, int(min(y_coords)) - 3)
            y2 = int(max(y_coords)) + 3
            crop = img_array[y1:y2, x1:x2]
            if crop.size > 0:
                crop_pil = Image.fromarray(crop)
                vi_text = vietocr.predict(crop_pil)
                lines.append(vi_text if vi_text.strip() else "")
        except Exception:
            lines.append("")

    raw = "\n".join(lines)
    return _nlp_normalize(raw)


# ── Main entry ──

def ocr_file(
    file_path: Path,
    dpi: int = 300,
    lang: str = "vie",
    engine: str = "tesseract",
    poppler_path: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        images = pdf_to_images(file_path, dpi=dpi, poppler_path=poppler_path)
    else:
        images = [Image.open(file_path)]

    total = len(images)
    parts: list[str] = []

    for i, img in enumerate(images):
        if engine == "hybrid":
            processed = prepare_paddle(img)
            text = ocr_image_hybrid(processed, lang=lang)
        elif engine == "vietocr":
            processed = prepare_paddle(img)
            text = ocr_image_vietocr_full(processed, lang=lang)
        elif engine == "rapid":
            processed = prepare_paddle(img)
            text = ocr_image_rapid(processed)
        elif engine == "paddle":
            processed = prepare_paddle(img)
            text = ocr_image_paddle(processed, lang=lang)
        elif engine == "easyocr":
            processed = prepare_paddle(img)
            text = ocr_image_easyocr(processed, lang=lang)
        else:
            processed = prepare_tesseract(img)
            text = ocr_image_tesseract(processed, lang=lang)
        parts.append(text)
        if progress_callback:
            progress_callback(i + 1, total)

    return "\n".join(parts)
