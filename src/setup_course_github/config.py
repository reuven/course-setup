import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_config_dir

CONFIG_PATH = Path(user_config_dir("course-setup")) / "config.toml"
LEGACY_CONFIG_PATH = Path.home() / ".config" / "course-setup" / "config.toml"

VALID_NOTEBOOK_TYPES = {"jupyter", "marimo"}
VALID_WEEKEND_TYPES = {"standard", "israeli"}


class ConfigError(Exception):
    pass


@dataclass
class CourseConfig:
    github_token: str
    archive_path: Path
    default_notebook_type: str
    readme_source: str | None = None
    default_verbose: bool = False
    default_extras_group: str | None = None
    custom_extras: dict[str, list[str]] = field(default_factory=dict)
    default_weekend: str | None = None
    additional_files: list[str] = field(default_factory=list)
    default_private: bool = False


def load_config(path: Path = CONFIG_PATH) -> CourseConfig:
    if not path.exists():
        # Check for legacy ~/.config path when using the default location
        if path == CONFIG_PATH and LEGACY_CONFIG_PATH.exists():
            raise ConfigError(
                f"Config file found at old location: {LEGACY_CONFIG_PATH}\n"
                f"Please move it to the new location:\n"
                f'  mv "{LEGACY_CONFIG_PATH}" "{CONFIG_PATH}"'
            )
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

    # Default verbose: optional, defaults to False
    raw_verbose: object = defaults_section.get("verbose", False)
    if not isinstance(raw_verbose, bool):
        raise ConfigError(
            f"Invalid verbose value '{raw_verbose}'. Must be true or false"
        )
    default_verbose: bool = raw_verbose

    # Default extras group: optional, defaults to None
    raw_extras_group: object = defaults_section.get("extras_group")
    default_extras_group: str | None = None
    if raw_extras_group is not None:
        if not isinstance(raw_extras_group, str):
            raise ConfigError(
                f"Invalid extras_group value '{raw_extras_group}'. "
                "Must be a string (group name)"
            )
        default_extras_group = raw_extras_group

    # README source: optional file path or URL
    readme_source: str | None = paths_section.get("readme_source")

    # Custom extras groups: optional
    extras_section = data.get("extras", {})
    custom_extras: dict[str, list[str]] = {}
    for group_name, packages in extras_section.items():
        if not isinstance(packages, list):
            raise ConfigError(f"extras.{group_name} must be a list of package names")
        custom_extras[group_name] = [str(p) for p in packages]

    # Default weekend: optional, defaults to None
    raw_weekend: object = defaults_section.get("weekend")
    default_weekend: str | None = None
    if raw_weekend is not None:
        if not isinstance(raw_weekend, str) or raw_weekend not in VALID_WEEKEND_TYPES:
            valid = ", ".join(sorted(VALID_WEEKEND_TYPES))
            raise ConfigError(
                f"Invalid weekend value '{raw_weekend}'. Must be one of: {valid}"
            )
        default_weekend = raw_weekend

    # Default private: optional, defaults to False
    raw_private: object = defaults_section.get("private", False)
    if not isinstance(raw_private, bool):
        raise ConfigError(
            f"Invalid private value '{raw_private}'. Must be true or false"
        )
    default_private: bool = raw_private

    # Additional files: optional list of file/directory paths to copy
    raw_additional_files: object = paths_section.get("additional_files", [])
    if not isinstance(raw_additional_files, list):
        raise ConfigError("additional_files must be a list of file/directory paths")
    additional_files: list[str] = [str(f) for f in raw_additional_files]

    return CourseConfig(
        github_token=github_token,
        archive_path=archive_path,
        default_notebook_type=notebook_type,
        readme_source=readme_source,
        default_verbose=default_verbose,
        default_extras_group=default_extras_group,
        custom_extras=custom_extras,
        default_weekend=default_weekend,
        additional_files=additional_files,
        default_private=default_private,
    )
