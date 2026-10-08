"""Prove the HA adapter uses the real installed library contract."""

import subprocess
import sys

import pytest


# A child process isolates the real library from legacy tests' global module
# stubs. Only HA framework services and GATT are mocked, not the library API.
@pytest.mark.parametrize("profile", ["dcc", "controller", "rego", "riv"])
def test_entity_coordinator_and_real_library(profile):
    result = subprocess.run(
        [sys.executable, "-m", "tests.settings_candidate_scenario", profile],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
