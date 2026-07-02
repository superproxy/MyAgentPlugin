#!/bin/bash
echo "========================================"
echo "  MyAgentPlugin Install Script"
echo "========================================"
echo ""

echo "[1/2] List available plugins..."
python3 scripts/agentctl.py plugin list
echo ""

echo "[2/2] Setup: generate configs + install all plugins + sync to IDEs..."
python3 scripts/agentctl.py setup
echo ""

echo "========================================"
echo "  Install Complete!"
echo "========================================"
echo ""
echo "Tip: To install more plugins, run:"
echo "  python3 scripts/agentctl.py plugin install <plugin-file>"
echo ""

# 单独同步某个 IDE（可选）:
#python3 scripts/agentctl.py sync -i Agents -f
#python3 scripts/agentctl.py sync -i Cursor -f
#python3 scripts/agentctl.py sync -i Claude -f
#python3 scripts/agentctl.py sync -i TraeCN -f
#python3 scripts/agentctl.py sync -i Codex -f
#python3 scripts/agentctl.py sync -i OpenCode -f
#python3 scripts/agentctl.py sync -i IDEA -f
#python3 scripts/agentctl.py sync -i TraeSoloCN -f
