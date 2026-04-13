# wechat-mp-publisher

通过 chrome-devtools MCP 控制浏览器将漏洞预警 .md 文件内容发布到微信公众号。

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
      "command": "chrome-devtools-mcp",
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
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-wechat
```

---

## 二、执行流程概览

```
Step 0: 检查环境 → Step 1: 准备数据 → Step 2: 导航编辑页 → Step 3: 填写内容 → Step 4: 验证结果
```

---

## 三、详细步骤

### Step 0: 检查环境状态

**第一步必须先检查调试端口和 MCP 连接状态，确保环境就绪后再进行后续操作。**

#### 0.1 检查 Chrome 调试端口

```bash
curl -s http://localhost:9222/json/version
```

**预期输出**：
```json
{
  "Browser": "Chrome/xxx.x.xxxx.xx",
  "Protocol-Version": "1.3",
  "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/xxx"
}
```

**如果无输出或连接失败**：

```bash
# 启动 Chrome 调试模式
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-wechat &
```

#### 0.2 检查 MCP 连接状态

```
MCP: list_pages
```

**预期输出**：返回当前浏览器打开的页面列表。

#### 0.3 环境检查清单

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|----------|
| Chrome 调试端口 | `curl localhost:9222/json/version` | 返回 JSON |
| MCP 连接 | `list_pages` | 返回页面列表 |
| 微信公众号登录 | 用户手动登录 | 已登录 |

**只有当以上检查全部通过后，才继续执行后续步骤。**

---

### Step 1: 准备数据

#### 1.1 提取漏洞预警内容

从 .md 文件提取内容：

```bash
python3 scripts/extract_md_content.py "<md文件路径>"
```

**提取的字段**：

| 字段 | 来源 | 用途 |
|------|------|------|
| 标题 | 文件名或表格第一行 | 文章标题 |
| 导语 | 开头引用块内容 | 正文开头 |
| 漏洞信息表格 | `<table>` 元素 | 正文表格 |
| 漏洞描述 | "## 漏洞描述" 章节 | 正文内容 |
| 攻击向量 | "## 攻击向量" 章节 | 正文内容（可选） |
| 修复方案 | "## 修复方案" 章节 | 正文内容 |
| 参考资料 | "## 参考资料" 章节 | 正文底部 |

**输出示例**：
```json
{
  "title": "axios npm包存在供应链恶意代码注入漏洞预警",
  "intro": "近日安恒信息CERT监测到npm官方仓库中的axios包被植入恶意代码...",
  "vuln_table_html": "<table>...</table>",
  "description": "axios@>=1.14.1 和 >=0.30.4 版本中被植入恶意代码...",
  "fix_official": "官方当前未发布修复版本...",
  "fix_temp": "限制npm install的网络访问...",
  "references": "1. GitHub Advisory Database..."
}
```

---

### Step 2: 导航到微信公众号编辑页面

#### 2.1 打开微信公众号首页

```
MCP: navigate_page
  type: "url"
  url: "https://mp.weixin.qq.com/"
```

#### 2.2 检查登录状态

```
MCP: take_snapshot
```

**如果显示登录页面**：
- 提示用户手动扫码登录
- 等待用户确认登录成功后继续

#### 2.3 导航到新建图文页面

登录成功后：

```
MCP: take_snapshot

# 点击"新建图文"或类似按钮
MCP: click
  uid: "<新建图文按钮的 uid>"
```

---

### Step 3: 填写内容

微信公众号编辑器使用 UEditor，需要通过 JavaScript 操作。

#### 3.1 填写标题

```
MCP: take_snapshot
MCP: fill
  uid: "<标题输入框的 uid>"
  value: "<title>"
```

#### 3.2 填写正文（通过 JavaScript）

**获取编辑器 iframe 并设置内容**：

```
MCP: take_snapshot

