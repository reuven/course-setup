import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "course-setup" / "config.toml"

VALID_NOTEBOOK_TYPES = {"jupyter", "marimo"}


class ConfigError(Exception):
    pass


@dataclass
class CourseConfig:
    github_token: str
    archive_path: Path
    default_notebook_type: str
    readme_source: str | None = None


def load_config(path: Path = CONFIG_PATH) -> CourseConfig:
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}\nRun `setup-course-config` to create it."
        )

    with open(path, "rb") as f:
        data = tomllib.load(f)

    # GitHub token: config file first, then GITHUB_TOKEN env var
    github_section = data.get("github", {})
    github_token: str | None = github_section.get("token") or os.environ.get(
        "GITHUB_TOKEN"
    )
    if not github_token:
        raise ConfigError(
            "github_token not found. "
            "Set [github] token in config or GITHUB_TOKEN env var."
        )

    # Archive path: required
    paths_section = data.get("paths", {})
    raw_archive = paths_section.get("archive")
    if not raw_archive:
        raise ConfigError("archive path not found. Set [paths] archive in config.")
    archive_path = Path(raw_archive)

    # Default notebook type: optional, defaults to "jupyter"
    defaults_section = data.get("defaults", {})
    notebook_type: str = defaults_section.get("notebook_type", "jupyter")
    if notebook_type not in VALID_NOTEBOOK_TYPES:
        valid = ", ".join(sorted(VALID_NOTEBOOK_TYPES))
        raise ConfigError(
            f"Invalid notebook_type '{notebook_type}'. Must be one of: {valid}"
        )

    # README source: optional file path or URL
    readme_source: str | None = paths_section.get("readme_source")

    return CourseConfig(
        github_token=github_token,
        archive_path=archive_path,
        default_notebook_type=notebook_type,
        readme_source=readme_source,
    )
