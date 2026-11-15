"""Regression checks for the Uruguay Map default and team-logo disclosure."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UruguayMapDefaultTests(unittest.TestCase):
    def test_3d_is_explicit_default(self):
        source = (ROOT / "ignis_visual.py").read_text(encoding="utf-8")
        self.assertIn('["3D interactive", "2D zoomable", "2D scientific density"]', source)
        self.assertIn('index=0, horizontal=True, key="ignis_atlas_map_display"', source)
        self.assertIn('if map_mode == "3D interactive":', source)
        self.assertIn('height=620, context="atlas", show_report_map=False', source)
        self.assertIn('render_zoomable_uruguay_map(mapped, base)', source)
        self.assertIn('map_fn(mapped, "ignis_atlas_scientific")', source)

    def test_team_logo_has_visible_ai_label(self):
        source = (ROOT / "ignis_historico.py").read_text(encoding="utf-8")
        style = (ROOT / "ignis_visual.py").read_text(encoding="utf-8")
        self.assertIn('class="ignis-side-logo-ai-note"', source)
        self.assertIn('>IA generated</span>', source)
        self.assertIn('.ignis-side-brand-copy .ignis-side-logo-ai-note', style)

    def test_tracking_legend_does_not_overlay_controls(self):
        source = (ROOT / "assets" / "ignis_scene3d.html").read_text(encoding="utf-8")
        start = source.index('<section id="orbital-console"')
        end = source.index('</section>', start)
        panel = source[start:end]
        self.assertIn('<div id="legend" class="panel">', panel)
        self.assertGreater(panel.index('<div id="legend"'), panel.index('id="orbital-mode"'))
        self.assertIn('#orbital-console #legend{position:static;', source)
        self.assertIn('overflow-y:auto;', source)


if __name__ == "__main__":
    unittest.main()
