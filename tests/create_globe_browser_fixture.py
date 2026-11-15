"""Generate a clearly labeled synthetic fixture for real globe browser tests."""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SPACE = ROOT / "ignis_espacio.py"


def main():
    tree = ast.parse(SPACE.read_text(encoding="utf-8"))
    function = next(n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == "_render_globe_html")
    scope = {"Dict": dict, "Any": object, "json": json}
    exec(compile(ast.Module(body=[copy.deepcopy(function)], type_ignores=[]),
                 str(SPACE), "exec"), scope)
    config = {
        "region": "uruguay",
        "show_satellites": True, "show_orbits": True, "show_hotspots": True,
        "show_bounds": True, "show_clouds": True,
        "earth_visualization": "Blue Marble + Black Marble",
        "orbit_mode": "sgp4", "orbit_clock_mode": "current_utc",
        "orbit_reference_utc": datetime.now(timezone.utc).isoformat(),
        "satellites": [],
        "hotspots": [
            {"lon": -56.2, "lat": -33.4, "frp": 31.0,
             "date": "2026-11-14", "sensor": "VIIRS", "satellite": "SYNTHETIC"},
            {"lon": -54.9, "lat": -32.2, "frp": 7.4,
             "date": "2026-11-14", "sensor": "MODIS", "satellite": "SYNTHETIC"},
        ],
        "hotspots_total": 2,
        "outline": json.loads((ROOT / "uruguay_contorno.geojson").read_text())["features"][0]["geometry"]["coordinates"][0],
    }
    html = scope["_render_globe_html"](config)
    # Stable local package import paths for deterministic Chrome browser testing.
    html = html.replace("https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
                        "/node_modules/three/build/three.module.js")
    html = html.replace("https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/",
                        "/node_modules/three/examples/jsm/")
    banner = ('<div style="position:fixed;top:1px;left:32%;z-index:200;'
              'padding:5px 12px;background:#762312;border:2px solid #ffad6b;'
              'color:white;font:bold 11px Arial">SYNTHETIC BROWSER TEST · NOT REAL FIRE OBSERVATIONS</div>')
    html = html.replace("<body>", "<body>" + banner, 1)
    path = ROOT / "preview" / "ignis-globe-synthetic.html"
    path.parent.mkdir(exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
