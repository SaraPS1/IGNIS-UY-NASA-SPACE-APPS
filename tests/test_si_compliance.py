"""Regression checks for the public Space Apps SI disclosure.

Checks visible web overlay and code/data provenance plumbing. Standalone image
watermarking and NASA branding still require human asset review before release.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SIComplianceTests(unittest.TestCase):
    def test_provenance_document_and_machine_metadata(self):
        info = json.loads((ROOT / "docs" / "si_usage.json").read_text(encoding="utf-8"))
        self.assertTrue(info["categories"]["code"]["si_assisted"])
        self.assertTrue(info["categories"]["images"]["si_assisted"])
        self.assertFalse(info["categories"]["data"]["si_generated_source_observations"])
        self.assertTrue(info["policy"]["generated_artwork_must_not_contain_nasa_branding"])
        self.assertIn("SI-generated", (ROOT / "docs" / "SI_USAGE.md").read_text(encoding="utf-8"))

    def test_home_illustrations_have_visible_watermark(self):
        src = (ROOT / "ignis_visual.py").read_text(encoding="utf-8")
        self.assertIn('class="ignis-si-watermark"', src)
        self.assertIn("SI-generated illustration", src)
        self.assertIn("position:absolute!important", src)
        self.assertIn("z-index:4!important", src)
        self.assertIn("card_image = _home_background_image(", src)

    def test_master_export_records_si_processing_provenance(self):
        src = (ROOT / "ignis_historico.py").read_text(encoding="utf-8")
        self.assertIn("'si_use':", src)
        self.assertIn("'input_data':'NASA FIRMS externally sourced observations", src)
        self.assertIn("z.writestr('manifest.json'", src)
        self.assertIn("SI-assisted code", src)

    def test_3d_scene_acknowledges_procedural_visualization(self):
        src = (ROOT / "assets" / "ignis_scene3d.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="si-use"', src)
        self.assertIn("SI-assisted software visualization", src)


if __name__ == "__main__":
    unittest.main()
