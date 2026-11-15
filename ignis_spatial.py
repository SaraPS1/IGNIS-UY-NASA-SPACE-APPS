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


def _empty_scientific_outline_png() -> bytes:
    """Report-ready reference geography when no observations are loaded.

    No hotspots, sensor coverage, or invented ground incidents are drawn.
    """
    import io
    import json
    from pathlib import Path
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    geo = json.loads((Path(__file__).resolve().parent / "uruguay_contorno.geojson")
                     .read_text(encoding="utf-8"))
    ring = geo["features"][0]["geometry"]["coordinates"][0]
    fig = Figure(figsize=(7, 5.5), facecolor="#081728")
    ax = fig.add_axes([.13, .13, .79, .76], facecolor="#081728")
    ax.fill([p[0] for p in ring], [p[1] for p in ring],
            color="#15364c", alpha=.9)
    ax.plot([p[0] for p in ring], [p[1] for p in ring],
            color="#62d7eb", linewidth=1.5)
    ax.set_xlim(-58.85, -52.65)
    ax.set_ylim(-35.45, -29.75)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("Uruguay · reference geography", color="#dff8ff", fontsize=12)
    ax.set_xlabel("Longitude", color="#b8d2e4", fontsize=8)
    ax.set_ylabel("Latitude", color="#b8d2e4", fontsize=8)
    ax.text(.5, .03, "No imported FIRMS records · not evidence of no wildfires",
            color="#d9d2bc", fontsize=7, ha="center", transform=ax.transAxes,
            bbox={"facecolor": "#0d2a3d", "edgecolor": "none", "pad": 5})
    ax.tick_params(colors="#a1bfd2", labelsize=7)
    ax.grid(color="#294b62", alpha=.2)
    for spine in ax.spines.values():
        spine.set_color("#31566c")
    buffer = io.BytesIO()
    FigureCanvasAgg(fig).print_png(buffer)
    return buffer.getvalue()


def render_report_map(data: Optional[pd.DataFrame],
                      associations: Optional[pd.DataFrame] = None):
    """Generate precisely the same static 2D map used by IGNIS PDF reports.

    Returns PNG bytes, or None when no valid geospatial record exists.
    The calculation does not require WebGL, external map tiles or a browser.
    """
    frame = to_scene_frame(data)
    if frame.empty:
        return _empty_scientific_outline_png()
    from ignis_informe import map_figure
    stream = map_figure(frame, associations=associations)
    return stream.getvalue() if stream is not None else _empty_scientific_outline_png()


def render_spatial_pair(data: Optional[pd.DataFrame], year: Optional[int] = None,
                        associations: Optional[pd.DataFrame] = None,
                        height: int = 590, live_connection: bool = False,
                        context: str = "spatial", show_report_map: bool = True) -> dict:
    """Every science map is presented as synchronized interactive 3D + report-ready 2D.

    Both views and their downloadable PNG use the exact same normalized,
    temporally filtered source frame. No synthetic production points.
    """
    import streamlit as st
    from ignis_scene3d import render_uruguay_scene

    frame = to_scene_frame(data)
    if year is not None and not frame.empty:
        frame = frame.loc[frame["fecha"].dt.year == int(year)].copy()
    # The Dashboard has its own separate Uruguay Map page; show the 3D
    # visualization at full available width there without a second map.
    # All other callers keep the original paired 3D/2D rendering.
    if not show_report_map:
        st.markdown("**3D · Interactive exploration**")
        render_uruguay_scene(frame, selected_year=year, associations=associations,
                             height=height, live_connection=live_connection)
        return {"source_records": int(len(frame)),
                "selected_year": year,
                "report_map_available": False}

    left, right = st.columns([1.85, 1], gap="medium")
    with left:
        st.markdown("**3D · Interactive exploration**")
        render_uruguay_scene(frame, selected_year=year, associations=associations,
                             height=height, live_connection=live_connection)
    with right:
        st.markdown("**2D · Scientific report map**")
        if frame.empty:
            st.info("No imported thermal observations for this selection. The 2D map shows the national outline only.")
        png = render_report_map(frame, associations)
        if png is None:
            st.info("No georeferenced FIRMS observations for the selected filters. "
                    "The empty map does not imply absence of fire.")
        else:
            st.image(png, use_container_width=True,
                     caption=("No FIRMS observations · reference outline only" if frame.empty else "Same filtered records as 3D · visual density is not calibrated"))
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
