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
- `all_devices`: List of dictionaries for every Renogy device with `name`,
  `address`, `status`, `device_type`, and `rssi`.
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

extra_styles: |
  @keyframes pulseHealthy {
    0% { box-shadow: 0 0 0 0 rgba(17,107,47,0.45); }
    70% { box-shadow: 0 0 0 12px rgba(17,107,47,0); }
    100% { box-shadow: 0 0 0 0 rgba(17,107,47,0); }
  }
  @keyframes pulseWarn {
    0% { box-shadow: 0 0 0 0 rgba(122,90,17,0.45); }
    70% { box-shadow: 0 0 0 12px rgba(122,90,17,0); }
    100% { box-shadow: 0 0 0 0 rgba(122,90,17,0); }
  }
  @keyframes pulseCritical {
    0% { box-shadow: 0 0 0 0 rgba(122,17,17,0.5); }
    70% { box-shadow: 0 0 0 12px rgba(122,17,17,0); }
    100% { box-shadow: 0 0 0 0 rgba(122,17,17,0); }
  }

styles:
  grid:
    - grid-template-areas: '"n status" "summary summary" "devices devices"'
    - grid-template-columns: 1fr auto
    - grid-template-rows: min-content min-content min-content
    - row-gap: 8px
  card:
    - padding: 16px 18px
    - border-radius: 14px
    - background: "linear-gradient(135deg, #141414 0%, #1e1e1e 100%)"
    - color: "#f3f3f3"
    - animation: >
        [[[
          const s = entity?.state;
          if (s === "critical") return "pulseCritical 2s infinite";
          if (s === "warn") return "pulseWarn 2.5s infinite";
          if (s === "healthy") return "pulseHealthy 3s infinite";
          return "none";
        ]]]
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
    devices:
      - grid-area: devices
      - font-size: 12px
      - opacity: 0.9
      - text-align: right
      - justify-self: end

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
  devices: |
    [[[
      const list = entity?.attributes?.all_devices || [];
      if (!list.length) return "No devices found";
      const dot = s => s === "critical" ? "🔴" : s === "warn" ? "🟡" : s === "healthy" ? "🟢" : "⚪";
      const fmtRssi = rssi => (typeof rssi === "number" ? `${rssi} dBm` : "n/a");
      return list
        .map(d => `${dot(d.status)} ${d.name || d.address} (${d.status}, ${fmtRssi(d.rssi)})`)
        .join("<br>");
    ]]]
```

### Notes

- This card uses `all_devices` for a polished device list.
