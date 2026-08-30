# Renogy BLE Integration for Home Assistant

![Tests](https://github.com/IAmTheMitchell/renogy-ha/actions/workflows/test.yml/badge.svg)
![Hassfest](https://github.com/IAmTheMitchell/renogy-ha/actions/workflows/hassfest.yml/badge.svg)
![HACS](https://github.com/IAmTheMitchell/renogy-ha/actions/workflows/validate.yml/badge.svg)
![Release](https://github.com/IAmTheMitchell/renogy-ha/actions/workflows/release.yml/badge.svg)

This custom Home Assistant integration provides monitoring and control
capabilities for Renogy devices over Bluetooth Low Energy (BLE). Charge
controllers and DCC chargers use BT-1 or BT-2 modules. Supported batteries,
inverters, and Smart Shunt 300 devices advertise directly over BLE.

> **Disclaimer:** This integration is experimental software. Use caution when controlling electrical loads, and ensure any connected equipment is properly rated and protected.

## Supported Devices

Supported device families:

- Renogy charge controllers using BT-1 or BT-2, including Rover and Wanderer
- Renogy DC-DC chargers using BT-1 or BT-2, including DCC and RBC model families
- Renogy batteries using the legacy, Battery Pro, or RNGPRO protocol:
  - Legacy `BT-TH-*` names containing `BATT` or `BATTERY`
  - Battery Pro names beginning with `RNGRBP` or `RNGC`
  - RNGPRO-family names beginning with `RNGPRO`
  - Battery Pro advertisements containing manufacturer ID `0xE14C`
- Renogy inverters advertising `RNGRIU*`
- Renogy Smart Shunt 300 devices advertising `RTMShunt300*`

Expected to work, but not yet confirmed:

- Renogy Adventurer

Support is protocol-family based, so behavior can vary by model and firmware.
When reporting a problem, include the exact model, Bluetooth name, integration
debug logs, and a comparison with the Renogy app.

## Features

- Automatic discovery of Renogy BLE devices
- Automatic discovery of supported Renogy battery advertisements
- Automatic discovery of Renogy inverter devices advertising `RNGRIU*`
- Automatic discovery of Smart Shunt 300 devices advertising `RTMShunt300*`
- Monitor battery status (voltage, current, temperature, charge state)
- Monitor solar panel (PV) performance metrics
- Monitor load status and statistics
- Monitor inverter AC output, frequency, load power, temperature, and diagnostic metadata
- Monitor Smart Shunt voltage, current, power, state of charge, and derived energy
- Turn the DC load output on/off (supported controllers only)
- Configure supported DCC charging parameters, battery type, and maximum current
- Monitor controller information
- Telemetry exposed as Home Assistant sensors
- Energy dashboard compatible sensors
- Configurable polling interval
- Automatic error recovery

## Prerequisites

- Home Assistant instance (version 2026.3 or newer)
- A compatible Bluetooth adapter on your Home Assistant host device
- Bluetooth discovery enabled in Home Assistant

## Hardware

_Includes Amazon affiliate links which provide a small commission to support this project._

- Compatible Renogy device (see above)
  - Charge controllers and DCC chargers require a [BT-1](https://amzn.to/4pq4csm) or [BT-2](https://amzn.to/4iTNSO8) Bluetooth module.
  - Supported Renogy batteries use their built-in BLE radio.
  - Renogy inverters advertise directly over BLE as `RNGRIU*`.
  - Smart Shunt 300 devices use their built-in BLE radio and do not require a BT-1 or BT-2 dongle.
  - Make sure to purchase the correct module for your device. Different devices use different ports.
- Bluetooth radio for Home Assistant
  - [ESP32 for Bluetooth proxy](https://amzn.to/4lSBHkV) (Recommended)
  - [USB Bluetooth adapter](https://amzn.to/4lsxDrU)

## Installation

This integration can be installed via HACS (Home Assistant Community Store).

1. Ensure you have [HACS](https://hacs.xyz/) installed
2. Search for "Renogy" in the HACS store and install it
3. Restart Home Assistant

## Configuration

The integration is configurable through the Home Assistant UI after installation:

1. Go to Settings > Devices & Services
2. Click the "+ Add Integration" button
3. Search for "Renogy" and select it
4. The integration will automatically start scanning for devices

### Advanced Configuration Options

- **Polling Interval**: Adjust how frequently the device is polled (10-600 seconds, default: 60)
  - Can be configured per device in the device settings
  - Lower values provide more frequent updates but may impact battery life
- **Connection Mode**: Starting in `0.6.0`, devices expose connection mode options in the config entry options flow
  - Smart Shunt 300 devices support `sustained` and `intermittent`
  - Batteries, controllers, DCC chargers, and inverters support `intermittent` and `persistent_session`
  - See [docs/connection-modes.md](docs/connection-modes.md) for behavior and recommendations
- **Inverter Profile**: Inverter entries can use the generic register layout or
  the model-specific `RIV4835CSH1S` profile
  - Existing entries can switch profiles through **Reconfigure** without being deleted
  - See [docs/inverter-profiles.md](docs/inverter-profiles.md) for selection guidance

## Sensors

The integration provides the following sensor groups:

### Controller and DCC Battery Sensors

- Voltage
- Current
- Temperature
- State of Charge
- Charging Status

### Renogy Battery Sensors

- Voltage
- Current
- Power
- Temperature
- State of Charge
- Remaining and rated capacity
- Cycle count
- Cell count and voltage diagnostics, when reported
- Protection status, when the protocol exposes it

### Solar Panel (PV) Sensors

- Voltage
- Current
- Power
- Daily Generation
- Total Generation

### Load Sensors

- Status
- Current Draw
- Power Consumption
- Daily Usage

### Inverter Sensors

- Battery Voltage
- AC Output Voltage
- AC Output Current
- AC Output Frequency
- Input Frequency
- Load Active Power
- Load Apparent Power
- Temperature
- Device ID
- Model

### DC Load Control

Some Renogy charge controllers expose a controllable DC load output. This integration creates a `switch` entity that can turn the DC load on or off.

> **Caution:** This feature is experimental. Write commands may be interpreted differently by devices or firmware versions, which could cause unexpected load behavior. Use appropriate fusing and wiring, and verify behavior in a safe test setup before relying on it.

### DCC Configuration

Supported DC-DC chargers also expose configuration entities for battery type,
maximum charging current, charging voltages, protection thresholds, charge
timing, temperature compensation, and solar cutoff current.

> **Caution:** DCC configuration writes change charger behavior. Confirm that
> every value is appropriate for the connected battery and electrical system
> before applying it.

### Controller Info

- Temperature
- Device Information
- Operating Status

### Smart Shunt Sensors

- Shunt Voltage
- Shunt Current
- Shunt Power
- Shunt State of Charge
- Shunt Charge Status
- Shunt Energy

> **Caution:** Shunt support is experimental.

All sensors are automatically added to Home Assistant's Energy Dashboard where applicable.

## Troubleshooting

### Enable Debug Logging

It can be extremely helpful to enable debug logging when troubleshooting issues.

1. Open your Home Assistant instance and navigate to the [Renogy integration](https://my.home-assistant.io/redirect/integration/?domain=renogy)
2. Select "Enable debug logging"
3. Navigate to the [Home Assistant Core logs](https://my.home-assistant.io/redirect/logs/?provider=core)
4. Select the three dots in the top right and choose "Show raw logs"

### Device Not Found

1. Verify the device is supported by this integration
2. For controllers or DCC chargers, confirm a BT-1 or BT-2 module is installed
3. For batteries, confirm the advertisement matches one of the documented
   battery names or manufacturer IDs
4. For inverter devices, confirm the BLE name starts with `RNGRIU`
5. For Smart Shunt 300 devices, confirm the BLE name starts with `RTMShunt300`
6. Check that Bluetooth is enabled on your Home Assistant host
7. Ensure the device is within range (typically 10m/33ft)
8. Restart the Bluetooth adapter

### Connection Issues

- If the device shows as unavailable:
  1. Check the device is powered on
  2. Verify it's within range
  3. Check Home Assistant logs for specific error messages
  4. Try reducing the polling interval temporarily for testing

### Data Accuracy

- Verify your device firmware is up to date
- Check the Renogy app to compare readings
- Note that some values (like daily totals) reset at midnight
- Smart Shunt energy is integration-derived rather than read directly from the device

## Support

- For bugs, please open an issue on GitHub
- Include Home Assistant logs and your device model information

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
