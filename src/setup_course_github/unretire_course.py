#!/usr/bin/env python3

import argparse
import shutil
from pathlib import Path

from setup_course_github import __version__, get_github
from setup_course_github.retire_course import get_remote_url, parse_repo_name


def unretire_course(dirname: str) -> None:
    """Make the repo public again and move the directory to cwd."""
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
    parser = argparse.ArgumentParser(
        epilog=f"Version {__version__} — https://pypi.org/project/course-setup/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("dirname", help="Path to the course directory to unretire")
    args = parser.parse_args()

    unretire_course(args.dirname)


if __name__ == "__main__":  # pragma: no cover
    main()
