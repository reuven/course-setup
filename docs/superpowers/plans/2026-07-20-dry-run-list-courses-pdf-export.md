# dry-run / list-courses / PDF-export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three features to the `course-setup` CLI toolkit — a `--dry-run` preview for `retire-course`, a new read-only `list-courses` command, and PDF export (on by default) in `archive-course`.

**Architecture:** Each feature ships on its own feature branch merged to `main` when complete. A shared `notebooks.py` helper is extracted from `retire_course.py` (behavior-preserving) so `list-courses` and `retire-course` share notebook-discovery and date-range logic. All work is TDD with 100% line coverage.

**Tech Stack:** Python 3, `uv` (never pip/venv), pytest, `argparse`, `tomllib`, `nbconvert --to webpdf`, ruff, mypy strict, mutmut (<3).

## Global Constraints

- Use `uv` for everything: `uv add`, `uv run pytest`, `uv run ruff`, `uv run mypy`. Never invoke pip, python, or a venv directly.
- Never chain shell commands with `&&`. Issue separate, sequential commands.
- TDD: write the failing test first, watch it fail, implement, watch it pass, commit.
- 100% line coverage is enforced (`--cov-fail-under=100`). Every new branch needs a test.
- Type hints everywhere; `uv run mypy` in strict mode must pass before every commit.
- `uv run ruff format` and `uv run ruff check` before every commit.
- Commits are small and single-file where practical. Feature branches merge to `main`, then the branch is deleted immediately.
- On version bump: add a matching git tag. Before building/publishing: delete old `dist/` artifacts.
- mutmut (`uv run mutmut run`) is an audit before the release that ships these — not a per-commit gate.

---

## Feature 1 — `retire-course --dry-run`

**Branch:** `feature/retire-dry-run`

### File Structure

- Modify: `src/setup_course_github/retire_course.py` — add `dry_run` param + `--dry-run` flag.
- Test: `tests/test_retire_course.py` — new dry-run tests; update one existing assertion.

### Task 1: Add `dry_run` parameter to `retire_course()`

**Files:**
- Modify: `src/setup_course_github/retire_course.py` (function `retire_course`, lines 157-181)
- Test: `tests/test_retire_course.py`

**Interfaces:**
- Produces: `retire_course(dirname: str, keep_public: bool = False, dry_run: bool = False) -> None`

- [ ] **Step 1: Create and switch to the feature branch**

```bash
git switch -c feature/retire-dry-run
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_retire_course.py` (the file already imports `MagicMock, patch, pytest, Path`, and defines `FAKE_CONFIG`):

```python
def test_retire_course_dry_run_does_not_move(tmp_path: Path) -> None:
    course = tmp_path / "mycourse"
    course.mkdir()
    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.load_config", return_value=FAKE_CONFIG
        ):
            with patch("shutil.move") as mock_move:
                retire_course(str(course), dry_run=True)
    mock_move.assert_not_called()
    assert course.exists()


def test_retire_course_dry_run_skips_github() -> None:
    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch("setup_course_github.retire_course.get_github") as mock_gh:
            with patch(
                "setup_course_github.retire_course.load_config",
                return_value=FAKE_CONFIG,
            ):
                with patch("shutil.move"):
                    retire_course("/some/course/dir", dry_run=True)
    mock_gh.assert_not_called()


def test_retire_course_dry_run_skips_confirm_create_dir() -> None:
    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.load_config", return_value=FAKE_CONFIG
        ):
            with patch(
                "setup_course_github.retire_course._confirm_create_dir"
            ) as mock_confirm:
                with patch("shutil.move"):
                    retire_course("/some/course/dir", dry_run=True)
    mock_confirm.assert_not_called()


def test_retire_course_dry_run_prints_banner_and_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    course = tmp_path / "mycourse"
    course.mkdir()
    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.load_config", return_value=FAKE_CONFIG
        ):
            retire_course(str(course), dry_run=True)
    out = capsys.readouterr().out
    assert "[DRY RUN]" in out
    assert "Would retire" in out
    assert "Retirement Summary" in out
    # dry run describes intended action: repo would be made private
    assert "(now private)" in out


def test_retire_course_dry_run_keep_public_shows_still_public(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    course = tmp_path / "mycourse"
    course.mkdir()
    with patch(
        "setup_course_github.retire_course.get_remote_url",
        return_value="git@github.com:someuser/myrepo.git",
    ):
        with patch(
            "setup_course_github.retire_course.load_config", return_value=FAKE_CONFIG
        ):
            retire_course(str(course), keep_public=True, dry_run=True)
    out = capsys.readouterr().out
    assert "(still public)" in out
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_retire_course.py -k dry_run -v`
Expected: FAIL — `retire_course() got an unexpected keyword argument 'dry_run'`

- [ ] **Step 4: Implement the `dry_run` branch**

Replace the body of `retire_course` (lines 157-181) with:

