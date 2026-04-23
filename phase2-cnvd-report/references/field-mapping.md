# CNVD 字段映射表

## 1. 数据字段来源

浏览器填表阶段只读取 `/tmp/vulns-skills/phase2-cnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json`。`extract_vuln_data.py` 是底层提取脚本，不直接作为浏览器阶段的数据源；运行时 JSON 不写入 CNVD 提交材料目录。

| 表单字段 | 数据来源 | 字段名 |
|---------|---------|-------|
| 漏洞厂商 | form_context.json | unit_name |
| 厂商官网 | form_context.json | url |
| 影响对象类型 | form_context.json | soft_style_id |
| 影响产品 | form_context.json | affected_product |
| 影响产品版本 | form_context.json | version |
| 漏洞名称 | form_context.json | title_input |
| 漏洞类型 | form_context.json | vuln_type |
| 漏洞描述 | form_context.json | description，已清理固定分析前缀 |
| 漏洞附件 | form_context.json | attachment_zip_path |
| 钉钉下载附件 | form_context.json | submission_zip_path，等同 CNVD 原始整包 zip |

**标题拆分规则**：

| 字段 | 说明 |
|------|------|
| `title_original` | docx 中的原始漏洞名称 |
| `title_input` | 页面“漏洞名称”输入框填写值，取 `存在` 前面的部分 |
| `title_vuln_phrase` | 原始标题中 `存在` 和 `漏洞` 之间的描述 |
| `title_final_expected` | 提交后预期最终标题，默认等于 `title_original` |

示例：

| 原始标题 | title_input | title_final_expected |
|----------|-------------|----------------------|
| `emlog系统template.php模块存在文件上传漏洞` | `emlog系统template.php模块` | `emlog系统template.php模块存在文件上传漏洞` |
| `Linux内核系统-rxrpc模块存在二进制-内存缓冲区操作限制不当漏洞` | `Linux内核系统-rxrpc模块` | `Linux内核系统-rxrpc模块存在二进制-内存缓冲区操作限制不当漏洞` |

---

## 2. 漏洞类型映射

映射按优先级匹配。二进制、缓冲区、溢出、越界、释放后使用等关键词必须优先匹配为“二进制”，避免被“内存”等泛化词误判为“其他”。

| 数据值 | 下拉框选项 |
|--------|----------|
| SQL注入 | SQL注入 |
| XSS | XSS |
| 命令执行 | 命令执行 |
| 二进制 | 二进制 |
| 内存缓冲区/缓冲区/溢出/越界/释放后使用 | 二进制 |
| 信息泄露 | 信息泄露 |
| 其他 | 其他 |

---

## 3. 影响对象类型映射

| soft_style_id | 下拉框选项 |
|--------------|-----------|
| 27 | 操作系统 |
| 28 | 应用程序 |
| 29 | WEB应用 |
| 30 | 数据库 |

---

## 4. 空字段统一填写规则

| 字段类型 | 填写内容 |
|---------|---------|
| 临时解决方案 | "无" |
| 正式解决方案 | "见附件" |
| 其他无法获取的字段 | "见附件" |

## 5. CNVD 特殊规则

- “是否公开”必须选择“否”。
- 漏洞描述直接使用 `description` 字段，不要填写 `经恒脑AI代码审计智能体分析：` 前缀。
- 附件必须上传 `attachment_zip_path` 指向的 CNVD 原始整包 zip，不要重新压缩 docx 目录。
- 准备阶段 `ready` 为 `false` 时不能进入浏览器填表；先修复 `checks` 里失败的项。
- 提交成功后的钉钉附件下载也使用同一个 CNVD 原始整包 zip；不要上传整个批次目录。
