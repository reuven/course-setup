# course-setup: Instruction Manual

## Overview

`course-setup` is a command-line toolkit for managing GitHub-backed course
repositories. It provides five commands:

- **`setup-course`** — Create a new course directory with a notebook, a
  `pyproject.toml`, a Git repo, and a matching GitHub repo (public or private).
- **`retire-course`** — Archive a finished course by making its GitHub repo
  private and moving the local directory into a dated archive folder.
- **`unretire-course`** — Restore a previously retired course by making its
  GitHub repo public again and moving the directory back to your working
  directory.
- **`archive-course`** — Create a zip archive of a course directory, optionally
  exporting Jupyter notebooks to HTML.
- **`setup-course-config`** — Generate a starter configuration file.

All five commands support `--version` and `--help`. Both display the version
number, PyPI URL, author name (Reuven Lerner), and email address:

```
setup-course --version
retire-course --version
unretire-course --version
archive-course --version
setup-course-config --version
```

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

This installs it in an isolated environment and makes the five commands
available globally on your PATH:

- `setup-course`
- `retire-course`
- `unretire-course`
- `archive-course`
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

This creates a `config.toml` file in your platform's standard config directory
with a commented template. The location depends on your operating system:

| OS | Config path |
|----|-------------|
| macOS | `~/Library/Application Support/course-setup/config.toml` |
| Linux | `~/.config/course-setup/config.toml` |
| Windows | `%APPDATA%\course-setup\config.toml` |

If the file already exists, the command will refuse to overwrite it
unless you pass `--force`:

```
setup-course-config --force
```

### Step 2: Edit the config file

Open the generated `config.toml` in your editor. It looks like this:

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

# Optional: additional files or directories to copy into every new course.
# Examples: data files, exercise notebooks, solutions folder
# additional_files = ["/path/to/exercises", "/path/to/data.csv"]

[defaults]
# Default notebook type when running setup-course.
# Options: "jupyter" or "marimo"
notebook_type = "jupyter"

# Whether to show verbose output by default.
# Can be overridden with -v / --verbose on the command line.
# verbose = false

# Default dependency group to include when --extras is not specified.
# Can be a built-in group (python, data, viz, geo, db, ml) or a custom
# group defined in [extras] below.
# Example: extras_group = "python"
# extras_group = ""

# Whether to create private GitHub repos by default.
# Can be overridden with --private on the command line.
# private = false

# Weekend skipping policy for notebook date scheduling.
# Options: "standard" (skip Sat+Sun) or "israeli" (skip Fri+Sat)
# Can be overridden with --skip-weekends or --skip-israeli-weekends
# on the command line.
# weekend = "standard"

# [extras]
# Define custom dependency groups for --extras.
# These merge with built-in groups (python, data, viz, geo, db, ml).
# A custom group with the same name as a built-in group overrides it.
# Example:
# finance = ["yfinance", "pandas-datareader"]
# nlp = ["spacy", "nltk"]
```

Fill in each section:

| Setting | Required | Description |
|---------|----------|-------------|
| `[github] token` | Yes* | Your GitHub personal access token. |
| `[paths] archive` | Yes | Absolute path to the directory where retired courses are stored. |
| `[paths] readme_source` | No | Path or URL to a custom README.md. When set, `setup-course` uses this instead of the bundled default. Can be a local file path or an `https://` URL. |
| `[paths] additional_files` | No | List of file or directory paths to copy into every new course directory after template setup. Directories are copied recursively. This is additive -- the listed items are copied alongside the standard template files, not in place of them. |
| `[defaults] notebook_type` | No | `"jupyter"` (default) or `"marimo"`. Controls which kind of notebook file `setup-course` creates. |
| `[defaults] verbose` | No | `true` or `false` (default). When `true`, `setup-course` prints detailed output by default. Can be overridden with `-v` on the command line. |
| `[defaults] private` | No | `true` or `false` (default). When `true`, `setup-course` creates private GitHub repos by default. Can be overridden with `--private` on the command line. |
| `[defaults] extras_group` | No | Name of a dependency group to use by default when `--extras` is not passed on the command line. Can be a built-in group (e.g. `"python"`, `"data"`) or a custom group defined in `[extras]`. |
| `[defaults] weekend` | No | `"standard"` or `"israeli"`. Sets the default weekend-skipping policy for notebook date scheduling. `"standard"` skips Saturday and Sunday; `"israeli"` skips Friday and Saturday. Can be overridden on the command line with `--skip-weekends` or `--skip-israeli-weekends`. |
| `[extras] <name>` | No | Custom dependency groups for `--extras`. Each key is a group name, each value is a list of package names. |

