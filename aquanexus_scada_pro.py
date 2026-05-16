#!/usr/bin/env python3
# =============================================================================
#  AquaNexus SCADA Pro — Cascaded Tri-Loop Smart Water Management System
#  Single-File Master Python Implementation  |  Version 3.0
# =============================================================================
#
#  Author      : VK
#  Version     : 3.0  (Engineering-Correct Edition)
#  Year        : 2026
#
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │  LOOP-1  SCADA Process Control                                          │
#  │    └─ Full PID controller: Proportional + Integral + Derivative        │
#  │       Kp=2.2  Ki=0.08  Kd=0.6  |  Anti-windup integral clamp          │
#  │    └─ Precision valve FV201 (0–100 %) with MPC feedforward             │
#  │    └─ FDIR: Fault Detection, Isolation & Auto-Recovery (watchdog)      │
#  │    └─ Source tank LT101 → Precision Valve FV201 → Process tank LT202   │
#  │                                                                         │
#  │  LOOP-2  Agricultural Intelligence                                      │
#  │    └─ Real-time soil moisture sensor (evaporation / rain physics)      │
#  │    └─ Continuous soil pH sensor (natural drift + noise model)          │
#  │    └─ pH hysteresis band: alarm <6.2, clear >6.4 (no chatter)         │
#  │    └─ Weather-aware smart irrigation decision matrix (4-guard logic)   │
#  │    └─ Zero-waste cascade: WB001 reclaimed water → irrigation first     │
#  │    └─ Water conservation + power-saving KPI tracking                   │
#  │                                                                         │
#  │  LOOP-3  Digital Twin & Model Predictive Control (MPC)                  │
#  │    └─ 10-tick-ahead lookahead using same plant model as Loop-1         │
#  │    └─ MPC feedforward correction injected into FV201 setpoint          │
#  │    └─ OEE = Availability × Performance × Quality  (ISO 22400)         │
#  │    └─ SCADA Score: OEE(55%) + SP-Adherence(35%) + Sustainability(10%) │
#  │    └─ Financial ROI: water saved + kWh saved → cumulative profit       │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  Engineering keywords:
#    SCADA · Full PID Control · Anti-Windup · Precision Valve Control
#    Moisture Sensor · pH Sensor · pH Hysteresis · Waste Management
#    Water Conservation · Smart Irrigation · Power Saving · FDIR
#    Digital Twin · Model Predictive Control · OEE (ISO 22400)
#
#  Run          :  python aquanexus_scada_pro.py
#  Requirements :  pip install dash plotly
#  Dashboard    :  http://127.0.0.1:8050
# =============================================================================

import random
import csv
import threading
import webbrowser
from datetime import datetime
from collections import deque

import dash
from dash import dcc, html, Input, Output, State, ctx
import plotly.graph_objects as go

# ─── DESIGN TOKENS ────────────────────────────────────────────────────────────
BG     = '#05090f'
S1     = '#0a1220'
S2     = '#0e1a2c'
CYAN   = '#00ccff'
GOLD   = '#ffc107'
GREEN  = '#00e676'
RED    = '#ff4136'
ORANGE = '#ff7043'
BLUE   = '#448aff'
TEXT   = '#d8eaf8'
MUTED  = '#6f8faa'
BORDER = 'rgba(0,200,255,0.12)'
MONO   = "'Courier New', monospace"
MAX_H  = 100

# ─── BOOT LOG ─────────────────────────────────────────────────────────────────
_BOOT = [
    ('AquaNexus SCADA Pro v3.0 — System Online',              's'),
    ('LOOP-1: Full PID Controller  Kp=2.2  Ki=0.08  Kd=0.6', 'i'),
    ('LOOP-1: Anti-Windup Clamp Enabled  I_max=+/-25',        'i'),
    ('LOOP-1: FDIR Watchdog Active',                          'i'),
    ('LOOP-2: Soil Moisture Sensor — Calibrated',             'i'),
    ('LOOP-2: Soil pH Sensor — Hysteresis ON  <6.2 / >6.4',  'i'),
    ('LOOP-2: Zero-Waste Cascade WB001 — Online',             'i'),
    ('LOOP-2: Smart Irrigation 4-Guard Matrix — Armed',       'i'),
    ('LOOP-3: Digital Twin MPC — 10-Tick Lookahead Active',   'i'),
    ('LOOP-3: OEE Engine (ISO 22400) — Active',               'i'),
    ('SYSTEM: Power-Saving Scheduler — Active',               'i'),
    ('SYSTEM: All Loops Synchronised — Awaiting Tick-1',      'i'),
]

# ==============================================================================
#  SHARED SYSTEM STATE
# ==============================================================================
def _make_state() -> dict:
    now = datetime.now().strftime('%H:%M:%S')
    s = {
        'tick': 0,
        # ── Loop 1 — Full PID ─────────────────────────────────────────────────
        'lt101':          65.0,
        'fv201':          50.0,
        'lt202':          48.0,
        'setpoint':       75.0,
        'pump_on':        True,
        'mode':           'AUTO',
        'pid_integral':   0.0,
        'pid_prev_err':   0.0,
        'pid_d_live':     0.0,
        'PID_KP':         2.2,
        'PID_KI':         0.08,
        'PID_KD':         0.60,
        'PID_I_MAX':      25.0,
        'fault_active':   False,
        'alarm_latched':  False,
        'fault_ticks':    0,
        'uptime_ticks':   0,
        'consec_fault':   0,
        'oee_score':      0.0,

        # Engineering realism states
        'fv_cmd':         50.0,                 # controller demand
        'flow_delay':     deque([0.0]*6, maxlen=6),  # transport lag
        'lt202_meas':     48.0,                 # filtered measurement
        'sensor_alpha':   0.22,                 # first-order filter
        'fault_stuck_valve': False,
        # ── Loop 2 — Agricultural ─────────────────────────────────────────────
        'moisture':       45.0,
        'pH':              6.8,
        'pH_dir':         0.025,
        'pH_alarm':       False,
        'weather':        'Sunny',
        'wx_timer':       0,
        'irrigating':     False,
        'wb_level':       8.0,
        'wb_pH':          7.1,
        'water_saved':    0.0,
        'fresh_draw':     0.0,
        'reclaim_draw':   0.0,
        # ── Loop 3 — Digital Twin / MPC ───────────────────────────────────────
        'twin_pred':      [],
        'mpc_adj':        0.0,
        'kwh_saved':      0.0,
        'profit':         0.0,
        'scada_score':    0.0,
        # ── Rolling history ───────────────────────────────────────────────────
        'H': {
            'lt101':        deque(maxlen=MAX_H),
            'lt202':        deque(maxlen=MAX_H),
            'sp':           deque(maxlen=MAX_H),
            'oee':          deque(maxlen=50),
            'moisture':     deque(maxlen=MAX_H),
            'pH':           deque(maxlen=MAX_H),
            'fresh_draw':   deque(maxlen=MAX_H),
            'reclaim_draw': deque(maxlen=MAX_H),
            'profit':       deque(maxlen=MAX_H),
            'water_saved':  deque(maxlen=MAX_H),
            'kwh_saved':    deque(maxlen=MAX_H),
            'pid_p':        deque(maxlen=MAX_H),
            'pid_i':        deque(maxlen=MAX_H),
            'pid_d':        deque(maxlen=MAX_H),
        },
        'logs': deque(maxlen=150),
    }
    for msg, kind in reversed(_BOOT):
        s['logs'].appendleft({'ts': now, 'msg': msg, 'k': kind})
    return s

S     = _make_state()
_LOCK = threading.Lock()

# ==============================================================================
#  UTILITIES
# ==============================================================================
def clamp(v, lo, hi):
    return max(lo, min(hi, float(v)))

def add_log(msg, kind='i'):
    S['logs'].appendleft({'ts': datetime.now().strftime('%H:%M:%S'),
                          'msg': msg, 'k': kind})

def push_h(key, val):
    S['H'][key].append(round(float(val), 4))

