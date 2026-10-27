# NexusSim — Natural Language Processing Documentation

**Status:** Active (partial)  
**Phase coverage:** 16 (live metrics chat), 17 (incidents → simulation), 31 (sentiment/feedback)  
**Source of truth:** `ml/nlp/`, `engine/src/agent/NLPQueryParser.h`

---

## 1. Overview

Two NLP problems are addressed:

- **P1 — Live metrics chat:** answer plain-language questions about live simulation state (PRD G10 / Phase 16).
- **P2 — Incident reports → simulation mutation:** parse free-text incident reports into structured specs and apply them to the running simulation (PRD G11 / Phase 17).

NLP runs as an independent sidecar (port 9004) per TR-6. Depth is "medium" (PRD BR-2).

## 2. Chat Service (`ml/nlp/chat_service.py`)

FastAPI service on port 9004:
- `GET /health` → `{"status": "ok", ...}`.
- `POST /chat` `{query, city}` → `{intent, answer, confidence, handler}`.
- `POST /incident` `{text, city}` → parses text, returns incident spec.
- `POST /feedback` `{text, city}` → sentiment + category (Phase 31).

**Live metrics:** a background WebSocket-client thread connects to the engine (port 9001), subscribes to a city, and caches the latest state frame in `METRICS`. Chat answers for worst_zone / avg_speed / active_agents / gini / compare_policy use cached live metrics when available, falling back to static literals otherwise. `/health` reports `live_metrics`.

**Intent classifier:** rule-based regex over a fixed intent set (`worst_zone`, `avg_speed`, `active_agents`, `gini_explain`, `compare_policy`, `general_inquiry`). Optional LLM tool-calling layer falls back to `fallback_llm_stub` when no API key is configured.

## 3. Incident Parser (`ml/nlp/incident_parser.py`)

`IncidentParser(graph_dict=None, gazetteer_path=None)` parses free text into:
- `type`: accident / construction / closure / event
- `severity`: 0.0–1.0 (keywords major/severe/block → 0.9; minor/slight → 0.3; default 0.5)
- `duration_s`: parsed from "N minutes"/"Ns" (default 300s)
- `edges`: street → edge-id lookup via RapidFuzzy partial-ratio matching (≥60) against the gazetteer

**Gazetteer:** loads from an external JSON file (`gazetteer_path`) if provided; otherwise falls back to a small hardcoded Chicago seed set (7 streets, edge ids 101–114). `graph_dict` is accepted for future per-city edge derivation.

The engine-side `Simulation::apply_incident(edges, severity, duration_s)` applies temporary per-edge speed/capacity multipliers that expire after `duration_s`; `incidents[]` is added to the broadcast.

## 4. NLP Algorithm Inventory (`ml/nlp/`)

| Module | Algorithm | Status |
|--------|-----------|--------|
| `chat_service.py` | Regex intent classifier + LLM fallback | Executable (port 9004) |
| `incident_parser.py` | RapidFuzz gazetteer incident parser | Executable |
| `sentiment_analyzer.py` | VADER-style sentiment | Module present |
| `naive_bayes_classifier.py` | Naive Bayes incident classifier | Module present |
| `ner_extractor.py` | spaCy/Regex NER | Module present |
| `coref_resolver.py` | Coreference resolver | Module present |
| `event_extractor.py` | Traffic event extractor | Module present |
| `summarizer.py` | TextRank extractive summarizer | Module present |
| `qa_engine.py` | Extractive QA | Module present |
| `knowledge_graph.py` | RDF knowledge graph | Module present |
| `engine/src/agent/NLPQueryParser.h` | In-engine command parser | C++ |

## 5. Known Gaps

- No WebSocket client existed before this fix; now added (caches engine metrics).
- `/incident` parses and returns a spec; engine forwarding implemented via WS client (best-effort, engine must be reachable).
- Gazetteer is a small seed set; per-city street-name mapping not derived from `graph.json` (nodes/edges carry no street names).
- LLM tool-calling layer is a stub; no real LLM integration.
- `docs/NLP_DOCUMENTATION.md` was missing from the tree; this file is provided.
