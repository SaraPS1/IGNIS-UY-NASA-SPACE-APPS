import json
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st
from ignis_i18n import display_dataframe
import streamlit.components.v1 as components

try:
    from sgp4.api import Satrec
    HAS_SGP4 = True
except Exception:  # pragma: no cover - dependency optional
    Satrec = None
    HAS_SGP4 = False

SATELLITE_CATALOG = [
    {
        "name": "Terra (MODIS)",
        "sensor": "MODIS",
        "instrument": "MODIS",
        "orbit": "Sun-synchronous polar orbit",
        "source": "CelesTrak / NASA / MODIS",
        "color": "#5ec8ff",
        "catalog": "25994",
    },
    {
        "name": "Aqua (MODIS)",
        "sensor": "MODIS",
        "instrument": "MODIS",
        "orbit": "Sun-synchronous polar orbit",
        "source": "CelesTrak / NASA / MODIS",
        "color": "#7ad0ff",
        "catalog": "27424",
    },
    {
        "name": "Suomi-NPP (VIIRS)",
        "sensor": "VIIRS",
        "instrument": "VIIRS S-NPP",
        "orbit": "Polar orbit",
        "source": "CelesTrak / NOAA / VIIRS",
        "color": "#ffc857",
        "catalog": "37849",
    },
    {
        "name": "NOAA-20 (VIIRS)",
        "sensor": "VIIRS",
        "instrument": "VIIRS NOAA-20",
        "orbit": "Polar orbit",
        "source": "CelesTrak / NOAA / VIIRS",
        "color": "#8fe3a5",
        "catalog": "43013",
    },
    {
        "name": "NOAA-21 (VIIRS)",
        "sensor": "VIIRS",
        "instrument": "VIIRS NOAA-21",
        "orbit": "Polar orbit",
        "source": "CelesTrak / NOAA / VIIRS",
        "color": "#d7a4ff",
        "catalog": "54234",
    },
]


MAX_HOTSPOTS_3D = 1500


def _uruguay_outline() -> List[List[float]]:
    """Contorno [lon, lat] desde uruguay_contorno.geojson (vacío si falta)."""
    try:
        from pathlib import Path
        path = Path(__file__).resolve().parent / "uruguay_contorno.geojson"
        data = json.loads(path.read_text(encoding="utf-8"))
        geometry = data["features"][0]["geometry"]
        ring = geometry["coordinates"][0]
        return [[float(p[0]), float(p[1])] for p in ring]
    except Exception:
        return []


def _normalize_fire_frame(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["fecha", "latitude", "longitude", "instrumento", "satellite", "frp", "confidence"])
    frame = df.copy()
    frame["fecha"] = pd.to_datetime(frame.get("fecha", pd.NaT), errors="coerce", utc=True)
    frame["latitude"] = pd.to_numeric(frame.get("latitude", pd.Series(np.nan, index=frame.index)), errors="coerce")
    frame["longitude"] = pd.to_numeric(frame.get("longitude", pd.Series(np.nan, index=frame.index)), errors="coerce")
    frame["frp"] = pd.to_numeric(frame.get("frp", pd.Series(np.nan, index=frame.index)), errors="coerce")
    frame["confidence"] = frame.get("confidence", pd.Series("", index=frame.index)).fillna("").astype(str)
    frame["instrumento"] = frame.get("instrumento", pd.Series("", index=frame.index)).fillna("").astype(str)
    frame["satellite"] = frame.get("satellite", pd.Series("", index=frame.index)).fillna("").astype(str)
    frame = frame.dropna(subset=["fecha", "latitude", "longitude"]).copy()
    frame = frame[(frame["latitude"].between(-90, 90)) & (frame["longitude"].between(-180, 180))]
    if frame.empty:
        return frame
    frame = frame.sort_values("fecha").reset_index(drop=True)
    return frame


