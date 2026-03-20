from github import Github
from github.AuthenticatedUser import AuthenticatedUser

from setup_course_github.config import load_config

__version__ = "2.12.0"
__author__ = "Reuven Lerner"
__email__ = "reuven@lerner.co.il"


def get_github() -> Github:
    config = load_config()
    return Github(config.github_token)


def get_github_user() -> AuthenticatedUser:
    user = get_github().get_user()
    assert isinstance(user, AuthenticatedUser)
    return user
