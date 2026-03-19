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

README_SOURCE_FILE_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"
readme_source = "/path/to/my/README.md"
"""

README_SOURCE_URL_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"
readme_source = "https://example.com/README.md"
"""

MISSING_TOKEN_TOML = """
[paths]
archive = "/tmp/archive"
"""

MISSING_ARCHIVE_TOML = """
[github]
token = "ghp_testtoken"
"""


def test_config_path_is_xdg() -> None:
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
    assert config.readme_source is None


def test_readme_source_defaults_to_none(tmp_path: Path) -> None:
    """When readme_source is not in config, it defaults to None."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(MINIMAL_TOML)
    config = load_config(config_file)
    assert config.readme_source is None


def test_readme_source_file_path(tmp_path: Path) -> None:
    """readme_source can be a local file path."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(README_SOURCE_FILE_TOML)
    config = load_config(config_file)
    assert config.readme_source == "/path/to/my/README.md"


def test_readme_source_url(tmp_path: Path) -> None:
    """readme_source can be a URL."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(README_SOURCE_URL_TOML)
    config = load_config(config_file)
    assert config.readme_source == "https://example.com/README.md"


# ---------------------------------------------------------------------------
# Hardening tests
# ---------------------------------------------------------------------------


def test_config_token_takes_precedence_over_env(tmp_path: Path) -> None:
    """When both config file and env have a token, config file wins."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(MINIMAL_TOML)  # has ghp_testtoken
    with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_should_lose"}):
        config = load_config(config_file)
    assert config.github_token == "ghp_testtoken"


def test_empty_token_in_config_falls_back_to_env(tmp_path: Path) -> None:
    """An empty string token in config should fall back to GITHUB_TOKEN env var."""
    toml_content = """
[github]
token = ""

[paths]
archive = "/tmp/archive"
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(toml_content)
    with patch.dict(os.environ, {"GITHUB_TOKEN": "env_fallback_token"}):
        config = load_config(config_file)
    assert config.github_token == "env_fallback_token"


def test_empty_readme_source_is_stored(tmp_path: Path) -> None:
    """An empty readme_source string is stored (not converted to None)."""
    toml_content = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"
readme_source = ""
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(toml_content)
    config = load_config(config_file)
    # Note: empty string is truthy-ish for paths, which might cause issues
    # downstream. This test documents the current behavior.
    assert config.readme_source == ""


def test_config_ignores_unknown_keys(tmp_path: Path) -> None:
    """Unknown keys in the config file are silently ignored."""
    toml_content = """
[github]
token = "ghp_testtoken"
unknown_key = "whatever"

[paths]
archive = "/tmp/archive"

[some_random_section]
foo = "bar"
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(toml_content)
    config = load_config(config_file)
    assert config.github_token == "ghp_testtoken"


# ---------------------------------------------------------------------------
# Custom extras tests
# ---------------------------------------------------------------------------

CUSTOM_EXTRAS_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"

[extras]
finance = ["yfinance", "pandas-datareader"]
nlp = ["spacy", "nltk"]
"""

CUSTOM_EXTRAS_OVERRIDE_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"

[extras]
data = ["polars", "duckdb"]
"""

INVALID_EXTRAS_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"

[extras]
bad_group = "not-a-list"
"""


def test_custom_extras_loaded(tmp_path: Path) -> None:
    """Custom extras groups are loaded from [extras] section."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(CUSTOM_EXTRAS_TOML)
    config = load_config(config_file)
    assert "finance" in config.custom_extras
    assert config.custom_extras["finance"] == ["yfinance", "pandas-datareader"]
    assert "nlp" in config.custom_extras
    assert config.custom_extras["nlp"] == ["spacy", "nltk"]


def test_custom_extras_empty_by_default(tmp_path: Path) -> None:
    """When no [extras] section, custom_extras is empty dict."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(MINIMAL_TOML)
    config = load_config(config_file)
    assert config.custom_extras == {}


def test_custom_extras_override_builtin_name(tmp_path: Path) -> None:
    """Custom group with same name as built-in is loaded."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(CUSTOM_EXTRAS_OVERRIDE_TOML)
    config = load_config(config_file)
    assert config.custom_extras["data"] == ["polars", "duckdb"]


def test_custom_extras_invalid_type_raises(tmp_path: Path) -> None:
    """Non-list value in [extras] raises ConfigError."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(INVALID_EXTRAS_TOML)
    with pytest.raises(ConfigError, match="extras.bad_group"):
        load_config(config_file)


# ---------------------------------------------------------------------------
# Default verbose tests
# ---------------------------------------------------------------------------

VERBOSE_TRUE_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"

[defaults]
verbose = true
"""

VERBOSE_INVALID_TOML = """
[github]
token = "ghp_testtoken"

[paths]
archive = "/tmp/archive"

[defaults]
verbose = "yes"
"""


def test_default_verbose_defaults_to_false(tmp_path: Path) -> None:
    """When verbose is not in config, it defaults to False."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(MINIMAL_TOML)
    config = load_config(config_file)
    assert config.default_verbose is False


def test_default_verbose_true(tmp_path: Path) -> None:
    """verbose = true in config sets default_verbose to True."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(VERBOSE_TRUE_TOML)
    config = load_config(config_file)
    assert config.default_verbose is True


def test_default_verbose_invalid_type_raises(tmp_path: Path) -> None:
    """Non-boolean verbose value raises ConfigError."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(VERBOSE_INVALID_TOML)
    with pytest.raises(ConfigError, match="verbose"):
        load_config(config_file)