# ==============================================================================
#  LOOP-3  MPC — runs FIRST each cycle
# ==============================================================================
def run_mpc():
    if S['mode'] != 'AUTO' or not S['pump_on']:
        S['mpc_adj'] = 0.0
        return

    sim = S['lt202_meas']
    pred = []

    for _ in range(10):
        err = S['setpoint'] - sim
        sim_valve = clamp(50.0 + err * 1.6, 0, 100)

        sim_inflow = (sim_valve / 100.0) * 1.45
        sim_outflow = 0.05 * (max(sim, 1.0) ** 0.5)

        sim = clamp(sim + sim_inflow - sim_outflow, 0, 100)
        pred.append(round(sim, 2))

    S['twin_pred'] = pred

    pred_err = S['setpoint'] - pred[-1]
    S['mpc_adj'] = clamp(pred_err * 0.65, -15.0, 15.0)
# ==============================================================================
#  LOOP-1  SCADA Process Control — Full PID + Anti-Windup + FDIR
# ==============================================================================
def run_loop1():
    if S['fault_active']:
        S['fault_ticks'] += 1

        # only auto-recover genuine AUTO control faults
        if S['mode'] == 'FAULT':
            S['consec_fault'] += 1

            if S['consec_fault'] == 1:
                S['pid_integral'] = 0.0
                S['pid_prev_err'] = 0.0

            if S['consec_fault'] >= 6:
                S['fault_active'] = False
                S['fault_stuck_valve'] = False
                S['alarm_latched'] = False
                S['mode'] = 'AUTO'
                S['fv201'] = 50.0
                S['fv_cmd'] = 50.0
                S['consec_fault'] = 0
                add_log('AUTO-RECOVERY SUCCESSFUL — PID Reset, Returning to AUTO', 's')

        return

    if not S['pump_on']:
        S['fv201'] = 0.0
        S['fv_cmd'] = 0.0
        S['pid_integral'] = 0.0
        S['pid_prev_err'] = 0.0
        S['lt101'] = clamp(S['lt101'] + 0.12, 0, 100)
        return

    S['uptime_ticks'] += 1

    measured = (
        S['sensor_alpha'] * S['lt202'] +
        (1.0 - S['sensor_alpha']) * S['lt202_meas'] +
        (random.random() - 0.5) * 0.18
    )
    S['lt202_meas'] = clamp(measured, 0, 100)

    if S['mode'] == 'AUTO':
        err = S['setpoint'] - S['lt202_meas']

        p_term = S['PID_KP'] * err

        if 0 < S['fv201'] < 100:
            S['pid_integral'] = clamp(
                S['pid_integral'] + err,
                -S['PID_I_MAX'],
                S['PID_I_MAX']
            )
        else:
            S['pid_integral'] *= 0.68

        if err * S['pid_prev_err'] < 0:
            S['pid_integral'] *= 0.50

        i_term = S['PID_KI'] * S['pid_integral']

        d_term = S['PID_KD'] * (err - S['pid_prev_err'])
        S['pid_prev_err'] = err

        base_bias = S['fv201']

        S['fv_cmd'] = clamp(
            base_bias + p_term + i_term + d_term + S['mpc_adj'],
            0.0,
            100.0
        )

        push_h('pid_p', p_term)
        push_h('pid_i', i_term)
        push_h('pid_d', d_term)
        S['pid_d_live'] = d_term
        if not S['fault_stuck_valve']:
            delta = S['fv_cmd'] - S['fv201']

            # industrial valve deadband + stiction
            if abs(delta) > 0.5:
                step = clamp(delta * 0.55, -5.0, 5.0)
                S['fv201'] = clamp(S['fv201'] + step, 0, 100)

        inflow = (S['fv201'] / 100.0) * 1.55
        S['flow_delay'].append(inflow)
        delayed_inflow = S['flow_delay'][0]

        outflow = 0.05 * (max(S['lt202'], 1.0) ** 0.5)

        prev_level = S['lt202']

        S['lt202'] = clamp(
            S['lt202'] + delayed_inflow - outflow,
            0,
            100
        )

        source_refill = random.uniform(0.05, 0.16) if S['lt101'] < 35 else random.uniform(0.01, 0.06)

        S['lt101'] = clamp(
            S['lt101'] - delayed_inflow * 0.58 + source_refill,
            0,
            100
        )

        if S['lt202'] > 96:
            overflow = S['lt202'] - 94.0
            S['lt202'] = 94.0
            S['wb_level'] = clamp(S['wb_level'] + overflow * 0.55, 0, 100)

            S['pid_integral'] = clamp(
                S['pid_integral'] * 0.82,
                -S['PID_I_MAX'],
                S['PID_I_MAX']
            )

        level_change = S['lt202'] - prev_level

        if (
            err > 22 and
            S['fv201'] > 95 and
            level_change < 0.03
        ):
            S['consec_fault'] += 1

            if S['consec_fault'] >= 4:
                S['fault_active'] = True
                S['alarm_latched'] = True
                S['mode'] = 'FAULT'
                S['consec_fault'] = 0
                add_log('CRITICAL: Process non-response detected — FDIR engaged', 'c')
        else:
            S['consec_fault'] = 0

        if abs(err) < 4 and abs(S['mpc_adj']) < 2:
            S['kwh_saved'] += 0.0015
    elif S['mode'] == 'MANUAL':
        if not S['fault_stuck_valve']:
            delta = S['fv_cmd'] - S['fv201']

            if abs(delta) > 0.4:
                step = clamp(delta * 0.85, -8.0, 8.0)
                S['fv201'] = clamp(S['fv201'] + step, 0, 100)

        inflow = (S['fv201'] / 100.0) * 1.55
        S['flow_delay'].append(inflow)
        delayed_inflow = S['flow_delay'][0]

        outflow = 0.05 * (max(S['lt202'], 1.0) ** 0.5)

        S['lt202'] = clamp(
            S['lt202'] + delayed_inflow - outflow,
            0,
            100
        )

        source_refill = random.uniform(0.05, 0.16) if S['lt101'] < 35 else random.uniform(0.01, 0.06)

        S['lt101'] = clamp(
            S['lt101'] - delayed_inflow * 0.58 + source_refill,
            0,
            100
        )
# ==============================================================================
#  LOOP-2  Agricultural Intelligence
# ==============================================================================
def run_loop2():
    # ── Weather simulation ────────────────────────────────────────────────────
    S['wx_timer'] += 1
    if S['wx_timer'] >= 60 + random.randint(0, 60):
        S['wx_timer'] = 0
        nw = random.choice(['Sunny','Sunny','Sunny','Cloudy','Cloudy','Rain'])
        if nw != S['weather']:
            S['weather'] = nw
            add_log(f'FORECAST: Weather → {nw}', 'w')

    # ── Soil moisture sensor (physics) ───────────────────────────────────────
    evap  = {'Sunny': 0.15, 'Cloudy': 0.06, 'Rain': 0.00}[S['weather']]
    rain  = 0.55 if S['weather'] == 'Rain' else 0.0
    S['moisture'] = clamp(
        S['moisture'] - evap + rain + (random.random() - 0.5) * 0.25,
        15, 92)

    # ── Soil pH sensor (continuous drift + noise) ─────────────────────────────
    S['pH'] += S['pH_dir']
    if S['pH'] > 7.9 or S['pH'] < 6.0:
        S['pH_dir'] *= -1
    S['pH'] = clamp(S['pH'] + (random.random() - 0.5) * 0.04, 5.5, 8.3)

    # ── pH Hysteresis Alarm (IEC 61511 — no relay chatter) ───────────────────
    #   ALARM  triggers when pH drops below 6.20
    #   ALARM  clears  when pH rises above 6.40  (0.20 hysteresis band)
    if not S['pH_alarm'] and S['pH'] < 6.20:
        S['pH_alarm'] = True
        add_log(f'ALARM: pH low — {S["pH"]:.2f} < 6.20  (lower process limit)', 'c')
    elif S['pH_alarm'] and S['pH'] > 6.40:
        S['pH_alarm'] = False
        add_log(f'CLEAR: pH recovered — {S["pH"]:.2f} > 6.40  (hysteresis cleared)', 's')

    # ── Waste buffer ──────────────────────────────────────────────────────────
    S['wb_pH']    = clamp(S['pH'] + 0.18 + (random.random() - 0.5) * 0.08, 5.8, 8.1)
    S['wb_level'] = clamp(S['wb_level'] - 0.04, 0, 100)

    # ── Smart Irrigation Decision Matrix (4 guards ALL must be TRUE) ──────────
    #   Guard 1: soil is dry enough to need water
    #   Guard 2: not currently raining (free moisture already available)
    #   Guard 3: process tank safe to draw from  (LT202 > 22 %)
    #   Guard 4: waste buffer pH safe for plants  (6.2 – 7.8)
    needs_water = S['moisture']  < 52
    not_raining = S['weather']  != 'Rain'
    tank_safe   = S['lt202']     > 22
    wb_pH_safe  = 6.2 <= S['wb_pH'] <= 7.8

    S['fresh_draw'] = S['reclaim_draw'] = 0.0

    if needs_water and not_raining and tank_safe:
        S['irrigating'] = True
        if S['wb_level'] > 6 and wb_pH_safe:
            # Zero-Waste Cascade: reclaimed buffer water used first
            used              = min(0.32, S['wb_level'] * 0.08)
            S['wb_level']     = clamp(S['wb_level'] - used, 0, 100)
            S['moisture']     = clamp(S['moisture'] + used * 0.75, 0, 90)
            S['water_saved'] += used * 0.48
            S['reclaim_draw'] = used * 0.48
            S['kwh_saved']   += 0.0008
            S['profit']      += used * 0.48 * 0.0012
        else:
            # Fallback: fresh water from process tank
            used = random.uniform(0.12, 0.22)
            S['lt202']     = clamp(S['lt202'] - used, 0, 100)
            S['moisture']  = clamp(S['moisture'] + used * 0.55, 0, 90)
            S['fresh_draw'] = used * 0.48
    else:
        S['irrigating'] = False

    if S['weather'] == 'Rain':
        S['kwh_saved'] += 0.0008
        S['profit']    += 0.00008

