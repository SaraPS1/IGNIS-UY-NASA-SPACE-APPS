"""3D migration and orbital UI tests, without external satellite requests."""
from __future__ import annotations
import ast
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ignis_spatial import to_scene_frame

ROOT = Path(__file__).resolve().parents[1]


class Spatial3DTests(unittest.TestCase):
    def test_nrt_import_uses_real_timestamp_and_coordinates(self):
        data = pd.DataFrame([
            {"adquisicion_utc": "2026-11-14T14:52:00Z",
             "latitude": -33.1, "longitude": -56.6,
             "producto": "VIIRS NOAA-21", "satellite": "NOAA-21", "frp": 12.3},
            {"adquisicion_utc": "2026-11-14T14:52:00Z",
             "latitude": 999, "longitude": -56.6, "producto": "VIIRS NOAA-21"},
        ])
        result = to_scene_frame(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["instrumento"], "VIIRS NOAA-21")
        self.assertEqual(result.iloc[0]["satellite"], "NOAA-21")
        self.assertEqual(result.iloc[0]["frp"], 12.3)
        self.assertEqual(result.iloc[0]["fecha"].isoformat(), "2026-11-14T14:52:00+00:00")

    def test_fusion_import_retains_real_coordinates(self):
        data = pd.DataFrame([
            {"fecha_utc": "2025-09-01 12:00", "lat": -31.5, "lon": -55.9,
             "instrumento": "MODIS", "frp": 28.5},
        ])
        result = to_scene_frame(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(float(result.iloc[0]["longitude"]), -55.9)
        self.assertEqual(result.iloc[0]["instrumento"], "MODIS")
        self.assertTrue(pd.isna(result.iloc[0]["satellite"]))

    def test_invalid_observation_is_never_filled_in(self):
        data = pd.DataFrame({"fecha_utc": ["invalid"], "lat": [-33.0],
                             "lon": [-56.0], "frp": [10]})
        self.assertTrue(to_scene_frame(data).empty)
        self.assertTrue(to_scene_frame(None).empty)

    def test_shared_scene_on_all_relevant_maps(self):
        for file in ("ignis_visual.py","ignis_dashboard.py",
                     "ignis_nrt.py","ignis_fusion_terrestre.py","ignis_historico.py"):
            text = (ROOT / file).read_text(encoding="utf-8")
            with self.subTest(file=file):
                self.assertIn("render_spatial_3d(", text)
        scene = (ROOT / "ignis_spatial.py").read_text(encoding="utf-8")
        self.assertIn("render_uruguay_scene(", scene)
        self.assertIn("to_scene_frame(data)", scene)

    def test_one_shared_utc_backend_for_both_satellite_views(self):
        main = (ROOT / "ignis_scene3d.py").read_text(encoding="utf-8")
        earth = (ROOT / "ignis_espacio.py").read_text(encoding="utf-8")
        self.assertIn("from ignis_orbits import current_bundle", main)
        self.assertIn("from ignis_orbits import current_bundle", earth)
        self.assertIn('payload["orbit"] = current_bundle()', main)
        self.assertIn("bundle = current_bundle()", earth)

    def test_satellites_not_permanently_above_uruguay_in_scientific_mode(self):
        scene = (ROOT / "assets" / "ignis_scene3d.html").read_text(encoding="utf-8")
        self.assertIn("satelliteInViewport(sample.lon,sample.lat)", scene)
        self.assertIn("if(s.mode!=='sgp4'", scene)
        self.assertIn("orbitalMode==='illustrative'", scene)
        self.assertIn("if(!sample||!satelliteInViewport", scene)
        self.assertIn("orbitalTimeMs=Date.now()", scene)
        self.assertIn("replayPass('last')", scene)
        self.assertIn("replayPass('next')", scene)
        self.assertIn("ground-track ≠ sensor coverage", scene)

    def test_globe_html_script_syntax_and_lastpass_consistency(self):
        # Compile _render_globe_html in isolation: no Streamlit UI/network needed.
        path = ROOT / "ignis_espacio.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "_render_globe_html")
        scope = {"Dict": dict, "Any": object, "json": json}
        module = ast.Module(body=[fn], type_ignores=[])
        exec(compile(module, str(path), "exec"), scope)
        html = scope["_render_globe_html"]({
            "region": "uruguay", "show_satellites": True,
            "show_orbits": True, "hotspots": [], "satellites": [],
            "orbit_mode": "sgp4", "outline": []
        })
        for token in ("ignis-last-pass", "ignis-next-pass",
                      "new Date(orbitalUtcMs)", "m.sat===trackedSat()",
                      "m.times", "interpolateTime", "scientific"):
            self.assertIn(token, html)
        if shutil.which("node"):
            script = re.search(r'<script type="module">([\s\S]*?)</script>', html)
            self.assertIsNotNone(script)
            with tempfile.TemporaryDirectory() as d:
                file = Path(d) / "globe.mjs"
                file.write_text(script.group(1), encoding="utf-8")
                result = subprocess.run(["node", "--check", str(file)],
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
