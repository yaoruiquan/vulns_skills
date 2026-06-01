#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出 CNNVD 浏览器自动化常用 evaluate_script 片段。"""

from __future__ import annotations

import argparse
import json
import re
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


def disclosure_payload(context: dict, cnnvd_id: str) -> dict:
    report = context.get("disclosure_report", {})
    page1 = dict(report.get("page1", {}))
    page2 = dict(report.get("page2", {}))
    related_id = cnnvd_id or page1.get("related_vuln_id") or report.get("cnnvd_id_placeholder", "")
    match = re.search(r"CNNVD-\d{4}-(\d+)", related_id, flags=re.I)
    related_digits = match.group(1) if match else "".join(ch for ch in related_id if ch.isdigit())
    for data in (page1, page2):
        for key, value in list(data.items()):
            if isinstance(value, str):
                data[key] = value.replace("{cnnvd_id}", related_id)
    page1["related_vuln_id"] = related_id
    page1["related_vuln_search_keyword"] = related_digits or related_id
    return {"required": bool(report.get("required")), "page1": page1, "page2": page2}


def sync_disclosure_report_script(context: dict, cnnvd_id: str) -> str:
    payload_json = json.dumps(disclosure_payload(context, cnnvd_id), ensure_ascii=False)
    return as_iife(f"""async () => {{
  const payload = {payload_json};
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const seen = new Set();
  let comp = null;
  const walk = (item) => {{
    if (!item || seen.has(item)) return;
    seen.add(item);
    if (item.$options && item.$options.name === 'VulWarnSend') comp = item;
    if (item.$children) item.$children.forEach(walk);
  }};
  Array.from(document.querySelectorAll('*')).forEach((el) => {{
    if (el.__vue__) walk(el.__vue__);
  }});
  if (!comp) return {{ ok: false, code: 'CNNVD_DISCLOSURE_COMPONENT_NOT_FOUND' }};
  if (!payload.required) return {{ ok: true, code: 'CNNVD_DISCLOSURE_NOT_REQUIRED' }};
  const page1 = payload.page1 || {{}};
  const page2 = payload.page2 || {{}};
  const form = comp.form || {{}};
  const setIf = (key, value) => {{
    if (value !== undefined && value !== null && value !== '') {{
      if (typeof comp.$set === 'function') comp.$set(form, key, value);
      else form[key] = value;
    }}
  }};
  const boolValue = (value) => String(value || '').trim() === '有' || String(value || '').trim() === '是' ? 1 : 2;
  setIf('isPoc', boolValue(page1.is_poc));
  setIf('pocVerified', boolValue(page1.poc_verified));
  setIf('isExp', boolValue(page1.is_exp));
  setIf('expVerified', boolValue(page1.exp_verified));
  setIf('isTool', boolValue(page1.is_tool));
  setIf('toolVerified', boolValue(page1.tool_verified));
  setIf('submitter', page1.submitter);
  setIf('submitterPhone', page1.submitter_phone);
  setIf('submitterEmail', page1.submitter_email);
  setIf('supporter', page1.supporter || form.submitter);
  setIf('supporterPhone', page1.supporter_phone || form.supporterPhone || '');
  setIf('supporterEmail', page1.supporter_email || form.submitterEmail);
  if (form.submitterPhone && form.supporterPhone && form.submitterPhone === form.supporterPhone) {{
    const fallbackPhones = [page1.alternate_phone, '15727382818', '17557289379'].filter(Boolean);
    const replacement = fallbackPhones.find((phone) => phone !== form.submitterPhone);
    if (replacement) setIf('supporterPhone', replacement);
  }}

  const related = String(page1.related_vuln_id || '').trim();
  const searchKeyword = String(page1.related_vuln_search_keyword || related).trim();
  let matched = null;
  if (typeof comp.$set === 'function') comp.$set(form, 'vulIdList', []);
  else form.vulIdList = [];
  comp.vulIdListNew = [];
  if (searchKeyword) {{
    if (typeof comp.remoteMethod === 'function') {{
      try {{
        comp.remoteMethod(searchKeyword);
        await wait(1200);
      }} catch (error) {{}}
    }}
    const list = Array.isArray(comp.vulList) ? comp.vulList : [];
    matched = list.find((item) => {{
      const code = String(item.cnnvdCode || '');
      return (related && code.includes(related)) || (searchKeyword && code.includes(searchKeyword));
    }});
    if (matched) {{
      const value = matched.id || matched.vulId || matched.cnnvdCode;
      if (typeof comp.$set === 'function') comp.$set(form, 'vulIdList', [value]);
      else form.vulIdList = [value];
      comp.vulIdListNew = [matched];
      if (typeof comp.vulIdListChange === 'function') {{
        try {{ comp.vulIdListChange(form.vulIdList); }} catch (error) {{}}
      }}
    }}
  }}
  const dropdownOpen = () => Array.from(document.querySelectorAll('.el-select-dropdown,.el-autocomplete-suggestion')).some((el) => {{
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  }});
  const clickOutsideDropdown = () => {{
    const points = [
      [Math.max(12, Math.floor(window.innerWidth * 0.18)), Math.max(12, Math.floor(window.innerHeight * 0.18))],
      [Math.max(12, Math.floor(window.innerWidth * 0.5)), Math.max(12, Math.floor(window.innerHeight * 0.08))],
      [Math.max(12, Math.floor(window.innerWidth * 0.82)), Math.max(12, Math.floor(window.innerHeight * 0.18))],
    ];
    for (const [x, y] of points) {{
      const target = document.elementFromPoint(x, y) || document.body;
      if (target && target.closest && target.closest('.el-select-dropdown,.el-autocomplete-suggestion')) continue;
      for (const type of ['pointerdown', 'mousedown', 'mouseup', 'click']) {{
        target.dispatchEvent(new MouseEvent(type, {{ bubbles: true, cancelable: true, clientX: x, clientY: y }}));
      }}
      return true;
    }}
    return false;
  }};
  const active = document.activeElement;
  if (active && typeof active.blur === 'function') active.blur();
  document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true }}));
  clickOutsideDropdown();
  await wait(300);

  comp.form = form;
  comp.detailForm = comp.detailForm || {{}};
  const warnName = page2.warn_name || '';
  const content = page2.enclosure_content || '';
  if (warnName) {{
    if (typeof comp.$set === 'function') comp.$set(comp.detailForm, 'warnName', warnName);
    else comp.detailForm.warnName = warnName;
  }}
  if (content) {{
    if (typeof comp.$set === 'function') comp.$set(comp.detailForm, 'enclosureContent', content);
    else comp.detailForm.enclosureContent = content;
    for (const iframe of Array.from(document.querySelectorAll('iframe'))) {{
      try {{
        const doc = iframe.contentDocument;
        if (doc && doc.body && doc.body.isContentEditable) {{
          doc.body.innerHTML = content;
          doc.body.dispatchEvent(new Event('input', {{ bubbles: true }}));
          doc.body.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
      }} catch (error) {{}}
    }}
    if (window.tinymce && window.tinymce.editors) {{
      const editors = Array.isArray(window.tinymce.editors)
        ? window.tinymce.editors
        : Object.values(window.tinymce.editors);
      for (const editor of editors) {{
        try {{
          if (
            editor &&
            editor.initialized !== false &&
            editor.getBody &&
            editor.getBody() &&
            typeof editor.setContent === 'function'
          ) {{
            editor.getBody().innerHTML = content;
            if (typeof editor.fire === 'function') editor.fire('change');
            if (typeof editor.save === 'function') editor.save();
          }}
        }} catch (error) {{
          // TinyMCE may throw selection/bookmark errors when hidden; Vue model above is authoritative.
        }}
      }}
    }}
  }}
  if (typeof comp.$forceUpdate === 'function') comp.$forceUpdate();
  const missing = [];
  if (related && !matched) missing.push(`关联漏洞编号未匹配到平台选项，搜索关键词: ${{searchKeyword}}`);
  for (const key of ['submitter', 'submitterPhone', 'submitterEmail', 'supporter', 'supporterPhone', 'supporterEmail']) {{
    if (!form[key]) missing.push(key);
  }}
  if (!comp.detailForm.warnName) missing.push('warnName');
  if (!comp.detailForm.enclosureContent) missing.push('enclosureContent');
  if (Array.isArray(form.vulIdList) && form.vulIdList.length > 1) missing.push(`关联漏洞编号多选残留: ${{form.vulIdList.length}}`);
  const isDropdownClosed = !dropdownOpen();
  if (!isDropdownClosed) missing.push('关联漏洞编号下拉框未收起');
  return {{
    ok: missing.length === 0,
    code: missing.length === 0 ? 'CNNVD_DISCLOSURE_SYNCED' : 'CNNVD_DISCLOSURE_NEEDS_REVIEW',
    active: comp.active,
    matchedVuln: matched ? {{ id: matched.id, cnnvdCode: matched.cnnvdCode }} : null,
    missing,
    dropdownClosed: isDropdownClosed,
    attachmentPath: page1.attachment_path || '',
    next: '上传 disclosure_report.page1.attachment_path 后点击下一步；第二页确认富文本后再进入第三页提交。'
  }};
}}""")


