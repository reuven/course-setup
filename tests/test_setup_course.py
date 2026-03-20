"""Tests for setup_course v2 CLI."""

import datetime
import os
import sys
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from setup_course_github.setup_course import (
    EXTRAS_GROUPS,
    IMPORT_MAP,
    _build_git_config,
    _build_import_lines,
    _build_pyproject_toml,
    _get_template_dir,
    _notebook_dates,
    _print_status,
    _print_verbose,
    _resolve_group,
    main,
)

FAKE_TODAY = datetime.date(2026, 3, 19)


def _fake_subprocess(*args: Any, **kwargs: Any) -> Any:
    """Simulate subprocess.run for git and uv commands."""
    cmd = args[0] if args else kwargs.get("args", [])
    cwd = kwargs.get("cwd")
    if cmd == ["git", "init"] and cwd is not None:
        (Path(cwd) / ".git").mkdir(exist_ok=True)
    # All other commands (git add, git commit, git push, uv sync) are no-ops
    return MagicMock(returncode=0)


def make_mock_config(
    default_notebook_type: str = "jupyter",
    readme_source: str | None = None,
    default_weekend: str | None = None,
) -> MagicMock:
    """Return a mock CourseConfig with sensible defaults."""
    config = MagicMock()
    config.github_token = "ghp_testtoken"
    config.default_notebook_type = default_notebook_type
    config.readme_source = readme_source
    config.default_verbose = False
    config.default_extras_group = None
    config.custom_extras = {}
    config.default_weekend = default_weekend
    return config


def make_mock_user(login: str = "testuser") -> MagicMock:
    """Return a mock AuthenticatedUser."""
    user = MagicMock()
    user.login = login
    user.create_repo = MagicMock(return_value=MagicMock())
    return user


def setup_template(tmp_path: Path) -> Path:
    """Create a minimal generic template directory in tmp_path."""
    template = tmp_path / "generic"
    template.mkdir(parents=True, exist_ok=True)
    (template / "Course notebook.ipynb").write_text('{"cells": []}\n')
    (template / "README.md").write_text("# Course\n")
    (template / ".gitignore").write_text("# Python\n__pycache__/\n")
    return template


@pytest.fixture
def course_env(tmp_path: Path) -> Generator[dict[str, Any], None, None]:
    """Set up standard mocks and chdir to tmp_path for a main() call."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user()

    with (
        patch(
            "setup_course_github.setup_course.load_config",
            return_value=mock_config,
        ),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir",
            return_value=template,
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_subprocess,
        ) as mock_run,
        patch(
            "setup_course_github.setup_course._today",
            return_value=FAKE_TODAY,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user
        orig_cwd = Path.cwd()
        os.chdir(tmp_path)
        try:
            yield {
                "tmp_path": tmp_path,
                "template": template,
                "config": mock_config,
                "user": mock_user,
                "github_cls": mock_github_cls,
                "mock_run": mock_run,
            }
        finally:
            os.chdir(orig_cwd)


# ---------------------------------------------------------------------------
# Argument parsing tests
# ---------------------------------------------------------------------------


def test_client_and_topic_are_required(course_env: dict[str, Any]) -> None:
    """Calling with missing -c or -t raises SystemExit."""
    sys.argv = ["setup-course", "-c", "acme"]
    with pytest.raises(SystemExit):
        main()

    sys.argv = ["setup-course", "-t", "python"]
    with pytest.raises(SystemExit):
        main()


def test_old_repo_flag_not_accepted(course_env: dict[str, Any]) -> None:
    """The removed -r flag is rejected."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-r", "foo"]
    with pytest.raises(SystemExit):
        main()


def test_freq_without_n_is_error(course_env: dict[str, Any]) -> None:
    """--freq without -n raises an error."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--freq",
        "daily",
    ]
    with pytest.raises(SystemExit):
        main()


# ---------------------------------------------------------------------------
# Auto-generated name tests
# ---------------------------------------------------------------------------


def test_repo_name_is_client_topic_yyyy_mm(course_env: dict[str, Any]) -> None:
    """GitHub repo is created with auto-generated name."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    course_env["user"].create_repo.assert_called_once_with(
        name="acme-python-2026-03", private=False
    )


def test_directory_name_matches_repo_name(course_env: dict[str, Any]) -> None:
    """Destination directory matches the auto-generated repo name."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert dest.exists()
    assert dest.is_dir()


def test_date_override_changes_repo_name(course_env: dict[str, Any]) -> None:
    """Passing -d overrides the YYYY-MM portion."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "2025-11"]
    main()
    course_env["user"].create_repo.assert_called_once_with(
        name="acme-python-2025-11", private=False
    )
    dest = course_env["tmp_path"] / "acme-python-2025-11"
    assert dest.exists()


# ---------------------------------------------------------------------------
# Single notebook (default) tests
# ---------------------------------------------------------------------------


def test_jupyter_notebook_filename(course_env: dict[str, Any]) -> None:
    """Jupyter notebook is named REPO-MM-DD.ipynb."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.ipynb").exists()
    assert not (dest / "Course notebook.ipynb").exists()


def test_marimo_notebook_filename(course_env: dict[str, Any]) -> None:
    """Marimo notebook is named REPO-MM-DD.py."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--notebook-type",
        "marimo",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.py").exists()
    assert not (dest / "Course notebook.ipynb").exists()
    assert not (dest / "acme-python-2026-03-19.ipynb").exists()


def test_date_override_notebook_still_uses_todays_day(
    course_env: dict[str, Any],
) -> None:
    """With -d override, notebook MM-DD still comes from today."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "2025-11"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2025-11"
    assert (dest / "acme-python-2026-03-19.ipynb").exists()


# ---------------------------------------------------------------------------
# Multi-session tests (-n / --freq)
# ---------------------------------------------------------------------------


def test_n_daily_creates_sequential_notebooks(course_env: dict[str, Any]) -> None:
    """'-n 5 --freq daily' creates 5 notebooks with consecutive dates."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "5",
        "--freq",
        "daily",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.ipynb").exists()
    assert (dest / "acme-python-2026-03-20.ipynb").exists()
    assert (dest / "acme-python-2026-03-21.ipynb").exists()
    assert (dest / "acme-python-2026-03-22.ipynb").exists()
    assert (dest / "acme-python-2026-03-23.ipynb").exists()


def test_n_weekly_creates_weekly_notebooks(course_env: dict[str, Any]) -> None:
    """'-n 3 --freq weekly' creates 3 notebooks spaced a week apart."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "3",
        "--freq",
        "weekly",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.ipynb").exists()
    assert (dest / "acme-python-2026-03-26.ipynb").exists()
    assert (dest / "acme-python-2026-04-02.ipynb").exists()


def test_n_without_freq_defaults_to_daily(course_env: dict[str, Any]) -> None:
    """'-n 3' without --freq defaults to daily."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-n", "3"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.ipynb").exists()
    assert (dest / "acme-python-2026-03-20.ipynb").exists()
    assert (dest / "acme-python-2026-03-21.ipynb").exists()


def test_n_1_creates_single_notebook(course_env: dict[str, Any]) -> None:
    """'-n 1' creates exactly one notebook, same as no -n."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-n", "1"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    notebooks = list(dest.glob("*.ipynb"))
    assert len(notebooks) == 1
    assert notebooks[0].name == "acme-python-2026-03-19.ipynb"


def test_n_daily_marimo_creates_py_files(course_env: dict[str, Any]) -> None:
    """Multi-session with marimo creates .py files."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "2",
        "--notebook-type",
        "marimo",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.py").exists()
    assert (dest / "acme-python-2026-03-20.py").exists()
    assert not list(dest.glob("*.ipynb"))


