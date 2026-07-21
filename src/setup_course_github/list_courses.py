import argparse
import re
import subprocess
import sys
from pathlib import Path

from setup_course_github import __author__, __email__, __version__
from setup_course_github.config import CourseConfig, load_config
from setup_course_github.notebooks import date_range, find_notebooks

JUNK_NAMES = frozenset(
    {"__pycache__", "build", "dist", "bin", "include", "lib", "node_modules"}
)
_YEAR_RE = re.compile(r"^\d{4}$")
_YEAR_TOKEN_RE = re.compile(r"^\d{4}(-\d{4})?$")
_GITHUB_RE = re.compile(r"github\.com[:/](?P<path>[^/]+/[^/]+?)(?:\.git)?/?$")


def _is_junk_name(name: str) -> bool:
    """True for hidden (dot-prefixed) or known build/cache directory names."""
    return name.startswith(".") or name in JUNK_NAMES


def is_course(path: Path) -> bool:
    """A course is a directory with a .git subdir and at least one notebook."""
    if not (path / ".git").is_dir():
        return False
    ipynb_files, marimo_files = find_notebooks(path)
    return bool(ipynb_files or marimo_files)


def is_archived_course(path: Path) -> bool:
    """An archived course: a non-junk directory containing at least one notebook.

    Unlike active courses, a ``.git`` subdir is NOT required (archived repos may
    have had it stripped).
    """
    if _is_junk_name(path.name):
        return False
    ipynb_files, marimo_files = find_notebooks(path)
    return bool(ipynb_files or marimo_files)


def course_summary_line(path: Path) -> str:
    """Return '<name> — <N> notebooks (<date range>)' for a course directory."""
    ipynb_files, marimo_files = find_notebooks(path)
    count = len(ipynb_files) + len(marimo_files)
    span = date_range(ipynb_files + marimo_files)
    return f"{path.name} — {count} notebooks ({span})"


def _github_url(remote: str) -> str | None:
    """Normalize a GitHub SSH/HTTPS remote to https://github.com/<owner>/<repo>.

    Returns None for an empty string or a non-GitHub remote.
    """
    match = _GITHUB_RE.search(remote)
    if not match:
        return None
    return f"https://github.com/{match.group('path')}"


def github_url(course_path: Path) -> str | None:
    """Return the course repo's GitHub URL from its local origin remote, or None.

    Reads ``git config --get remote.origin.url`` in *course_path*; no network.
    """
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=str(course_path),
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return _github_url(result.stdout.decode().strip())


def _matches_names(name: str, patterns: list[str]) -> bool:
    """True if *name* (case-insensitively) contains any of *patterns*.

    An empty *patterns* list matches everything.
    """
    if not patterns:
        return True
    lowered = name.lower()
    return any(p.lower() in lowered for p in patterns)


def filter_active(courses: list[Path], patterns: list[str]) -> list[Path]:
    """Keep only active-course paths whose name matches *patterns*."""
    return [c for c in courses if _matches_names(c.name, patterns)]


def filter_archived(
    archived: dict[str, list[Path]], years: list[str], patterns: list[str]
) -> dict[str, list[Path]]:
    """Filter the {year: courses} map by *years* (if non-empty) and *patterns*.

    Years not in *years* are dropped; within a kept year, courses are filtered by
    name; years left with no matching courses are omitted.
    """
    result: dict[str, list[Path]] = {}
    for year, courses in archived.items():
        if years and year not in years:
            continue
        matched = [c for c in courses if _matches_names(c.name, patterns)]
        if matched:
            result[year] = matched
    return result


def archive_summary_line(archived: dict[str, list[Path]], patterns: list[str]) -> str:
    """One-line summary of the archived-course count and year span."""
    total = sum(len(courses) for courses in archived.values())
    match_clause = ""
    if patterns:
        quoted = ", ".join(f'"{p}"' for p in patterns)
        match_clause = f" matching {quoted}"
    if total == 0:
        return f"Archived: none{match_clause}"
    years = sorted(archived.keys())
    span = years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}"
    noun = "course" if total == 1 else "courses"
    return (
        f"Archived: {total} {noun}{match_clause} across {span}"
        " — use --archived to list them."
    )


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
    """Return {year: [course dirs]} under archive_path/<YYYY>/<course>.

    Only directories named like a 4-digit year are treated as year groups, and
    only ``is_archived_course`` children are included.
    """
    result: dict[str, list[Path]] = {}
    if not archive_path.is_dir():
        return result
    for year_dir in sorted(archive_path.iterdir()):
        if not (year_dir.is_dir() and _YEAR_RE.match(year_dir.name)):
            continue
        courses = sorted(
            c for c in year_dir.iterdir() if c.is_dir() and is_archived_course(c)
        )
        if courses:
            result[year_dir.name] = courses
    return result


