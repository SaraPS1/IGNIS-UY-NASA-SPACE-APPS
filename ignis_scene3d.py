"""IGNIS UY · Interactive 3D Uruguay scene (isolated Three.js component).

Architecture
------------
Python prepares a compact JSON payload from the *real* records loaded in the
session (no synthetic observations are ever generated here) and renders a
self-contained HTML document through ``st.components.v1.html``. The document
loads Three.js from a CDN (the same approach already used by
``ignis_espacio.py``) and never calls back into Streamlit: every toggle,
timeline step and camera move happens client-side, so the Streamlit app is
not re-run while the user explores the scene.

Scientific integrity
--------------------
* Thermal observations are NASA FIRMS thermal anomalies, not confirmed fires.
* Terrain relief is an *illustrative* procedural surface; the repository has
  no elevation dataset, so no elevation measurements are claimed.
* Satellite orbits in this scene are schematic animations. Verified
  TLE-based trajectories live in the "3D Earth & Satellites" page.
* Department boundaries are drawn only if a verified GeoJSON is provided in
  ``assets/uruguay_departamentos.geojson``; otherwise the toggle reports
  that no verified data is available.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
GRID_STEP = 0.2
MAX_POINTS = 6000
YEAR_MIN, YEAR_MAX = 2000, 2026

PALETTE = {
    "navy": "#06101D", "midnight": "#091827", "cyan": "#00D9F5",
    "ice": "#7DEBFF", "orange": "#FF6A1A", "ember": "#FF3B30",
    "slate": "#91A8BA", "white": "#F4FAFF",
}


# --------------------------------------------------------------------------
# Geography (verified sources only)
# --------------------------------------------------------------------------
def load_outline() -> List[List[float]]:
    """[lon, lat] ring of the national outline shipped with the repository."""
    try:
        data = json.loads((BASE / "uruguay_contorno.geojson").read_text(encoding="utf-8"))
        ring = data["features"][0]["geometry"]["coordinates"][0]
        return [[round(float(p[0]), 5), round(float(p[1]), 5)] for p in ring]
    except (OSError, KeyError, IndexError, ValueError, TypeError):
        return []


def load_departments() -> List[Dict[str, Any]]:
    """Optional verified department boundaries (GeoJSON Polygon/MultiPolygon).

    Returns an empty list when the file is absent: the UI then states that
    no verified boundary dataset is available instead of inventing one.
    """
    path = BASE / "assets" / "uruguay_departamentos.geojson"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for feature in data.get("features", []):
        geom = feature.get("geometry") or {}
        props = feature.get("properties") or {}
        name = str(props.get("name") or props.get("NOMBRE") or props.get("nombre") or "")
        rings: List[List[List[float]]] = []
        if geom.get("type") == "Polygon":
            rings = [geom["coordinates"][0]]
        elif geom.get("type") == "MultiPolygon":
            rings = [poly[0] for poly in geom["coordinates"]]
        for ring in rings:
            try:
                out.append({"name": name,
                            "ring": [[round(float(p[0]), 4), round(float(p[1]), 4)] for p in ring]})
            except (TypeError, ValueError, IndexError):
                continue
    return out


def documented_cases() -> List[Dict[str, Any]]:
    """Documented wildfire reference towns from the fusion module (guarded)."""
    try:
        from ignis_fusion_terrestre import CASOS_DOCUMENTADOS
    except Exception:  # pragma: no cover - optional dependency on the module
        return []
    cases = []
    for c in CASOS_DOCUMENTADOS:
        try:
            cases.append({"name": str(c["nombre"]), "lat": float(c["lat"]), "lon": float(c["lon"]),
                          "start": str(c.get("inicio", "")), "end": str(c.get("fin", "")),
                          "source": str(c.get("fuente", "")), "url": str(c.get("url", ""))})
        except (KeyError, TypeError, ValueError):
            continue
    return cases


# --------------------------------------------------------------------------
# Observations
# --------------------------------------------------------------------------
def _normalize(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    cols = ["fecha", "latitude", "longitude", "instrumento", "satellite", "frp", "confidence"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    f = df.copy()
    f["fecha"] = pd.to_datetime(f.get("fecha"), errors="coerce", utc=True)
    f["latitude"] = pd.to_numeric(f.get("latitude"), errors="coerce")
    f["longitude"] = pd.to_numeric(f.get("longitude"), errors="coerce")
    f["frp"] = pd.to_numeric(f.get("frp", np.nan), errors="coerce")
    for c in ("instrumento", "satellite", "confidence"):
        f[c] = f.get(c, pd.Series("", index=f.index)).fillna("").astype(str)
    f = f.dropna(subset=["fecha", "latitude", "longitude"])
    f = f[f["latitude"].between(-90, 90) & f["longitude"].between(-180, 180)]
    return f[cols].reset_index(drop=True)


def _family(instrument: str) -> int:
    u = instrument.upper()
    if "VIIRS" in u:
        return 1
    if "MODIS" in u:
        return 0
    return 2


def _sample_points(frame: pd.DataFrame, max_points: int) -> pd.DataFrame:
    """Keep at most ``max_points`` rows, spread across years, highest FRP first.

    Full per-year counts are reported separately, so capping only affects how
    many markers are drawn, never the figures shown to the user.
    """
    if len(frame) <= max_points:
        return frame
    years = frame["year"].value_counts()
    share = (years / years.sum() * max_points).clip(lower=min(60, max_points // max(len(years), 1)))
    parts = []
    for year, n in share.items():
        sub = frame[frame["year"] == year]
        n = int(min(len(sub), round(n)))
        parts.append(sub.sort_values("frp", ascending=False, na_position="last").head(n))
    return pd.concat(parts).head(max_points)


def recurrence_grid(frame: pd.DataFrame, step: float = GRID_STEP) -> List[List[float]]:
    """0.2° cells with the number of distinct years and records (descriptive)."""
    if frame.empty:
        return []
    g = pd.DataFrame({
        "ilat": np.floor(frame["latitude"] / step).astype(int),
        "ilon": np.floor(frame["longitude"] / step).astype(int),
        "year": frame["year"],
    })
    agg = g.groupby(["ilat", "ilon"]).agg(years=("year", "nunique"), records=("year", "size")).reset_index()
    return [[round((r.ilon + 0.5) * step, 3), round((r.ilat + 0.5) * step, 3), int(r.years), int(r.records)]
            for r in agg.itertuples()]


def associations_payload(assoc: Optional[pd.DataFrame], limit: int = 800) -> List[Dict[str, Any]]:
    """Satellite–ground associations computed by the fusion tab (if any)."""
    if assoc is None or not isinstance(assoc, pd.DataFrame) or assoc.empty:
        return []
    needed = {"lat", "lon", "fecha_utc", "resultado"}
    if not needed.issubset(assoc.columns):
        return []
    out = []
    for r in assoc.head(limit).itertuples():
        try:
            out.append({"lat": float(r.lat), "lon": float(r.lon), "date": str(r.fecha_utc)[:16],
                        "result": str(r.resultado), "sources": str(getattr(r, "fuentes", "")),
                        "n_firms": int(getattr(r, "n_firms", 0) or 0),
                        "simulated": str(getattr(r, "simulado", "No")).upper().startswith("YES")})
        except (TypeError, ValueError):
            continue
    return out


def build_scene_payload(df: Optional[pd.DataFrame], selected_year: Optional[int] = None,
                        associations: Optional[pd.DataFrame] = None,
                        max_points: int = MAX_POINTS, live_connection: bool = False) -> Dict[str, Any]:
    """Everything the client needs, computed only from the supplied records."""
    frame = _normalize(df)
    frame["year"] = frame["fecha"].dt.year.astype(int) if len(frame) else pd.Series(dtype=int)
    year_counts = {int(k): int(v) for k, v in frame["year"].value_counts().sort_index().items()} if len(frame) else {}
    year_fam: Dict[int, List[int]] = {}
    if len(frame):
        fam_series = frame["instrumento"].map(_family)
        for (yr, fam), n in frame.groupby([frame["year"], fam_series]).size().items():
            year_fam.setdefault(int(yr), [0, 0, 0])[int(fam)] = int(n)
    fam_counts = frame["instrumento"].map(_family).value_counts() if len(frame) else pd.Series(dtype=int)
    shown = _sample_points(frame, max_points) if len(frame) else frame

    sats = sorted(set(shown["satellite"].tolist())) if len(shown) else []
    sat_index = {s: i for i, s in enumerate(sats)}
    points = {
        "lon": [round(float(v), 4) for v in shown["longitude"]],
        "lat": [round(float(v), 4) for v in shown["latitude"]],
        "frp": [None if pd.isna(v) else round(float(v), 1) for v in shown["frp"]],
        "fam": [int(_family(v)) for v in shown["instrumento"]],
        "inst": [str(v) for v in shown["instrumento"]],
        "sat": [int(sat_index[v]) for v in shown["satellite"]],
        "year": [int(v) for v in shown["year"]],
        "day": [v.strftime("%Y-%m-%d %H:%M UTC") for v in shown["fecha"]],
        "conf": [str(v) for v in shown["confidence"]],
    }
    years_present = sorted(year_counts)
    latest = frame["fecha"].max() if len(frame) else None
    stats = {
        "observations": int(len(frame)),
        "shown": int(len(shown)),
        "years": int(len(years_present)),
        "first_year": years_present[0] if years_present else None,
        "last_year": years_present[-1] if years_present else None,
        "modis": int(fam_counts.get(0, 0)),
        "viirs": int(fam_counts.get(1, 0)),
        "latest": latest.strftime("%Y-%m-%d %H:%M UTC") if latest is not None else None,
    }
    sel = int(selected_year) if selected_year is not None else (years_present[-1] if years_present else YEAR_MAX)
    return {
        "outline": load_outline(),
        "departments": load_departments(),
        "cases": documented_cases(),
        "associations": associations_payload(associations),
        "grid": recurrence_grid(frame),
        "points": points,
        "satellites": sats,
        "yearCounts": year_counts,
        "yearFamilyCounts": year_fam,
        "stats": stats,
        "selectedYear": sel,
        "yearRange": [YEAR_MIN, YEAR_MAX],
        "liveConnection": bool(live_connection),
        "palette": PALETTE,
        "gridStep": GRID_STEP,
    }


# --------------------------------------------------------------------------
# HTML document
# --------------------------------------------------------------------------
def scene_html(payload: Dict[str, Any]) -> str:
    """Self-contained document: Three.js scene, HUD, timeline, 2D fallback."""
    data = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    return _TEMPLATE.replace("__IGNIS_PAYLOAD__", data.replace("</", "<\\/"))


def render_uruguay_scene(df: Optional[pd.DataFrame], selected_year: Optional[int] = None,
                         associations: Optional[pd.DataFrame] = None, height: int = 720,
                         live_connection: bool = False) -> Dict[str, Any]:
    """Render the component inside Streamlit and return the payload stats."""
    import streamlit.components.v1 as components
    payload = build_scene_payload(df, selected_year, associations, live_connection=live_connection)
    components.html(scene_html(payload), height=height, scrolling=False)
    return payload["stats"]


_TEMPLATE = (BASE / "assets" / "ignis_scene3d.html").read_text(encoding="utf-8") \
    if (BASE / "assets" / "ignis_scene3d.html").exists() else "<!doctype html><html><body>__IGNIS_PAYLOAD__</body></html>"
