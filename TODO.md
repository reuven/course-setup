# course-setup: Road to 1.0.0

## Config file

Location: `~/.config/course-setup/config.toml`

## CLI commands

- `setup-course` — create a new course repo (existing)
- `retire-course` — archive a course repo (existing)
- `setup-course-config` — NEW: create `~/.config/course-setup/config.toml` with commented template

```toml
[github]
token = "ghp_..."          # fallback: GITHUB_TOKEN env var

[paths]
archive = "/path/to/Archive"

[defaults]
notebook_type = "jupyter"  # or "marimo"
```

---

## Tasks

### Phase 1 — Tooling & Infrastructure
- [x] 1. Add dev dependencies and tool config to `pyproject.toml`: black, ruff, mypy, pytest, pytest-cov
- [x] 2. Create `src/setup_course_github/config.py`: load/validate config from `~/.config/course-setup/config.toml`; fall back to `GITHUB_TOKEN` env var for token
- [x] 3. Create `src/setup_course_github/init_config.py`: `setup-course-config` command that writes a commented template config to `~/.config/course-setup/config.toml` (errors if file already exists, unless `--force`)

### Phase 2 — Refactor existing code (TDD: tests first)
- [x] 3. Refactor `__init__.py`: use config module; remove hardcoded token path
- [x] 4. Write tests for `init_config.py`
- [x] 5. Refactor `setup_course.py`:
       - Use config for GitHub username
       - Add `--notebook-type` flag (jupyter | marimo, default: jupyter)
       - Rename/create the correct notebook file
       - Generate a `pyproject.toml` in the new course dir (with jupyter/marimo + gitautopush deps)
       - Add type hints throughout
- [x] 6. Refactor `retire_course.py`:
       - Use config for archive path and GitHub username
       - Add type hints throughout

### Phase 3 — Tests (100% coverage)
- [x] 7. Write tests for `config.py`
- [x] 8. Write tests for `setup_course.py` (mock GitHub API + filesystem)
- [x] 9. Write tests for `retire_course.py` (mock GitHub API + filesystem)

### Phase 4 — Quality gates
- [x] 10. Format all code with `black`; lint with `ruff`; type-check with `mypy --strict`
- [x] 11. Confirm `pytest --cov` reports 100% coverage

### Phase 5 — Polish & publish
- [x] 12. Write a proper `README.md` (install, config, usage, examples)
- [x] 13. Update `pyproject.toml` metadata (description, author, license, URLs, classifiers, version → 1.0.0)
- [x] 14. Add `setup-course-config` entry point to `pyproject.toml`
- [x] 15. Build (`uv build`)
