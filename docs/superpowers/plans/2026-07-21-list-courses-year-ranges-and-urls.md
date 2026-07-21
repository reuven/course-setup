# list-courses year ranges + per-course GitHub URLs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two `list-courses` enhancements shipped together as **3.3.0** — inclusive `--year` ranges (`2020-2022`, with reversed-range auto-swap), and per-course GitHub URLs shown by default (with `--no-urls` opt-out).

**Architecture:** Both features live in `src/setup_course_github/list_courses.py`. Year ranges add a token regex + a pure expansion helper wired into `main()`. URLs add a pure normalizer + a local-git lookup + a per-course print helper that replaces the two inline course-print lines. One feature branch, TDD, merged to `main` via PR, released to PyPI.

**Tech Stack:** Python 3, `uv`, pytest, argparse, `re`, `subprocess` (local `git`), ruff, mypy strict, mutmut (<3).

## Global Constraints

- Use `uv` for everything (`uv run pytest`, `uv run ruff`, `uv run mypy`, `uv build`, `uv publish`). Never pip/python/venv directly.
- **Never chain shell commands with `&&`.** Separate, sequential commands only.
- TDD: failing test first, confirm red, implement, confirm green, commit.
- 100% line coverage enforced; type hints everywhere; `uv run mypy --strict` clean; `uv run ruff format` + `uv run ruff check` clean before every commit.
- Small commits; exact commit messages as given.
- Design refs: `docs/superpowers/specs/2026-07-21-list-courses-year-ranges-design.md` and `docs/superpowers/specs/2026-07-21-list-courses-github-urls-design.md`.
- Output-string mutations are NOT killed in the mutation audit; real operator/keyword/boundary gaps ARE.
- `list-courses` stays read-only and network-free (URL lookup reads the local git remote only).

---

## Task 1: Year ranges — token validation + expansion

**Files:**
- Modify: `src/setup_course_github/list_courses.py`
- Test: `tests/test_list_courses.py`

**Interfaces:**
- Produces:
  - `_YEAR_TOKEN_RE` (module constant)
  - `_year_arg(value: str) -> str` (extended to accept `YYYY` or `YYYY-YYYY`)
  - `_expand_year_tokens(tokens: list[str]) -> tuple[list[str], list[str]]` → `(years, notes)`
  - `main()` expands tokens and prints swap notes to stderr; passes the flat year list to `filter_archived`.

- [ ] **Step 1: Create the feature branch**

```bash
git switch -c feature/list-courses-year-ranges-urls
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_list_courses.py` (imports: add `_expand_year_tokens` and
`_year_arg` to the `from setup_course_github.list_courses import (...)` block; the
file already imports `main`, `pytest`, `patch`, `Path`):

```python
def test_year_arg_accepts_single_and_range() -> None:
    from setup_course_github.list_courses import _year_arg

    assert _year_arg("2024") == "2024"
    assert _year_arg("2020-2022") == "2020-2022"


def test_year_arg_rejects_bad_tokens() -> None:
    import argparse

    from setup_course_github.list_courses import _year_arg

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
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_list_courses.py -k "year_arg or expand_year" -v`
Expected: FAIL — `cannot import name '_expand_year_tokens'`, and `_year_arg`
rejects `2020-2022`.

- [ ] **Step 4: Implement token regex + expansion, and update `_year_arg`**

In `src/setup_course_github/list_courses.py`, add the token regex next to
`_YEAR_RE` (after line 12):

```python
_YEAR_TOKEN_RE = re.compile(r"^\d{4}(-\d{4})?$")
```

**Replace** `_year_arg` (currently lines 141-145) with:

```python
def _year_arg(value: str) -> str:
    """argparse type: accept a 4-digit year or an inclusive YYYY-YYYY range."""
    if not _YEAR_TOKEN_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid year '{value}' (expected YYYY or YYYY-YYYY)"
        )
    return value


def _expand_year_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Flatten single-year and range tokens into individual 4-digit years.

    Returns ``(years, notes)`` where *notes* holds a message for each reversed
    range that was auto-swapped. Ranges are inclusive; a reversed range like
    ``2022-2020`` is swapped to ``2020-2022``.
    """
    years: list[str] = []
    notes: list[str] = []
    for token in tokens:
        if "-" in token:
            start_s, end_s = token.split("-")
            start, end = int(start_s), int(end_s)
            if start > end:
                notes.append(
                    f"swapped reversed year range {start_s}-{end_s} "
                    f"→ {end_s}-{start_s}"
                )
                start, end = end, start
            years.extend(f"{year:04d}" for year in range(start, end + 1))
        else:
            years.append(token)
    return years, notes
```

