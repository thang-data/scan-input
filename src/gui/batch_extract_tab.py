from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.batch_worker import BatchExtractWorker
from src.io.file_utils import discover_files, is_supported_file
from src.template.formula_extractor import FormulaTemplate, TEMPLATES_DIR

FILE_FILTER = "Images & PDFs (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp)"


class BatchExtractTab(QWidget):
    def __init__(self, get_settings, main_window):
        super().__init__()
        self.get_settings = get_settings
        self.main_window = main_window
        self.file_list: list[Path] = []
        self.current_template: FormulaTemplate | None = None
        self.extraction_results: list[dict[str, str]] = []
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # File selection + template
        top = QHBoxLayout()
        self.btn_add_files = QPushButton("Add Files")
        self.btn_add_folder = QPushButton("Add Folder")
        self.btn_clear = QPushButton("Clear")
        top.addWidget(self.btn_add_files)
        top.addWidget(self.btn_add_folder)
        top.addWidget(self.btn_clear)
        top.addStretch()
        top.addWidget(QLabel("Template:"))
        self.combo_template = QComboBox()
        self.combo_template.setMinimumWidth(200)
        self.btn_refresh = QPushButton("↻")
        top.addWidget(self.combo_template)
        top.addWidget(self.btn_refresh)
        layout.addLayout(top)

        # File list
        self.list_widget = QListWidget()
        self.list_widget.setMaximumHeight(120)
        layout.addWidget(self.list_widget)

        # Start + progress
        mid = QHBoxLayout()
        self.btn_start = QPushButton("Start Extraction")
        self.btn_start.setStyleSheet("font-weight: bold; padding: 6px;")
        mid.addWidget(self.btn_start)
        self.lbl_status = QLabel("Ready")
        mid.addWidget(self.lbl_status)
        self.progress = QProgressBar()
        mid.addWidget(self.progress, stretch=1)
        layout.addLayout(mid)

        # Results table
        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Signals
        self.btn_add_files.clicked.connect(self._on_add_files)
        self.btn_add_folder.clicked.connect(self._on_add_folder)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_refresh.clicked.connect(self._refresh_templates)
        self.btn_start.clicked.connect(self._on_start)

        self._refresh_templates()

    def _refresh_templates(self):
        self.combo_template.clear()
        for p in FormulaTemplate.list_templates():
            self.combo_template.addItem(p.stem, str(p))

    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", FILE_FILTER)
        for f in files:
            p = Path(f)
            if is_supported_file(p) and p not in self.file_list:
                self.file_list.append(p)
                self.list_widget.addItem(str(p))

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            for f in discover_files(Path(folder)):
                if f not in self.file_list:
                    self.file_list.append(f)
                    self.list_widget.addItem(str(f))

    def _on_clear(self):
        self.file_list.clear()
        self.list_widget.clear()
        self.table.setRowCount(0)
        self.extraction_results.clear()

    def _on_start(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            return

        if not self.file_list:
            QMessageBox.warning(self, "No files", "Add files first.")
            return

        tmpl_path = self.combo_template.currentData()
        if not tmpl_path:
            QMessageBox.warning(self, "No template", "Select or create a template first.")
            return

        self.current_template = FormulaTemplate.load(Path(tmpl_path))
        settings = self.get_settings()

        # Setup table columns
        keys = [f.key for f in self.current_template.fields]
        self.table.setColumnCount(len(keys) + 1)
        self.table.setHorizontalHeaderLabels(["File"] + keys)
        self.table.setRowCount(0)
        self.extraction_results.clear()
        self.progress.setValue(0)

        self._worker = BatchExtractWorker(
            file_list=list(self.file_list),
            template=self.current_template,
            engine=settings["engine"],
            lang=settings["lang"],
            dpi=settings["dpi"],
            poppler_path=settings.get("poppler_path"),
        )
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_finished.connect(self._on_file_finished)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

        self.btn_start.setText("Cancel")

    def _on_file_started(self, name, idx, total):
        self.lbl_status.setText(f"Processing {name} ({idx}/{total})")

    def _on_file_finished(self, name, data):
        self.extraction_results.append(data)
        keys = [f.key for f in self.current_template.fields]
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))
        for col, key in enumerate(keys, 1):
            self.table.setItem(row, col, QTableWidgetItem(data.get(key, "")))

    def _on_file_error(self, name, err):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"[ERR] {name}: {err}"))

    def _on_all_done(self, success, errors):
        self.btn_start.setText("Start Extraction")
        self.lbl_status.setText("Done")
        # Share results with main window for Excel export tab
        self.main_window.extraction_results = self.extraction_results
        self.main_window.current_template = self.current_template
        QMessageBox.information(self, "Done", f"Success: {success}, Errors: {errors}")