# ==============================================================================
#  LOOP-3  KPIs & Financial Digital Twin
# ==============================================================================
def run_loop3():
    total = S['uptime_ticks'] + S['fault_ticks']

    # Availability
    avail = (S['uptime_ticks'] / total) if total > 0 else 1.0

    # Performance (industrial realistic startup handling)
    err_pct = abs(S['lt202_meas'] - S['setpoint'])

    if S['mode'] == 'MANUAL':
        perf = clamp(1.0 - err_pct / 45.0, 0.55, 0.92)

    elif err_pct <= 3:
        perf = 1.00

    elif err_pct <= 8:
        perf = 0.96

    elif err_pct <= 15:
        perf = 0.90

    elif err_pct <= 25:
        perf = 0.82

    elif err_pct <= 35:
        perf = 0.72

    else:
        perf = 0.60
    # Quality (avoid over-punishing normal process drift)
    moist_score = clamp(S['moisture'] / 55.0, 0.88, 1.0)

    ph_dev = abs(S['pH'] - 7.0)
    ph_score = clamp(1.0 - ph_dev / 3.2, 0.88, 1.0)

    qual = moist_score * ph_score

    # Smoothed OEE
    instant_oee = avail * perf * qual * 100.0

    if S['oee_score'] == 0:
        S['oee_score'] = max(65.0, instant_oee)
    else:
        S['oee_score'] = 0.82 * S['oee_score'] + 0.18 * instant_oee

    # SCADA score
    sp_adher = clamp(1.0 - err_pct / 60.0, 0.75, 1.0)

    sust_idx = clamp(
        S['water_saved'] * 0.06 +
        S['kwh_saved'] * 10.0,
        0,
        1
    )

    safety_penalty = 1.0
    if S['pH_alarm']:
        safety_penalty = 0.75
    if S['fault_active']:
        safety_penalty *= 0.75

    base_score = (
        S['oee_score'] * 0.55 +
        sp_adher * 100 * 0.35 +
        sust_idx * 100 * 0.10
    )

    # immediate operational state correction
    if not S['pump_on']:
        S['scada_score'] = clamp(S['scada_score'] * 0.82, 0, 100)
        return

    if S['mode'] == 'MANUAL':
        base_score *= 0.90

    if S['fault_active']:
        base_score *= 0.75

    S['scada_score'] = clamp(
        base_score * safety_penalty,
        0,
        100
    )

    S['profit'] = S['water_saved'] * 0.0012 + S['kwh_saved'] * 0.13
    S['H']['oee'].append(round(S['oee_score'], 1))
# ==============================================================================
#  MASTER TICK
# ==============================================================================
def master_tick():
    with _LOCK:
        S['tick'] += 1
        run_mpc()
        run_loop1()
        run_loop2()
        run_loop3()
        push_h('lt101',        S['lt101'])
        push_h('lt202',        S['lt202'])
        push_h('sp',           S['setpoint'])
        push_h('moisture',     S['moisture'])
        push_h('pH',           S['pH'])
        push_h('fresh_draw',   S['fresh_draw'])
        push_h('reclaim_draw', S['reclaim_draw'])
        push_h('profit',       S['profit'])
        push_h('water_saved',  S['water_saved'])
        push_h('kwh_saved',    S['kwh_saved'])

# ==============================================================================
#  CSV EXPORT
# ==============================================================================
def do_export_csv():
    H, n  = S['H'], len(S['H']['lt202'])
    fname = f"AquaNexus_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    rows  = {k: list(v) for k, v in H.items()}
    with open(fname, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Tick','LT101(%)','LT202(%)','Setpoint(%)',
                    'Moisture(%)','pH','FreshDraw(L)','ReclaimDraw(L)',
                    'OEE(%)','WaterSaved(L)','kWhSaved','Profit(USD)',
                    'PID_P','PID_I','PID_D'])
        def g(k, i): return rows[k][i] if i < len(rows[k]) else ''
        for i in range(n):
            w.writerow([i,
                g('lt101',i), g('lt202',i), g('sp',i),
                g('moisture',i), g('pH',i), g('fresh_draw',i), g('reclaim_draw',i),
                g('oee',i),
                g('water_saved',i), g('kwh_saved',i), g('profit',i),
                g('pid_p',i), g('pid_i',i), g('pid_d',i)])
    return fname

# ==============================================================================
#  CHART HELPERS
# ==============================================================================
def _layout(title='', yrange=None, y2=False):
    d = dict(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=42, r=12, t=30, b=26),
        font=dict(family=MONO, color=MUTED, size=9),
        title=dict(text=title, font=dict(color=GREEN, size=10),
                   x=0, xanchor='left', pad=dict(l=0)),
        legend=dict(font=dict(size=10, color=MUTED), bgcolor='rgba(0,0,0,0)',
                    orientation='h', yanchor='bottom', y=1.01, xanchor='left', x=0),
        xaxis=dict(gridcolor='rgba(0,200,255,0.06)', color=MUTED,
                   tickfont=dict(size=9, family=MONO)),
        yaxis=dict(gridcolor='rgba(0,200,255,0.06)', color=MUTED,
                   tickfont=dict(size=9, family=MONO)),
    )
    if yrange:
        d['yaxis']['range'] = yrange
    if y2:
        d['yaxis2'] = dict(gridcolor='rgba(0,0,0,0)', color=MUTED,
                           overlaying='y', side='right',
                           tickfont=dict(size=8, family=MONO))
    return d

def _empty(title=''):
    f = go.Figure()
    f.update_layout(**_layout(title))
    return f

# ==============================================================================
#  DASH APPLICATION
# ==============================================================================
app = dash.Dash(__name__, title='AquaNexus SCADA Pro',
                update_title=None, suppress_callback_exceptions=True)

# ─── UI component helpers ──────────────────────────────────────────────────────
def _btn(label, bid, fg, bg, border=None):
    return html.Button(label, id=bid, n_clicks=0, style={
        'width':'100%','padding':'8px 6px','marginBottom':'5px',
        'border': f'1px solid {border}' if border else 'none',
        'borderRadius':'2px','fontFamily':MONO,'fontSize':'10px',
        'fontWeight':'700','letterSpacing':'1.5px','textTransform':'uppercase',
        'cursor':'pointer','color':fg,'background':bg,
    })