def test_weekly_across_month_boundary(course_env: dict[str, Any]) -> None:
    """Weekly sessions that cross a month boundary have correct dates."""
    # FAKE_TODAY is March 19. 3 weeks: Mar 19, Mar 26, Apr 2
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "3",
        "--freq",
        "weekly",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.ipynb").exists()
    assert (dest / "acme-python-2026-03-26.ipynb").exists()
    assert (dest / "acme-python-2026-04-02.ipynb").exists()


def test_template_notebook_removed_with_multi_session(
    course_env: dict[str, Any],
) -> None:
    """The template 'Course notebook.ipynb' is always removed."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-n", "3"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert not (dest / "Course notebook.ipynb").exists()


# ---------------------------------------------------------------------------
# _notebook_dates helper tests
# ---------------------------------------------------------------------------


def test_notebook_dates_daily() -> None:
    """_notebook_dates returns consecutive dates for daily freq."""
    start = datetime.date(2026, 3, 17)
    result = _notebook_dates(start, 5, "daily")
    assert result == [
        datetime.date(2026, 3, 17),
        datetime.date(2026, 3, 18),
        datetime.date(2026, 3, 19),
        datetime.date(2026, 3, 20),
        datetime.date(2026, 3, 21),
    ]


def test_notebook_dates_weekly() -> None:
    """_notebook_dates returns weekly-spaced dates."""
    start = datetime.date(2026, 3, 3)
    result = _notebook_dates(start, 5, "weekly")
    assert result == [
        datetime.date(2026, 3, 3),
        datetime.date(2026, 3, 10),
        datetime.date(2026, 3, 17),
        datetime.date(2026, 3, 24),
        datetime.date(2026, 3, 31),
    ]


def test_notebook_dates_single() -> None:
    """_notebook_dates with count=1 returns a single date."""
    start = datetime.date(2026, 3, 19)
    result = _notebook_dates(start, 1, "daily")
    assert result == [datetime.date(2026, 3, 19)]


# ---------------------------------------------------------------------------
# Template copy and git init
# ---------------------------------------------------------------------------


def test_template_copied_and_git_init_called(course_env: dict[str, Any]) -> None:
    """git init is called in the destination directory."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    calls = course_env["mock_run"].call_args_list
    git_init_calls = [c for c in calls if c[0][0] == ["git", "init"]]
    assert len(git_init_calls) == 1
    assert git_init_calls[0][1]["cwd"] == "acme-python-2026-03"


# ---------------------------------------------------------------------------
# pyproject.toml tests
# ---------------------------------------------------------------------------


def test_pyproject_toml_uses_auto_repo_name(course_env: dict[str, Any]) -> None:
    """pyproject.toml uses the auto-generated repo name."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert 'name = "acme-python-2026-03"' in content


def test_pyproject_toml_jupyter_dependency(course_env: dict[str, Any]) -> None:
    """pyproject.toml has jupyter dependency for jupyter type."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert "jupyter" in content
    assert "gitautopush" in content
    assert "marimo" not in content


def test_pyproject_toml_marimo_dependency(course_env: dict[str, Any]) -> None:
    """pyproject.toml has marimo dependency for marimo type."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--notebook-type",
        "marimo",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert "marimo" in content
    assert "gitautopush" in content
    assert "jupyter" not in content


def test_pyproject_toml_always_has_gitautopush(course_env: dict[str, Any]) -> None:
    """gitautopush is always in pyproject.toml dependencies."""
    for notebook_type in ("jupyter", "marimo"):
        sys.argv = [
            "setup-course",
            "-c",
            "acme",
            "-t",
            notebook_type,
            "--notebook-type",
            notebook_type,
        ]
        main()
        dest = course_env["tmp_path"] / f"acme-{notebook_type}-2026-03"
        content = (dest / "pyproject.toml").read_text()
        assert "gitautopush" in content, f"gitautopush missing for {notebook_type}"


# ---------------------------------------------------------------------------
# Git config tests
# ---------------------------------------------------------------------------


def test_git_config_uses_api_username(course_env: dict[str, Any]) -> None:
    """Git remote URL uses username from GitHub API."""
    course_env["user"].login = "api_user_123"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    git_config = (dest / ".git" / "config").read_text()
    assert "api_user_123" in git_config
    assert "acme-python-2026-03.git" in git_config


def test_git_config_not_hardcoded_reuven(course_env: dict[str, Any]) -> None:
    """The hardcoded 'reuven' username is never used."""
    course_env["user"].login = "different_user"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    git_config = (dest / ".git" / "config").read_text()
    assert "different_user" in git_config
    assert "reuven" not in git_config


# ---------------------------------------------------------------------------
# GitHub API interaction tests
# ---------------------------------------------------------------------------


def test_github_repo_created_as_public(course_env: dict[str, Any]) -> None:
    """GitHub repo is created via API as a public repo."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    course_env["user"].create_repo.assert_called_once_with(
        name="acme-python-2026-03", private=False
    )


def test_github_authenticated_with_token(course_env: dict[str, Any]) -> None:
    """Github is instantiated with the token from the config."""
    course_env["config"].github_token = "ghp_supersecrettoken"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    course_env["github_cls"].assert_called_once_with("ghp_supersecrettoken")


# ---------------------------------------------------------------------------
# --notebook-type flag tests
# ---------------------------------------------------------------------------


def test_notebook_type_flag_overrides_config(course_env: dict[str, Any]) -> None:
    """--notebook-type flag overrides the config default."""
    course_env["config"].default_notebook_type = "jupyter"
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--notebook-type",
        "marimo",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.py").exists()
    assert not (dest / "acme-python-2026-03-19.ipynb").exists()


def test_default_notebook_type_from_config_marimo(
    course_env: dict[str, Any],
) -> None:
    """When --notebook-type is not given, config default marimo is used."""
    course_env["config"].default_notebook_type = "marimo"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.py").exists()
    assert not (dest / "acme-python-2026-03-19.ipynb").exists()


def test_default_notebook_type_from_config_jupyter(
    course_env: dict[str, Any],
) -> None:
    """When --notebook-type is not given, config default jupyter is used."""
    course_env["config"].default_notebook_type = "jupyter"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.ipynb").exists()
    assert not (dest / "acme-python-2026-03-19.py").exists()


# ---------------------------------------------------------------------------
# Marimo notebook content
# ---------------------------------------------------------------------------


def test_marimo_notebook_content(course_env: dict[str, Any]) -> None:
    """The marimo notebook has the correct minimal content."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--notebook-type",
        "marimo",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "acme-python-2026-03-19.py").read_text()
    assert "import marimo" in content
    assert "__generated_with" in content
    assert "app = marimo.App()" in content
    assert "@app.cell" in content
    assert "app.run()" in content


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_get_template_dir_returns_generic_path() -> None:
    """_get_template_dir returns a path ending in 'generic' within the package."""
    result = _get_template_dir()
    assert result.name == "generic"
    assert result.parent.name == "setup_course_github"


def test_today_returns_a_date() -> None:
    """_today returns today's date."""
    from setup_course_github.setup_course import _today

    result = _today()
    assert isinstance(result, datetime.date)
    assert result == datetime.date.today()


