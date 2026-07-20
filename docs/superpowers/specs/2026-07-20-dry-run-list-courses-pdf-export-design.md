# Design: dry-run retire, list-courses, PDF export

Date: 2026-07-20

Three independent features added to the `course-setup` CLI toolkit:

1. `retire-course --dry-run` — preview a retirement without mutating anything.
2. `list-courses` — a new read-only command listing active and archived courses.
3. PDF export in `archive-course` — export notebooks to PDF (via webpdf) alongside HTML.

Each feature is developed on its own feature branch, TDD, with 100% line
coverage, ruff + mypy strict, and merged to main when done. A mutation-testing
audit (`uv run mutmut run`) runs before the release that ships these.

---

## Feature 1 — `retire-course --dry-run`

### Goal

Let the user preview exactly what `retire-course` *would* do — which repo, where
it would be archived, whether it would be made private — without performing any
irreversible action.

### Behavior

`retire_course()` gains a keyword parameter `dry_run: bool = False`. When
`dry_run` is `True`, only the read-only steps run:

| Step | Normal run | Dry run |
|------|-----------|---------|
| `_check_not_inside_course(dirname)` | ✅ | ✅ (cheap guard, no mutation) |
| `load_config()` | ✅ | ✅ (needed for archive path) |
| `get_remote_url` + `parse_repo_name` | ✅ | ✅ (local git, no network) |
| `get_github()` / `repo.edit(private=True)` | ✅ | ❌ skipped entirely — no token or network needed |
| `_confirm_create_dir(dest)` (`mkdir`) | ✅ | ❌ skipped — do not create the archive dir |
| `_build_retirement_summary(...)` | ✅ | ✅ (reads disk only) |
| `shutil.move(dirname, dest)` | ✅ | ❌ skipped |

Output in dry-run mode:

```
[DRY RUN] Would retire <dirname> → <dest>
<retirement summary>
```

The existing summary already ends with `GitHub repo: <url> (now private)` or
`(still public)`; in dry-run this correctly describes the *intended* action, so
no change to the summary text is required. The `kept_public` flag still controls
that line.

`main()`'s multi-directory loop and error aggregation are unchanged; the
`--dry-run` flag is parsed once and passed to every `retire_course()` call.

### CLI

```
retire-course [--keep-public] [--dry-run] dirname [dirname ...]
```

### Tests (TDD, write first)

- Dry-run does **not** move the directory (source still exists, `dest` not created).
- Dry-run does **not** touch GitHub (`get_github` mocked; assert not called).
- Dry-run prints the `[DRY RUN]` banner and the full summary.
- Dry-run with `--keep-public` shows the "(still public)" line.
- Normal (non-dry-run) behavior is unaffected (existing tests stay green).

---

## Feature 2 — `list-courses` (new command)

### Goal

A read-only command that lists the user's courses — both the active ones in
their working directories and the archived ones — with a quick summary of each.
Never mutates anything, never touches the network or GitHub.

### Config change

New optional key under `[paths]`: `course_dirs`, a **list** of directories to
scan for active courses.

```toml
[paths]
course_dirs = ["~/Courses/Current"]
```

- `CourseConfig` gains `course_dirs: list[str] = field(default_factory=list)`.
- The loader reads `paths_section.get("course_dirs", [])`, raising `ConfigError`
  if it is present but not a list; each entry is coerced to `str`. `~` is
  expanded at use time via `Path(d).expanduser()` (not stored expanded).
- `init_config.py` `CONFIG_TEMPLATE` gains a commented example under `[paths]`.

### What counts as a course

A directory is a course if it contains **both**:

- a `.git/` subdirectory, **and**
- at least one notebook — a `*.ipynb` file, or a `*.py` file that is a marimo
  notebook (reusing the `_is_marimo_notebook` heuristic).

### Scan resolution order (active courses)

1. Positional CLI arguments, if any (`list-courses DIR [DIR ...]`) — override config.
2. Otherwise `config.course_dirs`.
3. Otherwise fall back to `.` (current working directory).

Each scan directory's immediate children are inspected (non-recursive) for
courses.

### Output

Two sections. Each course line:

```
<name> — <N> notebooks (<first-date> → <last-date>)
```

where the date range is parsed from notebook filenames (the same
`(\d{4}-\d{2}-\d{2})` pattern used by `retire_course`); when no dated notebooks
exist the range is `n/a`.

- **Active courses** — courses found in the scanned dirs, sorted alphabetically.
  If a directory does not exist or contains no courses, that is noted; if no
  active courses are found at all, print `No active courses found`.
