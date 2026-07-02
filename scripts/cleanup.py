#!/usr/bin/env python3
import os

files_to_remove = [
    "agents/plugins/browser-use.plugin.yaml",
    "agents/plugins/hybrid-example.plugin.yaml"
]

for file_path in files_to_remove:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Removed: {file_path}")
    else:
        print(f"Not found: {file_path}")

print("Cleanup complete!")
