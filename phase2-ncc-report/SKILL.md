---
name: phase2-ncc-report
description: 通过 Chrome DevTools MCP 控制真实浏览器完成 NCC 平台漏洞上报。适用于 https://www.nccsec.cn/company-center/manage-center 的企业中心漏洞材料提交、表单填写、附件上传、验证码/OCR 处理和提交结果记录。
---

# phase2-ncc-report

通过 Chrome DevTools MCP 控制真实浏览器完成 NCC 平台漏洞上报。

---

## 环境配置

### 1. 初始化

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/setup.sh
vim .env
```

`setup.sh` 会创建 `.env`、生成当前路径的 `.mcp.json`，并设置脚本可执行权限。已有 `.env` 不会被覆盖。

### 2. 必填配置

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `NCC_PLATFORM_URL` | NCC 平台管理中心地址 | `https://www.nccsec.cn/company-center/manage-center` |
| `VULN_DATA_DIR` | 漏洞数据父目录，包含 DAS-T* 文件夹 | `/path/to/your/vulnerability/data` |
| `PYTHON_PROJECT_PATH` | Python 项目路径，可选，用于导入共享模块 | `/path/to/your/python/project` |
| `NCC_USERNAME` | NCC 平台登录账号，可选 | 空 |
| `NCC_PASSWORD` | NCC 平台登录密码，可选 | 空 |
| `CHROME_DEBUG_PORT` | 本 skill 专用 Chrome 调试端口 | `9334` |
| `CHROME_PROFILE_NAME` | 本 skill 专用 Chrome profile | `ncc-report` |
| `DINGTALK_WEBHOOK` | 钉钉机器人 webhook，可选 | 空 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥，可选 | 空 |
| `DINGTALK_KEYWORD` | 钉钉机器人关键词，可选 | 空 |
| `DINGTALK_ENABLED` | 是否启用钉钉通知 | `true` |

兼容旧变量 `CLAUDE_CHROME_MCP_PORT` 和 `CLAUDE_CHROME_PROFILE_NAME`，但新配置优先使用 `CHROME_DEBUG_PORT` 和 `CHROME_PROFILE_NAME`。

### 3. 浏览器配置

本 skill 默认使用：

- 调试端口：`9334`
- Chrome profile：`ncc-report`
- 启动脚本：`scripts/start-chrome-debug.sh`

```bash
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9334/json/version
```

可选模式：

- `isolated`：独立空 profile，默认模式。
- `seed-default`：复制日常 Chrome profile 快照，适合复用登录态。
- `live-default`：直接使用日常 Chrome 用户数据目录，使用前先关闭普通 Chrome。

### 4. MCP 配置

如果从本 skill 目录启动 Claude Code，`.mcp.json` 会作为项目配置使用，server 名为 `chrome-devtools`。

如果从其他项目目录启动 Claude Code，在那个项目目录注册本 skill 的 wrapper：

```bash
claude mcp add chrome-devtools -- /Users/yao/.claude/skills/phase2-ncc-report/scripts/chrome-devtools-mcp-wrapper.sh
```

如果这个 skill 需要和其他浏览器 MCP 在同一个 Claude 项目里同时加载，给本 skill 使用唯一名称注册：

```bash
claude mcp add ncc-chrome -- /Users/yao/.claude/skills/phase2-ncc-report/scripts/chrome-devtools-mcp-wrapper.sh
```

本 skill 的端口/profile 独立于其他 skill；只有同一个 Claude 项目里同时注册多个 MCP server 时，server 名才需要唯一。

### 5. 验证

```bash
curl -s http://127.0.0.1:9334/json/version
claude mcp get chrome-devtools
# 如果同项目并发时注册了唯一名称，则改查：
# claude mcp get ncc-chrome
```

---

## 工作流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 0 | 检查环境 | 确认 `.env`、Chrome 调试端口和 MCP 可用 |
| 1 | 准备数据 | 用 `extract_vuln_data.py` 从具体 `DAS` 目录或 `docx` 提取 NCC 字段 |
| 2 | 登录并进入填表页 | 打开 `NCC_PLATFORM_URL`，必要时完成企业登录，再从右上角“提交漏洞”进入表单 |
| 3 | 确认表单 | 用 MCP 快照确认表单字段、下拉值和上传控件 |
| 4 | 填写表单 | 按 `references/field-mapping.md` 填写漏洞信息 |
| 5 | 上传附件 | 第一版优先上传 `upload_zip_path`，如页面支持再补充 `docx/截图/视频` |
| 6 | 提交验证 | 点击提交后，人工完成拖拽拼图验证 |
| 7 | 记录结果 | 读取成功页中的 `NCC-xxxx` 编号 |
| 8 | 可选通知 | 已配置 `DINGTALK_WEBHOOK` 时推送钉钉通知 |

详细步骤见 `references/workflow.md`。

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/setup.sh` | 初始化 `.env`、`.mcp.json` 和脚本权限 |
| `scripts/start-chrome-debug.sh` | 启动本 skill 专用 Chrome |
| `scripts/chrome-devtools-mcp-wrapper.sh` | MCP wrapper，连接到 `CHROME_DEBUG_PORT` |
| `scripts/extract_vuln_data.py` | 从 `DAS` 目录或 `docx` 提取 NCC 上报字段，并识别 zip/截图/视频附件 |
| `scripts/captcha_ocr.py` | 验证码 OCR |
| `scripts/dingtalk_notify.py` | 将上报结果推送到钉钉机器人，支持关键词和链接 |

---

## 参考资料

- `references/setup-guide.md`：环境与依赖说明
- `references/workflow.md`：NCC 平台上报步骤
- `references/field-mapping.md`：字段映射
- `references/selectors.md`：平台表单选择器记录
- `references/captcha-ocr.md`：验证码 OCR
- `references/mcp-connection.md`：MCP 连接经验
- `references/mcp-tools.md`：MCP 工具参考

---

## 注意事项

- NCC 平台账号密码明文存储有风险，不要复制或分享 `.env`。
- 钉钉 webhook 属于敏感配置，只能放在 `.env`，不要写进文档或提交到 Git。
- `.env` 里只保存父目录，不保存具体某一次的 `docx` 路径；实际运行时通过 `--input-path` 或 `--docx-path` 传入。
- 钉钉通知是可选收尾动作；`--text` 中的字面量 `\n` 会被脚本转换为真实换行。
- 第一次开发或平台页面变化时，必须先用 MCP `take_snapshot` 更新 `references/selectors.md`，再执行填表。
- 当前已知登录页没有普通验证码；点击提交后会出现拖拽拼图验证，第一版由人工接管。
- 不要把其他 skill 的端口表放进本文件；跨 skill 并发说明放在 README 高级章节。
