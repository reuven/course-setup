# list-courses filters + archive junk fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `list-courses` usable on a large archive: fix the archive-listing junk bug, default to an active-full + archive-summary view, and add filters (`--active`/`--archived`, repeatable `--year`, positional name match, `--count`, and a new `--dir` scan-override flag).

**Architecture:** All logic lives in `src/setup_course_github/list_courses.py`. Add small pure helpers (junk detection, name/year filters, summary line), rewrite `find_archived_courses`, and rebuild `main()`'s argument parsing + display composition. One feature branch, TDD, merged to `main` via PR, released as 3.2.0.

**Tech Stack:** Python 3, `uv`, pytest, argparse, `re`, ruff, mypy strict, mutmut (<3).

## Global Constraints

- Use `uv` for everything (`uv run pytest`, `uv run ruff`, `uv run mypy`, `uv build`, `uv publish`). Never pip/python/venv directly.
- **Never chain shell commands with `&&`.** Separate, sequential commands only.
- TDD: failing test first, confirm red, implement, confirm green, commit.
- 100% line coverage enforced (`--cov-fail-under=100`); type hints everywhere; `uv run mypy --strict` clean; `uv run ruff format` + `uv run ruff check` clean before every commit.
- Small commits; use the exact commit messages given.
- Design reference: `docs/superpowers/specs/2026-07-21-list-courses-filters-design.md`.
- **Breaking change:** the positional argument is now a name filter; the scan-directory override moves to `--dir`.
- Output-string mutations are intentionally NOT killed in the mutation audit; real operator/keyword/boundary gaps ARE.

---

## Task 1: Archive-course detection + rewritten `find_archived_courses`

**Files:**
- Modify: `src/setup_course_github/list_courses.py`
- Test: `tests/test_list_courses.py`

**Interfaces:**
- Produces:
  - `JUNK_NAMES: frozenset[str]`
  - `_is_junk_name(name: str) -> bool`
  - `is_archived_course(path: Path) -> bool`
  - `find_archived_courses(archive_path: Path) -> dict[str, list[Path]]` (rewritten: only `^\d{4}$` year dirs; only `is_archived_course` children)

- [ ] **Step 1: Create the feature branch**

```bash
git switch -c feature/list-courses-filters
```

- [ ] **Step 2: Update the existing archive tests + write the new detection tests**

In `tests/test_list_courses.py`, **replace** the three existing archive tests
(currently at the `test_find_archived_courses_*` block) with these (they now give
courses real notebooks, since detection requires ≥1 notebook) and add the new
detection tests. Use the existing module-level `_make_course` helper (it creates a
`.git` dir + a `lesson.ipynb`, which satisfies `is_archived_course`):

```python
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
```

Add `find_archived_courses`, `is_archived_course` to the existing
`from setup_course_github.list_courses import (...)` block at the top of the test
file (they are already imported — confirm `is_archived_course` is added).

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_list_courses.py -k "archived_course or is_archived" -v`
Expected: FAIL — `cannot import name 'is_archived_course'`, plus the updated
grouped/junk tests fail against the current permissive `find_archived_courses`.

- [ ] **Step 4: Implement detection**

In `src/setup_course_github/list_courses.py`, add `import re` at the top (after
`from pathlib import Path`), and add the constants + helpers. Place `JUNK_NAMES`
and `_YEAR_RE` near the top (after imports), and `_is_junk_name` /
`is_archived_course` next to `is_course`:

```python
JUNK_NAMES = frozenset(
    {"__pycache__", "build", "dist", "bin", "include", "lib", "node_modules"}
)
_YEAR_RE = re.compile(r"^\d{4}$")


def _is_junk_name(name: str) -> bool:
    """True for hidden (dot-prefixed) or known build/cache directory names."""
    return name.startswith(".") or name in JUNK_NAMES


def is_archived_course(path: Path) -> bool:
    """An archived course: a non-junk directory containing at least one notebook.

    Unlike active courses, a ``.git`` subdir is NOT required (archived repos may
    have had it stripped).
    """
    if _is_junk_name(path.name):
        return False
    ipynb_files, marimo_files = find_notebooks(path)
    return bool(ipynb_files or marimo_files)
