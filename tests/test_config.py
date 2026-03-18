import os
from pathlib import Path
from unittest.mock import patch

import pytest

from setup_course_github.config import (
    CONFIG_PATH,
    ConfigError,
    CourseConfig,
    load_config,
)

MINIMAL_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"
"""

FULL_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"

[defaults]
notebook_type = "marimo"
"""

MISSING_TOKEN_TOML = """
[paths]
archive = "/tmp/archive"
"""

MISSING_ARCHIVE_TOML = """
[github]
token = "ghp_testtoken"
"""


def test_config_path_is_xdg():
    assert CONFIG_PATH == Path.home() / ".config" / "course-setup" / "config.toml"


def test_load_config_minimal(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(MINIMAL_TOML)
    config = load_config(config_file)
    assert config.github_token == "ghp_testtoken"
    assert config.archive_path == Path("/tmp/archive")
    assert config.default_notebook_type == "jupyter"


def test_load_config_full(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(FULL_TOML)
    config = load_config(config_file)
    assert config.github_token == "ghp_testtoken"
    assert config.archive_path == Path("/tmp/archive")
    assert config.default_notebook_type == "marimo"


def test_load_config_token_from_env(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(MISSING_TOKEN_TOML)
    with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
        config = load_config(config_file)
    assert config.github_token == "env_token"


def test_load_config_missing_token_no_env(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(MISSING_TOKEN_TOML)
    with patch.dict(os.environ, {}, clear=True):
        # Remove GITHUB_TOKEN if it happens to exist in the environment
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigError, match="github_token"):
                load_config(config_file)


def test_load_config_missing_archive(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(MISSING_ARCHIVE_TOML)
    with pytest.raises(ConfigError, match="archive"):
        load_config(config_file)


def test_load_config_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-file.toml"
    with pytest.raises(ConfigError, match="not found"):
        load_config(missing)


def test_invalid_notebook_type(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(MINIMAL_TOML + '\n[defaults]\nnotebook_type = "invalid"\n')
    with pytest.raises(ConfigError, match="notebook_type"):
        load_config(config_file)


def test_course_config_dataclass() -> None:
    config = CourseConfig(
        github_token="tok",
        archive_path=Path("/tmp"),
        default_notebook_type="jupyter",
    )
    assert config.github_token == "tok"
    assert config.archive_path == Path("/tmp")
    assert config.default_notebook_type == "jupyter"
