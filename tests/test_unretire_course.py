from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup_course_github.unretire_course import main, unretire_course

# ---------------------------------------------------------------------------
# unretire_course
# ---------------------------------------------------------------------------


def test_unretire_makes_repo_public() -> None:
    """unretire_course must call repo.edit(private=False)."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.unretire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.unretire_course.get_github",
            return_value=mock_github,
        ):
            with patch("setup_course_github.unretire_course.shutil.move"):
                with patch(
                    "setup_course_github.unretire_course.Path.cwd",
                    return_value=Path("/fake/cwd"),
                ):
                    with patch(
                        "setup_course_github.unretire_course.Path.exists",
                        return_value=False,
                    ):
                        unretire_course("/archive/2024/myrepo")

    mock_repo.edit.assert_called_once_with(private=False)


def test_unretire_moves_to_cwd() -> None:
    """unretire_course moves the directory to cwd."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.unretire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.unretire_course.get_github",
            return_value=mock_github,
        ):
            with patch("setup_course_github.unretire_course.shutil.move") as mock_move:
                with patch(
                    "setup_course_github.unretire_course.Path.cwd",
                    return_value=Path("/fake/cwd"),
                ):
                    with patch(
                        "setup_course_github.unretire_course.Path.exists",
                        return_value=False,
                    ):
                        unretire_course("/archive/2024/myrepo")

    mock_move.assert_called_once_with(
        "/archive/2024/myrepo", str(Path("/fake/cwd") / "myrepo")
    )


def test_unretire_preserves_dir_name() -> None:
    """Only the basename of dirname is used for the destination."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.unretire_course.get_remote_url",
        return_value="git@github.com:someuser/mycourse.git",
    ):
        with patch(
            "setup_course_github.unretire_course.get_github",
            return_value=mock_github,
        ):
            with patch("setup_course_github.unretire_course.shutil.move") as mock_move:
                with patch(
                    "setup_course_github.unretire_course.Path.cwd",
                    return_value=Path("/work"),
                ):
                    with patch(
                        "setup_course_github.unretire_course.Path.exists",
                        return_value=False,
                    ):
                        unretire_course("/deep/nested/path/mycourse")

    dest = mock_move.call_args[0][1]
    assert dest == str(Path("/work/mycourse"))


def test_unretire_fails_if_dest_exists() -> None:
    """If a directory with the same name exists in cwd, raise RuntimeError."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.unretire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.unretire_course.get_github",
            return_value=mock_github,
        ):
            with patch(
                "setup_course_github.unretire_course.Path.cwd",
                return_value=Path("/fake/cwd"),
            ):
                with patch(
                    "setup_course_github.unretire_course.Path.exists",
                    return_value=True,
                ):
                    with pytest.raises(RuntimeError, match="already exists"):
                        unretire_course("/archive/2024/myrepo")


def test_unretire_prints_success_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Success message includes the directory name."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.unretire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.unretire_course.get_github",
            return_value=mock_github,
        ):
            with patch("setup_course_github.unretire_course.shutil.move"):
                with patch(
                    "setup_course_github.unretire_course.Path.cwd",
                    return_value=Path("/fake/cwd"),
                ):
                    with patch(
                        "setup_course_github.unretire_course.Path.exists",
                        return_value=False,
                    ):
                        unretire_course("/archive/2024/myrepo")

    captured = capsys.readouterr()
    assert "/archive/2024/myrepo" in captured.out
    assert "unretired" in captured.out.lower() or "Successfully" in captured.out


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_unretire_main_calls_unretire_course() -> None:
    """main() parses args and calls unretire_course."""
    with patch("setup_course_github.unretire_course.unretire_course") as mock_unretire:
        with patch("sys.argv", ["unretire-course", "/archive/2024/myrepo"]):
            main()

    mock_unretire.assert_called_once_with("/archive/2024/myrepo")


def test_unretire_main_requires_dirname() -> None:
    """main() must exit if dirname is not supplied."""
    with patch("sys.argv", ["unretire-course"]):
        with pytest.raises(SystemExit):
            main()


# ---------------------------------------------------------------------------
# --version flag
# ---------------------------------------------------------------------------


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    """--version prints the version, PyPI URL, and author info."""
    from setup_course_github import __author__, __email__, __version__

    with patch("sys.argv", ["unretire-course", "--version"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert __version__ in output
    assert "https://pypi.org/project/course-setup/" in output
    assert __author__ in output
    assert __email__ in output


def test_help_shows_version_and_url(capsys: pytest.CaptureFixture[str]) -> None:
    """--help output contains version, PyPI URL, and author name."""
    from setup_course_github import __author__, __version__

    with patch("sys.argv", ["unretire-course", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert __version__ in output
    assert "https://pypi.org/project/course-setup/" in output
    assert __author__ in output


# ---------------------------------------------------------------------------
# Spaces in directory names
# ---------------------------------------------------------------------------


def test_unretire_dirname_with_spaces() -> None:
    """unretire_course handles a dirname with spaces correctly."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.unretire_course.get_remote_url",
        return_value="git@github.com:user/Acme Corp-python.git",
    ):
        with patch(
            "setup_course_github.unretire_course.get_github",
            return_value=mock_github,
        ):
            with patch("setup_course_github.unretire_course.shutil.move") as mock_move:
                with patch(
                    "setup_course_github.unretire_course.Path.cwd",
                    return_value=Path("/fake/cwd"),
                ):
                    with patch(
                        "setup_course_github.unretire_course.Path.exists",
                        return_value=False,
                    ):
                        unretire_course("/archive/2024/Acme Corp-python")

    dest = mock_move.call_args[0][1]
    assert dest == str(Path("/fake/cwd/Acme Corp-python"))
