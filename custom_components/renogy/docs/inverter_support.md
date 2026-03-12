# Renogy Home Assistant Integration: Inverter Support

## Overview
This integration allows Home Assistant to connect to Renogy inverters over Bluetooth Low Energy (BLE), enabling real-time monitoring and control of inverter data.

## Supported Inverter Models
- RIV1220PU and compatible Renogy inverters with BLE support

## Features
- Automatic discovery of Renogy inverters via BLE
- Entity creation for inverter main data, load data, device ID, and model
- Periodic polling and real-time updates
- Unified experience with other Renogy BLE devices (controllers, shunts, DCC)

## Setup Instructions
1. Install the integration via HACS or copy the `renogy` custom component to your Home Assistant `custom_components` directory.
2. Ensure your Renogy inverter is powered on and in range.
3. Add the integration in Home Assistant. The inverter will be auto-discovered if BLE is enabled.
4. Entities for inverter data will be created automatically.

## Entities Created
- `sensor.inverter_main_data`
- `sensor.inverter_load_data`
- `sensor.inverter_device_id`
- `sensor.inverter_model`

## Troubleshooting
- Ensure your inverter is powered on and within BLE range.
- If entities are not created, check Home Assistant logs for errors.
- For advanced debugging, enable debug logging for `custom_components.renogy`.

## Notes
- Inverter support requires the latest `renogy-ble` library.
- Only basic inverter sensors are included by default. For advanced sensors, extend the sensor mapping in `sensor.py`.

---
For more details, see the main integration documentation or contact the project maintainers.
