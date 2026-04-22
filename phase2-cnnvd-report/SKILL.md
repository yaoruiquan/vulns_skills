# phase2-cnnvd-report

通过 Chrome DevTools MCP 控制真实浏览器完成 CNNVD 漏洞上报，并在需要时更新本地漏洞汇总表。

---

## 环境配置

### 1. 初始化

```bash
cd /Users/yao/.claude/skills/phase2-cnnvd-report
./scripts/setup.sh
vim .env
```

`setup.sh` 会创建 `.env`、生成当前路径的 `.mcp.json`，并设置脚本可执行权限。已有 `.env` 不会被覆盖。

### 2. 必填配置

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `CNNVD_USERNAME` | CNNVD 登录用户名 | `user@example.com` |
| `CNNVD_PASSWORD` | CNNVD 登录密码 | `your_password` |
| `VULNS_DATA_DIR` | 漏洞数据根目录，包含 DAS-ID 文件夹 | `/path/to/vulns/date` |
| `SUMMARY_TABLE_PATH` | 漏洞汇总表 xlsx 路径 | `/path/to/漏洞汇总表.xlsx` |
| `COMPANY_NAME` | 技术支持单位名称 | `杭州安恒信息技术股份有限公司` |
| `DEFAULT_CONTACT_PHONE` | 默认联系电话 | `15700082275` |
| `CHROME_DEBUG_PORT` | 本 skill 专用 Chrome 调试端口 | `9333` |
| `CHROME_PROFILE_NAME` | 本 skill 专用 Chrome profile | `cnnvd-report` |
| `DINGTALK_WEBHOOK` | 钉钉机器人 webhook，可选 | 空 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥，可选 | 空 |
| `DINGTALK_ENABLED` | 是否启用钉钉通知 | `true` |
| `DINGTALK_KEYWORD` | 钉钉机器人关键词 | `监管上报` |

`.env.template` 是历史模板，当前新用户优先使用 `.env.example`。

### 3. 浏览器配置

本 skill 默认使用：

- 调试端口：`9333`
- Chrome profile：`cnnvd-report`
- 启动脚本：`scripts/start-chrome-debug.sh`

```bash
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9333/json/version
```

可选模式：

- `isolated`：独立空 profile，默认模式。
- `seed-default`：复制日常 Chrome profile 快照，适合复用登录态。
- `live-default`：直接使用日常 Chrome 用户数据目录，使用前先关闭普通 Chrome。

### 4. MCP 配置

如果从本 skill 目录启动 Claude Code，`.mcp.json` 会作为项目配置使用，server 名为 `chrome-devtools`。

如果从其他项目目录启动 Claude Code，在那个项目目录注册本 skill 的 wrapper：

```bash
claude mcp add chrome-devtools -- /Users/yao/.claude/skills/phase2-cnnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

如果这个 skill 需要和其他浏览器 MCP 在同一个 Claude 项目里同时加载，给本 skill 使用唯一名称注册：

```bash
claude mcp add cnnvd-chrome -- /Users/yao/.claude/skills/phase2-cnnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

本 skill 的端口/profile 独立于其他 skill；只有同一个 Claude 项目里同时注册多个 MCP server 时，server 名才需要唯一。

### 5. 验证

```bash
curl -s http://127.0.0.1:9333/json/version
claude mcp get chrome-devtools
# 如果同项目并发时注册了唯一名称，则改查：
# claude mcp get cnnvd-chrome
```

---

## 工作流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 0 | 检查环境 | 确认 `.env`、Chrome 调试端口和 MCP 可用 |
| 1 | 准备数据 | 用 `extract_vuln_data.py` 从本地 docx 提取 CNNVD 字段 |
| 2 | 导航登录 | 打开 CNNVD、登录、进入通用型漏洞报送 |
| 3 | 基本信息 | 填写漏洞名称、类型、受影响实体和实体描述 |
| 4 | 漏洞详情 | 填写漏洞描述、技术支持单位和联系电话 |
| 5 | 漏洞验证 | 填写验证过程，上传视频和 PoC 附件 |
| 6 | 提交记录 | 提交后获取 `CNNVD-ID`，并按需更新汇总表 |
| 7 | 钉钉通知 | 已配置 `DINGTALK_WEBHOOK` 时推送 `DAS-ID` 和 `CNNVD 编号` |

详细步骤见 `references/setup-guide.md`、`references/data-fields.md` 和 `references/summary-table.md`。

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/setup.sh` | 初始化 `.env`、`.mcp.json` 和脚本权限 |
| `scripts/config.py` | 读取 `.env` 配置 |
| `scripts/start-chrome-debug.sh` | 启动本 skill 专用 Chrome |
| `scripts/chrome-devtools-mcp-wrapper.sh` | MCP wrapper，连接到 `CHROME_DEBUG_PORT` |
| `scripts/extract_vuln_data.py` | 从 docx 提取 CNVD/CNNVD 上报字段 |
| `scripts/compress_zip.py` | 压缩附件目录 |
| `scripts/captcha_ocr.py` | 验证码 OCR |
| `scripts/update_summary.py` | 更新漏洞汇总表 |
| `scripts/dingtalk_notify.py` | 将上报结果推送到钉钉机器人 |

---

## 参考资料

- `references/setup-guide.md`：环境配置详细步骤
- `references/data-fields.md`：数据字段映射
- `references/vuln-type-mapping.md`：漏洞类型级联选择
- `references/captcha-ocr.md`：验证码 OCR
- `references/word-extraction.md`：Word 提取规则
- `references/video-compression.md`：视频压缩
- `references/summary-table.md`：汇总表说明
- `references/mcp-tools.md`：MCP 工具参考
- `references/mcp-connection.md`：MCP 连接经验
- `references/original-SKILL.md`：本次规范化前的原始 `SKILL.md`
- `references/original-README.md`：本次规范化前的原始 `README.md`

---

## 注意事项

- CNNVD 密码明文存储有风险，不要复制或分享 `.env`。
- 钉钉 webhook 属于敏感配置，只能放在 `.env`，不要写进文档或提交到 Git。
- 监管上报类技能统一使用同一个机器人，关键词统一为 `监管上报`。
- 钉钉通知是收尾动作；提交成功后必须把 `DAS-ID` 和 `CNNVD 编号` 写入 `--text`，字面量 `\n` 会被脚本转换为真实换行。
- 受影响实体描述需要基于可追溯资料整理，不要凭空编写。
- 有验证视频时必须上传，并按 `references/video-compression.md` 控制体积。
- 不要把其他 skill 的端口表放进本文件；跨 skill 并发说明放在 README 高级章节。
