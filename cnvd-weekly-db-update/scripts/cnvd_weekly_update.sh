#!/bin/bash
# CNVD 每周数据库更新脚本
# 用法: ./cnvd_weekly_update.sh [xml文件目录]
# 默认使用 ~/Downloads

set -e

# 配置
SERVER="10.50.10.8"
SERVER_USER="root"
CONTAINER="crawlab"
REMOTE_TMP="/tmp"
CONTAINER_NEW="/opt/cnvd/new"
CONTAINER_CNVD="/opt/cnvd/cnvd"

# 参数（展开 ~ 为实际路径）
XML_DIR="${1:-$HOME/Downloads}"

echo "=== CNVD 每周数据库更新 ==="
echo "XML 目录: $XML_DIR"
echo ""

# Step 1: 检查 XML 文件
echo "[Step 1] 检查 XML 文件..."
XML_FILES=$(ls "$XML_DIR"/2026-0*.xml 2>/dev/null || true)
if [ -z "$XML_FILES" ]; then
    echo "错误: 未找到 XML 文件 (格式: 2026-XX-XX_2026-XX-XX.xml)"
    echo "请先从 CNVD 官网下载 XML 文件到 $XML_DIR"
    exit 1
fi
echo "找到文件:"
for f in $XML_FILES; do
    echo "  - $(basename $f)"
done
echo ""

# Step 2: 上传到服务器
echo "[Step 2] 上传文件到服务器 $SERVER..."
scp "$XML_DIR"/2026-0*.xml "$SERVER_USER@$SERVER:$REMOTE_TMP/"
echo "上传完成"
echo ""

# Step 3: 拷贝到 Docker 容器 + 执行解析
echo "[Step 3] 在服务器上执行操作..."
ssh "$SERVER_USER@$SERVER" << 'REMOTE_SCRIPT'
set -e

echo "进入 /tmp 目录..."
cd /tmp

# 列出 XML 文件
XML_FILES=$(ls 2026-0*.xml)
echo "待处理文件: $XML_FILES"

# 逐个拷贝到容器
echo "拷贝文件到 Docker 容器..."
for f in $XML_FILES; do
    echo "  docker cp $f crawlab:/opt/cnvd/new/"
    docker cp "$f" crawlab:/opt/cnvd/new/
done

# 进入容器执行解析
echo "进入容器执行解析脚本..."
docker exec crawlab python3 /opt/cnvd/parse.py

# 归档文件
echo "归档处理完成的文件..."
docker exec crawlab bash -c "cd /opt/cnvd/new && mv * ../cnvd/ 2>/dev/null || true"

echo "服务器端操作完成"
REMOTE_SCRIPT

echo ""
echo "=== 更新完成 ==="
echo "所有 XML 文件已解析入库并归档"