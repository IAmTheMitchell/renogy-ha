## Renogy Health Card (Aggregate)

The integration exposes an aggregate health sensor named `sensor.renogy_health`.
It summarizes all Renogy devices and lists failing devices in attributes.

### Status Rules

- `critical` if any device is `critical` or `disconnected`
- `warn` if any device is `warn`
- `healthy` only if all devices are healthy
- `unknown` if no devices are available

### Attributes

- `failing_devices`: List of dictionaries with `name`, `address`, `status`,
  `device_type`, and `rssi`.
- `total_devices`, `healthy_devices`, `warn_devices`, `critical_devices`,
  `disconnected_devices`

### Button-Card Snippet

Requires the `button-card` custom card. Install it via HACS:
`HACS → Frontend → Button Card`.

```yaml
type: custom:button-card
entity: sensor.renogy_health
name: Renogy Health
show_icon: false
show_state: false
tap_action:
  action: more-info

styles:
  grid:
    - grid-template-areas: '"n status" "summary summary" "failures failures"'
    - grid-template-columns: 1fr auto
    - grid-template-rows: min-content min-content min-content
    - row-gap: 6px
  card:
    - padding: 16px 18px
    - border-radius: 14px
    - background: "linear-gradient(135deg, #141414 0%, #1e1e1e 100%)"
    - color: "#f3f3f3"
  name:
    - font-size: 18px
    - font-weight: 700
  custom_fields:
    status:
      - grid-area: status
      - align-self: center
      - justify-self: end
      - padding: 4px 10px
      - border-radius: 999px
      - font-size: 12px
      - font-weight: 700
      - text-transform: uppercase
    summary:
      - grid-area: summary
      - font-size: 13px
      - opacity: 0.85
    failures:
      - grid-area: failures
      - font-size: 12px
      - opacity: 0.75

custom_fields:
  status: |
    [[[
      const s = entity?.state;
      if (s === "critical") return `<span style="background:#7a1111;color:#fff">Critical</span>`;
      if (s === "warn") return `<span style="background:#7a5a11;color:#fff">Warning</span>`;
      if (s === "healthy") return `<span style="background:#116b2f;color:#fff">Healthy</span>`;
      return `<span style="background:#444;color:#fff">Unknown</span>`;
    ]]]
  summary: |
    [[[
      const a = entity?.attributes || {};
      return `Devices: ${a.total_devices ?? 0} · Warn: ${a.warn_devices ?? 0} · Critical: ${a.critical_devices ?? 0} · Offline: ${a.disconnected_devices ?? 0}`;
    ]]]
  failures: |
    [[[
      const list = entity?.attributes?.failing_devices || [];
      if (!list.length) return "All devices healthy";
      return "Issues: " + list.map(d => `${d.name || d.address} (${d.status})`).join(", ");
    ]]]
```

### Entities-Card Alternative

No custom card required.

```yaml
type: entities
title: Renogy Health
entities:
  - entity: sensor.renogy_health
    name: Overall Health
  - type: attribute
    entity: sensor.renogy_health
    attribute: failing_devices
    name: Failing Devices
```
