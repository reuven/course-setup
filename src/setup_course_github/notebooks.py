import re
from collections.abc import Iterable
from pathlib import Path

_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})\.\w+$")


def is_marimo_notebook(path: Path) -> bool:
    """Return True if a .py file looks like a marimo notebook."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return "import marimo" in text and "marimo.App()" in text


def find_notebooks(path: Path) -> tuple[list[Path], list[Path]]:
    """Return (ipynb_files, marimo_files) found directly in *path*, each sorted."""
    ipynb_files = sorted(path.glob("*.ipynb"))
    marimo_files = sorted(p for p in path.glob("*.py") if is_marimo_notebook(p))
    return ipynb_files, marimo_files


def date_range(files: Iterable[Path]) -> str:
    """Return '<first> → <last>' parsed from filenames, or 'n/a' if none match."""
    dates: list[str] = []
    for p in files:
        match = _DATE_PATTERN.search(p.name)
        if match:
            dates.append(match.group(1))
    dates.sort()
    if dates:
        return f"{dates[0]} → {dates[-1]}"
    return "n/a"