def audit_disclosure_report_script(context: dict, cnnvd_id: str) -> str:
    payload_json = json.dumps(disclosure_payload(context, cnnvd_id), ensure_ascii=False)
    return as_iife(f"""() => {{
  const payload = {payload_json};
  if (!payload.required) return {{ ok: true, code: 'CNNVD_DISCLOSURE_NOT_REQUIRED' }};
  const seen = new Set();
  let comp = null;
  const walk = (item) => {{
    if (!item || seen.has(item)) return;
    seen.add(item);
    if (item.$options && item.$options.name === 'VulWarnSend') comp = item;
    if (item.$children) item.$children.forEach(walk);
  }};
  Array.from(document.querySelectorAll('*')).forEach((el) => {{
    if (el.__vue__) walk(el.__vue__);
  }});
  if (!comp) return {{ ok: false, code: 'CNNVD_DISCLOSURE_COMPONENT_NOT_FOUND' }};
  const form = comp.form || {{}};
  const detail = comp.detailForm || {{}};
  const fileNames = Array.from(document.querySelectorAll('.el-upload-list__item-name')).map((el) => el.innerText.trim()).filter(Boolean);
  const dropdownOpen = Array.from(document.querySelectorAll('.el-select-dropdown,.el-autocomplete-suggestion')).some((el) => {{
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  }});
  const missing = [];
  if (!Array.isArray(form.vulIdList) || !form.vulIdList.length) missing.push('关联漏洞编号');
  if (Array.isArray(form.vulIdList) && form.vulIdList.length !== 1) missing.push(`关联漏洞编号多选残留: ${{form.vulIdList.length}}`);
  if (dropdownOpen) missing.push('关联漏洞编号下拉框未收起');
  for (const key of ['submitter', 'submitterPhone', 'submitterEmail', 'supporter', 'supporterPhone', 'supporterEmail']) {{
    if (!form[key]) missing.push(key);
  }}
  if (!detail.warnName) missing.push('漏洞通报名称');
  if (!detail.enclosureContent) missing.push('漏洞通报正文');
  if (!fileNames.length) missing.push('上传附件');
  const errors = Array.from(document.querySelectorAll('.el-form-item__error,.el-message,.el-alert')).map((el) => el.innerText.trim()).filter(Boolean);
  return {{
    ok: missing.length === 0 && errors.length === 0,
    code: missing.length === 0 && errors.length === 0 ? 'CNNVD_DISCLOSURE_AUDIT_OK' : 'CNNVD_DISCLOSURE_AUDIT_FAILED',
    active: comp.active,
    missing,
    errors,
    fileNames,
    dropdownOpen,
    relatedCount: Array.isArray(form.vulIdList) ? form.vulIdList.length : 0,
  }};
}}""")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="输出 CNNVD 浏览器 evaluate_script 片段")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("probe-form-model", help="探查页面 Vue formModel 字段")
    sync = sub.add_parser("sync-form-model", help="按 form_context.json 同步 Vue formModel 和 TinyMCE")
    sync.add_argument("--form-context", required=True)
    disclosure = sub.add_parser("sync-disclosure-report", help="按 form_context.json 同步非原创漏洞通报页面数据")
    disclosure.add_argument("--form-context", required=True)
    disclosure.add_argument("--cnnvd-id", required=True)
    audit = sub.add_parser("audit-disclosure-report", help="检查非原创漏洞通报页面必填项和附件状态")
    audit.add_argument("--form-context", required=True)
    audit.add_argument("--cnnvd-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "probe-form-model":
        print(probe_form_model_script())
    elif args.command == "sync-form-model":
        print(sync_form_model_script(load_context(args.form_context)))
    elif args.command == "sync-disclosure-report":
        print(sync_disclosure_report_script(load_context(args.form_context), args.cnnvd_id))
    elif args.command == "audit-disclosure-report":
        print(audit_disclosure_report_script(load_context(args.form_context), args.cnnvd_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
