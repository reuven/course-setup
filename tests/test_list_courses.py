from pathlib import Path
from unittest.mock import patch

import pytest

from setup_course_github.config import CourseConfig
from setup_course_github.list_courses import (
    _matches_names,
    archive_summary_line,
    course_summary_line,
    filter_active,
    filter_archived,
    find_active_courses,
    find_archived_courses,
    is_archived_course,
    is_course,
    main,
    resolve_scan_dirs,
)

MARIMO_SOURCE = "import marimo\n\napp = marimo.App()\n"


def _make_course(parent: Path, name: str, notebook: str = "lesson.ipynb") -> Path:
    course = parent / name
    course.mkdir(parents=True)
    (course / ".git").mkdir()
    (course / notebook).write_text("{}")
    return course


def test_is_course_true_with_git_and_notebook(tmp_path: Path) -> None:
    course = _make_course(tmp_path, "algebra")
    assert is_course(course) is True


def test_is_course_false_git_without_notebook(tmp_path: Path) -> None:
    course = tmp_path / "empty"
    course.mkdir()
    (course / ".git").mkdir()
    assert is_course(course) is False


def test_is_course_false_notebook_without_git(tmp_path: Path) -> None:
    course = tmp_path / "loose"
    course.mkdir()
    (course / "lesson.ipynb").write_text("{}")
    assert is_course(course) is False


def test_is_course_true_with_marimo_notebook(tmp_path: Path) -> None:
    course = tmp_path / "marimo-course"
    course.mkdir()
    (course / ".git").mkdir()
    (course / "nb.py").write_text(MARIMO_SOURCE)
    assert is_course(course) is True


def test_course_summary_line_counts_and_dates(tmp_path: Path) -> None:
    course = tmp_path / "python-intro"
    course.mkdir()
    (course / "lesson-2026-03-01.ipynb").write_text("{}")
    (course / "lesson-2026-03-08.ipynb").write_text("{}")
    line = course_summary_line(course)
    assert line == "python-intro — 2 notebooks (2026-03-01 → 2026-03-08)"


def test_course_summary_line_sums_ipynb_and_marimo(tmp_path: Path) -> None:
    """Count is ipynb + marimo, not a difference.

    Pins ``len(ipynb_files) + len(marimo_files)`` against a mutation to
    ``-``: a course with one of each must report 2, which ``1 - 1 == 0``
    would fail. A single-kind course cannot distinguish the operators.
    """
    course = tmp_path / "mixed"
    course.mkdir()
    (course / "lesson.ipynb").write_text("{}")
    (course / "nb.py").write_text(MARIMO_SOURCE)
    line = course_summary_line(course)
    assert "— 2 notebooks" in line


def test_resolve_scan_dirs_cli_overrides_config() -> None:
    config = CourseConfig(
        github_token="t",
        archive_path=Path("/tmp/archive"),
        default_notebook_type="jupyter",
        course_dirs=["/from/config"],
    )
    result = resolve_scan_dirs(["/from/cli"], config)
    assert result == [Path("/from/cli")]


def test_resolve_scan_dirs_uses_config_when_no_cli() -> None:
    config = CourseConfig(
        github_token="t",
        archive_path=Path("/tmp/archive"),
        default_notebook_type="jupyter",
        course_dirs=["~/Courses/Current"],
    )
    result = resolve_scan_dirs([], config)
    assert result == [Path("~/Courses/Current").expanduser()]


def test_resolve_scan_dirs_falls_back_to_cwd() -> None:
    config = CourseConfig(
        github_token="t",
        archive_path=Path("/tmp/archive"),
        default_notebook_type="jupyter",
    )
    result = resolve_scan_dirs([], config)
    assert result == [Path(".")]


def test_find_active_courses_skips_non_courses(tmp_path: Path) -> None:
    _make_course(tmp_path, "real-course")
    (tmp_path / "not-a-course").mkdir()
    result = find_active_courses([tmp_path])
    assert [p.name for p in result] == ["real-course"]


def test_find_active_courses_skips_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    assert find_active_courses([missing]) == []


def test_find_archived_courses_grouped_by_year(tmp_path: Path) -> None:
    _make_course(tmp_path / "2025", "old-course")
    _make_course(tmp_path / "2026", "newer-course")
    result = find_archived_courses(tmp_path)
    assert list(result.keys()) == ["2025", "2026"]
    assert [p.name for p in result["2026"]] == ["newer-course"]


def test_find_archived_courses_missing_archive(tmp_path: Path) -> None:
    missing = tmp_path / "no-archive"
    assert find_archived_courses(missing) == {}


def test_find_archived_courses_ignores_non_year_dirs(tmp_path: Path) -> None:
    _make_course(tmp_path / "2026", "real-course")
    _make_course(tmp_path / "build", "not-a-year")  # non-year top-level dir
    (tmp_path / "README.txt").write_text("stray file")
    result = find_archived_courses(tmp_path)
    assert list(result.keys()) == ["2026"]


def test_find_archived_courses_skips_junk_and_zero_notebook_dirs(
    tmp_path: Path,
) -> None:
    year = tmp_path / "2024"
    _make_course(year, "real-course")
    (year / ".git").mkdir(parents=True)  # hidden
    (year / ".ipynb_checkpoints").mkdir()  # hidden
    (year / "__pycache__").mkdir()  # junk name
    (year / "empty-course").mkdir()  # a dir with no notebooks
    result = find_archived_courses(tmp_path)
    assert [p.name for p in result["2024"]] == ["real-course"]


