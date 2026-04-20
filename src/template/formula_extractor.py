"""Formula-based text extraction using anchor patterns.

Supported formulas:
  BETWEEN("anchor_before", "anchor_after")  — text between two anchors
  AFTER("anchor")                           — text after anchor until end or next line
  BEFORE("anchor")                          — text before anchor from start or prev line
  LINE_AFTER("anchor")                      — full line(s) after the line containing anchor
  LINE_BEFORE("anchor")                     — full line(s) before the line containing anchor
  BETWEEN_LINES("anchor_start", "anchor_end") — all lines between two anchor lines
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


@dataclass
class FormulaField:
    key: str             # e.g. "Họ tên"
    formula_type: str    # BETWEEN, AFTER, BEFORE, LINE_AFTER, LINE_BEFORE, BETWEEN_LINES
    anchor1: str         # first anchor text
    anchor2: str = ""    # second anchor (for BETWEEN, BETWEEN_LINES)
    strip: bool = True   # strip whitespace from result


@dataclass
class FormulaTemplate:
    name: str
    description: str = ""
    fields: list[FormulaField] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, folder: Path | None = None) -> Path:
        folder = folder or TEMPLATES_DIR
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{self.name}.json"
        data = asdict(self)
        data["_type"] = "formula"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> FormulaTemplate:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("_type", None)
        fields = [FormulaField(**f) for f in data.pop("fields", [])]
        return cls(**data, fields=fields)

    @staticmethod
    def list_templates(folder: Path | None = None) -> list[Path]:
        folder = folder or TEMPLATES_DIR
        if not folder.exists():
            return []
        result = []
        for p in sorted(folder.glob("*.json")):
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                if raw.get("_type") == "formula":
                    result.append(p)
            except Exception:
                pass
        return result


def _find_text(text: str, anchor: str) -> int:
    """Find anchor in text (case-insensitive fuzzy)."""
    # Try exact match first
    idx = text.find(anchor)
    if idx >= 0:
        return idx
    # Try case-insensitive
    idx = text.lower().find(anchor.lower())
    if idx >= 0:
        return idx
    # Try with normalized whitespace
    normalized = re.sub(r'\s+', ' ', text)
    norm_anchor = re.sub(r'\s+', ' ', anchor)
    idx = normalized.lower().find(norm_anchor.lower())
    if idx >= 0:
        return idx
    return -1


def _find_line_idx(lines: list[str], anchor: str) -> int:
    """Find which line contains the anchor."""
    for i, line in enumerate(lines):
        if anchor.lower() in line.lower():
            return i
        if re.sub(r'\s+', ' ', anchor.lower()) in re.sub(r'\s+', ' ', line.lower()):
            return i
    return -1


def extract_by_formula(text: str, field_def: FormulaField) -> str:
    """Extract a value from text using the formula definition."""
    ftype = field_def.formula_type.upper()
    lines = text.split("\n")

    if ftype == "BETWEEN":
        start = _find_text(text, field_def.anchor1)
        if start < 0:
            return ""
        start += len(field_def.anchor1)
        end = _find_text(text[start:], field_def.anchor2)
        if end < 0:
            return text[start:].strip() if field_def.strip else text[start:]
        result = text[start:start + end]

    elif ftype == "AFTER":
        start = _find_text(text, field_def.anchor1)
        if start < 0:
            return ""
        start += len(field_def.anchor1)
        # Take until end of line or next significant text
        remaining = text[start:]
        # Take first line of remaining
        first_line = remaining.split("\n")[0]
        result = first_line

    elif ftype == "BEFORE":
        end = _find_text(text, field_def.anchor1)
        if end < 0:
            return ""
        # Take from start of current line
        before = text[:end]
        last_line = before.split("\n")[-1]
        result = last_line

    elif ftype == "LINE_AFTER":
        idx = _find_line_idx(lines, field_def.anchor1)
        if idx < 0 or idx + 1 >= len(lines):
            return ""
        result = lines[idx + 1]

    elif ftype == "LINE_BEFORE":
        idx = _find_line_idx(lines, field_def.anchor1)
        if idx <= 0:
            return ""
        result = lines[idx - 1]

    elif ftype == "BETWEEN_LINES":
        start_idx = _find_line_idx(lines, field_def.anchor1)
        end_idx = _find_line_idx(lines, field_def.anchor2)
        if start_idx < 0 or end_idx < 0 or start_idx >= end_idx:
            return ""
        result = "\n".join(lines[start_idx + 1:end_idx])

    else:
        return f"[Unknown formula: {ftype}]"

    return result.strip() if field_def.strip else result


def extract_all_fields(text: str, template: FormulaTemplate) -> dict[str, str]:
    """Extract all fields from text using formula template."""
    result: dict[str, str] = {}
    for f in template.fields:
        result[f.key] = extract_by_formula(text, f)
    return result
