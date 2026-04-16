# phase2-cnnvd-report-MCP

通过 chrome-devtools MCP 控制浏览器完成 CNNVD 漏洞上报。

> MCP 工具详细说明参见 [references/mcp-tools.md](references/mcp-tools.md)

---

## 一、前提条件

### 1.1 安装 chrome-devtools-mcp

```bash
npm install -g chrome-devtools-mcp@latest
```

### 1.2 配置 MCP

在当前 skill 目录的 `./.mcp.json` 或 `./.claude/settings.json` 中配置：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

### 1.3 启动 Chrome（调试端口）

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh
```

该 skill 的固定隔离配置：

- 调试端口：`9333`
- 独立 profile：`~/.claude/chrome-profiles/cnnvd-report`
- 与日常 Chrome 默认 profile 隔离

如果站点保护页、登录态或浏览器足迹有问题，优先改用：

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

启动模式说明：

- `isolated`：纯隔离 profile，默认值。
- `seed-default`：先复制日常 Chrome 的 `Default` profile 到 skill profile，再用 `9333` 启动。
- `live-default`：直接使用日常 Chrome 的用户数据目录。只有 `seed-default` 仍不够时再用，并先关闭普通 Chrome。

### 1.4 安装 OCR 依赖

```bash
pip install ddddocr
```

---

## 二、执行流程概览

```
Step 0: 检查环境 → Step 1: 准备数据 → Step 2: 导航登录 → Step 3: 基本信息 → Step 4: 漏洞详情 → Step 5: 漏洞验证 → 提交
```

**表单分为3步**：
1. 漏洞基本信息
2. 漏洞详情
3. 漏洞验证

---

## 三、详细步骤

### Step 0: 检查环境状态

**第一步必须先检查调试端口和 MCP 连接状态，确保环境就绪后再进行后续操作。**

#### 0.1 检查 Chrome 调试端口

```bash
curl -s http://localhost:9333/json/version
```

**预期输出**：
```json
{
  "Browser": "Chrome/xxx.x.xxxx.xx",
  "Protocol-Version": "1.3",
  "webSocketDebuggerUrl": "ws://localhost:9333/devtools/browser/xxx"
}
```

**如果无输出或连接失败**：

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh
```

**如果需要复用日常 Chrome 足迹**：

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

#### 0.2 检查 MCP 连接状态

```
MCP: list_pages
```

**预期输出**：返回当前浏览器打开的页面列表。

**如果返回错误**：
1. 检查当前 skill 目录的 `./.mcp.json` 或 `./.claude/settings.json` 是否正确
2. 检查 MCP server 是否启动：`ps aux | grep chrome-devtools-mcp`
3. 重启 Claude Code 会话

#### 0.3 环境检查清单

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|----------|
| Chrome 调试端口 | `curl localhost:9333/json/version` | 返回 JSON |
| MCP 连接 | `list_pages` | 返回页面列表 |
| 登录状态 | 打开 CNNVD 首页检查 | 已登录/未登录 |

**只有当以上检查全部通过后，才继续执行后续步骤。**

---

## 四、数据字段与映射

| 表单字段 | 数据来源 | 字段名 | 备注 |
|---------|---------|-------|------|
| 漏洞名称 | extract_vuln_data | title | |
| CVE编号 | extract_vuln_data | cve_id | 可选 |
| 漏洞类型 | extract_vuln_data | vuln_type | 需映射到级联路径 |
| 漏洞自评级 | extract_vuln_data | risk_level | 超危/高危/中危/低危 |
| 公开情况 | 固定值 | 未公开 | 默认即可 |
| 受影响实体厂商名称 | extract_vuln_data | unit_name | |
| 受影响实体分类 | 根据产品判断 | - | 操作系统/Web应用/数据库等 |
| 受影响实体名称 | extract_vuln_data | affected_product | |
| 受影响实体版本 | extract_vuln_data | version | |
| 受影响实体原始下载链接 | extract_vuln_data | download_url | 可选 |
| 受影响实体描述 | 联网搜索 | - | 产品简介，50-200字 |
| 受影响网络资源数量 | 固定值 | 空 | 默认即可 |
| 漏洞描述或简介 | extract_vuln_data | description | |
| 技术支持 | 固定值 | 杭州安恒信息技术股份有限公司 | |
| 技术支持联系电话 | extract_vuln_data | contact | 或默认 15700082275 |
| 验证过程 | Word 文档表格 | verification | 去掉开头结尾标记 |

