# antian-security 公众号安全预警主题

本文件用于指导 agent 将漏洞预警 Markdown 转成微信公众号兼容的完整内联 HTML。该主题面向“安恒信息 CERT / 产品安全研究部”类安全通告，不依赖浏览器操作。

确定性渲染入口是 `scripts/render_wechat_article.py`，占位符模板是 `assets/wechat-alert-article-template.placeholders.html`。真实样式基准来自 `assets/wechat-alert-article-template.html`，仅用于维护模板时参考，不能原样上传其中的旧漏洞内容、图片地址、编辑器属性或微信后台痕迹。

## 使用场景

- 用户提供漏洞预警 `.md`，要求生成公众号 HTML。
- 用户要求将漏洞预警同步到公众号草稿箱。
- `md2wechat` 识别到 `antian-security` 主题但只返回通用 AI prompt 时，不再让 agent 手写 HTML，改为运行 `scripts/render_wechat_article.py`。

## 总体原则

1. 只输出公众号正文 HTML，不输出完整网页壳，不包含 `<!DOCTYPE html>`、`html`、`head`、`body`、`style`、`script`。
2. 所有样式必须写在标签 `style` 属性中，禁止 `<style>`、外链 CSS、JS、事件属性。
3. HTML 必须可直接作为公众号图文正文内容使用。
4. 不新增漏洞事实，不改写 CVE、版本、风险等级、修复方案、参考链接等关键内容。
5. 标题、摘要、作者、封面属于草稿元数据，公众号后台会在正文上方显示草稿标题；HTML 正文首屏只放固定横幅 `assets/logo.png`，随后进入漏洞概述表格，不插入源 Markdown 的 logo、封面图或独立大标题。
6. 表格必须适配手机端，优先使用 `width:100%; table-layout:fixed; word-break:break-word;`。
7. 不要使用渐变头部卡片、圆角卡片堆叠等自由发挥样式；这些与真实模板差异过大。

## 色彩

| 用途 | 颜色 |
|------|------|
| 主色 | `#4577da` |
| 强调黄 | `#f8c025` |
| 正文 | `#3e3e3e` |
| 次级文字 | `#666666` |
| 弱文字 | `#8a8f99` |
| 浅蓝背景 | `#f4f7ff` |
| 浅黄背景 | `#fff8df` |
| 边框 | `#d9e4ff` |
| 表头背景 | `#4577da` |
| 危急/高危 | `#d93026` |
| 中危 | `#f29900` |
| 低危 | `#2e7d32` |

## 字体和基础排版

主容器使用：

```html
<section style="margin:0 auto;padding:0 0 16px 0;max-width:677px;color:#3e3e3e;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue','Microsoft YaHei',Arial,sans-serif;font-size:15px;line-height:1.9;letter-spacing:0.3px;word-break:break-word;">
```

正文段落：

```html
<p style="margin:0 0 14px 0;color:#3e3e3e;font-size:15px;line-height:1.9;text-align:justify;">
```

正文链接：

```html
<a href="URL" style="color:#4577da;text-decoration:none;word-break:break-all;">URL</a>
```

## 页面结构

正文按以下顺序组织，尽量对齐 `assets/wechat-alert-article-template.html`：

1. 固定横幅：使用 `assets/logo.png`，按真实公众号模板的 1080x300 横幅比例渲染，不使用源 Markdown 附带图片。
2. 漏洞概述表格：四列表格，蓝色整行表头“漏洞概述”，字段包含漏洞名称、安恒CERT评级、CVSS3.1评分、CVE/CNVD/CNNVD/安恒CERT编号、POC/EXP/在野利用/研究情况、危害描述。
3. 风险提醒段落：说明产品使用范围、危害性和建议客户自查防护。
4. 漏洞描述：使用真实模板的二级小标题样式和正文段落。
5. 影响范围：列出影响版本、安全版本、影响产品。
6. 修复建议：官方修复方案、临时缓解方案。
7. 参考资料：蓝色装饰标题后直接列 URL。
8. 产品能力覆盖：如 Markdown 提供相关内容则生成；否则省略，不要虚构。
9. 技术支持：固定保留 `如有漏洞相关需求支持请联系400-6059-110获取相关能力支撑。`

如果原 Markdown 缺少某一部分，不要虚构；可以省略该模块。

## 正文开头

