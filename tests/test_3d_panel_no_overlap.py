"""Layout regression tests: 3D information panels must not overlap.

The Mission Brief and Satellite Tracking panels must share one scrolling
container. Legacy absolute offsets are overridden for both panels.
"""
import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "assets" / "ignis_scene3d.html")


class ThreeDPanelLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML.read_text(encoding="utf-8")

    def test_both_panels_are_siblings_inside_one_dock(self):
        html = self.html
        start = html.index('<div id="right-dock"')
        finish = html.index('</div><!-- right-dock:', start)
        section = html[start:finish]
        self.assertIn('<section id="mission"', section)
        self.assertIn('<section id="orbital-console"', section)
        self.assertLess(section.index('<section id="mission"'),
                        section.index('<section id="orbital-console"'))
        self.assertEqual(section.count('<section'), 2)
        self.assertIn('id="orbital-mode"', section)
        self.assertIn('id="legend"', section)

    def test_layout_uses_flow_not_absolute_offsets(self):
        source = self.html
        self.assertIn('#right-dock{', source)
        self.assertIn('display:flex;flex-direction:column;gap:12px;', source)
        self.assertIn('overflow-y:auto;overflow-x:hidden;', source)
        self.assertIn('#right-dock > #mission,', source)
        self.assertIn('#right-dock > #orbital-console{', source)
        self.assertIn('position:relative;left:auto;right:auto;top:auto;bottom:auto;', source)
        self.assertIn('width:100%;max-height:none;overflow:visible;', source)

    def test_responsive_and_hidden_state_rules(self):
        source = self.html
        self.assertIn('@media(max-width:1050px)', source)
        self.assertIn('@media(max-width:760px)', source)
        self.assertIn('#stage.compact #right-dock > #mission{display:none}', source)


if __name__ == "__main__":
    unittest.main()
