# -*- coding: utf-8 -*-
"""一键打包脚本（推荐方式）。

在 PyCharm 里打开本项目 → 右键本文件 → Run 'build'，即可自动打包出 exe。
完全不需要配置系统 PATH，也不需要双击 .bat。

命令行方式： python build.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print('>>', ' '.join(cmd))
    return subprocess.call(cmd)


def main():
    print('=' * 56)
    print('  桌面宠物 · 一键打包')
    print('=' * 56)

    # 1) 安装依赖
    print('[1/3] 安装依赖 ...')
    if run([sys.executable, '-m', 'pip', 'install', '-r',
            os.path.join(ROOT, 'requirements.txt')]) != 0:
        print('依赖安装失败，请检查网络后重试。')
        input('按回车退出...')
        sys.exit(1)

    # 2) 打包 exe
    print('[2/3] 打包 exe ...')
    icon = os.path.join(ROOT, 'icon', 'cat1.ico')
    cmd = [sys.executable, '-m', 'PyInstaller',
           '--noconfirm', '--clean', '--onefile', '--windowed',
           '--name', '桌面宠物',
           '--icon', icon,
           'main.py']
    if run(cmd) != 0:
        print('打包失败，请查看上方报错信息。')
        input('按回车退出...')
        sys.exit(1)

    # 3) 复制宠物图片目录到 exe 旁边
    print('[3/3] 复制宠物图片目录 ...')
    dist = os.path.join(ROOT, 'dist')
    pets_dst = os.path.join(dist, 'pets')
    os.makedirs(pets_dst, exist_ok=True)
    for f in os.listdir(os.path.join(ROOT, 'pets')):
        shutil.copy2(os.path.join(ROOT, 'pets', f), os.path.join(pets_dst, f))

    exe_path = os.path.join(dist, '桌面宠物.exe')
    print()
    print('=' * 56)
    print('  打包完成！')
    print('  exe 位置：', exe_path)
    print('  宠物图片：', pets_dst, '（可直接增删图片换形象）')
    print('=' * 56)

    # 4) 尝试帮用户打开 dist 文件夹
    try:
        if os.name == 'nt':
            os.startfile(dist)      # Windows 资源管理器
    except Exception:
        pass


if __name__ == '__main__':
    main()
