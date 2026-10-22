import inspect
import os
import subprocess
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup_course_github.archive_course import (
    _apply_size_guard,
    _archive_members,
    _ask_to_drop,
    _choose_drops,
    _format_size,
    _megabytes_to_bytes,
    _member_contributions,
    _size_candidates,
    _write_zip,
    archive_course,
    main,
)

# ---------------------------------------------------------------------------
# archive_course function tests
# ---------------------------------------------------------------------------


def test_archive_creates_zip(tmp_path: Path) -> None:
    """Archive a temp dir with files, verify .zip exists and contains them."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "file1.txt").write_text("hello")
    (course_dir / "file2.txt").write_text("world")

    out = str(tmp_path / "mycourse.zip")
    zip_path = archive_course(str(course_dir), output=out, export_html=False)

    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "mycourse/file1.txt" in names
        assert "mycourse/file2.txt" in names


def test_archive_default_output_uses_dirname(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no output is given, zip is created in cwd as {dirname}.zip."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "file.txt").write_text("hello")

    monkeypatch.chdir(tmp_path)
    zip_path = archive_course(str(course_dir), export_html=False)

    assert zip_path == Path("mycourse.zip")
    assert (tmp_path / "mycourse.zip").exists()


def test_archive_custom_output_path(tmp_path: Path) -> None:
    """Use --output custom.zip, verify it's created at that path."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "file1.txt").write_text("hello")

    custom_output = str(tmp_path / "custom.zip")
    zip_path = archive_course(str(course_dir), output=custom_output, export_html=False)

    assert zip_path == Path(custom_output)
    assert zip_path.exists()


def test_archive_html_export(tmp_path: Path) -> None:
    """Create a temp dir with a fake .ipynb file, mock subprocess.run for nbconvert."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    nb_file = course_dir / "lesson.ipynb"
    nb_file.write_text('{"cells": []}')

    out = str(tmp_path / "out.zip")
    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        archive_course(str(course_dir), output=out, export_html=True, export_pdf=False)

    mock_run.assert_called_once_with(
        ["uv", "run", "jupyter", "nbconvert", "--to", "html", "lesson.ipynb"],
        cwd=str(course_dir),
        capture_output=True,
        check=True,
    )


def test_archive_no_html_flag(tmp_path: Path) -> None:
    """With --no-html, subprocess for nbconvert should NOT be called."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')

    out = str(tmp_path / "out.zip")
    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        archive_course(str(course_dir), output=out, export_html=False, export_pdf=False)

    mock_run.assert_not_called()


def test_archive_zip_contains_html(tmp_path: Path) -> None:
    """After HTML export (mocked), verify the zip includes .html files."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')
    # Simulate the HTML file that nbconvert would create
    (course_dir / "lesson.html").write_text("<html></html>")

    out = str(tmp_path / "out.zip")
    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        zip_path = archive_course(str(course_dir), output=out, export_html=True)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "mycourse/lesson.html" in names
        assert "mycourse/lesson.ipynb" in names


def test_archive_no_notebooks_skips_html(tmp_path: Path) -> None:
    """Directory with no .ipynb files, no nbconvert call."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "readme.txt").write_text("no notebooks here")

    out = str(tmp_path / "out.zip")
    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        archive_course(str(course_dir), output=out, export_html=True)

    mock_run.assert_not_called()


def test_archive_prints_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify stdout includes zip filename and file count."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "file1.txt").write_text("hello")
    (course_dir / "file2.txt").write_text("world")

    out = str(tmp_path / "mycourse.zip")
    zip_path = archive_course(str(course_dir), output=out, export_html=False)

    captured = capsys.readouterr()
    assert str(zip_path) in captured.out
    assert "Files: 2" in captured.out


def test_archive_summary_lists_all_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Summary lists non-notebook files under 'Other files' section."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "script.py").write_text("print('hi')")
    (course_dir / "data.csv").write_text("a,b\n1,2\n")
    (course_dir / "pyproject.toml").write_text("[project]\nname = 'x'\n")

    out = str(tmp_path / "mycourse.zip")
    archive_course(str(course_dir), output=out, export_html=False)

    captured = capsys.readouterr()
    assert "Other files:" in captured.out
    assert "data.csv" in captured.out
    assert "pyproject.toml" in captured.out
    assert "script.py" in captured.out


def test_archive_summary_lists_notebooks_and_other_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Summary lists both notebooks and other files in separate sections."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')
    (course_dir / "helper.py").write_text("x = 1")

    out = str(tmp_path / "mycourse.zip")
    archive_course(str(course_dir), output=out, export_html=False, export_pdf=False)

    captured = capsys.readouterr()
    assert "Notebooks:" in captured.out
    assert "lesson.ipynb" in captured.out
    assert "Other files:" in captured.out
    assert "helper.py" in captured.out


def test_archive_summary_no_other_files_section_when_only_notebooks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No 'Other files' section when directory only contains notebooks."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')

    out = str(tmp_path / "mycourse.zip")
    archive_course(str(course_dir), output=out, export_html=False, export_pdf=False)

    captured = capsys.readouterr()
    assert "Notebooks:" in captured.out
    assert "Other files:" not in captured.out


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------


