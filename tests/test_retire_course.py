import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup_course_github.config import CourseConfig
from setup_course_github.retire_course import (
    _build_retirement_summary,
    _confirm_create_dir,
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
                with patch("setup_course_github.retire_course._confirm_create_dir"):
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
                with patch("setup_course_github.retire_course._confirm_create_dir"):
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
                with patch("setup_course_github.retire_course._confirm_create_dir"):
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
                with patch("setup_course_github.retire_course._confirm_create_dir"):
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
                with patch("setup_course_github.retire_course._confirm_create_dir"):
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
                with patch("setup_course_github.retire_course._confirm_create_dir"):
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
                with patch("setup_course_github.retire_course._confirm_create_dir"):
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
                with patch("setup_course_github.retire_course._confirm_create_dir"):
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

    mock_retire.assert_called_once_with(str(tmp_path), keep_public=False)


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
    mock_retire.assert_any_call(dir1, keep_public=False)
    mock_retire.assert_any_call(dir2, keep_public=False)
    mock_retire.assert_any_call(dir3, keep_public=False)


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


# ---------------------------------------------------------------------------
# Additional QA tests
# ---------------------------------------------------------------------------


def test_parse_repo_name_https_url() -> None:
    """Document that parse_repo_name only handles SSH format.

    An HTTPS URL like "https://github.com/user/repo.git" is split on ":"
    into ["https", "//github.com/user/repo.git"].  Index [1] gives
    "//github.com/user/repo.git", and after stripping ".git" the result
    is "//github.com/user/repo" — clearly wrong, but this is the current
    (known) behavior.
    """
    result = parse_repo_name("https://github.com/user/repo.git")
    # Documents the actual (unexpected) result for HTTPS URLs
    assert result == "//github.com/user/repo"


def test_get_remote_url_empty_on_failure(tmp_path: Path) -> None:
    """When subprocess returns empty stdout, get_remote_url returns ''."""
    mock_result = MagicMock()
    mock_result.stdout = b""

    with patch("subprocess.run", return_value=mock_result):
        url = get_remote_url(str(tmp_path))

    assert url == ""


def test_retire_course_error_on_empty_remote_url() -> None:
    """When get_remote_url returns '', parse_repo_name raises IndexError."""
    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="",
    ):
        with patch(
            "setup_course_github.retire_course.load_config",
            return_value=FAKE_CONFIG,
        ):
            with pytest.raises(IndexError):
                retire_course("/some/course/dir")


def test_main_prints_error_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Document that errors are printed to stdout, not stderr.

    Line 66 of retire_course.py uses plain print() rather than
    print(..., file=sys.stderr), so error messages go to stdout.
    """
    dir1 = str(tmp_path / "bad_course")
    with patch(
        "setup_course_github.retire_course.retire_course",
        side_effect=RuntimeError("some failure"),
    ):
        with patch("sys.argv", ["retire-course", dir1]):
            with pytest.raises(SystemExit):
                main()

    captured = capsys.readouterr()
    # Error appears on stdout, NOT stderr
    assert "some failure" in captured.out
    assert captured.err == ""


# ---------------------------------------------------------------------------
# --version flag
# ---------------------------------------------------------------------------


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    """--version prints the version, PyPI URL, and author info."""
    from setup_course_github import __author__, __email__, __version__

    with patch("sys.argv", ["retire-course", "--version"]):
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

    with patch("sys.argv", ["retire-course", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert __version__ in output
    assert "https://pypi.org/project/course-setup/" in output
    assert __author__ in output


# ---------------------------------------------------------------------------
# _confirm_create_dir
# ---------------------------------------------------------------------------


def test_archive_dir_exists_no_prompt(tmp_path: Path) -> None:
    """When the year directory already exists, no prompt is shown."""
    year_dir = tmp_path / "2026"
    year_dir.mkdir()

    mock_confirm = MagicMock()
    _confirm_create_dir(year_dir, confirm=mock_confirm)

    mock_confirm.assert_not_called()


def test_archive_dir_missing_user_says_yes(tmp_path: Path) -> None:
    """When the year dir doesn't exist and user says 'y', dir is created."""
    year_dir = tmp_path / "2026"
    assert not year_dir.exists()

    mock_confirm = MagicMock(return_value="y")
    _confirm_create_dir(year_dir, confirm=mock_confirm)

    assert year_dir.exists()
    mock_confirm.assert_called_once()


def test_archive_dir_missing_user_says_no(tmp_path: Path) -> None:
    """When user says 'n', RuntimeError is raised and dir is not created."""
    year_dir = tmp_path / "2026"
    assert not year_dir.exists()

    mock_confirm = MagicMock(return_value="n")
    with pytest.raises(RuntimeError, match="Aborted"):
        _confirm_create_dir(year_dir, confirm=mock_confirm)

    assert not year_dir.exists()


