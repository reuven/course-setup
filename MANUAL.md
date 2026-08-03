# course-setup: Instruction Manual

## Overview

`course-setup` is a command-line toolkit for managing GitHub-backed course
repositories. It provides six commands:

- **`setup-course`** — Create a new course directory with a notebook, a
  `pyproject.toml`, a Git repo, and a matching GitHub repo (public or private).
- **`retire-course`** — Archive a finished course by making its GitHub repo
  private and moving the local directory into a dated archive folder. Supports
  `--dry-run` to preview the retirement without changing anything.
- **`unretire-course`** — Restore a previously retired course by making its
  GitHub repo public again and moving the directory back to your working
  directory.
- **`archive-course`** — Create a zip archive of a course directory, exporting
  Jupyter notebooks to HTML and PDF by default.
- **`list-courses`** — List active and archived courses. Read-only; makes no
  changes and no GitHub API calls (it reads your config file but does not use
  the network).
- **`setup-course-config`** — Generate a starter configuration file.

All six commands support `--version` and `--help`. Both display the version
number, PyPI URL, author name (Reuven Lerner), and email address:

```
setup-course --version
retire-course --version
unretire-course --version
archive-course --version
list-courses --version
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
   repositories).
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

This installs it in an isolated environment and makes the six commands
available globally on your PATH:

- `setup-course`
- `retire-course`
- `unretire-course`
- `archive-course`
- `list-courses`
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

### Continuous integration

Every push and pull request runs these checks on GitHub Actions as three
parallel jobs (`.github/workflows/ci.yml`):

```
uv run ruff check .          # lint        (Linux)
uv run ruff format --check . # formatting  (Linux; verify only, no rewrite)
uv run mypy src tests        # type check  (Linux, strict)
uv run pytest                # tests       (Linux + macOS + Windows, 3.13 & 3.14)
```

Lint and type-check results are OS-independent, so they run once on Linux;
the tests run across all three operating systems and both Python versions,
since that is where filesystem and path behaviour can differ. Run the commands
locally before pushing to get the same green/red result CI will report.

Two further automations:

- **Mutation testing** (`.github/workflows/mutation.yml`) runs `mutmut` weekly
  (and on demand via the Actions "Run workflow" button) as a test-quality
  audit. It reports surviving mutants but never fails the run — review the job
  summary, and ignore string-literal mutations in output/help text.
- **Dependabot** (`.github/dependabot.yml`) opens weekly pull requests to bump
  GitHub Actions and Python (uv) dependencies; CI vets each one.

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
# Needs: repo (read/write)
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

# Optional: directories that `list-courses` scans for active courses.
# Each entry is a directory whose immediate subdirectories may be courses
# (a course = a subdir containing a .git folder and at least one notebook).
# Examples:
#   course_dirs = ["~/Courses/Current"]
#   course_dirs = ["~/Courses/Current", "~/Courses/Consulting"]
# course_dirs = []

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
| `[paths] course_dirs` | No | List of directories that `list-courses` scans for active courses (e.g. `["~/Courses/Current"]`). `~` is expanded. Overridden by `--dir` arguments on the `list-courses` command line. Defaults to the current directory if unset and no `--dir` arguments are given. |
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
retire-course DIRNAME [DIRNAME ...] [--keep-public] [--dry-run] [--version]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `DIRNAME...` | Yes | One or more paths to course directories to retire. |

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--keep-public` | No | Archive the course without making the GitHub repo private. Useful for courses (e.g., O'Reilly) where the repo should remain publicly accessible. |
| `--dry-run` | No | Preview the retirement without making any changes: the GitHub repo is not touched, the archive directory is not created, and the course directory is not moved. Prints a `[DRY RUN]` banner followed by the same retirement summary the real run would show. Your config file is read, but no GitHub API call is made, so a dry run touches nothing on the network. Applies to every directory passed on the command line. |
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

With `--dry-run`, steps 2, 4, and 5 above are skipped entirely -- no GitHub
API call is made, no directory is created, and nothing is moved. Instead,
`retire-course` prints a `[DRY RUN]` banner followed by the same retirement
summary the real run would produce, so you can preview the effect on multiple
directories without any GitHub API calls (your config file is still read, but
the network is not used).

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

Preview a retirement without changing anything:

```
retire-course --dry-run ./Acme-2026-03 ./Beta-2026-03
```

Prints a `[DRY RUN]` banner and the retirement summary for each directory;
the GitHub repos stay untouched and neither directory is moved. `--dry-run`
combines with `--keep-public` if you want to preview a public-repo retirement.

#### Requirements

- The course directory must be a Git repo with an SSH remote URL in the format
  `git@github.com:username/reponame.git`.
- Your GitHub token must have the `repo` scope.
- The archive directory (`[paths] archive`) must already exist. The year
  subdirectory (e.g., `2026/`) will be created automatically if you confirm
  the prompt.
- Run `retire-course` from the *parent* of the course directory, not from
  inside it. If you're already inside, the command stops with a clear error
  telling you to `cd ..` rather than failing deep in the git plumbing.

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
- If you run `unretire-course` while `cd`'d into the course directory itself
  (e.g., passing `.` or its bare name), the command stops up front and tells
  you to `cd ..` rather than failing with a cryptic git error.

---

### `archive-course` -- Create a zip archive

#### Synopsis

```
archive-course DIRNAME [--output PATH] [--no-html] [--no-pdf] [--version]
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
| `--no-pdf` | No | Skip PDF export of Jupyter notebooks. By default, each `.ipynb` file is also exported to PDF (see below) and included alongside the `.ipynb`/`.html` files. |
| `--version` | No | Show the version number, PyPI URL, author, and email, then exit. |

#### What it does

1. **Finds all Jupyter notebooks** (`.ipynb` files) in the course directory
   (recursively).
2. **Exports each notebook to HTML** using `uv run jupyter nbconvert --to html`.
   This step is skipped if `--no-html` is passed or if no notebooks are found.
3. **Exports each notebook to PDF** using
   `uv run jupyter nbconvert --to webpdf`, which renders the PDF with headless
   Chromium instead of requiring a LaTeX installation. This is **on by
   default**; pass `--no-pdf` to skip it, or it is skipped automatically if no
   notebooks are found. `archive-course` auto-installs the Chromium browser
   itself the first time a course needs it. See
   [PDF export requirements](#pdf-export-requirements) below for one-time
   setup and failure behavior.
4. **Creates a zip archive** containing all files in the course directory
   (including the generated `.html` and `.pdf` files), excluding `.git`,
   `.venv`, `__pycache__`, and `.ipynb_checkpoints` directories. The archive
   preserves the directory structure, with the course directory as the
   top-level folder inside the zip.
5. **Prints a summary** showing:
   - Archive path and file count
   - Archive size (displayed in KB or MB)
   - List of notebooks and their corresponding HTML/PDF exports, shown as
     `notebook.ipynb + notebook.html + notebook.pdf`
   - `HTML exports: N` and `PDF exports: N` counts
   - List of all other included files (`.py`, `.csv`, `.toml`, etc.)

#### PDF export requirements

PDF export uses `nbconvert`'s `webpdf` exporter, which drives a headless
Chromium browser instead of requiring a LaTeX toolchain. That needs two
things: the `nbconvert[webpdf]` library (which bundles Playwright) as a
course dependency, and the Chromium browser binary itself.

**New courses (3.3.1+)** are set up with `nbconvert[webpdf]` in their
`pyproject.toml` automatically, so nothing extra needs installing there.
Marimo courses don't need it, since `archive-course` only exports `.ipynb`
notebooks.

**Chromium is handled automatically too.** The first time `archive-course`
needs it in a given course environment and it isn't there yet, it installs
it for you -- a one-time, per-machine download -- and prints a short status
line while it works:

```
Chromium isn't installed yet (needed for PDF export).
Installing it once now — this may take a minute...
Chromium installed.
```

You no longer need to run `uv run playwright install chromium` by hand; the
notebook that triggered the install is retried automatically once Chromium is
ready, and later notebooks in the same run proceed normally (the install
happens at most once per `archive-course` invocation).

If that automatic install itself fails (e.g. no network), `archive-course`
falls back to printing that same command for you to run yourself:

```
Could not install Chromium automatically; skipping PDF.
  To enable it, run: uv run playwright install chromium
```

PDF export is skipped for the rest of the run, but the archive still
completes normally with HTML exports and the zip.

**Courses created before 3.3.1** don't have `nbconvert[webpdf]` as a
dependency yet. To enable PDF export on one, run this once inside the course
directory:

```
uv add "nbconvert[webpdf]"
```

That's a real, committable change to the course's own dependencies, so
`archive-course` never makes it for you. After adding it, archive the course
again and Chromium installs itself as described above.

**If PDF export still can't run** -- the library is missing and you haven't
added it yet, the Chromium auto-install itself fails (e.g. no network), or
some other export error occurs -- `archive-course` prints a concise hint
rather than a full traceback, and still completes the archive normally
(HTML exports and the zip are unaffected). For example, a missing library
prints:

```
PDF export needs the webpdf extra. In the course dir run:
  uv add "nbconvert[webpdf]"
(then archive again, or use --no-pdf to skip PDF.)
```

Use `--no-pdf` to opt out of PDF export entirely, e.g. on machines where
installing Chromium isn't practical.

#### Examples

Archive a course with HTML and PDF exports (default):

```
archive-course ./Acme-python-intro-2026-03
```

Creates `Acme-python-intro-2026-03.zip` containing all course files plus HTML
and PDF versions of every notebook.

Archive to a custom path:

```
archive-course ./Acme-python-intro-2026-03 -o /tmp/acme-course.zip
```

Skip HTML export:

```
archive-course ./Acme-python-intro-2026-03 --no-html
```

Creates the zip with all course files but skips the HTML conversion step
(PDF export still runs).

Skip PDF export:

```
archive-course ./Acme-python-intro-2026-03 --no-pdf
```

Creates the zip with all course files but skips the PDF conversion step
(HTML export still runs). Useful on machines where you'd rather not trigger
the one-time Chromium download at all, or on courses where `nbconvert[webpdf]`
hasn't been added yet.

---

### `list-courses` -- List active and archived courses

#### Breaking change (3.2.0)

In earlier versions, the positional argument to `list-courses` was a
scan-directory override (`list-courses ~/Other` scanned `~/Other` instead of
`course_dirs`). **That positional argument is now a name filter instead.**
The old scan-directory behavior moved to a new repeatable `--dir PATH` flag:

```
list-courses --dir ~/Other
```

If you have scripts or aliases that pass a directory as a bare positional
argument to `list-courses`, update them to use `--dir`.

#### Synopsis

```
list-courses [NAME ...] [--dir PATH]... [--active] [--archived]
             [--year YYYY[-YYYY]]... [--count] [--no-urls] [--version]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `NAME...` | No | Filter courses by case-insensitive name **substring** match on the course directory name. Repeatable / space-separated; multiple names match as OR (a course matches if its name contains any of them). A name filter narrows whatever section(s) are shown -- it does not by itself expand the archive to its full listing (see "Behavior composition" below). |

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--dir PATH` | No | Directory to scan for active courses (repeatable). Replaces `[paths] course_dirs` from the config file for this run -- this is the old positional-argument behavior, moved here. |
| `--active` | No | Show only the active-courses section. |
| `--archived` | No | Show only the archived-courses section, expanded and grouped by year. |
| `--year YYYY[-YYYY]` | No | Restrict archived courses to a year or an inclusive year **range** (repeatable: `--year 2024 --year 2025`, or `--year 2020-2022`; singles and ranges mix freely across repeats, e.g. `--year 2019 --year 2021-2023`). Each token must be a 4-digit year, optionally followed by `-` and another 4-digit year, or `list-courses` exits with an error (`invalid year '...'`). A **reversed** range such as `--year 2022-2020` is accepted and automatically swapped to `2020-2022`; a notice (`Note: swapped reversed year range 2022-2020 → 2020-2022`) is printed to **stderr**, one per reversed token. Focuses on the archive: passing `--year` without `--active` suppresses the active section (as if `--archived` had been passed, scoped to those years). If `--active` is also given, the active section is shown and `--year` is ignored for it (active courses aren't year-organized). |
| `--count` | No | Print counts instead of individual course lines, honoring all other filters (name, `--dir`, `--active`/`--archived`, `--year`). |
| `--no-urls` | No | Hide the per-course GitHub URL line shown by default under each listed course (see "Per-course GitHub URLs" below). |
| `--version` | No | Show the version number, PyPI URL, author, and email, then exit. |

#### What it does

`list-courses` is read-only -- it never modifies files, moves directories, or
contacts GitHub over the network. It does read each listed course's local
`git` configuration to resolve its GitHub URL (see "Per-course GitHub URLs"
below), but that is a local `git config` read, not a network call.

1. **Resolves which directories to scan for active courses** in this order:
   `--dir PATH` values passed on the command line (repeatable); otherwise
   `[paths] course_dirs` from the config file; otherwise the current
   directory.
2. **Finds active courses**: for each scan directory, its immediate
   subdirectories that qualify as a *course* -- a directory containing both a
   `.git` subdirectory and at least one notebook (`.ipynb`, or a marimo
   `.py`).
3. **Finds archived courses**: directories found under
   `{archive}/{year}/{course}`, using the `[paths] archive` directory from
   your config file. Only directories directly under the archive root whose
   name is a 4-digit year (`^\d{4}$`) are treated as year groups; everything
   else at the archive root is ignored. Within a year, a directory counts as
   an archived course if its name is not hidden (doesn't start with `.`), is
   not a known junk name (`__pycache__`, `build`, `dist`, `bin`, `include`,
   `lib`, `node_modules`), and contains at least one notebook. Unlike active
   courses, an archived course does **not** need a `.git` subdirectory
   (archived repos may have had it stripped).
4. **Expands `--year` tokens.** Each `--year` value is either a single
   4-digit year or an inclusive `YYYY-YYYY` range; ranges are flattened into
   individual years before filtering. A reversed range is swapped (see the
   `--year` option above) and a notice is printed to stderr.
5. **Applies the name filter and the expanded years**, then decides what to
   print (see "Behavior composition" below). Each course is shown as:

   ```
   name — N notebooks (first-date → last-date)
   ```

   with the date range parsed from notebook filenames (`n/a` if none match).

#### Per-course GitHub URLs

By default, an indented line beneath each **listed** course shows its GitHub
URL:

```
Active courses:
  python-intro — 3 notebooks (2026-03-01 → 2026-03-15)
    https://github.com/reuven/python-intro
```

The URL line sits 2 spaces deeper than its course line: 4 spaces for an
active course (which prints at 2 spaces), 6 spaces for an archived course
under a `  <year>:` heading (which prints at 4 spaces).

The URL is read from the course's local `git` `origin` remote --
`git config --get remote.origin.url`, run with the course directory as the
working directory. This is a local read; no network call is made, and
`list-courses` never contacts GitHub. Both the SSH form
(`git@github.com:owner/repo.git`) and the HTTPS form
(`https://github.com/owner/repo.git`) are recognized and normalized to
`https://github.com/owner/repo`.

If a course has no `.git` directory, no `origin` remote, or a remote that
isn't a GitHub URL (for example, an archived course whose `.git` was
stripped), an indented placeholder is shown instead so the layout stays
uniform:

