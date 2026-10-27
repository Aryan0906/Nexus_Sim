# NexusSim — Computer Vision Documentation

**Status:** Active (partial)  
**Phase coverage:** 14 (real-world congestion), 15 (virtual camera), 25 (CV foundation: YOLO + MOG2)  
**Source of truth:** `pipeline/src/cv_congestion.py`, `ml/cv/`, `engine/tests/fixtures/*.onnx`

---

## 1. Overview

Two CV problems are addressed:

- **P1 — Real-world congestion classification:** classify road congestion (free / light / moderate / heavy) per zone per hour, used as a blended fitness term in GA calibration (PRD G8 / Phase 14).
- **P2 — Synthetic virtual camera:** detect and count traffic on the simulation's own rendered output, an independent sidecar on port 9003 (PRD G9 / Phase 15).

CV runs as an independent sidecar process (TR-6), never in the C++ engine hot path or the frontend bundle. Depth is "medium" (PRD BR-2): breadth across techniques, not research-grade depth in any single one.

## 2. Congestion Classification (`pipeline/src/cv_congestion.py`)

`cv_congestion.py --city <city>` reads zones from `data/<city>/od_matrix.json`, iterates hours 0–23, classifies one tile per zone per hour, and writes `data/<city>/cv_congestion.json`.

**Input data:**
- Preferred: real traffic-flow tiles via Mapbox Traffic Tiles (`MAPBOX_ACCESS_TOKEN`) or TomTom Traffic Flow API (`TOMTOM_API_KEY`). API key via env var, never committed, ToS-compliant (BR-6). No key → synthetic fallback.
- Fallback: synthetic 64×64 BGR tiles colour-coded by hour-of-day (peak = red, midday = yellow, off-peak = green).

**Methods:**
- Classical: OpenCV HSV thresholding (red/yellow/green masks → level 0–3).
- CNN mockup: grayscale-variance heuristic (stand-in for a learned classifier).
- Consensus: level from the classifier with higher confidence.

Output schema per zone/hour: `{classical: {level, confidence}, cnn: {level, confidence}, consensus_level}`.

## 3. Virtual Camera (`ml/cv/virtual_camera.py`, `ml/cv/virtual_camera_service.py`)

- WS client consumes the engine state stream (port 9001) + `graph.json` road geometry.
- Rasterises a top-down frame (roads + agents as coloured shapes by type).
- OpenCV contour/blob + colour segmentation detection on rendered pixels.
- Service on port 9003: `GET /health`, `GET /api/camera/feed?agent_count=N` → base64 frame + `detected_count` + `ground_truth_count` + `error_pct` + `accuracy_pct`.
- Accuracy vs ground truth logged as a running error %.

## 4. CV Algorithm Inventory (`ml/cv/`)

| Module | Algorithm | Status |
|--------|-----------|--------|
| `virtual_camera.py` / `virtual_camera_service.py` | Top-down blob detection + counting | Executable |
| `yolo_detector.py` | YOLO object detector + MOG2 subtractor | Module present; no weights in repo |
| `deepsort_tracker.py` | DeepSORT vehicle tracker | Module present |
| `unet_segmentation.py` | U-Net road segmentation | Module present |
| `mask_rcnn.py` | Mask R-CNN instance silhouettes | Module present |
| `anomaly_detector.py` | Hazard-perception anomaly detector | Module present |
| `optical_flow.py` | Lucas-Kanade optical flow | Module present |
| `lane_detector.py` | Lane boundary detector | Module present |
| `crowd_density.py` | Crowd density estimator | Module present |

YOLO/DeepSORT/U-Net/Mask R-CNN modules exist but no real model weights are committed; all catalog accuracy figures (e.g. 91.4%/94.8%/97.5% in `docs/results.md`) are unverified.

## 5. Integration

- Dashboard panels: `CongestionCVOverlay.tsx` (zone bubbles), `VirtualCameraPanel.tsx` (annotated feed).
- Cross-subject event bus (`pipeline/src/event_bus.py`, port 9005): planned topology `cv.anomaly → nlp.incident → sc.adaptation → rl.action` (broker implemented; live wiring TBD).
- No CV signal enters signal timing today; fuzzy/RL inputs come from engine queues and waits.

## 6. Known Gaps

- Real Mapbox/TomTom tile fetch wired but requires an env API key; unverified against live data.
- No CV unit/integration tests; no held-out labelled dataset; no confusion matrix.
- Virtual camera cadence (~1 Hz stream) claimed in docs but implemented as request/response REST.
- `docs/CV_DOCUMENTATION.md` was missing from the tree; this file is provided.