### 4.2 漏洞类型映射表

| 数据值 | CNNVD 级联路径 |
|-------|--------------|
| 命令执行/命令注入 | 代码问题 → 输入验证错误 → 注入 → 命令注入 |
| 越界写入/堆溢出 | 代码问题 → 输入验证错误 → 缓冲区错误 |
| SQL注入 | 代码问题 → 输入验证错误 → 注入 → SQL注入 |
| XSS/跨站脚本 | 代码问题 → 输入验证错误 → 注入 → 跨站脚本 |
| 代码执行/代码注入 | 代码问题 → 输入验证错误 → 注入 → 代码注入 |
| 路径遍历 | 代码问题 → 输入验证错误 → 路径遍历 |
| CSRF | 代码问题 → 输入验证错误 → 跨站请求伪造 |

### 4.3 漏洞类型层级结构

```
代码问题
├── 输入验证错误
│   ├── 注入
│   │   ├── 代码注入
│   │   ├── 跨站脚本
│   │   ├── 命令注入
│   │   ├── 格式化字符串错误
│   │   └── SQL注入
│   ├── 跨站请求伪造
│   ├── 缓冲区错误    ← 越界写入/堆溢出选此项
│   ├── 后置链接
│   └── 路径遍历
├── 授权问题
├── 竞争条件问题
├── 处理逻辑错误
├── 数字错误
├── 未声明问题
├── 加密问题
├── 数据转换问题
└── 资源管理错误
配置错误
其他
环境问题
```

---

## 五、详细步骤

#### 1.1 提取漏洞数据

**脚本路径**：`~/.claude/skills/phase2-cnnvd-report-cdp/scripts/extract_vuln_data.py`

**默认数据目录**：`/Users/yao/LLM/vulns/date`

```bash
python3 ~/.claude/skills/phase2-cnnvd-report-cdp/scripts/extract_vuln_data.py <DAS-ID> --platform CNNVD
```

**指定数据目录**：
```bash
python3 ~/.claude/skills/phase2-cnnvd-report-cdp/scripts/extract_vuln_data.py <DAS-ID> --platform CNNVD --data-dir "<自定义数据目录>"
```

**输出示例**：
```json
{
  "das_id": "DAS-T105970",
  "title": "Claude Code系统getMcpHeadersFromHelper模块存在命令执行漏洞",
  "description": "漏洞描述内容...",
  "vuln_type": "命令执行",
  "affected_product": "Claude Code",
  "version": "2.1.89",
  "unit_name": "Anthropic",
  "verification": "详细验证过程...",
  "contact": "15700082275",
  "folder_path": "/Users/yao/LLM/vulns/date/DAS-T105970-xxx/CNNVD-xxx",
  "docx_path": "/Users/yao/LLM/vulns/date/DAS-T105970-xxx/CNNVD-xxx/xxx.docx"
}
```

#### 1.2 压缩附件

```bash
cd "<CNNVD文件夹路径>" && zip -r /tmp/<DAS-ID>-CNNVD.zip .
```

或使用脚本：
```bash
python3 ~/.claude/skills/phase2-cnnvd-report-cdp/scripts/compress_zip.py "<CNNVD文件夹路径>" /tmp/<DAS-ID>-CNNVD.zip
```

---

### Step 2: 导航到表单页面

#### 2.1 打开 CNNVD 首页

```
MCP: navigate_page
  type: "url"
  url: "https://www.cnnvd.org.cn/home/childHome"
```

#### 2.2 点击登录

```
MCP: take_snapshot
MCP: click
  uid: "<登录链接的 uid>"
```

#### 2.3 登录流程（自动 OCR 识别）

##### 2.3.1 点击登录按钮

```
MCP: take_snapshot
MCP: click
  uid: "<登录按钮的 uid>"
```

##### 2.3.2 填写账号密码

```
MCP: take_snapshot
MCP: fill_form
  elements:
    - uid: "<用户名输入框的 uid>"
      value: "tina.zhang@dbappsecurity.com.cn"
    - uid: "<密码输入框的 uid>"
      value: "Dbapp@12345"
```

##### 2.3.3 OCR 识别验证码

**重要：验证码操作必须先刷新再识别**

