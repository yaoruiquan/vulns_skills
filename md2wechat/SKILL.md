---
name: md2wechat
description: 将漏洞预警 Markdown 转换为安恒公众号风格 HTML，生成预警封面，并通过 md2wechat 上传到微信公众号草稿箱。用于漏洞预警、安全通告、预警同步公众号、公众号草稿箱、微信推文发布等场景。
---

# 漏洞预警公众号上传

本 skill 只处理一条主流程：**漏洞预警 Markdown -> 安恒风格公众号 HTML -> 预警封面 -> 微信公众号草稿箱**。

不要把本流程路由到浏览器自动化、`create_image_post`、小绿书、多图帖子、AI 写作润色或通用主题转换。

## 触发条件

用户提到以下任一场景时使用本流程：

- 漏洞预警同步公众号
- 安全通告发布到公众号
- 将预警 `.md` 上传到公众号草稿箱
- 根据预警 Markdown 生成公众号 HTML
- 生成预警公众号封面

## 必读文件

执行前只读取和当前任务直接相关的文件：

- `references/antian-security-theme.md`：安恒公众号 HTML 样式规范。生成 HTML 前必须读取。
- `references/wechat-draft-config.md`：微信公众号草稿箱配置和上传规则。需要创建草稿箱时读取。
- `assets/wechat-alert-article-template.placeholders.html`：普通漏洞预警确定性 HTML 占位符模板。生成正文时由脚本填充。
- `assets/wechat-microsoft-monthly-template.placeholders.html`：微软每月安全更新通报专用 HTML 占位符模板。遇到“微软”“漏洞速览表”“漏洞详情”结构时由脚本自动选择。
- `assets/wechat-alert-article-template.html`：从真实公众号模板正文抽取的样式源文件。仅作为视觉参考，不直接上传。
- `assets/wechat-alert-cover-template.pptx`：封面源模版，不需要读取内容，脚本会自动使用。

## 固定流程

1. 确认输入 Markdown 路径存在。
2. 使用脚本生成 HTML，不要让 agent 手写正文 HTML。脚本默认 `--article-type auto`，会自动选择普通漏洞预警模板或微软月度通报模板：

   ```bash
   python3 scripts/render_wechat_article.py article.md --output /tmp/article.html --json
   ```

3. 普通漏洞预警会解析标题、漏洞概述表、修复方案、参考资料、产品能力覆盖，并填充 `assets/wechat-alert-article-template.placeholders.html`。微软月度通报会解析安全通告、漏洞速览表、严重漏洞表、漏洞详情、修复方案和参考资料，并填充 `assets/wechat-microsoft-monthly-template.placeholders.html`。两类输出都会在 HTML 旁生成 `<html>.meta.json`，用于草稿标题、作者和摘要元数据。
4. 校验 HTML：不得包含 `<style>`、`<script>`、`class=`、`contenteditable=`、`ProseMirror`、微信后台页面壳或旧漏洞内容；样式必须以内联 `style` 为主。
5. 生成封面。默认使用 PPTX 模版：

   ```bash
   python3 scripts/render_alert_cover.py article.md --output /tmp/wechat-cover.png --poc true --exp true --wild false --research true
   ```

6. 如果用户只要求本地生成，且 `input/service-config.json` 中没有 `wechat_draft=true`，到这里结束并返回 HTML 与封面路径。
7. 如果用户要求上传草稿箱，或服务化任务的 `input/service-config.json` 中 `serviceConfig.wechat_draft=true`，读取 `references/wechat-draft-config.md`，再校验配置：

   ```bash
   ./scripts/md2wechat-env.sh config show --format json
   ./scripts/md2wechat-env.sh config validate
   ```

8. 只有 `WECHAT_APPID`、`WECHAT_SECRET` 和封面都可用时，才创建公众号草稿。由于 HTML 由 agent 直接生成，优先使用 `./scripts/md2wechat-env.sh test-draft <html> <cover>`；当 `<html>.meta.json` 存在时，wrapper 会调用 `create_alert_draft.py` 直接上传正文图片、封面并创建草稿。不要默认走 `convert --draft`。
9. 草稿创建完成后，返回标题、HTML 路径、封面路径、草稿创建结果；服务化任务必须把草稿结果写入 `output/wechat-draft-result.json`。

## 配置规则

