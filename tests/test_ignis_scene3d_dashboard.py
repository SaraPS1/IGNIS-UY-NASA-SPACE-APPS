"""Regression tests for the premium 3D control center.

They verify that the scene payload is built only from supplied records, that
capping never changes the reported figures, that unavailable datasets are
reported instead of invented, and that the HTML document carries the scene,
its controls, the 2D fallback and the scientific disclaimers.
"""
import ast
import json
import re
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import ignis_scene3d as sc

ROOT = Path(__file__).resolve().parents[1]


def frame(n=300, seed=0, start="2004-01-01"):
    rng = np.random.default_rng(seed)
    d = pd.to_datetime(start, utc=True) + pd.to_timedelta(rng.integers(0, 7000, n), unit="D")
    return pd.DataFrame({
        "fecha": d, "latitude": rng.uniform(-34.9, -30.1, n), "longitude": rng.uniform(-58.4, -53.2, n),
        "instrumento": rng.choice(["MODIS", "VIIRS S-NPP"], n), "satellite": rng.choice(["Terra", "N"], n),
        "frp": rng.uniform(1, 90, n), "confidence": "n",
    })


class ScenePayloadTests(unittest.TestCase):
    def test_empty_input_produces_empty_scene_without_fabrication(self):
        p = sc.build_scene_payload(None, None)
        self.assertEqual(p["stats"]["observations"], 0)
        self.assertEqual(p["points"]["lon"], [])
        self.assertEqual(p["grid"], [])
        self.assertEqual(p["yearCounts"], {})
        self.assertFalse(p["liveConnection"])
        self.assertGreater(len(p["outline"]), 3)

    def test_points_match_records_and_families(self):
        df = frame()
        p = sc.build_scene_payload(df, 2010)
        self.assertEqual(p["stats"]["observations"], len(df))
        self.assertEqual(p["stats"]["shown"], len(df))
        self.assertEqual(sum(p["yearCounts"].values()), len(df))
        self.assertEqual(p["stats"]["modis"] + p["stats"]["viirs"], len(df))
        self.assertEqual(set(p["points"]["fam"]), {0, 1})
        self.assertEqual(p["selectedYear"], 2010)
        for y, fams in p["yearFamilyCounts"].items():
            self.assertEqual(sum(fams), p["yearCounts"][y])

    def test_capping_only_limits_markers_not_figures(self):
        df = frame(n=1200, seed=2)
        p = sc.build_scene_payload(df, None, max_points=400)
        self.assertEqual(p["stats"]["observations"], 1200)
        self.assertLessEqual(p["stats"]["shown"], 400)
        self.assertEqual(sum(p["yearCounts"].values()), 1200)
        self.assertEqual(len(p["points"]["lon"]), p["stats"]["shown"])

    def test_invalid_rows_are_dropped_not_repaired(self):
        df = frame(n=20).astype({"fecha": object})
        df.loc[0, "latitude"] = 999
        df.loc[1, "fecha"] = "not a date"
        p = sc.build_scene_payload(df, None)
        self.assertEqual(p["stats"]["observations"], 18)

    def test_departments_absent_means_empty_list(self):
        # The repository ships no verified department polygons: the UI must say so.
        self.assertEqual(sc.load_departments(), [])

    def test_associations_require_expected_columns(self):
        self.assertEqual(sc.associations_payload(pd.DataFrame({"x": [1]})), [])
        assoc = pd.DataFrame({"lat": [-33.0], "lon": [-56.0], "fecha_utc": ["2022-01-01 10:00"], "resultado": ["NASA + ground (review)"],
                              "fuentes": ["Firefighters/PAIF + NASA FIRMS"], "n_firms": [3], "simulado": ["YES — DO NOT USE AS EVIDENCE"]})
        out = sc.associations_payload(assoc)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0]["simulated"])

    def test_recurrence_grid_counts_years(self):
        df = frame(n=50)
        df["year"] = df["fecha"].dt.year
        cells = sc.recurrence_grid(df)
        self.assertTrue(all(len(c) == 4 and c[2] >= 1 and c[3] >= c[2] for c in cells))
        self.assertEqual(sum(c[3] for c in cells), 50)


