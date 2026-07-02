#!/usr/bin/env python3
"""
插件管理器 - 用于解析和安装通用格式的插件
"""

import argparse
import csv
import json
import os
import subprocess
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


def _load_yaml_module():
    try:
        import yaml
        return yaml
    except ImportError:
        print(f"{COLOR_RED}[ERROR] PyYAML is required to read llm.yaml/mcp.yaml. Install: pip install pyyaml{COLOR_RESET}")
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
            _load_yaml_module().safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")


def load_plugin_config(plugin_path: Path) -> dict:
    """加载插件配置文件"""
    if not plugin_path.exists():
        print(f"{COLOR_RED}[!] 插件文件不存在: {plugin_path}{COLOR_RESET}", file=sys.stderr)
        sys.exit(1)

    with open(plugin_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_plugin_config(config: dict) -> bool:
    """验证插件配置格式"""
    required_fields = ["name", "version"]
    for field in required_fields:
        if field not in config:
            print(f"{COLOR_RED}[!] 缺少必需字段: {field}{COLOR_RESET}", file=sys.stderr)
            return False
    return True


def update_env_file(env_path: Path, plugin_config: dict) -> None:
    """更新环境变量文件"""
    if "envVars" not in plugin_config:
        return

    if not env_path.exists():
        print(f"{COLOR_YELLOW}[!] 环境变量文件不存在，创建新文件: {env_path}{COLOR_RESET}")
        env_config = {}
    else:
        env_config = load_env_config_file(env_path)

    # 更新环境变量
    updated = False
    for var_name, var_info in plugin_config["envVars"].items():
        if var_name not in env_config:
            default_value = var_info.get("default", "")
            env_config[var_name] = default_value
            print(f"{COLOR_YELLOW}[~] 添加环境变量: {var_name} = {default_value}{COLOR_RESET}")
            print(f"    描述: {var_info.get('description', '')}")
            updated = True
        else:
            print(f"{COLOR_DARKGRAY}[~] 环境变量已存在: {var_name}{COLOR_RESET}")

    if updated:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        save_env_config_file(env_path, env_config)
        print(f"{COLOR_GREEN}[OK] 环境变量文件已更新: {env_path}{COLOR_RESET}")


def update_mcp_template(mcp_template_path: Path, plugin_config: dict) -> None:
    """更新MCP配置模板"""
    if "mcpServers" not in plugin_config:
        return

    if not mcp_template_path.exists():
        print(f"{COLOR_YELLOW}[!] MCP模板文件不存在，创建新文件: {mcp_template_path}{COLOR_RESET}")
        mcp_config = {"mcpServers": {}}
    else:
        with open(mcp_template_path, "r", encoding="utf-8") as f:
            mcp_config = json.load(f)

    # 确保有mcpServers字段
    if "mcpServers" not in mcp_config:
        mcp_config["mcpServers"] = {}

    # 更新MCP服务器配置
    updated = False
    for server_name, server_config in plugin_config["mcpServers"].items():
        if server_name not in mcp_config["mcpServers"]:
            mcp_config["mcpServers"][server_name] = server_config
            print(f"{COLOR_GREEN}[+] 添加MCP服务器: {server_name}{COLOR_RESET}")
            updated = True
        else:
            print(f"{COLOR_DARKGRAY}[~] MCP服务器已存在: {server_name}{COLOR_RESET}")

    if updated:
        mcp_template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(mcp_template_path, "w", encoding="utf-8") as f:
            json.dump(mcp_config, f, indent=2, ensure_ascii=False)
        print(f"{COLOR_GREEN}[OK] MCP模板已更新: {mcp_template_path}{COLOR_RESET}")


def parse_shorthand(source_str: str) -> tuple[str, str]:
    """
    解析 owner/repo@skill 简写格式，返回 (source, skill)。
    - "vercel-labs/skills@find-skills" → ("vercel-labs/skills", "find-skills")
    - "vercel-labs/skills"             → ("vercel-labs/skills", "")
    - "find-skills"                    → ("", "find-skills")  # 无 /，当作 skill name
    - "git@github.com:owner/repo.git"  → ("git@github.com:owner/repo.git", "")  # git URL 不拆
    - "https://github.com/owner/repo"  → ("https://github.com/owner/repo", "")  # URL 不拆
    """
    if not source_str:
        return ("", "")

    stripped = source_str.strip()

    # URL / git URL / ssh URL：不解析 @ 简写
    if (stripped.startswith("http://")
            or stripped.startswith("https://")
            or stripped.startswith("git@")
            or stripped.startswith("ssh://")
            or stripped.startswith("git://")):
        return (stripped, "")

    # 无 /：当作简单 skill name
    if "/" not in stripped:
        return ("", stripped)

    # owner/repo 形式：检查最后一个 / 之后是否有 @
    last_slash_idx = stripped.rfind("/")
    after_slash = stripped[last_slash_idx + 1:]
    at_idx = after_slash.find("@")
    if at_idx >= 0:
        # 拆分 source 和 skill
        source = stripped[:last_slash_idx + 1 + at_idx]
        skill = after_slash[at_idx + 1:]
        return (source, skill)
    return (stripped, "")


def build_install_command(skill_config: dict or str, use_symlink: bool = False) -> tuple[str, str]:
    """构建安装命令，返回 (skill_name, install_command)

    use_symlink:
      - False（默认）：加 --copy 强制复制，避免 Trae 沙箱等环境下 symlink 创建失败
                       导致 npx fallback 到全局 ~/.agents/skills/，项目目录反而没有该 skill。
      - True：不加 --copy，使用 npx 默认行为（可能对部分 IDE 用 symlink）。

    支持的配置形式：
      - "find-skills"                                    → npx skills add find-skills --copy -y
      - "vercel-labs/skills"                             → npx skills add vercel-labs/skills --copy -y
      - "vercel-labs/skills@find-skills"                 → npx skills add vercel-labs/skills --skill find-skills --copy -y
      - "npx skills add owner/repo --skill foo -y"       → 原样执行（用户完整命令不强制改）
      - {"name": "foo", "source": "owner/repo", "skill": "foo"}
      - {"name": "foo", "source": "owner/repo@foo"}      → @ 简写，拆分后等价于上一行
      - {"name": "foo", "url": "https://..."}            → 第三方市场 URL
    """
    skill_name = ""
    # 默认 --copy 强制复制；启用 symlink 时留空
    copy_flag = "" if use_symlink else "--copy"

    if isinstance(skill_config, dict):
        # 对象格式
        explicit_skill = skill_config.get("skill", "")
        skill_name = explicit_skill or skill_config.get("name", "")
        source = skill_config.get("source", "")
        url = skill_config.get("url", "")

        if url:
            # 第三方市场 URL
            install_command = f"npx skills add {url} --skill {skill_name} {copy_flag} -y".strip()
        elif source:
            # 尝试从 source 解析 @ 简写（仅当未显式指定 skill 时）
            parsed_source, parsed_skill = parse_shorthand(source)
            if not explicit_skill and parsed_skill:
                # source 含 @ 简写，且未显式指定 skill → 用解析结果
                effective_source = parsed_source
                effective_skill = parsed_skill
                skill_name = effective_skill or skill_name
            else:
                effective_source = source
                effective_skill = explicit_skill

            if effective_skill:
                install_command = f"npx skills add {effective_source} --skill {effective_skill} {copy_flag} -y".strip()
            else:
                install_command = f"npx skills add {effective_source} {copy_flag} -y".strip()
        else:
            # 只有 skill name
            install_command = f"npx skills add {skill_name} {copy_flag} -y".strip()
    elif isinstance(skill_config, str):
        # 字符串格式
        if skill_config.startswith("npx"):
            # 完整命令，原样执行（用户明确写的命令不强制改）
            install_command = skill_config
            import re
            match = re.search(r'--skill\s+([^\s]+)', install_command)
            if match:
                skill_name = match.group(1)
            else:
                # 无 --skill，尝试解析 add 后的源是否含 @ 简写
                match = re.search(r'add\s+([^\s]+)', install_command)
                if match:
                    raw_source = match.group(1)
                    _, parsed_skill = parse_shorthand(raw_source)
                    skill_name = parsed_skill or raw_source
        else:
            # 简写或名称：尝试解析 @ 简写
            parsed_source, parsed_skill = parse_shorthand(skill_config)
            if parsed_source and parsed_skill:
                # owner/repo@skill 简写
                skill_name = parsed_skill
                install_command = f"npx skills add {parsed_source} --skill {parsed_skill} {copy_flag} -y".strip()
            elif parsed_source:
                # 仅 owner/repo，安装整个集合
                skill_name = parsed_source
                install_command = f"npx skills add {parsed_source} {copy_flag} -y".strip()
            else:
                # 仅 skill name
                skill_name = parsed_skill
                install_command = f"npx skills add {parsed_skill} {copy_flag} -y".strip()
    else:
        skill_name = str(skill_config)
        install_command = f"npx skills add {skill_name} {copy_flag} -y".strip()

    # 规范化：把多余空格压缩（copy_flag 为空时避免双空格）
    import re as _re
    install_command = _re.sub(r'\s+', ' ', install_command).strip()
    return skill_name, install_command


def install_skill(skill_config: dict or str, source_dir: Path = None, use_symlink: bool = False) -> None:
    """安装技能：优先检查本地缓存"""
    skill_name, install_command = build_install_command(skill_config, use_symlink=use_symlink)

    if not skill_name and source_dir:
        print(f"{COLOR_YELLOW}[!] Could not determine skill name, skipping{COLOR_RESET}")
        return

    if source_dir:
        dot_agents_skills_dir = source_dir / ".agents" / "skills"
        dot_agents_skills_dir.mkdir(parents=True, exist_ok=True)

        target_skill_dir = dot_agents_skills_dir / skill_name

        # 如果 .agents/skills 中已有该技能，就跳过更新
        if target_skill_dir.exists():
            print(f"{COLOR_DARKGRAY}[-] Skill already exists in .agents/skills: {skill_name}, skipping update{COLOR_RESET}")
            return

        # 检查 agents/skills 缓存
        cache_skill_dir = source_dir / "agents" / "skills" / skill_name
        if cache_skill_dir.exists():
            print(f"{COLOR_MAGENTA}[-] Installing skill from cache: {skill_name}{COLOR_RESET}")
            try:
                import shutil
                shutil.copytree(cache_skill_dir, target_skill_dir, ignore=shutil.ignore_patterns('.git'))
                print(f"{COLOR_GREEN}[OK] Skill copied from cache: {skill_name}{COLOR_RESET}")
                return
            except Exception as e:
                print(f"{COLOR_YELLOW}[!] Cache copy failed, will download from remote: {e}{COLOR_RESET}")

    # 从远程安装
    print(f"{COLOR_MAGENTA}[-] Installing skill: {install_command}{COLOR_RESET}")

    # npx skills add 默认安装到 cwd 下的 .agents/skills/，
    # 必须把工作目录设为项目根，否则会装到全局 ~/.agents/skills/ 或错误位置
    install_cwd = source_dir if source_dir else None

    try:
        result = subprocess.run(
            install_command,
            shell=True,
            capture_output=False,
            text=True,
            encoding='utf-8',
            errors='ignore',
            cwd=install_cwd
        )
        if result.returncode == 0:
            # 验证 skill 是否真的装到项目 .agents/skills/<name>
            if source_dir and skill_name:
                expected = source_dir / ".agents" / "skills" / skill_name
                if expected.exists():
                    print(f"{COLOR_GREEN}[OK] Skill installed successfully{COLOR_RESET}")
                else:
                    # npx 可能装到了全局 ~/.agents/skills/，提示用户
                    home_skill = Path.home() / ".agents" / "skills" / skill_name
                    if home_skill.exists():
                        print(f"{COLOR_YELLOW}[!] Skill installed to global dir: {home_skill}{COLOR_RESET}")
                        print(f"    期望位置: {expected}")
                        print(f"    可手动复制或加 -g 标志确认全局安装意图{COLOR_RESET}")
                    else:
                        print(f"{COLOR_YELLOW}[!] Skill install reported success but not found at: {expected}{COLOR_RESET}")
            else:
                print(f"{COLOR_GREEN}[OK] Skill installed successfully{COLOR_RESET}")
        else:
            print(f"{COLOR_RED}[!] Skill install failed (exit={result.returncode}){COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}[!] Skill install error: {e}{COLOR_RESET}")


def run_plugin_scripts(plugin_config: dict) -> None:
    """执行插件脚本

    注意：install 脚本失败或超时不阻塞后续 skill 安装，只告警。
    原因：scripts.install 常含 npm i -g / browser setup 等可能交互或耗时的命令，
    卡住或失败不应导致 skill 安装（步骤 4）无法执行。
    """
    if "scripts" not in plugin_config:
        return

    scripts = plugin_config["scripts"]

    # 执行 install 脚本
    if "install" in scripts:
        install_cmd = scripts["install"]
        print(f"{COLOR_MAGENTA}[~] 执行插件安装脚本: {install_cmd}{COLOR_RESET}")
        try:
            # 不 capture_output，让用户看到实时进度（避免交互式命令卡死时无任何输出）
            # 设置 timeout 防止交互式命令无限阻塞后续 skill 安装
            result = subprocess.run(
                install_cmd,
                shell=True,
                timeout=300,  # 5 分钟超时，避免 browser setup 卡死
                capture_output=False,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            if result.returncode == 0:
                print(f"{COLOR_GREEN}[OK] 脚本执行成功{COLOR_RESET}")
            else:
                # 失败不阻塞，继续安装 skill
                print(f"{COLOR_YELLOW}[!] 脚本执行失败 (exit={result.returncode})，继续安装 skill{COLOR_RESET}")
        except subprocess.TimeoutExpired:
            print(f"{COLOR_YELLOW}[!] 脚本执行超时 (>300s)，可能为交互式命令，继续安装 skill{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_YELLOW}[!] 脚本执行错误: {e}，继续安装 skill{COLOR_RESET}")


def install_skills(plugin_config: dict, source_dir: Path, use_symlink: bool = False) -> None:
    """安装插件所需技能"""
    if "skills" not in plugin_config:
        return

    skills = plugin_config["skills"]

    for skill in skills:
        install_skill(skill, source_dir, use_symlink=use_symlink)


def install_plugin(
    plugin_path: Path,
    env_path: Path,
    mcp_template_path: Path,
    source_dir: Path,
    dry_run: bool = False,
    use_symlink: bool = False
) -> None:
    """安装插件"""
    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")
    print(f"{COLOR_CYAN}  插件安装{COLOR_RESET}")
    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")

    # 加载和验证插件配置
    plugin_config = load_plugin_config(plugin_path)
    if not validate_plugin_config(plugin_config):
        sys.exit(1)

    # 显示插件信息
    print(f"\n{COLOR_WHITE}插件名称: {plugin_config.get('name', '')}{COLOR_RESET}")
    print(f"{COLOR_WHITE}版本: {plugin_config.get('version', '')}{COLOR_RESET}")
    print(f"{COLOR_WHITE}描述: {plugin_config.get('description', '')}{COLOR_RESET}")
    print(f"{COLOR_WHITE}作者: {plugin_config.get('author', '')}{COLOR_RESET}")

    if dry_run:
        print(f"\n{COLOR_YELLOW}[!] 这是模拟运行，不进行实际修改{COLOR_RESET}")
        return

    # 执行安装步骤
    print(f"\n{COLOR_MAGENTA}步骤 1/4: 更新环境变量{COLOR_RESET}")
    update_env_file(env_path, plugin_config)

    print(f"\n{COLOR_MAGENTA}步骤 2/4: 更新MCP配置{COLOR_RESET}")
    update_mcp_template(mcp_template_path, plugin_config)

    print(f"\n{COLOR_MAGENTA}步骤 3/4: 执行插件脚本{COLOR_RESET}")
    run_plugin_scripts(plugin_config)

    print(f"\n{COLOR_MAGENTA}步骤 4/4: 安装技能{COLOR_RESET}")
    install_skills(plugin_config, source_dir, use_symlink=use_symlink)

    print(f"\n{COLOR_GREEN}{'=' * 40}{COLOR_RESET}")
    print(f"{COLOR_GREEN}  插件安装完成！{COLOR_RESET}")
    print(f"{COLOR_GREEN}{'=' * 40}{COLOR_RESET}")
    print(f"\n{COLOR_YELLOW}下一步: {COLOR_RESET}")
    print(f"  {COLOR_WHITE}1. 运行 init-env.py 更新运行时配置{COLOR_RESET}")
    print(f"  {COLOR_WHITE}2. 运行 init-ide.py 同步到IDE{COLOR_RESET}")


def list_plugins(plugins_dir: Path) -> None:
    """列出可用的插件"""
    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")
    print(f"{COLOR_CYAN}  可用插件列表{COLOR_RESET}")
    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")

    if not plugins_dir.exists():
        print(f"{COLOR_YELLOW}[!] 插件目录不存在: {plugins_dir}{COLOR_RESET}")
        return

    # 查找插件文件
    plugin_files = []
    for file in plugins_dir.iterdir():
        if file.is_file() and file.suffix == ".json":
            try:
                with open(file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "name" in config and "version" in config:
                        plugin_files.append((file, config))
            except:
                continue

    if not plugin_files:
        print(f"{COLOR_YELLOW}[!] 没有找到有效的插件{COLOR_RESET}")
        return

    print(f"\n找到 {len(plugin_files)} 个插件:\n")
    for i, (file, config) in enumerate(plugin_files, 1):
        print(f"{COLOR_WHITE}{i}. {config.get('name', file.stem)}{COLOR_RESET}")
        print(f"   {COLOR_DARKGRAY}版本: {config.get('version', 'unknown')}{COLOR_RESET}")
        print(f"   {COLOR_DARKGRAY}描述: {config.get('description', '')}{COLOR_RESET}")
        print(f"   {COLOR_DARKGRAY}文件: {file}{COLOR_RESET}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="插件管理器 - 安装和管理通用格式的插件"
    )
    subparsers = parser.add_subparsers(title="命令", dest="command")

    # install 命令
    install_parser = subparsers.add_parser("install", help="安装插件")
    install_parser.add_argument(
        "plugin",
        help="插件文件路径"
    )
    install_parser.add_argument(
        "--env-file",
        default="llm.yaml",
        help="环境变量文件路径 (默认: llm.yaml)"
    )
    install_parser.add_argument(
        "--mcp-template",
        default="agents/mcp/mcp.template.json",
        help="MCP模板文件路径 (默认: agents/mcp/mcp.template.json)"
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不进行实际修改"
    )
    install_parser.add_argument(
        "--symlink",
        action="store_true",
        help="使用 symlink 安装 skill（默认 --copy 强制复制，避免沙箱环境下 symlink 失败导致装到全局）"
    )
    install_parser.add_argument(
        "--source-dir",
        default="",
        help="源目录路径 (默认: 当前目录)"
    )

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出可用插件")
    list_parser.add_argument(
        "--plugins-dir",
        default="agents/plugins",
        help="插件目录路径 (默认: agents/plugins)"
    )
    list_parser.add_argument(
        "--source-dir",
        default="",
        help="源目录路径 (默认: 当前目录)"
    )

    args = parser.parse_args()

    # 确定源目录
    if args.source_dir:
        source_dir = Path(args.source_dir).resolve()
    else:
        script_dir = Path(__file__).resolve().parent
        source_dir = script_dir.parent.resolve()

    if args.command == "install":
        plugin_path = Path(args.plugin).resolve()
        env_path = source_dir / args.env_file
        mcp_template_path = source_dir / args.mcp_template
        install_plugin(
            plugin_path,
            env_path,
            mcp_template_path,
            source_dir,
            args.dry_run,
            use_symlink=args.symlink
        )
    elif args.command == "list":
        plugins_dir = source_dir / args.plugins_dir
        list_plugins(plugins_dir)
    else:
        parser.print_help()


def load_skills_mapping(csv_path: Path) -> list[dict]:
    """从 skills-mapping.csv 加载技能映射"""
    skills = []
    if not csv_path.exists():
        print(f"{COLOR_YELLOW}[!] 技能映射文件不存在: {csv_path}{COLOR_RESET}")
        return skills

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            skills.append(row)

    return skills


def generate_plugin_from_csv(
    csv_path: Path,
    output_path: Path,
    plugin_name: str,
    plugin_description: str,
    category_filter: str = None
) -> None:
    """根据 skills-mapping.csv 生成插件配置"""
    skills = load_skills_mapping(csv_path)
    if not skills:
        print(f"{COLOR_RED}[!] 没有找到技能数据{COLOR_RESET}")
        return

    plugin_skills = []
    for skill in skills:
        # 如果指定了分类过滤
        if category_filter and skill.get("category") != category_filter:
            continue

        skill_name = skill.get("skill_name")
        source_type = skill.get("source_type", "local")
        source = skill.get("source", skill_name)
        description = skill.get("description", "")

        if source_type == "local":
            plugin_skills.append({
                "name": skill_name,
                "type": "local",
                "source": source,
                "description": description
            })
        else:
            # 构建完整的远程安装命令
            plugin_skills.append(f"npx skills add {source} --skill {skill_name} -y")

    plugin_config = {
        "name": plugin_name,
        "version": "1.0.0",
        "description": plugin_description,
        "author": "MyAgentPlugin",
        "mcpServers": {},
        "skills": plugin_skills
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plugin_config, f, indent=2, ensure_ascii=False)

    print(f"{COLOR_GREEN}[OK] 插件已生成: {output_path}{COLOR_RESET}")
    print(f"   包含 {len(plugin_skills)} 个技能")


def list_skills_from_csv(csv_path: Path) -> None:
    """从 skills-mapping.csv 列出所有技能"""
    skills = load_skills_mapping(csv_path)
    if not skills:
        return

    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")
    print(f"{COLOR_CYAN}  技能列表{COLOR_RESET}")
    print(f"{COLOR_CYAN}{'=' * 40}{COLOR_RESET}")

    # 按分类分组
    categories = {}
    for skill in skills:
        category = skill.get("category", "未分类")
        if category not in categories:
            categories[category] = []
        categories[category].append(skill)

    for category in sorted(categories.keys()):
        print(f"\n{COLOR_WHITE}## {category}{COLOR_RESET}")
        for skill in categories[category]:
            source_type = skill.get("source_type", "local")
            print(f"   - {skill.get('skill_name')} [{source_type}]")
            print(f"     {skill.get('description', '')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="插件管理器 - 安装和管理通用格式的插件"
    )
    subparsers = parser.add_subparsers(title="命令", dest="command")

    # install 命令
    install_parser = subparsers.add_parser("install", help="安装插件")
    install_parser.add_argument(
        "plugin",
        help="插件文件路径"
    )
    install_parser.add_argument(
        "--env-file",
        default="llm.yaml",
        help="环境变量文件路径 (默认: llm.yaml)"
    )
    install_parser.add_argument(
        "--mcp-template",
        default="agents/mcp/mcp.template.json",
        help="MCP模板文件路径 (默认: agents/mcp/mcp.template.json)"
    )
    install_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不进行实际修改"
    )
    install_parser.add_argument(
        "--symlink",
        action="store_true",
        help="使用 symlink 安装 skill（默认 --copy 强制复制，避免沙箱环境下 symlink 失败导致装到全局）"
    )
    install_parser.add_argument(
        "--source-dir",
        default="",
        help="源目录路径 (默认: 当前目录)"
    )

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出可用插件")
    list_parser.add_argument(
        "--plugins-dir",
        default="agents/plugins",
        help="插件目录路径 (默认: agents/plugins)"
    )
    list_parser.add_argument(
        "--source-dir",
        default="",
        help="源目录路径 (默认: 当前目录)"
    )

    # list-skills 命令
    list_skills_parser = subparsers.add_parser("list-skills", help="从 skills-mapping.csv 列出所有技能")
    list_skills_parser.add_argument(
        "--csv",
        default="doc/skills-mapping.csv",
        help="技能映射文件路径 (默认: doc/skills-mapping.csv)"
    )
    list_skills_parser.add_argument(
        "--source-dir",
        default="",
        help="源目录路径 (默认: 当前目录)"
    )

    # generate-plugin 命令
    generate_plugin_parser = subparsers.add_parser("generate-plugin", help="根据 skills-mapping.csv 生成插件")
    generate_plugin_parser.add_argument(
        "--csv",
        default="doc/skills-mapping.csv",
        help="技能映射文件路径 (默认: doc/skills-mapping.csv)"
    )
    generate_plugin_parser.add_argument(
        "--output",
        required=True,
        help="输出插件文件路径"
    )
    generate_plugin_parser.add_argument(
        "--name",
        required=True,
        help="插件名称"
    )
    generate_plugin_parser.add_argument(
        "--description",
        required=True,
        help="插件描述"
    )
    generate_plugin_parser.add_argument(
        "--category",
        help="按分类过滤技能 (可选)"
    )
    generate_plugin_parser.add_argument(
        "--source-dir",
        default="",
        help="源目录路径 (默认: 当前目录)"
    )

    args = parser.parse_args()

    # 确定源目录
    if args.source_dir:
        source_dir = Path(args.source_dir).resolve()
    else:
        script_dir = Path(__file__).resolve().parent
        source_dir = script_dir.parent.resolve()

    if args.command == "install":
        plugin_path = Path(args.plugin).resolve()
        env_path = source_dir / args.env_file
        mcp_template_path = source_dir / args.mcp_template
        install_plugin(
            plugin_path,
            env_path,
            mcp_template_path,
            source_dir,
            args.dry_run,
            use_symlink=args.symlink
        )
    elif args.command == "list":
        plugins_dir = source_dir / args.plugins_dir
        list_plugins(plugins_dir)
    elif args.command == "list-skills":
        csv_path = source_dir / args.csv
        list_skills_from_csv(csv_path)
    elif args.command == "generate-plugin":
        csv_path = source_dir / args.csv
        output_path = Path(args.output).resolve()
        generate_plugin_from_csv(
            csv_path,
            output_path,
            args.name,
            args.description,
            args.category
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
