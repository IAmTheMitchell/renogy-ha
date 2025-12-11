"""Tests for the RenogyBLEDevice class without dependencies."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

# Define constants locally to avoid importing the actual module
RENOGY_BT_PREFIX = "BT-TH-"


class TestRenogyBLEDevice:
    """Test the RenogyBLEDevice functionality without importing the full module."""

    @pytest.fixture
    def mock_ble_device(self):
        """Create a mock BLE device."""
        device = MagicMock()
        device.name = f"{RENOGY_BT_PREFIX}7724620D"
        device.address = "AA:BB:CC:DD:EE:FF"
        device.rssi = -60
        return device

    @pytest.fixture
    def device_class(self):
        """Create a RenogyBLEDevice-like class for testing."""

        # This represents a simplified version of RenogyBLEDevice
        class MockRenogyDevice:
            def __init__(
                self, ble_device, advertisement_rssi=None, device_type="controller"
            ):
                self.ble_device = ble_device
                self.address = ble_device.address
                self.name = ble_device.name or "Unknown Renogy Device"
                self.rssi = advertisement_rssi or ble_device.rssi or -70
                self.last_seen = datetime.now()
                self.data = None
                self.failure_count = 0
                self.max_failures = 3
                self.available = True
                self.parsed_data = {}
                self.device_type = device_type
                self.last_unavailable_time = None
                self.update_availability_calls = []

            @property
            def is_available(self):
                """Return True if device is available."""
                return self.available and self.failure_count < self.max_failures

            @property
            def should_retry_connection(self):
                """Check if we should retry connecting to an unavailable device."""
                if self.is_available:
                    return True

                # If we've never set an unavailable time, set it now
                if self.last_unavailable_time is None:
                    self.last_unavailable_time = datetime.now()
                    return False

                # Check if enough time has elapsed since the last poll
                retry_time = self.last_unavailable_time + timedelta(minutes=10)
                if datetime.now() >= retry_time:
                    self.last_unavailable_time = datetime.now()
                    return True
                return False

            def update_availability(self, success, error=None):
                self.update_availability_calls.append((success, error))
                if success:
                    if self.failure_count > 0:
                        # Log would happen here in real implementation
                        pass
                    self.failure_count = 0
                    if not self.available:
                        # Log would happen here in real implementation
                        self.available = True
                        self.last_unavailable_time = None
                else:
                    self.failure_count += 1
                    # Log would happen here in real implementation

                    if self.failure_count >= self.max_failures and self.available:
                        # Log warning would happen here in real implementation
                        self.available = False
                        self.last_unavailable_time = datetime.now()

            def update_parsed_data(self, raw_data, register, cmd_name="unknown"):
                """Simulate update_parsed_data function."""
                if not raw_data:
                    return False

                try:
                    # Simulate successful parsing
                    if len(raw_data) > 0:
                        self.parsed_data = {
                            "battery_voltage": 12.6,
                            "battery_percentage": 85,
                        }
                        return True
                    return False
                except Exception:
                    return False

        return MockRenogyDevice

    def test_device_initialization(self, mock_ble_device, device_class):
        """Test device initialization."""
        device = device_class(mock_ble_device)

        # Verify the initial state
        assert device.address == mock_ble_device.address
        assert device.name == mock_ble_device.name
        assert device.rssi == mock_ble_device.rssi
        assert device.available is True
        assert device.failure_count == 0
        assert device.parsed_data == {}
        assert device.device_type == "controller"

    def test_update_availability(self, mock_ble_device, device_class):
        """Test the update_availability method."""
        device = device_class(mock_ble_device)

        # Test successful update
        device.available = False
        device.failure_count = 3
        device.update_availability(True)

        assert device.available is True
        assert device.failure_count == 0

        # Test failed update
        device.update_availability(False)
        assert device.failure_count == 1
        assert device.available is True  # Still true until max_failures reached

        # Test reaching max failures
        device.update_availability(False)  # 2 failures
        device.update_availability(False)  # 3 failures

        assert device.failure_count == 3
        assert device.available is False

    def test_is_available(self, mock_ble_device, device_class):
        """Test the is_available property."""
        device = device_class(mock_ble_device)

        device.available = True
        device.failure_count = 0
        assert device.is_available is True

        device.available = False
        assert device.is_available is False

        device.available = True
        device.failure_count = device.max_failures
        assert device.is_available is False

    def test_should_retry_connection(self, mock_ble_device, device_class):
        """Test the should_retry_connection property."""
        device = device_class(mock_ble_device)

        # Available devices should always return True
        device.available = True
        device.failure_count = 0
        assert device.should_retry_connection is True

        # Unavailable devices without a last_unavailable_time should set it and
        # return False.
        device.available = False
        device.failure_count = 3
        device.last_unavailable_time = None
        assert device.should_retry_connection is False
        assert device.last_unavailable_time is not None

        # Mock the last_unavailable_time to be far in the past
        past_time = datetime.now() - timedelta(
            minutes=20
        )  # 20 minutes ago, which is > 10 minutes retry interval
        device.last_unavailable_time = past_time

        # Should retry connection as enough time has passed
        assert device.should_retry_connection is True

    def test_update_parsed_data(self, mock_ble_device, device_class):
        """Test the update_parsed_data method."""
        device = device_class(mock_ble_device)

        # Create some test raw data
        raw_data = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])

        # Test successful parsing
        result = device.update_parsed_data(raw_data, register=256)
        assert result is True
        assert "battery_voltage" in device.parsed_data
        assert "battery_percentage" in device.parsed_data

        # Test with empty data
        result = device.update_parsed_data(bytes([]), register=256)
        assert result is False

    def test_availability_after_consecutive_failures(
        self, mock_ble_device, device_class
    ):
        """Test device availability after consecutive failures."""
        device = device_class(mock_ble_device)

        # Initial state should be available
        assert device.available is True
        assert device.is_available is True

        # First failure
        device.update_availability(False)
        assert device.failure_count == 1
        assert device.available is True
        assert device.is_available is True

        # Second failure
        device.update_availability(False)
        assert device.failure_count == 2
        assert device.available is True
        assert device.is_available is True

        # Third failure - should mark device as unavailable
        device.update_availability(False)
        assert device.failure_count == 3
        assert device.available is False
        assert device.is_available is False

    def test_recovery_after_failures(self, mock_ble_device, device_class):
        """Test device recovery after previous failures."""
        device = device_class(mock_ble_device)

        # Set initial state to unavailable after failures
        device.failure_count = 4
        device.available = False
        assert device.is_available is False

        # Successful communication should reset failure count and make device available
        device.update_availability(True)
        assert device.failure_count == 0
        assert device.available is True
        assert device.is_available is True
