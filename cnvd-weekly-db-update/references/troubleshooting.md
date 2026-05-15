# 常见问题排查

## 一、SSH 相关问题

### 1.1 Permission denied

**错误信息**：
```
Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password)
```

**排查步骤**：

```bash
# 1. 检查 SSH Key 文件是否存在
ls -la ~/.ssh/id_rsa ~/.ssh/id_rsa.pub

# 2. 测试 SSH 连接
ssh -i ~/.ssh/id_rsa root@10.50.10.8 "echo test"

# 3. 检查服务器上的 authorized_keys
ssh root@10.50.10.8 "cat ~/.ssh/authorized_keys"
```

**解决方案**：

```bash
# 重新生成无密码的 SSH Key
ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa

# 复制公钥到服务器
ssh-copy-id -i ~/.ssh/id_rsa.pub root@10.50.10.8
```

### 1.2 ssh-agent 无密钥缓存

**错误信息**：
```
The agent has no identities.
```

**解决方案**：

```bash
# 添加密钥到 ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa
```

---

## 二、文件上传问题

### 2.1 未找到 XML 文件

**错误信息**：
```
错误: 未找到 XML 文件 (格式: 2026-XX-XX_2026-XX-XX.xml)
```

**排查步骤**：

```bash
# 检查当前 job 输入目录
ls input/xml/*.xml

# 检查文件名格式
ls input/xml/2026-*.xml
```

**解决方案**：
- 确保文件名格式正确：`YYYY-MM-DD_YYYY-MM-DD.xml`
- 确保文件已通过前端或 API 上传到当前 job 的 `input/xml/` 目录

### 2.2 SCP 上传中断

**解决方案**：

```bash
# 使用 -C 启用压缩
scp -C input/xml/2026-*.xml root@10.50.10.8:/tmp/
```

---

## 三、Docker 相关问题

### 3.1 容器未运行

**错误信息**：
```
Error: No such container: crawlab
```

**排查步骤**：

```bash
ssh root@10.50.10.8 "docker ps -a | grep crawlab"
```

**解决方案**：

```bash
# 启动容器
ssh root@10.50.10.8 "docker start crawlab"
```

### 3.2 docker cp 权限问题

**排查步骤**：

```bash
ssh root@10.50.10.8 "docker exec crawlab ls -la /opt/cnvd/new/"
```

---

## 四、解析脚本问题

### 4.1 parse.py 执行报错

**排查步骤**：

```bash
ssh root@10.50.10.8 "docker exec crawlab ls /opt/cnvd/new/"
ssh root@10.50.10.8 "docker exec crawlab cat /opt/cnvd/parse.py | head -20"
```

### 4.2 数据入库失败

**症状**：`成功 0, 失败 N`

**排查**：
- 检查 XML 文件格式是否正确
- 检查数据库连接状态
- 查看 parse.py 详细错误日志

---

## 五、文件归档问题

### 5.1 mv 命令失败

**排查步骤**：

```bash
ssh root@10.50.10.8 "docker exec crawlab ls /opt/cnvd/new/"
ssh root@10.50.10.8 "docker exec crawlab ls /opt/cnvd/cnvd/"
```

---

## 六、网络问题

### 6.1 无法连接服务器

**排查步骤**：

```bash
# Ping 测试
ping 10.50.10.8

# SSH 端口测试
nc -zv 10.50.10.8 22
```

### 6.2 VPN/跳板机问题

如果服务器需要通过 VPN 或跳板机访问：
- 确保 VPN 已连接
- 确保跳板机配置正确

---

## 七、快速诊断命令

```bash
# 一键诊断
ssh root@10.50.10.8 << 'EOF'
echo "=== Docker 状态 ==="
docker ps | grep crawlab

echo "=== /opt/cnvd 目录 ==="
docker exec crawlab ls -la /opt/cnvd/

echo "=== new 目录内容 ==="
docker exec crawlab ls /opt/cnvd/new/

echo "=== cnvd 目录内容（最近5个） ==="
docker exec crawlab ls -t /opt/cnvd/cnvd/ | head -5
EOF
```
