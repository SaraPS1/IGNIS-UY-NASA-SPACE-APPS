"""Shared adapters and 3D map renderer for all IGNIS spatial views.

Never manufacture observations: map source fields only and drop invalid rows.
The 3D map is a visual exploration of imported thermal anomalies, not a
wildfire prediction or a validated burned-area layer.
"""
from __future__ import annotations

from typing import Optional
import pandas as pd


FIELDS = ("fecha", "latitude", "longitude", "instrumento",
          "satellite", "frp", "confidence")


def to_scene_frame(data: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Normalize FIRMS/historical/NRT/fusion frames without inventing data."""
    if not isinstance(data, pd.DataFrame) or data.empty:
        return pd.DataFrame(columns=FIELDS)
    aliases = {
        "fecha": ("fecha", "fecha_utc", "adquisicion_utc"),
        "latitude": ("latitude", "lat"),
        "longitude": ("longitude", "lon"),
        "instrumento": ("instrumento", "producto", "instrument"),
        "satellite": ("satellite",),
        "frp": ("frp",),
        "confidence": ("confidence",),
    }
    output = pd.DataFrame(index=data.index)
    for name, alternatives in aliases.items():
        source = next((key for key in alternatives if key in data.columns), None)
        output[name] = data[source] if source is not None else None
    output["fecha"] = pd.to_datetime(output["fecha"], utc=True, errors="coerce")
    for name in ("latitude", "longitude", "frp"):
        output[name] = pd.to_numeric(output[name], errors="coerce")
    valid = (output["fecha"].notna() & output["latitude"].between(-90, 90) &
             output["longitude"].between(-180, 180))
    return output.loc[valid, list(FIELDS)].reset_index(drop=True)


def render_spatial_3d(data: Optional[pd.DataFrame], year: Optional[int] = None,
                      associations: Optional[pd.DataFrame] = None,
                      height: int = 590, live_connection: bool = False) -> dict:
    """Use the *same* 3D engine and UTC orbital provider across spatial pages."""
    from ignis_scene3d import render_uruguay_scene
    return render_uruguay_scene(
        to_scene_frame(data), selected_year=year,
        associations=associations, height=height,
        live_connection=live_connection,
    )
