"""Bluetooth LE reader for the AirburgEmoPlus PM2.5 sensor."""

import asyncio
import logging
import struct
from typing import Optional

from bleak import BleakClient
from bleak.exc import BleakDeviceNotFoundError, BleakError

from airburg import AirburgReading

logger = logging.getLogger(__name__)


class AirburgBleError(Exception):
    """Raised when BLE connection, discovery or reading fails."""


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
        self._client: Optional[BleakClient] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def __enter__(self) -> "AirburgReader":
        logger.info("Connecting to BLE device %s", self._device_addr)
        self._loop = asyncio.new_event_loop()
        try:
            self._client = BleakClient(self._device_addr)
            self._loop.run_until_complete(self._client.connect())
        except (BleakError, BleakDeviceNotFoundError, asyncio.TimeoutError) as exc:
            self._close_loop()
            raise AirburgBleError(
                f"Failed to connect to {self._device_addr}: {exc}"
            ) from exc
        except Exception as exc:
            self._close_loop()
            raise AirburgBleError(
                f"Unexpected error connecting to {self._device_addr}: {exc}"
            ) from exc
        logger.info("已连接到 BLE 设备 %s", self._device_addr)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if self._client is not None and self._client.is_connected:
                self._loop.run_until_complete(self._client.disconnect())
                logger.info("已断开 BLE 设备 %s", self._device_addr)
        except Exception:
            logger.warning("Failed to disconnect cleanly", exc_info=True)
        finally:
            self._close_loop()
        return False

    def _close_loop(self) -> None:
        """Close and cleanup the private event loop."""
        if self._loop is not None:
            try:
                self._loop.close()
            except Exception:
                logger.warning("Error while closing event loop", exc_info=True)
            finally:
                self._loop = None
        self._client = None

    def read(self) -> AirburgReading:
        """Read the warm-up characteristic, wait, then read the value characteristic."""
        if self._client is None or not self._client.is_connected:
            raise AirburgBleError("BLE client is not connected")

        try:
            return self._loop.run_until_complete(self._read())
        except (BleakError, BleakDeviceNotFoundError, asyncio.TimeoutError) as exc:
            raise AirburgBleError(
                f"Failed to read from {self._device_addr}: {exc}"
            ) from exc
        except Exception as exc:
            raise AirburgBleError(
                f"Unexpected error reading from {self._device_addr}: {exc}"
            ) from exc

    async def _read(self) -> AirburgReading:
        await self._client.read_gatt_char(self._warmup_char_uuid)

        logger.debug("Waiting %.1f seconds for sensor warm-up", self._warmup_sleep)
        await asyncio.sleep(self._warmup_sleep)

        value = await self._client.read_gatt_char(self._value_char_uuid)
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
