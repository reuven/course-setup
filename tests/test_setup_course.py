"""Tests for the refactored setup_course module."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from setup_course_github.setup_course import _get_template_dir, main


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


# ---------------------------------------------------------------------------
# Destination directory name tests
# ---------------------------------------------------------------------------


def test_destination_dir_without_name(tmp_path: Path) -> None:
    """Destination is client-date when --name is not provided."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user()
    dest = tmp_path / "acme-2026-01-01"

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course.Path.__new__",
        ),
        patch.object(
            Path,
            "__truediv__",
            side_effect=lambda self, other: (
                template if other == "generic" else Path.__truediv__(self, other)
            ),
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-01-01",
            "-c",
            "acme",
            "-r",
            "some-repo",
            "--notebook-type",
            "jupyter",
        ]

        with (
            patch("setup_course_github.setup_course.Path.__new__"),
            patch.object(
                Path,
                "__truediv__",
                side_effect=lambda self, other: (
                    template
                    if other == "generic"
                    else type(self).__truediv__(self, other)
                ),
            ),
        ):
            pass  # tested via integration approach below

    # Use the integration approach: patch template_dir directly
    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-01-01",
            "-c",
            "acme",
            "-r",
            "some-repo",
            "--notebook-type",
            "jupyter",
        ]
        orig_cwd = Path.cwd()
        import os

        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(orig_cwd)

    assert dest.exists()
    assert dest.is_dir()


def test_destination_dir_with_name(tmp_path: Path) -> None:
    """Destination is client-date-name when --name is provided."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user()
    dest = tmp_path / "acme-2026-01-01-advanced"

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-01-01",
            "-c",
            "acme",
            "-r",
            "some-repo",
            "-n",
            "advanced",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    assert dest.exists()
    assert dest.is_dir()


# ---------------------------------------------------------------------------
# Template copy and dot-git rename
# ---------------------------------------------------------------------------


def test_template_copied_and_git_init_called(tmp_path: Path) -> None:
    """Template is copied and git init is run instead of renaming dot-git."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ) as mock_run,
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    assert not (dest / "dot-git").exists()
    mock_run.assert_called_once_with(["git", "init"], cwd="corp-2026-03-01", check=True)


# ---------------------------------------------------------------------------
# Notebook file tests
# ---------------------------------------------------------------------------


def test_jupyter_notebook_created(tmp_path: Path) -> None:
    """For jupyter type, Course notebook.ipynb is renamed correctly."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config(default_notebook_type="jupyter")
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    expected_notebook = dest / "corp - 2026-03-01.ipynb"
    assert expected_notebook.exists()
    assert not (dest / "Course notebook.ipynb").exists()


def test_jupyter_notebook_with_suffix(tmp_path: Path) -> None:
    """For jupyter type with --name, notebook filename includes the suffix."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config(default_notebook_type="jupyter")
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "-n",
            "advanced",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01-advanced"
    expected_notebook = dest / "corp - 2026-03-01-advanced.ipynb"
    assert expected_notebook.exists()


def test_marimo_notebook_created(tmp_path: Path) -> None:
    """For marimo type, a .py marimo notebook is created and .ipynb removed."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config(default_notebook_type="jupyter")
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "marimo",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    expected_py = dest / "corp - 2026-03-01.py"
    assert expected_py.exists()
    assert not (dest / "Course notebook.ipynb").exists()
    assert not (dest / "corp - 2026-03-01.ipynb").exists()


def test_marimo_notebook_content(tmp_path: Path) -> None:
    """The marimo notebook has the correct minimal content."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "marimo",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    py_file = dest / "corp - 2026-03-01.py"
    content = py_file.read_text()
    assert "import marimo" in content
    assert "__generated_with" in content
    assert "app = marimo.App()" in content
    assert "@app.cell" in content
    assert "app.run()" in content


# ---------------------------------------------------------------------------
# pyproject.toml tests
# ---------------------------------------------------------------------------


def test_pyproject_toml_created_jupyter(tmp_path: Path) -> None:
    """pyproject.toml is created in destination with jupyter dependency."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "my-course-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    toml_file = dest / "pyproject.toml"
    assert toml_file.exists()
    content = toml_file.read_text()
    assert 'name = "my-course-repo"' in content
    assert "jupyter" in content
    assert "gitautopush" in content
    assert "marimo" not in content
    assert ">=3.13" in content


def test_pyproject_toml_created_marimo(tmp_path: Path) -> None:
    """pyproject.toml is created with marimo dependency."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "my-course-repo",
            "--notebook-type",
            "marimo",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    toml_file = dest / "pyproject.toml"
    assert toml_file.exists()
    content = toml_file.read_text()
    assert 'name = "my-course-repo"' in content
    assert "marimo" in content
    assert "gitautopush" in content
    assert "jupyter" not in content


def test_pyproject_toml_always_has_gitautopush(tmp_path: Path) -> None:
    """gitautopush is always in the pyproject.toml dependencies."""
    mock_config = make_mock_config()
    mock_user = make_mock_user()

    for notebook_type in ("jupyter", "marimo"):
        # Fresh template each iteration
        local_template = setup_template(tmp_path / f"template_{notebook_type}")

        with (
            patch(
                "setup_course_github.setup_course.load_config", return_value=mock_config
            ),
            patch("setup_course_github.setup_course.Github") as mock_github_cls,
            patch(
                "setup_course_github.setup_course._get_template_dir",
                return_value=local_template,
            ),
            patch(
                "setup_course_github.setup_course.subprocess.run",
                side_effect=_fake_git_init,
            ),
        ):
            mock_github_cls.return_value.get_user.return_value = mock_user

            import os
            import sys

            dest_name = f"corp-2026-03-01-{notebook_type}"
            sys.argv = [
                "setup-course",
                "-d",
                "2026-03-01",
                "-c",
                "corp",
                "-r",
                "corp-repo",
                "-n",
                notebook_type,
                "--notebook-type",
                notebook_type,
            ]
            os.chdir(tmp_path)
            try:
                main()
            finally:
                os.chdir(Path(__file__).parent.parent)

        dest = tmp_path / dest_name
        content = (dest / "pyproject.toml").read_text()
        assert "gitautopush" in content, f"gitautopush missing for {notebook_type}"


