#!/usr/bin/env python3

import argparse
import shutil
import sys
from pathlib import Path

from setup_course_github import __author__, __email__, __version__, get_github
from setup_course_github.retire_course import (
    _check_not_inside_course,
    get_remote_url,
    parse_repo_name,
)


def unretire_course(dirname: str) -> None:
    """Make the repo public again and move the directory to cwd."""
    _check_not_inside_course(dirname)

    remote_url = get_remote_url(dirname)
    repo_name = parse_repo_name(remote_url)

    g = get_github()
    repo = g.get_repo(repo_name)
    repo.edit(private=False)

    dest = Path.cwd() / Path(dirname).name
    if dest.exists():
        raise RuntimeError(f"Destination already exists: {dest}")

    shutil.move(dirname, str(dest))

    print(f"Successfully unretired {dirname} → {dest}")


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
    parser.add_argument("dirname", help="Path to the course directory to unretire")
    args = parser.parse_args()

    try:
        unretire_course(args.dirname)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