```python
def retire_course(
    dirname: str, keep_public: bool = False, dry_run: bool = False
) -> None:
    """Move the local directory to the archive, optionally making the repo private.

    When *dry_run* is True, no repo is modified, no directory is created, and
    nothing is moved — only a preview of the intended actions is printed.
    """
    _check_not_inside_course(dirname)

    config = load_config()

    remote_url = get_remote_url(dirname)
    repo_name = parse_repo_name(remote_url)

    year = datetime.datetime.now().year
    dest = config.archive_path / str(year)

    if dry_run:
        summary = _build_retirement_summary(
            dirname, repo_name, dest, kept_public=keep_public
        )
        print(f"[DRY RUN] Would retire {dirname} → {dest / Path(dirname).name}")
        print(summary)
        return

    g = get_github()
    repo = g.get_repo(repo_name)
    if not keep_public:
        repo.edit(private=True)

    _confirm_create_dir(dest)

    summary = _build_retirement_summary(
        dirname, repo_name, dest, kept_public=keep_public
    )
    shutil.move(dirname, dest)

    print(f"Successfully retired {dirname} → {dest}")
    print(summary)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_retire_course.py -k dry_run -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/retire_course.py tests/test_retire_course.py
uv run ruff check src/setup_course_github/retire_course.py tests/test_retire_course.py
uv run mypy --strict src/setup_course_github/retire_course.py
git add src/setup_course_github/retire_course.py tests/test_retire_course.py
git commit -m "feat: add dry_run parameter to retire_course"
```

### Task 2: Wire `--dry-run` into the CLI

**Files:**
- Modify: `src/setup_course_github/retire_course.py` (function `main`, lines 184-220)
- Test: `tests/test_retire_course.py`

**Interfaces:**
- Consumes: `retire_course(dirname, keep_public=..., dry_run=...)` from Task 1.

- [ ] **Step 1: Update the existing `main` test and add a dry-run test**

The existing `test_main_calls_retire_course` asserts the exact call args; it must now include `dry_run=False`. Find it (around line 336) and change its assertion:

```python
    mock_retire.assert_called_once_with(str(tmp_path), keep_public=False, dry_run=False)
```

Then add a new test:

```python
def test_main_passes_dry_run(tmp_path: Path) -> None:
    with patch("setup_course_github.retire_course.retire_course") as mock_retire:
        with patch("sys.argv", ["retire-course", "--dry-run", str(tmp_path)]):
            main()
    mock_retire.assert_called_once_with(
        str(tmp_path), keep_public=False, dry_run=True
    )
```

- [ ] **Step 2: Run to verify the new test fails**

Run: `uv run pytest tests/test_retire_course.py -k "dry_run or main_calls" -v`
Expected: `test_main_passes_dry_run` FAILS (unrecognized arg `--dry-run`); `test_main_calls_retire_course` FAILS on the new assertion.

- [ ] **Step 3: Add the flag and pass it through**

In `main`, add the argument after the `--keep-public` block (after line 202):

```python
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="preview the retirement without changing GitHub or moving files",
    )
```

And update the `retire_course` call inside the loop (line 211):

```python
            retire_course(dirname, keep_public=args.keep_public, dry_run=args.dry_run)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_retire_course.py -v`
Expected: PASS (all)

- [ ] **Step 5: Format, lint, type-check, full suite, commit**

```bash
uv run ruff format src/setup_course_github/retire_course.py tests/test_retire_course.py
uv run ruff check src/setup_course_github/retire_course.py tests/test_retire_course.py
uv run mypy --strict src/setup_course_github/retire_course.py
uv run pytest
git add src/setup_course_github/retire_course.py tests/test_retire_course.py
git commit -m "feat: add --dry-run flag to retire-course CLI"
```

### Task 3: Merge Feature 1

- [ ] **Step 1: Confirm the full suite passes with coverage**

Run: `uv run pytest`
Expected: PASS, 100% coverage.

- [ ] **Step 2: Merge and delete the branch**

```bash
git switch main
git merge --no-ff feature/retire-dry-run -m "Merge feature/retire-dry-run: retire-course --dry-run"
git branch -d feature/retire-dry-run
```

---

## Feature 2 — `notebooks.py` helper + `list-courses` command

**Branch:** `feature/list-courses`

### File Structure

- Create: `src/setup_course_github/notebooks.py` — shared notebook discovery + date range.
- Create: `src/setup_course_github/list_courses.py` — the new command.
- Create: `tests/test_notebooks.py`, `tests/test_list_courses.py`.
- Modify: `src/setup_course_github/retire_course.py` — use `notebooks.py` (behavior-preserving).
- Modify: `src/setup_course_github/config.py` — add `course_dirs` field + loader.
- Modify: `src/setup_course_github/init_config.py` — document `course_dirs` in the template.
- Modify: `pyproject.toml` — add the `list-courses` console script.
- Test: `tests/test_config.py`, `tests/test_init_config.py`.

### Task 4: Extract `notebooks.py`

**Files:**
- Create: `src/setup_course_github/notebooks.py`
- Test: `tests/test_notebooks.py`

**Interfaces:**
- Produces:
  - `is_marimo_notebook(path: Path) -> bool`
  - `find_notebooks(path: Path) -> tuple[list[Path], list[Path]]` → `(ipynb_files, marimo_files)`, each sorted.
  - `date_range(files: Iterable[Path]) -> str` → `"<first> → <last>"` or `"n/a"`.

- [ ] **Step 1: Create the feature branch**

```bash
git switch -c feature/list-courses
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_notebooks.py`:

```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_notebooks.py -v`
Expected: FAIL — `ModuleNotFoundError: setup_course_github.notebooks`

