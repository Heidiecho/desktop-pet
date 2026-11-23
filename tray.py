# -*- coding: utf-8 -*-
"""系统托盘：图标取自 cat1（或 pets 里第一张），猫尽量占满图标，不缩小。"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QImage, QPixmap
from PyQt5.QtWidgets import QMenu, QSystemTrayIcon

from imgutils import cropped_pixmap
from storage import pets_dir

TRAY_SIZE = 64


def make_tray_icon():
    """用 cat1（不存在则用第一张图）生成占满图标的托盘图标。"""
    folder = pets_dir()
    path = os.path.join(folder, 'cat1.png')
    if not os.path.isfile(path):
        for fn in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            if fn.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                path = os.path.join(folder, fn)
                break
    pix = cropped_pixmap(path)   # 已裁掉透明边
    if pix.isNull():
        # 兜底：画一个圆点
        img = QImage(TRAY_SIZE, TRAY_SIZE, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        return QIcon(QPixmap.fromImage(img))
    # 覆盖式缩放：让猫占满 64x64，不留多余透明边
    scaled = pix.scaled(TRAY_SIZE, TRAY_SIZE, Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation)
    x = (scaled.width() - TRAY_SIZE) // 2
    y = (scaled.height() - TRAY_SIZE) // 2
    scaled = scaled.copy(x, y, TRAY_SIZE, TRAY_SIZE)
    icon = QIcon()
    icon.addPixmap(scaled)
    icon.addPixmap(scaled.scaled(32, 32, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
    icon.addPixmap(scaled.scaled(16, 16, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
    return icon


class PetTray(QSystemTrayIcon):
    def __init__(self, store, pet, app):
        super().__init__(make_tray_icon())
        self._pet = pet
        self._app = app
        self.setToolTip('桌面宠物')
        menu = QMenu()
        menu.addAction('显示宠物', pet.show_from_tray)
        menu.addAction('新建待办…', pet._open_todo)
        menu.addAction('本周统计…', pet._open_stats)
        menu.addAction('切换形象', pet._switch_image)
        menu.addSeparator()
        menu.addAction('退出', app.quit)
        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self.show()

    def _on_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._pet.show_from_tray()

    def update_status(self, text):
        self.setToolTip('桌面宠物　|　' + text)
