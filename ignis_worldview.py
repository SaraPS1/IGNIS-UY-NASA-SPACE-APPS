"""Reproducible inspection links in NASA Worldview.

Worldview is an independent source of visual CONTEXT; by itself it does
not validate a FIRMS detection or its size on the ground.
Parameter reference: nasa-gibs/worldview, doc/url_parameters.md.
"""
from __future__ import annotations

from urllib.parse import urlencode

import pandas as pd


def enlace_worldview(fecha: object, latitud: float, longitud: float, radio_grados: float = 0.20) -> str:
    """Open a date and area in the geographic projection of NASA Worldview."""
    lat, lon, radio = float(latitud), float(longitud), float(radio_grados)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Geographic coordinates out of range.")
    if not 0 < radio <= 5:
        raise ValueError("The map radius must be between 0 and 5 degrees.")
    fecha_dt = pd.to_datetime(fecha, errors="coerce", utc=True)
    if pd.isna(fecha_dt):
        raise ValueError("Invalid date.")
    dia = fecha_dt.strftime("%Y-%m-%d")
    # Do not cross the international geographic edges; the IGNIS operating
    # area is Uruguay, so no antimeridian handling is needed.
    oeste, este = max(-180, lon-radio), min(180, lon+radio)
    sur, norte = max(-90, lat-radio), min(90, lat+radio)
    vista = ",".join(f"{v:.5f}" for v in (oeste,sur,este,norte))
    return "https://worldview.earthdata.nasa.gov/?" + urlencode(
        {"p":"geographic","v":vista,"t":dia}
    )
