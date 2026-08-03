# Design: smoother webpdf/PDF export in archive-course

Date: 2026-08-03

PDF export (default-on since 3.2.0) uses `nbconvert --to webpdf`, which needs the
`nbconvert[webpdf]` extra (the **playwright** library) plus a one-time
**chromium** browser binary. New courses ship with neither, and when export
fails, `archive-course` prints nbconvert's entire traceback — so a missing
dependency looks catastrophic even though the archive still succeeds.

This makes PDF export work smoothly with (almost) no manual steps. Ships as
**3.3.1**.

---

## 1. New Jupyter courses include the webpdf library

`setup-course` builds a Jupyter course's base dependencies as
`["jupyter", "ipyparallel", "gitautopush"]` (setup_course.py:87 and :432 —
two occurrences). Add `nbconvert[webpdf]`:

```
["jupyter", "nbconvert[webpdf]", "ipyparallel", "gitautopush"]
```

Marimo courses are unchanged (archive only exports `.ipynb`). This gives new
Jupyter courses the playwright **library**; the chromium **browser** is handled
at archive time (§2). Existing courses need a one-time `uv add "nbconvert[webpdf]"`
(documented in §3) — a real, committable dependency change the user owns.

---

## 2. archive-course: classify failures, auto-install chromium, degrade cleanly

Replace the "dump the whole stderr" behavior. On a PDF export failure, classify
it from nbconvert/playwright stderr into one of three kinds and act:

- **`lib`** — the playwright library / `nbconvert[webpdf]` extra is missing
  (stderr mentions `nbconvert[webpdf]`, `No module named 'playwright'`, or
  `Playwright is not installed to support Web PDF conversion`). This is a course
  dependency the tool must not silently change. Print one concise hint and stop
  attempting PDF for the rest of the run:
  ```
  PDF export needs the webpdf extra. In the course dir run:
    uv add "nbconvert[webpdf]"
  (then archive again, or use --no-pdf to skip PDF.)
  ```

- **`chromium`** — the library is present but the chromium binary isn't (stderr
  mentions `playwright install`, `Executable doesn't exist`, or `download new
  browsers`). **Auto-install chromium once** (the user chose auto, no prompt):
  ```
  Chromium isn't installed yet (needed for PDF export).
  Installing it once now — this may take a minute...
  ```
  Run `uv run playwright install chromium` with `cwd` = the course dir (uses the
  course's playwright). On success print `Chromium installed.` and **retry** the
  current notebook; subsequent notebooks proceed normally (install happens at most
  once per archive run, guarded by a flag). On install failure, print a short
  note and fall through to graceful degradation for the rest.

- **`other`** — any other failure. Print a concise one-liner using the **last
  non-empty line** of stderr (not the whole traceback):
  ```
  Warning: failed to export <notebook> to PDF: <last stderr line>
  ```

In all cases the archive still completes (HTML export + zip succeed, exactly as
today) and only successfully-exported PDFs are counted / listed. PDF stays
**default-on**; `--no-pdf` skips the whole PDF phase (and thus any auto-install).

### Unit decomposition (in `archive_course.py`)

- `_last_error_line(stderr: str) -> str` — last non-empty stripped line, or `""`.
- `_pdf_failure_kind(stderr: str) -> str` — returns `"lib"`, `"chromium"`, or
  `"other"` from the stderr signals above (checked case-insensitively; `lib`
  takes priority over `chromium` if both somehow appear).
- `_install_chromium(course_path: Path) -> bool` — runs
  `["uv", "run", "playwright", "install", "chromium"]` with `cwd=course_path`,
  `capture_output=True`; returns True on returncode 0.
- The HTML path keeps the existing `_export_notebook`/`_export_notebook_to_html`
  behavior, but its `CalledProcessError` branch also switches to
  `_last_error_line` (no more full-traceback dumps for HTML either).
- The PDF phase becomes a small orchestration function,
  `_export_notebooks_to_pdf(notebooks: list[Path], course_path: Path) -> int`,
  that runs each notebook's `webpdf` export, applies the classification above,
  performs the one-time chromium auto-install + retry, and returns the count of
  PDFs produced. `archive_course()` calls it in place of the current inline PDF
  loop.

`_export_notebook_to_pdf` may be kept as the single-notebook runner used by
`_export_notebooks_to_pdf`, but it now returns enough information (success, or the
stderr) for the orchestrator to classify — e.g. return `tuple[bool, str]`
(ok, stderr) or raise-through the `CalledProcessError`. The plan picks the
cleanest shape; the observable behavior above is what matters.

---

## 3. Docs

README + MANUAL, `archive-course` section:

- New Jupyter courses include `nbconvert[webpdf]`, so PDF export works after
  `archive-course` auto-installs chromium the first time (a one-time, per-machine
  browser download it now handles for you — no manual `playwright` command).
- To enable PDF export on a course created before 3.3.1, run
  `uv add "nbconvert[webpdf]"` in the course once (then archive normally).
- `--no-pdf` still skips PDF entirely.

---

## 4. Testing

- `_last_error_line`: multi-line stderr → last non-empty line; trailing
  blanks ignored; empty → `""`.
- `_pdf_failure_kind`: representative `lib`, `chromium`, and `other` stderrs →
  correct kind; `lib` priority when signals overlap.
- `_install_chromium`: subprocess mocked — success → True; non-zero → False;
  asserts the `uv run playwright install chromium` command + `cwd`.
- `_export_notebooks_to_pdf` (subprocess/`_install_chromium` mocked):
  - all succeed → count == N, no install attempted.
  - `chromium` kind on first notebook → auto-install invoked once, retry
    succeeds → counted; second notebook exports without a second install.
  - `chromium` kind but install fails → graceful, count reflects only successes,
    the install-failed note printed.
  - `lib` kind → hint printed once, no per-notebook repetition, no install call.
  - `other` kind → concise last-line warning; archive continues.
- `archive_course` integration (subprocess mocked): a `lib`-kind failure still
  produces the zip + HTML and prints the `uv add` hint; PDF-exports line absent.
- Existing archive tests updated where they assert on the old full-stderr warning
  text or mock `_export_notebook_to_pdf`'s old signature; the HTML-failure and
  `--no-pdf`/count/summary tests keep their intent.
- `setup_course` tests: the Jupyter dependency-list assertions gain
  `nbconvert[webpdf]` (exact-token assertions per existing style).

---

## 5. Release

- Version bump to **3.3.1**; tag; clean `dist/`; PR to `main` (admin bypass);
  publish to PyPI.
- Mutation-audit the new `archive_course.py` logic (the classification branches,
  the install-once guard, the retry) — ignore output-string mutations.

---

## 6. Out of scope (YAGNI)

- Auto-running `uv add "nbconvert[webpdf]"` in a course (a committed dependency
  change the user should make/own).
- A prompt before installing chromium (user chose auto-install).
- LaTeX (`--to pdf`) as an alternative backend, and PDF export for marimo `.py`
  notebooks.
