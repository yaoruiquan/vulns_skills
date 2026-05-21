# phase2-ncc-report

通过 Chrome DevTools MCP 控制真实浏览器完成 NCC 平台漏洞上报。平台入口：`https://www.nccsec.cn/company-center/manage-center`。

## 功能

- 从本地漏洞 docx 材料提取上报字段
- 自动识别同目录下的 zip/截图/视频附件
- 打开 NCC 平台企业中心，完成登录、表单填写、验证码识别和提交
- 上传平台要求的附件材料
- 提交成功后记录平台返回的 NCC-xxxx 编号
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
cd /Users/yao/.claude/skills/phase2-ncc-report
cp .env.example .env
vim .env
```

填写 NCC 平台账号密码、漏洞数据父目录、钉钉配置等（agent 会引导你完成）。

如需上传 NCC 附件或推送下载链接，推荐配置 SSH key 免密；临时情况下可只在本机 `.env` 中填写 `REPORT_UPLOAD_PASSWORD`，不要提交到 Git。

### 第四步：启动 agent

```
cd /Users/yao/.claude/skills/phase2-ncc-report
claude --dangerously-skip-permissions
```

从固定目录启动可隔离 MCP 配置，确保 Chrome 调试端口（9334）和 profile 不冲突。

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
curl -s http://127.0.0.1:9334/json/version
claude mcp get ncc-chrome
```

### 第六步：执行上报

```
/phase2-ncc-report /path/to/漏洞数据目录/DAS-Txxxxx
```

## 目录结构

```
phase2-ncc-report/
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
│   ├── captcha_ocr.py
│   └── dingtalk_notify.py
└── references/           # agent 执行参考
    ├── workflow.md
    ├── field-mapping.md
    ├── selectors.md
    ├── captcha-ocr.md
    ├── mcp-connection.md
    └── mcp-tools.md
```
