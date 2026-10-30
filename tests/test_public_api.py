import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def load_checker():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_wheel.py"
    assert path.is_file(), "isolated installed-artifact checker missing"
    spec = importlib.util.spec_from_file_location("check_wheel", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checker_rejects_checkout_origin_and_metadata_mismatch(tmp_path):
    checker = load_checker()
    prefix = tmp_path / "venv"
    with pytest.raises(AssertionError, match="origin"):
        checker.verify_install(tmp_path / "checkout" / "__init__.py", prefix, "0.1.0", "0.1.0")
    with pytest.raises(AssertionError, match="version"):
        checker.verify_install(prefix / "lib" / "__init__.py", prefix, "0.2.0", "0.1.0")
    checker.verify_install(prefix / "lib" / "__init__.py", prefix, "0.1.0", "0.1.0")


def test_sample_is_an_unrelated_public_api_consumer():
    sample = Path(__file__).resolve().parents[1] / "examples" / "sample_app.py"
    assert sample.is_file(), "unrelated consumer sample missing"
    # Import in this test process so both checkout and installed test runs work.
    spec = importlib.util.spec_from_file_location("sample_app", sample)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == {"code": "BOOK_UNAVAILABLE", "message": "Book unavailable"}


def test_import_has_no_logger_configuration_or_app_dependencies():
    import modkit_diagnostics

    source = Path(modkit_diagnostics.__file__).resolve().parents[1]
    script = f"""import sys, logging
sys.path.insert(0, {str(source)!r})
root = logging.getLogger()
before = (root.handlers[:], root.level, root.propagate, dict(logging.Logger.manager.loggerDict))
loaded_before = set(sys.modules)
import modkit_diagnostics
assert before == (root.handlers, root.level, root.propagate, dict(logging.Logger.manager.loggerDict))
new_roots = {{name.split('.')[0] for name in set(sys.modules) - loaded_before}}
assert new_roots <= sys.stdlib_module_names | {{'modkit_diagnostics'}}
from modkit_diagnostics.errors import DiagnosticError
assert str(DiagnosticError('APP_ERROR')) == 'APP_ERROR'
"""
    subprocess.run([sys.executable, "-I", "-c", script], check=True)