**步骤 A：点击刷新验证码**

```
MCP: click
  uid: "<验证码图片的 uid>"
```

**步骤 B：截图验证码保存到本地**

```
MCP: take_screenshot
  uid: "<验证码图片的 uid>"
  filePath: "/tmp/cnnvd_captcha.png"
```

**步骤 C：运行 OCR 脚本识别**

```bash
python3 ~/.claude/skills/phase2-cnnvd-report-cdp/scripts/captcha_ocr.py /tmp/cnnvd_captcha.png
```

**输出示例**：
```
7mp9
```

最后一行即为识别结果（如 `7mp9`）。

**步骤 D：填入验证码**

```
MCP: click
  uid: "<验证码输入框的 uid>"

MCP: type_text
  text: "<OCR识别结果>"
```

**识别失败时：打开新标签页识别**

当截图识别无结果或识别错误时，使用新标签页方法：

```
# 1. 在新标签页打开验证码URL
MCP: new_page
  url: "<验证码图片URL>"

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
MCP: type_text
  text: "<OCR识别结果>"
```

##### 2.3.4 点击登录

```
MCP: click
  uid: "<登录按钮的 uid>"
```

##### 2.3.5 验证登录结果

```
MCP: take_snapshot
```

登录成功标志：URL 变为 `https://www.cnnvd.org.cn/backHome/workDesk`，显示用户名。

**登录失败处理**：
1. 验证码错误：重新执行 2.3.3 步骤
2. 账号密码错误：检查凭据
3. 刷新页面后重试

#### 2.4 导航到漏洞上报表单

登录成功后：

```
MCP: take_snapshot

# 点击"漏洞管理"
MCP: click
  uid: "<漏洞管理的 uid>"

# 点击"通用型漏洞报送"
MCP: take_snapshot
MCP: click
  uid: "<通用型漏洞报送的 uid>"
```

---

### Step 3: 填写表单（第1步：漏洞基本信息）

**表单页面 URL**: `https://www.cnnvd.org.cn/backHome/generalSend`

#### 3.1 表单字段列表

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 漏洞名称 | 文本框 | ✓ | title |
| CVE编号 | 文本框 | | 可选 |
| 漏洞类型 | 下拉框 | ✓ | vuln_type |
| 漏洞自评级 | 下拉框 | ✓ | 高危/中危/低危 |
| 公开情况 | 下拉框 | | 已公开/未公开 |
| 受影响实体厂商名称 | 文本框 | ✓ | unit_name |
| 受影响实体分类 | 下拉框 | ✓ | 软件/硬件/固件等 |
| 受影响实体名称 | 文本框 | ✓ | affected_product |
| 受影响实体版本 | 文本框 | ✓ | version |
| 受影响实体原始下载链接 | 文本框 | | 可选 |
| 受影响实体描述 | 多行文本框 | ✓ | 需联网搜索 |
| 受影响网络资源数量 | 数字输入框 | | 默认为空 |

#### 3.2 填写流程

##### 3.2.1 获取表单快照

```
MCP: take_snapshot
```

##### 3.2.2 填写漏洞名称

```
MCP: fill
  uid: "<漏洞名称输入框的 uid>"
  value: "<title>"
```

##### 3.2.3 选择漏洞类型（级联下拉框）

**漏洞类型是多级下拉菜单**，需要逐级展开：

```
MCP: click
  uid: "<漏洞类型下拉框的 uid>"

MCP: take_snapshot
```

**级联路径示例（命令执行）**：
1. 点击"代码问题"
2. 展开"输入验证错误"
3. 展开"注入"
4. 选择"命令注入"

```
# 第一级：代码问题
MCP: click
  uid: "<代码问题的 uid>"

MCP: take_snapshot

# 第二级：输入验证错误
MCP: click
  uid: "<输入验证错误的 uid>"

MCP: take_snapshot

# 第三级：注入
MCP: click
  uid: "<注入的 uid>"

MCP: take_snapshot

# 第四级：命令注入
MCP: click
  uid: "<命令注入 radio 的 uid>"

# 关闭下拉菜单
MCP: press_key
  key: "Escape"
```

