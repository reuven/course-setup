import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup_course_github.config import CourseConfig
from setup_course_github.retire_course import (
    get_remote_url,
    main,
    parse_repo_name,
    retire_course,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_CONFIG = CourseConfig(
    github_token="ghp_testtoken",
    archive_path=Path("/tmp/archive"),
    default_notebook_type="jupyter",
)


# ---------------------------------------------------------------------------
# get_remote_url
# ---------------------------------------------------------------------------


def test_get_remote_url_calls_subprocess_with_list_form(tmp_path: Path) -> None:
    """subprocess.run must be called with a list, not a shell string."""
    mock_result = MagicMock()
    mock_result.stdout = b"git@github.com:someuser/myrepo.git\n"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        get_remote_url(str(tmp_path))
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # First positional arg must be a list
        assert call_args[0][0] == ["git", "config", "remote.origin.url"]


def test_get_remote_url_passes_cwd(tmp_path: Path) -> None:
    """subprocess.run must use cwd= not os.chdir."""
    mock_result = MagicMock()
    mock_result.stdout = b"git@github.com:someuser/myrepo.git\n"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        get_remote_url(str(tmp_path))
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("cwd") == str(tmp_path)


def test_get_remote_url_no_shell_true(tmp_path: Path) -> None:
    """shell=True must NOT be used."""
    mock_result = MagicMock()
    mock_result.stdout = b"git@github.com:someuser/myrepo.git\n"

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        get_remote_url(str(tmp_path))
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get("shell", False) is False


def test_get_remote_url_returns_stripped_string(tmp_path: Path) -> None:
    """Returned URL must be stripped of whitespace."""
    mock_result = MagicMock()
    mock_result.stdout = b"git@github.com:someuser/myrepo.git\n"

    with patch("subprocess.run", return_value=mock_result):
        url = get_remote_url(str(tmp_path))
    assert url == "git@github.com:someuser/myrepo.git"


# ---------------------------------------------------------------------------
# parse_repo_name
# ---------------------------------------------------------------------------


def test_parse_repo_name_ssh_url() -> None:
    """Standard SSH URL: git@github.com:someuser/myrepo.git → 'someuser/myrepo'."""
    assert parse_repo_name("git@github.com:someuser/myrepo.git") == "someuser/myrepo"


def test_parse_repo_name_preserves_username() -> None:
    """Username in the URL is NOT hardcoded — it is extracted from the URL."""
    assert (
        parse_repo_name("git@github.com:otheruser/courserepo.git")
        == "otheruser/courserepo"
    )


def test_parse_repo_name_strips_dot_git() -> None:
    """The .git suffix must be stripped."""
    result = parse_repo_name("git@github.com:user/repo.git")
    assert not result.endswith(".git")


def test_parse_repo_name_no_hardcoded_reuven() -> None:
    """parse_repo_name must not inject a hardcoded username."""
    result = parse_repo_name("git@github.com:alice/myrepo.git")
    assert result == "alice/myrepo"
    assert "reuven" not in result


# ---------------------------------------------------------------------------
# retire_course (the core logic function)
# ---------------------------------------------------------------------------


def test_retire_course_makes_repo_private() -> None:
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("shutil.move"):
                    retire_course("/some/course/dir")

    mock_repo.edit.assert_called_once_with(private=True)


def test_retire_course_calls_get_repo_with_parsed_name() -> None:
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:alice/awesomecourse.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("shutil.move"):
                    retire_course("/some/course/dir")

    mock_github.get_repo.assert_called_once_with("alice/awesomecourse")


def test_retire_course_shutil_move_correct_source() -> None:
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("shutil.move") as mock_move:
                    retire_course("/some/course/dir")

    call_args = mock_move.call_args[0]
    assert call_args[0] == "/some/course/dir"


def test_retire_course_shutil_move_correct_destination() -> None:
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    year = datetime.datetime.now().year

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("shutil.move") as mock_move:
                    retire_course("/some/course/dir")

    call_args = mock_move.call_args[0]
    expected_dest = Path("/tmp/archive") / str(year)
    assert call_args[1] == expected_dest


def test_retire_course_uses_archive_path_from_config() -> None:
    """archive path comes from config, not hardcoded."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    custom_config = CourseConfig(
        github_token="tok",
        archive_path=Path("/custom/archive"),
        default_notebook_type="jupyter",
    )
    year = datetime.datetime.now().year

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:u/r.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=custom_config,
            ):
                with patch("shutil.move") as mock_move:
                    retire_course("/my/course")

    expected_dest = Path("/custom/archive") / str(year)
    assert mock_move.call_args[0][1] == expected_dest


def test_retire_course_no_os_chdir() -> None:
    """retire_course must not call os.chdir."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:u/r.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("shutil.move"):
                    with patch("os.chdir") as mock_chdir:
                        retire_course("/my/course")

    mock_chdir.assert_not_called()


# ---------------------------------------------------------------------------
# Hardening tests
# ---------------------------------------------------------------------------


def test_parse_repo_name_without_dot_git() -> None:
    """parse_repo_name handles URLs without the .git suffix."""
    result = parse_repo_name("git@github.com:someuser/myrepo")
    assert result == "someuser/myrepo"


def test_retire_course_passes_dirname_to_get_remote_url() -> None:
    """retire_course calls get_remote_url with the dirname it received."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:u/r.git",
    ) as mock_get_url:
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("shutil.move"):
                    retire_course("/specific/path/to/course")

    mock_get_url.assert_called_once_with("/specific/path/to/course")


def test_retire_course_prints_success_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """retire_course prints a success message with the dirname."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:u/r.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("shutil.move"):
                    retire_course("/my/course")

    captured = capsys.readouterr()
    assert "/my/course" in captured.out
    assert "retired" in captured.out.lower() or "Successfully" in captured.out


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_calls_retire_course(tmp_path: Path) -> None:
    """main() must parse positional dirname and call retire_course with it."""
    with patch("setup_course_github.retire_course.retire_course") as mock_retire:
        with patch("sys.argv", ["retire-course", str(tmp_path)]):
            main()

    mock_retire.assert_called_once_with(str(tmp_path))


def test_main_requires_dirname() -> None:
    """main() must exit if dirname is not supplied."""
    with patch("sys.argv", ["retire-course"]):
        with pytest.raises(SystemExit):
            main()


def test_main_multiple_dirs(tmp_path: Path) -> None:
    """main() calls retire_course once per directory."""
    dir1 = str(tmp_path / "course1")
    dir2 = str(tmp_path / "course2")
    dir3 = str(tmp_path / "course3")
    with patch("setup_course_github.retire_course.retire_course") as mock_retire:
        with patch("sys.argv", ["retire-course", dir1, dir2, dir3]):
            main()
    assert mock_retire.call_count == 3
    mock_retire.assert_any_call(dir1)
    mock_retire.assert_any_call(dir2)
    mock_retire.assert_any_call(dir3)


def test_main_continues_on_failure(tmp_path: Path) -> None:
    """If one directory fails, the rest are still processed."""
    dir1 = str(tmp_path / "course1")
    dir2 = str(tmp_path / "course2")

    def fail_on_first(dirname: str) -> None:
        if dirname == dir1:
            raise RuntimeError("GitHub API error")

    with patch(
        "setup_course_github.retire_course.retire_course",
        side_effect=fail_on_first,
    ) as mock_retire:
        with patch("sys.argv", ["retire-course", dir1, dir2]):
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 1
    assert mock_retire.call_count == 2


def test_main_exits_1_on_any_failure(tmp_path: Path) -> None:
    """main() exits with code 1 if any directory fails."""
    dir1 = str(tmp_path / "course1")
    with patch(
        "setup_course_github.retire_course.retire_course",
        side_effect=RuntimeError("fail"),
    ):
        with patch("sys.argv", ["retire-course", dir1]):
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 1


def test_main_no_exit_on_all_success(tmp_path: Path) -> None:
    """main() does not sys.exit when all directories succeed."""
    dir1 = str(tmp_path / "course1")
    dir2 = str(tmp_path / "course2")
    with patch("setup_course_github.retire_course.retire_course"):
        with patch("sys.argv", ["retire-course", dir1, dir2]):
            main()  # Should not raise SystemExit


def test_main_error_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Error messages include the failing directory name."""
    dir1 = str(tmp_path / "course1")
    with patch(
        "setup_course_github.retire_course.retire_course",
        side_effect=RuntimeError("connection refused"),
    ):
        with patch("sys.argv", ["retire-course", dir1]):
            with pytest.raises(SystemExit):
                main()
    captured = capsys.readouterr()
    assert "course1" in captured.out
    assert "connection refused" in captured.out


# ---------------------------------------------------------------------------
# setup_course_github.__init__ (get_github, get_github_user)
# ---------------------------------------------------------------------------


def test_get_github_returns_github_instance() -> None:
    from setup_course_github import get_github

    with patch("setup_course_github.load_config", return_value=FAKE_CONFIG):
        g = get_github()

    from github import Github

    assert isinstance(g, Github)


def test_get_github_user_returns_authenticated_user() -> None:
    from github.AuthenticatedUser import AuthenticatedUser

    from setup_course_github import get_github_user

    mock_user = MagicMock(spec=AuthenticatedUser)
    mock_github = MagicMock()
    mock_github.get_user.return_value = mock_user

    with patch("setup_course_github.get_github", return_value=mock_github):
        user = get_github_user()

    assert user is mock_user
