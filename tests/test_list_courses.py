from pathlib import Path
from unittest.mock import patch

import pytest

from setup_course_github.config import CourseConfig
from setup_course_github.list_courses import (
    _expand_year_tokens,
    _github_url,
    _matches_names,
    _print_course,
    _year_arg,
    archive_summary_line,
    course_summary_line,
    filter_active,
    filter_archived,
    find_active_courses,
    find_archived_courses,
    github_url,
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


def test_github_url_normalizes_ssh() -> None:
    assert (
        _github_url("git@github.com:reuven/demo.git")
        == "https://github.com/reuven/demo"
    )


def test_github_url_normalizes_https_with_and_without_git() -> None:
    assert (
        _github_url("https://github.com/reuven/demo.git")
        == "https://github.com/reuven/demo"
    )
    assert (
        _github_url("https://github.com/reuven/demo")
        == "https://github.com/reuven/demo"
    )


def test_github_url_normalizes_ssh_scheme_and_trailing_slash() -> None:
    assert (
        _github_url("ssh://git@github.com/reuven/demo.git")
        == "https://github.com/reuven/demo"
    )
    assert (
        _github_url("https://github.com/reuven/demo/")
        == "https://github.com/reuven/demo"
    )


def test_github_url_non_github_or_empty_is_none() -> None:
    assert _github_url("https://gitlab.com/foo/bar.git") is None
    assert _github_url("") is None


def test_github_url_reads_real_repo_remote(tmp_path: Path) -> None:
    import subprocess

    repo = tmp_path / "demo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:reuven/demo.git"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    assert github_url(repo) == "https://github.com/reuven/demo"


def test_github_url_no_remote_is_none(tmp_path: Path) -> None:
    import subprocess

    repo = tmp_path / "norem"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    assert github_url(repo) is None


def test_print_course_indents_summary_and_url(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    course = _make_course(tmp_path, "algebra")
    with patch(
        "setup_course_github.list_courses.github_url",
        return_value="https://github.com/reuven/algebra",
    ):
        _print_course(course, 2, True)
    out = capsys.readouterr().out
    assert out.splitlines() == [
        "  algebra — 1 notebooks (n/a)",
        "    https://github.com/reuven/algebra",
    ]


def test_print_course_no_urls_omits_url_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    course = _make_course(tmp_path, "algebra")
    with patch("setup_course_github.list_courses.github_url") as mock_url:
        _print_course(course, 4, False)
    out = capsys.readouterr().out
    assert out.splitlines() == ["    algebra — 1 notebooks (n/a)"]
    mock_url.assert_not_called()


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
        with patch("sys.argv", ["list-courses", "--no-urls"]):
            main()
    out = capsys.readouterr().out
    assert "Active courses:" in out
    assert "live-course" in out
    # default view: archive is a one-line summary, not an expanded listing
    assert "Archived: 1 course across 2026" in out
    assert "gone-course" not in out


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
    assert "Archived: none" in out


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
        with patch("sys.argv", ["list-courses", "--dir", str(cli_root), "--no-urls"]):
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


def test_year_arg_accepts_single_and_range() -> None:
    assert _year_arg("2024") == "2024"
    assert _year_arg("2020-2022") == "2020-2022"


def test_year_arg_rejects_bad_tokens() -> None:
    import argparse

    for bad in ["24", "2020-", "abcd", "2020-20222", "2020-2021-2022"]:
        with pytest.raises(argparse.ArgumentTypeError):
            _year_arg(bad)


def test_expand_year_tokens_single() -> None:
    years, notes = _expand_year_tokens(["2024"])
    assert years == ["2024"]
    assert notes == []


def test_expand_year_tokens_range_inclusive() -> None:
    years, notes = _expand_year_tokens(["2020-2022"])
    assert years == ["2020", "2021", "2022"]
    assert notes == []


def test_expand_year_tokens_degenerate_range() -> None:
    years, notes = _expand_year_tokens(["2024-2024"])
    assert years == ["2024"]
    assert notes == []


def test_expand_year_tokens_reversed_swaps_with_note() -> None:
    years, notes = _expand_year_tokens(["2022-2020"])
    assert years == ["2020", "2021", "2022"]
    assert notes == ["swapped reversed year range 2022-2020 → 2020-2022"]


def test_expand_year_tokens_mixed_singles_and_ranges() -> None:
    years, notes = _expand_year_tokens(["2019", "2021-2023"])
    assert years == ["2019", "2021", "2022", "2023"]
    assert notes == []


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


def test_archive_summary_line_singular_course(tmp_path: Path) -> None:
    """A single archived course reads 'course', not 'courses'."""
    archived = {"2024": [tmp_path / "only"]}
    line = archive_summary_line(archived, [])
    assert line.startswith("Archived: 1 course across 2024")
    assert "1 courses" not in line


def test_archive_summary_line_plural_two_courses(tmp_path: Path) -> None:
    """Two archived courses read 'courses' (pins the == 1 boundary)."""
    archived = {"2024": [tmp_path / "a", tmp_path / "b"]}
    line = archive_summary_line(archived, [])
    assert line.startswith("Archived: 2 courses across 2024")


def test_archive_summary_line_with_name_filter(tmp_path: Path) -> None:
    archived = {"2024": [tmp_path / "Cisco-a"]}
    line = archive_summary_line(archived, ["cisco"])
    assert line.startswith('Archived: 1 course matching "cisco" across 2024')


def test_archive_summary_line_none(tmp_path: Path) -> None:
    assert archive_summary_line({}, []) == "Archived: none"


def test_archive_summary_line_none_with_filter(tmp_path: Path) -> None:
    assert archive_summary_line({}, ["cisco"]) == 'Archived: none matching "cisco"'


def test_main_archived_flag_expands_listing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    _make_course(archive / "2026", "gone-course")
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--archived", "--no-urls"]):
            main()
    out = capsys.readouterr().out
    assert "Archived courses:" in out
    assert "gone-course" in out
    # --archived suppresses the active section
    assert "live-course" not in out


def test_main_active_flag_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    _make_course(archive / "2026", "gone-course")
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--active", "--no-urls"]):
            main()
    out = capsys.readouterr().out
    assert "live-course" in out
    assert "Archived" not in out


def test_main_name_filter_active_and_archive_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "Cisco-live")
    _make_course(active_root, "Apple-live")
    archive = tmp_path / "archive"
    _make_course(archive / "2026", "Cisco-old")
    _make_course(archive / "2026", "Apple-old")
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "cisco", "--no-urls"]):
            main()
    out = capsys.readouterr().out
    assert "Cisco-live" in out
    assert "Apple-live" not in out
    # bare name search keeps the archive as a name-filtered summary line
    assert 'Archived: 1 course matching "cisco"' in out
    assert "Cisco-old" not in out


