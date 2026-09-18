"""Home Assistant MQTT discovery publisher for AirburgEmoPlus readings."""

import logging
import time
from typing import Optional

from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import Sensor, SensorInfo

from config import AppConfig
from airburg import AirburgReading

logger = logging.getLogger(__name__)


class AirburgMqttError(Exception):
    """Raised when MQTT setup or publishing fails."""


class HomeAssistantPublisher:
    """Publishes PM2.5 density and count sensors via ha_mqtt_discoverable."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._density_sensor: Optional[Sensor] = None
        self._count_sensor: Optional[Sensor] = None
        self._closed = False
        self._setup_sensors()

    def _setup_sensors(self) -> None:
        try:
            mqtt_settings = Settings.MQTT(
                host=self._config.mqtt_host,
                port=self._config.mqtt_port,
                username=self._config.mqtt_username,
                password=self._config.mqtt_password,
                use_tls=self._config.mqtt_use_tls,
                discovery_prefix=self._config.mqtt_discovery_prefix,
                state_prefix=self._config.mqtt_state_prefix,
            )

            device_info = DeviceInfo(
                name=self._config.device_name,
                identifiers=self._config.device_identifier,
            )

            density_sensor_info = SensorInfo(
                name=self._config.sensor_density_name,
                device_class="pm25",
                state_class="measurement",
                icon="mdi:molecule",
                accuracy_decimals=0,
                unit_of_measurement="μg/m³",
                unique_id=f"{self._config.device_identifier}_pm2_5_density",
                device=device_info,
            )

            count_sensor_info = SensorInfo(
                name=self._config.sensor_count_name,
                state_class="measurement",
                icon="mdi:molecule",
                unit_of_measurement="/dL",
                accuracy_decimals=0,
                unique_id=f"{self._config.device_identifier}_pm2_5_count",
                object_id=f"{self._config.device_identifier}_pm2_5_count",
                device=device_info,
            )

            self._density_sensor = Sensor(
                Settings(mqtt=mqtt_settings, entity=density_sensor_info)
            )
            self._count_sensor = Sensor(
                Settings(mqtt=mqtt_settings, entity=count_sensor_info)
            )
        except Exception as exc:
            raise AirburgMqttError(f"Failed to setup MQTT sensors: {exc}") from exc

    def __enter__(self) -> "HomeAssistantPublisher":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False

    def publish(self, reading: AirburgReading) -> None:
        """Publish the reading to both MQTT sensors."""
        if self._closed:
            raise AirburgMqttError("Publisher is closed")

        try:
            self._density_sensor.set_state(reading.density)
            self._count_sensor.set_state(reading.count)
        except Exception as exc:
            raise AirburgMqttError(f"Failed to publish reading: {exc}") from exc

    def close(self) -> None:
        """Disconnect from the MQTT broker cleanly."""
        if self._closed:
            return
        self._closed = True

        # Give the background network loop a moment to flush the last publish.
        time.sleep(0.5)

        for sensor in (self._density_sensor, self._count_sensor):
            if sensor is None:
                continue
            try:
                sensor.mqtt_client.disconnect()
                sensor.mqtt_client.loop_stop()
            except Exception:
                logger.warning("Error while disconnecting MQTT client", exc_info=True)