正文开头先渲染固定横幅 `assets/logo.png`，再渲染“漏洞概述”表格。草稿元数据标题必须使用 `【已复现】漏洞名称（CVE-YYYY-NNNN）` 或 `【风险通告】漏洞名称（CVE-YYYY-NNNN）`；封面标题必须去掉前缀但保留 CVE。不要把源 Markdown 的 `logo-*.JPG`、公众号封面图、文章标题或 `<!-- IMG:banner -->` 放入正文首屏；封面只用于公众号草稿元数据。

风险等级颜色：

- 严重/超危/危急：`#b42318`
- 高危：`#d93026`
- 中危：`#f29900`
- 低危：`#2e7d32`

## 一级区块标题

用于“漏洞描述”“影响范围”“修复建议”“参考资料”“产品能力覆盖”“技术支持”等主要章节。样式要贴近真实模板：标题居中，左右为蓝色短竖条，标题下有蓝色细线。

```html
<section style="margin:20px 0px 15px;font-size:16px;letter-spacing:0.578px;display:flex;flex-flow:row;text-align:center;justify-content:center;">
  <section style="margin-right:4px;display:inline-block;vertical-align:bottom;width:auto;flex:0 0 0%;height:auto;align-self:flex-end;">
    <section style="display:inline-block;width:3px;height:10px;vertical-align:top;overflow:hidden;background-color:#4577da;"></section>
  </section>
  <section style="display:inline-block;vertical-align:bottom;width:auto;flex:0 0 auto;align-self:flex-end;min-width:10%;height:auto;padding:0px 12px;box-sizing:border-box;">
    <section style="text-align:justify;font-size:17px;"><p><strong>漏洞描述</strong></p></section>
    <section style="margin-top:2px;"><section style="background-color:#4577da;height:1px;"></section></section>
  </section>
  <section style="margin-left:4px;display:inline-block;vertical-align:bottom;width:auto;flex:0 0 0%;height:auto;align-self:flex-end;">
    <section style="display:inline-block;width:3px;height:16px;vertical-align:top;overflow:hidden;background-color:#4577da;"></section>
  </section>
</section>
```

## 二级小标题

用于“漏洞描述”“影响范围”“修复方案”“临时缓解方案”等。

```html
<section style="margin:20px 0 10px 0;">
  <span style="display:inline-block;width:8px;height:8px;margin-right:8px;background:#f8c025;transform:rotate(45deg);vertical-align:middle;"></span>
  <span style="display:inline-block;width:8px;height:8px;margin-right:8px;background:#4577da;transform:rotate(45deg);vertical-align:middle;"></span>
  <span style="color:#666666;font-size:15px;font-weight:800;vertical-align:middle;">漏洞描述</span>
</section>
```

## 信息卡片

适合摘要、风险提示和修复建议。

```html
<section style="margin:14px 0;padding:14px 15px;border-radius:10px;background:#f4f7ff;border:1px solid #d9e4ff;">
  <p style="margin:0;color:#3e3e3e;font-size:15px;line-height:1.9;text-align:justify;">内容</p>
</section>
```

重要提示卡片：

```html
<section style="margin:14px 0;padding:14px 15px;border-left:5px solid #f8c025;background:#fff8df;border-radius:8px;">
  <p style="margin:0;color:#3e3e3e;font-size:15px;line-height:1.9;text-align:justify;">建议用户尽快升级至安全版本。</p>
</section>
```

## 漏洞概述表

正文开头必须优先生成该表，而不是卡片式风险速览。表格结构为 4 列，第一行蓝底白字“漏洞概述”。

```html
<table style="min-width:100px;width:100%;border-collapse:collapse;table-layout:fixed;">
  <tbody>
    <tr>
      <td colspan="4" style="word-break:break-all;border:1px solid #4577da;background-color:#4577da;padding:5px;color:#ffffff;font-size:14px;text-align:center;"><strong>漏洞概述</strong></td>
    </tr>
    <tr>
      <td style="width:25%;word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;"><strong>漏洞名称</strong></td>
      <td colspan="3" style="width:75%;word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;">漏洞名称</td>
    </tr>
    <tr>
      <td style="width:25%;word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;"><strong>安恒CERT评级</strong></td>
      <td style="width:25%;word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;">评级</td>
      <td style="width:25%;word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;"><strong>CVSS3.1评分</strong></td>
      <td style="width:25%;word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;">评分</td>
    </tr>
    <tr>
      <td style="width:25%;word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;"><strong>危害描述</strong></td>
      <td colspan="3" style="width:75%;word-break:break-all;border:1px solid #4577da;padding:5px;font-size:14px;">危害描述</td>
    </tr>
  </tbody>
</table>
```