漏洞类型级联路径参见 [三、数据字段与映射](#三数据字段与映射)。

##### 3.2.4 选择漏洞自评级（下拉框）

```
MCP: click
  uid: "<漏洞自评级下拉框的 uid>"

MCP: take_snapshot
MCP: click
  uid: "<高危/中危/低危选项的 uid>"
```

##### 3.2.5 填写受影响实体信息

```
MCP: fill_form
  elements:
    - uid: "<受影响实体厂商名称的 uid>"
      value: "<unit_name>"
    - uid: "<受影响实体名称的 uid>"
      value: "<affected_product>"
    - uid: "<受影响实体版本的 uid>"
      value: "<version>"
```

##### 3.2.6 选择受影响实体分类（下拉框）

```
MCP: click
  uid: "<受影响实体分类下拉框的 uid>"

MCP: take_snapshot
MCP: click
  uid: "<分类选项的 uid>"
```

**分类选项**：
- 应用软件
- 操作系统
- 网络设备
- 安全设备
- 智能家居设备
- 移动设备
- 数据库
- Web应用
- 其他

##### 3.2.7 填写受影响实体描述

**注意**：需联网搜索产品描述，约 50-200 字。

```
MCP: fill
  uid: "<受影响实体描述文本框的 uid>"
  value: "<联网搜索得到的产品描述>"
```

##### 3.2.8 点击"下一步"

```
MCP: click
  uid: "<下一步按钮的 uid>"
```

#### 3.3 会话超时处理

**现象**：点击菜单后跳转回登录页面

**处理**：
1. 检查当前 URL 是否为登录页
2. 如果是，重新执行 Step 2.3 登录流程
3. 登录后重新导航到表单页面

```
# 检查是否需要重新登录
MCP: take_snapshot
# 如果看到登录表单，则重新登录
```

---

### Step 4: 漏洞详情

**表单步骤**: 第2步

#### 4.1 表单字段列表

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 漏洞描述或简介 | 多行文本框 | ✓ | description |
| 漏洞影响描述 | 多行文本框 | | 可选 |
| 网络资产探测指纹 | 多行文本框 | | 可选 |
| 漏洞定位 | 多行文本框 | | 可选 |
| 漏洞触发条件 | 多行文本框 | | 可选 |
| 技术支持 | 文本框 | ✓ | 固定值：杭州安恒信息技术股份有限公司 |
| 技术支持联系电话 | 文本框 | ✓ | contact_phone 或默认值 |

#### 4.2 填写流程

##### 4.2.1 获取表单快照

```
MCP: take_snapshot
```

##### 4.2.2 填写漏洞描述

```
MCP: fill
  uid: "<漏洞描述或简介文本框的 uid>"
  value: "<description>"
```

##### 4.2.3 填写提交者信息

**规则**：
- 技术支持：固定填写【杭州安恒信息技术股份有限公司】
- 技术支持联系电话：优先按 word 文档填写分析人员电话，无电话则填写 15700082275

```
MCP: fill_form
  elements:
    - uid: "<技术支持输入框的 uid>"
      value: "杭州安恒信息技术股份有限公司"
    - uid: "<技术支持联系电话输入框的 uid>"
      value: "<contact_phone 或 15700082275>"
```

##### 4.2.4 点击"下一步"

```
MCP: click
  uid: "<下一步按钮的 uid>"
```

---

### Step 5: 漏洞验证

**表单步骤**: 第3步

#### 5.1 表单字段列表

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 验证过程 | 富文本编辑器 | ✓ | 从 Word 文档复制 |
| 验证录像 | 文件上传 | 条件 | 视频文件，不超过 50MB |
| PoC属性 | 单选 + 文件上传 | 条件 | 脚本文件/二进制文件/其他/无 |
| 语言 | 下拉框 | 条件 | PoC 语言选择 |

#### 5.2 填写验证过程

**验证过程字段为富文本编辑器（iframe）**，从 Word 文档提取内容：

##### 5.2.1 从 Word 文档提取验证过程

```bash
python3 -c "
from docx import Document

doc = Document('<docx路径>')

# 获取表格中验证过程的内容
table = doc.tables[0]
for row in table.rows:
    cells = row.cells
    if len(cells) >= 2 and cells[0].text.strip() == '漏洞验证过程':
        content = cells[1].text.strip()
        # 去掉开头和结尾标记
        if content.startswith('此分析报告由VF自动生成，并经过人工核验。'):
            content = content[len('此分析报告由VF自动生成，并经过人工核验。'):].strip()
        if '（更多成果请查看VF官网：https://v.das-ai.com/）' in content:
            content = content.replace('（更多成果请查看VF官网：https://v.das-ai.com/）', '').strip()
        print(content)
        break
"
```

##### 5.2.2 通过 JavaScript 填写富文本编辑器

```
# 点击编辑区域
MCP: click
  uid: "<编辑区的 uid>"

# 执行 JavaScript 填写内容
MCP: evaluate_script
  function: |
    () => {
      const iframe = document.querySelector('iframe[title="Rich Text Area"]');
      if (iframe && iframe.contentDocument) {
        const content = `<验证过程内容>`;
        // 将文本转换为段落
        const paragraphs = content.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
        iframe.contentDocument.body.innerHTML = paragraphs;
        return '验证过程已填写';
      }
      return '未找到iframe';
    }
```

#### 5.3 上传验证录像

**重要**：如果有验证视频，必须上传。视频文件可能位于以下两个目录之一：

- `<CNNVD文件夹>/poc验证视频/`
- `<CNNVD文件夹>/exp验证视频/`

**步骤 A：选择"有"验证录像**

```
MCP: take_snapshot
MCP: click
  uid: "<有 radio 按钮的 uid>"
```

**步骤 B：上传视频文件**

```
MCP: take_snapshot
MCP: upload_file
  uid: "<点击上传按钮的 uid>"
  filePath: "<CNNVD文件夹>/<poc验证视频或exp验证视频>/<视频文件名>"
```

**验证视频路径示例**：
```
# poc验证视频目录
/Users/yao/Documents/网安- AI应用开发/监管上报/杭州安恒信息原创漏洞报送7个/DAS-T105995-xxx/CNNVD-xxx/poc验证视频/xxx.mp4

# exp验证视频目录
/Users/yao/Documents/网安- AI应用开发/监管上报/杭州安恒信息原创漏洞报送7个/DAS-T105995-xxx/CNNVD-xxx/exp验证视频/xxx.mp4
```

**注意**：
- 文件大小不超过 50MB，超过则联系漏洞提交者重新提供
- 支持格式：avi, wmv, mpeg, mp4, m4v, mov, asf, flv, f4v, rmvb, rm, 3gp, vob
- **必须先选择"有"选项，上传按钮才会变为可用状态**

#### 5.4 上传 PoC 附件

**重要**：PoC 附件可能位于以下两个目录之一：

- `<CNNVD文件夹>/exp/` （通常是 zip 文件）
- `<CNNVD文件夹>/poc/` （通常是 zip 文件）

**步骤 A：选择 PoC 属性**

```
MCP: click
  uid: "<其他/脚本文件/二进制文件 radio 的 uid>"
```

**步骤 B：上传 PoC 文件**

```
MCP: take_snapshot
MCP: upload_file
  uid: "<点击上传按钮的 uid>"
  filePath: "<CNNVD文件夹>/<exp或poc>/<PoC文件名>.zip"
```

**PoC 附件路径示例**：
```
# exp 目录
/Users/yao/Documents/网安- AI应用开发/监管上报/杭州安恒信息原创漏洞报送7个/DAS-T105995-xxx/CNNVD-xxx/exp/24b80411-bd8b-47e2-9a4d-de2c6f7be8ba.zip

# poc 目录
/Users/yao/Documents/网安- AI应用开发/监管上报/杭州安恒信息原创漏洞报送7个/DAS-T105995-xxx/CNNVD-xxx/poc/xxx.zip
```

**注意**：
- 支持格式：zip, rar
- 文件大小不超过 50MB

#### 5.5 提交表单

**重要**：根据实际测试，最终提交**不需要验证码**。

```
MCP: click
  uid: "<提交按钮的 uid>"
```

#### 5.6 获取 CNNVD-ID

提交成功后，页面跳转到"我的漏洞"页面，可从列表中获取 CNNVD-ID：

```
MCP: take_snapshot
```

在页面中查找 `CNNVD-\d{8}-\d+` 格式的编号。

#### 5.7 更新漏洞汇总表

提交成功后，将漏洞信息添加到汇总表：

**汇总表路径**：`/Users/yao/Documents/网安- AI应用开发/监管上报/汇总表/漏洞汇总表.xlsx`

**汇总表字段**：

| 字段 | 说明 | 示例 |
|------|------|------|
| 漏洞标题 | 漏洞完整名称 | Linux内核系统-rxrpc模块存在二进制-内存缓冲区操作限制不当漏洞 |
| 影响厂商 | 受影响厂商名称 | Linux |
| 漏洞编号 | DAS-ID | DAS-T105980 |
| 提交人员 | 分析人员姓名 | 从 Word 文档提取 |
| 上报CNVD编号 | CNVD 编号（如有） | CNVD-2026-xxxxx |
| 上报CNNVD编号 | CNNVD 编号 | CNNVD-2026-99372920 |
| 上报日期 | 提交日期 | 2026-04-09 |

**更新脚本**：

```bash
python3 ~/.claude/skills/phase2-cnnvd-report-cdp/scripts/update_summary.py \
  --title "<漏洞标题>" \
  --vendor "<影响厂商>" \
  --das-id "<DAS-ID>" \
  --submitter "<提交人员>" \
  --cnvd-id "<CNVD编号>" \
  --cnnvd-id "<CNNVD编号>" \
  --date "<上报日期>"
```

**注意**：
- 如果汇总表文件不存在，脚本会自动创建
- 如果漏洞已存在（根据 DAS-ID 判断），则更新对应行
- CNVD 编号可为空，CNNVD 编号必填

---

## 六、人工介入点与自动化

### 5.1 人工介入点汇总

| 步骤 | 操作 | 说明 |
|------|------|------|
| Step 2.3 | 登录验证码 | **已自动化**：ddddocr OCR 识别 |
| Step 3.2.7 | 受影响实体描述 | 需联网搜索产品描述 |
| Step 5.2 | 验证过程内容 | 从 Word 提取，去掉开头结尾标记 |

### 5.2 OCR 自动化说明

- 使用 `ddddocr` 库自动识别验证码
- 脚本路径：`~/.claude/skills/phase2-cnnvd-report-cdp/scripts/captcha_ocr.py`
- 识别率约 80-90%，失败时自动重试

> 详细说明参见 [references/captcha-ocr.md](references/captcha-ocr.md)

### 5.3 Word 文档验证过程提取规则

- 去掉开头：`此分析报告由VF自动生成，并经过人工核验。`
- 去掉结尾：`（更多成果请查看VF官网：https://v.das-ai.com/）`
- 验证过程内容在 Word 表格的"漏洞验证过程"单元格中

---

## 七、测试结果示例

**成功提交的漏洞**：
- CNNVD-ID: CNNVD-2026-53985539
- 漏洞名称: Linux内核系统nfs4xdr-c模块存在越界写入漏洞
- 危害等级: 高危
- 状态: 待研判

---

## 八、CNNVD 漏洞通报

漏洞预警漏洞应通报至 CNNVD 漏洞通报，并在表格《漏洞数据上报》中同步更新。

---

## 九、文件结构

```
phase2-cnnvd-report-MCP/
├── SKILL.md                  # 本文件
├── README.md                 # 详细说明
├── scripts/
│   ├── extract_vuln_data.py  # 提取漏洞数据
│   ├── compress_zip.py       # 压缩附件
│   ├── captcha_ocr.py        # 验证码 OCR 识别（ddddocr）
│   └── update_summary.py     # 更新漏洞汇总表
└── references/
    ├── captcha-ocr.md        # 验证码 OCR 详细说明
    ├── mcp-connection.md     # MCP 连接原理与经验
    ├── selectors.md          # CSS 选择器参考
    ├── mcp-tools.md          # MCP 工具详细参考
    └── error-handling.md     # 错误处理
```

---

## 十、汇总表

汇总表路径：`/Users/yao/Documents/网安- AI应用开发/监管上报/汇总表/漏洞汇总表.xlsx`

字段说明：

| 字段 | 说明 |
|------|------|
| 漏洞标题 | 漏洞完整名称 |
| 影响厂商 | 受影响厂商名称 |
| 漏洞编号 | DAS-ID |
| 提交人员 | 分析人员姓名 |
| 上报CNVD编号 | CNVD 编号（可为空） |
| 上报CNNVD编号 | CNNVD 编号 |
| 上报日期 | 提交日期 |

---

## 十一、相关链接

- [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [CNNVD 官网](https://www.cnnvd.org.cn/)
