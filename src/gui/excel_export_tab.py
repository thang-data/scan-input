from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.io.excel_io import get_workbook_info, write_extraction_to_excel


class ExcelExportTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.excel_path: Path | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Load Excel
        top = QHBoxLayout()
        self.btn_load = QPushButton("Load Excel File")
        self.lbl_path = QLabel("No file loaded")
        top.addWidget(self.btn_load)
        top.addWidget(self.lbl_path, stretch=1)
        layout.addLayout(top)

        # Sheet selector
        sheet_row = QHBoxLayout()
        sheet_row.addWidget(QLabel("Sheet:"))
        self.combo_sheet = QComboBox()
        self.combo_sheet.setMinimumWidth(200)
        sheet_row.addWidget(self.combo_sheet)
        sheet_row.addStretch()
        self.btn_load_data = QPushButton("Load Extraction Data")
        sheet_row.addWidget(self.btn_load_data)
        layout.addLayout(sheet_row)

        # Mapping table
        layout.addWidget(QLabel("Map keys to Excel columns:"))
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(3)
        self.mapping_table.setHorizontalHeaderLabels(["Key", "Column (e.g. B)", "Start Row (e.g. 5)"])
        self.mapping_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.mapping_table)

        # Preview info
        self.lbl_info = QLabel("")
        layout.addWidget(self.lbl_info)

        # Export
        self.btn_export = QPushButton("Export & Save As...")
        self.btn_export.setStyleSheet("font-weight: bold; padding: 6px;")
        layout.addWidget(self.btn_export)

        # Signals
        self.btn_load.clicked.connect(self._on_load_excel)
        self.btn_load_data.clicked.connect(self._on_load_data)
        self.btn_export.clicked.connect(self._on_export)

    def _on_load_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel (*.xlsx)")
        if not path:
            return
        self.excel_path = Path(path)
        self.lbl_path.setText(str(self.excel_path))
        try:
            sheets = get_workbook_info(self.excel_path)
            self.combo_sheet.clear()
            self.combo_sheet.addItems(sheets)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot read Excel: {e}")

    def _on_load_data(self):
        template = getattr(self.main_window, "current_template", None)
        results = getattr(self.main_window, "extraction_results", [])

        if not template or not results:
            QMessageBox.warning(self, "No data",
                                "Run Batch Extraction first (Tab 3).")
            return

        keys = [f.key for f in template.fields]
        self.mapping_table.setRowCount(len(keys))
        for i, key in enumerate(keys):
            item = QTableWidgetItem(key)
            item.setFlags(item.flags() & ~(item.flags() & item.flags()))  # non-editable
            self.mapping_table.setItem(i, 0, QTableWidgetItem(key))
            # Default column letters
            col_letter = chr(ord("B") + i)
            self.mapping_table.setItem(i, 1, QTableWidgetItem(col_letter))
            self.mapping_table.setItem(i, 2, QTableWidgetItem("2"))

        self.lbl_info.setText(f"Loaded {len(results)} rows, {len(keys)} fields")

    def _on_export(self):
        if not self.excel_path:
            QMessageBox.warning(self, "No Excel", "Load an Excel file first.")
            return

        results = getattr(self.main_window, "extraction_results", [])
        if not results:
            QMessageBox.warning(self, "No data", "Run Batch Extraction first.")
            return

        sheet = self.combo_sheet.currentText()
        if not sheet:
            QMessageBox.warning(self, "No sheet", "Select a sheet.")
            return

        # Build mapping from table
        mapping: dict[str, tuple[str, int]] = {}
        for row in range(self.mapping_table.rowCount()):
            key_item = self.mapping_table.item(row, 0)
            col_item = self.mapping_table.item(row, 1)
            row_item = self.mapping_table.item(row, 2)
            if not key_item or not col_item or not row_item:
                continue
            key = key_item.text().strip()
            col = col_item.text().strip().upper()
            try:
                start_row = int(row_item.text().strip())
            except ValueError:
                QMessageBox.warning(self, "Invalid row", f"Invalid start row for '{key}'")
                return
            if key and col:
                mapping[key] = (col, start_row)

        if not mapping:
            QMessageBox.warning(self, "No mapping", "Define column mappings.")
            return

        # Save dialog
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save Excel As", str(self.excel_path.parent / f"{self.excel_path.stem}_filled.xlsx"),
            "Excel (*.xlsx)")
        if not out_path:
            return

        try:
            write_extraction_to_excel(
                self.excel_path, sheet, mapping, results, Path(out_path))
            QMessageBox.information(self, "Success", f"Saved to {out_path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))
