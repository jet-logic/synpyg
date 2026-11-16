#!/usr/bin/env python3
"""Run the test suite under coverage and build an HTML report.

Everything this script generates (the coverage data file, the HTML report, the
generated coverage config and Python's bytecode caches) lives in one folder
under the system temp directory. Nothing is written into the project.

Usage:
    python scripts/coverage_html.py [--open] [--fail-under PERCENT] [--root DIR]
                                    [--package NAME] [--out-name NAME]

The package is resolved in this order: --package, COVERAGE_PACKAGE, then a
best-effort guess from the project layout (src/ or flat) and metadata
(pyproject.toml, setup.cfg, *.egg-info). The report folder is named after
--out-name / COVERAGE_OUT_NAME, or "<package>-coverage" if neither is given.

Requires the ``coverage`` package (``pip install coverage``).
The project's own coverage config (.coveragerc, setup.cfg, ...) is ignored so
that the output location can't be overridden; edit RC_TEMPLATE below instead.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover - neither available
        tomllib = None  # type: ignore[assignment]

TEST_ARGS = ["unittest", "discover", "-s", "tests", "-t", "."]  # run as `python -m ...`

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

# Folders that are never the package we want to measure.
_SKIP_DIRS = {
    "tests",
    "test",
    "docs",
    "doc",
    "examples",
    "scripts",
    "build",
    "dist",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "__pycache__",
    ".git",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "site-packages",
    ".idea",
    ".vscode",
}
_PROJECT_MARKERS = ("pyproject.toml", "setup.cfg", "setup.py", ".git")


# --------------------------------------------------------------------------- #
# Project root discovery
# --------------------------------------------------------------------------- #
def find_project_root(explicit: str | None) -> Path:
    """Locate the project root: explicit arg, else the nearest marker folder.

    Searches cwd first, then falls back to the script's own directory, then
    finally just returns cwd.
    """
    if explicit:
        root = Path(explicit).resolve()
        if not root.is_dir():
            sys.exit(f"error: --root is not a directory: {root}")
        return root

    starts = [Path.cwd().resolve(), Path(__file__).resolve().parent]
    for start in starts:
        for candidate in (start, *start.parents):
            if any((candidate / m).exists() for m in _PROJECT_MARKERS):
                return candidate
    return Path.cwd().resolve()


# --------------------------------------------------------------------------- #
# Package guessing
# --------------------------------------------------------------------------- #
def _candidate_dirs(root: Path) -> list[Path]:
    """Directories that plausibly contain an importable package."""
    found: list[Path] = []
    for base in (root, root / "src", root / "lib"):
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            if child.name in _SKIP_DIRS or child.name.startswith("."):
                continue
            if (child / "__init__.py").is_file():
                found.append(child)
            elif any(p.suffix == ".py" for p in child.glob("*.py")):
                # Namespace-ish package / loose module dir; lower confidence.
                found.append(child)
    return found


def _first_line(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            token = line.split("#", 1)[0].strip()
            if token:
                return token
    except OSError:
        return None
    return None


def _from_egg_info(root: Path) -> str | None:
    patterns = ("*.egg-info", "src/*.egg-info", "lib/*.egg-info")
    for pattern in patterns:
        for info in root.glob(pattern):
            top = info / "top_level.txt"
            if top.is_file():
                name = _first_line(top)
                if name and not name.startswith("_"):
                    return name
    return None


def _from_pyproject(root: Path) -> str | None:
    if tomllib is None:
        return None
    py = root / "pyproject.toml"
    if not py.is_file():
        return None
    try:
        data = tomllib.loads(py.read_text(encoding="utf-8"))
    except Exception:
        return None

    # setuptools explicitly lists packages -> most trustworthy.
    pkgs = data.get("tool", {}).get("setuptools", {}).get("packages")
    if isinstance(pkgs, list) and pkgs:
        return str(pkgs[0]).split(".")[0]

    # Poetry name.
    name = data.get("tool", {}).get("poetry", {}).get("name")
    if name:
        return name.replace("-", "_")

    # PEP 621 distribution name (may differ from import name; hint only).
    name = data.get("project", {}).get("name")
    if name:
        return name.replace("-", "_")

    return None


def _from_setup_cfg(root: Path) -> str | None:
    cfg = root / "setup.cfg"
    if not cfg.is_file():
        return None
    text = cfg.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^name\s*=\s*(\S+)", text, re.MULTILINE)
    return m.group(1).replace("-", "_") if m else None


def guess_package(root: Path) -> str | None:
    """Best-effort: return the importable top-level package name under *root*.

    Prefers metadata that matches an on-disk package, then src/ layout, then
    flat layout, then raw distribution name as a last resort. Never executes
    project code.
    """
    candidates = _candidate_dirs(root)
    by_name = {p.name for p in candidates}

    for probe in (_from_egg_info(root), _from_pyproject(root), _from_setup_cfg(root)):
        if probe and probe in by_name:
            return probe

    if candidates:
        src_hits = [p for p in candidates if p.parent.name in ("src", "lib")]
        return (src_hits or candidates)[0].name

    # Nothing on disk matched; fall back to metadata only.
    return _from_pyproject(root) or _from_setup_cfg(root)


# --------------------------------------------------------------------------- #
# Output directory
# --------------------------------------------------------------------------- #
def fresh_output_dir(name: str) -> Path:
    """Create (or empty) the report folder inside the system temp dir."""
    tmp = Path(tempfile.gettempdir()).resolve()
    out = tmp / name
    if out.exists():
        if out.resolve().parent != tmp:
            sys.exit(f"error: refusing to delete {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--root", help="project root (default: auto-detect)")
    parser.add_argument(
        "--open", action="store_true", help="open the report in a browser"
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        metavar="PERCENT",
        help="exit with status 2 if total coverage is below PERCENT",
    )
    parser.add_argument(
        "--package",
        default=os.environ.get("COVERAGE_PACKAGE"),
        help="package to measure (default: guessed from the project, "
        "env: COVERAGE_PACKAGE)",
    )
    parser.add_argument(
        "--out-name",
        default=os.environ.get("COVERAGE_OUT_NAME"),
        help="report folder name under the temp dir "
        "(default: '<package>-coverage', env: COVERAGE_OUT_NAME)",
    )
    args = parser.parse_args()

    if importlib.util.find_spec("coverage") is None:
        sys.exit(
            "error: the 'coverage' package is not installed.\n"
            f"       install it with:  {Path(sys.executable).name} -m pip install coverage"
        )

    root = find_project_root(args.root)

    package = args.package or guess_package(root)
    if not package:
        sys.exit(
            f"error: could not guess the package to measure under {root};\n"
            "       pass --package NAME (or set COVERAGE_PACKAGE)"
        )
    out_name = args.out_name or f"{package}-coverage"

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", package):
        sys.exit(f"error: invalid package name: {package!r}")
    if not out_name or "/" in out_name or "\\" in out_name or out_name in (".", ".."):
        sys.exit(f"error: invalid --out-name: {out_name!r}")

    # Sanity-check that the package actually exists on disk under the root.
    if (
        not (root / package).is_dir()
        and not (root / "src" / package).is_dir()
        and not (root / "lib" / package).is_dir()
    ):
        sys.exit(
            f"error: package {package!r} not found under {root} "
            "(looked in '.', 'src/', 'lib/')"
        )

    out = fresh_output_dir(out_name)
    data_file = out / ".coverage"
    html_dir = out / "html"
    rc_file = out / "coveragerc.ini"
    rc_file.write_text(
        RC_TEMPLATE.format(
            package=package,
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
        full = [
            sys.executable,
            "-m",
            "coverage",
            cmd[0],
            f"--rcfile={rc_file}",
            *cmd[1:],
        ]
        return subprocess.run(full, cwd=root, env=env).returncode

    print(f"project : {root}")
    print(f"package : {package}")
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
