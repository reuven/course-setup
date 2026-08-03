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
| `[paths] course_dirs` | No | List of directories that `list-courses` scans for active courses (e.g. `["~/Courses/Current"]`). `~` is expanded. Overridden by `--dir` on the `list-courses` command line. |
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
retirement summary the real run would show. It reads your config file but makes
no GitHub API calls, so a dry run touches nothing on the network. `--dry-run`
applies to every directory passed on the command line.

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
installation required). New Jupyter courses (3.3.1+) include the
`nbconvert[webpdf]` dependency out of the box, and `archive-course`
auto-installs the Chromium browser itself the first time it's needed — a
one-time, per-machine download, with a status line printed while it installs.
You no longer run any `playwright` command by hand — and if that automatic
install ever fails (e.g. offline), `archive-course` prints the one-time
`uv run playwright install chromium` command for you to run yourself, and
still completes the archive with HTML. For a course created before 3.3.1,
run `uv add "nbconvert[webpdf]"` in it once; `archive-course` still handles
Chromium from there. If PDF export still can't run, `archive-course` prints
a concise hint (not a traceback) and skips PDF — the rest of the archive
(HTML exports, zip) is still produced. After
creating the archive, a summary is printed listing the archive path, file
count, size, notebooks (shown as `notebook.ipynb + notebook.html +
notebook.pdf`), export counts, and all other included files.

### `list-courses` — List active and archived courses

```bash
list-courses
```

A read-only command: nothing is modified, and no GitHub API calls are made (it
reads your config file, and each course's local `git` remote, but does not use
the network).

> **Breaking change (3.2.0):** the positional argument used to be a
> scan-directory override (`list-courses ~/Other`). It is now a **name
> filter** instead. To scan a different directory, use the repeatable
> `--dir PATH` flag: `list-courses --dir ~/Other`.

By default, `list-courses` prints the full list of **active courses** — a
directory qualifies as a course if it has a `.git` subdirectory and at least
one notebook (`.ipynb`, or a marimo `.py`) — followed by a one-line summary of
the **archived courses** found under your configured `[paths] archive`
directory (an archived course is any non-hidden, non-junk directory under a
4-digit-year folder that contains at least one notebook):

```
Active courses:
  Acme-python-intro-2026-03 — 5 notebooks (2026-03-17 → 2026-03-21)
    https://github.com/acme/python-intro-2026-03
  Beta-pandas-2026-02 — 3 notebooks (2026-02-02 → 2026-02-16)
    https://github.com/beta/pandas-2026-02

Archived: 412 courses across 2018–2026 — use --archived to list them.
```

Each course line is shown as `name — N notebooks (first-date → last-date)`,
with dates parsed from notebook filenames (`n/a` if none are found). By
default, an indented line below each *listed* course (active courses, and
archived courses in the expanded `--archived`/`--year` views) shows its GitHub
URL, read from the course's local `git` `origin` remote — no network call. A
course with no usable GitHub remote shows `(no GitHub remote)` instead. Pass
`--no-urls` to hide these lines. URLs are not shown in the one-line archive
summary or with `--count`.

| Argument / Option | Description |
|----------|-------------|
| `NAME...` | Filter courses by case-insensitive name substring. Multiple names match as OR. Narrows whatever is shown; does not by itself expand the archive. |
| `--dir PATH` | Directory to scan for active courses (repeatable; replaces `course_dirs` from config for this run) |
| `--active` | Show only the active-courses section |
| `--archived` | Show only the archived-courses section, expanded and grouped by year |
| `--year YYYY[-YYYY]` | Restrict archived courses to a year or an inclusive `YYYY-YYYY` range (repeatable; singles and ranges mix freely); implies `--archived` unless `--active` is also given, in which case `--year` is ignored. A reversed range (e.g. `2022-2020`) is auto-swapped, printing `Note: swapped reversed year range 2022-2020 → 2020-2022` to stderr. |
| `--count` | Print counts instead of course lines, honoring all other filters |
| `--no-urls` | Hide the per-course GitHub URL line shown by default under each listed course |
| `--version` | Show the version number, PyPI URL, author name, and email |

Directories to scan for active courses are resolved in this order:

1. `--dir PATH` values passed on the command line (repeatable)
2. Otherwise, `[paths] course_dirs` from your config file
3. Otherwise, the current directory

#### Examples

| Command | Result |
|---|---|
| `list-courses` | active courses in full + `Archived: N courses across 2018–2026 — use --archived …` |
| `list-courses --archived` | archive only, expanded and grouped by year |
| `list-courses --active` | active courses only |
| `list-courses cisco` | active courses matching "cisco" + a name-filtered archive summary line |
| `list-courses cisco --archived` | archived courses matching "cisco" (all years, expanded) |
| `list-courses --year 2024` | archive for 2024 only (active section suppressed) |
| `list-courses --year 2024 --year 2025` | archive for 2024 and 2025 only |
| `list-courses --year 2020-2022` | archive for 2020 through 2022 only (inclusive range) |
| `list-courses --year 2019 --year 2021-2023` | archive for 2019, 2021, 2022, 2023 (singles and ranges mix) |
| `list-courses cisco --year 2024` | archived courses matching "cisco" from 2024 only |
| `list-courses --active --year 2024` | active only (`--year` is ignored for active) |
| `list-courses --count` | `Active courses: 3` + `Archived courses: 412` + per-year counts |
| `list-courses cisco --count` | counts of active + archived courses matching "cisco" |
| `list-courses --dir ~/Other` | scan `~/Other` for active courses instead of config `course_dirs` |
| `list-courses --no-urls` | active courses in full, without the per-course GitHub URL lines |

If there are no matching active or archived courses, it prints an empty-state
line (e.g. `No active courses found`, or `No active courses match: cisco` when
a name filter excludes everything).

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
