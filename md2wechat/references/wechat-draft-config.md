# 微信公众号草稿箱配置

将 HTML 推送到公众号草稿箱需要 `md2wechat` 能调用微信公众平台接口。当前流程不使用浏览器。

## 必需配置

至少需要：

```bash
WECHAT_APPID=公众号 AppID
WECHAT_SECRET=公众号 AppSecret
```

可通过环境变量提供，也可写入 `~/.config/md2wechat/config.yaml`。配置完成后执行：

```bash
md2wechat config show --format json
md2wechat config validate
```

`wechat_appid` 和 `wechat_secret` 不能为空。

## 使用本 skill 的 .env

可以把配置放在 `/Users/yao/.claude/skills/md2wechat/.env`：

```bash
cd /Users/yao/.claude/skills/md2wechat
cp .env.example .env
vim .env
```

然后统一使用 wrapper，它会先加载 `.env` 再执行 `md2wechat`：

```bash
./scripts/md2wechat-env.sh config show --format json
./scripts/md2wechat-env.sh config validate
```

注意：直接运行 `md2wechat ...` 不会自动读取 skill 目录下的 `.env`。

## 草稿封面

公众号图文草稿通常需要封面素材。二选一：

- 本地封面图：使用 `--cover /path/to/cover.jpg`
- 已上传永久素材：使用 `--cover-media-id <media_id>`

如果没有封面，只生成本地 HTML，不创建草稿。

## 封面模板自动生成

本 skill 提供：

```bash
python3 scripts/render_alert_cover.py article.md \
  --template "$WECHAT_COVER_TEMPLATE" \
  --output /tmp/md2wechat-covers/article-cover.png
```

默认模板已内置在：

```text
assets/wechat-alert-cover-template.pptx
```

脚本默认从 PPTX 中提取干净背景图，再绘制标题和四个选项，不依赖 PowerPoint 或浏览器。

支持两类模板：

- `.pptx`：推荐。脚本会提取模板中的背景图，再叠加标题和选项。
- `.png`：可用，但如果 PNG 已经带旧标题，需要脚本遮盖旧文字后重绘，效果可能弱于 PPTX。

依赖安装：

```bash
python3 -m pip install Pillow
```

标题按思源黑体风格绘制，字号约等于 PPT 中 18 号。四个选项为 `POC`、`EXP`、`在野利用`、`研究情况`；选中时方块填充浅绿色，不画勾。

如果本机安装了思源黑体，可在 `.env` 中配置：

```bash
WECHAT_COVER_FONT=/path/to/SourceHanSansCN-Bold.otf
```

也可以在命令行显式传入：

```bash
python3 scripts/render_alert_cover.py article.md --font /path/to/SourceHanSansCN-Bold.otf
```

## 推荐流程

```bash
md2wechat config validate
python3 scripts/render_wechat_article.py article.md --output article.html --json
md2wechat inspect article.md --mode ai --draft --cover cover.jpg --strict
md2wechat test-draft article.html cover.jpg
```

使用 `.env` wrapper 的推荐流程：

```bash
./scripts/md2wechat-env.sh config validate
python3 scripts/render_wechat_article.py article.md --output /tmp/article.html --json
python3 scripts/render_alert_cover.py article.md --output /tmp/article-cover.png --poc true --exp true --wild false --research true
./scripts/md2wechat-env.sh inspect article.md --mode ai --draft --cover /tmp/article-cover.png --strict
./scripts/md2wechat-env.sh test-draft /tmp/article.html /tmp/article-cover.png
```

HTML 必须由 `scripts/render_wechat_article.py` 根据占位符模板确定性生成，不要让 agent 临场手写 HTML。生成后优先使用 `test-draft <html_file> <cover_image>`。当前机器的 `md2wechat 2.1.0` 支持该命令。

`convert --draft` 默认走 API 模式，缺少 `MD2WECHAT_API_KEY` 时会被 `inspect --strict` 判定为不可用；除非已经配置 API key，否则不要把它作为预警流程的首选上传方式。

需要更细粒度控制草稿字段时，构造 `create_draft <json_file>` 所需 JSON 再上传。

## 当前机器状态

如果 `md2wechat config show --format json` 中显示：

```json
"wechat_appid": "",
"wechat_secret": ""
```

说明只能本地生成 HTML，不能推送公众号草稿箱。
