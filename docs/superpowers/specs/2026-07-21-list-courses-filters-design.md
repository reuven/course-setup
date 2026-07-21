# Design: list-courses filtering, summary default, and archive junk fix

Date: 2026-07-21

`list-courses` (shipped in 3.1.0) currently dumps every active course and every
directory under `archive_path/*/*` with no filtering, producing hundreds of
lines including non-course junk (`.git`, `__pycache__`, `.ipynb_checkpoints`,
`0 notebooks` entries, and non-year folders treated as year groups). This design
fixes the archive-listing correctness bug and adds filtering so the command is
usable on a large archive.

Target version: **3.2.0** (bug fix + new flags; includes one breaking CLI change).

---

## 1. Correctness fix — what counts, and how the archive is grouped

### Archived-course detection (new)

A directory under a year folder is an **archived course** iff:

- its name is **not hidden** (does not start with `.`), **and**
- its name is **not junk** — not in
  `JUNK_NAMES = {"__pycache__", "build", "dist", "bin", "include", "lib", "node_modules"}`, **and**
- it contains **≥1 notebook** (`*.ipynb` or a marimo `.py`, via `find_notebooks`).

The notebook requirement removes every `0 notebooks` entry; the name rules remove
`.git`, `.ipynb_checkpoints`, `.venv`, `.ruff_cache`, `.hypothesis`, `.idea`,
`__pycache__`, etc. Archived courses are **not** required to still contain `.git`
(archived repos may have had it stripped).

### Year grouping (new)

Only archive-root children whose name matches `^\d{4}$` are treated as year
groups. All other archive-root directories (`build`, `dist`, `exercises`,
`cisco1`, `oreilly-2022-q2-first-steps`, …) are ignored. **Accepted trade-off:**
loose course directories sitting directly in the archive root (not under a year)
are not listed.

### Active detection (unchanged)

Active course = directory with a `.git` subdir **and** ≥1 notebook.

---

## 2. Default view and section selection

- **`list-courses`** (no flags): active courses in full, then a single archive
  summary line:
  `Archived: <N> courses across <minYear>–<maxYear> — use --archived to list them.`
  - `<minYear>–<maxYear>` uses an en-dash; if only one year is present, show just
    that year (no range). If there are no archived courses: `Archived: none`.
- **`--active`**: show the active section only (no archive section at all).
- **`--archived`**: show the archive section only, expanded and grouped by year.
- **Both `--active` and `--archived`**: show both sections in full (active list +
  expanded archive).

---

## 3. Filters

### `--year YYYY`

Restrict the archive listing to a single year and expand it. Applies to the
archive section only (active courses are not year-organized). Passing `--year`
implies the archive is shown expanded even without `--archived`.

### Name match (positional) — BREAKING CHANGE

- Positional arguments (`list-courses cisco`) are now **name filters**:
  case-insensitive **substring** match on the course directory name. Multiple
  positionals match as OR (a course matches if its name contains any of them).
- The old positional behavior (scan-directory override) moves to a new
  repeatable **`--dir PATH`** flag (`list-courses --dir ~/Other`). This replaces
  the config `course_dirs` for that run, exactly as the positional used to.
- A name filter applies to **both** sections. Because a search implies you want
  results (not a summary), any name filter **expands** the archive listing
  (filtered to matches, still grouped by year).

### `--count`

Render counts instead of individual course lines, honoring all active filters
(section selection, `--year`, name match):

```
Active courses: 3
Archived courses: 412
  2018: 4
  2020: 44
  ...
```

---

## 4. Behavior composition (precise rules)

Inputs from argparse: `names` (list[str], positional), `dir` (list[str],
repeatable), `active` (bool), `archived` (bool), `year` (str|None), `count`
(bool).

- `only_active  = active and not archived`
- `only_archived = archived and not active`
- `show_active   = not only_archived`
- `show_archived = not only_active`
- `has_names = bool(names)`
- `archive_expanded = archived or only_archived or (year is not None) or has_names`

Active section (when `show_active`):
- Filter active courses by name (if `has_names`).
- If `count`: print `Active courses: <N>`.
- Else: print `Active courses:` then a line per course, or an empty-state line
  (`No active courses found`, or `No active courses match: <names>` when filtering).

Archive section (when `show_archived`):
- Build `{year: [courses]}` via the new detection, then apply `year` and name
  filters.
- If `count`: print `Archived courses: <total>` then `  <year>: <n>` per year.
- Elif `archive_expanded`: print `Archived courses:` then the grouped listing
  (`  <year>:` / `    <course line>`), or an empty-state line.
- Else (pure default): print the one-line summary from §2.

`--dir` feeds `resolve_scan_dirs` in place of the old positional; its signature
is unchanged.

### Example invocations

| Command | Result |
|---|---|
| `list-courses` | active full + `Archived: N courses across 2018–2026 — use --archived …` |
| `list-courses --archived` | archive only, expanded, grouped by year |
| `list-courses --active` | active only |
| `list-courses cisco` | active + archive entries whose name contains "cisco" (archive expanded) |
| `list-courses --year 2024` | active full + archive for 2024 (expanded) |
| `list-courses --archived --year 2024` | archive for 2024 only |
| `list-courses --count` | `Active courses: 3` + `Archived courses: 412` + per-year counts |
| `list-courses cisco --count` | counts of active + archive courses matching "cisco" |
| `list-courses --dir ~/Other` | scan `~/Other` for active courses instead of config `course_dirs` |

---

## 5. Implementation shape

All changes in `src/setup_course_github/list_courses.py` and
`tests/test_list_courses.py`.

New/changed units (each small, pure where possible, unit-tested):

- `JUNK_NAMES: frozenset[str]`
- `_is_junk_name(name: str) -> bool` — hidden or in `JUNK_NAMES`.
- `is_archived_course(path: Path) -> bool` — not junk name and ≥1 notebook.
- `find_archived_courses(archive_path: Path) -> dict[str, list[Path]]` — rewritten:
  only `^\d{4}$` year dirs; only `is_archived_course` children.
- `_matches_names(name: str, patterns: list[str]) -> bool` — no patterns → True;
  else case-insensitive substring OR.
- `filter_active(courses: list[Path], patterns: list[str]) -> list[Path]`
- `filter_archived(archived: dict[str, list[Path]], year: str | None, patterns: list[str]) -> dict[str, list[Path]]`
- `archive_summary_line(archived: dict[str, list[Path]]) -> str` — the §2 one-liner.
- `main()` — new argparse options and the §4 display logic.

`is_course`, `course_summary_line`, `resolve_scan_dirs`, `find_active_courses`
are unchanged (the last consumes `--dir` values now, but its signature does not
change).

---

## 6. Docs & release

- README and MANUAL: document the summary default, `--active`/`--archived`,
  `--year`, `--count`, positional name match, and the new `--dir` flag. Call out
  the **breaking change** (positional is now a name filter; use `--dir` for the
  scan-directory override).
- Version bump to **3.2.0** with a git tag; clean `dist/` before building; ship
  via a PR to `main` (owner admin-bypass), then publish to PyPI.
- Mutation-audit the new logic before release; kill real operator/boundary gaps
  (e.g. the `^\d{4}$` year match, substring match, count accumulation), ignore
  string-literal/output-text mutations per project policy.

---

## 7. Out of scope (YAGNI)

- Year ranges (`--year 2020-2022`), glob/regex name matching, date-based
  filtering beyond `--year`, listing loose courses in the archive root, and
  making `load_config` token-optional. Revisit only if needed.
