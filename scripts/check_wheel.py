"""Install one exact wheel and execute copied behavior tests outside the checkout."""

import argparse
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path


def verify_install(origin: Path, prefix: Path, actual: str, expected: str) -> None:
    """Fail on source-tree imports or mismatched installed metadata."""
    assert origin.resolve().is_relative_to(prefix.resolve()), "wrong installed origin"
    assert actual == expected, "wrong installed version"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    if not wheel.name.startswith("modkit_diagnostics-") or wheel.suffix != ".whl":
        parser.error("expected a modkit_diagnostics wheel")
    expected = wheel.name.split("-")[1]
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="diagnostics-consumer-") as directory:
        target = Path(directory)
        environment = target / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / (
            "Scripts/python.exe" if __import__("os").name == "nt" else "bin/python"
        )
        subprocess.run(
            [
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--index-url",
                "https://pypi.org/simple",
                str(wheel),
                "pytest==9.2.0",
            ],
            cwd=target,
            check=True,
        )
        for name in ("tests", "examples", "scripts"):
            shutil.copytree(
                root / name, target / name, ignore=shutil.ignore_patterns("__pycache__")
            )
        validation = f"""
import importlib.metadata as metadata
import runpy
import sys
from pathlib import Path
import modkit_diagnostics
checker = runpy.run_path({str(target / "scripts" / "check_wheel.py")!r})
checker['verify_install'](Path(modkit_diagnostics.__file__), Path(sys.prefix),
    metadata.version('modkit-diagnostics'), {expected!r})
assert metadata.requires('modkit-diagnostics') in (None, [])
assert sorted(d.metadata['Name'].lower().replace('_', '-') for d in metadata.distributions()
    if d.metadata['Name'].lower().startswith('modkit')) == ['modkit-diagnostics']
runpy.run_path({str(target / "examples" / "sample_app.py")!r}, run_name='__main__')
print('verified installed origin, version, zero runtime dependencies and sample')
"""
        subprocess.run([str(python), "-I", "-c", validation], cwd=target, check=True)
        subprocess.run([str(python), "-I", "-m", "pip", "check"], cwd=target, check=True)
        subprocess.run([str(python), "-I", "-m", "pytest", "tests", "-q"], cwd=target, check=True)


if __name__ == "__main__":
    main()
