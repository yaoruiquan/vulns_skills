# CNNVD 数据字段映射

## 一、最小必填填写规则

CNNVD 页面只填写带 danger/红色必填标记的字段，避免每个下拉框都重复快照、点击、交互。

数据准备阶段必须一次性整理完整 `FormContext`，不是只跑 Word 提取。详见 [data-preparation.md](data-preparation.md)。

`prepare_form_context.py` 在流程开始时运行一次，默认生成 `/tmp/vulns-skills/phase2-cnnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json`。后续浏览器阶段只读这个 JSON，不要再次执行提取脚本。

下拉框遇到不确定时，优先查 [dropdown-options.md](dropdown-options.md)。

优先直接读取 `dropdown_plan` 和 `page_payloads`。每页一次性填写，不要因为单个字段重复快照和判断。

### 第 1 页：漏洞基本信息

只处理必填下拉框和必填文本：

- `漏洞类型`：使用 `page_payloads.page1_dropdowns.vuln_type_path`，优先查 `references/dropdown-options.md`，再按 `references/vuln-type-mapping.md` 的级联路径选择。
- `漏洞自评级`：使用 `page_payloads.page1_dropdowns.risk_level`，Word 为空时脚本默认 `高危`。
- `受影响实体分类`：使用 `page_payloads.page1_dropdowns.affected_entity_category`，优先查 `references/dropdown-options.md` 的速查映射。
- 如页面提示必填，再补充 `漏洞名称`、`受影响实体名称`、`受影响实体版本`、`受影响实体描述`；其中 `受影响实体描述` 来自数据准备阶段的 websearch 总结。

### 第 2 页：漏洞详情

只填写：

- `漏洞描述或简介`：使用 `page_payloads.page2_text.description`，取 Word 的“漏洞简介”，并去掉 `经恒脑AI代码审计智能体分析：` 前缀。
- `技术支持`：使用 `page_payloads.page2_text.technical_support`。
- `技术支持联系电话`：使用 `page_payloads.page2_text.contact`。

手机号不只校验 11 位，还校验号段。准备脚本会把不合规号码（例如 `16880230001`）替换为平台可接受的默认号码；浏览器阶段不要再手工改回原 Word 号码。

`漏洞描述或简介` 页面限制最多 255 个字符。只填写 `description`，不要填写 `description_full`。

### 第 3 页：漏洞验证

只填写和上传：

- `验证过程`：只使用 `page_payloads.page3_text.verification`，不要重新运行脚本，不要直接粘贴 Word 原文；图片只作为理解材料，不插入表单。
- `验证录像`：上传 `page_payloads.page3_uploads.verification_video_path`。
- `POC文件`：上传 `page_payloads.page3_uploads.poc_file_path`。

## 二、表单字段与数据来源

| 表单字段 | 数据来源 | 字段名 | 备注 |
|---------|---------|-------|------|
| 漏洞名称 | extract_vuln_data | title | |
| CVE编号 | extract_vuln_data | cve_id | 可选 |
| 漏洞类型 | extract_vuln_data | vuln_type | 需映射到级联路径 |
| 漏洞自评级 | extract_vuln_data | risk_level | 超危/高危/中危/低危；Word 为空默认高危 |
| 公开情况 | 固定值 | 未公开 | 默认即可 |
| 受影响实体厂商名称 | extract_vuln_data | unit_name | |
| 受影响实体分类 | extract_vuln_data | affected_entity_category | 使用 CNNVD 平台枚举，如 `建站系统`、`web应用`、`中间件` 等 |
| 受影响实体名称 | extract_vuln_data | affected_product | |
| 受影响实体版本 | extract_vuln_data | version | |
| 受影响实体原始下载链接 | extract_vuln_data | download_url | 可选 |
| 受影响实体描述 | websearch | entity_description | 数据准备阶段补齐，50-120 字 |
| 受影响网络资源数量 | 固定值 | 空 | 默认即可 |
| 漏洞描述或简介 | extract_vuln_data | description | 使用 Word“漏洞简介”，已清理固定前缀，最多 255 字 |
| 漏洞描述原文 | extract_vuln_data | description_full | 只作参考，不直接填表 |
| 技术支持 | extract_vuln_data | technical_support | 默认杭州安恒信息技术股份有限公司 |
| 技术支持联系电话 | extract_vuln_data | contact | 或默认 17557289379 |
| 验证过程原文 | extract_vuln_data | verification_source | 只作为总结输入，不直接填表 |
| 验证过程 | 数据准备总结 | verification | 根据 `verification_source` 总结压缩为一段文字，不带图片 |
| 验证录像 | extract_vuln_data | verification_video_path | 优先取 `exp验证视频`，其次取 `poc验证视频`、`验证视频`、`视频`、`video` |
| POC 文件 | extract_vuln_data | poc_file_path | 优先取 `exp`，其次取 `poc`、`POC`、`PoC` |

## 三、数据提取脚本输出示例

```json
{
  "das_id": "DAS-T105970",
  "title": "Claude Code系统getMcpHeadersFromHelper模块存在命令执行漏洞",
  "description": "漏洞简介一句话...",
  "description_full": "完整漏洞简介...",
  "description_max_length": 255,
  "description_truncated": false,
  "vuln_type": "命令执行",
  "risk_level": "高危",
  "affected_entity_category": "web应用",
  "affected_product": "Claude Code",
  "version": "2.1.89",
  "entity_description": "产品简介...",
  "unit_name": "Anthropic",
  "technical_support": "杭州安恒信息技术股份有限公司",
  "verification_source": "Word 中清理后的验证过程原始文本...",
  "verification": "数据准备阶段总结压缩后的单段验证过程文本...",
  "verification_video_path": "/path/to/exp验证视频/demo.mp4",
  "poc_file_path": "/path/to/exp/poc.zip",
  "contact": "17557289379",
  "folder_path": "/Users/yao/LLM/vulns/date/DAS-T105970-xxx/CNNVD-xxx",
  "docx_path": "/Users/yao/LLM/vulns/date/DAS-T105970-xxx/CNNVD-xxx/xxx.docx"
}
```

