#!/usr/bin/env python3

import argparse
import subprocess
import zipfile
from pathlib import Path

from setup_course_github import __author__, __email__, __version__


def archive_course(
    dirname: str,
    output: str | None = None,
    export_html: bool = True,
) -> Path:
    """Create a zip archive of a course directory.

    Optionally exports notebooks to HTML first.
    """
    course_path = Path(dirname)
    if not course_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {dirname}")

    # Find all notebooks
    notebooks = sorted(course_path.rglob("*.ipynb"))

    # Export notebooks to HTML if requested
    if export_html and notebooks:
        for nb_path in notebooks:
            subprocess.run(
                ["uv", "run", "jupyter", "nbconvert", "--to", "html", str(nb_path)],
                cwd=dirname,
                check=True,
            )

    # Determine output path
    if output is not None:
        zip_path = Path(output)
    else:
        zip_path = Path(f"{course_path.name}.zip")

    # Create zip file
    parent = course_path.parent
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(course_path.rglob("*")):
            if file_path.is_file():
                arcname = file_path.relative_to(parent)
                zf.write(file_path, arcname)

    # Gather info for summary
    with zipfile.ZipFile(zip_path, "r") as zf:
        file_count = len(zf.namelist())

    zip_size = zip_path.stat().st_size

    # Print summary
    print(f"Archive created: {zip_path}")
    print(f"Files: {file_count}")
    print(f"Size: {zip_size} bytes")

    if notebooks:
        print("Notebooks:")
        for nb in notebooks:
            html_name = nb.with_suffix(".html").name
            if export_html:
                print(f"  {nb.name} -> {html_name}")
            else:
                print(f"  {nb.name}")

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
    args = parser.parse_args()

    archive_course(
        dirname=args.dirname,
        output=args.output,
        export_html=not args.no_html,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
