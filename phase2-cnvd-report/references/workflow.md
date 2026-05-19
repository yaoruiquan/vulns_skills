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

默认输出到 `/tmp/vulns-skills/phase2-cnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json`。运行时 JSON 不写入 CNVD 材料目录；如需指定其他位置，使用 `--output`。

注意：本 skill 的所有 Python 命令一律使用 `python3`，不要使用 `python`。

**输出示例**：
```json
{
  "output": "/tmp/vulns-skills/phase2-cnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json",
  "ready": true,
  "checks": {
    "form_type_ready": true,
    "title_input_ready": true,
    "title_final_expected_ready": true,
    "attachment_exists": true,
    "attachment_is_file": true,
    "attachment_is_zip": true,
    "attachment_name_starts_with_cnvd": true,
    "description_ready": true,
    "detail_url_ready": true,
    "is_open_no": true,
    "no_browser_phase_extraction": true
  }
}
```

### 1.2 浏览器阶段规则

`form_context.json` 是浏览器填表阶段唯一数据源。浏览器阶段只允许读取它，不要重新运行提取脚本、重新读取 Word、重新压缩目录或重新判断标题。

关键字段：

| 字段 | 用途 |
|------|------|
| `form_type_label` | 页面“漏洞所属类型”下拉框填写值，先选“通用型漏洞”或“事件型漏洞” |
| `title_input` | CNVD 页面“漏洞名称”输入框填写值 |
| `title_final_expected` | 提交后预期最终标题，用于一致性校验 |
| `description` / `detail_url` | 漏洞详情页直接填写值；`detail_url` 固定为 `http://test.com` |
| `temp_solution` / `formal_solution` | 漏洞详情页固定默认值，分别为 `无` / `见附件` |
| `attachment_zip_path` | CNVD 原始整包 zip 上传路径 |
| `attachment_status` | 附件存在性、类型、大小和命名检查 |
| `dropdown_phase` | 浏览器阶段先处理的下拉框目标值 |
| `page_payloads` | 页面联动后直接一次性填写的分页字段 |
| `browser_helpers` | 登录态检查、Select2 下拉框、验证码新标签页开图/提交脚本生成命令 |
| `ocr` | 验证码图片本地单次识别命令 |
| `checks` / `ready` | 准备阶段是否允许进入浏览器填表 |

### 1.3 附件预检查

附件必须使用 CNVD 平台目录中的原始整包 zip，即 `form_context.json` 中的 `attachment_zip_path`。

- `ready` 必须为 `true` 才能进入浏览器阶段。
- 不要把 docx 所在目录随手压成临时 `/tmp/<DAS-ID>-CNVD.zip`。
- 如果材料目录里还没有 `CNVD-*.zip`，准备阶段会在材料目录父级自动补建一个单漏洞整包 zip，再继续上报。

---

## Step 2: 导航到表单页面

### 2.1 打开 CNVD 首页

```
MCP: navigate_page
  type: "url"
  url: "https://www.cnvd.org.cn/"
```

> **注意**：首次访问 CNVD 首页会触发 Cloudflare 验证码保护（"本站开启了验证码保护"），必须先 OCR 识别该验证码并提交，才能进入首页。

### 2.2 处理门户验证码

门户防火墙验证码先 OCR，最多 3 次。每次失败后点击“换一张”或刷新验证码，重新截图新验证码，不复用旧图和旧结果；3 次仍未通过再写入 `等待人工防火墙验证码` 进度并等待前端人工输入。

```
MCP: take_snapshot
# 确认页面显示"本站开启了验证码保护"
MCP: take_screenshot
  uid: "<验证码 img 的 uid>"
  filePath: "/tmp/captcha_portal.png"
```

```bash
python3 scripts/captcha_ocr.py /tmp/captcha_portal.png --preprocess cnvd
```

```
MCP: fill
  uid: "<验证码输入框的 uid>"
  value: "<OCR 识别结果>"
MCP: click
  uid: "<提交验证码按钮的 uid>"
MCP: wait_for
  text: ["首页", "登录", "免费注册"]
```

验证通过后会进入 CNVD 首页。

### 2.3 点击登录

```
MCP: take_snapshot
MCP: click
  uid: "<登录链接的 uid>"
```

### 2.4 处理登录验证码

参见 [captcha-ocr.md](captcha-ocr.md)。

### 2.5 导航到漏洞上报表单

```
MCP: take_snapshot
MCP: click
  uid: "<用户中心的 uid>"

MCP: take_snapshot
MCP: click
  uid: "<立即上报漏洞的 uid>"
```

### 2.6 登录态与 Cloudflare 检查

进入表单后必须先执行登录态检查，不要直接开始填表。优先使用 `form_context.json.browser_helpers.login_guard_command` 生成脚本：

