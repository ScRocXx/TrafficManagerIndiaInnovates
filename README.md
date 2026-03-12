# 🚦 Fluid Traffic Engine
**Team: Northern Blades | India Innovates 2026**

## 📌 The Delhi Reality (Problem Statement)
Current traffic management in Indian metropolises relies on rigid, analog timers or rudimentary loop detectors. These systems fail catastrophically under the realities of Indian traffic:
1. They cannot handle dynamic, un-laned vehicle swarms.
2. Optical cameras go entirely blind during winter smog.
3. Ambulances are trapped in gridlock with no preemptive routing.
4. Heavy mass transit (DTC Buses) lose momentum, causing massive shockwaves.
5. Local waterlogging creates cascading, city-wide gridlock because intersections do not communicate.

## 🚀 The Solution: Fluid Macro-Grid Architecture
We abandoned the concept of "waiting in line." The **Fluid Traffic Engine** treats traffic as a continuous dynamic fluid. 

Instead of hardcoded loops, we deployed a **Scikit-Learn Random Forest Machine Learning Model** that predicts optimal traffic flow based on real-time mass, wait times, and environmental constraints. We then networked multiple intersections into a **Macro-Grid**, allowing them to share telemetry and reroute traffic autonomously to prevent downstream gridlock.

---

## ⚙️ Core Innovations & AI Features (USPs)

### 1. ML-Driven Fluid Math Engine
Instead of rigid timers, the system calculates `Pressure Score = Polygon Density (Mass) × Wait Time`. 
* **The AI Brain:** A Random Forest Classifier (trained on synthetic historical telemetry) evaluates the live pressure matrix and predicts the optimal green light configuration to maximize throughput while preventing starvation.

### 2. Smog-Proof Sensor Fusion
Optical YOLOv8 cameras are useless in 15% visibility Delhi smog. 
* **The Failsafe:** When the API detects low visibility, the AI dynamically drops optical data and fuses **Acoustic Honk Density** (decibel mapping) to estimate lane pressure, keeping the engine running completely blind.

### 3. Macro-Grid Ripple Routing (Waterlogging Divert)
Intersections are not isolated. 
* **The Failsafe:** If Node C (Minto Bridge) detects a flooded underpass, it broadcasts a signal upstream to Node A (Ashram Chowk). The AI immediately penalizes routes leading to the flood, autonomously diverting traffic *before* a jam occurs.

### 4. V2X Preemptive Ambulance Override
* **The Protocol:** Edge nodes detect RF/V2X signals from approaching emergency vehicles kilometers away. The system forces a preemptive Green Corridor, shifting the ambulance's route to the highest absolute priority, overriding all AI predictions until the vehicle clears.

### 5. Mass Transit Momentum Conservation (MTMC)
Heavy buses take 3x longer to accelerate, creating shockwaves.
* **The Protocol:** If the YOLO model classifies a heavy transit vehicle in an active green lane, the system applies an "Artificial Momentum Weight," holding the light green for a few extra seconds so the heavy mass can slide through without breaking.

### 6. ANPR E-Challan Integration (Wrong-Way Failsafe)
Traditional systems freeze intersections when someone drives the wrong way, penalizing everyone.
* **The Protocol:** Our engine ignores the violator to maintain macro-fluidity, but utilizes Edge vector-tracking to snap the license plate and instantly push an E-Challan generation alert to the MCD dashboard.

### 7. Hardware Failsafes (The 60s Cap & Island Mode)
AI must be bounded by human-centric rules.
* **Frustration Cap:** No lane will ever wait longer than 60 seconds. The system physically overrides the AI to clear stale queues.
* **Island Mode:** If an intersection loses connection to the Cloud Brain, it does not freeze. It gracefully degrades into a local, dumb hardware state, running a fixed 60-second analog loop until the network is restored.

---

## 💻 About This Prototype
*Note to Judges: Physical street-pole deployment of YOLOv8 cameras and networking hardware is impossible for us currently, but we plan to make it possible by the main event. This repository contains the **Enterprise Software Architecture** that proves our core AI and Macro-Grid routing logic.*

### The Stack
* **Cloud API:** FastAPI (Python)
* **AI/ML:** Scikit-Learn (Random Forest Classifier), NumPy
* **Command Dashboard:** Vanilla HTML5, CSS3 (Glassmorphism), JavaScript
* **Edge Simulation:** Python `requests` payload generator

---

## 🛠️ How to Run the Macro-Grid Simulation

**1. Install Dependencies:**
```bash
pip install fastapi uvicorn requests scikit-learn numpy



(*please reference to the submitted ppt to get more details about this project*)