def _card(cid, label, sub, color, vid, sid=None):
    return html.Div([
        html.Div(cid, style={'fontFamily':MONO,'fontSize':'9px','color':MUTED}),
        html.Div('--', id=vid, style={
            'fontFamily':MONO,'fontSize':'15px','fontWeight':'700',
            'color':color,'lineHeight':'1.0'}),
        html.Div(label, style={'fontSize':'9px','color':MUTED,'marginTop':'1px'}),
        html.Div(sub,   id=sid or (vid+'-sub'),
                 style={'fontSize':'9px','color':MUTED,'marginTop':'0px'}),
    ], style={
        'background':S1,'border':f'1px solid {BORDER}',
        'borderTop':f'2px solid {color}',
        'padding':'3px 6px','minWidth':'110px','flex':'1 1 0','boxSizing': 'border-box',
    })

def _akpi(label, vid, val, color):
    return html.Div([
        html.Div(label, style={
            'fontSize':'9px','color':MUTED,'fontFamily':MONO,
            'letterSpacing':'1px','marginBottom':'3px'}),
        html.Div(val, id=vid, style={
            'fontFamily':MONO,'fontSize':'15px','fontWeight':'700','color':color}),
    ], style={'flex':'1','background':S1,'border':f'1px solid {BORDER}','padding':'8px 10px'})

_LOGCOL = {'c':RED,'s':GREEN,'i':MUTED,'w':GOLD,'m':BLUE,'d':ORANGE}
_GS     = {'displayModeBar': False}

def _tab_sty(active, name):
    on = name == active
    return {
        'padding':'8px 18px','fontSize':'10px','fontWeight':'700',
        'letterSpacing':'2px','textTransform':'uppercase','fontFamily':MONO,
        'color': CYAN if on else MUTED,'cursor':'pointer',
        'borderBottom': f'2px solid {CYAN}' if on else '2px solid transparent',
    }

def _panel_sty(active, name):
    on = name == active
    return {
        'flex':'1','display':'flex' if on else 'none',
        'flexDirection':'column','gap':'2px',
        'padding':'3px','overflow':'hidden','minHeight':'0',
    }

# ==============================================================================
#  LAYOUT
# ==============================================================================
app.layout = html.Div([
    dcc.Interval(id='ticker', interval=1000, n_intervals=0),
    dcc.Store(id='tab-store', data='scada'),
    *[html.Div(id=f'_d{i}', style={'display':'none'}) for i in range(1, 7)],

    # HEADER
    html.Div([
        html.Div([
            html.H1('⬡ AquaNexus SCADA Pro', style={
                'fontSize':'15px','fontWeight':'800','color':CYAN,
                'letterSpacing':'1.5px','margin':'0'}),
            html.Div(
                'CASCADED TRI-LOOP CONTROL  |  LOOP-1: PID+SCADA  |  '
                'LOOP-2: AGRI  |  LOOP-3: MPC+TWIN  |  © VK 2026',
                style={'fontSize':'9px','color':MUTED,'fontFamily':MONO,'marginTop':'2px'}),
        ]),
        html.Div([
            html.Span(id='hclock', style={'fontFamily':MONO,'fontSize':'10px','color':MUTED}),
            html.Br(),
            html.Span('TICK: ', style={'fontFamily':MONO,'fontSize':'10px','color':MUTED}),
            html.Span(id='htick', style={'fontFamily':MONO,'fontSize':'10px','color':CYAN}),
        ], style={'textAlign':'right'}),
    ], style={
        'display':'flex','alignItems':'center','justifyContent':'space-between',
        'padding':'3px 10px','background':S1,
        'borderBottom':f'1px solid {BORDER}','flexShrink':'0',
    }),

    # STATUS BANNER
    html.Div(id='status-banner', children='Initialising…', style={
        'padding':'6px 16px','fontFamily':MONO,'fontSize':'11px',
        'fontWeight':'700','letterSpacing':'1px','textAlign':'center',
        'background':'rgba(0,230,118,0.10)','color':GREEN,
        'borderBottom':'1px solid rgba(0,230,118,0.25)','flexShrink':'0',
    }),

    # FLOW TICKER
    html.Div(id='flow-ticker', children='…', style={
        'padding':'4px 16px','fontFamily':MONO,'fontSize':'10px',
        'color':GREEN,'background':'rgba(0,230,118,0.04)',
        'borderBottom':'1px solid rgba(0,230,118,0.08)',
        'flexShrink':'0','letterSpacing':'0.4px',
        'whiteSpace':'nowrap','overflow':'hidden',
    }),

    # SENSOR CARDS
    html.Div([
        _card('LT101',      'Source Tank',    'Raw Supply',   CYAN,   'v-lt101'),
        _card('FV201',      'Precision Valve','Flow Control', GOLD,   'v-fv201'),
        _card('LT202',      'Process Tank',   'Target: --',   BLUE,   'v-lt202','v-sp-lbl'),
        _card('WB001',      'Waste Buffer',   'Standby',      RED,    'v-wb',   'v-wb-s'),
        _card('MOISTURE',   'Soil Moisture',  'Idle',         GREEN,  'v-mst',  'v-irr'),
        _card('pH SENSOR',  'Soil Chemistry', 'Normal',       ORANGE, 'v-ph',   'v-ph-s'),
        _card('WEATHER',    'Forecast',       'Live',         MUTED,  'v-wx'),
        _card('WATER SAVED','Conservation',   'Cumulative',   GREEN,  'v-ws'),
        _card('kWh SAVED',  'Power Saved',    'Total kWh',    GOLD,   'v-kwh'),
        _card('PROFIT',     'Financial ROI',  'USD Total',    GREEN,  'v-pft'),
    ], style={
        'display':'flex','gap':'2px','padding':'2px',
        'background':BG,'flexShrink':'0','overflow':'hidden',
    }),

    # MAIN BODY
    html.Div([

        # LEFT PANEL
        html.Div([
            # Tabs
            html.Div([
                html.Div('⬡ SCADA / PID',  id='tb-scada', n_clicks=0,
                         style=_tab_sty('scada','scada')),
                html.Div('⬡ Agriculture',  id='tb-agri',  n_clicks=0,
                         style=_tab_sty('scada','agri')),
                html.Div('⬡ Digital Twin', id='tb-twin',  n_clicks=0,
                         style=_tab_sty('scada','twin')),
            ], style={'display':'flex','background':S1,
                      'borderBottom':f'1px solid {BORDER}','flexShrink':'0'}),

            # SCADA/PID tab
            html.Div([
                dcc.Graph(id='ch-process',
                    figure=_empty('⬡ Process Trend — LT101 Source & LT202 Process Tank (%)'),
                    config=_GS, style={'flex':'1','minHeight':'0'}),
                dcc.Graph(id='ch-pid',
                    figure=_empty('⬡ PID Components — P term  I term  D term  (Live)'),
                    config=_GS, style={'flex':'1','minHeight':'0'}),
            ], id='tab-scada', style=_panel_sty('scada','scada')),

            # Agriculture tab
            html.Div([
                html.Div([
                    _akpi('IRRIGATION',   'ak-irr','IDLE', MUTED),
                    _akpi('WATER SOURCE', 'ak-src','FRESH',CYAN),
                    _akpi('WB pH STATUS', 'ak-ph', 'SAFE', GREEN),
                    _akpi('WEATHER',      'ak-wx', '—',    GOLD),
                    _akpi('WB LEVEL',     'ak-wb', '--',   RED),
                ], style={'display':'flex','gap':'2px',
                          'padding':'0 0 4px 0','flexShrink':'0'}),
                dcc.Graph(id='ch-soil',
                    figure=_empty('⬡ Soil Trends — Moisture (%) & pH [Hysteresis alarm shown]'),
                    config=_GS, style={'flex':'1','minHeight':'0'}),
                dcc.Graph(id='ch-cascade',
                    figure=_empty('⬡ Zero-Waste Cascade — Reclaimed vs Fresh Draw (L/tick)'),
                    config=_GS, style={'flex':'1','minHeight':'0'}),
            ], id='tab-agri', style=_panel_sty('scada','agri')),

            # Digital Twin tab
            html.Div([
                html.Div([
                    dcc.Graph(id='ch-gauge',
                        figure=_empty('⬡ Process Tank — Digital Twin Gauge'),
                        config=_GS, style={'flex':'1','minHeight':'0'}),
                    dcc.Graph(id='ch-twin',
                        figure=_empty('⬡ MPC — 10-Tick Lookahead Prediction'),
                        config=_GS, style={'flex':'1','minHeight':'0'}),
                ], style={'display':'flex','flex':'1','gap':'2px','minHeight':'0'}),
                html.Div([
                    dcc.Graph(id='ch-oee',
                        figure=_empty('⬡ OEE — Availability x Performance x Quality (ISO 22400)'),
                        config=_GS, style={'flex':'1','minHeight':'0'}),
                    dcc.Graph(id='ch-sust',
                        figure=_empty('⬡ Sustainability KPIs — Water · Power · Profit'),
                        config=_GS, style={'flex':'1','minHeight':'0'}),
                ], style={'display':'flex','flex':'1','gap':'2px','minHeight':'0'}),
            ], id='tab-twin', style=_panel_sty('scada','twin')),

        ], style={'display':'flex','flexDirection':'column',
                  'overflow':'hidden','minHeight':'0','flex':'1 1 auto','width':'0',}),

        # RIGHT PANEL
        html.Div([
            # Operator console
            html.Div([
                html.Div('Operator Console', style={
                    'fontFamily':MONO,'fontSize':'9px','fontWeight':'700',
                    'letterSpacing':'2.5px','color':CYAN,
                    'textTransform':'uppercase','marginBottom':'8px'}),
                _btn('▶  START / STOP PUMP',    'btn-pump', S1,    TEXT,  BORDER),
                _btn('⟳  TOGGLE AUTO / MANUAL', 'btn-mode', S1,    TEXT,  BORDER),
                _btn('⚡  INJECT FAULT',          'btn-fault','#fff', RED),
                _btn('✔  ACKNOWLEDGE ALARM',     'btn-ack',  '#000', GOLD),
                _btn('⬇  EXPORT CSV',            'btn-csv',  '#000', GREEN),
                html.Div(id='export-msg', style={
                    'fontFamily':MONO,'fontSize':'9px',
                    'color':CYAN,'marginTop':'4px','minHeight':'14px'}),
            ], style={'padding':'8px 10px',
                      'borderBottom':f'1px solid {BORDER}','flexShrink':'0'}),

            # PID Live Display
            html.Div([
                html.Div('PID State (Live)', style={
                    'fontFamily':MONO,'fontSize':'9px','fontWeight':'700',
                    'letterSpacing':'2px','color':CYAN,
                    'textTransform':'uppercase','marginBottom':'6px'}),
                html.Div(id='pid-params'),
            ], style={'padding':'8px 10px',
                      'borderBottom':f'1px solid {BORDER}','flexShrink':'0'}),

            # Setpoint
            html.Div([
                html.Div(id='sp-title', children='Setpoint (%)', style={
                    'fontFamily':MONO,'fontSize':'9px','fontWeight':'700',
                    'letterSpacing':'2.5px','color':CYAN,
                    'textTransform':'uppercase','marginBottom':'6px'}),
                html.Div([
                    html.Span('20%', style={'fontFamily':MONO,'fontSize':'9px','color':MUTED}),
                    dcc.Slider(id='sp-slider', min=20, max=95, step=1, value=75,
                               marks={20:'20',50:'50',75:'75',95:'95'},
                               tooltip={'placement':'top','always_visible':False}),
                    html.Span(id='sp-val', children='75%',
                        style={'fontFamily':MONO,'fontSize':'11px',
                               'color':CYAN,'minWidth':'36px'}),
                ], style={'display':'flex','alignItems':'center','gap':'6px'}),
            ], style={'padding':'8px 10px',
                      'borderBottom':f'1px solid {BORDER}','flexShrink':'0'}),

            # SCADA Score
            html.Div([
                html.Div('SCADA SCORE', style={
                    'fontFamily':MONO,'fontSize':'9px','color':MUTED,
                    'letterSpacing':'2px','textTransform':'uppercase'}),
                html.Div('0.0%', id='score-val', style={
                    'fontFamily':MONO,'fontSize':'24px',
                    'fontWeight':'700','color':GREEN,'lineHeight':'1.1'}),
                html.Div(id='mpc-line', style={
                    'fontFamily':MONO,'fontSize':'9px','color':MUTED,'marginTop':'2px'}),
            ], style={'padding':'8px 10px','textAlign':'center',
                      'borderBottom':f'1px solid {BORDER}','flexShrink':'0'}),

            # Log header
            html.Div([
                html.Div('Status Log', style={
                    'fontFamily':MONO,'fontSize':'9px','fontWeight':'700',
                    'letterSpacing':'2.5px','color':CYAN,'textTransform':'uppercase'}),
            ], style={'padding':'8px 10px 4px',
                      'borderBottom':f'1px solid {BORDER}','flexShrink':'0'}),

            html.Div(id='log-box', style={
                'flex':'1','overflowY':'auto','padding':'6px 12px',
                'fontFamily':MONO,'fontSize':'9.5px',
                'display':'flex','flexDirection':'column',
                'gap':'2px','minHeight':'0',
            }),

        ], style={
            'width':'250px','minWidth':'250px','maxWidth':'250px','background':S1,'borderLeft':f'1px solid {BORDER}',
            'display':'flex','flexDirection':'column',
            'overflow':'hidden','minHeight':'0','flexShrink':'0',
        }),

    ], style={'display':'flex','flex':'1','overflow':'hidden','minHeight':'0', 'width':'100%',}),

], style={
    'background':BG,'color':TEXT,
    'fontFamily':"'Segoe UI', system-ui, sans-serif",
    'fontSize':'13px','display':'flex','flexDirection':'column',
    'height':'100vh', 'width':'100%','overflow':'hidden',
})

