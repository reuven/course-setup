# Modernize pyproject.toml

- [x] Switch build backend from setuptools to uv_build
- [x] Add "B" (bugbear) and "UP" (pyupgrade) to ruff lint rules, add fixable = ["ALL"]
- [x] Migrate pytest config from [tool.pytest.ini_options] to [tool.pytest]
- [x] Run ruff check/format, mypy, and tests to verify everything still works
- [ ] Commit changes
