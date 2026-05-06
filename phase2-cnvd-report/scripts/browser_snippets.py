#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出 CNVD 浏览器自动化常用 evaluate_script 片段。"""

from __future__ import annotations

import argparse
import json
import shlex


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def select2_script(form_type: str, vuln_type: str, object_type: str) -> str:
    """生成 Select2 原位设值脚本。"""
    assignments = [
        {"name": "漏洞所属类型", "selectors": ["#isEvent1", "#isEvent"], "label": form_type},
        {"name": "漏洞类型", "selectors": ["#titlel1", "#titlel"], "label": vuln_type},
        {"name": "影响对象类型", "selectors": ["#softStyleId1", "#softStyleId"], "label": object_type},
    ]
    return f"""async () => {{
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
  const resolveOption = (el, label) => {{
    const options = Array.from(el.options || []);
    const target = options.find((option) =>
      option.value === label ||
      option.value === aliases[label] ||
      option.text.trim() === label ||
      normalize(option.text) === normalize(label)
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
    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
    if (window.jQuery) {{
      const $el = window.jQuery(el);
      $el.val(target.value).trigger('change');
      if ($el.data('select2')) $el.trigger('select2:select');
    }}
    return {{
      ok: true,
      selector: selectors.find((selector) => document.querySelector(selector)),
      value: el.value,
      text: target.text.trim()
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
}}"""


def captcha_tab_script() -> str:
    """生成把当前验证码图片 URL 直接打开到新标签页的脚本。"""
    return """() => {
  const image = document.querySelector('#codeSpan1 img') || document.querySelector('#codeSpan1');
  if (!image) return { ok: false, reason: '未找到 #codeSpan1 img 或 #codeSpan1' };
  if (image.tagName !== 'IMG') return { ok: false, reason: '#codeSpan1 不是 IMG 元素', tag: image.tagName };
  const rawSrc = image.currentSrc || image.src || image.getAttribute('src');
  if (!rawSrc) return { ok: false, reason: '验证码图片没有 src' };
  const src = new URL(rawSrc, location.href).href;
  const url = new URL(src);
  if (!/\\/common\\/myCodeNew$/i.test(url.pathname)) {
    return { ok: false, reason: '验证码地址不是 /common/myCodeNew，停止避免打开错误图片', src };
  }
  const win = window.open(src, '_blank');
  if (!win) return { ok: false, reason: '新窗口被浏览器拦截', src };
  return { ok: true, src, openedNewTab: true, currentTab: location.href };
}"""


def captcha_preview_script() -> str:
    """兼容旧命令名；实际行为是直接打开验证码图片新标签页。"""
    return captcha_tab_script()


def login_guard_script() -> str:
    """生成登录态/拦截页检查脚本。"""
    return """() => {
  const text = document.body ? document.body.innerText : '';
  const href = location.href;
  const hasCreateForm = Boolean(document.querySelector('#isEvent1, #title1, #flawAttFile, #subForm'));
  const cloudflarePattern = /cloudflare|cf-chl|turnstile|checking your browser|ray id|人机验证|安全验证|正在验证|验证您是真人/i;
  const hasCloudflare = !hasCreateForm && cloudflarePattern.test(text + ' ' + href);
  const hasPasswordInput = Boolean(document.querySelector('input[type="password"], input[name*="password"], input[id*="password"], #password'));
  const isLoginPage = !hasCreateForm && (/login|user\\/login/i.test(href) || hasPasswordInput || /用户登录|会员登录|登录名|密码/.test(text));
  return { ok: !hasCloudflare && !isLoginPage && hasCreateForm, hasCloudflare, isLoginPage, hasCreateForm, href };
}"""


def is_open_no_script() -> str:
    """生成将「是否公开」设为「否」的脚本。

    CNVD 页面有两组 name=isOpen 的 radio（一组隐藏、一组可见）。
    .find() 只找到第一组隐藏的，不会改 UI。本脚本遍历全部 4 个，
    确保所有 value=1(是) 都 unchecked、所有 value=0(否) 都 checked。
    """
    return """() => {
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
}"""


def submit_captcha_script(code: str) -> str:
    """生成填验证码并立即提交脚本。"""
    return f"""() => {{
  const code = {js_string(code)};
  const input = document.querySelector('#myCode1');
  if (!input) return {{ ok: false, reason: '未找到验证码输入框 #myCode1' }};
  input.value = code;
  input.dispatchEvent(new Event('input', {{ bubbles: true }}));
  input.dispatchEvent(new Event('change', {{ bubbles: true }}));
  const submit = document.querySelector('#subForm');
  if (!submit) return {{ ok: false, reason: '未找到提交按钮 #subForm' }};
  submit.click();
  return {{ ok: true, code }};
}}"""


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