```bash
python3 scripts/browser_snippets.py login-guard
```

把输出内容粘贴到 MCP `evaluate_script`。返回含义：

| 返回字段 | 处理方式 |
|----------|----------|
| `ok=true` | 已在表单页，可以进入 Step 3 |
| `hasCloudflare=true` | 停止自动提交验证码，手工通过 Cloudflare 后再重新检查 |
| `isLoginPage=true` | 重新登录；验证码失败后必须重新填密码，因为页面可能清空密码框 |
| `hasCreateForm=false` | 还没有进入上报表单，继续导航，不要填字段 |

如果首次进入 `/flaw/create` 触发 Cloudflare 或登录态失效，优先重启 Chrome 为 `seed-default` 复用日常 profile；`live-default` 只在确认普通 Chrome 已关闭时使用。验证码识别失败后不要复用旧验证码，也不要在密码框被清空时直接再次提交。

---

## Step 3: 填写表单

### 3.1 先处理 Select2 下拉框

CNVD 下拉框是 Select2 自定义组件，a11y 树里的选项经常不能点击；不要用 `click` 去点展开后的选项，也不要只设置原生 `<select>.value`。优先使用 `form_context.json.browser_helpers.select2_command` 生成脚本，脚本会通过原生 `change` 事件和 jQuery Select2 API 同步 UI。

```bash
python3 scripts/browser_snippets.py select2 \
  --form-type "<form_type_label>" \
  --vuln-type "<vuln_type>" \
  --object-type "<object_type_label>"
```

把输出内容粘贴到 MCP：

```text
MCP: evaluate_script
  function: |
    <browser_snippets.py select2 输出内容>
```

`browser_snippets.py` 输出已经是可直接执行的 IIFE 表达式，必须原样粘贴；不要把它改写成 `async () => {...}`，否则 `Runtime.evaluate` 只会返回函数对象 `{}`，Select2 实际不会执行。执行结果必须满足 `ok=true`。如果返回 `ok=false`，先看 `results[].reason` 和 `results[].options`，根据页面真实选项修正 `vuln_type` / `object_type_label`，不要继续填后续字段。

完成后只 `take_snapshot` 一次确认页面已刷新到目标表单状态，然后直接按 `page_payloads.base_info`、`page_payloads.vendor_info`、`page_payloads.detail_info` 统一填写其余非 Select2 字段。除这次联动确认外，不要为单个字段反复 `take_snapshot`。

**注意：二进制漏洞特殊字段**

当选择"二进制"类型时，表单会显示额外字段：

| 字段 | 说明 | 填写内容 |
|------|------|----------|
| 版本号 | 优先取 Word 的 `受影响实体版本号`，再回退 `影响版本` / `版本号` | `<version>` |
| 触发位置 | 漏洞触发位置 | 从漏洞描述中提取 |
| Poc | 漏洞验证代码 | 填写"见附件" |

### 3.2 页面联动完成后，再填写基本信息和其余字段

切换到目标“漏洞所属类型”并选好“漏洞类型”后，发现者和发现日期保持默认值不变，只修改“是否公开”。基本信息里的“是否公开”必须选择“否”。

优先使用 `form_context.json.browser_helpers.is_open_command` 生成脚本，该脚本会遍历全部两组 radio（CNVD 页面有两组 `name=isOpen` 的 radio，一组隐藏一组可见），确保所有"否"选中、"是"取消选中：

```bash
python3 scripts/browser_snippets.py is-open
```

```
MCP: evaluate_script
  function: |
    <browser_snippets.py is-open 输出内容>
```

执行后必须确认返回 `ok: true`。如果页面快照显示“否”未选中，不要提交。

后续文本字段优先按 `page_payloads` 分组一次性填写：

- `page_payloads.base_info`
- `page_payloads.vendor_info`
- `page_payloads.detail_info`

### 3.3 一次性填写厂商信息

`影响对象类型` 已在 3.1 的 Select2 helper 中处理；不要在 `fill_form` 里重复把它当普通下拉框填写。如果提交前校验发现它为空，重新运行 `browser_helpers.select2_command`，不要点击 Select2 选项。

```
MCP: take_snapshot
MCP: fill_form
  elements:
    - uid: "<漏洞厂商输入框的 uid>"
      value: "<unit_name>"
    - uid: "<厂商官网输入框的 uid>"
      value: "<url>"
    - uid: "<影响产品输入框的 uid>"
      value: "<affected_product>"
    - uid: "<影响产品版本输入框的 uid>"
      value: "<version>"
```

### 3.4 一次性填写漏洞详情

**重要：漏洞名称填写规则**

标题拆分在准备阶段已经固化，浏览器阶段不要重新拆分。

