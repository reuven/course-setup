#!/usr/bin/env python3

import argparse
import datetime
import shutil
import subprocess

from setup_course_github import get_github
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
    shutil.move(dirname, dest)

    print(f"Successfully retired {dirname} → {dest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dirname", required=True)
    args = parser.parse_args()

    retire_course(args.dirname)


if __name__ == "__main__":  # pragma: no cover
    main()
