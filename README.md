<p align="center">
  <img src="https://img.shields.io/badge/Team-Northern%20Blades-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Engine-V6.1-brightgreen?style=for-the-badge" />
  <img src="https://img.shields.io/badge/AI-YOLOv11m--seg-red?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Edge-Jetson%20Nano-76B900?style=for-the-badge&logo=nvidia" />
</p>

<h1 align="center">🚦 NORTHERN BLADES — AI Fluid Mass Traffic Engine</h1>
<h3 align="center">An Edge-AI Traffic Management System Built for the Chaos of Indian Roads</h3>

<p align="center">
  <b>India Innovates 2026 — National Hackathon Submission</b><br/>
  <sub>Real-time adaptive signal control · Emergency Vehicle Preemption · Intersection Gridlock Prevention · MCD Command Center</sub>
</p>

---

## 🚨 The Problem

India's urban intersections are controlled by **static fixed-timer signals** — systems designed for predictable, orderly traffic that simply doesn't exist on Indian roads. The consequences are devastating:

| Metric | Impact |
|--------|--------|
| **Economic Loss** | ₹1.5 lakh crore/year lost to congestion (MoRTH 2024) |
| **Lives Lost** | 1,72,000+ road fatalities/year — many due to delayed emergency vehicles |
| **CO₂ Emissions** | 30% of urban vehicular emissions are from idle-at-red scenarios |
| **Ambulance Delays** | Average 12+ extra minutes stuck at red signals in Delhi |

### Why Existing Solutions Fail in India

Conventional "smart traffic" solutions imported from the West break down because they assume:
- Vehicles stay in lanes → **They don't** (lane-free driving)
- No cows/animals on roads → **There are** (stray cattle blocking intersections)
- Cameras are clean → **They aren't** (dust, smog, monsoon glare)
- Emergency vehicles have GPS → **Many don't** (pre-2020 ambulances)
- Traffic is homogeneous → **It's not** (auto-rickshaws, e-rickshaws, bullock carts, pedestrian swarms)

---

## 💡 Our Solution 
**Northern Blades** is a production-grade, edge-AI traffic management platform that replaces fixed-timer signals with a **Fluid Mass Physics Engine** — treating traffic not as countable individual vehicles, but as a continuous fluid whose **pressure** ($P = N \times T$) determines which direction gets the green light.

### Key Innovations

