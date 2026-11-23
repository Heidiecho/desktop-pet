# -*- coding: utf-8 -*-
"""提醒弹窗：圆角对话框 + 朝外小尾巴，可拖动，点击按钮或 30 秒后自动关闭。"""
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

AUTO_CLOSE_MS = 30000   # 30 秒自动关闭

_BODY_STYLE = """
QPushButton { border-radius: 13px; padding: 6px 16px; font-size: 12px; }
QPushButton[primary="true"] { background: #4da6ff; color: white; border: none; }
QPushButton[primary="true"]:hover { background: #3b93ee; }
QPushButton[primary="false"] { background: #ffffff; color: #3b82f6; border: 1px solid #9fd0ff; }
QPushButton[primary="false"]:hover { background: #eef6ff; }
"""


class CloudPopup(QWidget):
    """buttons: [(文字, 键值), ...]；点击后发出 action(键值)，超时发出 action('timeout')。"""
    action = pyqtSignal(str)

    def __init__(self, text, buttons, tail='bottom', parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle('提醒')
        self._tail = tail
        self._tail_len = 14
        self._margin = 10
        self._finished = False
        self._drag_offset = None

        lay = QVBoxLayout(self)
        m = self._content_margins()
        lay.setContentsMargins(m[0], m[1], m[2], m[3])

        self._label = QLabel(text)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        f = self._label.font()
        f.setPointSize(11)
        self._label.setFont(f)
        self._label.setStyleSheet('color:#334155;')
        lay.addWidget(self._label)

        hb = QHBoxLayout()
        hb.setSpacing(10)
        hb.addStretch(1)
        first = True
        for label, key in buttons:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty('primary', 'true' if first else 'false')
            btn.clicked.connect(lambda _, k=key: self._finish(k))
            hb.addWidget(btn)
            first = False
        lay.addLayout(hb)

        self.setStyleSheet(_BODY_STYLE)
        self.setFixedWidth(340)
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height() + 4)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self._finish('timeout'))
        self._timer.start(AUTO_CLOSE_MS)

    def _content_margins(self):
        left = right = self._margin + 12
        if self._tail == 'bottom':
            return left, self._margin + 10, right, self._margin + self._tail_len + 8
        return left, self._margin + self._tail_len + 10, right, self._margin + 8

    def set_tail(self, tail):
        """切换尾巴方向（bottom=在宠物上方/尾巴朝下，top=在宠物下方/尾巴朝上）。"""
        if tail == self._tail:
            return
        self._tail = tail
        m = self._content_margins()
        self.layout().setContentsMargins(m[0], m[1], m[2], m[3])
        self.update()

    def _finish(self, key):
        if self._finished:
            return
        self._finished = True
        self._timer.stop()
        self.action.emit(key)
        self.close()

    # ---------------- 拖动 ----------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_offset = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPos() - self._drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_offset = None
            e.accept()
        else:
            super().mouseReleaseEvent(e)

    # ---------------- 绘制（圆角对话框 + 朝外小尾巴） ----------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        m = self._margin
        tl = self._tail_len
        cx = w / 2.0
        if self._tail == 'bottom':
            body = QRectF(m, m, w - 2 * m, h - 2 * m - tl)
            apex = QPointF(cx, body.bottom() + tl)
        else:
            body = QRectF(m, m + tl, w - 2 * m, h - 2 * m - tl)
            apex = QPointF(cx, m)

        # 主体：圆角矩形；尾巴：从主体边缘伸向宠物方向的三角形（尖端朝外）
        path = QPainterPath()
        path.addRoundedRect(body, 18, 18)
        bw = 24.0
        if self._tail == 'bottom':
            path.moveTo(cx - bw / 2, body.bottom() - 2)
            path.lineTo(cx, apex.y())
            path.lineTo(cx + bw / 2, body.bottom() - 2)
        else:
            path.moveTo(cx - bw / 2, body.top() + 2)
            path.lineTo(cx, apex.y())
            path.lineTo(cx + bw / 2, body.top() + 2)
        path.closeSubpath()
        path.setFillRule(Qt.WindingFill)   # 保证主体与尾巴无镂空

        # 阴影
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(80, 120, 180, 36))
        p.drawPath(path.translated(2, 4))
        # 主体
        grad = QLinearGradient(0, body.top(), 0, body.bottom())
        grad.setColorAt(0.0, QColor('#ffffff'))
        grad.setColorAt(1.0, QColor('#e8f4ff'))
        p.setBrush(grad)
        p.setPen(QColor('#8ec9ff'))
        p.drawPath(path)
        p.end()
