# -*- coding: utf-8 -*-
"""待办事项对话框 + 每周统计对话框。"""
import datetime

from PyQt5.QtCore import Qt, QRectF, QDateTime
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import (QDateTimeEdit, QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
                             QWidget)

_DT_FMT = 'MM/dd HH:mm'
_SAVE_FMT = 'yyyy-MM-dd HH:mm'


def _short(ts):
    """"YYYY-MM-DD HH:MM" -> "MM/dd HH:mm"；空返回 ''。"""
    if not ts:
        return ''
    return ts[5:]


# ==================== 待办事项 ====================
class TodoDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle('待办事项')
        self.setMinimumSize(420, 420)
        self.store = store

        lay = QVBoxLayout(self)

        # 内容输入
        self.edit = QLineEdit()
        self.edit.setPlaceholderText('输入新待办，如：完成PPT…')
        lay.addWidget(self.edit)

        # 提醒时间 / 截止时间
        row = QHBoxLayout()
        row.addWidget(QLabel('提醒时间'))
        self.remind_edit = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.remind_edit.setDisplayFormat(_DT_FMT)
        self.remind_edit.setCalendarPopup(True)
        row.addWidget(self.remind_edit)
        row.addWidget(QLabel('截止时间'))
        self.ddl_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.ddl_edit.setDisplayFormat(_DT_FMT)
        self.ddl_edit.setCalendarPopup(True)
        row.addWidget(self.ddl_edit)
        lay.addLayout(row)

        add_btn = QPushButton('添加')
        add_btn.setDefault(True)
        lay.addWidget(add_btn)

        self.listw = QListWidget()
        self.listw.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self.listw, 1)

        bottom = QHBoxLayout()
        tip = QLabel('勾选 = 完成｜提醒规则：提醒时间弹一次，截止前30分钟再弹一次，截止时再弹一次')
        tip.setWordWrap(True)
        tip.setStyleSheet('color:#94a3b8; font-size:11px;')
        del_btn = QPushButton('删除选中')
        bottom.addWidget(tip, 1)
        bottom.addWidget(del_btn)
        lay.addLayout(bottom)

        add_btn.clicked.connect(self._add_new)
        self.edit.returnPressed.connect(self._add_new)
        del_btn.clicked.connect(self._delete_selected)

        for t in store.todos['todos']:
            self._append_item(t)

    def _append_item(self, t):
        text = t['text']
        if t.get('remind_ts') or t.get('ddl_ts'):
            text += '　[提醒 {} / 截止 {}]'.format(_short(t.get('remind_ts')),
                                                 _short(t.get('ddl_ts')))
        item = QListWidgetItem()
        item.setText(text)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if t['done'] else Qt.Unchecked)
        item.setData(Qt.UserRole, t['id'])
        tips = ['创建于 ' + t['created']]
        if t.get('remind_ts'):
            tips.append('提醒时间 ' + t['remind_ts'])
        if t.get('ddl_ts'):
            tips.append('截止时间 ' + t['ddl_ts'])
        if t.get('done_ts'):
            tips.append('完成于 ' + t['done_ts'])
        item.setToolTip('\n'.join(tips))
        f = item.font()
        f.setStrikeOut(bool(t['done']))
        item.setFont(f)
        self.listw.addItem(item)

    def _add_new(self):
        text = self.edit.text().strip()
        if not text:
            return
        remind = self.remind_edit.dateTime().toString(_SAVE_FMT)
        ddl = self.ddl_edit.dateTime().toString(_SAVE_FMT)
        t = self.store.add_todo(text, remind_ts=remind, ddl_ts=ddl)
        self._append_item(t)
        self.edit.clear()

    def _on_item_changed(self, item):
        tid = item.data(Qt.UserRole)
        done = item.checkState() == Qt.Checked
        self.store.set_todo_done(tid, done)
        f = item.font()
        f.setStrikeOut(done)
        item.setFont(f)

    def _delete_selected(self):
        for it in self.listw.selectedItems():
            self.store.delete_todo(it.data(Qt.UserRole))
            self.listw.takeItem(self.listw.row(it))


# ==================== 每周统计 ====================
class BarChart(QWidget):
    """简单柱状图：每天 站立/护眼/放松次数。"""

    def __init__(self, days, series, parent=None):
        super().__init__(parent)
        self._days = days          # [(label, {key: value}), ...]
        self._series = series      # [(key, 颜色), ...]
        self.setFixedHeight(170)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        top, bottom = 14, h - 22
        left, right = 20, w - 10
        n = len(self._days)
        if n == 0:
            return
        slot = (right - left) / n
        bar_w = min(14.0, slot * 0.22)
        group = bar_w * len(self._series)
        for i, (label, vals) in enumerate(self._days):
            cx = left + slot * i + slot / 2
            x0 = cx - group / 2
            maxv = max((vals.get(k, 0) for k, _ in self._series), default=1) or 1
            for j, (key, color) in enumerate(self._series):
                v = vals.get(key, 0)
                bh = (bottom - top) * (v / maxv) if maxv else 0
                if bh > 0:
                    p.setBrush(QColor(color))
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(QRectF(x0 + j * bar_w, bottom - bh, bar_w - 2, bh), 2, 2)
            # 日期
            p.setPen(QColor('#64748b'))
            f = p.font()
            f.setPointSize(8)
            p.setFont(f)
            p.drawText(QRectF(cx - slot / 2, bottom + 4, slot, 16), Qt.AlignCenter, label)


class StatsDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle('本周统计')
        self.setMinimumSize(420, 400)
        self.store = store

        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        days = [monday + datetime.timedelta(days=i) for i in range(7)]

        total = {'focus_sec': 0, 'stand': 0, 'relax_cnt': 0, 'relax_sec': 0,
                 'eye': 0, 'todo_created': 0, 'todo_done': 0, 'rest': 0}
        chart_days = []
        for d in days:
            key = d.strftime('%Y-%m-%d')
            vals = store.daily.get(key, {})
            for k in total:
                total[k] += vals.get(k, 0)
            chart_days.append((d.strftime('%m-%d'), {
                'stand': vals.get('stand', 0),
                'eye': vals.get('eye', 0),
                'relax': vals.get('relax_cnt', 0),
            }))

        lay = QVBoxLayout(self)
        title = QLabel('本周（{} ~ {}）'.format(
            monday.strftime('%Y年%m月%d日'), min(today, days[-1]).strftime('%m月%d日')))
        f = title.font()
        f.setPointSize(12)
        f.setBold(True)
        title.setFont(f)
        lay.addWidget(title)

        info = (
            '专注时长：{}小时{}分\n'
            '站立提醒：{} 次　|　放松：{} 次 / 共 {} 分钟\n'
            '护眼提醒：{} 次　|　休息提醒：{} 次\n'
            '待办事项：新建 {} 条 / 完成 {} 条'.format(
                total['focus_sec'] // 3600, (total['focus_sec'] % 3600) // 60,
                total['stand'], total['relax_cnt'], total['relax_sec'] // 60,
                total['eye'], total['rest'],
                total['todo_created'], total['todo_done']))
        label = QLabel(info)
        label.setStyleSheet('color:#334155; font-size:12px; line-height:1.6;')
        lay.addWidget(label)

        lay.addWidget(QLabel('每日情况（蓝=站立　绿=护眼　橙=放松）'))
        lay.addWidget(BarChart(chart_days, [('stand', '#4da6ff'), ('eye', '#34d399'),
                                            ('relax', '#fbbf24')]))
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close)
        hb = QHBoxLayout()
        hb.addStretch(1)
        hb.addWidget(close_btn)
        lay.addLayout(hb)
