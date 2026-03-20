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

    zip_path = archive_course(str(course_dir), export_html=False)

    assert zip_path.exists()
    assert zip_path.suffix == ".zip"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "mycourse/file1.txt" in names
        assert "mycourse/file2.txt" in names


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

    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        archive_course(str(course_dir), export_html=True)

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

    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        archive_course(str(course_dir), export_html=False)

    mock_run.assert_not_called()


def test_archive_zip_contains_html(tmp_path: Path) -> None:
    """After HTML export (mocked), verify the zip includes .html files."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "lesson.ipynb").write_text('{"cells": []}')
    # Simulate the HTML file that nbconvert would create
    (course_dir / "lesson.html").write_text("<html></html>")

    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        zip_path = archive_course(str(course_dir), export_html=True)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "mycourse/lesson.html" in names
        assert "mycourse/lesson.ipynb" in names


def test_archive_no_notebooks_skips_html(tmp_path: Path) -> None:
    """Directory with no .ipynb files, no nbconvert call."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "readme.txt").write_text("no notebooks here")

    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        archive_course(str(course_dir), export_html=True)

    mock_run.assert_not_called()


def test_archive_prints_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify stdout includes zip filename and file count."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    (course_dir / "file1.txt").write_text("hello")
    (course_dir / "file2.txt").write_text("world")

    zip_path = archive_course(str(course_dir), export_html=False)

    captured = capsys.readouterr()
    assert str(zip_path) in captured.out
    assert "Files: 2" in captured.out


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

    zip_path = archive_course(str(course_dir), export_html=False)

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

    with patch(
        "setup_course_github.archive_course.subprocess.run", side_effect=fail_nbconvert
    ):
        zip_path = archive_course(str(course_dir), export_html=True)

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

    with patch(
        "setup_course_github.archive_course.subprocess.run", side_effect=raise_not_found
    ):
        zip_path = archive_course(str(course_dir), export_html=True)

    assert zip_path.exists()
    output = capsys.readouterr().out
    assert "jupyter nbconvert not found" in output


def test_archive_notebook_with_spaces_in_name(tmp_path: Path) -> None:
    """Notebooks with spaces in filenames are handled correctly."""
    course_dir = tmp_path / "mycourse"
    course_dir.mkdir()
    nb_file = course_dir / "My Notebook - Day 1.ipynb"
    nb_file.write_text('{"cells": []}')

    mock_run = MagicMock()
    with patch("setup_course_github.archive_course.subprocess.run", mock_run):
        archive_course(str(course_dir), export_html=True)

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