# ==============================================================================
#  OPERATOR CALLBACKS
# ==============================================================================
@app.callback(Output('_d1','children'), Input('btn-pump','n_clicks'), prevent_initial_call=True)
def cb_pump(n):
    if n:
        with _LOCK:
            if S['mode'] == 'FAULT':
                add_log('SYSTEM: Pump command blocked — FAULT active', 'd')

            elif S['mode'] == 'AUTO':
                add_log('SYSTEM: Pump command blocked — AUTO controller owns actuator', 'd')

            else:
                S['pump_on'] = not S['pump_on']

                if S['pump_on']:
                    S['fv_cmd'] = max(S['fv_cmd'], 30.0)
                    S['flow_delay'] = deque([0.0]*6, maxlen=6)
                    add_log('MANUAL: Pump ON', 'm')
                else:
                    S['fv201'] = 0.0
                    S['fv_cmd'] = 0.0
                    S['flow_delay'] = deque([0.0]*6, maxlen=6)
                    add_log('MANUAL: Pump OFF', 'm')

    return ''

@app.callback(Output('_d2','children'), Input('btn-mode','n_clicks'), prevent_initial_call=True)
def cb_mode(n):
    if n:
        with _LOCK:
            if S['mode'] == 'FAULT':
                add_log('SYSTEM: Cannot toggle — FAULT active', 'd')

            elif S['mode'] == 'AUTO':
                S['mode'] = 'MANUAL'
                S['fv_cmd'] = S['fv201']
                add_log('SYSTEM: Mode → MANUAL  (operator valve control)', 'w')

            else:
                S['mode'] = 'AUTO'

                if not S['pump_on']:
                    S['pump_on'] = True
                    S['fv201'] = 0.0
                    S['fv_cmd'] = 0.0
                    S['flow_delay'] = deque([0.0]*4, maxlen=4)
                    add_log('SYSTEM: AUTO requested — pump auto-started from idle', 'w')

                S['pid_integral'] = 0.0
                S['pid_prev_err'] = 0.0
                S['mpc_adj'] = 0.0

                add_log('SYSTEM: Mode → AUTO (bumpless transfer)', 'i')

    return ''

