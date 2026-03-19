#!/usr/bin/env python3

import argparse
import datetime
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import cast

from github import Github
from github.AuthenticatedUser import AuthenticatedUser

from setup_course_github.config import load_config

EXTRAS_GROUPS: dict[str, list[str]] = {
    "python": ["ipython"],
    "data": ["numpy", "pandas", "xlrd", "openpyxl", "plotly"],
    "viz": ["matplotlib", "seaborn"],
    "geo": ["geopandas", "folium", "shapely"],
    "db": ["duckdb", "sqlalchemy"],
    "ml": ["scikit-learn"],
}

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


def _build_pyproject_toml(
    repo_name: str,
    notebook_type: str,
    extras: list[str] | None = None,
) -> str:
    """Generate a pyproject.toml string for the new course directory."""
    notebook_dep = "jupyter" if notebook_type == "jupyter" else "marimo"
    deps = [notebook_dep, "gitautopush"]
    if extras:
        deps.extend(extras)
    deps_str = "\n".join(f'    "{d}",' for d in deps)
    return f"""\
[project]
name = "{repo_name}"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
{deps_str}
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


def _notebook_dates(start: datetime.date, count: int, freq: str) -> list[datetime.date]:
    """Return a list of dates for notebook files."""
    step = datetime.timedelta(days=1 if freq == "daily" else 7)
    return [start + step * i for i in range(count)]


def main() -> None:
    config = load_config()
    extras_groups = {**EXTRAS_GROUPS, **config.custom_extras}

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--client", required=True)
    parser.add_argument("-t", "--topic", required=True)
    parser.add_argument("-d", "--date", default=None, help="YYYY-MM override")
    parser.add_argument(
        "-n", "--num-sessions", type=int, default=None, help="number of sessions"
    )
    parser.add_argument(
        "--freq",
        choices=["daily", "weekly"],
        default=None,
        help="session frequency (requires -n)",
    )
    parser.add_argument(
        "--notebook-type",
        choices=["jupyter", "marimo"],
        default=None,
    )
    parser.add_argument(
        "--extras",
        nargs="*",
        default=None,
        help="dependency groups to include (e.g. python data viz geo db ml)",
    )

    args = parser.parse_args()

    # Validate -n / --freq interaction
    if args.freq is not None and args.num_sessions is None:
        parser.error("--freq requires -n/--num-sessions")

    # Validate --extras group names
    if args.extras is not None:
        unknown = [g for g in args.extras if g not in extras_groups]
        if unknown:
            parser.error(f"unknown extras group(s): {', '.join(unknown)}")

    # Resolve extras groups into a flat sorted+deduped list
    extra_packages: list[str] | None = None
    if args.extras:
        seen: set[str] = set()
        flat: list[str] = []
        for group in args.extras:
            for pkg in extras_groups[group]:
                if pkg not in seen:
                    seen.add(pkg)
                    flat.append(pkg)
        extra_packages = sorted(flat)

    notebook_type: str = (
        args.notebook_type
        if args.notebook_type is not None
        else config.default_notebook_type
    )

    today = _today()
    date_prefix = args.date if args.date else today.strftime("%Y-%m")
    repo_name = f"{args.client}-{args.topic}-{date_prefix}"
    destination = repo_name

    # Determine notebook dates
    num_sessions = args.num_sessions if args.num_sessions is not None else 1
    freq = args.freq if args.freq is not None else "daily"
    dates = _notebook_dates(today, num_sessions, freq)

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

    # Handle notebook files
    ipynb_path = Path(f"{destination}/Course notebook.ipynb")
    ipynb_path.unlink()

    for d in dates:
        notebook_base = f"{args.client}-{args.topic}-{d.strftime('%Y-%m-%d')}"
        if notebook_type == "jupyter":
            Path(f"{destination}/{notebook_base}.ipynb").write_text(
                '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}\n'
            )
        else:
            Path(f"{destination}/{notebook_base}.py").write_text(MARIMO_TEMPLATE)

    # Write pyproject.toml
    pyproject_content = _build_pyproject_toml(repo_name, notebook_type, extra_packages)
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

    # Initial commit and push
    subprocess.run(["git", "add", "."], cwd=destination, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=destination,
        check=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=destination,
        check=True,
    )

    # Install dependencies
    subprocess.run(["uv", "sync"], cwd=destination, check=True)


if __name__ == "__main__":  # pragma: no cover
    main()
