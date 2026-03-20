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
        ["uv", "run", "jupyter", "nbconvert", "--to", "html", str(nb_file)],
        cwd=str(course_dir),
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
