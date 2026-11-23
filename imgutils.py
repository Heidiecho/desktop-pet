# -*- coding: utf-8 -*-
"""Qt 图片工具：裁掉透明边、按比例缩放（窗口与托盘共用，保证主体视觉一致）。"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap

_BBOX_CACHE = {}          # (path, mtime_ns) -> bbox，避免重复扫描大图


def alpha_bbox(img, short=320):
    """扫描透明通道边界，映射回原图坐标（x1, y1, x2, y2）；无内容返回 None。"""
    w0, h0 = img.width(), img.height()
    if w0 <= 0 or h0 <= 0:
        return None
    scale = short / max(w0, h0)
    small = img.scaled(max(1, int(w0 * scale)), max(1, int(h0 * scale)),
                       Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    sw, sh = small.width(), small.height()
    minx, miny, maxx, maxy = sw, sh, -1, -1
    for y in range(sh):
        for x in range(sw):
            if small.pixelColor(x, y).alpha() > 8:
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y
    if maxx < minx or maxy < miny:
        return None
    inv = 1.0 / scale
    return (int(minx * inv), int(miny * inv),
            int((maxx + 1) * inv), int((maxy + 1) * inv))


def cropped_pixmap(path, scale=1.0):
    """裁掉透明边后按比例缩放的 QPixmap；图片无效返回空 pixmap。"""
    pix = QPixmap(path)
    if pix.isNull():
        return pix
    try:
        key = (path, os.path.getmtime(path))
    except Exception:
        key = None
    if key is not None and key in _BBOX_CACHE:
        bbox = _BBOX_CACHE[key]
    else:
        img = pix.toImage().convertToFormat(QImage.Format_ARGB32)
        bbox = alpha_bbox(img)
        if key is not None:
            _BBOX_CACHE[key] = bbox
    if bbox:
        x1, y1, x2, y2 = bbox
        pix = pix.copy(x1, y1, x2 - x1, y2 - y1)   # (x, y, 宽, 高)
    if abs(scale - 1.0) > 1e-6:
        pix = pix.scaled(max(1, int(pix.width() * scale)),
                         max(1, int(pix.height() * scale)),
                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pix
