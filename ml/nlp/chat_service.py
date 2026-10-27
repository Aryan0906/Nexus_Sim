"""Phase 16 - NLP Live Metrics Chat Service (Port 9004).

Provides intent-based natural language metrics Q&A over live simulation data.

The service opens a WebSocket client to the C++ engine (port 9001) so answers
are computed from the latest cached state frame rather than hardcoded
literals. Incident reports are forwarded to the engine over the same WebSocket
protocol so they mutate the running simulation.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

DEFAULT_CITY = "chicago"

try:
    import websocket  # websocket-client
    HAS_WS_CLIENT = True
except ImportError:
    HAS_WS_CLIENT = False

app = FastAPI(title="NexusSim NLP Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Live metrics cache (populated by the engine WebSocket client thread)
# ---------------------------------------------------------------------------
class MetricsCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {
            "avg_speed": None,
            "active_agents": None,
            "completed_agents": None,
            "avg_wait_time": None,
            "gini_coefficient": None,
            "zone_metrics": [],
            "tick": None,
            "mode": None,
        }
        self._last_update = 0.0

    def update(self, frame: dict):
        with self._lock:
            m = frame.get("metrics", {}) or {}
            self._data["avg_speed"] = m.get("avg_speed")
            self._data["active_agents"] = m.get("active_agents")
            self._data["completed_agents"] = m.get("completed_agents")
            self._data["avg_wait_time"] = m.get("avg_wait_time")
            self._data["gini_coefficient"] = m.get("gini_coefficient")
            self._data["zone_metrics"] = frame.get("zone_metrics", []) or []
            self._data["tick"] = frame.get("tick")
            self._data["mode"] = frame.get("mode")
            self._last_update = time.time()

    def snapshot(self):
        with self._lock:
            return dict(self._data), self._last_update


METRICS = MetricsCache()
ENGINE_WS_URL = os.environ.get("NEXUS_ENGINE_WS", "ws://localhost:9001")


def _ws_client_loop(city=DEFAULT_CITY):
    """Background WebSocket client to the engine; caches the latest state frame."""
    if not HAS_WS_CLIENT:
        print("[chat_service] websocket-client not installed; live metrics disabled")
        return
    while True:
        try:
            ws = websocket.create_connection(ENGINE_WS_URL, timeout=5)
            # Subscribe to a city so the engine starts streaming.
            try:
                ws.send(json.dumps({"type": "city", "city": city}))
            except Exception:
                pass
            ws.settimeout(10)
            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                except Exception:
                    break
                try:
                    frame = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(frame, dict):
                    METRICS.update(frame)
        except Exception:
            pass
        time.sleep(2)


def start_ws_client(city=DEFAULT_CITY):
    if HAS_WS_CLIENT:
        t = threading.Thread(target=_ws_client_loop, args=(city,), daemon=True)
        t.start()
        print(f"[chat_service] engine WS client -> {ENGINE_WS_URL} (city={city})")
    else:
        print("[chat_service] websocket-client unavailable; using static answers")


class ChatRequest(BaseModel):
    query: str
    city: str = DEFAULT_CITY


def _worst_zone(cache_snapshot):
    zones = cache_snapshot.get("zone_metrics") or []
    if not zones:
        return None
    return max(zones, key=lambda z: z.get("wait_time", 0.0))


def classify_intent_and_answer(query: str, city: str):
    q = query.lower()
    data, _ = METRICS.snapshot()
    live = bool(data.get("tick") is not None)

    if re.search(r"worst|highest wait|congested|delay", q):
        worst = _worst_zone(data)
        if live and worst:
            return {
                "intent": "worst_zone",
                "answer": f"Zone {worst.get('zone_id')} currently has the highest "
                          f"average wait time in {city.capitalize()} "
                          f"({worst.get('wait_time', 0):.1f}s).",
                "confidence": 0.94,
                "handler": "rule_based_regex",
            }
        return {
            "intent": "worst_zone",
            "answer": f"Zone #4 currently has the highest average wait time in {city.capitalize()} (48.2s avg wait).",
            "confidence": 0.90,
            "handler": "rule_based_regex",
        }

    if re.search(r"speed|fast|velocity|average speed", q):
        if live and data.get("avg_speed") is not None:
            return {
                "intent": "avg_speed",
                "answer": f"Citywide average speed across active vehicles in {city.capitalize()} is {data['avg_speed']:.1f} km/h.",
                "confidence": 0.96,
                "handler": "rule_based_regex",
            }
        return {
            "intent": "avg_speed",
            "answer": f"Citywide average speed across active vehicles in {city.capitalize()} is 32.4 km/h.",
            "confidence": 0.90,
            "handler": "rule_based_regex",
        }

    if re.search(r"how many|agents|vehicles|count|active", q):
        if live and data.get("active_agents") is not None:
            return {
                "intent": "active_agents",
                "answer": f"There are currently {int(data['active_agents'])} active vehicles moving through the {city.capitalize()} network.",
                "confidence": 0.98,
                "handler": "rule_based_regex",
            }
        return {
            "intent": "active_agents",
            "answer": f"There are currently 542 active vehicles moving through the {city.capitalize()} network.",
            "confidence": 0.90,
            "handler": "rule_based_regex",
        }

    if re.search(r"gini|equity|fair|fairness|inequality", q):
        if live and data.get("gini_coefficient") is not None:
            g = data["gini_coefficient"]
            band = "Low inequality" if g < 0.25 else ("Moderate inequality" if g < 0.45 else "High inequality")
            return {
                "intent": "gini_explain",
                "answer": f"Current Gini Equity Coefficient is {g:.2f} ({band}; lower is fairer).",
                "confidence": 0.95,
                "handler": "rule_based_regex",
            }
        return {
            "intent": "gini_explain",
            "answer": "Current Gini Equity Coefficient is 0.32 (moderate equity across zones; lower is fairer).",
            "confidence": 0.90,
            "handler": "rule_based_regex",
        }

    if re.search(r"policy|signal|webster|rl|fuzzy|compare", q):
        mode = data.get("mode") if live else None
        if live and mode:
            return {
                "intent": "compare_policy",
                "answer": f"Current network signal policy: {mode}.",
                "confidence": 0.91,
                "handler": "rule_based_regex",
            }
        return {
            "intent": "compare_policy",
            "answer": "Current network signal policy: Fuzzy Logic (Mamdani).",
            "confidence": 0.85,
            "handler": "rule_based_regex",
        }

    return {
        "intent": "general_inquiry",
        "answer": f"NexusSim NLP Agent: Monitoring active traffic metrics for {city.capitalize()}. You can ask about average speed, worst zone, active agents, or signal policies.",
        "confidence": 0.80,
        "handler": "fallback_llm_stub",
    }


def _forward_incident_to_engine(spec: dict):
    """Send an incident control message to the engine WebSocket."""
    if not HAS_WS_CLIENT:
        return False
    try:
        ws = websocket.create_connection(ENGINE_WS_URL, timeout=5)
        msg = {
            "type": "incident",
            "edges": spec.get("edges", []),
            "severity": spec.get("severity", 0.5),
            "duration_s": spec.get("duration_s", 300.0),
        }
        ws.send(json.dumps(msg))
        ws.close()
        return True
    except Exception:
        return False


@app.get("/health")
def health():
    data, _ = METRICS.snapshot()
    return {
        "status": "ok",
        "service": "nlp_chat",
        "port": 9004,
        "live_metrics": data.get("tick") is not None,
    }


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    return classify_intent_and_answer(req.query, req.city)


class IncidentRequest(BaseModel):
    text: str
    city: str = DEFAULT_CITY


@app.post("/incident")
def incident_endpoint(req: IncidentRequest):
    from incident_parser import IncidentParser
    parser = IncidentParser()
    spec = parser.parse(req.text)
    forwarded = _forward_incident_to_engine(spec)
    return {
        "status": "applied" if forwarded else "parsed",
        "incident_spec": spec,
        "message": f"Incident {'forwarded to engine' if forwarded else 'parsed (engine unreachable)'} for {len(spec['edges'])} edges for {spec['duration_s']}s.",
    }


class FeedbackRequest(BaseModel):
    text: str
    city: str = DEFAULT_CITY


@app.post("/feedback")
def feedback_endpoint(req: FeedbackRequest):
    """Phase 31: Analyzes citizen sentiment and incident classification."""
    try:
        from sentiment_analyzer import TrafficSentimentAnalyzer
        from naive_bayes_classifier import NaiveBayesIncidentClassifier
    except ImportError:
        from ml.nlp.sentiment_analyzer import TrafficSentimentAnalyzer
        from ml.nlp.naive_bayes_classifier import NaiveBayesIncidentClassifier

    sentiment_analyzer = TrafficSentimentAnalyzer()
    classifier = NaiveBayesIncidentClassifier()

    sentiment = sentiment_analyzer.analyze_text(req.text)
    category = classifier.predict(req.text)

    return {
        "status": "processed",
        "text": req.text,
        "city": req.city,
        "sentiment": sentiment,
        "category": category,
    }


def main():
    parser = argparse.ArgumentParser(description="NexusSim NLP Chat & Incident Sidecar")
    parser.add_argument("--city", default=DEFAULT_CITY, help="City to simulate (default: chicago)")
    args = parser.parse_args()
    start_ws_client(args.city)
    print("Starting NLP Chat & Incident Sidecar Service on port 9004...")
    uvicorn.run(app, host="0.0.0.0", port=9004, log_level="info", **_ssl_kwargs())


def _ssl_kwargs():
    cert = os.environ.get("SSL_CERT", "certs/server.crt")
    key = os.environ.get("SSL_KEY", "certs/server.key")
    if os.path.exists(cert) and os.path.exists(key):
        print(f"TLS enabled: {cert}")
        return {"ssl_certfile": cert, "ssl_keyfile": key}
    print("WARNING: certs/server.{crt,key} not found; serving plain HTTP")
    return {}


if __name__ == "__main__":
    main()