def test_is_archived_course_requires_notebook_not_git(tmp_path: Path) -> None:
    # No .git required for an archived course, but a notebook IS required.
    with_nb = tmp_path / "has-nb"
    with_nb.mkdir()
    (with_nb / "lesson.ipynb").write_text("{}")
    assert is_archived_course(with_nb) is True

    without_nb = tmp_path / "no-nb"
    without_nb.mkdir()
    assert is_archived_course(without_nb) is False


def test_is_archived_course_rejects_junk_and_hidden_names(tmp_path: Path) -> None:
    for name in ("__pycache__", ".ipynb_checkpoints", ".git"):
        d = tmp_path / name
        d.mkdir()
        (d / "lesson.ipynb").write_text("{}")  # even with a notebook
        assert is_archived_course(d) is False


def _config_for(archive: Path, course_dirs: list[str]) -> CourseConfig:
    return CourseConfig(
        github_token="t",
        archive_path=archive,
        default_notebook_type="jupyter",
        course_dirs=course_dirs,
    )


def test_main_lists_active_and_archived(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    _make_course(archive / "2026", "gone-course")

    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses"]):
            main()
    out = capsys.readouterr().out
    assert "Active courses:" in out
    assert "live-course" in out
    assert "Archived courses:" in out
    assert "2026" in out
    assert "gone-course" in out


def test_main_no_active_courses_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [str(empty)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses"]):
            main()
    out = capsys.readouterr().out
    assert "No active courses found" in out
    assert "No archived courses found" in out


def test_main_cli_dirs_override(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli_root = tmp_path / "cli"
    cli_root.mkdir()
    _make_course(cli_root, "cli-course")
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, ["/unused/config/path"])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", str(cli_root)]):
            main()
    out = capsys.readouterr().out
    assert "cli-course" in out


def test_matches_names_empty_patterns_matches_all() -> None:
    assert _matches_names("anything", []) is True


def test_matches_names_case_insensitive_substring() -> None:
    assert _matches_names("Cisco-2024-Python", ["cisco"]) is True
    assert _matches_names("Cisco-2024-Python", ["CISCO"]) is True
    assert _matches_names("Apple-2024", ["cisco"]) is False


def test_matches_names_multiple_patterns_or() -> None:
    assert _matches_names("Apple-2024", ["cisco", "apple"]) is True
    assert _matches_names("Google-2024", ["cisco", "apple"]) is False


def test_filter_active_keeps_only_matches(tmp_path: Path) -> None:
    a = tmp_path / "Cisco-A"
    b = tmp_path / "Apple-B"
    result = filter_active([a, b], ["cisco"])
    assert [p.name for p in result] == ["Cisco-A"]


def test_filter_archived_by_year(tmp_path: Path) -> None:
    archived = {
        "2024": [tmp_path / "2024" / "c1"],
        "2025": [tmp_path / "2025" / "c2"],
    }
    result = filter_archived(archived, ["2024"], [])
    assert list(result.keys()) == ["2024"]


def test_filter_archived_by_multiple_years(tmp_path: Path) -> None:
    archived = {
        "2023": [tmp_path / "2023" / "a"],
        "2024": [tmp_path / "2024" / "b"],
        "2025": [tmp_path / "2025" / "c"],
    }
    result = filter_archived(archived, ["2023", "2025"], [])
    assert sorted(result.keys()) == ["2023", "2025"]


def test_filter_archived_by_name_drops_empty_years(tmp_path: Path) -> None:
    archived = {
        "2024": [tmp_path / "2024" / "Cisco-x", tmp_path / "2024" / "Apple-y"],
        "2025": [tmp_path / "2025" / "Apple-z"],
    }
    result = filter_archived(archived, [], ["cisco"])
    assert list(result.keys()) == ["2024"]
    assert [p.name for p in result["2024"]] == ["Cisco-x"]


def test_archive_summary_line_multi_year(tmp_path: Path) -> None:
    archived = {
        "2018": [tmp_path / "a", tmp_path / "b"],
        "2026": [tmp_path / "c"],
    }
    line = archive_summary_line(archived, [])
    assert line == (
        "Archived: 3 courses across 2018–2026 — use --archived to list them."
    )


def test_archive_summary_line_single_year(tmp_path: Path) -> None:
    archived = {"2024": [tmp_path / "a"]}
    line = archive_summary_line(archived, [])
    assert "across 2024 " in line
    assert "–" not in line  # no en-dash range for a single year


def test_archive_summary_line_with_name_filter(tmp_path: Path) -> None:
    archived = {"2024": [tmp_path / "Cisco-a"]}
    line = archive_summary_line(archived, ["cisco"])
    assert line.startswith('Archived: 1 courses matching "cisco" across 2024')


def test_archive_summary_line_none(tmp_path: Path) -> None:
    assert archive_summary_line({}, []) == "Archived: none"


def test_archive_summary_line_none_with_filter(tmp_path: Path) -> None:
    assert archive_summary_line({}, ["cisco"]) == 'Archived: none matching "cisco"'
