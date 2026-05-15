#!/usr/bin/env python3
"""Create a WeChat draft from rendered alert HTML and its metadata."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_local_env() -> None:
    env_path = SKILL_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request_json(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def access_token() -> str:
    appid = os.environ.get("WECHAT_APPID", "")
    secret = os.environ.get("WECHAT_SECRET", "")
    if not appid or not secret:
        raise RuntimeError("WECHAT_APPID/WECHAT_SECRET is required")
    data = request_json(
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={appid}&secret={secret}"
    )
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"failed to get WeChat access token: {data}")
    return token


def multipart_body(path: Path, *, field_name: str = "media") -> tuple[bytes, str]:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    boundary = "----md2wechatAlertBoundary"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + path.read_bytes() + tail, f"multipart/form-data; boundary={boundary}"


def upload_cover(path: Path, token: str) -> str:
    body, content_type = multipart_body(path)
    data = request_json(
        f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image",
        data=body,
        headers={"Content-Type": content_type},
    )
    media_id = data.get("media_id")
    if not media_id:
        raise RuntimeError(f"failed to upload cover image: {data}")
    return media_id


def upload_article_image(data: bytes, filename: str, mime: str, token: str) -> str:
    boundary = "----md2wechatArticleImageBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    result = request_json(
        f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    url = result.get("url")
    if not url:
        raise RuntimeError(f"failed to upload article image: {result}")
    return url


def create_draft(payload: dict, token: str) -> dict:
    return request_json(
        f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


def replace_data_uri_images(content: str, token: str) -> str:
    def replace(match: re.Match[str]) -> str:
        fmt = match.group(1).lower()
        mime = f"image/{'jpeg' if fmt == 'jpg' else fmt}"
        image_data = base64.b64decode(match.group(2))
        return upload_article_image(image_data, f"image.{fmt}", mime, token)

    return re.sub(r"data:image/([A-Za-z0-9.+-]+);base64,([A-Za-z0-9+/=]+)", replace, content)


def build_draft(html_file: Path, cover_image: Path, metadata_file: Path, draft_json: Path) -> dict:
    token = access_token()
    metadata = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.is_file() else {}
    content = replace_data_uri_images(html_file.read_text(encoding="utf-8"), token)
    media_id = upload_cover(cover_image, token)
    article = {
        "title": metadata.get("title") or html_file.stem,
        "author": metadata.get("author") or os.environ.get("WECHAT_AUTHOR", "安恒CERT"),
        "digest": (metadata.get("digest") or metadata.get("title") or html_file.stem)[:120],
        "content": content,
        "content_source_url": "",
        "thumb_media_id": media_id,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    payload = {"articles": [article]}
    draft_json.parent.mkdir(parents=True, exist_ok=True)
    draft_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Create WeChat alert draft from rendered HTML")
    parser.add_argument("html_file", type=Path)
    parser.add_argument("cover_image", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--draft-json", type=Path)
    parser.add_argument("--create", action="store_true", help="Create the WeChat draft after writing JSON")
    parser.add_argument("--result-json", type=Path, help="Write machine-readable result JSON to this file")
    parser.add_argument("--json", action="store_true", help="Print machine-readable result")
    args = parser.parse_args()

    try:
        load_local_env()
        metadata = args.metadata or args.html_file.with_suffix(args.html_file.suffix + ".meta.json")
        draft_json = args.draft_json or Path(tempfile.gettempdir()) / f"{args.html_file.stem}.draft.json"
        payload = build_draft(args.html_file, args.cover_image, metadata, draft_json)

        result: dict = {
            "success": True,
            "draft_json": str(draft_json),
            "title": payload["articles"][0]["title"],
        }
        if args.create:
            token = access_token()
            draft_result = create_draft(payload, token)
            result["create_draft_result"] = draft_result
            if draft_result.get("errcode") not in (None, 0):
                result["success"] = False
                result["error"] = draft_result.get("errmsg") or str(draft_result)
            else:
                result["media_id"] = draft_result.get("media_id", "")
    except Exception as exc:
        result = {"success": False, "error": str(exc)}

    if args.result_json:
        args.result_json.parent.mkdir(parents=True, exist_ok=True)
        args.result_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result.get("draft_json", ""))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
