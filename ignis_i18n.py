"""Presentation-only English labels for IGNIS UY tables.

Scientific input schemas, exported CSV columns, and numeric computations remain unchanged.
"""

import pandas as pd
import streamlit as st

COLUMN_LABELS = {
    "anio": "Year", "Año": "Year", "ano": "Year",
    "Mes UTC": "UTC month", "Instrumento": "Instrument",
    "Observaciones importadas": "Imported observations",
    "Horarios válidos": "Valid timestamps", "FRP disponible": "Available FRP",
    "Estado de datos": "Data status", "Cobertura orbital verificada": "Verified orbital coverage",
    "Fechas UTC": "UTC dates", "Tipo": "Type", "Medio": "Publisher",
    "Fechas del hecho": "Event dates", "Lugar reportado": "Reported location",
    "Enlace": "Source URL", "Fuentes externas": "External sources",
    "mes": "Month", "Mes": "Month",
    "dia": "Day", "Día": "Day",
    "instrumento": "Instrument", "Instrumento": "Instrument",
    "sensores": "Sensors", "Sensor": "Sensor",
    "detecciones": "Detections", "Detecciones": "Detections",
    "observaciones": "Observations", "Observaciones": "Observations",
    "Registros": "Records", "registros": "Records",
    "Período": "Period", "Periodo": "Period", "Configuración instrumental": "Instrument configuration",
    "Celdas coincidentes": "Matching cells",
    "Celdas-día con ambos": "Cell-days with both families",
    "Días con coincidencia": "Days with matches",
    "Meses con ambas familias": "Months with both families",
    "Meses importados": "Imported months",
    "Ambas presentes": "Both present",
    "Mediana otros años": "Median of other years",
    "Índice frente a mediana": "Ratio to median",
    "Distancia mediana (km)": "Median distance (km)",
    "Diferencia mediana (min)": "Median time difference (min)",
    "Par instrumental": "Instrument pair", "Pares": "Pairs",
    "Resolución (°)": "Resolution (°)",
    "Días con detecciones": "Days with detections",
    "Coordenadas válidas": "Valid coordinates",
    "Fuente": "Source", "fuente": "Source",
    "nombre": "Name", "titulo": "Title", "resumen": "Summary",
    "Fecha publicación": "Publication date",
    "Estado": "Status", "Estado declarado": "Declared status",
    "Condición": "Status", "Procedencia": "Provenance",
    "Tipo informado": "Reported type", "ID": "ID",
    "Eventos en celda": "Events in cell",
    "Años de los eventos": "Event years",
    "Bomberos/PAIF cargados": "Uploaded Fire Service/PAIF",
    "SINAE/MIRA cargados": "Uploaded SINAE/MIRA",
    "fecha": "Date", "fecha_utc": "UTC date",
    "latitud": "Latitude", "longitud": "Longitude",
    "lat": "Latitude", "lon": "Longitude",
    "latitude": "Latitude", "longitude": "Longitude",
    "registros_validos": "Valid records",
    "primer_dia": "First day", "ultimo_dia": "Last day",
    "archivo": "File", "csv": "CSV",
}

MONTHS = {
    "Enero": "January", "Febrero": "February", "Marzo": "March",
    "Abril": "April", "Mayo": "May", "Junio": "June",
    "Julio": "July", "Agosto": "August", "Septiembre": "September",
    "Octubre": "October", "Noviembre": "November", "Diciembre": "December",
}


def english_view(data):
    """Return a display copy with translated headers and month names only."""
    if not isinstance(data, pd.DataFrame):
        return data
    shown = data.rename(columns=COLUMN_LABELS)
    if "Month" in shown and (shown["Month"].dtype == object or
                             pd.api.types.is_string_dtype(shown["Month"])):
        shown = shown.copy()
        shown["Month"] = shown["Month"].replace(MONTHS)
    if "Data status" in shown:
        shown = shown.copy()
        shown["Data status"] = shown["Data status"].replace(VALUE_LABELS)
    if "Verified orbital coverage" in shown:
        shown = shown.copy()
        shown["Verified orbital coverage"] = shown["Verified orbital coverage"].replace(VALUE_LABELS)
    return shown


def display_dataframe(data, *args, **kwargs):
    return st.dataframe(english_view(data), *args, **kwargs)


VALUE_LABELS = {
    "CON DETECCIONES IMPORTADAS": "IMPORTED DETECTIONS",
    "SIN REGISTROS IMPORTADOS": "NO RECORDS IMPORTED",
    "NO": "No",
}


def english_quality_notice(message: str) -> str:
    """Translate quality diagnostics at display time, preserving scientific outputs."""
    import re
    if message.startswith("Sin registros importados:"):
        return "No records imported: satellite coverage or absence of thermal activity cannot be inferred."
    if message.startswith("No se han verificado oportunidades"):
        return "Observation opportunities, cloud cover, and instrument coverage have not been verified."
    match = re.fullmatch(r"([\d,]+) de ([\d,]+) registros sin (.+) válida\.", message)
    if match:
        names = {"coordenadas": "coordinates", "fechas": "dates",
                 "horarios UTC": "UTC timestamps", "familia instrumental": "instrument family"}
        return f"{match.group(1)} of {match.group(2)} records have missing or invalid {names.get(match.group(3), match.group(3))}."
    match = re.fullmatch(r"Hay ([\d,]+) IDs repetidos en esta tabla\.", message)
    if match:
        return f"There are {match.group(1)} duplicate IDs in this table."
    return message
