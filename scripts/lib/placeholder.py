"""占位符替换与未解析块剪枝。

容器键剪枝：仅对 provider/providers/mcpServers/mcp 子项剪枝，
未填占位符的子项自动移除，避免污染最终配置。
"""
import json
import re
from typing import Tuple


def _has_unresolved_placeholder(value) -> bool:
    """检测 value 是否含未解析的 ${VAR} 占位符（不含 ${VAR:-default} 形式）。"""
    if isinstance(value, str):
        for m in re.finditer(r"\$\{(\w+)(?::-.*?)?\}", value):
            if ":-" not in m.group(0):
                return True
        return False
    if isinstance(value, dict):
        return any(_has_unresolved_placeholder(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_unresolved_placeholder(v) for v in value)
    return False


PRUNE_TARGET_KEYS = ("provider", "providers", "mcpServers", "mcp")


def prune_unresolved_blocks(content: str) -> Tuple[str, dict]:
    """从 JSON 内容中剪枝含未解析占位符的容器子项。

    Returns:
        (pruned_content, pruned_map) — pruned_map 形如 {"mcpServers": ["xxx"]}
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return content, {}

    pruned: dict = {}

    def walk(node):
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if key in PRUNE_TARGET_KEYS and isinstance(value, dict):
                    for child_name in list(value.keys()):
                        if _has_unresolved_placeholder(value[child_name]):
                            pruned.setdefault(key, []).append(child_name)
                            del value[child_name]
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    if not pruned:
        return content, {}
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n", pruned
