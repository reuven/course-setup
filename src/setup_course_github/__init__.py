from importlib.metadata import metadata

from github import Github
from github.AuthenticatedUser import AuthenticatedUser

from setup_course_github.config import load_config

_meta = metadata("course-setup")
__version__: str = _meta["Version"] or "0.0.0"
__author__: str = "Reuven Lerner"
__email__: str = "reuven@lerner.co.il"


def get_github() -> Github:
    config = load_config()
    return Github(config.github_token)


def get_github_user() -> AuthenticatedUser:
    user = get_github().get_user()
    assert isinstance(user, AuthenticatedUser)
    return user
