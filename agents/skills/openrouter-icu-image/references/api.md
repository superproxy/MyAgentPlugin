# Openrouter ICU 生图指南

适用范围：

- `POST https://openrouter.icu/v1/images/generations`
- `POST https://openrouter.icu/v1/images/edits`

目标：

- HTTP Base URL 使用 `https://openrouter.icu`，完整端点是 `https://openrouter.icu/v1/images/...`。
- OpenAI SDK `base_url` 使用 `https://openrouter.icu/v1`。
- 本 skill 的 CLI `--base-url` 同时接受 `https://openrouter.icu` 和 `https://openrouter.icu/v1`。
- 默认使用 `gpt-image-2`。
- 默认启用 streaming：`stream: true`，`partial_images: 2`。
- 用户没有指定质量时使用 `quality: "medium"`。
- 用户没有指定输出格式时使用 `output_format: "png"`。
- 缺少 `OPENROUTER_ICU_API_KEY` 时先询问用户提供 key，不发起请求。
- 显式设置 `size`、`quality`、`output_format`。
- 只在确认响应包含图片字段后解码 base64。
- API 控制信息留在请求参数和代码里，不要混进图片 `prompt`。
- 生图必须同步执行：不要后台运行或分离请求进程；必须等最终图片写入本地文件后再继续后续步骤或回复用户。

## 1. API 选择

| 场景 | 使用 |
|---|---|
| 文本生成图片 | `/v1/images/generations` |
| 本地图片编辑 | `/v1/images/edits` + multipart `image[]=@file.png` |
| 多张参考图生成 | `/v1/images/edits` + 多个 `image[]` 或 JSON `images` |
| 需要可感知进度 | `stream=true` + `partial_images=2` |

## 2. Prompt 边界

图片 `prompt` 只描述图像目标。请求参数、代码逻辑和运行时处理留在 API 参数或调用代码中。

- 主体、场景、构图、镜头、材质、光线、风格。
- 编辑意图，例如“保留人物和衣服，只替换背景”。
- 明确的负向视觉约束，例如“不要改变产品包装文字”。

示例：

```text
Change the background to a clean modern office while preserving the person, clothing, pose, and facial features.
```

## 3. 默认参数

通用默认值：

```json
{
  "model": "gpt-image-2",
  "size": "1024x1024",
  "quality": "medium",
  "output_format": "png",
  "stream": true,
  "partial_images": 2
}
```

### CLI 参数映射

本 skill 的脚本是：

```bash
python3 scripts/openrouter_icu_image.py
```

从 skill 目录运行脚本，或按实际安装位置传入脚本路径。使用 Python 3 启动器：macOS/Linux 通常用 `python3 scripts/openrouter_icu_image.py`；Windows PowerShell/CMD 通常用 `py -3 scripts\openrouter_icu_image.py`，没有 Python launcher 时可用指向 Python 3 的 `python scripts\openrouter_icu_image.py`。脚本只使用 Python 标准库，不依赖 Bash、curl、chmod 或 POSIX 文件权限。

CLI 参数使用短横线形式，同时也接受 API 风格的下划线别名。请求 payload 仍使用 API 参数名。

脚本默认同步阻塞：HTTP 响应完成、SSE 解析完成、最终图片解码并写入 `--output` 后才退出。调用时不要后台运行、分离进程、启动隐藏终端或使用异步任务让主 agent 继续运行。若终端工具返回 live session，需要持续读取该 session，直到进程退出并确认输出文件存在。

| CLI 参数 | API / multipart 参数 |
|---|---|
| `generate` 子命令 | `POST /v1/images/generations` |
| `edit` 子命令 | `POST /v1/images/edits` |
| `--prompt` | `prompt` |
| `--model` | `model` |
| `--size` | `size` |
| `--quality` | `quality` |
| `--n` | `n` |
| `--output-format` / `--output_format` | `output_format` |
| `--output-compression` / `--output_compression` | `output_compression` |
| `--moderation` | `moderation` |
| `--user` | `user` |
| `--stream`, `--stream true`, `--stream false` | `stream` |
| `--no-stream` / `--no_stream` | `stream=false` |
| 默认 streaming | `stream=true` |
| `--partial-images` / `--partial_images` | `partial_images`，仅 streaming 时发送 |
| `--image` / `--image-file` | multipart `image[]` |
| `--file-id` / `--file_id` | JSON `images[].file_id` |
| `--image-url` / `--image_url` | JSON `images[].image_url` |
| `--output` | 本地保存路径，不发送到 API |
| `--events-output` / `--events_output` | 本地调试日志路径，不发送到 API |
| `--dry-run` | 本地检查请求形状，不发送到 API |

## 4. 尺寸与质量

### `size`

常用尺寸：

- `1024x1024`
- `1536x1024`
- `1024x1536`
- `2048x2048`
- `2048x1152`
- `3840x2160`
- `2160x3840`
- `auto`