Keep `_YEAR_RE` unchanged — it still matches archive year-directory names in
`find_archived_courses`.

- [ ] **Step 5: Wire expansion into `main()`**

Add `import sys` to the top of the module (after `import re`).

In `main()`, immediately after `args = parser.parse_args(argv)` (line 198), add:

```python
    years, year_notes = _expand_year_tokens(args.years)
    for note in year_notes:
        print(f"Note: {note}", file=sys.stderr)
```

Then change the `filter_archived(...)` call (line 228-230) to use the expanded
`years` instead of `args.years`:

```python
        archived = filter_archived(
            find_archived_courses(config.archive_path), years, patterns
        )
```

Leave `has_years = bool(args.years)` as-is (it keys off the raw tokens). Update the
`--year` help text to mention ranges:

```python
        help="Restrict archived courses to a year or YYYY-YYYY range (repeatable)",
```

- [ ] **Step 6: Run, format, lint, type-check, commit**

The `main()`-level year-range tests are added in **Task 2** (they use the
`--no-urls` flag that Task 2 introduces). Task 1 ships only the pure
`_year_arg`/`_expand_year_tokens` unit tests from Step 2.

Run: `uv run pytest tests/test_list_courses.py -k "year_arg or expand_year" -v` (PASS)
Run: `uv run pytest` (full suite still green — the year-expansion is behavior-preserving for single-year `--year`, which existing tests cover)

```bash
uv run ruff format src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run ruff check src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run mypy --strict src/setup_course_github/list_courses.py
git add src/setup_course_github/list_courses.py tests/test_list_courses.py
git commit -m "feat: accept YYYY-YYYY ranges in list-courses --year"
```

---

## Task 2: Per-course GitHub URLs (default on, `--no-urls`)

**Files:**
- Modify: `src/setup_course_github/list_courses.py`
- Test: `tests/test_list_courses.py`

**Interfaces:**
- Consumes: `course_summary_line`, `main()` display loops from Task 1.
- Produces:
  - `_github_url(remote: str) -> str | None`
  - `github_url(course_path: Path) -> str | None`
  - `_print_course(course: Path, indent: int, show_urls: bool) -> None`
  - `--no-urls` flag; URL/placeholder lines under each listed course.

- [ ] **Step 1: Write the failing unit + integration tests**

Add to `tests/test_list_courses.py` (add `_github_url`, `github_url`,
`_print_course` to the import block; add `import subprocess` at the top of the
test file if not present):

```python
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
```

- [ ] **Step 2: Add the URL + year `main` behavior tests**

First, the three year-range `main` tests (deferred from Task 1 — they use
`--no-urls`, added in this task):

```python
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
```

Then these URL tests:

```python
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
        with patch(
            "setup_course_github.list_courses.github_url", return_value=None
        ):
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
        with patch(
            "setup_course_github.list_courses.github_url"
        ) as mock_url:
            with patch("sys.argv", ["list-courses", "--count"]):
                main()
    mock_url.assert_not_called()
```

- [ ] **Step 3: Update existing `main` list-tests to pass `--no-urls`**

With URLs on by default, existing `main` tests that **list courses** would emit
extra `(no GitHub remote)` placeholder lines (the fixtures' `.git` is an empty
dir with no remote). Add `--no-urls` to the `sys.argv` list in exactly these
tests so they keep testing only which courses appear:

- `test_main_lists_active_and_archived`
- `test_main_cli_dirs_override`
- `test_main_archived_flag_expands_listing`
- `test_main_active_flag_only`
- `test_main_name_filter_active_and_archive_summary`
- `test_main_name_filter_with_archived_expands`
- `test_main_year_focus_suppresses_active`
- `test_main_year_repeatable`
- `test_main_active_year_shows_active_ignores_year`

