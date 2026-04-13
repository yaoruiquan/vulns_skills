# phase2-cnvd-report-MCP

通过 chrome-devtools MCP 控制浏览器完成 CNVD 漏洞上报。

> MCP 工具详细说明参见 [references/mcp-tools.md](references/mcp-tools.md)

---

## 一、前提条件

### 1.1 安装 chrome-devtools-mcp

```bash
npm install -g chrome-devtools-mcp@latest
```

### 1.2 配置 MCP

在 `~/.mcp.json` 中配置：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

并在 `~/.claude/settings.json` 中添加：

```json
{
  "enableAllProjectMcpServers": true
}
```

### 1.3 启动 Chrome（调试端口）

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9223 \
  --user-data-dir=/tmp/chrome-debug-cnvd
```

---

## 二、执行流程概览

```
Step 0: 检查环境 → Step 1: 准备数据 → Step 2: 导航表单 → Step 3: 填表 → Step 4: 上传 → Step 5: 提交
```

---

## 三、详细步骤

### Step 0: 检查环境状态

**第一步必须先检查调试端口和 MCP 连接状态，确保环境就绪后再进行后续操作。**

#### 0.1 检查 Chrome 调试端口

```bash
curl -s http://localhost:9223/json/version
```

**预期输出**：
```json
{
  "Browser": "Chrome/xxx.x.xxxx.xx",
  "Protocol-Version": "1.3",
  "webSocketDebuggerUrl": "ws://localhost:9223/devtools/browser/xxx"
}
```

**如果无输出或连接失败**：

```bash
# 启动 Chrome 调试模式
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9223 \
  --user-data-dir=/tmp/chrome-debug-cnvd &
```

#### 0.2 检查 MCP 连接状态

```
MCP: list_pages
```

**预期输出**：返回当前浏览器打开的页面列表。

**如果返回错误**：
1. 检查 `~/.mcp.json` 配置是否正确
2. 检查 MCP server 是否启动：`ps aux | grep chrome-devtools-mcp`
3. 重启 Claude Code 会话

#### 0.3 环境检查清单

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|----------|
| Chrome 调试端口 | `curl localhost:9223/json/version` | 返回 JSON |
| MCP 连接 | `list_pages` | 返回页面列表 |
| 登录状态 | 打开 CNVD 首页检查 | 已登录/未登录 |

**只有当以上检查全部通过后，才继续执行后续步骤。**

---

### Step 1: 准备数据

#### 1.1 提取漏洞数据

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

#### 1.2 压缩附件

```bash
cd "<CNVD文件夹路径>" && zip -r /tmp/<DAS-ID>-CNVD.zip .
```

---

### Step 2: 导航到表单页面

#### 2.1 打开 CNVD 首页

```
MCP: navigate_page
  type: "url"
  url: "https://www.cnvd.org.cn/"
```

#### 2.2 点击登录

```
MCP: take_snapshot
MCP: click
  uid: "<登录链接的 uid>"
```

#### 2.3 处理登录验证码

参见 [五、自动化验证码识别](#五自动化验证码识别)。

#### 2.4 导航到漏洞上报表单

登录成功后：

```
MCP: take_snapshot

# 点击"用户中心"
MCP: click
  uid: "<用户中心的 uid>"

# 点击"立即上报漏洞"
MCP: take_snapshot
MCP: click
  uid: "<立即上报漏洞的 uid>"
```

---

### Step 3: 填写表单

#### 3.1 切换表单类型 + 选择漏洞类型

**关键步骤**：先切换到"通用型漏洞"，然后选择漏洞类型（从数据中获取）。

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

当选择"二进制"类型时，表单会显示额外字段，需要填写：

| 字段 | 说明 | 填写内容 |
|------|------|----------|
| 版本号 | 影响版本 | `<version>` |
| 触发位置 | 漏洞触发位置 | 从漏洞描述中提取，如"rxrpc模块" |
| Poc | 漏洞验证代码 | 填写"见附件" |

漏洞类型映射参见 [四、字段映射表](#四字段映射表)。

#### 3.2 填写基本信息

**注意**：切换到"通用型漏洞"后，发现者和发现日期保持默认值不变，只修改"是否公开"。

```
MCP: take_snapshot

