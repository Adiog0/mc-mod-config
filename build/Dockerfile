FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir pyinstaller PyQt6 tomlkit pyjson5 pyyaml

WORKDIR /build

ENTRYPOINT ["pyinstaller", "--noconfirm", "--log-level=WARN", "build/build.spec"]
