from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.ocr.engine import ocr_file
from src.template.formula_extractor import FormulaTemplate, extract_all_fields


class BatchExtractWorker(QThread):
    file_started = pyqtSignal(str, int, int)
    file_finished = pyqtSignal(str, dict)
    file_error = pyqtSignal(str, str)
    progress = pyqtSignal(int)
    all_done = pyqtSignal(int, int)

    def __init__(
        self,
        file_list: list[Path],
        template: FormulaTemplate,
        engine: str,
        lang: str,
        dpi: int,
        poppler_path: str | None = None,
    ):
        super().__init__()
        self.file_list = file_list
        self.template = template
        self.engine = engine
        self.lang = lang
        self.dpi = dpi
        self.poppler_path = poppler_path

    def run(self):
        total = len(self.file_list)
        success = 0
        errors = 0

        for i, fp in enumerate(self.file_list):
            if self.isInterruptionRequested():
                break
            self.file_started.emit(fp.name, i + 1, total)
            try:
                text = ocr_file(fp, dpi=self.dpi, lang=self.lang,
                                engine=self.engine, poppler_path=self.poppler_path)
                data = extract_all_fields(text, self.template)
                data["_file"] = fp.name
                self.file_finished.emit(fp.name, data)
                success += 1
            except Exception as e:
                self.file_error.emit(fp.name, str(e))
                errors += 1
            self.progress.emit(int((i + 1) / total * 100))

        self.all_done.emit(success, errors)
