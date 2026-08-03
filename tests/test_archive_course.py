import subprocess
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from setup_course_github.archive_course import archive_course, main

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
        result = _export_notebook_to_pdf(nb, course)
    assert result is True
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


def test_export_notebook_to_pdf_handles_called_process_error(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _export_notebook_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nb = course / "lesson.ipynb"
    nb.write_text("{}")
    err = subprocess.CalledProcessError(1, "nbconvert", stderr=b"chromium missing")
    with patch("subprocess.run", side_effect=err):
        result = _export_notebook_to_pdf(nb, course)
    assert result is False


def test_export_notebook_to_pdf_handles_missing_binary(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _export_notebook_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nb = course / "lesson.ipynb"
    nb.write_text("{}")
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        result = _export_notebook_to_pdf(nb, course)
    assert result is False


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

    def fake_pdf(nb_path: Path, course_path: Path) -> bool:
        nb_path.with_suffix(".pdf").write_text("%PDF-fake")
        return True

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

    def fake_pdf(nb_path: Path, course_path: Path) -> bool:
        nb_path.with_suffix(".pdf").write_text("%PDF-fake")
        return True

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
        dirname=str(course), output=None, export_html=True, export_pdf=False
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
            return_value=True,
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
            return_value=False,
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
