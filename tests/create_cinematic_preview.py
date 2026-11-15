"""Create a clearly marked SYNTHETIC browser-test fixture, never production data."""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ignis_scene3d import scene_html, build_scene_payload, load_outline


def main():
    # A deterministic visual fixture within the verified Uruguay outline.
    # Coordinates and observations are deliberately synthetic and should never
    # be mistaken for real FIRMS records.
    rng = np.random.default_rng(1948)
    outline = load_outline()
    xs = np.array([p[0] for p in outline])
    ys = np.array([p[1] for p in outline])

    def inside(x, y):
        result = False
        j = len(outline)-1
        for i, (xi, yi) in enumerate(outline):
            xj, yj = outline[j]
            if (yi > y) != (yj > y) and x < ((xj-xi)*(y-yi)/(yj-yi)+xi):
                result = not result
            j = i
        return result

    data = []
    for idx in range(420):
        for _ in range(300):
            x, y = rng.uniform(xs.min(), xs.max()), rng.uniform(ys.min(), ys.max())
            if inside(x, y):
                break
        else:
            continue
        year = int(rng.choice([2022, 2023, 2024, 2025, 2026]))
        family = "MODIS" if idx%3==0 else "VIIRS"
        dt = datetime(year, int(rng.integers(1, 13)), 1, tzinfo=timezone.utc)+timedelta(days=int(rng.integers(0, 25)))
        data.append({
            "fecha": dt,
            "latitude": y, "longitude": x,
            "instrumento": family, "satellite": "Terra" if family == "MODIS" else "NOAA-20",
            "frp": round(float(rng.gamma(2, 15)), 2), "confidence": "SYNTHETIC",
        })
    html = scene_html(build_scene_payload(pd.DataFrame(data), 2026))
    # Strong, persistent disclosure on top of all scene content.
    banner = (
        '<div style="position:fixed;z-index:100;right:18px;top:12px;'
        'background:#702119;color:white;border:2px solid #ff995f;'
        'padding:9px 12px;font:bold 12px Arial,sans-serif;letter-spacing:.04em;">'
        'SYNTHETIC VISUAL TEST · NOT REAL FIRE DETECTIONS</div>'
    )
    html = html.replace('<body>', '<body>' + banner, 1)
    out = ROOT / "preview" / "ignis-cinematic-visual-test.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
