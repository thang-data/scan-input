from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.io.file_utils import generate_output_path
from src.io.pdf_reader import is_scan_pdf, extract_text_pdf
from src.io.word_export import text_to_word
from src.ocr.engine import ocr_file


class OcrWorker(QThread):
    file_started = pyqtSignal(str, int, int)
    file_finished = pyqtSignal(str, str)
    file_error = pyqtSignal(str, str)
    progress = pyqtSignal(int)
    all_done = pyqtSignal(int, int)

    def __init__(
        self,
        file_list: list[Path],
        output_dir: Path | None,
        lang: str,
        dpi: int,
        engine: str = "vietocr",
        output_format: str = "txt",  # "txt", "docx", "both"
        poppler_path: str | None = None,
    ):
        super().__init__()
        self.file_list = file_list
        self.output_dir = output_dir
        self.lang = lang
        self.dpi = dpi
        self.engine = engine
        self.output_format = output_format
        self.poppler_path = poppler_path

    def _get_text(self, file_path: Path) -> str:
        """Smart text extraction — use pdfplumber for text PDFs, OCR for scans/images."""
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            try:
                if not is_scan_pdf(file_path):
                    text = extract_text_pdf(file_path)
                    if text.strip():
                        return text
            except Exception:
                pass
        # Fallback to OCR
        return ocr_file(file_path, dpi=self.dpi, lang=self.lang,
                        engine=self.engine, poppler_path=self.poppler_path)

    def run(self):
        total = len(self.file_list)
        success = 0
        errors = 0

        for i, file_path in enumerate(self.file_list):
            if self.isInterruptionRequested():
                break

            self.file_started.emit(file_path.name, i + 1, total)

            try:
                text = self._get_text(file_path)
                outputs = []

                # Save as .txt
                if self.output_format in ("txt", "both"):
                    txt_path = generate_output_path(file_path, self.output_dir)
                    txt_path.write_text(text, encoding="utf-8")
                    outputs.append(str(txt_path))

                # Save as .docx
                if self.output_format in ("docx", "both"):
                    base = generate_output_path(file_path, self.output_dir)
                    docx_path = base.with_suffix(".docx")
                    text_to_word(text, docx_path)
                    outputs.append(str(docx_path))

                self.file_finished.emit(file_path.name, ", ".join(outputs))
                success += 1
            except Exception as e:
                self.file_error.emit(file_path.name, str(e))
                errors += 1

            self.progress.emit(int((i + 1) / total * 100))

        self.all_done.emit(success, errors)
