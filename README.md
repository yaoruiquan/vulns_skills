# 漏洞管理自动化工作流 Skills 集合

Claude Code Skills 集合，用于自动化处理漏洞管理相关工作流程。

## 包含 Skills

| Skill | 功能 | 调试端口 |
|-------|------|----------|
| **cnvd-weekly-db-update** | CNVD 每周 XML 数据库更新 | - |
| **msrc-vulnerability-report** | MSRC 微软安全更新漏洞报告生成 | - |
| **phase1-material-processor** | 监管上报前材料整理（重命名 + docx 模板） | - |
| **phase2-cnnvd-report-cdp** | CNNVD 漏洞上报（浏览器自动化） | 9333 |
| **phase2-cnvd-report-cdp** | CNVD 漏洞上报（浏览器自动化） | 9332 |
| **vulnerability-alert-processor** | 漏洞预警材料整理（Word/Markdown 报告） | 9331 |
| **wechat-mp-publisher** | 微信公众号文章发布（浏览器自动化） | - |

## 工作流程关系

```
┌─────────────────────────────────────────────────────────────┐
│                    漏洞管理完整流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐                                  │
│  │ cnvd-weekly-db-update │ ← CNVD XML 数据入库              │
│  └──────────────────────┘                                  │
│                                                             │
│  ┌──────────────────────┐                                  │
│  │ msrc-vulnerability-report │ ← MSRC 报告生成               │
│  └──────────────────────┘                                  │
│                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │ phase1-test          │ →  │ phase2-cnvd-report   │      │
│  │ (材料整理)            │    │ -cdp (CNVD上报)      │      │
│  └──────────────────────┘    └──────────────────────┘      │
│                                      ↓                      │
│                              ┌──────────────────────┐      │
│                              │ phase2-cnnvd-report  │      │
│                              │ -cdp (CNNVD上报)      │      │
│                              └──────────────────────┘      │
│                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │ vulnerability-alert  │ →  │ wechat-mp-publisher  │      │
│  │ -processor (预警整理) │    │ (公众号发布)          │      │
│  └──────────────────────┘    └──────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 前置依赖

```bash
# MCP 工具
npm install -g chrome-devtools-mcp@latest

# Python 依赖
pip install websocket-client python-docx openpyxl ddddocr pandas
```

### 使用方式

在 Claude Code 中调用：

```bash
/cnvd-weekly-db-update
/msrc-vulnerability-report "/path/to/material-package"
/phase1-test "/path/to/漏洞批次文件夹"
/phase2-cnvd-report-cdp
/phase2-cnnvd-report-cdp
/vulnerability-alert-processor
/wechat-mp-publisher
```

## 浏览器自动化 Skills

以下 skills 使用 Chrome DevTools MCP 控制真实浏览器：

| Skill | 调试端口 | Profile 目录 |
|-------|----------|--------------|
| vulnerability-alert-processor | 9331 | `~/.claude/chrome-profiles/vuln-alert` |
| phase2-cnvd-report-cdp | 9332 | `~/.claude/chrome-profiles/cnvd-report` |
| phase2-cnnvd-report-cdp | 9333 | `~/.claude/chrome-profiles/cnnvd-report` |

**启动浏览器**（在各 skill 目录下）：

```bash
./scripts/start-chrome-debug.sh
```

**检查端口**：

```bash
curl -s http://127.0.0.1:9331/json/version
curl -s http://127.0.0.1:9332/json/version
curl -s http://127.0.0.1:9333/json/version
```

## 各 Skill 详细说明

### cnvd-weekly-db-update

自动化处理 CNVD 每周发布的 XML 漏洞数据更新：
- SSH 上传 XML 文件到服务器
- Docker 容器内执行解析入库
- 文件归档管理

详见 [cnvd-weekly-db-update/README.md](cnvd-weekly-db-update/README.md)

### msrc-vulnerability-report

从微软安全更新材料包生成漏洞预警 Word/PDF 报告：
- 解析 CVRF JSON/CSV 数据
- 调用恒脑 AI 翻译漏洞标题
- 生成格式规范的 Word/PDF

详见 [msrc-vulnerability-report/README.md](msrc-vulnerability-report/README.md)

### phase1-material-processor

监管上报前材料整理：
- 统计漏洞数量并重命名文件夹
- 批量修改 docx 模板（添加前缀后缀、填写提交人员）

详见 [phase1-material-processor/SKILL.md](phase1-material-processor/SKILL.md)

### phase2-cnvd-report-cdp

通过浏览器自动化完成 CNVD 漏洞上报：
- 提取 docx 材料字段
- 填写 CNVD 表单
- 处理验证码、上传附件
- 记录上报结果

详见 [phase2-cnvd-report-cdp/README.md](phase2-cnvd-report-cdp/README.md)

### phase2-cnnvd-report-cdp

通过浏览器自动化完成 CNNVD 漏洞上报：
- 提取 docx 材料字段
- 填写 CNNVD 表单
- 上传验证录像
- 更新本地汇总表

详见 [phase2-cnnvd-report-cdp/README.md](phase2-cnnvd-report-cdp/README.md)

### vulnerability-alert-processor

漏洞预警材料整理：
- 收集漏洞资料、整理字段
- 生成内容一致的 Word/Markdown 报告
- 通过浏览器访问预警平台

详见 [vulnerability-alert-processor/README.md](vulnerability-alert-processor/README.md)

### wechat-mp-publisher

微信公众号文章发布：
- 解析 Markdown 文章结构
- 渲染微信兼容 HTML
- 浏览器自动化填写草稿

详见 [wechat-mp-publisher/SKILL.md](wechat-mp-publisher/SKILL.md)

## 目录结构

```
vulns_skills/
├── README.md                          # 本文件
├── .gitignore                         # 白名单模式
├── cnvd-weekly-db-update/
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/
│   └── references/
├── msrc-vulnerability-report/
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/
│   ├── assets/
│   └── requirements.txt
├── phase1-material-processor/
│   ├── SKILL.md
│   └── scripts/
├── phase2-cnnvd-report-cdp/
│   ├── SKILL.md
│   ├── README.md
│   ├── .mcp.json
│   ├── .claude/settings.json
│   ├── scripts/
│   └── references/
├── phase2-cnvd-report-cdp/
│   ├── SKILL.md
│   ├── README.md
│   ├── .mcp.json
│   ├── .claude/settings.json
│   ├── scripts/
│   └── references/
├── vulnerability-alert-processor/
│   ├── SKILL.md
│   ├── README.md
│   ├── .env.example
│   ├── .mcp.json
│   ├── .claude/settings.json
│   ├── scripts/
│   ├── assets/
│   └── references/
└── wechat-mp-publisher/
    ├── SKILL.md
    ├── scripts/
    └── references/
```

## 维护者

柘狐（ZheFox）

## 相关链接

- [CNVD 官网](https://www.cnvd.org.cn/)
- [CNNVD 官网](https://www.cnnvd.org.cn/)
- [Microsoft Security Response Center](https://msrc.microsoft.com/)