def test_main_calls_archive_course(tmp_path: Path) -> None:
    """main() parses args correctly and calls archive_course."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "file.txt").write_text("test")

    with patch("setup_course_github.archive_course.archive_course") as mock_archive:
        with patch("sys.argv", ["archive-course", str(course_dir)]):
            main()

    mock_archive.assert_called_once_with(
        dirname=str(course_dir),
        output=None,
        export_html=True,
        export_pdf=True,
        max_size=10.0,
        keep_all=False,
    )


def test_main_requires_dirname() -> None:
    """No args -> SystemExit."""
    with patch("sys.argv", ["archive-course"]):
        with pytest.raises(SystemExit):
            main()


def test_archive_nonexistent_dir_fails(tmp_path: Path) -> None:
    """Non-existent directory raises FileNotFoundError."""
    nonexistent = str(tmp_path / "does_not_exist")
    with pytest.raises(FileNotFoundError, match="Directory not found"):
        archive_course(nonexistent)


# ---------------------------------------------------------------------------
# Error handling and exclusion tests
# ---------------------------------------------------------------------------


def test_archive_excludes_git_and_venv(tmp_path: Path) -> None:
    """Zip excludes .git, .venv, __pycache__, .ipynb_checkpoints."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "file.txt").write_text("keep")
    (course_dir / ".git").mkdir()
    (course_dir / ".git" / "config").write_text("git")
    (course_dir / ".venv").mkdir()
    (course_dir / ".venv" / "bin").mkdir()
    (course_dir / ".venv" / "bin" / "python").write_text("py")
    (course_dir / "__pycache__").mkdir()
    (course_dir / "__pycache__" / "mod.pyc").write_text("cache")
    (course_dir / ".ipynb_checkpoints").mkdir()
    (course_dir / ".ipynb_checkpoints" / "nb.ipynb").write_text("{}")

    out = str(tmp_path / "out.zip")
    zip_path = archive_course(str(course_dir), output=out, export_html=False)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "mycourse/file.txt" in names
        assert not any(".git" in n for n in names)
        assert not any(".venv" in n for n in names)
        assert not any("__pycache__" in n for n in names)
        assert not any(".ipynb_checkpoints" in n for n in names)


def test_archive_html_export_failure_continues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When nbconvert fails, a warning is printed but archive still completes."""
    import subprocess as sp

    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')

    def fail_nbconvert(*args: object, **kwargs: object) -> None:
        raise sp.CalledProcessError(1, "nbconvert", stderr=b"conversion error")

    out = str(tmp_path / "out.zip")
    with patch(
        "setup_course_github.archive_course.subprocess.run", side_effect=fail_nbconvert
    ):
        zip_path = archive_course(str(course_dir), output=out, export_html=True)

    assert zip_path.exists()
    output = capsys.readouterr().out
    assert "Warning" in output


def test_archive_html_export_jupyter_not_found(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When jupyter is not installed, a warning is printed but archive completes."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')

    def raise_not_found(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("No such file or directory: 'uv'")

    out = str(tmp_path / "out.zip")
    with patch(
        "setup_course_github.archive_course.subprocess.run", side_effect=raise_not_found
    ):
        zip_path = archive_course(str(course_dir), output=out, export_html=True)

    assert zip_path.exists()
    output = capsys.readouterr().out
    assert "jupyter nbconvert not found" in output


def test_export_notebook_to_pdf_runs_webpdf(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _export_notebook_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nb = course / "lesson.ipynb"
    nb.write_text("{}")
    with patch("subprocess.run") as mock_run:
        ok, stderr = _export_notebook_to_pdf(nb, course)
    assert ok is True
    assert stderr == ""
    args = mock_run.call_args
    assert args.kwargs["cwd"] == str(course)
    cmd = args.args[0]
    assert cmd == [
        "uv",
        "run",
        "jupyter",
        "nbconvert",
        "--to",
        "webpdf",
        "lesson.ipynb",
    ]
    # check=True is load-bearing: without it a failed export would look like success
    assert args.kwargs["check"] is True
    assert args.kwargs["capture_output"] is True


def test_export_notebook_to_pdf_handles_called_process_error(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _export_notebook_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nb = course / "lesson.ipynb"
    nb.write_text("{}")
    err = subprocess.CalledProcessError(1, "nbconvert", stderr=b"chromium missing")
    with patch("subprocess.run", side_effect=err):
        ok, stderr = _export_notebook_to_pdf(nb, course)
    assert ok is False
    assert "chromium missing" in stderr


def test_export_notebook_to_pdf_handles_missing_binary(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _export_notebook_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nb = course / "lesson.ipynb"
    nb.write_text("{}")
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        ok, stderr = _export_notebook_to_pdf(nb, course)
    assert ok is False


def test_install_chromium_runs_playwright(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _install_chromium

    course = tmp_path / "course"
    course.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert _install_chromium(course) is True
    cmd = mock_run.call_args.args[0]
    assert cmd == ["uv", "run", "playwright", "install", "chromium"]
    assert mock_run.call_args.kwargs["cwd"] == str(course)
    assert mock_run.call_args.kwargs["capture_output"] is True


def test_export_notebooks_to_pdf_install_failure_stops_no_second_install(
    tmp_path: Path,
) -> None:
    """When chromium install fails, stop (break) — don't retry install per notebook.

    Pins `break` (vs `continue`) in the install-failure branch: with two
    chromium-failing notebooks, `_install_chromium` is attempted exactly once.
    """
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        return_value=(False, "Executable doesn't exist"),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium",
            return_value=False,
        ) as mock_install:
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 0
    mock_install.assert_called_once()


def test_export_notebooks_to_pdf_installs_chromium_only_once_across_notebooks(
    tmp_path: Path,
) -> None:
    """After a successful install, a later chromium failure does NOT re-install.

    Pins the `chromium_installed = True` guard: notebook a triggers a successful
    install + retry; notebook b also reports chromium-missing but must NOT cause a
    second install, so `_install_chromium` is called exactly once.
    """
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    # a: chromium-missing, retry ok; b: chromium-missing (already installed)
    results = iter(
        [
            (False, "Executable doesn't exist"),
            (True, ""),
            (False, "Executable doesn't exist"),
        ]
    )
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        side_effect=lambda *a, **k: next(results),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium",
            return_value=True,
        ) as mock_install:
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 1
    mock_install.assert_called_once()


def test_install_chromium_returns_false_on_failure(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _install_chromium

    course = tmp_path / "course"
    course.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert _install_chromium(course) is False


def test_export_notebooks_to_pdf_all_succeed(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        return_value=(True, ""),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium"
        ) as mock_install:
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 2
    mock_install.assert_not_called()


def test_export_notebooks_to_pdf_installs_chromium_once_then_retries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    # a.ipynb: first call chromium-missing, retry succeeds; b.ipynb succeeds
    results = iter([(False, "Executable doesn't exist"), (True, ""), (True, "")])
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        side_effect=lambda *a, **k: next(results),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium",
            return_value=True,
        ) as mock_install:
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 2
    mock_install.assert_called_once()
    out = capsys.readouterr().out
    assert "Installing it once now" in out
    assert "Chromium installed." in out


def test_export_notebooks_to_pdf_install_failure_degrades(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb"]
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        return_value=(False, "Executable doesn't exist"),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium",
            return_value=False,
        ):
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 0
    assert "Could not install Chromium" in capsys.readouterr().out


def test_export_notebooks_to_pdf_lib_missing_prints_hint_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        return_value=(False, "Please install `nbconvert[webpdf]`"),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium"
        ) as mock_install:
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 0
    mock_install.assert_not_called()
    out = capsys.readouterr().out
    assert out.count('uv add "nbconvert[webpdf]"') == 1  # printed once, not per-nb


def test_export_notebooks_to_pdf_other_error_warns_and_continues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    results = iter([(False, "weird\nRuntimeError: nope"), (True, "")])
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        side_effect=lambda *a, **k: next(results),
    ):
        count = _export_notebooks_to_pdf(nbs, course)
    assert count == 1
    out = capsys.readouterr().out
    assert "Warning: failed to export a.ipynb to PDF: RuntimeError: nope" in out


def test_archive_notebook_with_spaces_in_name(tmp_path: Path) -> None:
    """Notebooks with spaces in filenames are handled correctly."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    nb_file = course_dir / "My Notebook - Day 1.ipynb"
    nb_file.write_text('{"cells": []}')

    out = str(tmp_path / "out.zip")
    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        archive_course(str(course_dir), output=out, export_html=True, export_pdf=False)

    # Should pass relative path, not absolute
    mock_run.assert_called_once_with(
        [
            "uv",
            "run",
            "jupyter",
            "nbconvert",
            "--to",
            "html",
            "My Notebook - Day 1.ipynb",
        ],
        cwd=str(course_dir),
        capture_output=True,
        check=True,
    )


