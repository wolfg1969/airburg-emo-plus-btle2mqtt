"""Environment-variable based configuration for the AirburgEmoPlus bridge."""

import os
import re
import uuid
from dataclasses import dataclass
from typing import Mapping, Optional

_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration parsed from environment variables."""

    ble_device_addr: str
    ble_service_uuid: str
    ble_warmup_char_uuid: str
    ble_value_char_uuid: str
    ble_warmup_sleep: float
    calib_density_multiplier: float
    calib_count_multiplier: float

    mqtt_host: str
    mqtt_port: int
    mqtt_username: Optional[str]
    mqtt_password: Optional[str]
    mqtt_use_tls: bool
    mqtt_discovery_prefix: str
    mqtt_state_prefix: str

    device_name: str
    device_identifier: str
    sensor_density_name: str
    sensor_count_name: str

    log_level: str


def _parse_mac(value: str) -> str:
    value = value.strip()
    if not _MAC_RE.match(value):
        raise ValueError(f"Invalid BLE MAC address: {value!r}")
    return value.lower()


def _parse_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value.strip())).lower()
    except ValueError as exc:
        raise ValueError(f"Invalid UUID: {value!r}") from exc


def _parse_float(
    value: str,
    name: str,
    *,
    min_value: Optional[float] = None,
    must_be_positive: bool = False,
) -> float:
    try:
        parsed = float(value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc
    if must_be_positive and parsed <= 0:
        raise ValueError(f"{name} must be > 0, got {parsed}")
    if min_value is not None and parsed < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {parsed}")
    return parsed


def _parse_int(
    value: str,
    name: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc
    if min_value is not None and parsed < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {parsed}")
    if max_value is not None and parsed > max_value:
        raise ValueError(f"{name} must be <= {max_value}, got {parsed}")
    return parsed


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "on"}


def _parse_nonempty(value: str, name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} cannot be empty")
    return value


def _parse_log_level(value: str) -> str:
    level = value.strip().upper()
    if level not in _LOG_LEVELS:
        raise ValueError(
            f"LOG_LEVEL must be one of {_LOG_LEVELS}, got {value!r}"
        )
    return level


def load_config(environ: Optional[Mapping[str, str]] = None) -> AppConfig:
    """Load and validate configuration from environment variables."""
    env = environ if environ is not None else os.environ

    return AppConfig(
        ble_device_addr=_parse_mac(
            env.get("BLE_DEVICE_ADDR", "20:16:09:10:00:96")
        ),
        ble_service_uuid=_parse_uuid(
            env.get("BLE_SERVICE_UUID", "0000fff0-0000-1000-8000-00805f9b34fb")
        ),
        ble_warmup_char_uuid=_parse_uuid(
            env.get("BLE_WARMUP_CHAR_UUID", "0000fff3-0000-1000-8000-00805f9b34fb")
        ),
        ble_value_char_uuid=_parse_uuid(
            env.get("BLE_VALUE_CHAR_UUID", "0000fff2-0000-1000-8000-00805f9b34fb")
        ),
        ble_warmup_sleep=_parse_float(
            env.get("BLE_WARMUP_SLEEP", "20"),
            "BLE_WARMUP_SLEEP",
            min_value=0,
        ),
        calib_density_multiplier=_parse_float(
            env.get("CALIB_DENSITY_MULTIPLIER", "1.265"),
            "CALIB_DENSITY_MULTIPLIER",
            must_be_positive=True,
        ),
        calib_count_multiplier=_parse_float(
            env.get("CALIB_COUNT_MULTIPLIER", "2.56"),
            "CALIB_COUNT_MULTIPLIER",
            must_be_positive=True,
        ),
        mqtt_host=_parse_nonempty(
            env.get("MQTT_BROKER_HOST", "localhost"), "MQTT_BROKER_HOST"
        ),
        mqtt_port=_parse_int(
            env.get("MQTT_BROKER_PORT", "1883"),
            "MQTT_BROKER_PORT",
            min_value=1,
            max_value=65535,
        ),
        mqtt_username=env.get("MQTT_USERNAME") or None,
        mqtt_password=env.get("MQTT_PASSWORD") or None,
        mqtt_use_tls=_parse_bool(env.get("MQTT_USE_TLS", "false")),
        mqtt_discovery_prefix=_parse_nonempty(
            env.get("MQTT_DISCOVERY_PREFIX", "homeassistant"),
            "MQTT_DISCOVERY_PREFIX",
        ),
        mqtt_state_prefix=_parse_nonempty(
            env.get("MQTT_STATE_PREFIX", "hmd"), "MQTT_STATE_PREFIX"
        ),
        device_name=_parse_nonempty(
            env.get("DEVICE_NAME", "AirburgEmoPlus"), "DEVICE_NAME"
        ),
        device_identifier=_parse_nonempty(
            env.get("DEVICE_IDENTIFIER", "airburg_emo_plus"), "DEVICE_IDENTIFIER"
        ),
        sensor_density_name=_parse_nonempty(
            env.get("SENSOR_DENSITY_NAME", "PM2.5"), "SENSOR_DENSITY_NAME"
        ),
        sensor_count_name=_parse_nonempty(
            env.get("SENSOR_COUNT_NAME", "PM2.5 Count"), "SENSOR_COUNT_NAME"
        ),
        log_level=_parse_log_level(env.get("LOG_LEVEL", "INFO")),
    )
