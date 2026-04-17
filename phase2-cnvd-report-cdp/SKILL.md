# phase2-cnvd-report-MCP

通过 chrome-devtools MCP 控制浏览器完成 CNVD 漏洞上报。

> MCP 工具详细说明参见 [references/mcp-tools.md](references/mcp-tools.md)

---

## 流程概览

| 步骤 | 操作 | 说明 |
|------|------|------|
| 0 | 检查环境 | 确认 Chrome 调试端口和 MCP 连接 |
| 1 | 准备数据 | 提取漏洞数据、压缩附件 |
| 2 | 导航表单 | 打开 CNVD、登录、进入上报表单 |
| 3 | 填写表单 | 切换表单类型、填写厂商和漏洞信息 |
| 4 | 上传附件 | 上传 zip 文件 |
| 4.5 | 验证完整性 | 检查所有字段已填写 |
| 5 | 验证码提交 | OCR 识别验证码并提交 |

---

## 快速开始

### 1. 启动 Chrome

```bash
/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/start-chrome-debug.sh
```

**如果 CNVD 返回 Cloudflare 521**：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

### 2. 检查环境

```bash
curl -s http://localhost:9332/json/version
```

```
MCP: list_pages
```

### 3. 提取数据

```bash
python scripts/extract_vuln_data.py <DAS-ID> --platform CNVD --data-dir "<数据目录>"
```

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