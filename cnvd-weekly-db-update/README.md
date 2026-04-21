# CNVD 每周数据库更新 - 详细说明

## 概述

本 skill 用于自动化处理 CNVD（国家信息安全漏洞共享平台）每周发布的 XML 漏洞数据更新。

通过 SSH Key 免密登录 + Docker 容器操作，一键完成：
- XML 文件上传
- Docker 容器拷贝
- 数据解析入库
- 文件归档

---

## 一、前提条件

### 1.1 SSH Key 免密登录

脚本依赖 SSH Key 免密登录服务器。配置方法：

```bash
# 生成无密码的 SSH Key（推荐无密码，自动化更方便）
ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa

# 复制公钥到服务器（输入一次服务器密码）
ssh-copy-id -i ~/.ssh/id_rsa.pub root@10.50.10.8

# 测试免密登录
ssh root@10.50.10.8 "echo 'SSH Key 配置成功'"
```

**注意事项**：
- 建议使用 `-N ""` 生成无密码的密钥，避免每次需要输入 passphrase
- 如果已有密钥但设置了 passphrase，可重新生成覆盖

### 1.2 服务器信息

| 配置项 | 值 |
|--------|-----|
| IP 地址 | `10.50.10.8` |
| 登录用户 | `root` |
| 登录方式 | SSH Key |
| Docker 容器 | `crawlab` |

### 1.3 目录结构

**服务器端**：
```
/tmp/                          # 上传临时目录
/opt/cnvd/                     # CNVD 数据处理目录
├── parse.py                   # 解析脚本（已存在）
├── new/                       # 新 XML 文件存放目录
└── cnvd/                      # 已处理文件归档目录
```

**Docker 容器内**：
```
/opt/cnvd/                     # 容器内目录（与宿主机映射）
├── parse.py
├── new/
└── cnvd/
```

---

## 二、使用方法

### 2.1 下载 XML 文件

1. 登录 CNVD 官网：https://www.cnvd.org.cn/
2. 进入「统计查询」→「共享数据下载」
3. 下载每周更新的 XML 文件
4. 文件保存到本地 `~/Downloads` 目录

**文件命名格式**：`YYYY-MM-DD_YYYY-MM-DD.xml`

示例：
- `2026-03-09_2026-03-15.xml`
- `2026-04-06_2026-04-12.xml`

### 2.2 执行一键脚本

```bash
# 默认从 ~/Downloads 读取 XML 文件
/Users/yao/.claude/skills/cnvd-weekly-db-update/scripts/cnvd_weekly_update.sh

# 指定其他目录
/Users/yao/.claude/skills/cnvd-weekly-db-update/scripts/cnvd_weekly_update.sh /path/to/xml/files
```

### 2.3 执行流程

脚本自动完成以下步骤：

```
[Step 1] 检查 XML 文件
        ↓
[Step 2] SCP 上传到服务器 /tmp
        ↓
[Step 3] SSH 登录服务器
        ├── Docker cp 拷贝到容器 /opt/cnvd/new/
        ├── 执行 parse.py 解析入库
        └── 归档文件到 /opt/cnvd/cnvd/
        ↓
[完成] 所有 XML 已解析入库并归档
```

---

## 三、脚本详解

### 3.1 cnvd_weekly_update.sh

```bash
#!/bin/bash
# CNVD 每周数据库更新脚本

# 配置
SERVER="10.50.10.8"
SERVER_USER="root"
CONTAINER="crawlab"

# Step 1: 检查 XML 文件
XML_FILES=$(ls "$XML_DIR"/2026-0*.xml)

# Step 2: SCP 上传
scp "$XML_DIR"/2026-0*.xml "$SERVER_USER@$SERVER:/tmp/"

# Step 3: SSH 远程执行
ssh "$SERVER_USER@$SERVER" << 'REMOTE_SCRIPT'
# Docker cp
docker cp *.xml crawlab:/opt/cnvd/new/

# 执行解析
docker exec crawlab python3 /opt/cnvd/parse.py

# 归档
docker exec crawlab bash -c "cd /opt/cnvd/new && mv * ../cnvd/"
REMOTE_SCRIPT
```

