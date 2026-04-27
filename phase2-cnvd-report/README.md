# phase2-cnvd-report

通过 Chrome DevTools MCP 控制真实浏览器完成 CNVD 漏洞上报。

## 功能

- 从本地漏洞 docx 材料提取上报字段
- 自动识别附件（zip/截图/视频），预生成表单上下文
- 打开 CNVD 页面，自动登录、填写表单、识别验证码并提交
- 上传原始整包 zip 附件
- 提交成功后记录 CNVD 编号
- 可选推送钉钉通知（需配置 webhook）

## 使用流程

### 第一步：安装 Claude Code（或其他 agent 工具）

参见官网文档安装配置。

### 第二步：安装本 skill

一句指令，通过 GitHub 地址安装到 agent 工具：

```
claude skills install <GitHub 地址>
```

### 第三步：手动配置 .env

```
cd /Users/yao/.claude/skills/phase2-cnvd-report
cp .env.example .env
vim .env
```

填写平台账号、密码、路径等配置（agent 会引导你完成）。

### 第四步：启动 agent

```
cd /Users/yao/.claude/skills/phase2-cnvd-report
claude
```

从固定目录启动可隔离 MCP 配置，确保 Chrome 调试端口和 profile 不冲突。

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
curl -s http://127.0.0.1:9332/json/version
claude mcp get cnvd-chrome
```

### 第六步：执行上报

```
/phase2-cnvd-report /path/to/漏洞数据目录/DAS-Txxxxx
```

## 目录结构

```
phase2-cnvd-report/
├── SKILL.md              # agent 执行指令（流程、规则、约束）
├── README.md             # 本文件（用户使用说明）
├── .env.example          # 配置模板，首次使用 cp 为 .env
├── .mcp.json             # MCP 配置（setup.sh 自动生成）
├── scripts/              # 实现脚本
│   ├── setup.sh
│   ├── start-chrome-debug.sh
│   ├── chrome-devtools-mcp-wrapper.sh
│   ├── prepare_form_context.py
│   ├── publish_submission_zip.py
│   ├── captcha_ocr.py
│   └── dingtalk_notify.py
└── references/           # agent 执行参考
    ├── workflow.md
    ├── field-mapping.md
    ├── selectors.md
    └── captcha-ocr.md
```
