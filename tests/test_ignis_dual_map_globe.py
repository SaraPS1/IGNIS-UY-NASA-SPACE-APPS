"""Regressions for synchronized 3D/2D views and PDF-ready scientific maps."""
from __future__ import annotations

import ast
import json
from io import BytesIO
from pathlib import Path
import unittest

import pandas as pd

from ignis_spatial import to_scene_frame, render_report_map

ROOT=Path(__file__).resolve().parents[1]


class DualMapTests(unittest.TestCase):
    def test_2d_renderer_returns_real_png_without_webgl(self):
        data=pd.DataFrame([
            {"fecha":"2025-04-01T10:00:00Z","latitude":-33.5,
             "longitude":-56.0,"instrumento":"MODIS","satellite":"Terra","frp":35},
            {"fecha":"2025-06-01T11:00:00Z","latitude":-34.1,
             "longitude":-54.7,"instrumento":"VIIRS","satellite":"NOAA-20","frp":9},
        ])
        result=render_report_map(data)
        self.assertIsInstance(result,bytes)
        self.assertTrue(result.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(result),10000)

    def test_report_renderer_reuses_pdf_map_figure(self):
        from ignis_informe import map_figure
        data=pd.DataFrame([{"fecha":"2024-01-01T00:00:00Z","latitude":-33.6,
                            "longitude":-55.6,"instrumento":"VIIRS","frp":12}])
        normalized=to_scene_frame(data)
        expected=map_figure(normalized).getvalue()
        self.assertEqual(render_report_map(data),expected)

    def test_ground_associations_are_optional_and_not_invented(self):
        data=pd.DataFrame([{"fecha":"2024-01-01","latitude":-33.3,
                            "longitude":-56.0,"instrumento":"MODIS"}])
        assoc=pd.DataFrame([{"lon":-56.3,"lat":-33.7,"resultado":"SYNTHETIC TEST"}])
        self.assertTrue(render_report_map(data,associations=assoc).startswith(b"\x89PNG"))
        self.assertIsNone(render_report_map(pd.DataFrame()))

    def test_every_spatial_page_uses_shared_pair(self):
        for path in ("ignis_dashboard.py","ignis_visual.py","ignis_nrt.py",
                     "ignis_historico.py","ignis_fusion_terrestre.py"):
            content=(ROOT/path).read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIn("render_spatial_pair(",content)
        source=(ROOT/"ignis_spatial.py").read_text(encoding="utf-8")
        self.assertIn("st.columns([1.85, 1]",source)
        self.assertIn("render_uruguay_scene(frame",source)
        self.assertIn("render_report_map(frame, associations)",source)
        self.assertIn('file_name=f"IGNIS_{context}_2d_report.png"',source)

    def test_earth_dual_map_and_report_source(self):
        source=(ROOT/"ignis_espacio.py").read_text(encoding="utf-8")
        self.assertIn("globe_3d_col, globe_2d_col = st.columns(",source)
        self.assertIn("render_report_map(filtered_frame)",source)
        self.assertIn('key="ignis_globe_2d_download"',source)

    def test_texture_failure_is_not_a_fatal_webgl_failure(self):
        source=(ROOT/"ignis_espacio.py").read_text(encoding="utf-8")
        self.assertIn("textureFailures++",source)
        self.assertIn("3D active with fallback visuals",source)
        self.assertIn("window.__ignisRenderFallback",source)
        self.assertNotIn("Could not initialize the 3D view",source)

    def test_satellite_clock_references_are_not_inside_foreach(self):
        source=(ROOT/"ignis_espacio.py").read_text(encoding="utf-8")
        idx=source.index("const orbitalRecords=Array.isArray")
        loop=source.index("orbitalRecords.forEach((sat,index)",idx)
        self.assertLess(source.index("const scientific=payload.orbit_mode",idx),loop)
        self.assertLess(source.index("const selectedUtc=payload.orbit_clock_mode",idx),loop)
        self.assertLess(source.index("const referenceUtcMs=",idx),loop)
        self.assertIn("let playing=!scientific,orbitT=0,orbitSpeed=1",source)
        self.assertIn("speedSelect.disabled=scientific&&replayKind==='current'",source)

    def test_home_spacing_is_localized(self):
        text=(ROOT/"ignis_visual.py").read_text(encoding="utf-8")
        self.assertIn('padding-left:clamp(24px,2.5vw,40px)',text)


if __name__=="__main__":
    unittest.main()
