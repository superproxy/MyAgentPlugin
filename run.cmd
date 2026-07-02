@echo off
REM MyAgentPlugin 配置工具 Web UI 启动脚本 (Windows)
REM 用法: run.cmd [port]

setlocal
set PORT=%1
if "%PORT%"=="" set PORT=5000

cd /d "%~dp0"

REM 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.8+
    exit /b 1
)

REM 检查依赖（缺失则提示安装）
python -c "import flask, yaml, requests" 2>nul
if errorlevel 1 (
    echo [INFO] 缺少依赖，正在安装 flask pyyaml requests ...
    python -m pip install flask pyyaml requests
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败，请手动执行: python -m pip install flask pyyaml requests
        exit /b 1
    )
)

echo [INFO] 启动配置工具: http://127.0.0.1:%PORT%
python tools\config_server.py --port %PORT%
endlocal
