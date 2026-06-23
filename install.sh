#!/bin/bash
echo "========================================"
echo "  MyAgentPlugin Install Script"
echo "========================================"
echo ""

echo "[1/11] List available plugins..."
python3 scripts/plugin-manager.py list
echo ""

echo "[2/11] Preparing .agents/skills directory..."
mkdir -p .agents/skills
echo ""

echo "[3/11] Install core plugin..."
if [ -f "agents/plugins/core.plugin.json" ]; then
    python3 scripts/plugin-manager.py install agents/plugins/core.plugin.json
fi
echo ""

echo "[4/11] Install computer-use plugin..."
if [ -f "agents/plugins/computer-use.plugin.json" ]; then
    python3 scripts/plugin-manager.py install agents/plugins/computer-use.plugin.json
fi
echo ""

echo "[5/11] Install browser-use plugin..."
if [ -f "agents/plugins/browser-use.plugin.json" ]; then
    python3 scripts/plugin-manager.py install agents/plugins/browser-use.plugin.json
fi
echo ""

echo "[6/11] Install frontend-design plugin..."
if [ -f "agents/plugins/frontend-design.plugin.json" ]; then
    python3 scripts/plugin-manager.py install agents/plugins/frontend-design.plugin.json
fi
echo ""

echo "[7/11] Install productivity plugin..."
if [ -f "agents/plugins/productivity.plugin.json" ]; then
    python3 scripts/plugin-manager.py install agents/plugins/productivity.plugin.json
fi
echo ""

echo "[8/11] Install dev-tools plugin..."
if [ -f "agents/plugins/dev-tools.plugin.json" ]; then
    python3 scripts/plugin-manager.py install agents/plugins/dev-tools.plugin.json
fi
echo ""

echo "[9/11] Install mattpocock plugin..."
if [ -f "agents/plugins/mattpocock.plugin.json" ]; then
    python3 scripts/plugin-manager.py install agents/plugins/mattpocock.plugin.json
fi
echo ""

echo "[10/11] Install superpowers plugin..."
if [ -f "agents/plugins/superpowers.plugin.json" ]; then
    python3 scripts/plugin-manager.py install agents/plugins/superpowers.plugin.json
fi
echo ""

echo "[11/11] Initialize environment and sync to IDEs..."
python3 scripts/init-env.py -a Generate
python3 scripts/init-ide.py -i All  -f
echo ""

echo "========================================"
echo "  Install Complete!"
echo "========================================"
echo ""
echo "Tip: To install more plugins, run:"
echo "  python3 scripts/plugin-manager.py install <plugin-file>"
echo ""

#python3 scripts/init-ide.py -i Agents -f
#python3 scripts/init-ide.py -i Cursor -f
#python3 scripts/init-ide.py -i Claude -f
#python3 scripts/init-ide.py -i trae-cn -f
#python3 scripts/init-ide.py -i Codex -f
#python3 scripts/init-ide.py -i OpenCode -f
#python3 scripts/init-ide.py -i IDEA -f
#python3 scripts/init-ide.py -i trae-solo-cn -f
