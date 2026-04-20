from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def discover_files(folder: Path) -> list[Path]:
    files = []
    for f in sorted(folder.rglob("*")):
        if f.is_file() and is_supported_file(f):
            files.append(f)
    return files


def generate_output_path(input_path: Path, output_dir: Path | None = None) -> Path:
    stem = input_path.stem
    name = f"{stem}_gen_from_scan.txt"
    if output_dir is not None:
        return output_dir / name
    return input_path.parent / name
