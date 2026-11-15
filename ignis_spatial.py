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


def render_report_map(data: Optional[pd.DataFrame],
                      associations: Optional[pd.DataFrame] = None):
    """Generate precisely the same static 2D map used by IGNIS PDF reports.

    Returns PNG bytes, or None when no valid geospatial record exists.
    The calculation does not require WebGL, external map tiles or a browser.
    """
    frame = to_scene_frame(data)
    if frame.empty:
        return None
    from ignis_informe import map_figure
    stream = map_figure(frame, associations=associations)
    return stream.getvalue() if stream is not None else None


def render_spatial_pair(data: Optional[pd.DataFrame], year: Optional[int] = None,
                        associations: Optional[pd.DataFrame] = None,
                        height: int = 590, live_connection: bool = False,
                        context: str = "spatial") -> dict:
    """Every science map is presented as synchronized interactive 3D + report-ready 2D.

    Both views and their downloadable PNG use the exact same normalized,
    temporally filtered source frame. No synthetic production points.
    """
    import streamlit as st
    from ignis_scene3d import render_uruguay_scene

    frame = to_scene_frame(data)
    if year is not None and not frame.empty:
        frame = frame.loc[frame["fecha"].dt.year == int(year)].copy()
    left, right = st.columns([1.85, 1], gap="medium")
    with left:
        st.markdown("**3D · Interactive exploration**")
        render_uruguay_scene(frame, selected_year=year, associations=associations,
                             height=height, live_connection=live_connection)
    with right:
        st.markdown("**2D · Scientific report map**")
        png = render_report_map(frame, associations)
        if png is None:
            st.info("No georeferenced FIRMS observations for the selected filters. "
                    "The empty map does not imply absence of fire.")
        else:
            st.image(png, use_container_width=True,
                     caption="Same filtered records as 3D · visual density is not calibrated")
            st.download_button("Download 2D report map (PNG)", data=png,
                               file_name=f"IGNIS_{context}_2d_report.png",
                               mime="image/png", key=f"ignis_{context}_2d_png",
                               use_container_width=True)
        st.caption("2D is the printable map used in the scientific reports. "
                   "3D altitude and decorative effects are illustrative; "
                   "FIRMS thermal anomalies are not confirmed wildfires.")
    return {"source_records": int(len(frame)),
            "selected_year": year,
            "report_map_available": png is not None}
