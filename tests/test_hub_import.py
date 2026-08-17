"""Regression tests for loading the production Communication Hub module."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_real_hub_module_imports_in_clean_interpreter() -> None:
    """Load the production Hub module without package or test-module stubs."""
    repo_root = Path(__file__).resolve().parents[1]
    hub_path = repo_root / "custom_components" / "renogy" / "hub.py"
    script = f"""
import importlib.util
import sys
import types
from pathlib import Path

hub_path = Path({str(hub_path)!r}).resolve()

custom_components_pkg = types.ModuleType("custom_components")
custom_components_pkg.__path__ = [str(hub_path.parents[1])]
sys.modules["custom_components"] = custom_components_pkg

renogy_pkg = types.ModuleType("custom_components.renogy")
renogy_pkg.__path__ = [str(hub_path.parent)]
sys.modules["custom_components.renogy"] = renogy_pkg

spec = importlib.util.spec_from_file_location("custom_components.renogy.hub", hub_path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

assert Path(module.__file__).resolve() == hub_path
assert module.__name__ == "custom_components.renogy.hub"
assert hasattr(module, "RenogyHubBatteryManager")
assert hasattr(module, "RenogyHubBatteryState")
assert module._optional_float("1.5") == 1.5
assert module._optional_float(object()) is None
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
