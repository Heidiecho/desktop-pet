# -*- coding: utf-8 -*-
"""冒烟测试：提醒事件 -> 云朵弹窗 -> 点击按钮 -> 状态切换 -> 排队弹窗"""
import os
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication

app = QApplication([])

from storage import Store
from scheduler import ReminderEngine
from pet_window import PetWindow

base = '/tmp/pet_smoke'
store = Store(base_dir=base + '/store')
eng = ReminderEngine(store.config, store.daily)
pet = PetWindow(store, eng)
assert pet._current.endswith('.png'), '应加载到宠物图片'
print('PASS 宠物图片加载:', os.path.basename(pet._current))

# 站立提醒 -> 弹窗出现
pet.queue_reminder(('stand', {}))
assert pet.popup_open()
print('PASS 站立提醒弹窗已弹出')

# 点击“放松10分钟” -> 状态切换为放松中
pet._on_popup_action(('stand', {}), 'relax10')
assert eng.status == 'relaxing', eng.status
assert eng.daily[store.today_str()]['relax_cnt'] == 1
assert not pet.popup_open()
print('PASS 放松10分钟 -> 状态=放松中，弹窗已关')

# 弹窗排队：放松期间又来了护眼事件 -> 排队，等放松结束后弹出
pet.queue_reminder(('eye', {}))
pet.queue_reminder(('eye', {}))  # 重复类型应被去重
assert len(pet._pending) == 1
print('PASS 弹窗排队 + 重复去重')

# 放松到期回到专注
import datetime
from scheduler import _parse
end = _parse(eng.relax_end_ts)
eng.relax_end_ts = (datetime.datetime.now() - datetime.timedelta(seconds=1)).isoformat(timespec='seconds')
ev = eng.tick(datetime.datetime.now())
assert eng.status == 'focusing'
print('PASS 放松结束自动回到专注')

# 排队中的护眼弹窗自动弹出
assert pet.popup_open()
print('PASS 排队弹窗自动接续弹出')

# 休息提醒确认 -> 休息中
pet._on_popup_action(('eye', {}), 'ok')
pet.queue_reminder(('rest', {}))
assert pet.popup_open()
pet._on_popup_action(('rest', {}), 'ok')
assert eng.status == 'resting'
while pet.popup_open():               # 清掉排队中自动接续的弹窗
    pet._on_popup_action(('rest', {}), 'ok')
assert not pet.popup_open() and not pet._pending
print('PASS 休息提醒 -> 状态=休息中')

# 待办 + 统计
store.add_todo('测试待办')
assert len(store.todos['todos']) == 1
store.set_todo_done(store.todos['todos'][0]['id'], True)
assert store.todos['todos'][0]['done'] is True
assert store.daily[store.today_str()]['todo_done'] == 1
print('PASS 待办添加/完成/统计')

# 待办三段式提醒：提醒时间 -> DDL前30分钟 -> DDL到点
import datetime
now = datetime.datetime.now()
t = store.add_todo('完成PPT',
                   remind_ts=(now - datetime.timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M'),
                   ddl_ts=(now + datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M'))
pet.check_todo_reminders(now)
assert t['remind_done'] and t.get('remind_ts') and not t['ddl30_done'], '应只触发提醒时间那次'
assert pet.popup_open(), '提醒时间到应弹窗'
# 弹窗里点“标记完成” -> 待办完成，后续不再提醒
assert pet._popup is not None
pet._on_popup_action(('todo', {'id': t['id']}), 'done')
assert store.todos['todos'][-1]['done'] is True
assert not pet.popup_open()
pet.check_todo_reminders(now + datetime.timedelta(minutes=40))
assert not pet.popup_open() and not pet._pending, '已完成待办不应再提醒'
print('PASS 待办三段式提醒（提醒时间→标记完成→不再提醒）')

# 未完成待办：DDL前30分钟 与 DDL 到点各提醒一次
t2 = store.add_todo('写周报',
                    remind_ts=(now - datetime.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
                    ddl_ts=(now + datetime.timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M'))
pet.check_todo_reminders(now)
assert t2['remind_done'], '过去时间的提醒应立即触发'
pet._on_popup_action(('todo', {'id': t2['id']}), 'ok')
# 现在处于 DDL 前 30 分钟窗口内，应触发 ddl30
pet.check_todo_reminders(now)
assert t2['ddl30_done'], 'DDL前30分钟应弹窗'
pet._on_popup_action(('todo', {'id': t2['id']}), 'ok')
assert not pet.popup_open()
print('PASS 待办 DDL 前 30 分钟提醒')

# 模拟 DDL 前 1 秒仍未完成：ddl30 已弹过，不重复；到 DDL 触发
t2['ddl30_done'] = False
pet.check_todo_reminders(now)
assert t2['ddl30_done'], 'DDL前30分钟内仍应触发'
pet._on_popup_action(('todo', {'id': t2['id']}), 'ok')
ddl_time = now + datetime.timedelta(minutes=21)
pet.check_todo_reminders(ddl_time)
assert t2['ddl_done'], 'DDL到点应弹窗'
assert pet.popup_open()
print('PASS 待办 DDL 到点提醒')

# 换图（双击路径）
before = pet._current
pet._switch_image()
assert pet._current != before
print('PASS 双击换图')

# 滚轮缩放（含防出画上限）
from PyQt5.QtCore import QPoint, QPointF, Qt
from PyQt5.QtGui import QWheelEvent
from imgutils import cropped_pixmap
pet._scale = 1.0
pix = cropped_pixmap(pet._current)
scr = QApplication.primaryScreen().availableGeometry()
max_s = max(0.2, min(3.0, (scr.width() - 20) / max(1, pix.width()),
                     (scr.height() - 40) / max(1, pix.height())))
e = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, 120),
                Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
pet.wheelEvent(e)
assert abs(pet._scale - min(max_s, 1.1)) < 1e-6, pet._scale
e2 = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120),
                 Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
pet.wheelEvent(e2)
assert abs(pet._scale - min(max_s, 1.1) * 0.9) < 1e-6, pet._scale   # 放大再缩小
print('PASS 滚轮缩放（含防出画上限）')

print('OK 冒烟测试全部通过')
