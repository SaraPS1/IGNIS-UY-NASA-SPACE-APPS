"""Conservative, per-ROW sensor identification in NASA FIRMS files.

It never classifies a whole CSV from the satellite of the first row.
It avoids mixing NOAA-20, NOAA-21 and Suomi-NPP platforms when they arrive
together in a file downloaded or merged by the user.
"""
from __future__ import annotations

import pandas as pd


def clasificar_instrumentos(df: pd.DataFrame, nombre_archivo: str = "") -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype="object", name="instrumento")
    idx = df.index
    inst = (df["instrument"].fillna("").astype(str).str.upper().str.strip()
            if "instrument" in df else pd.Series("",index=idx))
    sat = (df["satellite"].fillna("").astype(str).str.upper().str.strip()
           if "satellite" in df else pd.Series("",index=idx))
    name = str(nombre_archivo).lower()
    # These labels come from FIRMS products, not from the inferred resolution.
    archivo_modis = any(x in name for x in ("m-c61", "modis", "mcd14", "mod14"))
    archivo_viirs = any(x in name for x in ("viirs", "sv-c2", "j1v", "j2v", "noaa"))
    familia_modis = inst.str.startswith("MODIS") | (
        inst.eq("") & sat.isin(["T","A","TERRA","AQUA"])
    ) | (inst.eq("") & sat.eq("") & archivo_modis)
    familia_viirs = inst.str.startswith("VIIRS") | (
        inst.eq("") & sat.isin(["N20","NOAA-20","J1","N21","NOAA-21","J2","SNPP","S-NPP","NPP"])
    ) | (inst.eq("") & sat.eq("") & archivo_viirs)
    # If the row explicitly declares MODIS/VIIRS, it wins over the file name.
    salida = pd.Series(pd.NA,index=idx,dtype="object",name="instrumento")
    salida.loc[familia_modis] = "MODIS"
    salida.loc[familia_viirs & ~familia_modis] = "VIIRS (plataforma no identificada)"
    vi = familia_viirs & ~familia_modis
    s20 = sat.isin(["N20","NOAA-20","J1"])
    s21 = sat.isin(["N21","NOAA-21","J2"])
    snpp = sat.isin(["SNPP","S-NPP","NPP"])
    salida.loc[vi & s20] = "VIIRS NOAA-20"
    salida.loc[vi & s21] = "VIIRS NOAA-21"
    salida.loc[vi & snpp] = "VIIRS S-NPP"
    # Rescue only if the file has an unambiguous platform, without
    # overwriting known satellite metadata from another platform.
    sin_plataforma = vi & ~(s20 | s21 | snpp) & sat.eq("")
    if any(x in name for x in ("j2v", "noaa21", "noaa-21")):
        salida.loc[sin_plataforma] = "VIIRS NOAA-21"
    elif any(x in name for x in ("j1v", "noaa20", "noaa-20")):
        salida.loc[sin_plataforma] = "VIIRS NOAA-20"
    elif any(x in name for x in ("sv-c2", "snpp", "s-npp")):
        salida.loc[sin_plataforma] = "VIIRS S-NPP"
    return salida
