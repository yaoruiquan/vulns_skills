# CNNVD 数据准备规范

数据准备阶段必须一次性整理完整 `FormContext` 并输出 `form_context.json`。后续浏览器第 1、2、3 页都只能读取这个 JSON，不要进入页面后再重新运行提取脚本或重新总结。

---

## 一、输入

支持三种输入：

- `DAS-ID`
- `DAS` 漏洞目录路径
- `CNNVD` docx 文件路径

基础示例：

```bash
python3 scripts/prepare_form_context.py "/path/to/DAS-T106006-xxx"
```

推荐示例：

```bash
python3 scripts/prepare_form_context.py \
  "/path/to/DAS-T106006-xxx" \
  --entity-description "emlog 是一款基于 PHP 的开源博客和内容管理系统，常用于个人博客、轻量级网站和内容发布场景，支持模板、插件和后台管理功能。" \
  --verification "验证过程显示，漏洞入口位于模板 ZIP 上传功能。攻击者在具备后台权限并获取有效 token 后，构造包含合法模板文件和路径遍历文件名的 ZIP 包上传，服务端未校验压缩包内全部文件名，解压后可将恶意 PHP 文件写入可访问目录。访问写入文件可触发代码执行，证明该漏洞可被利用。"
```

默认输出到 `/tmp` 运行时目录，避免污染 CNNVD 提交材料目录：

```text
/tmp/vulns-skills/phase2-cnnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json
```

如需指定其他位置，使用 `--output`。

---

## 二、FormContext 必备字段

`form_context.json` 中必须包含以下字段：

| 字段 | 来源 | 处理规则 |
|---|---|---|
| `das_id` | 脚本提取 | DAS 编号 |
| `title` | Word | 漏洞名称 |
| `vuln_type` | Word + 速查表 | 用 [dropdown-options.md](dropdown-options.md) 判断级联路径 |
| `risk_level` | Word | 空值默认 `高危` |
| `affected_entity_category` | Word/名称/速查表 | 用 [dropdown-options.md](dropdown-options.md) 判断 |
| `affected_product` | Word/漏洞名称 | 受影响实体名称 |
| `version` | Word | 受影响实体版本 |
| `entity_description` | websearch/脚本兜底 | 受影响实体描述，50-120 字 |
| `description` | Word | 漏洞简介，去掉固定 AI 前缀 |
| `description_full` | Word | 原始完整简介，留作参考，不直接填表 |
| `description_max_length` | 固定值 | `255` |
| `description_truncated` | 脚本判断 | `true` 表示简介已被截断 |
| `technical_support` | `.env` | 技术支持单位 |
| `contact` | Word/`.env` | 技术支持联系电话 |
| `verification_source` | Word | 清理后的验证过程原始文本，只作为总结输入 |
| `verification` | agent 总结压缩/脚本草稿 | 一段文字，不插入图片 |
| `verification_video_path` | 本地目录 | 优先取 `exp验证视频` 下的视频，其次取 `poc验证视频`、`验证视频`、`视频`、`video` |
| `poc_file_path` | 本地目录 | 优先取 `exp` 下的 zip/脚本，其次取 `poc`、`POC`、`PoC` |
| `submission_zip_path` | 本地目录 | 单个漏洞的 CNNVD 原始整包 zip，用于提交成功后的钉钉附件下载链接 |
| `publish_ready` | 脚本判断 | `true` 表示提交成功后可直接运行上传推送脚本 |

---

## 三、受影响实体描述

`受影响实体描述` 不是 Word 直接提取字段，必须在数据准备阶段补齐。

处理规则：

1. 根据 `affected_product`、`title` 或产品关键词进行 websearch。
2. 提取产品/系统的用途、类型和典型使用场景。
3. 写成 50-120 字中文描述。
4. 不写漏洞影响，不写修复建议，不写营销语。
5. 找不到可靠来源时，基于产品名称做保守描述，并标记为简短通用描述。

示例：

```text
emlog 是一款基于 PHP 的开源博客和内容管理系统，常用于个人博客、轻量级网站和内容发布场景，支持模板、插件和后台管理功能。
```

---

## 四、漏洞验证过程

Word 中的 `漏洞验证过程` 往往很长，可能包含图片、HTTP 报文、代码和步骤说明。不能直接整段粘贴。

处理规则：

1. 先阅读 `form_context.json` 中的 `verification_source`。
2. Word 内容在表格中，不在普通段落里；脚本会遍历所有表格提取字段。
3. 忽略 Word 图片，只提取可文字化的关键步骤。
4. 总结为一段文字，建议 150-300 字。
5. 必须包含入口点、触发条件、关键利用步骤和验证结果。
6. 不要保留大段 HTTP 请求头、Cookie、无关代码块或图片占位。
7. 写入表单时使用 `form_context.json` 中的 `verification`。
8. 不要把 `verification_source` 直接填进页面。

示例结构：

```text
验证过程显示，漏洞入口位于模板 ZIP 上传功能。攻击者在具备后台权限并获取有效 token 后，构造包含合法 header.php 与路径遍历文件名的 ZIP 包上传，服务端仅校验首个模板文件，未校验全部压缩包文件名，随后调用解压逻辑将恶意 PHP 文件写入可访问目录。访问写入后的文件可触发服务端代码执行，证明该文件上传链路可被利用。
```

---

## 五、页面复用规则

- 浏览器阶段只读取 `/tmp/vulns-skills/phase2-cnnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json`。
- 第 1 页使用 `vuln_type`、`risk_level`、`affected_entity_category`、`title`、`affected_product`、`version`、`entity_description`。
- 第 2 页使用 `description`、`technical_support`、`contact`；`description` 已限制在 255 字以内，不要改用 `description_full`。
- 第 3 页使用 `verification`、`verification_video_path`、`poc_file_path`。
- 第 2 页和第 3 页禁止重新运行 `extract_vuln_data.py`。
- 第 3 页禁止再跑任何 Word 提取脚本；如果 `verification` 为空，必须回到数据准备阶段补齐，而不是在页面内临时提取。

---

## 六、提交前检查

提交前确认：

- 三个必填下拉框已选中，且级联下拉已点击最终叶子选项前面的圆圈/单选按钮。
- `entity_description` 已补齐。
- `description` 长度不超过 255 字。
- `verification` 是总结压缩后的一段文字，不是 Word 原文长文本。
- `verification` 不能为空；不能为空时不要进入第 3 页填写。
- 视频和 PoC 路径存在。
- `ready` 必须为 `true`；如为 `false`，先修复 `checks` 中失败项。

---

## 七、提交后的附件上传与钉钉通知

提交成功拿到 `CNNVD-ID` 后，优先使用上传脚本作为收尾动作：

```bash
python3 scripts/publish_submission_zip.py \
  "/tmp/vulns-skills/phase2-cnnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json" \
  --platform-id "<CNNVD-ID>" \
  --notify
```

规则：

- 只上传单个漏洞的 `CNNVD-*.zip` 原始整包。
- 不上传整个批次目录。
- 不重新压缩材料目录。
- 钉钉消息必须包含漏洞名称、`DAS-ID`、`CNNVD 编号` 和附件下载链接。
- 默认远端目录为 `/root/msrc-report-downloads/cnnvd-submissions/YYYY-MM/DAS-ID/`。
