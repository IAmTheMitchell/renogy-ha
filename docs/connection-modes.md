# Connection Modes

Starting with `renogy-ha` `0.6.0`, the integration exposes connection mode options
in the config entry options flow.

You can change them in Home Assistant:

1. Go to `Settings` > `Devices & Services`.
2. Open the Renogy config entry for the device.
3. Select `Configure`.

The available options depend on the device type.

## Smart Shunt 300

Smart Shunt devices support two connection modes:

- `sustained`
- `intermittent`

### Sustained

`sustained` is the default mode for Smart Shunt 300 devices.

In this mode, the integration keeps a BLE notification listener running and
publishes updates from live notification payloads instead of doing a normal
poll on every refresh interval.

Use `sustained` when:

- You want the most responsive Smart Shunt updates.
- The device and Bluetooth adapter or proxy have a stable connection.
- You want Home Assistant to stay connected and receive live shunt data.

Keep in mind:

- The polling interval is not the primary driver for Smart Shunt updates in this mode.
- A sustained connection is generally the best choice for live shunt monitoring.
- If your Bluetooth environment is unstable, you may see reconnect attempts in the logs.

### Intermittent

In `intermittent` mode, the integration connects, reads data, and disconnects on
the normal refresh cycle.

Use `intermittent` when:

- You prefer traditional polling behavior.
- You are troubleshooting sustained connection problems.
- Your Bluetooth environment does not handle a long-lived Smart Shunt connection well.

Keep in mind:

- Update frequency follows the configured polling interval.
- Sensor values may feel less immediate than in `sustained` mode.

## Controllers, DCC Chargers, and Inverters

Non-shunt devices do not use the Smart Shunt `sustained` listener. They expose:

- `intermittent`
- `persistent_session`

### Intermittent

`intermittent` is the default for non-shunt devices.

The integration connects to the device for a refresh, reads data, and then
disconnects.

### Persistent Session

`persistent_session` keeps the underlying BLE session open across refreshes while
still updating entities on the normal polling interval.

Use `persistent_session` when:

- A device is more reliable with fewer reconnects.
- You want to avoid reconnecting for every scheduled refresh.

Keep in mind:

- This mode is still poll-driven.
- The polling interval still controls how often Home Assistant requests fresh data.

## Which Mode Should You Use?

- For Smart Shunt 300 devices, start with `sustained`.
- Switch a Smart Shunt to `intermittent` if you see repeated disconnects or poor
  Bluetooth stability.
- For controllers, DCC chargers, and inverters, start with `intermittent`.
- Try `persistent_session` on non-shunt devices only if repeated reconnects are
  causing trouble and you want to test a longer-lived BLE session.
