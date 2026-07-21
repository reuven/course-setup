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
  - When a name filter is active, the summary reflects it:
    `Archived: <N> courses matching "cisco" across <minYear>–<maxYear> — use --archived to list them.`,
    or `Archived: none matching "cisco"` when nothing matches.
- **`--active`**: show the active section only (no archive section at all).
- **`--archived`**: show the archive section only, expanded and grouped by year.
- **Both `--active` and `--archived`**: show both sections in full (active list +
  expanded archive).

---

## 3. Filters

### `--year YYYY` (repeatable)

Restrict the archive listing to the given year(s) and expand it. `--year` is
**repeatable** — `--year 2024 --year 2025` shows both years — collected into a
list. Each value must be a 4-digit year. `--year` is an **archive-focusing**
flag: because active courses are not year-organized, passing `--year` (without
`--active`) shows the archive section only and suppresses the active section — it
behaves like `--archived` scoped to those years. If `--active` is given
explicitly, the active section is shown and `--year` is ignored for it (active
has no years).

### Name match (positional) — BREAKING CHANGE

- Positional arguments (`list-courses cisco`) are now **name filters**:
  case-insensitive **substring** match on the course directory name. Multiple
  positionals match as OR (a course matches if its name contains any of them).
- The old positional behavior (scan-directory override) moves to a new
  repeatable **`--dir PATH`** flag (`list-courses --dir ~/Other`). This replaces
  the config `course_dirs` for that run, exactly as the positional used to.
- A name filter **narrows whatever scope is shown** — it does NOT by itself
  open the archive. So `list-courses cisco` lists active courses matching "cisco"
  and shows the archive as a (name-filtered) summary line; the archive expands
  only when you also pass `--archived` or `--year`. This keeps a bare name search
  from dumping the hundreds of archived courses a common term like "cisco"
  matches. When the archive IS shown (via `--archived`/`--year`), the name filter
  applies there too.

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
repeatable), `active` (bool), `archived` (bool), `years` (list[str], repeatable
`--year`, possibly empty), `count` (bool).

- `has_names = bool(names)`
- `has_years = bool(years)`
- `only_active   = active and not archived`
- `only_archived = archived and not active`
- `year_focus    = has_years and not active and not archived`
  (a bare `--year` focuses the archive when neither section flag is set)
- `show_active   = not (only_archived or year_focus)`
- `show_archived = not only_active`
- `archive_expanded = archived or has_years`

A name filter is NOT in `archive_expanded`: it narrows the shown scope but does
not open the archive. `--year` hides the active section unless `--active` is
explicitly passed; `--active --year …` shows active only (years ignored for
active).

Active section (when `show_active`):
- Filter active courses by name (if `has_names`).
- If `count`: print `Active courses: <N>`.
- Else: print `Active courses:` then a line per course, or an empty-state line
  (`No active courses found`, or `No active courses match: <names>` when filtering).

Archive section (when `show_archived`):
- Build `{year: [courses]}` via the new detection, then apply `years` and name
  filters.
- If `count`: print `Archived courses: <total>` then `  <year>: <n>` per year.
- Elif `archive_expanded`: print `Archived courses:` then the grouped listing
  (`  <year>:` / `    <course line>`), or an empty-state line.
- Else (pure default, incl. a bare name filter): print the one-line summary from
  §2 (reflecting the name filter when present).

`--dir` feeds `resolve_scan_dirs` in place of the old positional; its signature
is unchanged.

### Example invocations

| Command | Result |
|---|---|
| `list-courses` | active full + `Archived: N courses across 2018–2026 — use --archived …` |
| `list-courses --archived` | archive only, expanded, grouped by year |
| `list-courses --active` | active only |
| `list-courses cisco` | active courses matching "cisco" + a name-filtered archive summary line |
| `list-courses cisco --archived` | archive courses matching "cisco" (all years, expanded) |
| `list-courses --year 2024` | archive for 2024 only (active section suppressed) |
| `list-courses --year 2024 --year 2025` | archive for 2024 and 2025 only |
| `list-courses cisco --year 2024` | archive courses matching "cisco" from 2024 only |
| `list-courses --active --year 2024` | active only (`--year` ignored for active) |
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
- `filter_archived(archived: dict[str, list[Path]], years: list[str], patterns: list[str]) -> dict[str, list[Path]]`
  — empty `years` → no year filter; otherwise keep only listed years.
- `archive_summary_line(archived: dict[str, list[Path]], patterns: list[str]) -> str`
  — the §2 one-liner, including the `matching "…"` clause when `patterns` is non-empty.
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

- Year **ranges** (`--year 2020-2022`) — repeatable `--year` covers the common
  case; ranges can come later. Also: glob/regex name matching, date-based
  filtering beyond `--year`, listing loose courses in the archive root, and
  making `load_config` token-optional. Revisit only if needed.
