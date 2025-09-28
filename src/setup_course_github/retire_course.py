#!/usr/bin/env python3

from setup_course_github import get_github
import argparse
import datetime
import os
import shutil
import subprocess


def main():
    # Get the directory of the course we want to retire
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dirname", required=True)
    args = parser.parse_args()
    dirname = args.dirname

    # ------------------------------------------------------------
    # Make the Git repo private
    # Switch to that directory
    print(f"Now retiring repo in {dirname}")
    os.chdir(dirname)
    wd = os.getcwd()
    print(f"Now in directory {wd}")

    # Get the GitHub repo for the current directory
    full_reponame = (
        subprocess.run("git config remote.origin.url", shell=True, capture_output=True)
        .stdout.decode()
        .strip()
    )
    print(f"{full_reponame=}")

    before, after = full_reponame.split("/")
    repo_name = "reuven/" + after.split(".")[0]

    # Connect to GitHub
    g = get_github()

    # get the repo from the current directory!
    print(repo_name)
    repo = g.get_repo(repo_name)
    print(repo)

    repo.edit(private=True)

    # ------------------------------------------------------------
    # Move the directory to the archive
    os.chdir("..")
    wd = os.getcwd()
    print(f"Now in directory {wd}")

    year = datetime.datetime.now().year

    shutil.move(dirname, f"/Users/reuven/Courses/Python/Archive/{year}/")

    print(f"Successfully moved to {dirname}")

if __name__ == '__main__':
    main()
