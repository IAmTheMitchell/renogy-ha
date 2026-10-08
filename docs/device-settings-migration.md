# Semantic device-settings migration

This candidate depends on the paired, unpublished renogy-ble settings API.
Released renogy-ble 2.9.0 does not provide it. Do not merge or deploy this HA
candidate with its current release pins.

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
Overlapping open PRs #238 and #236 must adopt this semantic API in their own
workstreams and establish write support separately. Readable registers alone do
not confer write support. Shunt300 streaming and Hub behavior remain preserved.

## Validate the paired candidate

On a platform where the existing project lock installs successfully:

```sh
BLE_CANDIDATE=/absolute/path/to/ble-device-settings-api
uv sync --all-groups
uv run --with-editable "$BLE_CANDIDATE" python -c 'import renogy_ble; print(renogy_ble.__file__); assert hasattr(renogy_ble.RenogyBleClient, "write_setting")'
uv run --with-editable "$BLE_CANDIDATE" pytest tests
uv run --with-editable "$BLE_CANDIDATE" ruff format --check .
uv run --with-editable "$BLE_CANDIDATE" ruff check .
uv run --with-editable "$BLE_CANDIDATE" ty check .
git diff --check
```

The integration tests execute isolated child processes with HA framework stubs
and mocked GATT, using the actual candidate serializer, response handling and
read parsers. Child processes inherit the same candidate Python environment;
an obsolete installed library cannot satisfy the tests' API assertions.

The locked macOS PyObjC 10.3.2 build fails on Python 3.14 because its build helpers
import the removed `pkg_resources`. For a project-scoped local validation
workaround, create an ignored UV project from the HA worktree (adjust the sibling
library path if necessary):

```sh
mkdir -p .codex-cache/settings-validation
cat > .codex-cache/settings-validation/pyproject.toml <<'EOF'
[project]
name = "renogy-settings-validation"
version = "0.0.0"
requires-python = ">=3.14.2"
dependencies = ["homeassistant==2026.8.3", "renogy-ble", "pytest>=9.1.1", "pytest-asyncio>=1.4.0", "ruff==0.16.9", "ty==0.0.78"]
[tool.uv.sources]
renogy-ble = { path = "../../../ble-device-settings-api", editable = true }
[tool.uv]
override-dependencies = ["pyobjc-core==12.1", "pyobjc-framework-cocoa==12.1", "pyobjc-framework-corebluetooth==12.1", "pyobjc-framework-libdispatch==12.1"]
EOF
uv sync --project .codex-cache/settings-validation
uv run --project .codex-cache/settings-validation --no-sync python -c 'import renogy_ble; print(renogy_ble.__file__); assert hasattr(renogy_ble.RenogyBleClient, "write_setting")'
uv run --project .codex-cache/settings-validation --no-sync pytest tests
uv run --project .codex-cache/settings-validation --no-sync ruff format --check .
uv run --project .codex-cache/settings-validation --no-sync ruff check .
uv run --project .codex-cache/settings-validation --no-sync ty check . --python .codex-cache/settings-validation/.venv/bin/python
git diff --check
```

This workaround validates the exact local library source with HA 2026.8.3 and
compatible macOS dependencies. It does not establish a clean installation of the
committed lock or Linux/HAOS hardware operation.

## Release handoff

1. Review and release the paired library change using its normal release process.
2. Verify the actual published release includes `write_setting`, `DeviceSetting`,
   `SettingValue` and `get_device_settings`. No version is assumed in this candidate.
3. Pin that real release in `pyproject.toml` and
   `custom_components/renogy/manifest.json`, regenerate `uv.lock`, and validate the
   installed wheel, full suite and minimum supported Home Assistant resolution.
4. Merge the dependent HA PR only after those pins and validations are complete.

Until then, all three HA dependency surfaces retain the current released 2.9.0
pin. Live hardware persistence and device-specific limits were not revalidated;
wire acknowledgement remains distinct from authoritative poll readback.

## Local validation record

- Library base: `31c0a1b1f4c722969f384bd344f71d2bb818b851` (released 2.9.0).
- HA base: `82da4aad66a7ca2a64f036150d5c20a02f01706e` (merged Shunt300 migration).
- Library: Ruff formatting/lint, ty, lock consistency and 377 tests pass.
- HA: Ruff formatting/lint, ty and 216 tests pass using the exact local library
  with HA 2026.8.3. The same 216 tests and ty pass with HA 2026.3.0 in a second
  ignored UV project using the same local-library source and PyObjC workaround.
- HA number/select presentation fields were compared with the baseline AST:
  all fields other than removed wire metadata remain identical.
- HA release pins and lock are byte-for-byte unchanged from the baseline.
- Both primary checkouts and existing worktrees are preserved.

## Independent review disposition

The read-only library review found no actionable defects and independently
passed all 377 tests plus Ruff and ty. The HA review found a P1 dependency
mismatch: released 2.9.0 cannot satisfy the candidate's required imports or
semantic calls. This is a confirmed, pending-release blocker, not a clean or
merge-ready HA result. It is resolved only by the release handoff above; inventing
a version or retaining raw-write compatibility fallbacks would not satisfy the
migration. No other actionable HA defect was established. The reviewer's own
HA test run was blocked by its read-only sandbox; the parent validation runs
above passed with the explicit local-library environments.
