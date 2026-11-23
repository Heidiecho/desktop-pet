# -*- coding: utf-8 -*-
"""桌面宠物 —— 程序入口。

运行：python main.py （或双击打包后的 exe/app）
功能：每小时站立提醒、20 分钟护眼提醒、22 点休息提醒、
      待办事项、每周统计、托盘、云朵弹窗。
"""
import datetime
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from scheduler import ReminderEngine
from storage import Store
from pet_window import PetWindow
from tray import PetTray


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName('桌面宠物')

    store = Store()
    engine = ReminderEngine(store.config, store.daily)
    pet = PetWindow(store, engine)
    tray = PetTray(store, pet, app)

    tick = [0]

    def on_tick():
        now = datetime.datetime.now()
        for ev in engine.tick(now):
            pet.queue_reminder(ev)
        pet.check_todo_reminders(now)   # 待办三段式提醒
        pet.update_badge()              # 头顶状态标签
        # 每 5 秒落盘一次（引擎状态变化时也立刻保存）
        tick[0] += 1
        if engine.dirty or tick[0] % 5 == 0:
            engine.sync_to_config()
            store.save_config()
            store.save_daily()
        tray.update_status(pet._status_text())

    timer = QTimer()
    timer.timeout.connect(on_tick)
    timer.start(1000)

    def on_quit():
        engine.sync_to_config()
        store.save_config()
        store.save_daily()

    app.aboutToQuit.connect(on_quit)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