自定义尺寸规则：

- 格式：`WIDTHxHEIGHT`
- 宽和高都必须能被 16 整除。
- 宽高比必须在 `1:3` 到 `3:1` 之间。
- 最大分辨率不超过 `3840x2160` 的像素约束。
- 超过 `2560x1440` 的尺寸只在确实需要高分辨率时使用。

### `quality`

| 值 | 用途 |
|---|---|
| `low` | 草稿、缩略图、快速预览 |
| `medium` | Web 预览、普通成图 |
| `high` | 最终资产 |
| `auto` | 让模型选择 |

## 5. `/v1/images/generations`

用途：根据文本生成图片。

### 参数

| 参数 | 必填 | 说明 |
|---|---:|---|
| `prompt` | 是 | 只放图像目标描述。 |
| `model` | 否 | 默认 `gpt-image-2`。 |
| `size` | 否 | 输出尺寸。 |
| `quality` | 否 | `low`、`medium`、`high`、`auto`。 |
| `n` | 否 | 生成数量。 |
| `output_format` | 否 | 默认 `png`；可选 `jpeg`、`webp`。 |
| `output_compression` | 否 | 0-100，仅 `jpeg` / `webp` 使用。 |
| `moderation` | 否 | `auto` 或 `low`。 |
| `stream` | 否 | 默认设为 `true`。 |
| `partial_images` | 否 | 默认设为 `2`，范围 0-3。 |
| `user` | 否 | 终端用户 ID。 |

### 流式 curl

```bash
events="$(mktemp)"

curl -sS -N \
  https://openrouter.icu/v1/images/generations \
  -H "Authorization: Bearer $OPENROUTER_ICU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "prompt": "A clean product photo of a white ceramic coffee mug on a wooden desk, soft natural light",
    "size": "1024x1024",
    "quality": "medium",
    "output_format": "png",
    "stream": true,
    "partial_images": 2
  }' > "$events"
```

用第 7 节的 SSE 解析器保存图片。

## 6. `/v1/images/edits`

用途：根据输入图片和文本说明生成编辑后的图片。

### 参数

| 参数 | 必填 | 说明 |
|---|---:|---|
| `image[]` | 本地文件时是 | multipart 上传本地输入图。可传多个。 |
| `images` | JSON 引用时是 | JSON body 中的 `file_id` 或 `image_url` 数组。 |
| `prompt` | 是 | 只放视觉编辑目标。 |
| `model` | 否 | 默认 `gpt-image-2`。 |
| `size` | 否 | 输出尺寸。 |
| `quality` | 否 | `low`、`medium`、`high`、`auto`。 |
| `n` | 否 | 生成数量。 |
| `output_format` | 否 | 默认 `png`；可选 `jpeg`、`webp`。 |
| `output_compression` | 否 | 0-100，仅 `jpeg` / `webp` 使用。 |
| `moderation` | 否 | `auto` 或 `low`。 |
| `stream` | 否 | 默认设为 `true`。 |
| `partial_images` | 否 | 默认设为 `2`，范围 0-3。 |
| `user` | 否 | 终端用户 ID。 |

### 本地图片编辑，流式

```bash
events="$(mktemp)"

curl -sS -N \
  -X POST https://openrouter.icu/v1/images/edits \
  -H "Authorization: Bearer $OPENROUTER_ICU_API_KEY" \
  -F "model=gpt-image-2" \
  -F "image[]=@input.png" \
  -F "prompt=Change the background to a clean modern office while preserving the subject, clothing, pose, and facial features" \
  -F "size=1024x1024" \
  -F "quality=medium" \
  -F "output_format=png" \
  -F "stream=true" \
  -F "partial_images=2" > "$events"
```

用第 7 节的 SSE 解析器保存图片。

### 多图参考

```bash
events="$(mktemp)"

curl -sS -N \
  -X POST https://openrouter.icu/v1/images/edits \
  -H "Authorization: Bearer $OPENROUTER_ICU_API_KEY" \
  -F "model=gpt-image-2" \
  -F "image[]=@product.png" \
  -F "image[]=@background-reference.png" \
  -F "prompt=Create a premium product photo using the product from the first image and the environment style from the second image" \
  -F "size=1024x1024" \
  -F "quality=medium" \
  -F "output_format=png" \
  -F "stream=true" \
  -F "partial_images=2" > "$events"
```

### JSON 图片引用

```bash
events="$(mktemp)"

curl -sS -N \
  https://openrouter.icu/v1/images/edits \
  -H "Authorization: Bearer $OPENROUTER_ICU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-image-2",
    "images": [
      { "file_id": "file_abc123" },
      { "image_url": "https://example.com/input.png" }
    ],
    "prompt": "Create a premium product photo using these visual references",
    "size": "1024x1024",
    "quality": "medium",
    "output_format": "png",
    "stream": true,
    "partial_images": 2
  }' > "$events"
```

