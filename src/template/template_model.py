from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


@dataclass
class FieldDefinition:
    key: str
    start_line: int      # 0-based
    end_line: int         # inclusive
    start_char: int       # -1 = from beginning
    end_char: int         # -1 = to end of line


@dataclass
class ExtractionTemplate:
    name: str
    description: str = ""
    fields: list[FieldDefinition] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def save(self, folder: Path | None = None) -> Path:
        folder = folder or TEMPLATES_DIR
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{self.name}.json"
        data = asdict(self)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> ExtractionTemplate:
        data = json.loads(path.read_text(encoding="utf-8"))
        fields = [FieldDefinition(**f) for f in data.pop("fields", [])]
        return cls(**data, fields=fields)

    @staticmethod
    def list_templates(folder: Path | None = None) -> list[Path]:
        folder = folder or TEMPLATES_DIR
        if not folder.exists():
            return []
        return sorted(folder.glob("*.json"))
