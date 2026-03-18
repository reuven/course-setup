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
| `[defaults] notebook_type` | No | `"jupyter"` (default) or `"marimo"`. Controls which kind of notebook file `setup-course` creates. |

*You can omit the token from the config file and set the `GITHUB_TOKEN`
environment variable instead. If both are set, the config file value takes
precedence.

---

## Commands

### `setup-course` — Create a new course

#### Synopsis

```
setup-course -d DATE -c CLIENT -r REPO [-n NAME] [--notebook-type TYPE]
```

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `-d`, `--date` | Yes | The course date, used in the directory and notebook names. Use any format you like (e.g., `2026-03-18`). |
| `-c`, `--client` | Yes | The client or company name. |
| `-r`, `--repo` | Yes | The name for the new GitHub repository. |
| `-n`, `--name` | No | An optional suffix appended to the directory and notebook names (e.g., `advanced`, `day1`). |
| `--notebook-type` | No | `jupyter` or `marimo`. Overrides the default from your config file. |

#### What it does

1. **Copies the bundled course template** into a new directory in the current
   working directory. The directory is named `{client}-{date}` — or
   `{client}-{date}-{name}` if you provide the `-n` flag.

2. **Creates a notebook file** in the new directory:
   - Jupyter: renames the template's `Course notebook.ipynb` to
     `{client} - {date}.ipynb` (or `{client} - {date}-{name}.ipynb`).
   - Marimo: deletes the `.ipynb` and writes a new `.py` file with a minimal
     Marimo app scaffold.

3. **Generates a `pyproject.toml`** in the new directory with the repo name,
   a dependency on either `jupyter` or `marimo`, and `gitautopush`.

4. **Creates a public GitHub repository** using the GitHub API and configures
   the local `.git/config` with the correct SSH remote URL, using the
   authenticated user's GitHub username.

#### Example

```
setup-course -d 2026-03-18 -c Acme -r acme-python-2026
```

This creates:

```
Acme-2026-03-18/
  .git/
    config           # remote set to git@github.com:youruser/acme-python-2026.git
  Acme - 2026-03-18.ipynb
  pyproject.toml
  README.md
```

With the `-n` flag:

```
setup-course -d 2026-03-18 -c Acme -r acme-python-advanced -n advanced
```

Creates the directory `Acme-2026-03-18-advanced/` with notebook
`Acme - 2026-03-18-advanced.ipynb`.

With Marimo:

```
setup-course -d 2026-03-18 -c Acme -r acme-python-2026 --notebook-type marimo
```

Creates `Acme - 2026-03-18.py` instead of the `.ipynb`.

---

### `retire-course` — Archive a finished course

#### Synopsis

```
retire-course -d DIRNAME
```

#### Options

| Option | Required | Description |
|--------|----------|-------------|
| `-d`, `--dirname` | Yes | Path to the course directory to retire. |

#### What it does

1. **Reads the Git remote URL** from the course directory's `.git/config`.
2. **Makes the GitHub repository private** via the GitHub API.
3. **Moves the local directory** into `{archive_path}/{current_year}/`, where
   `archive_path` is the value from your config file and `current_year` is the
   four-digit year (e.g., `2026`).

#### Example

```
retire-course -d ./Acme-2026-03-18
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
setup-course -d 2026-03-18 -c Acme -r acme-python-2026

# After the course is over
retire-course -d ./Acme-2026-03-18
```

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
