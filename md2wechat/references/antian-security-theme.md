# antian-security 公众号安全预警主题

本文件用于指导 agent 将漏洞预警 Markdown 转成微信公众号兼容的完整内联 HTML。该主题面向“安恒信息 CERT / 产品安全研究部”类安全通告，不依赖浏览器操作。

## 使用场景

- 用户提供漏洞预警 `.md`，要求生成公众号 HTML。
- 用户要求将漏洞预警同步到公众号草稿箱。
- `md2wechat` 识别到 `antian-security` 主题，但只返回通用 AI prompt，需要 agent 按本规范直接生成 HTML。

## 总体原则

1. 只输出公众号正文 HTML，不输出完整网页壳，不包含 `<!DOCTYPE html>`、`html`、`head`、`body`、`style`、`script`。
2. 所有样式必须写在标签 `style` 属性中，禁止 `<style>`、外链 CSS、JS、事件属性。
3. HTML 必须可直接作为公众号图文正文内容使用。
4. 不新增漏洞事实，不改写 CVE、版本、风险等级、修复方案、参考链接等关键内容。
5. 标题、摘要、作者、封面属于草稿元数据，不强行写入正文；正文首屏只保留主题头图/导语/风险概览。
6. 表格必须适配手机端，优先使用 `width:100%; table-layout:fixed; word-break:break-word;`。

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

正文按以下顺序组织：

1. 头部卡片：通告类型、标题、风险等级、发布日期。
2. 导语摘要：1-2 段，说明漏洞影响和处理建议。
3. 风险速览：CVE、漏洞等级、影响产品、是否公开 PoC、是否在野利用。
4. 漏洞详情：漏洞描述、影响范围、CVSS、利用条件。
5. 修复建议：官方修复方案、临时缓解方案。
6. 参考链接。
7. 免责声明/技术支持。

如果原 Markdown 缺少某一部分，不要虚构；可以省略该模块。

## 头部卡片

用于文章开头，突出安全通告属性。

```html
<section style="margin:0 0 22px 0;padding:22px 18px;border-radius:14px;background:linear-gradient(135deg,#f4f7ff 0%,#ffffff 62%,#fff8df 100%);border:1px solid #d9e4ff;box-shadow:0 8px 24px rgba(69,119,218,0.10);">
  <p style="margin:0 0 10px 0;color:#4577da;font-size:13px;line-height:1.6;font-weight:700;letter-spacing:1px;">安全预警 / SECURITY ADVISORY</p>
  <h1 style="margin:0;color:#1f2d3d;font-size:22px;line-height:1.45;font-weight:800;">文章标题</h1>
  <p style="margin:14px 0 0 0;color:#666666;font-size:14px;line-height:1.8;">风险等级：<span style="display:inline-block;padding:1px 8px;border-radius:999px;background:#d93026;color:#ffffff;font-size:13px;font-weight:700;">高危</span></p>
</section>
```

风险等级颜色：

- 严重/超危/危急：`#b42318`
- 高危：`#d93026`
- 中危：`#f29900`
- 低危：`#2e7d32`

## 一级区块标题

用于“一、安全通告”“二、漏洞信息”等主要章节。

```html
<section style="margin:28px 0 14px 0;text-align:center;">
  <section style="display:inline-block;padding:0 16px 8px 16px;border-bottom:2px solid #4577da;">
    <span style="display:inline-block;width:4px;height:14px;margin-right:4px;background:#4577da;vertical-align:middle;border-radius:2px;"></span>
    <span style="display:inline-block;width:4px;height:18px;margin-right:10px;background:#f8c025;vertical-align:middle;border-radius:2px;"></span>
    <span style="color:#1f2d3d;font-size:17px;font-weight:800;vertical-align:middle;">一、安全通告</span>
    <span style="display:inline-block;width:4px;height:18px;margin-left:10px;background:#f8c025;vertical-align:middle;border-radius:2px;"></span>
    <span style="display:inline-block;width:4px;height:14px;margin-left:4px;background:#4577da;vertical-align:middle;border-radius:2px;"></span>
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

## 风险速览表

用于 CVE、漏洞类型、风险等级、影响产品、公开状态。

```html
<table style="width:100%;margin:14px 0 18px 0;border-collapse:collapse;table-layout:fixed;border:1px solid #4577da;font-size:14px;line-height:1.7;">
  <tbody>
    <tr>
      <td style="width:32%;padding:8px 8px;background:#4577da;color:#ffffff;font-weight:700;border:1px solid #4577da;">CVE 编号</td>
      <td style="padding:8px 8px;color:#3e3e3e;border:1px solid #4577da;word-break:break-all;">CVE-YYYY-NNNN</td>
    </tr>
    <tr>
      <td style="width:32%;padding:8px 8px;background:#f4f7ff;color:#1f2d3d;font-weight:700;border:1px solid #4577da;">风险等级</td>
      <td style="padding:8px 8px;color:#d93026;font-weight:700;border:1px solid #4577da;">高危</td>
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

1. Markdown 一级标题可作为草稿标题，不一定进入正文；如果进入正文，使用头部卡片。
2. Markdown 二级标题转换为“一级区块标题”样式。
3. Markdown 三级标题转换为“二级小标题”样式。
4. 普通段落转换为带完整内联样式的 `<p>`。
5. 表格必须完整转换，不能丢列。
6. 引用块转换为重要提示卡片。
7. 链接保留原 URL。
8. 图片使用 `<!-- IMG:index -->` 占位，不擅自生成远程图片 URL。
9. 生成 HTML 后必须检查是否存在 `<style>`、`<script>`、`class=`、`onclick=`；存在则重写。

## 草稿元数据建议

- 标题：取 Markdown 第一个一级标题，超过 32 字时压缩但保留产品名、漏洞类型和“风险提示/安全通告”。
- 作者：`安恒信息CERT` 或用户指定作者，最多 16 字。
- 摘要：从安全通告首段压缩到 120 字以内。
- 封面：公众号草稿通常需要 `cover` 或 `cover_media_id`；若用户未提供，先生成 HTML，不直接创建草稿。

## 最终输出要求

当用户要求“生成公众号 HTML”时：

- 输出一个 `.html` 文件路径。
- 文件内容只包含公众号正文片段，不包含浏览器保存下来的公众号后台整页 HTML。

当用户要求“推送草稿箱”时：

- 先确认 `md2wechat config validate` 通过。
- 必须具备 `WECHAT_APPID`、`WECHAT_SECRET`，并提供本地封面图或永久素材 `cover_media_id`。
- 生成 HTML 后通过 `md2wechat create_draft` 或 `md2wechat convert --draft` 推送。
