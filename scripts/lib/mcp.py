"""MCP 配置生成与各 IDE 格式转换。

迁移自 scripts/init-env.py（invoke_generate_step / invoke_mcp_generate_step）+
scripts/init-ide.py（convert_to_cursor_mcp / convert_to_codex_mcp / convert_to_opencode_mcp +
文件复制工具）。保持函数签名与行为不变。
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from lib.config_io import load_env_config_file
from lib.logging import (
    COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_DARKGRAY, COLOR_RESET,
)
from lib.placeholder import prune_unresolved_blocks


# ============================================================
# 模板生成（占位符替换 + 剪枝）
# ============================================================

def invoke_generate_step(
    flat_config: dict,
    template_file: Path,
    output_file: Path,
    prune: bool = True,
) -> None:
    """从模板生成配置：占位符替换 + 可选剪枝未解析块。"""
    print(f"{COLOR_CYAN}========================================{COLOR_RESET}")
    print(f"{COLOR_CYAN}  Step: Generate config from template{COLOR_RESET}")
    print(f"{COLOR_CYAN}========================================{COLOR_RESET}")
    print()

    if not template_file.exists():
        print(f"{COLOR_RED}[ERROR] Template file not found: {template_file}{COLOR_RESET}")
        sys.exit(1)

    print(f"{COLOR_GREEN}Template : {template_file}{COLOR_RESET}")
    print(f"{COLOR_GREEN}Output   : {output_file}{COLOR_RESET}")
    print()

    template_content = template_file.read_text(encoding="utf-8")

    replaced = 0
    env_map = {k: str(v) if v is not None else "" for k, v in flat_config.items()}
    for key, value in env_map.items():
        placeholder = "${" + key + "}"
        if placeholder in template_content:
            template_content = template_content.replace(placeholder, value)
            print(f"  {COLOR_GREEN}[REPLACED] {placeholder}{COLOR_RESET}")
            replaced += 1

    default_replaced = 0
    for m in re.finditer(r"\$\{(\w+):-(.*?)\}", template_content):
        var_name = m.group(1)
        default_value = m.group(2)
        full_match = m.group(0)
        resolved = env_map.get(var_name, default_value)
        template_content = template_content.replace(full_match, resolved)
        if var_name in env_map:
            print(f"  {COLOR_GREEN}[REPLACED] {full_match} -> (env){resolved}{COLOR_RESET}")
        else:
            print(f"  {COLOR_CYAN}[DEFAULT] {full_match} -> {resolved}{COLOR_RESET}")
        default_replaced += 1
    replaced += default_replaced

    if prune and template_file.suffix.lower() == ".json":
        new_content, pruned_map = prune_unresolved_blocks(template_content)
        if pruned_map:
            template_content = new_content
            print()
            print(f"  {COLOR_YELLOW}[PRUNE] 移除未配置的子项（占位符未解析）:{COLOR_RESET}")
            for parent, names in pruned_map.items():
                for n in names:
                    print(f"    - {parent}.{n}")

    remaining = re.findall(r"\$\{(\w+)\}", template_content)
    if remaining:
        print()
        print(f"  {COLOR_YELLOW}[WARN] Unresolved placeholders (missing in llm.yaml/mcp.yaml):{COLOR_RESET}")
        seen = sorted(set(remaining))
        for p in seen:
            print(f"    - ${{{p}}}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(template_content, encoding="utf-8")

    print()
    print(f"  {COLOR_CYAN}Result: {replaced} placeholder(s) replaced, output={output_file}{COLOR_RESET}")
    print()


def collect_plugin_mcp_servers(plugins_dir: Path) -> dict:
    """扫描 agents/plugins/*.plugin.yaml，合并所有插件的 mcpServers。

    plugin.yaml 中的 mcpServers 与 mcp.yaml 的 mcpServers 在 generate 阶段
    一起合并到 mcp.json，避免污染 mcp.yaml（保持 mcp.yaml 为用户手写的纯净源）。

    合并规则：
    - mcp.yaml 的 mcpServers 优先（用户手写覆盖插件默认）
    - plugin.yaml 的 mcpServers 作为补充（同名校验：若 mcp.yaml 已有则跳过）
    """
    if not plugins_dir or not plugins_dir.exists():
        return {}

    merged = {}
    for p in sorted(plugins_dir.glob("*.plugin.yaml")):
        try:
            cfg = load_env_config_file(p)
            if not isinstance(cfg, dict):
                continue
        except Exception as e:
            print(f"{COLOR_YELLOW}[!] 跳过无法解析的插件 {p.name}: {e}{COLOR_RESET}")
            continue
        servers = cfg.get("mcpServers", {})
        if not isinstance(servers, dict):
            continue
        for name, server_cfg in servers.items():
            if name in merged:
                print(f"{COLOR_DARKGRAY}[~] plugin mcp 重复，跳过: {name} (in {p.name}){COLOR_RESET}")
                continue
            merged[name] = server_cfg
            print(f"{COLOR_GREEN}[+] plugin mcp: {name} (from {p.name}){COLOR_RESET}")
    return merged


def invoke_mcp_generate_step(
    flat_config: dict,
    mcp_yaml_file: Path,
    output_file: Path,
    plugins_dir: Path | None = None,
) -> None:
    """从 mcp.yaml + plugins/*.plugin.yaml 合并 mcpServers，替换占位符后生成 mcp.json。

    合并优先级：mcp.yaml（用户手写）> plugin.yaml（插件默认）。
    """
    print(f"{COLOR_CYAN}========================================{COLOR_RESET}")
    print(f"{COLOR_CYAN}  Step: Generate mcp.json from mcp.yaml + plugins{COLOR_RESET}")
    print(f"{COLOR_CYAN}========================================{COLOR_RESET}")
    print()

    if not mcp_yaml_file.exists():
        print(f"{COLOR_RED}[ERROR] mcp.yaml not found: {mcp_yaml_file}{COLOR_RESET}")
        sys.exit(1)

    print(f"{COLOR_GREEN}Source   : {mcp_yaml_file}{COLOR_RESET}")
    if plugins_dir and plugins_dir.exists():
        print(f"{COLOR_GREEN}Plugins  : {plugins_dir}{COLOR_RESET}")
    print(f"{COLOR_GREEN}Output   : {output_file}{COLOR_RESET}")
    print()

    try:
        mcp_data = load_env_config_file(mcp_yaml_file) or {}
    except Exception as e:
        print(f"{COLOR_RED}[ERROR] 解析 mcp.yaml 失败: {e}{COLOR_RESET}")
        sys.exit(1)

    mcp_servers = mcp_data.get("mcpServers", {}) if isinstance(mcp_data, dict) else {}

    # 合并 plugin.yaml 的 mcpServers（mcp.yaml 优先）
    if plugins_dir:
        print(f"{COLOR_CYAN}--- Merging plugin mcpServers ---{COLOR_RESET}")
        plugin_servers = collect_plugin_mcp_servers(plugins_dir)
        for name, cfg in plugin_servers.items():
            if name not in mcp_servers:
                mcp_servers[name] = cfg
        print()

    enabled_servers = {
        name: cfg for name, cfg in mcp_servers.items()
        if not (isinstance(cfg, dict) and (cfg.get("disabled") is True or cfg.get("disabled") == "true"))
    }
    skipped = len(mcp_servers) - len(enabled_servers)
    if skipped:
        print(f"  {COLOR_DARKGRAY}[SKIP] 跳过 {skipped} 个 disabled 的 MCP 服务{COLOR_RESET}")
    template_content = json.dumps({"mcpServers": enabled_servers}, indent=2, ensure_ascii=False) + "\n"

    replaced = 0
    env_map = {k: str(v) if v is not None else "" for k, v in flat_config.items()}
    for key, value in env_map.items():
        placeholder = "${" + key + "}"
        if placeholder in template_content:
            template_content = template_content.replace(placeholder, value)
            print(f"  {COLOR_GREEN}[REPLACED] {placeholder}{COLOR_RESET}")
            replaced += 1

    default_replaced = 0
    for m in re.finditer(r"\$\{(\w+):-(.*?)\}", template_content):
        var_name = m.group(1)
        default_value = m.group(2)
        full_match = m.group(0)
        resolved = env_map.get(var_name, default_value)
        template_content = template_content.replace(full_match, resolved)
        if var_name in env_map:
            print(f"  {COLOR_GREEN}[REPLACED] {full_match} -> (env){resolved}{COLOR_RESET}")
        else:
            print(f"  {COLOR_CYAN}[DEFAULT] {full_match} -> {resolved}{COLOR_RESET}")
        default_replaced += 1
    replaced += default_replaced

    new_content, pruned_map = prune_unresolved_blocks(template_content)
    if pruned_map:
        template_content = new_content
        print()
        print(f"  {COLOR_YELLOW}[PRUNE] 移除未配置的子项（占位符未解析）:{COLOR_RESET}")
        for parent, names in pruned_map.items():
            for n in names:
                print(f"    - {parent}.{n}")

    remaining = re.findall(r"\$\{(\w+)\}", template_content)
    if remaining:
        print()
        print(f"  {COLOR_YELLOW}[WARN] Unresolved placeholders (missing in llm.yaml/mcp.yaml):{COLOR_RESET}")
        seen = sorted(set(remaining))
        for p in seen:
            print(f"    - ${{{p}}}")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(template_content, encoding="utf-8")

    print()
    print(f"  {COLOR_CYAN}Result: {replaced} placeholder(s) replaced, output={output_file}{COLOR_RESET}")
    print()


def _inject_opencode_models(opencode_file: Path, env_config: dict) -> None:
    """向 opencode.json 注入 provider models（来自 llm.yaml）。"""
    if not opencode_file.exists():
        return
    with open(opencode_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    llm_section = env_config.get("llm", {})
    if not isinstance(llm_section, dict):
        return
    providers_config = config.get("provider", {})
    injected = 0
    for provider_name, provider_value in llm_section.items():
        if provider_name.startswith("_"):
            continue
        if not isinstance(provider_value, dict):
            continue
        if provider_name not in providers_config:
            continue
        merged_models = {}
        for protocol_name, protocol_value in provider_value.items():
            if protocol_name.startswith("_"):
                continue
            if not isinstance(protocol_value, dict):
                continue
            models_dict = protocol_value.get("models", {})
            if isinstance(models_dict, dict):
                merged_models.update(models_dict)
        if merged_models:
            providers_config[provider_name]["models"] = merged_models
            injected += 1
    if injected > 0:
        with open(opencode_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  {COLOR_GREEN}[MODELS] Injected models into {injected} provider(s) in {opencode_file}{COLOR_RESET}")


# ============================================================
# 文件/目录复制工具
# ============================================================

def copy_dir_safe(src: Path, dst: Path, label: str, force: bool) -> None:
    if not src.exists():
        print(f"{COLOR_YELLOW}[!] Skills source dir not found: {src}{COLOR_RESET}")
        return
    if dst.exists():
        if force:
            print(f"{COLOR_YELLOW}[!] Removing existing {label} ...{COLOR_RESET}")
            if dst.is_symlink() or dst.is_file():
                dst.unlink(missing_ok=True)
            else:
                shutil.rmtree(str(dst), ignore_errors=True)
        else:
            print(f"{COLOR_YELLOW}[!] {label} already exists, use --force to overwrite{COLOR_RESET}")
            return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(str(src), str(dst), ignore=shutil.ignore_patterns('.git'))
        print(f"{COLOR_GREEN}[OK] Copied dir: {label} <- {src}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}[!] Failed to copy dir {label}: {e}{COLOR_RESET}")


def copy_file_safe(src: Path, dst: Path, label: str, force: bool) -> None:
    if not src.exists():
        print(f"{COLOR_YELLOW}[!] Source file not found: {src}{COLOR_RESET}")
        return

    if dst.exists() or dst.is_symlink():
        if force:
            print(f"{COLOR_YELLOW}[!] Removing existing {label} ...{COLOR_RESET}")
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(str(dst), ignore_errors=True)
            else:
                dst.unlink(missing_ok=True)
        else:
            print(f"{COLOR_YELLOW}[!] {label} already exists, use --force to overwrite{COLOR_RESET}")
            return

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(str(src), str(dst))
        print(f"{COLOR_GREEN}[OK] Copied file: {label} <- {src}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}[!] Failed to copy file {label}: {e}{COLOR_RESET}")


def copy_mcp_file_safe(src: Path, dst: Path, label: str, force: bool) -> None:
    """复制 mcp.json（规范化 JSON 格式）。"""
    if not src.exists():
        print(f"{COLOR_YELLOW}[!] Source file not found: {src}{COLOR_RESET}")
        return

    if dst.exists() or dst.is_symlink():
        if force:
            print(f"{COLOR_YELLOW}[!] Removing existing {label} ...{COLOR_RESET}")
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(str(dst), ignore_errors=True)
            else:
                dst.unlink(missing_ok=True)
        else:
            print(f"{COLOR_YELLOW}[!] {label} already exists, use --force to overwrite{COLOR_RESET}")
            return

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(src, "r", encoding="utf-8") as f:
            content = json.load(f)
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"{COLOR_GREEN}[OK] Copied MCP file: {label} <- {src}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}[!] Failed to copy MCP file {label}: {e}{COLOR_RESET}")


# ============================================================
# 各 IDE MCP 格式转换
# ============================================================

def _safe_write_json(target_file: Path, data: dict, retries: int = 5, delay: float = 0.4) -> None:
    """写入 JSON 文件，带重试以处理 PermissionError。"""
    last_exc = None
    for attempt in range(retries):
        try:
            if target_file.exists():
                try:
                    os.chmod(target_file, 0o666)
                except Exception:
                    pass
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            return
        except PermissionError as e:
            last_exc = e
            wait = delay * (2 ** attempt)
            print(f"{COLOR_YELLOW}[!] {target_file.name} 被占用，{wait:.1f}s 后重试 ({attempt + 1}/{retries}){COLOR_RESET}")
            time.sleep(wait)
        except OSError as e:
            last_exc = e
            wait = delay * (2 ** attempt)
            print(f"{COLOR_YELLOW}[!] 写入 {target_file.name} 失败: {e}，{wait:.1f}s 后重试 ({attempt + 1}/{retries}){COLOR_RESET}")
            time.sleep(wait)
    raise last_exc


def _toml_string(value: str) -> str:
    """Convert a Python string to a safe TOML string representation."""
    if '"' in value and "'" not in value:
        return f"'{value}'"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def convert_to_cursor_mcp(source_file: Path, target_file: Path, force: bool) -> None:
    """生成 Cursor 格式 mcp.json（仅 mcpServers，url/command+args+env）。"""
    if not source_file.exists():
        print(f"{COLOR_YELLOW}[!] MCP source not found: {source_file}{COLOR_RESET}")
        return

    if target_file.exists():
        if not force:
            print(f"{COLOR_YELLOW}[!] Cursor MCP already exists, use --force to overwrite{COLOR_RESET}")
            return
        target_file.unlink()

    with open(source_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    cursor_mcp = {"mcpServers": {}}
    for server_name, server in content.get("mcpServers", content).items():
        server_config = {}
        if server.get("type") in ("http", "streamableHttp") or server.get("url"):
            server_config["url"] = server["url"]
            if server.get("headers"):
                server_config["headers"] = dict(server["headers"])
        else:
            server_config["command"] = server["command"]
            if server.get("args"):
                server_config["args"] = list(server["args"])
            if server.get("env"):
                server_config["env"] = dict(server["env"])
        cursor_mcp["mcpServers"][server_name] = server_config

    target_file.parent.mkdir(parents=True, exist_ok=True)
    _safe_write_json(target_file, cursor_mcp)
    print(f"{COLOR_GREEN}[OK] Cursor MCP generated: {target_file}{COLOR_RESET}")


def convert_to_codex_mcp(source_file: Path, target_file: Path, force: bool,
                         template_file: Path | None = None) -> None:
    """生成 Codex 格式 config.toml（[mcp_servers.X] 段）。"""
    if not source_file.exists():
        print(f"{COLOR_YELLOW}[!] MCP source not found: {source_file}{COLOR_RESET}")
        return

    if target_file.exists():
        if not force:
            print(f"{COLOR_YELLOW}[!] Codex MCP already exists, use --force to overwrite{COLOR_RESET}")
            return
        target_file.unlink()

    with open(source_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    mcp_lines = []
    for server_name, server in content.get("mcpServers", content).items():
        if server.get("disabled", False):
            continue
        mcp_lines.append(f"[mcp_servers.{server_name}]")
        if server.get("type") in ("http", "streamableHttp") or server.get("url"):
            mcp_lines.append(f'url = {_toml_string(server["url"])}')
            if server.get("headers"):
                headers = server["headers"]
                header_parts = [f'{k} = {_toml_string(v)}' for k, v in headers.items()]
                mcp_lines.append(f"http_headers = {{ {', '.join(header_parts)} }}")
        else:
            mcp_lines.append(f'command = {_toml_string(server["command"])}')
            if server.get("args"):
                args_str = ", ".join(_toml_string(a) for a in server["args"])
                mcp_lines.append(f"args = [{args_str}]")
            timeout_ms = server.get("startupTimeout")
            if timeout_ms is not None:
                timeout_sec = max(1, int(timeout_ms / 1000))
                mcp_lines.append(f"startup_timeout_sec = {timeout_sec}")
            if server.get("env"):
                mcp_lines.append(f"[mcp_servers.{server_name}.env]")
                for k, v in server["env"].items():
                    mcp_lines.append(f'{k} = {_toml_string(v)}')
        mcp_lines.append("")

    target_file.parent.mkdir(parents=True, exist_ok=True)

    if template_file and template_file.exists():
        template_text = template_file.read_text(encoding="utf-8")
        merged_lines = []
        in_mcp_section = False
        for line in template_text.splitlines(keepends=False):
            stripped = line.strip()
            if stripped.startswith("[mcp_servers."):
                in_mcp_section = True
                continue
            if in_mcp_section:
                if stripped.startswith("[") or stripped == "":
                    in_mcp_section = False
                    merged_lines.append(line)
                continue
            merged_lines.append(line)

        merged_text = "\n".join(merged_lines).rstrip("\n")
        if merged_text and not merged_text.endswith("\n\n"):
            merged_text += "\n"
        merged_text += "\n" + "\n".join(mcp_lines)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(merged_text + "\n")
    else:
        lines = [
            "# Codex MCP Configuration",
            "# Auto-generated by agentctl from agents/mcp/mcp.json",
            "",
        ]
        lines.extend(mcp_lines)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    print(f"{COLOR_GREEN}[OK] Codex MCP generated: {target_file}{COLOR_RESET}")


def _resolve_placeholders(obj, env_map: dict) -> tuple:
    if isinstance(obj, str):
        replaced = 0
        for key, value in env_map.items():
            placeholder = "${" + key + "}"
            if placeholder in obj:
                obj = obj.replace(placeholder, value)
                replaced += 1
        for m in re.finditer(r"\$\{(\w+):-(.*?)\}", obj):
            var_name = m.group(1)
            default_value = m.group(2)
            full_match = m.group(0)
            resolved = env_map.get(var_name, default_value)
            obj = obj.replace(full_match, resolved)
            replaced += 1
        return obj, replaced
    if isinstance(obj, dict):
        total = 0
        for k in obj:
            obj[k], r = _resolve_placeholders(obj[k], env_map)
            total += r
        return obj, total
    if isinstance(obj, list):
        total = 0
        for i in range(len(obj)):
            obj[i], r = _resolve_placeholders(obj[i], env_map)
            total += r
        return obj, total
    return obj, 0


def _collect_placeholders(obj, result: list) -> None:
    if isinstance(obj, str):
        for m in re.finditer(r"\$\{(\w+)(?::-.*?)?\}", obj):
            if ":-" not in m.group(0):
                result.append(m.group(1))
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_placeholders(v, result)
    elif isinstance(obj, list):
        for v in obj:
            _collect_placeholders(v, result)


def convert_to_opencode_mcp(source_file: Path, target_file: Path, force: bool,
                            template_file: Path | None = None,
                            env_config: dict | None = None) -> None:
    """生成 OpenCode 格式 opencode.json（含 provider models 注入）。"""
    if not source_file.exists():
        print(f"{COLOR_YELLOW}[!] MCP source not found: {source_file}{COLOR_RESET}")
        return

    if target_file.exists():
        if not force:
            print(f"{COLOR_YELLOW}[!] OpenCode config already exists, use --force to overwrite{COLOR_RESET}")
            return
        target_file.unlink()

    with open(source_file, "r", encoding="utf-8") as f:
        content = json.load(f)

    opencode_mcp = {}
    for server_name, server in content.get("mcpServers", content).items():
        server_config = {}
        if server.get("type") in ("http", "streamableHttp") or server.get("url"):
            server_config["type"] = "remote"
            server_config["url"] = server["url"]
            if server.get("headers"):
                server_config["headers"] = dict(server["headers"])
        else:
            server_config["type"] = "local"
            command_parts = [server["command"]]
            if server.get("args"):
                command_parts.extend(list(server["args"]))
            server_config["command"] = command_parts
            if server.get("env"):
                server_config["environment"] = dict(server["env"])
        server_config["enabled"] = not server.get("disabled", False)
        opencode_mcp[server_name] = server_config

    config = {"$schema": "https://opencode.ai/config.json", "mcp": opencode_mcp}

    if template_file and template_file.exists():
        with open(template_file, "r", encoding="utf-8") as f:
            template = json.load(f)
        for key in ("provider", "model", "small_model", "server", "instructions", "permission", "autoCompact"):
            if key in template:
                config[key] = template[key]
        if "mcp" in template and isinstance(template["mcp"], dict):
            for name, cfg in template["mcp"].items():
                if name not in opencode_mcp:
                    opencode_mcp[name] = cfg

    env_map = {}
    if env_config:
        active_provider = ""
        active_protocols = ["openai"]
        llm_section = env_config.get("llm", {})
        if isinstance(llm_section, dict):
            active_provider = llm_section.get("_active_provider", "")
            raw = llm_section.get("_active_protocol", "openai")
            active_protocols = [p.strip() for p in str(raw).split("|") if p.strip()]
        protocol_env_map = {
            "openai": {"base_url": "OPEN_AI_API_BASE_URL", "api_key": "OPEN_AI_API_KEY", "model": "OPENAI_MODEL"},
            "anthropic": {"base_url": "ANTHROPIC_BASE_URL", "api_key": "ANTHROPIC_AUTH_TOKEN", "model": "ANTHROPIC_MODEL"},
        }
        for section_key, section_value in env_config.items():
            if section_key == "_description":
                continue
            if section_key == "llm" and isinstance(section_value, dict):
                for provider_name, provider_value in section_value.items():
                    if provider_name.startswith("_"):
                        continue
                    if not isinstance(provider_value, dict):
                        continue
                    is_active = provider_name == active_provider
                    provider_upper = provider_name.upper().replace("-", "_")
                    for protocol_name, protocol_value in provider_value.items():
                        if protocol_name.startswith("_"):
                            continue
                        if not isinstance(protocol_value, dict):
                            continue
                        protocol_upper = protocol_name.upper().replace("-", "_")
                        for k, v in protocol_value.items():
                            if k.startswith("_") or k == "models":
                                continue
                            if not v or not str(v).strip():
                                continue
                            named_key = f"LLM_{provider_upper}_{protocol_upper}_{k.upper()}"
                            env_map[named_key] = str(v)
                        if is_active and protocol_name in active_protocols:
                            mapping = protocol_env_map.get(protocol_name, {})
                            models_dict = protocol_value.get("models", {})
                            if isinstance(models_dict, dict) and models_dict:
                                default_model = next(iter(models_dict.keys()), "")
                                std_model_key = mapping.get("model")
                                if std_model_key and default_model:
                                    env_map[std_model_key] = default_model
                            for k, v in protocol_value.items():
                                if k.startswith("_") or k == "models":
                                    continue
                                if not v or not str(v).strip():
                                    continue
                                std_key = mapping.get(k)
                                if std_key:
                                    env_map[std_key] = str(v)
                                else:
                                    env_map[k] = str(v)
                            if protocol_name == "openai":
                                env_map["OPENAI_API_KEY"] = str(protocol_value.get("api_key", ""))
            elif isinstance(section_value, dict):
                for k, v in section_value.items():
                    if k.startswith("_"):
                        continue
                    if isinstance(v, dict):
                        for k2, v2 in v.items():
                            if k2.startswith("_"):
                                continue
                            if v2 and str(v2).strip():
                                env_map[k2] = str(v2)
                    elif v and str(v).strip():
                        env_map[k] = str(v)
            elif section_value and str(section_value).strip():
                env_map[section_key] = str(section_value)

    if env_map:
        config, replaced = _resolve_placeholders(config, env_map)
        if replaced > 0:
            print(f"{COLOR_GREEN}[OK] Resolved {replaced} placeholder(s) from llm.yaml/mcp.yaml{COLOR_RESET}")

    if env_config:
        _inject_opencode_models_into_config(config, env_config)

    remaining = []
    _collect_placeholders(config, remaining)
    if remaining:
        print(f"{COLOR_YELLOW}[!] Unresolved placeholders: {', '.join(sorted(set(remaining)))}{COLOR_RESET}")

    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"{COLOR_GREEN}[OK] OpenCode config generated: {target_file}{COLOR_RESET}")


def _inject_opencode_models_into_config(config: dict, env_config: dict) -> None:
    """将 llm.yaml 的 provider models 注入到 opencode config 的 provider 段。"""
    llm_section = env_config.get("llm", {})
    if not isinstance(llm_section, dict):
        return
    providers_config = config.get("provider", {})
    for provider_name, provider_value in llm_section.items():
        if provider_name.startswith("_"):
            continue
        if not isinstance(provider_value, dict):
            continue
        if provider_name not in providers_config:
            continue
        merged_models = {}
        for protocol_name, protocol_value in provider_value.items():
            if protocol_name.startswith("_"):
                continue
            if not isinstance(protocol_value, dict):
                continue
            models_dict = protocol_value.get("models", {})
            if isinstance(models_dict, dict):
                merged_models.update(models_dict)
        if merged_models:
            providers_config[provider_name]["models"] = merged_models