## 四、受影响实体分类选项

完整平台选项和常见产品映射见 [dropdown-options.md](dropdown-options.md)。这里不重复维护枚举，避免和平台实际选项不一致。

## 五、漏洞自评级选项

- 超危
- 高危
- 中危
- 低危

## 六、下拉框操作原则

- 只操作 `漏洞类型`、`漏洞自评级`、`受影响实体分类` 这三个必填下拉框。
- 优先用 `evaluate_script` 直接点击 Element UI 下拉项，避免每个选项都用 `take_snapshot` 查 uid。
- 每页字段准备好后尽量一次性 `fill_form`，不要填完一个字段就再确认一次页面状态。
- 级联下拉选择最终节点时，点击选项前面的圆圈/单选按钮，不要只点击文字。
- 受影响实体分类必须点击平台 DOM 选项；不要直接写 Vue model 值，避免 `"30"` 这类值映射到错误中文选项。
- 如果选择某项后动态出现新的非必填字段，不填写；如果动态出现必填字段，能选择“其他”就选“其他”，文本框统一填“见附件”。

## 七、Vue 模型同步

CNNVD 页面中文标签和 Vue model 字段名不一致。提交前执行 `form_context.json.browser_helpers.sync_form_model_command`，它会同步：

- `vulName`：漏洞名称
- `affectedVendor`：厂商名称
- `affectedEntityName`：受影响实体
- `affectedEntityVersion`：版本
- `affectedEntityDesc`：描述
- `hazardLevel`：自评级
- `vulDesc`：漏洞描述
- `supporter`：技术支持
- `supporterPhone`：联系电话
- `verifyProcess`：验证过程

TinyMCE/iframe 内容必须和 `formModel.verifyProcess` 同步；只改 iframe body 会导致提交校验提示“请输入验证过程”。

## 八、非原创漏洞通报报送

非原创漏洞在通用型漏洞报送成功并取得 `CNNVD-ID` 后，还要进入 `https://www.cnnvd.org.cn/backHome/vulWarnSend` 执行三页“漏洞通报报送”。页面数据只读取 `form_context.json.disclosure_report`。

### 第 1 页：漏洞通报信息

- `关联漏洞编号`：使用刚获取的 `CNNVD-ID`，但平台远程搜索只输入最后一段数字，例如 `CNNVD-2026-39895760` 搜索 `39895760`；匹配结果仍按完整编号校验后选中。
- 同一个 Vue SPA 会话中，`vulIdList` 可能保留上一条漏洞的 UUID；同步关联编号前必须先清空 `form.vulIdList` 和 `vulIdListNew`，再写入当前匹配项，避免页面显示 `+1`。
- 关联编号选中后必须先收起下拉框再上传附件；下拉框未关闭时点击上传区域可能误选第二个 CNNVD 编号并显示 `+1`。
- `有无POC` / `是否验证过`：默认 `有` / `是`。
- `有无EXP` / `是否验证过`：默认 `有` / `是`。
- `有无检测工具` / `是否验证过`：默认 `无` / `否`。
- `上传附件`：上传 `disclosure_report.page1.attachment_path`，通常为单个漏洞的 CNNVD 原始整包 zip。
- `联系人信息`：提交人信息优先保留页面登录态默认值；技术支持信息优先使用 `.env` 中 `CNNVD_DISCLOSURE_*`，缺失时由 `DEFAULT_CONTACT_*` 兜底。
- 提交人联系电话和技术支持联系电话不能相同；如相同，脚本自动把技术支持联系电话改为 `ALTERNATE_CONTACT_PHONE`。

### 第 2 页：撰写漏洞通报

- `漏洞通报名称`：使用 `disclosure_report.page2.warn_name`。
- 富文本正文：使用 `disclosure_report.page2.enclosure_content`，内容包含产品描述、影响版本、受影响资产情况、利用过程、技术细节、修补措施、检测规则和漏洞来源。
- 富文本正文必须保留平台模板的 1-9 项标题顺序：
  `1、产品描述（必填）`、`2、影响产品或组件及版本（必填）`、`3、受影响资产情况（必填）`、`4、受影响资产列表`、`5、利用过程及结果`、`6、技术细节表述（必填）`、`7、修补措施（必填）`、`8、检测规则`、`9、漏洞来源（必填）`。
- 不要提交平台模板中的“示例/说明”原文；每一项都要用材料提取结果或固定兜底内容替换。
- 富文本同步优先写 Vue `detailForm.enclosureContent` 和 iframe DOM；TinyMCE API 只作为兜底，避免隐藏编辑器触发 `bookmark` 异常。

### 第 3 页：提交

- 第 3 页只做最终确认和提交。
- 提交前必须执行：

```bash
python3 scripts/browser_snippets.py audit-disclosure-report \
  --form-context "<form_context.json>" \
  --cnnvd-id "<CNNVD-ID>"
```

`ok=true` 后才能提交；如出现验证码，按 `captcha-ocr.md` 的单次识别流程处理。
