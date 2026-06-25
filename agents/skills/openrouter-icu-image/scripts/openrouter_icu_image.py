#!/usr/bin/env python3
"""Generate or edit images with the OpenRouter ICU image API."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


BASE_URL = "https://openrouter.icu"
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "medium"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_PARTIAL_IMAGES = 2
MAX_PIXELS = 3840 * 2160
RETRY_STATUSES = {408, 409, 429, 500, 502, 503, 504}


class OpenRouterImageError(RuntimeError):
    """Raised for expected API and response handling failures."""


def configure_standard_streams() -> None:
    """Use UTF-8 console streams where Python exposes reconfigure()."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


class BooleanOptionalValueAction(argparse.Action):
    """Accept --flag, --flag true, and --flag false forms."""

    TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
    FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | None,
        option_string: str | None = None,
    ) -> None:
        if values is None:
            setattr(namespace, self.dest, True)
            return
        normalized = values.lower()
        if normalized in self.TRUE_VALUES:
            setattr(namespace, self.dest, True)
            return
        if normalized in self.FALSE_VALUES:
            setattr(namespace, self.dest, False)
            return
        parser.error(f"{option_string} expects one of true/false, yes/no, on/off, or 1/0")


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def compression_value(value: str) -> int:
    parsed = int(value)
    if not 0 <= parsed <= 100:
        raise argparse.ArgumentTypeError("must be between 0 and 100")
    return parsed


def partial_images_value(value: str) -> int:
    parsed = int(value)
    if not 0 <= parsed <= 3:
        raise argparse.ArgumentTypeError("must be between 0 and 3")
    return parsed


def validate_size(value: str) -> str:
    if value == "auto":
        return value

    match = re.fullmatch(r"(\d+)x(\d+)", value)
    if not match:
        raise argparse.ArgumentTypeError("size must be auto or WIDTHxHEIGHT")

    width = int(match.group(1))
    height = int(match.group(2))
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("width and height must be positive")
    if width % 16 or height % 16:
        raise argparse.ArgumentTypeError("width and height must be divisible by 16")

    ratio = width / height
    if ratio < 1 / 3 or ratio > 3:
        raise argparse.ArgumentTypeError("aspect ratio must be between 1:3 and 3:1")
    if width * height > MAX_PIXELS:
        raise argparse.ArgumentTypeError("pixel count must not exceed 3840x2160")

    return value


def parse_header_pairs(values: list[str] | None) -> dict[str, str]:
    headers: dict[str, str] = {}
    for raw in values or []:
        if ":" not in raw:
            raise argparse.ArgumentTypeError(f"header must be NAME:VALUE, got {raw!r}")
        name, value = raw.split(":", 1)
        name = name.strip()
        if not name:
            raise argparse.ArgumentTypeError(f"header name is empty in {raw!r}")
        headers[name] = value.strip()
    return headers


def output_paths(output: Path, count: int, output_format: str) -> list[Path]:
    suffix = "." + output_format
    if count == 1:
        return [with_suffix(output, suffix)]

    stem_path = output
    if stem_path.suffix:
        stem_path = stem_path.with_suffix("")
    return [stem_path.with_name(f"{stem_path.name}-{index}{suffix}") for index in range(1, count + 1)]


def with_suffix(path: Path, suffix: str) -> Path:
    if path.suffix.lower() == suffix.lower():
        return path
    return path.with_suffix(suffix)


def make_common_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
        "n": args.n,
        "output_format": args.output_format,
        "stream": args.stream,
    }
    if args.stream:
        payload["partial_images"] = args.partial_images
    if args.output_compression is not None:
        payload["output_compression"] = args.output_compression
    if args.moderation is not None:
        payload["moderation"] = args.moderation
    if args.user is not None:
        payload["user"] = args.user
    return payload


