from pathlib import Path

from setup_course_github.config import CourseConfig
from setup_course_github.notebooks import date_range, find_notebooks


def is_course(path: Path) -> bool:
    """A course is a directory with a .git subdir and at least one notebook."""
    if not (path / ".git").is_dir():
        return False
    ipynb_files, marimo_files = find_notebooks(path)
    return bool(ipynb_files or marimo_files)


def course_summary_line(path: Path) -> str:
    """Return '<name> — <N> notebooks (<date range>)' for a course directory."""
    ipynb_files, marimo_files = find_notebooks(path)
    count = len(ipynb_files) + len(marimo_files)
    span = date_range(ipynb_files + marimo_files)
    return f"{path.name} — {count} notebooks ({span})"


def resolve_scan_dirs(cli_dirs: list[str], config: CourseConfig) -> list[Path]:
    """Choose which directories to scan: CLI args, else config, else cwd."""
    if cli_dirs:
        return [Path(d).expanduser() for d in cli_dirs]
    if config.course_dirs:
        return [Path(d).expanduser() for d in config.course_dirs]
    return [Path(".")]


def find_active_courses(scan_dirs: list[Path]) -> list[Path]:
    """Return course directories found directly under each scan dir, sorted."""
    courses: list[Path] = []
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for child in sorted(scan_dir.iterdir()):
            if child.is_dir() and is_course(child):
                courses.append(child)
    return courses


def find_archived_courses(archive_path: Path) -> dict[str, list[Path]]:
    """Return {year: [course dirs]} found under archive_path/<year>/<course>."""
    result: dict[str, list[Path]] = {}
    if not archive_path.is_dir():
        return result
    for year_dir in sorted(archive_path.iterdir()):
        if not year_dir.is_dir():
            continue
        courses = sorted(c for c in year_dir.iterdir() if c.is_dir())
        if courses:
            result[year_dir.name] = courses
    return result
