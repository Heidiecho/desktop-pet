# -*- coding: utf-8 -*-
"""提醒引擎单元测试：python3 tests/test_scheduler.py"""
import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scheduler import ReminderEngine, FOCUS, RELAX, REST

D = datetime.datetime


def fresh():
    cfg = {'stand_accum_sec': 0, 'status': FOCUS, 'relax_end_ts': None,
           'last_eye_ts': None, 'last_rest_date': ''}
    return ReminderEngine(cfg, {}), cfg


def test_stand_fires_after_1h_focus():
    eng, _ = fresh()
    t = D(2026, 10, 9, 9, 0, 0)
    for _ in range(3599):
        ev = eng.tick(t)
        assert not any(e[0] == 'stand' for e in ev), '3600 秒内不应触发站立提醒'
        t += datetime.timedelta(seconds=1)
    ev = eng.tick(t)
    assert any(e[0] == 'stand' for e in ev), '第 3600 秒应触发站立提醒'
    assert eng.stand_accum == 0
    # 之后重新累计
    t += datetime.timedelta(seconds=1)
    ev = eng.tick(t)
    assert eng.stand_accum == 1


def test_relax_pauses_stand_timer():
    eng, _ = fresh()
    t = D(2026, 10, 9, 9, 0, 0)
    for _ in range(1800):
        eng.tick(t)
        t += datetime.timedelta(seconds=1)
    assert eng.stand_accum == 1800
    # 放松 10 分钟：计时暂停
    eng.start_relax(10, t)
    assert eng.status == RELAX
    for _ in range(600):
        eng.tick(t)
        t += datetime.timedelta(seconds=1)
    assert eng.stand_accum == 1800, '放松期间站立计时不应累计'
    # 放松结束回到专注，继续累计（结束那一秒即恢复）
    ev = eng.tick(t)
    assert eng.status == FOCUS
    assert eng.stand_accum == 1801


def test_relax_records_stats():
    eng, _ = fresh()
    t = D(2026, 10, 9, 12, 0, 0)
    eng.start_relax(5, t)
    d = eng.daily['2026-10-09']
    assert d['relax_cnt'] == 1 and d['relax_sec'] == 300


def test_eye_every_20min_in_window():
    eng, _ = fresh()
    t = D(2026, 10, 9, 9, 0, 0)
    eng.tick(t)  # 初始化 last_eye = 09:00:00
    t = D(2026, 10, 9, 9, 20, 0)
    ev = eng.tick(t)
    assert any(e[0] == 'eye' for e in ev)
    t = D(2026, 10, 9, 9, 20, 1)
    assert not any(e[0] == 'eye' for e in eng.tick(t))
    t = D(2026, 10, 9, 9, 40, 0)
    assert any(e[0] == 'eye' for e in eng.tick(t))


def test_eye_no_fire_after_22():
    eng, _ = fresh()
    t = D(2026, 10, 9, 21, 59, 0)
    eng.last_eye_ts = t.isoformat(timespec='seconds')
    t = D(2026, 10, 9, 22, 30, 0)
    assert not any(e[0] == 'eye' for e in eng.tick(t))


def test_eye_cross_day_reset_to_9():
    eng, _ = fresh()
    eng.last_eye_ts = D(2026, 10, 8, 21, 0, 0).isoformat(timespec='seconds')
    t = D(2026, 10, 9, 9, 19, 0)
    assert not any(e[0] == 'eye' for e in eng.tick(t)), '跨天应重置到当天 9 点，9:19 不应触发'
    t = D(2026, 10, 9, 9, 20, 0)
    assert any(e[0] == 'eye' for e in eng.tick(t))


def test_rest_once_per_evening():
    eng, _ = fresh()
    t = D(2026, 10, 9, 22, 0, 0)
    ev = eng.tick(t)
    assert any(e[0] == 'rest' for e in ev)
    ev = eng.tick(t + datetime.timedelta(minutes=30))
    assert not any(e[0] == 'rest' for e in ev)
    # 次日 22 点再次提醒
    t2 = D(2026, 10, 10, 22, 0, 0)
    assert any(e[0] == 'rest' for e in eng.tick(t2))


def test_resting_holds_until_manual_focus():
    """休息中保持、不计时；即使到了 9 点也不会自动回专注，只有手动 set_focus。"""
    eng, _ = fresh()
    eng.status = REST
    t = D(2026, 10, 10, 8, 59, 59)
    eng.tick(t)
    assert eng.status == REST
    t = D(2026, 10, 10, 9, 0, 0)
    for _ in range(5):
        eng.tick(t)
        t += datetime.timedelta(seconds=1)
    assert eng.status == REST, '9 点后休息中应保持，不自动回专注'
    assert eng.stand_accum == 0, '休息中不计时'
    eng.set_focus()
    assert eng.status == FOCUS


def test_no_eye_while_resting():
    """休息中不弹护眼提醒（不被打扰）。"""
    eng, _ = fresh()
    eng.status = REST
    t = D(2026, 10, 10, 11, 0, 0)
    eng.tick(t)
    assert not any(e[0] == 'eye' for e in eng.tick(t + datetime.timedelta(minutes=25)))


def test_no_stand_accum_outside_9_21():
    eng, _ = fresh()
    t = D(2026, 10, 9, 21, 0, 0)
    for _ in range(60):
        eng.tick(t)
        t += datetime.timedelta(seconds=1)
    assert eng.stand_accum == 0


def test_stand_not_accumulate_when_resting():
    eng, _ = fresh()
    eng.status = REST
    t = D(2026, 10, 9, 23, 0, 0)   # 夜间休息状态保持，且不计时
    for _ in range(60):
        eng.tick(t)
        t += datetime.timedelta(seconds=1)
    assert eng.status == REST
    assert eng.stand_accum == 0


def test_set_focus_manual():
    eng, _ = fresh()
    eng.start_relax(5, D(2026, 10, 9, 12, 0, 0))
    assert eng.status == RELAX
    eng.set_focus()
    assert eng.status == FOCUS
    assert eng.relax_end_ts is None


if __name__ == '__main__':
    fns = [v for k, v in sorted(globals().items()) if k.startswith('test_')]
    for fn in fns:
        fn()
        print('PASS', fn.__name__)
    print('\n全部 {} 项测试通过'.format(len(fns)))
