# archive-course webpdf/PDF smoothing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `archive-course` PDF export smooth: new Jupyter courses ship the webpdf library, chromium auto-installs itself once when needed, and failures print a concise actionable hint instead of a raw traceback.

**Architecture:** Two source files. `setup_course.py` adds `nbconvert[webpdf]` to new Jupyter course deps. `archive_course.py` classifies PDF failures (`lib`/`chromium`/`other`), auto-installs chromium once and retries, and degrades cleanly (HTML + zip always succeed). One feature branch, TDD, merged to `main` via PR, released as 3.3.1.

**Tech Stack:** Python 3, `uv`, pytest, `subprocess` (local `git`/`uv`/`playwright`/`nbconvert`), ruff, mypy strict, mutmut (<3).

## Global Constraints

- Use `uv` for everything (`uv run pytest`, `uv run ruff`, `uv run mypy`, `uv build`, `uv publish`). Never pip/python/venv directly.
- **Never chain shell commands with `&&`.** Separate, sequential commands only.
- TDD: failing test first, confirm red, implement, confirm green, commit.
- 100% line coverage enforced; type hints everywhere; `uv run mypy --strict` clean; `uv run ruff format` + `uv run ruff check` clean before every commit.
- Small commits; exact commit messages as given.
- Design ref: `docs/superpowers/specs/2026-08-03-archive-pdf-webpdf-setup-design.md`.
- Output-string mutations are NOT killed in the mutation audit; real operator/keyword/boundary gaps ARE.
- PDF export stays **default-on**; `--no-pdf` skips the whole PDF phase (and any auto-install).

---

## Task 1: New Jupyter courses include `nbconvert[webpdf]`

**Files:**
- Modify: `src/setup_course_github/setup_course.py` (two dep lists: ~line 87 and ~line 432)
- Test: `tests/test_setup_course.py`

**Interfaces:**
- Produces: Jupyter course deps become `["jupyter", "nbconvert[webpdf]", "ipyparallel", "gitautopush"]`.

- [ ] **Step 1: Create the feature branch**

```bash
git switch -c feature/archive-pdf-webpdf-setup
```

- [ ] **Step 2: Update the failing test**

In `tests/test_setup_course.py`, the exact-list assertion (currently at line 1068)
must include the new dep. Change it to:

```python
    assert deps == ["jupyter", "nbconvert[webpdf]", "ipyparallel", "gitautopush"]
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_setup_course.py -k "jupyter_deps or dependencies" -v`
Expected: FAIL — the exact-list assertion still sees the old 3-item list.

- [ ] **Step 4: Add the dependency in both spots**

In `src/setup_course_github/setup_course.py`, both occurrences of the Jupyter
branch (the `_build_pyproject_toml` helper near line 87, and the status-print
block near line 432) read:

```python
        ["jupyter", "ipyparallel", "gitautopush"]
```

Change **both** to:

```python
        ["jupyter", "nbconvert[webpdf]", "ipyparallel", "gitautopush"]
```

- [ ] **Step 5: Run and fix any other exact-list/status assertions**

Run: `uv run pytest tests/test_setup_course.py -v`
Expected: PASS. If any other test asserts the exact Jupyter dependency list or the
exact `Dependencies: jupyter, ipyparallel, gitautopush` status line, update it to
include `nbconvert[webpdf]` (in the same position). Tests asserting only
`"jupyter" in content` / `"ipyparallel" in deps` (substring) need no change.

- [ ] **Step 6: Full suite, format, lint, type-check, commit**

```bash
uv run pytest
uv run ruff format src/setup_course_github/setup_course.py tests/test_setup_course.py
uv run ruff check src/setup_course_github/setup_course.py tests/test_setup_course.py
uv run mypy --strict src/setup_course_github/setup_course.py
git add src/setup_course_github/setup_course.py tests/test_setup_course.py
git commit -m "feat: add nbconvert[webpdf] to new Jupyter course deps"
```

---

## Task 2: PDF-failure classification helpers

**Files:**
- Modify: `src/setup_course_github/archive_course.py`
- Test: `tests/test_archive_course.py`

**Interfaces:**
- Produces:
  - `_last_error_line(stderr: str) -> str`
  - `_pdf_failure_kind(stderr: str) -> str` → `"lib"`, `"chromium"`, or `"other"`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_archive_course.py`:

```python
def test_last_error_line_returns_last_nonblank() -> None:
    from setup_course_github.archive_course import _last_error_line

    assert _last_error_line("first\nRuntimeError: boom\n\n") == "RuntimeError: boom"
    assert _last_error_line("   ") == ""
    assert _last_error_line("") == ""


