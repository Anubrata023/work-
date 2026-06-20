# VECTOR GRID - Parking Intelligence & Enforcement Prioritization

VECTOR GRID is an analytical decision dashboard designed for smart city enforcement (Bengaluru Traffic Police) and logistics dispatch (Flipkart Logistics). It identifies illegal parking hotspots, calculates traffic congestion impact, models spatial spillovers, and simulates tactical enforcement campaigns before teams hit the field.

---

## 🛠️ Platform Core Features

### 1. Strategic Optimization Sandbox Simulator
The Sandbox Simulator is an interactive "What-If" planning workbench. Instead of deploying patrols blindly, supervisors select a target zone (H3 cell) and configure:
* **Force Size Deployment Footprint (Officers):** Number of personnel allocated.
* **Force Allocation Duration Window (Hours):** Patrol time window.

#### 📈 What It Simulates
1. **Projected Constraint Relief Rate (%):** Calculates how much illegal parking will decrease based on patrol friction curves:
   $$\text{Relief} = \min(95.0, \min(82.5, \text{officers} \times 14.2) \times \text{duration\_modifier})$$
2. **Estimated Commuter-Hours Saved (Hrs):** Uses **M/D/1 queuing theory** to calculate delay reductions.

#### 🧮 Mathematical Model (Exponential Decay Capacity)
To resolve the flat-line limitation where large violation clusters yielded $0.0\text{ Hrs}$ saved, we use a continuous exponential capacity decay model:
$$\mu_{\text{actual}} = \mu_{\text{nominal}} \times (0.2 + 0.8 \times e^{-0.02 \times \text{violations}})$$
* **Arrival Rate ($\lambda$):** Poisson arrival rate proportional to typical hourly road volumes.
* **Service Rate ($\mu$):** Deterministic capacity rate, which degrades down to a $20\%$ floor under massive parking obstructions.
* **Average Delay ($W$):**
  $$W = \frac{1}{\mu} + \frac{\lambda}{2\mu(\mu - \lambda)}$$
* **Oversaturation Model:** If $\lambda \ge 0.95 \mu$, the queue transitions to a transient deterministic queue accumulation model to evaluate bottleneck delays.

### 2. Isolation Forest Anomaly Detection
* **Module:** `utils/anomaly_detector.py`
* Trains an unsupervised `IsolationForest` model dynamically on active violations, speed drop, CCIS, and deviations from baseline.
* Computes the **Parking Obstruction Index (POI)** on a 0–10 scale:
  $$\text{POI} = \text{clip}(\text{CCIS} \times 0.6 + \text{anomaly\_score\_normalized} \times 4.0, 0, 10)$$
* Triggers red banner **Anomaly Alerts** in the dashboard and Leaflet popups when deviations from historical Day-of-Week averages are detected.

### 3. Cascade Propagation Spillover Model
* **Module:** `models/cascade_propagator.py`
* Traces multi-hop gridlock spillovers outward from a source cell through surrounding street corridors.
* Evaluates decay rings using H3 spatial hexagons:
  $$\text{Propagated CCIS}_k = \text{Base CCIS} \times \alpha^k$$
* Displays spillovers on the dashboard map in **purple dashed circles** with custom hover text.

### 4. Historical Trend Panel
* **Module:** `utils/historical_trends.py`
* Evaluates average daily CCIS levels for the last 14 days and renders an interactive time-series line chart in the Zone Details panel.

### 5. Multi-Granularity Aggregation Engine
* **Module:** `utils/multi_granularity.py`
* Aggregates and recalculates CCIS scores at multiple spatial scales:
  * **City View (H3-6):** Spacing ~3.2km (strategic municipal planning).
  * **Zone View (H3-8):** Spacing ~460m (enforcement patrol beats).
  * **Street View (H3-9):** Spacing ~100m (tactical patrol allocations).

---

## 🧠 Machine Learning & Analytical Models