def _parse_tle_pair(raw_text: str) -> Optional[tuple]:
    """Acepta TLE estándar de 2 líneas o 3LE con una línea de nombre."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    line1 = next((line for line in lines if line.startswith("1 ") and len(line) >= 60), None)
    line2 = next((line for line in lines if line.startswith("2 ") and len(line) >= 60), None)
    if not line1 or not line2:
        return None
    if line1[2:7].strip() != line2[2:7].strip():
        return None
    return line1, line2


def _fetch_celestrak_tle(catalog_num: str) -> Optional[str]:
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={catalog_num}&FORMAT=TLE"
    try:
        response = requests.get(url, timeout=(3, 4))
        response.raise_for_status()
        pair = _parse_tle_pair(response.text)
        return "\n".join(pair) if pair else None
    except requests.RequestException:
        return None


def _utc_to_jd_utc(dt: datetime) -> float:
    unix_seconds = dt.astimezone(timezone.utc).timestamp()
    return 2440587.5 + (unix_seconds / 86400.0)


def _generate_orbit_positions_from_tle(tle_text: str, steps: int = 80) -> List[Dict[str, float]]:
    """Compatibility wrapper. Skyfield WGS84 + SGP4, never a stale TLE."""
    from ignis_orbits import satellite_from_tle, valid_for_time, positions_at, step_times
    pair = _parse_tle_pair(tle_text)
    if not pair:
        return []
    try:
        sat = satellite_from_tle(pair, "IGNIS compatibility")
        now = datetime.now(timezone.utc)
        if not valid_for_time(sat, now):
            return []
        interval = step_times(now, now + timedelta(minutes=100),
                              max(1, int(6000 / max(1, steps - 1))))
        return positions_at(sat, interval)
    except (ValueError, TypeError, RuntimeError, ArithmeticError):
        return []



def _generate_simulated_orbit(name: str, steps: int = 80) -> List[Dict[str, float]]:
    phase = {
        "Terra (MODIS)": 0.15,
        "Aqua (MODIS)": 1.85,
        "Suomi-NPP (VIIRS)": 2.7,
        "NOAA-20 (VIIRS)": 4.2,
        "NOAA-21 (VIIRS)": 5.1,
    }.get(name, 0.0)
    angles = np.linspace(0, 2 * np.pi, steps + 1)
    lat = 52 * np.sin(angles + phase) + 5 * np.cos(angles * 2.4)
    lon = -180 + (angles / (2 * np.pi)) * 360
    return [{"lat": float(lat[idx]), "lon": float(lon[idx]), "alt_km": float(700 + 35 * np.sin(angles[idx] * 2.2))} for idx in range(len(angles))]


@st.cache_data(ttl=3600, show_spinner=False)
def _build_satellite_payload(use_live_tle: bool = False) -> List[Dict[str, Any]]:
    """Renderiza inmediatamente en modo ilustrativo; Current TLE data bajo demanda.

    Los TLE consultados NO reconstruyen la fecha histórica de los puntos FIRMS.
    """
    fetched: Dict[str, Optional[str]] = {}
    if use_live_tle:
        # Cinco peticiones independientes a CelesTrak en paralelo.
        # El modo predeterminado evita cualquier espera de red.
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(
                _fetch_celestrak_tle,
                [sat["catalog"] for sat in SATELLITE_CATALOG],
            ))
        fetched = {sat["catalog"]: value
                   for sat, value in zip(SATELLITE_CATALOG, results)}

    payload: List[Dict[str, Any]] = []
    for sat in SATELLITE_CATALOG:
        positions: List[Dict[str, float]] = []
        tle_text = fetched.get(sat["catalog"])
        if tle_text:
            positions = _generate_orbit_positions_from_tle(tle_text)
        payload.append({
            "name": sat["name"],
            "sensor": sat["sensor"],
            "instrument": sat["instrument"],
            "orbit": sat["orbit"],
            "source": sat["source"],
            "color": sat["color"],
            "mode": "tle_actual" if positions else "ilustrativa",
            "positions": positions,
        })
    return payload


def _build_hotspot_payload(frame: pd.DataFrame, selected_date: Optional[datetime] = None, satellite_filter: str = "All") -> List[Dict[str, Any]]:
    hotspot_frame = frame.copy()
    hotspot_frame["fecha"] = pd.to_datetime(hotspot_frame["fecha"], errors="coerce", utc=True)
    if selected_date is not None:
        if hasattr(selected_date, "date"):
            selected_day = selected_date.date()
        else:
            selected_day = pd.Timestamp(selected_date).date()
        hotspot_frame = hotspot_frame[hotspot_frame["fecha"].dt.date == selected_day]
    if satellite_filter and satellite_filter != "All":
        hotspot_frame = hotspot_frame[hotspot_frame["satellite"].str.contains(satellite_filter, case=False, na=False)]
    if len(hotspot_frame) > MAX_HOTSPOTS_3D:
        # Con tope, se conservan los de mayor FRP (no los más antiguos).
        hotspot_frame = hotspot_frame.assign(
            _frp_orden=pd.to_numeric(hotspot_frame.get("frp"), errors="coerce").fillna(0)
        ).nlargest(MAX_HOTSPOTS_3D, "_frp_orden")
    hotspot_frame = hotspot_frame.sort_values("fecha").reset_index(drop=True)
    items: List[Dict[str, Any]] = []
    for _, row in hotspot_frame.iterrows():
        frp = float(row.get("frp", 0) or 0)
        color = "#f7b267"
        if frp > 150:
            color = "#ff5d73"
        elif frp > 70:
            color = "#ff9f43"
        elif frp > 25:
            color = "#ffd166"
        items.append({
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
            "frp": frp,
            "sensor": str(row.get("instrumento", "")),
            "satellite": str(row.get("satellite", "")),
            "confidence": str(row.get("confidence", "")),
            "date": row["fecha"].isoformat(timespec="seconds") if pd.notna(row["fecha"]) else "",
            "color": color,
        })
    return items


def _country_regions_html() -> str:
    return json.dumps({
        "global": {"lat": -25, "lon": -58, "height": 4800000},
        "south_america": {"lat": -25, "lon": -62, "height": 2700000},
        "uruguay": {"lat": -32.8, "lon": -56.0, "height": 1600000},
        "selected": {"lat": -32.8, "lon": -56.0, "height": 1600000},
    })


def _render_globe_html(config: Dict[str, Any]) -> str:
    # Do not let imported source text close the embedded JSON script element.
    payload = json.dumps(config, allow_nan=False).replace("</", "<\\/")
    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          html, body {{
            width: 100%; height: 100%; margin: 0; overflow: hidden; background: #020812;
            font-family: Arial, sans-serif;
          }}
          #globe-shell {{
            position: relative; width: 100%; height: 100%; min-height: 640px; display: block; background: radial-gradient(circle at top, #071827 0%, #020812 55%, #01050a 100%);
            border-radius: 18px; overflow: hidden;
          }}
          #globe-root {{
            width: 100%; height: 100%; min-height: 640px; display: block; background: radial-gradient(circle at top, #071827 0%, #020812 55%, #01050a 100%);
          }}
          #ignis-globe-status {{
            position: absolute; left: 16px; top: 16px; z-index: 10;
            padding: 8px 12px; border-radius: 999px; font: 12px/1.2 Arial, sans-serif;
            color: #dfeaff; background: rgba(8, 16, 30, 0.75); border: 1px solid rgba(110, 138, 255, 0.65);
            backdrop-filter: blur(6px);
          }}
          .ignis-globe-watermark {{
            position:absolute; top:18px; right:18px; z-index:10;
            color:#effcff; padding:9px 13px; border-radius:11px;
            background:rgba(3,14,28,.75); border:1px solid rgba(61,180,223,.38);
            font:bold 12px Arial,sans-serif; letter-spacing:.09em;
            pointer-events:none;
          }}
          .ignis-globe-watermark span {{font-weight:400;color:#81cae5}}
          .ignis-globe-help {{
            position:absolute; bottom:19px; left:18px; z-index:10;
            color:#c8e0ef;padding:8px 12px;border-radius:10px;
            background:rgba(3,14,28,.76);font:12px Arial,sans-serif;
            pointer-events:none;
          }}
          canvas {{
            display: block; width: 100% !important; height: 100% !important;
          }}
          #ignis-tip {{
            position:absolute; z-index:12; display:none; pointer-events:none;
            white-space:pre; padding:7px 10px; border-radius:9px;
            font:12px/1.4 Arial,sans-serif; color:#effcff;
            background:rgba(3,14,28,.92); border:1px solid rgba(255,157,67,.7);
          }}
          #ignis-legend {{
            position:absolute; right:18px; bottom:19px; z-index:10;
            padding:8px 12px; border-radius:10px; color:#c8e0ef;
            background:rgba(3,14,28,.76); font:11px/1.6 Arial,sans-serif;
          }}
          #ignis-legend i {{
            display:inline-block; width:9px; height:9px; border-radius:50%;
            margin-right:6px;
          }}
          #ignis-orbit-ctl {{
            position:absolute; left:50%; bottom:19px; transform:translateX(-50%);
            z-index:10; display:flex; flex-wrap:wrap; justify-content:center; max-width:90%; gap:7px; align-items:center;
            padding:6px 12px; border-radius:10px; color:#c8e0ef;
            background:rgba(3,14,28,.76); font:12px Arial,sans-serif;
          }}
          #ignis-orbit-ctl button, #ignis-orbit-ctl select {{
            background:#0b2237; color:#effcff; border:1px solid #326180;
            border-radius:7px; padding:8px 10px; font:11px Arial,sans-serif;
            cursor:pointer; min-height:35px;
          }}
          #ignis-orbit-ctl button:hover, #ignis-orbit-ctl select:hover {{border-color:#5ee5fc; background:#134061;}}
          #ignis-orbit-ctl button:focus-visible, #ignis-orbit-ctl select:focus-visible {{outline:2px solid #67dffb;outline-offset:2px}}
          #ignis-orbit-ctl button:disabled, #ignis-orbit-ctl select:disabled {{opacity:.43;cursor:not-allowed}}
          #ignis-orbit-ctl label {{font-size:10px;color:#acd9e9;font-weight:700;letter-spacing:.06em}}
          #ignis-orbit-ctl {{box-shadow:0 12px 48px #0009;border:1px solid #244c68;max-width:calc(100% - 250px)}}
          #globe-shell {{border:1px solid rgba(72,165,198,.34);box-shadow:inset 0 0 80px #041020b0}}
          #ignis-globe-status {{border-radius:6px;max-width:62%}}
          @media(max-width:970px){{#ignis-orbit-ctl{{max-width:94%;bottom:65px}}.ignis-globe-help{{display:none}}}}
          @media(prefers-reduced-motion:reduce){{#globe-shell *{{scroll-behavior:auto!important}}}}

        </style>
      </head>
      <body>
        <div id="globe-shell">
          <div id="ignis-globe-status">Preparing 3D globe…</div>
          <div class="ignis-globe-watermark">
            IGNIS UY <span>· 3D ORBITAL EXPLORER</span>
          </div>
          <div class="ignis-globe-help">Drag to rotate · Scroll to zoom · Hover over a column</div>
          <div id="ignis-tip"></div>
          <div id="ignis-legend">
            <b>Fire Radiative Power (FRP)</b><br>
            <i style="background:#f7b267"></i>&lt; 25 MW<br>
            <i style="background:#ffd166"></i>25–70 MW<br>
            <i style="background:#ff9f43"></i>70–150 MW<br>
            <i style="background:#ff5d73"></i>&gt; 150 MW<br>
            Marker height ∝ FRP
          </div>
          <div id="ignis-orbit-ctl">
            <label for="ignis-tracked-sat">SATELLITE</label><select id="ignis-tracked-sat" aria-label="Choose satellite to replay"></select>
            <button id="ignis-last-pass" type="button">Last pass</button>
            <button id="ignis-next-pass" type="button">Next pass</button>
            <button id="ignis-current" type="button">Current UTC</button>
            <button id="ignis-play" type="button">⏸ Pause</button>
            <label for="ignis-speed">REPLAY SPEED</label><select id="ignis-speed" aria-label="Orbital playback speed">
              <option value="1" selected>1×</option>
              <option value="5">5×</option>
              <option value="10">10×</option>
              <option value="30">30×</option>
              <option value="60">60×</option>
            </select>
            <span id="ignis-orbit-clock" aria-live="polite"></span>
          </div>
          <div id="globe-root"></div>
        </div>
        <script>
          (function(){{
            const data={payload};
            const root=document.getElementById('globe-root');
            const status=document.getElementById('ignis-globe-status');
            window.__ignisGlobeReady=false;
            window.__ignisGlobeFallbackActive=false;
            function drawScientificFallback(){{
              if(!root)return;
              root.replaceChildren();
              const wrap=document.createElement('div');
              wrap.style.cssText='width:100%;height:100%;display:flex;align-items:center;justify-content:center;position:relative;background:radial-gradient(ellipse at 50% 38%,#10324d,#040e1b 75%)';
              const cv=document.createElement('canvas');
              cv.style.cssText='display:block;max-width:100%;max-height:100%';
              wrap.appendChild(cv);root.appendChild(wrap);
              const ring=(Array.isArray(data.outline)&&data.outline.length>3)?data.outline:[[-58.4,-34.9],[-58.1,-34.2],[-57.2,-33.5],[-56.4,-32.8],[-55.8,-32],[-54.7,-31.6],[-54.3,-32.2],[-54.7,-33],[-55.5,-34],[-56.1,-34.8]];
              const observations=Array.isArray(data.hotspots)?data.hotspots:[];
              const bounds={{lon0:-59.1,lon1:-52.4,lat0:-35.7,lat1:-29.6}};
              function point(lon,lat,w,h){{
                const size=Math.min(w*.84,h*.82);
                const sx=(Number(lon)-bounds.lon0)/(bounds.lon1-bounds.lon0);
                const sy=(Number(lat)-bounds.lat0)/(bounds.lat1-bounds.lat0);
                const scale=Math.min(size/6.7,(h*.80)/6.1);
                return [w*.5+(sx-.5)*6.7*scale,h*.5-(sy-.5)*6.1*scale];
              }}
              function paint(){{
                const w=Math.max(340,root.clientWidth||800),h=Math.max(350,root.clientHeight||640);
                const ratio=Math.min(window.devicePixelRatio||1,2);
                cv.width=Math.round(w*ratio);cv.height=Math.round(h*ratio);
                cv.style.width=w+'px';cv.style.height=h+'px';
                const ctx=cv.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);
                const bg=ctx.createLinearGradient(0,0,w,h);
                bg.addColorStop(0,'#0a233a');bg.addColorStop(1,'#050e1e');
                ctx.fillStyle=bg;ctx.fillRect(0,0,w,h);
                ctx.strokeStyle='rgba(101,210,235,.10)';ctx.lineWidth=1;
                for(let x=w*.15;x<w;x+=Math.max(55,w/15)){{ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}}
                for(let y=h*.16;y<h;y+=Math.max(55,h/11)){{ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}}
                if(ring.length){{
                  ctx.beginPath();
                  ring.forEach((p,i)=>{{const q=point(p[0],p[1],w,h);i===0?ctx.moveTo(q[0],q[1]):ctx.lineTo(q[0],q[1]);}});
                  ctx.closePath();ctx.fillStyle='rgba(21,79,95,.72)';ctx.fill();
                  ctx.shadowColor='#31d6ed';ctx.shadowBlur=12;ctx.strokeStyle='#69ddf0';ctx.lineWidth=2;ctx.stroke();ctx.shadowBlur=0;
                }}
                observations.slice(0,4000).forEach(p=>{{
                  const x=Number(p.lon),y=Number(p.lat);if(!Number.isFinite(x)||!Number.isFinite(y))return;
                  const q=point(x,y,w,h);
                  ctx.beginPath();ctx.arc(q[0],q[1],Math.max(2,Math.min(6,Math.sqrt(Math.max(0,Number(p.frp)||0))*.38+2)),0,2*Math.PI);
                  ctx.fillStyle='#ff914e';ctx.fill();
                }});
                ctx.fillStyle='#e2f6ff';ctx.font='bold 17px Arial,sans-serif';ctx.textAlign='left';
                ctx.fillText('URUGUAY · 2D OBSERVATION MAP',20,35);
                ctx.font='12px Arial,sans-serif';ctx.fillStyle='#a8c4d5';
                ctx.fillText('Imported FIRMS thermal anomalies · not confirmed wildfires',20,55);
                ctx.fillText(observations.length.toLocaleString()+' plotted observations · geographic reference outline',20,h-23);
              }}
              paint();
              if(window.ResizeObserver)new ResizeObserver(paint).observe(root);
              const button=document.createElement('button');button.type='button';button.textContent='Retry 3D';
              button.style.cssText='position:absolute;top:18px;right:18px;border:1px solid #5fcadf;background:#10354a;color:#ecfcff;border-radius:4px;padding:9px 12px;cursor:pointer';
              button.onclick=()=>window.location.reload();wrap.appendChild(button);
            }}
            window.__ignisRenderFallback=function(error){{
              if(window.__ignisGlobeReady||window.__ignisGlobeFallbackActive)return;
              window.__ignisGlobeFallbackActive=true;
              console.warn('IGNIS 3D unavailable; using local 2D map',error);
              status.textContent='WebGL unavailable · showing local 2D map';
              status.style.borderColor='#f6ab71';status.style.color='#ffe1c8';
              drawScientificFallback();
            }};
            // Handles failed import maps/CDNs, where a module never reaches its try/catch.
            window.setTimeout(()=>{{
              if(!window.__ignisGlobeReady)window.__ignisRenderFallback('Renderer or dependencies did not become ready');
            }},14000);
          }})();
        </script>
        <script type="importmap">
          {{
            "imports": {{
              "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
              "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
            }}
          }}
        </script>
        <script type="module">
          const payload = {payload};
          const status = document.getElementById('ignis-globe-status');
          const shell = document.getElementById('globe-shell');
          const root = document.getElementById('globe-root');
          const setStatus = (text, level = 'info') => {{
            status.textContent = text;
            status.style.borderColor = level === 'error' ? 'rgba(255, 124, 124, 0.8)' : 'rgba(110, 138, 255, 0.65)';
            status.style.color = level === 'error' ? '#ffd9d9' : '#dfeaff';
            status.style.background = level === 'error' ? 'rgba(44, 12, 14, 0.8)' : 'rgba(8, 16, 30, 0.75)';
          }};

          try {{
            // Catch network/CORS/module failures in this same error boundary.
            const THREE = await import("three");
            const {{ OrbitControls }} = await import("three/addons/controls/OrbitControls.js");
            if (!window.WebGLRenderingContext) {{
              throw new Error('WebGL is not available in this browser.');
            }}
            if (!root || !shell) {{
              throw new Error('The 3D view container is missing.');
            }}
            if (root.clientWidth < 50 || root.clientHeight < 50) {{
              throw new Error('The 3D container has invalid dimensions.');
            }}

            setStatus('Loading map data...');
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x020812);

            const camera = new THREE.PerspectiveCamera(35, root.clientWidth / root.clientHeight, 0.1, 2000);
            camera.position.set(0, 1.2, 6.4);

            const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
            renderer.setPixelRatio(Math.min(window.devicePixelRatio||1, 1.75));
            renderer.setSize(root.clientWidth, root.clientHeight);
            root.appendChild(renderer.domElement);

            const controls = new OrbitControls(camera, renderer.domElement);
          controls.enableDamping = true;
          controls.dampingFactor = 0.06;
          controls.enablePan = false;
          controls.minDistance = 3.1;
          controls.maxDistance = 12;
          controls.enableZoom = true;
          controls.autoRotate = payload.orbit_mode==='illustrative';
          controls.autoRotateSpeed = 0.24;
          controls.target.set(-0.1, -0.25, 0);

          const ambient = new THREE.AmbientLight(0x9bbdff, 1.15);
          scene.add(ambient);

          const sunLight = new THREE.DirectionalLight(0xffffff, 1.8);
          sunLight.position.set(5, 3, 7);
          scene.add(sunLight);

          const starGeometry = new THREE.BufferGeometry();
          const starCount = 2200;
          const starPositions = new Float32Array(starCount * 3);
          for (let i = 0; i < starCount; i++) {{
            const radius = 25 + Math.random() * 18;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            starPositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
            starPositions[i * 3 + 1] = radius * Math.cos(phi);
            starPositions[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta);
          }}
          starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
          const stars = new THREE.Points(starGeometry, new THREE.PointsMaterial({{ color: 0xdfeaff, size: 0.08, transparent: true, opacity: 0.95 }}));
          scene.add(stars);

          const earthGroup = new THREE.Group();
          scene.add(earthGroup);

          // Earth day/night. earth_normal_2048.jpg es un mapa de relieve, NO luces nocturnas.
          const textureLoader = new THREE.TextureLoader();
          textureLoader.setCrossOrigin('anonymous');
          const textureBase = 'https://threejs.org/examples/textures/planets/';
          const blueMarbleUrl = textureBase + 'earth_atmos_4096.jpg';
          const blackMarbleUrl = textureBase + 'earth_lights_2048.png';
          const cloudMapUrl = textureBase + 'earth_clouds_1024.png';
          const earthView = payload.earth_visualization || 'Blue Marble + Black Marble';
          function solidTex(color) {{
            const tex = new THREE.DataTexture(new Uint8Array(color), 1, 1, THREE.RGBFormat);
            tex.colorSpace = THREE.SRGBColorSpace;
            tex.needsUpdate = true;
            return tex;
          }}
          const globeUniforms = {{
            dayMap: {{value:solidTex([30,83,128])}},
            nightMap: {{value:solidTex([2,4,10])}},
            sunDirection: {{value:sunLight.position.clone().normalize()}},
            mode: {{value:earthView === 'Blue Marble (day)' ? 1 :
                    earthView === 'Black Marble (night)' ? 2 : 0}}
          }};
          const earth = new THREE.Mesh(
            new THREE.SphereGeometry(2.2, 128, 128),
            new THREE.ShaderMaterial({{
              uniforms: globeUniforms,
              vertexShader:
                'varying vec2 vMapUV; varying vec3 vNormalWorld;' +
                'void main() {{ vMapUV=uv;' +
                'vNormalWorld=normalize(mat3(modelMatrix)*normal);' +
                'gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }}',
              fragmentShader:
                'uniform sampler2D dayMap; uniform sampler2D nightMap;' +
                'uniform vec3 sunDirection; uniform int mode;' +
                'varying vec2 vMapUV; varying vec3 vNormalWorld;' +
                'void main() {{' +
                'vec3 day=texture2D(dayMap,vMapUV).rgb;' +
                'vec3 night=texture2D(nightMap,vMapUV).rgb;' +
                'float solar=dot(normalize(vNormalWorld),normalize(sunDirection));' +
                'float light=smoothstep(-0.12,0.22,solar);' +
                'vec3 dayLit=day*(0.25+0.75*max(solar,0.0));' +
                'vec3 nightLit=night*1.70+day*0.035;' +
                'vec3 rgb=mix(nightLit,dayLit,light);' +
                'if(mode==1)rgb=day*0.95;' +
                'if(mode==2)rgb=night*1.70+day*0.015;' +
                'gl_FragColor=vec4(rgb,1.0);\\n' +
                '#include <tonemapping_fragment>\\n' +
                '#include <colorspace_fragment>\\n' +
                '}}'
            }})
          );
          earthGroup.add(earth);
          let textureCount=0;
          let textureFailures=0;
          let sceneReady=false;
          function reportSceneStatus(){{
            if(!sceneReady)return;
            const incomplete=textureFailures>0 || textureCount<2;
            setStatus(incomplete?'3D active with fallback visuals':'3D ready · Earth textures loaded');
          }}
          function loadGlobeTexture(url,key){{
            textureLoader.load(url,(image)=>{{
              image.colorSpace=THREE.SRGBColorSpace;
              image.anisotropy=Math.min(renderer.capabilities.getMaxAnisotropy(),8);
              globeUniforms[key].value=image;
              globeUniforms[key].value.needsUpdate=true;
              textureCount++;
              reportSceneStatus();
            }},undefined,()=>{{
              textureFailures++;
              reportSceneStatus();
            }});
          }}
          loadGlobeTexture(blueMarbleUrl,'dayMap');
          loadGlobeTexture(blackMarbleUrl,'nightMap');
          if (payload.show_clouds !== false) {{
            textureLoader.load(cloudMapUrl,(cloudTex) => {{
              cloudTex.colorSpace = THREE.SRGBColorSpace;
              const clouds = new THREE.Mesh(
                new THREE.SphereGeometry(2.215,96,96),
                new THREE.MeshBasicMaterial({{
                  map:cloudTex,transparent:true,opacity:0.20,
                  side:THREE.FrontSide,depthWrite:false
                }})
              );
              clouds.renderOrder=2;
              earthGroup.add(clouds);
            }},undefined,() => {{}});
          }}
          const atmosphere = new THREE.Mesh(
            new THREE.SphereGeometry(2.35,96,96),
            new THREE.MeshPhongMaterial({{
              color:0x4da4ff,transparent:true,opacity:0.13,
              side:THREE.BackSide,depthWrite:false
            }})
          );
          earthGroup.add(atmosphere);

          function latLonToVector3(lat, lon, radius) {{
            const phi = (90 - lat) * Math.PI / 180;
            const theta = (lon + 180) * Math.PI / 180;
            return new THREE.Vector3(
              -(radius * Math.sin(phi) * Math.cos(theta)),
              radius * Math.cos(phi),
              radius * Math.sin(phi) * Math.sin(theta)
            );
          }}

          const showSatellites = payload.show_satellites !== false;
          const showOrbits = payload.show_orbits !== false;
          const showHotspots = payload.show_hotspots !== false;
          const showBounds = payload.show_bounds !== false;

          if (showBounds) {{
            const fallbackOutline = [
              [-58.4, -34.9], [-58.1, -34.2], [-57.2, -33.5], [-56.4, -32.8], [-55.8, -32.0],
              [-54.7, -31.6], [-54.3, -32.2], [-54.7, -33.0], [-55.5, -34.0], [-56.1, -34.8]
            ];
            const ring = (Array.isArray(payload.outline) && payload.outline.length > 3)
              ? payload.outline : fallbackOutline;
            const uruguayPoints = ring.map(([lon, lat]) => latLonToVector3(lat, lon, 2.205));
            uruguayPoints.push(uruguayPoints[0].clone());
            const outline = new THREE.BufferGeometry().setFromPoints(uruguayPoints);
            const outlineLine = new THREE.Line(
              outline,
              new THREE.LineBasicMaterial({{ color: 0x7ad9ff, transparent: true, opacity: 0.8 }})
            );
            earthGroup.add(outlineLine);
          }}

          // Anillos esquemáticos, SOLO cuando CelesTrak/SGP4 no aporta trayectoria.
          // No son órbitas verificadas ni posiciones de la fecha histórica FIRMS.
          function schematicOrbit(index) {{
            const r = 2.55;
            const inclination = 98 * Math.PI / 180;
            const node = index * Math.PI * 2 / 5;
            const result = [];
            for (let i = 0; i <= 128; i++) {{
              const t = (i / 128) * Math.PI * 2;
              const point = new THREE.Vector3(
                r * Math.sin(t) * Math.sin(inclination),
                r * Math.cos(t),
                r * Math.sin(t) * Math.cos(inclination)
              );
              point.applyAxisAngle(new THREE.Vector3(0, 1, 0), node);
              result.push(point);
            }}
            return result;
          }}

          function makeSatelliteLabel(label, colorString) {{
            const canvas = document.createElement('canvas');
            canvas.width = 512;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = 'rgba(3,12,25,.89)';
            ctx.beginPath();
            ctx.roundRect(6,8,500,108,18);
            ctx.fill();
            ctx.lineWidth = 5;
            ctx.strokeStyle = colorString;
            ctx.stroke();
            ctx.fillStyle = '#f2f9ff';
            ctx.font = 'bold 48px Arial, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(label,256,64,465);
            const texture = new THREE.CanvasTexture(canvas);
            texture.colorSpace=THREE.SRGBColorSpace;
            const sprite = new THREE.Sprite(new THREE.SpriteMaterial({{
              map:texture,transparent:true,depthTest:true,depthWrite:false
            }}));
            sprite.scale.set(.96,.24,1);
            return sprite;
          }}
          let illustrativeOrbits=0;
          let tleOrbits=0;
          const movers=[];
          const orbitalRecords=Array.isArray(payload.satellites)?payload.satellites:[];
          // Must be in the module's top-level scene scope, NOT inside forEach.
          // The playback controls and animation loop use these same references.
          const scientific=payload.orbit_mode==='sgp4';
          const selectedUtc=payload.orbit_clock_mode==='selected_utc';
          const selectedMs=Date.parse(payload.orbit_reference_utc||'');
          const referenceUtcMs=()=>selectedUtc&&Number.isFinite(selectedMs)?selectedMs:Date.now();
          document.getElementById('ignis-current').textContent=selectedUtc?'Selected UTC':'Current UTC';
          if(showSatellites||showOrbits){{
            orbitalRecords.forEach((sat,index)=>{{
              const valid=scientific&&sat.mode==='sgp4'&&
                Array.isArray(sat.positions)&&sat.positions.length>=2;
              const demo=payload.orbit_mode==='illustrative';
              if(!valid&&!demo)return; // Never fabricate real-mode positions.
              const color=new THREE.Color(sat.color);
              const points=valid? sat.positions.map((p)=>latLonToVector3(
                p.lat,p.lon,2.2*(1+Math.max(0,Number(p.alt_km)||0)/6378.137)
              )):schematicOrbit(index);
              let orbitLine=null;
              if(showOrbits){{
                const geometry=new THREE.BufferGeometry().setFromPoints(points);
                const material=demo?
                  new THREE.LineDashedMaterial({{color,transparent:true,opacity:.48,dashSize:.08,gapSize:.09}}):
                  new THREE.LineBasicMaterial({{color,transparent:true,opacity:.73}});
                const line=new THREE.Line(geometry,material);
                if(demo)line.computeLineDistances();
                earthGroup.add(line);orbitLine=line;
                if(demo)illustrativeOrbits++;else tleOrbits++;
              }}
              if(showSatellites&&points.length){{
                const marker=new THREE.Group();
                marker.add(new THREE.Mesh(
                  new THREE.BoxGeometry(.09,.065,.13),
                  new THREE.MeshStandardMaterial({{color:0xdbe8f6,metalness:.72,roughness:.28}})
                ));
                const panelMaterial=new THREE.MeshStandardMaterial({{
                  color:0x174f9e,metalness:.52,roughness:.33,emissive:0x092250,emissiveIntensity:.4}});
                for(const side of [-1,1]){{
                  const panel=new THREE.Mesh(new THREE.BoxGeometry(.19,.015,.075),panelMaterial);
                  panel.position.x=side*.145;marker.add(panel);
                }}
                marker.position.copy(points[0]);earthGroup.add(marker);
                const labelText=sat.name.replace(' (MODIS)','').replace(' (VIIRS)','');
                const label=makeSatelliteLabel(labelText,sat.color);
                label.position.copy(points[0]).multiplyScalar(1.06);
                label.position.y+=.10;earthGroup.add(label);
                movers.push({{marker,label,points,sat,orbitLine,schematic:demo,
                  phase:demo?((index*.18+.07)%1):0,
                  times:valid?sat.positions.map(p=>Date.parse(p.t)):[]}});
              }}
            }});
          }}

          let hotspotMesh = null;
          if (showHotspots && payload.hotspots && payload.hotspots.length) {{
            // Una sola InstancedMesh: columnas apoyadas en la superficie, altura ∝ FRP.
            const items = payload.hotspots;
            const columnGeometry = new THREE.CylinderGeometry(0.008, 0.014, 1, 6, 1, false);
            columnGeometry.translate(0, 0.5, 0);
            hotspotMesh = new THREE.InstancedMesh(
              columnGeometry,
              new THREE.MeshBasicMaterial({{ color: 0xffffff, transparent: true, opacity: 0.95 }}),
              items.length
            );
            const upAxis = new THREE.Vector3(0, 1, 0);
            const dummy = new THREE.Object3D();
            items.forEach((point, i) => {{
              const normal = latLonToVector3(point.lat, point.lon, 1).normalize();
              const frp = Math.min(Math.max(Number(point.frp) || 0, 0), 300);
              dummy.position.copy(normal).multiplyScalar(2.2);
              dummy.quaternion.setFromUnitVectors(upAxis, normal);
              dummy.scale.set(1, 0.05 + (frp / 300) * 0.40, 1);
              dummy.updateMatrix();
              hotspotMesh.setMatrixAt(i, dummy.matrix);
              hotspotMesh.setColorAt(i, new THREE.Color(point.color));
            }});
            hotspotMesh.instanceMatrix.needsUpdate = true;
            if (hotspotMesh.instanceColor) hotspotMesh.instanceColor.needsUpdate = true;
            earthGroup.add(hotspotMesh);
          }}

          // Tooltip: se ignoran columnas ocultas detrás de la Tierra.
          const tip = document.getElementById('ignis-tip');
          const raycaster = new THREE.Raycaster();
          const pointer = new THREE.Vector2();
          renderer.domElement.addEventListener('pointermove', (event) => {{
            if (!hotspotMesh) return;
            const rect = renderer.domElement.getBoundingClientRect();
            pointer.set(
              ((event.clientX - rect.left) / rect.width) * 2 - 1,
              -((event.clientY - rect.top) / rect.height) * 2 + 1
            );
            raycaster.setFromCamera(pointer, camera);
            const hit = raycaster.intersectObjects([earth, hotspotMesh], false)[0];
            if (hit && hit.object === hotspotMesh && hit.instanceId !== undefined) {{
              const p = payload.hotspots[hit.instanceId];
              tip.textContent = [
                (p.sensor || 'Sensor ?') + ' · ' + (p.satellite || ''),
                'FRP: ' + (Number(p.frp) || 0).toFixed(1) + ' MW',
                'Confidence: ' + (p.confidence || '—'),
                (p.date || '').replace('T', ' ').slice(0, 16) + ' UTC',
                p.lat.toFixed(3) + ', ' + p.lon.toFixed(3)
              ].join('\\n');
              tip.style.left = (event.clientX - rect.left + 14) + 'px';
              tip.style.top = (event.clientY - rect.top + 14) + 'px';
              tip.style.display = 'block';
            }} else {{
              tip.style.display = 'none';
            }}
          }});

          const region = payload.region || 'global';
          if (region === 'uruguay') {{
            camera.position.set(0.9, 1.4, 5.5);
            controls.target.set(-0.2, -0.2, 0.1);
          }} else if (region === 'south_america') {{
            camera.position.set(1.9, 0.8, 5.4);
            controls.target.set(-0.6, -0.2, 0.1);
          }} else {{
            camera.position.set(0, 1.2, 6.4);
            controls.target.set(0, 0, 0);
          }}
          controls.update();

          const onResize = () => {{
            const width = root.clientWidth || 900;
            const height = root.clientHeight || 640;
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
            renderer.setSize(width, height);
          }};
          window.addEventListener('resize', onResize);
          onResize();
          setTimeout(() => {{
            onResize();
            renderer.render(scene, camera);
          }}, 180);

          setStatus('Initializing 3D · optional textures are loading…');

          /* Scientific mode and last/next crossing replay use the SAME UTC
             timestamped ephemerides as the Uruguay mission-control scene. */
          const scientific=payload.orbit_mode==='sgp4';
          let playing=!scientific,orbitT=0,orbitSpeed=1;
          let orbitalUtcMs=referenceUtcMs(),replayKind='current',replayTrack=null;
          let replaySelected=0;
          const orbitClock=document.getElementById('ignis-orbit-clock');
          const playButton=document.getElementById('ignis-play');
          const speedSelect=document.getElementById('ignis-speed');
          const satSelect=document.getElementById('ignis-tracked-sat');
          orbitalRecords.forEach((sat,index)=>{{
            const opt=document.createElement('option');opt.value=String(index);
            opt.textContent=sat.name+' · '+(sat.mode==='sgp4'?'SGP4':'unavailable');
            satSelect.appendChild(opt);
          }});
          if(!orbitalRecords.length){{
            const opt=document.createElement('option');opt.textContent='No satellite records';
            satSelect.appendChild(opt);
          }}
          if(orbitalRecords.length){{
            replaySelected=Math.max(0,orbitalRecords.findIndex(s=>s.mode==='sgp4'));
            satSelect.value=String(replaySelected);
          }}
          function trackedSat(){{return orbitalRecords[replaySelected]||null;}}
          function trackedPass(kind){{
            const sat=trackedSat();return scientific&&sat&&sat.mode==='sgp4'?sat[kind+'_pass']:null;
          }}
          function updatePassControls(){{
            document.getElementById('ignis-last-pass').disabled=!trackedPass('last');
            document.getElementById('ignis-next-pass').disabled=!trackedPass('next');
            document.getElementById('ignis-current').disabled=!scientific;
            playButton.disabled=scientific&&replayKind==='current';
            speedSelect.disabled=scientific&&replayKind==='current';
            if(!scientific)playButton.textContent=playing?'⏸ Pause':'▶ Play';
            else playButton.textContent=replayKind==='current'?'Current UTC':playing?'⏸ Pause':'▶ Play';
          }}
          function replayPass(kind){{
            const pass=trackedPass(kind);
            if(!pass||!Array.isArray(pass.track)||pass.track.length<2)return;
            replayKind=kind;
            replayTrack=pass.track.map(p=>({{
              t:Date.parse(p.t),
              pos:latLonToVector3(p.lat,p.lon,2.2*(1+Math.max(0,p.alt_km)/6378.137))
            }}));
            orbitalUtcMs=replayTrack[0].t;playing=true;
            movers.forEach(m=>{{
              if(!m.orbitLine)return;
              const same=m.sat===trackedSat();
              m.orbitLine.visible=same;
              if(same){{
                m.orbitLine.geometry.dispose();
                m.orbitLine.geometry=new THREE.BufferGeometry().setFromPoints(replayTrack.map(p=>p.pos));
              }}
            }});
            updatePassControls();
          }}
          function restoreCurrent(){{
            replayKind='current';replayTrack=null;orbitalUtcMs=referenceUtcMs();playing=false;
            movers.forEach(m=>{{
              if(!m.orbitLine)return;
              m.orbitLine.geometry.dispose();
              m.orbitLine.geometry=new THREE.BufferGeometry().setFromPoints(m.points);
              m.orbitLine.visible=true;
            }});
            updatePassControls();
          }}
          document.getElementById('ignis-last-pass').onclick=()=>replayPass('last');
          document.getElementById('ignis-next-pass').onclick=()=>replayPass('next');
          document.getElementById('ignis-current').onclick=restoreCurrent;
          satSelect.onchange=()=>{{replaySelected=Number(satSelect.value)||0;restoreCurrent();}};
          playButton.onclick=()=>{{if(scientific&&replayKind==='current')return;
            playing=!playing;updatePassControls();}};
          speedSelect.onchange=()=>{{orbitSpeed=Number(speedSelect.value)||1;}};
          updatePassControls();
          function interpolateTime(points,times,ms){{
            if(!points.length||ms<times[0]||ms>times[times.length-1])return null;
            let lo=0,hi=times.length-1;
            while(lo<hi){{const mid=(lo+hi)>>1;if(times[mid]<ms)lo=mid+1;else hi=mid;}}
            if(lo===0)return points[0];
            const a=times[lo-1],b=times[lo];
            return points[lo-1].clone().lerp(points[lo],b===a?0:(ms-a)/(b-a));
          }}
          function updateMovers(){{
            movers.forEach(m=>{{
              let pos=null;
              if(m.schematic){{
                const n=m.points.length;
                pos=m.points[Math.min(n-1,Math.floor(((orbitT+m.phase)%1)*(n-1)))];
              }}else if(replayKind==='current'){{
                pos=interpolateTime(m.points,m.times,orbitalUtcMs);
              }}else if(m.sat===trackedSat()&&replayTrack){{
                pos=interpolateTime(replayTrack.map(p=>p.pos),replayTrack.map(p=>p.t),orbitalUtcMs);
              }}
              const visible=!!pos;
              m.marker.visible=visible;m.label.visible=visible;
              if(!visible)return;
              m.marker.position.copy(pos);
              m.label.position.copy(pos).multiplyScalar(1.06);
              m.label.position.y+=.10;
            }});
            const sat=trackedSat();
            if(!scientific){{
              orbitClock.textContent='ILLUSTRATIVE MOTION · NOT REAL UTC TRACKING';
            }}else if(!sat||sat.mode!=='sgp4'){{
              orbitClock.textContent='Verified orbital position unavailable · '+(sat?.status||'No suitable TLE');
            }}else{{
              const prefix=replayKind==='current'?(selectedUtc?'SGP4 selected UTC estimate':'SGP4 current UTC estimate'):
                replayKind==='last'?'Last ground-track replay':'Next ground-track replay';
              orbitClock.textContent=prefix+' · '+new Date(orbitalUtcMs).toISOString().replace('.000Z','Z')+
                ' · TLE epoch '+(sat.tle_epoch||'unknown')+' · NOT verified sensor coverage';
            }}
          }}
          let priorFrame=performance.now();
          function animate(){{
            requestAnimationFrame(animate);
            const now=performance.now(),delta=Math.min(0.12,(now-priorFrame)/1000);
            priorFrame=now;
            if(scientific){{
              if(replayKind==='current')orbitalUtcMs=referenceUtcMs();
              else if(playing&&replayTrack){{
                orbitalUtcMs+=delta*1000*orbitSpeed;
                const end=replayTrack[replayTrack.length-1].t;
                if(orbitalUtcMs>=end){{orbitalUtcMs=end;playing=false;updatePassControls();}}
              }}
            }}else if(playing&&movers.length){{
              orbitT=(orbitT+delta*.025*orbitSpeed)%1;
            }}
            updateMovers();
            controls.update();
            renderer.render(scene,camera);
          }}
          animate();
          const orbitStatus = (showOrbits && illustrativeOrbits > 0)
            ? ' · illustrative orbits ('+illustrativeOrbits+')'
            : (showOrbits && tleOrbits > 0 ? ' · current TLE' : '');
          const shownHotspots = (payload.hotspots || []).length;
          const totalHotspots = Number(payload.hotspots_total) || shownHotspots;
          const hotspotNote = (showHotspots && totalHotspots > shownHotspots)
            ? ' · hotspots: ' + shownHotspots + ' of ' + totalHotspots + ' (highest FRP)'
            : (showHotspots && shownHotspots ? ' · hotspots: ' + shownHotspots : '');
          sceneReady=true;
          window.__ignisGlobeReady=true;
          renderer.render(scene,camera);
          reportSceneStatus();
          }} catch (error) {{
            console.error('IGNIS 3D error:', error);
            const message = error && error.message ? error.message : 'Unknown error while initializing the 3D view.';
            setStatus('Error 3D: ' + message, 'error');
            window.__ignisRenderFallback?.(message);
          }}
        </script>
      </body>
    </html>
    """


