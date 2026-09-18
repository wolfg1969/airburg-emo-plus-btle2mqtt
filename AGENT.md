# 项目架构

AirburgEmoPlus PM2.5 BLE → MQTT 桥接服务：通过蓝牙低功耗（BLE）从
AirburgEmoPlus 传感器读取 PM2.5 浓度与颗粒计数，经校准后通过 MQTT
发现协议发布到 Home Assistant。

## 模块结构

```
main.py     入口与轮询循环
config.py   环境变量配置的解析与校验
airburg.py  AirburgReading 数据类（btle 与 mqtt 共享的类型契约）
btle.py     BLE 连接与读数（基于 bluepy）
mqtt.py     Home Assistant MQTT 发现发布（基于 ha-mqtt-discoverable）
```

## 模块职责

### main.py
- `main()` 加载配置、初始化日志，据 `READ_INTERVAL` 决定单次运行或持续轮询。
- `_run_once(config)` 执行一次「读数 → 发布」周期：先建 `HomeAssistantPublisher`，
  再用 `AirburgReader` 上下文管理器读取，最后发布。异常按
  `AirburgBleError` / `AirburgMqttError` / 其它分别记日志，`finally` 中关闭 publisher。

### config.py
- `AppConfig` frozen dataclass，所有运行期配置集中于此。
- `load_config()` 从环境变量读取并校验（MAC、UUID、数值范围、布尔、日志级别），
  任何非法值抛 `ValueError`，`main()` 据此返回退出码 2。
- 各字段带有项目默认值，覆盖默认只需设置对应环境变量。

### airburg.py
- 仅含 `AirburgReading` frozen dataclass（`density`、`count`）。
- 作为 btle.py 与 mqtt.py 之间的共享类型契约，避免循环导入。

### btle.py
- `AirburgReader` 上下文管理器：`__enter__` 连接设备，`__exit__` 断开，
  `read()` 触发暖机特性、等待、读取数值特性并解析。
- `_parse_value()` 将原始字节按偏移解析为密度与计数，乘以校准系数。
- `AirburgBleError` 封装所有 BLE 连接/读数失败。

### mqtt.py
- `HomeAssistantPublisher` 创建两个 Sensor（密度 pm2.5、计数 /dL），
  通过 ha-mqtt-discoverable 注册到 Home Assistant MQTT 发现。
- `publish(reading)` 发布两路状态；`close()` 刷新并断开 MQTT 客户端。
- `AirburgMqttError` 封装所有 MQTT 设置/发布失败。

## 数据流

```
AirburgEmoPlus --BLE--> AirburgReader.read()
                           |  AirburgReading(density, count)
                           v
                       HomeAssistantPublisher.publish()
                           |  MQTT state topic
                           v
                       Home Assistant (via MQTT discovery)
```

一次读数周期：
1. 触发暖机特性（`BLE_WARMUP_CHAR_UUID`），等待 `BLE_WARMUP_SLEEP` 秒。
2. 读取数值特性（`BLE_VALUE_CHAR_UUID`），解析 14+ 字节负载的第 10–13 字节。
3. 密度 = `(b<<8 | a) * CALIB_DENSITY_MULTIPLIER`，
   计数 = `((a&0xFF) + (b&0xFF)<<8) * CALIB_COUNT_MULTIPLIER`（负值置零）。
4. 发布到 MQTT，断开 BLE。

## 部署

Docker 单容器服务（见 `Dockerfile` / `docker-compose.yml`）：
- 多阶段构建：builder 阶段编译 vendor 的 bluepy（bluepy-helper），
  runtime 阶段仅携带运行期依赖（libglib2.0-0、bluez）。
- BLE 经 DBus 与主机 bluetoothd 通信，故 compose 使用 `network_mode: host`
  + `privileged` + 挂载 `/run/dbus/system_bus_socket`。
- 配置全部由环境变量传入，`docker-compose.yml` 列出常用变量示例。

## 关键约束

- bluepy 依赖 vendor 的 `./bluepy` 源码，构建期编译 bluepy-helper；
  运行期镜像不可复制 `bluepy/` 目录，以免遮蔽 site-packages 中已安装的包。
- `READ_INTERVAL <= 0` 表示单次运行后退出（退出码反映成功与否）；
  `> 0` 表示无限轮询。
- BLE 暖机约需 20 秒，单次读数周期含此等待；轮询间隔应远大于此。
- 校准系数（`CALIB_DENSITY_MULTIPLIER`、`CALIB_COUNT_MULTIPLIER`）必须为正。