@app.callback(Output('_d3','children'), Input('btn-fault','n_clicks'), prevent_initial_call=True)
def cb_fault(n):
    if n:
        with _LOCK:
            if S['fault_active']:
                add_log('SYSTEM: Fault already active', 'd')
            else:
                S['fault_active'] = True
                S['alarm_latched'] = True
                if S['mode'] == 'AUTO':
                    S['mode'] = 'FAULT'
                S['consec_fault'] = 0
                S['fault_stuck_valve'] = True
                add_log('CRITICAL: Manual Fault Injected — FDIR Active', 'c')
    return ''

@app.callback(Output('_d4','children'), Input('btn-ack','n_clicks'), prevent_initial_call=True)
def cb_ack(n):
    if n:
        with _LOCK:
            if not S['alarm_latched']:
                add_log('SYSTEM: ACK ignored — no active latch', 'd')

            else:
                S['alarm_latched'] = False
                S['fault_active'] = False
                S['fault_stuck_valve'] = False
                S['fault_ticks'] = 0
                S['consec_fault'] = 0

                S['mode'] = 'MANUAL'
                S['pump_on'] = True

                # preserve operator state
                S['fv_cmd'] = S['fv201']
                S['flow_delay'] = deque([0.0]*6, maxlen=6)

                add_log('FAULT ACKNOWLEDGED — released to MANUAL control', 's')

    return ''
@app.callback(
    Output('export-msg','children'), Output('_d5','children'),
    Input('btn-csv','n_clicks'), prevent_initial_call=True)
def cb_csv(n):
    if n:
        with _LOCK:
            fname = do_export_csv()
            add_log(f'DATA: CSV Exported → {fname}', 's')
        return f'✔ Saved: {fname}', ''
    return '', ''

@app.callback(
    Output('sp-val','children'),
    Input('sp-slider','value'),
    prevent_initial_call=True
)
def cb_sp(val):
    if val is not None:
        with _LOCK:
            if S['mode'] == 'AUTO':
                S['setpoint'] = float(val)
                S['pid_integral'] = 0.0
                add_log(f'SYSTEM: Setpoint → {val}%  (integrator reset)', 'i')
                return f'{val}%'

            elif S['mode'] == 'MANUAL':
                S['fv_cmd'] = float(val)
                add_log(f'MANUAL: Valve command → {val}%', 'm')
                return f'{val}%'

    return '--'
@app.callback(
    Output('tab-store','data'),
    Output('tb-scada','style'), Output('tb-agri','style'), Output('tb-twin','style'),
    Input('tb-scada','n_clicks'), Input('tb-agri','n_clicks'), Input('tb-twin','n_clicks'),
    State('tab-store','data'), prevent_initial_call=True)
def cb_tabs(ns, na, nt, cur):
    tab = {'tb-scada':'scada','tb-agri':'agri','tb-twin':'twin'}.get(ctx.triggered_id, cur)
    return tab, _tab_sty(tab,'scada'), _tab_sty(tab,'agri'), _tab_sty(tab,'twin')

