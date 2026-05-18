#!/usr/bin/env python3

import argparse
import datetime
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

from setup_course_github import __author__, __email__, __version__, get_github
from setup_course_github.config import load_config


class InsideCourseDirectoryError(RuntimeError):
    """Raised when a command is run from inside the course directory it targets."""


def _check_not_inside_course(dirname: str) -> None:
    """Raise InsideCourseDirectoryError if the user is inside *dirname*.

    Two cases are detected:
      1. *dirname* resolves to the current working directory (e.g. ``.`` or
         the absolute path of cwd).
      2. *dirname* does not exist relative to cwd, but its basename matches
         cwd's basename — the user has cd'd into the directory and then
         passed its bare name on the command line.
    """
    cwd = Path.cwd().resolve()
    target = Path(dirname)

    inside = False
    if target.exists() and target.resolve() == cwd:
        inside = True
    elif not target.exists() and target.name == cwd.name:
        inside = True

    if inside:
        raise InsideCourseDirectoryError(
            f"You appear to be inside '{dirname}'. "
            "Move up one directory (cd ..) and run the command again."
        )


def get_remote_url(dirname: str) -> str:
    """Return the git remote.origin.url for the repo in dirname."""
    result = subprocess.run(
        ["git", "config", "remote.origin.url"],
        capture_output=True,
        cwd=dirname,
    )
    return result.stdout.decode().strip()


def parse_repo_name(remote_url: str) -> str:
    """Parse 'username/reponame' from an SSH remote URL.

    Example: git@github.com:someuser/myrepo.git  →  someuser/myrepo
    """
    # remote_url looks like: git@github.com:username/reponame.git
    after_colon = remote_url.split(":")[1]  # username/reponame.git
    repo_with_git = after_colon  # username/reponame.git
    if repo_with_git.endswith(".git"):
        repo_with_git = repo_with_git[:-4]  # username/reponame
    return repo_with_git


def _confirm_create_dir(dest: Path, confirm: Callable[[str], str] = input) -> None:
    """Prompt the user to create an archive directory if it doesn't exist."""
    if not dest.exists():
        answer = confirm(f"Archive directory {dest} does not exist. Create it? [y/N] ")
        if answer.strip().lower().startswith("y"):
            dest.mkdir(parents=True, exist_ok=True)
        else:
            raise RuntimeError(f"Aborted: archive directory {dest} not created")


def _is_marimo_notebook(path: Path) -> bool:
    """Return True if a .py file looks like a marimo notebook."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return "import marimo" in text and "marimo.App()" in text


def _build_retirement_summary(
    dirname: str, repo_name: str, dest: Path, *, kept_public: bool = False
) -> str:
    """Build a human-readable retirement summary for the course.

    Must be called while *dirname* still exists on disk (before shutil.move).
    """
    dirpath = Path(dirname)

    # --- count notebooks ---------------------------------------------------
    ipynb_files = list(dirpath.glob("*.ipynb"))
    marimo_files = [p for p in dirpath.glob("*.py") if _is_marimo_notebook(p)]
    nb_count = len(ipynb_files) + len(marimo_files)

    if ipynb_files and marimo_files:
        nb_label = f"{nb_count} (.ipynb + marimo .py)"
    elif ipynb_files:
        nb_label = f"{nb_count} (.ipynb)"
    elif marimo_files:
        nb_label = f"{nb_count} (marimo .py)"
    else:
        nb_label = "0"

    # --- date range from filenames -----------------------------------------
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\.\w+$")
    dates: list[str] = []
    for p in ipynb_files + marimo_files:
        m = date_pattern.search(p.name)
        if m:
            dates.append(m.group(1))
    dates.sort()
    if dates:
        date_range = f"{dates[0]} \u2192 {dates[-1]}"
    else:
        date_range = "n/a"

    # --- dependencies from pyproject.toml ----------------------------------
    pyproject_path = dirpath / "pyproject.toml"
    deps_str: str
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            raw_deps: list[str] = data.get("project", {}).get("dependencies", [])
            # Strip version specifiers for display
            dep_names = [re.split(r"[><=!~;]", d)[0].strip() for d in raw_deps]
            deps_str = ", ".join(dep_names) if dep_names else "none"
        except Exception:
            deps_str = "none"
    else:
        deps_str = "none"

    # --- build the summary string ------------------------------------------
    repo_url = f"https://github.com/{repo_name}"
    lines = [
        "\u2500\u2500 Retirement Summary \u2500\u2500",
        f"  Course: {dirpath.name}",
        f"  Notebooks: {nb_label}",
        f"  Date range: {date_range}",
        f"  Dependencies: {deps_str}",
        f"  Archived to: {dest / dirpath.name}",
        f"  GitHub repo: {repo_url} (still public)"
        if kept_public
        else f"  GitHub repo: {repo_url} (now private)",
    ]
    return "\n".join(lines)


def retire_course(dirname: str, keep_public: bool = False) -> None:
    """Move the local directory to the archive, optionally making the repo private."""
    _check_not_inside_course(dirname)

    config = load_config()

    remote_url = get_remote_url(dirname)
    repo_name = parse_repo_name(remote_url)

    g = get_github()
    repo = g.get_repo(repo_name)
    if not keep_public:
        repo.edit(private=True)

    year = datetime.datetime.now().year
    dest = config.archive_path / str(year)
    _confirm_create_dir(dest)

    summary = _build_retirement_summary(
        dirname, repo_name, dest, kept_public=keep_public
    )
    shutil.move(dirname, dest)

    print(f"Successfully retired {dirname} \u2192 {dest}")
    print(summary)


def main() -> None:
    pypi_url = "https://pypi.org/project/course-setup/"
    author_line = f"{__author__} <{__email__}>"

    parser = argparse.ArgumentParser(
        epilog=f"Version {__version__} — {pypi_url}\n{author_line}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}\n{pypi_url}\n{author_line}",
    )
    parser.add_argument(
        "--keep-public",
        action="store_true",
        default=False,
        help="archive without making the GitHub repo private",
    )
    parser.add_argument(
        "dirnames", nargs="+", help="Path(s) to course directories to retire"
    )
    args = parser.parse_args()

    errors: list[tuple[str, str]] = []
    for dirname in args.dirnames:
        try:
            retire_course(dirname, keep_public=args.keep_public)
        except Exception as e:
            print(f"Error retiring {dirname}: {e}")
            errors.append((dirname, str(e)))

    if errors:
        print(f"\n{len(errors)} error(s) occurred:")
        for dirname, msg in errors:
            print(f"  {dirname}: {msg}")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