- [ ] **Step 4: Implement `notebooks.py`**

Create `src/setup_course_github/notebooks.py`:

```python
import re
from collections.abc import Iterable
from pathlib import Path

_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})\.\w+$")


def is_marimo_notebook(path: Path) -> bool:
    """Return True if a .py file looks like a marimo notebook."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return "import marimo" in text and "marimo.App()" in text


def find_notebooks(path: Path) -> tuple[list[Path], list[Path]]:
    """Return (ipynb_files, marimo_files) found directly in *path*, each sorted."""
    ipynb_files = sorted(path.glob("*.ipynb"))
    marimo_files = sorted(p for p in path.glob("*.py") if is_marimo_notebook(p))
    return ipynb_files, marimo_files


def date_range(files: Iterable[Path]) -> str:
    """Return '<first> → <last>' parsed from filenames, or 'n/a' if none match."""
    dates: list[str] = []
    for p in files:
        match = _DATE_PATTERN.search(p.name)
        if match:
            dates.append(match.group(1))
    dates.sort()
    if dates:
        return f"{dates[0]} → {dates[-1]}"
    return "n/a"
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_notebooks.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/notebooks.py tests/test_notebooks.py
uv run ruff check src/setup_course_github/notebooks.py tests/test_notebooks.py
uv run mypy --strict src/setup_course_github/notebooks.py
git add src/setup_course_github/notebooks.py tests/test_notebooks.py
git commit -m "feat: add shared notebooks helper module"
```

### Task 5: Refactor `retire_course.py` to use `notebooks.py`

**Files:**
- Modify: `src/setup_course_github/retire_course.py` (remove `_is_marimo_notebook`; use helpers in `_build_retirement_summary`)
- Modify: `tests/test_retire_course.py` (remove the one test that imports the deleted `_is_marimo_notebook`)
- Modify: `tests/test_notebooks.py` (receive the migrated marimo-markers test)

**Interfaces:**
- Consumes: `find_notebooks`, `date_range`, `is_marimo_notebook` from Task 4.

> **Correction (found during execution):** two errors in the original draft of
> this task. (1) `import re` must NOT be removed — `re.split(r"[><=!~;]", d)` in the
> dependency-stripping block still uses it. (2) `tests/test_retire_course.py`
> contains a pre-existing test `test_marimo_notebook_requires_both_markers` that
> imports the `_is_marimo_notebook` being deleted, and it asserts the
> exactly-one-marker→False case that `test_notebooks.py` does not otherwise cover.
> So this is not a "no test changes" refactor: migrate that test to
> `test_notebooks.py`, retargeting it to `is_marimo_notebook`.

- [ ] **Step 1: Confirm the existing retire tests are green before refactoring**

Run: `uv run pytest tests/test_retire_course.py -v`
Expected: PASS (baseline before refactor).

- [ ] **Step 2: Apply the refactor**

In `src/setup_course_github/retire_course.py`:

1. Add to the imports (after line 14, `from setup_course_github.config import load_config`):

```python
from setup_course_github.notebooks import date_range, find_notebooks
```

2. **Keep `import re`** — `re.split(r"[><=!~;]", d)` in the dependency-stripping
   block still uses it. (The original draft wrongly claimed `date_pattern` was
   its only user.)

3. Delete the `_is_marimo_notebook` function (the `re`-based `date_pattern` line
   inside `_build_retirement_summary` also goes, replaced in step 4). Then migrate
   its test: **remove** `test_marimo_notebook_requires_both_markers` from
   `tests/test_retire_course.py`, and **add** it to `tests/test_notebooks.py`
   importing `is_marimo_notebook` from `setup_course_github.notebooks`:

```python
def test_is_marimo_notebook_requires_both_markers(tmp_path: Path) -> None:
    """is_marimo_notebook requires BOTH markers — not just one."""
    import_only = tmp_path / "import_only.py"
    import_only.write_text("import marimo\n\nprint('hello')\n")
    assert not is_marimo_notebook(import_only)

    app_only = tmp_path / "app_only.py"
    app_only.write_text("# no import\napp = marimo.App()\n")
    assert not is_marimo_notebook(app_only)
```

4. In `_build_retirement_summary`, replace the notebook-counting block (lines 99-101) and the date-range block (lines 112-123) so the function body reads:

```python
    dirpath = Path(dirname)

    # --- count notebooks ---------------------------------------------------
    ipynb_files, marimo_files = find_notebooks(dirpath)
    nb_count = len(ipynb_files) + len(marimo_files)

    if ipynb_files and marimo_files:
        nb_label = f"{nb_count} (.ipynb + marimo .py)"
    elif ipynb_files:
        nb_label = f"{nb_count} (.ipynb)"
    elif marimo_files:
        nb_label = f"{nb_count} (marimo .py)"
    else:
        nb_label = "0"

    # --- date range from filenames -----------------------------------------
    date_range_str = date_range(ipynb_files + marimo_files)
```

Then update the summary line that used `date_range` (was line 147) to use the local variable:

```python
        f"  Date range: {date_range_str}",
```

- [ ] **Step 3: Run the retire + notebooks suites to verify behavior is preserved**

