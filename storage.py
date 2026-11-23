# -*- coding: utf-8 -*-
"""数据存储：配置、每日统计、待办事项（全部落在 exe/app 同目录的 data/ 下）。"""
import datetime
import json
import os
import sys


def app_dir():
    """程序所在目录：打包后为 exe 所在目录，源码运行时为项目目录。"""
    if getattr(sys, 'frozen', False):  # PyInstaller 打包
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def pets_dir():
    """宠物图片目录：程序目录下的 pets/，用户可直接增删图片。"""
    return os.path.join(app_dir(), 'pets')


DEFAULT_CONFIG = {
    'scale': 1.0,             # 宠物缩放比例
    'pos_x': None,            # 上次窗口位置
    'pos_y': None,
    'current_image': '',      # 当前图片文件名
    'last_image_date': '',    # 上次自动换图的日期
    'stand_accum_sec': 0,     # 站立提醒累计秒数（刨除放松时间）
    'status': 'focusing',     # focusing 专注中 / relaxing 放松中 / resting 休息中
    'relax_end_ts': None,     # 放松结束时间 iso
    'last_eye_ts': None,      # 上次护眼提醒时间 iso
    'last_rest_date': '',     # 上次休息提醒日期
}


def empty_day():
    return {
        'focus_sec': 0, 'stand': 0, 'relax_cnt': 0, 'relax_sec': 0,
        'eye': 0, 'todo_created': 0, 'todo_done': 0, 'rest': 0,
    }


def parse_dt(s):
    """解析 "YYYY-MM-DD HH:MM" 或 iso 格式；失败返回 None。"""
    if not s:
        return None
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.datetime.strptime(s, fmt)
        except Exception:
            continue
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None


class Store:
    def __init__(self, base_dir=None):
        self.base = base_dir or app_dir()
        self.data_dir = os.path.join(self.base, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.config = self._load('config.json', {})
        for k, v in DEFAULT_CONFIG.items():
            self.config.setdefault(k, v)
        self.daily = self._load('daily_stats.json', {})
        self.todos = self._load('todos.json', {'todos': []})

    # ---------- 基础读写 ----------
    def _path(self, name):
        return os.path.join(self.data_dir, name)

    def _load(self, name, default):
        try:
            with open(self._path(name), 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default

    def _dump(self, name, obj):
        try:
            with open(self._path(name), 'w', encoding='utf-8') as f:
                json.dump(obj, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def save_config(self):
        self._dump('config.json', self.config)

    def save_daily(self):
        self._dump('daily_stats.json', self.daily)

    def save_todos(self):
        self._dump('todos.json', self.todos)

    # ---------- 每日统计 ----------
    def today_str(self):
        return datetime.date.today().strftime('%Y-%m-%d')

    def today(self):
        t = self.today_str()
        if t not in self.daily:
            self.daily[t] = empty_day()
        return self.daily[t]

    def add_today(self, key, value=1):
        self.today()[key] = self.today()[key] + value

    # ---------- 待办事项 ----------
    def add_todo(self, text, remind_ts=None, ddl_ts=None):
        t = {
            'id': int(datetime.datetime.now().timestamp() * 1000),
            'text': text,
            'created': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'remind_ts': remind_ts,      # 提醒时间 "YYYY-MM-DD HH:MM"
            'ddl_ts': ddl_ts,            # 截止时间 "YYYY-MM-DD HH:MM"
            'remind_done': False,        # 提醒时间那次已弹
            'ddl30_done': False,         # DDL 前 30 分钟那次已弹
            'ddl_done': False,           # DDL 到点那次已弹
            'done': False,
            'done_ts': None,
        }
        self.todos['todos'].append(t)
        self.add_today('todo_created')
        self.save_todos()
        self.save_daily()
        return t

    def set_todo_done(self, todo_id, done):
        for t in self.todos['todos']:
            if t['id'] == todo_id and t['done'] != done:
                t['done'] = done
                t['done_ts'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M') if done else None
                if done:
                    self.add_today('todo_done')
                else:
                    d = self.today()
                    d['todo_done'] = max(0, d['todo_done'] - 1)
                self.save_todos()
                self.save_daily()
                return

    def delete_todo(self, todo_id):
        self.todos['todos'] = [t for t in self.todos['todos'] if t['id'] != todo_id]
        self.save_todos()
