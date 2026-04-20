from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ocr.engine import ocr_file
from src.template.formula_extractor import (
    FormulaField,
    FormulaTemplate,
    extract_by_formula,
    TEMPLATES_DIR,
)


class _OcrWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, path, engine, lang, dpi, poppler_path=None):
        super().__init__()
        self.path, self.engine, self.lang = path, engine, lang
        self.dpi, self.poppler_path = dpi, poppler_path

    def run(self):
        try:
            self.finished.emit(ocr_file(self.path, self.dpi, self.lang,
                                        self.engine, self.poppler_path))
        except Exception as e:
            self.error.emit(str(e))


class TemplateEditorTab(QWidget):
    def __init__(self, get_settings):
        super().__init__()
        self.get_settings = get_settings
        self.fields: list[FormulaField] = []
        self.ocr_text = ""
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ── Top: OCR button ──
        top = QHBoxLayout()
        self.btn_ocr = QPushButton("OCR a Sample File")
        top.addWidget(self.btn_ocr)
        top.addStretch()
        layout.addLayout(top)

        # ── Middle: Text + Formula builder ──
        mid = QHBoxLayout()

        # Left: OCR text
        left = QVBoxLayout()
        left.addWidget(QLabel("OCR Text (select text to use as anchors):"))
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        left.addWidget(self.text_edit)
        mid.addLayout(left, stretch=2)

        # Right: Formula builder + field list
        right = QVBoxLayout()

        # Formula type
        right.addWidget(QLabel("Formula Type:"))
        self.combo_formula = QComboBox()
        self.combo_formula.addItems([
            "BETWEEN — text between 2 anchors",
            "AFTER — text after anchor",
            "BEFORE — text before anchor",
            "LINE_AFTER — next line after anchor",
            "LINE_BEFORE — line before anchor",
            "BETWEEN_LINES — lines between 2 anchors",
        ])
        right.addWidget(self.combo_formula)

        # Anchor 1
        a1_row = QHBoxLayout()
        a1_row.addWidget(QLabel("Anchor 1:"))
        self.anchor1_edit = QLineEdit()
        self.anchor1_edit.setPlaceholderText("Select text or type")
        a1_row.addWidget(self.anchor1_edit, stretch=1)
        self.btn_set_a1 = QPushButton("← Set from selection")
        a1_row.addWidget(self.btn_set_a1)
        right.addLayout(a1_row)

        # Anchor 2
        a2_row = QHBoxLayout()
        a2_row.addWidget(QLabel("Anchor 2:"))
        self.anchor2_edit = QLineEdit()
        self.anchor2_edit.setPlaceholderText("(for BETWEEN formulas)")
        a2_row.addWidget(self.anchor2_edit, stretch=1)
        self.btn_set_a2 = QPushButton("← Set from selection")
        a2_row.addWidget(self.btn_set_a2)
        right.addLayout(a2_row)

        # Key name
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("Key:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("e.g. Họ tên, Ngày sinh")
        key_row.addWidget(self.key_edit, stretch=1)
        right.addLayout(key_row)

        # Preview + Add
        btn_row = QHBoxLayout()
        self.btn_preview = QPushButton("Preview Result")
        self.btn_add = QPushButton("Add Field")
        self.btn_add.setStyleSheet("font-weight: bold;")
        btn_row.addWidget(self.btn_preview)
        btn_row.addWidget(self.btn_add)
        right.addLayout(btn_row)

        # Preview result
        self.lbl_preview = QLabel("")
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setStyleSheet("background: #f0f0f0; padding: 4px; border: 1px solid #ccc;")
        right.addWidget(self.lbl_preview)

        # Field list
        right.addWidget(QLabel("Defined Fields:"))
        self.field_list = QListWidget()
        right.addWidget(self.field_list)

        self.btn_delete = QPushButton("Delete Selected Field")
        right.addWidget(self.btn_delete)

        mid.addLayout(right, stretch=1)
        layout.addLayout(mid)

        # ── Bottom: Save/Load ──
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("Template Name:"))
        self.name_edit = QLineEdit()
        bottom.addWidget(self.name_edit, stretch=1)
        self.btn_save = QPushButton("Save Template")
        self.btn_load = QPushButton("Load Template")
        bottom.addWidget(self.btn_save)
        bottom.addWidget(self.btn_load)
        layout.addLayout(bottom)

        # ── Signals ──
        self.btn_ocr.clicked.connect(self._on_ocr)
        self.btn_set_a1.clicked.connect(lambda: self._set_anchor(self.anchor1_edit))
        self.btn_set_a2.clicked.connect(lambda: self._set_anchor(self.anchor2_edit))
        self.btn_preview.clicked.connect(self._on_preview)
        self.btn_add.clicked.connect(self._on_add_field)
        self.btn_delete.clicked.connect(self._on_delete_field)
        self.btn_save.clicked.connect(self._on_save)
        self.btn_load.clicked.connect(self._on_load)

    def _get_formula_type(self) -> str:
        return self.combo_formula.currentText().split(" — ")[0]

    def _set_anchor(self, edit: QLineEdit):
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            edit.setText(cursor.selectedText())
        else:
            QMessageBox.information(self, "Tip", "Select text in the OCR output first.")

    # ── OCR ──

    def _on_ocr(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select sample file", "",
            "Images & PDFs (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
        if not path:
            return
        s = self.get_settings()
        self.btn_ocr.setEnabled(False)
        self.btn_ocr.setText("Processing...")
        self._worker = _OcrWorker(Path(path), s["engine"], s["lang"], s["dpi"], s.get("poppler_path"))
        self._worker.finished.connect(self._on_ocr_done)
        self._worker.error.connect(self._on_ocr_error)
        self._worker.start()

    def _on_ocr_done(self, text):
        self.ocr_text = text
        self.text_edit.setPlainText(text)
        self.btn_ocr.setEnabled(True)
        self.btn_ocr.setText("OCR a Sample File")

    def _on_ocr_error(self, err):
        QMessageBox.warning(self, "OCR Error", err)
        self.btn_ocr.setEnabled(True)
        self.btn_ocr.setText("OCR a Sample File")

    # ── Preview ──

    def _on_preview(self):
        if not self.ocr_text:
            QMessageBox.warning(self, "No text", "OCR a file first.")
            return
        a1 = self.anchor1_edit.text().strip()
        if not a1:
            QMessageBox.warning(self, "No anchor", "Set Anchor 1.")
            return
        field_def = FormulaField(
            key="preview",
            formula_type=self._get_formula_type(),
            anchor1=a1,
            anchor2=self.anchor2_edit.text().strip(),
        )
        result = extract_by_formula(self.ocr_text, field_def)
        self.lbl_preview.setText(f"Result: {result}" if result else "No match found")

        # Highlight the result in text
        self._highlight_text(result)

    def _highlight_text(self, target: str):
        """Highlight extracted text in the text editor."""
        if not target:
            return
        # Reset formatting
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        cursor.setCharFormat(fmt)

        # Highlight matches
        fmt_highlight = QTextCharFormat()
        fmt_highlight.setBackground(QColor("#FFFF00"))
        text = self.text_edit.toPlainText()
        start = 0
        while True:
            idx = text.find(target, start)
            if idx < 0:
                break
            cursor.setPosition(idx)
            cursor.setPosition(idx + len(target), QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(fmt_highlight)
            start = idx + len(target)

    # ── Add/Delete field ──

    def _on_add_field(self):
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "No key", "Enter a key name.")
            return
        a1 = self.anchor1_edit.text().strip()
        if not a1:
            QMessageBox.warning(self, "No anchor", "Set Anchor 1.")
            return

        ftype = self._get_formula_type()
        field_def = FormulaField(
            key=key,
            formula_type=ftype,
            anchor1=a1,
            anchor2=self.anchor2_edit.text().strip(),
        )
        self.fields.append(field_def)

        display = f'{key}  |  {ftype}("{a1}"'
        if field_def.anchor2:
            display += f', "{field_def.anchor2}"'
        display += ")"
        self.field_list.addItem(display)

        # Clear inputs
        self.key_edit.clear()
        self.anchor1_edit.clear()
        self.anchor2_edit.clear()
        self.lbl_preview.clear()

    def _on_delete_field(self):
        row = self.field_list.currentRow()
        if row >= 0:
            self.field_list.takeItem(row)
            self.fields.pop(row)

    # ── Save/Load ──

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "No name", "Enter a template name.")
            return
        if not self.fields:
            QMessageBox.warning(self, "No fields", "Add at least one field.")
            return
        tmpl = FormulaTemplate(name=name, fields=list(self.fields))
        path = tmpl.save()
        QMessageBox.information(self, "Saved", f"Template saved: {path.name}")

    def _on_load(self):
        templates = FormulaTemplate.list_templates()
        if not templates:
            QMessageBox.warning(self, "No templates", "No formula templates found.")
            return
        names = [t.stem for t in templates]
        name, ok = QInputDialog.getItem(self, "Load Template", "Select:", names, 0, False)
        if not ok:
            return
        path = TEMPLATES_DIR / f"{name}.json"
        tmpl = FormulaTemplate.load(path)
        self.fields = list(tmpl.fields)
        self.name_edit.setText(tmpl.name)
        self.field_list.clear()
        for f in self.fields:
            display = f'{f.key}  |  {f.formula_type}("{f.anchor1}"'
            if f.anchor2:
                display += f', "{f.anchor2}"'
            display += ")"
            self.field_list.addItem(display)
