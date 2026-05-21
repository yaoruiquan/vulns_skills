#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出 CNVD 浏览器自动化常用 evaluate_script 片段。"""

from __future__ import annotations

import argparse
import json
import os
import shlex


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def as_iife(script: str) -> str:
    """把页面脚本包装成 Runtime.evaluate 可直接执行的表达式。"""
    code = script.strip()
    if code.startswith("async () =>") or code.startswith("() =>") or code.startswith("function"):
        return f"({code})()"
    return code


def select2_script(form_type: str, vuln_type: str, object_type: str) -> str:
    """生成 Select2 原位设值脚本。"""
    assignments = [
        {"name": "漏洞所属类型", "selectors": ["#isEvent1", "#isEvent"], "label": form_type},
        {"name": "漏洞类型", "selectors": ["#titlel1", "#titlel"], "label": vuln_type},
        {"name": "影响对象类型", "selectors": ["#softStyleId1", "#softStyleId"], "label": object_type},
    ]
    return as_iife(f"""async () => {{
  const assignments = {json.dumps(assignments, ensure_ascii=False)};
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const aliases = {{
    '通用型漏洞': '0',
    '事件型漏洞': '1',
    '操作系统': '27',
    '应用程序': '28',
    'WEB应用': '29',
    '数据库': '30',
    '网络设备': '31',
    '安全产品': '32',
    '智能设备': '33',
    '工业控制': '38',
    '其他': 'other',
    '其它': 'other'
  }};
  const normalize = (value) => String(value || '').replace(/\\s+/g, '').trim();
  const setNativeValue = (el, value) => {{
    const proto = Object.getPrototypeOf(el);
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor && descriptor.set) descriptor.set.call(el, value);
    else el.value = value;
  }};
  const fire = (el, type, detail = undefined) => {{
    const event = detail === undefined
      ? new Event(type, {{ bubbles: true }})
      : new CustomEvent(type, {{ bubbles: true, detail }});
    el.dispatchEvent(event);
  }};
  const resolveOption = (el, label) => {{
    const options = Array.from(el.options || []);
    const target = options.find((option) =>
      option.value === label ||
      option.value === aliases[label] ||
      option.text.trim() === label ||
      normalize(option.text) === normalize(label) ||
      normalize(option.text).includes(normalize(label)) ||
      normalize(label).includes(normalize(option.text))
    );
    return {{ options, target }};
  }};
  const setSelect2 = async (selectors, label) => {{
    let el = null;
    let options = [];
    let target = null;
    for (let attempt = 0; attempt < 10; attempt += 1) {{
      el = selectors.map((selector) => document.querySelector(selector)).find(Boolean);
      if (!el) {{
        await sleep(300);
        continue;
      }}
      const resolved = resolveOption(el, label);
      options = resolved.options;
      target = resolved.target;
      if (target) break;
      await sleep(300);
    }}
    if (!el) return {{ ok: false, reason: `未找到 ${{selectors.join(' / ')}}` }};
    if (!target) {{
      return {{
        ok: false,
        reason: `未找到选项: ${{label}}`,
        selector: selectors.find((selector) => document.querySelector(selector)),
        options: options.map((option) => ({{ value: option.value, text: option.text.trim() }}))
      }};
    }}
    setNativeValue(el, target.value);
    fire(el, 'input');
    fire(el, 'change');
    if (window.jQuery) {{
      const $el = window.jQuery(el);
      $el.val(target.value).trigger('input').trigger('change');
      if ($el.data('select2')) {{
        $el.trigger({{
          type: 'select2:select',
          params: {{ data: {{ id: target.value, text: target.text.trim(), element: target }} }}
        }});
      }}
    }}
    fire(el, 'blur');
    return {{
      ok: true,
      selector: selectors.find((selector) => document.querySelector(selector)),
      value: el.value,
      expectedValue: target.value,
      text: target.text.trim(),
      selectedText: el.selectedOptions && el.selectedOptions[0] ? el.selectedOptions[0].text.trim() : ''
    }};
  }};
  const results = [];
  for (const item of assignments) {{
    const result = await setSelect2(item.selectors, item.label);
    results.push({{ name: item.name, ...result }});
    await sleep(300);
  }}
  return {{
    ok: results.every((item) => item.ok),
    results
  }};
}}""")


