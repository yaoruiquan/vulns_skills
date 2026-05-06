# 产品安全研究部 AI-Skills

> 赋能安全研究，探索AI驱动的下一代安全能力

## 🧠 关于本仓库

本仓库由 **产品安全研究部** 维护，聚焦于 **人工智能与安全研究深度融合** 的实践沉淀。我们致力于探索利用大语言模型（LLM）、机器学习（ML）等 AI 技术，提升安全检测、漏洞分析、威胁情报、自动化攻防等方向的研究效率与创新边界。

无论你是安全研究员、开发工程师，还是对 AI + Security 交叉领域感兴趣的探索者，这里都将为你提供可落地的代码、实验案例、研究思路和最佳实践。

## 🎯 主要方向

- **智能漏洞挖掘**：基于 LLM 的代码审计、Fuzzing 用例生成、污点分析辅助
- **自动化逆向分析**：二进制理解、反编译代码注释、控制流/数据流智能分析
- **威胁情报与态势感知**：非结构化情报信息抽取、IOC 自动化提炼、攻击链推理
- **AI 安全评估**：模型鲁棒性测试、对抗样本生成、提示词注入检测
- **安全运营自动化**：告警降噪、事件自动分类、响应剧本生成

## Skills

| Skill | 用途 |
|-------|------|
| [vulnerability-alert-processor](vulnerability-alert-processor/README.md) | 漏洞预警材料整理，生成 Markdown/Word/PDF 报告 |
| [md2wechat](md2wechat/README.md) | 漏洞预警 Markdown 转公众号 HTML，生成封面并上传草稿箱 |
| [msrc-vulnerability-report](msrc-vulnerability-report/README.md) | 微软安全更新漏洞预警报告生成 |
| [phase1-material-processor](phase1-material-processor/SKILL.md) | 监管上报前材料整理（重命名 + docx 模板） |
| [phase2-ncc-report](phase2-ncc-report/README.md) | NCC 平台漏洞上报（浏览器自动化） |
| [phase2-cnvd-report](phase2-cnvd-report/README.md) | CNVD 漏洞上报（浏览器自动化） |
| [phase2-cnnvd-report](phase2-cnnvd-report/README.md) | CNNVD 漏洞上报（浏览器自动化） |
| [cnvd-weekly-db-update](cnvd-weekly-db-update/README.md) | CNVD 每周 XML 数据库更新 |

> 每个 skill 目录下均有 README.md 说明使用流程，SKILL.md 为 agent 执行指令。

## 新用户准备

### 1. 安装 agent 工具

先安装 Claude Code 或团队指定的其他 agent 工具。安装完成后确认命令可用：

```bash
claude --version
```

### 2. 安装 skills

推荐使用 `npx` 一条命令安装：

```bash
npx @yaoruiquan/vulns-skills
```

这个 npm 包只是轻量安装器，不打包本仓库的所有 skill 内容。它会在本机执行：

```bash
claude skills install https://github.com/yaoruiquan/vulns_skills.git
```

如果不想使用 `npx`，也可以直接运行上面的 `claude skills install` 命令。使用 HTTPS 地址通常不需要 SSH key。

如果使用公司内网 GitLab 或 SSH 地址，按下面“没有 SSH key 怎么办”先配置访问权限。

### 3. 初始化单个 skill

进入具体 skill 目录后，可以直接让 agent 处理初始化：

```text
安装依赖并初始化环境
```

agent 会按该 skill 的 README 和 SKILL.md 执行依赖安装、`.env` 初始化、浏览器 MCP 启动和连通性检查。

## 没有 SSH key 怎么办

新用户常见有两类 SSH 需求：代码仓库访问、报告上传服务器访问。两者不是一回事。

### 1. 访问 GitHub/GitLab 仓库

如果只是安装或拉取公开仓库，优先使用 HTTPS 地址，不需要 SSH key。

如果仓库要求 SSH 访问，先生成本机 SSH key：

```bash
ssh-keygen -t ed25519 -C "your.name@dbappsecurity.com.cn"
```

一路回车使用默认路径即可，通常会生成：

```text
~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub
```

复制公钥：

```bash
pbcopy < ~/.ssh/id_ed25519.pub
```

然后把公钥添加到 GitHub 或 GitLab：

- GitHub：Settings -> SSH and GPG keys -> New SSH key
- GitLab：Preferences -> SSH Keys -> Add new key

验证连接：

```bash
ssh -T git@github.com
ssh -T git@gitlab.info.dbappsecurity.com.cn
```

看到欢迎或认证成功提示即可。即使提示 “shell access is not provided”，也通常表示 Git 认证已成功。

### 2. 上传报告到内部服务器

预警、MSRC、CNVD、CNNVD、NCC、CNVD weekly 等 skill 的发布或更新脚本可能会通过 SSH/SCP 上传 zip、PDF、HTML 预览或 XML 文件到内部服务器。

推荐做法是让服务器管理员把你的公钥加入上传账号的 `~/.ssh/authorized_keys`。先生成并复制公钥：

```bash
ssh-keygen -t ed25519 -C "your.name@dbappsecurity.com.cn"
pbcopy < ~/.ssh/id_ed25519.pub
```

如果服务器支持 `ssh-copy-id`，也可以直接安装公钥：

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub <user>@<upload-host>
```

验证上传服务器登录：

```bash
ssh <user>@<upload-host>
```

如果暂时没有 SSH key，也可以在本机 `.env` 中配置 `REPORT_UPLOAD_PASSWORD` 作为临时方案。密码只能保存在本机 `.env`，不要写入 `.env.example`、README、聊天记录或提交到 Git。

## 维护 npm 安装器

根目录的 `package.json` 和 `bin/install.js` 只用于发布轻量 npm 安装器。npm 包内容只包含安装脚本和 README，真正的 skills 仍从 GitHub 仓库安装。

发布前检查：

```bash
node --check bin/install.js
npm pack --dry-run
```

首次发布：

```bash
npm login
npm publish --access public
```

后续更新安装器本身时，先提升 `package.json` 的 `version`，再执行：

```bash
npm publish --access public
```

如果只是更新 skills 内容，不需要重新发布 npm 包；把 GitHub 仓库更新并推送即可。

## 维护者

姚瑞泉
