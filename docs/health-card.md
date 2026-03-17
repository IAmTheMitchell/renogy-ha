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

Requires the `button-card` custom card.

```yaml
type: custom:button-card
entity: sensor.renogy_health
name: Renogy Health
show_state: true
show_icon: false
tap_action:
  action: more-info
styles:
  card:
    - padding: 16px
    - border-radius: 12px
    - background: var(--card-background-color)
    - color: var(--primary-text-color)
  name:
    - font-size: 18px
    - font-weight: 600
  state:
    - font-size: 14px
    - opacity: 0.8
custom_fields:
  status: |
    [[[
      const s = entity?.state;
      if (s === "critical") return "🔴 Critical";
      if (s === "warn") return "🟡 Warning";
      if (s === "healthy") return "🟢 Healthy";
      return "⚪ Unknown";
    ]]]
  failing: |
    [[[
      const list = entity?.attributes?.failing_devices || [];
      if (!list.length) return "All devices healthy";
      return list.map(d => `${d.name || d.address} (${d.status})`).join(", ");
    ]]]
styles:
  custom_fields:
    status:
      - font-size: 14px
      - margin-top: 6px
    failing:
      - font-size: 12px
      - margin-top: 8px
      - opacity: 0.8
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
