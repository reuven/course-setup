"""Tests for setup_course v2 CLI."""

import datetime
import os
import sys
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from setup_course_github.setup_course import (
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