def test_main_name_filter_with_archived_expands(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    _make_course(archive / "2025", "Cisco-a")
    _make_course(archive / "2026", "Cisco-b")
    _make_course(archive / "2026", "Apple-c")
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "cisco", "--archived", "--no-urls"]):
            main()
    out = capsys.readouterr().out
    assert "Cisco-a" in out
    assert "Cisco-b" in out
    assert "Apple-c" not in out


def test_main_year_focus_suppresses_active(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    _make_course(archive / "2024", "old-2024")
    _make_course(archive / "2025", "old-2025")
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--year", "2024", "--no-urls"]):
            main()
    out = capsys.readouterr().out
    assert "old-2024" in out
    assert "old-2025" not in out
    assert "live-course" not in out  # active suppressed by --year


def test_main_year_repeatable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    _make_course(archive / "2024", "c-2024")
    _make_course(archive / "2025", "c-2025")
    _make_course(archive / "2026", "c-2026")
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch(
            "sys.argv",
            ["list-courses", "--year", "2024", "--year", "2026", "--no-urls"],
        ):
            main()
    out = capsys.readouterr().out
    assert "c-2024" in out
    assert "c-2026" in out
    assert "c-2025" not in out


def test_main_year_range(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    archive = tmp_path / "archive"
    _make_course(archive / "2020", "c-2020")
    _make_course(archive / "2021", "c-2021")
    _make_course(archive / "2022", "c-2022")
    _make_course(archive / "2023", "c-2023")
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--year", "2021-2022", "--no-urls"]):
            main()
    out = capsys.readouterr().out
    assert "c-2021" in out
    assert "c-2022" in out
    assert "c-2020" not in out
    assert "c-2023" not in out


def test_main_year_mixed_single_and_range(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    for y in ("2019", "2020", "2021", "2022", "2023"):
        _make_course(archive / y, f"c-{y}")
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch(
            "sys.argv",
            ["list-courses", "--year", "2019", "--year", "2021-2022", "--no-urls"],
        ):
            main()
    out = capsys.readouterr().out
    assert "c-2019" in out
    assert "c-2021" in out
    assert "c-2022" in out
    assert "c-2020" not in out
    assert "c-2023" not in out


def test_main_year_reversed_range_prints_note_to_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    _make_course(archive / "2020", "c-2020")
    _make_course(archive / "2021", "c-2021")
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--year", "2021-2020", "--no-urls"]):
            main()
    captured = capsys.readouterr()
    assert "swapped reversed year range 2021-2020 → 2020-2021" in captured.err
    assert "c-2020" in captured.out
    assert "c-2021" in captured.out


def test_main_active_year_shows_active_ignores_year(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    _make_course(archive / "2024", "old-2024")
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch(
            "sys.argv", ["list-courses", "--active", "--year", "2024", "--no-urls"]
        ):
            main()
    out = capsys.readouterr().out
    assert "live-course" in out
    assert "old-2024" not in out


def test_main_shows_github_url_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch(
            "setup_course_github.list_courses.github_url",
            return_value="https://github.com/reuven/live-course",
        ):
            with patch("sys.argv", ["list-courses"]):
                main()
    out = capsys.readouterr().out
    assert "  live-course — " in out
    assert "    https://github.com/reuven/live-course" in out


def test_main_url_placeholder_when_no_remote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("setup_course_github.list_courses.github_url", return_value=None):
            with patch("sys.argv", ["list-courses"]):
                main()
    out = capsys.readouterr().out
    assert "    (no GitHub remote)" in out


def test_main_no_urls_suppresses_url_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch(
            "setup_course_github.list_courses.github_url",
            return_value="https://github.com/reuven/live-course",
        ) as mock_url:
            with patch("sys.argv", ["list-courses", "--no-urls"]):
                main()
    out = capsys.readouterr().out
    assert "live-course" in out
    assert "https://github.com/reuven/live-course" not in out
    assert "(no GitHub remote)" not in out
    mock_url.assert_not_called()


def test_main_archived_url_indented_six_spaces(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    _make_course(archive / "2026", "gone-course")
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch(
            "setup_course_github.list_courses.github_url",
            return_value="https://github.com/reuven/gone-course",
        ):
            with patch("sys.argv", ["list-courses", "--archived"]):
                main()
    out = capsys.readouterr().out
    assert "    gone-course — " in out
    assert "      https://github.com/reuven/gone-course" in out


def test_main_count_prints_no_urls(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("setup_course_github.list_courses.github_url") as mock_url:
            with patch("sys.argv", ["list-courses", "--count"]):
                main()
    mock_url.assert_not_called()


def test_main_count(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "live-course")
    archive = tmp_path / "archive"
    _make_course(archive / "2024", "a")
    _make_course(archive / "2024", "b")
    _make_course(archive / "2025", "c")
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--count"]):
            main()
    out = capsys.readouterr().out
    assert "Active courses: 1" in out
    assert "Archived courses: 3" in out
    assert "2024: 2" in out
    assert "2025: 1" in out


def test_main_name_filter_no_active_match_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    active_root = tmp_path / "current"
    active_root.mkdir()
    _make_course(active_root, "Apple-live")
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [str(active_root)])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "cisco"]):
            main()
    out = capsys.readouterr().out
    assert "No active courses match: cisco" in out


def test_main_archived_expanded_no_match_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    _make_course(archive / "2026", "Apple-x")
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "cisco", "--archived"]):
            main()
    out = capsys.readouterr().out
    assert "No archived courses match" in out


def test_main_archived_flag_empty_archive_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--archived"]):
            main()
    out = capsys.readouterr().out
    assert "No archived courses found" in out


def test_main_rejects_bad_year(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--year", "24"]):
            with pytest.raises(SystemExit):
                main()


# ---------------------------------------------------------------------------
# Mutation-audit hardening
# ---------------------------------------------------------------------------


def test_is_archived_course_rejects_every_junk_name(tmp_path: Path) -> None:
    """Every entry in JUNK_NAMES is filtered out, even with a notebook present.

    Iterates a hardcoded list (not JUNK_NAMES itself), so a mutation that drops
    a single name from the set is caught rather than being self-consistent.
    """
    for name in [
        "__pycache__",
        "build",
        "dist",
        "bin",
        "include",
        "lib",
        "node_modules",
    ]:
        d = tmp_path / name
        d.mkdir()
        (d / "lesson.ipynb").write_text("{}")
        assert is_archived_course(d) is False, name


def test_find_active_courses_missing_dir_does_not_abort_later_dirs(
    tmp_path: Path,
) -> None:
    """A missing scan dir is skipped, not treated as a stop signal.

    Pins the `continue` (vs `break`) in the missing-dir guard: a later scan dir
    must still be scanned.
    """
    missing = tmp_path / "does-not-exist"
    real = tmp_path / "real"
    real.mkdir()
    _make_course(real, "live-course")
    result = find_active_courses([missing, real])
    assert [p.name for p in result] == ["live-course"]


def test_find_archived_courses_non_year_before_year_does_not_abort(
    tmp_path: Path,
) -> None:
    """A non-year entry sorting before a real year dir must not stop the scan.

    Pins the `continue` (vs `break`) in the year-dir guard: `0000-junk` sorts
    before `2024`, so a `break` there would drop the 2024 courses.
    """
    (tmp_path / "0000-junk").mkdir()
    _make_course(tmp_path / "2024", "real-course")
    result = find_archived_courses(tmp_path)
    assert list(result.keys()) == ["2024"]


def test_archive_summary_line_three_year_span(tmp_path: Path) -> None:
    """The range uses the LAST year, not the second.

    Pins `years[-1]` against a mutation to `years[+1]` (== years[1]), which a
    two-year span cannot distinguish (years[-1] == years[1] there).
    """
    archived = {
        "2018": [tmp_path / "a"],
        "2020": [tmp_path / "b"],
        "2026": [tmp_path / "c"],
    }
    line = archive_summary_line(archived, [])
    assert "across 2018–2026 " in line


def test_archive_summary_line_multiple_name_patterns(tmp_path: Path) -> None:
    """Multiple name patterns are rendered comma-separated in the summary."""
    archived = {"2024": [tmp_path / "a"]}
    line = archive_summary_line(archived, ["cisco", "apple"])
    assert 'matching "cisco", "apple"' in line
