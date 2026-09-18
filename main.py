#!/usr/bin/env python3
"""AirburgEmoPlus BLE → MQTT bridge.

Reads PM2.5 density and particle count from an AirburgEmoPlus device over
Bluetooth Low Energy and publishes the values to an MQTT broker using Home
Assistant MQTT discovery.

All runtime configuration is read from environment variables; see config.py
for the complete list.
"""

import logging
import sys
import time

from config import AppConfig, load_config
from btle import AirburgReader, AirburgBleError
from mqtt import HomeAssistantPublisher, AirburgMqttError

logger = logging.getLogger("airburg")


def _run_once(config: AppConfig) -> bool:
    """Perform one read-publish cycle. Returns True on success."""
    publisher: HomeAssistantPublisher | None = None
    try:
        publisher = HomeAssistantPublisher(config)
        with AirburgReader(
            device_addr=config.ble_device_addr,
            service_uuid=config.ble_service_uuid,
            warmup_char_uuid=config.ble_warmup_char_uuid,
            value_char_uuid=config.ble_value_char_uuid,
            warmup_sleep=config.ble_warmup_sleep,
            density_multiplier=config.calib_density_multiplier,
            count_multiplier=config.calib_count_multiplier,
        ) as reader:
            reading = reader.read()

        logger.info('{"density": %d, "count": %d}', reading.density, reading.count)
        publisher.publish(reading)
        return True
    except AirburgBleError as exc:
        logger.error("BLE 设备不可用: %s", exc)
        if publisher is not None:
            publisher.mark_unavailable()
    except AirburgMqttError as exc:
        logger.error("MQTT 错误: %s", exc)
    except Exception:
        logger.exception("未预期的错误")
    finally:
        if publisher is not None:
            publisher.close()
    return False


def main() -> int:
    try:
        config = load_config()
    except ValueError as exc:
        logging.basicConfig(level=logging.INFO)
        logging.error("配置错误: %s", exc)
        return 2

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if config.read_interval <= 0:
        return 0 if _run_once(config) else 1

    logger.info("启动轮询，间隔 %.1f 秒", config.read_interval)
    while True:
        _run_once(config)
        logger.info("等待 %.1f 秒后再次读取...", config.read_interval)
        time.sleep(config.read_interval)


if __name__ == "__main__":
    sys.exit(main())
