# CNVD 漏洞上报流程

## 流程概览

```text
Step 0: 检查环境 -> Step 1: 准备 FormContext -> Step 2: 导航表单 -> Step 3: 填表 -> Step 4: 上传 -> Step 4.5: 验证 -> Step 5: 提交并提取编号 -> Step 6: 钉钉通知
```

---

## Step 1: 准备 FormContext

### 1.1 生成 `form_context.json`

```bash
python3 scripts/prepare_form_context.py <DAS-ID或DAS目录或CNVD目录或docx路径> --data-dir "<数据目录>"
```

**输出示例**：
```json
{
  "output": "/path/to/CNVD-xxx/form_context.json",
  "ready": true,
  "checks": {
    "title_input_ready": true,
    "title_final_expected_ready": true,
    "attachment_exists": true,
    "attachment_is_file": true,
    "attachment_is_zip": true,
    "attachment_name_starts_with_cnvd": true,
    "description_ready": true,
    "is_open_no": true,
    "no_browser_phase_extraction": true
  }
}
```

### 1.2 浏览器阶段规则

`form_context.json` 是浏览器填表阶段唯一数据源。浏览器阶段只允许读取它，不要重新运行提取脚本、重新压缩目录或重新判断标题。

关键字段：

| 字段 | 用途 |
|------|------|
| `title_input` | CNVD 页面“漏洞名称”输入框填写值 |
| `title_final_expected` | 提交后预期最终标题，用于一致性校验 |
| `attachment_zip_path` | CNVD 原始整包 zip 上传路径 |
| `attachment_status` | 附件存在性、类型、大小和命名检查 |
| `checks` / `ready` | 准备阶段是否允许进入浏览器填表 |

### 1.3 附件预检查

附件必须使用 CNVD 平台目录中的原始整包 zip，即 `form_context.json` 中的 `attachment_zip_path`。

- `ready` 必须为 `true` 才能进入浏览器阶段。
- 不要把 docx 所在目录重新压缩成 `/tmp/<DAS-ID>-CNVD.zip`。
- 如果 `attachment_exists`、`attachment_is_zip` 或 `attachment_name_starts_with_cnvd` 为 `false`，先修复材料目录，再继续上报。

---

## Step 2: 导航到表单页面

### 2.1 打开 CNVD 首页

```
MCP: navigate_page
  type: "url"
  url: "https://www.cnvd.org.cn/"
```

### 2.2 点击登录

```
MCP: take_snapshot
MCP: click
  uid: "<登录链接的 uid>"
```

### 2.3 处理登录验证码

参见 [captcha-ocr.md](captcha-ocr.md)。

### 2.4 导航到漏洞上报表单

```
MCP: take_snapshot
MCP: click
  uid: "<用户中心的 uid>"

MCP: take_snapshot
MCP: click
  uid: "<立即上报漏洞的 uid>"
```

---

## Step 3: 填写表单

### 3.1 切换表单类型 + 选择漏洞类型

**关键步骤**：先切换到"通用型漏洞"，然后选择漏洞类型。

```
MCP: take_snapshot

# 切换到"通用型漏洞"
MCP: fill
  uid: "<漏洞所属类型下拉框的 uid>"
  value: "通用型漏洞"

# 等待表单刷新后，选择漏洞类型
MCP: take_snapshot
MCP: fill
  uid: "<漏洞类型下拉框的 uid>"
  value: "<vuln_type>"
```

**注意：二进制漏洞特殊字段**

当选择"二进制"类型时，表单会显示额外字段：

| 字段 | 说明 | 填写内容 |
|------|------|----------|
| 版本号 | 影响版本 | `<version>` |
| 触发位置 | 漏洞触发位置 | 从漏洞描述中提取 |
| Poc | 漏洞验证代码 | 填写"见附件" |

### 3.2 填写基本信息

切换到"通用型漏洞"后，发现者和发现日期保持默认值不变，只修改"是否公开"。基本信息里的“是否公开”必须选择“否”。

```
MCP: take_snapshot
MCP: evaluate_script
  function: |
    () => {
      const candidates = Array.from(document.querySelectorAll('input[name="isOpen"]'));
      const noRadio = candidates.find((el) => el.value === '0' || el.value === '否');
      if (!noRadio) return { ok: false, reason: '未找到是否公开=否的 radio' };
      noRadio.click();
      noRadio.dispatchEvent(new Event('change', { bubbles: true }));
      return { ok: true, value: noRadio.value };
    }
```

执行后必须确认返回 `ok: true`。如果页面快照显示“否”未选中，不要提交。

### 3.3 填写厂商信息

```
MCP: take_snapshot
MCP: fill_form
  elements:
    - uid: "<漏洞厂商输入框的 uid>"
      value: "<unit_name>"
    - uid: "<厂商官网输入框的 uid>"
      value: "<url>"
    - uid: "<影响对象类型下拉框的 uid>"
      value: "<soft_style_id 对应的中文>"
    - uid: "<影响产品输入框的 uid>"
      value: "<affected_product>"
    - uid: "<影响产品版本输入框的 uid>"
      value: "<version>"
```

### 3.4 填写漏洞详情

**重要：漏洞名称填写规则**

标题拆分在准备阶段已经固化，浏览器阶段不要重新拆分。

- “漏洞名称”输入框：填写 `form_context.json` 的 `title_input`。
- 提交后最终标题：必须与 `form_context.json` 的 `title_final_expected` 一致。
- “漏洞类型”下拉框：填写 `form_context.json` 的 `vuln_type`。

