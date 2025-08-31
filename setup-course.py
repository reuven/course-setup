#!/usr/bin/env python3

import argparse
import shutil
import os
from github import Github
from pathlib import Path

github_token = open("/Users/reuven/.github_token").read().strip()

parser = argparse.ArgumentParser()

parser.add_argument("-d", "--date", required=True)
parser.add_argument("-c", "--client", required=True)
parser.add_argument("-r", "--repo", required=True)
parser.add_argument("-n", "--name", default="")

args = parser.parse_args()

if args.name:
    suffix = f"-{args.name}"
else:
    suffix = ""

destination = f"{args.client}-{args.date}{suffix}"


# hard-code to be the "generic" directory in the current folder
template_dir = Path(__file__).parent / 'generic'

print(f'Copying from "{template_dir}" to "{destination}"')

shutil.copytree(template_dir, destination)

os.rename(
    f"{destination}/dot-git",
    f"{destination}/.git",
)

os.rename(
    f"{destination}/Course notebook.ipynb",
    f"{destination}/{args.client} - {args.date}{suffix}.ipynb",
)


remote_info = f"""
[core]
        repositoryformatversion = 0
        filemode = true
        bare = false
        logallrefupdates = true
        ignorecase = true
        precomposeunicode = true
[remote "origin"]
        url = git@github.com:reuven/{args.repo}.git
        fetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
        remote = origin
        merge = refs/heads/main
"""




# Write the remote info to the Git configuration file
with open(f"{destination}/.git/config", "w") as outfile:
    outfile.write(remote_info)

# Create the repo on GitHub
g = Github(github_token)
user = g.get_user()
repo = user.create_repo(name=args.repo, private=False)
