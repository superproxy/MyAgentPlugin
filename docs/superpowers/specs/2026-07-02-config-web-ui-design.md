# 配置工具 Web UI 设计

**日期**: 2026-07-02
**状态**: Approved
**作者**: 用户 + Assistant

## 1. 背景与目标

为 `MyAgentPlugin` 仓库提供一个本地 Web 配置工具，替代纯 CLI 操作，让团队成员（前端/后端/设计/产品）能通过浏览器完成：

1. **env 配置**：可视化编辑 `env.yaml`（LLM providers、MCP 密钥、embedding/tts/asr/vision 等）
2. **插件组装**：从技能目录 + MCP 目录勾选，组装 `plugin.json` 定义并安装
3. **MCP 安装**：管理 MCP 服务器配置（本地预置 + 手动粘贴 Smithery/mcp.so 配置）
4. **Skill 安装**：搜索 skills.sh 市场 + 本地预置，一键安装到 `.agents/skills/`

## 2. 非目标

- 不做用户认证/多用户（纯本地工具）
- 不做云端部署（仅 `127.0.0.1` 本地服务）
- 不重新实现 `plugin-manager.py` / `init-env.py` 的逻辑，只做 UI 包装
- 不支持 MCP 市场的在线拉取（Smithery/mcp.so 无公开 API，只能手动粘贴配置）

## 3. 架构

### 3.1 目录结构

```
tools/
  ├── config_server.py        # Flask 后端，单文件，所有 API 路由
  ├── config_ui.html          # 单页前端，原生 HTML/JS/CSS，4 个页签
  └── README.md               # 启动说明
```

### 3.2 技术栈

- **后端**: Flask（单文件 `config_server.py`）
- **前端**: 原生 HTML + Vanilla JS + CSS（无构建工具、无 npm 依赖）
- **依赖**: `flask`、`pyyaml`、`requests`（pyyaml 已在用）

### 3.3 复用策略

后端通过 `sys.path.insert` 引入 `scripts/` 目录，直接 import 现有函数：

```python
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from plugin_manager import (
    load_plugin_config, install_plugin, build_install_command,
    load_env_config_file, save_env_config_file
)
from init_env import generate_mcp_json  # 复用 Generate 步骤
```

不重写、不复制现有逻辑。

## 4. 功能页签

### 4.1 Env 配置页

**布局**:
- 顶部：active provider 下拉 + active protocol 下拉
- LLM Providers 区：每个 provider（openicu/openrouter/openai/anthropic/deepseek/volcengine/volcengineCoding/volcengineAgent）折叠面板，内含 openai/anthropic 子协议的 `base_url`/`api_key` 输入框 + models 表格（增删改）
- MCP 密钥区：8 个 MCP key 表单（AMAP_MAPS_API_KEY、WECOM_WEBHOOK_URL、TAVILY_API_KEY、FIRECRAWL_API_KEY、YUQUE_TOKEN、STITCH_API_KEY、MASTERGO_MAGIC_TOKEN、CONTEXT7_API_KEY）
- 其他区：proxy（enable/base_url/api_key）、embedding、tts、asr、vision、misc 的字段
- 底部：「保存为 env.yaml」按钮（调用 `save_env_config_file`）

**API**:
- `GET /api/env` → 返回 env.yaml JSON
- `POST /api/env` → 保存 env.yaml

### 4.2 插件组装页

**布局**:
- 左侧（40%）：技能目录，从 `skills-mapping.csv` 渲染为可过滤列表
  - 顶部：category 下拉（浏览器/原型生成/API设计/...）+ role 下拉（Frontend/Backend/...）+ 搜索框
  - 列表项：复选框 + skill_name + category 标签 + description
- 中间（30%）：MCP 目录，从 `mcp.template.json` 的 `mcpServers` 渲染
  - 列表项：复选框 + server name + command/url 摘要
- 右侧（30%）：插件元信息 + 选中清单 + 操作按钮
  - 元信息表单：name（必填）、version（默认 1.0.0）、description、author
  - 已选 skills 列表（可移除）
  - 已选 mcp 列表（可移除）
  - 「预览 plugin.json」按钮 → 弹窗显示 JSON
  - 「保存为 plugin.json」按钮 → 写入 `agents/plugins/<name>.plugin.json`
  - 「安装插件」按钮 → 调用 `install_plugin()`，SSE 推送日志