```
MCP: take_snapshot
MCP: fill_form
  elements:
    - uid: "<漏洞名称输入框的 uid>"
      value: "<title_input>"
    - uid: "<漏洞类型下拉框的 uid>"
      value: "<vuln_type>"
    - uid: "<漏洞描述输入框的 uid>"
      value: "<description>"
    - uid: "<临时解决方案输入框的 uid>"
      value: "无"
    - uid: "<正式解决方案输入框的 uid>"
      value: "见附件"
```

---

## Step 4: 上传附件

```
MCP: take_snapshot
MCP: upload_file
  uid: "<文件上传输入框的 uid>"
  filePath: "<attachment_zip_path>"
```

这里的 `<attachment_zip_path>` 必须来自 `form_context.json`，并且准备阶段 `ready` 必须为 `true`。

---

## Step 4.5: 验证表单完整性

**提交前必须验证所有字段已填写完整**。

**检查清单**：

| 字段 | 要求 | 默认值/空值处理 |
|------|------|----------------|
| 发现者 | ✓ 已填写 | 保持默认 |
| 发现日期 | ✓ 已填写 | 保持默认 |
| 漏洞所属类型 | ✓ 已选择 | 必须为"通用型漏洞" |
| 是否公开 | ✓ 选择"否" | 必须手动选择 |
| 漏洞厂商 | ✓ 已填写 | 从数据获取 |
| 厂商官网 | ✓ 已填写 | 从数据获取 |
| 影响对象类型 | ✓ 已选择 | 从数据获取 |
| 影响产品 | ✓ 已填写 | 从数据获取 |
| 影响产品版本 | ✓ 已填写 | 从数据获取 |
| 漏洞名称 | ✓ 已填写 | 从数据获取 |
| 漏洞类型 | ✓ 已选择 | 从数据获取 |
| 漏洞描述 | ✓ 已填写 | 从数据获取 |
| 临时解决方案 | ✓ 已填写 | 默认填写"无" |
| 正式解决方案 | ✓ 已填写 | 默认填写"见附件" |
| 漏洞附件 | ✓ 已上传 | `attachment_zip_path` 指向的 CNVD 原始 zip |
| 验证码 | 待填写 | OCR识别后填写 |

同时检查：

- `form_context.json` 的 `ready` 为 `true`。
- 页面中“漏洞名称”输入值等于 `title_input`。
- 上传附件路径等于 `attachment_zip_path`。
- 提交后页面返回的最终漏洞标题应等于 `title_final_expected`。

推荐在提交前执行一次页面内校验，避免“表单未填写完整”：

```
MCP: evaluate_script
  function: |
    () => {
      const valueOf = (selector) => {
        const el = document.querySelector(selector);
        return el ? String(el.value || '').trim() : '';
      };
      const isOpenNo = Array.from(document.querySelectorAll('input[name="isOpen"]'))
        .some((el) => (el.value === '0' || el.value === '否') && el.checked);
      const required = {
        "漏洞所属类型": valueOf('#isEvent1'),
        "是否公开": isOpenNo ? '否' : '',
        "漏洞厂商": valueOf('#manuName'),
        "厂商官网": valueOf('#changshang1'),
        "影响对象类型": valueOf('#softStyleId1'),
        "影响产品": valueOf('#productCategoryName'),
        "影响版本": valueOf('#edition'),
        "漏洞名称": valueOf('#title1'),
        "漏洞类型": valueOf('#titlel1'),
        "漏洞描述": valueOf('#description1'),
        "临时解决方案": valueOf('#tempWay1'),
        "正式解决方案": valueOf('#formalWay11')
      };
      return Object.entries(required)
        .filter(([, value]) => !value)
        .map(([field]) => field);
    }
```

返回必须为空数组；如果返回字段名，先补齐再提交。

---

## Step 5: 验证码、提交与提取编号

参见 [captcha-ocr.md](captcha-ocr.md)。

提交成功后提取 CNVD-ID：

```
MCP: evaluate_script
  function: |
    () => {
      const content = document.body.innerText;
      const match = content.match(/CNVD-[C-]?\d+-\d+/);
      return match ? match[0] : null;
    }
```

记录：

- `DAS-ID`
- `CNVD-ID`
- 提交时间
- 页面成功提示或返回结果

---

## Step 6: 推送钉钉通知

提交成功后，如果 `.env` 已配置 `DINGTALK_WEBHOOK`，优先上传本漏洞的 CNVD 原始整包 zip，并把漏洞名称、`DAS-ID`、本次平台编号和下载链接推送到钉钉：

```bash
python3 scripts/publish_submission_zip.py \
  "<CNVD材料目录>/form_context.json" \
  --platform-id "<CNVD-ID>" \
  --notify
```

该脚本只上传 `form_context.json` 中的 `submission_zip_path` / `attachment_zip_path`，即单个漏洞的 CNVD 原始整包 zip；不会上传整个批次目录，也不会重新压缩。默认远端目录为 `/root/msrc-report-downloads/cnvd-submissions/YYYY-MM/DAS-ID/`。

失败时也应推送失败原因，便于群里跟踪：

```bash
python3 scripts/dingtalk_notify.py \
  --title "监管上报 CNVD 上报失败" \
  --status failed \
  --text "DAS-ID：<DAS-ID>\n失败原因：<原因>"
```

> CSS 选择器参考详见 [selectors.md](selectors.md)
> 字段映射表详见 [field-mapping.md](field-mapping.md)