# ---------------------------------------------------------------------------
# Spaces in directory names
# ---------------------------------------------------------------------------


def test_archive_dirname_with_spaces(tmp_path: Path) -> None:
    """Archive a directory whose name contains spaces."""
    course_dir = tmp_path / "My Course"
    course_dir.mkdir()
    (course_dir / "notes.txt").write_text("hello")
    (course_dir / "data.csv").write_text("a,b\n1,2\n")

    out = str(tmp_path / "My Course.zip")
    zip_path = archive_course(str(course_dir), output=out, export_html=False)

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "My Course/notes.txt" in names
        assert "My Course/data.csv" in names


def test_archive_excludes_dirs_when_dirname_has_spaces(tmp_path: Path) -> None:
    """Excluded dirs (.git, .venv, etc.) are still excluded when dirname has spaces."""
    course_dir = tmp_path / "My Course"
    course_dir.mkdir()
    (course_dir / "file.txt").write_text("keep")
    (course_dir / ".git").mkdir()
    (course_dir / ".git" / "config").write_text("git")
    (course_dir / ".venv").mkdir()
    (course_dir / ".venv" / "pyvenv.cfg").write_text("venv")
    (course_dir / "__pycache__").mkdir()
    (course_dir / "__pycache__" / "mod.pyc").write_text("cache")
    (course_dir / ".ipynb_checkpoints").mkdir()
    (course_dir / ".ipynb_checkpoints" / "nb.ipynb").write_text("{}")

    out = str(tmp_path / "out.zip")
    zip_path = archive_course(str(course_dir), output=out, export_html=False)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "My Course/file.txt" in names
        assert not any(".git" in n for n in names)
        assert not any(".venv" in n for n in names)
        assert not any("__pycache__" in n for n in names)
        assert not any(".ipynb_checkpoints" in n for n in names)