| Innovation | Description |
|------------|-------------|
| **Fluid Mass Model** | Measures road density as a percentage (N%) using segmentation masks, not vehicle counts — immune to occlusion and overlap |
| **T-8 Batch Dispatcher** | Evaluates extension decisions every 8 seconds, preventing greedy monopolization |
| **5th Camera (God's Eye)** | Dedicated overhead camera monitors intersection box occupancy to prevent gridlock |
| **Two-Phase EVP Corridor** | GPS + Acoustic siren detection creates a "Green Wave" for ambulances from 500m out |
| **Veto Priority Matrix** | 4-tier decision hierarchy: Physics → Life Safety → Human Psychology → Mathematics |
| **BEV Geometry Engine** | Converts perspective camera views to Bird's Eye View for accurate density measurement |
| **20+ India Edge Cases** | Custom handlers for baraats, holy cows, monsoon floods, GRAP truck bans, Diwali gridlocks, and more |

---

## 🏗 System Architecture

```
                           ┌─────────────────────────────────────────┐
                           │       MCD GOVERNMENT DASHBOARD          │
                           │     (Next.js 16 + Leaflet + Recharts)   │
                           │  • 25-Node Network Map (Live Physics)   │
                           │  • Per-Intersection Drill-Down          │
                           │  • Ambulance Alert Center               │
                           │  • CO₂ Savings Tracker                  │
                           └──────────────────┬──────────────────────┘
                                              │ MQTT + REST API
                           ┌──────────────────┴──────────────────────┐
                           │      CLOUD BACKEND (FastAPI + SQLAlchemy)│
                           │  • PostgreSQL / SQLite Persistence      │
                           │  • MQTT Subscriber (HiveMQ)             │
                           │  • Ghost Node Physics Simulation (×23)  │
                           │  • Device Health Monitoring              │
                           │  • Render.com Cloud Deploy              │
                           └──────────────────┬──────────────────────┘
                                              │ MQTT (broker.hivemq.com)
            ┌─────────────────────────────────┼──────────────────────────────┐
            │                                 │                              │
  ┌─────────┴─────────┐          ┌────────────┴────────────┐    ┌────────────┴──────────┐
  │   EDGE NODE #1    │          │   EDGE NODE #2          │    │   (×23 Simulated)     │
  │   (Jetson Nano)   │          │   (Jetson Nano)         │    │   Ghost Nodes         │
  │                   │          │                         │    │   (Server-side        │
  │ ┌──────────────┐  │          │ ┌──────────────┐        │    │    physics sim)       │
  │ │ 4× CCTV Cams │  │          │ │ 4× CCTV Cams │        │    └───────────────────────┘
  │ │ 1× God's Eye │  │          │ │ 1× God's Eye │        │
  │ └──────┬───────┘  │          │ └──────┬───────┘        │
  │        ▼          │          │        ▼                │
  │  YOLOv11m-seg     │          │  YOLOv11m-seg           │
  │  Geometry Engine  │          │  Geometry Engine         │
  │  Traffic Engine   │          │  Traffic Engine          │
  │  EVP Engine       │          │  EVP Engine              │
  │  Siren Detector   │          │  Siren Detector          │
  │  Cloud Reporter   │          │  Cloud Reporter          │
  └───────────────────┘          └─────────────────────────┘
```

### Three-Tier Design

| Tier | Component | Runs On | Purpose |
|------|-----------|---------|---------|
| **Tier 1: Edge** | Edge Node + AI Models | NVIDIA Jetson Nano | Real-time YOLO inference, signal control, V2X handling |
| **Tier 2: Cloud Backend** | FastAPI + MQTT + PostgreSQL | Render.com / VPS | Data persistence, 25-node network aggregation, MCD API |
| **Tier 3: Frontend** | Next.js Dashboard | Vercel / Static | Government operators monitor city-wide traffic, issue overrides |

---

## 🧠 Core AI Pipeline (Edge Node)

The edge pipeline processes 4 camera feeds simultaneously at **1 FPS per lane** (with Sentry Mode reducing idle lanes to 0.2 FPS to save compute):

```
Camera/Video  →  YOLOv11m-seg  →  Geometry Engine  →  REST API  →  Backend
                                                                      ↓
                          Dashboard WebSocket ← Live camera feeds + engine state
```

### Step-by-Step Pipeline

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ CAM-001  │   │ CAM-002  │   │ CAM-003  │   │ CAM-004  │
│ (Lane 1) │   │ (Lane 2) │   │ (Lane 3) │   │ (Lane 4) │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     └───────────┬──┴─────────┬────┘              │
                 ▼            ▼                    ▼
          YOLO Batch Inference (YOLOv11m-seg, conf=0.35)
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Geometry Engine (per-lane)                              │
│  ① Occlusion Filter (IOU Depth-Check)                   │
│  ② Single-Point Anchor Extraction (tire contact point)  │
│  ③ Lens Undistortion (K, D matrices)                    │
│  ④ Piecewise Homography → Bird's Eye View (BEV) Warp   │
│  ⑤ Synthetic Footprint Injection (anti-overlap)         │
│  ⑥ Fluid Mass % = filled_px / canvas_area × 100        │
└─────────────────────────────────────────────────────────┘
                 │
                 ▼
   REST API → Backend (/api/telemetry, /api/box, /api/latency)
```

### YOLOv11m-seg Custom Model

Our custom-trained model detects and segments **5 India-specific vehicle classes**:

| Class ID | Class Name | Examples |
|----------|-----------|----------|
| 0 | `Heavy_Motor` | Bus, Truck, Mini-bus, LCV, Tempo |
| 1 | `Light_Motor` | Hatchback, Sedan, SUV, MUV |
| 2 | `Organic_Object` | Cows, handcarts, debris |
| 3 | `Three_Wheeler` | Auto-rickshaw, E-rickshaw |
| 4 | `Two_Wheeler` | Motorcycle, Bicycle |

**Training Data**: ~4,000+ images sourced from:
- UVH-26 Dataset (top 2000 densest Indian traffic frames)
- Live Delhi CCTV YouTube streams (manual extraction)
- Weather augmentation (fog, rain, smog, night, dense fog, glare)
- **SAM (Segment Anything Model)** for automatic polygon mask generation

### Geometry Engine — Bird's Eye View

The **`NorthernBladesGeometryEngine`** solves the fundamental problem of perspective distortion — vehicles far from the camera appear smaller and closer together, making pixel-based density meaningless.

```python
# Pipeline per vehicle:
anchor    = extract_anchor(bbox)                  # (cx, ymax) tire-contact point
anchor    = undistort_point(anchor, K, D)         # Lens-corrected anchor
bev_pt    = apply_bev_warp(anchor, homography_H)  # 2D BEV coordinate
            inject_footprint(bev_pt, class_id)     # Rigid rectangle on canvas
density   = process_fluid_mass()                   # N% = filled_px / canvas × 100
```

Key features:
- **Piecewise Homography**: Different H matrices for different zones of the frame (near vs far)
- **Occlusion Filter**: Removes phantom "ghost detections" caused by overlapping vehicles
- **Synthetic Footprints**: Each vehicle class injects a standardized rectangle on the BEV canvas, eliminating mask jitter

---

## ⚙️ The Fluid Mass Engine (V6.1)

The heart of Northern Blades is a **finite state machine** that makes signal decisions every second using a 4-tier **Veto Priority Matrix**:

### Veto Priority Matrix

```
┌─────────────────────────────────────────────────────────────┐
│  RANK 0: PHYSICS (Absolute Veto)                           │
│  • Exit Jam > 85% → Lane physically blocked, DISQUALIFIED  │
│  • Box Density > 80% → ALL-RED DYNAMIC HOLD                │
├─────────────────────────────────────────────────────────────┤
│  RANK 1: LIFE SAFETY                                       │
│  • V2X Ambulance detected → Instant Green Override         │
│  • VIP + Ambulance conflict → Ambulance ALWAYS wins        │
│  • Dual ambulances → Time-To-Arrival (TTA) comparison      │
├─────────────────────────────────────────────────────────────┤
│  RANK 2: HUMAN PSYCHOLOGY (Anti-Starvation)                │
│  • Wait Time T > 180s → Forced promotion                   │
│  • Prevents total starvation of low-density lanes          │
├─────────────────────────────────────────────────────────────┤
│  RANK 3: MATHEMATICS (Fluid Dynamics)                      │
│  • Pressure P = N% × T(seconds)                            │
│  • Highest P wins the Green Light                          │
│  • Ties → Higher wait time wins → Higher density wins      │
└─────────────────────────────────────────────────────────────┘
```

### State Machine

```
  IDLE → BASE_GREEN → EXTENSION → LOOKAHEAD → YELLOW → DYNAMIC_RED
   ↑         ↓                                              ↓
   ╰─────────╯                                    ROUND_ROBIN_FLUSH
```

| State | Duration | Description |
|-------|----------|-------------|
| `IDLE` | 0s | Evaluates all lanes, picks winner |
| `BASE_GREEN` | 15–60s | Green phase calculated using Exponential Density formula |
| `EXTENSION` | +8s (max 1) | T-8 Dispatcher grants extension if inflow N > 15% |
| `LOOKAHEAD` | 5s | Locks next winner T-5 seconds before handover |
| `YELLOW` | 3s | Standard yellow clearance |
| `DYNAMIC_RED` | 0–180s | All-red hold if intersection box is occupied |
| `ROUND_ROBIN_FLUSH` | 30s/lane | Emergency equalization if gridlock exceeds 180s |

### Green Time Formula (Exponential Density)

```
G_base = G_min + (D/100)^1.5 × (G_max - G_min)     // Slow-start curve
M_w    = 1.0 + 0.5 × (W / W_max)                     // Wait time multiplier
G_t    = Clamp(G_base × M_w, 15s, 60s)                // Final green duration
```

Where:
- `D` = Lane density N% (0–100)
- `W` = Wait time T in seconds
- `G_min` = 15s, `G_max` = 60s, `W_max` = 180s

### 5th Camera (God's Eye) — Intersection Gating

A dedicated overhead camera monitors the **intersection box** — the central square where all lanes converge. If vehicles are **stuck inside the box** (density > 80%), the engine blocks ALL new green phases to prevent "intersection boxing" — a cascade failure where cross-traffic enters an already-occupied box.

```
Box Density ≥ 80% → DYNAMIC_RED (All lanes held at Red)
Box Density ≤ 60% → Release (Hysteresis prevents oscillation)
180s Timeout      → ROUND_ROBIN_FLUSH (30s each lane, ordered by wait time)
```

---

## 🚑 Emergency Vehicle Preemption (EVP)

The EVP system creates a **"Green Corridor"** for approaching emergency vehicles using a hybrid GPS + Acoustic architecture:

### Two-Phase GeoFence Corridor

```
    500m ────────── 250m ────────── 150m ────────── 0m (Intersection)
    │                │                │                │
    │   OUTSIDE      │  PHASE A       │  PHASE B       │  ARRIVED
    │   (Normal)     │  (Soft Cap)    │  (Hard Lock)   │  (Clear)
    │                │  ↓ Cap green   │  ↓ Instant     │
    │                │    to 15s max  │    Green for    │
    │                │                │    ambulance    │
```

| Phase | Distance | Action |
|-------|----------|--------|
| **Phase A** (Far Zone) | ≤ 250m | Cap current green to 15s, deny extensions |
| **Phase B** (Near Zone) | ≤ 150m | Hard override — instant yellow for current green, then ambulance gets absolute green |
| **Conflict Resolution** | Dual ambulances | Time-To-Arrival (TTA) comparison — fastest ambulance wins |
| **VIP vs Ambulance** | N/A | **Ambulance ALWAYS wins** (hardcoded life-safety rule) |
| **Anti-Ghost Timeout** | 45s | If ambulance tracking is lost for 45s, override expires |

### Acoustic Siren Detector (GPS Failsafe)

When V2X/GPS fails (common with older ambulances), the edge node's **I2S microphone** performs real-time FFT analysis:

- **Band Detection**: 1200–1500 Hz siren frequency band
- **Volume Trend Analysis**: Doppler-based escalation detection (approaching vs. fading)
- **Confidence Threshold**: ≥ 70% to trigger emergency response
- **Action**: If no GPS ambulance is active, triggers a conservative all-red safety hold

---

## 🇮🇳 20+ India-Specific Edge Cases

We designed and tested **20 unique real-world scenarios** that all competitive solutions ignore:

| # | Scenario | Indian Context | Engine Response |
|---|----------|---------------|-----------------|
| 1 | **Normal Flow** | Standard pressure-based decision | Highest P wins |
| 2 | **Exit Gridlock** | ITO junction at 6 PM | Exit > 85% → Lane DENIED despite high P |
| 3 | **Ambulance Override** | V2X siren from 150m | Hard lock Green for ambulance lane |
| 4 | **Barricade Ghost Jam** | Police barricade blocks half the lane | N reduced by 50% penalty |
| 5 | **DTC Bus Occlusion** | Giant DTC bus hides 20 vehicles behind it | Fallback to last-known density |
| 6 | **Baraat / Pedestrian Swarm** | Wedding procession floods the road | Algorithm SUSPENDED → 60s hardcoded cycle |
| 7 | **Wrong-Way Swarm** | Vehicles enter from wrong direction | ALL-RED → 10s intersection clear |
| 8 | **Lens Dirt / Ghost Object** | Static pixels from dirty camera | Artifact subtraction: N reduced by static % |
| 9 | **GRAP Truck Ban** | Stage 4 air quality ban on trucks | 80% mass reduction for truck class, auto e-challan flagged |
| 10 | **Ultimate Delhi Deadlock** | All exits jammed + ambulance | Ambulance overrides even in total gridlock |
| 11 | **Holy Cow Paradox** | Cow sits in intersection center for 5+ minutes | FLASHING YELLOW → Manual MCD intervention requested |
| 12 | **Dual Emergency Deadlock** | Two ambulances from different lanes | TTA comparison — fastest ambulance wins |
| 13 | **Monsoon Flash Flood** | Camera detects massive glare/water reflection | ALL-RED → Revert to historical fixed-timer |
| 14 | **VIP vs Ambulance** | Police convoy vs ambulance conflict | **Ambulance ALWAYS wins** — alert to Police Control Room |
| 15 | **Diwali Gridlock Matrix** | All 4 lanes > 85% exit density | MICRO-PULSE MODE — 5s green pulses clockwise |
| 16 | **Kanwar Yatra + Blind Spot** | Religious procession + bus occlusion | ALL-RED safety lock — AI cannot verify pedestrian safety |
| 17 | **Phantom Free-Left** | Left-turn lane blocked by physical encroachment | Lane sub-routing — grant green to straight vector only |
| 18 | **Blinding Smog** | YOLO confidence < 15% across all frames | GRACEFUL DEGRADATION → 90s fixed winter timer |
| 19 | **Jugaad Towing** | Broken truck straddling two lanes | MERGED ROIs — calculate as single pressure unit |
| 20 | **Apex Breakdown** | Exit path physically blocked by stalled vehicle | Redirect green to next highest eligible lane |

---

## 🖥 Government Web Dashboard (MCD Command Center)

A full-stack **Next.js 16** dashboard designed for Municipal Corporation (MCD) traffic operators to monitor Delhi's entire 25-intersection network:

### Dashboard Features

| Feature | Description |
|---------|-------------|
| **Interactive Map** | Leaflet map with 25 live intersection nodes, color-coded by congestion level |
| **Per-Node Drill-Down** | Click any node → real-time lane metrics, green timer, engine state, traffic light visualization |
| **Manual Override** | Operators can force Green/Red/Code-Red on any lane from the dashboard |
| **Ambulance Alert Center** | Real-time EVP alerts with distance tracking and lane identification |
| **Most Busiest View** | Rankings, peak hour analytics, and historical congestion patterns |
| **Hardware Health** | Device uptime, firmware, self-reported issues, fault detection |
| **CO₂ Savings Tracker** | Live accumulation of estimated CO₂ savings vs fixed-timer baseline |
| **Peak Hours Analysis** | Recharts-powered time-series graphs of traffic patterns |

### Ghost Node Simulation

To demonstrate scalability at the hackathon, the backend simulates **23 additional intersections** using the same Fluid Mass physics engine running server-side. Each ghost node:
- Independently switches signals based on pressure (P = N × T)
- Uses the same exponential density green-time formula
- Responds to manual overrides from the dashboard
- Contributes to global CO₂ and time-saved statistics

---

## 📊 Edge Node Command Center (Dashboard)

A dedicated **single-page HTML dashboard** (`dashboard.html`) connects directly to the edge node's FastAPI backend via WebSocket for sub-second telemetry:

### Dashboard Panels

| Panel | What It Shows |
|-------|--------------|
| **Engine State Badge** | Current state machine phase (BASE_GREEN, EXTENSION, YELLOW, etc.) |
| **Traffic Lights** | 4 animated traffic signals reflecting actual engine state |
| **Live YOLO Vision** | 4 real-time camera feeds with YOLO detection overlays |
| **Physics Leaderboard** | All 4 lanes ranked by P = N × T with live progress bars |
| **5th Camera (God's Eye)** | Intersection box density gauge with threshold markers |
| **Engine Math & Transparency** | Real-time formula evaluation visible to the operator |
| **Decision Stream** | Scrolling log of every engine decision with tick timestamps |
| **EVP Control Panel** | Dispatch simulated ambulances and track approach progress |
| **Evidence Trail** | Horizontal timeline of captured frame snapshots with metadata |
| **Pipeline Latency Widget** | YOLO, BEV, and Engine processing times in milliseconds |

---

## 🔬 Custom Dataset Pipeline

We built a **7-step automated pipeline** to create a training dataset specifically for Indian traffic:

```
Step 01 → Step 02 → Step 03 → Step 00 → Step 04 → Step 05 → Step 06
```

| Step | Script | Purpose |
|------|--------|---------|
| 01 | `01_download_uvh26.py` | Download top 2000 densest frames from UVH-26 (Indian traffic dataset) |
| 02 | `02_youtube_extractor.py` | Extract frames from 3 live Delhi CCTV YouTube streams |
| 03 | `03_sam_mask_generator.py` | Convert bounding box annotations → SAM polygon segmentation masks |
| 00 | `00_weather_augment.py` | Add fog, rain, smog, glare, night augmentations to 30% of images |
| 04 | `04_finalize_dataset.py` | 90/10 train/val split + YOLO training YAML generation |
| 05 | `05_train.py` | Train YOLOv11m-seg (200 epochs, 640px input, Colab GPU) |
| 06 | `06_validate.py` | Per-class mAP metrics + FPS benchmark on validation set |

### Output: `best.pt` (45 MB)

The final trained model (`best.pt`) is included in `edge_model/dataset/` and is loaded by the edge node at startup.

---

## 🛠️ Tech Stack

### Edge Node (Tier 1)

| Technology | Purpose |
|------------|---------|
| **Python 3.11** | Core runtime |
| **YOLOv11m-seg** (Ultralytics) | Instance segmentation model |
| **OpenCV** | Frame capture, BEV warp, polygon rendering |
| **NumPy** | Matrix operations, homography transforms |
| **FastAPI** | Edge REST API + WebSocket telemetry server |
| **Paho MQTT** | V2X ambulance protocol + Cloud Reporter |
| **FFmpeg** | RTSP/RTMP streaming for remote cameras |

### Cloud Backend (Tier 2)

| Technology | Purpose |
|------------|---------|
| **FastAPI** | REST API server |
| **SQLAlchemy** | ORM for PostgreSQL / SQLite |
| **PostgreSQL** | Production database (Render.com) |
| **SQLite** | Local development database |
| **Paho MQTT** | Subscribe to edge node telemetry via HiveMQ |
| **Pydantic** | Request/response validation |
| **Uvicorn** | ASGI server |

### Government Frontend (Tier 3)

| Technology | Purpose |
|------------|---------|
| **Next.js 16** | React framework with App Router |
| **TypeScript** | Type-safe development |
| **Leaflet + React-Leaflet** | Interactive map with 25-node network |
| **Recharts** | Traffic analytics charts |
| **Lucide React** | Icon library |
| **Tailwind CSS v4** | Utility-first styling |

### Infrastructure

| Service | Purpose |
|---------|---------|
| **Render.com** | Cloud backend deployment (Python + PostgreSQL) |
| **Vercel** | Frontend deployment |
| **HiveMQ** (Public Broker) | MQTT message broker for edge ↔ cloud communication |
| **YouTube Live** | Backup video streaming for remote demos |

---

## 📁 Project Structure

```
TrafficManagerIndiaInnovates/
│
├── edge_model/                         # 🧠 EDGE NODE (Jetson/Local)
│   │
│   ├── edge/                           # Production edge pipeline
│   │   ├── edge_node.py                # Main: Camera → YOLO → Geometry → API
│   │   ├── geometry_engine.py          # BEV Warp, Footprint Injection, Fluid Mass
│   │   ├── roi_configurator.py         # Interactive ROI zone drawing tool
│   │   ├── roi_config.json             # Saved ROI polygons (incoming/outgoing/exit)
│   │   ├── calibration_config.json     # Piecewise homography matrices
│   │   ├── auto_calibrator.py          # Auto-calibration from vanishing points
│   │   ├── siren_detector.py           # Acoustic FFT siren detection (I2S mic)
│   │   ├── box_monitor.py              # 5th camera (God's Eye) monitor
│   │   └── test_geometry.py            # Unit tests for geometry engine
│   │
│   ├── model_backend/                  # FastAPI backend running on edge
│   │   ├── main.py                     # API: /api/telemetry, /ws/telemetry, /api/box
│   │   ├── engine.py                   # 🔥 TrafficEngine V6.1 (State Machine + Physics)
│   │   ├── evp_engine.py               # Emergency Vehicle Preemption (subclass)
│   │   ├── mqtt_handler.py             # V2X GeoFence + Siren handler
│   │   ├── cloud_reporter.py           # Event-driven MQTT publisher to cloud
│   │   ├── test_engine.py              # Engine unit tests
│   │   └── requirements.txt            # Edge dependencies
│   │
│   ├── dataset/                        # Custom YOLOv11m-seg training pipeline
│   │   ├── 00_weather_augment.py       # Fog/rain/smog/night augmentation
│   │   ├── 01_download_uvh26.py        # UVH-26 dataset downloader
│   │   ├── 02_youtube_extractor.py     # Delhi CCTV frame extractor
│   │   ├── 03_sam_mask_generator.py    # SAM bounding-box → polygon converter
│   │   ├── 04_finalize_dataset.py      # Train/val split + YAML generator
│   │   ├── 05_train.py                 # YOLOv11m-seg training script
│   │   ├── 06_validate.py              # Validation + FPS benchmark
│   │   ├── best.pt                     # ✅ Final trained model (45 MB)
│   │   └── README.md                   # Dataset pipeline documentation
│   │
│   ├── dashboard.html                  # Edge Node Command Center (WebSocket UI)
│   ├── poc_engine.py                   # Proof-of-concept: Scenarios 1–10
│   ├── poc_advanced.py                 # Proof-of-concept: Scenarios 11–20
│   ├── god_mode_sim.py                 # V2X ambulance MQTT simulator
│   ├── integration_test.py             # Full system integration tests
│   ├── start_rtsp_streams.bat          # RTSP stream launcher (FFmpeg)
│   └── start_youtube_streams.bat       # YouTube Live stream launcher
│
├── web_dashboard/                      # ☁️ CLOUD + GOVERNMENT DASHBOARD
│   │
│   ├── backend/                        # FastAPI Cloud Backend
│   │   ├── main.py                     # 25-node API + MQTT subscriber + Ghost physics
│   │   ├── database.py                 # SQLAlchemy engine (PostgreSQL / SQLite)
│   │   ├── models.py                   # ORM models: Health, Traffic, GlobalStats
│   │   ├── jetson_simulator.py         # Simulated Jetson data generator
│   │   ├── .env.example                # Environment variables template
│   │   └── requirements.txt            # Cloud backend dependencies
│   │
│   └── frontend/                       # Next.js 16 Government Dashboard
│       ├── src/
│       │   ├── app/
│       │   │   ├── page.tsx            # Main dashboard page
│       │   │   ├── layout.tsx          # Root layout with metadata
│       │   │   ├── globals.css         # Global styles
│       │   │   └── intersection/       # Per-node drill-down pages
│       │   ├── components/
│       │   │   ├── MapComponent.tsx     # Leaflet 25-node network map
│       │   │   ├── Sidebar.tsx         # Navigation sidebar
│       │   │   ├── AmbulanceModal.tsx  # EVP alert modal
│       │   │   ├── PeakHoursView.tsx   # Time-series analytics
│       │   │   ├── MostBusiestView.tsx # Intersection rankings
│       │   │   ├── HardwareVulnerabilityView.tsx # Device health
│       │   │   └── Overlays.tsx        # Loading/connection overlays
│       │   ├── hooks/                  # Custom React hooks
│       │   └── lib/                    # Utility functions
│       ├── package.json
│       └── tsconfig.json
│
├── render.yaml                         # Render.com deployment config
├── .gitignore
└── README.md                           # ← You are here
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for frontend)
- **Git**
- **FFmpeg** (optional, for RTSP/RTMP streaming)
- **NVIDIA GPU** (optional, for YOLO inference acceleration)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/TrafficManagerIndiaInnovates.git
cd TrafficManagerIndiaInnovates
```

### 2. Edge Node Setup

```bash
# Navigate to edge model directory
cd edge_model

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r model_backend/requirements.txt