def captcha_tab_script() -> str:
    """生成把当前验证码图片 URL 直接打开到新标签页的脚本。"""
    return as_iife("""() => {
  const image = document.querySelector('#codeSpan1 img') || document.querySelector('#codeSpan1');
  if (!image) return { ok: false, reason: '未找到 #codeSpan1 img 或 #codeSpan1' };
  if (image.tagName !== 'IMG') return { ok: false, reason: '#codeSpan1 不是 IMG 元素', tag: image.tagName };
  const rect = image.getBoundingClientRect();
  if (!image.complete || image.naturalWidth === 0 || image.naturalHeight === 0) {
    return {
      ok: false,
      code: 'CNVD_CAPTCHA_IMAGE_BROKEN',
      reason: '提交验证码图片未加载成功，通常是 /common/myCodeNew 触发了 CNVD 防火墙验证码；不要 OCR 页面占位文字。',
      src: image.currentSrc || image.src || image.getAttribute('src') || '',
      naturalWidth: image.naturalWidth,
      naturalHeight: image.naturalHeight,
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
      next: '保存当前页面或 /common/myCodeNew 防火墙页截图到 logs/human-cnvd-firewall.png，并等待人工输入防火墙验证码。'
    };
  }
  const rawSrc = image.currentSrc || image.src || image.getAttribute('src');
  if (!rawSrc) return { ok: false, reason: '验证码图片没有 src' };
  const src = new URL(rawSrc, location.href).href;
  const url = new URL(src);
  if (!/\\/common\\/myCodeNew$/i.test(url.pathname)) {
    return { ok: false, reason: '验证码地址不是 /common/myCodeNew，停止避免打开错误图片', src };
  }
  const win = window.open(src, '_blank');
  if (!win) return { ok: false, reason: '新窗口被浏览器拦截', src };
  return {
    ok: true,
    src,
    openedNewTab: true,
    currentTab: location.href,
    screenshotRule: '切到新标签页后只能截验证码 img 元素到 /tmp/captcha.png；禁止截整页或视口。'
  };
}""")


def captcha_preview_script() -> str:
    """兼容旧命令名；实际行为是直接打开验证码图片新标签页。"""
    return captcha_tab_script()


def login_guard_script() -> str:
    """生成登录态/拦截页检查脚本。"""
    return as_iife("""() => {
  const text = document.body ? document.body.innerText : '';
  const href = location.href;
  const hasCreateForm = Boolean(document.querySelector('#isEvent1, #title1, #flawAttFile, #subForm'));
  const cloudflarePattern = /cloudflare|cf-chl|turnstile|checking your browser|ray id|人机验证|安全验证|正在验证|验证您是真人/i;
  const hasCloudflare = !hasCreateForm && cloudflarePattern.test(text + ' ' + href);
  const hasPasswordInput = Boolean(document.querySelector('input[type="password"], input[name*="password"], input[id*="password"], #password'));
  const isLoginPage = !hasCreateForm && (/login|user\\/login/i.test(href) || hasPasswordInput || /用户登录|会员登录|登录名|密码/.test(text));
  return { ok: !hasCloudflare && !isLoginPage && hasCreateForm, hasCloudflare, isLoginPage, hasCreateForm, href };
}""")


def is_open_no_script() -> str:
    """生成将「是否公开」设为「否」的脚本。

    CNVD 页面有两组 name=isOpen 的 radio（一组隐藏、一组可见）。
    .find() 只找到第一组隐藏的，不会改 UI。本脚本遍历全部 4 个，
    确保所有 value=1(是) 都 unchecked、所有 value=0(否) 都 checked。
    """
    return as_iife("""() => {
  const radios = document.querySelectorAll('input[name="isOpen"]');
  const yes = []; const no = [];
  radios.forEach((r) => { (r.value === '0' ? no : yes).push(r); });
  yes.forEach((r) => { r.checked = false; });
  no.forEach((r) => {
    r.checked = true;
    r.dispatchEvent(new Event('click', { bubbles: true }));
    r.dispatchEvent(new Event('change', { bubbles: true }));
  });
  const allYesUnchecked = yes.every((r) => !r.checked);
  const allNoChecked = no.every((r) => r.checked);
  return { ok: allYesUnchecked && allNoChecked, yesCount: yes.length, noCount: no.length };
}""")