Run: `uv run pytest tests/test_retire_course.py tests/test_notebooks.py -v`
Expected: PASS. The retire suite has one fewer test than Step 1 (the marimo-markers
test moved to `test_notebooks.py`, where it now appears) — every other retire test
still passes unchanged, confirming the refactor preserved behavior.

- [ ] **Step 4: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/retire_course.py tests/test_retire_course.py tests/test_notebooks.py
uv run ruff check src/setup_course_github/retire_course.py tests/test_retire_course.py tests/test_notebooks.py
uv run mypy --strict src/setup_course_github/retire_course.py
git add src/setup_course_github/retire_course.py tests/test_retire_course.py tests/test_notebooks.py
git commit -m "refactor: use shared notebooks helper in retire_course"
```

### Task 6: Add `course_dirs` to config

**Files:**
- Modify: `src/setup_course_github/config.py` (`CourseConfig` + loader)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `CourseConfig.course_dirs: list[str]` (default `[]`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_config.py`:

```python
COURSE_DIRS_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"
course_dirs = ["~/Courses/Current", "/other/courses"]
"""

COURSE_DIRS_NOT_LIST_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"
course_dirs = "not-a-list"
"""


def test_load_config_course_dirs_list(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(COURSE_DIRS_TOML)
    config = load_config(config_file)
    assert config.course_dirs == ["~/Courses/Current", "/other/courses"]


def test_load_config_course_dirs_absent_defaults_empty(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(MINIMAL_TOML)
    config = load_config(config_file)
    assert config.course_dirs == []


def test_load_config_course_dirs_not_list_raises(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(COURSE_DIRS_NOT_LIST_TOML)
    with pytest.raises(ConfigError):
        load_config(config_file)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_config.py -k course_dirs -v`
Expected: FAIL — `CourseConfig` has no attribute `course_dirs`.

- [ ] **Step 3: Implement the field and loader**

In `src/setup_course_github/config.py`:

1. Add the dataclass field (after `additional_files`, line 29):

```python
    course_dirs: list[str] = field(default_factory=list)
```

2. In `load_config`, after the `additional_files` block (after line 129) add:

```python
    # Course directories: optional list of dirs scanned by `list-courses`
    raw_course_dirs: object = paths_section.get("course_dirs", [])
    if not isinstance(raw_course_dirs, list):
        raise ConfigError("course_dirs must be a list of directory paths")
    course_dirs: list[str] = [str(d) for d in raw_course_dirs]
```

3. Add `course_dirs=course_dirs,` to the `CourseConfig(...)` constructor call (after `default_private=default_private,`, line 141).

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_config.py -k course_dirs -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/config.py tests/test_config.py
uv run ruff check src/setup_course_github/config.py tests/test_config.py
uv run mypy --strict src/setup_course_github/config.py
git add src/setup_course_github/config.py tests/test_config.py
git commit -m "feat: add course_dirs config option"
```

### Task 7: Document `course_dirs` in the config template

**Files:**
- Modify: `src/setup_course_github/init_config.py` (`CONFIG_TEMPLATE`)
- Test: `tests/test_init_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_init_config.py` (match the existing style of asserting on template content — check the file for the exact import of `CONFIG_TEMPLATE` or `create_config`):

```python
def test_config_template_mentions_course_dirs() -> None:
    from setup_course_github.init_config import CONFIG_TEMPLATE

    assert "course_dirs" in CONFIG_TEMPLATE
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_init_config.py -k course_dirs -v`
Expected: FAIL.

- [ ] **Step 3: Add the commented example to the template**

In `src/setup_course_github/init_config.py`, inside `CONFIG_TEMPLATE`, add under the `[paths]` section (after the `additional_files` comment block, before `[defaults]`):

```
# Optional: directories that `list-courses` scans for active courses.
# Each entry is a directory whose immediate subdirectories may be courses
# (a course = a subdir containing a .git folder and at least one notebook).
# Examples:
#   course_dirs = ["~/Courses/Current"]
#   course_dirs = ["~/Courses/Current", "~/Courses/Consulting"]
# course_dirs = []
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_init_config.py -k course_dirs -v`
Expected: PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
uv run ruff format src/setup_course_github/init_config.py tests/test_init_config.py
uv run ruff check src/setup_course_github/init_config.py tests/test_init_config.py
git add src/setup_course_github/init_config.py tests/test_init_config.py
git commit -m "docs: document course_dirs in config template"
```

### Task 8: Implement `list_courses.py` core logic

**Files:**
- Create: `src/setup_course_github/list_courses.py`
- Test: `tests/test_list_courses.py`

**Interfaces:**
- Consumes: `find_notebooks`, `date_range` (Task 4); `load_config`, `CourseConfig` (config).
- Produces:
  - `is_course(path: Path) -> bool`
  - `course_summary_line(path: Path) -> str` → `"<name> — <N> notebooks (<range>)"`
  - `resolve_scan_dirs(cli_dirs: list[str], config: CourseConfig) -> list[Path]`
  - `find_active_courses(scan_dirs: list[Path]) -> list[Path]`
  - `find_archived_courses(archive_path: Path) -> dict[str, list[Path]]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_list_courses.py`:

