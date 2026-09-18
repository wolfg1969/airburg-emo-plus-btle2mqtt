# airburg-emo-plus-btle2mqtt

通过蓝牙低功耗（BLE）从 AirburgEmoPlus PM2.5 传感器读取浓度与颗粒计数，
经校准后通过 MQTT 发现协议发布到 Home Assistant 的桥接服务。

## 功能

- 连接 AirburgEmoPlus 设备，触发暖机并读取 PM2.5 数值特性。
- 解析原始 BLE 负载，按可配置的校准系数计算：
  - PM2.5 密度（μg/m³）
  - 颗粒计数（/dL）
- 通过 [ha-mqtt-discoverable] 向 Home Assistant 注册两个传感器并发布状态。
- 支持单次运行或按间隔持续轮询。
- 全部配置经环境变量传入，便于容器化部署。

[ha-mqtt-discoverable]: https://github.com/utfla/ha-mqtt-discoverable

## 架构

项目架构详见 [AGENT.md](AGENT.md)。模块结构：

```
main.py     入口与轮询循环
config.py   环境变量配置的解析与校验
airburg.py  AirburgReading 数据类（共享类型契约）
btle.py     BLE 连接与读数（基于 bluepy）
mqtt.py     Home Assistant MQTT 发现发布（基于 ha-mqtt-discoverable）
```

## 依赖

- Python 3.10+
- [bluepy]（使用仓库内 vendor 的 `./bluepy` 源码，构建期编译 bluepy-helper）
- [ha-mqtt-discoverable]
- 运行主机需具备蓝牙适配器与 BlueZ（bluetoothd），bluepy 经 DBus 与之通信。

[bluepy]: https://github.com/IanHarvey/bluepy

## 配置

全部配置通过环境变量传入，带默认值，按需覆盖。完整列表见 [config.py](config.py)。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BLE_DEVICE_ADDR` | `20:16:09:10:00:96` | 设备 BLE MAC 地址 |
| `BLE_SERVICE_UUID` | `0000fff0-...` | 服务 UUID |
| `BLE_WARMUP_CHAR_UUID` | `0000fff3-...` | 暖机特性 UUID |
| `BLE_VALUE_CHAR_UUID` | `0000fff2-...` | 数值特性 UUID |
| `BLE_WARMUP_SLEEP` | `20` | 暖机等待秒数（≥0） |
| `CALIB_DENSITY_MULTIPLIER` | `1.265` | 密度校准系数（>0） |
| `CALIB_COUNT_MULTIPLIER` | `2.56` | 计数校准系数（>0） |
| `MQTT_BROKER_HOST` | `localhost` | MQTT broker 主机 |
| `MQTT_BROKER_PORT` | `1883` | MQTT broker 端口（1–65535） |
| `MQTT_USERNAME` | _（空）_ | MQTT 用户名（可选） |
| `MQTT_PASSWORD` | _（空）_ | MQTT 密码（可选） |
| `MQTT_USE_TLS` | `false` | 是否启用 TLS |
| `MQTT_DISCOVERY_PREFIX` | `homeassistant` | 发现前缀 |
| `MQTT_STATE_PREFIX` | `hmd` | 状态前缀 |
| `DEVICE_NAME` | `AirburgEmoPlus` | 设备名称 |
| `DEVICE_IDENTIFIER` | `airburg_emo_plus` | 设备唯一标识 |
| `SENSOR_DENSITY_NAME` | `PM2.5` | 密度传感器名称 |
| `SENSOR_COUNT_NAME` | `PM2.5 Count` | 计数传感器名称 |
| `READ_INTERVAL` | `0` | 轮询间隔秒数；`<=0` 单次运行后退出 |
| `LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |

## 运行

### Docker（推荐）

```bash
# 按需修改 docker-compose.yml 中的 BLE_DEVICE_ADDR、MQTT_BROKER_HOST 等
docker compose up -d --build
```

容器需访问主机蓝牙适配器：compose 使用 `network_mode: host` + `privileged`
并挂载 `/run/dbus/system_bus_socket`。

查看日志：

```bash
docker compose logs -f
```

### 本地运行

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
BLE_DEVICE_ADDR=xx:xx:xx:xx:xx:xx MQTT_BROKER_HOST=... python main.py
```

## 树内 vendor 说明

`bluepy/` 为树内 vendor 的 bluepy 源码，构建期会编译 bluepy-helper。
该目录不应复制进运行期镜像，以免遮蔽 site-packages 中已安装的 bluepy。

## 许可证

[MIT](LICENSE)
