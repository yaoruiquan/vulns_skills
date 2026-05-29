#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""输出 NCC 浏览器自动化常用 evaluate_script 片段。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def as_iife(script: str) -> str:
    """把页面脚本包装成 Runtime.evaluate 可直接执行的表达式。"""
    code = script.strip()
    if code.startswith("async () =>") or code.startswith("() =>") or code.startswith("function"):
        return f"({code})()"
    return code


def load_context(path: str) -> dict:
    """读取 form_context.json。"""
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def fill_form_script(context: dict) -> str:
    """生成按 label 填写 NCC 表单的浏览器脚本。"""
    ctx = json.dumps(context, ensure_ascii=False)
    return as_iife(f"""async () => {{
  const ctx = {ctx};
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const norm = (value) => String(value || '').replace(/[：:*\\s]/g, '').trim();
  const visible = (el) => {{
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  }};
  const formItems = () => [...document.querySelectorAll('.el-form-item')].filter(visible);
  const labelEntries = () => formItems().map((item) => {{
    const label = item.querySelector('.el-form-item__label');
    return {{ item, label: label ? norm(label.innerText) : '' }};
  }}).filter((entry) => entry.label);
  const itemByLabel = (labelText) => {{
    const wanted = norm(labelText);
    const items = labelEntries();
    const exact = items.find((entry) => entry.label === wanted);
    if (exact) return exact.item;
    if (wanted.length >= 4) {{
      const suffix = items.find((entry) => entry.label.endsWith(wanted));
      if (suffix) return suffix.item;
    }}
    if (wanted.length >= 6) {{
      const contains = items.find((entry) => entry.label.includes(wanted));
      if (contains) return contains.item;
    }}
    return null;
  }};
  const setNativeValue = (el, value) => {{
    const proto = Object.getPrototypeOf(el);
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor && descriptor.set) descriptor.set.call(el, value);
    else el.value = value;
  }};
  const fire = (el) => {{
    for (const type of ['input', 'change', 'blur']) {{
      el.dispatchEvent(new Event(type, {{ bubbles: true }}));
    }}
  }};
  const setByLabel = (labelText, value) => {{
    const item = itemByLabel(labelText);
    if (!item) return {{ ok: false, label: labelText, reason: 'form item not found' }};
    const target = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
    if (!target) return {{ ok: false, label: labelText, reason: 'input not found' }};
    setNativeValue(target, value || '');
    fire(target);
    return {{ ok: String(target.value || '').trim() === String(value || '').trim(), label: labelText, length: String(value || '').length }};
  }};
  const visiblePoppers = () => [...document.querySelectorAll('.el-select-dropdown, .el-popper')]
    .filter((popper) => visible(popper) && popper.querySelector('.el-select-dropdown__item'));
  const activePopperForItem = (item, openedAfter = new Set()) => {{
    const input = item.querySelector('input:not([type="hidden"])');
    const ids = [
      input?.getAttribute('aria-controls'),
      input?.getAttribute('aria-owns'),
      input?.getAttribute('aria-describedby'),
    ].filter(Boolean);
    for (const id of ids) {{
      const byId = document.getElementById(id);
      const popper = byId?.matches?.('.el-select-dropdown, .el-popper') ? byId : byId?.closest?.('.el-select-dropdown, .el-popper');
      if (popper && visible(popper)) return popper;
    }}
    const candidates = visiblePoppers();
    const fresh = candidates.find((popper) => !openedAfter.has(popper));
    if (fresh) return fresh;
    return candidates.at(-1) || null;
  }};
  const optionPool = (item, openedAfter = new Set()) => {{
    const popper = activePopperForItem(item, openedAfter);
    if (!popper) return [];
    return [...popper.querySelectorAll('.el-select-dropdown__item')]
      .filter((option) => visible(option) && !option.classList.contains('is-disabled'))
      .filter((option) => option.innerText.trim());
  }};
  const optionMatch = (options, wantedText, fallbackText = '其他') => {{
    const wanted = norm(wantedText);
    const fallback = norm(fallbackText);
    const exactWanted = options.find((option) => norm(option.innerText) === wanted);
    if (exactWanted) return exactWanted;
    if (wanted && wanted.length >= 4) {{
      const fuzzyWanted = options.find((option) => {{
        const text = norm(option.innerText);
        return text.includes(wanted) || wanted.includes(text);
      }});
      if (fuzzyWanted) return fuzzyWanted;
    }}
    const exactFallback = options.find((option) => norm(option.innerText) === fallback);
    if (exactFallback) return exactFallback;
    if (fallback && fallback.length >= 4) {{
      return options.find((option) => norm(option.innerText).includes(fallback));
    }}
    return null;
  }};
  const selectInItem = async (item, labelText, wantedText, fallbackText = '其他') => {{
    const trigger = item.querySelector('.el-select, .el-select__wrapper, input');
    if (!trigger) return {{ ok: false, label: labelText, reason: 'select trigger not found' }};
    const currentInput = item.querySelector('input:not([type="hidden"])');
    const currentText = String(currentInput?.value || item.innerText || '').trim();
    if (wantedText && norm(currentText).includes(norm(wantedText))) {{
      return {{ ok: true, label: labelText, selected: currentInput?.value || wantedText, skipped: 'already selected' }};
    }}
    document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }}));
    await sleep(100);
    const openedBefore = new Set(visiblePoppers());
    trigger.click();
    await sleep(350);
    let options = [];
    for (let attempt = 0; attempt < 8; attempt += 1) {{
      options = optionPool(item, openedBefore);
      if (options.length) break;
      await sleep(250);
    }}
    const optionTexts = options.map((option) => option.innerText.trim());
    const target = optionMatch(options, wantedText, fallbackText);
    if (!target) return {{ ok: false, label: labelText, wanted: wantedText, options: optionTexts }};
    const selected = target.innerText.trim();
    target.click();
    await sleep(500);
    const afterText = String(currentInput?.value || item.querySelector('input:not([type="hidden"])')?.value || '').trim();
    const verified = afterText ? norm(afterText).includes(norm(selected)) || norm(afterText).includes(norm(wantedText)) : true;
    return {{ ok: verified, label: labelText, selected, current: afterText, options: optionTexts }};
  }};
  const selectByLabel = async (labelText, wantedText, fallbackText = '其他') => {{
    const item = itemByLabel(labelText);
    if (!item) return {{ ok: false, label: labelText, reason: 'form item not found' }};
    return selectInItem(item, labelText, wantedText, fallbackText);
  }};
  const selectByLabels = async (labelTexts, wantedText, fallbackText = '其他') => {{
    if (!['是', '否'].includes(String(wantedText || '')) && labelTexts.some((label) => /0Day|0day|原创/.test(label))) {{
      return {{ ok: false, label: labelTexts.join('/'), reason: 'missing yes/no value' }};
    }}
    const missed = [];
    for (const labelText of labelTexts) {{
      const result = await selectByLabel(labelText, wantedText, fallbackText);
      if (result.ok || result.reason !== 'form item not found') return result;
      missed.push(labelText);
    }}
    return {{ ok: false, label: labelTexts.join('/'), reason: 'form item not found', missed }};
  }};
  const handledSelectLabels = new Set([
    '是否0Day漏洞',
    '是否0day漏洞',
    '0Day漏洞',
    '是否为原创漏洞',
    '是否原创漏洞',
    '是否原创',
    '漏洞业务类型',
    '漏洞类型',
    '影响对象',
    '厂商所属国家',
    '产品厂商所属国家',
    '产品厂商',
    '所属国家',
    '国家地区',
    '国家/地区',
    '国家',
    '漏洞详细分类',
  ].map(norm));
  const isHandledSelectLabel = (labelText) => {{
    const label = norm(labelText);
    return [...handledSelectLabels].some((handled) => label === handled || label.includes(handled));
  }};
  const fillDynamicBinaryFields = async () => {{
    const binary = ctx.browser_defaults?.binary_required_fields || {{}};
    const results = [];
    for (const [label, value] of Object.entries(binary)) {{
      if (itemByLabel(label)) results.push(setByLabel(label, value));
    }}
    return results;
  }};
  const fillRemainingRequiredSelects = async () => {{
    const results = [];
    for (let round = 0; round < 20; round += 1) {{
      const item = formItems().find((candidate) => {{
        const label = candidate.querySelector('.el-form-item__label')?.innerText.trim() || '';
        const required = candidate.classList.contains('is-required') || label.includes('*');
        if (!required) return false;
        const select = candidate.querySelector('.el-select, .el-select__wrapper');
        if (!select) return false;
        const cleanLabel = label.replace(/[：:*]/g, '').trim();
        if (isHandledSelectLabel(cleanLabel)) return false;
        const target = candidate.querySelector('textarea') || candidate.querySelector('input:not([type="hidden"])');
        return !String(target?.value || '').trim();
      }});
      if (!item) break;
      const label = item.querySelector('.el-form-item__label')?.innerText.trim() || '';
      const cleanLabel = label.replace(/[：:*]/g, '').trim();
      results.push(await selectInItem(item, cleanLabel, '其他', '其他'));
    }}
    return results;
  }};
  const fillRemainingRequiredText = async () => {{
    const results = [];
    for (const item of formItems()) {{
      const label = item.querySelector('.el-form-item__label')?.innerText.trim() || '';
      const required = item.classList.contains('is-required') || label.includes('*');
      if (!required) continue;
      const select = item.querySelector('.el-select, .el-select__wrapper');
      if (select) continue;
      const target = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
      const current = String(target?.value || '').trim();
      if (current) continue;
      const cleanLabel = label.replace(/[：:*]/g, '').trim();
      if (target) results.push(setByLabel(cleanLabel, '见附件'));
    }}
    return results;
  }};
  const auditRequired = () => {{
    const missing = [];
    for (const item of formItems()) {{
      const label = item.querySelector('.el-form-item__label')?.innerText.trim() || '';
      const required = item.classList.contains('is-required') || label.includes('*');
      if (!required) continue;
      const target = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
      const current = String(target?.value || '').trim();
      if (!current) missing.push(label.replace(/[：:*]/g, '').trim());
    }}
    return missing;
  }};
  const selectedTextByLabel = (labelText) => {{
    const item = itemByLabel(labelText);
    if (!item) return '';
    const input = item.querySelector('input:not([type="hidden"])');
    return String(input?.value || '').trim();
  }};
  const auditProtectedSelects = () => {{
    const expected = [
      ['漏洞业务类型', ctx.business_type || ctx.browser_defaults?.business_type || '通用型漏洞'],
      ['影响对象', ctx.target_type || ctx.browser_defaults?.target_type || '应用程序'],
      ['漏洞详细分类', ctx.detail_category || ctx.browser_defaults?.detail_category || '其他'],
    ];
    const mismatched = [];
    for (const [label, wanted] of expected) {{
      const current = selectedTextByLabel(label);
      if (current && wanted && !norm(current).includes(norm(wanted))) {{
        mismatched.push({{ label, current, wanted }});
      }}
    }}
    return mismatched;
  }};
  const results = [];
  results.push(await selectByLabels(['是否0Day漏洞', '是否0day漏洞', '0Day漏洞'], ctx.is_0day || ctx.browser_defaults?.is_0day || '', ''));
  results.push(await selectByLabels(['是否为原创漏洞', '是否原创漏洞', '是否原创'], ctx.is_original || ctx.browser_defaults?.is_original || '', ''));
  results.push(await selectByLabels(['漏洞业务类型', '漏洞类型'], ctx.business_type || ctx.browser_defaults?.business_type || '通用型漏洞', '通用型漏洞'));
  results.push(await selectByLabel('影响对象', ctx.target_type || ctx.browser_defaults?.target_type || '应用程序', '应用程序'));
  results.push(await selectByLabels(['厂商所属国家', '产品厂商所属国家', '产品厂商', '所属国家', '国家地区', '国家/地区', '国家'], ctx.vendor_country || ctx.browser_defaults?.vendor_country || '中国大陆', '中国大陆'));
  results.push(await selectByLabel('漏洞详细分类', ctx.detail_category || ctx.browser_defaults?.detail_category || '其他', '其他'));
  results.push(...await fillRemainingRequiredSelects());
  results.push(setByLabel('漏洞厂商', ctx.unit_name || '见附件'));
  results.push(setByLabel('影响组件', ctx.affected_product || '见附件'));
  results.push(setByLabel('影响版本', ctx.version || '见附件'));
  results.push(setByLabel('漏洞名称', ctx.title || '见附件'));
  results.push(...await fillDynamicBinaryFields());
  results.push(setByLabel('漏洞URL', ctx.url || '见附件'));
  results.push(setByLabel('漏洞描述', ctx.description || '见附件'));
  results.push(setByLabel('漏洞危害', ctx.impact || '见附件'));
  results.push(setByLabel('修复方案说明', ctx.formal_solution || ctx.temporary_solution || '见附件'));
  results.push(...await fillRemainingRequiredText());
  const missingRequired = auditRequired();
  const protectedSelectMismatches = auditProtectedSelects();
  return {{
    ok: results.every((item) => item.ok) && missingRequired.length === 0 && protectedSelectMismatches.length === 0,
    results,
    missingRequired,
    protectedSelectMismatches,
    uploadZipPath: ctx.upload_zip_path,
    attachmentPolicy: ctx.browser_defaults?.attachment_policy || ''
  }};
}}""")