def test_archive_dir_missing_user_says_empty(tmp_path: Path) -> None:
    """When user just hits Enter (empty string), treated as 'no'."""
    year_dir = tmp_path / "2026"
    assert not year_dir.exists()

    mock_confirm = MagicMock(return_value="")
    with pytest.raises(RuntimeError, match="Aborted"):
        _confirm_create_dir(year_dir, confirm=mock_confirm)

    assert not year_dir.exists()


def test_confirm_create_dir_creates_nested(tmp_path: Path) -> None:
    """mkdir uses parents=True so intermediate directories are created."""
    nested_dir = tmp_path / "deep" / "nested" / "2026"
    assert not nested_dir.exists()

    mock_confirm = MagicMock(return_value="yes")
    _confirm_create_dir(nested_dir, confirm=mock_confirm)

    assert nested_dir.exists()


# ---------------------------------------------------------------------------
# _build_retirement_summary
# ---------------------------------------------------------------------------


def test_retirement_summary_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """retire_course prints a Retirement Summary with count and path."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    # Create a notebook so the summary has something to count
    (course_dir / "Lecture-2026-03-19.ipynb").write_text("{}")

    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    year = datetime.datetime.now().year
    archive_config = CourseConfig(
        github_token="tok",
        archive_path=tmp_path / "archive",
        default_notebook_type="jupyter",
    )
    archive_dest = tmp_path / "archive" / str(year)
    archive_dest.mkdir(parents=True)

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:user/mycourse.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=archive_config,
            ):
                with patch("setup_course_github.retire_course._confirm_create_dir"):
                    with patch("shutil.move"):
                        retire_course(str(course_dir))

    captured = capsys.readouterr()
    assert "Retirement Summary" in captured.out
    assert "Notebooks:" in captured.out
    assert str(archive_dest / "mycourse") in captured.out


def test_retirement_summary_with_notebooks(tmp_path: Path) -> None:
    """_build_retirement_summary counts notebooks and extracts date range."""
    course_dir = tmp_path / "python-course"
    course_dir.mkdir()
    # Create fake notebook files with date patterns
    (course_dir / "Lecture-2026-03-19.ipynb").write_text("{}")
    (course_dir / "Lecture-2026-03-20.ipynb").write_text("{}")
    (course_dir / "Lecture-2026-03-23.ipynb").write_text("{}")
    # Create a pyproject.toml with dependencies
    toml = (
        '[project]\nname = "test"\n'
        'dependencies = ["jupyter", "numpy>=1.21", "pandas"]\n'
    )
    (course_dir / "pyproject.toml").write_text(toml)

    dest = tmp_path / "archive" / "2026"
    summary = _build_retirement_summary(str(course_dir), "user/python-course", dest)

    assert "Notebooks: 3 (.ipynb)" in summary
    assert "2026-03-19" in summary
    assert "2026-03-23" in summary
    assert "jupyter" in summary
    assert "numpy" in summary
    assert "pandas" in summary


def test_retirement_summary_no_notebooks(tmp_path: Path) -> None:
    """Directory with no notebooks shows 0 in summary."""
    course_dir = tmp_path / "empty-course"
    course_dir.mkdir()

    dest = tmp_path / "archive" / "2026"
    summary = _build_retirement_summary(str(course_dir), "user/empty-course", dest)

    assert "Notebooks: 0" in summary


def test_retirement_summary_no_pyproject(tmp_path: Path) -> None:
    """Directory with no pyproject.toml still produces a valid summary."""
    course_dir = tmp_path / "no-pyproject"
    course_dir.mkdir()
    (course_dir / "Lecture-2026-03-19.ipynb").write_text("{}")

    dest = tmp_path / "archive" / "2026"
    summary = _build_retirement_summary(str(course_dir), "user/no-pyproject", dest)

    assert "Retirement Summary" in summary
    assert "Dependencies: none" in summary
    assert "Notebooks: 1" in summary


def test_retirement_summary_marimo_notebooks(tmp_path: Path) -> None:
    """Marimo .py notebooks are counted correctly."""
    course_dir = tmp_path / "marimo-course"
    course_dir.mkdir()
    marimo_content = (
        "import marimo\n\napp = marimo.App()\n\n@app.cell\ndef _():\n    pass\n"
    )
    (course_dir / "Lecture-2026-03-19.py").write_text(marimo_content)
    (course_dir / "Lecture-2026-03-20.py").write_text(marimo_content)

    dest = tmp_path / "archive" / "2026"
    summary = _build_retirement_summary(str(course_dir), "user/marimo-course", dest)

    assert "Notebooks: 2 (marimo .py)" in summary
    assert "2026-03-19" in summary
    assert "2026-03-20" in summary


def test_retirement_summary_mixed_notebooks(tmp_path: Path) -> None:
    """Both .ipynb and marimo .py notebooks are counted together."""
    course_dir = tmp_path / "mixed-course"
    course_dir.mkdir()
    (course_dir / "Lecture-2026-03-19.ipynb").write_text("{}")
    marimo_content = "import marimo\n\napp = marimo.App()\n"
    (course_dir / "Lecture-2026-03-20.py").write_text(marimo_content)

    dest = tmp_path / "archive" / "2026"
    summary = _build_retirement_summary(str(course_dir), "user/mixed-course", dest)

    assert "Notebooks: 2 (.ipynb + marimo .py)" in summary


def test_retirement_summary_non_marimo_py_not_counted(tmp_path: Path) -> None:
    """Regular .py files (not marimo) should not be counted as notebooks."""
    course_dir = tmp_path / "regular-py"
    course_dir.mkdir()
    (course_dir / "helper-2026-03-19.py").write_text("print('hello')\n")

    dest = tmp_path / "archive" / "2026"
    summary = _build_retirement_summary(str(course_dir), "user/regular-py", dest)

    assert "Notebooks: 0" in summary


def test_retirement_summary_unreadable_py_file(tmp_path: Path) -> None:
    """A .py file that cannot be read is not counted as a notebook."""
    course_dir = tmp_path / "bad-py"
    course_dir.mkdir()
    bad_file = course_dir / "Lecture-2026-03-19.py"
    bad_file.write_bytes(b"\x80\x81\x82\x83")  # invalid UTF-8

    dest = tmp_path / "archive" / "2026"
    summary = _build_retirement_summary(str(course_dir), "user/bad-py", dest)

    assert "Notebooks: 0" in summary


def test_retirement_summary_corrupt_pyproject(tmp_path: Path) -> None:
    """A corrupt pyproject.toml results in 'none' for dependencies."""
    course_dir = tmp_path / "corrupt-toml"
    course_dir.mkdir()
    (course_dir / "pyproject.toml").write_text("this is not valid toml [[[[")

    dest = tmp_path / "archive" / "2026"
    summary = _build_retirement_summary(str(course_dir), "user/corrupt-toml", dest)

    assert "Dependencies: none" in summary


# ---------------------------------------------------------------------------
# Spaces in directory / repo names
# ---------------------------------------------------------------------------


def test_retire_dirname_with_spaces() -> None:
    """retire_course works when dirname contains spaces."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:user/Acme Corp-python-2026-03.git",
    ) as mock_get_url:
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("setup_course_github.retire_course._confirm_create_dir"):
                    with patch("shutil.move") as mock_move:
                        retire_course("Acme Corp-python-2026-03")

    mock_get_url.assert_called_once_with("Acme Corp-python-2026-03")
    assert mock_move.call_args[0][0] == "Acme Corp-python-2026-03"


