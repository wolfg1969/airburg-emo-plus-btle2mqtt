# airburg-emo-plus-btle2mqtt

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://docker.com)
[![Home Assistant](https://img.shields.io/badge/home%20assistant-%2341BDF5.svg?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)

通过蓝牙低功耗（BLE）从 AirburgEmoPlus PM2.5 传感器读取浓度与颗粒计数，
经校准后通过 MQTT 发现协议发布到 Home Assistant 的桥接服务。

> 设备连接不上时，自动向 MQTT 发送「离线」状态，Home Assistant 中将显示传感器为不可用。

## 功能

- 连接 AirburgEmoPlus 设备，触发暖机并读取 PM2.5 数值特性。
- 解析原始 BLE 负载，按可配置的校准系数计算：
  - PM2.5 密度（μg/m³）
  - 颗粒计数（/dL）
- 通过 [ha-mqtt-discoverable] 向 Home Assistant 注册两个传感器并发布状态。
- 支持单次运行或按间隔持续轮询。
- BLE 连接失败时自动发布 MQTT 离线状态，Home Assistant 中显示传感器为不可用。
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

## 前提与依赖

### 硬件需求
- Raspberry Pi（内置蓝牙适配器）或支持 BLE 的 Linux 主机 + 蓝牙 4.0+ 适配器。
- 蓝牙适配器必须运行 **BlueZ**（`bluetoothd`），bluepy 通过 DBus 与其通信。
- 容器部署需要挂载 `/run/dbus/system_bus_socket`，因此 host 网络模式下需 `privileged`。

### 软件依赖与 Python 包
- **Python 3.10+**（Docker 镜像使用 Python 3.13.15‑slim）
- **[bluepy]**（使用仓库内 vendor 的 `./bluepy` 源码，构建期编译 bluepy‑helper）
- **[ha‑mqtt‑discoverable]**（Home Assistant MQTT 发现客户端）

[bluepy]: https://github.com/IanHarvey/bluepy

## 配置

全部配置通过环境变量传入，带默认值，按需覆盖。完整列表见 [config.py](config.py)。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BLE_DEVICE_ADDR` | `20:16:09:10:00:96` | 设备 BLE MAC 地址 |
| `BLE_SERVICE_UUID` | `0000fff0‑0000‑1000‑8000‑00805f9b34fb` | 服务 UUID |
| `BLE_WARMUP_CHAR_UUID` | `0000fff3‑0000‑1000‑8000‑00805f9b34fb` | 暖机特性 UUID |
| `BLE_VALUE_CHAR_UUID` | `0000fff2‑0000‑1000‑8000‑00805f9b34fb` | 数值特性 UUID |
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
| `READ_INTERVAL` | `0` | 轮询间隔秒数；`≤0` 单次运行后退出 |
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

`bluepy/` 为树内 vendor 的 bluepy 源码，构建期会编译 bluepy‑helper。
该目录**不应**复制进运行期镜像（见 `Dockerfile` `COPY` 语句），避免遮蔽 site‑packages 中已安装的 bluepy。

## 常见问题

**Home Assistant 侧传感器显示为不可用，即使设备在线：**
- BLE 连接失败时会发布 `offline` 状态。成功读数后会立即置 `online`。
- 如果传感器持续不可用，检查日志是否出现 `BLE 设备不可用` 错误。
- 确保 `docker‑compose.yml` 中的 `BLE_DEVICE_ADDR` 与你的设备 MAC 一致。

**Docker 启动报错 `dbus` / `bluetoothd` 连接失败：**
- 容器必须挂载 `/run/dbus/system_bus_socket` 并使用 `privileged`。
- 主机的蓝牙适配器需运行 `systemctl start bluetooth`。

**读数异常（密度或计数明显偏差）：**
- 可通过 `CALIB_DENSITY_MULTIPLIER` 与 `CALIB_COUNT_MULTIPLIER` 调整校准系数。
- 原始解析逻辑见 `btle.py` 的 `_parse_value()`。

## 许可证

[MIT](LICENSE) © 2026 wolfg1969