```

Then **replace** the existing `find_archived_courses` with:

```python
def find_archived_courses(archive_path: Path) -> dict[str, list[Path]]:
    """Return {year: [course dirs]} under archive_path/<YYYY>/<course>.

    Only directories named like a 4-digit year are treated as year groups, and
    only ``is_archived_course`` children are included.
    """
    result: dict[str, list[Path]] = {}
    if not archive_path.is_dir():
        return result
    for year_dir in sorted(archive_path.iterdir()):
        if not (year_dir.is_dir() and _YEAR_RE.match(year_dir.name)):
            continue
        courses = sorted(
            c for c in year_dir.iterdir() if c.is_dir() and is_archived_course(c)
        )
        if courses:
            result[year_dir.name] = courses
    return result
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_list_courses.py -k "archived_course or is_archived" -v`
Expected: PASS.

- [ ] **Step 6: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run ruff check src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run mypy --strict src/setup_course_github/list_courses.py
git add src/setup_course_github/list_courses.py tests/test_list_courses.py
git commit -m "feat: filter archived courses to real courses under year dirs"
```

---

## Task 2: Pure filter + summary helpers

**Files:**
- Modify: `src/setup_course_github/list_courses.py`
- Test: `tests/test_list_courses.py`

**Interfaces:**
- Consumes: nothing from Task 1 except module context.
- Produces:
  - `_matches_names(name: str, patterns: list[str]) -> bool`
  - `filter_active(courses: list[Path], patterns: list[str]) -> list[Path]`
  - `filter_archived(archived: dict[str, list[Path]], years: list[str], patterns: list[str]) -> dict[str, list[Path]]`
  - `archive_summary_line(archived: dict[str, list[Path]], patterns: list[str]) -> str`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_list_courses.py` (add `archive_summary_line`, `filter_active`,
`filter_archived`, `_matches_names` to the import block):

```python
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
        "Archived: 3 courses across 2018–2026 "
        "— use --archived to list them."
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_list_courses.py -k "matches_names or filter_ or summary_line" -v`
Expected: FAIL — `cannot import name '_matches_names'` (etc.).

- [ ] **Step 3: Implement the helpers**

Add to `src/setup_course_github/list_courses.py` (after `course_summary_line`):

```python
def _matches_names(name: str, patterns: list[str]) -> bool:
    """True if *name* (case-insensitively) contains any of *patterns*.

    An empty *patterns* list matches everything.
    """
    if not patterns:
        return True
    lowered = name.lower()
    return any(p.lower() in lowered for p in patterns)


def filter_active(courses: list[Path], patterns: list[str]) -> list[Path]:
    """Keep only active-course paths whose name matches *patterns*."""
    return [c for c in courses if _matches_names(c.name, patterns)]


def filter_archived(
    archived: dict[str, list[Path]], years: list[str], patterns: list[str]
) -> dict[str, list[Path]]:
    """Filter the {year: courses} map by *years* (if non-empty) and *patterns*.

    Years not in *years* are dropped; within a kept year, courses are filtered by
    name; years left with no matching courses are omitted.
    """
    result: dict[str, list[Path]] = {}
    for year, courses in archived.items():
        if years and year not in years:
            continue
        matched = [c for c in courses if _matches_names(c.name, patterns)]
        if matched:
            result[year] = matched
    return result


