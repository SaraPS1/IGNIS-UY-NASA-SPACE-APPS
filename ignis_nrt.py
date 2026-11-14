"""IGNIS UY: optional, lightweight query of recent NASA FIRMS detections.

It does NOT alter or import into the IGNIS Master. Detections do not confirm fires.
The network request happens ONLY when the form button is pressed.
"""

from __future__ import annotations

import io
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ignis_worldview import enlace_worldview

FUENTES = {
    "VIIRS NOAA-20": "VIIRS_NOAA20_NRT",
    "VIIRS NOAA-21": "VIIRS_NOAA21_NRT",
    "MODIS Terra/Aqua": "MODIS_NRT",
}
# Same approximate bounding box used in the historical dashboard.
BBOX_URUGUAY = "-58.6,-35.2,-53.0,-30.0"  # west,south,east,north
LIMITE_BYTES = 4_000_000


def _clave_nasa():
    """The key comes from Streamlit's secure secrets manager; never from the repository.

    Both names are accepted to stay compatible with the existing dashboard
    configuration (FIRMS_MAP_KEY) and with the new NRT API.
    """
    for nombre in ("NASA_FIRMS_MAP_KEY", "FIRMS_MAP_KEY"):
        try:
            clave = str(st.secrets.get(nombre, "")).strip()
            if clave:
                return clave
        except Exception:
            pass
    for nombre in ("NASA_FIRMS_MAP_KEY", "FIRMS_MAP_KEY"):
        clave = os.environ.get(nombre, "").strip()
        if clave:
            return clave
    return ""


