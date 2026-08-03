#!/usr/bin/env python3

import argparse
import subprocess
import zipfile
from pathlib import Path

from setup_course_github import __author__, __email__, __version__


def _last_error_line(stderr: str) -> str:
    """Return the last non-blank line of *stderr* (stripped), or "" if none."""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _pdf_failure_kind(stderr: str) -> str:
    """Classify a webpdf failure as 'lib', 'chromium', or 'other'.

    'lib' (the nbconvert[webpdf]/playwright library is missing) takes priority
    over 'chromium' (the browser binary is missing) when both appear.
    """
    low = stderr.lower()
    lib_signals = (
        "nbconvert[webpdf]",
        "no module named 'playwright'",
        "playwright is not installed to support web pdf",
    )
    if any(signal in low for signal in lib_signals):
        return "lib"
    chromium_signals = (
        "playwright install",
        "executable doesn't exist",
        "download new browsers",
    )
    if any(signal in low for signal in chromium_signals):
        return "chromium"
    return "other"


def _export_notebook(nb_path: Path, course_path: Path, fmt: str, label: str) -> bool:
    """Export a notebook to *fmt* via nbconvert. Returns True on success.

    *label* is the human-readable format name used in warning messages.
    """
    # Use the notebook's relative path from the course dir so nbconvert
    # can find it regardless of spaces in the name.
    relative = nb_path.relative_to(course_path)
    try:
        subprocess.run(
            ["uv", "run", "jupyter", "nbconvert", "--to", fmt, str(relative)],
            cwd=str(course_path),
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if exc.stderr else ""
        print(
            f"  Warning: failed to export {nb_path.name} to {label}: "
            f"{_last_error_line(stderr)}"
        )
        return False
    except FileNotFoundError:
        print(f"  Warning: jupyter nbconvert not found, skipping {label} export")
        return False


def _export_notebook_to_html(nb_path: Path, course_path: Path) -> bool:
    """Export a single notebook to HTML. Returns True on success."""
    return _export_notebook(nb_path, course_path, "html", "HTML")


def _export_notebook_to_pdf(nb_path: Path, course_path: Path) -> tuple[bool, str]:
    """Run webpdf export for one notebook. Returns (ok, stderr); does not print."""
    relative = nb_path.relative_to(course_path)
    try:
        subprocess.run(
            ["uv", "run", "jupyter", "nbconvert", "--to", "webpdf", str(relative)],
            cwd=str(course_path),
            capture_output=True,
            check=True,
        )
        return True, ""
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr.decode() if exc.stderr else ""
    except FileNotFoundError:
        return False, "jupyter nbconvert not found"


def _install_chromium(course_path: Path) -> bool:
    """Install the chromium browser for webpdf via the course's playwright.

    Returns True on success. Runs `uv run playwright install chromium` in the
    course dir; the browser lands in a shared per-machine cache.
    """
    result = subprocess.run(
        ["uv", "run", "playwright", "install", "chromium"],
        cwd=str(course_path),
        capture_output=True,
    )
    return result.returncode == 0


def _export_notebooks_to_pdf(notebooks: list[Path], course_path: Path) -> int:
    """Export notebooks to PDF, auto-installing chromium once if needed.

    Returns the number of PDFs produced. Prints concise, actionable messages and
    never raises — a failure leaves the HTML export + zip intact.
    """
    exported = 0
    chromium_installed = False
    for nb_path in notebooks:
        ok, stderr = _export_notebook_to_pdf(nb_path, course_path)
        if ok:
            exported += 1
            continue
        kind = _pdf_failure_kind(stderr)
        if kind == "lib":
            print("  PDF export needs the webpdf extra. In the course dir run:")
            print('    uv add "nbconvert[webpdf]"')
            print("  (then archive again, or use --no-pdf to skip PDF.)")
            break
        if kind == "chromium" and not chromium_installed:
            print("  Chromium isn't installed yet (needed for PDF export).")
            print("  Installing it once now — this may take a minute...")
            if not _install_chromium(course_path):
                print("  Could not install Chromium automatically; skipping PDF.")
                print("    To enable it, run: uv run playwright install chromium")
                break
            chromium_installed = True
            print("  Chromium installed.")
            ok, stderr = _export_notebook_to_pdf(nb_path, course_path)
            if ok:
                exported += 1
                continue
        print(
            f"  Warning: failed to export {nb_path.name} to PDF: "
            f"{_last_error_line(stderr)}"
        )
    return exported


def archive_course(
    dirname: str,
    output: str | None = None,
    export_html: bool = True,
    export_pdf: bool = True,
) -> Path:
    """Create a zip archive of a course directory.

    Optionally exports notebooks to HTML and/or PDF first.
    """
    course_path = Path(dirname)
    if not course_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {dirname}")

    # Find all notebooks (skip .ipynb_checkpoints)
    notebooks = sorted(
        nb
        for nb in course_path.rglob("*.ipynb")
        if ".ipynb_checkpoints" not in nb.parts
    )

    # Export notebooks to HTML if requested
    html_exported = 0
    if export_html and notebooks:
        print("Exporting notebooks to HTML...")
        for nb_path in notebooks:
            if _export_notebook_to_html(nb_path, course_path):
                html_exported += 1

    # Export notebooks to PDF if requested
    pdf_exported = 0
    if export_pdf and notebooks:
        print("Exporting notebooks to PDF...")
        pdf_exported = _export_notebooks_to_pdf(notebooks, course_path)

    # Determine output path
    if output is not None:
        zip_path = Path(output)
    else:
        zip_path = Path(f"{course_path.name}.zip")

    # Directories to exclude from the zip
    exclude_dirs = {".git", ".venv", "__pycache__", ".ipynb_checkpoints"}

    # Create zip file
    parent = course_path.parent
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(course_path.rglob("*")):
            if file_path.is_file() and not (
                set(file_path.relative_to(course_path).parts) & exclude_dirs
            ):
                arcname = file_path.relative_to(parent)
                zf.write(file_path, arcname)

    # Gather info for summary
    with zipfile.ZipFile(zip_path, "r") as zf:
        file_count = len(zf.namelist())

    zip_size = zip_path.stat().st_size
    size_str = (
        f"{zip_size / 1024:.1f} KB"
        if zip_size < 1024 * 1024
        else f"{zip_size / (1024 * 1024):.1f} MB"
    )

    # Collect non-notebook, non-HTML, non-PDF files for the summary
    notebook_names = {nb.name for nb in notebooks}
    html_names = {nb.with_suffix(".html").name for nb in notebooks}
    pdf_names = {nb.with_suffix(".pdf").name for nb in notebooks}
    with zipfile.ZipFile(zip_path, "r") as zf:
        other_files = sorted(
            Path(name).name
            for name in zf.namelist()
            if Path(name).name not in notebook_names
            and Path(name).name not in html_names
            and Path(name).name not in pdf_names
        )

    # Print summary
    print(f"Archive created: {zip_path}")
    print(f"Files: {file_count}")
    print(f"Size: {size_str}")

    if notebooks:
        print("Notebooks:")
        for nb in notebooks:
            parts = [nb.name]
            html_path = nb.with_suffix(".html")
            if export_html and html_path.exists():
                parts.append(html_path.name)
            pdf_path = nb.with_suffix(".pdf")
            if export_pdf and pdf_path.exists():
                parts.append(pdf_path.name)
            print("  " + " + ".join(parts))
    if export_html and html_exported > 0:
        print(f"HTML exports: {html_exported}")
    if export_pdf and pdf_exported > 0:
        print(f"PDF exports: {pdf_exported}")

    if other_files:
        print("Other files:")
        for name in other_files:
            print(f"  {name}")

    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a zip archive of a course directory",
        epilog=(
            f"Version {__version__} — https://pypi.org/project/course-setup/\n"
            f"{__author__} <{__email__}>"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=(
            f"%(prog)s {__version__}\n"
            f"https://pypi.org/project/course-setup/\n"
            f"{__author__} <{__email__}>"
        ),
    )
    parser.add_argument("dirname", help="Path to course directory")
    parser.add_argument(
        "--output",
        "-o",
        help="Custom output zip path",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        default=False,
        help="Skip HTML export of notebooks",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        default=False,
        help="Skip PDF export of notebooks",
    )
    args = parser.parse_args()

    archive_course(
        dirname=args.dirname,
        output=args.output,
        export_html=not args.no_html,
        export_pdf=not args.no_pdf,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
