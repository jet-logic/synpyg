#!/usr/bin/env python3
"""Run the test suite under coverage and build an HTML report.

Everything this script generates (the coverage data file, the HTML report, the
generated coverage config and Python's bytecode caches) lives in one folder
under the system temp directory. Nothing is written into the project.

Usage:
    python scripts/coverage_html.py [--open] [--fail-under PERCENT] [--root DIR]

Requires the ``coverage`` package (``pip install coverage``).
The project's own coverage config (.coveragerc, setup.cfg, ...) is ignored so
that the output location can't be overridden; edit RC_TEMPLATE below instead.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

PACKAGE = "synpyg"  # the package to measure
TEST_ARGS = ["unittest", "discover", "-s", "tests", "-t", "."]  # run as `python -m ...`
OUT_NAME = "synpyg-coverage"  # folder name inside the system temp dir

RC_TEMPLATE = """\
[run]
branch = True
source = {package}
data_file = {data_file}

[report]
show_missing = True
skip_empty = True

[html]
directory = {html_dir}
title = {package} coverage
"""


def find_root(explicit: str | None) -> Path:
    """Locate the project root: the folder that contains the package."""
    if explicit:
        root = Path(explicit).resolve()
        if not (root / PACKAGE).is_dir():
            sys.exit(f"error: {root} has no {PACKAGE!r} package")
        return root
    here = Path(__file__).resolve().parent
    for candidate in (here, here.parent, Path.cwd()):
        if (candidate / PACKAGE).is_dir():
            return candidate
    sys.exit(f"error: cannot find the {PACKAGE!r} package; pass --root DIR")


def fresh_output_dir() -> Path:
    """Create (or empty) the report folder inside the system temp dir."""
    tmp = Path(tempfile.gettempdir()).resolve()
    out = tmp / OUT_NAME
    if out.exists():
        # Only ever delete our own folder, directly inside the temp dir.
        if out.resolve().parent != tmp:
            sys.exit(f"error: refusing to delete {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", help="project root (default: auto-detect)")
    parser.add_argument("--open", action="store_true", help="open the report in a browser")
    parser.add_argument(
        "--fail-under",
        type=float,
        metavar="PERCENT",
        help="exit with status 2 if total coverage is below PERCENT",
    )
    args = parser.parse_args()

    if importlib.util.find_spec("coverage") is None:
        sys.exit(
            "error: the 'coverage' package is not installed.\n"
            f"       install it with:  {Path(sys.executable).name} -m pip install coverage"
        )

    root = find_root(args.root)
    out = fresh_output_dir()
    data_file = out / ".coverage"
    html_dir = out / "html"
    rc_file = out / "coveragerc.ini"
    rc_file.write_text(
        RC_TEMPLATE.format(
            package=PACKAGE,
            data_file=data_file.as_posix(),
            html_dir=html_dir.as_posix(),
        ),
        encoding="utf-8",
    )

    env = dict(os.environ)
    env["COVERAGE_FILE"] = str(data_file)
    env["PYTHONPYCACHEPREFIX"] = str(out / "pycache")  # no __pycache__ in the project
    scratch = out / "tmp"  # temp files the tests create stay in our folder too
    scratch.mkdir()
    for var in ("TMPDIR", "TEMP", "TMP"):
        env[var] = str(scratch)
    env.pop("PYTHONDONTWRITEBYTECODE", None)

    def coverage(*cmd: str) -> int:
        full = [sys.executable, "-m", "coverage", cmd[0], f"--rcfile={rc_file}", *cmd[1:]]
        return subprocess.run(full, cwd=root, env=env).returncode

    print(f"project : {root}")
    print(f"output  : {out}\n")

    test_status = coverage("run", "-m", *TEST_ARGS)
    if not data_file.exists():
        print("error: no coverage data was produced (did the tests fail to start?)")
        return test_status or 1

    # Build the report even when tests fail: it shows what the run did cover.
    if coverage("html") != 0:
        print("error: could not build the HTML report")
        return 1

    report_args = ["report"]
    if args.fail_under is not None:
        report_args.append(f"--fail-under={args.fail_under}")
    report_status = coverage(*report_args)

    index = (html_dir / "index.html").resolve()
    print(f"\nHTML report: {index.as_uri()}")
    if args.open:
        webbrowser.open(index.as_uri())

    if test_status:
        print("note: the test run reported failures")
        return test_status
    return report_status


if __name__ == "__main__":
    sys.exit(main())