def post_upload_audit_script(context: dict) -> str:
    """生成上传附件后的漏填检查和兜底补全脚本。"""
    ctx = json.dumps(context, ensure_ascii=False)
    return as_iife(f"""async () => {{
  const ctx = {ctx};
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const norm = (value) => String(value || '').replace(/[：:*\\s]/g, '').trim();
  const visible = (el) => {{
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  }};
  const formItems = () => [...document.querySelectorAll('.el-form-item')].filter(visible);
  const itemLabel = (item) => item.querySelector('.el-form-item__label')?.innerText.trim() || '';
  const cleanLabel = (label) => String(label || '').replace(/[：:*]/g, '').trim();
  const currentValue = (item) => {{
    const input = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
    return String(input?.value || '').trim();
  }};
  const visiblePoppers = () => [...document.querySelectorAll('.el-select-dropdown, .el-popper')]
    .filter((popper) => visible(popper) && popper.querySelector('.el-select-dropdown__item'));
  const activePopperForItem = (item, openedAfter = new Set()) => {{
    const input = item.querySelector('input:not([type="hidden"])');
    const ids = [
      input?.getAttribute('aria-controls'),
      input?.getAttribute('aria-owns'),
      input?.getAttribute('aria-describedby'),
    ].filter(Boolean);
    for (const id of ids) {{
      const byId = document.getElementById(id);
      const popper = byId?.matches?.('.el-select-dropdown, .el-popper') ? byId : byId?.closest?.('.el-select-dropdown, .el-popper');
      if (popper && visible(popper)) return popper;
    }}
    const candidates = visiblePoppers();
    const fresh = candidates.find((popper) => !openedAfter.has(popper));
    if (fresh) return fresh;
    return candidates.at(-1) || null;
  }};
  const optionPool = (item, openedAfter = new Set()) => {{
    const popper = activePopperForItem(item, openedAfter);
    if (!popper) return [];
    return [...popper.querySelectorAll('.el-select-dropdown__item')]
      .filter((option) => visible(option) && !option.classList.contains('is-disabled'))
      .filter((option) => option.innerText.trim());
  }};
  const optionMatch = (options, wantedText, fallbackText = '其他') => {{
    const wanted = norm(wantedText);
    const fallback = norm(fallbackText);
    const exactWanted = options.find((option) => norm(option.innerText) === wanted);
    if (exactWanted) return exactWanted;
    if (wanted && wanted.length >= 4) {{
      const fuzzyWanted = options.find((option) => {{
        const text = norm(option.innerText);
        return text.includes(wanted) || wanted.includes(text);
      }});
      if (fuzzyWanted) return fuzzyWanted;
    }}
    const exactFallback = options.find((option) => norm(option.innerText) === fallback);
    if (exactFallback) return exactFallback;
    if (fallback && fallback.length >= 4) {{
      return options.find((option) => norm(option.innerText).includes(fallback));
    }}
    return null;
  }};
  const setNativeValue = (el, value) => {{
    const proto = Object.getPrototypeOf(el);
    const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
    if (descriptor && descriptor.set) descriptor.set.call(el, value);
    else el.value = value;
  }};
  const fire = (el) => {{
    for (const type of ['input', 'change', 'blur']) {{
      el.dispatchEvent(new Event(type, {{ bubbles: true }}));
    }}
  }};
  const selectInItem = async (item, labelText, wantedText = '其他') => {{
    const trigger = item.querySelector('.el-select, .el-select__wrapper, input');
    if (!trigger) return {{ ok: false, label: labelText, reason: 'select trigger not found' }};
    const current = currentValue(item);
    if (current) return {{ ok: true, label: labelText, selected: current, skipped: 'already filled' }};
    document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }}));
    await sleep(100);
    const openedBefore = new Set(visiblePoppers());
    trigger.click();
    await sleep(350);
    let options = [];
    for (let attempt = 0; attempt < 8; attempt += 1) {{
      options = optionPool(item, openedBefore);
      if (options.length) break;
      await sleep(250);
    }}
    const optionTexts = options.map((option) => option.innerText.trim());
    const target = optionMatch(options, wantedText, '其他');
    if (!target) return {{ ok: false, label: labelText, wanted: wantedText, options: optionTexts }};
    const selected = target.innerText.trim();
    target.click();
    await sleep(500);
    const afterText = currentValue(item);
    const verified = afterText ? norm(afterText).includes(norm(selected)) || norm(afterText).includes(norm(wantedText)) : true;
    return {{ ok: verified, label: labelText, selected, current: afterText, options: optionTexts }};
  }};
  const fillTextInItem = (item, labelText) => {{
    const target = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
    if (!target) return {{ ok: false, label: labelText, reason: 'input not found' }};
    if (String(target.value || '').trim()) return {{ ok: true, label: labelText, skipped: 'already filled' }};
    setNativeValue(target, '见附件');
    fire(target);
    return {{ ok: String(target.value || '').trim() === '见附件', label: labelText, filled: '见附件' }};
  }};
  const protectedExpected = new Map([
    [norm('漏洞业务类型'), ctx.business_type || ctx.browser_defaults?.business_type || '通用型漏洞'],
    [norm('漏洞类型'), ctx.business_type || ctx.browser_defaults?.business_type || '通用型漏洞'],
    [norm('影响对象'), ctx.target_type || ctx.browser_defaults?.target_type || '应用程序'],
    [norm('漏洞详细分类'), ctx.detail_category || ctx.browser_defaults?.detail_category || '其他'],
    [norm('是否0Day漏洞'), ctx.is_0day || ctx.browser_defaults?.is_0day || ''],
    [norm('是否0day漏洞'), ctx.is_0day || ctx.browser_defaults?.is_0day || ''],
    [norm('是否为原创漏洞'), ctx.is_original || ctx.browser_defaults?.is_original || ''],
    [norm('是否原创漏洞'), ctx.is_original || ctx.browser_defaults?.is_original || ''],
    [norm('是否原创'), ctx.is_original || ctx.browser_defaults?.is_original || ''],
  ]);
  const protectedWanted = (labelText) => {{
    const label = norm(labelText);
    for (const [key, value] of protectedExpected.entries()) {{
      if (label === key || label.includes(key)) return value;
    }}
    return '';
  }};
  const patched = [];
  const skippedProtected = [];
  for (let round = 0; round < 40; round += 1) {{
    const next = formItems().find((candidate) => {{
      const rawLabel = itemLabel(candidate);
      const required = candidate.classList.contains('is-required') || rawLabel.includes('*');
      return required && !currentValue(candidate);
    }});
    if (!next) break;
    const rawLabel = itemLabel(next);
    const label = cleanLabel(rawLabel);
    const select = next.querySelector('.el-select, .el-select__wrapper');
    const wantedProtected = protectedWanted(label);
    if (select) patched.push(await selectInItem(next, label, wantedProtected || '其他'));
    else patched.push(fillTextInItem(next, label));
  }}
  for (const item of formItems()) {{
    const rawLabel = itemLabel(item);
    const label = cleanLabel(rawLabel);
    const required = item.classList.contains('is-required') || rawLabel.includes('*');
    if (!required) continue;
    const wantedProtected = protectedWanted(label);
    const value = currentValue(item);
    if (wantedProtected && value && !norm(value).includes(norm(wantedProtected))) {{
      skippedProtected.push({{ label, current: value, wanted: wantedProtected }});
    }}
  }}
  const missingRequired = [];
  for (const item of formItems()) {{
    const rawLabel = itemLabel(item);
    const required = item.classList.contains('is-required') || rawLabel.includes('*');
    if (!required) continue;
    if (!currentValue(item)) missingRequired.push(cleanLabel(rawLabel));
  }}
  return {{
    ok: patched.every((item) => item.ok) && missingRequired.length === 0 && skippedProtected.length === 0,
    patched,
    missingRequired,
    skippedProtected,
  }};
}}""")


