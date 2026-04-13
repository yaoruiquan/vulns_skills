# phase2-cnvd-report-cdp

通过 chrome-devtools-mcp 控制浏览器完成 CNVD 漏洞上报。

## 概述

本 Skill 用于自动化完成 CNVD（国家信息安全漏洞共享平台）漏洞上报流程。基于 MCP (Model Context Protocol) 协议，通过 chrome-devtools-mcp 控制真实浏览器进行操作。

## 技术架构

```
┌─────────────────┐   MCP Protocol   ┌─────────────────┐
│  Claude Code    │ ───────────────→ │ chrome-devtools │
│  Agent          │                  │ -mcp (Puppeteer)│
└─────────────────┘ ←─────────────── └─────────────────┘
                      Browser Control    │
                                        ▼
                                 ┌─────────────────┐
                                 │  Chrome Browser │
                                 └─────────────────┘
```

## 文件结构

```
phase2-cnvd-report-cdp/
├── SKILL.md                  # 执行流程文档（Agent 入口）
├── README.md                 # 本文件
├── scripts/                  # 可执行脚本
│   ├── extract_vuln_data.py  # 从 docx 提取漏洞数据
│   ├── compress_zip.py       # 压缩附件文件夹
│   └── captcha_ocr.py        # 验证码 OCR 识别
└── references/               # 参考文档
    ├── selectors.md          # CNVD 表单 CSS 选择器
    ├── mcp-tools.md          # MCP 工具详细参考
    └── error-handling.md     # 错误处理指南
```

## 前提条件

### 1. 安装 chrome-devtools-mcp

```bash
npm install -g chrome-devtools-mcp@latest
```

### 2. 配置 MCP

在项目根目录 `.mcp.json` 中添加：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

### 3. 依赖安装

```bash
# Python 依赖（用于数据提取脚本）
pip install websocket-client python-docx openpyxl

# OCR 验证码识别
pip install ddddocr
```

## 使用方法

```
/phase2-cnvd-report-cdp DAS-T105966 --folder "/path/to/CNVD-folder"
```

### 辅助脚本

```bash
# 提取漏洞数据
python scripts/extract_vuln_data.py DAS-T105966 --platform CNVD --data-dir "/path/to/data"

# 压缩附件
python scripts/compress_zip.py "/path/to/CNVD-folder"

# 验证码 OCR 识别
python scripts/captcha_ocr.py /tmp/captcha.png
```

## 执行流程

```
Step 1: 准备数据
    ├─ extract_vuln_data.py 提取漏洞信息
    └─ compress_zip.py 压缩附件

Step 2: 导航表单
    ├─ navigate_page → CNVD 首页
    ├─ OCR 自动识别登录验证码
    ├─ click → 用户中心
    └─ click → 立即漏洞上报

Step 3: 填写表单
    ├─ fill → 切换表单类型
    ├─ fill_form → 基本信息
    ├─ fill_form → 厂商信息
    └─ fill_form → 漏洞详情

Step 4: 上传附件
    └─ upload_file → 上传 zip

Step 5: 提交
    ├─ take_screenshot → 截图验证码
    ├─ captcha_ocr.py → OCR 识别
    ├─ fill → 填入验证码
    ├─ click → 提交
    └─ evaluate_script → 提取 CNVD-ID
```

## 核心脚本说明

### extract_vuln_data.py

从 docx 文件提取漏洞数据：

```bash
python scripts/extract_vuln_data.py DAS-T105966 --platform CNVD
```

输出 JSON：
```json
{
  "das_id": "DAS-T105966",
  "title": "漏洞名称",
  "vuln_type": "binaryVulnerability",
  "description": "漏洞描述",
  "unit_name": "厂商",
  "affected_product": "影响产品",
  "version": "影响版本"
}
```

## 字段映射

### 漏洞类型

| 中文 | 值 |
|------|---|
| SQL注入 | sqlInjectionVulnerability |
| XSS | xssVulnerability |
| 命令执行 | remoteCommandExecution |
| 二进制 | binaryVulnerability |
| 信息泄露 | informationLeakage |
| 其他 | other |

### 影响对象类型

| 中文 | 值 |
|------|---|
| 操作系统 | 27 |
| 应用程序 | 28 |
| WEB应用 | 29 |
| 数据库 | 30 |

## 注意事项

1. **验证码处理**：使用 ddddocr 自动识别验证码，无需人工介入
   - 登录验证码：中文词语（如"读书"），识别率约 80%
   - 提交验证码：字母数字组合（如"db3D"），识别率约 50-70%
   - 如识别失败，重新截图并重试即可
2. **表单类型切换**：CNVD 有两种表单模式，必须先切换到"通用型漏洞"
3. **文件上传**：使用 MCP 的 `upload_file` 工具上传 zip 附件

## 参考文档

| 文档 | 说明 |
|------|------|
| [captcha-ocr.md](references/captcha-ocr.md) | 验证码 OCR 自动识别详细说明 |
| [mcp-connection.md](references/mcp-connection.md) | chrome-devtools MCP 连接原理与经验 |
| [selectors.md](references/selectors.md) | CNVD 表单 CSS 选择器 |
| [mcp-tools.md](references/mcp-tools.md) | MCP 工具详细参考 |
| [error-handling.md](references/error-handling.md) | 错误处理指南 |

---

## 与其他 Skill 的关系

```
phase1-test (材料整理)
    │
    ▼ 生成 docx 文件
phase2-cnvd-report-cdp (本 Skill)
    │
    ▼ 获取 CNVD-ID
phase3-archive (归档，待开发)
```

## 相关链接

- [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [CNVD 官网](https://www.cnvd.org.cn/)

## 更新日志

- **2026-04-03**: 添加验证码 OCR 自动识别
  - 使用 ddddocr 库识别验证码
  - 登录验证码（中文词语）识别率约 80%
  - 提交验证码（字母数字）识别率约 50-70%
  - 实现全自动化流程，无需人工介入
- **2026-04-03**: chrome-devtools MCP 连接成功
  - 解决警告信息干扰 MCP 协议握手问题
  - 添加 wrapper 脚本过滤 stderr 警告
  - 验证可正常访问 CNVD 等有防火墙保护的网站
- **2026-04-02**: 初始版本，基于 chrome-devtools-mcp 实现
  - 支持完整的 CNVD 上报流程
  - 提供数据提取和附件压缩脚本
  - 包含完整的参考文档