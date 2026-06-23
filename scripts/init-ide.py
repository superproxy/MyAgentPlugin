#!/usr/bin/env python3
"""
Initialize IDE config from agents/ shared source.

Uses directory junctions so source is the single source of truth.
- .agent/rules/     : Junction -> source rules/ (通用目录，大部分 IDE 原生支持)
- .trae/rules/      : Junction -> source rules/
- .trae-cn/rules/       : Junction -> source rules/
- .trae-solo-cn/rules/  : Junction -> source rules/
- .cursor/rules/        : Junction -> source rules/
- .codex/rules/     : Junction -> source rules/
- .claude/rules/    : Junction -> source rules/
- .workbuddy/rules/ : Junction -> source rules/
- .qoder/rules/     : Junction -> source rules/
- .openclaw/rules/  : Junction -> source rules/
- .mcp.json         : Symlink/Copy -> source mcp/mcp.json
- .cursor/mcp.json   : Generated (mcpServers key)
- .codex/config.toml : Generated (TOML format)
- .claude/settings.json : Generated (from template + env.json)
- opencode.json       : Generated (OpenCode format)
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_MAGENTA = "\033[95m"
COLOR_WHITE = "\033[97m"
COLOR_DARKGRAY = "\033[90m"
COLOR_RESET = "\033[0m"

H1 = "## "
H2 = "### "
H3 = "#### "


def write_banner(title: str, source_dir: str, target_dir: str, ide: str) -> None:
    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")
    print(f"{COLOR_CYAN}  {title}{COLOR_RESET}")
    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")
    print(f"{COLOR_YELLOW}Source : {source_dir}{COLOR_RESET}")
    print(f"{COLOR_YELLOW}Target : {target_dir}{COLOR_RESET}")
    print(f"{COLOR_YELLOW}IDE(s) : {ide}{COLOR_RESET}")
    print()


def test_prerequisites(source_dir: Path, source_rules_dir: Path) -> None:
    if not source_dir.exists():
        print(f"{COLOR_RED}Source directory not found: {source_dir}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)
    print(f"{COLOR_GREEN}[OK] Source agents/ found{COLOR_RESET}")
    if not source_rules_dir.exists():
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping rules junction{COLOR_RESET}")

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
                import shutil
                shutil.rmtree(str(dst), ignore_errors=True)
        else:
            print(f"{COLOR_YELLOW}[!] {label} already exists, use --force to overwrite{COLOR_RESET}")
            return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        import shutil
        shutil.copytree(str(src), str(dst), ignore=shutil.ignore_patterns('.git'))
        print(f"{COLOR_GREEN}[OK] Copied dir: {label} <- {src}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}[!] Failed to copy dir {label}: {e}{COLOR_RESET}")


def copy_skills_safe(src: Path, dst: Path, label: str, force: bool) -> None:
    if not src.exists():
        print(f"{COLOR_YELLOW}[!] Skills source dir not found: {src}{COLOR_RESET}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    import shutil
    copied = 0
    skipped = 0
    for skill_dir in sorted(src.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_dst = dst / skill_dir.name
        if skill_dst.exists():
            if force:
                shutil.rmtree(str(skill_dst), ignore_errors=True)
            else:
                skipped += 1
                continue
        try:
            shutil.copytree(str(skill_dir), str(skill_dst), ignore=shutil.ignore_patterns('.git'))
            copied += 1
        except Exception as e:
            print(f"{COLOR_RED}[!] Failed to copy skill {skill_dir.name}: {e}{COLOR_RESET}")

    if copied > 0:
        print(f"{COLOR_GREEN}[OK] {label}: {copied} skills copied{COLOR_RESET}")
    if skipped > 0:
        print(f"{COLOR_DARKGRAY}[~] {label}: {skipped} skills skipped (already exist){COLOR_RESET}")


def copy_file_safe(src: Path, dst: Path, label: str, force: bool) -> None:
    if not src.exists():
        print(f"{COLOR_YELLOW}[!] Source file not found: {src}{COLOR_RESET}")
        return

    if dst.exists() or dst.is_symlink():
        if force:
            print(f"{COLOR_YELLOW}[!] Removing existing {label} ...{COLOR_RESET}")
            if dst.is_dir() and not dst.is_symlink():
                import shutil
                shutil.rmtree(str(dst), ignore_errors=True)
            else:
                dst.unlink(missing_ok=True)
        else:
            print(f"{COLOR_YELLOW}[!] {label} already exists, use --force to overwrite{COLOR_RESET}")
            return

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        import shutil
        shutil.copy2(str(src), str(dst))
        print(f"{COLOR_GREEN}[OK] Copied file: {label} <- {src}{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}[!] Failed to copy file {label}: {e}{COLOR_RESET}")


def copy_mcp_file_safe(src: Path, dst: Path, label: str, force: bool) -> None:
    if not src.exists():
        print(f"{COLOR_YELLOW}[!] Source file not found: {src}{COLOR_RESET}")
        return

    if dst.exists() or dst.is_symlink():
        if force:
            print(f"{COLOR_YELLOW}[!] Removing existing {label} ...{COLOR_RESET}")
            if dst.is_dir() and not dst.is_symlink():
                import shutil
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


def convert_to_cursor_mcp(source_file: Path, target_file: Path, force: bool) -> None:
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

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(cursor_mcp, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"{COLOR_GREEN}[OK] Cursor MCP generated: {target_file}{COLOR_RESET}")


def _toml_string(value: str) -> str:
    """Convert a Python string to a safe TOML string representation.

    Uses single-quoted literal strings when the value contains double quotes
    (e.g. JSON), avoiding the need to escape them. Falls back to escaped
    double-quoted strings otherwise.
    """
    if '"' in value and "'" not in value:
        return f"'{value}'"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def convert_to_codex_mcp(source_file: Path, target_file: Path, force: bool,
                         template_file: Path | None = None) -> None:
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
                header_parts = []
                for k, v in headers.items():
                    header_parts.append(f'{k} = {_toml_string(v)}')
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
        lines = []
        lines.append("# Codex MCP Configuration")
        lines.append("# Auto-generated by init-ide.py from agents/mcp/mcp.json")
        lines.append("")
        lines.extend(mcp_lines)

        with open(target_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    print(f"{COLOR_GREEN}[OK] Codex MCP generated: {target_file}{COLOR_RESET}")


def _resolve_placeholders(obj, env_map: dict[str, str]) -> tuple[any, int]:
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


def convert_to_opencode_mcp(source_file: Path, target_file: Path, force: bool,
                            template_file: Path | None = None,
                            env_file: Path | None = None) -> None:
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
    if env_file and env_file.exists():
        with open(env_file, "r", encoding="utf-8-sig") as f:
            env_config = json.load(f)
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
            print(f"{COLOR_GREEN}[OK] Resolved {replaced} placeholder(s) from env.json{COLOR_RESET}")

    if env_file and env_file.exists():
        with open(env_file, "r", encoding="utf-8-sig") as f:
            env_config = json.load(f)
        llm_section = env_config.get("llm", {})
        if isinstance(llm_section, dict):
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

    remaining = []
    _collect_placeholders(config, remaining)
    if remaining:
        print(f"{COLOR_YELLOW}[!] Unresolved placeholders: {', '.join(sorted(set(remaining)))}{COLOR_RESET}")

    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"{COLOR_GREEN}[OK] OpenCode config generated: {target_file}{COLOR_RESET}")


def _collect_placeholders(obj, result: list[str]) -> None:
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


def load_skill_mapping(csv_path: Path) -> dict[str, dict[str, str]]:
    """Load skill-to-role mapping from CSV file.

    Returns dict: {skill_name: {category, role, description, trigger_keywords, installable}}
    """
    mapping = {}
    if not csv_path.exists():
        return mapping
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("skill_name", "").strip()
            if name:
                mapping[name] = {
                    "category": row.get("category", "").strip(),
                    "role": row.get("role", "").strip(),
                    "description": row.get("description", "").strip(),
                    "trigger_keywords": row.get("trigger_keywords", "").strip(),
                    "installable": row.get("installable", "false").strip().lower() == "true",
                }
    return mapping


def build_role_mapping_table(mapping: dict[str, dict[str, str]]) -> list[str]:
    """Build role-to-skills mapping table lines from CSV data.

    Separates built-in skills from installable (通用) skills.
    """
    role_skills: dict[str, list[str]] = {}
    installable_skills: list[str] = []

    for skill_name, info in mapping.items():
        if info.get("installable"):
            installable_skills.append(skill_name)
            continue
        roles = [r.strip() for r in info["role"].split("|") if r.strip()]
        for role in roles:
            if role not in role_skills:
                role_skills[role] = []
            role_skills[role].append(skill_name)

    lines = []
    lines.append(f"{H2}Skill to Role Mapping")
    lines.append("")
    lines.append("| Role | Recommended Skills |")
    lines.append("|------|-------------------|")
    for role in sorted(role_skills.keys()):
        skills = ", ".join(role_skills[role])
        lines.append(f"| {role} | {skills} |")

    if installable_skills:
        lines.append("")
        lines.append(f"{H2}Installable Skills (通用)")
        lines.append("")
        lines.append("> 以下技能为通用技能，需通过 `find-skills` 安装后使用。")
        lines.append("")
        lines.append("| Skill | Category | Description |")
        lines.append("|-------|----------|-------------|")
        for skill_name in sorted(installable_skills):
            info = mapping[skill_name]
            lines.append(f"| `{skill_name}` | {info['category']} | {info['description']} |")

    return lines


def write_skills_index(skills_source_dir: Path, target_file: Path, ide_name: str, force: bool) -> None:
    if not skills_source_dir.exists():
        print(f"{COLOR_YELLOW}[!] Skills source dir not found: {skills_source_dir}{COLOR_RESET}")
        return

    if target_file.exists() and not force:
        print(f"{COLOR_YELLOW}[!] Skills index exists, use --force to overwrite{COLOR_RESET}")
        return

    target_file.parent.mkdir(parents=True, exist_ok=True)

    lines = []

    lines.append(f"{H1}{ide_name} Skills Index")
    lines.append("")
    lines.append("Auto-generated by init-ide.py. Lists all available AI skills.")
    lines.append("")

    if ide_name == "Cursor":
        lines.append("> Cursor IDE does not natively support a Skills directory. Use `@file-path` to reference SKILL.md in conversations.")
    elif ide_name == "Agents":
        lines.append("> `.agents/` 是全局共享 AI 智能体目录，可作为多项目通用技能源。")
    elif ide_name == "Codex":
        lines.append("> Codex IDE supports Skills via `.codex/skills/` directory.")
    elif ide_name == "Claude":
        lines.append("> Claude IDE supports Skills via `.claude/skills/` directory.")
    else:
        lines.append("> Trae IDE supports Skills via `.agents/skills/` directory.")
    lines.append("")

    lines.append(f"{H2}Skill List")
    lines.append("")

    for skill_dir in sorted(skills_source_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        skill_content = skill_file.read_text(encoding="utf-8")
        name = skill_dir.name
        description = ""

        desc_match = re.search(r'description:\s*>-?\s*\n?\s*(.+?)(\n\w+:|$)', skill_content)
        if not desc_match:
            desc_match = re.search(r'description:\s*"(.+?)"', skill_content)
        if not desc_match:
            desc_match = re.search(r'description:\s*(.+?)(\n\w+:|$)', skill_content)
        if desc_match:
            description = desc_match.group(1).strip()
            description = re.sub(r'>\s*', ' ', description)
            description = re.sub(r'\s+', ' ', description).strip()

        try:
            relative_path = skill_file.resolve().relative_to(Path.cwd())
        except ValueError:
            relative_path = skill_file

        lines.append(f"{H3}{name}")
        lines.append("")
        lines.append(f"- **Description**: {description}")
        lines.append(f"- **Path**: {relative_path}")
        lines.append("")

    lines.append(f"{H2}Skill to Role Mapping")
    lines.append("")

    csv_path = skills_source_dir.parent.parent / "skills-mapping.csv"
    mapping = load_skill_mapping(csv_path)
    if mapping:
        lines.extend(build_role_mapping_table(mapping))
    else:
        lines.append("| Role | Recommended Skills |")
        lines.append("|------|-------------------|")
        lines.append("| Frontend | stitch-prototype-skill, mastergo-magic-skill, drawio-skill, mermaid-sequence-from-flow |")
        lines.append("| Backend | restful-api-design-skill, task-plan-skill, drawio-skill |")
        lines.append("| Design | stitch-prototype-skill, mastergo-magic-skill, prd-to-mastergo-interaction-skill, drawio-skill |")
        lines.append("| Product | usecase-prd-skill, task-plan-skill, weekly-report-skill, prd-to-mastergo-interaction-skill |")
        lines.append("")
        lines.append(f"{H2}Installable Skills (通用)")
        lines.append("")
        lines.append("> 以下技能为通用技能，需通过 `find-skills` 安装后使用。")
        lines.append("")
        lines.append("| Skill | Category | Description |")
        lines.append("|-------|----------|-------------|")
        lines.append("| `find-skills` | 技能发现 | 帮助发现和查找仓库中的 AI 技能 |")
        lines.append("| `personnel-recruitment` | 人力资源 | 结构化招聘（JD优化/简历筛选/面试设计/评分卡/录用建议） |")
        lines.append("| `hardware-agent-prompt-skill` | 硬件AI | 为硬件 AI 智能体生成提示词与角色设定 |")
        lines.append("| `elon-musk-perspective` | 思维模型 | 马斯克思维模型分析（第一性原理/五步算法/白痴指数/垂直整合） |")

    target_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{COLOR_GREEN}[OK] Skills index: {target_file}{COLOR_RESET}")


def init_cursor(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
                source_skills_dir: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- Cursor IDE ---{COLOR_RESET}")

    cursor_dir = target_dir / ".cursor"
    cursor_rules_dir = cursor_dir / "rules"
    cursor_skills_dir = cursor_dir / "skills"

    cursor_dir.mkdir(parents=True, exist_ok=True)

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, cursor_rules_dir, ".cursor/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    convert_to_cursor_mcp(source_mcp_file, cursor_dir / "mcp.json", force)

    copy_skills_safe(source_skills_dir, cursor_skills_dir, ".cursor/skills/", force)

    write_skills_index(source_skills_dir, cursor_skills_dir / "README.md", "Cursor", force)
    return "cursor"


def _get_ide_user_dir(ide_name: str) -> Path:
    """获取 IDE 的 User 目录（跨平台）"""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / ide_name / "User"
    elif sys.platform == "win32":
        return Path.home() / "AppData" / "Roaming" / ide_name / "User"
    else:
        return Path.home() / ".config" / ide_name / "User"


def init_trae(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
              source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- Trae IDE ---{COLOR_RESET}")

    # Trae 全局目录 ~/.trae/（跨平台通用，存 rules/skills）
    trae_global_dir = Path.home() / ".trae"
    trae_global_dir.mkdir(parents=True, exist_ok=True)

    trae_rules_dir = trae_global_dir / "rules"
    trae_skills_dir = trae_global_dir / "skills"

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, trae_rules_dir, "~/.trae/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    # MCP 配置写到 IDE User 目录
    trae_user_mcp = _get_ide_user_dir("Trae") / "mcp.json"
    copy_mcp_file_safe(source_mcp_file, trae_user_mcp, f"Trae User/mcp.json", force)

    copy_skills_safe(source_skills_dir, trae_skills_dir, "~/.trae/skills/", force)

    if source_skills_dir.exists():
        skill_count = sum(1 for d in source_skills_dir.iterdir() if d.is_dir())
        print(f"{COLOR_GREEN}[OK] {skill_count} skills available in agents/skills/{COLOR_RESET}")
    return "trae"


def init_trae_cn(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
                 source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- Trae CN IDE ---{COLOR_RESET}")

    # Trae-CN 全局目录 ~/.trae-cn/（跨平台通用，存 rules/skills）
    trae_cn_global_dir = Path.home() / ".trae-cn"
    trae_cn_global_dir.mkdir(parents=True, exist_ok=True)

    trae_cn_rules_dir = trae_cn_global_dir / "rules"
    trae_cn_skills_dir = trae_cn_global_dir / "skills"

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, trae_cn_rules_dir, "~/.trae-cn/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    # MCP 配置写到 IDE User 目录
    trae_cn_user_mcp = _get_ide_user_dir("Trae CN") / "mcp.json"
    copy_mcp_file_safe(source_mcp_file, trae_cn_user_mcp, "Trae CN User/mcp.json", force)

    copy_skills_safe(source_skills_dir, trae_cn_skills_dir, "~/.trae-cn/skills/", force)

    if source_skills_dir.exists():
        skill_count = sum(1 for d in source_skills_dir.iterdir() if d.is_dir())
        print(f"{COLOR_GREEN}[OK] {skill_count} skills available in agents/skills/{COLOR_RESET}")
    return "trae-cn"


def init_trae_solo_cn(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
                      source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- TRAE SOLO CN IDE ---{COLOR_RESET}")

    # TRAE SOLO CN 全局目录 ~/.trae-solo-cn/（跨平台通用，存 rules/skills）
    trae_solo_cn_global_dir = Path.home() / ".trae-solo-cn"
    trae_solo_cn_global_dir.mkdir(parents=True, exist_ok=True)

    trae_solo_cn_rules_dir = trae_solo_cn_global_dir / "rules"
    trae_solo_cn_skills_dir = trae_solo_cn_global_dir / "skills"

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, trae_solo_cn_rules_dir, "~/.trae-solo-cn/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    # MCP 配置写到 IDE User 目录
    trae_solo_cn_user_mcp = _get_ide_user_dir("TRAE SOLO CN") / "mcp.json"
    copy_mcp_file_safe(source_mcp_file, trae_solo_cn_user_mcp, "TRAE SOLO CN User/mcp.json", force)

    copy_skills_safe(source_skills_dir, trae_solo_cn_skills_dir, "~/.trae-solo-cn/skills/", force)

    if source_skills_dir.exists():
        skill_count = sum(1 for d in source_skills_dir.iterdir() if d.is_dir())
        print(f"{COLOR_GREEN}[OK] {skill_count} skills available in agents/skills/{COLOR_RESET}")
    return "trae-solo-cn"


def init_agents(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
                source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- .agents (全局共享目录) ---{COLOR_RESET}")

    agents_dir = target_dir / ".agents"
    agents_rules_dir = agents_dir / "rules"
    agents_mcp_dir = agents_dir / "mcp"
    agents_mcp_file = agents_dir / "mcp" / ".mcp.json"
    agents_skills_dir = agents_dir / "skills"

    agents_dir.mkdir(parents=True, exist_ok=True)

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, agents_rules_dir, ".agents/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    agents_mcp_dir.mkdir(parents=True, exist_ok=True)
    copy_file_safe(source_mcp_file, agents_mcp_file, ".agents/mcp/.mcp.json", force)

    copy_skills_safe(source_skills_dir, agents_skills_dir, ".agents/skills/", force)

    write_skills_index(source_skills_dir, agents_skills_dir / "README.md", "Agents", force)

    if source_skills_dir.exists():
        skill_count = sum(1 for d in source_skills_dir.iterdir() if d.is_dir())
        print(f"{COLOR_GREEN}[OK] {skill_count} skills available in agents/skills/{COLOR_RESET}")
    return "agents"


def init_codex(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
               source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- Codex IDE ---{COLOR_RESET}")

    codex_dir = target_dir / ".codex"
    codex_rules_dir = codex_dir / "rules"
    codex_skills_dir = codex_dir / "skills"

    codex_dir.mkdir(parents=True, exist_ok=True)

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, codex_rules_dir, ".codex/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    source_dir = source_rules_dir.parent.parent
    codex_template = source_dir / "ide" / "codex" / "config.toml"
    convert_to_codex_mcp(source_mcp_file, codex_dir / "config.toml", force, codex_template)

    codex_auth_src = source_dir / "ide" / "codex" / "auth.json"
    copy_file_safe(codex_auth_src, codex_dir / "auth.json", ".codex/auth.json", force)

    copy_skills_safe(source_skills_dir, codex_skills_dir, ".codex/skills/", force)

    write_skills_index(source_skills_dir, codex_skills_dir / "README.md", "Codex", force)
    return "codex"


def _generate_claude_settings(template_file: Path, target_file: Path, env_file: Path, force: bool) -> None:
    if not template_file.exists():
        print(f"{COLOR_YELLOW}[!] Claude settings template not found: {template_file}{COLOR_RESET}")
        return

    if target_file.exists():
        if not force:
            print(f"{COLOR_YELLOW}[!] Claude settings.json already exists, use --force to overwrite{COLOR_RESET}")
            return
        target_file.unlink()

    with open(template_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    env_map = {}
    if env_file and env_file.exists():
        with open(env_file, "r", encoding="utf-8-sig") as f:
            env_config = json.load(f)
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
        for provider_name, provider_value in llm_section.items():
            if provider_name.startswith("_"):
                continue
            if not isinstance(provider_value, dict):
                continue
            is_active = provider_name == active_provider
            for protocol_name, protocol_value in provider_value.items():
                if protocol_name.startswith("_"):
                    continue
                if not isinstance(protocol_value, dict):
                    continue
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
        for section_key in ("mcp", "misc"):
            section_value = env_config.get(section_key, {})
            if not isinstance(section_value, dict):
                continue
            for k, v in section_value.items():
                if k.startswith("_"):
                    continue
                if v and str(v).strip():
                    env_map[k] = str(v)

    if env_map:
        config, replaced = _resolve_placeholders(config, env_map)
        if replaced > 0:
            print(f"{COLOR_GREEN}[OK] Resolved {replaced} placeholder(s) in Claude settings{COLOR_RESET}")

    remaining = []
    _collect_placeholders(config, remaining)
    if remaining:
        print(f"{COLOR_YELLOW}[!] Unresolved placeholders in Claude settings: {', '.join(sorted(set(remaining)))}{COLOR_RESET}")

    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"{COLOR_GREEN}[OK] Claude settings generated: {target_file}{COLOR_RESET}")


def init_claude(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
                source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- Claude IDE ---{COLOR_RESET}")

    claude_dir = target_dir / ".claude"
    claude_rules_dir = claude_dir / "rules"
    claude_skills_dir = claude_dir / "skills"

    claude_dir.mkdir(parents=True, exist_ok=True)

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, claude_rules_dir, ".claude/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    copy_file_safe(source_mcp_file, claude_dir / "mcp.json", ".claude/mcp.json", force)

    source_dir = source_rules_dir.parent.parent
    claude_settings_template = source_dir / "ide" / "claude" / "settings.template.json"
    env_file = source_dir / "env.json"
    _generate_claude_settings(claude_settings_template, claude_dir / "settings.json", env_file, force)

    copy_skills_safe(source_skills_dir, claude_skills_dir, ".claude/skills/", force)

    write_skills_index(source_skills_dir, claude_skills_dir / "README.md", "Claude", force)
    return "claude"


def init_workbuddy(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
                   source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- WorkBuddy IDE ---{COLOR_RESET}")

    wb_dir = target_dir / ".workbuddy"
    wb_rules_dir = wb_dir / "rules"
    wb_skills_dir = wb_dir / "skills"

    wb_dir.mkdir(parents=True, exist_ok=True)

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, wb_rules_dir, ".workbuddy/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    copy_file_safe(source_mcp_file, wb_dir / "mcp.json", ".workbuddy/mcp.json", force)

    copy_skills_safe(source_skills_dir, wb_skills_dir, ".workbuddy/skills/", force)

    write_skills_index(source_skills_dir, wb_skills_dir / "README.md", "WorkBuddy", force)
    return "workbuddy"


def init_qoder(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
               source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- Qoder IDE ---{COLOR_RESET}")

    qoder_dir = target_dir / ".qoder"
    qoder_rules_dir = qoder_dir / "rules"
    qoder_skills_dir = qoder_dir / "skills"

    qoder_dir.mkdir(parents=True, exist_ok=True)

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, qoder_rules_dir, ".qoder/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    copy_file_safe(source_mcp_file, qoder_dir / "mcp.json", ".qoder/mcp.json", force)

    copy_skills_safe(source_skills_dir, qoder_skills_dir, ".qoder/skills/", force)

    write_skills_index(source_skills_dir, qoder_skills_dir / "README.md", "Qoder", force)
    return "qoder"


def init_openclaw(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
                  source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- OpenClaw IDE ---{COLOR_RESET}")

    oc_dir = target_dir / ".openclaw"
    oc_rules_dir = oc_dir / "rules"
    oc_skills_dir = oc_dir / "skills"

    oc_dir.mkdir(parents=True, exist_ok=True)

    if source_rules_dir.exists():
        copy_dir_safe(source_rules_dir, oc_rules_dir, ".openclaw/rules/", force)
    else:
        print(f"{COLOR_YELLOW}[!] Source rules/ not found, skipping{COLOR_RESET}")

    copy_file_safe(source_mcp_file, oc_dir / "mcp.json", ".openclaw/mcp.json", force)

    copy_skills_safe(source_skills_dir, oc_skills_dir, ".openclaw/skills/", force)

    write_skills_index(source_skills_dir, oc_skills_dir / "README.md", "OpenClaw", force)
    return "openclaw"


def init_opencode(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
                  source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- OpenCode IDE ---{COLOR_RESET}")

    opencode_dir = Path.home() / ".config" / "opencode"
    opencode_skills_dir = opencode_dir / "skills"

    opencode_dir.mkdir(parents=True, exist_ok=True)

    source_dir = source_rules_dir.parent.parent
    opencode_template = source_dir / "ide" / "opencode" / "opencode.template.json"
    env_file = source_dir / "env.json"
    convert_to_opencode_mcp(source_mcp_file, opencode_dir / "opencode.json", force, opencode_template, env_file)

    copy_skills_safe(source_skills_dir, opencode_skills_dir, ".opencode/skills/", force)

    write_skills_index(source_skills_dir, opencode_skills_dir / "README.md", "OpenCode", force)
    return "opencode"


def _deploy_acp_to_jetbrains(acp_src: Path, force: bool) -> int:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", "")) / "JetBrains"
        if not base.exists():
            print(f"{COLOR_YELLOW}[!] JetBrains config dir not found: {base}{COLOR_RESET}")
            return 0

        ide_pattern = re.compile(
            r"^(IntelliJIdea|WebStorm|PyCharm|PhpStorm|GoLand|Rider|CLion|"
            r"DataGrip|RubyMine|AppCode|DataSpell|Fleet|Aqua|RustRover|Writerside)",
            re.IGNORECASE,
        )

        copied = 0
        for ide_dir in sorted(base.iterdir()):
            if not ide_dir.is_dir():
                continue
            if not ide_pattern.match(ide_dir.name):
                continue

            target = ide_dir / "acp.json"
            if target.exists() and not force:
                print(f"{COLOR_DARKGRAY}[~] {ide_dir.name}: acp.json exists, skipping{COLOR_RESET}")
                continue

            try:
                import shutil
                shutil.copy2(str(acp_src), str(target))
                print(f"{COLOR_GREEN}[OK] {ide_dir.name} -> {target}{COLOR_RESET}")
                copied += 1
            except Exception as e:
                print(f"{COLOR_RED}[!] {ide_dir.name}: {e}{COLOR_RESET}")

        return copied
    else:
        # macOS / Linux: single global ~/.jetbrains/acp.json
        target = Path.home() / ".jetbrains" / "acp.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists() and not force:
            print(f"{COLOR_DARKGRAY}[~] ~/.jetbrains/acp.json exists, skipping{COLOR_RESET}")
            return 0

        try:
            import shutil
            shutil.copy2(str(acp_src), str(target))
            print(f"{COLOR_GREEN}[OK] -> {target}{COLOR_RESET}")
            return 1
        except Exception as e:
            print(f"{COLOR_RED}[!] ~/.jetbrains/acp.json: {e}{COLOR_RESET}")
            return 0


def init_idea(target_dir: Path, source_rules_dir: Path, source_mcp_file: Path,
              source_skills_dir: Path, source_agents_md: Path, force: bool) -> str | None:
    print(f"\n{COLOR_MAGENTA}--- IntelliJ IDEA (JetBrains) ---{COLOR_RESET}")

    source_dir = source_rules_dir.parent.parent
    acp_src = source_dir / "ide" / "idea" / "acp.json"

    idea_dir = target_dir / ".idea"
    idea_skills_dir = idea_dir / "skills"

    idea_dir.mkdir(parents=True, exist_ok=True)

    copy_skills_safe(source_skills_dir, idea_skills_dir, ".idea/skills/", force)

    write_skills_index(source_skills_dir, idea_skills_dir / "README.md", "IDEA", force)

    if not acp_src.exists():
        print(f"{COLOR_YELLOW}[!] acp.json source not found: {acp_src}{COLOR_RESET}")
        return "idea"

    copied = _deploy_acp_to_jetbrains(acp_src, force)

    if copied == 0:
        print(f"{COLOR_YELLOW}[!] No JetBrains IDE config dirs found or all skipped{COLOR_RESET}")
    else:
        print(f"{COLOR_GREEN}[OK] Deployed acp.json to {copied} JetBrains IDE(s){COLOR_RESET}")

    return "idea"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize IDE config (Cursor/Trae/trae-cn/trae-solo-cn/Codex/Claude/WorkBuddy/Qoder/OpenClaw/OpenCode/IDEA/Agent) from agents/ shared source"
    )
    parser.add_argument(
        "--target-dir", "-t",
        default="",
        help="Target project root directory (default: user home directory)"
    )
    parser.add_argument(
        "--source-dir", "-s",
        default="",
        help="Source directory containing agents/ (default: parent of scripts/)"
    )
    parser.add_argument(
        "--ide", "-i",
        choices=["Cursor", "Trae", "trae-cn", "trae-solo-cn", "Codex", "Claude", "WorkBuddy", "Qoder", "OpenClaw", "OpenCode", "IDEA", "Agents", "All"],
        default="All",
        help="Target IDE (default: All)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force overwrite existing config"
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent

    if args.source_dir:
        source_dir = Path(args.source_dir).resolve()
    else:
        source_dir = script_dir.parent.resolve()

    if args.target_dir:
        target_dir = Path(args.target_dir).resolve()
    else:
        target_dir = Path.home()

    # 优先从 .agents 目录加载，不存在则从 agents 加载
    source_agents_dir = source_dir / ".agents"
    if not source_agents_dir.exists():
        source_agents_dir = source_dir / "agents"
    source_rules_dir = source_agents_dir / "rules"
    source_mcp_file = source_agents_dir / "mcp" / "mcp.json"
    source_skills_dir = source_agents_dir / "skills"
    source_agents_md = source_dir / "AGENTS.md"

    write_banner("IDE Init Script (Copy Mode)", str(source_dir), str(target_dir), args.ide)
    test_prerequisites(source_dir, source_rules_dir)

    processed = set()

    if args.ide in ("Cursor", "All"):
        r = init_cursor(target_dir, source_rules_dir, source_mcp_file,
                        source_skills_dir, args.force)
        if r: processed.add(r)

    if args.ide in ("Trae", "All"):
        r = init_trae(target_dir, source_rules_dir, source_mcp_file,
                      source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("Agents", "All"):
        r = init_agents(target_dir, source_rules_dir, source_mcp_file,
                        source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("Codex", "All"):
        r = init_codex(target_dir, source_rules_dir, source_mcp_file,
                       source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("Claude", "All"):
        r = init_claude(target_dir, source_rules_dir, source_mcp_file,
                        source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("TraeCN", "trae-cn", "All"):
        r = init_trae_cn(target_dir, source_rules_dir, source_mcp_file,
                         source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("trae-solo-cn", "All"):
        r = init_trae_solo_cn(target_dir, source_rules_dir, source_mcp_file,
                              source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("WorkBuddy", "All"):
        r = init_workbuddy(target_dir, source_rules_dir, source_mcp_file,
                           source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("Qoder", "All"):
        r = init_qoder(target_dir, source_rules_dir, source_mcp_file,
                       source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("OpenClaw", "All"):
        r = init_openclaw(target_dir, source_rules_dir, source_mcp_file,
                          source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("OpenCode", "All"):
        r = init_opencode(target_dir, source_rules_dir, source_mcp_file,
                          source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    if args.ide in ("IDEA", "All"):
        r = init_idea(target_dir, source_rules_dir, source_mcp_file,
                      source_skills_dir, source_agents_md, args.force)
        if r: processed.add(r)

    print(f"\n{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")
    print(f"{COLOR_GREEN}  Init Complete!{COLOR_RESET}")
    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")
    print()

    print(f"{COLOR_YELLOW}Architecture (single source of truth):{COLOR_RESET}")
    print()
    print(f"  {COLOR_WHITE}agents/rules/            <-- SOURCE (edit here){COLOR_RESET}")
    arch_lines = {
        "agents":       ".agents/",
        "trae":         ".trae/",
        "trae-cn":      ".trae-cn/",
        "trae-solo-cn": ".trae-solo-cn/",
        "cursor":       ".cursor/",
        "codex":        ".codex/",
        "claude":       ".claude/",
        "workbuddy":    ".workbuddy/",
        "qoder":        ".qoder/",
        "openclaw":     ".openclaw/",
        "opencode":     ".opencode/",
        "idea":         ".idea/",
    }
    for key in sorted(arch_lines):
        if key in processed:
            print(f"  {COLOR_DARKGRAY}{arch_lines[key]}{key}/rules/    --Copy--> agents/rules/{COLOR_RESET}")
    if "trae" in processed:
        mcp_path = _get_ide_user_dir("Trae") / "mcp.json"
        print(f"  {COLOR_DARKGRAY}{mcp_path}  --Copy--> agents/mcp/mcp.json{COLOR_RESET}")
    if "trae-cn" in processed:
        mcp_path = _get_ide_user_dir("Trae CN") / "mcp.json"
        print(f"  {COLOR_DARKGRAY}{mcp_path}  --Copy--> agents/mcp/mcp.json{COLOR_RESET}")
    if "trae-solo-cn" in processed:
        mcp_path = _get_ide_user_dir("TRAE SOLO CN") / "mcp.json"
        print(f"  {COLOR_DARKGRAY}{mcp_path}  --Copy--> agents/mcp/mcp.json{COLOR_RESET}")
    if "cursor" in processed:
        print(f"  {COLOR_DARKGRAY}.cursor/mcp.json     (generated, mcpServers key){COLOR_RESET}")
    if "codex" in processed:
        print(f"  {COLOR_DARKGRAY}.codex/config.toml    (generated, TOML format){COLOR_RESET}")
    if "claude" in processed:
        print(f"  {COLOR_DARKGRAY}.claude/settings.json (generated, from template + env.json){COLOR_RESET}")
    if "opencode" in processed:
        print(f"  {COLOR_DARKGRAY}.opencode/opencode.json (generated, OpenCode format){COLOR_RESET}")
    if "idea" in processed:
        print(f"  {COLOR_DARKGRAY}JetBrains/*/acp.json     (copied, ACP agent config){COLOR_RESET}")
    print()

    print(f"{COLOR_YELLOW}Next steps:{COLOR_RESET}")
    print(f"  {COLOR_WHITE}1. Edit files in agents/ - changes need re-run to sync{COLOR_RESET}")
    print(f"  {COLOR_WHITE}2. Open project in your IDE{COLOR_RESET}")
    print(f"  {COLOR_WHITE}3. Check MCP server status in IDE settings{COLOR_RESET}")


if __name__ == "__main__":
    main()