"""Bluetooth LE reader for the AirburgEmoPlus PM2.5 sensor."""

import logging
import struct
import time
from typing import Optional

from bluepy import btle as bluepy_btle

from airburg import AirburgReading

logger = logging.getLogger(__name__)


class AirburgBleError(Exception):
    """Raised when BLE connection, discovery or reading fails."""


class _NoopDelegate(bluepy_btle.DefaultDelegate):
    """Default delegate that ignores notifications."""


class AirburgReader:
    """Context manager that connects to the AirburgEmoPlus and reads values."""

    def __init__(
        self,
        device_addr: str,
        service_uuid: str,
        warmup_char_uuid: str,
        value_char_uuid: str,
        warmup_sleep: float = 20.0,
        density_multiplier: float = 1.265,
        count_multiplier: float = 2.56,
    ) -> None:
        self._device_addr = device_addr
        self._service_uuid = service_uuid
        self._warmup_char_uuid = warmup_char_uuid
        self._value_char_uuid = value_char_uuid
        self._warmup_sleep = warmup_sleep
        self._density_multiplier = density_multiplier
        self._count_multiplier = count_multiplier
        self._peripheral: Optional[bluepy_btle.Peripheral] = None

    def __enter__(self) -> "AirburgReader":
        logger.info("Connecting to BLE device %s", self._device_addr)
        try:
            self._peripheral = bluepy_btle.Peripheral().withDelegate(_NoopDelegate())
            self._peripheral.connect(self._device_addr)
        except bluepy_btle.BTLEException as exc:
            raise AirburgBleError(
                f"Failed to connect to {self._device_addr}: {exc}"
            ) from exc
        logger.info("已连接到 BLE 设备 %s", self._device_addr)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        peripheral = self._peripheral
        self._peripheral = None
        if peripheral is not None:
            device_addr = getattr(peripheral, "addr", "unknown")
            try:
                peripheral.disconnect()
                logger.info("已断开 BLE 设备 %s", device_addr)
            except bluepy_btle.BTLEException:
                logger.warning("Failed to disconnect cleanly", exc_info=True)
        return False

    def read(self) -> AirburgReading:
        """Read the warm-up characteristic, wait, then read the value characteristic."""
        if self._peripheral is None:
            raise AirburgBleError("BLE peripheral is not connected")

        try:
            service = self._peripheral.getServiceByUUID(self._service_uuid)

            warmup_chars = service.getCharacteristics(forUUID=self._warmup_char_uuid)
            if not warmup_chars:
                raise AirburgBleError(
                    f"Warm-up characteristic {self._warmup_char_uuid} not found"
                )
            warmup_chars[0].read()

            logger.debug("Waiting %.1f seconds for sensor warm-up", self._warmup_sleep)
            time.sleep(self._warmup_sleep)

            value_chars = service.getCharacteristics(forUUID=self._value_char_uuid)
            if not value_chars:
                raise AirburgBleError(
                    f"Value characteristic {self._value_char_uuid} not found"
                )
            value = value_chars[0].read()
            reading = _parse_value(
                value,
                self._density_multiplier,
                self._count_multiplier,
            )
            logger.info(
                "读到数值：density=%d, count=%d",
                reading.density,
                reading.count,
            )
            return reading
        except bluepy_btle.BTLEException as exc:
            raise AirburgBleError(
                f"Failed to read from {self._device_addr}: {exc}"
            ) from exc


def _parse_value(
    value: bytes,
    density_multiplier: float,
    count_multiplier: float,
) -> AirburgReading:
    """Parse the raw characteristic bytes into density and count."""
    if len(value) < 14:
        raise AirburgBleError(f"Value payload too short: {len(value)} bytes")

    c1 = bytes(value[10:12])
    c2 = bytes(value[12:14])

    a = struct.unpack("B", c1[1:])[0]
    b = struct.unpack("B", c1[:1])[0]
    density = int((b << 8) | (a & 0xFF)) * density_multiplier

    a = struct.unpack("B", c2[1:])[0]
    b = struct.unpack("B", c2[:1])[0]
    count = (int((a & 0xFF) << 0) + int((b & 0xFF) << 8)) * count_multiplier
    if count < 0:
        count = 0

    return AirburgReading(density=int(density), count=int(count))
