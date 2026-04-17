# CNVD 字段映射表

## 1. 数据字段来源

| 表单字段 | 数据来源 | 字段名 |
|---------|---------|-------|
| 漏洞厂商 | extract_vuln_data | unit_name |
| 厂商官网 | extract_vuln_data | url |
| 影响对象类型 | extract_vuln_data | soft_style_id |
| 影响产品 | extract_vuln_data | affected_product |
| 影响产品版本 | extract_vuln_data | version |
| 漏洞名称 | CNVD文件夹名/docx文件名 | 完整漏洞描述（不含"存在"和"漏洞"） |
| 漏洞类型 | extract_vuln_data | vuln_type |
| 漏洞描述 | extract_vuln_data | description |

**漏洞名称提取示例**：
- CNVD文件夹名：`CNVD-Linux内核系统-rxrpc模块存在二进制-内存缓冲区操作限制不当漏洞`
- 提取结果：`Linux内核系统rxrpc模块内存缓冲区操作限制不当`

---

## 2. 漏洞类型映射

| 数据值 | 下拉框选项 |
|--------|----------|
| SQL注入 | SQL注入 |
| XSS | XSS |
| 命令执行 | 命令执行 |
| 二进制 | 二进制 |
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