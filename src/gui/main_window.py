from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.gui.batch_extract_tab import BatchExtractTab
from src.gui.excel_export_tab import ExcelExportTab
from src.gui.template_editor import TemplateEditorTab
from src.gui.worker import OcrWorker
from src.io.file_utils import discover_files, is_supported_file
from src.ocr.engine import check_tesseract

FILE_FILTER = "Images & PDFs (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp)"

ENGINE_MAP = {
    "VietOCR (full)": "vietocr",
    "Hybrid (Rapid+VietOCR+NLP)": "hybrid",
    "Tesseract": "tesseract",
    "RapidOCR": "rapid",
    "EasyOCR": "easyocr",
    "PaddleOCR": "paddle",
}


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scan Input - OCR Tool")
        self.setMinimumSize(900, 700)
        self.worker: OcrWorker | None = None
        self.file_list: list[Path] = []

        # Shared state for batch extraction → excel export
        self.extraction_results: list[dict[str, str]] = []
        self.current_template = None

        self._build_ui()
        self._check_tesseract()

    def get_settings(self) -> dict:
        """Return current OCR settings as dict. Used by other tabs."""
        tesseract_path = self.tesseract_edit.text().strip()
        if tesseract_path:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return {
            "engine": ENGINE_MAP[self.combo_engine.currentText()],
            "lang": self.combo_lang.currentText(),
            "dpi": int(self.combo_dpi.currentText()),
            "poppler_path": self.poppler_edit.text().strip() or None,
        }

    def _build_ui(self):
        root = QVBoxLayout(self)

        # --- Shared settings bar (visible across all tabs) ---
        settings_layout = QHBoxLayout()

        settings_layout.addWidget(QLabel("Engine:"))
        self.combo_engine = QComboBox()
        self.combo_engine.addItems(list(ENGINE_MAP.keys()))
        settings_layout.addWidget(self.combo_engine)

        settings_layout.addWidget(QLabel("Lang:"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["vie", "eng", "vie+eng", "jpn", "jpn+eng"])
        settings_layout.addWidget(self.combo_lang)

        settings_layout.addWidget(QLabel("DPI:"))
        self.combo_dpi = QComboBox()
        self.combo_dpi.addItems(["200", "300", "400", "600"])
        self.combo_dpi.setCurrentText("300")
        settings_layout.addWidget(self.combo_dpi)

        settings_layout.addWidget(QLabel("Tesseract:"))
        self.tesseract_edit = QLineEdit()
        self.tesseract_edit.setPlaceholderText("Auto")
        self.tesseract_edit.setMaximumWidth(150)
        settings_layout.addWidget(self.tesseract_edit)

        settings_layout.addWidget(QLabel("Poppler:"))
        self.poppler_edit = QLineEdit()
        self.poppler_edit.setPlaceholderText("Auto")
        self.poppler_edit.setMaximumWidth(150)
        settings_layout.addWidget(self.poppler_edit)

        root.addLayout(settings_layout)

        # --- Tabs ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_ocr_tab(), "1. OCR")
        self.tabs.addTab(TemplateEditorTab(self.get_settings), "2. Template Editor")
        self.tabs.addTab(BatchExtractTab(self.get_settings, self), "3. Batch Extract")
        self.tabs.addTab(ExcelExportTab(self), "4. Excel Export")
        root.addWidget(self.tabs)

    def _build_ocr_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Input files
        input_group = QGroupBox("Input Files")
        input_layout = QHBoxLayout(input_group)
        self.list_widget = QListWidget()
        input_layout.addWidget(self.list_widget, stretch=1)

        btn_layout = QVBoxLayout()
        self.btn_add_folder = QPushButton("Add Folder")
        self.btn_add_files = QPushButton("Add Files")
        self.btn_clear = QPushButton("Clear")
        btn_layout.addWidget(self.btn_add_folder)
        btn_layout.addWidget(self.btn_add_files)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        input_layout.addLayout(btn_layout)
        layout.addWidget(input_group)

        # Output folder
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Folder:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Leave empty to save alongside original files")
        output_layout.addWidget(self.output_edit, stretch=1)
        self.btn_browse_output = QPushButton("Browse")
        output_layout.addWidget(self.btn_browse_output)
        layout.addLayout(output_layout)

        self.chk_alongside = QCheckBox("Save output alongside original files")
        self.chk_alongside.setChecked(True)
        layout.addWidget(self.chk_alongside)

        # Output format
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("Output Format:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["Text (.txt)", "Word (.docx)", "Both (.txt + .docx)"])
        fmt_layout.addWidget(self.combo_format)
        fmt_layout.addStretch()
        layout.addLayout(fmt_layout)

        # Start
        self.btn_start = QPushButton("Start OCR")
        self.btn_start.setStyleSheet("font-weight: bold; padding: 8px;")
        layout.addWidget(self.btn_start)

        # Progress
        self.lbl_status = QLabel("Ready")
        layout.addWidget(self.lbl_status)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Log
        layout.addWidget(QLabel("Log:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Signals
        self.btn_add_folder.clicked.connect(self.on_add_folder)
        self.btn_add_files.clicked.connect(self.on_add_files)
        self.btn_clear.clicked.connect(self.on_clear)
        self.btn_browse_output.clicked.connect(self.on_browse_output)
        self.btn_start.clicked.connect(self.on_start_or_cancel)
        self.chk_alongside.toggled.connect(self._toggle_output_dir)
        self._toggle_output_dir(True)

        return tab

    def _toggle_output_dir(self, alongside: bool):
        self.output_edit.setEnabled(not alongside)
        self.btn_browse_output.setEnabled(not alongside)

    def _check_tesseract(self):
        ok, msg = check_tesseract()
        if not ok:
            QMessageBox.warning(self, "Tesseract OCR", msg)

    # --- File management ---

    def on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return
        for f in discover_files(Path(folder)):
            if f not in self.file_list:
                self.file_list.append(f)
                self.list_widget.addItem(str(f))

    def on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", FILE_FILTER)
        for f in files:
            p = Path(f)
            if is_supported_file(p) and p not in self.file_list:
                self.file_list.append(p)
                self.list_widget.addItem(str(p))

    def on_clear(self):
        self.file_list.clear()
        self.list_widget.clear()

    def on_browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_edit.setText(folder)

    # --- OCR ---

    def on_start_or_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.btn_start.setEnabled(False)
            return
        self._start_ocr()

    def _start_ocr(self):
        if not self.file_list:
            QMessageBox.warning(self, "No files", "Add files first.")
            return

        output_dir = None
        if not self.chk_alongside.isChecked():
            t = self.output_edit.text().strip()
            if not t:
                QMessageBox.warning(self, "No output", "Select output folder.")
                return
            output_dir = Path(t)
            if not output_dir.is_dir():
                QMessageBox.warning(self, "Invalid", f"Folder not found: {output_dir}")
                return

        settings = self.get_settings()
        self.progress_bar.setValue(0)
        self.log_text.append(f"\n--- OCR: {len(self.file_list)} files, {settings['engine']}, {settings['lang']}, {settings['dpi']}dpi ---")

        fmt_map = {"Text (.txt)": "txt", "Word (.docx)": "docx", "Both (.txt + .docx)": "both"}
        output_format = fmt_map[self.combo_format.currentText()]

        self.worker = OcrWorker(
            file_list=list(self.file_list),
            output_dir=output_dir,
            lang=settings["lang"],
            dpi=settings["dpi"],
            engine=settings["engine"],
            output_format=output_format,
            poppler_path=settings["poppler_path"],
        )
        self.worker.file_started.connect(lambda n, i, t: self.lbl_status.setText(f"{n} ({i}/{t})"))
        self.worker.file_finished.connect(lambda n, p: self.log_text.append(f"[OK] {n} → {p}"))
        self.worker.file_error.connect(lambda n, e: self.log_text.append(f'<span style="color:red">[ERR] {n} - {e}</span>'))
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.all_done.connect(self._on_all_done)
        self.worker.start()
        self.btn_start.setText("Cancel")

    def _on_all_done(self, success, errors):
        self.btn_start.setText("Start OCR")
        self.btn_start.setEnabled(True)
        self.lbl_status.setText("Done")
        self.log_text.append(f"--- Done: {success} OK, {errors} errors ---")
        QMessageBox.information(self, "OCR Complete", f"Success: {success}\nErrors: {errors}")
