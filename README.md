# course-setup

CLI tools for setting up and retiring GitHub-backed course repositories.

## Installation

Because `course-setup` is a standalone CLI tool (not a library you import into
projects), the recommended way to install it is as a
[uv tool](https://docs.astral.sh/uv/concepts/tools/):

```bash
uv tool install course-setup
```

This installs it in an isolated environment and makes `setup-course`,
`retire-course`, and `setup-course-config` available globally on your PATH.

To upgrade later:

```bash
uv tool upgrade course-setup
```

Alternatively, you can install with pip:

```bash
pip install course-setup
```

## Configuration

Run the config generator to create a starter config file:

```bash
setup-course-config
```

This creates `~/.config/course-setup/config.toml`:

```toml
[github]
token = "ghp_YOUR_TOKEN_HERE"

[paths]
archive = "/path/to/your/archive"
# readme_source = "/path/to/custom/README.md"   # or a URL

[defaults]
notebook_type = "jupyter"   # or "marimo"
```

Edit the file to fill in your GitHub personal access token and archive path.

You can optionally set `readme_source` under `[paths]` to a local file path
or URL. When set, `setup-course` uses that as the README for new courses
instead of the bundled default.

Alternatively, you can set the `GITHUB_TOKEN` environment variable instead of putting the token in the config file.

Use `--force` to overwrite an existing config:

```bash
setup-course-config --force
```

## Usage

### `setup-course` — Create a new course repo

```bash
setup-course -c Acme -t python-intro
```

Options:

| Flag | Description |
|------|-------------|
| `-c`, `--client` | Client name (required) |
| `-t`, `--topic` | Course topic (required) |
| `-d`, `--date` | YYYY-MM override (defaults to current month) |
| `-n`, `--num-sessions` | Number of sessions (creates one notebook per session) |
| `--freq` | Session frequency: `daily` or `weekly` (requires `-n`, defaults to `daily`) |
| `--notebook-type` | `jupyter` or `marimo` (overrides config default) |

This will:

1. Copy the bundled course template to a new directory named `{client}-{topic}-{YYYY-MM}`
2. Create one or more Jupyter notebooks (`.ipynb`) or Marimo notebooks (`.py`) named `{client}-{topic}-{YYYY-MM-DD}` for each session date
3. Generate a `pyproject.toml` with the appropriate notebook dependency and `gitautopush`
4. Create a public GitHub repo and configure the local `.git/config` remote

### `retire-course` — Archive a course repo

```bash
retire-course -d ./Acme-2026-03-18
```

Options:

| Flag | Description |
|------|-------------|
| `-d`, `--dirname` | Path to the course directory to retire (required) |

This will:

1. Make the GitHub repo private
2. Move the local directory to your configured archive path under the current year

## Development

```bash
git clone https://github.com/reuven/course-setup.git
cd course-setup
uv sync --dev
```

Run tests:

```bash
uv run pytest
```

Format and lint:

```bash
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy --strict src/
```

## License

MIT — see [LICENSE](LICENSE) for details.
