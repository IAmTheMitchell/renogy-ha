# Library device-identification migration

## Released dependency

The integration consumes the public identification API from `renogy-ble==2.11.0`.
The library implementation merged in
[renogy-ble #188](https://github.com/IAmTheMitchell/renogy-ble/pull/188), and
[renogy-ha #262](https://github.com/IAmTheMitchell/renogy-ha/pull/262) aligned
`pyproject.toml`, `custom_components/renogy/manifest.json`, and `uv.lock` with that
released version. This migration includes that dependency update from HA main.

## Ownership and consumers

`renogy_ble.identification` owns advertisement prefixes, manufacturer IDs, device
identifiers, battery variants, and DCC model recognition. HA's `device_name.py`
contains thin policy adapters: it rejects HA's `Unknown` labels, applies the
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
the selected type and inverter profile remain intact. A legacy battery name
containing `BATT` or `BATTERY` identifies a battery and is compatible only with
battery readiness. Reported DCC models retain the existing warning and
reconfiguration behavior. No config-entry migration is introduced.

## Validation with the released library

Use a project-scoped UV environment and clear any previous source override:

```sh
unset PYTHONPATH
uv sync --locked --all-groups
uv run --no-sync python -c 'import importlib.metadata, renogy_ble; print(importlib.metadata.version("renogy-ble")); print(renogy_ble.__file__)'
uv run --no-sync ruff format --check .
uv run --no-sync ruff check . --output-format=github
uv run --no-sync ty check . --output-format=github
uv run --no-sync pytest tests
git diff --check
```

The installed distribution must be 2.11.0 and its source must resolve inside the
project environment's `site-packages`, not a local library worktree. Subprocess
contract tests exercise real library classification and device objects together
with HA discovery and coordinator adapters. The regression suite covers
manufacturer-only discovery, repeated nameless packets, actual-address/UUID
placeholders, persisted fallbacks, confirmed names, hardware display names,
selected protocols/profiles, model warnings, reconfiguration, and entity setup.

On macOS/Python 3.14, the locked PyObjC 10.3.2 build fails because
`pkg_resources` is missing. Local validation installed the other locked packages,
including the published library, with these native packages omitted:

```sh
uv sync --locked --all-groups \
  --no-install-package pyobjc-core \
  --no-install-package pyobjc-framework-cocoa \
  --no-install-package pyobjc-framework-corebluetooth \
  --no-install-package pyobjc-framework-libdispatch
```

This avoids changing the committed dependency files. Use `--no-sync` for subsequent
local checks so UV does not retry those native builds. Physical Bluetooth hardware,
a running HA installation, and an unmodified full macOS installation are outside
this validation. GitHub CI independently runs the normal Linux environment and
the minimum supported Home Assistant 2026.3.0 environment.