def test_pdf_failure_kind_lib() -> None:
    from setup_course_github.archive_course import _pdf_failure_kind

    assert _pdf_failure_kind("ModuleNotFoundError: No module named 'playwright'") == "lib"
    assert (
        _pdf_failure_kind("Please install `nbconvert[webpdf]` to enable.") == "lib"
    )
    assert (
        _pdf_failure_kind("Playwright is not installed to support Web PDF conversion")
        == "lib"
    )


def test_pdf_failure_kind_chromium() -> None:
    from setup_course_github.archive_course import _pdf_failure_kind

    assert _pdf_failure_kind("Executable doesn't exist at /x/chromium") == "chromium"
    assert _pdf_failure_kind("please run: playwright install") == "chromium"
    assert _pdf_failure_kind("download new browsers") == "chromium"


def test_pdf_failure_kind_other_and_priority() -> None:
    from setup_course_github.archive_course import _pdf_failure_kind

    assert _pdf_failure_kind("some unrelated error") == "other"
    # lib signal wins even if a chromium phrase is also present
    assert (
        _pdf_failure_kind("No module named 'playwright'; try playwright install")
        == "lib"
    )
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_archive_course.py -k "last_error_line or pdf_failure_kind" -v`
Expected: FAIL — `cannot import name '_last_error_line'`.

- [ ] **Step 3: Implement the helpers**

In `src/setup_course_github/archive_course.py`, add near the top (after the
imports, before `_export_notebook`):

```python
def _last_error_line(stderr: str) -> str:
    """Return the last non-blank line of *stderr* (stripped), or "" if none."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _pdf_failure_kind(stderr: str) -> str:
    """Classify a webpdf failure as 'lib', 'chromium', or 'other'.

    'lib' (the nbconvert[webpdf]/playwright library is missing) takes priority
    over 'chromium' (the browser binary is missing) when both appear.
    """
    low = stderr.lower()
    lib_signals = (
        "nbconvert[webpdf]",
        "no module named 'playwright'",
        "playwright is not installed to support web pdf",
    )
    if any(signal in low for signal in lib_signals):
        return "lib"
    chromium_signals = (
        "playwright install",
        "executable doesn't exist",
        "download new browsers",
    )
    if any(signal in low for signal in chromium_signals):
        return "chromium"
    return "other"
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_archive_course.py -k "last_error_line or pdf_failure_kind" -v`
Expected: PASS.

- [ ] **Step 5: Format, lint, type-check, commit**

```bash
uv run ruff format src/setup_course_github/archive_course.py tests/test_archive_course.py
uv run ruff check src/setup_course_github/archive_course.py tests/test_archive_course.py
uv run mypy --strict src/setup_course_github/archive_course.py
git add src/setup_course_github/archive_course.py tests/test_archive_course.py
git commit -m "feat: add PDF-failure classification helpers"
```

---

## Task 3: chromium auto-install + PDF orchestration + clean HTML warning

**Files:**
- Modify: `src/setup_course_github/archive_course.py`
- Test: `tests/test_archive_course.py`

**Interfaces:**
- Consumes: `_last_error_line`, `_pdf_failure_kind` (Task 2).
- Produces:
  - `_install_chromium(course_path: Path) -> bool`
  - `_export_notebook_to_pdf(nb_path: Path, course_path: Path) -> tuple[bool, str]` (CHANGED return type: `(ok, stderr)`, no printing)
  - `_export_notebooks_to_pdf(notebooks: list[Path], course_path: Path) -> int`
  - `archive_course()` PDF phase calls `_export_notebooks_to_pdf`.

- [ ] **Step 1: Update the existing PDF tests to the new `_export_notebook_to_pdf` contract**

`_export_notebook_to_pdf` now returns `tuple[bool, str]` and does not print. Update
these existing tests in `tests/test_archive_course.py`:

**(a)** `test_export_notebook_to_pdf_runs_webpdf` — change the call/assert:

```python
    with patch("subprocess.run") as mock_run:
        ok, stderr = _export_notebook_to_pdf(nb, course)
    assert ok is True
    assert stderr == ""
    args = mock_run.call_args
    assert args.kwargs["cwd"] == str(course)
    cmd = args.args[0]
    assert cmd == ["uv", "run", "jupyter", "nbconvert", "--to", "webpdf", "lesson.ipynb"]
```

**(b)** `test_export_notebook_to_pdf_handles_called_process_error`:

```python
    err = subprocess.CalledProcessError(1, "nbconvert", stderr=b"chromium missing")
    with patch("subprocess.run", side_effect=err):
        ok, stderr = _export_notebook_to_pdf(nb, course)
    assert ok is False
    assert "chromium missing" in stderr
```

**(c)** `test_export_notebook_to_pdf_handles_missing_binary`:

```python
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        ok, stderr = _export_notebook_to_pdf(nb, course)
    assert ok is False
```

**(d)** In the four `archive_course`-level PDF tests, the `_export_notebook_to_pdf`
mock must now return/`side_effect` a `(bool, str)` tuple:
- `test_archive_exports_pdf_by_default`: its `fake_pdf(nb_path, course_path)` should
  write the `.pdf` and `return True, ""`.
- `test_archive_summary_lists_pdf_next_to_notebook`: same `fake_pdf` → `return True, ""`.
- `test_archive_pdf_export_count_accumulates_across_notebooks`: change
  `return_value=True` → `return_value=(True, "")`.
- `test_archive_failed_pdf_export_not_counted`: change `return_value=False` →
  `return_value=(False, "")`.

`test_archive_no_pdf_skips_export` (asserts `_export_notebook_to_pdf` not called with
`export_pdf=False`) needs no change.

- [ ] **Step 2: Write the new orchestration + install tests**

Add to `tests/test_archive_course.py`:

```python
def test_install_chromium_runs_playwright(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _install_chromium

    course = tmp_path / "course"
    course.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert _install_chromium(course) is True
    cmd = mock_run.call_args.args[0]
    assert cmd == ["uv", "run", "playwright", "install", "chromium"]
    assert mock_run.call_args.kwargs["cwd"] == str(course)


def test_install_chromium_returns_false_on_failure(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _install_chromium

    course = tmp_path / "course"
    course.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert _install_chromium(course) is False


def test_export_notebooks_to_pdf_all_succeed(tmp_path: Path) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        return_value=(True, ""),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium"
        ) as mock_install:
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 2
    mock_install.assert_not_called()


def test_export_notebooks_to_pdf_installs_chromium_once_then_retries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    # a.ipynb: first call chromium-missing, retry succeeds; b.ipynb succeeds
    results = iter(
        [(False, "Executable doesn't exist"), (True, ""), (True, "")]
    )
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        side_effect=lambda *a, **k: next(results),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium",
            return_value=True,
        ) as mock_install:
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 2
    mock_install.assert_called_once()
    out = capsys.readouterr().out
    assert "Installing it once now" in out
    assert "Chromium installed." in out


def test_export_notebooks_to_pdf_install_failure_degrades(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb"]
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        return_value=(False, "Executable doesn't exist"),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium",
            return_value=False,
        ):
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 0
    assert "Could not install Chromium" in capsys.readouterr().out


def test_export_notebooks_to_pdf_lib_missing_prints_hint_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        return_value=(False, "Please install `nbconvert[webpdf]`"),
    ):
        with patch(
            "setup_course_github.archive_course._install_chromium"
        ) as mock_install:
            count = _export_notebooks_to_pdf(nbs, course)
    assert count == 0
    mock_install.assert_not_called()
    out = capsys.readouterr().out
    assert out.count('uv add "nbconvert[webpdf]"') == 1  # printed once, not per-nb


def test_export_notebooks_to_pdf_other_error_warns_and_continues(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from setup_course_github.archive_course import _export_notebooks_to_pdf

    course = tmp_path / "course"
    course.mkdir()
    nbs = [course / "a.ipynb", course / "b.ipynb"]
    results = iter([(False, "weird\nRuntimeError: nope"), (True, "")])
    with patch(
        "setup_course_github.archive_course._export_notebook_to_pdf",
        side_effect=lambda *a, **k: next(results),
    ):
        count = _export_notebooks_to_pdf(nbs, course)
    assert count == 1
    out = capsys.readouterr().out
    assert "Warning: failed to export a.ipynb to PDF: RuntimeError: nope" in out
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest tests/test_archive_course.py -k "install_chromium or export_notebooks_to_pdf or to_pdf" -v`
Expected: FAIL — new symbols not importable; tuple contract not yet in place.

- [ ] **Step 4: Rewrite `_export_notebook_to_pdf`, add `_install_chromium` + `_export_notebooks_to_pdf`, and clean the HTML warning**

In `src/setup_course_github/archive_course.py`:

**(a)** In `_export_notebook` (the HTML runner), change the `CalledProcessError`
branch to use the last line (replace the `stderr = ...; print(...)` lines):

```python
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if exc.stderr else ""
        print(
            f"  Warning: failed to export {nb_path.name} to {label}: "
            f"{_last_error_line(stderr)}"
        )
        return False
```

**(b)** **Replace** the existing `_export_notebook_to_pdf` (the thin wrapper) with a
standalone runner returning `(ok, stderr)` and NOT printing:

```python
def _export_notebook_to_pdf(nb_path: Path, course_path: Path) -> tuple[bool, str]:
    """Run webpdf export for one notebook. Returns (ok, stderr); does not print."""
    relative = nb_path.relative_to(course_path)
    try:
        subprocess.run(
            ["uv", "run", "jupyter", "nbconvert", "--to", "webpdf", str(relative)],
            cwd=str(course_path),
            capture_output=True,
            check=True,
        )
        return True, ""
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.decode() if exc.stderr else ""
    except FileNotFoundError:
        return False, "jupyter nbconvert not found"


def _install_chromium(course_path: Path) -> bool:
    """Install the chromium browser for webpdf via the course's playwright.

    Returns True on success. Runs `uv run playwright install chromium` in the
    course dir; the browser lands in a shared per-machine cache.
    """
    result = subprocess.run(
        ["uv", "run", "playwright", "install", "chromium"],
        cwd=str(course_path),
        capture_output=True,
    )
    return result.returncode == 0


def _export_notebooks_to_pdf(notebooks: list[Path], course_path: Path) -> int:
    """Export notebooks to PDF, auto-installing chromium once if needed.

    Returns the number of PDFs produced. Prints concise, actionable messages and
    never raises — a failure leaves the HTML export + zip intact.
    """
    exported = 0
    chromium_installed = False
    for nb_path in notebooks:
        ok, stderr = _export_notebook_to_pdf(nb_path, course_path)
        if ok:
            exported += 1
            continue
        kind = _pdf_failure_kind(stderr)
        if kind == "lib":
            print("  PDF export needs the webpdf extra. In the course dir run:")
            print('    uv add "nbconvert[webpdf]"')
            print("  (then archive again, or use --no-pdf to skip PDF.)")
            break
        if kind == "chromium" and not chromium_installed:
            print("  Chromium isn't installed yet (needed for PDF export).")
            print("  Installing it once now — this may take a minute...")
            if not _install_chromium(course_path):
                print("  Could not install Chromium automatically; skipping PDF.")
                print("    To enable it, run: uv run playwright install chromium")
                break
            chromium_installed = True
            print("  Chromium installed.")
            ok, stderr = _export_notebook_to_pdf(nb_path, course_path)
            if ok:
                exported += 1
                continue
        print(
            f"  Warning: failed to export {nb_path.name} to PDF: "
            f"{_last_error_line(stderr)}"
        )
    return exported
```

**(c)** In `archive_course()`, replace the inline PDF loop (currently lines 77-83):

```python
    # Export notebooks to PDF if requested
    pdf_exported = 0
    if export_pdf and notebooks:
        print("Exporting notebooks to PDF...")
        pdf_exported = _export_notebooks_to_pdf(notebooks, course_path)
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_archive_course.py -v`
Expected: PASS (all — new tests plus the updated existing PDF tests).

- [ ] **Step 6: Format, lint, type-check, full suite, commit**

```bash
uv run ruff format src/setup_course_github/archive_course.py tests/test_archive_course.py
uv run ruff check src/setup_course_github/archive_course.py tests/test_archive_course.py
uv run mypy --strict src/setup_course_github/archive_course.py
uv run pytest
git add src/setup_course_github/archive_course.py tests/test_archive_course.py
git commit -m "feat: auto-install chromium and classify PDF export failures"
```

---

## Task 4: Docs — README + MANUAL

**Files:**
- Modify: `README.md`
- Modify: `MANUAL.md`

- [ ] **Step 1: Update the README `archive-course` section**

Document: new Jupyter courses include `nbconvert[webpdf]`; the first PDF export
triggers a one-time automatic chromium install (no manual `playwright` command);
to enable PDF on a course created before 3.3.1, run `uv add "nbconvert[webpdf]"`
in it once; `--no-pdf` skips PDF entirely.

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: document webpdf setup + chromium auto-install in README"
```

- [ ] **Step 3: Update the MANUAL `archive-course` section**

Same at manual depth: how PDF export works now, the auto-install, enabling PDF on
older courses, and the failure hints.

- [ ] **Step 4: Commit MANUAL**

```bash
git add MANUAL.md
git commit -m "docs: document webpdf setup + chromium auto-install in the manual"
```

---

## Task 5: Mutation-testing audit

- [ ] **Step 1: Run the audit**

Run: `uv run mutmut run`
(Tally via `sqlite3 .mutmut-cache "SELECT status,COUNT(*) FROM Mutant GROUP BY status"`.)

- [ ] **Step 2: Triage survivors in the changed files**

List survivors for `archive_course.py` and `setup_course.py`:
`sqlite3 .mutmut-cache "SELECT m.id,l.line_number,l.line FROM Mutant m JOIN Line l ON m.line=l.id JOIN SourceFile sf ON l.sourcefile=sf.id WHERE m.status='bad_survived' AND (sf.filename LIKE '%archive_course.py' OR sf.filename LIKE '%setup_course.py') ORDER BY sf.filename, l.line_number"`

Kill real logic gaps only: `_pdf_failure_kind` signal/priority branches, the
`chromium_installed` install-once guard, the `not _install_chromium(...)`
degrade branch, the retry `if ok` path, `_last_error_line`'s last-nonblank logic,
and the `nbconvert[webpdf]` dep addition. Ignore output-string/help-text mutations
per policy. For each real gap: `uv run mutmut apply <id>` → confirm a test fails →
`git checkout -- <src>` → write the killing test → verify → commit
(`Kill archive-course mutant <id>: <what>`).

---

## Task 6: Version bump, release PR, tag, publish

- [ ] **Step 1: Bump the version**

In `pyproject.toml:3`, change `version = "3.3.0"` to `version = "3.3.1"`.

- [ ] **Step 2: Sync, commit**

```bash
uv sync
git add pyproject.toml uv.lock
git commit -m "Bump version to 3.3.1"
```

- [ ] **Step 3: Full suite green**

Run: `uv run pytest`
Expected: PASS, 100% coverage.

- [ ] **Step 4: Push branch and open PR**

```bash
git push -u origin feature/archive-pdf-webpdf-setup
gh pr create --base main --head feature/archive-pdf-webpdf-setup --title "Release 3.3.1: smoother archive-course PDF export" --body "See docs/superpowers/specs/2026-08-03-archive-pdf-webpdf-setup-design.md. New Jupyter courses get nbconvert[webpdf]; archive-course auto-installs chromium once and classifies PDF failures cleanly."
```

- [ ] **Step 5: Merge (admin bypass), merge commit**

```bash
gh pr merge --merge --admin --delete-branch
```

- [ ] **Step 6: Sync main, tag, push tag**

```bash
git switch main
git pull
git tag v3.3.1
git push origin v3.3.1
```

- [ ] **Step 7: Clean dist, build, publish, verify**

```bash
rm -rf dist/*
uv build
uv publish
```

Run: `curl -s https://pypi.org/simple/course-setup/ | grep -o 'course_setup-3.3.1[^"#]*' | sort -u`
Expected: both 3.3.1 files listed.

---

## Self-Review Notes

- **Spec coverage:** §1 template dep → Task 1; §2 classification + auto-install + degradation → Tasks 2-3; §3 docs → Task 4; §4 testing → folded into Tasks 1-3; §5 release → Task 6; mutation audit → Task 5. All mapped.
- **Breaking-change fallout:** `_export_notebook_to_pdf` return type changes to `tuple[bool, str]`; Task 3 Step 1 updates the 3 direct tests + 4 archive-level PDF tests that mock it. HTML-failure/`--no-pdf`/count/summary tests keep their intent.
- **Type consistency:** `_export_notebook_to_pdf -> tuple[bool, str]`; `_export_notebooks_to_pdf(list[Path], Path) -> int`; `_install_chromium(Path) -> bool`; `_pdf_failure_kind(str) -> str`; `_last_error_line(str) -> str`. `archive_course` PDF phase consumes `_export_notebooks_to_pdf`.
- **Read-only/offline preserved elsewhere:** only `archive-course` shells out (nbconvert/playwright); `list-courses` etc. unchanged.
```