## 普通表格

Markdown 表格转换时使用：

```html
<table style="width:100%;margin:14px 0 18px 0;border-collapse:collapse;table-layout:fixed;border:1px solid #4577da;font-size:14px;line-height:1.7;">
  <thead>
    <tr>
      <th style="padding:8px;background:#4577da;color:#ffffff;font-weight:700;border:1px solid #4577da;text-align:left;">字段</th>
      <th style="padding:8px;background:#4577da;color:#ffffff;font-weight:700;border:1px solid #4577da;text-align:left;">内容</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding:8px;color:#3e3e3e;border:1px solid #4577da;word-break:break-word;">字段</td>
      <td style="padding:8px;color:#3e3e3e;border:1px solid #4577da;word-break:break-word;">内容</td>
    </tr>
  </tbody>
</table>
```

## 列表

```html
<ul style="margin:8px 0 14px 0;padding-left:20px;color:#3e3e3e;font-size:15px;line-height:1.9;">
  <li style="margin:0 0 6px 0;color:#3e3e3e;">列表项</li>
</ul>
```

## 代码和命令

公众号正文中尽量少用代码块。必须保留时：

```html
<pre style="margin:12px 0;padding:12px;border-radius:8px;background:#1f2d3d;color:#f8fafc;font-size:13px;line-height:1.7;white-space:pre-wrap;word-break:break-all;"><code>command</code></pre>
```

## 参考链接

参考链接必须直接展示 URL，不能只写“点击阅读原文”。

```html
<section style="margin:8px 0 10px 0;padding:10px 12px;border-radius:8px;background:#f8fafc;border:1px solid #e5e7eb;">
  <p style="margin:0;color:#666666;font-size:14px;line-height:1.8;">[1] <a href="URL" style="color:#4577da;text-decoration:none;word-break:break-all;">URL</a></p>
</section>
```

## 末尾声明

```html
<section style="margin:26px 0 0 0;padding:12px 14px;border-radius:10px;background:#f8fafc;border:1px solid #e5e7eb;">
  <p style="margin:0;color:#8a8f99;font-size:13px;line-height:1.8;text-align:justify;">本文由产品安全研究部根据公开信息整理，仅供安全加固和风险排查参考。请结合实际业务环境评估影响范围并及时完成修复。</p>
</section>
```

## 转换规则

1. Markdown 一级标题作为草稿标题；正文不要生成渐变头部卡片。
2. 先根据 Markdown 中的漏洞信息表生成“漏洞概述”四列表格。
3. Markdown 二级标题转换为真实模板的蓝色装饰标题样式。
4. Markdown 三级标题转换为“二级小标题”样式。
5. 普通段落转换为带完整内联样式的 `<p>`。
6. 表格必须完整转换，不能丢列。
7. 引用块转换为重要提示卡片。
8. 链接保留原 URL。
9. 图片使用 `<!-- IMG:index -->` 占位，不擅自生成远程图片 URL。
10. 生成 HTML 后必须检查是否存在 `<style>`、`<script>`、`class=`、`contenteditable=`、`ProseMirror`、`onclick=`；存在则重写。

## 草稿元数据建议

- 标题：取 Markdown 第一个一级标题，超过 32 字时压缩但保留产品名、漏洞类型和“风险提示/安全通告”。
- 作者：`安恒信息CERT` 或用户指定作者，最多 16 字。
- 摘要：从安全通告首段压缩到 120 字以内。
- 封面：公众号草稿通常需要 `cover` 或 `cover_media_id`；若用户未提供，先生成 HTML，不直接创建草稿。

## 最终输出要求

当用户要求“生成公众号 HTML”时：

- 运行 `python3 scripts/render_wechat_article.py article.md --output article.html --json`。
- 输出一个 `.html` 文件路径。
- 文件内容只包含公众号正文片段，不包含浏览器保存下来的公众号后台整页 HTML。

当用户要求“推送草稿箱”时：

- 先确认 `md2wechat config validate` 通过。
- 必须具备 `WECHAT_APPID`、`WECHAT_SECRET`，并提供本地封面图或永久素材 `cover_media_id`。
- 生成 HTML 后通过 `md2wechat create_draft` 或 `md2wechat convert --draft` 推送。
