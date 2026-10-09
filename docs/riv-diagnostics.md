# RIV4835CSH1S LCD diagnostics

This draft depends on [renogy-ble PR #187](https://github.com/IAmTheMitchell/renogy-ble/pull/187).
The dependency is temporarily pinned to its tested commit for reproducible
testing. Replace the Git pin in the manifest, project dependencies, and lockfile
with the released library version before merging this Home Assistant draft.

Select the RIV4835CSH1S inverter profile, then open the integration's **Configure**
options and enable **Read-only inverter LCD diagnostics**. It is disabled by
default and is offered only for this profile. Changing the option reloads the
entry. The normal polling interval still applies.

The option adds 45 diagnostic sensors: 29 LCD settings, operating state, four
fault-code slots with a fault summary/count and description status, the raw
warning mask and bits with an interpretation status, three firmware fields,
and diagnostic read status. Settings use native precision (including 49.2 V
and 53.6 V), rather than rounding voltage setpoints to whole volts. Settings
have no measurement/statistics state class.

All register reads and decoding belong to the library's public
`read_inverter_diagnostics` API. Home Assistant only manages the option, cache,
entities, and downloadable diagnostic snapshot. No settings writes are added.
Existing charging controls and the separate output-priority contribution are
unchanged.

## Validation and limits

The contribution is based on successful reads and physical LCD comparisons
from one RIV4835CSH1S, whose LCD firmware words were **403 / 107**. In particular,
native Programs 23, 24, 26, and 27 displayed ENA, Program 36 displayed 80 A,
and Program 38 displayed 120 V. These comparisons establish observed values,
not every setting transition or compatibility with all firmware revisions.

Program 28 already has a maximum AC charging-current entity. It is not duplicated.
Programs 16, 21, 29, and 39 are excluded from this submission. Program 39's
Modbus mapping remains unresolved despite a readable physical LCD setting;
it is not replaced with a guessed value or used to enforce a circuit limit.

The warning word is raw. A value of 50 gives `Unverified (0x0032)` and bits
`1, 4, 5`, not unproven AC/battery warning descriptions. Fault descriptions
follow the RIV LCD manual; unknown codes remain explicitly unverified. The
four fault slots were zero on the tested installation, so nonzero fault labels
are manual-based rather than induced fault tests.

Software Version Word 0x0014 and 0x0015 preserve raw values 403 and 107. SDK
Firmware Text Candidate read `300*107*160*403`. The component identities remain
unverified; these sensors do not replace the device-info firmware label.

## Polling and history

After a successful measurement poll, diagnostics add eight short read blocks
and at most one extra native/firmware read. At one-minute polling, allow about
nine polls for the first complete extra pass. Native settings refresh every
15 minutes; successful firmware reads cache until an integration reload.
Validated unsupported replies cache until reload. The extra BLE requests add
poll time, so enable the option only when the diagnostics are needed.

Missing/failed values are unavailable, not zero. Per-entity attributes retain
the register, raw value, status, timestamps, cache flag, and response evidence.
`pending`, `partial`, and `complete` describe the read plan; they do not verify
warning meanings or all inverter features.

Diagnostic sensors can be included in history like other entities. Adding
them to a dashboard does not change Recorder exclusions or retention, and
does not backfill periods before they were recorded. A history-card entity
list is independent of CSV export and the available recorded date range.

Use the integration entry's **Download diagnostics** action to obtain the last
completed cached snapshot with diagnostic values and read evidence. Downloading
does not issue BLE requests. Entry identifiers and Bluetooth addresses are
excluded/redacted. Review the snapshot before sharing it publicly.

The companion library documentation lists exact register mappings, observed
values, and protocol sources. Experimental Program 39 probes, native fault
bitmaps, and unverified warning definitions remain separate research work.
