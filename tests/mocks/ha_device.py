"""Mock implementations of Home Assistant device classes for testing."""

from dataclasses import dataclass, field
from typing import Optional, Set, Tuple


@dataclass
class DeviceInfo:
    """Device information used in entity registry."""

    identifiers: Set[Tuple[str, str]] = field(default_factory=set)
    connections: Set[Tuple[str, str]] = field(default_factory=set)
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    name: Optional[str] = None
    sw_version: Optional[str] = None
    hw_version: Optional[str] = None
    via_device: Optional[Tuple[str, str]] = None
    configuration_url: Optional[str] = None
    entry_type: Optional[str] = None
    suggested_area: Optional[str] = None
