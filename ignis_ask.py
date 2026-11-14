"""Transparent statistical query engine for ASK IGNIS.

It does not use an LLM, generative AI or external services: only explicit
rules and the records uploaded by the user. It does not validate fires.
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
    """Answers in English without attributing the results to an AI model.

    The function does not add detections as if they were unique fires, nor
    does it create data from questions. Filters apply to the received file.
    Keyword matching accepts English and Spanish phrasing.
    """
    q = normalizar_pregunta(pregunta)
    if not q:
        return _resultado("Type a question about your FIRMS records.")

    if any(t in q for t in (
        "que es ask ignis", "que ia", "que modelo", "como funciona ask",
        "what is ask ignis", "which ai", "what model", "how does ask",
    )):
        return _resultado(
            "ASK IGNIS is a statistical assistant based on Python and Pandas rules. "
            "It does not use GPT, Gemini or any other generative model. "
            "It analyzes only the files uploaded in this session."
        )
    if any(t in q for t in (
        "incendio confirmado", "incendios confirmados", "fuego confirmado",
        "son incendios", "validar incendio", "verificar incendio",
        "confirmed fire", "confirmed fires", "are they fires", "are these fires",
        "validate fire", "verify fire",
    )):
        return _resultado(
            "A FIRMS hotspot is an observation of a thermal anomaly, not the "
            "confirmation of a fire. Verifying an event requires external "
            "sources with comparable dates and coordinates. "
            "Check “Alerts and traceability” to review documentation."
        )

    if datos is None or datos.empty:
        return _resultado(
            "There are no records loaded yet. Import a NASA FIRMS ZIP/CSV or an "
            "IGNIS Master in “Data upload” to run statistical queries."
        )

    frame = datos.copy()
    frame["fecha"] = pd.to_datetime(frame["fecha"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["fecha"])
    if frame.empty:
        return _resultado(
            "The file does not contain valid dates to analyze. Check the upload."
        )

    # This provenance only indicates the supplied file, not an independent
    # validation of the observations or of a fire.
    fuentes = ["Records imported into IGNIS (current session)"]
    if "fuente" in frame.columns and frame["fuente"].notna().any():
        fuentes.append("Provenance field “fuente” of the uploaded file")

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

    if "departamento" in q or "department" in q or any(n in q for n in (
        "durazno", "lavalleja", "artigas", "canelones", "treinta y tres", "cerro del toro"
    )):
        return _resultado(
            "ASK IGNIS cannot yet automatically assign each detection to a "
            "department or case from text. Select the region in the IGNIS "
            "filters to explore that area. "
            "No administrative boundaries are invented.",
            fuentes=fuentes,
        )

    if (has_modis and has_viirs) or (
        "compar" in q and ("sensor" in q or "instrument" in q)
    ):
        grouped = frame.groupby("instrumento").size().reset_index(name="Observations")
        grouped = grouped.rename(columns={"instrumento": "Instrument"})
        return _resultado(
            "Descriptive comparison of MODIS and VIIRS records in the uploaded "
            "file. Counts are not harmonized between sensors and are not "
            "equivalent to unique fires.",
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
                "No numeric FRP values are available in the loaded selection.",
                fuentes=fuentes,
            )
        return _resultado(
            f"Across {len(frp):,} records with FRP available, the minimum is "
            f"{frp.min():,.2f} MW, the maximum {frp.max():,.2f} MW and the "
            f"mean {frp.mean():,.2f} MW. "
            "These values alone do not measure burned area.",
            fuentes=fuentes,
        )

    if any(t in q for t in ("este mes", "mes actual", "this month", "current month")):
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
            f"In {now.strftime('%Y-%m')} there are {len(frame):,} observations "
            "in the uploaded files for the queried area. "
            "A zero does not prove the absence of fires or complete coverage.",
            grouped,
            fuentes,
        )

    if any(t in q for t in ("ultimos cinco", "ultimos 5", "last five years", "last 5 years")):
        last = int(frame["fecha"].dt.year.max())
        frame = frame[frame["fecha"].dt.year >= last - 4]
        grouped = frame.groupby(frame["fecha"].dt.year).size().reset_index(
            name="Observations"
        )
        grouped.columns = ["Year", "Observations"]
        return _resultado(
            f"Activity over the five years up to {last}, according to the years "
            "present in the file. These are observed records, not confirmed fires.",
            grouped,
            fuentes,
        )

    if any(t in q for t in (
        "historico", "historia", "por ano", "periodos", "evolucion anual",
        "historical", "by year", "per year", "yearly", "annual",
    )):
        grouped = frame.groupby(frame["fecha"].dt.year).size().reset_index(
            name="Observations"
        )
        grouped.columns = ["Year", "Observations"]
        return _resultado(
            "Annual series computed from the history actually loaded. "
            "The comparison may be affected by differences in coverage and "
            "sensors between years.",
            grouped,
            fuentes,
        )

    if any(t in q for t in (
        "por mes", "por meses", "actividad mensual", "activity by month",
        "by month", "per month", "monthly",
    )):
        grouped = frame.groupby(frame["fecha"].dt.month).size().reset_index(
            name="Observations"
        )
        grouped.columns = ["Month", "Observations"]
        return _resultado(
            "Distribution by calendar month of the observations in the file. "
            "It combines the loaded years and is not equivalent to a fire rate.",
            grouped,
            fuentes,
        )

    if any(t in q for t in (
        "cuant", "cantidad", "numero", "total", "deteccion", "observacion",
        "hotspot", "punto de calor", "registro", "count", "how many", "number",
        "detection", "observation", "record",
    )):
        counts = frame.groupby("instrumento").size().reset_index(
            name="Observations"
        ).rename(columns={"instrumento": "Instrument"})
        return _resultado(
            f"The queried selection contains {len(frame):,} records of "
            "uploaded thermal observations. They are not unique fires "
            "or burned area.",
            counts,
            fuentes,
        )

    return _resultado(
        "I don't recognize that question yet. Try asking for the total number of "
        "observations, the MODIS vs. VIIRS comparison, activity by year or "
        "month, or the FRP values. ASK IGNIS does not invent answers "
        "when the question is outside its rules.",
        fuentes=fuentes,
    )
