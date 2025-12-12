# Renogy Rover BLE Integration Specification for Home Assistant

## Overview

This document outlines the detailed requirements, architecture, data handling, error management strategies, and testing plan for a Home Assistant integration supporting Renogy Rover charge controllers via Bluetooth (BLE), specifically with BT-1 and BT-2 modules. The integration leverages the existing `renogy-ble` Python parsing library.

---

## 1. Functional Requirements

### 1.1 Supported Devices
- Initially support **Renogy Rover charge controllers** (BT-1 and BT-2 modules)
- Expandable to support other models later

### 1.2 Sensor Exposure

All sensors from the provided `REGISTER_MAP` will be exposed clearly as Home Assistant entities:

### Battery Sensors
- Battery Voltage (`V`, scaled ×0.1)
- Battery Current (`A`, scaled ×0.01)
- Battery Percentage (`%`, raw)
- Battery Temperature (`°C`, raw)
- Battery Type (`open`, `sealed`, `gel`, `lithium`, `custom`)
- Charging Amp Hours Today (`Ah`, daily cumulative)
- Discharging Amp Hours Today (`Ah`, daily cumulative)
- Charging Status (`deactivated`, `activated`, `mppt`, `equalizing`, `boost`, `floating`, `current limiting`)

### Solar Panel (PV) Sensors
- PV Voltage (`V`, scaled ×0.1)
- PV Current (`A`, scaled ×0.01)
- PV Power (`W`, raw)
- Max Charging Power Today (`W`)
- Power Generation Today (`Wh`, daily cumulative)
- Power Generation Total (`kWh`, cumulative)

### Load Sensors
- Load Voltage (`V`, scaled ×0.1)
- Load Current (`A`, scaled ×0.01)
- Load Power (`W`, raw)
- Load Status (`on`, `off`)
- Power Consumption Today (`Wh`, daily cumulative)
- Discharging Amp Hours Today (`Ah`, daily cumulative)

### Controller Info Sensors
- Controller Temperature (`°C`, raw)
- Device ID (text)
- Model (text)
- Battery Temperature (`°C`, raw)
- Max Charging Power Today (`W`, daily cumulative)
- Max Discharging Power Today (`W`, daily cumulative)
- Power Generation Today (`Wh`, daily cumulative)
- Power Generation Total (`kWh`, cumulative)

## Architecture

### BLE Communication
- Active BLE polling of Renogy devices.
- Polling interval default: **60 seconds**, user-configurable between **10–600 seconds**.

### Device Discovery and Setup
- Home Assistant automatically discovers Renogy Rover devices within BLE range.
- Discovered devices appear in the Home Assistant UI for easy setup.
- Device names default to their unique Bluetooth identifiers (e.g., `BT-TH-7724620D`).
- Device metadata (manufacturer, model, firmware version, serial/device ID) stored as device-level attributes in Home Assistant.

### Entity Organization
Sensors automatically grouped logically in Home Assistant:
- **Battery**
- **Solar Panel (PV)**
- **Load**
- **Controller Info**

## Data Handling

- Raw BLE Modbus data parsed via provided `renogy-ble` parsing library.
- Numeric values scaled according to provided mapping definitions.
- Textual status values provided as separate, text-based sensors.
- Temperature units default to Celsius (`°C`).
- Energy metrics use standard units (`Wh` daily metrics, `kWh` cumulative totals).
- Sensors configured with appropriate `device_class` and `state_class` to integrate smoothly with Home Assistant’s Energy Dashboard:
  - Real-time sensors (`measurement`)
  - Daily cumulative sensors (`total_increasing`, daily reset)
  - Long-term cumulative sensors (`total_increasing`)

## Error Handling and Stability
- Integration attempts silent retries on BLE communication failures.
- Sensors and devices marked as `Unavailable` after **3 consecutive polling failures**.
- Automatic recovery: devices marked available automatically once successful polling resumes.
- Clear and concise logging of communication issues, availability changes, and recovery events.

## Security and Privacy
- No sensitive user credentials or personal information stored.
- All BLE communication is local.
- No cloud or external dependencies.

## Testing Plan
- **Unit tests** (leveraging existing parser library unit tests):
  - Validate parsing correctness
  - Test BLE communication logic (simulate connection success/failure)
  - Verify entity availability logic (marking unavailable and recovery)
- **Integration testing**:
  - Verify end-to-end integration setup in Home Assistant OS environment.
  - Confirm auto-discovery functionality and correct device/entity creation.
  - Validate correct application of sensor scaling, units, and device classes.
  - Ensure compatibility with Home Assistant's Energy Dashboard.

## Documentation
- Minimal README-style documentation for initial release:
  - Brief integration description
  - Setup and installation instructions via HACS
  - Required hardware clearly stated (Renogy Rover devices with BT-1/BT-2, Bluetooth adapter)

## Licensing
- Integration code licensed under **Apache License 2.0**, matching existing parsing library.

## Deployment and Compatibility
- Initial deployment via HACS (`custom_components/renogy_ble`)
- Explicitly supported on Home Assistant OS, latest stable version (`2025.3`)
- Compatibility with other Home Assistant installations not officially supported initially, but possible.

---

This specification provides all the necessary information and guidelines to begin immediate implementation of the Renogy Rover BLE integration for Home Assistant.

