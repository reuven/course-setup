# course-setup

[![CI](https://github.com/reuven/course-setup/actions/workflows/ci.yml/badge.svg)](https://github.com/reuven/course-setup/actions/workflows/ci.yml)

CLI tools for setting up and retiring GitHub-backed course repositories.

## Installation

Install as a [uv tool](https://docs.astral.sh/uv/concepts/tools/) (recommended):

```bash
uv tool install course-setup
```

This makes `setup-course`, `retire-course`, `unretire-course`,
`archive-course`, `list-courses`, and `setup-course-config` available on your
PATH. All six commands support `--version` and `--help`, which display the
version number, PyPI URL, author name (Reuven Lerner), and email. To upgrade:

```bash
uv tool upgrade course-setup
```

You can also install with pip (`pip install course-setup`).

## Configuration

Generate a starter config file:

```bash
setup-course-config
```

This creates a `config.toml` file in your platform's config directory
(e.g., `~/Library/Application Support/course-setup/` on macOS,
`~/.config/course-setup/` on Linux, `%APPDATA%\course-setup\` on Windows).
Open it and fill in your settings:

```toml
[github]
token = "ghp_YOUR_TOKEN_HERE"

[paths]
archive = "/path/to/your/archive"
# readme_source = "/path/to/custom/README.md"   # or a URL

[defaults]
notebook_type = "jupyter"   # or "marimo"
```

| Setting | Required | Description |
|---------|----------|-------------|
| `[github] token` | Yes | GitHub personal access token. Alternatively, set the `GITHUB_TOKEN` environment variable. |
| `[paths] archive` | Yes | Directory where retired courses are archived. |
| `[paths] readme_source` | No | Local path or URL to a custom README for new courses. Omit to use the bundled default. |
| `[paths] additional_files` | No | List of file/directory paths to copy into every new course (e.g. data files, exercise notebooks). |
| `[paths] course_dirs` | No | List of directories that `list-courses` scans for active courses (e.g. `["~/Courses/Current"]`). `~` is expanded. |
| `[defaults] notebook_type` | No | `"jupyter"` (default) or `"marimo"`. |
| `[defaults] verbose` | No | `true` or `false` (default). Sets the default verbosity for `setup-course`. |
| `[defaults] private` | No | `true` or `false` (default). When `true`, `setup-course` creates private GitHub repos by default. |
| `[defaults] extras_group` | No | Default dependency group when `--extras` is not passed (e.g. `"python"`). |
| `[defaults] weekend` | No | `"standard"` (skip Sat/Sun) or `"israeli"` (skip Fri/Sat). Default for `--skip-weekends`/`--skip-israeli-weekends`. |

To regenerate the config file, use `setup-course-config --force`.

## Usage

### `setup-course` — Create a new course repo

```bash
setup-course -c Acme -t python-intro
```

| Flag | Description |
|------|-------------|
| `-c`, `--client` | Client name (required) |
| `-t`, `--topic` | Course topic (required) |
| `-d`, `--date` | YYYY-MM override (defaults to current month). Validated: must be a real month, not more than 2 years ahead. |
| `-n`, `--num-sessions` | Number of sessions (creates one notebook per session) |
| `--freq` | Session frequency: `daily` or `weekly` (requires `-n`, defaults to `daily`) |
| `--first-notebook-date` | Start date for notebook files (YYYY-MM-DD); defaults to today |
| `--skip-weekends` | Skip Saturdays and Sundays when scheduling notebooks |
| `--skip-israeli-weekends` | Skip Fridays and Saturdays when scheduling notebooks |
| `--notebook-type` | `jupyter` or `marimo` (overrides config default) |
| `--extras` | Dependency groups to add to the course `pyproject.toml` (see below) |
| `--add-imports` | Pre-populate notebooks with import statements from `--extras` groups |
| `-v`, `--verbose` | Show detailed output (paths, filenames, dependencies) |
| `--private` | Create the GitHub repo as private instead of public (overrides config default) |
| `--dry-run` | Preview what would be created without making any changes |

#### Dependency groups

| Group | Packages |
|-------|----------|
| `python` | ipython |
| `data` | numpy, pandas, xlrd, openpyxl, pyarrow |
| `viz` | matplotlib, seaborn, plotly |
| `geo` | geopandas, folium, shapely |
| `db` | duckdb, sqlalchemy |
| `ml` | scikit-learn |

You can also define custom groups in your `config.toml` under `[extras]`.
Entries can be package names or references to other groups (built-in or custom):

```toml
[extras]
finance = ["yfinance", "pandas-datareader"]
reuven = ["python", "data", "plotly"]   # expands python & data groups + plotly
```

Example — a Pandas course with Python extras and data/viz packages:

```bash
setup-course -c Acme -t pandas --extras python data
```

This will:

1. Create a directory and GitHub repo named `{client}-{topic}-{YYYY-MM}` (public by default; use `--private` for private)
2. Create a notebook per session, named `{client}-{topic}-{YYYY-MM-DD}`
   (`.ipynb` for Jupyter, `.py` for Marimo)
3. Generate a `pyproject.toml` with the notebook dependency and `gitautopush`
4. Include a `.gitignore` for Python, virtual environments, and IDE files
5. Configure the local `.git/config` with the GitHub SSH remote
6. Make an initial commit and push to GitHub
7. Run `uv sync` to install all dependencies

By default, a single notebook is created for today's date. Use `-n` to
create multiple notebooks for multi-day or multi-week courses:

```bash
setup-course -c Acme -t python-intro -n 5              # 5 daily sessions
setup-course -c Acme -t python-intro -n 5 --freq weekly # 5 weekly sessions
```

### `retire-course` — Archive a course repo

```bash
retire-course ./Acme-python-intro-2026-03
```

| Argument / Flag | Description |
|-----------------|-------------|
| `DIRNAME...` | One or more course directories to retire |
| `--keep-public` | Archive without making the GitHub repo private |
| `--dry-run` | Preview the retirement without making any changes |

This will (for each directory):

1. Make the GitHub repo private (unless `--keep-public` is passed)
2. Move the local directory to your configured archive path under the current year
   (prompts for confirmation if the year directory doesn't exist)
3. Print a retirement summary showing: notebook count, date range, dependencies,
   archive location, and GitHub URL

With `--dry-run`, none of that happens: the GitHub repo is not touched, the
archive directory is not created, and the course directory is not moved.
Instead, `retire-course` prints a `[DRY RUN]` banner followed by the same
retirement summary the real run would show, so no GitHub token or network
access is required. `--dry-run` applies to every directory passed on the
command line.

You can retire multiple courses at once:

```bash
retire-course ./Acme-2026-03 ./Beta-2026-03 ./Gamma-2026-02
```

If any directory fails, the rest are still processed and errors are reported at the end.

> **Tip:** run `retire-course` from the *parent* of the course directory, not
> from inside it. If you're already inside, the command detects it and tells
> you to `cd ..` rather than failing with a confusing error.

### `archive-course` — Create a zip archive of a course

```bash
archive-course ./Acme-python-intro-2026-03
```

| Flag | Description |
|------|-------------|
| `--output`, `-o` | Custom output zip path (defaults to `{dirname}.zip`) |
| `--no-html` | Skip HTML export of Jupyter notebooks |
| `--no-pdf` | Skip PDF export of Jupyter notebooks |

This archives **all files** in the course directory (`.py`, `.csv`, `.toml`,
notebooks, etc.), excluding `.git`, `.venv`, `__pycache__`, and
`.ipynb_checkpoints` directories. For Jupyter notebooks, each `.ipynb` is also
exported to HTML and to PDF, and both are included alongside the original;
use `--no-html` / `--no-pdf` to skip either export. PDF export is **on by
default**, via `nbconvert --to webpdf` (headless Chromium — no LaTeX
installation required). The first time you export to PDF, you may need to
run `uv run playwright install chromium` inside the course directory to
download the Chromium binary. If the PDF engine isn't available, `archive-course`
prints a warning and skips PDF for that notebook rather than failing — the
rest of the archive is still produced. After creating the archive, a summary
is printed listing the archive path, file count, size, notebooks (shown as
`notebook.ipynb + notebook.html + notebook.pdf`), export counts, and all
other included files.

### `list-courses` — List active and archived courses

```bash
list-courses
```

A read-only command: nothing is modified, and no GitHub token or network
access is needed. It lists:

- **Active courses**: for each scan directory, its immediate subdirectories
  that qualify as a *course* — a directory containing both a `.git`
  subdirectory and at least one notebook (`.ipynb`, or a marimo `.py`).
- **Archived courses**: courses found under `{archive}/{year}/{course}`,
  grouped by year, using your configured `[paths] archive` directory.

Each course is shown as:

```
name — N notebooks (first-date → last-date)
```

with dates parsed from notebook filenames (`n/a` if none are found). If there
are no active or archived courses, it prints `No active courses found` /
`No archived courses found` respectively.

| Argument | Description |
|----------|-------------|
| `DIR...` | Optional directories to scan (overrides `course_dirs` from config) |

Directories to scan are resolved in this order:

1. Positional directories passed on the command line (`list-courses DIR ...`)
2. Otherwise, `[paths] course_dirs` from your config file
3. Otherwise, the current directory

Like the other commands, `list-courses --version` prints the version number,
PyPI URL, author name, and email.

### `unretire-course` — Restore a retired course

```bash
unretire-course /path/to/archive/2026/Acme-python-intro-2026-03
```

This will:

1. Make the GitHub repo public again
2. Move the directory from the archive back to your current working directory

### Live teaching with `gitautopush`

In a separate terminal, run `uv run gitautopush .` from inside the course
directory. This watches for notebook changes and automatically pushes them to
GitHub, so students can follow along in real time by viewing the public repo.

## Development

```bash
git clone https://github.com/reuven/course-setup.git
cd course-setup
uv sync --dev
```

Run tests, format, and lint:

```bash
uv run pytest
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run mypy --strict src/
```

## License

MIT — see [LICENSE](LICENSE) for details.
