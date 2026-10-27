## Slide 1: Title — NexusSim CV Component: Congestion Classification & Virtual Camera
- Scope: two CV problems — (1) classify real-world road congestion from traffic imagery, (2) detect/count traffic on the simulation's own rendered output (synthetic virtual camera)
- Verified artifacts: pipeline/src/cv_congestion.py; ml/cv/virtual_camera.py and ml/cv/virtual_camera_service.py; ml/cv/{yolo_detector,deepsort_tracker,unet_segmentation,mask_rcnn,anomaly_detector,optical_flow,lane_detector,crowd_density}.py
- Outputs: data/<city>/cv_congestion.json (per zone per hour); annotated frames + detection counts on port 9003
- Sidecar pattern (TR-6): CV runs as an independent process, never in the C++ engine hot path and never in the frontend bundle
- Depth: "medium" per PRD BR-2 — breadth across techniques, not research-grade depth in any single one
**Speaker notes:** The CV component exists as code, but with a major caveat stated immediately: the documented real-world traffic-tile feed (Mapbox Traffic Tiles / TomTom) is not implemented — cv_congestion.py classifies synthetic tiles it renders itself. This deck separates the module inventory (present) from the live-data integration (absent).

## Slide 2: CV Problems Being Solved
- P1: real-world congestion classification — free / light / moderate / heavy per zone per hour, used as an extra fitness term in the GA calibration pipeline (Phase 14 / PRD G8)
- P2: synthetic virtual camera — top-down render of the live agent stream with genuine OpenCV detection/counting on rendered pixels, independent service on port 9003 (Phase 15 / PRD G9)
- Supporting (planned/module inventory): vehicle tracking (DeepSORT), road segmentation (U-Net), instance silhouettes (Mask R-CNN), optical flow, lane detection, crowd density, anomaly/hazard perception
- Non-goals: no research contributions; no live CCTV ingestion; not a full video analytics product
**Speaker notes:** P1 bridges simulation to reality (observed congestion calibrates the simulator); P2 gives the dashboard an independent ground truth for simulated traffic. The planned techniques (tracking, segmentation) exist as module files but are not wired into the live pipeline — see Slide 9.

## Slide 3: Input Data / Sensors
- Per TRD/PRD: traffic-flow tiles via Mapbox Traffic Tiles or TomTom Traffic Flow API, API key via environment variable, never committed, ToS-compliant — NOT implemented in code (no network request, no API key anywhere in pipeline/src/cv_congestion.py)
- Code reality: cv_congestion.py synthesizes 64×64 BGR tiles per zone per hour (red in peak hours 7–9/16–18, yellow midday, green off-peak) and classifies them
- Virtual camera input: the engine's live WebSocket state stream (agents + graph.json road geometry), rasterized into a top-down frame; agents drawn as colored shapes by type
- No real traffic imagery, CCTV, or labeled dataset exists in the repo
**Speaker notes:** This is the single largest documentation-vs-code gap in CV: TRD TR-PIPE-08 describes tile fetching from Mapbox/TomTom, but the implementation draws synthetic tiles. BR-6 (no ToS-violating scraping) is therefore a documented intent, not an implemented compliance control — an API key would need to be wired before any real tile is fetched.

## Slide 4: Models & Techniques
- Congestion classification: classical OpenCV HSV thresholding (red/yellow/green masks → level 0–3) + a "CNN" mockup implemented as grayscale-variance heuristic; both run per zone per hour, consensus level chosen by higher confidence
- Virtual camera detection: OpenCV contour/blob detection and color segmentation on rendered pixels; annotated PNG (base64) + detected_count + ground_truth_count + error_pct
- CV module inventory (ml/cv/): YOLO object detector, MOG2 background subtractor, DeepSORT tracker, U-Net road segmentation, Mask R-CNN instance silhouettes, anomaly detector, Lucas-Kanade optical flow, lane boundary detector, crowd density estimator
- Wired vs catalog: cv_congestion.py and virtual_camera.py are executable; YOLO/DeepSORT/U-Net/Mask R-CNN modules exist but no real model weights are in the repo; all catalog accuracy figures are unverified
**Speaker notes:** Treat the module list as a design inventory, not a validated pipeline. The only executed CV code paths are the HSV thresholding + variance heuristic on synthetic tiles, and the virtual camera's blob/color segmentation on rendered sim frames.

## Slide 5: Preprocessing & Pipeline
- cv_congestion.py --city <city>: reads data/<city>/od_matrix.json zones; iterates hours 0–23; builds a synthetic tile per hour; runs classical + CNN-mockup classification; writes data/<city>/cv_congestion.json {city, generated_at, methodology, zones: {zid: {hour: {classical, cnn, consensus_level}}}}
- Consensus output feeds the GA (optimize_calibration.py) as a blended fitness term alongside simulation MAPE
- Virtual camera pipeline: WS client consumes engine state → rasterize roads + agents → OpenCV contour/blob + color segmentation → count → service on port 9003 (/health, /api/camera/feed?agent_count=N) returns base64 frame + count + error %
- Output cadence: request/response REST; docs claim ~1 Hz streaming (not verified in code)
**Speaker notes:** The pipeline is deterministic and offline: no live imagery enters the system. The GA integration claim (CV output as fitness term) exists in the TRD and the optimize_calibration.py design, but whether cv_congestion.json's output is actually consumed by the GA fitness function could not be confirmed from the code read — flag as TBD.

