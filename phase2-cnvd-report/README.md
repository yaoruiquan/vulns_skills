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
CNVD OCR 默认使用 `18765`，CNNVD OCR 默认使用 `18766`，两个 skill 同时运行时不要共用同一个 OCR 端口。

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

批量上报：

```
/phase2-cnvd-report /path/to/批次目录
```

批次目录内部包含多个 `DAS-*` 目录时，agent 会按目录名顺序上报 `CNVD-*` 材料。第一条做环境检查；每条完成后记录编号并直接进入下一条；全部完成后统一发送一条钉钉消息。

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
│   ├── browser_snippets.py
│   ├── batch_report.py
│   ├── publish_submission_zip.py
│   ├── captcha_ocr.py
│   └── dingtalk_notify.py
└── references/           # agent 执行参考
    ├── workflow.md
    ├── batch-report.md
    ├── field-mapping.md
    ├── selectors.md
    └── captcha-ocr.md
```

## 上报注意事项

- 进入 `/flaw/create` 后先做登录态检查；出现 Cloudflare 或回到登录页时，先恢复会话，不要继续填表。
- CNVD 下拉框是 Select2 组件，选项无法点击时让 agent 使用 `scripts/browser_snippets.py select2`，不要反复点 a11y 树。
- 验证码识别固定使用 `browser_snippets.py captcha-tab`：把当前 `/common/myCodeNew?t=...` 验证码图片打开到新标签页，不覆盖表单页；识别后回原表单页提交。
- 登录验证码失败后页面可能清空密码框；重试前必须重新确认账号、密码、验证码都已填写。
- 批量模式使用 `scripts/batch_report.py` 管理状态；单条完成后只记录编号，不单独推送钉钉，最后统一通知。
