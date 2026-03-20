#!/usr/bin/env python3

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import cast

from github import Github
from github.AuthenticatedUser import AuthenticatedUser

from setup_course_github.config import load_config

EXTRAS_GROUPS: dict[str, list[str]] = {
    "python": ["ipython"],
    "data": ["numpy", "pandas", "xlrd", "openpyxl", "pyarrow"],
    "viz": ["matplotlib", "seaborn", "plotly"],
    "geo": ["geopandas", "folium", "shapely"],
    "db": ["duckdb", "sqlalchemy"],
    "ml": ["scikit-learn"],
}

IMPORT_MAP: dict[str, list[str]] = {
    "python": [],
    "data": [
        "import numpy as np",
        "import pandas as pd",
    ],
    "viz": [
        "import matplotlib.pyplot as plt",
        "import seaborn as sns",
        "import plotly.express as px",
    ],
    "geo": [
        "import geopandas as gpd",
        "import folium",
    ],
    "db": [
        "import duckdb",
        "import sqlalchemy",
    ],
    "ml": [
        "from sklearn import datasets, model_selection, metrics",
    ],
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


def _resolve_group(
    group_name: str,
    all_groups: dict[str, list[str]],
    _expanding: set[str] | None = None,
) -> tuple[list[str], set[str]]:
    """Resolve a group into (flat_packages, referenced_group_names).

    Each entry in a group's list is checked: if it's a key in *all_groups*,
    it is recursively expanded.  Otherwise it is treated as a literal package
    name.  Raises ``ValueError`` on circular references.
    """
    if _expanding is None:
        _expanding = set()

    if group_name in _expanding:
        raise ValueError(
            f"Circular extras-group reference: "
            f"{' -> '.join(_expanding)} -> {group_name}"
        )

    _expanding = _expanding | {group_name}
    expanded_groups: set[str] = {group_name}

    seen: set[str] = set()
    flat: list[str] = []

    for entry in all_groups.get(group_name, []):
        if entry in all_groups:
            # It's a group reference – recurse
            sub_pkgs, sub_groups = _resolve_group(entry, all_groups, _expanding)
            expanded_groups |= sub_groups
            for pkg in sub_pkgs:
                if pkg not in seen:
                    seen.add(pkg)
                    flat.append(pkg)
        else:
            # Literal package name
            if entry not in seen:
                seen.add(entry)
                flat.append(entry)

    return flat, expanded_groups


def _build_import_lines(groups: list[str]) -> str:
    """Collect import statements for the given extras groups, deduplicated."""
    seen: set[str] = set()
    lines: list[str] = []
    for group in groups:
        for line in IMPORT_MAP.get(group, []):
            if line not in seen:
                seen.add(line)
                lines.append(line)
    return "\n".join(lines)


def _print_status(msg: str) -> None:
    """Print a progress status message."""
    print(msg)


def _print_verbose(msg: str, verbose: bool) -> None:
    """Print a message only when verbose mode is enabled."""
    if verbose:
        print(msg)


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
    parser.add_argument(
        "--add-imports",
        action="store_true",
        default=False,
        help="pre-populate notebooks with import statements from --extras groups",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=None,
        help="show detailed output for each step",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="show what would be done without making any changes",
    )

    args = parser.parse_args()

    # Resolve verbose: CLI flag overrides config default
    verbose: bool = args.verbose if args.verbose is not None else config.default_verbose

    # Validate -n / --freq interaction
    if args.freq is not None and args.num_sessions is None:
        parser.error("--freq requires -n/--num-sessions")

    # Resolve --extras: CLI flag overrides config default_extras_group
    effective_extras: list[str] | None = args.extras
    if effective_extras is None and config.default_extras_group is not None:
        effective_extras = [config.default_extras_group]

    # Validate extras group names
    if effective_extras is not None:
        unknown = [g for g in effective_extras if g not in extras_groups]
        if unknown:
            parser.error(f"unknown extras group(s): {', '.join(unknown)}")

    # Resolve extras groups into a flat sorted+deduped list
    extra_packages: list[str] | None = None
    all_expanded_groups: set[str] = set()
    if effective_extras:
        seen: set[str] = set()
        flat: list[str] = []
        for group in effective_extras:
            pkgs, expanded = _resolve_group(group, extras_groups)
            all_expanded_groups |= expanded
            for pkg in pkgs:
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

    # Dry-run: print summary and exit without side effects
    if args.dry_run:
        ext = ".ipynb" if notebook_type == "jupyter" else ".py"
        notebook_filenames = [
            f"{args.client}-{args.topic}-{d.strftime('%Y-%m-%d')}{ext}" for d in dates
        ]
        _print_status("[dry-run] Would create the following:")
        _print_status(f"  Repository: {repo_name}")
        _print_status(f"  Directory: {destination}")
        _print_status(f"  Notebook type: {notebook_type}")
        _print_status(f"  Notebooks: {', '.join(notebook_filenames)}")
        deps = ["jupyter" if notebook_type == "jupyter" else "marimo", "gitautopush"]
        if extra_packages:
            deps.extend(extra_packages)
        _print_status(f"  Dependencies: {', '.join(deps)}")
        _print_status(f"  GitHub repo: <your-github-username>/{repo_name}")
        return

    cleanup_actions: list[tuple[str, Callable[[], None]]] = []

    try:
        _print_status("Creating course directory...")
        _print_verbose(f"  Template: {template_dir}", verbose)
        _print_verbose(f"  Destination: {destination}", verbose)
        shutil.copytree(str(template_dir), destination)
        cleanup_actions.append(("local directory", lambda: shutil.rmtree(destination)))

        _print_status("Initializing git repository...")
        subprocess.run(["git", "init"], cwd=destination, check=True)

        # Replace README if a custom source is configured
        if config.readme_source:
            _print_status("Setting up README...")
            readme_path = Path(f"{destination}/README.md")
            source = config.readme_source
            _print_verbose(f"  README source: {source}", verbose)
            if source.startswith(("http://", "https://")):
                with urllib.request.urlopen(source) as response:
                    readme_path.write_text(response.read().decode("utf-8"))
            else:
                shutil.copy2(source, str(readme_path))

        # Handle notebook files
        _print_status("Creating notebook files...")
        ipynb_path = Path(f"{destination}/Course notebook.ipynb")
        ipynb_path.unlink()

        import_code = ""
        if args.add_imports and effective_extras:
            import_code = _build_import_lines(sorted(all_expanded_groups))

        for d in dates:
            notebook_base = f"{args.client}-{args.topic}-{d.strftime('%Y-%m-%d')}"
            ext = ".ipynb" if notebook_type == "jupyter" else ".py"
            _print_verbose(f"  {notebook_base}{ext}", verbose)
            if notebook_type == "jupyter":
                if import_code:
                    cell: dict[str, object] = {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": [import_code],
                    }
                    nb = {
                        "cells": [cell],
                        "metadata": {},
                        "nbformat": 4,
                        "nbformat_minor": 5,
                    }
                    notebook_content = json.dumps(nb, indent=1) + "\n"
                else:
                    nb = {
                        "cells": [],
                        "metadata": {},
                        "nbformat": 4,
                        "nbformat_minor": 5,
                    }
                    notebook_content = json.dumps(nb, indent=1) + "\n"
                Path(f"{destination}/{notebook_base}.ipynb").write_text(
                    notebook_content
                )
            else:
                if import_code:
                    marimo_content = f"""\
import marimo

__generated_with = "0.13.0"
app = marimo.App()


@app.cell
def _():
{chr(10).join("    " + line for line in import_code.split(chr(10)))}
    return


if __name__ == "__main__":
    app.run()
"""
                else:
                    marimo_content = MARIMO_TEMPLATE
                Path(f"{destination}/{notebook_base}.py").write_text(marimo_content)

        # Write pyproject.toml
        _print_status("Writing project configuration...")
        pyproject_content = _build_pyproject_toml(
            repo_name, notebook_type, extra_packages
        )
        if extra_packages:
            _print_verbose(f"  Dependencies: {', '.join(extra_packages)}", verbose)
        Path(f"{destination}/pyproject.toml").write_text(pyproject_content)

        # Authenticate with GitHub API
        _print_status("Creating GitHub repository...")
        github = Github(config.github_token)
        user = cast(AuthenticatedUser, github.get_user())

        # Write git remote config using API username
        _print_verbose(f"  GitHub user: {user.login}", verbose)
        _print_verbose(f"  Repo: {repo_name}", verbose)
        git_config_content = _build_git_config(user.login, repo_name)
        with open(f"{destination}/.git/config", "w") as outfile:
            outfile.write(git_config_content)

        # Create the repo on GitHub
        created_repo = user.create_repo(name=repo_name, private=False)
        cleanup_actions.append(("GitHub repository", lambda: created_repo.delete()))

        # Initial commit and push
        _print_status("Pushing to GitHub...")
        remote_url = f"git@github.com:{user.login}/{repo_name}.git"
        _print_verbose(f"  Remote: {remote_url}", verbose)
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
        _print_status("Installing dependencies...")
        subprocess.run(["uv", "sync"], cwd=destination, check=True)

        _print_status(f"Done! Course ready at {destination}")

    except Exception as exc:
        _print_status(f"Error: {exc}")
        _print_status("Rolling back...")
        for name, action in reversed(cleanup_actions):
            try:
                _print_status(f"  Removing {name}...")
                action()
            except Exception as cleanup_exc:
                _print_status(f"  Warning: failed to remove {name}: {cleanup_exc}")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
