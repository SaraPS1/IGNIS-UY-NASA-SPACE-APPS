"""Check SI provenance in the two scientific PDF generators."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PDFSIDisclosureTests(unittest.TestCase):
    def test_main_report(self):
        s=(ROOT/"ignis_informe.py").read_text(encoding="utf-8")
        self.assertIn("subject='SI-assisted Python report generation",s)
        self.assertIn("Super Intelligence (SI) provenance:",s)
        self.assertIn("SI-generated team logo",s)
        self.assertIn("SI-generated / SI-assisted illustration",s)\n        self.assertIn("class SIWatermarkedImage(RLImage)",s)
        self.assertNotIn("image_asset('logo_nasa",s)
        self.assertIn("SI-assisted report generation",s)

    def test_grid_cell_report(self):
        s=(ROOT/"ignis_fusion_terrestre.py").read_text(encoding="utf-8")
        self.assertIn("subject='SI-assisted Python report generation",s)
        self.assertIn("SI provenance:",s)
        self.assertIn("SI-assisted report generation",s)
        self.assertNotIn("logo_nasa=base/'logo_nasa_informe.png'",s)
        self.assertIn("not SI-generated",s)

    def test_readme_and_si_usage_document_exports(self):
        r=(ROOT/"README.md").read_text(encoding="utf-8")
        p=(ROOT/"docs"/"SI_USAGE.md").read_text(encoding="utf-8")
        self.assertIn("Scientific PDF exports:",r)
        self.assertIn("Exported PDF scientific reports",p)

if __name__=="__main__":
    unittest.main()
