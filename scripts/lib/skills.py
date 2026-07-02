"""技能安装与同步。

迁移自 scripts/init-ide.py（copy_skills_safe / write_skills_index，含白名单过滤）+
scripts/plugin-manager.py（parse_shorthand / build_install_command / install_skill）。
保持函数签名与行为不变。

INCLUDE_SKILLS 全局变量改为函数参数 include_skills，避免模块级状态。
"""
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

from lib.logging import (
    COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_DARKGRAY, COLOR_MAGENTA, COLOR_RESET,
)

H1 = "## "
H2 = "### "
H3 = "#### "


# ============================================================
# Skill 同步（含白名单过滤）
# ============================================================

def copy_skills_safe(src: Path, dst: Path, label: str, force: bool,
                     include_skills=None) -> None:
    """复制技能目录到 IDE skills 目录。

    Args:
        include_skills: 白名单集合，仅复制名称在此集合内的技能；
                        None 表示复制全部。
    """
    if not src.exists():
        print(f"{COLOR_YELLOW}[!] Skills source dir not found: {src}{COLOR_RESET}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for skill_dir in sorted(src.iterdir()):
        if not skill_dir.is_dir():
            continue
        # 按白名单过滤
        if include_skills is not None and skill_dir.name not in include_skills:
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


def load_skill_mapping(csv_path: Path) -> dict:
    """Load skill-to-role mapping from CSV file."""
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


def build_role_mapping_table(mapping: dict) -> list:
    """Build role-to-skills mapping table lines from CSV data."""
    role_skills: dict = {}
    installable_skills: list = []
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


def write_skills_index(skills_source_dir: Path, target_file: Path, ide_name: str, force: bool,
                       include_skills=None) -> None:
    """生成技能索引 README.md。

    Args:
        include_skills: 白名单集合，仅索引名称在此集合内的技能；
                        None 表示索引全部。
    """
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
    lines.append("Auto-generated by agentctl. Lists all available AI skills.")
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
        # 按白名单过滤
        if include_skills is not None and skill_dir.name not in include_skills:
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
    csv_path = skills_source_dir.parent.parent / "skills-index.csv"
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


# ============================================================
# Skill 安装（来自 plugin-manager.py）
# ============================================================

def parse_shorthand(source_str: str) -> tuple:
    """解析 owner/repo@skill 简写格式，返回 (source, skill)。"""
    if not source_str:
        return ("", "")

    stripped = source_str.strip()

    if (stripped.startswith("http://")
            or stripped.startswith("https://")
            or stripped.startswith("git@")
            or stripped.startswith("ssh://")
            or stripped.startswith("git://")):
        return (stripped, "")

    if "/" not in stripped:
        return ("", stripped)

    last_slash_idx = stripped.rfind("/")
    after_slash = stripped[last_slash_idx + 1:]
    at_idx = after_slash.find("@")
    if at_idx >= 0:
        source = stripped[:last_slash_idx + 1 + at_idx]
        skill = after_slash[at_idx + 1:]
        return (source, skill)
    return (stripped, "")


def build_install_command(skill_config, use_symlink: bool = False) -> tuple:
    """构建安装命令，返回 (skill_name, install_command)。"""
    skill_name = ""
    copy_flag = "" if use_symlink else "--copy"

    if isinstance(skill_config, dict):
        explicit_skill = skill_config.get("skill", "")
        skill_name = explicit_skill or skill_config.get("name", "")
        source = skill_config.get("source", "")
        url = skill_config.get("url", "")

        if url:
            install_command = f"npx skills add {url} --skill {skill_name} {copy_flag} -y".strip()
        elif source:
            parsed_source, parsed_skill = parse_shorthand(source)
            if not explicit_skill and parsed_skill:
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
            install_command = f"npx skills add {skill_name} {copy_flag} -y".strip()
    elif isinstance(skill_config, str):
        if skill_config.startswith("npx"):
            install_command = skill_config
            match = re.search(r'--skill\s+([^\s]+)', install_command)
            if match:
                skill_name = match.group(1)
            else:
                match = re.search(r'add\s+([^\s]+)', install_command)
                if match:
                    raw_source = match.group(1)
                    _, parsed_skill = parse_shorthand(raw_source)
                    skill_name = parsed_skill or raw_source
        else:
            parsed_source, parsed_skill = parse_shorthand(skill_config)
            if parsed_source and parsed_skill:
                skill_name = parsed_skill
                install_command = f"npx skills add {parsed_source} --skill {parsed_skill} {copy_flag} -y".strip()
            elif parsed_source:
                skill_name = parsed_source
                install_command = f"npx skills add {parsed_source} {copy_flag} -y".strip()
            else:
                skill_name = parsed_skill
                install_command = f"npx skills add {parsed_skill} {copy_flag} -y".strip()
    else:
        skill_name = str(skill_config)
        install_command = f"npx skills add {skill_name} {copy_flag} -y".strip()

    install_command = re.sub(r'\s+', ' ', install_command).strip()
    return skill_name, install_command


def install_skill(skill_config, source_dir: Path = None, use_symlink: bool = False) -> None:
    """安装技能：优先检查本地缓存，再从远程安装。"""
    skill_name, install_command = build_install_command(skill_config, use_symlink=use_symlink)

    if not skill_name and source_dir:
        print(f"{COLOR_YELLOW}[!] Could not determine skill name, skipping{COLOR_RESET}")
        return

    if source_dir:
        dot_agents_skills_dir = source_dir / ".agents" / "skills"
        dot_agents_skills_dir.mkdir(parents=True, exist_ok=True)

        target_skill_dir = dot_agents_skills_dir / skill_name

        if target_skill_dir.exists():
            print(f"{COLOR_DARKGRAY}[-] Skill already exists in .agents/skills: {skill_name}, skipping update{COLOR_RESET}")
            return

        cache_skill_dir = source_dir / "agents" / "skills" / skill_name
        if cache_skill_dir.exists():
            print(f"{COLOR_MAGENTA}[-] Installing skill from cache: {skill_name}{COLOR_RESET}")
            try:
                shutil.copytree(cache_skill_dir, target_skill_dir, ignore=shutil.ignore_patterns('.git'))
                print(f"{COLOR_GREEN}[OK] Skill copied from cache: {skill_name}{COLOR_RESET}")
                return
            except Exception as e:
                print(f"{COLOR_YELLOW}[!] Cache copy failed, will download from remote: {e}{COLOR_RESET}")

    print(f"{COLOR_MAGENTA}[-] Installing skill: {install_command}{COLOR_RESET}")

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
            if source_dir and skill_name:
                expected = source_dir / ".agents" / "skills" / skill_name
                if expected.exists():
                    print(f"{COLOR_GREEN}[OK] Skill installed successfully{COLOR_RESET}")
                else:
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