```python
from pathlib import Path

from setup_course_github.config import CourseConfig
from setup_course_github.list_courses import (
    course_summary_line,
    find_active_courses,
    find_archived_courses,
    is_course,
    resolve_scan_dirs,
)

MARIMO_SOURCE = "import marimo\n\napp = marimo.App()\n"


def _make_course(parent: Path, name: str, notebook: str = "lesson.ipynb") -> Path:
    course = parent / name
    course.mkdir()
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
    (tmp_path / "2025" / "old-course").mkdir(parents=True)
    (tmp_path / "2026" / "newer-course").mkdir(parents=True)
    result = find_archived_courses(tmp_path)
    assert list(result.keys()) == ["2025", "2026"]
    assert [p.name for p in result["2026"]] == ["newer-course"]


def test_find_archived_courses_missing_archive(tmp_path: Path) -> None:
    missing = tmp_path / "no-archive"
    assert find_archived_courses(missing) == {}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_list_courses.py -v`
Expected: FAIL — `ModuleNotFoundError: setup_course_github.list_courses`

- [ ] **Step 3: Implement the core logic**

Create `src/setup_course_github/list_courses.py`:

```python
import argparse
from pathlib import Path

from setup_course_github import __author__, __email__, __version__
from setup_course_github.config import CourseConfig, load_config
from setup_course_github.notebooks import date_range, find_notebooks


def is_course(path: Path) -> bool:
    """A course is a directory with a .git subdir and at least one notebook."""
    if not (path / ".git").is_dir():
        return False
    ipynb_files, marimo_files = find_notebooks(path)
    return bool(ipynb_files or marimo_files)


def course_summary_line(path: Path) -> str:
    """Return '<name> — <N> notebooks (<date range>)' for a course directory."""
    ipynb_files, marimo_files = find_notebooks(path)
    count = len(ipynb_files) + len(marimo_files)
    span = date_range(ipynb_files + marimo_files)
    return f"{path.name} — {count} notebooks ({span})"


def resolve_scan_dirs(cli_dirs: list[str], config: CourseConfig) -> list[Path]:
    """Choose which directories to scan: CLI args, else config, else cwd."""
    if cli_dirs:
        return [Path(d).expanduser() for d in cli_dirs]
    if config.course_dirs:
        return [Path(d).expanduser() for d in config.course_dirs]
    return [Path(".")]


def find_active_courses(scan_dirs: list[Path]) -> list[Path]:
    """Return course directories found directly under each scan dir, sorted."""
    courses: list[Path] = []
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for child in sorted(scan_dir.iterdir()):
            if child.is_dir() and is_course(child):
                courses.append(child)
    return courses


def find_archived_courses(archive_path: Path) -> dict[str, list[Path]]:
    """Return {year: [course dirs]} found under archive_path/<year>/<course>."""
    result: dict[str, list[Path]] = {}
    if not archive_path.is_dir():
        return result
    for year_dir in sorted(archive_path.iterdir()):
        if not year_dir.is_dir():
            continue
        courses = sorted(c for c in year_dir.iterdir() if c.is_dir())
        if courses:
            result[year_dir.name] = courses
    return result
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_list_courses.py -v`
Expected: PASS (all core-logic tests)

- [ ] **Step 5: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run ruff check src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run mypy --strict src/setup_course_github/list_courses.py
git add src/setup_course_github/list_courses.py tests/test_list_courses.py
git commit -m "feat: add list_courses core discovery logic"
```

### Task 9: Add `list_courses.main()` and the console script

**Files:**
- Modify: `src/setup_course_github/list_courses.py` (add `main`)
- Modify: `pyproject.toml` (`[project.scripts]`)
- Test: `tests/test_list_courses.py`

**Interfaces:**
- Consumes: all Task 8 functions.
- Produces: `main(argv: list[str] | None = None) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_list_courses.py`:

```python
import pytest
from unittest.mock import patch

from setup_course_github.list_courses import main


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
    (archive / "2026" / "gone-course").mkdir(parents=True)

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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_list_courses.py -k main -v`
Expected: FAIL — `cannot import name 'main'`.

- [ ] **Step 3: Implement `main`**

Append to `src/setup_course_github/list_courses.py`:

```python
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
        "dirs",
        nargs="*",
        help="Directories to scan (overrides course_dirs from config)",
    )
    args = parser.parse_args(argv)

    config = load_config()
    scan_dirs = resolve_scan_dirs(args.dirs, config)

    active = find_active_courses(scan_dirs)
    print("Active courses:")
    if active:
        for course in active:
            print(f"  {course_summary_line(course)}")
    else:
        print("  No active courses found")

    archived = find_archived_courses(config.archive_path)
    print("\nArchived courses:")
    if archived:
        for year, courses in archived.items():
            print(f"  {year}:")
            for course in courses:
                print(f"    {course_summary_line(course)}")
    else:
        print("  No archived courses found")


if __name__ == "__main__":  # pragma: no cover
    main()
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_list_courses.py -v`
Expected: PASS (all)

- [ ] **Step 5: Register the console script**

In `pyproject.toml`, under `[project.scripts]` (after line 33, the `archive-course` entry), add:

```toml
    list-courses = "setup_course_github.list_courses:main"