- “漏洞名称”输入框：填写 `form_context.json` 的 `title_input`。
- 提交后最终标题：必须与 `form_context.json` 的 `title_final_expected` 一致。
- “漏洞类型”下拉框：已由 3.1 的 Select2 helper 填写；不要在 `fill_form` 中重复处理。
- 选择完“漏洞类型”后，漏洞详情里只有“漏洞描述”继续使用提取值；其余必填项直接使用 `form_context.json` 中的固定默认值，不再临时读取 docx。
- “漏洞URL”固定填写 `detail_url=http://test.com`。
- 详情页其他拿不到的必填项统一填写 `detail_unknown_value=见附件`。

```
MCP: take_snapshot
MCP: fill_form
  elements:
    - uid: "<漏洞名称输入框的 uid>"
      value: "<title_input>"
    - uid: "<漏洞描述输入框的 uid>"
      value: "<description>"
    - uid: "<漏洞URL输入框的 uid>"
      value: "<detail_url>"
    - uid: "<临时解决方案输入框的 uid>"
      value: "<temp_solution>"
    - uid: "<正式解决方案输入框的 uid>"
      value: "<formal_solution>"
```

---

## Step 4: 上传附件

附件上传必须走 `form_context.json.browser_helpers` 的两段式强校验。不要直接凭 a11y 树猜 file input；CNVD 页面通常同时存在隐藏表单的 `#flawAttFile` 和当前可见表单的 `#flawAttFile1`，上传错 input 会导致平台报 `请按规定上传附件，附件格式不正确！`。

### 4.1 定位当前可见附件 input

先执行 `browser_helpers.attachment_prepare_command`：

```bash
python3 scripts/browser_snippets.py attachment-prepare --attachment-path "<browser_upload_path>"
```

把输出内容粘贴到 MCP：

```text
MCP: evaluate_script
  function: |
    <browser_snippets.py attachment-prepare 输出内容>
```

返回必须满足：

- `ok=true`
- `code=CNVD_ATTACHMENT_TARGET_READY`
- `targetId` 优先为 `flawAttFile1`
- `uploadRule` 明确要求只上传到带有 `aria-label="CNVD 附件上传目标"` 的控件

如果返回 `ok=false`，立即写 `output/summary.txt` 说明找不到当前可见附件 input，然后停止；不要自己尝试 `querySelector`、`DataTransfer`、`fetch` 或临时构造文件。

### 4.2 上传原始 CNVD zip

然后执行一次 `take_snapshot`，在快照中找到 `attachment-prepare` 标记过的 file input，再上传 `browser_upload_path`。`browser_upload_path` 是 `prepare_form_context.py` 从 CNVD 原始 zip 复制出来的 ASCII 路径副本，用于避开 Docker Chrome / CDP 对中文路径上传不稳定的问题：

```
MCP: take_snapshot
MCP: upload_file
  uid: "<带有 CNVD 附件上传目标 aria-label 的文件上传输入框 uid>"
  filePath: "<browser_upload_path>"
```

这里的 `<browser_upload_path>` 必须来自 `form_context.json`，并且准备阶段 `ready` 必须为 `true`。不要自行复制到 `/tmp`，因为 `/tmp` 通常只在 OpenCode 容器内可见，Docker Chrome 容器不可见。

禁止事项：

- 禁止上传到未标记的 file input。
- 禁止把验证码图片、`test.png` 或临时文件作为漏洞附件。
- 禁止用 JS `DataTransfer`、`fetch('/tmp/...')`、`fetch('http://localhost:...')` 等方式构造文件；浏览器安全模型下这些做法不稳定，且会掩盖真实失败点。

### 4.3 上传后强校验

上传后必须执行 `browser_helpers.attachment_verify_command`：

```bash
python3 scripts/browser_snippets.py attachment-verify --attachment-path "<browser_upload_path>"
```

把输出内容粘贴到 MCP：

```text
MCP: evaluate_script
  function: |
    <browser_snippets.py attachment-verify 输出内容>
```

返回必须满足：

- `ok=true`
- `code=CNVD_ATTACHMENT_VERIFIED`
- `fileName` 等于 `browser_upload_path` 的 basename
- `fileSize > 0`
- `fileName` 以 `.zip` 结尾

如果返回 `CNVD_ATTACHMENT_FILE_EMPTY`、`CNVD_ATTACHMENT_FILE_MISMATCH`、`CNVD_ATTACHMENT_FILE_INVALID_TYPE` 或任意 `ok=false`，立即写 `output/summary.txt` 并停止。不要继续验证码，不要点击提交。

---

## Step 4.5: 验证表单完整性

**提交前必须验证所有字段已填写完整**。

**检查清单**：