### 1. M/D/1 Queuing Delay Simulator (`models/hours_saved_calculator.py` & `models/what_if_simulator.py`)
Provides predictive "What-If" enforcement simulation for target H3 cells and hours:
* **Queuing Class:** Single-channel, Poisson arrivals, deterministic service times.
* **Service Rate Capacity ($\mu$):** Diminishes exponentially under violation loads:
  $$\mu = \mu_{\text{nominal}} \times (0.2 + 0.8 \times e^{-0.02 \times \text{violations}})$$
* **Steady-State Average Delay ($W$):**
  $$W = \frac{1}{\mu} + \frac{\lambda}{2\mu(\mu - \lambda)}$$
* **Oversaturation Flow Approximation:** Used when $\lambda \ge 0.95 \mu$, modeling transient queue build-ups over the deployment window:
  $$W_{\text{bottleneck}} = W_{\text{steady}} + \frac{(\lambda - \mu) \times T}{2\mu}$$

### 2. Ridge Regression CCIS Forecaster (`models/forecast_model.py`)
Predicts CCIS scores $1\text{ hour}$ ahead to enable proactive police deployments:
* **Regression Algorithm:** Ridge Regression with automated regularization tuning ($\alpha \in \{0.01, 0.1, 1.0, 10.0, 100.0\}$).
* **Feature Vector:**
  * `hour_sin` / `hour_cos`: Trigonometric hour mapping.
  * `day_sin` / `day_cos`: Trigonometric weekday mapping.
  * `historical_mean`: Long-term cell average CCIS.
  * `lag_1` / `lag_2`: Prior two hours' CCIS values.
* **Residual Correction:** Corrects forecasts dynamically using historically averaged error terms per (cell, hour):
  $$\text{CCIS}_{\text{corrected}} = \text{Forecast} + \text{Correction}$$

### 3. Spatial Cascade Propagation (`models/cascade_propagator.py`)
Models physical congestion spillovers across the H3 grid system:
* **Spatial System:** Uber H3 Hexagonal Grid.
* **Propagation Formula:**
  $$\text{Propagated CCIS}_k = \text{Base CCIS} \times \alpha^k$$
  * $\alpha$: Attenuation decay coefficient per step (default 0.6).
  * $k$: Hop distance calculated using H3 cell rings.
* **Visualization:** Highlights risk boundaries in Leaflet mapping.

### 4. Unsupervised ML Anomaly Detector (`utils/anomaly_detector.py`)
* **Algorithm:** Isolation Forest with 10% contamination.
* **Features:** `violation_count`, `speed_drop`, `ccis`, and `baseline_deviation`.
* **Output:** Detects statistical baseline deviations and returns the Parking Obstruction Index (POI).

---

## 📁 Project Directory Structure

```
gridlock/
│
├── app.py                      # Main Streamlit Dashboard Application
├── map_template.html           # Leaflet HTML/JS Map Visualization Template
├── Pitch_Deck.pdf              # 10-slide Project Pitch Presentation
├── Technical_Architecture.md   # Architectural Layout & Diagrams
├── README.md                   # Unified Project Documentation (This File)
├── .gitignore                  # Git Version Control Exclude Settings
│
├── data/
│   ├── processed/              # Aggregated CCIS CSV datasets and clustered hotspots
│   └── raw/                    # Original raw gridlock CSV feeds
│
├── models/
│   ├── hours_saved_calculator.py# M/D/1 Queuing Math Calculations
│   ├── what_if_simulator.py    # Sandbox Simulator Tactical Engine
│   └── cascade_propagator.py   # Multi-hop Spatial Spillover Model
│
└── utils/
    ├── anomaly_detector.py     # Isolation Forest & POI Calculations
    ├── historical_trends.py    # Time-series Trend Compiler
    ├── generate_artifacts.py   # Non-code Artifact (PDF/MD) Compiler
    └── multi_granularity.py    # Spatial H3 Res Aggregator
```

---

## 🚀 Running the Dashboard

### 1. Installation
Install all requirements from the root directory:
```bash
pip install -r requirements.txt
```

### 2. Execution
Run the Streamlit dashboard:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.
