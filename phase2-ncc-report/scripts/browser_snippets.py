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
  const FAST_WAIT = 80;
  const OPEN_WAIT = 120;
  const SELECT_WAIT = 160;
  const MAX_OPTION_ATTEMPTS = 5;
  const norm = (value) => String(value || '').replace(/[：:*\\s]/g, '').trim();
  const styleVisible = (el) => {{
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.visibility !== 'hidden' && style.display !== 'none' && el.getAttribute('aria-hidden') !== 'true';
  }};
  const visible = (el) => {{
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    if (!styleVisible(el)) return false;
    if (el.matches?.('.el-select-dropdown, .el-popper, .el-select-dropdown__item')) return true;
    return rect.width > 0 && rect.height > 0;
  }};
  const popperUsable = (popper) => styleVisible(popper) && popper.querySelector('.el-select-dropdown__item');
  const optionUsable = (option) => {{
    const popper = option.closest('.el-select-dropdown, .el-popper');
    return styleVisible(option) && (!popper || styleVisible(popper)) && !option.classList.contains('is-disabled') && Boolean(option.innerText.trim());
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
  const itemText = (item) => String(item?.innerText || '').trim();
  const selectedValueInItem = (item) => {{
    const input = item?.querySelector('input:not([type="hidden"])');
    const selected = item?.querySelector('.el-select__selected-item, .el-select__tags-text, .el-input__inner');
    return String(input?.value || selected?.innerText || '').trim();
  }};
  const isPlaceholderSelectValue = (value) => {{
    const text = norm(value);
    return !text || /^请选择/.test(String(value || '').trim()) || ['请选择', '请选择类型', '请选择中间件/框架'].map(norm).includes(text);
  }};
  const clickSelectTrigger = (item) => {{
    const target =
      item.querySelector('.el-select input:not([type="hidden"])') ||
      item.querySelector('.el-select__wrapper') ||
      item.querySelector('.el-select') ||
      item.querySelector('input:not([type="hidden"])');
    if (!target) return null;
    target.focus?.();
    for (const type of ['mousedown', 'mouseup', 'click']) {{
      target.dispatchEvent(new MouseEvent(type, {{ bubbles: true, cancelable: true, view: window }}));
    }}
    return target;
  }};
  const clickRadioInItem = (item, labelText, wantedText, fallbackText = '') => {{
    if (!item) return {{ ok: false, label: labelText, reason: 'form item not found' }};
    const wanted = norm(wantedText);
    const fallback = norm(fallbackText);
    const elementRadios = [...item.querySelectorAll('.el-radio')].filter(visible);
    const fallbackRadios = [...item.querySelectorAll('[role="radio"], input[type="radio"], label')].filter(visible);
    const radios = elementRadios.length ? elementRadios : fallbackRadios;
    const radioText = (radio) => String(radio.querySelector?.('.el-radio__label')?.innerText || radio.innerText || radio.value || radio.getAttribute('aria-label') || '').trim();
    const target =
      radios.find((radio) => norm(radioText(radio)) === wanted) ||
      radios.find((radio) => wanted && norm(radioText(radio)).includes(wanted)) ||
      radios.find((radio) => fallback && norm(radioText(radio)) === fallback);
    if (!target) return {{ ok: false, label: labelText, wanted: wantedText, reason: 'radio option not found', options: radios.map(radioText).filter(Boolean) }};
    target.click();
    const selected = radioText(target) || wantedText;
    return {{ ok: true, label: labelText, selected, type: 'radio' }};
  }};
  const radioGroups = () => {{
    const groups = [...document.querySelectorAll('.el-radio-group, [role="radiogroup"]')].filter(visible);
    if (groups.length) return groups;
    return formItems().filter((item) => item.querySelector('.el-radio, [role="radio"], input[type="radio"]'));
  }};
  const clickRadioGroupByIndex = (groupIndex, labelText, wantedText, fallbackText = '') => {{
    const group = radioGroups()[groupIndex];
    if (!group) return {{ ok: false, label: labelText, wanted: wantedText, reason: 'radio group not found', groupIndex, groupCount: radioGroups().length }};
    return clickRadioInItem(group, labelText, wantedText, fallbackText);
  }};
  const forceRadioGroupByIndex = (groupIndex, labelText, wantedText, fallbackText = '') => {{
    const result = clickRadioGroupByIndex(groupIndex, labelText, wantedText, fallbackText);
    return result.ok ? {{ ...result, forced: 'radioGroupIndex', groupIndex }} : result;
  }};
  const chooseByLabelOrRadioGroup = async (labelTexts, groupIndex, wantedText, fallbackText = '', dropdownIndex = null) => {{
    const result = await chooseByLabels(labelTexts, wantedText, fallbackText, dropdownIndex);
    if (result.ok) return result;
    const fallback = clickRadioGroupByIndex(groupIndex, labelTexts[0], wantedText, fallbackText);
    return fallback.ok ? {{ ...fallback, fallback: 'radioGroupIndex', originalResult: result }} : result;
  }};
  const chooseByLabel = async (labelText, wantedText, fallbackText = '其他', dropdownIndex = null) => {{
    const item = itemByLabel(labelText);
    if (!item) return {{ ok: false, label: labelText, reason: 'form item not found', availableLabels: labelEntries().map((entry) => entry.label) }};
    const hasSelect = Boolean(item.querySelector('.el-select, .el-select__wrapper'));
    if (hasSelect) return selectInItem(item, labelText, wantedText, fallbackText, dropdownIndex);
    if (item.querySelector('.el-radio, [role="radio"], input[type="radio"]')) return clickRadioInItem(item, labelText, wantedText, fallbackText);
    return {{ ok: false, label: labelText, reason: 'choice control not found', itemText: itemText(item).slice(0, 120) }};
  }};
  const visiblePoppers = () => [...document.querySelectorAll('.el-select-dropdown, .el-popper')]
    .filter(popperUsable);
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
      if (popper && popperUsable(popper)) return popper;
    }}
    const candidates = visiblePoppers();
    const fresh = candidates.find((popper) => !openedAfter.has(popper));
    if (fresh) return fresh;
    return candidates.at(-1) || null;
  }};
  const optionPool = (item, openedAfter = new Set()) => {{
    const visibleOptions = () => [...document.querySelectorAll('.el-select-dropdown__item')]
      .filter(optionUsable);
    const popper = activePopperForItem(item, openedAfter);
    if (!popper) return visibleOptions();
    const scoped = [...popper.querySelectorAll('.el-select-dropdown__item')]
      .filter(optionUsable);
    return scoped.length ? scoped : visibleOptions();
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
  const indexedOptionPool = (dropdownIndex) => {{
    if (!Number.isInteger(dropdownIndex)) return [];
    const dropdown = [...document.querySelectorAll('.el-select-dropdown')][dropdownIndex];
    if (!dropdown) return [];
    return [...dropdown.querySelectorAll('.el-select-dropdown__item')]
      .filter((option) => !option.classList.contains('is-disabled'))
      .filter((option) => option.innerText.trim());
  }};
  const clickOption = (option) => {{
    option.scrollIntoView?.({{ block: 'nearest' }});
    for (const type of ['mouseenter', 'mousemove', 'mousedown', 'mouseup', 'click']) {{
      option.dispatchEvent(new MouseEvent(type, {{ bubbles: true, cancelable: true, view: window }}));
    }}
  }};
  const selectInItem = async (item, labelText, wantedText, fallbackText = '其他', dropdownIndex = null) => {{
    const currentInput = item.querySelector('input:not([type="hidden"])');
    const currentText = selectedValueInItem(item);
    if (wantedText && norm(currentText).includes(norm(wantedText))) {{
      return {{ ok: true, label: labelText, selected: currentInput?.value || wantedText, skipped: 'already selected' }};
    }}
    document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }}));
    await sleep(FAST_WAIT);
    const openedBefore = new Set(visiblePoppers());
    const trigger = clickSelectTrigger(item);
    if (!trigger) return {{ ok: false, label: labelText, reason: 'select trigger not found' }};
    await sleep(OPEN_WAIT);
    let options = [];
    for (let attempt = 0; attempt < MAX_OPTION_ATTEMPTS; attempt += 1) {{
      options = Number.isInteger(dropdownIndex) ? indexedOptionPool(dropdownIndex) : optionPool(item, openedBefore);
      if (options.length) break;
      await sleep(FAST_WAIT);
    }}
    const optionTexts = options.map((option) => option.innerText.trim());
    const target = optionMatch(options, wantedText, fallbackText);
    if (!target) return {{ ok: false, label: labelText, wanted: wantedText, dropdownIndex, options: optionTexts }};
    const selected = target.innerText.trim();
    clickOption(target);
    await sleep(SELECT_WAIT);
    const afterText = selectedValueInItem(item);
    const verified = Boolean(afterText) && !isPlaceholderSelectValue(afterText) && (norm(afterText).includes(norm(selected)) || norm(afterText).includes(norm(wantedText)));
    return {{ ok: verified, label: labelText, selected, current: afterText, dropdownIndex, options: optionTexts, reason: verified ? '' : 'selected option did not update this control' }};
  }};
  const selectByLabel = async (labelText, wantedText, fallbackText = '其他', dropdownIndex = null) => {{
    const item = itemByLabel(labelText);
    if (!item) return {{ ok: false, label: labelText, reason: 'form item not found' }};
    return selectInItem(item, labelText, wantedText, fallbackText, dropdownIndex);
  }};
  const chooseByLabels = async (labelTexts, wantedText, fallbackText = '其他', dropdownIndex = null) => {{
    if (!['是', '否'].includes(String(wantedText || '')) && labelTexts.some((label) => /0Day|0day|原创/.test(label))) {{
      return {{ ok: false, label: labelTexts.join('/'), reason: 'missing yes/no value' }};
    }}
    const missed = [];
    for (const labelText of labelTexts) {{
      const result = await chooseByLabel(labelText, wantedText, fallbackText, dropdownIndex);
      if (result.ok || result.reason !== 'form item not found') return result;
      missed.push(labelText);
    }}
    return {{ ok: false, label: labelTexts.join('/'), reason: 'form item not found', missed, availableLabels: labelEntries().map((entry) => entry.label) }};
  }};
  const selectByLabels = async (labelTexts, wantedText, fallbackText = '其他', dropdownIndex = null) => {{
    if (!['是', '否'].includes(String(wantedText || '')) && labelTexts.some((label) => /0Day|0day|原创/.test(label))) {{
      return {{ ok: false, label: labelTexts.join('/'), reason: 'missing yes/no value' }};
    }}
    const missed = [];
    for (const labelText of labelTexts) {{
      const result = await selectByLabel(labelText, wantedText, fallbackText, dropdownIndex);
      if (result.ok || result.reason !== 'form item not found') return result;
      missed.push(labelText);
    }}
    return {{ ok: false, label: labelTexts.join('/'), reason: 'form item not found', missed, availableLabels: labelEntries().map((entry) => entry.label) }};
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
      const item = itemByLabel(label);
      if (!item) continue;
      const target = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
      if (String(target?.value || '').trim()) {{
        results.push({{ ok: true, label, skipped: 'already filled' }});
      }} else {{
        results.push(setByLabel(label, value));
      }}
    }}
    return results;
  }};
  const findItemByLabels = (labels) => {{
    for (const label of labels) {{
      const item = itemByLabel(label);
      if (item) return {{ item, label }};
    }}
    return {{ item: null, label: labels[0] || '' }};
  }};
  const setByLabelsIfPresent = (labels, value) => {{
    const {{ item, label }} = findItemByLabels(labels);
    if (!item) return {{ ok: true, label: labels.join('/'), skipped: 'dynamic field not present' }};
    const target = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
    if (!target) return {{ ok: false, label, reason: 'input not found' }};
    if (String(target.value || '').trim()) return {{ ok: true, label, skipped: 'already filled' }};
    setNativeValue(target, value || '见附件');
    fire(target);
    return {{ ok: String(target.value || '').trim() === String(value || '见附件').trim(), label, length: String(value || '见附件').length }};
  }};
  const selectByLabelsIfPresent = async (labels, wantedText = '其他', required = false) => {{
    const {{ item, label }} = findItemByLabels(labels);
    if (!item) return {{ ok: !required, label: labels.join('/'), reason: required ? 'required dynamic select not present' : '', skipped: required ? '' : 'dynamic select not present' }};
    return selectInItem(item, label, wantedText, '其他');
  }};
  const radioByLabelsIfPresent = (labels, wantedText, fallbackText = '') => {{
    const {{ item, label }} = findItemByLabels(labels);
    if (!item) return {{ ok: true, label: labels.join('/'), skipped: 'dynamic radio not present' }};
    return clickRadioInItem(item, label, wantedText, fallbackText);
  }};
  const requestMethodForSqlPoc = () => {{
    const explicit = String(ctx.request_method || '').toLowerCase();
    if (explicit.includes('post')) return 'post';
    if (explicit.includes('get')) return 'get';
    const poc = String(ctx.poc_text || ctx.verification || '').toLowerCase();
    return poc.includes('post') ? 'post' : 'get';
  }};
  const sqlPocText = () => String(ctx.poc_text || ctx.verification || '').trim() || '见附件';
  const setSqlCodeMirrorPoc = () => {{
    const editors = [...document.querySelectorAll('.CodeMirror')]
      .map((node) => node.CodeMirror)
      .filter(Boolean);
    if (!editors.length) return {{ ok: true, label: 'SQL注入Poc CodeMirror', skipped: 'CodeMirror not present' }};
    const value = sqlPocText();
    const editor = editors.find((cm) => !String(cm.getValue?.() || '').trim()) || editors[0];
    editor.setValue(value);
    editor.save?.();
    editor.refresh?.();
    const current = String(editor.getValue?.() || '').trim();
    return {{ ok: current === value.trim(), label: 'SQL注入Poc CodeMirror', length: value.length, currentLength: current.length }};
  }};
  const linkedCategoryRules = {{
    [norm('SQL注入')]: {{
      radios: [{{ labels: ['SQL注入Poc', 'SQL注入POC', 'SQL注入PoC'], value: requestMethodForSqlPoc(), fallback: 'get' }}],
      texts: [{{ labels: ['目录导航'], value: '见附件' }}],
    }},
    [norm('XSS')]: {{
      texts: [{{ labels: ['触发xss的payload', '触发XSS的payload', 'payload'], value: '见附件' }}],
    }},
    [norm('弱口令')]: {{
      texts: [
        {{ labels: ['弱口令账号'], value: '见附件' }},
        {{ labels: ['弱口令密码'], value: '见附件' }},
      ],
    }},
    [norm('命令执行')]: {{
      selects: [
        {{ labels: ['类型'], value: '其他', required: true }},
        {{ labels: ['中间件/框架'], value: '其他', required: true }},
      ],
      texts: [{{ labels: ['利用工具'], value: '见附件' }}],
    }},
    [norm('拒绝服务')]: {{
      texts: [
        {{ labels: ['PoC', 'POC', 'poc'], value: '见附件' }},
        {{ labels: ['触发过程'], value: '见附件' }},
      ],
    }},
    [norm('二进制')]: {{
      texts: [
        {{ labels: ['版本号'], value: ctx.version || '见附件' }},
        {{ labels: ['触发位置'], value: '见附件' }},
        {{ labels: ['PoC', 'POC', 'poc'], value: '见附件' }},
      ],
    }},
    [norm('工控设备')]: {{
      texts: [
        {{ labels: ['触发位置'], value: '见附件' }},
        {{ labels: ['PoC', 'POC', 'poc'], value: '见附件' }},
      ],
    }},
    [norm('其他')]: {{
      texts: [{{ labels: ['poc', 'PoC', 'POC'], value: '见附件' }}],
    }},
  }};
  const activeLinkedCategoryRule = () => {{
    const category = ctx.detail_category || ctx.browser_defaults?.detail_category || '';
    return linkedCategoryRules[norm(category)] || null;
  }};
  const linkedRuleLabels = (rule) => [
    ...(rule?.selects || []).flatMap((entry) => entry.labels || []),
    ...(rule?.radios || []).flatMap((entry) => entry.labels || []),
    ...(rule?.texts || []).flatMap((entry) => entry.labels || []),
  ];
  const waitForLinkedCategoryFields = async (rule) => {{
    const labels = linkedRuleLabels(rule);
    if (!labels.length) return {{ ok: true, skipped: 'no linked fields for category' }};
    for (let attempt = 0; attempt < 12; attempt += 1) {{
      if (labels.some((label) => itemByLabel(label))) return {{ ok: true, attempts: attempt + 1 }};
      await sleep(OPEN_WAIT);
    }}
    const requiredLabels = [
      ...(rule?.selects || []).filter((entry) => entry.required).flatMap((entry) => entry.labels || []),
      ...(rule?.radios || []).filter((entry) => entry.required).flatMap((entry) => entry.labels || []),
      ...(rule?.texts || []).filter((entry) => entry.required).flatMap((entry) => entry.labels || []),
    ];
    const missingRequiredLabels = requiredLabels.filter((label) => !itemByLabel(label));
    return {{ ok: missingRequiredLabels.length === 0, reason: missingRequiredLabels.length ? 'required linked fields not present after wait' : '', skipped: missingRequiredLabels.length ? '' : 'linked fields not present after wait', labels, missingRequiredLabels }};
  }};
  const fillLinkedCategoryFields = async () => {{
    const rule = activeLinkedCategoryRule();
    if (!rule) return [{{ ok: true, skipped: 'no linked rule', category: ctx.detail_category || '' }}];
    const results = [await waitForLinkedCategoryFields(rule)];
    for (const entry of rule.selects || []) {{
      results.push(await selectByLabelsIfPresent(entry.labels, entry.value || '其他', Boolean(entry.required)));
    }}
    for (const entry of rule.radios || []) {{
      results.push(radioByLabelsIfPresent(entry.labels, entry.value || entry.fallback || '', entry.fallback || ''));
    }}
    if (norm(ctx.detail_category || ctx.browser_defaults?.detail_category || '') === norm('SQL注入')) {{
      results.push(setSqlCodeMirrorPoc());
    }}
    for (const entry of rule.texts || []) {{
      results.push(setByLabelsIfPresent(entry.labels, entry.value || '见附件'));
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
  const phaseResults = {{ protectedChoices: [], dynamicChoices: [], text: [] }};
  phaseResults.protectedChoices.push(forceRadioGroupByIndex(0, '漏洞业务类型', ctx.business_type || ctx.browser_defaults?.business_type || '通用型漏洞', '通用型漏洞'));
  phaseResults.protectedChoices.push(forceRadioGroupByIndex(1, '是否0Day漏洞', ctx.is_0day || ctx.browser_defaults?.is_0day || '', ''));
  phaseResults.protectedChoices.push(forceRadioGroupByIndex(2, '是否原创漏洞', ctx.is_original || ctx.browser_defaults?.is_original || '', ''));
  phaseResults.protectedChoices.push(await chooseByLabel('影响对象', ctx.target_type || ctx.browser_defaults?.target_type || '应用程序', '应用程序', 0));
  phaseResults.protectedChoices.push(await chooseByLabels(['产品厂商归属国家及地区', '产品厂商归属国家/地区', '产品厂商归属地', '厂商归属国家及地区', '厂商归属国家/地区', '厂商归属地', '厂商所属国家及地区', '厂商所属国家/地区', '厂商所属国家', '产品厂商所属国家及地区', '产品厂商所属国家/地区', '产品厂商所属国家', '所属国家及地区', '所属国家/地区', '所属国家', '国家地区', '国家/地区', '国家'], ctx.vendor_country || ctx.browser_defaults?.vendor_country || '中国大陆', '中国大陆', 1));
  phaseResults.protectedChoices.push(await chooseByLabel('漏洞详细分类', ctx.detail_category || ctx.browser_defaults?.detail_category || '其他', '其他', 2));
  phaseResults.protectedChoices.push(await chooseByLabel('修复方案', ctx.solution_type || ctx.browser_defaults?.solution_type || '临时方案', '临时方案'));
  const protectedChoiceFailures = phaseResults.protectedChoices.filter((item) => !item.ok);
  if (protectedChoiceFailures.length) {{
    return {{
      ok: false,
      stoppedBeforeText: true,
      reason: 'protected choices failed; text fields were not filled',
      protectedChoiceFailures,
      results: [...phaseResults.protectedChoices],
      phaseResults,
      uploadZipPath: ctx.upload_zip_path,
      attachmentPolicy: ctx.browser_defaults?.attachment_policy || ''
    }};
  }}
  const guidanceFailures = [];
  const invalidGuidanceValue = (value) => {{
    const text = String(value || '').trim();
    return !text || ['见附件', '无', '暂无', 'N/A', 'n/a', '-', '--'].includes(text);
  }};
  const solutionText = ctx.formal_solution || ctx.temporary_solution || '';
  if (invalidGuidanceValue(ctx.impact)) guidanceFailures.push('漏洞危害缺失或仍为占位值');
  if (invalidGuidanceValue(solutionText)) guidanceFailures.push('修复方案说明缺失或仍为占位值');
  if (guidanceFailures.length) {{
    return {{
      ok: false,
      stoppedBeforeText: true,
      reason: 'security guidance failed; impact and solution must be completed during prepare stage',
      guidanceFailures,
      securityGuidance: ctx.security_guidance || null,
      results: [...phaseResults.protectedChoices],
      phaseResults,
      uploadZipPath: ctx.upload_zip_path,
      attachmentPolicy: ctx.browser_defaults?.attachment_policy || ''
    }};
  }}
  phaseResults.dynamicChoices.push(...await fillLinkedCategoryFields());
  phaseResults.dynamicChoices.push(...await fillRemainingRequiredSelects());
  results.push(...phaseResults.protectedChoices, ...phaseResults.dynamicChoices);
  results.push(setByLabel('漏洞厂商', ctx.unit_name || '见附件'));
  results.push(setByLabel('影响组件', ctx.affected_product || '见附件'));
  results.push(setByLabel('影响版本', ctx.version || '见附件'));
  results.push(setByLabel('漏洞名称', ctx.title || '见附件'));
  results.push(...await fillDynamicBinaryFields());
  results.push(setByLabel('漏洞URL', ctx.url || '见附件'));
  results.push(setByLabel('漏洞描述', ctx.description || '见附件'));
  results.push(setByLabel('漏洞危害', ctx.impact));
  results.push(setByLabel('修复方案说明', solutionText));
  results.push(...await fillRemainingRequiredText());
  phaseResults.text.push(...results.filter((item) => !phaseResults.protectedChoices.includes(item) && !phaseResults.dynamicChoices.includes(item)));
  const missingRequired = auditRequired();
  const protectedSelectMismatches = auditProtectedSelects();
  return {{
    ok: results.every((item) => item.ok) && missingRequired.length === 0 && protectedSelectMismatches.length === 0,
    results,
    phaseResults,
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
  const FAST_WAIT = 80;
  const OPEN_WAIT = 120;
  const SELECT_WAIT = 160;
  const MAX_OPTION_ATTEMPTS = 5;
  const norm = (value) => String(value || '').replace(/[：:*\\s]/g, '').trim();
  const styleVisible = (el) => {{
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.visibility !== 'hidden' && style.display !== 'none' && el.getAttribute('aria-hidden') !== 'true';
  }};
  const visible = (el) => {{
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    if (!styleVisible(el)) return false;
    if (el.matches?.('.el-select-dropdown, .el-popper, .el-select-dropdown__item')) return true;
    return rect.width > 0 && rect.height > 0;
  }};
  const popperUsable = (popper) => styleVisible(popper) && popper.querySelector('.el-select-dropdown__item');
  const optionUsable = (option) => {{
    const popper = option.closest('.el-select-dropdown, .el-popper');
    return styleVisible(option) && (!popper || styleVisible(popper)) && !option.classList.contains('is-disabled') && Boolean(option.innerText.trim());
  }};
  const formItems = () => [...document.querySelectorAll('.el-form-item')].filter(visible);
  const itemLabel = (item) => item.querySelector('.el-form-item__label')?.innerText.trim() || '';
  const cleanLabel = (label) => String(label || '').replace(/[：:*]/g, '').trim();
  const currentValue = (item) => {{
    const input = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
    return String(input?.value || '').trim();
  }};
  const selectedValueInItem = (item) => {{
    const input = item?.querySelector('input:not([type="hidden"])');
    const selected = item?.querySelector('.el-select__selected-item, .el-select__tags-text, .el-input__inner');
    return String(input?.value || selected?.innerText || '').trim();
  }};
  const clickSelectTrigger = (item) => {{
    const target =
      item.querySelector('.el-select input:not([type="hidden"])') ||
      item.querySelector('.el-select__wrapper') ||
      item.querySelector('.el-select') ||
      item.querySelector('input:not([type="hidden"])');
    if (!target) return null;
    target.focus?.();
    for (const type of ['mousedown', 'mouseup', 'click']) {{
      target.dispatchEvent(new MouseEvent(type, {{ bubbles: true, cancelable: true, view: window }}));
    }}
    return target;
  }};
  const visiblePoppers = () => [...document.querySelectorAll('.el-select-dropdown, .el-popper')]
    .filter(popperUsable);
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
      if (popper && popperUsable(popper)) return popper;
    }}
    const candidates = visiblePoppers();
    const fresh = candidates.find((popper) => !openedAfter.has(popper));
    if (fresh) return fresh;
    return candidates.at(-1) || null;
  }};
  const optionPool = (item, openedAfter = new Set()) => {{
    const visibleOptions = () => [...document.querySelectorAll('.el-select-dropdown__item')]
      .filter(optionUsable);
    const popper = activePopperForItem(item, openedAfter);
    if (!popper) return visibleOptions();
    const scoped = [...popper.querySelectorAll('.el-select-dropdown__item')]
      .filter(optionUsable);
    return scoped.length ? scoped : visibleOptions();
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
    const current = selectedValueInItem(item);
    if (current && !isPlaceholderSelectValue(current)) return {{ ok: true, label: labelText, selected: current, skipped: 'already filled' }};
    document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }}));
    await sleep(FAST_WAIT);
    const openedBefore = new Set(visiblePoppers());
    const trigger = clickSelectTrigger(item);
    if (!trigger) return {{ ok: false, label: labelText, reason: 'select trigger not found' }};
    await sleep(OPEN_WAIT);
    let options = [];
    for (let attempt = 0; attempt < MAX_OPTION_ATTEMPTS; attempt += 1) {{
      options = optionPool(item, openedBefore);
      if (options.length) break;
      await sleep(FAST_WAIT);
    }}
    const optionTexts = options.map((option) => option.innerText.trim());
    const target = optionMatch(options, wantedText, '其他');
    if (!target) return {{ ok: false, label: labelText, wanted: wantedText, options: optionTexts }};
    const selected = target.innerText.trim();
    target.click();
    await sleep(SELECT_WAIT);
    const afterText = selectedValueInItem(item);
    const verified = Boolean(afterText) && !isPlaceholderSelectValue(afterText) && (norm(afterText).includes(norm(selected)) || norm(afterText).includes(norm(wantedText)));
    return {{ ok: verified, label: labelText, selected, current: afterText, options: optionTexts, reason: verified ? '' : 'selected option did not update this control' }};
  }};
  const fillTextInItem = (item, labelText) => {{
    const target = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
    if (!target) return {{ ok: false, label: labelText, reason: 'input not found' }};
    if (String(target.value || '').trim()) return {{ ok: true, label: labelText, skipped: 'already filled' }};
    setNativeValue(target, '见附件');
    fire(target);
    return {{ ok: String(target.value || '').trim() === '见附件', label: labelText, filled: '见附件' }};
  }};
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
  const findItemByLabels = (labels) => {{
    for (const label of labels) {{
      const item = itemByLabel(label);
      if (item) return {{ item, label }};
    }}
    return {{ item: null, label: labels[0] || '' }};
  }};
  const setByLabelsIfPresent = (labels, value = '见附件') => {{
    const {{ item, label }} = findItemByLabels(labels);
    if (!item) return {{ ok: true, label: labels.join('/'), skipped: 'dynamic field not present' }};
    const target = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])');
    if (!target) return {{ ok: false, label, reason: 'input not found' }};
    if (String(target.value || '').trim()) return {{ ok: true, label, skipped: 'already filled' }};
    setNativeValue(target, value || '见附件');
    fire(target);
    return {{ ok: String(target.value || '').trim() === String(value || '见附件').trim(), label, length: String(value || '见附件').length }};
  }};
  const selectByLabelsIfPresent = async (labels, wantedText = '其他', required = false) => {{
    const {{ item, label }} = findItemByLabels(labels);
    if (!item) return {{ ok: !required, label: labels.join('/'), reason: required ? 'required dynamic select not present' : '', skipped: required ? '' : 'dynamic select not present' }};
    return selectInItem(item, label, wantedText);
  }};
  const clickRadioInItem = (item, labelText, wantedText, fallbackText = '') => {{
    if (!item) return {{ ok: false, label: labelText, reason: 'form item not found' }};
    const wanted = norm(wantedText);
    const fallback = norm(fallbackText);
    const radios = [...item.querySelectorAll('.el-radio, [role="radio"], input[type="radio"], label')].filter(visible);
    const radioText = (radio) => String(radio.querySelector?.('.el-radio__label')?.innerText || radio.innerText || radio.value || radio.getAttribute('aria-label') || '').trim();
    const target =
      radios.find((radio) => norm(radioText(radio)) === wanted) ||
      radios.find((radio) => wanted && norm(radioText(radio)).includes(wanted)) ||
      radios.find((radio) => fallback && norm(radioText(radio)) === fallback);
    if (!target) return {{ ok: false, label: labelText, wanted: wantedText, reason: 'radio option not found', options: radios.map(radioText).filter(Boolean) }};
    target.click();
    return {{ ok: true, label: labelText, selected: radioText(target) || wantedText, type: 'radio' }};
  }};
  const radioByLabelsIfPresent = (labels, wantedText, fallbackText = '') => {{
    const {{ item, label }} = findItemByLabels(labels);
    if (!item) return {{ ok: true, label: labels.join('/'), skipped: 'dynamic radio not present' }};
    return clickRadioInItem(item, label, wantedText, fallbackText);
  }};
  const requestMethodForSqlPoc = () => {{
    const explicit = String(ctx.request_method || '').toLowerCase();
    if (explicit.includes('post')) return 'post';
    if (explicit.includes('get')) return 'get';
    const poc = String(ctx.poc_text || ctx.verification || '').toLowerCase();
    return poc.includes('post') ? 'post' : 'get';
  }};
  const sqlPocText = () => String(ctx.poc_text || ctx.verification || '').trim() || '见附件';
  const setSqlCodeMirrorPoc = () => {{
    const editors = [...document.querySelectorAll('.CodeMirror')]
      .map((node) => node.CodeMirror)
      .filter(Boolean);
    if (!editors.length) return {{ ok: true, label: 'SQL注入Poc CodeMirror', skipped: 'CodeMirror not present' }};
    const value = sqlPocText();
    const editor = editors.find((cm) => !String(cm.getValue?.() || '').trim()) || editors[0];
    editor.setValue(value);
    editor.save?.();
    editor.refresh?.();
    const current = String(editor.getValue?.() || '').trim();
    return {{ ok: current === value.trim(), label: 'SQL注入Poc CodeMirror', length: value.length, currentLength: current.length }};
  }};
  const linkedCategoryRules = {{
    [norm('SQL注入')]: {{
      radios: [{{ labels: ['SQL注入Poc', 'SQL注入POC', 'SQL注入PoC'], value: requestMethodForSqlPoc(), fallback: 'get' }}],
      texts: [{{ labels: ['目录导航'], value: '见附件' }}],
    }},
    [norm('XSS')]: {{
      texts: [{{ labels: ['触发xss的payload', '触发XSS的payload', 'payload'], value: '见附件' }}],
    }},
    [norm('弱口令')]: {{
      texts: [
        {{ labels: ['弱口令账号'], value: '见附件' }},
        {{ labels: ['弱口令密码'], value: '见附件' }},
      ],
    }},
    [norm('命令执行')]: {{
      selects: [
        {{ labels: ['类型'], value: '其他', required: true }},
        {{ labels: ['中间件/框架'], value: '其他', required: true }},
      ],
      texts: [{{ labels: ['利用工具'], value: '见附件' }}],
    }},
    [norm('拒绝服务')]: {{
      texts: [
        {{ labels: ['PoC', 'POC', 'poc'], value: '见附件' }},
        {{ labels: ['触发过程'], value: '见附件' }},
      ],
    }},
    [norm('二进制')]: {{
      texts: [
        {{ labels: ['版本号'], value: ctx.version || '见附件' }},
        {{ labels: ['触发位置'], value: '见附件' }},
        {{ labels: ['PoC', 'POC', 'poc'], value: '见附件' }},
      ],
    }},
    [norm('工控设备')]: {{
      texts: [
        {{ labels: ['触发位置'], value: '见附件' }},
        {{ labels: ['PoC', 'POC', 'poc'], value: '见附件' }},
      ],
    }},
    [norm('其他')]: {{
      texts: [{{ labels: ['poc', 'PoC', 'POC'], value: '见附件' }}],
    }},
  }};
  const fillLinkedCategoryFields = async () => {{
    const rule = linkedCategoryRules[norm(ctx.detail_category || ctx.browser_defaults?.detail_category || '')];
    if (!rule) return [{{ ok: true, skipped: 'no linked rule', category: ctx.detail_category || '' }}];
    const allLabels = [
      ...(rule?.selects || []).flatMap((entry) => entry.labels || []),
      ...(rule?.radios || []).flatMap((entry) => entry.labels || []),
      ...(rule?.texts || []).flatMap((entry) => entry.labels || []),
    ];
    const requiredLabels = [
      ...(rule?.selects || []).filter((entry) => entry.required).flatMap((entry) => entry.labels || []),
      ...(rule?.radios || []).filter((entry) => entry.required).flatMap((entry) => entry.labels || []),
      ...(rule?.texts || []).filter((entry) => entry.required).flatMap((entry) => entry.labels || []),
    ];
    const waitResult = {{ ok: true, skipped: 'no linked fields for category' }};
    if (allLabels.length) {{
      waitResult.skipped = '';
      for (let attempt = 0; attempt < 12; attempt += 1) {{
        if (allLabels.some((label) => itemByLabel(label))) {{
          waitResult.attempts = attempt + 1;
          break;
        }}
        await sleep(OPEN_WAIT);
      }}
      const missingRequiredLabels = requiredLabels.filter((label) => !itemByLabel(label));
      waitResult.ok = missingRequiredLabels.length === 0;
      waitResult.reason = missingRequiredLabels.length ? 'required linked fields not present after wait' : '';
      waitResult.missingRequiredLabels = missingRequiredLabels;
    }}
    const results = [waitResult];
    for (const entry of rule.selects || []) {{
      results.push(await selectByLabelsIfPresent(entry.labels, entry.value || '其他', Boolean(entry.required)));
    }}
    for (const entry of rule.radios || []) {{
      results.push(radioByLabelsIfPresent(entry.labels, entry.value || entry.fallback || '', entry.fallback || ''));
    }}
    if (norm(ctx.detail_category || ctx.browser_defaults?.detail_category || '') === norm('SQL注入')) {{
      results.push(setSqlCodeMirrorPoc());
    }}
    for (const entry of rule.texts || []) {{
      results.push(setByLabelsIfPresent(entry.labels, entry.value || '见附件'));
    }}
    return results;
  }};
  const protectedExpected = new Map([
    [norm('漏洞业务类型'), ctx.business_type || ctx.browser_defaults?.business_type || '通用型漏洞'],
    [norm('漏洞类型'), ctx.business_type || ctx.browser_defaults?.business_type || '通用型漏洞'],
    [norm('影响对象'), ctx.target_type || ctx.browser_defaults?.target_type || '应用程序'],
    [norm('产品厂商归属国家及地区'), ctx.vendor_country || ctx.browser_defaults?.vendor_country || '中国大陆'],
    [norm('产品厂商归属国家/地区'), ctx.vendor_country || ctx.browser_defaults?.vendor_country || '中国大陆'],
    [norm('厂商所属国家及地区'), ctx.vendor_country || ctx.browser_defaults?.vendor_country || '中国大陆'],
    [norm('厂商所属国家/地区'), ctx.vendor_country || ctx.browser_defaults?.vendor_country || '中国大陆'],
    [norm('所属国家及地区'), ctx.vendor_country || ctx.browser_defaults?.vendor_country || '中国大陆'],
    [norm('国家/地区'), ctx.vendor_country || ctx.browser_defaults?.vendor_country || '中国大陆'],
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
  patched.push(...await fillLinkedCategoryFields());
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
  const uploadName = String(ctx.upload_zip_path || '').split(/[\\\\/]/).pop();
  const uploadSelectors = [
    '.el-upload-list',
    '.el-upload-list__item',
    '.el-upload-list__item-name',
    '[class*="upload"]',
    '[class*="Upload"]'
  ];
  const attachmentElements = [...document.querySelectorAll(uploadSelectors.join(','))];
  const attachmentText = attachmentElements.map((el) => el.innerText || el.textContent || '').join('\\n');
  const bodyText = document.body ? document.body.innerText : '';
  const uploadErrorPatterns = ['请选择漏洞附件', '请选择附件', '附件不能为空', '上传失败', '文件不存在', '上传错误'];
  const uploadErrors = uploadErrorPatterns.filter((item) => attachmentText.includes(item) || bodyText.includes(item));
  const exactAttachmentMatch = Boolean(uploadName && (attachmentText.includes(uploadName) || bodyText.includes(uploadName)));
  const anyUploadItem = Boolean(document.querySelector('.el-upload-list__item, .el-upload-list__item-name, [class*="upload-list"] [class*="item"]'));
  const attachmentUploaded = Boolean(uploadName && exactAttachmentMatch && uploadErrors.length === 0);
  const finalCheck = {{
    missingRequired,
    skippedProtected,
    attachmentUploaded,
    expectedAttachment: uploadName,
    exactAttachmentMatch,
    anyUploadItem,
    uploadErrors,
    attachmentEvidence: attachmentText.slice(0, 1000),
  }};
  return {{
    ok: patched.every((item) => item.ok) && missingRequired.length === 0 && skippedProtected.length === 0 && attachmentUploaded,
    patched,
    ...finalCheck,
    finalCheck,
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