```
  old-course — 4 notebooks (n/a)
    (no GitHub remote)
```

URL lines only appear where courses are printed individually: the active
section, and the archived section when expanded via `--archived` or
`--year`. They never appear in the one-line archive summary (the default,
un-expanded archive view) or under `--count`, since neither prints
individual course lines.

Pass **`--no-urls`** to suppress all URL and placeholder lines (matches the
existing `--no-html` / `--no-pdf` opt-out convention on `archive-course`; no
short alias).

#### Behavior composition

By default (no flags), `list-courses` prints the **active** section in full,
followed by a **one-line archive summary** instead of the full archive
listing:

```
Archived: 412 courses across 2018–2026 — use --archived to list them.
```

If there are no archived courses, this line reads `Archived: none`. If a name
filter is active, the line reflects it: `Archived: 3 courses matching
"cisco" across 2019–2024 — use --archived to list them.` (or `Archived: none
matching "cisco"`).

The rules for which section(s) are shown, and whether the archive is shown in
full ("expanded") or as the one-line summary:

| Flags | Active shown? | Archive shown? | Archive form |
|---|---|---|---|
| *(none)* | Yes, full | Yes | Summary line |
| `--active` | Yes, full | No | -- |
| `--archived` | No | Yes | Expanded, grouped by year |
| `--active --archived` | Yes, full | Yes | Expanded, grouped by year |
| `--year YYYY` | No | Yes | Expanded, scoped to that year |
| `--active --year YYYY` | Yes, full | No | -- (`--year` ignored) |
| `NAME` (positional, alone) | Yes, filtered | Yes | Summary line, name-filtered |
| `NAME --archived` / `NAME --year YYYY` | per above | Yes, filtered | Expanded, name-filtered |

