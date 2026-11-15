"""Protect the team's rehearsed IGNIS workflow while retaining opt-in 3D.

The snapshots below describe the approved pre-cinematic 2D-first interface.
Navigation and existing widget keys must not move when switching display modes.
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]


class PresentationCompatibilityTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main=(ROOT/"ignis_historico.py").read_text(encoding="utf-8")
        cls.visual=(ROOT/"ignis_visual.py").read_text(encoding="utf-8")
        cls.nrt=(ROOT/"ignis_nrt.py").read_text(encoding="utf-8")
        cls.earth=(ROOT/"ignis_espacio.py").read_text(encoding="utf-8")
        cls.fusion=(ROOT/"ignis_fusion_terrestre.py").read_text(encoding="utf-8")
        cls.modes=(ROOT/"ignis_modes.py").read_text(encoding="utf-8")

    def test_default_is_original_home_not_new_dashboard(self):
        self.assertIn('st.session_state.setdefault("ignis_nav", NAV_PAGES[0])',self.main)
        self.assertIn('st.session_state.setdefault("ignis_3d_explorer", False)',self.main)
        self.assertIn('st.toggle("3D Explorer", key="ignis_3d_explorer"',self.main)

    def test_requested_sidebar_order_and_remaining_buttons_stay_stable(self):
        tree=ast.parse(self.main)
        nav=next(item for item in tree.body
                 if isinstance(item,ast.Assign)
                 and any(isinstance(x,ast.Name) and x.id=="NAV_PAGES" for x in item.targets))
        titles=ast.literal_eval(nav.value)
        self.assertEqual(len(titles),15)
        self.assertEqual([t.split(" ",1)[1] for t in titles[:7]],[
            "Home · Discover IGNIS","Data upload","Dashboard",
            "NASA Yearly Overview","Historical Archive 2000–2026",
            "MODIS–VIIRS Harmonization","Uruguay Map"])
        self.assertEqual(titles[9].split(" ",1)[1],"PDF Report")
        self.assertEqual(titles[11].split(" ",1)[1],"3D Earth & Satellites")
        self.assertEqual(titles[13].split(" ",1)[1],"Satellite–Ground Fusion")
        self.assertIn('key=f"ignis_nav_{i:02d}"',self.main)
        self.assertIn('on_click=_ignis_navigate_to',self.main)

    def test_switch_is_after_rehearsed_filters_and_resource_links(self):
        keys=[
            'key="sidebar_region"', 'key="sidebar_sensores"',
            'st.link_button(\n        "🚀 NASA Space Apps 2026"',
            'st.toggle("3D Explorer"', '<div class="ignis-side-footer">',
        ]
        offsets=[self.main.find(p) for p in keys]
        self.assertTrue(all(o>=0 for o in offsets),offsets)
        self.assertEqual(offsets,sorted(offsets),
                         "The new display toggle must not displace navigation or analysis filters")
        self.assertIn('key="ignis_selected_year"',self.main)
        self.assertIn('st.session_state["region"] = region',self.main)
        self.assertIn('st.session_state["sensores"] = sensors',self.main)

    def test_dashboard_preserves_original_chart_map_and_button_keys(self):
        start=self.visual.index("def render_classic_control_center(")
        stop=self.visual.index("def render_control_center(",start)
        classic=self.visual[start:stop]
        self.assertIn('st.columns(4,gap="small")',classic)
        self.assertIn('st.columns([1.9,1],gap="medium")',classic)
        self.assertIn('map_fn(view,"ignis_control_map")',classic)
        self.assertIn('"#### 📡 Instruments"',classic)
        self.assertIn('"#### 🛡️ External validation"',classic)
        self.assertIn('"#### 📚 Other tools"',classic)
        for widget_key in ("control_upload","control_evidence","control_atlas",
                           "control_harmonization","ignis_control_sensors",
                           "ignis_control_months"):
            with self.subTest(widget_key=widget_key):
                self.assertIn(widget_key,classic)
        self.assertLess(classic.index('map_fn(view,"ignis_control_map")'),
                        classic.index('st.markdown("#### 📡 Instruments")'))
        self.assertIn('render_classic_control_center(combined, sample, selected',
                      self.visual)
        self.assertIn('show_presentation_return("ignis_dashboard_back_to_presentation")',
                      self.visual)
        self.assertIn('render_premium_dashboard(',self.visual)

    def test_original_atlas_controls_and_map_key_are_preserved(self):
        for key in ("ignis_atlas_period","ignis_atlas_scientific",
                    "atlas_harmonization","atlas_sources","atlas_download"):
            self.assertIn(key,self.visual)
        self.assertIn('map_fn(mapped, "ignis_atlas_scientific")',self.visual)
        self.assertIn('if is_explorer():',self.visual)

    def test_rehearsed_2d_first_other_pages(self):
        self.assertIn("_mapa_liviano(datos)",self.nrt)
        self.assertIn("if is_explorer() and isinstance(sample, pd.DataFrame)",self.main)
        self.assertIn('if is_explorer():\n            st.markdown("#### Historical archive',self.main)
        self.assertIn("st.plotly_chart(fig,use_container_width=True,on_select='rerun'",self.fusion)
        self.assertIn('show_explorer_entry("ignis_fusion_explore_3d"',self.fusion)
        self.assertLess(self.nrt.index('Download recent query CSV'),
                        self.nrt.index('show_explorer_entry("ignis_nrt_explore_3d"'))
        self.assertLess(self.fusion.index("Download PDF report for this cell"),
                        self.fusion.index('show_explorer_entry("ignis_fusion_explore_3d"'))
        self.assertIn('if is_explorer():\n        st.markdown("**Selected-cell 2D map',self.fusion)
        self.assertIn('globe_2d_slot = None',self.earth)
        self.assertIn('if globe_2d_slot is not None:',self.earth)

    def test_mode_toggle_does_not_modify_navigation_or_filters(self):
        # Only the presentation preference may be changed by mode callbacks.
        from ignis_modes import set_explorer,is_explorer
        state={"ignis_nav":"Uruguay Map", "sidebar_region":"Uruguay",
               "sidebar_sensores":["MODIS"],"combined":"unchanged"}
        fake=SimpleNamespace(session_state=state)
        with patch.dict(sys.modules,{"streamlit":fake}):
            self.assertFalse(is_explorer())
            set_explorer(True)
            self.assertTrue(is_explorer())
            set_explorer(False)
            self.assertFalse(is_explorer())
        self.assertEqual(state["ignis_nav"],"Uruguay Map")
        self.assertEqual(state["sidebar_region"],"Uruguay")
        self.assertEqual(state["sidebar_sensores"],["MODIS"])
        self.assertEqual(state["combined"],"unchanged")

    def test_scientific_renderer_remains_unmodified(self):
        spatial=(ROOT/"ignis_spatial.py").read_text(encoding="utf-8")
        self.assertIn("def render_spatial_pair(",spatial)
        self.assertIn("render_uruguay_scene(frame",spatial)
        self.assertIn("render_report_map(frame, associations)",spatial)


if __name__ == "__main__":
    import unittest
    unittest.main()
