# phase2-cnnvd-report-MCP

通过 chrome-devtools-mcp 控制浏览器完成 CNNVD 漏洞上报。

## 概述

本 Skill 用于自动化完成 CNNVD（中国国家信息安全漏洞库）漏洞上报流程。基于 MCP (Model Context Protocol) 协议，通过 chrome-devtools-mcp 控制真实浏览器进行操作。

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

## 与 CNVD 的区别

| 对比项 | CNVD | CNNVD |
|--------|------|-------|
| 平台 | 国家信息安全漏洞共享平台 | 中国国家信息安全漏洞库 |
| 表单入口 | 用户中心 → 立即上报漏洞 | 漏洞管理 → 通用型漏洞报送 |
| 提交者单位 | 从 docx 或参数获取 | 固定：杭州安恒信息技术股份有限公司 |
| 联系电话 | 无固定要求 | 优先用 docx 中分析人员电话，否则 15700082275 |
| 验证录像 | 无要求 | 必须上传，不超过 50MB |
| 受影响实体描述 | 漏洞描述 | 需联网搜索简单描述 |

## 文件结构

```
phase2-cnnvd-report-MCP/
├── SKILL.md                  # 执行流程文档（Agent 入口）
├── README.md                 # 本文件
├── scripts/                  # 可执行脚本
│   ├── extract_vuln_data.py  # 从 docx 提取漏洞数据
│   ├── compress_zip.py       # 压缩附件文件夹
│   └── captcha_ocr.py        # 验证码 OCR 识别
└── references/               # 参考文档
    ├── selectors.md          # CNNVD 表单 CSS 选择器
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

# OCR 验证码识别（可选）
pip install ddddocr
```

## 使用方法

```
/phase2-cnnvd-report-cdp DAS-T105966 --folder "/path/to/CNNVD-folder"
```

### 辅助脚本

```bash
# 提取漏洞数据
python scripts/extract_vuln_data.py DAS-T105966 --platform CNNVD --data-dir "/path/to/data"

# 压缩附件
python scripts/compress_zip.py "/path/to/CNNVD-folder"

# 验证码 OCR 识别
python scripts/captcha_ocr.py /tmp/captcha.png
```

## 执行流程

```
Step 1: 准备数据
    ├─ extract_vuln_data.py 提取漏洞信息
    └─ compress_zip.py 压缩附件

Step 2: 导航表单
    ├─ navigate_page → CNNVD 首页
    ├─ (人工登录并处理验证码)
    ├─ click → 漏洞管理
    └─ click → 通用型漏洞报送

Step 3: 填写表单
    ├─ fill_form → 基本信息
    ├─ fill → 受影响实体描述（联网搜索）
    ├─ fill → 验证过程
    └─ fill_form → 提交者信息

Step 4: 上传附件
    ├─ upload_file → 上传验证录像
    └─ upload_file → 上传其他附件

Step 5: 提交
    ├─ take_screenshot → 截图验证码
    ├─ (人工输入验证码)
    ├─ click → 提交
    └─ evaluate_script → 提取 CNNVD-ID
```

## 核心脚本说明

### extract_vuln_data.py

从 docx 文件提取漏洞数据：

```bash
python scripts/extract_vuln_data.py DAS-T105966 --platform CNNVD
```

输出 JSON：
```json
{
  "das_id": "DAS-T105966",
  "title": "漏洞名称",
  "vuln_type": "命令执行",
  "description": "漏洞描述",
  "affected_product": "影响产品",
  "version": "影响版本",
  "verify_process": "验证过程",
  "reporter": "杭州安恒信息技术股份有限公司",
  "contact_phone": "15700082275"
}
```

## 字段映射

### 漏洞类型

| 中文 | 值 |
|------|---|
| SQL注入 | SQL注入 |
| XSS | XSS |
| 命令执行 | 命令执行 |
| 二进制 | 二进制 |
| 信息泄露 | 信息泄露 |
| 其他 | 其他 |

## 注意事项

1. **人工介入点**：
   - 登录验证码需人工识别
   - 提交验证码需人工识别
   - 受影响实体描述需联网搜索获取
2. **验证录像**：文件大小不超过 50MB，超过需联系提交者重新提供
3. **提交者信息**：固定为杭州安恒信息技术股份有限公司
4. **联系电话**：优先使用 docx 中分析人员电话，否则使用 15700082275
5. **漏洞通报**：漏洞预警漏洞应通报至 CNNVD 漏洞通报，并在《漏洞数据上报》表格中同步更新

## 与其他 Skill 的关系

```
phase1-test (材料整理)
    │
    ▼ 生成 docx 文件
phase2-cnvd-report-cdp (CNVD 上报)
    │
    ▼ 获取 CNVD-ID
phase2-cnnvd-report-cdp (本 Skill - CNNVD 上报)
    │
    ▼ 获取 CNNVD-ID
phase3-archive (归档，待开发)
```

## 相关链接

- [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [CNNVD 官网](https://www.cnnvd.org.cn/)

## 更新日志

- **2026-04-05**: 初始版本，基于 phase2-cnvd-report-cdp 实现
  - 支持完整的 CNNVD 上报流程
  - 适配 CNNVD 表单结构
  - 包含提交者信息固定值规则
  - 支持验证录像上传