### 3.2 parse.py（服务器已存在）

解析脚本位于 `/opt/cnvd/parse.py`，功能：
- 读取 `/opt/cnvd/new/` 目录下的 XML 文件
- 解析漏洞数据结构
- 写入数据库
- 输出执行结果（成功/失败条数）

---

## 四、执行结果示例

```bash
=== CNVD 每周数据库更新 ===
XML 目录: /Users/yao/Downloads

[Step 1] 检查 XML 文件...
找到文件:
  - 2026-04-06_2026-04-12.xml

[Step 2] 上传文件到服务器 10.50.10.8...
上传完成

[Step 3] 在服务器上执行操作...
拷贝文件到 Docker 容器...
  docker cp 2026-04-06_2026-04-12.xml crawlab:/opt/cnvd/new/
进入容器执行解析脚本...
插入报告: CNVD-2026-16412, 严重程度: Low
插入报告: CNVD-2026-16411, 严重程度: Medium
...
文件 2026-04-06_2026-04-12.xml 处理完成: 成功 163, 失败 0

=== 更新完成 ===
所有 XML 文件已解析入库并归档
```

---

## 五、常见问题

### 5.1 SSH 连接失败

**症状**：`Permission denied (publickey,password)`

**解决方案**：
```bash
# 检查 SSH Key 是否正确配置
ssh -i ~/.ssh/id_rsa root@10.50.10.8 "echo test"

# 重新配置 SSH Key
ssh-copy-id -i ~/.ssh/id_rsa.pub root@10.50.10.8
```

### 5.2 未找到 XML 文件

**症状**：`错误: 未找到 XML 文件`

**解决方案**：
- 确认 XML 文件在 `~/Downloads` 目录
- 确认文件名格式为 `2026-XX-XX_2026-XX-XX.xml`

### 5.3 Docker 容器未运行

**症状**：`docker cp` 报错

**解决方案**：
```bash
ssh root@10.50.10.8 "docker ps | grep crawlab"
# 如果容器停止，启动它
ssh root@10.50.10.8 "docker start crawlab"
```

### 5.4 数据已存在（成功 0）

**说明**：如果显示 `成功 0, 失败 0`，说明该周数据已入库，无需重复处理。

---

## 六、维护说明

### 6.1 更新服务器配置

如需更换服务器或容器，修改脚本中的配置变量：

```bash
SERVER="新IP地址"
CONTAINER="新容器名"
```

### 6.2 更新解析脚本

`parse.py` 位于服务器 `/opt/cnvd/`，如有更新需求请联系服务器管理员。

---

## 七、相关链接

- [CNVD 官网](https://www.cnvd.org.cn/)
- CNVD 共享数据下载：官网 → 统计查询 → 共享数据下载

---

## 八、钉钉机器人通知

本 skill 支持在执行完成或失败时向钉钉自定义机器人推送 Markdown 消息。

### 8.1 配置

```bash
cd /Users/yao/.claude/skills/cnvd-weekly-db-update
cp .env.example .env
vim .env
```

`.env` 中填写：

```env
DINGTALK_WEBHOOK=你的钉钉机器人 webhook
DINGTALK_SECRET=
DINGTALK_ENABLED=true
```

`.env` 已被仓库忽略，不要提交真实 webhook。

### 8.2 自动推送

`scripts/cnvd_weekly_update.sh` 执行成功后会自动推送：

- Skill 名称
- 执行状态
- XML 目录
- 已处理 XML 文件

如果脚本异常退出，会推送失败状态和退出码。

### 8.3 手动推送

```bash
python3 scripts/dingtalk_notify.py \
  --title "CNVD 每周数据库更新完成" \
  --status success \
  --text "所有 XML 文件已解析入库并归档" \
  --output "/Users/yao/Downloads"
```
