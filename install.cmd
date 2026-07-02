@echo off
chcp 65001 > nul
echo ========================================
echo   MyAgentPlugin Install Script
echo ========================================
echo.

echo [1/2] List available plugins...
python scripts\agentctl.py plugin list
echo.

echo [2/2] Setup: generate configs + install all plugins + sync to IDEs...
python scripts\agentctl.py setup
echo.

echo ========================================
echo   Install Complete!
echo ========================================
echo.
echo Tip: To install more plugins, run:
echo   python scripts\agentctl.py plugin install ^<plugin-file^>
echo.
@REM 单独同步某个 IDE（可选）:
@REM python scripts\agentctl.py sync -i trae-cn -f
@REM python scripts\agentctl.py sync -i Cursor -f
@REM python scripts\agentctl.py sync -i Codex -f
@REM python scripts\agentctl.py sync -i OpenCode -f
@REM python scripts\agentctl.py sync -i IDEA -f
@REM python scripts\agentctl.py sync -i trae-solo-cn -f
