"""IGNIS UY · Satellite–ground fusion, cartographic version 3.0 (2026-11-05).

Isolated import: ``from ignis_fusion_terrestre import mostrar_fusion_terrestre``.
It does not connect to operational systems or send external alerts. It does not rewrite the Master.

Inputs:
- NASA FIRMS: existing ``combined`` DataFrame, columns fecha/latitude/longitude,
  instrumento/acq_time/id_registro.
- Firefighters/PAIF: manual CSV or JSON/GeoJSON, with field mapping.
- SINAE/MIRA: manual CSV or JSON/GeoJSON, with field mapping.

Output: exploratory spatial and temporal associations, NOT validated
detection, not fire prediction or an operational alert.
"""
from __future__ import annotations

import io
import hashlib
import zipfile
import json
import math
import re
import unicodedata
from datetime import timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

TZ_LOCAL = ZoneInfo("America/Montevideo")
BBOX_UY = (-35.6, -29.9, -58.9, -52.9)
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_ROWS = 100_000

FUENTE_MIRA = (
    "https://catalogodatos.gub.uy/dataset/"
    "sinae01-focos-de-incendios-registrados-en-el-sistema-mira/"
    "resource/76860165-d9a9-4d00-800e-a31ad514d22b"
)
FUENTE_CAMARAS = (
    "https://www.gub.uy/ministerio-interior/comunicacion/noticias/"
    "nuevo-sistema-inteligente-para-deteccion-incendios-geolocalizacion"
)
FUENTE_PAIF = (
    "https://www.spf.com.uy/es/actualidad/temporada-2025-26-del-operativo-paif"
)

ALIASES = {
    "fecha": ["fecha", "fecha_utc", "fecha_hora", "fecha_y_hora", "fecha_evento",
              "fechainicio", "fecha_inicio", "datetime", "date", "timestamp",
              "fecha_registro", "fecha_ocurrencia", "fecha_de_inicio", "fecha_deteccion"],
    "hora": ["hora", "hora_utc", "hora_deteccion", "time", "acq_time"],
    "lat": ["latitud", "latitude", "lat", "y", "coord_y", "coordenada_y", "lat_wgs84"],
    "lon": ["longitud", "longitude", "lon", "long", "lng", "x", "coord_x",
            "coordenada_x", "lon_wgs84"],
    "wkt": ["geometry", "geometria", "wkt", "geom", "the_geom", "punto"],
    "id": ["evento_id", "id_evento", "id", "objectid", "fid", "codigo", "identificador"],
    "detalle": ["tipo_deteccion", "tipo_incendio", "tipo", "subtipo", "descripcion",
                "detalle", "observacion", "observaciones", "situacion", "clase"],
    "estado": ["estado", "confirmado", "estatus", "resultado", "verificacion"],
    "origen": ["fuente", "origen", "institucion", "reportado_por", "organismo"],
}


def canon(s: object) -> str:
    s = unicodedata.normalize("NFKD", str(s).strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def encontrar_columna(columns: list[str], tipo: str) -> str | None:
    dic = {canon(c): c for c in columns}
    for alias in ALIASES[tipo]:
        if canon(alias) in dic:
            return dic[canon(alias)]
    return None


def leer_tabla_bytes(nombre: str, contenido: bytes) -> pd.DataFrame:
    """Reads CSV/JSON/GeoJSON WITHOUT network connections or content execution."""
    if len(contenido) > MAX_UPLOAD_BYTES:
        raise ValueError("File too large for this demo (maximum 12 MB).")
    extension = Path(nombre).suffix.lower()
    if extension == ".csv":
        errors = []
        for enc in ("utf-8-sig", "latin-1"):
            try:
                df = pd.read_csv(io.BytesIO(contenido), sep=None, engine="python", encoding=enc,
                                 dtype=str, on_bad_lines="error")
                break
            except Exception as e:
                errors.append(str(e))
        else:
            raise ValueError("Could not read CSV: " + errors[-1][:160])
    elif extension in (".json", ".geojson"):
        data = json.loads(contenido.decode("utf-8-sig"))
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and data.get("type") == "FeatureCollection":
            records = []
            for f in data.get("features", []):
                p = f.get("properties") or {}
                geo = f.get("geometry") or {}
                if geo.get("type") == "Point" and len(geo.get("coordinates", [])) >= 2:
                    lon, lat = geo["coordinates"][:2]
                    p = {**p, "__geo_lat": lat, "__geo_lon": lon}
                records.append(p)
            df = pd.DataFrame(records)
        else:
            for key in ("eventos", "events", "records", "features", "data"):
                if isinstance(data, dict) and isinstance(data.get(key), list):
                    df = pd.DataFrame(data[key])
                    break
            else:
                df = pd.DataFrame([data])
    else:
        raise ValueError("Unsupported format: upload CSV, JSON or GeoJSON.")
    if len(df) > MAX_ROWS:
        raise ValueError("Too many rows (maximum 100,000 records per upload).")
    if df.empty:
        raise ValueError("The file contains no data rows.")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def leer_firms_adicional(nombre: str, contenido: bytes) -> pd.DataFrame:
    """Additional NASA FIRMS CSV/ZIP, to import NRT observations manually.
    It does NOT query an API or modify the original Master.
    """
    if len(contenido) > MAX_UPLOAD_BYTES:
        raise ValueError("NASA CSV/ZIP exceeds the 12 MB limit of this demo.")
    tablas=[]
    if nombre.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            csvs=[info for info in z.infolist() if info.filename.lower().endswith(".csv")]
            if len(csvs)>20 or sum(x.file_size for x in csvs)>40*1024*1024:
                raise ValueError("NASA ZIP too large for this demo.")
            for f in csvs:
                tablas.append(leer_tabla_bytes(f.filename,z.read(f)))
    else:
        tablas=[leer_tabla_bytes(nombre,contenido)]
    preparados=[]
    for df in tablas:
        cols={canon(c):c for c in df.columns}
        def col(name,default=None):
            return df[cols[name]] if name in cols else default
        if not set(["latitude","longitude"]).issubset(cols):
            continue
        fecha=col("acq_date",col("fecha"))
        if fecha is None:
            continue
        out=pd.DataFrame({
            "fecha":fecha.astype(str),
            "latitude":pd.to_numeric(col("latitude"),errors="coerce"),
            "longitude":pd.to_numeric(col("longitude"),errors="coerce"),
            "instrumento":col("instrument",pd.Series("NASA FIRMS",index=df.index)).fillna("NASA FIRMS").astype(str),
            "acq_time":col("acq_time",pd.Series("",index=df.index)).fillna("").astype(str),
        })
        satellite=col("satellite",pd.Series("",index=df.index)).fillna("").astype(str)
        ids=(out.fecha+"|"+out.latitude.astype(str)+"|"+out.longitude.astype(str)+"|"+
             satellite+"|"+out.acq_time+"|"+out.instrumento)
        out["id_registro"]=ids.map(lambda x:hashlib.sha256(x.encode()).hexdigest()[:24])
        preparados.append(out)
    if not preparados:
        raise ValueError("NASA FIRMS: latitude, longitude and acq_date/fecha columns were not found.")
    return pd.concat(preparados,ignore_index=True)


def parsear_hora(v: object) -> str | None:
    if v is None or pd.isna(v):
        return None
    s = str(v).strip().replace(".0", "")
    if not s:
        return None
    if re.fullmatch(r"\d{1,4}", s):
        s = s.zfill(4)
        h, m = int(s[:2]), int(s[2:])
        return f"{h:02d}:{m:02d}" if h < 24 and m < 60 else None
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", s)
    if match and int(match[1]) < 24 and int(match[2]) < 60:
        return f"{int(match[1]):02d}:{int(match[2]):02d}"
    return None


def fecha_hora(v: object, hora: object | None = None, origen_tz: str = "America/Montevideo") -> tuple[pd.Timestamp | pd.NaT, bool]:
    """UTC + date-only flag. It does not fabricate time precision."""
    if v is None or pd.isna(v) or not str(v).strip():
        return pd.NaT, True
    s = str(v).strip()
    es_dia = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}", s))
    hh = parsear_hora(hora)
    if es_dia and hh:
        s = f"{s} {hh}"
        es_dia = False
    try:
        dt = pd.to_datetime(s, dayfirst=bool(re.match(r"\d{1,2}/", s)), errors="coerce")
        if pd.isna(dt):
            return pd.NaT, es_dia
        dt = pd.Timestamp(dt)
        if dt.tzinfo is None:
            dt = dt.tz_localize(origen_tz, ambiguous="NaT", nonexistent="NaT")
        return dt.tz_convert("UTC"), es_dia
    except (ValueError, TypeError):
        return pd.NaT, es_dia


def extraer_wkt_point(v: object) -> tuple[float, float]:
    if pd.isna(v):
        return float("nan"), float("nan")
    m = re.search(r"POINT\s*(?:Z\s*)?\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", str(v), re.I)
    if not m:
        return float("nan"), float("nan")
    return float(m[2]), float(m[1])  # lat, lon


