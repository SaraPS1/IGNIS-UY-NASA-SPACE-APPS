"""Shared, time-based SGP4 ephemerides for IGNIS UY.

Authoritative positions are calculated with Skyfield's SGP4 and WGS84
geodetic conversion, NEVER with an artistic orbital phase. A ground-track
intersection with the supplied simplified Uruguay polygon is NOT a
validated instrument swath, thermal detection, or fire event.

No stale TLE is silently used for historical reconstruction.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any, Mapping, Optional

import requests

try:
    from skyfield.api import EarthSatellite, load, wgs84
    SKYFIELD_AVAILABLE = True
except ImportError:  # graceful offline / partially installed environment
    EarthSatellite = load = wgs84 = None
    SKYFIELD_AVAILABLE = False

ROOT = Path(__file__).resolve().parent
SOURCE = "CelesTrak GP/TLE"
MAX_EPOCH_DISTANCE_DAYS = 5.0   # conservative operational policy, not a guarantee of accuracy
CACHE_SECONDS = 1200
CATALOG = (
    {"catalog": "25994", "name": "Terra", "sensor": "MODIS", "color": "#ff965c"},
    {"catalog": "27424", "name": "Aqua", "sensor": "MODIS", "color": "#ff965c"},
    {"catalog": "37849", "name": "Suomi NPP", "sensor": "VIIRS", "color": "#00d9f5"},
    {"catalog": "43013", "name": "NOAA-20", "sensor": "VIIRS", "color": "#00d9f5"},
    {"catalog": "54234", "name": "NOAA-21", "sensor": "VIIRS", "color": "#00d9f5"},
)


def utc(value: Optional[datetime] = None) -> datetime:
    if value is None:
        value = datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError("An explicitly timezone-aware UTC datetime is required")
    return value.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return utc(dt).isoformat(timespec="seconds").replace("+00:00", "Z")


@lru_cache(maxsize=1)
def uruguay_polygon() -> tuple[tuple[float, float], ...]:
    data = json.loads((ROOT / "uruguay_contorno.geojson").read_text(encoding="utf-8"))
    polygon = data["features"][0]["geometry"]["coordinates"][0]
    return tuple((float(lon), float(lat)) for lon, lat in polygon)


def point_in_polygon(lon: float, lat: float, ring: tuple[tuple[float, float], ...]) -> bool:
    """Lon/lat containment against a simplified *geographical* reference boundary."""
    if not (math.isfinite(lon) and math.isfinite(lat)) or len(ring) < 4:
        return False
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < cross:
                inside = not inside
        j = i
    return inside


def parse_tle(text: str, catalog: str) -> Optional[tuple[str, str]]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    for i in range(len(lines) - 1):
        first, second = lines[i:i + 2]
        if not (first.startswith("1 ") and second.startswith("2 ")):
            continue
        if first[2:7] != second[2:7] or first[2:7] != str(catalog).zfill(5):
            continue
        if len(first) < 69 or len(second) < 69:
            continue
        return first, second
    return None


def tle_url(catalog: str) -> str:
    return f"https://celestrak.org/NORAD/elements/gp.php?CATNR={catalog}&FORMAT=TLE"


def fetch_tle(catalog: str) -> dict[str, Any]:
    """Network errors are visible as unavailable, never silently simulated."""
    fetched_at = utc()
    try:
        response = requests.get(tle_url(catalog), timeout=(3, 6))
        response.raise_for_status()
        pair = parse_tle(response.text, catalog)
        if not pair:
            raise ValueError("No valid matching TLE in the response")
        return {"tle": list(pair), "fetched_at": iso(fetched_at), "source_url": tle_url(catalog)}
    except (requests.RequestException, ValueError) as error:
        return {"tle": None, "fetched_at": iso(fetched_at),
                "source_url": tle_url(catalog), "error": str(error)[:180]}


try:
    import streamlit as st
    cached_fetch_tle = st.cache_data(ttl=CACHE_SECONDS, show_spinner=False)(fetch_tle)
except ImportError:
    cached_fetch_tle = fetch_tle


@lru_cache(maxsize=1)
def timescale():
    if not SKYFIELD_AVAILABLE:
        raise RuntimeError("Skyfield is not installed")
    return load.timescale(builtin=True)


def satellite_from_tle(tle: tuple[str, str], name: str):
    if not SKYFIELD_AVAILABLE:
        raise RuntimeError("Skyfield is not installed")
    return EarthSatellite(tle[0], tle[1], name, timescale())


def epoch_and_age(satellite, when: datetime) -> tuple[datetime, float]:
    epoch = utc(satellite.epoch.utc_datetime())
    age_days = abs((utc(when) - epoch).total_seconds()) / 86400.0
    return epoch, age_days


def valid_for_time(satellite, when: datetime) -> bool:
    return epoch_and_age(satellite, when)[1] <= MAX_EPOCH_DISTANCE_DAYS


def positions_at(satellite, timestamps: list[datetime]) -> list[dict[str, Any]]:
    """Vectorized SGP4 + WGS84. Do not accept non-finite or stale coordinates."""
    if not timestamps:
        return []
    if not all(valid_for_time(satellite, stamp) for stamp in timestamps):
        return []
    t = timescale().from_datetimes([utc(stamp) for stamp in timestamps])
    geocentric = satellite.at(t)
    position = wgs84.geographic_position_of(geocentric)
    out = []
    for stamp, lat, lon, alt in zip(timestamps,
                                     position.latitude.degrees,
                                     position.longitude.degrees,
                                     position.elevation.km):
        if not all(math.isfinite(float(x)) for x in (lat, lon, alt)):
            return []
        if not (-90 <= lat <= 90 and -180 <= lon <= 180 and alt > 0):
            return []
        out.append({"t": iso(stamp), "lat": round(float(lat), 5),
                    "lon": round(float(lon), 5), "alt_km": round(float(alt), 2)})
    return out


def step_times(start: datetime, finish: datetime, step_seconds: int) -> list[datetime]:
    if step_seconds <= 0 or finish < start:
        raise ValueError("Invalid sampling interval")
    n = int(math.ceil((finish - start).total_seconds() / step_seconds))
    return [min(start + timedelta(seconds=i * step_seconds), finish) for i in range(n + 1)]


def groundtrack_events(points: list[dict[str, Any]],
                       ring: Optional[tuple[tuple[float, float], ...]] = None
                       ) -> list[dict[str, Any]]:
    """Discrete crossing intervals. No claims about sensor field of view."""
    polygon = uruguay_polygon() if ring is None else ring
    events = []
    enter = None
    for i, pt in enumerate(points):
        inside = point_in_polygon(pt["lon"], pt["lat"], polygon)
        if inside and enter is None:
            enter = i
        elif not inside and enter is not None:
            events.append({"entry_index": enter, "exit_index": i,
                           "start_utc": points[enter]["t"],
                           "end_utc": points[i]["t"],
                           "event_type": "subsatellite_groundtrack_crossing",
                           "boundary_resolution": "simplified national polygon",
                           "swath_verified": False})
            enter = None
    # An open-ended event is not a completed last pass.
    return events


def _pass_payload(points: list[dict[str, Any]], event: dict[str, Any]) -> dict[str, Any]:
    i = max(0, event["entry_index"] - 5)
    j = min(len(points), event["exit_index"] + 6)
    return {"start_utc": event["start_utc"], "end_utc": event["end_utc"],
            "event_type": event["event_type"], "swath_verified": False,
            "boundary_resolution": event["boundary_resolution"],
            "track": points[i:j]}


def available_bundle(reference_utc: Optional[datetime] = None,
                     tle_sources: Optional[Mapping[str, Mapping[str, Any]]] = None,
                     catalog: tuple[dict[str, str], ...] = CATALOG
                     ) -> dict[str, Any]:
    """One shared source of truth for the dashboard and full Earth globe.

    If sources are supplied, no network calls are performed (for deterministic tests).
    Current tracking provides a bounded 100-min ephemeris; pass search uses a
    separate 24h window either side of the selected UTC instant.
    """
    reference = utc(reference_utc)
    if tle_sources is None:
        with ThreadPoolExecutor(max_workers=5) as pool:
            sources = dict(zip((s["catalog"] for s in catalog),
                               pool.map(cached_fetch_tle, (s["catalog"] for s in catalog))))
    else:
        sources = dict(tle_sources)

    records = []
    for entry in catalog:
        base = {"catalog": entry["catalog"], "name": entry["name"],
                "sensor": entry["sensor"], "color": entry["color"],
                "mode": "unavailable", "track": [], "last_pass": None,
                "next_pass": None, "current_position": None,
                "event_definition": "subsatellite ground-track crosses Uruguay",
                "source": SOURCE, "source_url": tle_url(entry["catalog"]),
                "computed_utc": iso(reference)}
        source = sources.get(entry["catalog"], {})
        base["fetched_at"] = source.get("fetched_at")
        tle = source.get("tle")
        if not SKYFIELD_AVAILABLE:
            base["status"] = "Skyfield orbital dependency unavailable"
        elif not tle or len(tle) != 2:
            base["status"] = "Verified TLE unavailable"
        else:
            try:
                sat = satellite_from_tle((tle[0], tle[1]), entry["name"])
                epoch, age = epoch_and_age(sat, reference)
                base["tle_epoch"] = iso(epoch)
                base["epoch_distance_days"] = round(age, 3)
                if age > MAX_EPOCH_DISTANCE_DAYS - 1:
                    base["status"] = "TLE too far from selected UTC time for bounded pass calculations"
                else:
                    times = step_times(reference - timedelta(minutes=5),
                                       reference + timedelta(minutes=95), 20)
                    track = positions_at(sat, times)
                    past_to_future = step_times(reference - timedelta(hours=24),
                                                reference + timedelta(hours=24), 40)
                    search = positions_at(sat, past_to_future)
                    if not track or not search:
                        base["status"] = "SGP4 propagation unavailable or outside validity interval"
                    else:
                        base["mode"] = "sgp4"
                        base["track"] = track
                        base["current_position"] = positions_at(sat, [reference])[0]
                        events = groundtrack_events(search)
                        completed = [e for e in events if e["end_utc"] <= iso(reference)]
                        upcoming = [e for e in events if e["start_utc"] > iso(reference)]
                        if completed:
                            base["last_pass"] = _pass_payload(search, completed[-1])
                        if upcoming:
                            base["next_pass"] = _pass_payload(search, upcoming[0])
                        base["status"] = "SGP4 estimate · simplified ground-track boundary"
            except (ValueError, TypeError, RuntimeError, IndexError, ArithmeticError) as error:
                base["status"] = f"Orbital calculation unavailable: {type(error).__name__}"
        records.append(base)
    return {"reference_utc": iso(reference), "clock_mode": "current_utc",
            "source": SOURCE, "epoch_policy_days": MAX_EPOCH_DISTANCE_DAYS,
            "pass_definition": "subsatellite ground-track crossing; not instrument coverage",
            "satellites": records, "terrain_is_illustrative": True}