# ---------------------------------------------------------------------------
# README source tests
# ---------------------------------------------------------------------------


def test_bundled_readme_used_when_no_readme_source(
    course_env: dict[str, Any],
) -> None:
    """When readme_source is None, the bundled template README is used."""
    course_env["config"].readme_source = None
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    readme = dest / "README.md"
    assert readme.exists()
    assert readme.read_text() == "# Course\n"


def test_bundled_readme_used_when_readme_source_is_empty_string(
    course_env: dict[str, Any],
) -> None:
    """When readme_source is '', behave as if None — use bundled template."""
    course_env["config"].readme_source = ""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    readme = dest / "README.md"
    assert readme.exists()
    assert readme.read_text() == "# Course\n"


def test_readme_from_local_file(course_env: dict[str, Any]) -> None:
    """When readme_source is a local file path, that file is used as README."""
    custom_readme = course_env["tmp_path"] / "my-custom-readme.md"
    custom_readme.write_text("# My Custom README\nHello world!\n")
    course_env["config"].readme_source = str(custom_readme)

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    readme = dest / "README.md"
    assert readme.exists()
    assert readme.read_text() == "# My Custom README\nHello world!\n"


def test_readme_from_url(course_env: dict[str, Any]) -> None:
    """When readme_source is a URL, the content is fetched and used as README."""
    url = "https://example.com/my-readme.md"
    fetched_content = "# README from URL\nFetched content.\n"
    course_env["config"].readme_source = url

    with patch(
        "setup_course_github.setup_course.urllib.request.urlopen"
    ) as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = fetched_content.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
        main()

    dest = course_env["tmp_path"] / "acme-python-2026-03"
    readme = dest / "README.md"
    assert readme.exists()
    assert readme.read_text() == fetched_content


# ---------------------------------------------------------------------------
# --extras flag tests
# ---------------------------------------------------------------------------


def test_extras_python_data_adds_correct_deps(course_env: dict[str, Any]) -> None:
    """--extras python data adds ipython, numpy, pandas, xlrd, openpyxl, pyarrow."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "python",
        "data",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    for pkg in ["ipython", "numpy", "pandas", "xlrd", "openpyxl", "pyarrow"]:
        assert f'"{pkg}"' in content, f"{pkg} missing from pyproject.toml"
    assert '"plotly"' not in content


def test_extras_empty_adds_no_extra_deps(course_env: dict[str, Any]) -> None:
    """--extras with no groups adds no extra deps."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    # Should only have jupyter and gitautopush
    assert '"jupyter"' in content
    assert '"gitautopush"' in content
    # None of the extras should be present
    assert '"ipython"' not in content
    assert '"numpy"' not in content


def test_extras_unknown_group_causes_exit(course_env: dict[str, Any]) -> None:
    """Unknown group name causes SystemExit via parser.error."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "nonexistent",
    ]
    with pytest.raises(SystemExit):
        main()


def test_extras_multiple_groups_merge_and_deduplicate(
    course_env: dict[str, Any],
) -> None:
    """Multiple groups merge and deduplicate correctly."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "viz",
        "ml",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    for pkg in ["matplotlib", "seaborn", "scikit-learn"]:
        assert f'"{pkg}"' in content, f"{pkg} missing from pyproject.toml"


def test_extras_base_deps_always_present(course_env: dict[str, Any]) -> None:
    """Base deps (jupyter + gitautopush) are always present regardless of extras."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "db",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"jupyter"' in content
    assert '"gitautopush"' in content
    assert '"duckdb"' in content
    assert '"sqlalchemy"' in content


def test_extras_deps_sorted_alphabetically(course_env: dict[str, Any]) -> None:
    """Extra deps are sorted alphabetically in the generated pyproject.toml."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "data",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    # Extract dependency lines
    import re

    deps = re.findall(r'"(\w[\w-]*)"', content)
    # Filter to just the extras (exclude repo name, jupyter, gitautopush, build deps)
    extra_deps = [d for d in deps if d in {"numpy", "pandas", "xlrd", "openpyxl"}]
    assert extra_deps == sorted(extra_deps), f"Extras not sorted: {extra_deps}"


def test_build_pyproject_toml_with_extras() -> None:
    """_build_pyproject_toml includes extras in dependencies when provided."""
    result = _build_pyproject_toml("test-repo", "jupyter", extras=["numpy", "pandas"])
    assert '"numpy"' in result
    assert '"pandas"' in result
    assert '"jupyter"' in result
    assert '"gitautopush"' in result


def test_build_pyproject_toml_without_extras() -> None:
    """_build_pyproject_toml works without extras (backward compatible)."""
    result = _build_pyproject_toml("test-repo", "jupyter")
    assert '"jupyter"' in result
    assert '"gitautopush"' in result
    assert '"numpy"' not in result