# ---------------------------------------------------------------------------
# Git config tests
# ---------------------------------------------------------------------------


def test_git_config_uses_api_username(tmp_path: Path) -> None:
    """Git remote URL uses username from GitHub API, not hardcoded."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user(login="api_user_123")

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    git_config = (dest / ".git" / "config").read_text()
    assert "api_user_123" in git_config
    assert "reuven" not in git_config
    assert "corp-repo.git" in git_config


def test_git_config_not_hardcoded_reuven(tmp_path: Path) -> None:
    """The hardcoded 'reuven' username is never used; API login is used instead."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user(login="different_user")

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    git_config = (dest / ".git" / "config").read_text()
    assert "different_user" in git_config


# ---------------------------------------------------------------------------
# GitHub API interaction tests
# ---------------------------------------------------------------------------


def test_github_repo_created_as_public(tmp_path: Path) -> None:
    """GitHub repo is created via API as a public repo."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "my-public-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    mock_user.create_repo.assert_called_once_with(name="my-public-repo", private=False)


def test_github_authenticated_with_token(tmp_path: Path) -> None:
    """Github is instantiated with the token from the config."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config()
    mock_config.github_token = "ghp_supersecrettoken"
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    mock_github_cls.assert_called_once_with("ghp_supersecrettoken")


# ---------------------------------------------------------------------------
# --notebook-type flag tests
# ---------------------------------------------------------------------------


def test_notebook_type_flag_overrides_config(tmp_path: Path) -> None:
    """--notebook-type flag overrides the config default."""
    template = setup_template(tmp_path)
    # Config says jupyter, but flag says marimo
    mock_config = make_mock_config(default_notebook_type="jupyter")
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "marimo",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    # Should have .py not .ipynb
    assert (dest / "corp - 2026-03-01.py").exists()
    assert not (dest / "corp - 2026-03-01.ipynb").exists()


def test_default_notebook_type_from_config(tmp_path: Path) -> None:
    """When --notebook-type is not given, config default is used."""
    template = setup_template(tmp_path)
    # Config says marimo, no flag provided
    mock_config = make_mock_config(default_notebook_type="marimo")
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            # No --notebook-type flag
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    assert (dest / "corp - 2026-03-01.py").exists()
    assert not (dest / "corp - 2026-03-01.ipynb").exists()


def test_default_notebook_type_jupyter_from_config(tmp_path: Path) -> None:
    """When --notebook-type is not given and config default is jupyter."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config(default_notebook_type="jupyter")
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            # No --notebook-type flag
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    assert (dest / "corp - 2026-03-01.ipynb").exists()
    assert not (dest / "corp - 2026-03-01.py").exists()


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_get_template_dir_returns_generic_path() -> None:
    """_get_template_dir returns a path ending in 'generic' within the package."""
    result = _get_template_dir()
    assert result.name == "generic"
    assert result.parent.name == "setup_course_github"


# ---------------------------------------------------------------------------
# README source tests
# ---------------------------------------------------------------------------


def test_bundled_readme_used_when_no_readme_source(tmp_path: Path) -> None:
    """When readme_source is None, the bundled template README is used."""
    template = setup_template(tmp_path)
    mock_config = make_mock_config(readme_source=None)
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    readme = dest / "README.md"
    assert readme.exists()
    assert readme.read_text() == "# Course\n"


def test_readme_from_local_file(tmp_path: Path) -> None:
    """When readme_source is a local file path, that file is used as README."""
    template = setup_template(tmp_path)
    custom_readme = tmp_path / "my-custom-readme.md"
    custom_readme.write_text("# My Custom README\nHello world!\n")

    mock_config = make_mock_config(readme_source=str(custom_readme))
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    readme = dest / "README.md"
    assert readme.exists()
    assert readme.read_text() == "# My Custom README\nHello world!\n"


def test_readme_from_url(tmp_path: Path) -> None:
    """When readme_source is a URL, the content is fetched and used as README."""
    template = setup_template(tmp_path)
    url = "https://example.com/my-readme.md"
    fetched_content = "# README from URL\nFetched content.\n"

    mock_config = make_mock_config(readme_source=url)
    mock_user = make_mock_user()

    with (
        patch("setup_course_github.setup_course.load_config", return_value=mock_config),
        patch("setup_course_github.setup_course.Github") as mock_github_cls,
        patch(
            "setup_course_github.setup_course._get_template_dir", return_value=template
        ),
        patch(
            "setup_course_github.setup_course.urllib.request.urlopen"
        ) as mock_urlopen,
        patch(
            "setup_course_github.setup_course.subprocess.run",
            side_effect=_fake_git_init,
        ),
    ):
        mock_github_cls.return_value.get_user.return_value = mock_user
        mock_response = MagicMock()
        mock_response.read.return_value = fetched_content.encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        import os
        import sys

        sys.argv = [
            "setup-course",
            "-d",
            "2026-03-01",
            "-c",
            "corp",
            "-r",
            "corp-repo",
            "--notebook-type",
            "jupyter",
        ]
        os.chdir(tmp_path)
        try:
            main()
        finally:
            os.chdir(Path(__file__).parent.parent)

    dest = tmp_path / "corp-2026-03-01"
    readme = dest / "README.md"
    assert readme.exists()
    assert readme.read_text() == fetched_content