# Start the Edge Backend (FastAPI + Traffic Engine)
uvicorn model_backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start the Edge Node (AI Pipeline)

```bash
# In a new terminal (with venv activated):
python edge/edge_node.py --fps 1

# Options:
#   --fps 2          → Process at 2 FPS per lane
#   --no-display     → Run headless (no OpenCV windows)
#   --save out.mp4   → Save dashboard recording
#   --backend http://remote-ip:8000  → Point to remote backend
```

### 4. Open the Edge Dashboard

Open `edge_model/dashboard.html` in your browser. It connects to `ws://localhost:8000/ws/telemetry` automatically.

### 5. Cloud Backend Setup

```bash
# In a new terminal:
cd web_dashboard/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # or source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Create .env file from template
copy .env.example .env  # Edit DATABASE_URL if using PostgreSQL

# Start the cloud backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 6. Frontend Setup

```bash
# In a new terminal:
cd web_dashboard/frontend

# Install Node.js dependencies
npm install

# Start the development server
npm run dev

# Open http://localhost:3000 in your browser
```

---

## 📡 API Reference

### Edge Node API (`localhost:8000`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/telemetry` | Ingest camera telemetry (density, exit, frame) |
| `POST` | `/api/box` | 5th Camera box density update |
| `POST` | `/api/latency` | Pipeline latency metrics |
| `POST` | `/api/override` | Manual sandbox override (testing) |
| `POST` | `/api/simulate/ambulance` | Dispatch simulated ambulance |
| `GET` | `/api/state` | Full engine state snapshot |
| `GET` | `/api/simulate/status` | Ambulance simulation progress |
| `WS` | `/ws/telemetry` | Real-time WebSocket (1Hz state pushes) |

