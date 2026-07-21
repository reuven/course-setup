# Design: year ranges for `list-courses --year`

Date: 2026-07-21

`list-courses --year` (shipped 3.2.0) accepts a single 4-digit year and is
repeatable. This adds inclusive **range** syntax so a span of years can be given
in one token. Target version: **3.3.0** (new capability, backward compatible).

---

## 1. Syntax and semantics

- Each `--year` value is now either a **single year** (`2024`) or an **inclusive
  range** (`2020-2022` = 2020, 2021, 2022).
- `--year` stays **repeatable**, and singles and ranges **mix freely**:
  `list-courses --year 2019 --year 2021-2023` → archived courses from 2019, 2021,
  2022, 2023.
- A range is inclusive of both endpoints. A degenerate range `2024-2024` → just
  2024 (no note).

### Reversed ranges — auto-swap with a notice

A reversed range like `--year 2022-2020` is **accepted and swapped** to
`2020-2022`, and a notice is printed to **stderr**:

```
Note: swapped reversed year range 2022-2020 → 2020-2022
```

(stderr keeps the swap notice out of the course listing on stdout.) One notice
per reversed range token. The results are then exactly those of the normalized
range.

### Validation

Each `--year` token must match `^\d{4}(-\d{4})?$` (a 4-digit year, optionally a
hyphen and another 4-digit year). Anything else is an argparse error
(`invalid year '...'`), as today. Both orderings of a range are valid at parse
time; the swap is handled during expansion, not rejected.

---

## 2. Behavior composition (unchanged)

`--year` remains **archive-focusing**: `has_years` (and therefore `year_focus`,
`show_active`, `show_archived`, `archive_expanded`) key off whether *any* `--year`
token was given — the range expansion does not change that logic. `--active`
still overrides (active shown, years ignored for active). `--count`, name
filters, and `--dir` are all unaffected.

---

## 3. Implementation (contained to `list_courses.py`)

- Keep `_YEAR_RE = ^\d{4}$` as-is — it matches archive **year directory** names
  in `find_archived_courses` and must stay strict.
- Add `_YEAR_TOKEN_RE = re.compile(r"^\d{4}(-\d{4})?$")` for CLI validation.
- `_year_arg(value: str) -> str`: raise `argparse.ArgumentTypeError` unless
  `_YEAR_TOKEN_RE` matches; return the token unchanged (no reorder here).
- New pure helper
  `_expand_year_tokens(tokens: list[str]) -> tuple[list[str], list[str]]`:
  returns `(years, notes)` where `years` is the flat list of individual
  4-digit year strings and `notes` is a list of human-readable swap messages.
  - For a single-year token → `[token]`.
  - For a range `a-b`: parse ints; if `a > b`, append a note
    `f"swapped reversed year range {a}-{b} → {b}-{a}"` and swap; expand inclusive
    as `[f"{y:04d}" for y in range(lo, hi + 1)]` (zero-padded to preserve the
    4-digit form used by year-dir names).
- `main()`:
  - `years, notes = _expand_year_tokens(args.years)`
  - `for note in notes: print(f"Note: {note}", file=sys.stderr)`
  - pass `years` to `filter_archived` (its signature is unchanged — still a flat
    `list[str]` of individual years).
  - `has_years` continues to key off `bool(args.years)` (the raw tokens).
- Add `import sys` to the module.

`filter_archived`, `find_archived_courses`, `resolve_scan_dirs`, and the display
composition are all unchanged.

---

## 4. Tests

- `_year_arg`: accepts `2024` and `2020-2022`; rejects `24`, `2020-`, `abcd`,
  `2020-20222`, `2020-2021-2022` (argparse error).
- `_expand_year_tokens`:
  - single year → `["2024"]`, no notes.
  - range → all inclusive years, no notes (`2020-2022` → `["2020","2021","2022"]`).
  - degenerate `2024-2024` → `["2024"]`, no notes.
  - reversed `2022-2020` → `["2020","2021","2022"]` + one note.
  - mixed singles + ranges across repeated tokens → union (order preserved).
- `main()` (capsys):
  - `--year 2020-2022` shows only those archived years, active suppressed.
  - mixed `--year 2019 --year 2021-2023` shows the right set.
  - reversed `--year 2022-2020` prints the `Note: swapped …` line to **stderr**
    (assert via `capsys.readouterr().err`) and still lists 2020–2022.
- Existing single-year `--year` tests continue to pass unchanged.

---

## 5. Docs & release

- README + MANUAL: document range syntax on `--year`, the mix-and-repeat
  behavior, and the reversed-range auto-swap notice. Update the example table.
- Version bump to **3.3.0** with a tag; clean `dist/` before building; ship via a
  PR to `main` (admin bypass), then publish to PyPI.
- Mutation-audit the new logic (`_YEAR_TOKEN_RE`, the `a > b` swap branch, the
  inclusive `range(lo, hi + 1)` boundary); ignore output-string mutations.

---

## 6. Out of scope (YAGNI)

- Open-ended ranges (`2020-`, `-2022`), step syntax, non-year date filtering,
  and applying `--year` to active courses (active has no years). Revisit only if
  needed.
