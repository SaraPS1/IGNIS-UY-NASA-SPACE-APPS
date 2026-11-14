"""Motor transparente de consultas estadísticas de ASK IGNIS.

No utiliza un LLM, IA generativa ni servicios externos: solo reglas explícitas
y los registros cargados por la persona usuaria. No valida incendios.
"""
import unicodedata

import pandas as pd


def normalizar_pregunta(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").strip()


def _resultado(respuesta: str, grafico=None, fuentes=None):
    return {
        "answer": respuesta,
        "chart": grafico,
        "sources": fuentes if fuentes is not None else [],
    }


def responder_ignis(datos: pd.DataFrame, pregunta: str):
    """Responde en español sin atribuir los resultados a un modelo de IA.

    La función no suma detecciones como si fueran incendios únicos ni crea
    datos a partir de preguntas. Los filtros se aplican al archivo recibido.
    """
    q = normalizar_pregunta(pregunta)
    if not q:
        return _resultado("Ask a question about your FIRMS records.")

    if any(t in q for t in ("que es ask ignis", "que ia", "que modelo", "como funciona ask")):
        return _resultado(
            "ASK IGNIS is a rule-based statistical assistant built with Python and Pandas. "
            "It does not use GPT, Gemini, or any other generative model. "
            "It only analyzes files uploaded during this session."
        )
    if any(t in q for t in (
        "incendio confirmado", "incendios confirmados", "fuego confirmado",
        "son incendios", "validar incendio", "verificar incendio",
    )):
        return _resultado(
            "A FIRMS hotspot is a thermal anomaly observation, not "
            "confirmation of a wildfire. Verifying an event requires "
            "external evidence, comparable dates, and coordinates. "
            "See “Alerts and traceability” to review documentation."
        )

    if datos is None or datos.empty:
        return _resultado(
            "No records have been uploaded yet. Import a NASA FIRMS ZIP/CSV or an "
            "IGNIS Master dataset in “Data upload” to run statistical queries."
        )

    frame = datos.copy()
    frame["fecha"] = pd.to_datetime(frame["fecha"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["fecha"])
    if frame.empty:
        return _resultado(
            "This file has no valid dates to analyze. Review the upload."
        )

    # Esta procedencia indica únicamente el archivo aportado, no una
    # validación independiente de las observaciones o de un incendio.
    fuentes = ["Records imported into IGNIS (current session)"]
    if "fuente" in frame.columns and frame["fuente"].notna().any():
        fuentes.append("“fuente” provenance field in the uploaded file")

    if "uruguay" in q or " uy" in " " + q:
        frame = frame[
            frame["latitude"].between(-35.5, -29.7)
            & frame["longitude"].between(-58.8, -52.8)
        ]

    has_modis = "modis" in q
    has_viirs = "viirs" in q
    if has_modis and not has_viirs:
        frame = frame[frame["instrumento"].astype(str).str.contains(
            "MODIS", case=False, na=False
        )]
    elif has_viirs and not has_modis:
        frame = frame[frame["instrumento"].astype(str).str.contains(
            "VIIRS", case=False, na=False
        )]

    if "departamento" in q or any(n in q for n in (
        "durazno", "lavalleja", "artigas", "canelones", "treinta y tres", "cerro del toro"
    )):
        return _resultado(
            "ASK IGNIS cannot yet automatically assign each detection to a "
            "department or case based on text. Select the region using "
            "IGNIS filters to explore the area. "
            "Administrative boundaries are not inferred.",
            fuentes=fuentes,
        )

    if (has_modis and has_viirs) or (
        ("compar" in q or "compare" in q) and ("sensor" in q or "instrument" in q)
    ):
        grouped = frame.groupby("instrumento").size().reset_index(name="Observations")
        grouped = grouped.rename(columns={"instrumento": "Instrument"})
        return _resultado(
            "Descriptive comparison of MODIS and VIIRS records in the "
            "uploaded file. Counts have not been harmonized across sensors and do not "
            "represent unique wildfires.",
            grouped,
            fuentes,
        )

    if "frp" in q or "potencia radiativa" in q or "fire radiative power" in q:
        frp = pd.to_numeric(
            frame.get("frp", pd.Series(index=frame.index, dtype=float)),
            errors="coerce",
        ).dropna()
        if frp.empty:
            return _resultado(
                "No numeric FRP values are available in the uploaded selection.",
                fuentes=fuentes,
            )
        return _resultado(
            f"Among {len(frp):,} records with FRP, the minimum is "
            f"{frp.min():,.2f} MW, the maximum is {frp.max():,.2f} MW, and the "
            f"average is {frp.mean():,.2f} MW. "
            "These values alone cannot measure burned area.",
            fuentes=fuentes,
        )

    if any(t in q for t in ("este mes", "mes actual", "this month")):
        now = pd.Timestamp.now(tz="UTC")
        frame = frame[
            (frame["fecha"].dt.year == now.year)
            & (frame["fecha"].dt.month == now.month)
        ]
        grouped = frame.groupby(frame["fecha"].dt.day).size().reset_index(
            name="Observations"
        )
        grouped.columns = ["Day", "Observations"]
        return _resultado(
            f"In {now.strftime('%Y-%m')}, there are {len(frame):,} observations "
            "in uploaded files for the selected area. "
            "Zero observations do not prove an absence of wildfires or complete coverage.",
            grouped,
            fuentes,
        )

    if any(t in q for t in ("ultimos cinco", "ultimos 5", "last five years")):
        last = int(frame["fecha"].dt.year.max())
        frame = frame[frame["fecha"].dt.year >= last - 4]
        grouped = frame.groupby(frame["fecha"].dt.year).size().reset_index(
            name="Observations"
        )
        grouped.columns = ["Year", "Observations"]
        return _resultado(
            f"Activity over the five years up to {last}, based on years included "
            "in the file. These are observations, not confirmed wildfires.",
            grouped,
            fuentes,
        )

    if any(t in q for t in (
        "historico", "historia", "por ano", "periodos", "evolucion anual",
         "historical"
    )):
        grouped = frame.groupby(frame["fecha"].dt.year).size().reset_index(
            name="Observations"
        )
        grouped.columns = ["Year", "Observations"]
        return _resultado(
            "Annual series calculated from uploaded historical records. "
            "The comparison may be affected by differences in coverage and "
            "sensor availability across years.",
            grouped,
            fuentes,
        )

    if any(t in q for t in ("por mes", "por meses", "actividad mensual", "activity by month", "monthly", "by month")):
        grouped = frame.groupby(frame["fecha"].dt.month).size().reset_index(
            name="Observations"
        )
        grouped.columns = ["Month", "Observations"]
        return _resultado(
            "Distribution of file observations by calendar month. "
            "It combines all uploaded years and does not represent a wildfire rate.",
            grouped,
            fuentes,
        )

    if any(t in q for t in (
        "cuant", "cantidad", "numero", "total", "deteccion", "observacion",
        "hotspot", "punto de calor", "registro", "count", "observations"
    )):
        counts = frame.groupby("instrumento").size().reset_index(
            name="Observations"
        ).rename(columns={"instrumento": "Instrument"})
        return _resultado(
            f"The requested area contains {len(frame):,} records of "
            "uploaded thermal observations. These are neither unique wildfires "
            "nor burned area.",
            counts,
            fuentes,
        )

    return _resultado(
        "I cannot answer that question yet. Try asking about the total number of "
        "observations, MODIS–VIIRS comparisons, activity by year or "
        "month, or FRP values. ASK IGNIS does not invent answers "
        "when a question falls outside its supported rules.",
        fuentes=fuentes,
    )