```

- [ ] **Step 6: Reinstall the project so the entry point is available**

Run: `uv sync`
Expected: succeeds; `list-courses` becomes an available command.

- [ ] **Step 7: Smoke-test the real command**

Run: `uv run list-courses --version`
Expected: prints the version + PyPI URL + author line (confirms the entry point resolves).

- [ ] **Step 8: Format, lint, type-check, full suite, commit**

```bash
uv run ruff format src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run ruff check src/setup_course_github/list_courses.py tests/test_list_courses.py
uv run mypy --strict src/setup_course_github/list_courses.py
uv run pytest
git add src/setup_course_github/list_courses.py tests/test_list_courses.py pyproject.toml
git commit -m "feat: add list-courses command and console script"
```

### Task 10: Merge Feature 2

- [ ] **Step 1: Full suite with coverage**

Run: `uv run pytest`
Expected: PASS, 100% coverage.

- [ ] **Step 2: Merge and delete the branch**

```bash
git switch main
git merge --no-ff feature/list-courses -m "Merge feature/list-courses: list-courses command + notebooks helper"
git branch -d feature/list-courses
```

---

## Feature 3 — PDF export in `archive-course`

**Branch:** `feature/archive-pdf`

### File Structure

- Modify: `src/setup_course_github/archive_course.py` — add `_export_notebook_to_pdf`, `export_pdf` param, `--no-pdf` flag, summary changes.
- Test: `tests/test_archive_course.py`.

### Task 11: Extract shared `_export_notebook` helper + add `_export_notebook_to_pdf`

To keep DRY (per the pre-flight decision), factor the shared subprocess/try-except
body of `_export_notebook_to_html` into a single `_export_notebook(nb_path,
course_path, fmt, label)` helper, and make both `_export_notebook_to_html` and the
new `_export_notebook_to_pdf` thin one-line callers. The public helper names are
preserved so existing tests and call sites that patch them keep working.

**Files:**
- Modify: `src/setup_course_github/archive_course.py`
- Test: `tests/test_archive_course.py`

**Interfaces:**
- Produces:
  - `_export_notebook(nb_path: Path, course_path: Path, fmt: str, label: str) -> bool`
  - `_export_notebook_to_html(nb_path: Path, course_path: Path) -> bool` (thin caller — unchanged signature)
  - `_export_notebook_to_pdf(nb_path: Path, course_path: Path) -> bool` (thin caller)

- [ ] **Step 1: Create the feature branch**

```bash
git switch -c feature/archive-pdf
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_archive_course.py`. Its current top-level imports are
`zipfile`, `Path`, `MagicMock, patch`, `pytest`, and `archive_course, main` —
**it does not import `subprocess`**, which the error-path tests below need. Add
`import subprocess` to the top of the file first, then add:

```python
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
    assert cmd == ["uv", "run", "jupyter", "nbconvert", "--to", "webpdf", "lesson.ipynb"]


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
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_archive_course.py -k to_pdf -v`
Expected: FAIL — `cannot import name '_export_notebook_to_pdf'`.

- [ ] **Step 4: Refactor to a shared helper and add the PDF caller**

In `src/setup_course_github/archive_course.py`, **replace** the entire existing
`_export_notebook_to_html` function (lines 11-30) with the shared helper plus two
thin callers:

```python
def _export_notebook(
    nb_path: Path, course_path: Path, fmt: str, label: str
) -> bool:
    """Export a notebook to *fmt* via nbconvert. Returns True on success.

    *label* is the human-readable format name used in warning messages.
    """
    # Use the notebook's relative path from the course dir so nbconvert
    # can find it regardless of spaces in the name.
    relative = nb_path.relative_to(course_path)
    try:
        subprocess.run(
            ["uv", "run", "jupyter", "nbconvert", "--to", fmt, str(relative)],
            cwd=str(course_path),
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if exc.stderr else ""
        print(
            f"  Warning: failed to export {nb_path.name} to {label}: {stderr.strip()}"
        )
        return False
    except FileNotFoundError:
        print(f"  Warning: jupyter nbconvert not found, skipping {label} export")
        return False


def _export_notebook_to_html(nb_path: Path, course_path: Path) -> bool:
    """Export a single notebook to HTML. Returns True on success."""
    return _export_notebook(nb_path, course_path, "html", "HTML")


def _export_notebook_to_pdf(nb_path: Path, course_path: Path) -> bool:
    """Export a single notebook to PDF via webpdf. Returns True on success."""
    return _export_notebook(nb_path, course_path, "webpdf", "PDF")
```

Note on preserved behavior: the HTML `FileNotFoundError` message is byte-identical
to the original (`...skipping HTML export`), and the HTML nbconvert command is
still `--to html`, so the existing `test_archive_html_export` and
`test_archive_html_export_jupyter_not_found` assertions continue to hold. The
HTML `CalledProcessError` message gains ` to HTML` before the colon; no existing
test asserts that exact wording (they assert only the substring `"Warning"`).

- [ ] **Step 5: Run to verify the new PDF tests pass and existing HTML tests stay green**

Run: `uv run pytest tests/test_archive_course.py -k "to_pdf or html_export" -v`
Expected: PASS — the 3 new PDF tests pass and the existing HTML-export tests
still pass (the refactor preserved their behavior).

- [ ] **Step 6: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/archive_course.py tests/test_archive_course.py
uv run ruff check src/setup_course_github/archive_course.py tests/test_archive_course.py
uv run mypy --strict src/setup_course_github/archive_course.py
git add src/setup_course_github/archive_course.py tests/test_archive_course.py
git commit -m "refactor: share nbconvert export helper; add PDF export helper"
```

### Task 12: Wire PDF export into `archive_course` + summary + `--no-pdf`

**Files:**
- Modify: `src/setup_course_github/archive_course.py` (`archive_course` body, summary, `main`)
- Test: `tests/test_archive_course.py`

**Interfaces:**
- Consumes: `_export_notebook_to_pdf` (Task 11).
- Produces: `archive_course(dirname, output=None, export_html=True, export_pdf=True) -> Path`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_archive_course.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_archive_course.py -k "pdf" -v`
Expected: FAIL (`export_pdf` not accepted; `--no-pdf` unrecognized; no `PDF exports` line).

- [ ] **Step 3: Add `export_pdf` and the PDF export loop**

In `archive_course` change the signature (line 33-37):

```python
def archive_course(
    dirname: str,
    output: str | None = None,
    export_html: bool = True,
    export_pdf: bool = True,
) -> Path:
```

After the HTML export loop (after line 59, `html_exported += 1`), add the PDF loop:

```python
    # Export notebooks to PDF if requested
    pdf_exported = 0
    if export_pdf and notebooks:
        print("Exporting notebooks to PDF...")
        for nb_path in notebooks:
            if _export_notebook_to_pdf(nb_path, course_path):
                pdf_exported += 1
```

- [ ] **Step 4: Exclude `.pdf` from "Other files"**

Replace the exclusion block (lines 92-100) with:

```python
    # Collect non-notebook, non-HTML, non-PDF files for the summary
    notebook_names = {nb.name for nb in notebooks}
    html_names = {nb.with_suffix(".html").name for nb in notebooks}
    pdf_names = {nb.with_suffix(".pdf").name for nb in notebooks}
    with zipfile.ZipFile(zip_path, "r") as zf:
        other_files = sorted(
            Path(name).name
            for name in zf.namelist()
            if Path(name).name not in notebook_names
            and Path(name).name not in html_names
            and Path(name).name not in pdf_names
        )
```

- [ ] **Step 5: Extend the notebook summary lines and add the PDF-exports line**

Replace the notebook-listing block (lines 107-116) with:

```python
    if notebooks:
        print("Notebooks:")
        for nb in notebooks:
            parts = [nb.name]
            html_path = nb.with_suffix(".html")
            if export_html and html_path.exists():
                parts.append(html_path.name)
            pdf_path = nb.with_suffix(".pdf")
            if export_pdf and pdf_path.exists():
                parts.append(pdf_path.name)
            print("  " + " + ".join(parts))
    if export_html and html_exported > 0:
        print(f"HTML exports: {html_exported}")
    if export_pdf and pdf_exported > 0:
        print(f"PDF exports: {pdf_exported}")
```

- [ ] **Step 6: Add the `--no-pdf` flag in `main`**

After the `--no-html` argument block (after line 155), add:

```python
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        default=False,
        help="Skip PDF export of notebooks",
    )
