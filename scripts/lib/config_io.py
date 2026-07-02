"""统一 yaml/json 读写。消除三脚本重复的 load/save 函数。"""
import json
import sys
from pathlib import Path


def _load_yaml_module():
    try:
        import yaml
        return yaml
    except ImportError:
        print("[ERROR] PyYAML is required. Install: pip install pyyaml", file=sys.stderr)
        sys.exit(1)


def load_env_config_file(path: Path) -> dict:
    """Load env config file, auto-detecting JSON or YAML by extension."""
    with open(path, "r", encoding="utf-8-sig") as f:
        if path.suffix.lower() in (".yaml", ".yml"):
            return _load_yaml_module().safe_load(f)
        return json.load(f)


def save_env_config_file(path: Path, data: dict) -> None:
    """Save env config file, format detected by extension."""
    with open(path, "w", encoding="utf-8") as f:
        if path.suffix.lower() in (".yaml", ".yml"):
            _load_yaml_module().safe_dump(
                data, f, allow_unicode=True, sort_keys=False, default_flow_style=False
            )
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
