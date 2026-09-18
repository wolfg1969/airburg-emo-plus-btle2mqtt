# 构建阶段：编译 vendor 的 bluepy（把 bluez 编译为 bluepy-helper）
FROM python:3.13.15-slim AS builder

# bluepy 编译 bluepy-helper 需要的构建依赖（pkg-config + glib 头文件 + bluetooth 头文件）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc make pkg-config \
        libglib2.0-dev \
        libbluetooth-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先拷贝 dependencies 定义，利用 Docker layer 缓存
COPY requirements.txt ./
COPY bluepy ./bluepy

# 安装到系统 Python（不需要 venv，容器本身就是隔离的）
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13.15-slim AS runtime

# bluepy 运行期需要 BlueZ/dbus 的客户端库
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 bluez \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin /usr/local/bin

# 只复制应用代码（不复制 bluepy/，避免遮蔽 site-packages 中已安装的 bluepy）
COPY main.py config.py airburg.py btle.py mqtt.py ./

CMD ["python", "main.py"]