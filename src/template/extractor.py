from src.template.template_model import ExtractionTemplate


def extract_fields(text: str, template: ExtractionTemplate) -> dict[str, str]:
    """Extract fields from OCR text based on template definitions."""
    lines = text.split("\n")
    result: dict[str, str] = {}

    for field_def in template.fields:
        parts: list[str] = []
        for line_idx in range(field_def.start_line, field_def.end_line + 1):
            if line_idx < 0 or line_idx >= len(lines):
                continue
            line = lines[line_idx]
            if line_idx == field_def.start_line and line_idx == field_def.end_line:
                sc = 0 if field_def.start_char == -1 else field_def.start_char
                ec = len(line) if field_def.end_char == -1 else field_def.end_char
                parts.append(line[sc:ec])
            elif line_idx == field_def.start_line:
                sc = 0 if field_def.start_char == -1 else field_def.start_char
                parts.append(line[sc:])
            elif line_idx == field_def.end_line:
                ec = len(line) if field_def.end_char == -1 else field_def.end_char
                parts.append(line[:ec])
            else:
                parts.append(line)

        result[field_def.key] = " ".join(parts).strip()

    return result
