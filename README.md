# Snap7 Qt Monitor & Diagnostic Station

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()
[![Framework: PySide6](https://img.shields.io/badge/Framework-PySide6%20(Qt6)-green.svg)]()
[![Platform: Windows | Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()

A high-performance desktop commissioning workbench and diagnostic HMI for Siemens S7 PLCs, built with **PySide6 (Qt for Python)** and powered by the **Snap7** industrial communication suite.

Designed for automation engineers, system integrators, and software developers to inspect, validate, and test S7 Data Block (DB) communications during commissioning without requiring full engineering software suites like Step 7 or TIA Portal.

---

## 🎯 System Architecture & Design

The application enforces a strict separation between low-level socket communication, background telemetry polling, and the user interface to ensure high responsiveness and zero UI freezing:


```

┌─────────────────────────────────────────────────────────────┐
│                      PySide6 UI Layer                       │
│     (KPI Cards, PyQtGraph Charts, Event Logs, Settings)     │
└──────────────────────────────▲──────────────────────────────┘
│ Qt Signals & Slots
┌──────────────────────────────▼──────────────────────────────┐
│                    PLCWorker (QThread)                      │
│   (Background cyclic polling, reconnection, state tracker)  │
└──────────────────────────────▲──────────────────────────────┘
│ High-level Typed API
┌──────────────────────────────▼──────────────────────────────┐
│                     ForkClient Bridge                       │
│    (Python wrapper around python-snap7 / snap7 native DLL)  │
└──────────────────────────────▲──────────────────────────────┘
│ ISO-on-TCP (RFC 1006 / S7comm)
▼
Physical PLC or Mock Server

```

---

## ⚙️ Key Technical Features

* **Decoupled Asynchronous Polling:** Dedicated `QThread` polling loop running at a configurable interval (default 500 ms) guarantees an uninterrupted 60 FPS UI rendering pipeline.
* **Dual-Mode Operation (Live vs. Simulated):**
  * **LIVE Mode:** Connects to real Siemens hardware or a local Snap7 server over TCP port 102.
  * **SIMULATED Mode:** Built-in dynamic math generator simulating realistic thermal process curves with drift, Gaussian noise, and system resource metrics.
* **Automatic Network Failover:** Detects connection drops and gracefully degrades to internal loopback simulation to keep the UI operative without crashes or data corruption.
* **Dynamic S7 Mock Server (`snap7_server.py`):** Standalone multi-threaded server emulating a real Siemens PLC with auto-updating registers for offline integration testing.
* **Low-Overhead Telemetry Charting:** Powered by `pyqtgraph` with hardware-accelerated time-series rendering, custom dashed setpoint overlays, and mode-dependent visual cues.
* **Protocol Diagnostic Terminal:** Structured console logging incoming and outgoing frames, connection states, and setpoint dispatches with millisecond-accurate timestamps.

---

## 📊 Default Memory Mapping (DB1)

The station reads and writes to structured registers in **Data Block 1 (DB1)**:

| Offset | S7 Data Type | Python Equivalent | Description | Access |
| :--- | :--- | :--- | :--- | :--- |
| **0** | `REAL` | `float` (32-bit IEEE) | Process Temperature (°C) | Read-only |
| **4** | `REAL` | `float` (32-bit IEEE) | System CPU Metric (%) | Read-only |
| **8** | `REAL` | `float` (32-bit IEEE) | System RAM Metric (%) | Read-only |
| **12** | `REAL` | `float` (32-bit IEEE) | Temperature Setpoint Target | Read / Write |
| **16** | `BYTE` | `int` (8-bit unsigned) | Heartbeat Rolling Counter (0–255) | Read-only |

---

## 📁 Repository Structure


```

snap7-qt-monitor/
├── scada_dashboard.py       # Main GUI entry point & thread orchestrator
├── fork_bridge.py           # High-level typed client wrapper around Snap7
├── snap7_server.py          # Standalone dynamic mock PLC server
├── sensor_simulator.py      # Mathematical process generator (noise & drift)
├── test_bridge.py           # Comprehensive connectivity & unit test suite
├── config.ini               # Persistent network configuration (IP, Rack, Slot)
├── config.yaml              # Mock server memory configuration
├── requirements.txt         # Python package dependencies
├── snap7.dll                # Native Snap7 64-bit communication binary
├── ui/                      # Modular Qt UI components
│   ├── dashboard_ui.py      # Main window & layout orchestration
│   ├── chart_widget.py      # Real-time pyqtgraph telemetry widget
│   ├── status_cards.py      # KPI cards with live state indicators
│   ├── asset_panel.py       # Station navigation sidebar
│   ├── log_widget.py        # Real-time event logging terminal
│   ├── theme.py             # Dark industrial palette design tokens
│   ├── views.py             # Main dashboard multi-column layout
│   └── widgets.py           # Header, footer, and interactive control panels
└── LICENSE                  # LGPL-3.0 License

```

---

## 🚀 Getting Started

### 1. Requirements & Prerequisites

* Python **3.10+** (64-bit recommended).
* Windows 10/11 or Linux x86_64.
* For physical PLCs (S7-1200 / S7-1500):
  * **"Permit access with PUT/GET communication"** must be enabled in the CPU hardware configuration.
  * Data Block DB1 must use **Standard (Non-Optimized)** block access.

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone [https://github.com/esmaeilireza/snap7-qt-monitor.git](https://github.com/esmaeilireza/snap7-qt-monitor.git)
cd snap7-qt-monitor
pip install -r requirements.txt

```

### 3. Launching the Station

#### Option A: Offline Simulation Mode (No hardware needed)

```bash
python scada_dashboard.py --simulate

```

#### Option B: Testing with Local Mock Server

1. Start the mock PLC server in a separate terminal:
```bash
python snap7_server.py

```


2. Launch the monitor dashboard:
```bash
python scada_dashboard.py

```


3. Set the target IP to `127.0.0.1`, Rack `0`, Slot `1` inside the **Settings** page or verify via `config.ini`.

#### Option C: Live PLC Deployment

Launch the dashboard and input your hardware parameters:

```bash
python scada_dashboard.py --ip 192.168.0.1 --rack 0 --slot 1

```

---

## ⌨️ Shortcuts & Hotkeys

* **`Ctrl + Shift + D`**: Toggles **High-Speed Demo Mode** (accelerates simulator drift, introduces random dynamic jumps, and enables the demo badge for video recording and demonstrations).

---

## 📄 License

This software is distributed under the **GNU Lesser General Public License v3.0 (LGPLv3)**.

---

## 🌐 Acknowledgments

* **Davide Nardella** – Creator of the foundational [Snap7](https://www.google.com/search?q=https://snap7.sourceforge.net/) Ethernet communication library.
* **Gijs Molenaar** – Developer of the Python bindings for Snap7 (`python-snap7`).
* The **Qt Company** & **PyQtGraph team** for modern cross-platform GUI and visualization tooling.

```

---