Do NOT change tests that list no courses (`test_main_no_active_courses_message`,
`test_main_name_filter_no_active_match_message`,
`test_main_archived_expanded_no_match_message`,
`test_main_archived_flag_empty_archive_message`), the count test
(`test_main_count`), or `test_main_rejects_bad_year`. Example edit:

```python
        with patch("sys.argv", ["list-courses", "--no-urls"]):
```
(for `test_main_cli_dirs_override`: `["list-courses", "--dir", str(cli_root), "--no-urls"]`).

- [ ] **Step 4: Run to verify failure**

Run: `uv run pytest tests/test_list_courses.py -k "github_url or url or year_range or year_mixed or reversed_range" -v`
Expected: FAIL — `cannot import name '_github_url'`; `--no-urls` unrecognized.

- [ ] **Step 5: Implement the URL helpers, print helper, and `--no-urls`**

In `src/setup_course_github/list_courses.py`, add `import subprocess` at the top
(after `import re`). Add the GitHub-URL regex near the other module constants
(after `_YEAR_TOKEN_RE`):

```python
_GITHUB_RE = re.compile(r"github\.com[:/](?P<path>[^/]+/[^/]+?)(?:\.git)?/?$")
```

Add these functions (place `_github_url`/`github_url` after `course_summary_line`,
and `_print_course` just above `main`):

```python
def _github_url(remote: str) -> str | None:
    """Normalize a GitHub SSH/HTTPS remote to https://github.com/<owner>/<repo>.

    Returns None for an empty string or a non-GitHub remote.
    """
    match = _GITHUB_RE.search(remote)
    if not match:
        return None
    return f"https://github.com/{match.group('path')}"


def github_url(course_path: Path) -> str | None:
    """Return the course repo's GitHub URL from its local origin remote, or None.

    Reads ``git config --get remote.origin.url`` in *course_path*; no network.
    """
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=str(course_path),
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return _github_url(result.stdout.decode().strip())


def _print_course(course: Path, indent: int, show_urls: bool) -> None:
    """Print a course summary line and, when *show_urls*, its indented URL line."""
    print(f"{' ' * indent}{course_summary_line(course)}")
    if show_urls:
        url = github_url(course)
        print(f"{' ' * (indent + 2)}{url or '(no GitHub remote)'}")
```

Add the `--no-urls` argument (after the `--count` argument):

```python
    parser.add_argument(
        "--no-urls",
        action="store_true",
        help="Do not show each course's GitHub URL",
    )
```

After the boolean block in `main()`, add:

```python
    show_urls = not args.no_urls
```

Replace the active-loop print (currently `print(f"  {course_summary_line(course)}")`)
with:

```python
                for course in active:
                    _print_course(course, 2, show_urls)
```

Replace the archived-loop print (currently
`print(f"    {course_summary_line(course)}")`) with:

```python
                    for course in archived[year]:
                        _print_course(course, 4, show_urls)
```

- [ ] **Step 6: Run to verify pass**

Run: `uv run pytest tests/test_list_courses.py -v`
Expected: PASS (all, including the moved year-range main tests).

- [ ] **Step 7: Smoke-test the real command**

Run: `uv run list-courses --help`
Expected: shows `--no-urls`; `--year` help mentions `YYYY-YYYY`.

- [ ] **Step 8: Format, lint, type-check, full suite, commit**

```bash
uv run ruff format src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run ruff check src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run mypy --strict src/setup_course_github/list_courses.py
uv run pytest
git add src/setup_course_github/list_courses.py tests/test_list_courses.py
git commit -m "feat: show per-course GitHub URLs by default (--no-urls to hide)"
```

---

## Task 3: Docs — README + MANUAL

**Files:**
- Modify: `README.md`
- Modify: `MANUAL.md`

- [ ] **Step 1: Update README `list-courses` section**