### Cloud Backend API (`localhost:8001`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/network-status` | 25-node network status |
| `GET` | `/api/traffic` | Latest traffic for all nodes |
| `GET` | `/api/traffic/{node_id}` | Detailed metrics for one node |
| `POST` | `/api/traffic` | Ingest traffic payload from edge |
| `POST` | `/api/health` | Device health ingestion |
| `POST` | `/api/override` | Send override command to edge node |
| `GET` | `/api/devices` | All registered devices |
| `GET` | `/api/stats` | Global CO₂ + time saved |
| `GET` | `/api/stream-status` | Check if live data is flowing |
| `GET` | `/api/ambulance-alerts/{id}` | Ambulance alert for a node |
| `POST` | `/api/ambulance-alerts/{id}/clear` | Clear acknowledged alert |

---

## ✅ Testing & Validation

### Unit Tests

```bash
# Engine unit tests (edge)
cd edge_model
python -m pytest model_backend/test_engine.py -v

# Geometry engine tests
python -m pytest edge/test_geometry.py -v
```

### Integration Tests

```bash
# Requires edge backend running on localhost:8000
python integration_test.py
```

Tests 5 scenarios against the live backend:
1. **Normal Flow** — Highest pressure wins
2. **Gridlocked Exit** — Physics gate blocks jammed lane
3. **Anti-Starvation** — Long-waiting lane gets promoted
4. **V2X Ambulance** — Emergency override correct
5. **Accordion Discharge** — Green time scales with density

### POC Engine Scenarios

```bash
# Run all 20 standalone scenarios (no backend required)
python poc_engine.py      # Scenarios 1–10
python poc_advanced.py    # Scenarios 11–20
```

---

## 🌱 Environmental Impact

Northern Blades estimates CO₂ savings using a validated model:

```
Per idle vehicle:  ~1.8g CO₂/second
Saved idle time:   15% reduction vs fixed-timer baseline
25 intersections:  ~40 vehicles/intersection × 4 lanes
```

**Projected Daily Savings** (across 25 Delhi intersections):
- **~185 kg CO₂ saved/day** 
- **~1.5 million vehicle-seconds saved/day**
- Equivalent to planting **~8 trees/day**

These metrics are calculated in real-time and displayed on the Government Dashboard, persisted to PostgreSQL for historical tracking.

---


## 👥 Team

**Team Northern Blades** — India Innovates 2026

> *"We didn't build a traffic light controller. We built a traffic physicist."*

---

<p align="center">
  <sub>Built with ❤️ for Indian roads • India Innovates 2026</sub>
</p>
