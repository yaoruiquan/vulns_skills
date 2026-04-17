# CNVD 漏洞上报流程

## 流程概览

```
Step 0: 检查环境 → Step 1: 准备数据 → Step 2: 导航表单 → Step 3: 填表 → Step 4: 上传 → Step 4.5: 验证 → Step 5: 提交
```

---

## Step 1: 准备数据

### 1.1 提取漏洞数据

```bash
python scripts/extract_vuln_data.py <DAS-ID> --platform CNVD --data-dir "<数据目录>"
```

**输出示例**：
```json
{
  "das_id": "DAS-T105970",
  "title": "Claude Code系统getMcpHeadersFromHelper模块存在命令执行漏洞",
  "description": "漏洞描述内容...",
  "vuln_type": "命令执行",
  "url": "http://127.0.0.1/",
  "unit_name": "Anthropic",
  "soft_style_id": "28",
  "discoverer_name": "恒脑AI代码审计智能体",
  "affected_product": "Claude Code",
  "version": "2.1.89"
}
```

### 1.2 压缩附件

```bash
cd "<CNVD文件夹路径>" && zip -r /tmp/<DAS-ID>-CNVD.zip .
```

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

切换到"通用型漏洞"后，发现者和发现日期保持默认值不变，只修改"是否公开"。

```
MCP: take_snapshot
MCP: click
  uid: "<否 radio 按钮的 uid>"
```

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

CNVD 表单的漏洞名称最终组合为：`<漏洞名称输入框>存在<漏洞类型>漏洞`

- **漏洞名称输入框**：填写完整漏洞描述（不含"存在"和"漏洞"字样）
  - 示例：`Linux内核系统rxrpc模块内存缓冲区操作限制不当`
- **漏洞类型下拉框**：选择漏洞大类（如"二进制"、"命令执行"等）

```
MCP: take_snapshot
MCP: fill_form
  elements:
    - uid: "<漏洞名称输入框的 uid>"
      value: "<完整的漏洞描述>"
    - uid: "<漏洞类型下拉框的 uid>"
      value: "<vuln_type>"
    - uid: "<漏洞描述输入框的 uid>"
      value: "<description>（不含前缀）"
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
  filePath: "/tmp/<DAS-ID>-CNVD.zip"
```

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
| 漏洞附件 | ✓ 已上传 | zip 文件 |
| 验证码 | 待填写 | OCR识别后填写 |

---

## Step 5: 验证码与提交

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

---

> CSS 选择器参考详见 [selectors.md](selectors.md)
> 字段映射表详见 [field-mapping.md](field-mapping.md)