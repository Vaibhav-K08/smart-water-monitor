# 💧 Smart Water Tank Digital Twin SCADA System

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

*A 3D SCADA digital twin that monitors three water tanks in real time, automates flow between them, and visualizes everything on a live glass style web dashboard.*

</div>

---

## What This Does

Three tanks — Source, Process, and Reserve; run as a live digital twin. The system tracks water levels every second, triggers pump transfers automatically when thresholds are breached, and renders the entire plant as an interactive 3D visualization in the browser at `http://localhost:5000`.

Tank colors shift from blue to orange to red as levels drop, the transfer pipe turns cyan when flow is active, and a commentary engine describes what the system is currently doing in plain language.

---

## How It Works

```
Simulation Loop (1 second per step)
        ↓
  Source   ← slow natural inflow
  Process  ← continuous consumption (faster drain)
  Reserve  ← standby, assists only when Process is critical
        ↓
  Transfer Logic
  ├── Source → Process pump ON  when Process < 40% and Source > 50%
  ├── Source → Process pump OFF when Process > 70%
  └── Reserve → Process assist  when Process < 35% and Reserve > 40%
        ↓
  3D Mesh Visualization   ← tank fill height updates live
  Billboard Labels        ← name + percentage per tank
  Transfer Pipe           ← cyan when active, grey when idle
        ↓
  Flask serves dashboard  ← Plotly 3D scene, updates every second
```

---

## The 3D Visualization

Each tank is rendered as a 3D mesh with two layers: a translucent grey frame and a colored water fill that scales in height with the actual level. The water color changes based on how full the tank is:

| Level | Color | Meaning |
|---|---|---|
| Above 45% | Blue | Normal |
| 30 — 45% | Orange | Warning |
| Below 30% | Red | Critical |

The transfer pipe between Source and Process is rendered as a 3D line; cyan when the pump is running, grey when idle. Billboard labels above each tank show the name and live percentage, styled with system fonts for a clean look.

---

## Dashboard

Glass-style web UI served at `http://localhost:5000`:

- Left panel — full height 3D Plotly plant visualization
- Right panel — live level readings (Source, Process, Reserve), current status commentary, and a color legend
- Updates every second via `/data` endpoint
- Dark background, frosted glass cards, Apple system font stack

---

## Features

- Three tank digital twin with physically realistic flow dynamics
- Automatic pump control; no manual intervention needed
- Reserve tank acts as a secondary failsafe when Process drops critically low
- 3D mesh visualization with live fill height and color coded water levels
- Transfer pipe changes color when flow is active
- Commentary engine describes system state in plain language
- Flask + Plotly web dashboard, runs entirely in the browser

---

## Tech Stack

| Library | Purpose |
|---|---|
| Flask | Web server and live data API |
| Plotly | 3D tank mesh and transfer pipe visualization |
| threading | Simulation loop runs parallel to web server |

No external dependencies beyond Flask and Plotly.

---

## Running It

```bash
git clone https://github.com/YOUR_USERNAME/smart-water-monitor.git
cd smart-water-monitor
pip install -r requirements.txt
python water_monitor.py
```

Open `http://localhost:5000` in your browser. The simulation starts immediately.

---

## Project Structure

```
smart-water-monitor/
├── water_monitor.py
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Industrial Applications

- Automated tank monitoring in residential and commercial buildings
- Agricultural irrigation control systems
- Industrial water storage and distribution automation
- Smart pump automation systems
- Integration into IoT based water monitoring platforms

## Societal Applications

- Reduction of water wastage through automation
- Improved water availability in rural regions
- Affordable smart water management systems
- Reliable household water supply automation
- Sustainable water usage support

---

## Author

**Vaibhav Krishna V**  
Electronics & Communication Engineer  
📧 vaibhavkv078@gmail.com

---

## License

MIT — see [LICENSE](LICENSE) for details.