Document: `--year` now accepts a `YYYY-YYYY` range (inclusive, repeatable, mixes
with singles); a reversed range is auto-swapped with a `Note:` printed to stderr.
Per-course GitHub URLs are shown by default under each listed course (indented),
with `--no-urls` to hide them and `(no GitHub remote)` when a course has no usable
remote. Update the options table and an example.

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: document --year ranges and per-course URLs in README"
```

- [ ] **Step 3: Update MANUAL `list-courses` section**

Same content at manual depth: range syntax + auto-swap note, and the default-on
URL display + `--no-urls` + placeholder, with example output showing the indented
URL line.

- [ ] **Step 4: Commit MANUAL**

```bash
git add MANUAL.md
git commit -m "docs: document --year ranges and per-course URLs in the manual"
```

---

## Task 4: Mutation-testing audit

- [ ] **Step 1: Run the audit**

Run: `uv run mutmut run`
(Slow. Tally survivors via
`sqlite3 .mutmut-cache "SELECT status,COUNT(*) FROM Mutant GROUP BY status"`.)

- [ ] **Step 2: Triage `list_courses.py` survivors**

List survivors:
`sqlite3 .mutmut-cache "SELECT m.id,l.line_number,l.line FROM Mutant m JOIN Line l ON m.line=l.id JOIN SourceFile sf ON l.sourcefile=sf.id WHERE m.status='bad_survived' AND sf.filename LIKE '%list_courses.py' ORDER BY l.line_number"`

Kill real logic gaps only: the `_YEAR_TOKEN_RE`/`_GITHUB_RE` patterns, the
`start > end` swap branch, the inclusive `range(start, end + 1)` boundary, the
`_github_url` `None` branch, `show_urls`/`indent + 2` logic. Ignore
string-literal/help-text/output mutations per project policy. For each real gap:
`uv run mutmut apply <id>` → confirm a test fails → `git checkout -- <src>` →
write the killing test → verify → commit (`Kill list-courses mutant <id>: <what>`).

---

## Task 5: Version bump, release PR, tag, publish

- [ ] **Step 1: Bump the version**

In `pyproject.toml:3`, change `version = "3.2.1"` to `version = "3.3.0"`.

- [ ] **Step 2: Sync, commit**

```bash
uv sync
git add pyproject.toml uv.lock
git commit -m "Bump version to 3.3.0"
```

- [ ] **Step 3: Full suite green**

Run: `uv run pytest`
Expected: PASS, 100% coverage.

- [ ] **Step 4: Push branch and open PR**

```bash
git push -u origin feature/list-courses-year-ranges-urls
gh pr create --base main --head feature/list-courses-year-ranges-urls --title "Release 3.3.0: list-courses --year ranges + per-course GitHub URLs" --body "See docs/superpowers/specs/2026-07-21-list-courses-year-ranges-design.md and 2026-07-21-list-courses-github-urls-design.md."
```

- [ ] **Step 5: Merge (admin bypass), merge commit**

```bash
gh pr merge --merge --admin --delete-branch
```

- [ ] **Step 6: Sync main, tag, push tag**

```bash
git switch main
git pull
git tag v3.3.0
git push origin v3.3.0
```

- [ ] **Step 7: Clean dist, build, publish, verify**

```bash
rm -rf dist/*
uv build
uv publish
```

Run: `curl -s https://pypi.org/simple/course-setup/ | grep -o 'course_setup-3.3.0[^"#]*' | sort -u`
Expected: both 3.3.0 files listed.

---

## Self-Review Notes

- **Spec coverage:** year-range spec §1-4 → Task 1 (+ 3 main tests moved into Task 2); URL spec §1-3 → Task 2; both docs → Task 3; both release sections → Task 5; mutation audits → Task 4. All mapped.
- **Cross-task ordering:** the three `--no-urls` year-range `main` tests are added in Task 2 (they need Task 2's flag). Task 1 adds only the pure `_year_arg`/`_expand_year_tokens` tests. This is called out at Task 1 Step 6.
- **Existing-test fallout:** URLs on-by-default → Task 2 Step 3 adds `--no-urls` to the nine listing tests; non-listing/count/error tests are explicitly left alone.
- **Type consistency:** `_expand_year_tokens -> tuple[list[str], list[str]]`; `_github_url(str) -> str | None`; `github_url(Path) -> str | None`; `_print_course(Path, int, bool) -> None`; `filter_archived(..., years: list[str], ...)` unchanged and fed the expanded list.
- **Read-only/offline preserved:** `github_url` shells to local `git config` only; no network.
```
