# 构建阶段：安装 bleak 及其可选编译依赖
FROM python:3.13.15-slim AS builder

# 使用清华大学 Debian 镜像加速 apt
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
        /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
        /etc/apt/sources.list.d/debian.sources

# bleak 在 Linux 通过 dbus-fast 与 BlueZ 通信；ARM 平台可能需编译 dbus-fast
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc make pkg-config \
        libdbus-1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先拷贝 dependencies 定义，利用 Docker layer 缓存
COPY requirements.txt ./

# 安装到系统 Python（不需要 venv，容器本身就是隔离的）
# 使用清华大学 PyPI 镜像加速
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r requirements.txt

FROM python:3.13.15-slim AS runtime

# 使用清华大学 Debian 镜像加速 apt
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
        /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' \
        /etc/apt/sources.list.d/debian.sources

# bleak 运行期需要 BlueZ/dbus 的客户端库
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bluez \
        dbus \
        libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin /usr/local/bin

COPY main.py config.py airburg.py btle.py mqtt.py ./

CMD ["python", "main.py"]
