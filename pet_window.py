# -*- coding: utf-8 -*-
"""悬浮宠物主窗口：拖动、滚轮缩放、双击换图、右键菜单、头顶状态标签、云朵弹窗。"""
import datetime
import os
import random

from PyQt5.QtCore import Qt, QPoint, QPointF
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QLabel, QMenu, QWidget

from cloud_popup import CloudPopup
from dialogs import StatsDialog, TodoDialog
from imgutils import cropped_pixmap
from storage import parse_dt, pets_dir

IMG_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
DEFAULT_SHORT_EDGE = 180   # 首次运行默认长边像素（原 360，用户要求 1/2）


class StatusBadge(QLabel):
    """头顶状态标签：幼圆字体、白色文字、蓝色描边、透明背景、可点击。"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAlignment(Qt.AlignCenter)
        fam = '幼圆'
        try:
            families = set(QFontDatabase().families())
            for cand in ('幼圆', 'YouYuan'):
                if cand in families:
                    fam = cand
                    break
        except Exception:
            pass
        self._font = QFont(fam, 12, QFont.Bold)
        self._font.setPixelSize(11)              # 字号约为之前(21)的一半
        self._badge_color = QColor('#ffffff')
        self._border_color = QColor('#a6cfff')   # 浅浅的蓝色描边
        self.setText(text)

    def setText(self, text):
        super().setText(text)
        fm = QFontMetrics(self._font)
        self.setFixedSize(fm.horizontalAdvance(text) + 22, fm.height() + 12)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(self._font)
        fm = p.fontMetrics()
        x = (self.width() - fm.horizontalAdvance(self.text())) / 2.0
        y = (self.height() - fm.height()) / 2.0 + fm.ascent()
        path = QPainterPath()
        path.addText(QPointF(x, y), self._font, self.text())
        p.setPen(QPen(self._border_color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)                 # 蓝色描边
        p.fillPath(path, self._badge_color)   # 白色填充
        p.end()


class PetWindow(QWidget):
    def __init__(self, store, engine):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle('桌面宠物')
        self.store = store
        self.engine = engine
        self._drag_offset = None
        self._press_pos = None
        # 首次运行：scale=None，根据图片大小自动取合适比例；之后沿用记忆的缩放
        if store.config.get('pos_x') is not None and store.config.get('scale') is not None:
            self._scale = float(store.config['scale'])
            self._scale_from_config = True
        else:
            self._scale = None
            self._scale_from_config = False
        self._popup = None
        self._pending = []      # 待弹出的提醒事件
        self._images = []
        self._current = ''
        self._anchored = False  # 窗口定位过之后，换图/缩放时保持底部中心锚定
        self._init_ui()
        self._apply_daily_switch()
        self._restore_position()
        self._anchored = True
        self.show()

    # ---------------- 初始化 ----------------
    def _init_ui(self):
        self._label = QLabel(self)
        self._label.setAttribute(Qt.WA_TranslucentBackground)
        self._badge = StatusBadge('专注中', self)
        self._badge.mousePressEvent = self._badge_click

    def _rescan_images(self):
        """扫描 pets/ 目录，支持运行中增删图片。"""
        folder = pets_dir()
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        imgs = []
        for fn in sorted(os.listdir(folder)):
            if fn.lower().endswith(IMG_EXTS):
                imgs.append(os.path.join(folder, fn))
        self._images = imgs
        return imgs

    def _apply_daily_switch(self):
        """每天随机换一张图；同一天再次启动则沿用当天已选的图。"""
        imgs = self._rescan_images()
        today = datetime.date.today().strftime('%Y-%m-%d')
        cur = self.store.config.get('current_image', '')
        if cur and not os.path.isfile(cur):
            cur = ''
        if today != self.store.config.get('last_image_date', ''):
            others = [p for p in imgs if p != cur] or imgs
            cur = random.choice(others) if others else ''
            self.store.config['last_image_date'] = today
        if not cur:
            cur = random.choice(imgs) if imgs else ''
        self._set_image(cur)
        self.store.save_config()

    def _set_image(self, path):
        if not path:
            self._show_no_image()
            return
        self._current = path
        self._render()
        self.store.config['current_image'] = path
        self.store.save_config()

    def _screen(self):
        return QApplication.primaryScreen().availableGeometry()

    def _render(self):
        pix = cropped_pixmap(self._current)
        if pix.isNull():
            self._show_no_image()
            return
        base = pix.size()
        if self._scale is None:
            # 首次运行：让图片长边约 DEFAULT_SHORT_EDGE px
            self._scale = max(0.1, min(1.0, DEFAULT_SHORT_EDGE / max(base.width(), base.height())))
            self.store.config['scale'] = round(self._scale, 3)
        elif self._scale_from_config:
            # 旧版本默认 360 偏大 → 新版默认 180：渲染长边超过 1.5 倍则自动重置
            self._scale_from_config = False
            if max(base.width(), base.height()) * self._scale > DEFAULT_SHORT_EDGE * 1.5:
                self._scale = max(0.1, min(1.0, DEFAULT_SHORT_EDGE / max(base.width(), base.height())))
                self.store.config['scale'] = round(self._scale, 3)
        # 尺寸上限：不许超过屏幕（避免放大后出画、点不到）
        screen = self._screen()
        max_s = min(3.0, (screen.width() - 20) / max(1, base.width()),
                    (screen.height() - 40) / max(1, base.height()))
        self._scale = max(0.1, min(self._scale, max(0.1, max_s)))
        scaled = pix.scaled(int(base.width() * self._scale),
                            int(base.height() * self._scale),
                            Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 换图/缩放时保持底部中心锚定（猫脚位置不动），窗口整体更稳定
        if self._anchored:
            old_cx = self.x() + self.width() / 2.0
            old_bottom = self.y() + self.height()
            self.setFixedSize(scaled.size())
            self.move(int(old_cx - scaled.width() / 2.0), int(old_bottom - scaled.height()))
        else:
            self.setFixedSize(scaled.size())
        self._label.setPixmap(scaled)
        self._label.setGeometry(0, 0, scaled.width(), scaled.height())
        self._relayout_badge()
        if self._anchored:
            self._clamp_to_screen()

    def _show_no_image(self):
        self._label.setText('请在 pets 文件夹\n放入宠物图片')
        self._label.setStyleSheet('color:#94a3b8; font-size:12px;')
        self._label.adjustSize()
        self.setFixedSize(self._label.size())
        self._relayout_badge()

    def _restore_position(self):
        px = self.store.config.get('pos_x')
        py = self.store.config.get('pos_y')
        if px is not None and py is not None:
            self.move(int(px), int(py))
        else:
            # 首次运行：默认放在屏幕右下角
            screen = self._screen()
            self.move(screen.right() - self.width() - 60,
                      screen.bottom() - self.height() - 40)
        self._clamp_to_screen()

    def _clamp_to_screen(self):
        screen = self._screen()
        x = max(screen.left(), min(self.x(), screen.right() - self.width() + 1))
        y = max(screen.top(), min(self.y(), screen.bottom() - self.height() + 1))
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    # ---------------- 头顶状态标签 ----------------
    def _relayout_badge(self):
        bw = self._badge.width()
        self._badge.move(max(2, (self.width() - bw) // 2), 4)

    def update_badge(self):
        s = self.engine.status
        if s == 'focusing':
            text = '专注中'
        elif s == 'relaxing':
            text = '放松中 ' + self._relax_remaining() + '…'
        else:
            text = '休息中…'
        if self._badge.text() != text:
            self._badge.setText(text)   # setText 内部已按新字号重算尺寸
            self._relayout_badge()

    def _badge_click(self, event):
        if event.button() != Qt.LeftButton:
            return
        menu = QMenu(self._badge)
        menu.addAction('专注中', lambda: self._switch_status('focus'))
        menu.addAction('放松5分钟', lambda: self._switch_status('relax5'))
        menu.addAction('放松10分钟', lambda: self._switch_status('relax10'))
        menu.addAction('休息中', lambda: self._switch_status('rest'))
        menu.exec_(self._badge.mapToGlobal(QPoint(0, self._badge.height())))
        self.update_badge()

    def _switch_status(self, target):
        if target == 'focus':
            self.engine.set_focus()
        elif target == 'relax5':
            self.engine.start_relax(5)
        elif target == 'relax10':
            self.engine.start_relax(10)
        else:
            self.engine.confirm_rest()
        self.update_badge()

    def _relax_remaining(self):
        end = parse_dt(self.engine.relax_end_ts)
        if not end:
            return '--:--'
        sec = max(0, int((end - datetime.datetime.now()).total_seconds()))
        return '{}:{:02d}'.format(sec // 60, sec % 60)

    # ---------------- 交互 ----------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press_pos = e.globalPos()
            self._drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None and (e.buttons() & Qt.LeftButton):
            if (e.globalPos() - self._press_pos).manhattanLength() > 3:
                self.move(e.globalPos() - self._drag_offset)
                e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._drag_offset is not None:
            self.store.config['pos_x'] = self.x()
            self.store.config['pos_y'] = self.y()
            self.store.save_config()
            self._drag_offset = None
            self._press_pos = None
            e.accept()
        else:
            super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_offset = None
            self._press_pos = None
            self._switch_image()
            e.accept()
        else:
            super().mouseDoubleClickEvent(e)

    def wheelEvent(self, e):
        pix = cropped_pixmap(self._current)
        if pix.isNull():
            return
        iw, ih = pix.width(), pix.height()
        screen = self._screen()
        max_s = min(3.0, (screen.width() - 20) / max(1, iw),
                    (screen.height() - 40) / max(1, ih))
        max_s = max(0.1, max_s)
        delta = e.angleDelta().y()
        new = self._scale * (1.1 if delta > 0 else 0.9)
        self._scale = max(0.1, min(max_s, new))
        self.store.config['scale'] = round(self._scale, 3)
        self.store.save_config()
        self._render()
        self._clamp_to_screen()

    def _switch_image(self):
        imgs = self._rescan_images()
        if not imgs:
            self._show_no_image()
            return
        others = [p for p in imgs if p != self._current] or imgs
        self._set_image(random.choice(others))

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        st = QMenu(self)
        st.setTitle(self._status_text())
        st.setEnabled(False)
        menu.addAction(st.menuAction())
        menu.addSeparator()
        menu.addAction('新建待办…', self._open_todo)
        menu.addAction('本周统计…', self._open_stats)
        menu.addAction('切换形象', self._switch_image)
        menu.addAction('最小化到托盘', self._minimize_to_tray)
        menu.addSeparator()
        menu.addAction('退出', QApplication.instance().quit)
        menu.exec_(e.globalPos())

    def _status_text(self):
        s = self.engine.status
        if s == 'focusing':
            return '状态：专注中'
        if s == 'relaxing':
            return '状态：放松中（剩余 {}）…'.format(self._relax_remaining())
        return '状态：休息中…'

    # ---------------- 云朵弹窗 ----------------
    def queue_reminder(self, event):
        """event: ('stand'|'eye'|'rest'|'todo', payload)，若已有弹窗则排队。"""
        if event[0] == 'todo':
            if any(ev[0] == 'todo' and ev[1].get('id') == event[1].get('id')
                   for ev in self._pending):
                return
        elif any(ev[0] == event[0] for ev in self._pending):
            return
        if self._popup is not None:
            self._pending.append(event)
            return
        self._show_reminder(event)

    def _show_reminder(self, event):
        etype = event[0]
        if etype == 'stand':
            text = '已经专注满 1 小时啦，站起来活动一下，伸伸懒腰、喝口水吧！'
            buttons = [('确认', 'ok'), ('放松5分钟', 'relax5'), ('放松10分钟', 'relax10')]
        elif etype == 'eye':
            text = '护眼时间到：请向 20 米外远眺 6 秒，让眼睛休息一下～'
            buttons = [('已完成', 'ok')]
        elif etype == 'todo':
            payload = event[1]
            ttext = payload.get('text', '')
            why = payload.get('why', 'remind')
            if why == 'ddl30':
                text = '待办「{}」还有 30 分钟就到截止时间啦！'.format(ttext)
            elif why == 'ddl':
                text = '待办「{}」已到截止时间，完成了吗？'.format(ttext)
            else:
                text = '待办提醒：「{}」，别忘了哦～'.format(ttext)
            buttons = [('知道了', 'ok'), ('标记完成', 'done')]
        else:
            text = '已经 22:00 了，今天的工作先放一放，早点休息吧！'
            buttons = [('好的，去休息', 'ok'), ('再坚持一会', 'later')]

        popup = CloudPopup(text, buttons)
        popup.action.connect(lambda key, ev=event: self._on_popup_action(ev, key))
        self._position_popup(popup)
        self._popup = popup
        popup.show()
        popup.raise_()
        popup.activateWindow()

    def _position_popup(self, popup):
        screen = self._screen()
        ph = popup.height()
        pw = popup.width()
        x = self.x() + self.width() // 2 - pw // 2
        above_y = self.y() - ph + 10
        if above_y >= screen.top():
            y = above_y
            tail = 'bottom'
        else:
            y = self.y() + self.height() - 10
            tail = 'top'
        popup.set_tail(tail)
        x = max(screen.left() + 4, min(x, screen.right() - pw - 4))
        y = max(screen.top() + 4, min(y, screen.bottom() - ph - 4))
        popup.move(x, y)

    def _on_popup_action(self, event, key):
        etype = event[0]
        if etype == 'stand':
            if key == 'relax5':
                self.engine.start_relax(5)
            elif key == 'relax10':
                self.engine.start_relax(10)
        elif etype == 'rest':
            if key == 'ok':
                self.engine.confirm_rest()
        elif etype == 'todo':
            if key == 'done':
                self.store.set_todo_done(event[1].get('id'), True)
        self._popup = None
        if self._pending:
            self._show_reminder(self._pending.pop(0))

    def popup_open(self):
        return self._popup is not None

    # ---------------- 待办提醒（三段式） ----------------
    def check_todo_reminders(self, now):
        """提醒时间弹一次 → 截止前30分钟弹一次 → 截止时弹一次（均只对未完成待办）。"""
        changed = False
        for t in self.store.todos['todos']:
            if t.get('done'):
                continue
            tid = t['id']
            rts = parse_dt(t.get('remind_ts'))
            dts = parse_dt(t.get('ddl_ts'))
            if rts is not None and not t.get('remind_done') and now >= rts:
                t['remind_done'] = True
                changed = True
                self.queue_reminder(('todo', {'id': tid, 'text': t['text'], 'why': 'remind'}))
            if dts is not None:
                if not t.get('ddl30_done') and (dts - datetime.timedelta(minutes=30)) <= now < dts:
                    t['ddl30_done'] = True
                    changed = True
                    self.queue_reminder(('todo', {'id': tid, 'text': t['text'], 'why': 'ddl30'}))
                if not t.get('ddl_done') and now >= dts:
                    t['ddl_done'] = True
                    changed = True
                    self.queue_reminder(('todo', {'id': tid, 'text': t['text'], 'why': 'ddl'}))
        if changed:
            self.store.save_todos()

    # ---------------- 菜单动作 ----------------
    def _open_todo(self):
        TodoDialog(self.store, self).exec_()

    def _open_stats(self):
        StatsDialog(self.store, self).exec_()

    def _minimize_to_tray(self):
        self.hide()

    def show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()
