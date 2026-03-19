# course-setup: Instruction Manual

## Overview

`course-setup` is a command-line toolkit for managing GitHub-backed course
repositories. It provides three commands:

- **`setup-course`** — Create a new course directory with a notebook, a
  `pyproject.toml`, a Git repo, and a matching public GitHub repo.
- **`retire-course`** — Archive a finished course by making its GitHub repo
  private and moving the local directory into a dated archive folder.
- **`setup-course-config`** — Generate a starter configuration file.

---

## Prerequisites

- Python 3.13 or later
- A GitHub account with a personal access token (classic)
- Git configured with SSH access to GitHub (`git@github.com:...`)
- An existing directory to use as your course archive (for `retire-course`)

### Creating a GitHub personal access token

1. Go to **GitHub > Settings > Developer settings > Personal access tokens >
   Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. Give it a descriptive name (e.g., "course-setup").
4. Select at minimum the **`repo`** scope (full control of private
   repositories). If you plan to use `retire-course`, also select
   **`delete_repo`**.
5. Click **Generate token** and copy the token immediately — you won't be able
   to see it again.

---

## Installation

Because `course-setup` is a standalone CLI tool (not a library you import into
projects), the recommended way to install it is as a
[uv tool](https://docs.astral.sh/uv/concepts/tools/):

```
uv tool install course-setup
```

This installs it in an isolated environment and makes the three commands
available globally on your PATH:

- `setup-course`
- `retire-course`
- `setup-course-config`

To upgrade later:

```
uv tool upgrade course-setup
```

Alternatively, you can install with pip:

```
pip install course-setup
```

For a development install from a local clone:

```
git clone https://github.com/reuven/course-setup.git
cd course-setup
uv sync
```

---

## Configuration

### Step 1: Generate the config file

Run:

```
setup-course-config
```

This creates the file `~/.config/course-setup/config.toml` with a commented
template. If the file already exists, the command will refuse to overwrite it
unless you pass `--force`:

```
setup-course-config --force
```

### Step 2: Edit the config file

Open `~/.config/course-setup/config.toml` in your editor. It looks like this:

```toml
# course-setup configuration file

[github]
# Your GitHub personal access token.
# Needs: repo (read/write), delete_repo (if using retire-course)
# Alternatively, set the GITHUB_TOKEN environment variable.
token = "ghp_YOUR_TOKEN_HERE"

[paths]
# Directory where retired course repos are archived.
# Example: "/Users/yourname/Courses/Archive"
archive = "/path/to/your/archive"

# Optional: path or URL to a custom README.md for new courses.
# If not set, the bundled default README is used.
# Examples:
#   readme_source = "/Users/yourname/templates/README.md"
#   readme_source = "https://example.com/my-readme.md"
# readme_source = ""

[defaults]
# Default notebook type when running setup-course.
# Options: "jupyter" or "marimo"
notebook_type = "jupyter"
```

Fill in each section:

| Setting | Required | Description |
|---------|----------|-------------|
| `[github] token` | Yes* | Your GitHub personal access token. |
| `[paths] archive` | Yes | Absolute path to the directory where retired courses are stored. |
| `[paths] readme_source` | No | Path or URL to a custom README.md. When set, `setup-course` uses this instead of the bundled default. Can be a local file path or an `https://` URL. |
| `[defaults] notebook_type` | No | `"jupyter"` (default) or `"marimo"`. Controls which kind of notebook file `setup-course` creates. |
| `[defaults] verbose` | No | `true` or `false` (default). When `true`, `setup-course` prints detailed output by default. Can be overridden with `-v` on the command line. |
| `[defaults] extras_group` | No | Name of a dependency group to use by default when `--extras` is not passed on the command line. Can be a built-in group (e.g. `"python"`, `"data"`) or a custom group defined in `[extras]`. |
| `[extras] <name>` | No | Custom dependency groups for `--extras`. Each key is a group name, each value is a list of package names. |

*You can omit the token from the config file and set the `GITHUB_TOKEN`
environment variable instead. If both are set, the config file value takes
precedence.

---

## Commands

### `setup-course` — Create a new course

#### Synopsis

```
setup-course -c CLIENT -t TOPIC [-d YYYY-MM] [-n NUM] [--freq daily|weekly] [--notebook-type TYPE] [--extras GROUP ...] [--add-imports] [-v] [--dry-run]
```

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `-c`, `--client` | Yes | The client or company name. |
| `-t`, `--topic` | Yes | The course topic (e.g., `python-intro`, `pandas`). |
| `-d`, `--date` | No | Override the year-month in `YYYY-MM` format. Defaults to the current month. |
| `-n`, `--num-sessions` | No | Number of sessions. Creates one notebook per session. |
| `--freq` | No | Session frequency: `daily` or `weekly`. Requires `-n`. Defaults to `daily` when `-n` is given. |
| `--notebook-type` | No | `jupyter` or `marimo`. Overrides the default from your config file. |
| `--extras` | No | One or more dependency groups to add to the course `pyproject.toml`. See [Dependency groups](#dependency-groups) below. |
| `--add-imports` | No | Pre-populate each notebook with import statements matching the `--extras` groups. Has no effect without `--extras`. |
| `-v`, `--verbose` | No | Show detailed output for each step: template and destination paths, notebook filenames, dependency list, GitHub username, repo name, and remote URL. Overrides the `[defaults] verbose` config setting. |
| `--dry-run` | No | Print a summary of what would be created (repo name, directory, notebooks, dependencies) without making any changes. No filesystem, Git, or GitHub API calls are made. |

#### Dependency groups

The `--extras` flag accepts one or more group names. Each group adds a set of
packages to the generated `pyproject.toml`:

| Group | Packages | Use case |
|-------|----------|----------|
| `python` | ipython | Python courses (enhanced REPL in Jupyter) |
| `data` | numpy, pandas, xlrd, openpyxl, pyarrow | Data / Pandas courses |
| `viz` | matplotlib, seaborn, plotly | Visualization libraries (matplotlib, seaborn, plotly) |
| `geo` | geopandas, folium, shapely | Geospatial / mapping courses |
| `db` | duckdb, sqlalchemy | Database courses |
| `ml` | scikit-learn | Machine learning courses |

You can combine groups freely:

```
setup-course -c Acme -t pandas --extras python data
setup-course -c Acme -t geo-analysis --extras python data geo
setup-course -c Acme -t ml-intro --extras python data ml
```

Duplicate packages across groups are automatically deduplicated and sorted.

##### Custom groups

You can define additional groups (or override built-in ones) in your
`config.toml`:

```toml
[extras]
finance = ["yfinance", "pandas-datareader"]
nlp = ["spacy", "nltk"]
```

Custom groups are merged with the built-in groups. If a custom group has the
same name as a built-in group, the custom definition takes precedence.

#### What it does

1. **Auto-generates a repo name** from the client, topic, and date:
   `{client}-{topic}-{YYYY-MM}`. The same name is used for the local
   directory and the GitHub repository.

2. **Copies the bundled course template** into a new directory in the current
   working directory.

3. **Creates notebook file(s)** in the new directory. Each notebook is named
   `{client}-{topic}-{YYYY-MM-DD}.ipynb` (or `.py` for Marimo), where
   YYYY-MM-DD is the session date. By default a single notebook is created for
   today. With `-n`, multiple notebooks are created — one per session, with
   dates advancing daily or weekly from today.

4. **Generates a `pyproject.toml`** in the new directory with the repo name,
   a dependency on either `jupyter` or `marimo`, `gitautopush`, and any
   additional packages from `--extras` groups.

5. **Creates a public GitHub repository** using the GitHub API and configures
   the local `.git/config` with the correct SSH remote URL, using the
   authenticated user's GitHub username.

6. **Makes an initial commit and pushes** to GitHub, so the repo is ready for
   `gitautopush` immediately.

7. **Runs `uv sync`** in the course directory to install all dependencies, so
   you can start Jupyter or Marimo right away.

#### Examples

Single session (run on 2026-03-19):

```
setup-course -c Acme -t python-intro
```

Creates:

```
Acme-python-intro-2026-03/
  .git/
    config           # remote set to git@github.com:youruser/Acme-python-intro-2026-03.git
  Acme-python-intro-2026-03-19.ipynb
  pyproject.toml
  README.md
```

Multi-day course (5 daily sessions starting March 17):

```
setup-course -c Acme -t python-intro -n 5
```

Creates 5 notebooks:
`Acme-python-intro-2026-03-17.ipynb` through
`Acme-python-intro-2026-03-21.ipynb`.

Weekly course (5 weekly sessions starting March 3):

```
setup-course -c Acme -t python-intro -n 5 --freq weekly
```

Creates 5 notebooks:
`Acme-python-intro-2026-03-03.ipynb`,
`Acme-python-intro-2026-03-10.ipynb`,
`Acme-python-intro-2026-03-17.ipynb`,
`Acme-python-intro-2026-03-24.ipynb`,
`Acme-python-intro-2026-03-31.ipynb`.

With a date override:

```
setup-course -c Acme -t python-intro -d 2025-11
```

Creates the directory `Acme-python-intro-2025-11/` with notebook
`Acme-python-intro-2026-03-19.ipynb` (the day always comes from today).

With dependency groups:

```
setup-course -c Acme -t pandas --extras python data
```

Creates the course with ipython, numpy, pandas, xlrd, openpyxl, pyarrow, and plotly
added to the `pyproject.toml` dependencies alongside jupyter and gitautopush.

With pre-populated imports:

```
setup-course -c Acme -t pandas --extras python data --add-imports
```

Same as above, but each notebook starts with a code cell containing:
`import numpy as np`, `import pandas as pd`, `import plotly.express as px`.

With Marimo:

```
setup-course -c Acme -t python-intro --notebook-type marimo
```

Creates `Acme-python-intro-2026-03-19.py` instead of the `.ipynb`.

Dry run (preview without creating anything):

```
setup-course -c Acme -t python-intro --extras data --dry-run
```

Outputs a summary of what would be created, then exits. No files, Git
repos, or GitHub repos are created.

Verbose output:

```
setup-course -c Acme -t python-intro -v
```

Shows detailed information about each step, including template path,
destination, notebook filenames, dependencies, GitHub user, and remote URL.

#### Error handling and rollback

If any step fails during course creation (e.g., the GitHub API call fails
or `git push` is rejected), `setup-course` automatically rolls back
completed steps in reverse order:

- If the GitHub repository was created, it is deleted.
- If the local directory was created, it is removed.

A clear error message is printed along with the rollback actions. The
command exits with code 1 on failure. If a cleanup action itself fails, a
warning is printed and the remaining cleanup actions still execute.

---

### `retire-course` — Archive a finished course

#### Synopsis

```
retire-course DIRNAME [DIRNAME ...]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `DIRNAME...` | Yes | One or more paths to course directories to retire. |

#### What it does

For each directory:

1. **Reads the Git remote URL** from the course directory's `.git/config`.
2. **Makes the GitHub repository private** via the GitHub API.
3. **Moves the local directory** into `{archive_path}/{current_year}/`, where
   `archive_path` is the value from your config file and `current_year` is the
   four-digit year (e.g., `2026`).

If any directory fails, the remaining directories are still processed and all
errors are reported at the end.

#### Examples

Single course:

```
retire-course ./Acme-2026-03-18
```

Multiple courses at once:

```
retire-course ./Acme-2026-03 ./Beta-2026-03 ./Gamma-2026-02
```

If your archive path is `/Users/reuven/Courses/Archive`, this moves the
directory to `/Users/reuven/Courses/Archive/2026/Acme-2026-03-18` and sets
the GitHub repo to private.

#### Requirements

- The course directory must be a Git repo with an SSH remote URL in the format
  `git@github.com:username/reponame.git`.
- Your GitHub token must have the `repo` scope (and `delete_repo` if needed).
- The archive directory must already exist. The year subdirectory
  (e.g., `2026/`) will be the move target, so it should exist or the parent
  must allow creation.

---

### `setup-course-config` — Generate a config file

#### Synopsis

```
setup-course-config [--force]
```

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--force` | No | Overwrite an existing config file. Without this flag, the command will refuse to overwrite. |

#### What it does

Writes a commented template to `~/.config/course-setup/config.toml`. Creates
the parent directories if they don't exist.

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | Fallback GitHub token. Used when `[github] token` is not set in the config file. |

---

## Typical workflow

```
# One-time setup
uv tool install course-setup
setup-course-config
# Edit ~/.config/course-setup/config.toml with your token, archive path, etc.

# Before each course
setup-course -c Acme -t python-intro --extras python data

# After the course is over
retire-course ./Acme-python-intro-2026-03
```

---

## Live teaching with gitautopush

Every course created by `setup-course` includes `gitautopush` as a dependency
in its `pyproject.toml`. During a live teaching session you can use it to
automatically push your notebook changes to GitHub so that students can follow
along from their own computers.

### Steps

1. Run `setup-course` as usual and start your Jupyter or Marimo session.
2. Open a **separate terminal window**.
3. `cd` into the course directory (e.g., `cd Acme-python-intro-2026-03`).
4. Run:

   ```
   uv run gitautopush .
   ```

5. `gitautopush` watches the directory for changes and pushes updated files to
   GitHub every few minutes.
6. Students can view the **public GitHub repository** from their own computers
   to get a read-only, auto-updating copy of the notebook.
7. Keep `gitautopush` running for the entire duration of the teaching session.
   When you are done, press `Ctrl-C` to stop it.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Config file not found` | Run `setup-course-config` to create it, then edit it. |
| `github_token not found` | Set `token` in the `[github]` section of your config, or export `GITHUB_TOKEN`. |
| `archive path not found` | Set `archive` in the `[paths]` section of your config. |
| `Invalid notebook_type` | Must be `"jupyter"` or `"marimo"` in the `[defaults]` section. |
| `Config file already exists` | Use `setup-course-config --force` to overwrite. |
| GitHub API 401 error | Your token is invalid or expired. Generate a new one. |
| GitHub API 403 error | Your token doesn't have the required scopes (`repo`, `delete_repo`). |
| `Permission denied` on SSH push | Make sure your SSH key is added to your GitHub account and `ssh -T git@github.com` works. |
