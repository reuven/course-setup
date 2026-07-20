import argparse
from pathlib import Path

from setup_course_github import __author__, __email__, __version__
from setup_course_github.config import CourseConfig, load_config
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


def main(argv: list[str] | None = None) -> None:
    pypi_url = "https://pypi.org/project/course-setup/"
    author_line = f"{__author__} <{__email__}>"

    parser = argparse.ArgumentParser(
        description="List active and archived courses.",
        epilog=f"Version {__version__} — {pypi_url}\n{author_line}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}\n{pypi_url}\n{author_line}",
    )
    parser.add_argument(
        "dirs",
        nargs="*",
        help="Directories to scan (overrides course_dirs from config)",
    )
    args = parser.parse_args(argv)

    config = load_config()
    scan_dirs = resolve_scan_dirs(args.dirs, config)

    active = find_active_courses(scan_dirs)
    print("Active courses:")
    if active:
        for course in active:
            print(f"  {course_summary_line(course)}")
    else:
        print("  No active courses found")

    archived = find_archived_courses(config.archive_path)
    print("\nArchived courses:")
    if archived:
        for year, courses in archived.items():
            print(f"  {year}:")
            for course in courses:
                print(f"    {course_summary_line(course)}")
    else:
        print("  No archived courses found")


if __name__ == "__main__":  # pragma: no cover
    main()
