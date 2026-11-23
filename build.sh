#!/usr/bin/env bash
# 桌面宠物 - macOS / Linux 打包脚本
set -e
cd "$(dirname "$0")"
echo "[1/3] 安装依赖..."
python3 -m pip install -r requirements.txt
echo "[2/3] 打包..."
python3 -m PyInstaller --noconfirm --clean --onefile --windowed \
    --name 桌面宠物 --icon icon/cat1.ico main.py
echo "[3/3] 复制宠物图片目录..."
mkdir -p dist/pets
cp pets/* dist/pets/ 2>/dev/null || true
echo
echo "打包完成：dist/桌面宠物"
echo "宠物图片目录：dist/pets/（可直接增删图片）"
