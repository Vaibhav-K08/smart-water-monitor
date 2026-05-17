# AquaNexus SCADA Pro: Cascaded Tri-Loop Smart Water Management System

<div align="center">

![Version](https://img.shields.io/badge/Version-3.0-00ccff?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white)
![Dash](https://img.shields.io/badge/Dash%20%2B%20Plotly-SCADA%20Dashboard-purple?style=flat-square)
![Standard](https://img.shields.io/badge/OEE-ISO%2022400-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-brightgreen?style=flat-square)

**Author:** Vaibhav Krishna V &nbsp;|&nbsp; **Architecture:** LOOP-1: PID+SCADA → LOOP-2: AGRI → LOOP-3: MPC+TWIN

</div>

---

## What This Is

AquaNexus SCADA Pro is a real-time smart water management system that brings together three interlocked control disciplines — industrial process control, agricultural intelligence, and model predictive control into a single cohesive platform running on a Python backend with a live Dash dashboard.

The system manages the flow path from a source reservoir (LT101) through a precision motorised valve (FV201) into a process tank (LT202), while simultaneously monitoring soil moisture and pH for smart irrigation, routing overflow through a waste buffer (WB001) for zero-discharge reclamation, predicting future tank levels ten ticks ahead using a digital twin, and computing ISO 22400 OEE continuously.

All three loops run synchronised on a single master tick. Every physical constant: valve stiction thresholds, transport lag, pH drift rates, evaporation coefficients by weather is grounded in engineering reality rather than arbitrary interpolation.

---

## Why Three Loops

A conventional PID loop manages the tank level. That is the minimum viable solution. But a real water management system has to answer harder questions: *What happens if the valve is stuck and the tank isn't responding?* *Is it worth pulling fresh water when the reclaim buffer has usable water at a safe pH?* *Is the controller going to overshoot in the next ten seconds, and if so, can we correct for it now?*

Loop-2 exists because irrigation decisions are not binary. Pumping water onto soil when it is already raining wastes energy and causes runoff. Irrigating with reclaimed water at pH 8.3 damages crops. The 4-guard decision matrix checking soil dryness, weather, tank safety, and reclaimed water pH simultaneously is what separates a real agricultural control system from a timer-based sprinkler.

Loop-3 exists because PID operates on the past. MPC operates on the future. The feedforward correction computed from the 10-tick plant simulation preemptively adjusts the valve setpoint before the error grows, reducing overshoot and settling time without the cost of a more aggressive Ki that would cause integrator windup.

The three loops are not independent modules bolted together. They share state: MPC feedforward flows into the PID command, overflow from Loop-1 replenishes the WB001 buffer consumed by Loop-2, and Loop-3's OEE degrades immediately when Loop-2 flags a pH alarm.

---

## System Architecture

```
Master Tick  (1 Hz)
│
├── LOOP-3  Model Predictive Control  ← runs FIRST
│     10-tick plant simulation → feedforward adj ∈ [−15, +15] %
│
├── LOOP-1  Full PID Process Control
│     Sensor filter (α=0.22) → PID (Kp=2.2 Ki=0.08 Kd=0.6)
│     Anti-windup clamp (±25) → MPC feedforward inject
│     Valve deadband + stiction → Transport lag (6-tick FIFO)
│     Overflow → WB001 replenishment
│     FDIR: 4-tick detect → 6-tick auto-recovery
│
├── LOOP-2  Agricultural Intelligence
│     Weather simulation → Soil moisture physics → pH drift model
│     pH hysteresis alarm (IEC 61511)
│     4-Guard irrigation matrix
│     Zero-Waste Cascade: WB001 reclaim priority over fresh draw
│
└── LOOP-3  KPIs & Financial Twin
      OEE (ISO 22400): Availability × Performance × Quality
      SCADA Score: OEE(55%) + SP-Adherence(35%) + Sustainability(10%)
      Financial ROI: water_saved × $0.0012 + kwh_saved × $0.13
      CSV telemetry export (15-column log, full history)

Dash Frontend  →  http://127.0.0.1:8050  (3 tabs, 1-second polling)
```

---

## Engineering Depth

### Loop-1 — Full PID with Anti-Windup, Valve Dynamics, and Transport Lag

The PID implementation is engineering-correct in ways that matter in production:

**Anti-windup:** The integral term is clamped symmetrically to ±25 and suspended when the valve is saturated (FV201 = 0 or 100%). When the error sign reverses indicating the process is crossing the setpoint, the integral is immediately halved to prevent overshoot from accumulated wind-up:

```python
if err * pid_prev_err < 0:
    pid_integral *= 0.50
```

**Valve dynamics:** The valve does not track its command instantaneously. A deadband of ±0.5% filters out command chatter, and a slew limiter of ±5%/tick (with a 0.55 tracking gain) models the motor-driven actuator's finite response speed. Faults inject a `fault_stuck_valve` flag that freezes valve movement entirely, creating a realistic non-response condition.

**Transport lag:** Inflow does not reach the tank immediately. A six-element FIFO deque delays the inflow signal by six ticks, modelling the pipe transit time between valve and tank. The MPC plant simulation also models this: its predicted inflow is drawn from the same delay structure.

**Sensor filtering:** The LT202 measurement is processed through a first-order low-pass filter with α = 0.22, plus additive Gaussian noise (±0.09%). The controller operates on the filtered measurement, not the raw level; the same way a real SCADA system uses a 4–20 mA signal from a level transmitter rather than ground truth.

**Overflow management:** When LT202 exceeds 96%, the overflow is redirected to WB001 with a 55% capture efficiency. The integrator is simultaneously softened (×0.82) to prevent the controller from aggressively fighting its own overflow. Bumpless MANUAL→AUTO transfer resets the integral to zero on mode switch.

**FDIR watchdog:** Four consecutive ticks where error > 22%, valve > 95%, and level change < 0.03% trips the fault. The system enters FAULT mode, resets the PID state, and after six fault ticks attempts auto-recovery restoring to AUTO with FV201 at 50% and logging a confirmed recovery event.

### Loop-2 — Agricultural Intelligence

**Soil moisture physics:** Evaporation varies by weather: 0.15%/tick (Sunny), 0.06%/tick (Cloudy), 0.00%/tick (Rain). Rainfall adds 0.55% moisture per tick. Additive Gaussian noise (±0.125%) prevents the sensor reading from appearing synthetic.

**Soil pH sensor:** Continuous directional drift at ±0.025 pH/tick, reversing at the bounds 6.0 and 7.9. Additive noise of ±0.02 pH models real sensor variability. This is not a stepped simulation, the pH trace is continuous and indistinguishable from a real electrode sensor output.

**pH hysteresis alarm (IEC 61511):** The alarm triggers below pH 6.20 and does not clear until pH rises above 6.40. The 0.20-unit hysteresis band prevents relay chatter — a standard requirement in process safety instrumentation. When latched, the pH alarm applies a 0.75 penalty factor to the SCADA Score.

**Weather simulation:** Weather transitions follow a weighted Markov-like process: Sunny (50%), Cloudy (33%), Rain (17%). Transitions occur every 60–120 ticks, and each transition is logged to the operator console.

**4-Guard smart irrigation decision matrix:**

| Guard | Condition | Rationale |
|---|---|---|
| 1 | moisture < 52% | Field capacity threshold — irrigation unnecessary above this |
| 2 | weather ≠ Rain | Free moisture incoming; don't irrigate into rain |
| 3 | LT202 > 22% | Protect process tank minimum level before drawing |
| 4 | 6.2 ≤ wb_pH ≤ 7.8 | Reclaimed water pH must be safe for crop root zones |

All four guards must be simultaneously true for irrigation to activate.

**Zero-Waste Cascade:** When irrigation triggers and WB001 has >6% level at safe pH, reclaimed water is used first: up to 0.32 L drawn at 0.08 × wb_level per tick, delivering 0.75 moisture efficiency to soil and crediting water_saved. Only when the buffer is depleted or pH is out of range does the system fall back to fresh draw from LT202.

### Loop-3 — Digital Twin, MPC, and OEE

**MPC feedforward:** The plant simulation runs forward ten ticks using the same physics as Loop-1 (valve → inflow 1.45 L/tick, outflow = 0.05 × LT202^0.5) but with a simplified PI-like valve model. The error between the predicted 10th-tick level and setpoint is mapped to a feedforward correction:

```python
mpc_adj = clamp(pred_err × 0.65, −15.0, +15.0)
```

This correction is injected directly into the PID output each tick not into the setpoint, but into the valve command; so it accelerates filling without disturbing the PID tuning. The MPC runs before Loop-1 every tick, meaning the correction is always one tick ahead of the reactive controller.

**OEE (ISO 22400):** Computed from three independent factors, each with engineering-realistic scaling:

*Availability* = uptime_ticks / (uptime_ticks + fault_ticks). Every tick in FAULT mode reduces this.

*Performance* is tiered on process error magnitude rather than a smooth function, to avoid falsely penalising normal startup transients:

| Error | Performance |
|---|---|
| ≤ 3% | 100% |
| ≤ 8% | 96% |
| ≤ 15% | 90% |
| ≤ 25% | 82% |
| ≤ 35% | 72% |
| > 35% | 60% |

*Quality* combines moisture score (moisture / 55, clamped 0.88–1.0) and pH score (1 − |pH − 7.0| / 3.2, clamped 0.88–1.0), both reflecting crop safety rather than arbitrary thresholds.

OEE is exponentially smoothed (0.82 × previous + 0.18 × instant) to prevent single-tick spikes from misrepresenting sustained performance.

**SCADA Score** is a composite of OEE (55%), setpoint adherence (35%), and sustainability index (10%), with multiplicative safety penalties for pH alarm (×0.75) and active fault (×0.75).

**Financial ROI** accumulates in real time: water_saved × $0.0012/L + kwh_saved × $0.13/kWh. Energy savings credit 0.0015 kWh per tick when the process is well-controlled (|error| < 4%, |MPC adj| < 2%), and 0.0008 kWh per tick during rain (when pump power is avoided).

---

## Dashboard Screenshots

All screenshots are live captures from a running simulation.

### SCADA / PID Tab — Process Regulation Active

Source LT101 at 65.2%, valve FV201 at 25%, process tank LT202 at 40.4% climbing toward 75% setpoint. PID live: Kp=2.2, Ki=0.08, Kd=0.6. Error +32.52%, integral sum accumulating. MPC feedforward active — "anticipatory fill correction" shown on SCADA Score panel. OEE: 49.2%. SCADA Score: 54.38.

![SCADA PID Tab](1.png)

### Agriculture Tab — High Demand Control, Active Recovery

Irrigation ACTIVE, water source FRESH (reclaim buffer exhausted), OB pH reading UNSAFE (8.05) — pH alarm latched. High evaporation weather event in progress. Waste buffer at 4.1%. Zero-Waste Cascade chart shows reclaimed vs. fresh draw history — reclaimed bars (green) dominating early ticks, fresh draw (cyan) taking over as buffer depletes. OEE: 55.4%. SCADA Score: 57.88.

![Agriculture Tab](2.png)

### Digital Twin Tab — Filling to Setpoint

Process tank at 59.6%, valve at 100%, actively filling. Process tank gauge with colour-coded zones (green: within 8% of SP, amber: 8–18%, red: >18%). MPC 10-tick lookahead prediction plot shows LT202 converging toward the 75% setpoint line. OEE trend chart climbing. Sustainability KPIs bar chart: water saved, kWh saved, and profit-scaled profit index. SCADA Score: 60.98.

![Digital Twin Tab](3.png)

---

## Project Structure

```
aquanexus_scada_pro.py        ─ Complete system: 1,428 lines, single-file architecture
├── Design tokens & shared state definition
├── LOOP-3  MPC / Digital Twin              (runs first each cycle)
├── LOOP-1  Full PID + FDIR + valve model
├── LOOP-2  Agricultural intelligence
├── LOOP-3  OEE + SCADA score + financial twin
├── Master tick (thread-safe with lock)
├── CSV export (15-column telemetry log)
├── Dash application layout (3 tabs)
│     ├── SCADA/PID:    process trend, PID component chart, live PID state panel
│     ├── Agriculture:  soil trends, zero-waste cascade chart, weather/irrigation status
│     └── Digital Twin: process gauge, MPC prediction, OEE history, sustainability KPIs
└── Operator console: pump control, auto/manual toggle, fault injection, alarm acknowledge
```

The single-file architecture is intentional. The full engineering logic — control, physics, analytics, and UI can be read, audited, and understood as one complete document without navigating a multi-module project.

---

## Getting Started

```bash
pip install dash plotly
python aquanexus_scada_pro.py
```

The system starts, logs all subsystem initialisation to the operator console, and opens the dashboard at `http://127.0.0.1:8050`. Chrome is launched in fullscreen app mode automatically if found at the default Windows path; any browser pointing to the address will work otherwise.

The dashboard refreshes every second via a Dash interval callback. All data is served from in-memory state protected by a threading lock. CSV export writes a timestamped 15-column file to the working directory on demand.

**Requirements:** Python 3.10+, Dash, Plotly. No database, no message broker, no external services.

---

## CSV Telemetry Export

Each exported file contains the complete rolling history of the simulation:

| Column | Description |
|---|---|
| Tick | Simulation step |
| LT101 (%) | Source tank level |
| LT202 (%) | Process tank level |
| Setpoint (%) | PID setpoint |
| Moisture (%) | Soil moisture |
| pH | Soil pH sensor reading |
| FreshDraw (L) | Fresh water drawn per tick |
| ReclaimDraw (L) | Reclaimed water drawn per tick |
| OEE (%) | ISO 22400 OEE |
| WaterSaved (L) | Cumulative water saved |
| kWhSaved | Cumulative energy saved |
| Profit (USD) | Cumulative financial ROI |
| PID_P | Proportional term contribution |
| PID_I | Integral term contribution |
| PID_D | Derivative term contribution |

A sample export (`AquaNexus_Export_20260512_114512.csv`) is included in this repository.

---

## What This Demonstrates

AquaNexus SCADA Pro covers the full vertical stack of an industrial control system, from sensor physics and actuator dynamics at the bottom to economic KPIs and ISO-standard metrics at the top.

The PID implementation is not textbook. It handles integrator windup from valve saturation, integrator halving on sign reversal, bumpless mode transfer, transport lag, sensor noise, and valve stiction — all of the complications that appear between a clean PID derivation and a controller that actually works on physical hardware.

The agricultural intelligence layer is not a rule engine. It models the physical processes that make irrigation decisions non-trivial: evaporation as a function of solar irradiance, pH drift as a continuous electrochemical process, and reclaimed water suitability as a multi-constraint safety check.

The digital twin is not a monitoring tool. It actively improves control performance every tick through MPC feedforward. The economic layer turns system performance into numbers that mean something to an operations team: litres saved, kilowatt-hours avoided, dollars returned.

Every part of the system is designed to be legible. An engineer reading the source should be able to trace any output on the dashboard back to the exact line of physics or control logic that produced it.

---

## Technical Highlights at a Glance

- **Kp=2.2, Ki=0.08, Kd=0.6** — tuned PID with full anti-windup (±25 clamp, saturation suspension, sign-reversal halving)
- **6-tick FIFO transport lag** on valve-to-tank inflow path, mirrored in MPC plant model
- **α=0.22 first-order sensor filter** + ±0.09% Gaussian noise on LT202 measurement
- **4-consecutive-tick FDIR detection**, 6-tick auto-recovery with integrator reset
- **IEC 61511 pH hysteresis:** alarm < 6.20, clear > 6.40, no relay chatter
- **4-guard smart irrigation matrix** — moisture, weather, tank level, reclaim pH checked simultaneously
- **Zero-Waste Cascade:** reclaimed water priority over fresh draw, 0.75 vs 0.55 moisture delivery efficiency
- **10-tick MPC lookahead** with feedforward adj ∈ [−15, +15] % injected into PID output pre-cycle
- **ISO 22400 OEE** = Availability × Performance (tiered, 6 levels) × Quality (moisture + pH)
- **SCADA Score** = OEE(55%) + SP-Adherence(35%) + Sustainability(10%) × safety penalties
- **Financial ROI** accumulated at $0.0012/L saved + $0.13/kWh saved, shown live on dashboard
- **15-column timestamped CSV export** of full telemetry history on operator demand

---

## Author

**Vaibhav Krishna V**  
Electronics and Communication Engineer
[GitHub](https://github.com/vaibhav-krishna-v ) · [LinkedIn](https://linkedin.com/in/vkv078 )

> *Built on the principle that industrial control systems are only as good as the engineering decisions made at every layer — from sensor noise modelling to economic accountability.*