@st.cache_data(ttl=900, max_entries=16, show_spinner=False)
def _pedir_sensor(clave: str, producto: str, dias: int):
    """A single download per sensor, at most once every 15 min thanks to the cache.

    The URL is never returned in exceptions: it contains the private MAP_KEY.
    """
    url = ("https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
           f"{clave}/{producto}/{BBOX_URUGUAY}/{dias}")
    request = Request(url, headers={"User-Agent": "IGNIS-UY/1.0 (NASA FIRMS research prototype)"})
    try:
        with urlopen(request, timeout=12) as respuesta:
            contenido = respuesta.read(LIMITE_BYTES + 1)
            if len(contenido) > LIMITE_BYTES:
                return pd.DataFrame(), "Response too large for lightweight mode"
    except HTTPError as error:
        return pd.DataFrame(), f"NASA FIRMS responded HTTP {error.code}"
    except (URLError, TimeoutError, OSError):
        return pd.DataFrame(), "Could not establish communication with NASA FIRMS"
    try:
        dataframe = pd.read_csv(io.BytesIO(contenido), low_memory=False)
        dataframe.columns = [str(col).strip().lower() for col in dataframe.columns]
        requeridas = {"latitude", "longitude", "acq_date", "acq_time"}
        if not requeridas.issubset(dataframe):
            return pd.DataFrame(), "Unexpected response format"
        dataframe["latitude"] = pd.to_numeric(dataframe["latitude"], errors="coerce")
        dataframe["longitude"] = pd.to_numeric(dataframe["longitude"], errors="coerce")
        dataframe = dataframe.dropna(subset=["latitude", "longitude"]).copy()
        dataframe = dataframe[
            dataframe.latitude.between(-35.2, -30.0)
            & dataframe.longitude.between(-58.6, -53.0)
        ].copy()
        # FIRMS acq_time is expressed as HHMM in UTC.
        hora = (dataframe["acq_time"].astype(str).str.replace(r"\.0$", "", regex=True)
                .str.zfill(4).str.slice(0, 2) + ":" +
                dataframe["acq_time"].astype(str).str.replace(r"\.0$", "", regex=True)
                .str.zfill(4).str.slice(2, 4))
        dataframe["adquisicion_utc"] = pd.to_datetime(
            dataframe["acq_date"].astype(str) + " " + hora,
            utc=True, errors="coerce"
        )
        dataframe["frp"] = pd.to_numeric(dataframe.get("frp", pd.Series(index=dataframe.index, dtype=float)), errors="coerce")
        dataframe["producto"] = next((nombre for nombre, codigo in FUENTES.items() if codigo == producto), producto)
        columnas = ["producto", "adquisicion_utc", "latitude", "longitude", "frp"]
        for adicional in ("confidence", "daynight", "satellite"):
            if adicional in dataframe:
                columnas.append(adicional)
        return dataframe[columnas].copy(), None
    except (ValueError, TypeError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return pd.DataFrame(), "NASA responded with data that could not be parsed"


def _consulta(clave: str, fuentes: list[str], dias: int):
    """Two or three bounded requests; it does not download the whole planet."""
    tablas, incidencias = [], []
    with ThreadPoolExecutor(max_workers=min(3, len(fuentes))) as ejecutor:
        trabajos = {ejecutor.submit(_pedir_sensor, clave, FUENTES[nombre], dias): nombre for nombre in fuentes}
        for trabajo in as_completed(trabajos):
            nombre = trabajos[trabajo]
            try:
                df, error = trabajo.result()
            except Exception:
                df, error = pd.DataFrame(), "Unexpected error during the query"
            if error:
                incidencias.append(f"{nombre}: {error}")
            elif not df.empty:
                tablas.append(df)
    if tablas:
        combinado = pd.concat(tablas, ignore_index=True, sort=False)
        combinado = combinado.sort_values("adquisicion_utc", ascending=False).reset_index(drop=True)
    else:
        combinado = pd.DataFrame()
    return combinado, incidencias


def _mapa_liviano(df: pd.DataFrame):
    """Lightweight chart without third-party tiles, using the existing Uruguay outline."""
    figura = go.Figure()
    geojson = Path(__file__).resolve().parent / "uruguay_contorno.geojson"
    if geojson.exists():
        try:
            objeto = json.loads(geojson.read_text(encoding="utf-8"))
            geometria = objeto["features"][0]["geometry"]
            anillo = (geometria["coordinates"][0] if geometria["type"] == "Polygon"
                      else geometria["coordinates"][0][0])
            figura.add_trace(go.Scatter(
                x=[p[0] for p in anillo], y=[p[1] for p in anillo],
                fill="toself", fillcolor="rgba(52,38,105,0.4)",
                line=dict(color="#9bc7ff", width=2), name="Uruguay (approx.)",
                hoverinfo="skip"
            ))
        except (ValueError, KeyError, IndexError, TypeError):
            pass
    colores = {"VIIRS NOAA-20": "#5de1ff", "VIIRS NOAA-21": "#ffc668", "MODIS Terra/Aqua": "#d2a4ff"}
    for nombre, subconjunto in df.groupby("producto", sort=True):
        muestra = subconjunto.iloc[:1200]  # visual limit: never exceed 3600 points
        figura.add_trace(go.Scattergl(
            x=muestra["longitude"], y=muestra["latitude"],
            mode="markers", name=nombre,
            marker=dict(size=8, opacity=0.8, color=colores.get(nombre, "#ddd")),
            customdata=muestra["adquisicion_utc"].dt.strftime("%Y-%m-%d %H:%M UTC").fillna("No time"),
            hovertemplate="%{customdata}<br>Latitude: %{y:.4f}<br>Longitude: %{x:.4f}<extra>"+nombre+"</extra>"
        ))
    figura.update_layout(
        height=460, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0b1230", margin=dict(l=12, r=12, t=20, b=15),
        legend=dict(orientation="h", y=1.05, x=0),
        xaxis=dict(title="Longitude", range=[-58.9, -52.8], gridcolor="rgba(170,190,235,.15)"),
        yaxis=dict(title="Latitude", range=[-35.5, -29.75], scaleanchor="x", scaleratio=1,
                   gridcolor="rgba(170,190,235,.15)")
    )
    st.plotly_chart(figura, use_container_width=True)


def mostrar_monitoreo_nrt():
    st.subheader("🛰️ Recent satellite monitoring · NASA FIRMS")
    st.caption("On-demand query. This module does NOT modify the historical data or the IGNIS Master.")
    st.info("NASA publishes thermal anomalies with some delay; this is not a continuous satellite feed or an emergency system.")
    clave = _clave_nasa()
    if not clave:
        st.warning("To enable queries, configure NASA_FIRMS_MAP_KEY or FIRMS_MAP_KEY in the Streamlit app Secrets (not on GitHub).")
        st.markdown("Request a free key: https://firms.modaps.eosdis.nasa.gov/api/map_key/")

    with st.form("ignis_nrt_consulta_form"):
        a, b = st.columns([2, 1])
        with a:
            seleccion = st.multiselect(
                "Satellites to query", list(FUENTES),
                default=["VIIRS NOAA-20", "VIIRS NOAA-21"],
                help="Each source is a separate product; they are not added up as fires."
            )
        with b:
            dias = st.selectbox("Recent period (UTC)", [1, 2, 3], index=1,
                                 format_func=lambda x: f"Last {x} calendar day(s)")
        enviar = st.form_submit_button("🔎 Query NASA FIRMS", disabled=(not clave or not seleccion), type="primary")

    if enviar:
        with st.spinner("Querying recent NASA FIRMS sources..."):
            datos, incidencias = _consulta(clave, seleccion, dias)
        st.session_state["ignis_nrt_ultimo"] = {
            "datos": datos, "incidencias": incidencias, "fuentes": seleccion,
            "dias": dias, "fecha_consulta": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        }
    estado = st.session_state.get("ignis_nrt_ultimo")
    if estado is None:
        st.caption("No queries made in this session. The historical platform works normally.")
        return

    st.caption(f"Query requested: {estado['fecha_consulta']} · Sources: {', '.join(estado['fuentes'])} · Window: {estado['dias']} UTC day(s). 15-minute cache.")
    for incidencia in estado["incidencias"]:
        st.warning(incidencia)
    datos = estado["datos"]
    if datos.empty:
        st.info("There are no detections in the queried responses for the Uruguay area, or the sources could not respond. This does NOT prove the absence of fires.")
        return

    x, y, z = st.columns(3)
    x.metric("Recent observations available", f"{len(datos):,}")
    y.metric("Sources with detections", datos["producto"].nunique())
    z.metric("Latest acquisition available (UTC)",
             datos["adquisicion_utc"].max().strftime("%d/%m %H:%M") if datos["adquisicion_utc"].notna().any() else "No time")
    st.markdown("#### Location of the received detections")
    _mapa_liviano(datos)
    # Contextual access to NASA imagery, without adding external requests in the app.
    visibles = datos.dropna(subset=["adquisicion_utc", "latitude", "longitude"]).copy()
    if not visibles.empty:
        mas_reciente = visibles.sort_values("adquisicion_utc", ascending=False).iloc[0]
        try:
            st.link_button(
                "Open latest observation in NASA Worldview",
                enlace_worldview(
                    mas_reciente["adquisicion_utc"],
                    mas_reciente["latitude"],
                    mas_reciente["longitude"],
                ),
            )
            st.caption("Worldview opens an approximate date and area; turn on the satellite layers of interest. It is not a fire verification.")
        except (ValueError, TypeError):
            pass
    st.caption("Approximate rectangular area: it may include areas outside Uruguay. Points limited to 1200 per source on the map; the table and the CSV keep every returned record.")
    st.markdown("#### Detections by source (not unique fires)")
    recuentos = datos.groupby("producto").size().reset_index(name="observations").rename(columns={"producto": "source"})
    st.dataframe(recuentos, use_container_width=True, hide_index=True)
    st.markdown("#### Recent records")
    tabla = datos.head(400).copy()
    tabla["adquisicion_utc"] = tabla["adquisicion_utc"].dt.strftime("%Y-%m-%d %H:%M UTC")
    st.dataframe(tabla, use_container_width=True, hide_index=True, height=260)
    exportar = datos.copy()
    exportar["adquisicion_utc"] = exportar["adquisicion_utc"].dt.strftime("%Y-%m-%d %H:%M UTC")
    st.download_button("⬇️ Download recent query CSV", exportar.to_csv(index=False).encode("utf-8-sig"),
                       file_name="IGNIS_FIRMS_consulta_reciente.csv", mime="text/csv")
    st.warning("Thermal detection ≠ confirmed fire. Do not infer burned area, severity, complete coverage or the number of fires by adding sensors. For emergencies use official channels.")
