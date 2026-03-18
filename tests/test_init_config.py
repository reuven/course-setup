from pathlib import Path
from unittest.mock import patch

import pytest

from setup_course_github.init_config import ConfigExistsError, create_config


def test_creates_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    assert config_file.exists()


def test_creates_parent_directories(tmp_path: Path) -> None:
    config_file = tmp_path / "nested" / "dirs" / "config.toml"
    create_config(config_file)
    assert config_file.exists()


def test_config_contains_github_section(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    content = config_file.read_text()
    assert "[github]" in content
    assert "token" in content


def test_config_contains_paths_section(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    content = config_file.read_text()
    assert "[paths]" in content
    assert "archive" in content


def test_config_contains_defaults_section(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    content = config_file.read_text()
    assert "[defaults]" in content
    assert "notebook_type" in content


def test_config_contains_readme_source(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    content = config_file.read_text()
    assert "readme_source" in content


def test_config_is_valid_toml(tmp_path: Path) -> None:
    import tomllib

    config_file = tmp_path / "config.toml"
    create_config(config_file)
    with open(config_file, "rb") as f:
        data = tomllib.load(f)
    assert "github" in data
    assert "paths" in data
    assert "defaults" in data


def test_raises_if_file_exists(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[github]\ntoken = 'existing'\n")
    with pytest.raises(ConfigExistsError):
        create_config(config_file)


def test_force_overwrites_existing(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[github]\ntoken = 'old'\n")
    create_config(config_file, force=True)
    content = config_file.read_text()
    assert "[paths]" in content


def test_main_creates_config(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    with patch("setup_course_github.init_config.CONFIG_PATH", config_file):
        from setup_course_github.init_config import main

        main([])
    assert config_file.exists()


def test_main_force_flag(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[github]\ntoken = 'old'\n")
    with patch("setup_course_github.init_config.CONFIG_PATH", config_file):
        from setup_course_github.init_config import main

        main(["--force"])
    content = config_file.read_text()
    assert "[paths]" in content


def test_main_exits_if_exists_no_force(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text("[github]\ntoken = 'existing'\n")
    with patch("setup_course_github.init_config.CONFIG_PATH", config_file):
        from setup_course_github.init_config import main

        with pytest.raises(SystemExit) as exc_info:
            main([])
    assert exc_info.value.code != 0
