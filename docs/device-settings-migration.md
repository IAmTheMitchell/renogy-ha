# Semantic device-settings migration

This integration uses the public settings API in released `renogy-ble==2.10.0`.
[Library PR #185](https://github.com/IAmTheMitchell/renogy-ble/pull/185) introduced
that API. [HA PR #257](https://github.com/IAmTheMitchell/renogy-ha/pull/257) adopted
2.10.0 in `pyproject.toml`, `custom_components/renogy/manifest.json`, and `uv.lock`.
This migration preserves those upstream pins and requires no editable-library
override or future release.

## Changes

Existing DCC numbers and battery/current selects, controller battery selection
and DC load switch, REGO inverter numbers, and RIV4835CSH1S maximum AC charging
current use native semantic calls. Entity keys, unique IDs, names, units, ranges,
options, profile gates, availability, optimistic updates and refresh scheduling
retain their existing behavior. A rejected write never updates an entity as if
it succeeded. Numbers/selects refresh after successful writes; a coordinator
update clears their optimistic values. Load control keeps its existing immediate
acknowledged-state publication and availability handling.

The library owns target registers, target addresses, encoding, constraints and
FC06 acknowledgement validation. Numeric battery codes and raw-write fallback
probes have been removed from HA. The adopted parser contract supplies normalized
battery-type strings. Library capability metadata supplies native charging-current
choices; HA formats them as the existing `10A` through `60A` labels.

No controller voltage controls or RIV output-priority control are added.
Overlapping PRs #238 and #236 must adopt the semantic API in their own workstreams
and establish write support separately. Readable registers alone do not confer
write support. Shunt300 streaming and Hub behavior remain preserved.

## Validate with the released library

On a platform where the project lock installs successfully:

```sh
uv sync --locked --all-groups
uv run --locked python -c 'from importlib.metadata import version; import renogy_ble; assert version("renogy-ble") == "2.10.0"; print(renogy_ble.__file__); assert hasattr(renogy_ble.RenogyBleClient, "write_setting")'
uv run --locked pytest tests
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check .
uv lock --check
git diff --check
```

The integration tests execute isolated child processes with HA framework stubs
and mocked GATT, using the actual installed library serializer, response handling
and read parsers. Child processes inherit the same released-library environment;
an obsolete library cannot satisfy the tests' API assertions.

The locked macOS PyObjC 10.3.2 build fails on Python 3.14 because its build helpers
import the removed `pkg_resources`. A project-scoped local validation workaround
can use the same published library with compatible PyObjC dependencies, without
changing the committed dependency files:

```sh
mkdir -p .codex-cache/settings-release-validation
cat > .codex-cache/settings-release-validation/pyproject.toml <<'EOF'
[project]
name = "settings-release-validation"
version = "0.0.0"
requires-python = ">=3.14.2"
dependencies = ["homeassistant==2026.8.3", "renogy-ble==2.10.0", "pytest>=9.1.1", "pytest-asyncio>=1.4.0", "ruff==0.16.9", "ty==0.0.78"]
[tool.uv]
override-dependencies = ["pyobjc-core==12.1", "pyobjc-framework-cocoa==12.1", "pyobjc-framework-corebluetooth==12.1", "pyobjc-framework-libdispatch==12.1"]
EOF
uv sync --project .codex-cache/settings-release-validation
uv run --project .codex-cache/settings-release-validation --no-sync python -c 'from importlib.metadata import version; import renogy_ble; assert version("renogy-ble") == "2.10.0"; print(renogy_ble.__file__); assert hasattr(renogy_ble.RenogyBleClient, "write_setting")'
uv run --project .codex-cache/settings-release-validation --no-sync pytest tests
uv run --project .codex-cache/settings-release-validation --no-sync ruff format --check .
uv run --project .codex-cache/settings-release-validation --no-sync ruff check .
uv run --project .codex-cache/settings-release-validation --no-sync ty check . --python .codex-cache/settings-release-validation/.venv/bin/python
```

For the minimum Home Assistant validation, create a second ignored UV project
with the same configuration and `homeassistant==2026.3.0`. Both environments use
the published wheel rather than the local library checkout. Local verification
uses the exact wheel URL in the inherited project lock, with SHA-256
`d748f0d70657c720460828fd8f135fc5b274dbc266cc36449ab6c4c22fff5ec5`.

The PyObjC workaround does not establish a clean installation of the committed
lock on macOS. Standard Linux CI validates the normal and minimum-HA dependency
paths. No new live-hardware or HAOS validation is claimed; wire acknowledgement
remains distinct from authoritative poll readback and persistent storage.

## Review and dependency status

The former P1 dependency mismatch is resolved by the real 2.10.0 release and the
upstream HA dependency bump. The migration preserves the 2.10.0 pins from HA
main at `e40f527` and regenerates the lock to repair its stale root-package
`==2.9.0` requirement metadata. Both primary checkouts and other worktrees are
preserved. It does not modify the independently owned library or add write
capabilities beyond the previously exposed controls.

## Released-package validation

- The installed 2.10.0 package was compared with the hash-verified wheel from
  `uv.lock`; all nine library Python source files match the published artifact.
- Full HA suite: 216 tests pass with HA 2026.8.3 and again with HA 2026.3.0,
  including real-library serialization, acknowledgement, and readback scenarios.
- Ruff formatting/lint, ty in both environments, regenerated-lock consistency,
  and diff checks pass.
- macOS validation uses the documented PyObjC workaround; ordinary Linux CI
  verifies the committed dependency resolution without that override.
