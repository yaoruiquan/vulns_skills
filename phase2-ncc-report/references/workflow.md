# NCC 平台漏洞上报流程

## 流程概览

```text
Step 0: 检查环境 -> Step 1: 生成 NCC 材料并准备数据 -> Step 2: 登录并进入填表页 -> Step 3: 确认表单 -> Step 4: 填表 -> Step 5: 上传附件 -> Step 6: 提交前表单检查 -> Step 7: 提交与人工滑块验证 -> Step 8: 记录 NCC 编号 -> Step 9: 钉钉通知
```

## Step 0: 检查环境

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9334/json/version
```

如果端口无响应，先重新执行 `./scripts/start-chrome-debug.sh`。企业登录后出现阿里云滑块/拼图验证时，自动化流程停在当前页，由人工完成验证后继续。

确认 MCP 可用：

```text
MCP: list_pages
```

## Step 1: 准备数据

### 1.1 生成/复用 `NCC-<漏洞名>` 材料目录

运行 `prepare_form_context.py` 前，必须先确认一次绑定参数：

- `是否0Day漏洞/是否原创漏洞`：只能是“是”或“否”；二者绑定，是都为是，否都为否。

该值必须通过 `--is-0day-original 是/否` 传入。缺失时脚本会在生成 NCC 材料和 `form_context.json` 之前直接退出；不得从 Word 字段或 `.env` 兜底猜测。兼容旧参数 `--is-0day`、`--is-original`，但二者必须一致，否则直接报错。

`prepare_form_context.py` 默认会先执行 NCC 材料处理：

- 在 DAS 目录下创建同级 `NCC-<漏洞名>` 文件夹，结构参考 CNVD/CNNVD 材料目录。
- Word 使用 `NCC通用型漏洞报告模板.docx` 生成，信息优先来自 CNVD Word，CNVD 缺失时用 CNNVD Word 补充。
- 原始 CNVD/CNNVD 目录不修改；已有 NCC 目录默认不覆盖，信息提取和材料整理只做一次，后续准备/上报直接复用已有 NCC 材料。
- NCC 目录中除新生成的 NCC Word 外，其余附件和证明材料从源材料目录原样复制过去，保持相对目录结构。
- `互联网资产证明`、`黑盒案例`、`其他受影响目标` 等材料中没有的信息填“无”；`漏洞发现时间` 使用当天日期；漏洞危害/修复方案缺失时必须在准备阶段执行 `security_guidance` 检索补全，不能写“见附件”。
- `互联网资产证明` 会根据产品名/厂商生成不含“or”的 FOFA 测绘语句和 FOFA Web 查询 URL；查询语法按 `app`、`product`、`title`、`header`、直接关键词、`body` 的精确度顺序选择，不按返回数量最大值倒向宽泛语句。截图直接使用原生 Chrome DevTools MCP，不使用 Playwright。需要登录时人工微信扫码，随后用 MCP 执行 `fofa_assets.py generate` 输出的页面提取脚本获取 `asset_count`、`has_results` 和 `no_result`。只有 `has_results=true` 时才截图并回填 Word；回填命令必须带 `--has-results true/false`。如果 `has_results=false`、`no_result=true`、`asset_count=0` 或未识别数量，资产数量写“未检索到互联网资产/待回填”，截图写“无”，不得保留空结果页截图。截图文件名建议包含产品名或 DAS-ID；准备阶段会先按产品/标题/查询语句匹配截图文件名，避免误用其他漏洞的最新截图，`apply` 未传 `--screenshot-path` 时才自动使用默认目录最新截图兜底。若配置 `FOFA_API_ENABLED=true` 和 `FOFA_API_KEY`，也可读取 FOFA API 返回 JSON 的 `size` 作为是否有结果的依据：`size>0` 可保留截图，`size=0` 不保留截图。

可单独运行：

```bash
python3 scripts/prepare_ncc_material.py "<具体 DAS 目录>" --is-0day-original 是
python3 scripts/prepare_ncc_material.py "<具体 DAS 目录>" --is-0day-original 否 --force
```

默认模板路径来自 `NCC_REPORT_TEMPLATE_PATH`；监管汇总表目录默认记录为 `REGULATORY_SUMMARY_DIR=/Users/yao/Documents/网安- AI应用开发/监管上报/汇总表`。

### 1.2 生成 `form_context.json`

```bash
python3 scripts/prepare_form_context.py --docx-path "<具体 docx 路径>" --is-0day-original 是
# 或
python3 scripts/prepare_form_context.py --input-path "<具体 DAS 目录>" --is-0day-original 是
# 或兼容旧用法
python3 scripts/prepare_form_context.py <DAS-ID> --data-dir "<数据根目录>" --is-0day-original 是
```

默认会先生成/复用 NCC 材料目录，并让 `form_context.json` 读取 NCC Word。排障或兼容旧流程时可加 `--no-prepare-ncc-material` 跳过。

`--is-0day-original` 接受 `是/否/yes/no/true/false/1/0`。开始执行时如果用户提示“是”，必须同时把 `is_0day` 和 `is_original` 写为“是”；如果提示“否”，二者同时写为“否”。如果用户没有明确说明，先问清楚，不生成 JSON。

默认输出到 `/tmp/vulns-skills/phase2-ncc-report/form-contexts/YYYY-MM/DAS-ID/form_context.json`。运行时 JSON 不写入 NCC/CNVD/CNNVD 提交材料目录；如需指定其他位置，使用 `--output`。

输出示例：

```json
{
  "ok": true,
  "output": "/tmp/vulns-skills/phase2-ncc-report/form-contexts/2026-04/DAS-T106003/form_context.json",
  "context": {
    "platform": "NCC",
    "das_id": "DAS-T106003",
    "material_dir": "/path/to/CNVD-材料目录",
    "material_source": "CNVD",
    "title": "7z系统WIM格式解析器模块存在内存缓冲区操作限制不当漏洞",
    "description": "7z WIM格式解析器递归调用无深度限制导致栈溢出",
    "vuln_type": "二进制",
    "business_type": "通用型漏洞",
    "target_type": "应用程序",
    "vendor_country": "美国",
    "is_0day": "是",
    "is_original": "是",
    "unit_name": "其他",
    "affected_product": "7z<=26.00",
    "version": "7z<=26.00",
    "url": "http://none",
    "docx_path": "/path/to/report.docx",
    "upload_zip_path": "/tmp/vulns-skills/phase2-ncc-report/upload-zips/DAS-T106003/NCC-7z系统WIM格式解析器模块存在内存缓冲区操作限制不当漏洞.zip",
    "upload_zip_source_path": "/path/to/CNVD-材料目录/exp/source.zip",
    "screenshot_paths": [
      "/path/to/poc验证图片/example.png"
    ],
    "video_paths": [
      "/path/to/poc验证视频/example.mp4"
    ],
    "detail_category": "二进制",
    "browser_defaults": {
      "is_0day": "是",
      "is_original": "是",
      "business_type": "通用型漏洞",
      "detail_category": "二进制",
      "target_type": "应用程序",
      "vendor_country": "美国",
      "binary_required_fields": {
        "版本号": "26.00",
        "触发位置": "见附件",
        "PoC": "PoC、验证截图和验证视频见附件压缩包。"
      }
    },
    "browser_phase_rule": "浏览器阶段只能读取本 form_context.json；禁止重新运行 Word 提取脚本。"
  }
}
```

### 1.3 准备附件

第一版按当前约定这样用：

- 以 NCC Word 作为信息提取输入
- `prepare_form_context.py` 会从 NCC 材料目录优先识别 `exp/*.zip` / `poc/*.zip`，复制到运行时目录并改名为 `NCC-*.zip`；没有现成 zip 时，会把 NCC 材料目录自动打包成 `NCC-*.zip`
- 如果运行时 zip 超过 `NCC_UPLOAD_MAX_MB`（默认 50 MiB），脚本会解包后用 ffmpeg 压缩其中的视频文件，再生成同目录 `NCC-*-compressed.zip`；`upload_zip_path` 会自动指向压缩后的 zip
- 压缩只发生在 `/tmp/vulns-skills/phase2-ncc-report/upload-zips/...` 运行时副本中，不修改 CNVD/CNNVD/NCC 源材料目录
- 以 `form_context.json` 中的 `upload_zip_path` 作为唯一默认上传附件
- `screenshot_paths` 和 `video_paths` 只用于记录和复核；NCC 当前上传控件可能是单文件，默认不要再补传，避免替换 zip

## Step 2: 登录并进入填表页

```text
MCP: navigate_page
  type: "url"
  url: "<NCC_PLATFORM_URL>"
```

默认地址：

```text
https://www.nccsec.cn/company-center/manage-center
```

如果未登录，按截图确认的顺序操作：

1. 切到“企业”页签。
2. 填写 `.env` 中的 `NCC_USERNAME`、`NCC_PASSWORD`。
3. 勾选协议复选框。
4. 点击蓝色“登录”按钮。
5. 登录成功后，在管理中心右上角点击“提交漏洞”下拉按钮。
6. 点击下拉菜单里的“提交漏洞”项，进入填表页。

## Step 3: 确认上报入口和表单

首次开发或页面变化时必须执行：

```text
MCP: take_snapshot
```

根据快照确认：

- 登录页 tab、账号框、密码框、协议勾选框、登录按钮
- 管理中心“提交漏洞”按钮和菜单项
- 表单字段名称
- 各下拉框真实选项值
- 附件上传控件
- 提交按钮
- 提交成功后 `NCC-xxxx` 所在位置

将确认结果补充到 [selectors.md](selectors.md)。

## Step 4: 填写表单

按 [field-mapping.md](field-mapping.md) 使用 `form_context.json` 填表。原则：

- `是否0Day漏洞` 和 `是否为原创漏洞` 使用 `form_context.json` 中的 `is_0day`、`is_original`，二者必须绑定一致；开始给“是”就两个都选“是”，给“否”就两个都选“否”，缺失或不一致时准备脚本直接报错。
- `发现日期` 不直接拿 `提交日期` 硬填。
- `漏洞业务类型/漏洞类型` 固定保持/选择 `business_type=通用型漏洞`，不要选“事件型漏洞”。
- 影响对象、厂商国家/地区、漏洞详细分类都从 JSON 读取；未知的动态下拉字段统一选“其他”。
- 所有主下拉和动态下拉必须在文本框填写前完成；兜底选择“其他”时必须跳过已经精确选择过的主下拉，不能回头覆盖“漏洞详细分类”等字段。
- 选择阶段包括下拉框和 radio/是否项：先处理 `漏洞业务类型`、`是否0Day漏洞`、`是否原创漏洞`、`影响对象`、`厂商国家/地区`、`漏洞详细分类`、`修复方案`，再处理页面联动新增下拉，最后才写文本框。
- NCC 页面顶部有 3 个 radio group：第 1 组是 `漏洞业务类型`（事件型/通用型），第 2 组是 `是否0Day漏洞`（是/否），第 3 组是 `是否原创`（是/否）。脚本必须强制按 group index 点击这 3 组，不走 label 匹配；尤其 `是否原创` 要直接点第 3 组中的“是/否”。
- `影响对象` 优先根据 `target_type` 选择。
- 厂商国家/地区优先根据 `vendor_country` 选择，页面 label 可能是 `产品厂商归属国家及地区`、`产品厂商归属国家/地区`、`厂商所属国家及地区` 等；不要用单独的“产品厂商”宽泛匹配国家字段，无法判断时默认“中国大陆”。
- 如果 `影响对象`、`产品厂商归属国家及地区`、`漏洞详细分类`、`修复方案` 等保护选择项任一失败，脚本必须立即停止并返回 `stoppedBeforeText=true`，禁止继续填写文本框。
- `漏洞厂商 / 影响组件 / 影响版本 / 漏洞名称 / 漏洞 URL / 漏洞描述` 直接使用 `form_context.json` 中的固化值；描述不保留“经恒脑AI代码审计智能体分析：”前缀。
- `漏洞危害` 使用 `form_context.json.impact`，`修复方案说明` 使用 `formal_solution` 或 `temporary_solution`；这两个字段必须在准备阶段通过 Word 字段或 `security_guidance` 检索策略补齐，禁止填写“见附件”。
- `修复方案` 先选页面单选项，再写入准备阶段固化的修复说明。
- 平台必填但材料缺失时暂停，不要凭空编写。
- 推荐用 `scripts/browser_snippets.py fill-form --context <form_context.json>` 生成一次性 `evaluate_script`，脚本按 label 填写字段，避免 textarea 顺序错位。

### 4.1 Element UI 下拉框规则

NCC 页面使用 Element UI，下拉选项是动态 popper。点击下拉框后，MCP `take_snapshot` 可能只显示：

```text
listbox orientation="vertical"
```

但不显示选项内容。遇到这种情况，不要继续依赖 `click(uid)` 选项，直接使用 `evaluate_script` 操作 DOM。

本 skill 需要精确操作这些业务下拉框：

| 下拉框 | 取值规则 |
|--------|----------|
| `漏洞业务类型/漏洞类型` | 固定 `business_type=通用型漏洞` |
| `影响对象` | 优先使用 `target_type`；无法匹配时选“其他” |
| `厂商所属国家/地区` | 使用 `vendor_country`；无法判断时选“中国大陆” |
| `漏洞详细分类` | 使用 `detail_category`，且必须是 [field-mapping.md](field-mapping.md) 中列出的 NCC 允许选项；无法确定时选“其他” |

其他因为页面联动新增出来的下拉框，一律选择“其他”。兜底逻辑只处理未被精确选择过的新下拉；不得重新处理 `漏洞业务类型/漏洞类型`、`影响对象`、`厂商所属国家/地区`、`漏洞详细分类`、`是否0Day漏洞`、`是否原创漏洞`。

动态下拉字段可能出现短 label，例如“类型”“中间件/框架”。处理这些字段时必须只操作当前 `.el-form-item` 内部的下拉控件，短 label 只能精确匹配，不能按 `includes('类型')` 搜索，否则“类型”会误匹配到前面的“漏洞类型”或“漏洞详细分类”。填完后必须回读保护字段，发现 `漏洞业务类型`、`影响对象`、`漏洞详细分类` 与 JSON 不一致时停止并报告 `protectedSelectMismatches`。

Element UI 关闭下拉后不会销毁历史选项，`.el-select-dropdown__item` 会混在全局 DOM 中。NCC 当前主下拉 DOM 顺序固定，保护选择项必须按 `.el-select-dropdown` 索引直接取选项：`[0]=影响对象`、`[1]=厂商国家/地区`、`[2]=漏洞详细分类`，并对目标选项触发 `mouseenter/mousemove/mousedown/mouseup/click`。动态新增下拉不使用固定索引，仍只操作当前 `.el-form-item` 内部触发器并回读当前控件值；未写回当前控件就返回失败并停止。

可直接复用以下脚本：

```javascript
async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function selectElementUiByLabel(labelText, wantedText, fallbackText = '其他') {
  const visible = (el) => {
    const rect = el?.getBoundingClientRect?.();
    const style = el ? window.getComputedStyle(el) : null;
    return !!rect && rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const norm = (value) => String(value || '').replace(/[：:*\s]/g, '').trim();
  const formItems = [...document.querySelectorAll('.el-form-item')].filter(visible);
  const formItem = formItems.find(item => {
    const label = item.querySelector('.el-form-item__label');
    return label && norm(label.innerText) === norm(labelText);
  });
  if (!formItem) {
    return { ok: false, label: labelText, reason: 'form item not found' };
  }

  const trigger = formItem.querySelector('.el-select, .el-select__wrapper, input');
  if (!trigger) {
    return { ok: false, label: labelText, reason: 'select trigger not found' };
  }

  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
  await sleep(100);
  const openedBefore = new Set([...document.querySelectorAll('.el-select-dropdown, .el-popper')].filter(visible));
  trigger.click();
  await sleep(300);

  const poppers = [...document.querySelectorAll('.el-select-dropdown, .el-popper')]
    .filter(popper => visible(popper) && popper.querySelector('.el-select-dropdown__item'));
  const popper = poppers.find(p => !openedBefore.has(p)) || poppers.at(-1);
  const options = [...(popper?.querySelectorAll('.el-select-dropdown__item') || [])]
    .filter(option => visible(option))
    .filter(option => !option.classList.contains('is-disabled'));

  const optionTexts = options.map(option => option.innerText.trim()).filter(Boolean);
  const target =
    options.find(option => norm(option.innerText) === norm(wantedText)) ||
    options.find(option => norm(option.innerText) === norm(fallbackText));

  if (!target) {
    return { ok: false, label: labelText, wanted: wantedText, options: optionTexts };
  }

  const selected = target.innerText.trim();
  target.click();
  await sleep(500);
  return { ok: true, label: labelText, selected, options: optionTexts };
}
```

调用示例：

```javascript
await selectElementUiByLabel('影响对象', '<target_type>', '其他');
await selectElementUiByLabel('漏洞详细分类', '<漏洞详细分类>', '其他');
```

进入浏览器阶段后，不要再运行 `extract_vuln_data.py`；如果发现字段不完整，回到 Step 1 重新生成 `form_context.json`。

### 4.2 动态新增必填字段规则

选择 `漏洞详细分类` 后，页面可能动态新增必填字段，例如：

- `类型`
- `中间件/框架`
- `利用工具`

这些字段按 [field-mapping.md](field-mapping.md) 的“漏洞详细分类联动字段映射表”处理，不能只依赖必填标记兜底；有些 PoC/利用工具类字段页面会出现但不稳定带 `is-required`。

| 新增字段类型 | 默认处理 |
|--------------|----------|
| `版本号` | 填写 `browser_defaults.binary_required_fields.版本号` |
| `触发位置` | 填写“见附件” |
| `PoC` / `poc` / `触发过程` / `触发xss的payload` | 填写“见附件” |
| `弱口令账号` / `弱口令密码` / `利用工具` | 填写“见附件” |
| 其他下拉框 | 选择“其他” |
| 其他输入框/文本域 | 填写“见附件” |
| `SQL注入Poc` radio | 根据 `request_method` 选 `get/post`，无法判断默认 `get` |
| SQL 注入真实 PoC 内容 | 写入 CodeMirror 编辑器，内容只能来自 `poc_text` 中的原始 HTTP 请求或 curl 命令；原始 HTTP 请求必须是 `GET /path HTTP/1.1` / `POST /path HTTP/1.1` 加逐行 Header 的格式。脚本会修复 Word 提取造成的 Header 换行丢失，但如果 Word 没有现成 PoC，不得根据 URL/请求方式自动拼接。只有 SQL 注入需要真实 PoC，其他分类继续填“见附件” |

每次选择 `漏洞详细分类` 后必须先等待并按映射表主动补齐该分类的联动字段，再扫描可见必填字段兜底：

- `命令执行` 的 `类型` 和 `中间件/框架` 是硬性联动下拉，必须等待字段出现并选择“其他”；如果字段没出现、仍是“请选择类型/请选择中间件/框架”、或选择后没有写回当前控件，脚本必须返回失败，不得按 skipped 成功继续。

```javascript
async function fillDynamicRequiredFields() {
  const items = [...document.querySelectorAll('.el-form-item')]
    .filter(item => item.offsetParent !== null);

  const results = [];
  for (const item of items) {
    const label = item.querySelector('.el-form-item__label')?.innerText.trim() || '';
    const required = item.classList.contains('is-required') || label.includes('*');
    if (!required) continue;

    const select = item.querySelector('.el-select, .el-select__wrapper');
    const textarea = item.querySelector('textarea');
    const input = item.querySelector('input:not([type="hidden"])');
    const currentValue = (textarea || input)?.value || '';

    if (select && !currentValue) {
      results.push(await selectElementUiByLabel(label.replace('*', ''), '其他', '其他'));
      continue;
    }

    if ((textarea || input) && !currentValue) {
      const target = textarea || input;
      target.value = '见附件';
      target.dispatchEvent(new Event('input', { bubbles: true }));
      target.dispatchEvent(new Event('change', { bubbles: true }));
      results.push({ ok: true, label, filled: '见附件' });
    }
  }
  return results;
}
```

调用顺序：

```javascript
await selectElementUiByLabel('影响对象', '<target_type>', '其他');
await selectElementUiByLabel('漏洞详细分类', '<漏洞详细分类>', '其他');
await fillDynamicRequiredFields();
```

示例操作：

```text
MCP: fill_form
  elements:
    - uid: "<漏洞名称 uid>"
      value: "<title>"
    - uid: "<漏洞描述 uid>"
      value: "<description>"
    - uid: "<影响组件 uid>"
      value: "<affected_product>"
    - uid: "<影响版本 uid>"
      value: "<version>"
```

## Step 5: 上传附件

上传前先从 `form_context.json` 解析真实文件路径，禁止手动拼接或改写 zip 文件名。漏洞名中的空格、短横线、下划线必须保持 JSON 原值，否则会出现路径不存在但上传流程空跑的问题。

```bash
python3 scripts/resolve_upload_path.py --context "<form_context.json>"
python3 scripts/resolve_upload_path.py --context "<form_context.json>" --plain
```

第一条命令返回的 `ok` 必须为 `true`，并且 `expected.exists=true`、`expected.size_bytes>0`。第二条命令只输出可直接传给 MCP 的精确路径。

批量上报前先扫整批 JSON：

```bash
python3 scripts/resolve_upload_path.py --batch-root "/tmp/vulns-skills/phase2-ncc-report/form-contexts/YYYY-MM"
```

返回 `ok=true`、`failed_count=0` 才能进入批量上传；任何一个 `upload_zip_path` 不存在或为空都必须先修复。

如果已经手工写了一个候选路径，先诊断候选路径，不要直接上传：

```bash
python3 scripts/resolve_upload_path.py --context "<form_context.json>" --candidate "<手工路径>"
```

只有 `candidate_ok=true` 且 `candidate_matches_expected=true` 才能使用候选路径；否则必须使用输出中的 `filePath` 原值。

```text
MCP: upload_file
  uid: "<文件上传输入框 uid>"
  filePath: "<resolve_upload_path.py 输出的 filePath>"
```

默认只传 `upload_zip_path`。不要继续上传 `docx_path`、`screenshot_paths`、`video_paths`，因为实测 NCC 控件可能只保留最后一次上传文件，后续上传会替换已经上传的 zip。

## Step 6: 提交前表单检查

上传附件后必须执行一次提交前表单检查，这是硬性 gate，不允许跳过：

```bash
python3 scripts/browser_snippets.py post-upload-audit --context "<form_context.json>"
```

把输出脚本放到 MCP `evaluate_script` 执行。该脚本只处理仍为空的必填项：

- 空的必填文本框/文本域填写“见附件”，但 `漏洞危害` 和 `修复方案说明` 例外：这两个字段必须来自准备阶段 `impact` / `formal_solution` / `temporary_solution`，为空或仍为“见附件”时停止回到 Step 1 重建 JSON。
- 空的未知必填下拉选择“其他”
- 空的保护下拉按 JSON 选择，例如 `漏洞业务类型=通用型漏洞`、`漏洞详细分类=<detail_category>`
- 检查附件上传状态，返回 `attachmentUploaded`
- 附件检查必须精确匹配 `upload_zip_path` 的文件名；仅出现任意上传列表项不算成功
- 如果页面仍有“请选择漏洞附件/上传失败/附件不能为空”等提示，返回 `uploadErrors`
- 已有值的保护下拉不覆盖；如果与 JSON 不一致，返回 `skippedProtected`，停止提交前人工复核

返回结果必须满足以下条件，才能继续提交：

- `ok=true`
- `missingRequired=[]`
- `skippedProtected=[]`
- `attachmentUploaded=true`
- `exactAttachmentMatch=true`
- `uploadErrors=[]`

如果任一条件不满足，继续修正表单或重新上传附件，不得点击提交。

## Step 7: 提交与人工滑块验证

提交前必须复核：

| 字段 | 要求 |
|------|------|
| 是否为原创漏洞 | 已选择 |
| 漏洞类型 | 已选择 |
| 影响对象 | 已选择 |
| 漏洞厂商 | 已填写 |
| 影响组件 | 已填写 |
| 影响版本 | 已填写 |
| 漏洞名称 | 已填写 |
| 漏洞描述 | 已填写 |
| 漏洞危害 | 已填写 |
| 修复方案 | 已填写 |
| 附件 | 已上传 |
| 提交按钮 | 已确认 |

点击“提交”后，会出现拖拽拼图验证。第一版按以下策略执行：

1. 自动化流程在点击提交前完成全部填表和上传。
2. 出现拖拽验证后，切换人工处理。
3. 人工完成拖拽后，自动化继续读取结果页。

## Step 8: 记录 NCC 编号

提交后使用快照或页面文本记录结果：

```text
MCP: take_snapshot
MCP: evaluate_script
  function: |
    () => document.body.innerText
```

记录：

- `NCC-xxxx` 编号
- 成功提示
- 提交时间
- 对应 `DAS-ID`

## Step 9: 钉钉通知

```bash
python3 scripts/dingtalk_notify.py \
  --title "NCC 平台上报完成" \
  --status success \
  --text "DAS-ID：<DAS-ID>\nNCC编号：<NCC-xxxx>" \
  --output "<材料目录>"
```
