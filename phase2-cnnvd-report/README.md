# phase2-cnnvd-report

通过 Chrome DevTools MCP 控制真实浏览器完成 CNNVD 漏洞上报，并在需要时更新本地漏洞汇总表。

## 功能

- 从本地 CNNVD docx 材料提取上报字段
- 打开 CNNVD 页面并进入通用型漏洞报送流程
- 按页面必填项填写，上传验证视频和 PoC 文件
- 提交成功后记录 CNNVD 编号
- 按需更新本地漏洞汇总表
- 可选推送钉钉通知（需配置 webhook）

## 使用流程

### 第一步：安装 Claude Code（或其他 agent 工具）

参见官网文档安装配置。

### 第二步：安装本 skill

一句指令，通过 GitHub 地址安装到 agent 工具：

```
claude skills install <GitHub 地址>
```

如果新用户没有 SSH key，优先使用 HTTPS 地址安装；需要 GitHub/GitLab SSH 或内部服务器上传权限时，先按 [上级 README 的 SSH key 说明](../README.md#没有-ssh-key-怎么办) 配置。

### 第三步：手动配置 .env

```
cd /Users/yao/.claude/skills/phase2-cnnvd-report
cp .env.example .env
vim .env
```

填写 CNNVD 平台账号密码、数据目录、汇总表路径、钉钉配置等（agent 会引导你完成）。

如需上传 CNNVD 原始整包 zip 并推送下载链接，推荐配置 SSH key 免密；临时情况下可只在本机 `.env` 中填写 `REPORT_UPLOAD_PASSWORD`，不要提交到 Git。

### 第四步：启动 agent

```
cd /Users/yao/.claude/skills/phase2-cnnvd-report
claude
```

从固定目录启动可隔离 MCP 配置，确保 Chrome 调试端口（9333）和 profile 不冲突。
验证码识别默认使用 MCP 截图验证码图片元素到 `/tmp/captcha.png`，再执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png` 单次识别。

### 第五步：调用 skill

给 agent 一句指令：

```
安装依赖并初始化环境
```

agent 会自动执行以下操作：

```
# MCP 工具
npm install -g chrome-devtools-mcp@latest

# Python 依赖
pip install websocket-client python-docx openpyxl ddddocr pandas

# 初始化配置
./scripts/setup.sh

# 启动 Chrome 并验证
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9333/json/version
claude mcp get cnnvd-chrome
```

### 第六步：执行上报

```
/phase2-cnnvd-report /path/to/漏洞数据目录/DAS-Txxxxx
```

批量上报：

```
/phase2-cnnvd-report /path/to/批次目录
```

批次目录内部包含多个 `DAS-*` 目录时，agent 会按目录名顺序上报 `CNNVD-*` 材料。第一条做环境检查；每条完成后记录编号并直接进入下一条；全部完成后统一发送一条钉钉消息。

## 目录结构

```
phase2-cnnvd-report/
├── SKILL.md              # agent 执行指令（流程、规则、约束）
├── README.md             # 本文件（用户使用说明）
├── .env.example          # 配置模板，首次使用 cp 为 .env
├── .mcp.json             # MCP 配置（setup.sh 自动生成）
├── scripts/              # 实现脚本
│   ├── setup.sh
│   ├── start-chrome-debug.sh
│   ├── chrome-devtools-mcp-wrapper.sh
│   ├── extract_vuln_data.py
│   ├── prepare_form_context.py
│   ├── batch_report.py
│   ├── publish_submission_zip.py
│   ├── captcha_ocr.py
│   ├── update_summary.py
│   └── dingtalk_notify.py
└── references/           # agent 执行参考
    ├── data-preparation.md
    ├── batch-report.md
    ├── data-fields.md
    ├── dropdown-options.md
    ├── vuln-type-mapping.md
    ├── captcha-ocr.md
    ├── word-extraction.md
    ├── video-compression.md
    └── summary-table.md
```
