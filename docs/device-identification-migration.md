# Library device-identification migration

## Coordinated baselines

The library candidate starts at `ee1d8dc` (released 2.10.0, semantic settings API
merged in #185). The integration candidate starts at `1776ed2` (semantic settings
consumer merged in #256). Both include the merged Shunt300 implementation.

## Ownership and consumers

`renogy_ble.identification` owns advertisement prefixes, manufacturer IDs, device
identifiers, battery variants, and DCC model recognition. HA's `device_name.py`
now contains thin policy adapters: it rejects HA's `Unknown` labels, applies the
existing default when classification is unresolved, and gates entity readiness
using library-defined name compatibility.

- `config_flow.py` consumes these adapters for discovery, type defaults, and
  model-based reconfiguration suggestions.
- `ble.py` consumes them for advertisement updates and model mismatch warnings.
- `switch.py` retains readiness behavior through the adapters. Sensor setup
  continues creating entities immediately using its existing display-name policy.
- `const.py` reexports the library `DeviceType` and uses its inverter model ID.
- `number.py` imports the shared REGO prefix for its existing presentation gate.

Bluetooth registration remains in HA's manifest. The configured name continues
to come from `entry.data[CONF_DEVICE_NAME]`, not the editable title. A confirmed
local name remains ahead of service-info/OS names and the stored fallback. A name
read from hardware remains the display name without replacing protocol evidence.
Missing manufacturer data in later packets continues to use cached data.

Generic BT-TH advertisements do not establish controller versus DCC hardware;
the selected type and inverter profile remain intact. Reported DCC models retain
the existing warning and reconfiguration behavior. No config-entry migration is
introduced, and family-specific discovery behavior is preserved.

## Release handoff

The identification API is new candidate code, absent from the 2.10.0 release.
**This HA change must wait for the library API to be merged and released.** The
existing `renogy-ble==2.10.0` entries in `pyproject.toml`, `manifest.json`, and
`uv.lock` remain aligned; no future release version is invented. Before marking the dependent
HA draft ready or merging it, adopt the real released version in all three:

```sh
uv add 'renogy-ble==<actual-released-version>'
# Set custom_components/renogy/manifest.json requirements to that same version.
uv sync --all-groups
```

Then rerun the full checks without the candidate overlay. The library's version
and changelog remain managed by release automation.

## Reproducible candidate validation

Use dedicated worktrees with project-scoped UV environments. Set `BLE_WORKTREE`
to the library candidate; no editable dependency or local path is committed to
HA's dependency files:

```sh
BLE_WORKTREE="$HOME/home_assistant/renogy/renogy-worktrees/ble-device-identification"
# From the HA candidate worktree, after uv sync --all-groups:
export PYTHONPATH="$BLE_WORKTREE/src"
uv run --no-sync python -c 'import importlib.metadata, renogy_ble; print(importlib.metadata.version("renogy-ble")); print(renogy_ble.__file__)'
uv run --no-sync ruff format --check .
uv run --no-sync ruff check . --output-format=github
uv run --no-sync ty check . --output-format=github
uv run --no-sync pytest tests
```

Verify the source path points to this exact candidate. Installed distribution
metadata is currently 2.10.0; the source overlay is intentionally unreleased API
code, not evidence that the published 2.10.0 wheel contains it. Subprocess contract
tests exercise real library identity and device objects, plus HA's discovery and
coordinator adapters, without replacing classification with matching mocks.

On this macOS/Python 3.14 machine, an unmodified fresh HA `uv sync` fails building
locked PyObjC 10.3.2 because `pkg_resources` is missing. Local validation provisioned
the new HA worktree environment using temporary `[tool.uv] override-dependencies`
for `pyobjc-core`, `pyobjc-framework-cocoa`, `pyobjc-framework-corebluetooth`, and
`pyobjc-framework-libdispatch`, all at 12.1. The temporary dependency-file changes
were restored before checks. This is a local tooling workaround; the committed
lock is unchanged. Use `--no-sync` for this provisioned environment so UV does not
restore those broken macOS packages. Ordinary locked installation and physical
Bluetooth hardware behavior were not validated by this workaround.

## Validation results

- Library: 426 tests passed, including 49 shared identification regressions.
- HA: 217 tests passed against the exact candidate library source, including
  isolated-process coverage using real classification and device objects.
- Ruff formatting/lint, full-repository ty, and `git diff --check` passed in both
  worktrees. HA uses its locked Ruff 0.16.9 / ty 0.0.78 / pytest 9.1.1; library
  uses Ruff 0.16.9 / ty 0.0.84 / pytest 9.1.1.
- HA installed metadata was explicitly checked: `renogy-ble` 2.10.0 and
  Home Assistant 2026.8.3. Imported source was explicitly checked to resolve to
  `ble-device-identification/src/renogy_ble`, including `identification.py`.
- Existing settings, Shunt300, discovery, configured-name, model-warning,
  reconfiguration, entity-readiness, and identifier regressions remain passing.
- Library UV sync also corrected the existing root-package lock metadata from
  2.9.0 to its already released 2.10.0 project version, with no dependency change.

The candidate branches are `feat/device-identification` (library) and
`refactor/library-device-identification` (HA). Validation used dedicated worktrees
and preserved the primary checkouts and other worktrees. No live device, Bluetooth adapter, or running Home
Assistant installation was used for these tests.
