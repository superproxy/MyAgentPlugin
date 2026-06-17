#!/bin/bash
python3 scripts/init-env.py -a Generate

python3 ./scripts/init-ide.py -f -i Agents

python3 ./scripts/init-ide.py -f -i Cursor

python3 ./scripts/init-ide.py -f -i Claude

python3 ./scripts/init-ide.py -f -i trae-cn



python3 ./scripts/init-ide.py -f -i Codex

python3 ./scripts/init-ide.py -f -i OpenCode

python3 ./scripts/init-ide.py -f -i IDEA

python3 scripts/init-ide.py -i trae-solo-cn -f
