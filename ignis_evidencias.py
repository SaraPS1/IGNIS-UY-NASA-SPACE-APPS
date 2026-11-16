"""Evidencia documental externa para los expedientes históricos de IGNIS."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from ignis_i18n import display_dataframe
RUTA_CATALOGO = Path(__file__).resolve().parent / "biblioteca_ignis" / "evidencias.json"
RUTA_MAESTRO_HISTORICO = Path(__file__).resolve().parent / "catalogo_fuentes_2000_2026.json"


def normalizar_catalogo(catalogo):
    if not isinstance(catalogo, dict):
        raise ValueError("The documentary master must be a JSON object.")
    fuentes = catalogo.get("fuentes")
    casos = catalogo.get("casos")
    if isinstance(fuentes, list) and fuentes:
        return {**catalogo, "casos": convertir_fuentes_a_casos(fuentes)}
    if isinstance(casos, list) and casos:
        return catalogo
    raise ValueError("The documentary master must contain a nonempty 'fuentes' or 'casos' list.")


def cargar_catalogo():
    if RUTA_MAESTRO_HISTORICO.exists():
        try:
            with RUTA_MAESTRO_HISTORICO.open("r", encoding="utf-8") as archivo:
                return normalizar_catalogo(json.load(archivo))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise ValueError(
                "The 2000–2026 documentary master is incomplete or empty. "
                "Do not substitute the older 2023 catalogue."
            ) from error

    with RUTA_CATALOGO.open("r", encoding="utf-8") as archivo:
        return normalizar_catalogo(json.load(archivo))


def convertir_fuentes_a_casos(fuentes):
    casos_por_año = {}
    for fuente in fuentes:
        año = int(fuente["anio"])
        fechas = sorted({fecha for fecha in (
            fuente.get("evento_desde", ""), fuente.get("evento_hasta", "")
        ) if fecha})
        caso = casos_por_año.setdefault(año, {
            "id": f"documental-{año}",
            "anio": año,
            "nombre": f"Documented incidents {año}",
            "departamento": fuente.get("lugar_reportado", "Uruguay"),
            "fechas_utc": fechas,
            "bbox": [-35.2, -30.0, -58.6, -53.0],
            "resumen": "External sources added to the historical archive; they are not wildfire perimeters or pixel-level validation.",
            "esperados": {},
            "fuentes": [],
        })
        caso["fechas_utc"] = sorted(set(caso["fechas_utc"] + fechas))
        caso["fuentes"].append({
            "tipo": fuente.get("clase", "External source"),
            "medio": fuente.get("organismo", "Agency not specified"),
            "titulo": fuente.get("titulo", "Untitled source"),
            "fecha_publicacion": fuente.get("fecha_publicacion", ""),
            "hecho_fecha_desde_local": fuente.get("evento_desde", ""),
            "hecho_fecha_hasta_local": fuente.get("evento_hasta", ""),
            "lugar": fuente.get("lugar_reportado", "Uruguay"),
            "url": fuente.get("url", ""),
            "alcance": fuente.get("alcance", "Contextual documentary source"),
            "notas": fuente.get("nota", ""),
        })
    return list(casos_por_año.values())


def coincidente_en_datos(caso: dict, datos: pd.DataFrame | None) -> tuple[bool, int]:
    if datos is None or datos.empty:
        return False, 0
    fechas = pd.to_datetime(datos["fecha"], errors="coerce", utc=True)
    lat_min, lat_max, lon_min, lon_max = caso["bbox"]
    valido = pd.DataFrame({
        "fecha": fechas,
        "latitude": pd.to_numeric(datos["latitude"], errors="coerce"),
        "longitude": pd.to_numeric(datos["longitude"], errors="coerce"),
    }).dropna()
    fechas_caso = set(pd.to_datetime(caso.get("fechas_utc", []), errors="coerce", utc=True).strftime("%Y-%m-%d"))
    if not fechas_caso:
        return False, 0
    recorte = valido[
        valido["fecha"].dt.strftime("%Y-%m-%d").isin(fechas_caso)
        & valido["latitude"].between(lat_min, lat_max)
        & valido["longitude"].between(lon_min, lon_max)
    ]
    return len(recorte) > 0, len(recorte)


def mostrar_evidencias(datos: pd.DataFrame | None = None, año: int | None = None) -> None:
    etiqueta_año = str(año) if año is not None else "all years"
    st.markdown(f"##### Verified external evidence · {etiqueta_año}")
    st.info("A news story, Fire Service statement, or SINAE report provides context for the reported fire but does not validate every FIRMS detection or its perimeter.")

    with st.expander("Additional sources uploaded by the user", expanded=False):
        maestro = st.file_uploader("Import an additional IGNIS documentary Master (optional JSON)", type=["json"], key="maestro_documental")
        if maestro is not None:
            try:
                candidato = json.loads(maestro.getvalue().decode("utf-8-sig"))
                candidato = normalizar_catalogo(candidato)
                st.session_state["maestro_documental_2000_2026"] = candidato
                st.success(f"Documentary master loaded: {len(candidato['casos'])} year-specific cases.")
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, ValueError) as error:
                st.error(f"Could not import documentary Master dataset: {error}")

    try:
        catalogo_sesion = st.session_state.get("maestro_documental_2000_2026")
        catalogo = normalizar_catalogo(catalogo_sesion) if catalogo_sesion is not None else cargar_catalogo()
    except (OSError, json.JSONDecodeError, ValueError) as error:
        st.error(f"Could not read the documentary catalogue: {error}")
        return

    st.download_button(
        "Download incorporated yearly catalogue (JSON)",
        data=json.dumps(catalogo, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="IGNIS_MAESTRO_DOCUMENTAL.json",
        mime="application/json",
        key="descargar_maestro_documental",
    )

    casos = catalogo.get("casos", [])
    if año is not None:
        casos = [caso for caso in casos if
                 int(caso.get("anio", año)) == año
                 or any(str(fecha).startswith(str(año)) for fecha in caso.get("fechas_utc", []))]
    if not casos:
        st.warning(f"No verified external sources have been incorporated for year {año}. This does not prove an absence of wildfires.")
        st.caption("For every new year, add cases with dates, locations, source links, and evidence scope to biblioteca_ignis/evidencias.json.")
        return

    opciones = {f"{caso['nombre']} ({', '.join(caso.get('fechas_utc', []))})": caso for caso in casos}
    elegido = st.selectbox("Documented case", list(opciones), key=f"evidencia_documental_{año or 'todos'}")
    caso = opciones[elegido]
    coincide, cantidad = coincidente_en_datos(caso, datos)

    col1, col2, col3 = st.columns(3)
    col1.metric("External sources", len(caso.get("fuentes", [])))
    col2.metric("FIRMS records in current upload", cantidad)
    col3.metric("Documentary association", "Regional/temporal match" if coincide else "No match in current upload")

    st.write(caso.get("resumen", "No summary available."))
    st.caption("The following counts and dates come from the historical catalogue and may differ from uploaded observations.")
    display_dataframe(pd.DataFrame([{
        "UTC dates": ", ".join(caso.get("fechas_utc", [])),
        "MODIS": caso.get("esperados", {}).get("MODIS", 0),
        "VIIRS S-NPP": caso.get("esperados", {}).get("VIIRS S-NPP", 0),
        "VIIRS NOAA-20": caso.get("esperados", {}).get("VIIRS NOAA-20", 0),
    }]), use_container_width=True, hide_index=True)

    fuentes = caso.get("fuentes", [])
    if not fuentes:
        st.warning("No geolocated external source is included for this case. This does not prove the wildfire did not occur.")
        return

    filas = []
    for fuente in fuentes:
        filas.append({
            "Type": fuente.get("tipo", ""),
            "Publisher": fuente.get("medio", ""),
            "Publication date": fuente.get("fecha_publicacion", ""),
            "Event dates": f"{fuente.get('hecho_fecha_desde_local', '')} to {fuente.get('hecho_fecha_hasta_local', '')}",
            "Reported location": fuente.get("lugar", ""),
            "Title": fuente.get("titulo", ""),
            "Source URL": fuente.get("url", ""),
        })
    display_dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

    for numero, fuente in enumerate(fuentes, start=1):
        with st.expander(f"Source {numero} · {fuente.get('medio', '')}", expanded=(numero == 1)):
            st.markdown(f"**{fuente.get('titulo', '')}**")
            st.write(f"Type: {fuente.get('tipo', '')} · Location: {fuente.get('lugar', '')}")
            st.caption(f"Reported event: {fuente.get('hecho_fecha_desde_local', '')} to {fuente.get('hecho_fecha_hasta_local', '')}")
            st.write(f"**Evidence scope:** {fuente.get('alcance', '')}")
            st.write(fuente.get("notas", ""))
            if fuente.get("url"):
                st.link_button("Open original source", fuente["url"])

    st.download_button(
        "Download full source catalogue (JSON)",
        data=json.dumps(catalogo, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="IGNIS_evidencias_externas.json",
        mime="application/json",
    )
    st.download_button(
        "Download flat source index (CSV)",
        data=pd.DataFrame(filas).to_csv(index=False).encode("utf-8-sig"),
        file_name="IGNIS_fuentes_externas.csv",
        mime="text/csv",
    )
    st.caption("The absence of geolocated catalogue sources does not prove an absence of wildfires. Each source retains its original URL for auditing.")
