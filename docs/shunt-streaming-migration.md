# Shunt300 library integration

The integration uses the public Shunt subscription API released in
[renogy-ble 2.9.0](https://github.com/IAmTheMitchell/renogy-ble/releases/tag/v2.9.0).
The dependency was adopted by
[renogy-ha #253](https://github.com/IAmTheMitchell/renogy-ha/pull/253);
`pyproject.toml`, `custom_components/renogy/manifest.json`, and `uv.lock` all select
`renogy-ble==2.9.0`.

The library owns GATT connection establishment, notification subscriptions, BlueZ
cache recovery, retries, disconnect cleanup, byte reassembly, decoding,
diagnostics, and per-device energy integration. HA supplies discovery handles and
retry eligibility, gates the first connection on startup/scanner readiness, owns
the background task, and publishes normalized readings and errors. Entity IDs,
options, availability grace/cooldowns, duplicate/five-minute publication behavior,
and sensor energy restoration are preserved.

This fixes the sustained-mode regression where a valid 110-byte live frame
received as two 55-byte notifications was discarded by HA. The HA contract test
uses the installed library subscription and decoder with mocked BLE I/O to verify
fragmented readings, error propagation, recovery, raw diagnostics, and shutdown.
Device-settings encoding and general advertisement/model classification remain
outside this migration.

## Validation against the released dependency

Use a project-scoped UV environment with no local library source override:

```sh
uv sync --locked --all-extras --dev
uv run --no-sync python -c \
  'from importlib.metadata import version; import renogy_ble.shunt as s; assert version("renogy-ble") == "2.9.0"; print(s.__file__)'
uv run --no-sync ruff format --check .
uv run --no-sync ruff check . --output-format=github
uv run --no-sync ty check . --output-format=github
uv run --no-sync pytest tests
```

Check that the reported module path belongs to the project environment's
`site-packages`, and remove any `PYTHONPATH` or editable installation that points
to a separate library checkout. The lockfile selects the published wheel with
SHA-256 `bb827729447fc548402d0ba4af8ad126b2744dcbc14bdc30dbc04ca10a01a3ea`.
The minimum-version CI job separately resolves Home Assistant 2026.3.0 with
`uv lock --upgrade-package homeassistant --resolution lowest-direct` and tests the
same released library dependency.

On the validation macOS host, a full locked install fails to build PyObjC 10.3.2
because its isolated build lacks `pkg_resources`. Local test setup omits only
`pyobjc-core`, `pyobjc-framework-cocoa`, `pyobjc-framework-corebluetooth`, and
`pyobjc-framework-libdispatch` using UV's `--no-install-package` options. This
validates the released library with mocked transport; physical Bluetooth, BlueZ,
proxy operation, and a full fresh macOS installation remain unverified.