def test_parse_repo_name_with_spaces() -> None:
    """parse_repo_name handles repo names with spaces."""
    result = parse_repo_name("git@github.com:user/Acme Corp-python.git")
    assert result == "user/Acme Corp-python"


# ---------------------------------------------------------------------------
# --keep-public flag
# ---------------------------------------------------------------------------


def test_keep_public_does_not_make_repo_private() -> None:
    """With keep_public=True, repo.edit(private=True) is NOT called."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:user/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("setup_course_github.retire_course._confirm_create_dir"):
                    with patch("shutil.move"):
                        retire_course("/some/course", keep_public=True)

    mock_repo.edit.assert_not_called()


def test_default_makes_repo_private() -> None:
    """Without keep_public, repo.edit(private=True) IS called."""
    mock_repo = MagicMock()
    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:user/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.get_github", return_value=mock_github
        ):
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("setup_course_github.retire_course._confirm_create_dir"):
                    with patch("shutil.move"):
                        retire_course("/some/course")

    mock_repo.edit.assert_called_once_with(private=True)


def test_keep_public_summary_says_still_public(tmp_path: Path) -> None:
    """Summary says 'still public' when keep_public=True."""
    from setup_course_github.retire_course import _build_retirement_summary

    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    dest = tmp_path / "archive" / "2026"

    summary = _build_retirement_summary(
        str(course_dir), "user/mycourse", dest, kept_public=True
    )
    assert "still public" in summary
    assert "now private" not in summary


def test_keep_public_summary_default_says_private(tmp_path: Path) -> None:
    """Summary says 'now private' by default."""
    from setup_course_github.retire_course import _build_retirement_summary

    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    dest = tmp_path / "archive" / "2026"

    summary = _build_retirement_summary(str(course_dir), "user/mycourse", dest)
    assert "now private" in summary
    assert "still public" not in summary


def test_main_keep_public_flag(tmp_path: Path) -> None:
    """main() passes keep_public=True when --keep-public is given."""
    with patch("setup_course_github.retire_course.retire_course") as mock_retire:
        with patch("sys.argv", ["retire-course", "--keep-public", str(tmp_path)]):
            main()

    mock_retire.assert_called_once_with(str(tmp_path), keep_public=True)


def test_main_no_keep_public_flag(tmp_path: Path) -> None:
    """main() passes keep_public=False by default."""
    with patch("setup_course_github.retire_course.retire_course") as mock_retire:
        with patch("sys.argv", ["retire-course", str(tmp_path)]):
            main()

    mock_retire.assert_called_once_with(str(tmp_path), keep_public=False)
