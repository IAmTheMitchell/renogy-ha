# Prompt 1: Project Setup & Repository Structure

We are building a Home Assistant integration for Renogy Rover BLE devices. The integration will be distributed via HACS. Start by setting up the project repository with the following structure:

    custom_components/
    └── renogy_ha/
        ├── __init__.py
        ├── manifest.json
        ├── config_flow.py   (if needed for UI configuration)
        ├── sensor.py
        ├── ble.py
        ├── const.py
        └── tests/
             ├── __init__.py
             └── test_ble.py

Tasks for this prompt:
- Create an initial `hacs.json` with basic metadata (name, version, documentation URL, and supported Home Assistant versions).
- Create an empty `__init__.py` and placeholder files for `sensor.py`, `ble.py`, and `const.py`.
- Write a minimal README that explains the integration’s purpose.
- Ensure the repository includes an Apache License 2.0 file.

The code should be minimal but correct, allowing the project to be discovered by Home Assistant.

# Prompt 2: BLE Communication Module – Basic Implementation

In this step, implement the BLE communication module (`ble.py`) that:
- Scans for Renogy Rover BLE devices (with BT-1 and BT-2 modules) by using their unique Bluetooth identifiers.
- Implements a polling function with a default interval of 60 seconds (and a configuration to set the interval between 10 and 600 seconds).

Additionally:
- Write a simple class (e.g., `RenogyBLEClient`) that initiates a BLE scan and returns a list of discovered devices.
- Include logging for start/stop of scanning.

Also, create a basic test stub in `tests/test_ble.py` that mocks BLE scanning and asserts that the scan function returns a dummy list of devices.

Ensure that the code is modular and testable.

# Prompt 3: Data Parsing & Integration of renogy-ble Library

Now integrate the `renogy-ble` parsing library in the BLE module:
- In `ble.py`, once a device is discovered, read the raw Modbus data.
- Pass the raw data to the `renogy-ble` library to parse it into a structured format.
- Ensure that numeric values are scaled appropriately according to the register map (e.g., battery voltage scaled by ×0.1, current by ×0.01, etc.).
- Write unit tests to validate that given a sample raw data payload, the parsing output matches expected sensor values.

Focus on isolating the parsing functionality so it can be reused by the sensor component.

# Prompt 4: Sensor Entity Mapping – Create Home Assistant Sensor Entities

Next, implement the Home Assistant sensor entities in `sensor.py`:
- Create sensor classes for the four groups: Battery, Solar Panel (PV), Load, and Controller Info.
- For each sensor, assign appropriate attributes:
  - Name, unit of measurement, device_class, state_class.
- Map the parsed data values to the corresponding Home Assistant sensor entities.
- Ensure that sensors have appropriate properties (e.g., battery voltage, battery current, PV power, etc.) as defined in the specification.

Write tests to verify that when given a sample parsed data dictionary, the sensor entities are instantiated with the correct values and metadata.

# Prompt 5: Device Discovery & Auto-Registration Integration

Integrate the BLE communication and sensor mapping into a cohesive workflow:
- Modify the integration’s initialization (in `__init__.py`) to start the BLE polling at the configured interval.
- When a device is discovered and parsed:
  - Register or update the device in the Home Assistant device registry with attributes (manufacturer, model, firmware version, serial/device ID).
  - Update the sensor entities with the latest values from the BLE data.
- Ensure that each sensor is assigned to the correct device and grouped logically (Battery, PV, Load, Controller Info).

Write an integration test that simulates a device being discovered and checks that:
- The device is properly registered.
- Sensor entities are created with the correct attributes.

# Prompt 6: Error Handling and Availability Logic

Implement error management in the BLE polling and sensor updating logic:
- Add a mechanism to track consecutive polling failures. After 3 consecutive failures, mark the sensor(s)/device as unavailable.
- Once a successful polling cycle occurs, mark the device as available again.
- Log all errors and recovery events clearly.

Create unit tests that simulate:
- Consecutive failures leading to the device being marked as unavailable.
- Recovery behavior once communication is restored.

# Prompt 7: End-to-End Wiring and Final Integration

Wire all components together:
- Ensure that the BLE communication module, parsing logic, sensor entity creation, and error handling are integrated.
- Modify the component setup to call each piece in sequence: start BLE polling, parse data, update Home Assistant entities, and handle errors.
- Create a main loop or scheduled task that triggers the polling and sensor updates at the configured interval.

Write a comprehensive integration test that:
- Simulates a full cycle (device discovery, data parsing, sensor update, error occurrence, and recovery).
- Verifies that the Home Assistant UI would see all entities correctly with updated states.
- Ensures no orphaned code remains and everything is fully wired.

# Prompt 8: Documentation and Final Testing

Finalize the project by:
- Updating the README with installation and configuration instructions.
- Documenting the supported hardware, configuration options (polling interval), and troubleshooting steps.
- Writing additional tests (both unit and integration) that cover edge cases such as malformed BLE data, unexpected disconnections, and recovery scenarios.

Wrap up by ensuring all tests pass and that the code adheres to Home Assistant integration best practices. Provide a final summary and integration checklist.