# 定位编辑器区域
MCP: evaluate_script
  function: |
    () => {
      // 查找 UEditor iframe
      const iframe = document.querySelector('#edui1_iframeholder iframe') ||
                     document.querySelector('.edui-editor-iframeholder iframe');
      if (!iframe) return { success: false, error: '未找到编辑器 iframe' };

      // 获取 iframe 内的文档
      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
      const body = iframeDoc.body;

      // 清空现有内容
      body.innerHTML = '';

      // 设置正文内容（Markdown 转 HTML）
      const content = `<intro_html>
        <h2>一、漏洞信息</h2>
        <vuln_table_html>
        <h2>二、漏洞描述</h2>
        <description_html>
        <h2>三、修复方案</h2>
        <h3>官方修复方案</h3>
        <fix_official_html>
        <h3>临时缓解方案</h3>
        <fix_temp_html>
        <h2>四、参考资料</h2>
        <references_html>`;

      body.innerHTML = content;

      return { success: true };
    }
```

#### 3.3 备选方案：分段填入

如果直接设置 innerHTML 失败，使用分段插入：

```
MCP: evaluate_script
  function: |
    () => {
      const iframe = document.querySelector('#edui1_iframeholder iframe');
      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

      // 使用 UEditor API（如果可用）
      if (typeof UE !== 'undefined' && UE.getEditor) {
        const editor = UE.getEditor('editor');
        editor.setContent('<content_html>');
        return { success: true, method: 'UEditor API' };
      }

      // 直接操作 iframe body
      iframeDoc.body.innerHTML = '<content_html>';
      return { success: true, method: 'iframe innerHTML' };
    }
```

---

### Step 4: 验证结果

#### 4.1 截图确认

```
MCP: take_screenshot
  filePath: "/tmp/wechat_preview.png"
  fullPage: true
```

#### 4.2 检查内容完整性

```
MCP: evaluate_script
  function: |
    () => {
      const iframe = document.querySelector('#edui1_iframeholder iframe');
      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;

      return {
        title: document.querySelector('#title')?.value || '',
        contentLength: iframeDoc.body.innerText.length,
        hasTable: iframeDoc.body.querySelector('table') !== null,
        hasHeaders: iframeDoc.body.querySelectorAll('h2').length > 0
      };
    }
```

---

## 四、微信公众号页面元素定位

### 4.1 主要元素选择器

| 元素 | 选择器 | 说明 |
|------|--------|------|
| 标题输入框 | `input[placeholder*="标题"]` 或 `#title` | 文章标题 |
| 正文编辑器 | `#edui1_iframeholder iframe` | UEditor iframe |
| 保存按钮 | `.weui-desktop-btn__primary` 或包含"保存"文字 | 保存草稿 |
| 发布按钮 | 包含"发布"文字的按钮 | 发布文章 |

### 4.2 UEditor API 参考

```javascript
// 获取编辑器实例
const editor = UE.getEditor('editor');

// 设置完整内容
editor.setContent('<html>');

// 追加内容
editor.execCommand('insertHtml', '<p>新段落</p>');

// 获取内容
const html = editor.getContent();
const text = editor.getContentTxt();
```

---

## 五、内容转换规则

### 5.1 Markdown 转 HTML

| Markdown 元素 | HTML 输出 |
|--------------|-----------|
| `# 标题` | `<h1>标题</h1>` |
| `## 标题` | `<h2>标题</h2>` |
| `**加粗**` | `<strong>加粗</strong>` |
| `> 引用` | `<blockquote>引用</blockquote>` |
| `<table>` | 保持原样 |
| 代码块 | `<pre><code>...</code></pre>` |
| 链接 `[text](url)` | `<a href="url">text</a>` |

### 5.2 图片处理

- 图片路径转换：本地路径 → 需手动上传或使用网络图片
- Logo 图片：保留占位，提示用户手动上传封面

---

## 六、错误处理

| 错误 | 处理方式 |
|------|----------|
| 未登录微信公众号 | 提示用户扫码登录 |
| 找不到编辑器 iframe | 刷新页面，重新定位 |
| JavaScript 执行失败 | 使用 fill/type 工具模拟输入 |
| 内容过长被截断 | 分段填入 |
| 图片上传失败 | 提示用户手动上传 |

---

## 七、文件结构

```
wechat-mp-publisher/
├── SKILL.md                   # 本文件
├── scripts/
│   └── extract_md_content.py  # 提取 .md 文件内容
└── references/
    └── wechat-editor.md       # 微信公众号编辑器详细参考
```

---

## 八、相关链接

- [微信公众号后台](https://mp.weixin.qq.com/)
- [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)