class SceneHtmlTests(unittest.TestCase):
    def setUp(self):
        self.html = sc.scene_html(sc.build_scene_payload(frame(), 2012))

    def test_payload_is_embedded_and_parseable(self):
        m = re.search(r'<script id="ignis-data" type="application/json">(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(m)
        data = json.loads(m.group(1))
        self.assertEqual(data["stats"]["observations"], 300)

    def test_controls_timeline_fallback_and_disclaimers_present(self):
        for token in ("id=\"tgModis\"", "id=\"tgViirs\"", "id=\"tgGrid\"", "id=\"tgDep\"", "id=\"tgCases\"", "id=\"tgAssoc\"",
                      "id=\"tgBeams\"", "id=\"tgAtmo\"", "id=\"tgOrbits\"", "id=\"tgReduce\"",
                      "id=\"slider\"", "id=\"play\"", "id=\"speed\"", "id=\"radial\"", "id=\"rCine\"", "id=\"rFull\"",
                      "id=\"flat\"", "start2D(", "prefers-reduced-motion", "InstancedMesh",
                      "not confirmed fires", "Illustrative relief", "schematic orbits",
                      "No imported observations for this interval"):
            self.assertIn(token, self.html, token)

    def test_live_badge_only_with_live_connection(self):
        self.assertIn("Historical data", self.html)
        self.assertIn("if (D.liveConnection)", self.html)
        live = sc.scene_html(sc.build_scene_payload(frame(), 2012, live_connection=True))
        self.assertIn('"liveConnection":true', live)

    def test_module_script_is_valid_javascript_shape(self):
        js = re.search(r'<script type="module">(.*?)</script>', self.html, re.S).group(1)
        self.assertEqual(js.count("{"), js.count("}"))
        self.assertEqual(js.count("("), js.count(")"))
        self.assertIn("window.addEventListener('pagehide', dispose", js)
        self.assertIn("webglcontextlost", js)


class DashboardSourceTests(unittest.TestCase):
    def setUp(self):
        self.dash = (ROOT / "ignis_dashboard.py").read_text(encoding="utf-8")
        self.visual = (ROOT / "ignis_visual.py").read_text(encoding="utf-8")
        self.main = (ROOT / "ignis_historico.py").read_text(encoding="utf-8")

    def test_modules_parse(self):
        for name in ("ignis_dashboard.py", "ignis_scene3d.py", "ignis_visual.py", "ignis_historico.py"):
            ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)

    def test_control_center_delegates_to_premium_dashboard(self):
        self.assertIn("def render_control_center", self.visual)
        self.assertIn("render_premium_dashboard", self.visual)
        self.assertIn("render_control_center(combined, sample, selected, BASE, mapa_ignis", self.main)

    def test_no_demo_figures_and_live_only_with_connection(self):
        self.assertIn("No demonstration figures are ever injected", self.dash)
        self.assertIn("'Live' appears only with an actual NRT connection", self.dash)
        self.assertIn("ignis_firms_vivos", self.main)
        self.assertNotIn("Active Detections", self.dash)
        self.assertNotIn("Risk Zones", self.dash)
        self.assertNotIn("Wildfire Probability", self.dash)

    def test_navigation_keeps_fifteen_routes(self):
        tree = ast.parse(self.main)
        nav = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "NAV_PAGES")
        labels = [e.value for e in nav.value.elts]
        self.assertEqual(len(labels), 15)
        for expected in ("Home", "Uruguay Map", "Historical Archive", "MODIS–VIIRS Harmonization", "Alerts & Traceability",
                         "Recent Monitoring", "3D Earth & Satellites", "Satellite–Ground Fusion", "Final Calendar",
                         "PDF Report", "Ask IGNIS", "Team & Contributions"):
            self.assertTrue(any(expected in l for l in labels), expected)

    def test_dashboard_stats_from_records_only(self):
        import importlib, sys, types
        if "streamlit" not in sys.modules:
            stub = types.ModuleType("streamlit"); stub.__getattr__ = lambda k: (lambda *a, **kw: None)
            stub.session_state = {}
            sys.modules["streamlit"] = stub
            comp = types.ModuleType("streamlit.components"); v1 = types.ModuleType("streamlit.components.v1"); v1.html = lambda *a, **k: None
            sys.modules["streamlit.components"] = comp; sys.modules["streamlit.components.v1"] = v1
        dash = importlib.import_module("ignis_dashboard")
        df = frame(n=120)
        df["anio"] = df["fecha"].dt.year; df["mes"] = df["fecha"].dt.month
        stats = dash.dashboard_stats(df, df, 2010, cases=5, associations=0)
        self.assertEqual(stats["obs"]["value"], 120)
        self.assertEqual(stats["modis"]["value"] + stats["viirs"]["value"], 120)
        self.assertEqual(stats["assoc"]["value"], 0)
        empty = dash.dashboard_stats(pd.DataFrame(), pd.DataFrame(), None, cases=0, associations=0)
        self.assertTrue(all(v["value"] == 0 for v in empty.values()))
        html = dash.stats_strip_html(stats)
        self.assertIn('data-v="120"', html)
        self.assertIn("prefers-reduced-motion", html)


if __name__ == "__main__":
    unittest.main()