**API**:
- `GET /api/skills/local` → 从 csv 返回本地技能列表
- `GET /api/mcp/list` → 返回 mcp.template.json 的 mcpServers
- `POST /api/plugin/save` → 保存 plugin.json 到 agents/plugins/
- `POST /api/plugin/install` (SSE) → 流式安装

### 4.3 MCP 安装页

**布局**:
- 顶部：市场源切换 Tab（ModelScope 市场 / 本地预置 / 手动添加）
- **ModelScope 市场 Tab**:
  - 搜索框（关键词，回车搜索）+ 分类筛选（可选）
  - 调用 `PUT https://www.modelscope.cn/openapi/v1/mcp/servers`（body: `{page_number, page_size, search}`）
  - 结果卡片：name、id（@owner/name）、description、author、分类标签
  - 「查看详情」按钮 → 调用 `GET /openapi/v1/mcp/servers/{owner}/{name}` 获取 `server_config`
  - 「添加到模板」按钮 → 把 server_config 转换为 mcp.template.json 中的条目
- **本地预置 Tab**:
  - 列表来自 `mcp.template.json` 的 `mcpServers`
  - 每条：name + command/url 摘要 + 启用/禁用开关（编辑 disabled 字段）+ 「编辑」+ 「删除」
  - 「保存到模板」按钮 → 写回 mcp.template.json
- **手动添加 Tab**:
  - 表单字段：name、command、args（逗号分隔）、type（stdio/http/streamableHttp）、url、headers（JSON 文本框）、env（JSON 文本框）
  - 「从 Smithery/mcp.so 配置粘贴」文本框：用户可粘贴复制的 JSON 配置，自动解析填充
  - 「添加」按钮 → 追加到模板
- 底部（全局）：「生成 mcp.json 运行态」按钮 → 调用 `init-env.py -a Generate`

**API**:
- `GET /api/mcp/list` → 返回 mcp.template.json
- `POST /api/mcp/save` → 保存 mcp.template.json
- `GET /api/mcp/search?q=&page=` → 代理调用 ModelScope OpenAPI（避免前端跨域）
- `GET /api/mcp/detail?owner=&name=` → 代理调用 ModelScope 详情 API，返回 server_config
- `POST /api/init-env` → 触发 init-env.py Generate

### 4.4 Skill 安装页

**布局**:
- 顶部：市场源切换 Tab（ModelScope 市场 / skills.sh / 本地预置）+ 搜索框
- **ModelScope 市场 Tab**（默认）:
  - 调用 `GET https://www.modelscope.cn/openapi/v1/skills?page_number=1&page_size=20&search=<q>`
  - 结果卡片：name、source（owner/repo）、description、install_count、license
  - 每条返回 `install_command`（npx/curl/pip 三种），优先使用 npx
  - 「安装」按钮 → 执行 install_command（加 `--copy`），SSE 推送日志
- **skills.sh Tab**:
  - 调用 `GET https://skills.sh/api/search?q=<query>`（公开端点）
  - 失败时前端显示「skills.sh 不可达，请用 ModelScope 或本地」
- **本地预置 Tab**:
  - 从 `skills-mapping.csv` 渲染，可按 category/role 过滤
  - 「安装」按钮 → 从 `agents/skills/` 缓存复制到 `.agents/skills/`
- **手动输入区**（始终可见）:
  - 文本框：用户可直接输入 `owner/repo`、`owner/repo@skill` 或完整 GitHub URL
  - 「安装」按钮 → 执行 `npx skills add <source> --skill <name> --copy -y`
- 下半：已装技能列表（扫描 `.agents/skills/` 目录）
  - 每条：skill name + 路径 + 「查看 SKILL.md」按钮（弹窗显示）+ 「卸载」按钮（删除目录）
- 底部：「同步到 IDE」按钮 → 调用 `init-ide.py --ide All`

