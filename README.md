# Renogy BLE Integration for Home Assistant
This custom Home Assistant integration provides monitoring capabilities for Renogy devices via Bluetooth Low Energy (BLE) connection, specifically for devices with BT-1 and BT-2 modules.

## Currently Supported Devices
Tested:
- Renogy Rover
- Renogy Wanderer
- Renogy DC-DC Charger

Should work, but untested:
- Renogy Adventurer

## Features
- Automatic discovery of Renogy BLE devices
- Monitor battery status (voltage, current, temperature, charge state)
- Monitor solar panel (PV) performance metrics
- Monitor load status and statistics
- Monitor controller information
- All data exposed as Home Assistant sensors
- Energy dashboard compatible sensors
- Configurable polling interval
- Automatic error recovery

## Prerequisites
- Home Assistant instance (version 2025.3 or newer)
- Renogy device with BT-1 or BT-2 Bluetooth module
- A compatible Bluetooth adapter on your Home Assistant host device
- Bluetooth discovery enabled in Home Assistant

## Installation
This integration can be installed via HACS (Home Assistant Community Store).

1. Ensure you have [HACS](https://hacs.xyz/) installed
2. Add this repository to your HACS custom repositories:
   - Click on HACS in the sidebar
   - Click on the three dots in the top right corner
   - Select "Custom repositories"
   - Add this repository URL
   - Select "Integration" as the category
3. Search for "Renogy" in the HACS store and install it
4. Restart Home Assistant

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

## Sensors
The integration provides the following sensor groups:

### Battery Sensors
- Voltage
- Current
- Temperature
- State of Charge
- Charging Status

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

### Controller Info
- Temperature
- Device Information
- Operating Status

All sensors are automatically added to Home Assistant's Energy Dashboard where applicable.

## Troubleshooting

### Enable Debug Logging
It can be extremely helpful to enable debug logging when troubleshooting issues.
1. Open your Home Assistant instance and navigate to the [Renogy integration](https://my.home-assistant.io/redirect/integration/?domain=renogy)
2. Select "Enable debug logging"
3. Navigate to the [Home Assistant Core logs](https://my.home-assistant.io/redirect/logs/?provider=core)
4. Select the three dots in the top right and choose "Show raw logs"

### Device Not Found
1. Verify your Renogy device has a BT-1 or BT-2 module installed
2. Check that Bluetooth is enabled on your Home Assistant host
3. Ensure the device is within range (typically 10m/33ft)
4. Restart the Bluetooth adapter

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

## Support
- For bugs, please open an issue on GitHub
- Include Home Assistant logs and your device model information

## License
This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
