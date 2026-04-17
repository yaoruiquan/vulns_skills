# phase2-cnnvd-report-cdp

通过 Chrome DevTools MCP 控制真实浏览器完成 CNNVD 漏洞上报。

这个 README 面向第一次使用或接手维护这个 skill 的用户。

## 这个 skill 做什么

`phase2-cnnvd-report-cdp` 用于将已经整理好的漏洞材料提交到 CNNVD 平台。常见操作包括：

- 从本地 `docx` 材料中提取字段
- 打开 CNNVD 页面并导航到报送入口
- 填写漏洞基本信息、漏洞详情和验证过程
- 上传验证录像和其他附件
- 提交成功后记录 CNNVD 编号
- 在需要时更新本地汇总表

## 新用户上手

### 1. 配置环境变量

**首次使用必须完成配置。**

```bash
# 复制配置模板
cp .env.template .env

# 编辑配置文件，填写实际值
vim .env
```

**必须配置项**：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `CNNVD_USERNAME` | CNNVD 登录用户名 | `user@example.com` |
| `CNNVD_PASSWORD` | CNNVD 登录密码 | `your_password` |
| `VULNS_DATA_DIR` | 漏洞数据目录 | `/path/to/vulns/date` |
| `SUMMARY_TABLE_PATH` | 漏洞汇总表路径 | `/path/to/漏洞汇总表.xlsx` |

**可选配置项**：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `COMPANY_NAME` | 技术支持单位名称 | `杭州安恒信息技术股份有限公司` |
| `DEFAULT_CONTACT_PHONE` | 默认联系电话 | `15700082275` |
| `CHROME_DEBUG_PORT` | Chrome 调试端口 | `9333` |
| `CHROME_PROFILE_NAME` | Chrome profile 名称 | `cnnvd-report` |

### 2. 安装依赖

```bash
npm install -g chrome-devtools-mcp@latest
pip install websocket-client python-docx openpyxl ddddocr
```

### 3. 启动 skill 专用浏览器

```bash
./scripts/start-chrome-debug.sh
```

### 4. 检查调试端口

```bash
curl -s http://127.0.1:9333/json/version
```

> 详细环境配置参见 [references/setup-guide.md](references/setup-guide.md)

## 目录结构

```text
phase2-cnnvd-report-cdp/
├── SKILL.md                    # 精简的操作指南
├── README.md                   # 本文件
├── .env.template               # 配置模板（首次使用必填）
├── .env                        # 实际配置（从模板复制）
├── .mcp.json                   # MCP server 配置
├── .claude/settings.json       # Claude Code 项目配置
├── scripts/
│   ├── config.py               # 配置加载模块
│   ├── chrome-devtools-mcp-wrapper.sh  # MCP wrapper
│   ├── start-chrome-debug.sh           # 启动调试浏览器
│   ├── extract_vuln_data.py            # 提取漏洞数据
│   ├── compress_zip.py                 # 压缩附件
│   ├── captcha_ocr.py                  # 验证码 OCR
│   └── update_summary.py               # 更新汇总表
└── references/
    ├── setup-guide.md         # 环境配置详细步骤
    ├── data-fields.md         # 数据字段映射说明
    ├── vuln-type-mapping.md   # 漏洞类型映射表
    ├── captcha-ocr.md         # 验证码 OCR 说明
    ├── word-extraction.md     # Word 文档提取规则
    ├── video-compression.md   # 视频压缩指南
    ├── summary-table.md       # 汇编表说明
    ├── mcp-tools.md           # MCP 工具参考
    └── mcp-connection.md      # MCP 连接原理
```

## 复用指南

### 复制 skill 给其他团队使用

1. **复制整个 skill 目录**
   ```bash
   cp -r ~/.claude/skills/phase2-cnnvd-report-cdp ~/.claude/skills/your-team-cnnvd-report
   ```

2. **重命名 profile 防止冲突**
   编辑 `.env` 文件：
   ```
   CHROME_PROFILE_NAME=your-team-cnnvd
   CHROME_DEBUG_PORT=9334  # 使用不同端口
   ```

3. **修改业务信息**
   编辑 `.env` 文件：
   ```
   COMPANY_NAME=你的公司名称
   DEFAULT_CONTACT_PHONE=你的联系电话
   ```

4. **配置数据路径**
   编辑 `.env` 文件：
   ```
   VULNS_DATA_DIR=/your/data/path
   SUMMARY_TABLE_PATH=/your/summary/path.xlsx
   ```

5. **检查共享依赖**
   确保 `shared-chrome-devtools` skill 存在：
   ```bash
   ls ~/.claude/skills/shared-chrome-devtools/
   ```

   如果不存在，需要将启动脚本改为独立实现（参见 `start-chrome-debug.sh`）。

## 常用命令

### 提取漏洞数据

```bash
python3 scripts/extract_vuln_data.py DAS-T105966 --platform CNNVD
```

### 压缩附件目录

```bash
python3 scripts/compress_zip.py "/path/to/CNNVD-folder"
```

### OCR 识别验证码

```bash
python3 scripts/captcha_ocr.py /tmp/captcha.png
```

### 更新本地汇总表

```bash
python3 scripts/update_summary.py \
  --title "漏洞标题" \
  --vendor "影响厂商" \
  --das-id "DAS-T105966" \
  --submitter "提交人员" \
  --cnvd-id "CNVD-2026-XXXX" \
  --cnnvd-id "CNNVD-202604-XXXX" \
  --date "2026-04-14"
```

## 参考文档

| 文档 | 说明 |
|------|------|
| [SKILL.md](./SKILL.md) | 精简的操作指南 |
| [.env.template](./.env.template) | 配置模板 |
| [setup-guide.md](./references/setup-guide.md) | 环境配置详细步骤 |
| [data-fields.md](./references/data-fields.md) | 数据字段映射 |
| [vuln-type-mapping.md](./references/vuln-type-mapping.md) | 漏洞类型级联选择 |
| [captcha-ocr.md](./references/captcha-ocr.md) | 验证码 OCR |
| [word-extraction.md](./references/word-extraction.md) | Word 提取规则 |
| [video-compression.md](./references/video-compression.md) | 视频压缩 |
| [summary-table.md](./references/summary-table.md) | 汇编表 |
| [mcp-tools.md](./references/mcp-tools.md) | MCP 工具参考 |

## 与其他技能的关系

典型链路：

```text
phase1-material-processor / 材料整理
  -> 生成 docx 和附件
phase2-cnvd-report-cdp
  -> 完成 CNVD 上报
phase2-cnnvd-report-cdp
  -> 完成 CNNVD 上报
```

## 相关链接

- [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [CNNVD 官网](https://www.cnnvd.org.cn/)