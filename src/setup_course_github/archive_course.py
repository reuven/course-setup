#!/usr/bin/env python3

import argparse
import subprocess
import zipfile
from pathlib import Path

from setup_course_github import __author__, __email__, __version__


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
            f"  Warning: failed to export {nb_path.name} to {label}: {stderr.strip()}"
        )
        return False
    except FileNotFoundError:
        print(f"  Warning: jupyter nbconvert not found, skipping {label} export")
        return False


def _export_notebook_to_html(nb_path: Path, course_path: Path) -> bool:
    """Export a single notebook to HTML. Returns True on success."""
    return _export_notebook(nb_path, course_path, "html", "HTML")


def _export_notebook_to_pdf(nb_path: Path, course_path: Path) -> bool:
    """Export a single notebook to PDF via webpdf. Returns True on success."""
    return _export_notebook(nb_path, course_path, "webpdf", "PDF")


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
        for nb_path in notebooks:
            if _export_notebook_to_pdf(nb_path, course_path):
                pdf_exported += 1

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