def guard_script() -> str:
    """生成登录态/滑块验证检查脚本。"""
    return as_iife("""() => {
  const text = document.body ? document.body.innerText : '';
  const href = location.href;
  const hasCreateForm = /vulnerabilities\\/create/i.test(href) || /是否为原创漏洞|漏洞详细分类|漏洞附件/.test(text);
  const hasSlider = /滑块|拖动|拼图|安全验证|阿里云|验证码/.test(text);
  const hasPasswordInput = Boolean(document.querySelector('input[type="password"]'));
  const isLoginPage = /login/i.test(href) || hasPasswordInput || /企业|请输入密码|登录/.test(text);
  return {
    ok: hasCreateForm && !hasSlider,
    href,
    hasCreateForm,
    hasSlider,
    isLoginPage,
    next: hasSlider ? '需要人工完成阿里云/拼图滑块验证，再继续自动化。' : ''
  };
}""")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="输出 NCC 浏览器 evaluate_script 片段")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fill = subparsers.add_parser("fill-form", help="按 form_context.json 生成填表脚本")
    fill.add_argument("--context", required=True, help="form_context.json 路径")

    audit = subparsers.add_parser("post-upload-audit", help="上传附件后检查漏填必填项并兜底补全")
    audit.add_argument("--context", required=True, help="form_context.json 路径")

    subparsers.add_parser("guard", help="生成登录态/滑块验证检查脚本")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "fill-form":
        print(fill_form_script(load_context(args.context)))
        return 0
    if args.command == "post-upload-audit":
        print(post_upload_audit_script(load_context(args.context)))
        return 0
    if args.command == "guard":
        print(guard_script())
        return 0
    parser.error(f"未知命令: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