## 7. SSE 解析器

首选使用 `scripts/openrouter_icu_image.py`，它在 Windows、macOS 和 Linux 上都可解析 streaming SSE 并保存最终图片。

如果只需要手动解析已经保存的 SSE 文本，对 streaming 响应只解码图片事件中的 base64 字段。遇到 error / failed event 直接退出。下面是 Unix shell 参考片段，不是跨平台推荐路径：

```bash
python3 - "$events" image-output <<'PY'
import base64
import json
import sys

events_path, output_prefix = sys.argv[1], sys.argv[2]
with open(events_path, "r", encoding="utf-8", errors="replace") as f:
    text = f.read()

events = []
block = []

def flush():
    if not block:
        return
    payload = "\n".join(
        line[5:].lstrip()
        for line in block
        if line.startswith("data:")
    ).strip()
    block.clear()
    if not payload or payload == "[DONE]":
        return
    try:
        events.append(json.loads(payload))
    except json.JSONDecodeError:
        print(f"Skipping non-JSON SSE payload: {payload[:200]}", file=sys.stderr)

for line in text.splitlines():
    if line.strip() == "":
        flush()
    else:
        block.append(line)
flush()

if not events:
    print("No parseable SSE events found.", file=sys.stderr)
    raise SystemExit(1)

for event in events:
    event_type = str(event.get("type", ""))
    if "error" in event or event_type.endswith(".failed") or "error" in event_type:
        print("Openrouter ICU stream error event:", file=sys.stderr)
        print(json.dumps(event, indent=2, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)

written = 0
for event in events:
    b64 = event.get("b64_json") or event.get("partial_image_b64")
    if not b64:
        continue
    written += 1
    with open(f"{output_prefix}-{written}.png", "wb") as f:
        f.write(base64.b64decode(b64))

if written == 0:
    print("No image payload found in SSE stream.", file=sys.stderr)
    print(json.dumps(events[-5:], indent=2, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(1)
PY
```

## 8. SDK 示例

### Node.js

```js
import fs from "node:fs";
import OpenAI from "openai";

const openai = new OpenAI({
  baseURL: "https://openrouter.icu/v1",
  apiKey: process.env.OPENROUTER_ICU_API_KEY,
});

try {
  const stream = await openai.images.generate({
    model: "gpt-image-2",
    prompt: "A clean product photo of a white ceramic coffee mug on a wooden desk",
    size: "1024x1024",
    quality: "medium",
    output_format: "png",
    stream: true,
    partial_images: 2,
  });

  for await (const event of stream) {
    if (event.type?.includes("failed") || event.error) {
      throw new Error(JSON.stringify(event.error ?? event));
    }

    if (
      event.type === "image_generation.partial_image" ||
      event.type === "image_generation.completed"
    ) {
      const b64 = event.b64_json;
      if (!b64) continue;
      const index = event.partial_image_index ?? "final";
      fs.writeFileSync(`image-${index}.png`, Buffer.from(b64, "base64"));
    }
  }
} catch (error) {
  console.error("Openrouter ICU image generation failed:", error);
  process.exitCode = 1;
}
```

### Python

```python
import base64
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.icu/v1",
    api_key=os.environ["OPENROUTER_ICU_API_KEY"],
)

try:
    stream = client.images.generate(
        model="gpt-image-2",
        prompt="A clean product photo of a white ceramic coffee mug on a wooden desk",
        size="1024x1024",
        quality="medium",
        output_format="png",
        stream=True,
        partial_images=2,
    )

    for event in stream:
        event_type = getattr(event, "type", "")
        if event_type.endswith(".failed") or getattr(event, "error", None):
            raise RuntimeError(event)

        if event_type in ("image_generation.partial_image", "image_generation.completed"):
            b64 = getattr(event, "b64_json", None)
            if not b64:
                continue
            index = getattr(event, "partial_image_index", "final")
            with open(f"image-{index}.png", "wb") as f:
                f.write(base64.b64decode(b64))
except Exception as exc:
    print(f"Openrouter ICU image generation failed: {exc}")
    raise
```

## 9. 错误处理

| HTTP 状态 | 处理 |
|---:|---|
| 400 | 打印完整错误 JSON，修正参数，不重试。 |
| 401 | 检查 `OPENROUTER_ICU_API_KEY`；如果用户没有提供 key，询问用户提供 key。 |
| 403 / 404 | 打印完整错误 JSON，检查模型、文件 ID、权限。 |
| 408 / 409 | 有限重试。 |
| 429 | 指数退避，降低并发。 |
| 500 / 502 / 503 | 指数退避重试，保留 `x-request-id`。 |

记录这些调试字段：

- `OPENROUTER_ICU_API_KEY` 是否存在
- HTTP status
- `x-request-id`
- 完整错误 JSON
- `model`
- `size`
- `quality`
- `output_format`
- 是否 streaming
- 最后收到的 SSE event type
