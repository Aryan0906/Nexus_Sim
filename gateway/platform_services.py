"""NexusSim platform services for the production roadmap.

Implements the backend capabilities described in docs/futureplanning.md:

- **Algorithm Registry** (Phase 4): versioned ONNX + sidecar plugin registration.
- **Rate Limiting** (Phase 2): per-workspace token bucket.
- **Emissions & Carbon Accounting** (Phase 5): ICE/EV energy + idling emissions.
- **Real-Time Ingestion** (Phase 4): GTFS-RT / CV2X / MQTT adapters -> event bus.

All state is in-memory for the current deployment; swap for PostgreSQL/Redis in
production (see docs/futureplanning.md Section 4.1).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Algorithm Registry (Phase 4 - Marketplace)
# ---------------------------------------------------------------------------

@dataclass
class RegisteredAlgorithm:
    algo_id: str
    name: str
    discipline: str  # CV / SC / NLP / RL
    version: str
    onnx_path: Optional[str] = None
    sidecar_url: Optional[str] = None
    author: str = "unknown"
    validation_status: str = "pending"  # pending | validated | rejected
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algo_id": self.algo_id,
            "name": self.name,
            "discipline": self.discipline,
            "version": self.version,
            "onnx_path": self.onnx_path,
            "sidecar_url": self.sidecar_url,
            "author": self.author,
            "validation_status": self.validation_status,
            "created_at": self.created_at,
        }


class AlgorithmRegistry:
    """In-memory registry of user-contributed algorithms (48 built-ins live in
    the algo_explorer sidecar; this holds the *extra* marketplace entries)."""

    def __init__(self):
        self._entries: Dict[str, RegisteredAlgorithm] = {}

    def register(self, algo: RegisteredAlgorithm) -> RegisteredAlgorithm:
        self._entries[algo.algo_id] = algo
        return algo

    def get(self, algo_id: str) -> Optional[RegisteredAlgorithm]:
        return self._entries.get(algo_id)

    def list(self, discipline: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for a in self._entries.values():
            if discipline and a.discipline.lower() != discipline.lower():
                continue
            out.append(a.to_dict())
        return sorted(out, key=lambda a: a["algo_id"])

    def set_validation(self, algo_id: str, status: str) -> bool:
        a = self._entries.get(algo_id)
        if not a:
            return False
        if status not in ("pending", "validated", "rejected"):
            raise ValueError("validation_status must be pending/validated/rejected")
        a.validation_status = status
        return True

    def remove(self, algo_id: str) -> bool:
        return self._entries.pop(algo_id, None) is not None


algorithm_registry = AlgorithmRegistry()


# ---------------------------------------------------------------------------
# Per-Workspace Rate Limiting (Phase 2)
# ---------------------------------------------------------------------------

@dataclass
class RateBucket:
    tokens: float
    last_refill: float


class RateLimiter:
    """Simple in-memory token-bucket limiter keyed by workspace_id.

    Each workspace gets `capacity` tokens, refilled at `refill_rate` tokens/sec.
    """

    def __init__(self, capacity: float = 100.0, refill_rate: float = 10.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._buckets: Dict[str, RateBucket] = {}
        self._hits: Dict[str, int] = {}

    def _refill(self, key: str, now: float) -> None:
        bucket = self._buckets.get(key)
        if bucket is None:
            self._buckets[key] = RateBucket(tokens=self.capacity, last_refill=now)
            return
        elapsed = now - bucket.last_refill
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_rate)
        bucket.last_refill = now

    def allow(self, key: str, cost: float = 1.0) -> tuple[bool, Dict[str, Any]]:
        now = time.time()
        self._refill(key, now)
        bucket = self._buckets[key]
        allowed = bucket.tokens >= cost
        if allowed:
            bucket.tokens -= cost
        self._hits[key] = self._hits.get(key, 0) + 1
        return allowed, {
            "allowed": allowed,
            "remaining": round(bucket.tokens, 3),
            "limit": self.capacity,
            "refill_rate": self.refill_rate,
        }

    def stats(self, key: Optional[str] = None) -> Dict[str, Any]:
        if key:
            return {"key": key, "requests": self._hits.get(key, 0)}
        return {"workspaces": len(self._buckets), "tracked_requests": sum(self._hits.values())}


# Shared instance (capacity/rate configurable via env in production)
rate_limiter = RateLimiter(
    capacity=float(__import__("os").environ.get("NEXUSSIM_RATE_CAPACITY", "100")),
    refill_rate=float(__import__("os").environ.get("NEXUSSIM_RATE_REFILL", "10")),
)


# ---------------------------------------------------------------------------
# Emissions & Carbon Accounting (Phase 5)
# ---------------------------------------------------------------------------

# Simplified COPERT-style constants (grams per unit)
# ICE fuel: ~2.31 kg CO2 per litre; base consumption ~7.0 L/100km at cruise.
ICE_FUEL_L_PER_100KM = 7.0
ICE_CO2_G_PER_L = 2310.0
ICE_NOX_G_PER_KM = 0.05
ICE_PM_G_PER_KM = 0.005

# EV energy: ~0.17 kWh/km. Grid CO2 intensity ~0.4 kg/kWh (modelled).
EV_KWH_PER_KM = 0.17
GRID_CO2_G_PER_KWH = 400.0
EV_NOX_G_PER_KM = 0.0  # tailpipe; brake/tyre PM still exists
EV_PM_G_PER_KM = 0.002

IDLE_FUEL_L_PER_MIN = 0.03  # litres/min idling at a signal
IDLE_CO2_G_PER_MIN = IDLE_FUEL_L_PER_MIN * ICE_CO2_G_PER_L


@dataclass
class EmissionsReport:
    agent_type: str
    distance_km: float
    idle_minutes: float
    co2_g: float
    nox_g: float
    pm_g: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "distance_km": round(self.distance_km, 4),
            "idle_minutes": round(self.idle_minutes, 4),
            "co2_g": round(self.co2_g, 3),
            "nox_g": round(self.nox_g, 5),
            "pm_g": round(self.pm_g, 5),
        }


def compute_emissions(
    agent_type: str,
    distance_km: float,
    idle_minutes: float = 0.0,
) -> EmissionsReport:
    """Estimate CO2 / NOx / PM for one agent over a distance and idle time."""
    at = agent_type.lower()
    if at in ("ev", "electric"):
        co2 = distance_km * EV_KWH_PER_KM * GRID_CO2_G_PER_KWH
        nox = distance_km * EV_NOX_G_PER_KM
        pm = distance_km * EV_PM_G_PER_KM
    else:
        co2 = distance_km * (ICE_FUEL_L_PER_100KM / 100.0) * ICE_CO2_G_PER_L
        nox = distance_km * ICE_NOX_G_PER_KM
        pm = distance_km * ICE_PM_G_PER_KM
    # Idling applies to ICE agents only (EVs idle without tailpipe emissions)
    if at not in ("ev", "electric") and idle_minutes > 0:
        co2 += idle_minutes * IDLE_CO2_G_PER_MIN
    return EmissionsReport(at, distance_km, idle_minutes, co2, nox, pm)


def aggregate_emissions(reports: List[EmissionsReport]) -> Dict[str, Any]:
    total_co2 = sum(r.co2_g for r in reports)
    total_nox = sum(r.nox_g for r in reports)
    total_pm = sum(r.pm_g for r in reports)
    by_type: Dict[str, Dict[str, float]] = {}
    for r in reports:
        d = by_type.setdefault(r.agent_type, {"count": 0, "co2_g": 0.0, "nox_g": 0.0, "pm_g": 0.0})
        d["count"] += 1
        d["co2_g"] += r.co2_g
        d["nox_g"] += r.nox_g
        d["pm_g"] += r.pm_g
    return {
        "total_agents": len(reports),
        "total_co2_g": round(total_co2, 3),
        "total_nox_g": round(total_nox, 5),
        "total_pm_g": round(total_pm, 5),
        "by_type": by_type,
    }


# ---------------------------------------------------------------------------
# Real-Time Ingestion (Phase 4)
# ---------------------------------------------------------------------------

class RealtimeIngestion:
    """Adapter framework mapping external feeds onto the NexusSim event bus.

    Supported feeds:
    - GTFS-Realtime (vehicle positions / trip updates) -> nlp.incident, cv.anomaly
    - CV2X / V2X basic safety messages -> cv.anomaly, sc.adaptation
    - MQTT (CCTV/telemetry) -> cv.anomaly
    - Weather API -> scenario.demand_spike

    Each adapter returns normalized events; the gateway forwards them to the
    event bus sidecar. This keeps the hot engine path isolated from external I/O.
    """

    TOPIC_MAP = {
        "gtfs": "nlp.incident",
        "cv2x": "cv.anomaly",
        "mqtt": "cv.anomaly",
        "weather": "scenario.demand_spike",
    }

    def __init__(self):
        self._adapters: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "gtfs": self._adapt_gtfs,
            "cv2x": self._adapt_cv2x,
            "mqtt": self._adapt_mqtt,
            "weather": self._adapt_weather,
        }

    def normalize(self, feed_type: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a raw feed message into a NexusSim event."""
        if feed_type not in self._adapters:
            raise ValueError(f"Unsupported feed type '{feed_type}'. Expected one of {sorted(self._adapters)}")
        event = self._adapters[feed_type](raw)
        event["feed_type"] = feed_type
        event["topic"] = self.TOPIC_MAP[feed_type]
        event["timestamp"] = time.time()
        return event

    # -- adapters ----------------------------------------------------------
    def _adapt_gtfs(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "payload": {
                "source": "GTFS-RT",
                "vehicle_id": raw.get("vehicle_id"),
                "route_id": raw.get("route_id"),
                "lat": raw.get("lat"),
                "lon": raw.get("lon"),
                "speed_kph": raw.get("speed_kph"),
                "delay_s": raw.get("delay_s", 0),
            }
        }

    def _adapt_cv2x(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "payload": {
                "source": "CV2X",
                "station_id": raw.get("station_id"),
                "lat": raw.get("lat"),
                "lon": raw.get("lon"),
                "speed_kph": raw.get("speed_kph"),
                "heading_deg": raw.get("heading_deg"),
                "basic_safety": raw.get("bsm", {}),
            }
        }

    def _adapt_mqtt(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "payload": {
                "source": "MQTT",
                "topic": raw.get("topic"),
                "broker": raw.get("broker"),
                "message": raw.get("message", {}),
            }
        }

    def _adapt_weather(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "payload": {
                "source": "OpenWeather",
                "city": raw.get("city"),
                "precip_mm": raw.get("precip_mm", 0.0),
                "wind_kph": raw.get("wind_kph", 0.0),
                "visibility_m": raw.get("visibility_m", 10000),
                "demand_multiplier": self._weather_demand_multiplier(raw),
            }
        }

    @staticmethod
    def _weather_demand_multiplier(raw: Dict[str, Any]) -> float:
        """Heuristic demand scaling: heavy rain/wind reduces demand slightly."""
        mult = 1.0
        if raw.get("precip_mm", 0.0) > 5.0:
            mult -= 0.05
        if raw.get("wind_kph", 0.0) > 40.0:
            mult -= 0.03
        return max(0.5, round(mult, 3))


realtime_ingestion = RealtimeIngestion()


# ---------------------------------------------------------------------------
# Scenario KPI Comparison (Phase 3)
# ---------------------------------------------------------------------------

def compare_kpis(baseline: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Compute absolute + percentage deltas between two simulation KPI snapshots."""
    keys = ("avg_wait_s", "gini", "throughput", "co2_g", "avg_speed_kph")
    comparison: Dict[str, Any] = {}
    for k in keys:
        b = baseline.get(k)
        s = scenario.get(k)
        if b is None or s is None:
            continue
        try:
            bf, sf = float(b), float(s)
        except (TypeError, ValueError):
            continue
        delta = sf - bf
        pct = (delta / bf * 100.0) if bf != 0 else None
        comparison[k] = {
            "baseline": bf,
            "scenario": sf,
            "delta": round(delta, 5),
            "delta_pct": round(pct, 3) if pct is not None else None,
        }
    return comparison