def attachment_prepare_script(attachment_path: str) -> str:
    """生成上传附件前定位并标记当前可见 file input 的脚本。"""
    expected_name = os.path.basename(attachment_path)
    return as_iife(f"""() => {{
  const expectedName = {js_string(expected_name)};
  const expectedPath = {js_string(attachment_path)};
  const isVisible = (el) => {{
    if (!el) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const form = el.closest('form');
    const formStyle = form ? getComputedStyle(form) : null;
    const formRect = form ? form.getBoundingClientRect() : null;
    return style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      Number(style.opacity || '1') > 0 &&
      rect.width > 0 &&
      rect.height > 0 &&
      (!form || (
        formStyle.display !== 'none' &&
        formStyle.visibility !== 'hidden' &&
        formRect.width > 0 &&
        formRect.height > 0
      ));
  }};
  const inputs = Array.from(document.querySelectorAll('input[type="file"][name="flawAttFile"], #flawAttFile1, #flawAttFile'));
  const details = inputs.map((el, index) => ({{
    index,
    id: el.id || '',
    name: el.name || '',
    visible: isVisible(el),
    disabled: el.disabled,
    accept: el.accept || '',
    files: el.files ? el.files.length : 0,
    fileName: el.files && el.files[0] ? el.files[0].name : '',
    formId: el.closest('form') ? (el.closest('form').id || '') : ''
  }}));
  const target = inputs.find((el) => el.id === 'flawAttFile1' && isVisible(el)) ||
    inputs.find((el) => isVisible(el) && el.name === 'flawAttFile') ||
    inputs.find((el) => isVisible(el));
  if (!target) {{
    return {{
      ok: false,
      code: 'CNVD_ATTACHMENT_TARGET_NOT_FOUND',
      reason: '未找到当前可见的漏洞附件 file input；禁止猜测上传目标。',
      expectedName,
      expectedPath,
      inputs: details
    }};
  }}
  for (const el of inputs) {{
    el.removeAttribute('data-opencode-upload-target');
    el.removeAttribute('aria-label');
    if (el !== target && !isVisible(el)) {{
      el.disabled = true;
      el.setAttribute('data-opencode-disabled-duplicate', 'true');
    }}
  }}
  target.disabled = false;
  target.setAttribute('data-opencode-upload-target', 'cnvd-attachment');
  target.setAttribute('aria-label', `CNVD 附件上传目标：仅将 ${{expectedName}} 上传到此控件`);
  target.scrollIntoView({{ block: 'center', inline: 'center' }});
  return {{
    ok: true,
    code: 'CNVD_ATTACHMENT_TARGET_READY',
    targetId: target.id || '',
    targetName: target.name || '',
    targetSelector: target.id ? `#${{target.id}}` : 'input[type=file][name=flawAttFile]',
    expectedName,
    expectedPath,
    uploadRule: '接下来必须 take_snapshot，并且只对带有 aria-label=\"CNVD 附件上传目标\" 的 file input 执行 MCP upload_file；禁止上传到其他 file input，禁止用 JS/DataTransfer/fetch 构造文件。',
    inputs: details
  }};
}}""")


def attachment_verify_script(attachment_path: str) -> str:
    """生成上传附件后的强校验脚本。"""
    expected_name = os.path.basename(attachment_path)
    return as_iife(f"""() => {{
  const expectedName = {js_string(expected_name)};
  const expectedPath = {js_string(attachment_path)};
  const invalidExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp'];
  const isVisible = (el) => {{
    if (!el) return false;
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const form = el.closest('form');
    const formStyle = form ? getComputedStyle(form) : null;
    const formRect = form ? form.getBoundingClientRect() : null;
    return style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      Number(style.opacity || '1') > 0 &&
      rect.width > 0 &&
      rect.height > 0 &&
      (!form || (
        formStyle.display !== 'none' &&
        formStyle.visibility !== 'hidden' &&
        formRect.width > 0 &&
        formRect.height > 0
      ));
  }};
  const inputs = Array.from(document.querySelectorAll('input[type="file"][name="flawAttFile"], #flawAttFile1, #flawAttFile'));
  const target = inputs.find((el) => el.getAttribute('data-opencode-upload-target') === 'cnvd-attachment') ||
    inputs.find((el) => el.id === 'flawAttFile1' && isVisible(el)) ||
    inputs.find((el) => isVisible(el) && el.name === 'flawAttFile');
  const details = inputs.map((el, index) => ({{
    index,
    id: el.id || '',
    name: el.name || '',
    visible: isVisible(el),
    disabled: el.disabled,
    markedTarget: el.getAttribute('data-opencode-upload-target') === 'cnvd-attachment',
    files: el.files ? el.files.length : 0,
    fileName: el.files && el.files[0] ? el.files[0].name : '',
    fileSize: el.files && el.files[0] ? el.files[0].size : 0,
    formId: el.closest('form') ? (el.closest('form').id || '') : ''
  }}));
  if (!target) {{
    return {{ ok: false, code: 'CNVD_ATTACHMENT_TARGET_LOST', reason: '上传后找不到可见附件目标，禁止继续提交。', expectedName, expectedPath, inputs: details }};
  }}
  const file = target.files && target.files[0] ? target.files[0] : null;
  if (!file) {{
    return {{ ok: false, code: 'CNVD_ATTACHMENT_FILE_EMPTY', reason: '当前可见附件 input 没有文件，禁止继续提交。', expectedName, expectedPath, targetId: target.id || '', inputs: details }};
  }}
  if (!file.size || file.size <= 0) {{
    return {{ ok: false, code: 'CNVD_ATTACHMENT_FILE_EMPTY', reason: `附件文件大小为 0，通常是 Chrome 无法读取上传路径或 CDP 中文路径上传失败。禁止继续提交。`, expectedName, actualName: file.name, fileSize: file.size || 0, expectedPath, targetId: target.id || '', inputs: details }};
  }}
  if (file.name !== expectedName) {{
    return {{ ok: false, code: 'CNVD_ATTACHMENT_FILE_MISMATCH', reason: `附件文件名不匹配，期望 ${{expectedName}}，实际 ${{file.name}}。禁止继续提交。`, expectedName, actualName: file.name, expectedPath, targetId: target.id || '', inputs: details }};
  }}
  if (!/\\.zip$/i.test(file.name) || invalidExtensions.some((ext) => file.name.toLowerCase().endsWith(ext))) {{
    return {{ ok: false, code: 'CNVD_ATTACHMENT_FILE_INVALID_TYPE', reason: `附件必须是 zip，实际为 ${{file.name}}。禁止继续提交。`, expectedName, actualName: file.name, expectedPath, targetId: target.id || '', inputs: details }};
  }}
  return {{
    ok: true,
    code: 'CNVD_ATTACHMENT_VERIFIED',
    targetId: target.id || '',
    fileName: file.name,
    fileSize: file.size,
    expectedName,
    expectedPath,
    inputs: details
  }};
}}""")


