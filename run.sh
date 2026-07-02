#!/usr/bin/env bash
# MyAgentPlugin 配置工具 Web UI 启动脚本 (Linux/macOS)
# 用法: ./run.sh [port]

set -e
PORT="${1:-5000}"

# 切到项目根目录（脚本所在目录）
cd "$(dirname "$0")"

# 检查 Python
if ! command -v python3 >/dev/null 2>&1; then
    if ! command -v python >/dev/null 2>&1; then
        echo "[ERROR] 未找到 Python，请先安装 Python 3.8+"
        exit 1
    fi
    PY=python
else
    PY=python3
fi

# 检查依赖（缺失则提示安装）
if ! $PY -c "import flask, yaml, requests" >/dev/null 2>&1; then
    echo "[INFO] 缺少依赖，正在安装 flask pyyaml requests ..."
    $PY -m pip install flask pyyaml requests || {
        echo "[ERROR] 依赖安装失败，请手动执行: $PY -m pip install flask pyyaml requests"
        exit 1
    }
fi

echo "[INFO] 启动配置工具: http://127.0.0.1:${PORT}"
exec $PY tools/config_server.py --port "$PORT"
