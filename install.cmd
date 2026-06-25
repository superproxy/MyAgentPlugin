@echo off
chcp 65001 > nul
echo ========================================
echo   MyAgentPlugin Install Script
echo ========================================
echo.

echo [1/11] List available plugins...
python scripts\plugin-manager.py list
echo.

echo [2/11] Preparing .agents/skills directory...
if not exist ".agents" mkdir ".agents"
if not exist ".agents\skills" mkdir ".agents\skills"
echo.

echo [3/11] Install core plugin...
if exist "agents\plugins\core.plugin.json" (
    python scripts\plugin-manager.py install agents\plugins\core.plugin.json
)
echo.

echo [4/11] Install computer-use plugin...
if exist "agents\plugins\computer-use.plugin.json" (
    python scripts\plugin-manager.py install agents\plugins\computer-use.plugin.json
)
echo.

echo [5/11] Install browser-use plugin...
if exist "agents\plugins\browser-use.plugin.json" (
    python scripts\plugin-manager.py install agents\plugins\browser-use.plugin.json
)
echo.

echo [6/11] Install frontend-design plugin...
if exist "agents\plugins\frontend-design.plugin.json" (
    python scripts\plugin-manager.py install agents\plugins\frontend-design.plugin.json
)
echo.

echo "[6/11] Install enhance-dev-design plugin..."
if [ -f "agents/plugins/enhance-dev.json" ]; then
    python3 scripts/plugin-manager.py install agents\plugins\enhance-dev.json
fi
echo.

echo [7/11] Install productivity plugin...
if exist "agents\plugins\productivity.plugin.json" (
    python scripts\plugin-manager.py install agents\plugins\productivity.plugin.json
)
echo.

echo [8/11] Install dev-tools plugin...
if exist "agents\plugins\dev-tools.plugin.json" (
    python scripts\plugin-manager.py install agents\plugins\dev-tools.plugin.json
)
echo.

echo [9/11] Install mattpocock plugin...
if exist "agents\plugins\mattpocock.plugin.json" (
    python scripts\plugin-manager.py install agents\plugins\mattpocock.plugin.json
)
echo.

echo [10/11] Install superpowers plugin...
if exist "agents\plugins\superpowers.plugin.json" (
    python scripts\plugin-manager.py install agents\plugins\superpowers.plugin.json
)
echo.

echo [11/11] Initialize environment and sync to IDEs...
python scripts\init-env.py -a Generate
python scripts\init-ide.py -i All -f
echo.

echo ========================================
echo   Install Complete!
echo ========================================
echo.
echo Tip: To install more plugins, run:
echo   python scripts\plugin-manager.py install ^<plugin-file^>
echo.
@REM python scripts\init-ide.py -i trae-cn -f
@REM python scripts\init-ide.py -i Cursor -f
@REM python scripts\init-ide.py -i Codex -f
@REM python scripts\init-ide.py -i OpenCode -f
@REM python scripts\init-ide.py -i IDEA -f
@REM python scripts\init-ide.py -i trae-solo-cn -f