def render_ignis_space_module(df: Optional[pd.DataFrame]) -> None:
    """Espacio inmersivo: globo protagonista, controles laterales y fecha inferior."""
    st.markdown("""
    <style>
    .ignis-space-kicker{font-size:.76rem;font-weight:800;letter-spacing:.13em;
      color:#4fd1eb;text-transform:uppercase;margin-bottom:.4rem}
    .ignis-space-subtitle{color:#b5d1e3;font-size:.92rem;line-height:1.55;
      margin-bottom:1.1rem}
    .ignis-orbit-guide{background:linear-gradient(135deg,#102a45,#0b1b30);
      border:1px solid #326180;border-radius:14px;padding:13px 15px;
      font-size:.81rem;color:#c6deec;line-height:1.55}
    .ignis-orbit-guide strong{color:#f2fbff}
    </style>
    <div class="ignis-space-kicker">Geospatial explorer · NASA FIRMS</div>
    <div class="ignis-space-subtitle">Navigate around Earth, compare
    MODIS–VIIRS observations and explore satellite trajectories.
    Illustrative orbits do not represent actual historical passes.</div>
    """, unsafe_allow_html=True)

    frame = _normalize_fire_frame(df)
    date_options = sorted(pd.to_datetime(frame["fecha"], utc=True).dt.date.unique())

    # La columna principal reserva el espacio del globo ANTES de mostrar
    # la línea temporal. El iframe se rellena luego de leer los filtros.
    controls_col, globe_col = st.columns([1, 3.1], gap="medium")
    with globe_col:
        globe_slot = st.empty()
        with st.container(border=True):
            st.caption("TIMELINE · FIRMS OBSERVATIONS")
            if date_options:
                selected_date = st.select_slider(
                    "Observation date", options=date_options,
                    value=date_options[-1], key="ignis_space_date",
                )
            else:
                selected_date = None
                st.caption("No dates uploaded. You can explore the globe without observations.")
            st.caption("The date changes thermal hotspots, not current TLE data.")

    with controls_col:
        with st.container(border=True):
            st.markdown("#### 🛰️ Orbital explorer")
            st.caption("Configure globe layers.")
            selected_region = st.selectbox(
                "Geographic focus",
                options=["uruguay", "south_america", "global", "selected"],
                index=0, key="ignis_space_region",
                format_func=lambda item: {
                    "uruguay": "🇺🇾 Uruguay",
                    "south_america": "🌎 South America",
                    "global": "🌍 Full Earth",
                    "selected": "📍 Selected area",
                }.get(item, item),
            )
            options = ["All"] + sorted(
                frame["satellite"].dropna().astype(str).unique().tolist()
            )
            selected_satellite = st.selectbox(
                "Filter observations", options=options, index=0,
                key="ignis_space_satellite",
            )
            st.caption("VISIBLE LAYERS")
            show_satellites = st.checkbox(
                "Satellites", value=True, key="ignis_space_show_satellites")
            show_orbits = st.checkbox(
                "Orbits", value=True, key="ignis_space_show_orbits")
            show_hotspots = st.checkbox(
                "Thermal hotspots", value=True, key="ignis_space_show_hotspots")
            show_bounds = st.checkbox(
                "Geographic boundaries", value=True, key="ignis_space_show_bounds")
            show_clouds = st.checkbox(
                "Thin clouds", value=True, key="ignis_space_show_clouds")
            earth_visualization = st.selectbox(
                "Earth imagery",
                ["Blue Marble + Black Marble", "Blue Marble (day)", "Black Marble (night)"],
                index=0, key="ignis_space_earth_style",
                help="Static compositions, not real-time Earth imagery.",
            )
            orbit_mode = st.radio(
                "Trajectory source",
                ["Illustrative trajectories", "Current TLE data"],
                index=1, key="ignis_orbit_source",
                help="Current TLE data cannot reconstruct orbits on historical FIRMS observation dates.",
            )

            st.caption("The FIRMS observation date does not change orbital UTC.")
            orbit_clock_mode = st.radio(
                "Orbital UTC clock", ["Current UTC", "Selected UTC"],
                index=0, key="ignis_orbit_clock_mode",
                help="Use a current TLE only near its epoch. Distant historical dates require archived elements.",
            )
            if orbit_clock_mode == "Selected UTC":
                now_utc = datetime.now(timezone.utc)
                orbital_date = st.date_input(
                    "Orbital date (UTC)", now_utc.date(), key="ignis_orbit_custom_date")
                orbital_time = st.time_input(
                    "Orbital time (UTC)", now_utc.time().replace(microsecond=0),
                    key="ignis_orbit_custom_time")
                st.session_state["ignis_orbit_selected_utc"] = datetime.combine(
                    orbital_date, orbital_time, tzinfo=timezone.utc).isoformat()
                st.caption("A historical TLE archive is not connected. Distant dates correctly show unavailable.")
            else:
                st.session_state.pop("ignis_orbit_selected_utc", None)

        with st.container(border=True):
            st.caption("DATA LOADED IN THIS SESSION")
            q1, q2 = st.columns(2, gap="small")
            q1.metric("Records", f"{len(frame):,}" if len(frame) else "—")
            q2.metric("Dates", len(date_options))
            q3, q4 = st.columns(2, gap="small")
            q3.metric("Sensors", frame["instrumento"].nunique() if len(frame) else "—")
            q4.metric("Orbit mode", "TLE" if orbit_mode == "Current TLE data" else "Illustrative")
        st.markdown(
            '<div class="ignis-orbit-guide"><strong>How to interpret the lines</strong>'
            '<p>— Solid: trajectory calculated from recent TLE data, when available.'
            '<p>┄ Dotted: illustrative visualization, not a validated orbit.'
            '<p>Orange points represent thermal anomalies, not confirmed wildfires.'
            '</div>', unsafe_allow_html=True,
        )

    filtered_frame = frame.copy()
    filtered_frame["fecha"] = pd.to_datetime(filtered_frame["fecha"], utc=True)
    if selected_date is not None:
        filtered_frame = filtered_frame[
            filtered_frame["fecha"].dt.date == selected_date
        ]
    else:
        filtered_frame = filtered_frame.iloc[0:0]
    if selected_satellite != "All":
        filtered_frame = filtered_frame[
            filtered_frame["satellite"].str.contains(
                selected_satellite, case=False, na=False)
        ]
    hotspots = _build_hotspot_payload(
        filtered_frame, selected_date=selected_date,
        satellite_filter=selected_satellite,
    )

    # Shared SGP4 source for both 3D views. FIRMS historical dates are separate.
    from ignis_orbits import shared_bundle
    use_live_tle = orbit_mode == "Current TLE data"
    if use_live_tle:
        bundle = shared_bundle()
        satellites = [
            {
                "name": item["name"], "sensor": item["sensor"],
                "color": item["color"], "mode": item["mode"],
                "positions": item["track"],
                "last_pass": item["last_pass"], "next_pass": item["next_pass"],
                "source": item["source"], "tle_epoch": item.get("tle_epoch"),
                "status": item.get("status", "Unavailable"),
            }
            for item in bundle["satellites"]
        ]
    else:
        # Explicit illustrative opt-in only. Never attach a real pass timestamp.
        bundle = {"reference_utc": None, "pass_definition": "illustrative demo"}
        satellites = [
            {**item, "mode": "illustrative", "last_pass": None,
             "next_pass": None, "tle_epoch": None}
            for item in _build_satellite_payload(use_live_tle=False)
        ]

    config = {
        "region": selected_region,
        "show_satellites": show_satellites,
        "show_orbits": show_orbits,
        "show_hotspots": show_hotspots,
        "show_bounds": show_bounds,
        "show_clouds": show_clouds,
        "earth_visualization": earth_visualization,
        "satellites": satellites,
        "orbit_mode": "sgp4" if use_live_tle else "illustrative",
        "orbit_reference_utc": bundle["reference_utc"],
        "orbit_clock_mode": bundle.get("clock_mode", "current_utc"),
        "hotspots": hotspots,
        "hotspots_total": int(len(filtered_frame)),
        "outline": _uruguay_outline(),
    }

    with globe_slot:
        components.html(_render_globe_html(config), height=690, scrolling=False)

    with globe_col:
        count = len(filtered_frame)
        st.caption(
            f"**{count:,} thermal observations** for the selected date and sensor. "
            "Orbit mode: current TLE estimates by default; optionally illustrative "
            "trajectories. Drag to rotate the globe and scroll "
            "to zoom in."
        )
        if not frame.empty and frame["frp"].notna().any():
            with st.expander("View observations for the selected date", expanded=False):
                fields = ["fecha", "latitude", "longitude", "instrumento",
                          "satellite", "frp", "confidence"]
                display_dataframe(filtered_frame[fields], use_container_width=True,
                             hide_index=True, height=260)

    st.caption(
        "Blue Marble and night lights are static visualizations, not live images "
        "or imagery from the selected date. TLE trajectories are "
        "current approximations and do not correspond to historical FIRMS dates. "
        "Dotted trajectories are illustrative. IGNIS does not issue official alerts."
    )
