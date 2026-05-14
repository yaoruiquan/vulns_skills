#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload CNNVD verification attachments and generate browser apply script.

This helper is intentionally stdlib-only so it can run inside the OpenCode
runtime image. It uploads local job files to CNNVD's same-origin upload API
with the browser JWT token, then emits JavaScript that replays the uploaded
server URLs into the Vue/Element upload components on page 3.
"""

import argparse
import json
import mimetypes
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_ENDPOINT = "https://www.cnnvd.org.cn/web/compatibilityProduct/importImplementImg"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def token_from_args(args: argparse.Namespace) -> str:
    if args.token_file:
        return Path(args.token_file).read_text(encoding="utf-8").strip()
    if args.token_stdin:
        return sys.stdin.read().strip()
    if args.token_env:
        return os.environ.get(args.token_env, "").strip()
    raise SystemExit("token source required: --token-file, --token-stdin, or --token-env")


def context_uploads(form_context: dict) -> dict:
    page_uploads = form_context.get("page_payloads", {}).get("page3_uploads", {})
    return {
        "video": form_context.get("verification_video_path") or page_uploads.get("verification_video_path") or "",
        "poc": form_context.get("poc_file_path") or page_uploads.get("poc_file_path") or "",
    }


def multipart_body(file_path: Path, file_field: str, boundary: str) -> bytes:
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode(),
        file_bytes,
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="fileField"\r\n\r\n',
        str(file_field).encode(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts)


def request_upload(endpoint: str, token: str, file_path: Path, file_field: str) -> dict:
    boundary = "----OpenCodeCNNVD" + secrets.token_hex(12)
    body = multipart_body(file_path, file_field, boundary)
    req = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Origin": "https://www.cnnvd.org.cn",
            "Referer": "https://www.cnnvd.org.cn/backHome/generalSend",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) HeadlessChrome Safari/537.36",
            "token": token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = resp.getcode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"upload failed for {file_path.name}: HTTP {exc.code} {raw[:500]}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"raw": raw}
    return {"httpStatus": status, "response": parsed}


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


def extract_uploaded_url(response: dict) -> str:
    for text in iter_strings(response):
        normalized = text.strip()
        if normalized.startswith(("group", "/group", "http://", "https://")):
            return normalized.lstrip("/")
    return ""


def upload_one(endpoint: str, token: str, kind: str, path_text: str, file_field: str) -> dict:
    file_path = Path(path_text)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"{kind} file not found: {file_path}")
    started = time.time()
    upload = request_upload(endpoint, token, file_path, file_field)
    uploaded_url = extract_uploaded_url(upload["response"])
    if not uploaded_url:
        raise RuntimeError(f"{kind} upload response did not include a server file path")
    return {
        "kind": kind,
        "fileField": file_field,
        "name": file_path.name,
        "size": file_path.stat().st_size,
        "mime": mimetypes.guess_type(str(file_path))[0] or "application/octet-stream",
        "url": uploaded_url,
        "durationMs": int((time.time() - started) * 1000),
        "response": upload["response"],
    }


def apply_js(payload: dict) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False)
    return f"""async () => {{
  const uploaded = {payload_json};
  const uploads = Array.from(document.querySelectorAll('.el-upload'));
  const results = [];

  async function wait(ms) {{
    return new Promise((resolve) => setTimeout(resolve, ms));
  }}

  function serverUrl(path) {{
    if (/^https?:\\/\\//i.test(path)) return path;
    return new URL('/' + String(path || '').replace(/^\\/+/, ''), location.origin).href;
  }}

  async function applyOne(index, item) {{
    const el = uploads[index];
    const comp = el && el.__vue__;
    if (!comp) return {{ kind: item.kind, success: false, error: 'upload component not found', index }};

    const url = serverUrl(item.url);
    let file = null;
    try {{
      const resp = await fetch(url, {{ credentials: 'include' }});
      if (!resp.ok) throw new Error('fetch uploaded file failed: ' + resp.status);
      const blob = await resp.blob();
      file = new File([blob], item.name, {{ type: item.mime || blob.type || 'application/octet-stream' }});
    }} catch (error) {{
      comp.fileList = [{{
        name: item.name,
        url: item.url,
        fileId: Date.now(),
        uid: Date.now(),
        status: 'success'
      }}];
      if (typeof comp.$emit === 'function') comp.$emit('change', comp.fileList);
      return {{ kind: item.kind, success: true, mode: 'direct-fileList', warning: error.message, fileList: comp.fileList }};
    }}

    const dt = new DataTransfer();
    dt.items.add(file);
    const event = {{ target: {{ files: dt.files }}, preventDefault() {{}} }};

    if (typeof comp.handleChange === 'function') {{
      comp.handleChange(event);
    }} else {{
      const input = el.querySelector('input[type="file"]');
      if (!input) return {{ kind: item.kind, success: false, error: 'file input not found' }};
      Object.defineProperty(input, 'files', {{ value: dt.files, configurable: true }});
      input.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}

    for (let i = 0; i < 40; i++) {{
      await wait(250);
      const list = Array.isArray(comp.fileList) ? comp.fileList : [];
      if (list.some((f) => f && (f.status === 'success' || f.url))) {{
        return {{ kind: item.kind, success: true, mode: 'handleChange', fileList: list.map((f) => ({{ name: f.name, url: f.url, status: f.status }})) }};
      }}
    }}
    return {{ kind: item.kind, success: false, error: 'component fileList did not reach success state', fileList: comp.fileList || [] }};
  }}

  if (uploaded.video) results.push(await applyOne(0, uploaded.video));
  if (uploaded.poc) results.push(await applyOne(1, uploaded.poc));
  return {{ success: results.every((item) => item.success), results }};
}}"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--form-context", required=True, help="Path to form_context.json")
    parser.add_argument("--output", required=True, help="Path to write uploaded attachment JSON")
    parser.add_argument("--apply-js", help="Optional path to write browser evaluate_script function")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--token-file")
    parser.add_argument("--token-stdin", action="store_true")
    parser.add_argument("--token-env")
    args = parser.parse_args()

    token = token_from_args(args)
    if not token:
        raise SystemExit("empty CNNVD token")

    form_context = load_json(Path(args.form_context))
    uploads = context_uploads(form_context)
    result = {
        "endpoint": args.endpoint,
        "video": upload_one(args.endpoint, token, "video", uploads["video"], "1"),
        "poc": upload_one(args.endpoint, token, "poc", uploads["poc"], "2"),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.apply_js:
        Path(args.apply_js).write_text(apply_js(result), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "video": {"name": result["video"]["name"], "url": result["video"]["url"]},
        "poc": {"name": result["poc"]["name"], "url": result["poc"]["url"]},
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