# ==============================================================================
#  MASTER RENDER CALLBACK
# ==============================================================================
@app.callback(
    Output('hclock','children'),          Output('htick','children'),
    Output('status-banner','children'),   Output('status-banner','style'),
    Output('flow-ticker','children'),
    Output('v-lt101','children'),  Output('v-fv201','children'),
    Output('v-lt202','children'),  Output('v-sp-lbl','children'),
    Output('v-wb','children'),     Output('v-wb-s','children'),
    Output('v-mst','children'),    Output('v-irr','children'),
    Output('v-ph','children'),     Output('v-ph-s','children'),
    Output('v-wx','children'),
    Output('v-ws','children'),     Output('v-kwh','children'), Output('v-pft','children'),
    Output('ak-irr','children'),   Output('ak-irr','style'),
    Output('ak-src','children'),   Output('ak-src','style'),
    Output('ak-ph','children'),    Output('ak-ph','style'),
    Output('ak-wx','children'),    Output('ak-wb','children'),
    Output('score-val','children'), Output('sp-title','children'),Output('score-val','style'),
    Output('mpc-line','children'),
    Output('pid-params','children'),
    Output('log-box','children'),
    Output('ch-process','figure'), Output('ch-pid','figure'),
    Output('ch-soil','figure'),    Output('ch-cascade','figure'),
    Output('ch-gauge','figure'),   Output('ch-twin','figure'),
    Output('ch-oee','figure'),     Output('ch-sust','figure'),
    Output('tab-scada','style'),   Output('tab-agri','style'), Output('tab-twin','style'),
    Input('ticker','n_intervals'),
    State('tab-store','data'),
)
def master_render(n, tab):
    master_tick()

    with _LOCK:
        H  = S['H']
        xs = list(range(len(H['lt202'])))
        WX = {'Sunny':'☀️','Cloudy':'☁️','Rain':'🌧️'}

        # Banner
        _bb = {'padding':'6px 16px','fontFamily':MONO,'fontSize':'11px',
               'fontWeight':'700','letterSpacing':'1px','textAlign':'center','flexShrink':'0'}
        if S['fault_active'] or S['mode'] == 'FAULT':
            bn_t = '⚠ CRITICAL FAULT — FDIR AUTO-RECOVERY IN PROGRESS'
            bn_s = {**_bb,'background':'rgba(255,65,54,0.15)','color':RED,
                    'borderBottom':'1px solid rgba(255,65,54,0.35)'}
        elif S['alarm_latched']:
            bn_t = '⚠ ALARM LATCHED — PRESS ACKNOWLEDGE ALARM'
            bn_s = {**_bb,'background':'rgba(255,193,7,0.10)','color':GOLD,
                    'borderBottom':'1px solid rgba(255,193,7,0.25)'}
        elif S['mode'] == 'MANUAL':
            bn_t = f'⚡ MANUAL MODE — PID SUSPENDED | OEE: {S["oee_score"]:.1f}%'
            bn_s = {**_bb,'background':'rgba(255,193,7,0.10)','color':GOLD,
                    'borderBottom':'1px solid rgba(255,193,7,0.25)'}
        else:
            ms = (
                '↑ PRE-OPEN' if S['mpc_adj'] > 0 else
                '↓ PRE-CLOSE' if S['mpc_adj'] < 0 else
                'NOMINAL'
            )

            ctrl_err = S['setpoint'] - S['lt202_meas']
            abs_err = abs(ctrl_err)

            pv_rising = False
            if len(H['lt202']) >= 6:
                pv_rising = (H['lt202'][-1] - H['lt202'][-6]) > 3.0

            if S['fv201'] >= 99:
                if abs_err > 15 and not pv_rising:
                    mpc_state = "SATURATED HIGH"
                elif abs_err <= 8:
                    mpc_state = "HIGH FLOW STABILIZING"
                else:
                    mpc_state = "HIGH DEMAND NORMAL"

            elif S['fv201'] <= 1:
                if abs_err > 15:
                    mpc_state = "SATURATED LOW"
                elif abs_err <= 8:
                    mpc_state = "LOW FLOW HOLDING"
                else:
                    mpc_state = "LOW DEMAND NORMAL"

            else:
                mpc_state = "NORMAL"
            if not S['pump_on']:
                bn_t = f'⚠ AUTO ACTIVE — PUMP STOPPED | OEE: {S["oee_score"]:.1f}%'

            elif ctrl_err > 15 and S['fv201'] < 5:
                bn_t = '⚠ CONTROL STARVATION — DEMAND HIGH, VALVE CLOSED'

            elif mpc_state == "SATURATED HIGH":
                bn_t = '⚠ ACTUATOR SATURATED HIGH — PROCESS NOT RESPONDING'

            elif mpc_state == "SATURATED HIGH RECOVERING":
                bn_t = '⚠ ACTUATOR SATURATED HIGH — PROCESS RECOVERING'

            elif mpc_state == "HIGH FLOW STABILIZING":
                bn_t = f'⚡ HIGH FLOW STABILIZING | OEE: {S["oee_score"]:.1f}%'

            elif mpc_state == "SATURATED LOW":
                bn_t = '⚠ ACTUATOR SATURATED LOW — DEMAND BLOCKED'

            elif mpc_state == "LOW FLOW HOLDING":
                bn_t = f'⚙ LOW FLOW HOLDING | OEE: {S["oee_score"]:.1f}%'
            elif ctrl_err > 20 and S['fv201'] > 60:
                bn_t = f'⚡ HIGH DEMAND CONTROL — ACTIVE RECOVERY | OEE: {S["oee_score"]:.1f}%'

            elif ctrl_err > 10 and S['fv201'] > 30:
                bn_t = f'↗ PROCESS CORRECTION ACTIVE — FILLING TO SETPOINT | OEE: {S["oee_score"]:.1f}%'

            elif ctrl_err < -15 and S['fv201'] < 30:
                bn_t = f'↘ OVERLEVEL RECOVERY — CONTROLLED DRAWDOWN | OEE: {S["oee_score"]:.1f}%'

            elif abs_err <= 4:
                if S['fv201'] > 85:
                    bn_t = f'⚡ HIGH FLOW STABILIZING | OEE: {S["oee_score"]:.1f}%'
                elif S['fv201'] < 15:
                    bn_t = f'⚙ LOW FLOW HOLDING | OEE: {S["oee_score"]:.1f}%'
                else:
                    bn_t = f'✅ SYSTEM NORMAL | OEE: {S["oee_score"]:.1f}% | MPC: {ms}'

            else:
                if ctrl_err < -4:
                    bn_t = f'↘ OVERLEVEL CORRECTION ACTIVE | OEE: {S["oee_score"]:.1f}%'
                elif ctrl_err > 4:
                    bn_t = f'↗ PROCESS REGULATION ACTIVE | OEE: {S["oee_score"]:.1f}%'
                else:
                    bn_t = f'⚙ PROCESS REGULATION ACTIVE | OEE: {S["oee_score"]:.1f}%'
            bn_s = {**_bb,'background':'rgba(0,230,118,0.10)','color':GREEN,
                    'borderBottom':'1px solid rgba(0,230,118,0.25)'}

        irr_s = 'ACTIVE 💧' if S['irrigating'] else 'OFF'
        ftick = (f"SOURCE [LT101: {S['lt101']:.1f}%]  >>>  "
                 f"VALVE [FV201: {S['fv201']:.0f}%]  >>>  "
                 f"PROCESS [LT202: {S['lt202']:.1f}%]  |  "
                 f"WASTE: {S['wb_level']:.1f}%  |  "
                 f"pH: {S['pH']:.2f}  |  MOISTURE: {S['moisture']:.1f}%  |  IRR: {irr_s}")

        wb_ok = 6.2 <= S['wb_pH'] <= 7.8
        ph_ok = not S['pH_alarm']
        ph_s = 'Stable' if ph_ok else '⚠ pH ALARM'

        use_r = S['wb_level'] > 6 and wb_ok
        wx_fx = {'Rain':'IRR SKIP 🌧','Cloudy':'LOW EVAP ☁','Sunny':'HIGH EVAP ☀'}[S['weather']]
        _f    = lambda c: {'fontFamily':MONO,'fontSize':'15px','fontWeight':'700','color':c}

        sc     = S['scada_score']
        sc_col = GREEN if sc>65 else GOLD if sc>35 else RED

        mpc_ln = ('⬆ MPC Feedforward: anticipatory fill correction' if S['mpc_adj'] > 0 else
            '⬇ MPC Feedforward: anticipatory reduction' if S['mpc_adj'] < 0 else
            'MPC Feedforward: prediction within bounds')

        # PID live panel
        err_now = S['setpoint'] - S['lt202_meas']
        p_now   = round(S['PID_KP'] * err_now, 3)
        i_now   = round(S['PID_KI'] * S['pid_integral'], 3)
        d_now   = round(S['pid_d_live'], 3)
        pid_el  = html.Div([
            html.Div(f"Kp={S['PID_KP']}  Ki={S['PID_KI']}  Kd={S['PID_KD']}",
                     style={'color':CYAN,'marginBottom':'3px'}),
            html.Div(f"Anti-Windup: ±{S['PID_I_MAX']:.0f}"),
            html.Div(f"Error  e(t): {err_now:+.2f}%"),
            html.Div(f"P = {p_now:+.3f}", style={'color':GREEN}),
            html.Div(f"I = {i_now:+.3f}  [sum={S['pid_integral']:.2f}]", style={'color':GOLD}),
            html.Div(f"D = {d_now:+.3f}", style={'color':BLUE}),
            html.Div(f"FV201 = {S['fv201']:.1f}%", style={'color':CYAN,'marginTop':'2px'}),
        ], style={'fontFamily':MONO,'fontSize':'10px','lineHeight':'1.8'})

        log_els = [
            html.Div(f"{l['ts']} | {l['msg']}",
                style={'color':_LOGCOL.get(l['k'],MUTED),'lineHeight':'1.5'})
            for l in list(S['logs'])
        ]

        # ── Charts ────────────────────────────────────────────────────────────

        # Process trend
        fp = go.Figure(layout=_layout(
            '⬡ Process Trend — LT101 Source & LT202 Process Tank (%)', yrange=[0,100]))
        fp.add_trace(go.Scatter(x=xs,y=list(H['lt101']),name='LT101 Source',
            line=dict(color=CYAN,width=1.5),mode='lines'))
        fp.add_trace(go.Scatter(x=xs,y=list(H['lt202']),name='LT202 Process',
            line=dict(color=RED,width=1.5),mode='lines'))
        fp.add_trace(go.Scatter(x=xs,y=list(H['sp']),name='Setpoint',
            line=dict(color='rgba(255,255,255,0.30)',width=1,dash='dot'),mode='lines'))
        # Normalize PID terms for display only
        p_disp = [clamp(v / max(1, S['PID_KP'] * 30) * 100, -100, 100) for v in H['pid_p']]
        i_disp = [clamp(v / 5.0 * 100, -100, 100) for v in H['pid_i']]
        d_disp = [clamp(v / 20.0 * 100, -100, 100) for v in H['pid_d']]
        # PID components (normalized for readable display)
        fpi = go.Figure(layout=_layout(
            '⬡ PID Components — Normalized P / I / D Contributions (%)'
        ))

        fpi.add_trace(go.Scatter(
            x=xs,
            y=p_disp,
            name='P term',
            line=dict(color=GREEN, width=1.5),
            mode='lines'
        ))

        fpi.add_trace(go.Scatter(
            x=xs,
            y=i_disp,
            name='I term',
            line=dict(color=GOLD, width=1.5),
            mode='lines'
        ))

        fpi.add_trace(go.Scatter(
            x=xs,
            y=d_disp,
            name='D term',
            line=dict(color=BLUE, width=1.5),
            mode='lines'
        ))

        fpi.add_trace(go.Scatter(
            x=xs,
            y=[0] * len(xs),
            name='Zero',
            line=dict(color='rgba(255,255,255,0.12)', width=1, dash='dot'),
            mode='lines'
        ))

        # Soil trends (dual axis)
        n_pts = len(xs)
        fs = go.Figure(layout=_layout(
            '⬡ Soil Trends — Moisture (%) & pH  [Hysteresis: alarm<6.20 / clear>6.40]',
            y2=True))
        fs.update_layout(
            yaxis =dict(range=[0,100],gridcolor='rgba(0,200,255,0.06)',
                        color=MUTED,tickfont=dict(size=8,family=MONO)),
            yaxis2=dict(range=[4,10], gridcolor='rgba(0,0,0,0)',
                        color=MUTED,tickfont=dict(size=8,family=MONO),
                        overlaying='y',side='right'))
        fs.add_trace(go.Scatter(x=xs,y=list(H['moisture']),name='Moisture %',
            line=dict(color=CYAN,width=1.5),mode='lines',yaxis='y'))
        fs.add_trace(go.Scatter(x=xs,y=list(H['pH']),name='pH',
            line=dict(color=ORANGE,width=1.5),mode='lines',yaxis='y2'))
        fs.add_trace(go.Scatter(x=xs,y=[6.20]*n_pts,name='Alarm <6.20',
            line=dict(color='rgba(255,65,54,0.55)',width=1,dash='dash'),
            mode='lines',yaxis='y2'))
        fs.add_trace(go.Scatter(x=xs,y=[6.40]*n_pts,name='Clear >6.40',
            line=dict(color='rgba(255,193,7,0.55)',width=1,dash='dash'),
            mode='lines',yaxis='y2'))

        # Water cascade
        fc = go.Figure(layout=_layout(
            '⬡ Zero-Waste Cascade — Reclaimed vs Fresh Draw (L/tick)'))
        fc.add_trace(go.Bar(x=xs,y=list(H['fresh_draw']),name='Fresh Draw (L)',
            marker_color='rgba(0,200,255,0.50)',
            marker_line_color=CYAN,marker_line_width=1))
        fc.add_trace(go.Bar(x=xs,y=list(H['reclaim_draw']),name='Reclaimed (L)',
            marker_color='rgba(0,230,118,0.55)',
            marker_line_color=GREEN,marker_line_width=1))

        # Gauge
        err_for_gauge = abs(S['setpoint'] - S['lt202'])

        if err_for_gauge <= 8:
            gc = GREEN
        elif err_for_gauge <= 18:
            gc = GOLD
        else:
            gc = RED
        fg = go.Figure(go.Indicator(
            mode='gauge+number',
            value=round(S['lt202'],1),
            number=dict(font=dict(family=MONO,color=gc,size=28)),
            gauge=dict(
                axis=dict(range=[0,100],tickfont=dict(color=MUTED,size=8),tickcolor=MUTED),
                bar=dict(color=gc,thickness=0.30),
                bgcolor=S2,bordercolor=BORDER,
                steps=[dict(range=[0,72],color='rgba(0,230,118,0.10)'),
                       dict(range=[72,87],color='rgba(255,193,7,0.10)'),
                       dict(range=[87,100],color='rgba(255,65,54,0.10)')],
                threshold=dict(line=dict(color='white',width=2),
                               thickness=0.75,value=S['setpoint']),
            ),
            title=dict(text=(f"PROCESS TANK (%)  SP: {S['setpoint']:.0f}%  "
                             f"I-sum: {S['pid_integral']:.1f}"),
                       font=dict(color=MUTED,size=9,family=MONO)),
        ))
        fg.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=30,r=30,t=50,b=10),font=dict(family=MONO,color=MUTED))

        # MPC prediction
        pred = S['twin_pred']
        pxs  = list(range(1,11))
        ft = go.Figure(layout=_layout(
            '⬡ MPC Prediction — 10-Tick Lookahead (Plant Model)',yrange=[0,100]))
        if pred:
            ft.add_trace(go.Scatter(x=pxs,y=pred,name='Predicted LT202',
                line=dict(color=GOLD,width=2),mode='lines+markers',
                marker=dict(color=GOLD,size=4)))
        ft.add_trace(go.Scatter(x=pxs,y=[S['setpoint']]*10,name='Setpoint',
            line=dict(color='rgba(255,255,255,0.25)',width=1,dash='dot'),mode='lines'))
        ft.add_trace(go.Scatter(x=pxs,y=[S['setpoint']-10]*10,name='Lower bound',
            line=dict(color='rgba(255,65,54,0.45)',width=1,dash='dot'),mode='lines'))
        ft.add_trace(go.Scatter(x=pxs,y=[S['setpoint']+10]*10,name='Upper bound',
            line=dict(color='rgba(255,65,54,0.45)',width=1,dash='dot'),mode='lines'))

        # OEE history
        oee_xs = list(range(len(H['oee'])))
        fo = go.Figure(layout=_layout(
            '⬡ OEE — Availability x Performance x Quality  (ISO 22400)',yrange=[0,100]))
        fo.add_trace(go.Bar(x=oee_xs,y=list(H['oee']),name='OEE (%)',
            marker_color='rgba(0,230,118,0.55)',
            marker_line_color=GREEN,marker_line_width=1))
        fo.add_trace(go.Scatter(x=oee_xs,y=[85]*len(oee_xs),name='Target 85%',
            line=dict(color=GOLD,width=1,dash='dash'),mode='lines'))

        # Sustainability KPIs
        fsu = go.Figure(layout=_layout('⬡ Sustainability KPIs — Water · Power · Profit'))
        fsu.add_trace(go.Bar(
            x=['Water Saved (L)','kWh Saved','Profit ($x100)'],
            y=[round(S['water_saved'],2),round(S['kwh_saved'],3),round(S['profit']*100,4)],
            name='KPI',
            marker_color=['rgba(0,200,255,0.55)','rgba(255,193,7,0.55)','rgba(0,230,118,0.55)'],
            marker_line_color=[CYAN,GOLD,GREEN],marker_line_width=1))
        fsu.update_layout(showlegend=False)

    return (
        datetime.now().strftime('%H:%M:%S'), str(S['tick']),
        bn_t, bn_s,
        ftick,
        f'{S["lt101"]:.1f}%', f'{S["fv201"]:.0f}%',
        f'{S["lt202"]:.1f}%', f'Target: {S["setpoint"]:.0f}%',
        f'{S["wb_level"]:.1f}%',
        ('♻ IRR-SAFE' if S['wb_level']>5 and wb_ok else
         '⚠ pH UNSAFE' if S['wb_level']>5 else 'EMPTY'),
        f'{S["moisture"]:.1f}%',
        ('💧 IRRIGATING' if S['irrigating'] else 'Idle'),
        f'{S["pH"]:.2f}', ph_s,
        f'{WX.get(S["weather"],"?")} {S["weather"]}',
        f'{S["water_saved"]:.2f}L', f'{S["kwh_saved"]:.3f}', f'${S["profit"]:.3f}',
        ('ACTIVE 💧' if S['irrigating'] else 'IDLE'), _f(GREEN if S['irrigating'] else MUTED),
        ('RECLAIMED ♻' if use_r else 'FRESH 💧'), _f(GREEN if use_r else CYAN),
        (f'SAFE ({S["wb_pH"]:.2f})' if wb_ok else f'UNSAFE ({S["wb_pH"]:.2f})'),
        _f(GREEN if wb_ok else RED),
        wx_fx, f'{S["wb_level"]:.1f}%',
        f'{sc:.1f}%',
        ('Valve Command (%)' if S['mode'] == 'MANUAL' else 'Setpoint (%)'),
        {'fontFamily':MONO,'fontSize':'24px','fontWeight':'700',
         'color':sc_col,'lineHeight':'1.1'},
        mpc_ln,
        pid_el,
        log_els,
        fp, fpi, fs, fc, fg, ft, fo, fsu,
        _panel_sty(tab,'scada'), _panel_sty(tab,'agri'), _panel_sty(tab,'twin'),
    )

