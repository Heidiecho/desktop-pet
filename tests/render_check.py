# -*- coding: utf-8 -*-
"""离屏渲染验证：宠物窗口 / 云朵弹窗 / 托盘图标 → PNG"""
import os
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

app = QApplication([])

from storage import Store
from scheduler import ReminderEngine
from pet_window import PetWindow
from cloud_popup import CloudPopup
from tray import make_tray_icon

base = '/tmp/pet_render'
os.makedirs(base, exist_ok=True)

store = Store(base_dir=base + '/store')
eng = ReminderEngine(store.config, store.daily)
pet = PetWindow(store, eng)

# 1) 宠物窗口
pet.grab().save(base + '/pet_window.png')

# 2) 云朵弹窗（站立提醒，带 3 个按钮，尾巴朝下）
pop = CloudPopup('已经专注满 1 小时啦，站起来活动一下，伸伸懒腰、喝口水吧！',
                 [('确认', 'ok'), ('放松5分钟', 'relax5'), ('放松10分钟', 'relax10')], tail='bottom')
pop.show()
app.processEvents()
pop.grab().save(base + '/popup_stand.png')
pop.close()

# 3) 云朵弹窗（尾巴朝上，短文本）
pop2 = CloudPopup('护眼时间到：请向 20 米外远眺 6 秒，让眼睛休息一下～',
                  [('已完成', 'ok')], tail='top')
pop2.show()
app.processEvents()
pop2.grab().save(base + '/popup_eye.png')
pop2.close()

# 3.5) 待办提醒弹窗
pop3 = CloudPopup('待办「完成PPT」还有 30 分钟就到截止时间啦！',
                  [('知道了', 'ok'), ('标记完成', 'done')], tail='bottom')
pop3.show()
app.processEvents()
pop3.grab().save(base + '/popup_todo.png')
pop3.close()

# 4) 托盘图标（猫应占满图标）
icon = make_tray_icon()
pm = icon.pixmap(64, 64)
pm.save(base + '/tray_icon_64.png')
pm32 = icon.pixmap(32, 32)
pm32.save(base + '/tray_icon_32.png')

# 5) 统计对话框渲染
from dialogs import StatsDialog
store.add_today('stand', 3)
store.add_today('eye', 4)
store.add_today('relax_cnt', 1)
store.add_today('relax_sec', 600)
dlg = StatsDialog(store)
dlg.show()
app.processEvents()
dlg.grab().save(base + '/stats_dialog.png')
dlg.close()

# 6) 待办对话框渲染
from dialogs import TodoDialog
store.add_todo('写周报')
store.add_todo('运动 30 分钟')
store.todos['todos'][0]['done'] = True
td = TodoDialog(store)
td.show()
app.processEvents()
td.grab().save(base + '/todo_dialog.png')
td.close()

print('rendered to', base)
