#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出 CNNVD 浏览器自动化常用 evaluate_script 片段。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def as_iife(script: str) -> str:
    code = script.strip()
    if code.startswith("async () =>") or code.startswith("() =>") or code.startswith("function"):
        return f"({code})()"
    return code


def load_context(path: str) -> dict:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def probe_form_model_script() -> str:
    return as_iife("""() => {
  const seen = new Set();
  const models = [];
  const walk = (comp, path) => {
    if (!comp || seen.has(comp)) return;
    seen.add(comp);
    if (comp.formModel && typeof comp.formModel === 'object') {
      models.push({ path, keys: Object.keys(comp.formModel), formModel: { ...comp.formModel } });
    }
    if (comp.$children) comp.$children.forEach((child, index) => walk(child, `${path}.$children[${index}]`));
  };
  Array.from(document.querySelectorAll('*')).forEach((el, index) => {
    if (el.__vue__) walk(el.__vue__, `${el.tagName.toLowerCase()}[${index}]`);
  });
  return { ok: models.length > 0, models };
}""")


def sync_form_model_script(context: dict) -> str:
    fields = context.get("vue_form_model_fields", {})
    payload = {
        "vulName": fields.get("vulName") or context.get("title", ""),
        "affectedVendor": fields.get("affectedVendor") or context.get("unit_name", ""),
        "affectedEntityName": fields.get("affectedEntityName") or context.get("affected_product", ""),
        "affectedEntityVersion": fields.get("affectedEntityVersion") or context.get("version", ""),
        "affectedEntityDesc": fields.get("affectedEntityDesc") or context.get("entity_description", ""),
        "hazardLevel": fields.get("hazardLevel") or context.get("risk_level", ""),
        "vulDesc": fields.get("vulDesc") or context.get("description", ""),
        "supporter": fields.get("supporter") or context.get("technical_support", ""),
        "supporterPhone": fields.get("supporterPhone") or context.get("contact", ""),
        "verifyProcess": fields.get("verifyProcess") or context.get("verification", ""),
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    return as_iife(f"""() => {{
  const payload = {payload_json};
  const seen = new Set();
  const candidates = [];
  const walk = (comp) => {{
    if (!comp || seen.has(comp)) return;
    seen.add(comp);
    if (comp.formModel && typeof comp.formModel === 'object') candidates.push(comp);
    if (comp.$children) comp.$children.forEach(walk);
  }};
  Array.from(document.querySelectorAll('*')).forEach((el) => {{
    if (el.__vue__) walk(el.__vue__);
  }});
  const comp = candidates.find((item) => item.formModel && ('verifyProcess' in item.formModel || 'vulName' in item.formModel)) || candidates[0];
  if (!comp) return {{ ok: false, code: 'CNNVD_FORM_MODEL_NOT_FOUND', candidates: candidates.length }};
  const model = comp.formModel;
  const changed = {{}};
  for (const [key, value] of Object.entries(payload)) {{
    if (value !== undefined && value !== null && key in model) {{
      model[key] = value;
      changed[key] = value;
    }}
  }}
  const verification = payload.verifyProcess || '';
  if (verification) {{
    if (window.tinymce && window.tinymce.editors) {{
      const editors = Array.isArray(window.tinymce.editors)
        ? window.tinymce.editors
        : Object.values(window.tinymce.editors);
      for (const editor of editors) {{
        if (editor && typeof editor.setContent === 'function') {{
          editor.setContent(`<p>${{verification}}</p>`);
          if (typeof editor.fire === 'function') editor.fire('change');
          if (typeof editor.save === 'function') editor.save();
        }}
      }}
    }}
    for (const iframe of Array.from(document.querySelectorAll('iframe'))) {{
      try {{
        const doc = iframe.contentDocument;
        if (doc && doc.body) {{
          doc.body.innerHTML = `<p>${{verification}}</p>`;
          doc.body.dispatchEvent(new Event('input', {{ bubbles: true }}));
          doc.body.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
      }} catch (error) {{}}
    }}
    model.verifyProcess = verification;
    changed.verifyProcess = verification;
  }}
  if (typeof comp.$forceUpdate === 'function') comp.$forceUpdate();
  return {{
    ok: Boolean(model.verifyProcess),
    code: model.verifyProcess ? 'CNNVD_FORM_MODEL_SYNCED' : 'CNNVD_VERIFY_PROCESS_EMPTY',
    changedKeys: Object.keys(changed),
    modelKeys: Object.keys(model),
    verifyProcessLength: String(model.verifyProcess || '').length,
    affectedClassifyRule: '受影响实体分类必须通过 DOM 下拉选项点击完成；不要直接写 affectedClassify=30。'
  }};
}}""")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="输出 CNNVD 浏览器 evaluate_script 片段")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe-form-model", help="探查页面 Vue formModel 字段")
    sync = sub.add_parser("sync-form-model", help="按 form_context.json 同步 Vue formModel 和 TinyMCE")
    sync.add_argument("--form-context", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "probe-form-model":
        print(probe_form_model_script())
    elif args.command == "sync-form-model":
        print(sync_form_model_script(load_context(args.form_context)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