def test_extras_groups_dict_exists() -> None:
    """EXTRAS_GROUPS is a dict with expected keys."""
    assert isinstance(EXTRAS_GROUPS, dict)
    expected_keys = {"python", "data", "viz", "geo", "db", "ml"}
    assert set(EXTRAS_GROUPS.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Hardening tests
# ---------------------------------------------------------------------------


def test_pyproject_toml_is_valid_toml(course_env: dict[str, Any]) -> None:
    """The generated pyproject.toml must be parseable as valid TOML."""
    import tomllib

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    with open(dest / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert data["project"]["name"] == "acme-python-2026-03"
    assert "dependencies" in data["project"]


def test_pyproject_toml_with_extras_is_valid_toml(course_env: dict[str, Any]) -> None:
    """pyproject.toml with --extras must still be valid TOML."""
    import tomllib

    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "python",
        "data",
        "viz",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    with open(dest / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    assert "jupyter" in deps
    assert "gitautopush" in deps
    assert "ipython" in deps
    assert "numpy" in deps
    assert "plotly" in deps
    assert "matplotlib" in deps


def test_jupyter_notebook_content_is_valid_json(course_env: dict[str, Any]) -> None:
    """Jupyter notebook must be valid JSON with expected ipynb keys."""
    import json

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = json.loads((dest / "acme-python-2026-03-19.ipynb").read_text())
    assert "cells" in content
    assert "metadata" in content
    assert "nbformat" in content


def test_build_pyproject_toml_empty_extras_list() -> None:
    """extras=[] (empty list) should behave like extras=None — no extras added."""
    result = _build_pyproject_toml("test-repo", "jupyter", extras=[])
    assert '"jupyter"' in result
    assert '"gitautopush"' in result
    assert '"numpy"' not in result
    assert '"ipython"' not in result


def test_build_pyproject_toml_output_is_valid_toml() -> None:
    """_build_pyproject_toml output must be parseable as TOML."""
    import tomllib

    result = _build_pyproject_toml("my-repo", "jupyter", extras=["numpy", "pandas"])
    data = tomllib.loads(result)
    assert data["project"]["name"] == "my-repo"
    deps = data["project"]["dependencies"]
    assert "jupyter" in deps
    assert "numpy" in deps
    assert "pandas" in deps


def test_extras_duplicate_group_deduplicates(course_env: dict[str, Any]) -> None:
    """Passing the same group twice should not duplicate packages."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "data",
        "data",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    # "numpy" should appear exactly once
    assert content.count('"numpy"') == 1
    assert content.count('"pandas"') == 1


def test_extras_all_groups(course_env: dict[str, Any]) -> None:
    """All six groups combined should include every package without error."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "python",
        "data",
        "viz",
        "geo",
        "db",
        "ml",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    all_pkgs: set[str] = set()
    for pkgs in EXTRAS_GROUPS.values():
        all_pkgs.update(pkgs)
    for pkg in all_pkgs:
        assert f'"{pkg}"' in content, f"{pkg} missing when all groups specified"


def test_invalid_notebook_type_rejected(course_env: dict[str, Any]) -> None:
    """--notebook-type with an invalid value should be rejected by argparse."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--notebook-type",
        "latex",
    ]
    with pytest.raises(SystemExit):
        main()


def test_notebook_dates_zero_count() -> None:
    """_notebook_dates with count=0 returns an empty list."""
    result = _notebook_dates(datetime.date(2026, 3, 19), 0, "daily")
    assert result == []


def test_client_topic_with_spaces_in_name(course_env: dict[str, Any]) -> None:
    """Client and topic values flow directly into directory/repo names."""
    sys.argv = ["setup-course", "-c", "Acme-Corp", "-t", "Python-Intro"]
    main()
    dest = course_env["tmp_path"] / "Acme-Corp-Python-Intro-2026-03"
    assert dest.exists()
    course_env["user"].create_repo.assert_called_once_with(
        name="Acme-Corp-Python-Intro-2026-03", private=False
    )


def test_build_git_config_contains_remote_url() -> None:
    """_build_git_config produces config with correct remote URL."""
    result = _build_git_config("myuser", "myrepo")
    assert "git@github.com:myuser/myrepo.git" in result
    assert '[remote "origin"]' in result
    assert '[branch "main"]' in result
    assert "repositoryformatversion" in result


def test_build_git_config_not_hardcoded() -> None:
    """_build_git_config uses the provided username, not a hardcoded one."""
    result = _build_git_config("alice", "her-course")
    assert "alice" in result
    assert "her-course" in result
    assert "reuven" not in result


def test_no_extras_flag_produces_only_base_deps(course_env: dict[str, Any]) -> None:
    """When --extras is not passed at all, only base deps appear."""
    import tomllib

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    with open(dest / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    assert deps == ["jupyter", "gitautopush"]


# ---------------------------------------------------------------------------
# Initial git commit/push and uv sync tests
# ---------------------------------------------------------------------------


def test_git_add_called_after_setup(course_env: dict[str, Any]) -> None:
    """git add . is called in the course directory."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    calls = course_env["mock_run"].call_args_list
    git_add_calls = [c for c in calls if c[0][0] == ["git", "add", "."]]
    assert len(git_add_calls) == 1
    assert git_add_calls[0][1]["cwd"] == "acme-python-2026-03"


def test_git_commit_called_after_setup(course_env: dict[str, Any]) -> None:
    """git commit is called in the course directory."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    calls = course_env["mock_run"].call_args_list
    git_commit_calls = [c for c in calls if c[0][0][:2] == ["git", "commit"]]
    assert len(git_commit_calls) == 1
    assert git_commit_calls[0][1]["cwd"] == "acme-python-2026-03"


def test_git_push_called_after_setup(course_env: dict[str, Any]) -> None:
    """git push is called in the course directory."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    calls = course_env["mock_run"].call_args_list
    git_push_calls = [c for c in calls if c[0][0][:2] == ["git", "push"]]
    assert len(git_push_calls) == 1
    assert git_push_calls[0][1]["cwd"] == "acme-python-2026-03"


def test_uv_sync_called_after_setup(course_env: dict[str, Any]) -> None:
    """uv sync is called in the course directory."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    calls = course_env["mock_run"].call_args_list
    uv_sync_calls = [c for c in calls if c[0][0] == ["uv", "sync"]]
    assert len(uv_sync_calls) == 1
    assert uv_sync_calls[0][1]["cwd"] == "acme-python-2026-03"


def test_subprocess_call_order(course_env: dict[str, Any]) -> None:
    """Subprocess calls happen in correct order."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    calls = course_env["mock_run"].call_args_list
    cmds = [c[0][0] for c in calls]
    assert cmds[0] == ["git", "init"]
    assert cmds[1] == ["git", "add", "."]
    assert cmds[2][:2] == ["git", "commit"]
    assert cmds[3][:2] == ["git", "push"]
    assert cmds[4] == ["uv", "sync"]


# ---------------------------------------------------------------------------
# Custom extras tests
# ---------------------------------------------------------------------------


def test_custom_extras_group_accepted(course_env: dict[str, Any]) -> None:
    """A custom extras group defined in config is accepted by --extras."""
    course_env["config"].custom_extras = {"finance": ["yfinance", "pandas-datareader"]}
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--extras", "finance"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"yfinance"' in content
    assert '"pandas-datareader"' in content


def test_custom_extras_override_builtin(course_env: dict[str, Any]) -> None:
    """Custom group with same name as built-in overrides it."""
    course_env["config"].custom_extras = {"data": ["polars"]}
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--extras", "data"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"polars"' in content
    assert '"numpy"' not in content  # built-in data group has numpy, but overridden


def test_custom_extras_unknown_still_rejected(course_env: dict[str, Any]) -> None:
    """Unknown group not in built-in or custom is still rejected."""
    course_env["config"].custom_extras = {"finance": ["yfinance"]}
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--extras", "nonexistent"]
    with pytest.raises(SystemExit):
        main()


def test_custom_and_builtin_groups_together(course_env: dict[str, Any]) -> None:
    """Custom and built-in groups can be used together."""
    course_env["config"].custom_extras = {"finance": ["yfinance"]}
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "python",
        "finance",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"ipython"' in content
    assert '"yfinance"' in content


# ---------------------------------------------------------------------------
# _resolve_group tests (group references in custom extras)
# ---------------------------------------------------------------------------


def test_resolve_group_plain_packages() -> None:
    """A group with only plain packages returns them unchanged."""
    groups = {**EXTRAS_GROUPS, "finance": ["yfinance", "pandas-datareader"]}
    pkgs, expanded = _resolve_group("finance", groups)
    assert pkgs == ["yfinance", "pandas-datareader"]
    assert expanded == {"finance"}


def test_resolve_group_references_builtin() -> None:
    """A group referencing built-in groups expands them."""
    groups = {**EXTRAS_GROUPS, "reuven": ["python", "data", "plotly"]}
    pkgs, expanded = _resolve_group("reuven", groups)
    # Should contain packages from python group, data group, and literal plotly
    assert "ipython" in pkgs
    assert "numpy" in pkgs
    assert "pandas" in pkgs
    assert "plotly" in pkgs
    # Should NOT contain the group names as literal packages
    assert "python" not in pkgs
    assert "data" not in pkgs
    assert {"reuven", "python", "data"} == expanded


def test_resolve_group_references_custom_group() -> None:
    """A custom group can reference another custom group."""
    groups = {
        **EXTRAS_GROUPS,
        "base": ["ipython", "rich"],
        "full": ["base", "matplotlib"],
    }
    pkgs, expanded = _resolve_group("full", groups)
    assert "ipython" in pkgs
    assert "rich" in pkgs
    assert "matplotlib" in pkgs
    assert "base" not in pkgs
    assert {"full", "base"} == expanded


def test_resolve_group_circular_reference_raises() -> None:
    """Circular group references raise ValueError."""
    groups = {**EXTRAS_GROUPS, "a": ["b"], "b": ["a"]}
    with pytest.raises(ValueError, match="[Cc]ircular"):
        _resolve_group("a", groups)


def test_resolve_group_deduplicates() -> None:
    """Packages appearing in multiple referenced groups are deduplicated."""
    groups = {**EXTRAS_GROUPS, "combo": ["data", "numpy"]}
    pkgs, _ = _resolve_group("combo", groups)
    assert pkgs.count("numpy") == 1


def test_custom_extras_group_references_builtin_e2e(
    course_env: dict[str, Any],
) -> None:
    """Custom group referencing built-in groups expands packages in pyproject.toml."""
    course_env["config"].custom_extras = {"reuven": ["python", "data", "plotly"]}
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "reuven",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    # Packages from "python" group
    assert '"ipython"' in content
    # Packages from "data" group
    assert '"numpy"' in content
    assert '"pandas"' in content
    # Literal package
    assert '"plotly"' in content
    # Group names must NOT appear as packages
    assert '"python"' not in content
    assert '"data"' not in content


def test_custom_extras_group_ref_imports_included(
    course_env: dict[str, Any],
) -> None:
    """Imports from referenced built-in groups are included with --add-imports."""
    course_env["config"].custom_extras = {"reuven": ["data", "plotly"]}
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "reuven",
        "--add-imports",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    nb_path = dest / "acme-python-2026-03-19.ipynb"
    import json as json_mod

    nb = json_mod.loads(nb_path.read_text())
    source = "".join(nb["cells"][0]["source"])
    assert "import numpy as np" in source
    assert "import pandas as pd" in source


def test_custom_extras_override_still_works(course_env: dict[str, Any]) -> None:
    """Custom group overriding built-in still works (no recursive expansion)."""
    course_env["config"].custom_extras = {"data": ["polars"]}
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--extras", "data"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"polars"' in content
    assert '"numpy"' not in content


# ---------------------------------------------------------------------------
# _build_import_lines tests
# ---------------------------------------------------------------------------


def test_build_import_lines_data_group() -> None:
    """data group produces numpy, pandas imports (not plotly)."""
    result = _build_import_lines(["data"])
    assert "import numpy as np" in result
    assert "import pandas as pd" in result
    assert "import plotly.express as px" not in result


def test_build_import_lines_viz_group_includes_plotly() -> None:
    """viz group includes plotly import."""
    result = _build_import_lines(["viz"])
    assert "import matplotlib.pyplot as plt" in result
    assert "import seaborn as sns" in result
    assert "import plotly.express as px" in result


def test_build_import_lines_multiple_groups() -> None:
    """Multiple groups merge their imports."""
    result = _build_import_lines(["data", "viz"])
    assert "import numpy as np" in result
    assert "import matplotlib.pyplot as plt" in result


def test_build_import_lines_empty_list() -> None:
    """Empty group list returns empty string."""
    assert _build_import_lines([]) == ""


def test_build_import_lines_python_group_has_no_imports() -> None:
    """python group has no import lines (ipython is interactive)."""
    assert _build_import_lines(["python"]) == ""


def test_build_import_lines_deduplicates() -> None:
    """Same group twice doesn't duplicate imports."""
    result = _build_import_lines(["data", "data"])
    assert result.count("import numpy as np") == 1


def test_build_import_lines_unknown_group_ignored() -> None:
    """Unknown groups are silently skipped (no KeyError)."""
    result = _build_import_lines(["nonexistent"])
    assert result == ""


# ---------------------------------------------------------------------------
# --add-imports integration tests
# ---------------------------------------------------------------------------


def test_add_imports_jupyter_with_data(course_env: dict[str, Any]) -> None:
    """--add-imports with --extras data populates Jupyter notebook with imports."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "data",
        "--add-imports",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "acme-python-2026-03-19.ipynb").read_text()
    assert "import pandas as pd" in content
    assert "import numpy as np" in content


def test_add_imports_jupyter_is_valid_json(course_env: dict[str, Any]) -> None:
    """Jupyter notebook with imports is valid JSON."""
    import json as json_mod

    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "data",
        "--add-imports",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    data = json_mod.loads((dest / "acme-python-2026-03-19.ipynb").read_text())
    assert len(data["cells"]) == 1
    assert data["cells"][0]["cell_type"] == "code"


def test_add_imports_marimo_with_data(course_env: dict[str, Any]) -> None:
    """--add-imports with --extras data populates Marimo notebook with imports."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "data",
        "--add-imports",
        "--notebook-type",
        "marimo",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "acme-python-2026-03-19.py").read_text()
    assert "import pandas as pd" in content
    assert "import numpy as np" in content
    assert "import marimo" in content


def test_add_imports_without_extras_is_noop(course_env: dict[str, Any]) -> None:
    """--add-imports without --extras doesn't add any imports."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--add-imports"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "acme-python-2026-03-19.ipynb").read_text()
    assert "import pandas" not in content
    assert '"cells": []' in content


def test_no_add_imports_flag_no_imports(course_env: dict[str, Any]) -> None:
    """Without --add-imports, extras don't produce imports in notebooks."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "data",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "acme-python-2026-03-19.ipynb").read_text()
    assert "import pandas" not in content


def test_add_imports_multiple_sessions(course_env: dict[str, Any]) -> None:
    """--add-imports populates ALL notebooks when using -n."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "3",
        "--extras",
        "data",
        "--add-imports",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    for day in ["19", "20", "21"]:
        content = (dest / f"acme-python-2026-03-{day}.ipynb").read_text()
        assert "import pandas as pd" in content


def test_import_map_exists() -> None:
    """IMPORT_MAP is a dict with expected keys."""
    assert isinstance(IMPORT_MAP, dict)
    expected_keys = {"python", "data", "viz", "geo", "db", "ml"}
    assert set(IMPORT_MAP.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Progress indicator tests
# ---------------------------------------------------------------------------


def test_print_status_prints_message(capsys: pytest.CaptureFixture[str]) -> None:
    """_print_status prints the given message to stdout."""
    _print_status("Hello world")
    captured = capsys.readouterr()
    assert "Hello world" in captured.out


def test_progress_messages_appear_in_order(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """All progress messages appear in stdout in the correct order."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    output = capsys.readouterr().out
    expected = [
        "Creating course directory...",
        "Initializing git repository...",
        "Creating notebook files...",
        "Writing project configuration...",
        "Creating GitHub repository...",
        "Pushing to GitHub...",
        "Installing dependencies...",
        "Done! Course ready at acme-python-2026-03",
    ]
    positions = []
    for msg in expected:
        pos = output.find(msg)
        assert pos != -1, f"Missing progress message: {msg}"
        positions.append(pos)
    assert positions == sorted(positions), "Progress messages out of order"


def test_progress_message_readme_appears_when_readme_source_set(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """'Setting up README...' appears only when readme_source is configured."""
    custom_readme = course_env["tmp_path"] / "my-readme.md"
    custom_readme.write_text("# Custom\n")
    course_env["config"].readme_source = str(custom_readme)

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    output = capsys.readouterr().out
    assert "Setting up README..." in output


def test_progress_message_readme_absent_when_no_readme_source(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """'Setting up README...' does NOT appear when readme_source is None."""
    course_env["config"].readme_source = None
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    output = capsys.readouterr().out
    assert "Setting up README..." not in output


# ---------------------------------------------------------------------------
# Verbose flag tests
# ---------------------------------------------------------------------------


def test_print_verbose_prints_when_true(capsys: pytest.CaptureFixture[str]) -> None:
    """_print_verbose prints when verbose=True."""
    _print_verbose("detail info", verbose=True)
    assert "detail info" in capsys.readouterr().out


def test_print_verbose_silent_when_false(capsys: pytest.CaptureFixture[str]) -> None:
    """_print_verbose is silent when verbose=False."""
    _print_verbose("detail info", verbose=False)
    assert capsys.readouterr().out == ""


def test_verbose_flag_shows_details(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With -v, verbose details (template, destination, GitHub user) appear."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-v"]
    main()
    output = capsys.readouterr().out
    assert "Template:" in output
    assert "Destination: acme-python-2026-03" in output
    assert "GitHub user: testuser" in output
    assert "Repo: acme-python-2026-03" in output
    assert "Remote:" in output


def test_no_verbose_flag_hides_details(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without -v, verbose details do NOT appear."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    output = capsys.readouterr().out
    assert "Template:" not in output
    assert "GitHub user:" not in output
    assert "Remote:" not in output
    # But progress messages still appear
    assert "Creating course directory..." in output


def test_verbose_shows_notebook_filenames(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With -v, each notebook filename is printed."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "3",
        "-v",
    ]
    main()
    output = capsys.readouterr().out
    assert "acme-python-2026-03-19.ipynb" in output
    assert "acme-python-2026-03-20.ipynb" in output
    assert "acme-python-2026-03-21.ipynb" in output


def test_verbose_shows_extras_deps(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With -v and --extras, dependency list is printed."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-v",
        "--extras",
        "data",
    ]
    main()
    output = capsys.readouterr().out
    assert "Dependencies:" in output
    assert "numpy" in output
    assert "pandas" in output


def test_verbose_shows_readme_source(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With -v and readme_source, the source is printed."""
    custom_readme = course_env["tmp_path"] / "my-readme.md"
    custom_readme.write_text("# Custom\n")
    course_env["config"].readme_source = str(custom_readme)

    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-v"]
    main()
    output = capsys.readouterr().out
    assert "README source:" in output


def test_verbose_config_default_true(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When config.default_verbose is True, verbose output appears without -v."""
    course_env["config"].default_verbose = True
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    output = capsys.readouterr().out
    assert "Template:" in output
    assert "GitHub user:" in output


def test_verbose_config_default_false(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When config.default_verbose is False and no -v, verbose output is hidden."""
    course_env["config"].default_verbose = False
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    output = capsys.readouterr().out
    assert "Template:" not in output


# ---------------------------------------------------------------------------
# --dry-run flag tests
# ---------------------------------------------------------------------------


def test_dry_run_no_directory_created(
    course_env: dict[str, Any],
) -> None:
    """--dry-run does not create the destination directory."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--dry-run"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert not dest.exists()


def test_dry_run_no_subprocess_calls(
    course_env: dict[str, Any],
) -> None:
    """--dry-run does not invoke any subprocess commands."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--dry-run"]
    main()
    course_env["mock_run"].assert_not_called()


def test_dry_run_no_github_api_calls(
    course_env: dict[str, Any],
) -> None:
    """--dry-run does not call GitHub API."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--dry-run"]
    main()
    course_env["github_cls"].assert_not_called()
    course_env["user"].create_repo.assert_not_called()


def test_dry_run_prints_repo_name(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--dry-run prints the repo name in the summary."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--dry-run"]
    main()
    output = capsys.readouterr().out
    assert "acme-python-2026-03" in output
    assert "[dry-run]" in output


def test_dry_run_prints_notebook_filenames(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--dry-run prints notebook filenames."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "2",
        "--dry-run",
    ]
    main()
    output = capsys.readouterr().out
    assert "acme-python-2026-03-19.ipynb" in output
    assert "acme-python-2026-03-20.ipynb" in output


def test_dry_run_prints_dependencies(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--dry-run prints the dependency list."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--dry-run",
        "--extras",
        "data",
    ]
    main()
    output = capsys.readouterr().out
    assert "jupyter" in output
    assert "gitautopush" in output
    assert "numpy" in output


def test_dry_run_uses_placeholder_github_user(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--dry-run uses placeholder instead of actual GitHub username."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--dry-run"]
    main()
    output = capsys.readouterr().out
    assert "<your-github-username>" in output


def test_dry_run_marimo_shows_py_extension(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--dry-run with marimo shows .py notebook extensions."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--notebook-type",
        "marimo",
        "--dry-run",
    ]
    main()
    output = capsys.readouterr().out
    assert "acme-python-2026-03-19.py" in output
    assert "marimo" in output


# ---------------------------------------------------------------------------
# Rollback tests
# ---------------------------------------------------------------------------


def test_rollback_removes_directory_on_create_repo_failure(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When create_repo raises, the local directory is removed."""
    course_env["user"].create_repo.side_effect = RuntimeError("API error")
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    with pytest.raises(SystemExit, match="1"):
        main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert not dest.exists()
    output = capsys.readouterr().out
    assert "Rolling back..." in output
    assert "Removing local directory..." in output


def test_rollback_deletes_repo_and_directory_on_push_failure(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When git push fails after create_repo, both repo and directory are removed."""
    created_repo = MagicMock()
    course_env["user"].create_repo.return_value = created_repo

    original_side_effect = _fake_subprocess

    def fail_on_push(*args: Any, **kwargs: Any) -> Any:
        cmd = args[0] if args else kwargs.get("args", [])
        if cmd[:2] == ["git", "push"]:
            raise RuntimeError("push failed")
        return original_side_effect(*args, **kwargs)

    course_env["mock_run"].side_effect = fail_on_push

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    with pytest.raises(SystemExit, match="1"):
        main()

    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert not dest.exists()
    created_repo.delete.assert_called_once()
    output = capsys.readouterr().out
    assert "Removing GitHub repository..." in output
    assert "Removing local directory..." in output


def test_rollback_handles_cleanup_failure_gracefully(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When cleanup itself fails, a warning is printed and rollback continues."""
    created_repo = MagicMock()
    created_repo.delete.side_effect = RuntimeError("delete failed")
    course_env["user"].create_repo.return_value = created_repo

    original_side_effect = _fake_subprocess

    def fail_on_push(*args: Any, **kwargs: Any) -> Any:
        cmd = args[0] if args else kwargs.get("args", [])
        if cmd[:2] == ["git", "push"]:
            raise RuntimeError("push failed")
        return original_side_effect(*args, **kwargs)

    course_env["mock_run"].side_effect = fail_on_push

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    with pytest.raises(SystemExit, match="1"):
        main()

    output = capsys.readouterr().out
    assert "Warning: failed to remove GitHub repository:" in output
    # Directory cleanup should still happen even though repo cleanup failed
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert not dest.exists()


def test_no_rollback_on_success(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """On successful run, no rollback messages appear."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    output = capsys.readouterr().out
    assert "Rolling back..." not in output
    assert "Done! Course ready at" in output


def test_rollback_exit_code_is_1(
    course_env: dict[str, Any],
) -> None:
    """On failure, sys.exit(1) is called."""
    course_env["user"].create_repo.side_effect = RuntimeError("API error")
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_rollback_prints_error_message(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """On failure, the error message is printed."""
    course_env["user"].create_repo.side_effect = RuntimeError("token expired")
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    with pytest.raises(SystemExit):
        main()
    output = capsys.readouterr().out
    assert "Error: token expired" in output


# ---------------------------------------------------------------------------
# Default extras group config tests
# ---------------------------------------------------------------------------


def test_default_extras_group_used_when_no_cli_extras(
    course_env: dict[str, Any],
) -> None:
    """Config default_extras_group is used when --extras is not passed."""
    course_env["config"].default_extras_group = "data"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"numpy"' in content
    assert '"pandas"' in content


def test_cli_extras_overrides_default_extras_group(
    course_env: dict[str, Any],
) -> None:
    """--extras on CLI overrides config default_extras_group."""
    course_env["config"].default_extras_group = "data"
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "viz",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"matplotlib"' in content
    assert '"numpy"' not in content


def test_default_extras_group_none_means_no_extras(
    course_env: dict[str, Any],
) -> None:
    """When default_extras_group is None and no --extras, no extras added."""
    course_env["config"].default_extras_group = None
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"numpy"' not in content
    assert '"matplotlib"' not in content


def test_default_extras_group_custom_group(
    course_env: dict[str, Any],
) -> None:
    """Config default_extras_group can refer to a custom extras group."""
    course_env["config"].custom_extras = {"reuven": ["ipython", "rich"]}
    course_env["config"].default_extras_group = "reuven"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"ipython"' in content
    assert '"rich"' in content


def test_default_extras_group_unknown_causes_exit(
    course_env: dict[str, Any],
) -> None:
    """Unknown default_extras_group causes SystemExit."""
    course_env["config"].default_extras_group = "nonexistent"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    with pytest.raises(SystemExit):
        main()


def test_cli_empty_extras_overrides_default_extras_group(
    course_env: dict[str, Any],
) -> None:
    """--extras with no groups overrides default_extras_group (no extras)."""
    course_env["config"].default_extras_group = "data"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--extras"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    content = (dest / "pyproject.toml").read_text()
    assert '"numpy"' not in content


# ---------------------------------------------------------------------------
# Additional QA tests
# ---------------------------------------------------------------------------


def test_rollback_on_uv_sync_failure(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When uv sync fails, both GitHub repo and local directory are rolled back."""
    created_repo = MagicMock()
    course_env["user"].create_repo.return_value = created_repo

    original_side_effect = _fake_subprocess

    def fail_on_uv_sync(*args: Any, **kwargs: Any) -> Any:
        cmd = args[0] if args else kwargs.get("args", [])
        if cmd == ["uv", "sync"]:
            raise RuntimeError("uv sync failed")
        return original_side_effect(*args, **kwargs)

    course_env["mock_run"].side_effect = fail_on_uv_sync

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    with pytest.raises(SystemExit, match="1"):
        main()

    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert not dest.exists()
    created_repo.delete.assert_called_once()
    output = capsys.readouterr().out
    assert "Rolling back..." in output
    assert "Removing GitHub repository..." in output
    assert "Removing local directory..." in output


def test_rollback_on_git_commit_failure(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When git commit fails, the local directory and GitHub repo are rolled back."""
    created_repo = MagicMock()
    course_env["user"].create_repo.return_value = created_repo

    original_side_effect = _fake_subprocess

    def fail_on_commit(*args: Any, **kwargs: Any) -> Any:
        cmd = args[0] if args else kwargs.get("args", [])
        if cmd[:2] == ["git", "commit"]:
            raise RuntimeError("commit failed")
        return original_side_effect(*args, **kwargs)

    course_env["mock_run"].side_effect = fail_on_commit

    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    with pytest.raises(SystemExit, match="1"):
        main()

    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert not dest.exists()
    created_repo.delete.assert_called_once()
    output = capsys.readouterr().out
    assert "Rolling back..." in output
    assert "Removing local directory..." in output


def test_n_zero_creates_no_notebooks(course_env: dict[str, Any]) -> None:
    """With -n 0, no notebook files are created (template is deleted)."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-n", "0"]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert not (dest / "Course notebook.ipynb").exists()
    notebooks = list(dest.glob("*.ipynb")) + list(dest.glob("*.py"))
    notebook_files = [f for f in notebooks if f.suffix == ".ipynb" or "2026" in f.name]
    assert len(notebook_files) == 0


def test_add_imports_python_only_no_cell(course_env: dict[str, Any]) -> None:
    """--add-imports with --extras python adds no cell (no imports)."""
    import json as json_mod

    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--extras",
        "python",
        "--add-imports",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    nb = json_mod.loads((dest / "acme-python-2026-03-19.ipynb").read_text())
    assert nb["cells"] == []


def test_dry_run_with_default_extras_group(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run with default_extras_group=data shows data packages."""
    course_env["config"].default_extras_group = "data"
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "--dry-run"]
    main()
    output = capsys.readouterr().out
    assert "[dry-run]" in output
    assert "numpy" in output
    assert "pandas" in output


def test_dry_run_shows_notebook_type(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run output includes the notebook type."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--notebook-type",
        "marimo",
        "--dry-run",
    ]
    main()
    output = capsys.readouterr().out
    assert "Notebook type: marimo" in output


# ---------------------------------------------------------------------------
# --version flag
# ---------------------------------------------------------------------------


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    """--version prints the version string and exits cleanly."""
    from setup_course_github import __version__

    with patch("sys.argv", ["setup-course", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert __version__ in output


# ---------------------------------------------------------------------------
# --first-notebook-date flag tests
# ---------------------------------------------------------------------------


def test_first_notebook_date_sets_start(course_env: dict[str, Any]) -> None:
    """--first-notebook-date overrides notebook start date."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--first-notebook-date",
        "2026-04-01",
        "-n",
        "3",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-04-01.ipynb").exists()
    assert (dest / "acme-python-2026-04-02.ipynb").exists()
    assert (dest / "acme-python-2026-04-03.ipynb").exists()


def test_first_notebook_date_with_weekly(course_env: dict[str, Any]) -> None:
    """--first-notebook-date with --freq weekly spaces notebooks a week apart."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--first-notebook-date",
        "2026-04-01",
        "-n",
        "3",
        "--freq",
        "weekly",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-04-01.ipynb").exists()
    assert (dest / "acme-python-2026-04-08.ipynb").exists()
    assert (dest / "acme-python-2026-04-15.ipynb").exists()


def test_first_notebook_date_invalid_format_rejected(
    course_env: dict[str, Any],
) -> None:
    """--first-notebook-date with invalid format causes SystemExit."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--first-notebook-date",
        "not-a-date",
    ]
    with pytest.raises(SystemExit):
        main()


def test_first_notebook_date_default_is_today(course_env: dict[str, Any]) -> None:
    """Without --first-notebook-date, notebooks start from FAKE_TODAY."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "2",
    ]
    main()
    dest = course_env["tmp_path"] / "acme-python-2026-03"
    assert (dest / "acme-python-2026-03-19.ipynb").exists()
    assert (dest / "acme-python-2026-03-20.ipynb").exists()


def test_first_notebook_date_dry_run(
    course_env: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run output shows correct dates when --first-notebook-date is used."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--first-notebook-date",
        "2026-04-01",
        "-n",
        "3",
        "--dry-run",
    ]
    main()
    output = capsys.readouterr().out
    assert "[dry-run]" in output
    assert "2026-04-01" in output
    assert "2026-04-02" in output
    assert "2026-04-03" in output


# ---------------------------------------------------------------------------
# -d/--date validation tests
# ---------------------------------------------------------------------------


def test_date_valid_format_accepted(course_env: dict[str, Any]) -> None:
    """-d 2026-01 is accepted without error."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "2026-01"]
    main()
    course_env["user"].create_repo.assert_called_once_with(
        name="acme-python-2026-01", private=False
    )


def test_date_invalid_format_rejected(course_env: dict[str, Any]) -> None:
    """-d blah is rejected."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "blah"]
    with pytest.raises(SystemExit):
        main()


def test_date_invalid_month_rejected(course_env: dict[str, Any]) -> None:
    """-d 2026-13 is rejected (month 13 does not exist)."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "2026-13"]
    with pytest.raises(SystemExit):
        main()


def test_date_invalid_month_zero_rejected(course_env: dict[str, Any]) -> None:
    """-d 2026-00 is rejected (month 0 does not exist)."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "2026-00"]
    with pytest.raises(SystemExit):
        main()


def test_date_too_far_future_rejected(course_env: dict[str, Any]) -> None:
    """-d 2029-01 is rejected (more than 2 years ahead of FAKE_TODAY 2026)."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "2029-01"]
    with pytest.raises(SystemExit):
        main()


def test_date_two_years_ahead_accepted(course_env: dict[str, Any]) -> None:
    """-d 2028-12 is accepted (exactly 2 years ahead of 2026)."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "2028-12"]
    main()
    course_env["user"].create_repo.assert_called_once_with(
        name="acme-python-2028-12", private=False
    )


def test_date_past_year_accepted(course_env: dict[str, Any]) -> None:
    """-d 2020-06 is accepted (past years are fine)."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python", "-d", "2020-06"]
    main()
    course_env["user"].create_repo.assert_called_once_with(
        name="acme-python-2020-06", private=False
    )


# ---------------------------------------------------------------------------
# Weekend skipping – _notebook_dates unit tests
# ---------------------------------------------------------------------------


def test_notebook_dates_skip_standard_weekends() -> None:
    """Daily with standard skip: Wed Mar 18 start, 5 sessions skips Sat+Sun."""
    # Mar 18 2026 = Wednesday (weekday 2)
    start = datetime.date(2026, 3, 18)
    result = _notebook_dates(start, 5, "daily", {5, 6})
    assert result == [
        datetime.date(2026, 3, 18),  # Wed
        datetime.date(2026, 3, 19),  # Thu
        datetime.date(2026, 3, 20),  # Fri
        datetime.date(2026, 3, 23),  # Mon (skip Sat+Sun)
        datetime.date(2026, 3, 24),  # Tue
    ]


def test_notebook_dates_skip_israeli_weekends() -> None:
    """Daily with Israeli skip: Wed Mar 18 start, 5 sessions skips Fri+Sat."""
    start = datetime.date(2026, 3, 18)
    result = _notebook_dates(start, 5, "daily", {4, 5})
    assert result == [
        datetime.date(2026, 3, 18),  # Wed
        datetime.date(2026, 3, 19),  # Thu
        datetime.date(2026, 3, 22),  # Sun (skip Fri+Sat)
        datetime.date(2026, 3, 23),  # Mon
        datetime.date(2026, 3, 24),  # Tue
    ]


def test_notebook_dates_start_on_skip_day() -> None:
    """If start date is a Saturday with standard skip, advance to Monday."""
    # Mar 21 2026 = Saturday (weekday 5)
    start = datetime.date(2026, 3, 21)
    result = _notebook_dates(start, 3, "daily", {5, 6})
    assert result == [
        datetime.date(2026, 3, 23),  # Mon
        datetime.date(2026, 3, 24),  # Tue
        datetime.date(2026, 3, 25),  # Wed
    ]


def test_notebook_dates_weekly_skip_weekends() -> None:
    """Weekly freq: start on Sat with standard skip advances to Monday."""
    # Start Sat Mar 21 → advance to Mon Mar 23. +7 = Mon Mar 30. +7 = Mon Apr 6.
    start = datetime.date(2026, 3, 21)  # Saturday
    result = _notebook_dates(start, 3, "weekly", {5, 6})
    assert result == [
        datetime.date(2026, 3, 23),  # Mon (advanced from Sat)
        datetime.date(2026, 3, 30),  # Mon (+7)
        datetime.date(2026, 4, 6),  # Mon (+7)
    ]


def test_skip_weekends_e2e(course_env: dict[str, Any]) -> None:
    """--skip-weekends with -n 5 generates correct notebook filenames."""
    # FAKE_TODAY = 2026-03-19 (Thursday)
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "5",
        "--skip-weekends",
        "--dry-run",
    ]
    main()
    # Verify the dates are correct by checking _notebook_dates directly
    dates = _notebook_dates(FAKE_TODAY, 5, "daily", {5, 6})
    assert dates == [
        datetime.date(2026, 3, 19),  # Thu
        datetime.date(2026, 3, 20),  # Fri
        datetime.date(2026, 3, 23),  # Mon
        datetime.date(2026, 3, 24),  # Tue
        datetime.date(2026, 3, 25),  # Wed
    ]


def test_skip_israeli_weekends_e2e(course_env: dict[str, Any]) -> None:
    """--skip-israeli-weekends with -n 5 generates correct notebook filenames."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "5",
        "--skip-israeli-weekends",
        "--dry-run",
    ]
    main()
    # Thu Mar 19, Sun Mar 22, Mon Mar 23, Tue Mar 24, Wed Mar 25
    dates = _notebook_dates(FAKE_TODAY, 5, "daily", {4, 5})
    assert dates == [
        datetime.date(2026, 3, 19),  # Thu
        datetime.date(2026, 3, 22),  # Sun (skip Fri+Sat)
        datetime.date(2026, 3, 23),  # Mon
        datetime.date(2026, 3, 24),  # Tue
        datetime.date(2026, 3, 25),  # Wed
    ]


def test_skip_weekends_mutually_exclusive(course_env: dict[str, Any]) -> None:
    """Both --skip-weekends and --skip-israeli-weekends together → SystemExit."""
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "--skip-weekends",
        "--skip-israeli-weekends",
    ]
    with pytest.raises(SystemExit):
        main()


def test_skip_weekends_config_default(course_env: dict[str, Any]) -> None:
    """Config default_weekend = 'standard' applies when no CLI flag."""
    course_env["config"].default_weekend = "standard"
    sys.argv = [
        "setup-course",
        "-c",
        "acme",
        "-t",
        "python",
        "-n",
        "5",
        "--dry-run",
    ]
    main()
    # FAKE_TODAY = Thu Mar 19, standard skip → same as test_skip_weekends_e2e
    dates = _notebook_dates(FAKE_TODAY, 5, "daily", {5, 6})
    assert dates == [
        datetime.date(2026, 3, 19),
        datetime.date(2026, 3, 20),
        datetime.date(2026, 3, 23),
        datetime.date(2026, 3, 24),
        datetime.date(2026, 3, 25),
    ]


def test_gitignore_present_in_course_directory(
    course_env: dict[str, Any],
) -> None:
    """.gitignore is copied into the new course directory."""
    sys.argv = ["setup-course", "-c", "acme", "-t", "python"]
    main()
    course_dir = Path(f"acme-python-{FAKE_TODAY:%Y-%m}")
    gitignore = course_dir / ".gitignore"
    assert gitignore.exists(), ".gitignore should be present in the course directory"
    contents = gitignore.read_text()
    assert "__pycache__/" in contents