def adaptar_externo(raw: pd.DataFrame, categoria: str, columnas: dict[str, str | None],
                     origen_tz: str = "America/Montevideo") -> tuple[pd.DataFrame, dict]:
    """Universal adapter. Avoids attributing unconfirmed fields to Firefighters."""
    if categoria not in ("BOMBEROS_PAIF", "SINAE_MIRA"):
        raise ValueError("Incorrect source category.")
    if not columnas.get("fecha"):
        raise ValueError("Choose the date column to enable the cross-check.")
    df = raw.copy()
    lat_col, lon_col = columnas.get("lat"), columnas.get("lon")
    if lat_col and lon_col:
        lat = pd.to_numeric(df[lat_col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        lon = pd.to_numeric(df[lon_col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    elif columnas.get("wkt"):
        pares = df[columnas["wkt"]].map(extraer_wkt_point)
        lat = pares.map(lambda t: t[0])
        lon = pares.map(lambda t: t[1])
    else:
        raise ValueError("Select latitude and longitude (WGS84) or a WKT POINT column.")
    result = []
    for i, (idx, row) in enumerate(df.iterrows()):
        f, es_dia = fecha_hora(row[columnas["fecha"]],
                             row[columnas["hora"]] if columnas.get("hora") else None,
                             origen_tz)
        def valor(n: str, default: str = "") -> str:
            col = columnas.get(n)
            if not col:
                return default
            x = row[col]
            return default if pd.isna(x) else str(x).strip()[:500]
        result.append({
            "id": valor("id", f"{categoria}_{i+1:05d}"),
            "fecha_utc": f,
            "solo_fecha": bool(es_dia),
            "lat": float(lat.loc[idx]) if pd.notna(lat.loc[idx]) else np.nan,
            "lon": float(lon.loc[idx]) if pd.notna(lon.loc[idx]) else np.nan,
            "categoria": categoria,
            "detalle": valor("detalle"),
            "estado_origen": valor("estado", "Unspecified"),
            "fuente_decl": valor("origen", categoria),
            "es_simulado": any("SIMULAD" in t.upper() or "SINTETIC" in t.upper()
                                for t in (valor("id"),valor("estado"),valor("origen"))),
        })
    out = pd.DataFrame(result)
    n_initial = len(out)
    out = out.dropna(subset=["fecha_utc", "lat", "lon"]).copy()
    out = out[out.lat.between(BBOX_UY[0], BBOX_UY[1]) &
              out.lon.between(BBOX_UY[2], BBOX_UY[3])]
    out = out.drop_duplicates(subset=["categoria", "id", "fecha_utc", "lat", "lon"])
    out = forzar_fechas_utc(out, categoria)
    return out.reset_index(drop=True), {"leidos": n_initial, "validos": len(out), "omitidos": n_initial-len(out)}


def normalizar_nasa(maestro: pd.DataFrame | None) -> pd.DataFrame:
    columnas = ["id", "fecha_utc", "solo_fecha", "lat", "lon", "instrumento", "fecha_local"]
    if maestro is None or maestro.empty:
        return pd.DataFrame(columns=columnas)
    df = maestro.copy()
    faltan = set(["fecha", "latitude", "longitude"]) - set(df.columns)
    if faltan:
        raise ValueError("The Master lacks expected columns: " + ", ".join(sorted(faltan)))
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    salida = pd.DataFrame({
        "id": df["id_registro"].astype(str) if "id_registro" in df else [f"FIRMS_{i}" for i in range(len(df))],
        "lat": lat,
        "lon": lon,
        "instrumento": df["instrumento"].fillna("NASA FIRMS").astype(str) if "instrumento" in df else "NASA FIRMS",
    })
    # Vectorized processing: 17,946 records in a fraction of a second.
    fechas_texto = df["fecha"].astype(str).str.strip()
    if "acq_time" in df.columns:
        horas_raw = df["acq_time"].fillna("").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        horas = horas_raw.str.zfill(4)
        validas = horas.str.fullmatch(r"(?:[01]\d|2[0-3])[0-5]\d")
    else:
        horas = pd.Series("0000",index=df.index)
        validas = pd.Series(False,index=df.index)
    texto_horas = horas.str.slice(0,2) + ":" + horas.str.slice(2,4)
    sin_hora = ~validas.fillna(False)
    marcas = pd.to_datetime(fechas_texto + " " + texto_horas.where(~sin_hora, "00:00"),
                            format="%Y-%m-%d %H:%M",errors="coerce",utc=True)
    salida["fecha_utc"] = marcas
    salida["solo_fecha"] = sin_hora.to_numpy(dtype=bool)
    salida = salida.dropna(subset=["fecha_utc", "lat", "lon"])
    salida = salida[salida.lat.between(BBOX_UY[0], BBOX_UY[1]) &
                    salida.lon.between(BBOX_UY[2], BBOX_UY[3])].copy()
    salida = forzar_fechas_utc(salida, "NASA FIRMS")
    salida["fecha_local"] = salida["fecha_utc"].dt.tz_convert("America/Montevideo").dt.date
    return salida[columnas].reset_index(drop=True)


def forzar_fechas_utc(df: pd.DataFrame, etiqueta: str) -> pd.DataFrame:
    """Forces UTC dates with datetime dtype even if pandas received objects.

    Needed to avoid `.dt` errors when concatenating DataFrames from
    different origins and types in newer pandas/Streamlit Cloud versions.
    It does not invent dates or times: impossible rows are excluded.
    """
    if df is None or df.empty:
        return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    if "fecha_utc" not in df:
        raise ValueError(f"{etiqueta}: the fecha_utc column is missing")
    salida = df.copy()
    try:
        fechas = pd.to_datetime(salida["fecha_utc"], utc=True,
                                errors="coerce", format="mixed")
    except (TypeError, ValueError):
        fechas = pd.to_datetime(salida["fecha_utc"], utc=True, errors="coerce")
    salida["fecha_utc"] = fechas
    salida = salida.dropna(subset=["fecha_utc"]).copy()
    if not salida.empty and "fecha_local" in salida:
        salida["fecha_local"] = salida["fecha_utc"].dt.tz_convert("America/Montevideo").dt.date
    return salida


def haversine_vector(lat: float, lon: float, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Distance in km, spherical Earth; enough for exploratory preselection."""
    r = 6371.0088
    a1, o1 = np.deg2rad(lat), np.deg2rad(lon)
    a2, o2 = np.deg2rad(lats), np.deg2rad(lons)
    z = np.sin((a2-a1)/2)**2 + np.cos(a1)*np.cos(a2)*np.sin((o2-o1)/2)**2
    return 2*r*np.arcsin(np.sqrt(np.clip(z, 0, 1)))


def buscar_asociaciones(fuentes: pd.DataFrame, candidatos: pd.DataFrame,
                        radio_km: float, ventana_h: float, ventana_dias_sin_hora: int = 0,
                        excluir_mismo_id: bool = False) -> dict[int, dict]:
    """Returns, per source record index, its candidates within the threshold.

    Date only: compare LOCAL DAY, without claiming a match in minutes.
    With time: compare the UTC instant, without using historical data as a predictor.
    """
    result = {}
    if fuentes.empty or candidatos.empty:
        return result
    # The DataFrame may carry dates as object after a concatenation
    # (especially with recent pandas). Convert them explicitly to UTC.
    fuentes = forzar_fechas_utc(fuentes, "origins").copy()
    c = forzar_fechas_utc(candidatos, "candidatos").copy()
    if fuentes.empty or c.empty:
        return result
    c["fecha_local"] = c["fecha_utc"].dt.tz_convert("America/Montevideo").dt.date
    by_day = {k: d for k,d in c.groupby("fecha_local", sort=False)}
    for idx, fila in fuentes.iterrows():
        f = pd.Timestamp(fila["fecha_utc"])
        local = f.tz_convert("America/Montevideo").date()
        # Even for timed detections, cover local day changes.
        dias = 1 + int(math.ceil(ventana_h/24))
        pool = []
        for offset in range(-dias-ventana_dias_sin_hora, dias+ventana_dias_sin_hora+1):
            d = local + timedelta(days=offset)
            if d in by_day:
                pool.append(by_day[d])
        if not pool:
            continue
        sub = pd.concat(pool)
        if excluir_mismo_id:
            sub = sub[sub.id.astype(str) != str(fila["id"])]
        if sub.empty:
            continue
        dist = haversine_vector(float(fila["lat"]), float(fila["lon"]),
                               sub.lat.to_numpy(dtype=float), sub.lon.to_numpy(dtype=float))
        en_espacio = dist <= radio_km
        if not np.any(en_espacio):
            continue
        sub = sub.loc[en_espacio].copy()
        sub["km"] = dist[en_espacio]
        sub["delta_min"] = np.abs((sub.fecha_utc-f).dt.total_seconds()/60)
        fila_dia = bool(fila["solo_fecha"])
        candidato_dia = sub.solo_fecha.to_numpy(dtype=bool)
        # If either date has no time, require a local-day match.
        hay_hora = ~candidato_dia & ~fila_dia
        misma_fecha = (sub.fecha_local.to_numpy() == local)
        if ventana_dias_sin_hora:
            same_days = np.array([abs((d-local).days) <= ventana_dias_sin_hora for d in sub.fecha_local])
        else:
            same_days = misma_fecha
        valida = np.where(hay_hora, sub.delta_min.to_numpy() <= ventana_h*60, same_days)
        sub = sub.loc[valida].sort_values(["km", "delta_min"])
        if sub.empty:
            continue
        result[idx] = {
            "n": len(sub), "mejor_id": str(sub.iloc[0]["id"]),
            "dist_km": float(sub.iloc[0]["km"]),
            "delta_min": (float(sub.iloc[0]["delta_min"])
                          if not fila_dia and not bool(sub.iloc[0]["solo_fecha"]) else np.nan),
            "precision": ("day match (time unknown)"
                          if fila_dia or bool(sub.iloc[0]["solo_fecha"]) else "UTC time"),
            "ids": sub.id.astype(str).tolist()[:20],
            "instrumentos": ", ".join(sorted(sub.instrumento.unique())) if "instrumento" in sub else "",
        }
    return result


def fusionar(nasa: pd.DataFrame, bomberos: pd.DataFrame, sinae: pd.DataFrame,
             radio_km: float = 10.0, ventana_h: float = 24.0,
             dias_sin_hora: int = 0) -> pd.DataFrame:
    """One row per external record, not per unique fire.

    Kept with a Firefighters event that links SINAE and NASA; linked SINAE
    rows are not duplicated as standalone events.
    """
    salidas=[]
    b = forzar_fechas_utc(bomberos, "Firefighters/PAIF").reset_index(drop=True)
    s = forzar_fechas_utc(sinae, "SINAE/MIRA").reset_index(drop=True)
    nasa = forzar_fechas_utc(nasa, "NASA FIRMS").reset_index(drop=True)
    x = pd.concat([b,s],ignore_index=True) if len(b)+len(s) else pd.DataFrame()
    if not x.empty:
        x = forzar_fechas_utc(x, "combined events").reset_index(drop=True)
    if x.empty:
        return pd.DataFrame(columns=["id_evento","fuentes","fecha_utc","lat","lon","resultado",
                                     "n_firms","n_sinae","distancia_km","minutos","precision",
                                     "instrumentos","detalle","estado_origen","simulado"])
    matches_firms = buscar_asociaciones(x,nasa,radio_km,ventana_h,dias_sin_hora)
    matches_sinae = buscar_asociaciones(b,s,radio_km,ventana_h,dias_sin_hora)
    used_sinae=set()
    for i, r in x.iterrows():
        b_row = i < len(b)
        match_s = matches_sinae.get(i) if b_row else None
        if match_s:
            used_sinae.update(match_s["ids"])
        if not b_row and str(r["id"]) in used_sinae:
            continue
        sat = matches_firms.get(i)
        ns = match_s["n"] if match_s else 0
        es_s = (r["categoria"] == "SINAE_MIRA")
        if sat and (ns or (es_s and len(b)>0 and any(str(r["id"]) in v["ids"] for v in matches_sinae.values()))):
            estado = "NASA + ground + SINAE (review)"
        elif sat:
            estado = "NASA + " + ("SINAE (review)" if es_s else "ground (review)")
        elif ns:
            estado = "Ground + SINAE, no FIRMS"
        else:
            estado = "SINAE with no nearby FIRMS" if es_s else "Ground with no nearby FIRMS"
        fuentes = {"SINAE/MIRA"} if es_s else {"Firefighters/PAIF"}
        if ns:
            fuentes.add("SINAE/MIRA")
        if sat:
            fuentes.add("NASA FIRMS")
        salidas.append({
            "id_evento":str(r["id"]), "fuentes":" + ".join(sorted(fuentes)),
            "fecha_utc":str(r["fecha_utc"]),"lat":round(float(r["lat"]),5),
            "lon":round(float(r["lon"]),5), "resultado":estado,
            "n_firms":int(sat["n"]) if sat else 0, "n_sinae":int(ns),
            "distancia_km":round(sat["dist_km"],2) if sat else np.nan,
            "minutos":round(sat["delta_min"],1) if sat and pd.notna(sat["delta_min"]) else np.nan,
            "precision":sat["precision"] if sat else ("date without time" if r["solo_fecha"] else "with time"),
            "instrumentos":sat["instrumentos"] if sat else "",
            "detalle":str(r["detalle"]), "estado_origen":str(r["estado_origen"]),
            "simulado":"YES — DO NOT USE AS EVIDENCE" if bool(r.get("es_simulado",False)) else "No",
        })
    return pd.DataFrame(salidas)


def demo_sintetica(nasa: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Test data, ALWAYS labelled as fictitious; it does not endorse effectiveness."""
    if nasa.empty:
        # Without a Master, show upload capability; do NOT invent a coincidence.
        return pd.DataFrame(),pd.DataFrame()
    post2018 = nasa[nasa.fecha_utc.dt.year >= 2018]
    sat = post2018.iloc[0] if not post2018.empty else nasa.iloc[0]
    f = pd.Timestamp(sat["fecha_utc"])
    fake1={"id":"SIMULADO_CAMARA_001","fecha_utc":f+pd.Timedelta(minutes=15),
           "solo_fecha":False,"lat":float(sat.lat)+0.006,"lon":float(sat.lon)+0.005,
           "categoria":"BOMBEROS_PAIF","detalle":"SIMULATION: camera detects possible smoke",
           "estado_origen":"SIMULATED — unverified", "fuente_decl":"SIMULATED", "es_simulado":True}
    fake2={"id":"SIMULADO_SINAE_001","fecha_utc":f+pd.Timedelta(minutes=23),
           "solo_fecha":False,"lat":float(sat.lat)+0.007,"lon":float(sat.lon)+0.005,
           "categoria":"SINAE_MIRA","detalle":"SIMULATION: event report (made up)",
           "estado_origen":"SIMULATED — unverified", "fuente_decl":"SIMULATED", "es_simulado":True}
    return pd.DataFrame([fake1]),pd.DataFrame([fake2])


def tabla_ejemplo(tipo: str) -> bytes:
    # Structure examples, not real incidents or institutional data.
    if tipo == "terrestre":
        datos=[dict(evento_id="SIMULADO_CAMARA_001",fecha_utc="2026-01-12T15:45:00Z",
                    latitud=-34.75,longitud=-55.70,fuente="EJEMPLO_SINTETICO_NO_REAL",
                    tipo_deteccion="posible_humo",estado="pendiente_revision")]
    else:
        datos=[dict(evento_id="SIMULADO_SINAE_001",fecha_utc="2026-01-12",
                    latitud=-34.75,longitud=-55.70,fuente="EJEMPLO_SINTETICO_NO_REAL",
                    tipo_incendio="no_determinado",estado="ejemplo")]
    return pd.DataFrame(datos).to_csv(index=False).encode("utf-8-sig")


def dibujar_mapa(nasa: pd.DataFrame, bom: pd.DataFrame, sin: pd.DataFrame,
                 resultados: pd.DataFrame) -> str:
    import folium
    mapa = folium.Map(location=[-32.95,-56.25], zoom_start=6, tiles="CartoDB dark_matter",control_scale=True)
    # Historical context: year-cell of 0.2 degrees (not confirmed fire points).
    if not nasa.empty:
        g=nasa.copy()
        g["ano"] = g.fecha_utc.dt.year
        g["ilat"] = np.floor(g.lat / 0.2).astype(int)
        g["ilon"] = np.floor(g.lon / 0.2).astype(int)
        r=g.groupby(["ilat","ilon"]).ano.nunique().sort_values(ascending=False)
        layer=folium.FeatureGroup(name="FIRMS historical recurrence (cells)",show=True)
        for (il,io),n in r.head(550).items():
            if n < 3:
                continue
            color=("#ff995f" if n>=18 else "#ebca75" if n>=11 else
                   "#67d5c4" if n>=6 else "#479bad")
            folium.Rectangle([[il*.2,io*.2],[(il+1)*.2,(io+1)*.2]],
                             fill=True,fill_color=color,fill_opacity=.53,
                             color=color,weight=0.4,
                             tooltip=f"{n} years with NASA FIRMS observation in a 0.2° cell").add_to(layer)
        layer.add_to(mapa)
    for df,color,title in ((bom,"#ffbe6d","Uploaded ground detection"),
                           (sin,"#6bd2fa","Uploaded SINAE/MIRA record")):
        if df.empty:
            continue
        layer=folium.FeatureGroup(name=f"{title} ({len(df)})",show=True)
        for _, r in df.head(500).iterrows():
            texto=(f"{escape(title)}<br>ID: {escape(str(r['id']))}<br>"
                   f"Date: {escape(str(r['fecha_utc']))}<br>"
                   f"Type: {escape(str(r['detalle']))}<br>"
                   f"Original status: {escape(str(r['estado_origen']))}")
            folium.CircleMarker([float(r.lat),float(r.lon)],radius=6,color=color,
                                fill=True,fill_color=color,fill_opacity=.90,
                                tooltip=f"{title} · {r['id']}",popup=folium.Popup(texto,max_width=330)).add_to(layer)
        layer.add_to(mapa)
    if not resultados.empty:
        layer=folium.FeatureGroup(name="Coincidences for review",show=True)
        for _,r in resultados[resultados.n_firms>0].head(300).iterrows():
            texto=escape(str(r.resultado))+'<br>Nearby FIRMS: '+str(r.n_firms)
            folium.CircleMarker([r.lat,r.lon],radius=11,weight=2,color="#f9e77d",
                                fill=False,tooltip=texto,popup=texto).add_to(layer)
        layer.add_to(mapa)
    # Do not plot camera positions or coverage limits that are not officially recorded.
    folium.LayerControl(collapsed=False).add_to(mapa)
    return mapa.get_root().render()




# ---------------------------------------------------------------------------
# MAP INTERFACE V2 — A single isolated module; the rest of IGNIS is not modified.
# ---------------------------------------------------------------------------

PASO_GRADOS = 0.2
CASOS_DOCUMENTADOS = [
    {"nombre":"Algorta / Orgoroso · coastal-west episode 2021–2022",
     "lat":-32.4222, "lon":-57.3922, "inicio":"2021-12-29", "fin":"2022-01-05",
     "fuente":"SINAE", "url":"https://www.gub.uy/sistema-nacional-emergencias/comunicacion/comunicados/informe-situacion-incendios-forestales-31-12-2021"},
    {"nombre":"Algorta · new episode 2023",
     "lat":-32.4222,"lon":-57.3922,"inicio":"2023-01-04","fin":"2023-01-05",
     "fuente":"SINAE", "url":"https://www.gub.uy/sistema-nacional-emergencias/comunicacion/noticias/informe-situacion-sobre-incendio-forestal-rio-negro"},
    {"nombre":"La Esmeralda, Rocha · 2005",
     "lat":-34.1575,"lon":-53.6931,"inicio":"2005-01-17","fin":"2005-01-25",
     "fuente":"SINAE", "url":"https://www.gub.uy/sistema-nacional-emergencias/comunicacion/publicaciones/incendios"},
    {"nombre":"La Esmeralda, Rocha · 2019",
     "lat":-34.1575,"lon":-53.6931,"inicio":"2019-12-10","fin":"2019-12-17",
     "fuente":"SINAE", "url":"https://www.gub.uy/sistema-nacional-emergencias/comunicacion/noticias/eventos-adversos-significativos-ocurridos-uruguay-entre-anos-2015-2019"},
    {"nombre":"Fortín de Santa Rosa · 2021–2022 season",
     "lat":-34.7719,"lon":-55.8056,"inicio":"2021-12-29","fin":"2022-01-03",
     "fuente":"SINAE", "url":"https://www.gub.uy/sistema-nacional-emergencias/comunicacion/comunicados/informe-situacion-incendios-forestales-31-12-2021"},
]
# ONLY approximate centers of localities named in communications / tender.
# They are NOT equivalent to the positions of the installed cameras or towers!
REFERENCIAS_CAMARAS = [
    {"nombre":"Santa Ana, Colonia", "lat":-34.4214,"lon":-57.5935,
     "nota":"Locality cited by the Ministry of the Interior; camera position unverified"},
    {"nombre":"Boca del Cufré, San José", "lat":-34.456,"lon":-57.111,
     "nota":"Cufré area cited by the Ministry of the Interior; camera position unverified"},
    {"nombre":"Parque del Plata, Canelones", "lat":-34.7560,"lon":-55.7226,
     "nota":"Locality mentioned in tender documentation; installation unverified"},
    {"nombre":"Punta Ballena, Maldonado", "lat":-34.8889,"lon":-55.0406,
     "nota":"Locality cited by the Ministry of the Interior; camera position unverified"},
]
ZONAS = {
    "All of Uruguay": (-35.28,-29.90,-58.70,-53.00),
    "Western coast · approximate area":(-34.0,-30.65,-58.70,-56.65),
    "Center · approximate area":(-34.3,-31.3,-57.55,-54.9),
    "South and east coast · approximate area":(-35.28,-33.35,-58.7,-53.0),
    "North · approximate area":(-32.0,-29.90,-58.65,-53.35),
}


def _normalizar_gps_uy(df: pd.DataFrame, lat_col="lat", lon_col="lon") -> pd.DataFrame:
    if df is None or df.empty:
        return df.copy() if isinstance(df,pd.DataFrame) else pd.DataFrame()
    out=df.copy()
    out[lat_col]=pd.to_numeric(out[lat_col],errors="coerce")
    out[lon_col]=pd.to_numeric(out[lon_col],errors="coerce")
    out=out.dropna(subset=[lat_col,lon_col])
    return out.loc[out[lat_col].between(BBOX_UY[0],BBOX_UY[1]) &
                   out[lon_col].between(BBOX_UY[2],BBOX_UY[3])].copy()


def _recortar(df: pd.DataFrame, zona: str, lat="lat",lon="lon") -> pd.DataFrame:
    if df is None or df.empty:return df.copy() if isinstance(df,pd.DataFrame) else pd.DataFrame()
    a,b,c,d=ZONAS[zona]
    return df.loc[df[lat].between(a,b)&df[lon].between(c,d)].copy()


def _contorno_uy() -> list[tuple[float,float]]:
    # Real file from the IGNIS repository; only a low-resolution national outline.
    p=Path(__file__).resolve().parent/'uruguay_contorno.geojson'
    if p.exists():
        try:
            data=json.loads(p.read_text(encoding="utf-8"))
            coords=data['features'][0]['geometry']['coordinates'][0]
            return [(float(x),float(y)) for x,y in coords]
        except (KeyError,IndexError,ValueError,TypeError, OSError):
            pass
    # Fallback of the same simplified outline included in the repository.
    return [(-57.62513342958296, -30.21629485445426), (-56.976025763564735, -30.109686374636127), (-55.97324459494094, -30.883075860316303), (-55.601510179249345, -30.853878676071393), (-54.57245154480512, -31.494511407193748), (-53.78795162618219, -32.047242526987624), (-53.209588995971544, -32.727666110974724), (-53.6505439927181, -33.20200408298183), (-53.373661668498244, -33.768377780900764), (-53.806425950726535, -34.39681487400223), (-54.93586605489773, -34.952646579733624), (-55.67408972840329, -34.75265878676407), (-56.21529700379607, -34.85983570733742), (-57.1396850246331, -34.430456231424245), (-57.81786068381551, -34.4625472958775), (-58.42707414410439, -33.909454441057576), (-58.349611172098875, -33.26318897881541), (-58.13264767112145, -33.040566908502015), (-58.14244035504076, -32.044503676076154), (-57.87493730328188, -31.016556084926208), (-57.62513342958296, -30.21629485445426)]


def _contiene_punto(lon:float, lat:float, poligono:list[tuple[float,float]]) -> bool:
    # Ray casting independent of shapely. Simplified outline = approximation.
    if not poligono:return True
    dentro=False
    for i in range(len(poligono)-1):
        x1,y1=poligono[i];x2,y2=poligono[i+1]
        if (y1>lat)!=(y2>lat):
            xcr=x1+(lat-y1)*(x2-x1)/(y2-y1)
            if lon<xcr:dentro=not dentro
    return dentro


def _crear_malla(nasa:pd.DataFrame) -> pd.DataFrame:
    cols=["ilat","ilon","lat_c","lon_c","registros","anios","dias","primer_ano","ultimo_ano","sensores"]
    if nasa is None or nasa.empty:return pd.DataFrame(columns=cols)
    d=forzar_fechas_utc(nasa,"NASA malla").copy()
    if d.empty:return pd.DataFrame(columns=cols)
    d['anio']=d['fecha_utc'].dt.year
    d['dia']=d['fecha_utc'].dt.date
    d['ilat']=np.floor(d['lat'].astype(float)/PASO_GRADOS).astype(int)
    d['ilon']=np.floor(d['lon'].astype(float)/PASO_GRADOS).astype(int)
    g=d.groupby(['ilat','ilon'],observed=True).agg(
        registros=('id','count'),anios=('anio','nunique'),dias=('dia','nunique'),
        primer_ano=('anio','min'),ultimo_ano=('anio','max'),
        sensores=('instrumento',lambda x:", ".join(sorted(set(x.astype(str)))))
    ).reset_index()
    g['lat_c']=(g.ilat+0.5)*PASO_GRADOS
    g['lon_c']=(g.ilon+0.5)*PASO_GRADOS
    # Se evita pintar celdas fuera del contorno nacional simplificado.
    polygon=_contorno_uy()
    if polygon:
        validos=[_contiene_punto(float(r.lon_c),float(r.lat_c),polygon) for r in g.itertuples()]
        g=g.loc[validos].copy()
    return g.sort_values(['anios','registros'],ascending=False).reset_index(drop=True)[cols]


def _paleta(n:int) -> str:
    if n>=18:return "#f48b5a"
    if n>=11:return "#e1bf73"
    if n>=6:return "#62c9bb"
    if n>=3:return "#458fa6"
    return "#24516a"


def _mapa_plotly(malla:pd.DataFrame, nasa:pd.DataFrame, bom:pd.DataFrame,
                  sin:pd.DataFrame, zona:str, ano:int|None,
                  ver_referencias:bool=True,ver_casos:bool=True,
                  celdas_activas:set|None=None, celda_seleccionada:tuple[int,int]|None=None):
    import plotly.graph_objects as go
    figura=go.Figure()
    geo=_contorno_uy()
    if geo:
        figura.add_trace(go.Scatter(
            x=[x for x,y in geo], y=[y for x,y in geo],mode='lines',
            fill='toself',fillcolor='rgba(26,48,70,.50)',
            line=dict(color='#c7e7fa',width=2),name='Simplified outline',hoverinfo='skip',
            showlegend=False))
    else:
        figura.add_trace(go.Scatter(x=[],y=[],mode='lines',showlegend=False))
    if not malla.empty:
        m=malla.sort_values(['ilon','ilat']).reset_index(drop=True)
        activas=(set() if celdas_activas is None else celdas_activas)
        bordes=['#ffed97' if (int(r.ilat),int(r.ilon)) in activas else 'rgba(4,17,30,.5)' for r in m.itertuples()]
        hover=(m['anios'].astype(str)+' years with FIRMS detections<br>'+
               m['registros'].astype(str)+' records in the cell<br>'+
               'Center: '+m['lat_c'].round(2).astype(str)+'°, '+m['lon_c'].round(2).astype(str)+'°<br>'+
               'Click to inspect')
        figura.add_trace(go.Scatter(
            x=m['lon_c'],y=m['lat_c'],mode='markers',name='FIRMS cells',
            marker=dict(symbol='square',size=23,color=[_paleta(int(v)) for v in m.anios],
                        line=dict(color=bordes,width=1.2 if celdas_activas is not None else 0.6),opacity=.96),
            customdata=np.array(m[['ilat','ilon']].values,object),
            text=hover,hovertemplate='%{text}<extra></extra>',showlegend=False))
    else:
        figura.add_trace(go.Scatter(x=[],y=[],mode='markers',name='FIRMS cells',showlegend=False))
    if celda_seleccionada is not None:
        il,jo=celda_seleccionada
        x0,x1=jo*PASO_GRADOS,(jo+1)*PASO_GRADOS
        y0,y1=il*PASO_GRADOS,(il+1)*PASO_GRADOS
        figura.add_trace(go.Scatter(x=[x0,x1,x1,x0,x0],y=[y0,y0,y1,y1,y0],
                    mode='lines',line=dict(color='#ffe36f',width=3.7),
                    hoverinfo='skip',showlegend=False,name='Selected grid cell'))
    if ver_referencias:
        ref=[r for r in REFERENCIAS_CAMARAS
             if ZONAS[zona][0]<=r['lat']<=ZONAS[zona][1] and ZONAS[zona][2]<=r['lon']<=ZONAS[zona][3]]
        if ref:
            figura.add_trace(go.Scatter(
                x=[x['lon'] for x in ref],y=[x['lat'] for x in ref],
                mode='markers',name='Reference localities, NOT towers',
                marker=dict(symbol='diamond-open',size=14,color='#4fc2ff',line=dict(width=2)),
                text=[f"{x['nombre']}<br>{x['nota']}" for x in ref],
                hovertemplate='%{text}<extra></extra>'))
    if ver_casos:
        cases=[x for x in CASOS_DOCUMENTADOS if
               ZONAS[zona][0]<=x['lat']<=ZONAS[zona][1] and
               ZONAS[zona][2]<=x['lon']<=ZONAS[zona][3] and
               (ano is None or int(x['inicio'][:4])<=ano<=int(x['fin'][:4]))]
        if cases:
            figura.add_trace(go.Scatter(
                x=[c['lon'] for c in cases],y=[c['lat'] for c in cases],
                mode='markers', name='Documented fire locality',
                marker=dict(symbol='circle-open',size=17,color='#ff8aa5',line=dict(width=2.5)),
                text=[c['nombre']+'<br>'+c['inicio']+' to '+c['fin']+
                      '<br>Locality position, NOT the exact fire point' for c in cases],
                hovertemplate='%{text}<extra></extra>'))
    for d,color,name in ((bom,'#ffbd60','Uploaded ground'),(sin,'#f17ce2','Uploaded SINAE')):
        if d is not None and not d.empty:
            d=d.head(1000)
            figura.add_trace(go.Scatter(
                x=d['lon'],y=d['lat'],mode='markers',name=name,
                marker=dict(symbol='x',size=11,color=color,line=dict(width=2)),
                text=[f"{name} • {r.id}<br>{str(r.fecha_utc)}<br>{'SIMULATED' if r.es_simulado else 'Status to verify'}" for r in d.itertuples()],
                hovertemplate='%{text}<extra></extra>'))
    a,b,c,d=ZONAS[zona]
    figura.update_layout(
        paper_bgcolor='#081426',plot_bgcolor='#081426',font=dict(color='#e9f5ff',size=12),
        height=690,margin=dict(t=15,b=25,l=15,r=15),
        hovermode='closest',clickmode='event+select',
        legend=dict(x=.01,y=.01,xanchor='left',yanchor='bottom',bgcolor='rgba(8,21,38,.7)',font=dict(size=10)),
        xaxis=dict(range=[c-.05,d+.05],title='Longitude (°W)',gridcolor='#1c3348',zeroline=False,
                   scaleanchor='y',scaleratio=1),
        yaxis=dict(range=[a-.05,b+.05],title='Latitude (°S)',gridcolor='#1c3348',zeroline=False)
    )
    return figura


def _seleccion_de_grafico(evento:object) -> tuple[int,int]|None:
    try:
        seleccion=evento.get('selection',{}) if isinstance(evento,dict) else getattr(evento,'selection',{})
        puntos=seleccion.get('points',[]) if isinstance(seleccion,dict) else getattr(seleccion,'points',[])
        for punto in puntos:
            if int(punto.get('curve_number',-1))!=1:continue
            cd=punto.get('customdata')
            if cd is not None and len(cd)>=2:
                return (int(cd[0]),int(cd[1]))
    except (TypeError,ValueError,AttributeError,IndexError):
        pass
    return None


def _descripcion_celda(malla:pd.DataFrame,c:tuple[int,int]) -> str:
    m=malla[(malla.ilat==c[0])&(malla.ilon==c[1])]
    if m.empty:return str(c)
    r=m.iloc[0]
    return (f"{r.lat_c:.2f}°S, {abs(r.lon_c):.2f}°W · "
            f"{int(r.anios)} years · {int(r.registros)} observations")


def _interpretacion_celda(hist:pd.DataFrame, b:pd.DataFrame, s:pd.DataFrame,
                           resultados:pd.DataFrame, sim:bool) -> str:
    if hist.empty:return 'There are no observations in the cell according to the loaded master.'
    anios=int(hist.fecha_utc.dt.year.nunique())
    partes=[f"The cell shows FIRMS thermal anomalies during {anios} different years of the included files."]
    if not b.empty:partes.append(f"{len(b)} ground records were uploaded in this cell.")
    if not s.empty:partes.append(f"{len(s)} SINAE records were uploaded in this cell.")
    if not resultados.empty and (resultados.n_firms>0).any():
        partes.append('The engine found at least one spatial and temporal proximity that must be reviewed; it does not confirm a fire.')
    elif not b.empty or not s.empty:
        partes.append('The absence of a coincidence under the current filters does not prove the detection is false.')
    if sim:partes.append('IMPORTANT: part of the ground/institutional evidence is SIMULATED.')
    partes.append('Counts are not corrected for revisits, cloud cover or MODIS–VIIRS differences.')
    return ' '.join(partes)


def _configuracion_automatica(st, raw:pd.DataFrame,prefijo:str, nombre:str) -> dict[str,str|None]:
    cols=list(raw.columns)
    config={key:encontrar_columna(cols,key) for key in ('fecha','hora','lat','lon','wkt','id','detalle','estado','origen')}
    if '__geo_lat' in cols: config['lat']='__geo_lat'
    if '__geo_lon' in cols: config['lon']='__geo_lon'
    auto=bool(config['fecha'] and ((config['lat'] and config['lon']) or config['wkt']))
    if auto:
        st.success(f"{nombre}: date and location columns recognized automatically.")
    else:
        st.warning(f"{nombre}: some fields still need identifying. Open “Adjust columns”.")
    with st.expander(f"Adjust {nombre} columns (optional if the green notice appears)",expanded=not auto):
        opciones=['— Not available —']+cols
        etiquetas={"fecha":"Date / date and time", "hora":"Separate time", "lat":"Latitude WGS84", "lon":"Longitude WGS84",
                  "wkt":"Alternative WKT POINT geometry", "id":"Event ID",
                  "detalle":"Type / description", "estado":"Observation status", "origen":"Organization or provenance"}
        for k in ('fecha','hora','lat','lon','wkt','id','detalle','estado','origen'):
            pred=config.get(k)
            o=st.selectbox(etiquetas[k],opciones,index=opciones.index(pred) if pred in opciones else 0,
                           key=f"fus_v2_map_{prefijo}_{k}")
            config[k]=None if o==opciones[0] else o
    return config


def _leer_fuente(st, uploaded, categoria:str,prefijo:str) -> pd.DataFrame:
    if uploaded is None:return pd.DataFrame()
    try:
        raw=leer_tabla_bytes(uploaded.name,uploaded.getvalue())
        cols=_configuracion_automatica(st,raw,prefijo,categoria.replace('_',' / '))
        tz_sugerido='UTC' if cols['fecha'] and 'utc' in canon(cols['fecha']) else 'America/Montevideo'
        with st.expander(f"Date, provenance and controls for {categoria.replace('_',' / ')}"):
            tz=st.selectbox('Time zone if the file does not include an explicit zone',
                            ['America/Montevideo','UTC'],index=0 if tz_sugerido=='America/Montevideo' else 1,
                            key=f'fus_v2_tz_{prefijo}')
            marcado_auto=('simulad' in uploaded.name.lower() or 'sintet' in uploaded.name.lower())
            marcar=st.checkbox('Mark as SIMULATED (test data)',value=marcado_auto,
                               key=f'fus_v2_sim_{prefijo}')
        data,resumen=adaptar_externo(raw,categoria,cols,tz)
        if not data.empty and (marcar or marcado_auto):
            data['es_simulado']=True
            data['estado_origen']=data['estado_origen'].astype(str)+' · SIMULATED'
        if resumen['omitidos']:
            st.warning(f"{categoria}: {resumen['omitidos']} rows without a valid date or WGS84 position were excluded.")
        st.caption(f"{categoria}: {len(data)} valid records (out of {resumen['leidos']})")
        return data
    except Exception as exc:
        st.error(f"{categoria}: {type(exc).__name__}: {exc}")
        return pd.DataFrame()


# --------------------------- PDF per cell -------------------------------
def _mapa_estatico_para_pdf(malla: pd.DataFrame, celda: tuple[int, int],
                           bom: pd.DataFrame, sin: pd.DataFrame) -> bytes:
    """A reproducible figure; the grid color comes only from FIRMS."""
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    fig = Figure(figsize=(8, 4.4), facecolor='#09182b')
    ax = fig.add_axes([0.07, 0.10, 0.88, 0.82], facecolor='#09182b')
    geo = _contorno_uy()
    if geo:
        ax.fill([x for x, y in geo], [y for x, y in geo], color='#13263a', alpha=.9)
        ax.plot([x for x, y in geo], [y for x, y in geo], c='#b9d8ed', linewidth=1.2)
    for r in malla.itertuples():
        ax.add_patch(Rectangle((r.ilon*PASO_GRADOS, r.ilat*PASO_GRADOS),
                               PASO_GRADOS, PASO_GRADOS,
                               facecolor=_paleta(int(r.anios)), edgecolor='#102237', linewidth=.3))
    lat0, lon0 = celda[0]*PASO_GRADOS, celda[1]*PASO_GRADOS
    ax.add_patch(Rectangle((lon0, lat0), PASO_GRADOS, PASO_GRADOS,
                           facecolor='none', edgecolor='#ffe57b', linewidth=3))
    for d, color, label in [(bom, '#ffba63', 'Firefighters/PAIF'),
                             (sin, '#fb83d9', 'SINAE/MIRA')]:
        if d is not None and not d.empty:
            ax.scatter(d.lon, d.lat, c=color, s=27, marker='x', linewidth=1.2, label=label)
    ax.set_xlim(-58.85, -53.05)
    ax.set_ylim(-35.25, -29.90)
    ax.set_aspect('equal', adjustable='box')
    ax.tick_params(axis='both', colors='#c8e0ef', labelsize=7)
    ax.grid(color='#253b55', alpha=.40)
    for sp in ax.spines.values(): sp.set_color('#243e5b')
    ax.set_xlabel('Longitude (WGS84)', color='#b7d1e6', fontsize=7)
    ax.set_ylabel('Latitude (WGS84)', color='#b7d1e6', fontsize=7)
    if ax.get_legend_handles_labels()[0]:
        leg = ax.legend(facecolor='#183148', edgecolor='#49617a', fontsize=7,
                        loc='lower right')
        for txt in leg.get_texts(): txt.set_color('#ffffff')
    out=io.BytesIO()
    FigureCanvasAgg(fig).print_png(out)
    return out.getvalue()


def generar_informe_pdf_celda(malla: pd.DataFrame, celda: tuple[int,int],
                              nasa_hist: pd.DataFrame, nasa_periodo: pd.DataFrame,
                              bom_celda: pd.DataFrame, sin_celda: pd.DataFrame,
                              asociaciones: pd.DataFrame, casos: list,
                              ano_filtro: int|None, umbral_km: float,
                              umbral_h: float, dias: int,
                              bom_mapeado: pd.DataFrame|None=None,
                              sin_mapeado: pd.DataFrame|None=None) -> bytes:
    """Local report; no invented data and explicit provenance."""
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, Image as RLImage, PageBreak)
    from reportlab.lib import colors as C
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.utils import ImageReader

    LAT0, LAT1 = celda[0]*PASO_GRADOS, (celda[0]+1)*PASO_GRADOS
    LON0, LON1 = celda[1]*PASO_GRADOS, (celda[1]+1)*PASO_GRADOS
    zona_texto=f'{LAT0:.2f} to {LAT1:.2f} S / {LON0:.2f} to {LON1:.2f} W'
    partes=[]
    estilo=getSampleStyleSheet()
    estilo.add(ParagraphStyle(name='IGNISTitle', parent=estilo['Heading1'], fontName='Helvetica-Bold',
                              textColor=C.HexColor('#14283e'), fontSize=16, spaceAfter=8, leading=20))
    estilo.add(ParagraphStyle(name='IGNISH2', parent=estilo['Heading2'],fontName='Helvetica-Bold',
                              textColor=C.HexColor('#116b83'),fontSize=10.3, spaceBefore=10,spaceAfter=5))
    estilo.add(ParagraphStyle(name='IGNISSmall',parent=estilo['Normal'],fontSize=8,leading=11,spaceAfter=6))
    estilo.add(ParagraphStyle(name='IGNISNote',parent=estilo['Normal'],fontSize=7.3,leading=9,
                              textColor=C.HexColor('#5a6675'),spaceAfter=5))
    estilo.add(ParagraphStyle(name='IGNISCell',parent=estilo['Normal'],fontSize=7.1,leading=9))
    buf=io.BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=1.55*cm,leftMargin=1.55*cm,
                          topMargin=2.55*cm,bottomMargin=1.75*cm, title='IGNIS - Exploratory grid cell analysis')

    def pagina(c, doc_):
        w,h=A4
        c.setFillColor(C.HexColor('#10243c'))
        c.rect(0,h-1.75*cm,w,1.75*cm,fill=1,stroke=0)
        base=Path(__file__).resolve().parent
        logo_nasa=base/'logo_nasa_informe.png'
        if logo_nasa.exists():
            try: c.drawImage(ImageReader(str(logo_nasa)),w-3.55*cm,h-1.52*cm,
                             width=1.5*cm,height=1.22*cm,preserveAspectRatio=True,mask='auto')
            except (OSError,ValueError): pass
        logo_sinae=base/'logo_sinae.png'
        if logo_sinae.exists():
            try:c.drawImage(ImageReader(str(logo_sinae)),w-5.10*cm,h-1.48*cm,
                            width=1.4*cm,height=1.12*cm,preserveAspectRatio=True,mask='auto')
            except (OSError,ValueError):pass
        else:
            # The text name identifies the source; it is NOT an invented official logo.
            c.setFillColor(C.HexColor('#70cddb'));c.setFont('Helvetica-Bold',10)
            c.drawRightString(w-3.85*cm,h-1.00*cm,'SINAE / MIRA')
        c.setFillColor(C.white);c.setFont('Helvetica-Bold',12)
        c.drawString(1.55*cm,h-.86*cm,'IGNIS UY | SKY - GROUND FUSION')
        c.setFillColor(C.HexColor('#b3dbf0'));c.setFont('Helvetica',8)
        c.drawString(1.55*cm,h-1.24*cm,'Exploratory report for a selected cell')
        c.setStrokeColor(C.HexColor('#b6c7d9'));c.line(1.55*cm,1.36*cm,w-1.55*cm,1.36*cm)
        c.setFillColor(C.HexColor('#586678'));c.setFont('Helvetica',7)
        c.drawString(1.55*cm,1.05*cm,
                     'Names and emblems identify sources; they do not imply validation or institutional endorsement.')
        c.drawRightString(w-1.55*cm,1.05*cm,f'Page {doc_.page}')

    partes.append(Paragraph('Observation sheet and associated evidence',estilo['IGNISTitle']))
    periodo='Full history' if ano_filtro is None else str(ano_filtro)
    partes.append(Paragraph(f'<b>0.2-degree cell:</b> {zona_texto} &nbsp; | &nbsp; '
                             f'<b>Display period:</b> {periodo}',estilo['IGNISSmall']))
    simulado=bool((not bom_celda.empty and bom_celda.es_simulado.any()) or
                  (not sin_celda.empty and sin_celda.es_simulado.any()) or
                  (not asociaciones.empty and asociaciones.simulado.astype(str).str.startswith('YES').any()))
    if simulado:
        partes.append(Paragraph('<b>DEMONSTRATION WITH SYNTHETIC DATA.</b> '
                                 'The observed fusion does not confirm real ground detections.',estilo['IGNISSmall']))
    partes.append(Paragraph('1. Cell summary',estilo['IGNISH2']))
    def n(x):return f'{int(x):,}'
    resumen_data=[['FIRMS observations in the period','Years with FIRMS signal in the history','Days with FIRMS records'],
                  [n(len(nasa_periodo)),n(nasa_hist.fecha_utc.dt.year.nunique() if not nasa_hist.empty else 0),
                   n(nasa_hist.fecha_utc.dt.date.nunique() if not nasa_hist.empty else 0)]]
    t=Table(resumen_data,colWidths=[5.9*cm]*3,rowHeights=[.67*cm,.78*cm])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C.HexColor('#e9f3fa')),
                           ('TEXTCOLOR',(0,0),(-1,0),C.HexColor('#3c5265')),
                           ('TEXTCOLOR',(0,1),(-1,1),C.HexColor('#0a617e')),
                           ('FONTNAME',(0,1),(-1,1),'Helvetica-Bold'),
                           ('FONTSIZE',(0,0),(-1,0),8),('FONTSIZE',(0,1),(-1,1),16),
                           ('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                           ('BOX',(0,0),(-1,-1),.4,C.HexColor('#a8c0d1'))]))
    partes.append(t);partes.append(Spacer(1,9))
    partes.append(Paragraph('2. Historical map and selected location',estilo['IGNISH2']))
    graf=_mapa_estatico_para_pdf(malla,celda,bom_mapeado if bom_mapeado is not None else bom_celda,
                                 sin_mapeado if sin_mapeado is not None else sin_celda)
    partes.append(RLImage(io.BytesIO(graf),width=17.6*cm,height=9.65*cm))
    partes.append(Paragraph('Colors = calendar years with at least one thermal anomaly in the cell. '
                             'Counts not corrected for coverage, revisit, cloud cover or MODIS/VIIRS differences. '
                             'They do not represent the number of fires or burned areas.',estilo['IGNISNote']))
    partes.append(PageBreak())
    partes.append(Paragraph('3. Uploaded observations and cross-check',estilo['IGNISTitle']))
    def fuente_fila(nombre,df):
        if df is None or df.empty:return [nombre,'0','No records uploaded for the cell','—']
        yini,yfin=int(df.fecha_utc.dt.year.min()),int(df.fecha_utc.dt.year.max())
        return [nombre,n(len(df)),f'{yini}–{yfin}', 'Synthetic' if df.es_simulado.any() else 'Declared origin']
    rows=[['Source','Events in cell','Years of the events','Condition']]
    rows.extend([fuente_fila('Firefighters / PAIF',bom_celda),fuente_fila('SINAE / MIRA',sin_celda)])
    tt=Table([[Paragraph(str(x),estilo['IGNISCell']) for x in row] for row in rows],
              colWidths=[4.0*cm,2.9*cm,6.1*cm,4.7*cm],repeatRows=1)
    tt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),C.HexColor('#dceaf2')),
                            ('GRID',(0,0),(-1,-1),.3,C.HexColor('#b6cedb')),
                            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
                            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    partes.append(tt);partes.append(Spacer(1,7))
    # Coincidences in the cell, not results for the whole country.
    coincidencias=asociaciones[asociaciones.n_firms.gt(0)] if not asociaciones.empty else pd.DataFrame()
    if coincidencias.empty:
        estado='No satellite–ground coincidences were obtained in this selection with the uploaded data.'
    else:
        estado=f'{len(coincidencias)} event(s) with FIRMS spatial and temporal proximity under the chosen filter.'
    partes.append(Paragraph(estado,estilo['IGNISSmall']))
    if not asociaciones.empty:
        tabl=[['Event date (UTC)','Source(s)','Nearby FIRMS','Exploratory result']]
        for r in asociaciones.head(12).itertuples():
            tabl.append([str(r.fecha_utc)[:16],str(r.fuentes)[:38],str(r.n_firms),str(r.resultado)[:80]])
        # Wrap in paragraphs to preserve readability.
        t=Table([[Paragraph(escape(str(x)),estilo['IGNISCell']) for x in row] for row in tabl],
                 colWidths=[3.2*cm,5.05*cm,2.0*cm,7.45*cm],repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),C.HexColor('#dceaf2')),
                               ('ROWBACKGROUNDS',(0,1),(-1,-1),[C.white,C.HexColor('#f4f9fc')]),
                               ('GRID',(0,0),(-1,-1),.25,C.HexColor('#d0dee9')),
                               ('VALIGN',(0,0),(-1,-1),'TOP')]))
        partes.append(t)
        if len(asociaciones)>12:
            partes.append(Paragraph(f'Abbreviated report: showing 12 of {len(asociaciones)} events. '
                                     'Use the results CSV for the full detail.',estilo['IGNISNote']))
    partes.append(Paragraph('4. Annual history of FIRMS observations',estilo['IGNISH2']))
    if not nasa_hist.empty:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        anual=nasa_hist.groupby(nasa_hist.fecha_utc.dt.year).size().sort_index()
        ff=Figure(figsize=(8.1,2.05),facecolor='#ffffff')
        aa=ff.add_axes([.075,.26,.88,.64]); aa.set_facecolor('#ffffff')
        aa.bar(anual.index.astype(int),anual.to_numpy(),color='#32a7c5',width=.77)
        aa.set_xlim(min(anual.index)-.7,max(anual.index)+.7)
        aa.tick_params(labelsize=7,colors='#364f62')
        aa.set_xticks(anual.index[::2].astype(int))
        aa.grid(axis='y',alpha=.2);aa.set_axisbelow(True)
        for sp in ('top','right'):aa.spines[sp].set_visible(False)
        aa.set_ylabel('Observations',fontsize=7)
        image_buffer=io.BytesIO()
        FigureCanvasAgg(ff).print_png(image_buffer)
        partes.append(RLImage(io.BytesIO(image_buffer.getvalue()),width=17.3*cm,height=4.37*cm))
        partes.append(Paragraph('The evolution of the count cannot be interpreted as an incidence '
                                'trend without normalizing sensor and coverage changes.',estilo['IGNISNote']))
    partes.append(Paragraph('5. Nearby documented fires',estilo['IGNISH2']))
    if casos:
        for caso,dist in casos:
            partes.append(Paragraph(f'<b>{escape(caso["nombre"])}</b> – locality approximately {dist:.1f} km '
                                     f'from the cell center; check the official source and the episode dates. '
                                     'The location is a reference, NOT the ignition point.',estilo['IGNISSmall']))
    else:
        partes.append(Paragraph('No case included in the limited IGNIS library for this cell. '
                                 'This is not equivalent to an absence of fires or of records from other institutions.',estilo['IGNISSmall']))
    partes.append(Paragraph('6. Criterion, coverage and limitations',estilo['IGNISH2']))
    notas=[
        f'Spatial association: {umbral_km:g} km. If both records include a time: up to {umbral_h:g} hours; '
        f'if the time is missing: local-date match with a margin of {dias} day(s).',
        'NASA FIRMS detects thermal anomalies, not necessarily confirmed fires. '
        'A coincidence between sources does not prove independence or an early detection.',
        'The open SINAE/MIRA CSV published in 2022 covers March 2018 to June 2022. '
        'Records from other years must be supplied and verified separately.',
        'The referenced coastal cameras are approximate localities, NOT verified tower positions or coverage. '
        'Individual positions of the PAIF network are not described.',
        'This is not an alarm or operational dispatch system. Synthetic files are NOT used as real evidence.'
    ]
    for nota in notas:partes.append(Paragraph('• '+escape(nota),estilo['IGNISNote']))
    partes.append(Paragraph('<b>Public sources:</b> NASA FIRMS; '
                             f'<link href="{FUENTE_MIRA}" color="blue">SINAE/MIRA (2018–2022 dataset)</link>; '
                             f'<link href="{FUENTE_CAMARAS}" color="blue">Ministry of the Interior (Firefighters)</link>.',estilo['IGNISNote']))
    doc.build(partes,onFirstPage=pagina,onLaterPages=pagina)
    return buf.getvalue()