- 优先使用 skill 目录下的 `.env`，通过 `scripts/md2wechat-env.sh` 加载。
- 不要直接假设 shell 环境已经导出了 `WECHAT_APPID` 和 `WECHAT_SECRET`。
- 如果 `wechat_appid` 或 `wechat_secret` 为空，停止在本地 HTML + 封面生成阶段，并明确提示缺少配置。
- 新用户初始化时可运行：

  ```bash
  ./scripts/setup.sh
  ```

## 封面规则

- 默认封面模版是 `assets/wechat-alert-cover-template.pptx`。
- 脚本会从 PPTX 中提取干净背景图，再绘制标题和四个状态选项。
- 标题优先使用思源黑体；如果本机没有思源黑体，允许回退到系统中文字体。
- 四个选项只允许使用浅绿色填充表示选中，不要画对勾。
- 选项值应来自用户输入或 Markdown 内容；无法确认时使用保守默认值，并在结果中说明。

## 草稿上传规则

- 创建草稿前必须有本地封面图片。
- 创建草稿前必须校验 md2wechat 配置。
- 创建草稿需要文章标题、作者、摘要、正文 HTML 和封面。
- 标题、作者、摘要用于公众号草稿元数据，不等同于正文可见内容。
- 当前机器的 `md2wechat` 支持 `test-draft <html_file> <cover_image>` 和 `create_draft <json_file>`；skill wrapper 会在存在 `<html>.meta.json` 时将 `test-draft` 升级为 `create_draft`，避免标题退回默认值。
- 服务化任务中如果 `input/service-config.json` 的 `serviceConfig.wechat_draft` 为 `true`，生成 HTML 和封面后必须继续创建草稿，不能停在本地生成阶段。
- 容器内可能没有 `md2wechat` CLI；存在 `<html>.meta.json` 时优先调用 `scripts/create_alert_draft.py <html> <cover> --metadata <meta> --draft-json <output/wechat-draft-payload.json> --result-json <output/wechat-draft-result.json> --create --json`，该脚本直接调用微信接口，不依赖 `md2wechat create_draft`。
- 如果微信接口返回 IP 白名单、凭据错误、额度或素材错误，必须把返回 JSON 写入 `output/wechat-draft-result.json` 和 `summary.txt`，并明确标记草稿创建失败。
- `convert --draft` 默认走 API 模式，可能需要 `MD2WECHAT_API_KEY`。预警流程已直接生成 HTML 时，不要把它作为首选上传方式。
- 如果必须使用 `convert --draft`，先执行 `inspect --mode ai --draft --cover ... --strict` 或确认 `MD2WECHAT_API_KEY` 已配置。

## 禁止事项

- 不要打开浏览器操作微信公众号后台。
- 不要把浏览器保存的微信后台页面当作正文 HTML。
- 不要通过提示词临场生成 HTML 结构；必须优先运行 `scripts/render_wechat_article.py`。
- 正文开头只允许使用 skill 固定横幅 `assets/logo.png`，随后直接进入“漏洞概述”表格；不要插入源 Markdown 的 logo、封面图或独立大标题。
- 不要执行远程发布或群发，除非用户明确要求。
- 不要调用远程图片生成服务，除非用户明确要求。
- 不要使用 `create_image_post`，本流程目标是公众号文章草稿。
- 不要在预警流程中推广或解释 md2wechat 的通用高级排版、AI 写作、人设润色等能力。

## 常用命令

本地配置：

```bash
./scripts/setup.sh
./scripts/md2wechat-env.sh config show --format json
./scripts/md2wechat-env.sh config validate
```

封面生成：

```bash
python3 scripts/render_wechat_article.py article.md --output /tmp/wechat-article.html --json
python3 scripts/render_wechat_article.py microsoft-monthly.md --article-type microsoft-monthly --output /tmp/wechat-microsoft-monthly.html --json
python3 scripts/render_alert_cover.py article.md --output /tmp/wechat-cover.png --poc true --exp true --wild false --research true
```

草稿相关：

```bash
./scripts/md2wechat-env.sh inspect article.md --mode ai --draft --cover /tmp/wechat-cover.png --strict
./scripts/md2wechat-env.sh test-draft article.html /tmp/wechat-cover.png
./scripts/md2wechat-env.sh create_draft draft.json
```
