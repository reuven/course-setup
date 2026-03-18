# course-setup

CLI tools for setting up and retiring GitHub-backed course repositories.

## Installation

```bash
pip install course-setup
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install course-setup
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

[defaults]
notebook_type = "jupyter"   # or "marimo"
```

Edit the file to fill in your GitHub personal access token and archive path.

Alternatively, you can set the `GITHUB_TOKEN` environment variable instead of putting the token in the config file.

Use `--force` to overwrite an existing config:

```bash
setup-course-config --force
```

## Usage

### `setup-course` — Create a new course repo

```bash
setup-course -d 2026-03-18 -c Acme -r acme-python-2026
```

Options:

| Flag | Description |
|------|-------------|
| `-d`, `--date` | Course date (required) |
| `-c`, `--client` | Client name (required) |
| `-r`, `--repo` | GitHub repo name to create (required) |
| `-n`, `--name` | Optional name suffix (e.g. `advanced`) |
| `--notebook-type` | `jupyter` or `marimo` (overrides config default) |

This will:

1. Copy the bundled course template to a new directory named `{client}-{date}[-{name}]`
2. Create a Jupyter notebook (`.ipynb`) or Marimo notebook (`.py`) based on the notebook type
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
