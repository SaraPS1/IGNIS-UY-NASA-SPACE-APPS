"""Regression checks for the cinematic, data-grounded IGNIS mission deck."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ignis_scene3d import build_scene_payload, scene_html

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "ignis_scene3d.html"


class CinematicObservatoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = ASSET.read_text(encoding="utf-8")
        cls.app_source = (ROOT / "ignis_historico.py").read_text(encoding="utf-8")
        cls.dashboard_source = (ROOT / "ignis_dashboard.py").read_text(encoding="utf-8")

    def test_real_3d_and_progressive_fallback(self):
        for feature in (
            "THREE.WebGLRenderer", "THREE.ExtrudeGeometry", "InstancedMesh",
            "OrbitControls", "function start2D(", "function resize()",
            "pagehide", "webglcontextlost", "prefers-reduced-motion",
        ):
            with self.subTest(feature=feature):
                self.assertIn(feature, self.template)

    def test_cinematic_mission_deck_is_real_interaction(self):
        for item in (
            'id="mission"', 'id="mission-year"', 'id="mission-bars"',
            'id="mission-count"', 'id="mission-split"',
            'id="mission-tour"', 'id="mission-focus"',
            "function currentCounts()", "function updateMission()",
            "function signalOrder()", "function nextTourStep()",
            "focusSignal(tourQueue[tourStep++],true)",
            "setTimeout(nextTourStep,3600)",
        ):
            with self.subTest(item=item):
                self.assertIn(item, self.template)

    def test_tour_uses_only_active_imported_points(self):
        # Do not create invented hot spots, hazard scores, or operational alerts.
        self.assertIn("activeIndices().slice().sort(", self.template)
        self.assertIn("P.frp[b]", self.template)
        self.assertIn("toXZ(P.lon[i],P.lat[i])", self.template)
        self.assertIn("Imported thermal anomalies, not confirmed wildfires", self.template)
        self.assertNotIn("Risk probability", self.template)
        self.assertNotIn("Active fire detected", self.template)

    def test_imported_text_is_escaped_in_html_tooltips(self):
        self.assertIn("function esc(value)", self.template)
        self.assertIn("esc(P.inst[i]", self.template)
        self.assertIn("esc(P.conf[i])", self.template)
        self.assertIn("esc(c.name)", self.template)
        self.assertIn("esc(a.result)", self.template)

    def test_observation_count_comes_from_records(self):
        sample = pd.DataFrame([
            {"fecha": "2024-03-01", "latitude": -32.9, "longitude": -56.0, "instrumento": "MODIS", "satellite": "Terra", "frp": 14, "confidence": "n"},
            {"fecha": "2025-05-02", "latitude": -34.0, "longitude": -55.1, "instrumento": "VIIRS", "satellite": "NOAA-20", "frp": 18, "confidence": "h"},
            {"fecha": "2025-06-01", "latitude": -34.1, "longitude": -55.3, "instrumento": "VIIRS", "satellite": "NOAA-20", "frp": 25, "confidence": "h"},
        ])
        p = build_scene_payload(sample, 2025)
        self.assertEqual(p["yearCounts"], {2024: 1, 2025: 2})
        self.assertEqual(p["yearFamilyCounts"][2025][1], 2)
        html = scene_html(p)
        match = re.search(r'<script id="ignis-data" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(match)
        embedded = json.loads(match.group(1))
        self.assertEqual(embedded["stats"]["observations"], 3)
        self.assertEqual(embedded["points"]["year"], [2024, 2025, 2025])

    def test_design_is_visually_prominent_and_primary_navigation(self):
        self.assertIn("st.columns([2, 1]", self.dashboard_source)
        self.assertIn("height=740", self.dashboard_source)
        self.assertIn('st.session_state.setdefault("ignis_nav", NAV_PAGES[0])', self.app_source)
        self.assertIn("Uruguay · Geospatial Observatory", self.dashboard_source)

    def test_scene_javascript_parses_in_node(self):
        if not shutil.which("node"):
            self.skipTest("Node.js unavailable")
        match = re.search(r'<script type="module">(.*?)</script>', self.template, re.S)
        self.assertIsNotNone(match)
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "ignis_scene.mjs"
            script.write_text(match.group(1), encoding="utf-8")
            result = subprocess.run(
                ["node", "--check", str(script)],
                text=True, capture_output=True, timeout=30, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
