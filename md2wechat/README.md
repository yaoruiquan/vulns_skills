# md2wechat

将漏洞预警 Markdown 转换为安恒公众号风格 HTML，生成预警封面，并上传到微信公众号草稿箱。

## 功能

- 从漏洞预警 Markdown 提取元数据（标题、CVE、风险等级、PoC/Exp/在野/研究状态）
- 通过 `scripts/render_wechat_article.py` 渲染对齐真实公众号模板的内联 HTML
- 支持两种正文模板：普通漏洞预警模板、微软每月安全更新通报模板
- 在 HTML 旁生成 `<html>.meta.json`，供草稿标题、作者和摘要使用
- 通过 `scripts/render_alert_cover.py` 基于 PPTX 模版生成带标题和状态标签的封面图
- 校验 HTML 合规性（禁止 `<style>`、`<script>`、`class=`、`contenteditable=` 等）
- 通过 md2wechat CLI 或 API 上传草稿到微信公众号草稿箱

## 使用流程

### 第一步：安装 Claude Code（或其他 agent 工具）

参见官网文档安装配置。

### 第二步：安装 md2wechat CLI

本 skill 依赖 `md2wechat` 命令行工具与微信 API 通信：

```bash
brew install geekjourneyx/homebrew-md2wechat/md2wechat
```

### 第三步：安装本 skill

```bash
claude skills install https://github.com/yaoruiquan/vulns_skills.git
```

如果新用户没有 SSH key，优先使用 HTTPS 地址安装；需要 GitHub/GitLab SSH 或内部服务器上传权限时，先按 [上级 README 的 SSH key 说明](../README.md#没有-ssh-key-怎么办) 配置。

### 第四步：配置环境变量

```bash
cd ~/.claude/skills/md2wechat
cp .env.example .env
# 编辑 .env 填入 WECHAT_APPID 和 WECHAT_SECRET
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `SKILL.md` | agent 执行指令 |
| `scripts/render_wechat_article.py` | 确定性 HTML 渲染脚本 |
| `scripts/create_alert_draft.py` | 使用 HTML 旁路元数据创建带真实标题的微信公众号草稿 |
| `scripts/render_alert_cover.py` | PPTX 封面渲染脚本 |
| `assets/wechat-alert-article-template.placeholders.html` | 普通漏洞预警正文 HTML 占位符模板 |
| `assets/wechat-microsoft-monthly-template.placeholders.html` | 微软月度安全更新通报正文 HTML 占位符模板 |
| `assets/wechat-alert-article-template.html` | 公众号正文样式源文件（仅视觉参考，不直接上传） |
| `assets/wechat-alert-cover-template.pptx` | 封面 PPTX 源模版 |
| `references/antian-security-theme.md` | 安恒公众号 HTML 样式规范 |
| `references/wechat-draft-config.md` | 微信公众号草稿箱配置规则 |

## 主要命令

```bash
# 生成公众号正文 HTML
python3 scripts/render_wechat_article.py article.md --output /tmp/article.html --json

# 强制使用微软月度通报模板（默认 auto 会自动识别）
python3 scripts/render_wechat_article.py microsoft-monthly.md --article-type microsoft-monthly --output /tmp/microsoft-monthly.html --json

# 生成封面
python3 scripts/render_alert_cover.py article.md --output /tmp/cover.png --poc true --exp false --wild false --research true

# 上传草稿箱（配置 .env 后）
./scripts/md2wechat-env.sh config validate
./scripts/md2wechat-env.sh test-draft /tmp/article.html /tmp/cover.png
```

`render_wechat_article.py` 会生成 `/tmp/article.html.meta.json`。通过 `scripts/md2wechat-env.sh test-draft` 上传时，如果该元数据文件存在，wrapper 会自动上传正文图片和封面，构造 `create_draft` JSON，并保留真实文章标题。