| 字段 | 要求 | 默认值/空值处理 |
|------|------|----------------|
| 发现者 | ✓ 已填写 | 保持默认 |
| 发现日期 | ✓ 已填写 | 保持默认 |
| 漏洞所属类型 | ✓ 已选择 | 必须等于 `form_type_label` |
| 是否公开 | ✓ 选择"否" | 必须手动选择 |
| 漏洞厂商 | ✓ 已填写 | 从数据获取 |
| 厂商官网 | ✓ 已填写 | 从数据获取 |
| 影响对象类型 | ✓ 已选择 | 从数据获取 |
| 影响产品 | ✓ 已填写 | 从数据获取 |
| 影响产品版本 | ✓ 已填写 | 从数据获取 |
| 漏洞名称 | ✓ 已填写 | 从数据获取 |
| 漏洞类型 | ✓ 已选择 | 从数据获取 |
| 漏洞描述 | ✓ 已填写 | 从数据获取 |
| 漏洞URL | ✓ 已填写 | 固定填写 `http://test.com` |
| 临时解决方案 | ✓ 已填写 | 默认填写"无" |
| 正式解决方案 | ✓ 已填写 | 默认填写"见附件" |
| 漏洞附件 | ✓ 已上传且通过 `attachment_verify_command` | `browser_upload_path` 指向的浏览器专用 ASCII zip 副本 |
| 验证码 | 待填写 | OCR识别后填写 |

同时检查：

- `form_context.json` 的 `ready` 为 `true`。
- 页面联动顺序必须正确：先选 `form_type_label`，再选 `vuln_type`，之后才开始填文本字段。
- 页面中“漏洞名称”输入值等于 `title_input`。
- 上传附件通过 `browser_helpers.attachment_verify_command`，页面可见 file input 中的 `fileName` 等于 `browser_upload_path` 的 basename。
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
        "漏洞URL": valueOf('#url1'),
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

验证码必须在提交前最后处理，固定流程如下。不要分情况刷新、裁剪或先点验证码图片。

1. 先完成 Step 4.5 表单完整性校验，确认除验证码外没有缺失字段。
2. 在原表单页执行 `browser_helpers.open_captcha_tab_command`。该脚本只读取当前 `#codeSpan1 img.src`，验证路径必须是 `/common/myCodeNew`，然后用新标签页打开验证码图片 URL；不会覆盖当前表单页，也不会点击刷新。

```bash
python3 scripts/browser_snippets.py captcha-tab
```

把输出内容粘贴到 MCP：

```text
MCP: evaluate_script
  function: |
    <browser_snippets.py captcha-tab 输出内容>
```

返回示例中的 `src` 应类似：

```text
https://www.cnvd.org.cn/common/myCodeNew?t=0.8846792108682565
```

如果返回 `reason=验证码地址不是 /common/myCodeNew`，停止识别，先检查页面选择器，避免打开错误图片。

如果返回 `code=CNVD_CAPTCHA_IMAGE_BROKEN`，说明提交验证码图片没有加载成功，通常是 `/common/myCodeNew` 被 CNVD 防火墙验证码拦截。此时不要截图表单页占位文字，不要把“看不清/点击更换/存在/二进制”当验证码提交；应切到防火墙验证码处理：保存防火墙页或当前页截图到 `logs/human-cnvd-firewall.png`，截取防火墙页真实验证码 img 元素后用 `captcha_ocr.py --preprocess cnvd` 最多尝试 3 次。3 次仍未通过再写入 `progress.jsonl` 的 `等待人工防火墙验证码` warning，并等待前端人工输入防火墙验证码后继续。

3. 切到新标签页。新标签页只显示验证码图片，必须只对验证码图片元素截图到 `/tmp/captcha.png`，不要截整个视口，然后识别。若 MCP 工具调用里没有 `uid`，说明你正在截整页/视口，必须停止并重新选择图片元素：

```bash
python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd
```

4. 识别结果返回后，立即回到原表单页。不要再执行 `take_snapshot` 或长时间等待；优先使用 `browser_helpers.submit_captcha_command_template` 生成脚本，用同一次 `evaluate_script` 完成填入验证码和点击提交。

```bash
python3 scripts/browser_snippets.py submit-captcha "<OCR识别结果>"
```

等价脚本如下：

```text
MCP: evaluate_script
  function: |
    () => {
      const code = "<OCR识别结果>";
      const input = document.querySelector("#myCode1");
      if (!input) return { ok: false, reason: "未找到验证码输入框 #myCode1" };
      input.value = code;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      const submit = document.querySelector("#subForm");
      if (!submit) return { ok: false, reason: "未找到提交按钮 #subForm" };
      submit.click();
      return { ok: true, code };
    }
```

5. 如果 OCR 识别失败或页面提示验证码错误，回到原表单页重新执行 `captcha-tab` 打开新的验证码图片标签页，再识别；不要复用旧标签页和旧结果。

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
  "/tmp/vulns-skills/phase2-cnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json" \
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