# 是否公开 - 选择"否"
MCP: click
  uid: "<否 radio 按钮的 uid>"
```

#### 3.3 填写厂商信息（从数据获取）

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

影响对象类型映射参见 [四、字段映射表](#四字段映射表)。

#### 3.4 填写漏洞详情（从数据获取）

**重要：漏洞名称填写规则**

CNVD 表单的漏洞名称分为两部分，最终组合为：`<漏洞名称输入框>存在<漏洞类型>漏洞`

- **漏洞名称输入框**：填写完整的漏洞描述（不含"存在"和"漏洞"字样）
  - 示例：`Linux内核系统rxrpc模块内存缓冲区操作限制不当`
  - 来源：从 CNVD 文件夹名或 docx 文件名提取
- **漏洞类型下拉框**：选择漏洞大类（如"二进制"、"命令执行"等）
  - 漏洞类型和漏洞名称是独立的，互不影响
  - 选择"二进制"不会改变漏洞名称内容

```
MCP: take_snapshot
MCP: fill_form
  elements:
    - uid: "<漏洞名称输入框的 uid>"
      value: "<完整的漏洞描述，如：Linux内核系统rxrpc模块内存缓冲区操作限制不当>"
    - uid: "<漏洞类型下拉框的 uid>"
      value: "<vuln_type，如：二进制>"
```

**其他字段填写**：

```
MCP: take_snapshot
MCP: fill_form
  elements:
    - uid: "<漏洞描述输入框的 uid>"
      value: "<description>（不含'经恒脑AI代码审计智能体分析：'前缀）"
    - uid: "<临时解决方案输入框的 uid>"
      value: "无"
    - uid: "<正式解决方案输入框的 uid>"
      value: "见附件"
```

**注意**：漏洞描述直接填写描述内容，不需要添加"经恒脑AI代码审计智能体分析："等前缀。

---

### Step 4: 上传附件

```
MCP: take_snapshot
MCP: upload_file
  uid: "<文件上传输入框的 uid>"
  filePath: "/tmp/<DAS-ID>-CNVD.zip"
```

---

### Step 4.5: 验证表单完整性

**提交前必须验证所有字段已填写完整**：

```
MCP: take_snapshot
```

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

**空字段统一填写规则**：

- 临时解决方案：填写"无"
- 正式解决方案：填写"见附件"
- 其他无法从数据获取的字段：填写"见附件"

**发现空字段时立即补填**：

```
MCP: fill_form
  elements:
    - uid: "<空字段 uid>"
      value: "见附件"  # 或 "无" 用于临时解决方案
```

---

### Step 5: 验证码与提交

参见 [五、自动化验证码识别](#五自动化验证码识别)。

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

## 四、字段映射表

### 4.1 数据字段来源

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

### 4.2 漏洞类型映射

| 数据值 | 下拉框选项 |
|--------|----------|
| SQL注入 | SQL注入 |
| XSS | XSS |
| 命令执行 | 命令执行 |
| 二进制 | 二进制 |
| 信息泄露 | 信息泄露 |
| 其他 | 其他 |

### 4.3 影响对象类型映射

| soft_style_id | 下拉框选项 |
|--------------|-----------|
| 27 | 操作系统 |
| 28 | 应用程序 |
| 29 | WEB应用 |
| 30 | 数据库 |

---

## 五、自动化验证码识别

使用 ddddocr 库自动识别验证码，无需人工介入。

> 详细说明参见 [references/captcha-ocr.md](references/captcha-ocr.md)

### 5.1 验证码类型

| 场景 | 验证码类型 | OCR 识别 |
|------|----------|----------|
| 登录验证码 | 中文词语（如"读书"） | ✓ 可识别 |
| 提交验证码 | 字母数字组合（如"db3D"） | ✓ 可识别 |

### 5.2 识别成功率

- 中文词语验证码：约 80%
- 字母数字验证码：约 50-70%

### 5.3 OCR 脚本

```bash
python3 scripts/captcha_ocr.py <图片路径>
```

### 5.4 验证码识别流程

**重要：验证码操作必须先刷新再识别**

```
# 1. 点击验证码图片刷新
MCP: click
  uid: "<验证码图片的 uid>"