def mostrar_fusion_terrestre(maestro:pd.DataFrame|None=None) -> None:
    """Single tab for the three-source integration and the selectable exploratory map.

    Called unchanged from the main app: mostrar_fusion_terrestre(combined)
    """
    import streamlit as st
    st.header('🌎 IGNIS | Sky–ground fusion map')
    st.caption('NASA MODIS/VIIRS + Firefighters/PAIF ground evidence + SINAE/MIRA records')
    st.info('Exploratory prototype. It is not connected to Firefighters, PAIF or MIRA; it does NOT generate '
            'operational alerts, does NOT predict fires and does NOT dispatch resources.')
    try:
        nasa=normalizar_nasa(maestro)
        nasa=forzar_fechas_utc(nasa,'NASA Master')
    except Exception as exc:
        nasa=pd.DataFrame()
        st.error(f"Could not parse the Master: {type(exc).__name__}: {exc}")
    if nasa.empty:
        st.warning('First upload the IGNIS Master in “Data upload” (tab 1). '
                   'You can also add an extra FIRMS CSV in “Data sources”.')
    with st.expander('📁 Data sources · upload NASA, Firefighters and SINAE',expanded=nasa.empty):
        st.caption('If you already uploaded the Master in the first tab, do NOT upload it again: '
                   'it is recovered automatically here. Institutional files are optional.')
        nasa_extra=st.file_uploader('Additional NASA FIRMS CSV/ZIP (optional; NOT needed if you use the Master)',
                                   type=['csv','zip'],key='fus_v2_extra_nasa')
        if nasa_extra is not None:
            try:
                nuevo=normalizar_nasa(leer_firms_adicional(nasa_extra.name,nasa_extra.getvalue()))
                nasa=pd.concat([nasa,nuevo],ignore_index=True).drop_duplicates(
                    subset=['fecha_utc','lat','lon','instrumento']).reset_index(drop=True)
                nasa=forzar_fechas_utc(nasa,'additional NASA').reset_index(drop=True)
                st.success(f"NASA ready: {len(nasa):,} unique observations in the wide area.")
            except Exception as exc:
                st.error(f"Additional NASA: {type(exc).__name__}: {exc}")
        cb,cs=st.columns(2)
        with cb:
            st.markdown('**Firefighters / PAIF**')
            b_file=st.file_uploader('CSV, JSON or GeoJSON of ground events',
                                    type=['csv','json','geojson'],key='fus_v2_bomberos')
            st.download_button('Download synthetic CSV for testing',tabla_ejemplo('terrestre'),
                               file_name='IGNIS_BOMBEROS_DEMO_SIMULADO.csv',mime='text/csv',
                               key='fus_v2_plantilla_bomberos')
        with cs:
            st.markdown('**SINAE / MIRA**')
            s_file=st.file_uploader('CSV, JSON or GeoJSON of institutional events',
                                    type=['csv','json','geojson'],key='fus_v2_sinae')
            st.download_button('Download synthetic CSV for testing',tabla_ejemplo('sinae'),
                               file_name='IGNIS_SINAE_DEMO_SIMULADO.csv',mime='text/csv',
                               key='fus_v2_plantilla_sinae')
            st.markdown(f'[Official SINAE/MIRA CSV (March 2018 – June 2022, published in 2022)]({FUENTE_MIRA})')
            st.caption('For 2023–2026 you need to import later authorized records: '
                       'the public CSV on that page does not cover those years.')
        b=_leer_fuente(st,b_file,'BOMBEROS_PAIF','b')
        s=_leer_fuente(st,s_file,'SINAE_MIRA','s')
        demo=st.checkbox('Add a demonstration with SYNTHETIC ground events near a NASA point',
                         value=False,key='fus_v2_demo')
        if demo and not nasa.empty:
            b_demo,s_demo=demo_sintetica(nasa)
            b=pd.concat([b,b_demo],ignore_index=True)
            s=pd.concat([s,s_demo],ignore_index=True)
            st.warning('Made-up data were added to test the engine. They are NOT real Firefighters or SINAE signals.')
    if nasa.empty:
        st.info('The map and reports will appear once you upload at least one real FIRMS file.')
        return

    # The display focuses on the map, not on the column configuration.
    st.markdown('### 🗺️ Historical map of Uruguay · pick a grid cell')
    years=sorted(int(v) for v in nasa.fecha_utc.dt.year.dropna().unique())
    col_z,col_y=st.columns([2,1])
    zona=col_z.selectbox('Query area',list(ZONAS),key='fus_v2_zona')
    year_opt=col_y.selectbox('Period',['Full history']+years,
                             index=0,key='fus_v2_anio')
    ano=year_opt if isinstance(year_opt,int) else None
    ver_torres=st.checkbox('Localities linked to the Firefighters coastal network (not verified towers)',
                          value=True,key='fus_v2_ver_refs')
    ver_casos=st.checkbox('Documented fires: locality reference points',
                         value=True,key='fus_v2_ver_casos')

    recorte=_recortar(nasa,zona)
    periodo=(recorte.loc[recorte.fecha_utc.dt.year==ano].copy()
             if ano is not None else recorte)
    hist_malla=_crear_malla(recorte)
    malla_periodo=_crear_malla(periodo)
    visible=hist_malla
    activas=None if ano is None else set(zip(malla_periodo.ilat.astype(int),malla_periodo.ilon.astype(int)))
    # Cases on the map do not represent the burned perimeter or the starting position.
    b_zona=_recortar(b,zona) if not b.empty else b
    s_zona=_recortar(s,zona) if not s.empty else s
    b_vista=b_zona.loc[b_zona.fecha_utc.dt.year==ano].copy() if ano is not None and not b_zona.empty else b_zona
    s_vista=s_zona.loc[s_zona.fecha_utc.dt.year==ano].copy() if ano is not None and not s_zona.empty else s_zona
    mk1,mk2,mk3=st.columns(3)
    mk1.metric('FIRMS observations in the period',f"{len(periodo):,}")
    mk2.metric('Years with data in the area',f"{recorte.fecha_utc.dt.year.nunique():,}")
    mk3.metric('Visible 0.2° cells',f"{len(visible):,}")
    st.caption('Colors represent YEARS with at least one thermal detection per cell, '
               'not the number of fires. The Master files do not necessarily cover every month. '
               'No correction for instrument differences, cloud cover or revisits.')
    # The session selection is drawn first; clicking another cell makes
    # Plotly rerun and the report follows the new point without manual lat/lon.
    guardada=st.session_state.get('fus_v2_celda')
    actual=guardada if guardada in set(zip(visible.ilat.astype(int),visible.ilon.astype(int))) else None
    fig=_mapa_plotly(visible,periodo,b_vista,s_vista,zona,ano,ver_torres,ver_casos,activas,actual)
    try:
        seleccion=st.plotly_chart(fig,use_container_width=True,on_select='rerun',
                                  selection_mode='points',key='fus_v2_click_'+str(zona)+str(ano))
    except TypeError:
        # Compatibility with older Streamlit releases without native selection.
        st.plotly_chart(fig,use_container_width=True)
        seleccion=None
    clicked=_seleccion_de_grafico(seleccion)
    st.caption('◼ Blue: 3–5 years · Turquoise: 6–10 · Yellow: 11–17 · Orange: 18+ '
               '· ◇ Blue: reference LOCALITY (NOT camera location) '
               '· ○ Pink: documented fire locality (NOT exact point).')
    if ano is not None:
        st.caption('Cells with a yellow border contain observations in the chosen year; '
                   'the inner color keeps the historical recurrence.')
    st.caption('Click on a colored cell. If your browser does not support selection, '
               'pick it in the selector shown below.')

    # If there are no observations in the area/period, do not risk an invalid index.
    if visible.empty:
        st.warning('There are no cells with FIRMS observations for that selection; '
                   'this does not prove that no fires occurred.')
        return
    opciones=list(zip(visible.ilat.astype(int),visible.ilon.astype(int)))
    key='fus_v2_celda'
    if clicked is not None and clicked in opciones:
        st.session_state[key]=clicked
    if key not in st.session_state or st.session_state[key] not in opciones:
        st.session_state[key]=opciones[0]
    st.success('📍 SELECTED GRID CELL: ' + _descripcion_celda(visible, st.session_state[key]) +
               ' · Click another colored cell to update the whole analysis.')
    with st.expander('Choose another grid cell from a list (alternative to clicking)'):
        seleccion_celda=st.selectbox('Grid cell to inspect',opciones,
                  format_func=lambda k:_descripcion_celda(visible,k),key=key)

    lat0,lat1=seleccion_celda[0]*PASO_GRADOS,(seleccion_celda[0]+1)*PASO_GRADOS
    lon0,lon1=seleccion_celda[1]*PASO_GRADOS,(seleccion_celda[1]+1)*PASO_GRADOS
    t_hist=recorte.loc[recorte.lat.ge(lat0)&recorte.lat.lt(lat1)&
                       recorte.lon.ge(lon0)&recorte.lon.lt(lon1)].copy()
    t_per=t_hist.loc[t_hist.fecha_utc.dt.year==ano].copy() if ano is not None else t_hist
    def dentro_celda(df:pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:return pd.DataFrame()
        return df.loc[df.lat.ge(lat0)&df.lat.lt(lat1)&df.lon.ge(lon0)&df.lon.lt(lon1)].copy()
    bom_cell=dentro_celda(b_vista)
    sin_cell=dentro_celda(s_vista)
    st.markdown('### 🔎 Automatic report for the chosen grid cell')
    a,b1,c1=st.columns(3)
    a.metric('Detections in the cell',len(t_per))
    b1.metric('Years with observed activity',t_hist.fecha_utc.dt.year.nunique())
    c1.metric('Distinct days observed',t_hist.fecha_utc.dt.date.nunique())
    st.caption(f"Approximate perimeter: latitudes {lat0:.2f} to {lat1:.2f}; "
               f"longitudes {lon0:.2f} to {lon1:.2f} degrees WGS84. "
               'It is a geographic cell, NOT a burned area.')
    if not t_hist.empty:
        por_anio=t_hist.groupby(t_hist.fecha_utc.dt.year).size().rename('Observations').reset_index()
        por_anio.columns=['Year','Observations']
        instrumentos=t_per.groupby('instrumento').size().rename('Records').reset_index().rename(columns={'instrumento':'Instrument'})
        x1,x2=st.columns([1,1])
        with x1:
            st.markdown('**Annual history of the cell**')
            st.bar_chart(por_anio.set_index('Year'))
        with x2:
            st.markdown('**Sensors present in the period**')
            st.dataframe(instrumentos,use_container_width=True,hide_index=True)
    else:
        st.info('There is no satellite data in this grid cell for the active period.')
    # Descriptive annual cross-check only: one row per year, never meaning a confirmed fire.
    hist_anual=(t_hist.groupby(t_hist.fecha_utc.dt.year).size().rename('NASA FIRMS').reset_index()
                if not t_hist.empty else pd.DataFrame(columns=['Year','NASA FIRMS']))
    if not hist_anual.empty: hist_anual.columns=['Year','NASA FIRMS']
    if not bom_cell.empty:
        hist_anual=hist_anual.merge(bom_cell.assign(Year=bom_cell.fecha_utc.dt.year).groupby('Year').size()
                      .rename('Firefighters/PAIF uploaded').rename_axis('Year').reset_index(),
                      how='outer',on='Year')
    if not sin_cell.empty:
        hist_anual=hist_anual.merge(sin_cell.assign(Year=sin_cell.fecha_utc.dt.year).groupby('Year').size()
                      .rename('SINAE/MIRA uploaded').rename_axis('Year').reset_index(),
                      how='outer',on='Year')
    if not hist_anual.empty:
        hist_anual=hist_anual.fillna(0).sort_values('Year')
        for col in hist_anual.columns:
            hist_anual[col]=hist_anual[col].astype(int)
        with st.expander('📅 Compare years: NASA vs. uploaded institutional records',expanded=False):
            st.dataframe(hist_anual,use_container_width=True,hide_index=True)
            st.caption('These counts come from different sources and resolutions. '
                       'Zero in SINAE or Firefighters means zero records IMPORTED into IGNIS in this cell, '
                       'not that no fires occurred. Open MIRA data cover only 2018–2022.')
    st.markdown('**Nearby documented background (references, not per-pixel verification)**')
    centroid=(lat0+lat1)/2,(lon0+lon1)/2
    casos=[]
    for x in CASOS_DOCUMENTADOS:
        dist=float(haversine_vector(centroid[0],centroid[1],np.array([x['lat']]),np.array([x['lon']]))[0])
        if dist<=30 and (ano is None or int(x['inicio'][:4])<=ano<=int(x['fin'][:4])):
            casos.append((x,dist))
    if casos:
        for x,dist in casos:
            st.markdown(f"- **{x['nombre']}** · locality about {dist:.1f} km from the cell center "
                        f"· [{x['fuente']} (documentary source)]({x['url']})")
    else:
        st.caption('There is no case in our small documentary library within 30 km. '
                   'That does NOT mean an absence of fires or institutional records.')

    st.markdown('### 🛰️ Exploratory fusion NASA · Firefighters · SINAE')
    ca,cb,cc=st.columns(3)
    radio=ca.select_slider('Maximum distance (km)',options=[1,3,5,10,15,20,30],value=10,
                            key='fus_v2_radio')
    horas=cb.select_slider('Maximum separation (h)',options=[1,3,6,12,24,48,72],value=24,
                           key='fus_v2_horas')
    dias=cc.selectbox('If only a date is available: margin (days)',[0,1],key='fus_v2_dias')
    # Engine over the whole area/period (not only the cell), then filter by cell.
    ext_n=len(b_vista)+len(s_vista)
    if ext_n>2000:
        st.warning(f'{ext_n:,} external events in the selection: for performance we analyze '
                   'only the first 2,000, without interpreting the result as exhaustive.')
    bb=b_vista.head(1000) if not b_vista.empty else b_vista
    ss=s_vista.head(1000) if not s_vista.empty else s_vista
    if ext_n and not periodo.empty:
        try:
            fusion=fusionar(periodo,bb,ss,float(radio),float(horas),int(dias))
        except Exception as exc:
            st.error(f"Controlled engine error: {type(exc).__name__}: {exc}. "
                     'Check the date, area and column types of the CSV.')
            fusion=pd.DataFrame()
    elif ext_n:
        # Even without FIRMS, external observations are kept for review.
        try:
            fusion=fusionar(pd.DataFrame(),bb,ss,float(radio),float(horas),int(dias))
        except Exception as exc:
            st.warning(f'Could not compute coincidences: {exc}')
            fusion=pd.DataFrame()
    else:
        fusion=pd.DataFrame()
    # Share the latest result with the control center (3D scene + analytics).
    st.session_state['ignis_fusion_results']=fusion if not fusion.empty else None
    if not fusion.empty:
        celda_fusion=fusion.loc[fusion.lat.ge(lat0)&fusion.lat.lt(lat1)&
                               fusion.lon.ge(lon0)&fusion.lon.lt(lon1)].copy()
        n_match=int((fusion.n_firms>0).sum())
        n_triple=int(fusion.resultado.astype(str).str.contains(r'NASA \+ ground \+ SINAE',regex=True).sum())
        xx,yy,zz=st.columns(3)
        xx.metric('External events in the area',len(fusion))
        yy.metric('With nearby NASA',n_match)
        zz.metric('Triple coincidences',n_triple)
        if fusion.simulado.astype(str).str.startswith('YES').any():
            st.warning('Includes synthetic records. A simulated coincidence tests the software cross-check, '
                       'not the operational capability to detect fires.')
        if not celda_fusion.empty:
            st.dataframe(celda_fusion,use_container_width=True,hide_index=True)
        else:
            st.info('There are no external events uploaded in the chosen grid cell; '
                    'associations from other cells can be downloaded.')
        st.download_button('⬇️ Download three-source results (CSV)',
            fusion.to_csv(index=False).encode('utf-8-sig'),
            file_name='IGNIS_FUSION_EXPLORATORIA_NO_OPERATIVA.csv',
            mime='text/csv',key='fus_v2_descargar_fusion')
        salida_local=celda_fusion
    else:
        salida_local=pd.DataFrame()
        st.info('To check coincidences, upload an authorized ground/SINAE CSV or '
                'enable the synthetic demonstration inside “Data sources”. '
                'The historical map works even if you upload no external files.')
    sim=bool((not bom_cell.empty and bom_cell.es_simulado.any()) or
             (not sin_cell.empty and sin_cell.es_simulado.any()))
    st.markdown('**Cell reading:** '+_interpretacion_celda(t_hist,bom_cell,sin_cell,salida_local,sim))
    resumen=pd.DataFrame([{
        'lat_min':lat0,'lat_max':lat1,'lon_min':lon0,'lon_max':lon1,
        'anio_filtro':ano if ano is not None else 'ALL',
        'observaciones_periodo':len(t_per),
        'anios_historicos':t_hist.fecha_utc.dt.year.nunique(),
        'dias_historicos':t_hist.fecha_utc.dt.date.nunique(),
        'registros_bomberos':len(bom_cell),'registros_sinae':len(sin_cell),
        'casos_documentados_cercanos':len(casos),
        'es_informe_operativo':False,
    }])
    # Cell reading: distinguishes supplied evidence from absence of evidence.
    st.markdown('#### 🔗 Result for the selected grid cell')
    if not bom_cell.empty or not sin_cell.empty:
        eventos_tabla=[]
        for nombre,df in [('Firefighters / PAIF',bom_cell),('SINAE / MIRA',sin_cell)]:
            for r in df.itertuples():
                eventos_tabla.append({'Provenance':nombre,'UTC date':str(r.fecha_utc)[:19],
                    'ID':str(r.id)[:50],'Reported type':str(r.detalle)[:100],
                    'Declared status':str(r.estado_origen)[:100],
                    'Condition':'SYNTHETIC' if bool(r.es_simulado) else 'Declared by file'})
        if eventos_tabla:
            st.dataframe(pd.DataFrame(eventos_tabla),use_container_width=True,hide_index=True)
    else:
        st.info('No Firefighters/PAIF or SINAE/MIRA records were imported within '
                'this grid cell and period. This does NOT imply there were no fires.')
    if not salida_local.empty and salida_local.n_firms.gt(0).any():
        st.success('There is at least one supplied event with a nearby FIRMS observation in the '
                   'configured window. It is a coincidence for review, NOT a fire confirmation.')
    elif not bom_cell.empty or not sin_cell.empty:
        st.warning('There are imported events, but no FIRMS coincidence was verified '
                   'in this cell with the chosen thresholds.')
    if not salida_local.empty and salida_local.simulado.astype(str).str.startswith('YES').any():
        st.warning('DEMONSTRATION RESULT: includes synthetic data; '
                   'it does not confirm real Firefighters or SINAE observations.')
    try:
        pdf_celda=generar_informe_pdf_celda(
            visible,seleccion_celda,t_hist,t_per,bom_cell,sin_cell,salida_local,
            casos,ano,float(radio),float(horas),int(dias),b_vista,s_vista)
        st.download_button('📄 Download PDF REPORT for this grid cell',pdf_celda,
            file_name=f'IGNIS_informe_celda_{abs(int(seleccion_celda[0]))}_{abs(int(seleccion_celda[1]))}_'
                      f'{ano or "history"}.pdf',
            mime='application/pdf',key='fus_v3_pdf_celda')
        st.caption('Exploratory analysis PDF with map, NASA history, supplied institutional '
                   'records and sources. It is not equivalent to a confirmed incident report.')
    except Exception as exc:
        st.warning(f'Could not build the PDF for this selection: {type(exc).__name__}: {exc}')
    st.download_button('⬇️ Download cell sheet (CSV)',
        resumen.to_csv(index=False).encode('utf-8-sig'),
        file_name='IGNIS_CELDA_ELEGIDA_EXPLORATORIA.csv',mime='text/csv',key='fus_v2_ficha')
    with st.expander('Methodology, provenance and limitations'):
        st.markdown(
            f"- NASA FIRMS: history actually included in the Master; not equivalent to confirmed fires.\n"
            f"- [Ministry of the Interior — Firefighters coastal network]({FUENTE_CAMARAS}): "
            "20 cameras are documented, but there is NO verified list of their coordinates in the project. "
            "Diamonds mark centers of reference localities, not towers or real surveillance radii.\n"
            f"- [SINAE/MIRA — historical CSV catalog 2018–2022]({FUENTE_MIRA}); "
            "events may also derive from other sources, including space observations.\n"
            "- Case library: approximate locations of LOCALITIES and documented dates; "
            "no burned polygons, ignition coordinates or exhaustive coverage are available.\n"
            "- PAIF: another network of 65 forest cameras (2025–2026 season); no claim is made "
            "about an absence of coverage outside Colonia–Rocha.\n"
            "- The grid is 0.2°; colors indicate years with some observation, not fire rates. "
            "Area clippings are APPROXIMATE, not departmental boundaries.\n"
            "- Correlation is based on configurable temporal and spatial coincidence: "
            "it does not validate source independence, sensor accuracy or alert times."
        )