def build_request(args: argparse.Namespace, api_key: str | None) -> tuple[str, bytes, dict[str, str]]:
    endpoint = "/v1/images/generations" if args.command == "generate" else "/v1/images/edits"
    url = build_api_url(args.base_url, endpoint)
    headers = {
        "Authorization": f"Bearer {api_key or '<OPENROUTER_ICU_API_KEY>'}",
        **parse_header_pairs(args.header),
    }

    payload = make_common_payload(args)
    if args.command == "generate" or not args.image:
        if args.command == "edit":
            images: list[dict[str, str]] = []
            images.extend({"file_id": value} for value in args.file_id)
            images.extend({"image_url": value} for value in args.image_url)
            if not images:
                raise OpenRouterImageError("edit requires --image, --file-id, or --image-url")
            payload["images"] = images
        headers["Content-Type"] = "application/json"
        return url, json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers

    if args.file_id or args.image_url:
        raise OpenRouterImageError("do not mix local --image uploads with --file-id or --image-url")

    body, content_type = encode_multipart(payload, [Path(value) for value in args.image])
    headers["Content-Type"] = content_type
    return url, body, headers


def build_api_url(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1") and endpoint.startswith("/v1/"):
        return base + endpoint[len("/v1") :]
    return base + endpoint


def encode_multipart(fields: dict[str, Any], image_paths: list[Path]) -> tuple[bytes, str]:
    boundary = "----openrouter-icu-" + uuid.uuid4().hex
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        if isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        chunks.append(text.encode("utf-8"))
        chunks.append(b"\r\n")

    for path in image_paths:
        if not path.is_file():
            raise OpenRouterImageError(f"image file does not exist: {path}")
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(
            (
                'Content-Disposition: form-data; name="image[]"; '
                f'filename="{path.name}"\r\nContent-Type: {mime_type}\r\n\r\n'
            ).encode("utf-8")
        )
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def send_request(url: str, body: bytes, headers: dict[str, str], timeout: int, retries: int) -> tuple[int, dict[str, str], bytes]:
    sanitized_headers = dict(headers)
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            response_body = exc.read()
            response_headers = dict(exc.headers)
            if exc.code not in RETRY_STATUSES or attempt >= retries:
                try:
                    raise_http_error(exc.code, response_headers, response_body, sanitized_headers)
                except OpenRouterImageError as error:
                    raise error from exc
            sleep_before_retry(attempt, response_headers)
        except urllib.error.URLError as exc:
            if attempt >= retries:
                raise OpenRouterImageError(f"request failed: {exc}") from exc
            sleep_before_retry(attempt, {})

    raise OpenRouterImageError("request failed after retries")


def sleep_before_retry(attempt: int, headers: dict[str, str]) -> None:
    retry_after = headers.get("retry-after") or headers.get("Retry-After")
    if retry_after:
        try:
            delay = min(float(retry_after), 30.0)
        except ValueError:
            delay = 0.0
    else:
        delay = min(2**attempt + random.random(), 30.0)
    time.sleep(delay)


def raise_http_error(status: int, headers: dict[str, str], body: bytes, request_headers: dict[str, str]) -> None:
    request_id = headers.get("x-request-id") or headers.get("X-Request-Id") or headers.get("x-openrouter-request-id")
    detail = decode_text(body)
    try:
        parsed = json.loads(detail)
        detail = json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

    key_present = "Authorization" in request_headers and "<OPENROUTER_ICU_API_KEY>" not in request_headers["Authorization"]
    message = [
        f"OpenRouter ICU request failed with HTTP {status}.",
        f"x-request-id: {request_id or '<missing>'}",
        f"OPENROUTER_ICU_API_KEY present: {str(key_present).lower()}",
        "Response:",
        detail or "<empty>",
    ]
    raise OpenRouterImageError("\n".join(message))


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def parse_sse(data: bytes) -> list[dict[str, Any]]:
    text = decode_text(data)
    events: list[dict[str, Any]] = []
    block: list[str] = []

    def flush() -> None:
        if not block:
            return
        payload = "\n".join(line[5:].lstrip() for line in block if line.startswith("data:")).strip()
        block.clear()
        if not payload or payload == "[DONE]":
            return
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError as exc:
            raise OpenRouterImageError(f"non-JSON SSE payload: {payload[:500]}") from exc

    for line in text.splitlines():
        if line.strip() == "":
            flush()
        else:
            block.append(line)
    flush()

    if not events:
        raise OpenRouterImageError("no parseable SSE events found")
    return events


def event_image_payload(event: dict[str, Any]) -> str | None:
    for key in ("b64_json", "partial_image_b64"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    data = event.get("data")
    if isinstance(data, dict):
        for key in ("b64_json", "partial_image_b64"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def event_type(event: dict[str, Any]) -> str:
    value = event.get("type")
    return value if isinstance(value, str) else ""


def ensure_no_error_events(events: list[dict[str, Any]]) -> None:
    for event in events:
        kind = event_type(event)
        if "error" in event or kind.endswith(".failed") or "error" in kind:
            raise OpenRouterImageError(
                "OpenRouter ICU stream error event:\n" + json.dumps(event, indent=2, ensure_ascii=False)
            )


def extract_stream_images(events: list[dict[str, Any]]) -> tuple[list[str], list[str], str]:
    ensure_no_error_events(events)
    finals: list[str] = []
    partials: list[str] = []
    last_type = ""

    for event in events:
        kind = event_type(event)
        if kind:
            last_type = kind
        payload = event_image_payload(event)
        if not payload:
            continue
        if kind == "image_generation.partial_image" or "partial" in kind:
            partials.append(payload)
        else:
            finals.append(payload)

    return finals, partials, last_type


def extract_json_images(data: bytes) -> list[str]:
    try:
        response = json.loads(decode_text(data))
    except json.JSONDecodeError as exc:
        raise OpenRouterImageError("non-stream response is not JSON") from exc

    if isinstance(response, dict) and response.get("error"):
        raise OpenRouterImageError("OpenRouter ICU error:\n" + json.dumps(response, indent=2, ensure_ascii=False))

    images: list[str] = []
    if isinstance(response, dict):
        data_items = response.get("data")
        if isinstance(data_items, list):
            for item in data_items:
                if isinstance(item, dict):
                    value = item.get("b64_json")
                    if isinstance(value, str) and value:
                        images.append(value)
        value = response.get("b64_json")
        if isinstance(value, str) and value:
            images.append(value)

    if not images:
        raise OpenRouterImageError(
            "no image payload found in JSON response:\n"
            + json.dumps(response, indent=2, ensure_ascii=False)[:4000]
        )
    return images


def write_images(encoded_images: list[str], paths: list[Path]) -> list[Path]:
    if len(encoded_images) < len(paths):
        raise OpenRouterImageError(f"expected {len(paths)} image(s), received {len(encoded_images)}")

    written: list[Path] = []
    for payload, path in zip(encoded_images, paths):
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            raw = base64.b64decode(payload, validate=True)
        except ValueError as exc:
            raise OpenRouterImageError(f"invalid base64 image payload for {path}") from exc
        path.write_bytes(raw)
        verify_written_file(path)
        written.append(path)
    return written


def verify_written_file(path: Path) -> None:
    if not path.is_file():
        raise OpenRouterImageError(f"image output was not written: {path}")
    if path.stat().st_size == 0:
        raise OpenRouterImageError(f"image output is empty: {path}")


def write_partials(partials: list[str], output: Path, output_format: str) -> list[Path]:
    if not partials:
        return []
    base = output.with_suffix("") if output.suffix else output
    paths = [base.with_name(f"{base.name}-partial-{index}.{output_format}") for index in range(1, len(partials) + 1)]
    return write_images(partials, paths)


def write_events(data: bytes, path: Path | None) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def dry_run(url: str, body: bytes, headers: dict[str, str], args: argparse.Namespace) -> None:
    safe_headers = dict(headers)
    if "Authorization" in safe_headers:
        safe_headers["Authorization"] = "Bearer <redacted>"
    request: dict[str, Any] = {
        "method": "POST",
        "url": url,
        "headers": safe_headers,
        "stream": args.stream,
        "output": str(args.output),
    }
    content_type = headers.get("Content-Type", "")
    if content_type.startswith("application/json"):
        request["json"] = json.loads(body.decode("utf-8"))
    else:
        request["multipart_bytes"] = len(body)
        request["local_images"] = args.image
    print(json.dumps(request, indent=2, ensure_ascii=False))


def command_run(args: argparse.Namespace) -> int:
    api_key = os.environ.get("OPENROUTER_ICU_API_KEY")
    if not api_key and not args.dry_run:
        raise OpenRouterImageError("OPENROUTER_ICU_API_KEY is missing; ask the user for a key before calling the API")

    url, body, headers = build_request(args, api_key)
    if args.dry_run:
        dry_run(url, body, headers, args)
        return 0

    status, response_headers, response_body = send_request(url, body, headers, args.timeout, args.retries)
    write_events(response_body, args.events_output)

    request_id = response_headers.get("x-request-id") or response_headers.get("X-Request-Id") or "<missing>"
    output_targets = output_paths(args.output, args.n, args.output_format)

    if args.stream:
        events = parse_sse(response_body)
        finals, partials, last_type = extract_stream_images(events)
        if not finals:
            raise OpenRouterImageError(
                "no final image payload found in SSE stream; "
                f"last event type: {last_type or '<missing>'}; partial payloads: {len(partials)}"
            )
        written = write_images(finals, output_targets)
        partial_paths = write_partials(partials, args.output, args.output_format) if args.save_partials else []
        print_result(status, request_id, written, partial_paths, last_type)
        return 0

    images = extract_json_images(response_body)
    written = write_images(images, output_targets)
    print_result(status, request_id, written, [], "")
    return 0


def print_result(status: int, request_id: str, written: list[Path], partials: list[Path], last_event_type: str) -> None:
    result: dict[str, Any] = {
        "status": status,
        "x_request_id": request_id,
        "images": [str(path) for path in written],
    }
    if partials:
        result["partials"] = [str(path) for path in partials]
    if last_event_type:
        result["last_event_type"] = last_event_type
    print(json.dumps(result, indent=2, ensure_ascii=False))


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", required=True, help="Visual-only prompt. Do not include API controls.")
    parser.add_argument("--output", required=True, type=Path, help="Output image path or filename stem.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--size", default=DEFAULT_SIZE, type=validate_size)
    parser.add_argument("--quality", default=DEFAULT_QUALITY, choices=("low", "medium", "high", "auto"))
    parser.add_argument("--output-format", "--output_format", default=DEFAULT_OUTPUT_FORMAT, choices=("png", "jpeg", "webp"))
    parser.add_argument("--output-compression", "--output_compression", type=compression_value)
    parser.add_argument("--n", default=1, type=positive_int)
    parser.add_argument("--moderation", choices=("auto", "low"))
    parser.add_argument("--user")
    parser.add_argument(
        "--base-url",
        "--base_url",
        default=BASE_URL,
        help="OpenRouter ICU root URL or /v1 API base URL.",
    )
    parser.add_argument("--timeout", default=300, type=positive_int)
    parser.add_argument("--retries", default=2, type=int)
    parser.add_argument("--header", action="append", help="Additional HTTP header as NAME:VALUE.")
    parser.add_argument(
        "--events-output",
        "--events_output",
        type=Path,
        help="Write raw API response or SSE event stream to this path.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the request shape without contacting the API.")
    parser.add_argument(
        "--stream",
        nargs="?",
        action=BooleanOptionalValueAction,
        help="Enable streaming. May be passed as --stream, --stream true, or --stream false.",
    )
    parser.add_argument(
        "--no-stream",
        "--no_stream",
        dest="stream",
        action="store_false",
        help="Disable streaming response handling.",
    )
    parser.set_defaults(stream=True)
    parser.add_argument("--partial-images", "--partial_images", default=DEFAULT_PARTIAL_IMAGES, type=partial_images_value)
    parser.add_argument(
        "--save-partials",
        "--save_partials",
        action="store_true",
        help="Save streaming partial images beside the final output.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate an image from a text prompt.")
    add_common_arguments(generate)

    edit = subparsers.add_parser("edit", help="Edit local images or use image references.")
    add_common_arguments(edit)
    edit.add_argument("--image", "--image-file", action="append", default=[], help="Local input image path. Repeat for multiple images.")
    edit.add_argument("--file-id", "--file_id", action="append", default=[], help="OpenRouter/OpenAI file ID image reference.")
    edit.add_argument("--image-url", "--image_url", action="append", default=[], help="Remote image URL reference.")

    return parser


def main(argv: list[str] | None = None) -> int:
    configure_standard_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.retries < 0:
        parser.error("--retries must be non-negative")
    if args.save_partials and not args.stream:
        parser.error("--save-partials requires streaming; remove --no-stream")
    try:
        return command_run(args)
    except OpenRouterImageError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
