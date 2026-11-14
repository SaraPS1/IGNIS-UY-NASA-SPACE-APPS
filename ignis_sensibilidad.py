"""Spatial sensitivity diagnosis of the MODIS–VIIRS coincidence.

It does not harmonize radiometry, coverage, detection probabilities or FRP.
Zeros represent an absence of records *in the uploaded files*,
NOT satellite observation with absence of fire.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RESOLUCIONES = (0.05, 0.10, 0.20, 0.40)
COLUMNAS = [
    "Resolution (°)", "Cell-days with both", "Days with coincidence",
    "Months with coincidence", "Months with both families",
]


def preparar_observaciones(datos: pd.DataFrame | None) -> pd.DataFrame:
    """Keep dated, geolocated observations with a recognized family.

    Satellite identity and the original counts are not replaced.
    """
    cols = ["fecha_utc", "mes_utc", "anio", "latitude", "longitude", "familia"]
    if datos is None or datos.empty:
        return pd.DataFrame(columns=cols)
    faltantes = {"fecha", "latitude", "longitude", "instrumento"} - set(datos.columns)
    if faltantes:
        raise ValueError("Missing Master columns: " + ", ".join(sorted(faltantes)))

    z = datos[["fecha", "latitude", "longitude", "instrumento"]].copy()
    fecha = pd.to_datetime(z["fecha"], errors="coerce", utc=True)
    z["latitude"] = pd.to_numeric(z["latitude"], errors="coerce")
    z["longitude"] = pd.to_numeric(z["longitude"], errors="coerce")
    nombre = z["instrumento"].fillna("").astype(str).str.upper().str.strip()
    z["familia"] = np.select(
        [nombre.str.startswith("MODIS"), nombre.str.startswith("VIIRS")],
        ["MODIS", "VIIRS"], default="",
    )
    z["fecha_utc"] = fecha.dt.strftime("%Y-%m-%d")
    z["mes_utc"] = fecha.dt.strftime("%Y-%m")
    z["anio"] = fecha.dt.year
    z = z.dropna(subset=["fecha_utc", "latitude", "longitude", "anio"])
    z = z[
        z["latitude"].between(-90, 90)
        & z["longitude"].between(-180, 180)
        & z["familia"].isin(["MODIS", "VIIRS"])
    ]
    return z[cols].copy().reset_index(drop=True)


def presencia_mensual(datos: pd.DataFrame | None) -> pd.DataFrame:
    """Counts per month/family of the imported file, without inferring coverage."""
    cols = ["UTC month", "MODIS", "VIIRS", "Both present"]
    z = preparar_observaciones(datos)
    if z.empty:
        return pd.DataFrame(columns=cols)
    p = z.groupby(["mes_utc", "familia"]).size().unstack(fill_value=0)
    for sensor in ("MODIS", "VIIRS"):
        if sensor not in p:
            p[sensor] = 0
    p = p[["MODIS", "VIIRS"]].sort_index().reset_index()
    p["Both present"] = (p.MODIS > 0) & (p.VIIRS > 0)
    return p.rename(columns={"mes_utc": "UTC month"})[cols]


def comparar_resoluciones(
    datos: pd.DataFrame | None,
    ano: int | None = None,
    resoluciones: tuple[float, ...] = RESOLUCIONES,
) -> pd.DataFrame:
    """Count coincident cell-days by grid size.

    Reproduces the Master convention: round(lat/degrees) and round(lon/degrees).
    'Cell-days' = same UTC date + cell + presence of both families.
    """
    z = preparar_observaciones(datos)
    if ano is not None:
        z = z[z["anio"] == int(ano)]
    meses_ambos = 0
    if not z.empty:
        presencia = z.groupby(["mes_utc", "familia"]).size().unstack(fill_value=0)
        if "MODIS" in presencia and "VIIRS" in presencia:
            meses_ambos = int(((presencia["MODIS"] > 0) & (presencia["VIIRS"] > 0)).sum())
    salida = []
    for res in resoluciones:
        res = float(res)
        if not np.isfinite(res) or res <= 0 or res > 5:
            raise ValueError("Resolution must be between 0 and 5 degrees, excluding 0.")
        if z.empty:
            salida.append([res, 0, 0, 0, 0])
            continue
        q = z.copy()
        q["grid_lat"] = np.rint(q["latitude"] / res).astype(int)
        q["grid_lon"] = np.rint(q["longitude"] / res).astype(int)
        g = q.groupby(
            ["fecha_utc", "grid_lat", "grid_lon", "familia"], sort=True
        ).size().unstack(fill_value=0)
        for sensor in ("MODIS", "VIIRS"):
            if sensor not in g:
                g[sensor] = 0
        coinciden = g[(g["MODIS"] > 0) & (g["VIIRS"] > 0)]
        dias = coinciden.index.get_level_values("fecha_utc").unique()
        meses = pd.Index(dias.str.slice(0, 7)).nunique()
        salida.append([res, int(len(coinciden)), int(len(dias)), int(meses), meses_ambos])
    return pd.DataFrame(salida, columns=COLUMNAS)


def diagnostico_comparabilidad(datos: pd.DataFrame | None) -> dict:
    """Descriptive summary: it does NOT compute or authorize a calibrated series."""
    z = preparar_observaciones(datos)
    meses = presencia_mensual(datos)
    return {
        "registros": int(len(z)),
        "meses_importados": int(len(meses)),
        "meses_con_ambas_familias": int(meses["Both present"].sum()) if len(meses) else 0,
        "dias_con_detecciones_modis": int(z.loc[z.familia == "MODIS", "fecha_utc"].nunique()),
        "dias_con_detecciones_viirs": int(z.loc[z.familia == "VIIRS", "fecha_utc"].nunique()),
        "cobertura_satelital_verificada": False,
        "serie_armonizada_validada": False,
    }
