# CNVD 每周数据库更新

通过 SSH Key 免密登录 + Docker 操作完成 CNVD 每周 XML 数据更新。

---

## 一、SSH Key 免密登录配置

### 1.1 生成 SSH Key（如已有可跳过）

```bash
ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa
```

### 1.2 复制公钥到服务器

```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub root@10.50.10.8
```

### 1.3 测试免密登录

```bash
ssh root@10.50.10.8 "echo 'SSH Key 配置成功'"
```

---

## 二、执行步骤

### Step 0: 检查 SSH 免密登录

调用本 skill 后，首先检查 SSH Key 配置：

```
ssh root@10.50.10.8 "echo 'SSH OK'"
```

**检查失败**：提示用户配置 SSH Key（参见上文）

**检查成功**：继续执行脚本

### Step 1: 下载 XML 文件

手动从 CNVD 官网下载 XML 到 `~/Downloads`：
- 官网 → 统计查询 → 共享数据下载
- 文件格式：`2026-XX-XX_2026-XX-XX.xml`

### Step 2: 执行一键脚本

```bash
/Users/yao/.claude/skills/cnvd-weekly-db-update/scripts/cnvd_weekly_update.sh
```

脚本自动完成：SCP 上传 → Docker cp → parse.py 解析 → 文件归档 → 钉钉通知（如果 `.env` 已配置 `DINGTALK_WEBHOOK`）

---

## 三、详细说明

参见 [README.md](README.md)。

---

## 四、文件结构

```
cnvd-weekly-db-update/
├── SKILL.md              # 本文件
├── README.md             # 详细说明
├── .env.example          # 钉钉 webhook 配置模板
├── scripts/
│   ├── cnvd_weekly_update.sh
│   └── dingtalk_notify.py
└── references/
    └── troubleshooting.md
```

---

## 五、钉钉通知

配置方式：

```bash
cd /Users/yao/.claude/skills/cnvd-weekly-db-update
cp .env.example .env
vim .env
```

填写 `DINGTALK_WEBHOOK` 后，`cnvd_weekly_update.sh` 会在成功或失败时自动推送消息到钉钉群。
