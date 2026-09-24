# Shunt300 library migration and release handoff

This integration candidate depends on the paired, unpublished `renogy-ble`
Shunt subscription API. It is not ready to merge with the current `2.8.0` pin.
No release number has been reserved or invented, and dependency metadata remains
unchanged until the library is released.

The library now owns GATT connection establishment, notification subscriptions,
BlueZ cache recovery, retries, disconnect cleanup, byte reassembly, decoding,
diagnostics, and per-device energy integration. HA supplies discovery handles and
retry eligibility, gates the first connection on startup/scanner readiness, owns
the background task, and publishes normalized readings and errors. Entity IDs,
options, availability grace/cooldowns, duplicate/five-minute publication behavior,
and sensor energy restoration are preserved.

The paired library fixes the sustained-mode regression where a valid 110-byte
live frame delivered as two 55-byte notifications was discarded by HA. The HA
contract test uses the actual library subscription and decoder with mocked BLE
I/O, including error propagation, recovery, raw diagnostics, and shutdown.

## Local validation

The initial baselines are HA `b8fb9a8b4a122ace5c0e01c7c2d50d7635a392d0`
and BLE `12ccf605fd86e6941deae9f63dbe3497c59239c8`, verified against upstream.
The library source must be selected explicitly while its API is unpublished:

```sh
# Run from the HA worktree; set this to the paired library worktree's src folder.
export SHUNT_LIBRARY_SOURCE=/path/to/ble-shunt-streaming/src
PYTHONPATH="$SHUNT_LIBRARY_SOURCE" uv run --no-sync python -c \
  'import renogy_ble.shunt as s; print(s.__file__); assert hasattr(s.ShuntBleClient, "subscribe")'
PYTHONPATH="$SHUNT_LIBRARY_SOURCE" uv run --no-sync pytest tests
uv run --no-sync ruff format --check .
uv run --no-sync ruff check . --output-format=github
uv run --no-sync ty check . --extra-search-path "$SHUNT_LIBRARY_SOURCE" --output-format=github
```

Use a project-scoped UV environment. On the validation macOS host, the frozen HA
environment fails to build PyObjC 10.3.2 because its isolated build lacks
`pkg_resources`. Test-only setup omitted `pyobjc-core`, `pyobjc-framework-cocoa`,
`pyobjc-framework-corebluetooth`, and `pyobjc-framework-libdispatch` with UV's
`--no-install-package` options. The library's own frozen environment installs
successfully. This validates mocked transport behavior, not a fresh full HA
installation or physical Bluetooth/proxy/BlueZ operation.

Local results for the prepared candidates:

| Candidate/environment | Result |
| --- | --- |
| Library, frozen UV environment | 281 tests passed |
| HA 2026.8.3, explicit local library source | 205 tests passed |
| HA 2026.3.0, lowest-direct environment, same library source | 205 tests passed |
| Ruff formatting/lint and ty in both worktrees | Passed |
| Minimum-HA ty and both whitespace checks | Passed |

The actual imported `renogy_ble.shunt.__file__` was asserted to point to the
paired worktree, rather than relying on installed package version metadata.
Upstream main tips were checked again at closeout and still matched the pinned
baselines above. Neither primary checkout was changed.

Regression coverage also checks that disconnect callbacks from failed connection
attempts cannot end a successful retry session, cancellation of `close()`
propagates while cleanup continues, and notifications received during failed
subscription setup cannot produce a successful intermittent read.

## Release sequence

1. Review and merge the library change, then publish its actual release using
   the repository's normal release process.
2. In the dependent HA PR, set that exact released version in both
   `pyproject.toml` and `custom_components/renogy/manifest.json`, regenerate
   `uv.lock` with UV, and verify that all three agree.
3. Repeat HA tests and Ruff/type checks against the released wheel without the
   source override. Run the minimum supported Home Assistant job as well as the
   normal locked environment, then validate sustained reconnect and unload on
   hardware before claiming hardware verification.
4. Merge/release the HA adapter only after that dependency handoff succeeds.

Device-settings encoding and general advertisement/model classification remain
outside this migration.