def archive_summary_line(
    archived: dict[str, list[Path]], patterns: list[str]
) -> str:
    """One-line summary of the archived-course count and year span."""
    total = sum(len(courses) for courses in archived.values())
    match_clause = ""
    if patterns:
        quoted = ", ".join(f'"{p}"' for p in patterns)
        match_clause = f" matching {quoted}"
    if total == 0:
        return f"Archived: none{match_clause}"
    years = sorted(archived.keys())
    span = years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}"
    return (
        f"Archived: {total} courses{match_clause} across {span}"
        " — use --archived to list them."
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_list_courses.py -k "matches_names or filter_ or summary_line" -v`
Expected: PASS.

- [ ] **Step 5: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run ruff check src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run mypy --strict src/setup_course_github/list_courses.py
git add src/setup_course_github/list_courses.py tests/test_list_courses.py
git commit -m "feat: add name/year filters and archive summary helper"
```

---

## Task 3: Rebuild `main()` — args, display composition, breaking `--dir`

**Files:**
- Modify: `src/setup_course_github/list_courses.py` (`main`, add `_year_arg`)
- Test: `tests/test_list_courses.py`

**Interfaces:**
- Consumes: all Task 1 + Task 2 functions, plus `find_active_courses`,
  `resolve_scan_dirs`, `course_summary_line`, `load_config`.
- Produces: `main(argv: list[str] | None = None) -> None`; `_year_arg(value: str) -> str`.

- [ ] **Step 1: Update the existing main tests broken by the redesign**

Three existing `main` tests change behavior. Apply these exact edits in
`tests/test_list_courses.py`:

**(a)** `test_main_lists_active_and_archived` — the default view now shows the
archive as a summary line, and archived courses need a notebook. Replace its body
with a default-view assertion:

```python
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
    # default view: archive is a one-line summary, not an expanded listing
    assert "Archived: 1 courses across 2026" in out
    assert "gone-course" not in out
```

**(b)** `test_main_no_active_courses_message` — empty archive now yields the
summary `Archived: none`, not `No archived courses found`:

```python
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
```

**(c)** `test_main_cli_dirs_override` — the scan-dir override is now `--dir`, not a
positional:

```python
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
        with patch("sys.argv", ["list-courses", "--dir", str(cli_root)]):
            main()
    out = capsys.readouterr().out
    assert "cli-course" in out
```

- [ ] **Step 2: Add the new `main` behavior tests**

Append to `tests/test_list_courses.py`:

```python
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
        with patch("sys.argv", ["list-courses", "--archived"]):
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
        with patch("sys.argv", ["list-courses", "--active"]):
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
        with patch("sys.argv", ["list-courses", "cisco"]):
            main()
    out = capsys.readouterr().out
    assert "Cisco-live" in out
    assert "Apple-live" not in out
    # bare name search keeps the archive as a name-filtered summary line
    assert 'Archived: 1 courses matching "cisco"' in out
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
        with patch("sys.argv", ["list-courses", "cisco", "--archived"]):
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
        with patch("sys.argv", ["list-courses", "--year", "2024"]):
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
        with patch("sys.argv", ["list-courses", "--year", "2024", "--year", "2026"]):
            main()
    out = capsys.readouterr().out
    assert "c-2024" in out
    assert "c-2026" in out
    assert "c-2025" not in out


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
        with patch("sys.argv", ["list-courses", "--active", "--year", "2024"]):
            main()
    out = capsys.readouterr().out
    assert "live-course" in out
    assert "old-2024" not in out


def test_main_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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


def test_main_rejects_bad_year(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    config = _config_for(archive, [])
    with patch("setup_course_github.list_courses.load_config", return_value=config):
        with patch("sys.argv", ["list-courses", "--year", "24"]):
            with pytest.raises(SystemExit):
                main()
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_list_courses.py -v`
Expected: FAIL — new tests fail (unrecognized `--dir`/`--archived`/`--year`/`--count`,
no `_year_arg`), and the three edited tests fail against the old `main`.

- [ ] **Step 4: Rewrite `main` and add `_year_arg`**

**Replace** the entire `main` function in `src/setup_course_github/list_courses.py`
with the following (and add `_year_arg` just above it):

```python
def _year_arg(value: str) -> str:
    """argparse type: accept only a 4-digit year."""
    if not _YEAR_RE.match(value):
        raise argparse.ArgumentTypeError(f"invalid year '{value}' (expected 4 digits)")
    return value


def main(argv: list[str] | None = None) -> None:
    pypi_url = "https://pypi.org/project/course-setup/"
    author_line = f"{__author__} <{__email__}>"

    parser = argparse.ArgumentParser(
        description="List active and archived courses.",
        epilog=f"Version {__version__} — {pypi_url}\n{author_line}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}\n{pypi_url}\n{author_line}",
    )
    parser.add_argument(
        "names",
        nargs="*",
        help="Filter courses by case-insensitive name substring (any match)",
    )
    parser.add_argument(
        "--dir",
        action="append",
        default=[],
        metavar="PATH",
        help="Directory to scan for active courses (repeatable; overrides config)",
    )
    parser.add_argument(
        "--active",
        action="store_true",
        help="Show only active courses",
    )
    parser.add_argument(
        "--archived",
        action="store_true",
        help="Show only archived courses (expanded, grouped by year)",
    )
    parser.add_argument(
        "--year",
        action="append",
        default=[],
        dest="years",
        type=_year_arg,
        metavar="YYYY",
        help="Restrict archived courses to a year (repeatable; hides active)",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Show counts instead of individual course lines",
    )
    args = parser.parse_args(argv)

    config = load_config()
    scan_dirs = resolve_scan_dirs(args.dir, config)

    patterns: list[str] = args.names
    has_names = bool(patterns)
    has_years = bool(args.years)
    only_active = args.active and not args.archived
    only_archived = args.archived and not args.active
    year_focus = has_years and not args.active and not args.archived
    show_active = not (only_archived or year_focus)
    show_archived = not only_active
    archive_expanded = args.archived or has_years

    if show_active:
        active = filter_active(find_active_courses(scan_dirs), patterns)
        if args.count:
            print(f"Active courses: {len(active)}")
        else:
            print("Active courses:")
            if active:
                for course in active:
                    print(f"  {course_summary_line(course)}")
            elif has_names:
                print(f"  No active courses match: {', '.join(patterns)}")
            else:
                print("  No active courses found")

    if show_archived:
        archived = filter_archived(
            find_archived_courses(config.archive_path), args.years, patterns
        )
        if show_active:
            print()
        if args.count:
            total = sum(len(courses) for courses in archived.values())
            print(f"Archived courses: {total}")
            for year in sorted(archived):
                print(f"  {year}: {len(archived[year])}")
        elif archive_expanded:
            print("Archived courses:")
            if archived:
                for year in sorted(archived):
                    print(f"  {year}:")
                    for course in archived[year]:
                        print(f"    {course_summary_line(course)}")
            elif has_names or has_years:
                print("  No archived courses match your filters")
            else:
                print("  No archived courses found")
        else:
            print(archive_summary_line(archived, patterns))
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_list_courses.py -v`
Expected: PASS (all).

- [ ] **Step 6: Smoke-test the real command**

Run: `uv run list-courses --help`
Expected: help text shows `names`, `--dir`, `--active`, `--archived`, `--year`, `--count`.

- [ ] **Step 7: Format, lint, type-check, full suite, commit**

```bash
uv run ruff format src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run ruff check src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run mypy --strict src/setup_course_github/list_courses.py
uv run pytest
git add src/setup_course_github/list_courses.py tests/test_list_courses.py
git commit -m "feat: add list-courses filters, summary default, and --dir override"
```

---

## Task 4: Docs — README + MANUAL

**Files:**
- Modify: `README.md`
- Modify: `MANUAL.md`

- [ ] **Step 1: Update README `list-courses` section**

In `README.md`, expand the `### list-courses` section to document:
- the default view (active full + one-line archive summary),
- `--active` / `--archived`, repeatable `--year`, `--count`,
- the positional **name filter** (case-insensitive substring), and
- the new `--dir` scan-override flag,
- a clear **Breaking change** note: the positional argument is now a name filter;
  use `--dir PATH` for the old scan-directory override.

Include the example-invocation table from the design spec §4.

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: document list-courses filters and --dir in README"
```

- [ ] **Step 3: Update MANUAL `list-courses` section**

In `MANUAL.md`, update the `list-courses` command subsection with the same
content at manual depth: a Synopsis showing all flags, an Options table, the
behavior-composition rules (default vs `--active`/`--archived`/`--year`), the
name-filter semantics, `--count`, `--dir`, and the breaking-change callout.

- [ ] **Step 4: Commit MANUAL**

```bash
git add MANUAL.md
git commit -m "docs: document list-courses filters and --dir in the manual"
```

---

## Task 5: Mutation-testing audit

- [ ] **Step 1: Run the audit**

Run: `uv run mutmut run`
(Slow. `mutmut results` may crash on 2.x; tally survivors via
`sqlite3 .mutmut-cache "SELECT status,COUNT(*) FROM Mutant GROUP BY status"`.)

- [ ] **Step 2: Triage survivors in `list_courses.py` only**

List survivors for the file:
`sqlite3 .mutmut-cache "SELECT m.id,l.line_number,l.line FROM Mutant m JOIN Line l ON m.line=l.id JOIN SourceFile sf ON l.sourcefile=sf.id WHERE m.status='bad_survived' AND sf.filename LIKE '%list_courses.py' ORDER BY l.line_number"`

Kill only real logic gaps (operator/keyword/boundary/default mutations on
non-string lines): candidates include the `^\d{4}$` year match, the
`_matches_names` `any(...)`/substring logic, the `only_active`/`only_archived`/
`year_focus`/`show_active`/`show_archived` boolean composition, the
`len(years) == 1` summary branch, and the `_is_junk_name` `or`. Ignore
string-literal/help-text/output mutations per project policy.

- [ ] **Step 3: For each real gap, add a killing test (TDD) and commit**

For each kept survivor: `uv run mutmut apply <id>` → confirm a test now fails →
`git checkout -- src/setup_course_github/list_courses.py` → write the killing
test → verify green → commit (small commit per gap, message
`Kill list-courses mutant <id>: <what it asserts>`).

---

## Task 6: Version bump, release PR, tag, publish

- [ ] **Step 1: Bump the version**

In `pyproject.toml:3`, change `version = "3.1.0"` to `version = "3.2.0"`.
(The version lives only here; `__version__` is read from package metadata.)

- [ ] **Step 2: Sync so metadata reflects the bump, then commit**

```bash
uv sync
git add pyproject.toml uv.lock
git commit -m "Bump version to 3.2.0"
```

- [ ] **Step 3: Full suite green with coverage**

Run: `uv run pytest`
Expected: PASS, 100% coverage.

- [ ] **Step 4: Push the branch and open a PR**

```bash
git push -u origin feature/list-courses-filters
gh pr create --base main --head feature/list-courses-filters --title "Release 3.2.0: list-courses filters + archive junk fix" --body "See docs/superpowers/specs/2026-07-21-list-courses-filters-design.md. Breaking: positional arg is now a name filter; scan-dir override moved to --dir."
```

- [ ] **Step 5: Merge the PR (owner admin bypass), using a merge commit**

```bash
gh pr merge --merge --admin --delete-branch
```

- [ ] **Step 6: Sync main, tag, push tag**

```bash
git switch main
git pull
git tag v3.2.0
git push origin v3.2.0
```

- [ ] **Step 7: Clean dist, build, publish**

```bash
rm -rf dist/*
uv build
uv publish
```

- [ ] **Step 8: Verify on PyPI**

Run: `curl -s https://pypi.org/pypi/course-setup/json | python3 -c "import sys,json; print(json.load(sys.stdin)['info']['version'])"`
Expected: `3.2.0`.

---

## Self-Review Notes

- **Spec coverage:** §1 detection → Task 1; §2 default view + §3 filters + §4
  composition → Tasks 2–3; §5 units → Tasks 1–3; §6 docs/release → Tasks 4 & 6;
  mutation audit → Task 5. All mapped.
- **Breaking-change fallout:** the three existing `main` tests that assumed the
  old positional/default behavior are rewritten in Task 3 Step 1; the three
  `find_archived_courses` tests that used notebook-less dirs are rewritten in
  Task 1 Step 2.
- **Type consistency:** `find_archived_courses -> dict[str, list[Path]]`;
  `filter_archived(archived, years: list[str], patterns: list[str])`;
  `archive_summary_line(archived, patterns)`; `main`/`_year_arg` signatures match
  every call site and test.
