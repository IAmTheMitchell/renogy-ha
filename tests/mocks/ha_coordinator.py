"""Mock implementations of Home Assistant update coordinator for testing."""


class CoordinatorEntity:
    """Mock implementation of a coordinator entity."""

    def __init__(self, coordinator):
        """Initialize the coordinator entity."""
        self.coordinator = coordinator
        self._attr_unique_id = None
        self._attr_name = None
        self._attr_device_info = None
        self.entity_description = None
        self.hass = None
        self._category = None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    def async_write_ha_state(self) -> None:
        """Write the state to Home Assistant."""
        # Mock implementation that does nothing
        pass


class ActiveBluetoothDataUpdateCoordinator:
    """Mock implementation of ActiveBluetoothDataUpdateCoordinator."""

    def __class_getitem__(cls, _item):
        """Support subscription for typing in tests."""
        return cls

    def __init__(self, hass, logger, address, **kwargs):
        """Initialize the coordinator."""
        self.hass = hass
        self.logger = logger
        self.address = address
        self.data = {}
        self.device = None
        self.last_update_success = True
        self._listeners = []

    def async_add_listener(self, update_callback, context=None):
        """Add a listener for update."""
        self._listeners.append(update_callback)

    def async_update_listeners(self):
        """Update all registered listeners."""
        for update_callback in self._listeners:
            update_callback()

    async def async_request_refresh(self):
        """Request a manual refresh."""
        pass

    def async_start(self):
        """Start polling."""

        def _unsub():
            pass

        return _unsub

    def async_stop(self):
        """Stop polling."""
        pass
