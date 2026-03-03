# 💧 Smart Water Tank Monitoring & Control System

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-11557c?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

*Automated water level regulation preventing both overflow and dry-tank conditions — scalable from home to industrial use.*

</div>

---

## 📌 Project Overview

An automated water tank monitoring and control system that maintains safe water levels using continuous monitoring and rule-based automation. The system simulates real-world water consumption and replenishment cycles while ensuring reliable pump control with full event logging.

---

## 🏗️ System Architecture

```
Level Monitoring (Continuous)
        ↓
  Threshold Logic          ← Min / Max level comparison
        ↓
  Pump Control             ← Activate / Deactivate pump
        ↓
  Event Logging            ← CSV + Python logging module
        ↓
  Real-Time Visualization  ← Matplotlib live chart
```

---

## 📊 Key Results

| Result | Application |
|---|---|
| Stable Water Level Control | Maintained safe tank limits |
| Automated Pump Operation | Threshold-based activation |
| Overflow Prevention | Upper limit enforcement |
| Dry Tank Prevention | Lower threshold detection |
| Event Logging | Traceable pump activity |
| Real-Time Monitoring | Continuous visualization |

**Live Monitoring Output (sample):**
- Source: 46.8% | Process: 22.7% | Reserve: 40.0%
- Status: Balancing flow from Source → Process

---

## ✅ Key Features

- 🔴 **Dynamic water level simulation** — models realistic consumption & refill
- 🧠 **Threshold-based automation** — no over-engineering, fully reliable
- 📊 **Dual logging** — CSV storage + Python logging for audit trails
- 🔧 **3-tank model** — Source, Process, Reserve tanks
- 📈 **Real-time Matplotlib visualization** — live level chart with pump status

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `NumPy` | Water level simulation and dynamics |
| `Matplotlib` | Live level trend visualization |
| `csv` | Historical data storage |
| `logging` | Event logging for pump activations |

---

## ⚙️ How to Run

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/smart-water-monitor.git
cd smart-water-monitor
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the simulation
```bash
python water_monitor.py
```

The system will:
- Start simulating water level changes
- Auto-activate/deactivate the pump at thresholds
- Save logs to `tank_log.csv` and `events.log`
- Display a real-time level chart

---

## 📁 Project Structure

```
smart-water-monitor/
├── water_monitor.py        # Main simulation — run this
├── tank_simulator.py       # Dynamic water level model
├── pump_controller.py      # Threshold-based pump automation
├── logger.py               # CSV + event logging module
├── visualizer.py           # Real-time Matplotlib dashboard
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 🏭 Applications

**Industrial:**
- Automated tank monitoring in residential buildings
- Agricultural irrigation tank control
- Industrial water storage automation
- Smart pump automation systems
- Integration into IoT-based water monitoring platforms

**Societal:**
- Reduction of water wastage through automation
- Improved water availability in rural regions
- Affordable smart water management systems
- Sustainable water usage support
- Reliable household water supply automation

---

## 👤 Author

**Vaibhav Krishna V**  
Electronics & Communication Engineering, NMIT Bengaluru  
USN: 1NT22EC182  
📧 vaibhavkv078@gmail.com

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
