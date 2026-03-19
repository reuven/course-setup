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
    main,
)

FAKE_TODAY = datetime.date(2026, 3, 19)


def _fake_git_init(*args: Any, **kwargs: Any) -> None:
    """Simulate git init by creating the .git directory."""
    cwd = kwargs.get("cwd")
    if cwd is not None:
        (Path(cwd) / ".git").mkdir(exist_ok=True)


def make_mock_config(
    default_notebook_type: str = "jupyter",
    readme_source: str | None = None,
) -> MagicMock:
    """Return a mock CourseConfig with sensible defaults."""
    config = MagicMock()
    config.github_token = "ghp_testtoken"
    config.default_notebook_type = default_notebook_type
    config.readme_source = readme_source
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
            side_effect=_fake_git_init,
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
    course_env["mock_run"].assert_called_once_with(
        ["git", "init"], cwd="acme-python-2026-03", check=True
    )


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
    """--extras python data adds ipython, numpy, pandas, xlrd, openpyxl, plotly."""
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
    for pkg in ["ipython", "numpy", "pandas", "xlrd", "openpyxl", "plotly"]:
        assert f'"{pkg}"' in content, f"{pkg} missing from pyproject.toml"


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
    extra_deps = [
        d for d in deps if d in {"numpy", "pandas", "xlrd", "openpyxl", "plotly"}
    ]
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
# _build_import_lines tests
# ---------------------------------------------------------------------------


def test_build_import_lines_data_group() -> None:
    """data group produces numpy, pandas, plotly imports."""
    result = _build_import_lines(["data"])
    assert "import numpy as np" in result
    assert "import pandas as pd" in result
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
