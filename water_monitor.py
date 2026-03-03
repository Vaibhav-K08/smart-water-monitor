"""
Smart Water Tank Monitoring and Control System
Author: Vaibhav Krishna V | NMIT Bengaluru | 1NT22EC182
"""

import numpy as np
import csv
import logging
import time
import os

# ── Configuration ─────────────────────────────────────
TANK_CAPACITY   = 1000.0   # Litres
LOWER_THRESHOLD = 200.0    # Pump ON  below this (20%)
UPPER_THRESHOLD = 900.0    # Pump OFF above this (90%)
CONSUMPTION_RATE = 8.0     # Litres per step
REFILL_RATE      = 20.0    # Litres per step when pump is ON
SIMULATION_STEPS = 150

LOG_FILE  = "events.log"
CSV_FILE  = "tank_log.csv"

# ── Logging Setup ──────────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

# ── Water Level Simulator ──────────────────────────────

class WaterTankSimulator:
    def __init__(self):
        self.source_level  = 468.0   # Litres
        self.process_level = 227.0
        self.reserve_level = 400.0
        self.pump_active   = False
        self.pump_events   = 0

    def step(self):
        # Random consumption
        consumption = np.random.uniform(5.0, 12.0)
        self.source_level  = max(0, self.source_level  - consumption * 0.5)
        self.process_level = max(0, self.process_level - consumption * 0.3)
        self.reserve_level = max(0, self.reserve_level - consumption * 0.2)

        # Pump logic — threshold based
        if self.source_level < LOWER_THRESHOLD and not self.pump_active:
            self.pump_active = True
            self.pump_events += 1
            logging.info(f"PUMP ON  | Source: {self.source_level:.1f}L | "
                         f"Process: {self.process_level:.1f}L")

        if self.source_level >= UPPER_THRESHOLD and self.pump_active:
            self.pump_active = False
            logging.info(f"PUMP OFF | Source: {self.source_level:.1f}L")

        if self.pump_active:
            self.source_level  = min(TANK_CAPACITY, self.source_level  + REFILL_RATE * 0.6)
            self.reserve_level = min(TANK_CAPACITY, self.reserve_level + REFILL_RATE * 0.4)

        # Balancing between tanks
        if self.source_level > self.process_level + 50:
            transfer = min(5.0, self.source_level - self.process_level)
            self.source_level  -= transfer * 0.3
            self.process_level += transfer * 0.3

        return {
            "source":  round(self.source_level,  1),
            "process": round(self.process_level, 1),
            "reserve": round(self.reserve_level, 1),
            "pump":    self.pump_active
        }

    def get_pct(self):
        return {
            "source":  round(self.source_level  / TANK_CAPACITY * 100, 1),
            "process": round(self.process_level / TANK_CAPACITY * 100, 1),
            "reserve": round(self.reserve_level / TANK_CAPACITY * 100, 1),
        }

# ── Main Monitor Loop ──────────────────────────────────

def run_monitor():
    tank = WaterTankSimulator()

    print("=" * 65)
    print("  Smart Water Tank Monitoring & Control System")
    print("  Author: Vaibhav Krishna V | NMIT | 1NT22EC182")
    print("=" * 65)
    print(f"  Tank Capacity   : {TANK_CAPACITY:.0f} L")
    print(f"  Pump ON  below  : {LOWER_THRESHOLD:.0f} L ({LOWER_THRESHOLD/TANK_CAPACITY*100:.0f}%)")
    print(f"  Pump OFF above  : {UPPER_THRESHOLD:.0f} L ({UPPER_THRESHOLD/TANK_CAPACITY*100:.0f}%)")
    print("=" * 65)
    print(f"  {'Step':>4} | {'Source':>8} | {'Process':>8} | "
          f"{'Reserve':>8} | {'Pump':>6} | Status")
    print(f"  {'-'*60}")

    # Open CSV for logging
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Step", "Source_L", "Process_L", "Reserve_L", "Pump"])

        for step in range(1, SIMULATION_STEPS + 1):
            state = tank.step()
            pct   = tank.get_pct()

            pump_str = "ON  🟢" if state["pump"] else "OFF ⚪"
            if state["source"] < LOWER_THRESHOLD * 1.2:
                status = "⚠ LOW SOURCE"
            elif state["source"] > UPPER_THRESHOLD * 0.95:
                status = "✓ FULL"
            else:
                status = "✓ Normal"

            print(f"  {step:>4} | {state['source']:>6.1f}L | "
                  f"{state['process']:>7.1f}L | {state['reserve']:>7.1f}L | "
                  f"{pump_str} | {status}")

            writer.writerow([step, state["source"], state["process"],
                             state["reserve"], state["pump"]])
            time.sleep(0.03)

    print(f"\n  Simulation complete.")
    print(f"  Total pump activations : {tank.pump_events}")
    print(f"  Final levels — "
          f"Source: {tank.source_level:.1f}L | "
          f"Process: {tank.process_level:.1f}L | "
          f"Reserve: {tank.reserve_level:.1f}L")
    print(f"\n  Logs saved to: {CSV_FILE} and {LOG_FILE}")

if __name__ == "__main__":
    run_monitor()