def submit_captcha_script(code: str) -> str:
    """生成填验证码并立即提交脚本。"""
    return as_iife(f"""() => {{
  const code = {js_string(code)};
  const text = String(code || '').trim();
  if (!text || /^ERROR\\b/i.test(text)) {{
    return {{
      ok: false,
      code: 'INVALID_OCR_TEXT',
      reason: 'OCR 结果为空或为错误输出；需重新获取真实验证码图片或进入防火墙人工处理。',
      value: code
    }};
  }}
  const input = document.querySelector('#myCode1');
  if (!input) return {{ ok: false, reason: '未找到验证码输入框 #myCode1' }};
  input.value = code;
  input.dispatchEvent(new Event('input', {{ bubbles: true }}));
  input.dispatchEvent(new Event('change', {{ bubbles: true }}));
  const submit = document.querySelector('#subForm');
  if (!submit) return {{ ok: false, reason: '未找到提交按钮 #subForm' }};
  submit.click();
  return {{ ok: true, code }};
}}""")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="输出 CNVD 浏览器 evaluate_script 片段")
    sub = parser.add_subparsers(dest="command", required=True)

    select2 = sub.add_parser("select2", help="输出 Select2 下拉框设值脚本")
    select2.add_argument("--form-type", default="通用型漏洞")
    select2.add_argument("--vuln-type", required=True)
    select2.add_argument("--object-type", default="应用程序")

    sub.add_parser("captcha-tab", help="输出把当前验证码图片 URL 打开到新标签页的脚本")
    sub.add_parser("captcha-preview", help="兼容旧命令名；同 captcha-tab")
    sub.add_parser("login-guard", help="输出登录态和 Cloudflare 拦截检查脚本")
    sub.add_parser("is-open", help="输出将是否公开设为否的脚本（处理 CNVD 两组 radio 的问题）")

    attachment_prepare = sub.add_parser("attachment-prepare", help="输出上传 CNVD 附件前定位当前可见 file input 的脚本")
    attachment_prepare.add_argument("--attachment-path", required=True)

    attachment_verify = sub.add_parser("attachment-verify", help="输出上传 CNVD 附件后的强校验脚本")
    attachment_verify.add_argument("--attachment-path", required=True)

    submit = sub.add_parser("submit-captcha", help="输出填入验证码并立即提交脚本")
    submit.add_argument("code")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "select2":
        print(select2_script(args.form_type, args.vuln_type, args.object_type))
    elif args.command == "captcha-tab":
        print(captcha_tab_script())
    elif args.command == "captcha-preview":
        print(captcha_preview_script())
    elif args.command == "login-guard":
        print(login_guard_script())
    elif args.command == "is-open":
        print(is_open_no_script())
    elif args.command == "attachment-prepare":
        print(attachment_prepare_script(args.attachment_path))
    elif args.command == "attachment-verify":
        print(attachment_verify_script(args.attachment_path))
    elif args.command == "submit-captcha":
        print(submit_captcha_script(args.code))
    return 0


def shell_command_for_select2(form_type: str, vuln_type: str, object_type: str) -> str:
    return "python3 scripts/browser_snippets.py select2 --form-type {} --vuln-type {} --object-type {}".format(
        shlex.quote(form_type),
        shlex.quote(vuln_type),
        shlex.quote(object_type),
    )


if __name__ == "__main__":
    raise SystemExit(main())