A name filter never *opens* the archive by itself -- it only narrows courses
within whichever section is already being shown. This keeps a bare
`list-courses cisco` from dumping hundreds of archived matches; you must add
`--archived` or `--year` to see the matching archived courses in full.

With `--count`, every row above prints counts instead of course lines:

```
Active courses: 3
Archived courses: 412
  2018: 4
  2020: 44
  ...
```

Empty-state messages: `No active courses found` (no active courses at all),
`No active courses match: <names>` (name filter excluded everything active),
`No archived courses found` (expanded archive view via `--archived` with no
name/year filters, nothing archived at all), and `No archived courses match
your filters` (expanded archive view, name/year filters excluded everything).
In the *default* view with nothing archived, the summary line reads
`Archived: none` instead (see above).

#### Examples

List courses using the configured `course_dirs` (default view):

```
list-courses
```

```
Active courses:
  Acme-python-intro-2026-03 — 5 notebooks (2026-03-17 → 2026-03-21)
    https://github.com/acme/python-intro-2026-03
  Beta-pandas-2026-02 — 3 notebooks (2026-02-02 → 2026-02-16)
    https://github.com/beta/pandas-2026-02

Archived: 412 courses across 2018–2026 — use --archived to list them.
```

Scan one or more specific directories, overriding the config:

```
list-courses --dir ~/Courses/Current --dir ~/Courses/Consulting
```

Filter by name, and list the matching archived courses too:

```
list-courses cisco --archived
```

List archived courses from specific years only, mixing a single year with a
range:

```
list-courses --year 2019 --year 2021-2023
```

A reversed range is accepted and swapped, with a notice on stderr:

```
list-courses --year 2022-2020
```

```
Note: swapped reversed year range 2022-2020 → 2020-2022
Archived courses:
  2020:
    ...
  2021:
    ...
  2022:
    ...
```

(The `Note:` line goes to stderr, so it's absent from redirected stdout.)

Print counts instead of course lines:

```
list-courses --count
```

Hide the per-course GitHub URL lines:

```
list-courses --no-urls
```

The table below gives the result of each documented invocation:

| Command | Result |
|---|---|
| `list-courses` | active full + `Archived: N courses across 2018–2026 — use --archived …` |
| `list-courses --archived` | archive only, expanded, grouped by year |
| `list-courses --active` | active only |
| `list-courses cisco` | active courses matching "cisco" + a name-filtered archive summary line |
| `list-courses cisco --archived` | archive courses matching "cisco" (all years, expanded) |
| `list-courses --year 2024` | archive for 2024 only (active section suppressed) |
| `list-courses --year 2024 --year 2025` | archive for 2024 and 2025 only |
| `list-courses --year 2020-2022` | archive for 2020 through 2022 only (inclusive range) |
| `list-courses --year 2019 --year 2021-2023` | archive for 2019, 2021, 2022, 2023 (singles and ranges mix) |
| `list-courses --year 2022-2020` | archive for 2020–2022 (reversed range swapped); `Note: swapped reversed year range 2022-2020 → 2020-2022` printed to stderr |
| `list-courses cisco --year 2024` | archive courses matching "cisco" from 2024 only |
| `list-courses --active --year 2024` | active only (`--year` ignored for active) |
| `list-courses --count` | `Active courses: 3` + `Archived courses: 412` + per-year counts (no URL lines) |
| `list-courses cisco --count` | counts of active + archive courses matching "cisco" |
| `list-courses --dir ~/Other` | scan `~/Other` for active courses instead of config `course_dirs` |
| `list-courses --no-urls` | active full + archive summary, without per-course GitHub URL lines |

#### Requirements

- `[paths] course_dirs` is optional in the config file; without it (and
  without `--dir` arguments) `list-courses` scans only the current directory.
- `[paths] archive` must be set for archived courses to be found (the same
  setting used by `retire-course` and `unretire-course`).

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
| `You appear to be inside '...'. Move up one directory (cd ..) and run the command again.` | You ran `retire-course` or `unretire-course` while `cd`'d into the course directory itself. `cd ..` and re-run the command, passing the directory name from outside. |
| GitHub API 401 error | Your token is invalid or expired. Generate a new one. |
| GitHub API 403 error | Your token doesn't have the required `repo` scope. |
| `Permission denied` on SSH push | Make sure your SSH key is added to your GitHub account and `ssh -T git@github.com` works. |
