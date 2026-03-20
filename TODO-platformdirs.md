# Use platformdirs for cross-platform config path

- [x] Add `platformdirs` dependency via `uv add`
- [x] Update `config.py` to use `platformdirs.user_config_dir()` instead of hardcoded `~/.config`
- [x] Update test `test_config_path_is_xdg` to verify platformdirs-based path
- [x] Run ruff, mypy, and full test suite
- [x] Update README and MANUAL with platform-specific paths
- [x] Add legacy config path migration check with tests
- [x] Commit changes
