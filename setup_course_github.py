from github import Github

def get_github():
    github_token = open("/Users/reuven/.github_token").read().strip()
    return Github(github_token)

def get_github_user():
    return get_github().get_user()
