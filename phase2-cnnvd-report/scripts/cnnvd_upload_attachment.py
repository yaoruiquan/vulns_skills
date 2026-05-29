#!/usr/bin/env python3
"""Upload attachment (video/poc) to CNNVD server and output apply-JS for browser.

Usage:
  # Upload video (fileField=1) and PoC (fileField=2) from form_context.json
  python3 scripts/cnnvd_upload_attachment.py <form_context.json> \\
      --token-file /tmp/cnnvd_token.txt \\
      --apply-js /tmp/apply.js

  # Upload a single file
  python3 scripts/cnnvd_upload_attachment.py --file video.mp4 --field 1 \\
      --endpoint https://www.cnnvd.org.cn/web/compatibilityProduct/importImplementImg \\
      --token-file /tmp/cnnvd_token.txt
"""
from __future__ import annotations

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
from typing import Optional


ENDPOINT = "https://www.cnnvd.org.cn/web/compatibilityProduct/importImplementImg"


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_multipart(file_path: Path, file_field: str, boundary: str) -> bytes:
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    body = file_path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        body,
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="fileField"\r\n\r\n',
        file_field.encode(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts)


def upload_file(
    endpoint: str,
    token: str,
    file_path: Path,
    file_field: str,
    timeout: int = 120,
) -> dict:
    boundary = "----PythonUpload" + secrets.token_hex(12)
    data = build_multipart(file_path, file_field, boundary)
    req = urllib.request.Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Origin": "https://www.cnnvd.org.cn",
            "Referer": "https://www.cnnvd.org.cn/backHome/generalSend",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "token": token,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {raw[:500]}") from exc

    parsed = json.loads(raw) if raw.strip().startswith("{") else {"raw": raw}
    return parsed


def extract_url(response: dict) -> str:
    """Extract uploaded file URL from response (walks nested dict/list)."""
    stack = [response]
    while stack:
        val = stack.pop()
        if isinstance(val, dict):
            for v in val.values():
                stack.append(v)
        elif isinstance(val, list):
            stack.extend(val)
        elif isinstance(val, str):
            val = val.strip()
            if val.startswith(("group", "/group")):
                return val.lstrip("/")
    return ""


def generate_apply_js(
    video_result: Optional[dict],
    poc_result: Optional[dict],
) -> str:
    """Generate browser JavaScript to apply uploaded files into Vue upload components."""
    payload = {
        "endpoint": ENDPOINT,
    }
    if video_result:
        payload["video"] = video_result
    if poc_result:
        payload["poc"] = poc_result

    payload_json = json.dumps(payload, ensure_ascii=False)

    return f"""async () => {{
  const uploaded = {payload_json};
  const uploads = Array.from(document.querySelectorAll('.el-upload'));
  const results = [];

  function wait(ms) {{ return new Promise(r => setTimeout(r, ms)); }}

  function serverUrl(path) {{
    if (/^https?:\\/\\//i.test(path)) return path;
    return new URL('/' + (path || '').replace(/^\\/+/, ''), location.origin).href;
  }}

  async function applyOne(index, item) {{
    const el = uploads[index];
    const comp = el && el.__vue__;
    if (!comp) return {{ kind: item.kind, success: false, error: 'component not found' }};

    const url = serverUrl(item.url);
    try {{
      const resp = await fetch(url, {{ credentials: 'include' }});
      if (!resp.ok) throw new Error('fetch: ' + resp.status);
      const blob = await resp.blob();
      const file = new File([blob], item.name, {{ type: item.mime }});
      const dt = new DataTransfer();
      dt.items.add(file);

      if (item.kind === 'video') {{
        const input = el.querySelector('input[type="file"]');
        if (!input) return {{ kind: item.kind, success: false, error: 'no input' }};
        Object.defineProperty(input, 'files', {{ value: dt.files, configurable: true }});
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
      }} else if (typeof comp.handleChange === 'function') {{
        comp.handleChange({{ target: {{ files: dt.files }}, preventDefault() {{}} }});
      }} else {{
        const input = el.querySelector('input[type="file"]');
        if (!input) return {{ kind: item.kind, success: false, error: 'no input' }};
        Object.defineProperty(input, 'files', {{ value: dt.files, configurable: true }});
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
      }}

      const deadline = Date.now() + 180000;
      while (Date.now() < deadline) {{
        await wait(500);
        const list = Array.isArray(comp.fileList) ? comp.fileList : [];
        if (list.some(f => f && f.status === 'success' && f.url))
          return {{ kind: item.kind, success: true }};
        if (list.some(f => f && f.status === 'fail'))
          return {{ kind: item.kind, success: false, error: 'upload fail' }};
      }}
      return {{ kind: item.kind, success: false, error: 'timeout' }};
    }} catch (e) {{
      return {{ kind: item.kind, success: false, error: e.message }};
    }}
  }}

  if (uploaded.video) results.push(await applyOne(0, uploaded.video));
  if (uploaded.poc) results.push(await applyOne(1, uploaded.poc));
  return {{ success: results.every(r => r.success), results }};
}}"""


