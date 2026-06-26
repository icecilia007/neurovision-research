"""Path resolution helpers shared across scripts."""

from pathlib import Path


def resolve_base_dir(base: str) -> Path:
    return Path(base).resolve()


def resolve_input_path(base_dir: Path, raw_path: str, must_exist: bool = True) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    return path


def resolve_output_dir(base_dir: Path, raw_path: str, create: bool = True) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path