# ---------------------------------------------------------------------------
# --version / --help flags
# ---------------------------------------------------------------------------


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    """--version prints version, PyPI URL, and author info without a config file."""
    from setup_course_github import __author__, __email__, __version__

    with patch("sys.argv", ["archive-course", "--version"]):
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
    """--help works without a config file and shows version, URL, and author."""
    from setup_course_github import __author__, __version__

    with patch("sys.argv", ["archive-course", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert __version__ in output
    assert "https://pypi.org/project/course-setup/" in output
    assert __author__ in output


# ---------------------------------------------------------------------------
# HTML export accounting (assert the *effect* of export, not just the call)
# ---------------------------------------------------------------------------


def test_archive_reports_html_export_count_on_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A successful HTML export is counted and reported in the summary."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')

    out = str(tmp_path / "out.zip")
    with patch("setup_course_github.archive_course.subprocess.run", MagicMock()):
        archive_course(str(course_dir), output=out, export_html=True)

    assert "HTML exports: 1" in capsys.readouterr().out


def test_archive_failed_html_export_not_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed nbconvert is not counted, so no 'HTML exports' line appears."""
    import subprocess as sp

    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')

    def fail_nbconvert(*args: object, **kwargs: object) -> None:
        raise sp.CalledProcessError(1, "nbconvert", stderr=b"boom")

    out = str(tmp_path / "out.zip")
    with patch(
        "setup_course_github.archive_course.subprocess.run", side_effect=fail_nbconvert
    ):
        archive_course(str(course_dir), output=out, export_html=True)

    assert "HTML exports:" not in capsys.readouterr().out


def test_archive_missing_nbconvert_not_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When jupyter/nbconvert is missing, nothing is counted as exported."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')

    out = str(tmp_path / "out.zip")
    with patch(
        "setup_course_github.archive_course.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        archive_course(str(course_dir), output=out, export_html=True)

    assert "HTML exports:" not in capsys.readouterr().out


def test_archive_no_html_ignores_existing_html_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With export_html=False, an existing .html on disk is not paired in summary."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')
    (course_dir / "lesson.html").write_text("<html></html>")

    out = str(tmp_path / "out.zip")
    archive_course(str(course_dir), output=out, export_html=False, export_pdf=False)

    output = capsys.readouterr().out
    assert "lesson.ipynb + lesson.html" not in output
    assert "lesson.ipynb" in output


def test_archive_excludes_checkpoint_notebooks_from_html(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Notebooks under .ipynb_checkpoints are not exported to HTML or counted."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')
    ckpt = course_dir / ".ipynb_checkpoints"
    ckpt.mkdir()
    (ckpt / "lesson-checkpoint.ipynb").write_text('{"cells": []}')

    out = str(tmp_path / "out.zip")
    with patch("setup_course_github.archive_course.subprocess.run", MagicMock()):
        archive_course(str(course_dir), output=out, export_html=True)

    output = capsys.readouterr().out
    assert "HTML exports: 1" in output
    assert "checkpoint" not in output


def test_archive_html_export_count_accumulates_across_notebooks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two successful exports are counted as 2, not reset to 1.

    Pins ``html_exported += 1`` against a mutation to ``html_exported = 1``,
    which a single-notebook test cannot distinguish (1 == 1).
    """
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson1.ipynb").write_text('{"cells": []}')
    (course_dir / "lesson2.ipynb").write_text('{"cells": []}')

    out = str(tmp_path / "out.zip")
    with patch("setup_course_github.archive_course.subprocess.run", MagicMock()):
        archive_course(str(course_dir), output=out, export_html=True)

    assert "HTML exports: 2" in capsys.readouterr().out


def test_archive_small_archive_size_reported_in_kb(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A sub-megabyte archive reports its size in KB, not MB.

    Pins the ``zip_size < 1024 * 1024`` threshold: a mutation turning the
    multiplication into division collapses the threshold to 1 byte, which
    would misreport every real archive as MB.
    """
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "file.txt").write_text("hello world")

    out = str(tmp_path / "out.zip")
    archive_course(str(course_dir), output=out, export_html=False)

    output = capsys.readouterr().out
    assert "KB" in output
    assert "MB" not in output


def test_archive_exports_pdf_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import archive_course

    course = tmp_path / "course"
    course.mkdir()
    (course / "lesson.ipynb").write_text("{}")

    def fake_pdf(nb_path: Path, course_path: Path) -> tuple[bool, str]:
        nb_path.with_suffix(".pdf").write_text("%PDF-fake")
        return True, ""

    with patch(
        "setup_course_github.archive_course._export_notebook_to_html",
        return_value=False,
    ):
        with patch(
            "setup_course_github.archive_course._export_notebook_to_pdf",
            side_effect=fake_pdf,
        ) as mock_pdf:
            archive_course(str(course), output=str(tmp_path / "out.zip"))
    assert mock_pdf.called
    out = capsys.readouterr().out
    assert "PDF exports: 1" in out


def test_archive_no_pdf_skips_export(tmp_path: Path) -> None:
    from setup_course_github.archive_course import archive_course

    course = tmp_path / "course"
    course.mkdir()
    (course / "lesson.ipynb").write_text("{}")
    with patch(
        "setup_course_github.archive_course._export_notebook_to_html",
        return_value=False,
    ):
        with patch(
            "setup_course_github.archive_course._export_notebook_to_pdf"
        ) as mock_pdf:
            archive_course(
                str(course), output=str(tmp_path / "out.zip"), export_pdf=False
            )
    mock_pdf.assert_not_called()


def test_archive_summary_lists_pdf_next_to_notebook(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import archive_course

    course = tmp_path / "course"
    course.mkdir()
    (course / "lesson.ipynb").write_text("{}")

    def fake_pdf(nb_path: Path, course_path: Path) -> tuple[bool, str]:
        nb_path.with_suffix(".pdf").write_text("%PDF-fake")
        return True, ""

    with patch(
        "setup_course_github.archive_course._export_notebook_to_html",
        return_value=False,
    ):
        with patch(
            "setup_course_github.archive_course._export_notebook_to_pdf",
            side_effect=fake_pdf,
        ):
            archive_course(str(course), output=str(tmp_path / "out.zip"))
    out = capsys.readouterr().out
    assert "lesson.ipynb + lesson.pdf" in out
    # the pdf must not be reported under "Other files"
    assert "Other files:" not in out


def test_archive_main_passes_no_pdf(tmp_path: Path) -> None:
    from setup_course_github.archive_course import main

    course = tmp_path / "course"
    course.mkdir()
    with patch("setup_course_github.archive_course.archive_course") as mock_archive:
        with patch("sys.argv", ["archive-course", "--no-pdf", str(course)]):
            main()
    mock_archive.assert_called_once_with(
        dirname=str(course),
        output=None,
        export_html=True,
        export_pdf=False,
        max_size=10.0,
        keep_all=False,
    )


def test_archive_pdf_export_count_accumulates_across_notebooks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two successful PDF exports are counted as 2, not reset to 1.

    Pins ``pdf_exported += 1`` against a mutation to ``pdf_exported = 1``,
    which a single-notebook test cannot distinguish (1 == 1).
    """
    course = tmp_path / "course"
    course.mkdir()
    (course / "lesson1.ipynb").write_text("{}")
    (course / "lesson2.ipynb").write_text("{}")

    with patch(
        "setup_course_github.archive_course._export_notebook_to_html",
        return_value=False,
    ):
        with patch(
            "setup_course_github.archive_course._export_notebook_to_pdf",
            return_value=(True, ""),
        ):
            archive_course(str(course), output=str(tmp_path / "out.zip"))

    assert "PDF exports: 2" in capsys.readouterr().out


def test_archive_failed_pdf_export_not_counted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When every PDF export fails, no 'PDF exports' line appears.

    Pins ``if export_pdf and pdf_exported > 0`` against mutations to
    ``>= 0`` (which would print ``PDF exports: 0``) and to ``or`` (which
    would print even though PDF export was requested but produced nothing).
    """
    course = tmp_path / "course"
    course.mkdir()
    (course / "lesson.ipynb").write_text("{}")

    with patch(
        "setup_course_github.archive_course._export_notebook_to_html",
        return_value=False,
    ):
        with patch(
            "setup_course_github.archive_course._export_notebook_to_pdf",
            return_value=(False, ""),
        ):
            archive_course(str(course), output=str(tmp_path / "out.zip"))

    assert "PDF exports:" not in capsys.readouterr().out


def test_archive_no_pdf_ignores_existing_pdf_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With export_pdf=False, an existing .pdf on disk is not paired in summary.

    Pins ``if export_pdf and pdf_path.exists()`` against a mutation to
    ``or``, which would pair a stray .pdf even though PDF export was off.
    """
    course = tmp_path / "course"
    course.mkdir()
    (course / "lesson.ipynb").write_text("{}")
    (course / "lesson.pdf").write_text("%PDF-fake")

    archive_course(
        str(course),
        output=str(tmp_path / "out.zip"),
        export_html=False,
        export_pdf=False,
    )

    output = capsys.readouterr().out
    assert "lesson.ipynb + lesson.pdf" not in output
    assert "lesson.ipynb" in output


def test_last_error_line_returns_last_nonblank() -> None:
    from setup_course_github.archive_course import _last_error_line

    assert _last_error_line("first\nRuntimeError: boom\n\n") == "RuntimeError: boom"
    assert _last_error_line("   ") == ""
    assert _last_error_line("") == ""


def test_pdf_failure_kind_lib() -> None:
    from setup_course_github.archive_course import _pdf_failure_kind

    assert (
        _pdf_failure_kind("ModuleNotFoundError: No module named 'playwright'") == "lib"
    )
    assert _pdf_failure_kind("Please install `nbconvert[webpdf]` to enable.") == "lib"
    assert (
        _pdf_failure_kind("Playwright is not installed to support Web PDF conversion")
        == "lib"
    )


def test_pdf_failure_kind_chromium() -> None:
    from setup_course_github.archive_course import _pdf_failure_kind

    assert _pdf_failure_kind("Executable doesn't exist at /x/chromium") == "chromium"
    assert _pdf_failure_kind("please run: playwright install") == "chromium"
    assert _pdf_failure_kind("download new browsers") == "chromium"


def test_pdf_failure_kind_other_and_priority() -> None:
    from setup_course_github.archive_course import _pdf_failure_kind

    assert _pdf_failure_kind("some unrelated error") == "other"
    # lib signal wins even if a chromium phrase is also present
    assert (
        _pdf_failure_kind("No module named 'playwright'; try playwright install")
        == "lib"
    )


# ---------------------------------------------------------------------------
# size guard: measuring each member's contribution
# ---------------------------------------------------------------------------


def test_member_contributions_reports_compressed_sizes(tmp_path: Path) -> None:
    """Each member maps to its compressed size as stored in the zip."""
    zip_path = tmp_path / "a.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("c/small.txt", "x")
        zf.writestr("c/big.csv", "a,b,c\n" * 20000)

    contributions = _member_contributions(zip_path)

    assert set(contributions) == {"c/small.txt", "c/big.csv"}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            assert contributions[info.filename] == info.compress_size


def test_member_contributions_measures_compressed_not_raw(tmp_path: Path) -> None:
    """A highly compressible member contributes far less than its raw size."""
    raw = "a,b,c\n" * 50000
    zip_path = tmp_path / "a.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("c/big.csv", raw)

    contributions = _member_contributions(zip_path)

    assert contributions["c/big.csv"] < len(raw) / 10


# ---------------------------------------------------------------------------
# size guard: ranking the candidates worth asking about
# ---------------------------------------------------------------------------


def test_size_candidates_ranks_largest_first() -> None:
    """Candidates come back ordered by contribution, biggest first."""
    contributions = {"a.csv": 300_000, "b.csv": 900_000, "c.csv": 600_000}

    assert _size_candidates(contributions, 10 * 1024 * 1024) == [
        ("b.csv", 900_000),
        ("c.csv", 600_000),
        ("a.csv", 300_000),
    ]


def test_size_candidates_breaks_ties_by_name() -> None:
    """Equal contributions are ordered by name, so the walk is deterministic."""
    contributions = {"z.csv": 500_000, "a.csv": 500_000, "m.csv": 500_000}

    assert [name for name, _ in _size_candidates(contributions, 10 * 1024 * 1024)] == [
        "a.csv",
        "m.csv",
        "z.csv",
    ]


def test_size_candidates_skips_files_too_small_to_help() -> None:
    """A file under 1% of the limit cannot close an overage, so it is not offered."""
    limit = 10 * 1024 * 1024
    floor = limit // 100
    contributions = {"big.csv": 5_000_000, "tiny.txt": floor - 1, "edge.txt": floor}

    assert _size_candidates(contributions, limit) == [
        ("big.csv", 5_000_000),
        ("edge.txt", floor),
    ]


def test_size_candidates_empty_when_nothing_is_big_enough() -> None:
    """Many small files yield no candidates -- dropping files is the wrong fix."""
    contributions = {f"f{i}.txt": 100 for i in range(50)}

    assert _size_candidates(contributions, 10 * 1024 * 1024) == []


def test_size_candidates_floor_is_at_least_one_byte() -> None:
    """A tiny limit must not make the floor zero and admit empty files."""
    contributions = {"empty.txt": 0, "some.txt": 1}

    assert _size_candidates(contributions, 10) == [("some.txt", 1)]


# ---------------------------------------------------------------------------
# size guard: human-readable sizes
# ---------------------------------------------------------------------------


def test_format_size_uses_kb_below_one_megabyte() -> None:
    """Sub-megabyte sizes read in KB with one decimal."""
    assert _format_size(1536) == "1.5 KB"
    assert _format_size(1024 * 1024 - 1) == "1024.0 KB"


def test_format_size_uses_mb_from_one_megabyte_up() -> None:
    """A full megabyte and above reads in MB."""
    assert _format_size(1024 * 1024) == "1.0 MB"
    assert _format_size(3 * 1024 * 1024 + 512 * 1024) == "3.5 MB"


# ---------------------------------------------------------------------------
# size guard: walking the candidates
# ---------------------------------------------------------------------------


def test_choose_drops_stops_as_soon_as_under_the_limit() -> None:
    """One oversized file is one question, even with other candidates behind it."""
    asked: list[str] = []

    def ask(name: str, size: int, projected: int) -> bool:
        asked.append(name)
        return True

    dropped = _choose_drops(
        [("huge.csv", 8_000_000), ("big.csv", 2_000_000), ("mid.csv", 1_000_000)],
        total=12_000_000,
        limit=10_000_000,
        ask=ask,
    )

    assert dropped == ["huge.csv"]
    assert asked == ["huge.csv"]


def test_choose_drops_moves_on_when_a_file_is_kept() -> None:
    """Declining the biggest file offers the next one instead."""

    def ask(name: str, size: int, projected: int) -> bool:
        return name != "huge.csv"

    dropped = _choose_drops(
        [("huge.csv", 8_000_000), ("big.csv", 3_000_000), ("mid.csv", 1_000_000)],
        total=12_000_000,
        limit=10_000_000,
        ask=ask,
    )

    assert dropped == ["big.csv"]


def test_choose_drops_keeps_asking_until_the_overage_is_closed() -> None:
    """Several medium files can add up to the needed saving."""

    def ask(name: str, size: int, projected: int) -> bool:
        return True

    dropped = _choose_drops(
        [("a.csv", 2_000_000), ("b.csv", 2_000_000), ("c.csv", 2_000_000)],
        total=13_000_000,
        limit=10_000_000,
        ask=ask,
    )

    assert dropped == ["a.csv", "b.csv"]


def test_choose_drops_returns_nothing_when_everything_is_kept() -> None:
    """Declining every candidate drops nothing and still terminates."""
    asked: list[str] = []

    def ask(name: str, size: int, projected: int) -> bool:
        asked.append(name)
        return False

    dropped = _choose_drops(
        [("a.csv", 2_000_000), ("b.csv", 2_000_000)],
        total=11_000_000,
        limit=10_000_000,
        ask=ask,
    )

    assert dropped == []
    assert asked == ["a.csv", "b.csv"]


def test_choose_drops_asks_nothing_when_already_under_the_limit() -> None:
    """A small archive is never questioned, however many candidates it has."""

    def ask(name: str, size: int, projected: int) -> bool:  # pragma: no cover
        raise AssertionError("should not ask about an archive already under the limit")

    assert (
        _choose_drops(
            [("a.csv", 2_000_000)], total=5_000_000, limit=10_000_000, ask=ask
        )
        == []
    )


def test_choose_drops_reports_the_projected_size_after_each_drop() -> None:
    """The question carries the size the archive would become, so the effect shows."""
    seen: list[tuple[str, int, int]] = []

    def ask(name: str, size: int, projected: int) -> bool:
        seen.append((name, size, projected))
        return False

    _choose_drops(
        [("a.csv", 2_000_000), ("b.csv", 1_000_000)],
        total=11_000_000,
        limit=10_000_000,
        ask=ask,
    )

    assert seen == [
        ("a.csv", 2_000_000, 9_000_000),
        ("b.csv", 1_000_000, 10_000_000),
    ]


# ---------------------------------------------------------------------------
# size guard: the interactive question
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("answer", ["y", "Y", "yes", " y "])
def test_ask_to_drop_accepts_yes(
    answer: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An explicit yes drops the file."""
    monkeypatch.setattr("builtins.input", lambda _: answer)

    assert _ask_to_drop("c/data/big.csv", 8 * 1024 * 1024, 4 * 1024 * 1024) is True


@pytest.mark.parametrize("answer", ["", "n", "no", "maybe", "q"])
def test_ask_to_drop_keeps_on_anything_else(
    answer: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keeping the file is the default: only an explicit yes drops it."""
    monkeypatch.setattr("builtins.input", lambda _: answer)

    assert _ask_to_drop("c/data/big.csv", 8 * 1024 * 1024, 4 * 1024 * 1024) is False


def test_ask_to_drop_shows_size_and_projected_total(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The question names the file, its weight, and the resulting archive size."""
    monkeypatch.setattr("builtins.input", lambda _: "n")

    _ask_to_drop("c/data/big.csv", 8 * 1024 * 1024, 4 * 1024 * 1024)

    out = capsys.readouterr().out
    assert "c/data/big.csv" in out
    assert "8.0 MB" in out
    assert "4.0 MB" in out


def test_ask_to_drop_keeps_file_when_stdin_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A closed stdin must not crash the archive; the file is kept."""

    def closed(_: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", closed)

    assert _ask_to_drop("c/data/big.csv", 8 * 1024 * 1024, 4 * 1024 * 1024) is False


# ---------------------------------------------------------------------------
# size guard: wired into archive_course
# ---------------------------------------------------------------------------


def _course_with_big_file(tmp_path: Path) -> Path:
    """A course dir whose data file dwarfs its lesson, for size-guard tests."""
    course_dir = tmp_path / "mycourse"
    (course_dir / "data").mkdir(parents=True)
    (course_dir / "lesson.txt").write_text("hello")
    # Random bytes so deflate cannot shrink it away.
    (course_dir / "data" / "big.csv").write_bytes(os.urandom(40_000))
    return course_dir


def test_archive_under_the_limit_says_nothing_about_size(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A normal archive never mentions the limit."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.txt").write_text("hello")

    archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
    )

    assert "over the" not in capsys.readouterr().out


def test_archive_over_the_limit_without_a_terminal_keeps_everything(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scripts and CI are never blocked on a question; they get a warning."""
    course_dir = _course_with_big_file(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    zip_path = archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
        max_size=0.01,
    )

    out = capsys.readouterr().out
    assert "over the" in out
    assert "not running interactively" in out.lower()
    with zipfile.ZipFile(zip_path) as zf:
        assert "mycourse/data/big.csv" in zf.namelist()


def test_archive_keep_all_reports_but_does_not_ask(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """--keep-all still flags an oversized archive, it just asks nothing."""
    course_dir = _course_with_big_file(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("should not ask"))

    zip_path = archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
        max_size=0.01,
        keep_all=True,
    )

    out = capsys.readouterr().out
    assert "over the" in out
    assert "--keep-all" in out
    with zipfile.ZipFile(zip_path) as zf:
        assert "mycourse/data/big.csv" in zf.namelist()


def test_archive_drops_the_file_when_asked_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Saying yes rewrites the archive without that file, and it really shrinks."""
    course_dir = _course_with_big_file(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "y")

    zip_path = archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
        max_size=0.01,
    )

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert "mycourse/data/big.csv" not in names
    assert "mycourse/lesson.txt" in names
    assert zip_path.stat().st_size < 10 * 1024


def test_archive_declining_keeps_the_file_and_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Declining every offer leaves the archive intact and over the limit."""
    course_dir = _course_with_big_file(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    zip_path = archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
        max_size=0.01,
    )

    with zipfile.ZipFile(zip_path) as zf:
        assert "mycourse/data/big.csv" in zf.namelist()
    assert "still over the limit" in capsys.readouterr().out


def test_archive_max_size_zero_disables_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """max_size=0 turns the guard off entirely."""
    course_dir = _course_with_big_file(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("should not ask"))

    archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
        max_size=0,
    )

    assert "over the" not in capsys.readouterr().out


def test_archive_many_small_files_over_the_limit_offers_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no one file is big enough to help, dropping files is the wrong fix."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    for i in range(150):
        (course_dir / f"f{i}.bin").write_bytes(os.urandom(60))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("should not ask"))

    archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
        max_size=0.01,
    )

    assert "no single file" in capsys.readouterr().out.lower()


def test_main_passes_max_size(tmp_path: Path) -> None:
    """--max-size overrides the default mail-friendly ceiling."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()

    with patch("setup_course_github.archive_course.archive_course") as mock_archive:
        with patch("sys.argv", ["archive-course", str(course_dir), "--max-size", "25"]):
            main()

    assert mock_archive.call_args.kwargs["max_size"] == 25.0


def test_main_max_size_zero_passes_through(tmp_path: Path) -> None:
    """--max-size 0 reaches archive_course as the off switch."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()

    with patch("setup_course_github.archive_course.archive_course") as mock_archive:
        with patch("sys.argv", ["archive-course", str(course_dir), "--max-size", "0"]):
            main()

    assert mock_archive.call_args.kwargs["max_size"] == 0.0


def test_main_passes_keep_all(tmp_path: Path) -> None:
    """--keep-all reaches archive_course."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()

    with patch("setup_course_github.archive_course.archive_course") as mock_archive:
        with patch("sys.argv", ["archive-course", str(course_dir), "--keep-all"]):
            main()

    assert mock_archive.call_args.kwargs["keep_all"] is True


# ---------------------------------------------------------------------------
# size guard: reporting what was left out
# ---------------------------------------------------------------------------


def test_archive_summary_names_the_files_left_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The summary records every omission, so nothing vanishes quietly."""
    course_dir = _course_with_big_file(tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "y")

    archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
        max_size=0.01,
    )

    out = capsys.readouterr().out
    assert "Left out (too big to email):" in out
    assert "mycourse/data/big.csv" in out.split("Left out (too big to email):")[1]


def test_archive_summary_omits_the_section_when_nothing_was_dropped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A normal archive has no omissions section."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.txt").write_text("hello")

    archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
    )

    assert "Left out" not in capsys.readouterr().out


def test_choose_drops_stops_when_no_combination_can_help(tmp_path: Path) -> None:
    """Once the remaining candidates cannot close the gap, stop asking.

    Declining the one big file leaves questions that are arithmetically
    pointless -- dropping everything still left would not get under the limit.
    """
    asked: list[str] = []

    def ask(name: str, size: int, projected: int) -> bool:
        asked.append(name)
        return False

    dropped = _choose_drops(
        [("huge.csv", 4_500_000), ("small.csv", 76_000), ("tiny.csv", 40_000)],
        total=4_600_000,
        limit=3_000_000,
        ask=ask,
    )

    assert dropped == []
    assert asked == ["huge.csv"]


def test_choose_drops_still_asks_when_candidates_can_combine(tmp_path: Path) -> None:
    """Several files that together close the gap are all still worth offering."""
    asked: list[str] = []

    def ask(name: str, size: int, projected: int) -> bool:
        asked.append(name)
        return name != "huge.csv"

    dropped = _choose_drops(
        [("huge.csv", 4_000_000), ("a.csv", 900_000), ("b.csv", 900_000)],
        total=4_600_000,
        limit=3_000_000,
        ask=ask,
    )

    assert dropped == ["a.csv", "b.csv"]
    assert asked == ["huge.csv", "a.csv", "b.csv"]


# ---------------------------------------------------------------------------
# size guard: boundaries and units
# ---------------------------------------------------------------------------


def test_choose_drops_treats_the_limit_itself_as_acceptable() -> None:
    """An archive sitting exactly on the limit is fine, not one byte too big."""

    def ask(name: str, size: int, projected: int) -> bool:  # pragma: no cover
        raise AssertionError("an archive exactly at the limit must not be questioned")

    assert (
        _choose_drops(
            [("a.csv", 2_000_000)], total=10_000_000, limit=10_000_000, ask=ask
        )
        == []
    )


def test_apply_size_guard_accepts_an_archive_exactly_at_the_limit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A zip whose size equals the limit passes silently."""
    course_dir = _course_with_big_file(tmp_path)
    members = _archive_members(course_dir)
    zip_path = tmp_path / "c.zip"
    _write_zip(zip_path, members)

    dropped = _apply_size_guard(
        zip_path, members, limit=zip_path.stat().st_size, keep_all=False
    )

    assert dropped == []
    assert capsys.readouterr().out == ""


def test_apply_size_guard_catches_an_archive_one_byte_over(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One byte over the limit is over the limit."""
    course_dir = _course_with_big_file(tmp_path)
    members = _archive_members(course_dir)
    zip_path = tmp_path / "c.zip"
    _write_zip(zip_path, members)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)

    _apply_size_guard(
        zip_path, members, limit=zip_path.stat().st_size - 1, keep_all=False
    )

    assert "over the" in capsys.readouterr().out


def test_format_size_counts_a_megabyte_as_1024_squared_bytes() -> None:
    """Sizes are in MiB, matching how every file manager reports them."""
    assert _format_size(100 * 1024 * 1024) == "100.0 MB"
    assert _format_size(100 * 1024) == "100.0 KB"


def test_archive_max_size_is_in_mebibytes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """--max-size 1 means 1 MiB: an archive of 1,020,000 bytes is under it.

    Were the limit read as 1,000,000 bytes this archive would be over it, so
    this pins the unit the documentation promises.
    """
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "data.bin").write_bytes(os.urandom(1_020_000))
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("should not ask"))

    zip_path = archive_course(
        str(course_dir),
        output=str(tmp_path / "c.zip"),
        export_html=False,
        export_pdf=False,
        max_size=1,
    )

    assert 1_000_000 < zip_path.stat().st_size < 1024 * 1024
    assert "over the" not in capsys.readouterr().out


def test_archive_defaults_to_a_ten_megabyte_ceiling() -> None:
    """The documented default lives in three places; pin the one in the API."""
    assert inspect.signature(archive_course).parameters["max_size"].default == 10.0


def test_megabytes_to_bytes_uses_binary_megabytes() -> None:
    """One MB is 1024*1024 bytes, the unit file managers and mail clients show."""
    assert _megabytes_to_bytes(1) == 1_048_576
    assert _megabytes_to_bytes(10) == 10_485_760
    assert _megabytes_to_bytes(7.5) == 7_864_320
    assert _megabytes_to_bytes(0) == 0
