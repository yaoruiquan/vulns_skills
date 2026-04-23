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
| `REPORT_UPLOAD_REMOTE_DIR` | CNNVD zip 远端存放目录 | `/root/msrc-report-downloads/cnnvd-submissions` |
| `REPORT_DOWNLOAD_BASE_URL` | CNNVD zip 下载 URL 根路径 | `http://10.50.10.29:8080/download/msrc/cnnvd-submissions` |

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

如果从本 skill 目录启动 Claude Code，`.mcp.json` 会作为项目配置使用，server 名为 `cnnvd-chrome`。

如果从其他项目目录启动 Claude Code，在那个项目目录注册本 skill 的 wrapper：

```bash
claude mcp add cnnvd-chrome -- /Users/yao/.claude/skills/phase2-cnnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

本 skill 的端口/profile/MCP server 名都独立于其他浏览器型 skill；不要把它注册成通用的 `chrome-devtools`，否则会覆盖或误连到其他 wrapper。

### 5. 验证

```bash
curl -s http://127.0.0.1:9333/json/version
claude mcp get cnnvd-chrome
```

---

## 工作流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 0 | 检查环境 | 确认 `.env`、Chrome 调试端口和 MCP 可用 |
| 1 | 准备数据 | 运行 `prepare_form_context.py` 生成 `form_context.json`；Word 提取、受影响实体描述、验证过程、附件和下拉值在此阶段定稿 |
| 2 | 导航登录 | 打开 CNNVD、登录、进入通用型漏洞报送 |
| 3 | 基本信息 | 只处理必填项；必填下拉框为漏洞类型、漏洞自评级、受影响实体分类 |
| 4 | 漏洞详情 | 只填写漏洞描述或简介、技术支持、技术支持联系电话 |
| 5 | 漏洞验证 | 填写单段验证过程，上传 `verification_video_path` 和 `poc_file_path` |
| 6 | 提交记录 | 提交后获取 `CNNVD-ID`，并按需更新汇总表 |
| 7 | 钉钉通知 | 已配置 `DINGTALK_WEBHOOK` 时上传单漏洞 CNNVD zip，并推送漏洞名称、`DAS-ID`、`CNNVD 编号` 和下载链接 |

详细步骤见 `references/data-preparation.md`、`references/data-fields.md`、`references/dropdown-options.md` 和 `references/summary-table.md`。

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/setup.sh` | 初始化 `.env`、`.mcp.json` 和脚本权限 |
| `scripts/config.py` | 读取 `.env` 配置 |
| `scripts/start-chrome-debug.sh` | 启动本 skill 专用 Chrome |
| `scripts/chrome-devtools-mcp-wrapper.sh` | MCP wrapper，连接到 `CHROME_DEBUG_PORT` |
| `scripts/extract_vuln_data.py` | 从 docx 提取 CNVD/CNNVD 上报字段 |
| `scripts/prepare_form_context.py` | 生成浏览器阶段唯一读取的 `form_context.json` |
| `scripts/publish_submission_zip.py` | 上传单个 CNNVD 原始整包 zip，并推送钉钉下载链接 |
| `scripts/compress_zip.py` | 可选历史工具；当前最小必填流程不依赖它 |
| `scripts/captcha_ocr.py` | 验证码 OCR |
| `scripts/update_summary.py` | 更新漏洞汇总表 |
| `scripts/dingtalk_notify.py` | 将上报结果推送到钉钉机器人 |

---

## 参考资料

- `references/data-preparation.md`：数据准备和完整 FormContext 规范
- `references/data-fields.md`：数据字段映射和最小必填填写规则
- `references/dropdown-options.md`：CNNVD 必填下拉框速查表
- `references/vuln-type-mapping.md`：漏洞类型级联选择
- `references/captcha-ocr.md`：验证码 OCR
- `references/word-extraction.md`：Word 提取规则
- `references/video-compression.md`：视频压缩
- `references/summary-table.md`：汇总表说明

---

## 注意事项

- CNNVD 密码明文存储有风险，不要复制或分享 `.env`。
- 钉钉 webhook 属于敏感配置，只能放在 `.env`，不要写进文档或提交到 Git。
- 监管上报类技能统一使用同一个机器人，关键词统一为 `监管上报`。
- 钉钉通知是收尾动作；提交成功后优先使用 `publish_submission_zip.py <form_context.json> --platform-id <CNNVD-ID> --notify`，消息必须包含漏洞名称、`DAS-ID`、`CNNVD 编号` 和附件下载链接。
- `publish_submission_zip.py` 只上传单个漏洞的 CNNVD 原始整包 zip，不上传整个批次目录，也不重新压缩。
- CNNVD 表单只填写带 danger/红色必填标记的字段；非必填字段不要为了补充信息而反复操作下拉框。
- Step 1 必须生成 `form_context.json`；浏览器阶段只读这个文件，不再运行 `extract_vuln_data.py`。
- `prepare_form_context.py` 负责整理完整 `FormContext`，包括 websearch 得到的受影响实体描述和总结压缩后的漏洞验证过程。
- 第 3 页漏洞验证阶段禁止再跑 Word 提取脚本；只填 `FormContext.verification`。如果为空，回到 Step 1 补齐。
- 第 1 页只操作三个必填下拉框：漏洞类型、漏洞自评级、受影响实体分类；遇到选项判断先查 `references/dropdown-options.md`。
- 级联下拉必须点击最终叶子选项前面的圆圈/单选按钮完成选择，不要只点击文字，也不要按 Escape 关闭。
- 漏洞描述或简介使用 Word 的“漏洞简介”，不要带 `经恒脑AI代码审计智能体分析：` 前缀。
- `漏洞描述或简介` 最多 255 字，只填 `description`，不要改用 `description_full`。
- 验证过程需要根据 `verification_source` 自行总结压缩成一段文字，不插入图片，不直接粘贴 `verification_source` 或 Word 超长原文。
- 有验证视频和 PoC 时必须分别上传 `verification_video_path` 和 `poc_file_path`，并按 `references/video-compression.md` 控制体积。
- 不要把其他 skill 的端口表放进本文件；跨 skill 并发说明放在 README 高级章节。
