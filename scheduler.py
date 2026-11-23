# -*- coding: utf-8 -*-
"""提醒引擎（纯逻辑，不依赖 Qt，便于测试）。

规则：
- 站立提醒：每天 09:00-21:00，每累计专注满 1 小时提醒一次；
  放松（5/10 分钟）和休息状态不计入该 1 小时。
- 护眼提醒：09:00-22:00，每 20 分钟提醒一次，远眺 20 米外 6 秒。
- 休息提醒：每天 22:00 之后提醒一次去休息。
"""
from datetime import datetime, timedelta

ACTIVE_START_H = 9    # 站立提醒开始（时）
ACTIVE_END_H = 21     # 站立提醒结束（时），21:00 后不再站立提醒
EYE_END_H = 22        # 护眼提醒结束（时）
REST_H = 22           # 22 点起提醒休息
STAND_INTERVAL_SEC = 3600
EYE_INTERVAL_SEC = 1200

FOCUS = 'focusing'
RELAX = 'relaxing'
REST = 'resting'


def is_stand_window(dt):
    return ACTIVE_START_H <= dt.hour < ACTIVE_END_H


def is_eye_window(dt):
    return ACTIVE_START_H <= dt.hour < EYE_END_H


def _parse(ts):
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


class ReminderEngine:
    def __init__(self, config, daily):
        self.config = config
        self.daily = daily
        self.stand_accum = int(config.get('stand_accum_sec', 0) or 0)
        self.status = config.get('status', FOCUS)
        self.relax_end_ts = config.get('relax_end_ts')
        self.last_eye_ts = config.get('last_eye_ts')
        self.last_rest_date = config.get('last_rest_date', '')
        self.dirty = False

    # ---------------- 状态操作 ----------------
    def start_relax(self, minutes, now=None):
        now = now or datetime.now()
        self.status = RELAX
        self.relax_end_ts = (now + timedelta(minutes=minutes)).isoformat(timespec='seconds')
        d = self._day(now)
        d['relax_cnt'] += 1
        d['relax_sec'] += minutes * 60
        self.dirty = True

    def confirm_rest(self):
        self.status = REST
        self.relax_end_ts = None
        self.dirty = True

    def set_focus(self):
        """手动切回专注状态（点击头顶状态标签用）。"""
        self.status = FOCUS
        self.relax_end_ts = None
        self.dirty = True

    def _day(self, dt):
        key = dt.strftime('%Y-%m-%d')
        return self.daily.setdefault(key, {
            'focus_sec': 0, 'stand': 0, 'relax_cnt': 0, 'relax_sec': 0,
            'eye': 0, 'todo_created': 0, 'todo_done': 0, 'rest': 0,
        })

    # ---------------- 每秒 tick ----------------
    def tick(self, now):
        """返回需要弹出的提醒事件列表，如 [('stand',{}), ('eye',{})]。"""
        self.dirty = False
        events = []
        hour = now.hour
        d = self._day(now)

        # 1) 状态自动迁移（仅放松会自动结束；休息中保持，只能手动切回专注）
        if self.status == RELAX:
            end = _parse(self.relax_end_ts)
            if end is not None and now >= end:
                self.status = FOCUS      # 放松结束回到专注
                self.relax_end_ts = None
                self.dirty = True

        # 2) 专注计时（放松/休息期间不计入）
        if self.status == FOCUS:
            d['focus_sec'] += 1
            if is_stand_window(now):
                self.stand_accum += 1
                if self.stand_accum >= STAND_INTERVAL_SEC:
                    self.stand_accum = 0
                    d['stand'] += 1
                    events.append(('stand', {}))

        # 3) 护眼提醒（09:00-22:00，每 20 分钟；休息中不打扰）
        if self.status != REST and is_eye_window(now):
            if not self.last_eye_ts:
                self.last_eye_ts = now.replace(hour=ACTIVE_START_H, minute=0, second=0,
                                               microsecond=0).isoformat(timespec='seconds')
            last = _parse(self.last_eye_ts)
            if last is not None:
                if last.date() != now.date():  # 跨天重置到当天 9 点
                    self.last_eye_ts = now.replace(hour=ACTIVE_START_H, minute=0, second=0,
                                                   microsecond=0).isoformat(timespec='seconds')
                    last = _parse(self.last_eye_ts)
                if now >= last + timedelta(seconds=EYE_INTERVAL_SEC):
                    self.last_eye_ts = now.isoformat(timespec='seconds')
                    d['eye'] += 1
                    events.append(('eye', {}))

        # 4) 夜间休息提醒（22 点后，每晚一次）
        if hour >= REST_H and self.last_rest_date != now.strftime('%Y-%m-%d'):
            self.last_rest_date = now.strftime('%Y-%m-%d')
            d['rest'] += 1
            events.append(('rest', {}))

        return events

    # ---------------- 持久化同步 ----------------
    def sync_to_config(self):
        self.config['stand_accum_sec'] = self.stand_accum
        self.config['status'] = self.status
        self.config['relax_end_ts'] = self.relax_end_ts
        self.config['last_eye_ts'] = self.last_eye_ts
        self.config['last_rest_date'] = self.last_rest_date