def upload_one(
    token: str,
    file_path: str,
    file_field: str,
    endpoint: str,
    timeout: int,
) -> dict:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"{file_path}")
    t0 = time.time()
    resp = upload_file(endpoint, token, path, file_field, timeout)
    url = extract_url(resp)
    if not url:
        raise RuntimeError(f"No URL in response: {json.dumps(resp, ensure_ascii=False)[:300]}")
    return {
        "kind": "video" if file_field == "1" else "poc",
        "fileField": file_field,
        "name": path.name,
        "size": path.stat().st_size,
        "mime": mimetypes.guess_type(str(path))[0] or "application/octet-stream",
        "url": url,
        "durationMs": int((time.time() - t0) * 1000),
        "response": resp,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload attachment to CNNVD")
    parser.add_argument("form_context", nargs="?", help="form_context.json (reads video/poc paths)")
    parser.add_argument("--file", help="Single file to upload (overrides form_context)")
    parser.add_argument("--field", choices=["1", "2"], help="fileField: 1=video, 2=poc")
    parser.add_argument("--endpoint", default=ENDPOINT)
    parser.add_argument("--token-file", required=True, help="File containing JWT token")
    parser.add_argument("--timeout", type=int, default=120, help="Upload timeout (seconds)")
    parser.add_argument("--apply-js", help="Output path for browser apply-JS script")
    parser.add_argument("--output", default="", help="Output path for upload result JSON")
    args = parser.parse_args()

    token = Path(args.token_file).read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("Empty token")

    results = {}

    if args.file:
        # Single file mode
        if not args.field:
            raise SystemExit("--field required with --file")
        results[args.field] = upload_one(token, args.file, args.field, args.endpoint, args.timeout)
    elif args.form_context:
        # Form context mode
        ctx = load_json(args.form_context)
        video_path = ctx.get("verification_video_path") or ""
        poc_path = ctx.get("poc_file_path") or ""
        if video_path:
            results["1"] = upload_one(token, video_path, "1", args.endpoint, args.timeout)
        if poc_path:
            results["2"] = upload_one(token, poc_path, "2", args.endpoint, args.timeout)
    else:
        raise SystemExit("Provide either form_context or --file")

    # Build output
    video_result = results.get("1")
    poc_result = results.get("2")
    output = {
        "endpoint": args.endpoint,
    }
    if video_result:
        output["video"] = video_result
    if poc_result:
        output["poc"] = poc_result

    if args.apply_js:
        Path(args.apply_js).write_text(
            generate_apply_js(video_result, poc_result), encoding="utf-8"
        )
        output["apply_js"] = args.apply_js

    output_json = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output_json + "\n", encoding="utf-8")

    print(output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
