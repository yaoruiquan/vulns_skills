# cnvd-weekly-db-update

通过 SSH Key 免密登录 + Docker 容器操作，自动完成 CNVD 每周 XML 漏洞数据更新。

## 功能

- 将 CNVD 官网下载的 XML 数据文件上传到内部服务器
- 通过 Docker cp 拷贝到容器
- 自动执行解析脚本入库
- 处理完成后归档文件
- 可选推送钉钉通知（需配置 webhook）

## 使用流程

### 第一步：安装 Claude Code（或其他 agent 工具）

参见官网文档安装配置。

### 第二步：安装本 skill

一句指令，通过 GitHub 地址安装到 agent 工具：

```
claude skills install <GitHub 地址>
```

如果新用户没有 SSH key，优先使用 HTTPS 地址安装；本 skill 还需要登录内部服务器执行上传和 Docker 操作，必须先按 [上级 README 的 SSH key 说明](../README.md#没有-ssh-key-怎么办) 配置服务器免密或申请管理员加入公钥。

### 第三步：手动配置 .env

```
cd /root/.agents/skills/cnvd-weekly-db-update
cp .env.example .env
vim .env
```

填写钉钉 webhook 配置（agent 会引导你完成）。

本 skill 默认通过 SSH key 免密访问内部服务器；不建议在文档或 Git 中保存服务器密码。

### 第四步：启动 agent

```
cd /data/work/jobs/{job_id}
claude
```

### 第五步：调用 skill

给 agent 一句指令：

```
安装依赖并初始化环境
```

agent 会自动执行以下操作：

```
# 检测 SSH Key 免密登录
ssh root@10.50.10.8 "echo 'SSH OK'"

# 初始化配置
cp .env.example .env
```

### 第六步：上传 XML 并执行数据库更新

通过前端或 API 先上传 CNVD 周库 XML，文件必须位于当前 job：

```
input/xml/2026-XX-XX_2026-XX-XX.xml
```

然后调用 skill。脚本默认只读取当前 job 的 `input/xml/*.xml`，不会读取 `~/Downloads` 或本机绝对路径。

```
/cnvd-weekly-db-update
```

执行前确认运行配置：

- `check` 模式只检查 XML 和远端环境，不写入数据库。
- `update` 模式需要同时把 `dry_run` 设为 `false`，才会真正上传并解析入库。

## 目录结构

```
cnvd-weekly-db-update/
├── SKILL.md              # agent 执行指令（流程、规则、约束）
├── README.md             # 本文件（用户使用说明）
├── .env.example          # 配置模板，首次使用 cp 为 .env
├── scripts/              # 实现脚本
│   ├── cnvd_weekly_update.sh
│   └── dingtalk_notify.py
└── references/           # agent 执行参考
    └── troubleshooting.md
```