*You can omit the token from the config file and set the `GITHUB_TOKEN`
environment variable instead. If both are set, the config file value takes
precedence.

#### Additional files example

To automatically include a `data/` folder and a `solutions.py` file in every
new course:

```toml
[paths]
archive = "/Users/reuven/Courses/Archive"
additional_files = [
    "/Users/reuven/templates/data",
    "/Users/reuven/templates/solutions.py",
]
```

When `setup-course` runs, it copies each entry into the new course directory:

- A **directory** (like `data/`) is copied recursively, preserving its name
  and structure.
- A **file** (like `solutions.py`) is copied directly into the course
  directory.

If any path in `additional_files` does not exist, `setup-course` raises an
error and rolls back.

---

## Commands

### `setup-course` -- Create a new course

#### Synopsis

```
setup-course -c CLIENT -t TOPIC [-d YYYY-MM] [-n NUM] [--freq daily|weekly]
             [--first-notebook-date YYYY-MM-DD]
             [--skip-weekends | --skip-israeli-weekends]
             [--notebook-type TYPE] [--extras GROUP ...] [--add-imports]
             [--private] [-v] [--dry-run] [--version]
```

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `-c`, `--client` | Yes | The client or company name. |
| `-t`, `--topic` | Yes | The course topic (e.g., `python-intro`, `pandas`). |
| `-d`, `--date` | No | Override the year-month in `YYYY-MM` format. Must be a valid month (01--12) and the year cannot be more than 2 years in the future. Defaults to the current month. |
| `-n`, `--num-sessions` | No | Number of sessions. Creates one notebook per session. |
| `--freq` | No | Session frequency: `daily` or `weekly`. Requires `-n`. Defaults to `daily` when `-n` is given. |
| `--first-notebook-date` | No | Start date for notebook files in `YYYY-MM-DD` format. When set, notebook dates begin from this date instead of today. Useful for scheduling a course that starts in the future. |
| `--skip-weekends` | No | Skip Saturdays and Sundays when scheduling notebook dates. Mutually exclusive with `--skip-israeli-weekends`. |
| `--skip-israeli-weekends` | No | Skip Fridays and Saturdays when scheduling notebook dates. Mutually exclusive with `--skip-weekends`. |
| `--notebook-type` | No | `jupyter` or `marimo`. Overrides the default from your config file. |
| `--extras` | No | One or more dependency groups to add to the course `pyproject.toml`. See [Dependency groups](#dependency-groups) below. |
| `--add-imports` | No | Pre-populate each notebook with import statements matching the `--extras` groups. Has no effect without `--extras`. |
| `-v`, `--verbose` | No | Show detailed output for each step: template and destination paths, notebook filenames, dependency list, GitHub username, repo name, and remote URL. Overrides the `[defaults] verbose` config setting. |
| `--private` | No | Create the GitHub repo as private instead of public. Overrides the `[defaults] private` config setting. |
| `--dry-run` | No | Print a summary of what would be created (repo name, directory, notebooks, dependencies) without making any changes. No filesystem, Git, or GitHub API calls are made. |
| `--version` | No | Show the version number, PyPI URL, author, and email, then exit. |

#### Date validation (`-d`)

The `-d` / `--date` flag now performs strict validation:

- The value must match `YYYY-MM` format exactly.
- The month must be a real month (01 through 12). Values like `2026-13` or
  `2026-00` are rejected.
- The year cannot be more than 2 years ahead of the current year. For example,
  if the current year is 2026, `2029-01` is rejected with the message:
  `date '2029-01' is too far in the future (max 2028)`.

#### Weekend skipping

When creating multi-session courses, you can skip weekend days so that
notebook dates only fall on business days. There are two modes:

- **Standard** (`--skip-weekends`): skips Saturday and Sunday.
- **Israeli** (`--skip-israeli-weekends`): skips Friday and Saturday
  (the Israeli weekend).

The two flags are mutually exclusive -- you cannot use both at the same time.

You can also set a default in your config file:

```toml
[defaults]
weekend = "standard"
```

or:

```toml
[defaults]
weekend = "israeli"
```

CLI flags always override the config file setting.

**How it works with daily frequency:** skip days are simply not counted. If
you request 5 daily sessions starting on a Thursday with `--skip-weekends`,
the dates will be Thu, Fri, Mon, Tue, Wed (skipping Sat and Sun).

**How it works with weekly frequency:** if a 7-day jump lands on a skip day,
the date is advanced to the next non-skip day.

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

##### Group references

Entries in a custom group can be package names **or** references to other
groups (built-in or custom). Referenced groups are recursively expanded into
their packages:

```toml
[extras]
reuven = ["python", "data", "plotly"]
```

Using `--extras reuven` (or setting `extras_group = "reuven"` in `[defaults]`)
installs everything from the `python` group, everything from the `data` group,
plus `plotly` as a standalone package. Circular references are detected and
rejected with a clear error.

#### What it does

1. **Auto-generates a repo name** from the client, topic, and date:
   `{client}-{topic}-{YYYY-MM}`. The same name is used for the local
   directory and the GitHub repository.

2. **Copies the bundled course template** into a new directory in the current
   working directory. The template includes a `.gitignore` file with Python
   defaults (ignoring `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `build/`,
   `.ipynb_checkpoints/`, and common IDE files).

3. **Copies additional files** into the course directory, if any are
   configured via `[paths] additional_files` in your config file. Directories
   are copied recursively; files are copied directly.

4. **Creates notebook file(s)** in the new directory. Each notebook is named
   `{client}-{topic}-{YYYY-MM-DD}.ipynb` (or `.py` for Marimo), where
   YYYY-MM-DD is the session date. By default a single notebook is created for
   today (or for the date given by `--first-notebook-date`). With `-n`,
   multiple notebooks are created -- one per session, with dates advancing
   daily or weekly. Weekend days can be skipped with `--skip-weekends` or
   `--skip-israeli-weekends`.

5. **Generates a `pyproject.toml`** in the new directory with the repo name,
   a dependency on either `jupyter` or `marimo`, `gitautopush`, and any
   additional packages from `--extras` groups.

6. **Creates a GitHub repository** (public by default, or private with
   `--private`) using the GitHub API and configures the local `.git/config`
   with the correct SSH remote URL, using the authenticated user's GitHub
   username.

7. **Makes an initial commit and pushes** to GitHub, so the repo is ready for
   `gitautopush` immediately.

8. **Runs `uv sync`** in the course directory to install all dependencies, so
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
  .gitignore         # Python defaults (pycache, venv, dist, etc.)
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

With a custom first notebook date:

```
setup-course -c Acme -t python-intro -n 5 --first-notebook-date 2026-04-01
```

Creates 5 notebooks starting from April 1, 2026:
`Acme-python-intro-2026-04-01.ipynb` through
`Acme-python-intro-2026-04-05.ipynb`.

Skipping standard weekends:

```
setup-course -c Acme -t python-intro -n 5 --first-notebook-date 2026-04-02 --skip-weekends
```

April 2, 2026 is a Thursday. With `--skip-weekends`, the 5 sessions land on:
Thu Apr 2, Fri Apr 3, Mon Apr 6, Tue Apr 7, Wed Apr 8 (skipping Sat and Sun).

Skipping Israeli weekends:

```
setup-course -c Acme -t python-intro -n 5 --first-notebook-date 2026-04-05 --skip-israeli-weekends
```

April 5, 2026 is a Sunday. With `--skip-israeli-weekends`, the 5 sessions
land on: Sun Apr 5, Mon Apr 6, Tue Apr 7, Wed Apr 8, Thu Apr 9 (skipping
Fri and Sat).

With dependency groups:

```
setup-course -c Acme -t pandas --extras python data
```

Creates the course with ipython, numpy, pandas, xlrd, openpyxl, and pyarrow
added to the `pyproject.toml` dependencies alongside jupyter and gitautopush.

With pre-populated imports:

```
setup-course -c Acme -t pandas --extras python data --add-imports
```

Same as above, but each notebook starts with a code cell containing:
`import numpy as np`, `import pandas as pd`.

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

Check installed version:

```
setup-course --version
```

Prints the version number, PyPI URL, author name (Reuven Lerner), and email.

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

### `retire-course` -- Archive a finished course

#### Synopsis

```
retire-course DIRNAME [DIRNAME ...] [--keep-public] [--version]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `DIRNAME...` | Yes | One or more paths to course directories to retire. |

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--keep-public` | No | Archive the course without making the GitHub repo private. Useful for courses (e.g., O'Reilly) where the repo should remain publicly accessible. |
| `--version` | No | Show the version number, PyPI URL, author, and email, then exit. |

#### What it does

For each directory:

1. **Reads the Git remote URL** from the course directory's `.git/config`.
2. **Makes the GitHub repository private** via the GitHub API (unless
   `--keep-public` is passed, in which case the repo stays public).
3. **Determines the archive destination** as `{archive_path}/{current_year}/`,
   where `archive_path` is the value from your config file and `current_year`
   is the four-digit year (e.g., `2026`).
4. **Checks if the year subdirectory exists.** If the year subdirectory
   (e.g., `2026/`) does not exist, `retire-course` prompts you to create it:

   ```
   Archive directory /Users/reuven/Courses/Archive/2026 does not exist. Create it? [y/N]
   ```

   Answer `y` to create it automatically, or `n` (or press Enter) to abort
   the retirement of that directory.

5. **Moves the local directory** into the year subdirectory.
6. **Prints a retirement summary** including:
   - Number of notebooks (`.ipynb` and/or marimo `.py`)
   - Date range extracted from notebook filenames
   - Dependencies from the course `pyproject.toml`
   - Archive location (full path)
   - GitHub repo URL (marked "now private" or "still public" depending on `--keep-public`)

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

Keep the repo public (e.g., for O'Reilly courses):

```
retire-course --keep-public ./OReilly-python-2026-03
```

This archives the directory but leaves the GitHub repo publicly accessible.

#### Requirements

- The course directory must be a Git repo with an SSH remote URL in the format
  `git@github.com:username/reponame.git`.
- Your GitHub token must have the `repo` scope (and `delete_repo` if needed).
- The archive directory (`[paths] archive`) must already exist. The year
  subdirectory (e.g., `2026/`) will be created automatically if you confirm
  the prompt.

---

### `unretire-course` -- Restore a retired course

#### Synopsis

```
unretire-course DIRNAME [--version]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `DIRNAME` | Yes | Path to the retired course directory (typically inside your archive). |

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--version` | No | Show the version number, PyPI URL, author, and email, then exit. |

#### What it does

1. **Reads the Git remote URL** from the course directory's `.git/config`.
2. **Makes the GitHub repository public** again via the GitHub API.
3. **Moves the course directory** from its current location (typically the
   archive) into the current working directory, preserving the directory name.

This is the inverse of `retire-course`: it restores a course from the archive
so you can resume teaching or sharing it.

#### Examples

Unretire a course from the archive:

```
unretire-course /Users/reuven/Courses/Archive/2026/Acme-python-intro-2026-03
```

This moves the directory to `./Acme-python-intro-2026-03` in the current
working directory and makes the GitHub repo public.

#### Error handling

- If a directory with the same name already exists in the current working
  directory, the command fails with:
  `Destination already exists: /path/to/Acme-python-intro-2026-03`
- If the Git remote URL cannot be read or the GitHub API call fails, the
  command prints an error and exits with code 1.

---

### `archive-course` -- Create a zip archive

#### Synopsis

```
archive-course DIRNAME [--output PATH] [--no-html] [--version]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `DIRNAME` | Yes | Path to the course directory to archive. |

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--output`, `-o` | No | Custom output path for the zip file. Defaults to `{dirname}.zip` in the current working directory. |
| `--no-html` | No | Skip HTML export of Jupyter notebooks. By default, each `.ipynb` file is exported to HTML via `nbconvert` and both the `.ipynb` and `.html` are included in the zip. |
| `--version` | No | Show the version number, PyPI URL, author, and email, then exit. |

#### What it does

1. **Finds all Jupyter notebooks** (`.ipynb` files) in the course directory
   (recursively).
2. **Exports each notebook to HTML** using `uv run jupyter nbconvert --to html`.
   This step is skipped if `--no-html` is passed or if no notebooks are found.
3. **Creates a zip archive** containing all files in the course directory
   (including the generated `.html` files). The archive preserves the directory
   structure, with the course directory as the top-level folder inside the zip.
4. **Prints a summary** showing:
   - Archive path and file count
   - Archive size in bytes
   - List of notebooks and their corresponding HTML exports

#### Examples

Archive a course with HTML exports (default):

```
archive-course ./Acme-python-intro-2026-03
```

Creates `Acme-python-intro-2026-03.zip` containing all course files plus HTML
versions of every notebook.

Archive to a custom path:

```
archive-course ./Acme-python-intro-2026-03 -o /tmp/acme-course.zip
```

Skip HTML export:

```
archive-course ./Acme-python-intro-2026-03 --no-html
```

Creates the zip with only the original `.ipynb` files (no HTML conversion).

---

### `setup-course-config` -- Generate a config file

#### Synopsis

```
setup-course-config [--force] [--version]
```

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--force` | No | Overwrite an existing config file. Without this flag, the command will refuse to overwrite. |
| `--version` | No | Show the version number, PyPI URL, author, and email, then exit. |

#### What it does

Writes a commented template to your platform's config directory (see
[Configuration](#configuration) above for exact paths). Creates the parent
directories if they don't exist. The `--help` output displays the full path
to the config file for your platform.

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
# Edit the generated config.toml with your token, archive path, etc.

# Before each course
setup-course -c Acme -t python-intro --extras python data

# After the course is over — archive a zip for your records
archive-course ./Acme-python-intro-2026-03

# Retire the course (makes GitHub repo private, moves to archive)
retire-course ./Acme-python-intro-2026-03

# Need to bring a course back from the archive?
unretire-course /Users/reuven/Courses/Archive/2026/Acme-python-intro-2026-03
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
| `invalid date 'YYYY-MM': expected YYYY-MM with a valid month` | The `-d` value is not in `YYYY-MM` format, or the month is not between 01 and 12. Use a valid year-month like `2026-03`. |
| `date 'YYYY-MM' is too far in the future (max YYYY)` | The year in `-d` is more than 2 years ahead of the current year. Use a closer date. |
| `invalid --first-notebook-date format: '...' (expected YYYY-MM-DD)` | The `--first-notebook-date` value is not a valid ISO date. Use the exact format `YYYY-MM-DD`, e.g. `2026-04-01`. |
| `Invalid weekend value` | The `[defaults] weekend` config value must be `"standard"` or `"israeli"`. |
| `Archive directory ... does not exist. Create it? [y/N]` | The year subdirectory under your archive path does not exist yet. Answer `y` to create it, or create it manually first. |
| `Aborted: archive directory ... not created` | You answered `n` (or pressed Enter) when prompted to create the archive year subdirectory. Create it manually or answer `y` next time. |
| `Additional file not found: ...` | A path listed in `[paths] additional_files` does not exist. Check the path and fix it in your config file. |
| `Destination already exists: ...` | When running `unretire-course`, a directory with the same name already exists in the current working directory. Remove or rename it first. |
| GitHub API 401 error | Your token is invalid or expired. Generate a new one. |
| GitHub API 403 error | Your token doesn't have the required scopes (`repo`, `delete_repo`). |
| `Permission denied` on SSH push | Make sure your SSH key is added to your GitHub account and `ssh -T git@github.com` works. |