- **Archived courses** — courses under `archive_path/*/*` (year → course),
  grouped by year (ascending), courses alphabetical within a year. If the
  archive path is missing or empty, print `No archived courses found`.

`--version` is supported, matching the other commands.

### Shared-logic refactor

The notebook-counting and date-range logic currently lives inline in
`retire_course.py` (`_is_marimo_notebook`, the `*.ipynb`/marimo globbing, and the
`date_pattern` range computation). Extract a small, behavior-preserving helper
module `notebooks.py`:

- `is_marimo_notebook(path: Path) -> bool`
- `find_notebooks(path: Path) -> tuple[list[Path], list[Path]]` — returns
  `(ipynb_files, marimo_files)`.
- `date_range(files: Iterable[Path]) -> str` — returns `"<first> → <last>"` or
  `"n/a"`.

`retire_course.py` is updated to import and use these (its existing tests must
stay green, guaranteeing behavior is preserved), and `list_courses.py` uses them
too. This avoids duplicating the logic across the two modules.

### New console script

```toml
[project.scripts]
list-courses = "setup_course_github.list_courses:main"
```

### Tests (TDD, write first)

- A dir with `.git` + a notebook is listed; a dir with `.git` but no notebook is
  not; a dir with a notebook but no `.git` is not.
- Marimo `.py` notebooks count; non-marimo `.py` files do not.
- Positional args override configured `course_dirs`; config is used when no args;
  cwd is used when neither is set.
- Archived courses are discovered under `archive_path/<year>/<name>` and grouped
  by year.
- Date range is rendered from filenames; `n/a` when undated.
- Empty-state messages for no active / no archived courses.
- Config loader: `course_dirs` accepted as a list; rejected (ConfigError) when
  not a list; absent → empty list.
- `notebooks.py` helpers covered directly; `retire_course` tests remain green.

---

## Feature 3 — PDF export in `archive-course`

### Goal

Export each notebook to PDF alongside the existing HTML export, so archived
courses have a print-friendly copy. On by default (archiving happens at most
~once per day, so the extra time is acceptable), with an opt-out flag.

### Engine

`nbconvert --to webpdf` (headless Chromium via playwright). No LaTeX toolchain
required. First use needs Chromium installed once
(`uv run playwright install chromium`).

### Behavior

- New helper `_export_notebook_to_pdf(nb_path: Path, course_path: Path) -> bool`,
  mirroring `_export_notebook_to_html`: runs
  `uv run jupyter nbconvert --to webpdf <relative>` with `cwd=course_path`,
  returning `True` on success.
- **Graceful degradation** (same pattern as HTML): on
  `subprocess.CalledProcessError` (e.g. webpdf/Chromium not installed) print a
  warning and return `False`; on `FileNotFoundError` warn and return `False`.
  A machine without the engine degrades to "PDF skipped," never a crash.
- `archive_course()` gains `export_pdf: bool = True`. After the HTML export loop,
  if `export_pdf and notebooks`, export each notebook to PDF and count
  `pdf_exported`.
- Summary:
  - notebook lines extend from `nb + html` to include ` + <pdf>` when the PDF
    exists;
  - add a `PDF exports: <N>` line when `export_pdf and pdf_exported > 0`;
  - add the `.pdf` names to the set excluded from the "Other files" listing
    (alongside the existing notebook and `.html` exclusions), so PDFs are not
    misreported as other files.

### CLI

```
archive-course [--output PATH] [--no-html] [--no-pdf] dirname
```

`export_pdf=not args.no_pdf` is passed through.

### Tests (TDD, write first)

- With `export_pdf=True` and notebooks present, `_export_notebook_to_pdf` is
  invoked per notebook (subprocess mocked) and `PDF exports: N` appears.
- `--no-pdf` skips PDF export entirely (no invocation, no `PDF exports` line).
- A failed PDF export (mocked `CalledProcessError`) warns and continues; the
  archive is still produced.
- `FileNotFoundError` path warns and continues.
- Summary notebook lines include the `.pdf` name when the PDF exists.
- `.pdf` files are excluded from the "Other files" section.
- HTML-only behavior (existing tests) stays green.

---

## Cross-cutting

- **Branches:** one feature branch per feature, merged to main when complete,
  branch deleted immediately after merge.
- **Docs:** update `README.md` and the manual for the new `--dry-run` flag, the
  `list-courses` command (+ the `course_dirs` config key), and the `--no-pdf`
  flag / PDF-on-by-default behavior.
- **Version:** bump the project version once the three features land; add the
  matching git tag. Delete old `dist/` artifacts before building/publishing.
- **Quality gates:** ruff format + ruff check, mypy strict, 100% line coverage
  throughout; a `mutmut run` audit before the release that ships these.
