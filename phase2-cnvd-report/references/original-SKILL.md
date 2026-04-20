# phase2-cnvd-report

通过 chrome-devtools MCP 控制浏览器完成 CNVD 漏洞上报。

> MCP 工具详细说明参见 [references/mcp-tools.md](references/mcp-tools.md)

---

## 流程概览

| 步骤 | 操作 | 说明 |
|------|------|------|
| 0 | 检查环境 | 确认 Chrome 调试端口和 MCP 连接 |
| 1 | 准备数据 | 提取漏洞数据、按 CNVD 要求准备附件 |
| 2 | 导航表单 | 打开 CNVD、登录、进入上报表单 |
| 3 | 填写表单 | 切换表单类型、填写厂商和漏洞信息 |
| 4 | 上传附件 | 上传 zip 文件 |
| 4.5 | 验证完整性 | 检查所有字段已填写 |
| 5 | 验证码提交 | OCR 识别验证码并提交 |

---

## 快速开始

### 0. 环境配置

首次使用先复制配置模板并填写实际路径：

```bash
cd /Users/yao/.claude/skills/phase2-cnvd-report
cp .env.example .env
vim .env
```

关键环境变量：

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `VULN_DATA_DIR` | 漏洞数据根目录，包含 DAS-T* 文件夹 | `/path/to/your/vulnerability/data` |
| `PYTHON_PROJECT_PATH` | Python 项目路径，可选 | `/path/to/your/python/project` |
| `CLAUDE_CHROME_MCP_PORT` | Chrome 调试端口 | `9332` |
| `CLAUDE_CHROME_PROFILE_NAME` | Chrome profile 名称 | `cnvd-report` |
| `CNVD_EMAIL` | CNVD 登录邮箱，可选 | 空 |
| `CNVD_PASSWORD` | CNVD 登录密码，可选 | 空 |

CNVD 密码明文存储有风险，优先使用 `seed-default` 复用 Chrome 登录态。

### 0.5. MCP 配置

如果从本 skill 目录启动 Claude Code，`.mcp.json` 会作为项目配置使用，server 名为 `chrome-devtools`。

如果从其他项目目录启动 Claude Code，需要在那个项目目录注册 wrapper：

```bash
claude mcp add chrome-devtools -- /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

如果这个 skill 需要和其他浏览器 MCP 在同一个 Claude 项目里同时加载，给本 skill 使用唯一名称注册：

```bash
claude mcp add cnvd-chrome -- /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

本 skill 默认使用 `9332` 端口和 `cnvd-report` profile。端口/profile 独立于其他 skill；只有在同一个 Claude 项目里同时注册多个 MCP server 时，server 名才需要唯一。

### 1. 启动 Chrome

```bash
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh
```

**如果 CNVD 返回 Cloudflare 521**：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh seed-default
```

### 2. 检查环境

```bash
curl -s http://localhost:9332/json/version
claude mcp get chrome-devtools
# 如果同项目并发时注册为 cnvd-chrome，则改用：
# claude mcp get cnvd-chrome
```

```
MCP: list_pages
```

### 3. 提取数据

```bash
python scripts/extract_vuln_data.py <DAS-ID> --platform CNVD --data-dir "<数据目录>"
```

附件压缩包按 CNVD 页面上传要求准备；当前 skill 不包含独立的 `compress_zip.py`。

### 4. 填表提交流程

详见 [references/workflow.md](references/workflow.md)

---

## 详细文档

| 文档 | 内容 |
|------|------|
| [setup-guide.md](references/setup-guide.md) | 前提条件、MCP 配置、环境检查 |
| [workflow.md](references/workflow.md) | 详细步骤（导航、填表、上传、提交） |
| [field-mapping.md](references/field-mapping.md) | 字段映射表、漏洞类型、影响对象类型 |
| [captcha-ocr.md](references/captcha-ocr.md) | 验证码 OCR 自动识别 |
| [selectors.md](references/selectors.md) | CNVD 表单 CSS 选择器参考 |
| [mcp-connection.md](references/mcp-connection.md) | MCP 连接原理与经验 |
| [error-handling.md](references/error-handling.md) | 错误处理指南 |

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/start-chrome-debug.sh` | 启动 skill 专用 Chrome（端口 9332） |
| `scripts/chrome-devtools-mcp-wrapper.sh` | MCP wrapper（连接到 9332） |
| `scripts/extract_vuln_data.py` | 提取漏洞数据 |
| `scripts/captcha_ocr.py` | 验证码 OCR 识别 |

---

## 相关链接

- [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [CNVD 官网](https://www.cnvd.org.cn/)