def _year_arg(value: str) -> str:
    """argparse type: accept a 4-digit year or an inclusive YYYY-YYYY range."""
    if not _YEAR_TOKEN_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid year '{value}' (expected YYYY or YYYY-YYYY)"
        )
    return value


def _expand_year_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Flatten single-year and range tokens into individual 4-digit years.

    Returns ``(years, notes)`` where *notes* holds a message for each reversed
    range that was auto-swapped. Ranges are inclusive; a reversed range like
    ``2022-2020`` is swapped to ``2020-2022``.
    """
    years: list[str] = []
    notes: list[str] = []
    for token in tokens:
        if "-" in token:
            start_s, end_s = token.split("-")
            start, end = int(start_s), int(end_s)
            if start > end:
                notes.append(
                    f"swapped reversed year range {start_s}-{end_s} → {end_s}-{start_s}"
                )
                start, end = end, start
            years.extend(f"{year:04d}" for year in range(start, end + 1))
        else:
            years.append(token)
    return years, notes


def _print_course(course: Path, indent: int, show_urls: bool) -> None:
    """Print a course summary line and, when *show_urls*, its indented URL line."""
    print(f"{' ' * indent}{course_summary_line(course)}")
    if show_urls:
        url = github_url(course)
        print(f"{' ' * (indent + 2)}{url or '(no GitHub remote)'}")


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
        "names",
        nargs="*",
        help="Filter courses by case-insensitive name substring (any match)",
    )
    parser.add_argument(
        "--dir",
        action="append",
        default=[],
        metavar="PATH",
        help="Directory to scan for active courses (repeatable; overrides config)",
    )
    parser.add_argument(
        "--active",
        action="store_true",
        help="Show only active courses",
    )
    parser.add_argument(
        "--archived",
        action="store_true",
        help="Show only archived courses (expanded, grouped by year)",
    )
    parser.add_argument(
        "--year",
        action="append",
        default=[],
        dest="years",
        type=_year_arg,
        metavar="YYYY",
        help="Restrict archived courses to a year or YYYY-YYYY range (repeatable)",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Show counts instead of individual course lines",
    )
    parser.add_argument(
        "--no-urls",
        action="store_true",
        help="Do not show each course's GitHub URL",
    )
    args = parser.parse_args(argv)

    years, year_notes = _expand_year_tokens(args.years)
    for note in year_notes:
        print(f"Note: {note}", file=sys.stderr)

    config = load_config()
    scan_dirs = resolve_scan_dirs(args.dir, config)

    patterns: list[str] = args.names
    has_names = bool(patterns)
    has_years = bool(args.years)
    only_active = args.active and not args.archived
    only_archived = args.archived and not args.active
    year_focus = has_years and not args.active and not args.archived
    show_active = not (only_archived or year_focus)
    show_archived = not only_active
    archive_expanded = args.archived or has_years
    show_urls = not args.no_urls

    if show_active:
        active = filter_active(find_active_courses(scan_dirs), patterns)
        if args.count:
            print(f"Active courses: {len(active)}")
        else:
            print("Active courses:")
            if active:
                for course in active:
                    _print_course(course, 2, show_urls)
            elif has_names:
                print(f"  No active courses match: {', '.join(patterns)}")
            else:
                print("  No active courses found")

    if show_archived:
        archived = filter_archived(
            find_archived_courses(config.archive_path), years, patterns
        )
        if show_active:
            print()
        if args.count:
            total = sum(len(courses) for courses in archived.values())
            print(f"Archived courses: {total}")
            for year in sorted(archived):
                print(f"  {year}: {len(archived[year])}")
        elif archive_expanded:
            print("Archived courses:")
            if archived:
                for year in sorted(archived):
                    print(f"  {year}:")
                    for course in archived[year]:
                        _print_course(course, 4, show_urls)
            elif has_names or has_years:
                print("  No archived courses match your filters")
            else:
                print("  No archived courses found")
        else:
            print(archive_summary_line(archived, patterns))


if __name__ == "__main__":  # pragma: no cover
    main()
