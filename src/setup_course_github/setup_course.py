#!/usr/bin/env python3

import argparse
import datetime
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import cast

from github import Github
from github.AuthenticatedUser import AuthenticatedUser

from setup_course_github.config import load_config

MARIMO_TEMPLATE = """\
import marimo

__generated_with = "0.13.0"
app = marimo.App()


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
"""


def _today() -> datetime.date:
    """Return today's date. Thin wrapper for testability."""
    return datetime.date.today()


def _get_template_dir() -> Path:
    """Return the path to the bundled generic template directory."""
    return Path(__file__).parent / "generic"


def _build_pyproject_toml(repo_name: str, notebook_type: str) -> str:
    """Generate a pyproject.toml string for the new course directory."""
    notebook_dep = "jupyter" if notebook_type == "jupyter" else "marimo"
    return f"""\
[project]
name = "{repo_name}"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "{notebook_dep}",
    "gitautopush",
]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
"""


def _build_git_config(username: str, repo: str) -> str:
    """Generate a git config string with the correct remote URL."""
    return f"""\
[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = false
\tlogallrefupdates = true
\tignorecase = true
\tprecomposeunicode = true
[remote "origin"]
\turl = git@github.com:{username}/{repo}.git
\tfetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
\tremote = origin
\tmerge = refs/heads/main
"""


def main() -> None:
    config = load_config()

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--client", required=True)
    parser.add_argument("-t", "--topic", required=True)
    parser.add_argument("-d", "--date", default=None, help="YYYY-MM override")
    parser.add_argument(
        "--notebook-type",
        choices=["jupyter", "marimo"],
        default=None,
    )

    args = parser.parse_args()

    notebook_type: str = (
        args.notebook_type
        if args.notebook_type is not None
        else config.default_notebook_type
    )

    today = _today()
    date_prefix = args.date if args.date else today.strftime("%Y-%m")
    repo_name = f"{args.client}-{args.topic}-{date_prefix}"
    destination = repo_name
    notebook_base = f"{repo_name}-{today.strftime('%d')}"

    template_dir = _get_template_dir()

    print(f'Copying from "{template_dir}" to "{destination}"')

    shutil.copytree(str(template_dir), destination)

    subprocess.run(["git", "init"], cwd=destination, check=True)

    # Replace README if a custom source is configured
    if config.readme_source is not None:
        readme_path = Path(f"{destination}/README.md")
        source = config.readme_source
        if source.startswith(("http://", "https://")):
            with urllib.request.urlopen(source) as response:
                readme_path.write_text(response.read().decode("utf-8"))
        else:
            shutil.copy2(source, str(readme_path))

    # Handle notebook file
    ipynb_path = Path(f"{destination}/Course notebook.ipynb")
    if notebook_type == "jupyter":
        os.rename(str(ipynb_path), f"{destination}/{notebook_base}.ipynb")
    else:
        ipynb_path.unlink()
        py_path = Path(f"{destination}/{notebook_base}.py")
        py_path.write_text(MARIMO_TEMPLATE)

    # Write pyproject.toml
    pyproject_content = _build_pyproject_toml(repo_name, notebook_type)
    Path(f"{destination}/pyproject.toml").write_text(pyproject_content)

    # Authenticate with GitHub API
    github = Github(config.github_token)
    user = cast(AuthenticatedUser, github.get_user())

    # Write git remote config using API username
    git_config_content = _build_git_config(user.login, repo_name)
    with open(f"{destination}/.git/config", "w") as outfile:
        outfile.write(git_config_content)

    # Create the repo on GitHub
    user.create_repo(name=repo_name, private=False)


if __name__ == "__main__":  # pragma: no cover
    main()
