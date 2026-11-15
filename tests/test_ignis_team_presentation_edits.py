"""Guard the two team-requested, presentation-only adjustments.

Both changes must remain cosmetic: sidebar navigation must still dispatch to
the correct pages and orbital scientific calculations must stay opt-in.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


class TeamRequestedUiChangesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = source("ignis_historico.py")
        cls.visual = source("ignis_visual.py")
        cls.dashboard = source("ignis_dashboard.py")
        cls.space = source("ignis_espacio.py")

    def test_sidebar_order_is_home_upload_dashboard_then_unchanged_pages(self):
        tree = ast.parse(self.main)
        nav = next(node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "NAV_PAGES"
                           for target in node.targets))
        titles = [label.split(" ", 1)[1] for label in ast.literal_eval(nav.value)]
        self.assertEqual(titles[:4], [
            "Home · Discover IGNIS", "Data upload", "Dashboard",
            "NASA Yearly Overview"])
        self.assertEqual(len(titles), 15)
        self.assertEqual(titles[9], "PDF Report")
        self.assertEqual(titles[11], "3D Earth & Satellites")
        self.assertEqual(titles[13], "Satellite–Ground Fusion")

    def test_main_routes_dispatch_to_correct_pages_after_reorder(self):
        self.assertRegex(self.main, r"if current_section==NAV_PAGES\[1\]:\s+st\.subheader\('Adding historical records'\)")
        self.assertRegex(self.main, r"if current_section == NAV_PAGES\[2\]:[\s\S]{0,400}?render_control_center\(")
        # The dashboard's special header is still handled by its own renderer.
        self.assertIn("NAV_PAGES[2], NAV_PAGES[6], NAV_PAGES[14]", self.main)

    def test_home_buttons_keep_labels_and_destinations(self):
        self.assertRegex(self.visual, r'key="hero_to_dashboard", on_click=navigate, args=\(pages\[2\],\)')
        self.assertRegex(self.visual, r'key="hero_to_upload", on_click=navigate, args=\(pages\[1\],\)')
        self.assertRegex(self.visual, r'key="control_upload",[\s\S]{0,130}?args=\(pages\[1\],\)')
        self.assertRegex(self.visual, r'key="atlas_upload",[\s\S]{0,130}?args=\(pages\[1\],\)')
        self.assertRegex(self.dashboard, r'key="ig_dash_upload",[\s\S]{0,130}?args=\(pages\[1\],\)')

    def test_sidebar_icons_follow_the_new_order(self):
        tree=ast.parse(self.visual)
        style=next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                   and node.name == "_reference_styles")
        strokes=next(node.value for node in ast.walk(style)
                     if isinstance(node, ast.Assign) and any(
                         isinstance(target, ast.Name) and target.id=="strokes"
                         for target in node.targets))
        icons=ast.literal_eval(strokes)
        self.assertIn("<path", icons[1], "Upload needs its arrow-and-cloud icon")
        self.assertIn("<rect", icons[2], "Dashboard needs its grid icon")
        self.assertIn('("hero_to_history",strokes[2])', self.visual)
        self.assertIn('("hero_to_upload",strokes[1])', self.visual)

    def test_globe_defaults_to_illustrative_with_calculated_mode_available(self):
        tree=ast.parse(self.space)
        radio=next(call for call in ast.walk(tree) if isinstance(call, ast.Call)
                   and isinstance(call.func, ast.Attribute)
                   and call.func.attr=="radio"
                   and call.args and isinstance(call.args[0], ast.Constant)
                   and call.args[0].value=="Trajectory source")
        options=ast.literal_eval(radio.args[1])
        self.assertEqual(options, ["Illustrative trajectories", "Current TLE data"])
        index=next(k.value for k in radio.keywords if k.arg=="index")
        self.assertEqual(ast.literal_eval(index),0)
        self.assertIn('key="ignis_orbit_source"', self.space)
        self.assertIn('use_live_tle = orbit_mode == "Current TLE data"',self.space)
        self.assertIn('"orbit_mode": "sgp4" if use_live_tle else "illustrative"',self.space)
        self.assertIn("NOT measured satellite positions", self.space)


if __name__ == "__main__":
    unittest.main()