```

And change the `archive_course(...)` call (lines 158-162) to:

```python
    archive_course(
        dirname=args.dirname,
        output=args.output,
        export_html=not args.no_html,
        export_pdf=not args.no_pdf,
    )
```

- [ ] **Step 7: Fix existing tests broken by PDF-on-by-default**

Turning PDF on by default changes the behavior of seven pre-existing tests that
were written when only HTML was default-on. Each must be updated. **These are the
only pre-existing tests that need changing — do not touch any others.**

Two groups:

**(a) Tests that must now pass `export_pdf=False`** — they either assert the
nbconvert subprocess call count/args (HTML only) or create a real notebook with
no subprocess mock (which would otherwise trigger a real `webpdf` run). Add
`export_pdf=False` to the `archive_course(...)` call in each:

- `test_archive_html_export` — asserts `mock_run.assert_called_once_with(... html ...)`; without this it is now called twice (html + webpdf).
- `test_archive_no_html_flag` — asserts `mock_run.assert_not_called()`; webpdf would call it.
- `test_archive_summary_lists_notebooks_and_other_files` — real notebook, no mock; would shell out to webpdf.
- `test_archive_summary_no_other_files_section_when_only_notebooks` — real notebook, no mock.
- `test_archive_notebook_with_spaces_in_name` — asserts `mock_run.assert_called_once_with(... html ...)`.
- `test_archive_no_html_ignores_existing_html_file` — real notebook, no mock; tests summary pairing with export off.

Example (the change is the same shape in each — add the one kwarg):

```python
    # before
    archive_course(str(course_dir), output=out, export_html=False)
    # after
    archive_course(str(course_dir), output=out, export_html=False, export_pdf=False)
```

**(b) The `main` call-args test** — `test_main_calls_archive_course` asserts the
exact kwargs `main` forwards; `main` now also passes `export_pdf`. Update its
expected call:

```python
    mock_archive.assert_called_once_with(
        dirname=str(course_dir),
        output=None,
        export_html=True,
        export_pdf=True,
    )