## Slide 6: Integration With the Rest of the System
- Sidecar service virtual_camera_service.py (port 9003) is a WS client of the engine stream and an HTTP provider to the dashboard
- Dashboard panels: CongestionCVOverlay.tsx (zone bubbles colored by CV-observed congestion), VirtualCameraPanel.tsx (live annotated feed)
- Engine is unaffected: CV only reads; no write path into Simulation state (unlike NLP incidents or RL signal actions)
- Cross-subject event bus (port 9005, pipeline/src/event_bus.py): planned topology cv.anomaly → NLP extraction → Soft Computing adaptation → RL action exploration (implemented as broker; live wiring TBD)
- No CV signal enters signal timing directly today — fuzzy/RL inputs come from engine queues and waits, not CV counts
**Speaker notes:** Integration is strictly consumer-side: CV observes the engine and the dashboard consumes CV. There is no documented path where CV output changes signal phases or routing, which limits CV's operational role to monitoring and the (unverified) GA fitness term.

## Slide 7: Use Cases Within NexusSim (Why CV Fits)
- UC1: congestion classification as GA fitness input — why CV: observed real-world congestion calibrates simulation parameters (speed_factor, route_spread, chaos, demand_scale) where OD demand alone is insufficient
- UC2: virtual camera counting — why CV: an independent vision-based count of simulated traffic validates simulator fidelity without instrumenting the engine internals; error % is logged as a running metric
- UC3 (planned, not wired): anomaly detection → NLP incident extraction → signal adaptation (CV-11 hazard detector → NLP-9 event extractor → engine incident API)
**Speaker notes:** UC1 is the strongest rationale: simulation validation needs real-world ground truth, and congestion level per zone/hour is a natural CV output. UC2 is elegant (the simulator watches itself) but currently runs on synthetic rendered frames, not physical cameras. UC3 remains a design intention.

## Slide 8: Evaluation Metrics
- docs/results.md §3.1 claims: classical HSV 91.4% / CNN 94.8% (< 1.2 ms); virtual camera 97.5% vehicle detection accuracy (12 ms); YOLO 95.2% (~15 ms); U-Net road IoU 100% — all marked catalog/unverified in the 2026-10 audit (docs/results.md provenance note)
- Runtime logging: virtual camera logs detected vs ground-truth count error % as a running metric (TBD — not exported in any committed report)
- No held-out labeled dataset, no test split, no confusion matrix committed to the repo
- CV accuracy figures cannot be reproduced from artifacts; mark all as TBD
**Speaker notes:** Every CV number in the documentation is either a catalog design target or a training-log claim. No CV test suite exists (ml/tests has no CV tests), so accuracy is the largest unverified surface of the whole project.

## Slide 9: Limitations
- Congestion module classifies synthetic tiles, not live imagery → Mapbox/TomTom fetch (TR-PIPE-08) unimplemented; BR-6 ToS compliance documented but not enforced by code
- Virtual camera: NEXUS-SIM-DOCUMENTATION.md §5.3 reports it draws a grey grid with synthesized agent positions and is request/response REST rather than a 1 Hz stream — code shows graph.json-based rasterization, a doc/code discrepancy to resolve
- YOLO/DeepSORT/U-Net/Mask R-CNN weights absent from repo; modules present but not runnable end-to-end
- No CV unit/integration tests; no measured accuracy; false-positive/false-negative behavior unknown
- GA fitness integration of cv_congestion.json output not confirmed in code
**Speaker notes:** None of these are fatal — they define the boundary between "CV module inventory exists" and "CV is a validated, live subsystem." For a presentation, the honest stance is: CV techniques are implemented and executable on synthetic data; real-world validation is pending.

## Slide 10: Next Steps
- Wire Mapbox Traffic Tiles / TomTom Traffic Flow fetch with an environment-variable API key (BR-6 compliant; key never committed)
- Collect a labeled real-world tile dataset per city; measure classical vs CNN accuracy on held-out data and publish a confusion matrix
- Ship or document download of YOLO/DeepSORT/U-Net/Mask R-CNN weights; verify modules end-to-end on sim frames
- Convert virtual camera to a streamed ~1 Hz annotated feed with logged error %; reconcile the grey-grid documentation discrepancy
- Confirm whether cv_congestion.json output is consumed by optimize_calibration.py fitness; if not, wire it or remove the claim
**Speaker notes:** These steps are ordered from data (real tiles) to validation (held-out accuracy) to integration (GA fitness, streaming camera). None are in-flight per docs/BACKLOG.md, which marks phases 26–36 PENDING.

## Slide 11: Q&A
- Artifacts to inspect: pipeline/src/cv_congestion.py, ml/cv/virtual_camera_service.py, data/chicago/cv_congestion.json, docs/results.md §3.1
- Unverified claims flagged: all CV accuracy figures, the Mapbox/TomTom integration, the GA fitness consumption, the 1 Hz camera cadence
**Speaker notes:** Close by reiterating the verification posture: CV is present as executable code on synthetic inputs; every real-world performance claim is TBD pending labeled data and a live tile feed.
