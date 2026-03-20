# TODO — Feature Sprint (v2.11.0)

## 1. Add `.gitignore` to bundled template
- [ ] Add `src/setup_course_github/generic/.gitignore` with standard Python defaults (matching what `uv init` generates): `__pycache__/`, `*.pyc`, `.venv/`, `.ipynb_checkpoints/`, `*.egg-info/`, `dist/`, `build/`, etc.
- [ ] Test that the `.gitignore` ends up in the created course directory
- [ ] Commit, update docs

## 2. Add `--version` flag to all three CLI commands
- [ ] Add a shared `__version__` string (sourced from one place)
- [ ] Add `--version` to `setup-course`, `retire-course`, and `setup-course-config` argparse configs
- [ ] Show version and PyPI URL in `--help` epilog
- [ ] Tests for each command's `--version` output
- [ ] Commit, update docs

## 3. Add `--first-notebook-date` flag
- [ ] New CLI flag `--first-notebook-date YYYY-MM-DD` for `setup-course`
- [ ] When set, notebook dates start from this date instead of today
- [ ] When not set, behavior unchanged (start from today)
- [ ] Validate the date format
- [ ] Tests: correct notebooks created, invalid format rejected, interaction with `-n`/`--freq`
- [ ] Commit, update docs

## 4. Add `--skip-weekends` and `--skip-israeli-weekends` flags
- [ ] `--skip-weekends` skips Saturday+Sunday when generating notebook dates
- [ ] `--skip-israeli-weekends` skips Friday+Saturday
- [ ] The two flags are mutually exclusive
- [ ] Add `[defaults] weekend` config option: `"standard"` (Sat+Sun), `"israeli"` (Fri+Sat), or omit for none
- [ ] CLI flags override the config default
- [ ] Works with both `daily` and `weekly` freq (weekly probably unaffected since it jumps 7 days)
- [ ] Update `_notebook_dates()` to accept skip days
- [ ] Tests: 5-day course skipping weekends, Israeli weekends, config default, CLI override, edge cases
- [ ] Commit, update docs

## 5. Validate `-d` format
- [ ] Check that `-d` value matches `YYYY-MM` pattern
- [ ] Validate it's a real month (not `2026-13`)
- [ ] Reject years more than 2 ahead of current year (so if now=2026, reject 2029+)
- [ ] Clear error messages on validation failure
- [ ] Tests for valid dates, invalid format, too-far-future years, edge cases
- [ ] Commit, update docs

## 6. Additional files config option
- [ ] New config option `[paths] additional_files` — list of file paths and/or directory paths
- [ ] These are copied INTO the new course directory after the bundled template is set up
- [ ] This is additive — the bundled template (with .gitignore, README, etc.) is always used first
- [ ] Use case: exercise files, data CSVs, extra notebooks, solutions/ folder, etc.
- [ ] Directories are copied recursively; files are copied individually
- [ ] Validate paths exist at setup-course time; clear error if a path is missing
- [ ] Tests: files copied, directories copied, missing path error, interaction with readme_source
- [ ] Commit, update docs

## 7. Ensure retire-course archive directory exists
- [ ] Before `shutil.move`, check if `archive_path/year` exists
- [ ] If not, prompt the user: "Archive directory {path} does not exist. Create it? [y/N]"
- [ ] If yes, `mkdir(parents=True)` and proceed
- [ ] If no, fail with clear error
- [ ] Tests: directory exists (no prompt), directory created on yes, fails on no
- [ ] Commit, update docs

## 8. Add `unretire-course` command
- [ ] New CLI entry point: `unretire-course`
- [ ] Takes a path to a retired course directory (in the archive)
- [ ] Makes the GitHub repo public again via API
- [ ] Moves the directory from archive to current working directory
- [ ] Add to `pyproject.toml` entry points
- [ ] Tests: repo made public, directory moved to cwd, error handling
- [ ] Commit, update docs

## Final
- [ ] Version bump to 2.11.0
- [ ] Full QA: ruff format, ruff check, mypy --strict, pytest 100% coverage
- [ ] Update README.md and MANUAL.md with all new features
- [ ] Tag, push, publish