```

Leave all other existing tests unchanged: tests that mock `subprocess.run` with a
generic `MagicMock` and assert only substrings (e.g. `HTML exports: N`) stay green
because the extra webpdf call is absorbed by the mock and produces no `.pdf` file.

- [ ] **Step 8: Run to verify pass**

Run: `uv run pytest tests/test_archive_course.py -v`
Expected: PASS (all)

- [ ] **Step 9: Format, lint, type-check, full suite, commit**

```bash
uv run ruff format src/setup_course_github/archive_course.py tests/test_archive_course.py
uv run ruff check src/setup_course_github/archive_course.py tests/test_archive_course.py
uv run mypy --strict src/setup_course_github/archive_course.py
uv run pytest
git add src/setup_course_github/archive_course.py tests/test_archive_course.py
git commit -m "feat: export notebooks to PDF by default in archive-course"
```

### Task 13: Merge Feature 3

- [ ] **Step 1: Full suite with coverage**

Run: `uv run pytest`
Expected: PASS, 100% coverage.

- [ ] **Step 2: Merge and delete the branch**

```bash
git switch main
git merge --no-ff feature/archive-pdf -m "Merge feature/archive-pdf: PDF export in archive-course"
git branch -d feature/archive-pdf
```

---

## Feature 4 — Docs, mutation audit, release

**Branch:** `feature/docs-and-release` (docs) — release steps run on `main`.

### Task 14: Update README and manual

**Files:**
- Modify: `README.md`
- Modify: the manual (locate the Markdown manual — likely `docs/manual.md` or similar; grep for the archive-course section).

- [ ] **Step 1: Create the branch**

```bash
git switch -c feature/docs-and-release
```

- [ ] **Step 2: Locate the docs**

Run: `ls README.md`
Run: `grep -rl "archive-course" --include=*.md .`
Expected: identifies README.md and the manual file.

- [ ] **Step 3: Update the docs**

In both README.md and the manual, add/adjust:
- `retire-course` usage: document `--dry-run` (preview without changing GitHub or moving files).
- A new `list-courses` section: what it lists (active + archived), the `course_dirs` config key, positional-dir override, and that it is read-only.
- `archive-course`: note PDF export is on by default (webpdf/Chromium), `--no-pdf` to skip, and the one-time `uv run playwright install chromium` setup.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document dry-run, list-courses, and PDF export in README"
```

(Commit the manual separately.)

```bash
git add <manual-file>
git commit -m "docs: document new features in the manual"
```

- [ ] **Step 5: Merge and delete the branch**

```bash
git switch main
git merge --no-ff feature/docs-and-release -m "Merge feature/docs-and-release: docs for new features"
git branch -d feature/docs-and-release
```

### Task 15: Mutation-testing audit

- [ ] **Step 1: Run the audit on main**

Run: `uv run mutmut run`
(This is slow. Per project memory, `mutmut results` may crash on 2.x; tally survivors via
`sqlite3 .mutmut-cache "SELECT status,COUNT(*) FROM Mutant GROUP BY status"` if needed.)

- [ ] **Step 2: Triage survivors on the new code only**

Focus on `list_courses.py`, `notebooks.py`, and the changed regions of
`retire_course.py` / `archive_course.py`. Kill only survivors that reflect a real
logic gap (operator/keyword/boundary/default mutations on non-string lines).
Ignore string-literal mutations in printed output/help text, type-annotation
mutations, and `pragma: no cover` lines (per project convention).

- [ ] **Step 3: For each real gap, add a killing test (TDD), commit**

For each kept survivor: `uv run mutmut apply <id>` → confirm a test now fails →
`git checkout -- <src file>` → write the test that kills it → verify green →
commit (one small commit per gap).

### Task 16: Version bump, tag, publish

- [ ] **Step 1: Bump the version**

The version is declared **only** in `pyproject.toml:3` (`version = "3.0.14"`);
`__version__` is read from package metadata at runtime, so there is no version
string to edit in `__init__.py`. Bump `pyproject.toml` from `3.0.14` to `3.1.0`
(new features → minor bump).

- [ ] **Step 2: Commit and tag**

```bash
git add pyproject.toml
git commit -m "Bump version to 3.1.0"
git tag v3.1.0
```

- [ ] **Step 3: Clean dist and build**

```bash
rm -rf dist/*
uv build
```

- [ ] **Step 4: Publish (only when you decide to release)**

Run: `uv publish`
Expected: uploads to PyPI. (Confirm with the user before publishing.)

- [ ] **Step 5: Push main and tags**

```bash
git push origin main
git push origin v3.1.0
```

---

## Self-Review Notes

- **Spec coverage:** Feature 1 → Tasks 1-3. Feature 2 (`list-courses` + `course_dirs` config + `notebooks.py` refactor + init_config template) → Tasks 4-10. Feature 3 (PDF export) → Tasks 11-13. Cross-cutting (docs, version+tag, dist cleanup, mutmut audit) → Tasks 14-16. All spec sections mapped.
- **Type consistency:** `find_notebooks` returns `tuple[list[Path], list[Path]]` and is consumed with that shape in `is_course`, `course_summary_line`, and `_build_retirement_summary`. `date_range(Iterable[Path]) -> str` used consistently. `retire_course(dirname, keep_public, dry_run)` and `archive_course(dirname, output, export_html, export_pdf)` signatures match every call site and test.
- **Ambiguity resolved:** active courses are a flat alphabetical list per scan dir (no per-dir grouping); archived courses grouped by year ascending.
```