**API**:
- `GET /api/skills/local` → 本地 csv
- `GET /api/skills/search?q=&source=` → source: modelscope|skillssh，聚合搜索
- `GET /api/skills/installed` → 扫描 .agents/skills/
- `POST /api/skills/install` (SSE) → 流式执行 npx skills add
- `DELETE /api/skills/<name>` → 删除 .agents/skills/<name>
- `POST /api/init-ide` → 触发 init-ide.py

## 5. API 汇总

| 端点 | 方法 | 用途 | 流式 |
|---|---|---|---|
| `/api/env` | GET | 读取 env.yaml | 否 |
| `/api/env` | POST | 保存 env.yaml | 否 |
| `/api/skills/local` | GET | 本地技能 csv | 否 |
| `/api/skills/search` | GET | skills.sh 搜索 | 否 |
| `/api/skills/installed` | GET | 已装技能扫描 | 否 |
| `/api/skills/install` | POST | npx skills add | SSE |
| `/api/skills/<name>` | DELETE | 卸载技能 | 否 |
| `/api/mcp/list` | GET | mcp.template.json | 否 |
| `/api/mcp/save` | POST | 保存 mcp.template.json | 否 |
| `/api/plugins` | GET | 列出 agents/plugins/ | 否 |
| `/api/plugin/save` | POST | 保存 plugin.json | 否 |
| `/api/plugin/install` | POST | 安装插件 | SSE |
| `/api/init-env` | POST | 触发 init-env.py Generate | 否 |
| `/api/init-ide` | POST | 触发 init-ide.py | SSE |
| `/` | GET | 返回 config_ui.html | 否 |

## 6. 安装执行策略

- 所有 `npx`/`subprocess` 调用走 **Server-Sent Events (SSE)** 推送实时日志到前端
- 复用 `plugin-manager.py` 的 `--copy` 强制复制策略，避免 Trae 沙箱下 symlink 失败
- 单个安装超时 5 分钟，失败不阻塞其他安装
- 后端用 `subprocess.Popen` 启动子进程，逐行读取 stdout/stderr 推给前端

## 7. 启动方式

```bash
# 安装依赖（一次性）
pip install flask pyyaml requests

# 启动
python tools/config_server.py
# 自动打开浏览器到 http://127.0.0.1:5000
```

`config_server.py` 启动时:
- 检测依赖缺失则打印安装提示并退出
- 默认绑定 `127.0.0.1:5000`，可用 `--port` / `--host` 覆盖
- 启动后调用 `webbrowser.open()` 自动打开

## 8. 错误处理

- env.yaml 不存在 → 自动从 env.example.yaml 复制
- skills.sh API 失败 → 前端显示「搜索失败，已切换到本地列表」+ 本地 csv 数据
- npx 命令不存在 → 前端提示「请先安装 Node.js」
- 子进程超时 → 推送 `[TIMEOUT]` 日志并结束 SSE
- 保存文件失败（权限/路径）→ 返回 500 + 错误详情

## 9. 测试

- 手动测试为主（Web UI 工具，无自动化测试需求）
- 启动后逐页签验证：env 保存、插件生成、MCP 编辑、skill 搜索安装
- 验证生成的文件可被现有 `init-env.py` / `init-ide.py` / `plugin-manager.py` CLI 正常消费

## 10. 范围确认

**已确认的设计决策**:
1. 文件位置 = `tools/` 目录（与 `scripts/` 平级）
2. **MCP 市场源**:
   - 主源 = ModelScope OpenAPI (`PUT /openapi/v1/mcp/servers` 列表 + `GET /openapi/v1/mcp/servers/{owner}/{name}` 详情，返回 server_config)
   - 补充 = 手动粘贴 Smithery/mcp.so 配置
   - 本地预置 = `mcp.template.json` 已有条目
3. **Skill 市场源**:
   - 主源 = ModelScope OpenAPI (`GET /openapi/v1/skills?search=<q>`)，返回 install_command
   - 备源 = skills.sh (`GET /api/search?q=<q>`)
   - 本地预置 = `skills-mapping.csv` + `agents/skills/` 缓存
   - 手动 = 输入 `owner/repo` 或 GitHub URL
4. 所有外部 API 由后端代理调用（前端不跨域，统一错误处理 + 超时控制）
