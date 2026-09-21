"""Hardware adapters.

All adapters are read-only with respect to the person wearing the sensor. See
``hardware/README.md`` for the physical side and ``security/threat-model.md``
for why the read-only property is treated as a safety boundary rather than a
limitation.

Optional dependencies (``pyserial``, ``pylsl``, ``bleak``) are imported inside
each driver, so this package imports cleanly on a machine that has none of them.
"""

from __future__ import annotations

from .base import (
    ChannelSpec,
    DeviceCapabilities,
    DeviceDriver,
    DeviceStatus,
    Sample,
    SampleQuality,
)
from .ble_heart_rate import (
    HEART_RATE_MEASUREMENT_UUID,
    HEART_RATE_SERVICE_UUID,
    BleHeartRateDevice,
    hrv_index_from_rmssd,
    parse_heart_rate_measurement,
    rmssd_ms,
)
from .lsl_device import LslInletDevice
from .registry import available, build, build_all, build_reported, describe_all, get, register
from .replay import ReplayDevice, write_recording
from .serial_bridge import SerialBridgeDevice, parse_line
from .simulated import SimulatedCardioDevice

__all__ = [
    "BleHeartRateDevice",
    "ChannelSpec",
    "DeviceCapabilities",
    "DeviceDriver",
    "DeviceStatus",
    "HEART_RATE_MEASUREMENT_UUID",
    "HEART_RATE_SERVICE_UUID",
    "LslInletDevice",
    "ReplayDevice",
    "Sample",
    "SampleQuality",
    "SerialBridgeDevice",
    "SimulatedCardioDevice",
    "available",
    "build",
    "build_all",
    "build_reported",
    "describe_all",
    "get",
    "hrv_index_from_rmssd",
    "parse_heart_rate_measurement",
    "parse_line",
    "register",
    "rmssd_ms",
    "write_recording",
]
