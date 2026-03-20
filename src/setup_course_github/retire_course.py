#!/usr/bin/env python3

import argparse
import datetime
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from setup_course_github import __version__, get_github
from setup_course_github.config import load_config


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


def _confirm_create_dir(
    dest: Path, confirm: Callable[[str], str] = input
) -> None:
    """Prompt the user to create an archive directory if it doesn't exist."""
    if not dest.exists():
        answer = confirm(
            f"Archive directory {dest} does not exist. Create it? [y/N] "
        )
        if answer.strip().lower().startswith("y"):
            dest.mkdir(parents=True, exist_ok=True)
        else:
            raise RuntimeError(f"Aborted: archive directory {dest} not created")


def retire_course(dirname: str) -> None:
    """Make the GitHub repo private and move the local directory to the archive."""
    config = load_config()

    remote_url = get_remote_url(dirname)
    repo_name = parse_repo_name(remote_url)

    g = get_github()
    repo = g.get_repo(repo_name)
    repo.edit(private=True)

    year = datetime.datetime.now().year
    dest = config.archive_path / str(year)
    _confirm_create_dir(dest)
    shutil.move(dirname, dest)

    print(f"Successfully retired {dirname} → {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(
        epilog=f"Version {__version__} — https://pypi.org/project/course-setup/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "dirnames", nargs="+", help="Path(s) to course directories to retire"
    )
    args = parser.parse_args()

    errors: list[tuple[str, str]] = []
    for dirname in args.dirnames:
        try:
            retire_course(dirname)
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
