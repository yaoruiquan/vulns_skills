# CNVD 字段映射表

## 1. 数据字段来源

浏览器填表阶段只读取 `/tmp/vulns-skills/phase2-cnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json`。`extract_vuln_data.py` 是底层提取脚本，不直接作为浏览器阶段的数据源；运行时 JSON 不写入 CNVD 提交材料目录。

优先读取 `dropdown_phase` 和 `page_payloads`。页面联动完成后，一次性填写同组字段，不要填一个字段就重新检查一次。

| 表单字段 | 数据来源 | 字段名 |
|---------|---------|-------|
| 漏洞所属类型 | form_context.json | form_type_label，先选“通用型漏洞”或“事件型漏洞” |
| 漏洞厂商 | form_context.json | unit_name |
| 厂商官网 | form_context.json | url |
| 影响对象类型 | form_context.json | soft_style_id |
| 影响产品 | form_context.json | affected_product |
| 影响产品版本 | form_context.json | version，优先取 Word 的 `受影响实体版本号`，再回退 `影响版本` / `版本号` |
| 漏洞名称 | form_context.json | title_input |
| 漏洞类型 | form_context.json | vuln_type |
| 漏洞描述 | form_context.json | description，已清理固定分析前缀 |
| 漏洞URL | form_context.json | detail_url，固定为 `http://test.com` |
| 临时解决方案 | form_context.json | temp_solution，固定为 `无` |
| 正式解决方案 | form_context.json | formal_solution，固定为 `见附件` |
| 漏洞附件 | form_context.json | browser_upload_path |
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

映射按优先级匹配。返回值必须是 CNVD 页面真实下拉选项，不允许把页面已有选项 fallback 成“其他”。二进制、缓冲区、溢出、越界、释放后使用等关键词必须优先匹配为“二进制”，避免被“内存”等泛化词误判为“其他”。

CNVD 页面当前允许的漏洞类型选项：

```text
SQL注入
XML实体注入
XSS
SSRF
弱口令
文件上传
信息泄露
未授权访问
逻辑缺陷
文件包含
命令执行
目录遍历
任意文件下载
任意文件读取
拒绝服务
二进制
工控设备
服务参数注入
点击劫持
其他
```

| 数据值 | 下拉框选项 |
|--------|----------|
| SQL注入 | SQL注入 |
| XML实体注入 / XXE | XML实体注入 |
| XSS | XSS |
| SSRF / 服务端请求伪造 | SSRF |
| 弱口令 | 弱口令 |
| 未授权访问 / 认证绕过 / 权限绕过 | 未授权访问 |
| 逻辑缺陷 / 业务逻辑 | 逻辑缺陷 |
| 文件包含 | 文件包含 |
| 命令执行 | 命令执行 |
| 远程代码执行 / 代码执行 / 反序列化 | 命令执行 |
| 目录遍历 / 路径遍历 | 目录遍历 |
| 任意文件下载 / 文件下载 | 任意文件下载 |
| 任意文件读取 / 文件读取 | 任意文件读取 |
| 拒绝服务 / DoS | 拒绝服务 |
| 二进制 | 二进制 |
| 内存缓冲区/缓冲区/溢出/越界/释放后使用 | 二进制 |
| 工控设备 / 工控 | 工控设备 |
| 服务参数注入 / 参数注入 | 服务参数注入 |
| 点击劫持 | 点击劫持 |
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
| 漏洞URL | `http://test.com` |
| 临时解决方案 | "无" |
| 正式解决方案 | "见附件" |
| 其他无法获取的字段 | "见附件" |

## 5. CNVD 特殊规则

- 填写顺序固定为：先选 `form_type_label`，再选 `vuln_type`，等待页面联动完成后，再一次性填写其余文本字段。
- “是否公开”必须选择“否”。
- 漏洞描述直接使用 `description` 字段，不要填写 `经恒脑AI代码审计智能体分析：` 前缀。
- 选择完“漏洞类型”后，漏洞详情页只允许继续填写 `description`、`detail_url`、`temp_solution`、`formal_solution` 和固定默认值；不要再次读取 docx 或临时运行提取脚本。
- 附件必须上传 `browser_upload_path` 指向的浏览器专用 ASCII zip 副本；若材料目录里还没有 `CNVD-*.zip`，准备阶段会自动补建原始整包 zip 并复制出浏览器上传副本。
- 准备阶段 `ready` 为 `false` 时不能进入浏览器填表；先修复 `checks` 里失败的项。
- 提交成功后的钉钉附件下载也使用同一个 CNVD 原始整包 zip；不要上传整个批次目录。