# 2. 截图验证码图片
MCP: take_screenshot
  uid: "<验证码图片的 uid>"
  filePath: "/tmp/captcha.png"

# 3. OCR 识别
python3 scripts/captcha_ocr.py /tmp/captcha.png

# 4. 直接填写验证码
MCP: fill
  uid: "<验证码输入框的 uid>"
  value: "<OCR识别结果>"
```

**识别失败时：打开新标签页识别**

当截图识别无结果或识别错误时，使用新标签页方法：

```
# 1. 在新标签页打开验证码URL
MCP: new_page
  url: "https://www.cnvd.org.cn/common/myCodeNew"

# 2. 截图新标签页
MCP: take_screenshot
  filePath: "/tmp/captcha_new_tab.png"

# 3. OCR 识别
python3 scripts/captcha_ocr.py /tmp/captcha_new_tab.png

# 4. 关闭新标签页，返回原表单页
MCP: list_pages
MCP: close_page
  pageId: <新标签页的 pageId>

# 5. 在表单页填写验证码
MCP: fill
  uid: "<验证码输入框的 uid>"
  value: "<OCR识别结果>"
```

### 5.5 登录验证码处理（Step 2.3）

```
# 1. 点击刷新验证码
MCP: click
  uid: "<验证码图片的 uid>"

# 2. 截图识别
MCP: take_screenshot
  uid: "<验证码图片的 uid>"
  filePath: "/tmp/captcha_login.png"

python3 scripts/captcha_ocr.py /tmp/captcha_login.png

# 3. 填写并提交
MCP: fill
  uid: "<验证码输入框的 uid>"
  value: "<OCR识别结果>"

MCP: click
  uid: "<提交按钮的 uid>"
```

### 5.6 提交验证码处理（Step 5）

```
# 1. 点击刷新验证码
MCP: click
  uid: "<验证码图片的 uid>"

# 2. 截图识别
MCP: take_screenshot
  uid: "<验证码图片的 uid>"
  filePath: "/tmp/captcha_form.png"

python3 scripts/captcha_ocr.py /tmp/captcha_form.png

# 3. 填写验证码
MCP: fill
  uid: "<验证码输入框的 uid>"
  value: "<OCR识别结果>"
```

**注意**：
- 新标签页的验证码可能与表单页不同步，但识别成功率更高
- OCR 识别成功率约 50-70%，可能需要重试

---

## 六、文件结构

```
phase2-cnvd-report-MCP/
├── SKILL.md                  # 本文件
├── README.md                 # 详细说明
├── .mcp.json                 # MCP server 配置
├── .claude/
│   └── settings.json         # Claude Code 项目配置
├── scripts/
│   ├── extract_vuln_data.py  # 提取漏洞数据
│   ├── compress_zip.py       # 压缩附件
│   ├── captcha_ocr.py        # 验证码 OCR 识别
│   └── chrome-devtools-mcp-wrapper.sh  # MCP wrapper 脚本
└── references/
    ├── captcha-ocr.md        # 验证码 OCR 详细说明
    ├── mcp-connection.md     # MCP 连接原理与经验
    ├── selectors.md          # CSS 选择器参考
    ├── mcp-tools.md          # MCP 工具详细参考
    └── error-handling.md     # 错误处理
```

---

## 七、相关链接

- [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [CNVD 官网](https://www.cnvd.org.cn/)