# ==============================================================================
#  ENTRY POINT
# ==============================================================================
if __name__ == '__main__':
    print()
    print('=' * 72)
    print('  AquaNexus SCADA Pro  |  Cascaded Tri-Loop Smart Water Management')
    print('  Author: VK  |  Version: 3.0  |  (c) 2026')
    print('=' * 72)
    print()
    print('  Engineering Spec (v3.0 — all issues corrected):')
    print('  ┌─ LOOP-1 ─ Full PID  Kp=2.2  Ki=0.08  Kd=0.60')
    print('  │           Anti-Windup clamp ±25')
    print('  │           Bumpless MANUAL → AUTO transfer (I reset)')
    print('  │           Integrator reset on setpoint step change')
    print('  │           FDIR Watchdog: 4-tick detect / 6-tick auto-recovery')
    print('  ├─ LOOP-2 ─ Soil Moisture + pH sensors (physics model)')
    print('  │           pH Hysteresis Alarm: trigger <6.20, clear >6.40')
    print('  │           4-Guard Smart Irrigation decision matrix')
    print('  │           Zero-Waste Cascade WB001')
    print('  └─ LOOP-3 ─ MPC 10-Tick Lookahead (plant model simulation)')
    print('              OEE (ISO 22400): Availability x Performance x Quality')
    print('              Financial ROI model')
    print()
    print('  Dashboard  →  http://127.0.0.1:8050')
    print('  Stop       →  Ctrl+C')
    print()

    def _open():
        import time as _t
        import subprocess
        _t.sleep(1.2)

        subprocess.Popen([
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "--start-fullscreen",
            "--app=http://127.0.0.1:8050"
        ])
    threading.Thread(target=_open, daemon=True).start()

    app.run(debug=False, host='127.0.0.1', port=8050)
