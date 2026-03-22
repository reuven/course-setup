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


def test_config_contains_extras_section(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    content = config_file.read_text()
    assert "extras" in content.lower()


# ---------------------------------------------------------------------------
# Additional QA tests
# ---------------------------------------------------------------------------


def test_main_error_prints_to_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When config exists and --force is not used, error goes to stderr."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("[github]\ntoken = 'existing'\n")
    with patch("setup_course_github.init_config.CONFIG_PATH", config_file):
        from setup_course_github.init_config import main

        with pytest.raises(SystemExit):
            main([])
    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "Error" not in captured.out


def test_config_template_mentions_verbose(tmp_path: Path) -> None:
    """The generated config template should mention 'verbose'."""
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    content = config_file.read_text()
    assert "verbose" in content


def test_config_template_mentions_weekend(tmp_path: Path) -> None:
    """The generated config template should mention 'weekend'."""
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    content = config_file.read_text()
    assert "weekend" in content


def test_config_template_mentions_extras_group(tmp_path: Path) -> None:
    """The generated config template should mention 'extras_group'."""
    config_file = tmp_path / "config.toml"
    create_config(config_file)
    content = config_file.read_text()
    assert "extras_group" in content


# ---------------------------------------------------------------------------
# --version flag
# ---------------------------------------------------------------------------


def test_version_flag_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    """--version prints the version, PyPI URL, and author info."""
    from setup_course_github import __author__, __email__, __version__
    from setup_course_github.init_config import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert __version__ in output
    assert "https://pypi.org/project/course-setup/" in output
    assert __author__ in output
    assert __email__ in output


def test_help_shows_version_and_url(capsys: pytest.CaptureFixture[str]) -> None:
    """--help output contains version, PyPI URL, and author name."""
    from setup_course_github import __author__, __version__
    from setup_course_github.init_config import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert __version__ in output
    assert "https://pypi.org/project/course-setup/" in output
    assert __author__ in output


def test_help_shows_config_path(capsys: pytest.CaptureFixture[str]) -> None:
    """--help output shows the config file path."""
    from setup_course_github.config import CONFIG_PATH
    from setup_course_github.init_config import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert str(CONFIG_PATH) in output
