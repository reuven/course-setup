from pathlib import Path

from setup_course_github.notebooks import (
    date_range,
    find_notebooks,
    is_marimo_notebook,
)

MARIMO_SOURCE = "import marimo\n\napp = marimo.App()\n"


def test_is_marimo_notebook_true(tmp_path: Path) -> None:
    p = tmp_path / "nb.py"
    p.write_text(MARIMO_SOURCE)
    assert is_marimo_notebook(p) is True


def test_is_marimo_notebook_false_plain_python(tmp_path: Path) -> None:
    p = tmp_path / "script.py"
    p.write_text("print('hello')\n")
    assert is_marimo_notebook(p) is False


def test_is_marimo_notebook_false_on_unreadable(tmp_path: Path) -> None:
    missing = tmp_path / "nope.py"
    assert is_marimo_notebook(missing) is False


def test_find_notebooks_separates_ipynb_and_marimo(tmp_path: Path) -> None:
    (tmp_path / "a.ipynb").write_text("{}")
    (tmp_path / "b.ipynb").write_text("{}")
    (tmp_path / "m.py").write_text(MARIMO_SOURCE)
    (tmp_path / "plain.py").write_text("x = 1\n")
    ipynb, marimo = find_notebooks(tmp_path)
    assert [p.name for p in ipynb] == ["a.ipynb", "b.ipynb"]
    assert [p.name for p in marimo] == ["m.py"]


def test_date_range_from_filenames(tmp_path: Path) -> None:
    files = [
        tmp_path / "lesson-2026-03-15.ipynb",
        tmp_path / "lesson-2026-03-01.ipynb",
    ]
    assert date_range(files) == "2026-03-01 → 2026-03-15"


def test_date_range_na_when_no_dates(tmp_path: Path) -> None:
    files = [tmp_path / "intro.ipynb"]
    assert date_range(files) == "n/a"
