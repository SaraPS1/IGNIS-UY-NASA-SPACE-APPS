"""Regression checks for the English-only IGNIS application chrome."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EnglishInterfaceTests(unittest.TestCase):
    def test_app_source_syntax(self):
        for file in (
            "ignis_historico.py", "ignis_visual.py", "ignis_espacio.py",
            "ignis_evidencias.py", "ignis_fusion_terrestre.py",
            "ignis_informe.py", "ignis_ask.py", "ignis_feedback.py",
            "ignis_nrt.py", "pages/space.py",
        ):
            with self.subTest(file=file):
                ast.parse((ROOT / file).read_text(encoding="utf-8"))

    def test_homepage_text_is_english(self):
        src = (ROOT / "ignis_visual.py").read_text(encoding="utf-8")
        for expected in (
            "Historical Archive · Uruguay",
            "Satellite analysis of thermal activity in Uruguay",
            "Explore NASA FIRMS observations",
            "Historical study 2000–2026",
            "Geospatial focus",
        ):
            self.assertIn(expected, src)
        for old in (
            "Histórico · Uruguay",
            "ANÁLISIS SATELITAL DE ACTIVIDAD TÉRMICA EN URUGUAY",
            "Explorá observaciones NASA FIRMS",
            "Estudio histórico 2000–2026",
            "Enfoque geoespacial",
        ):
            self.assertNotIn(old, src)

    def test_sidebar_is_english(self):
        src = (ROOT / "ignis_historico.py").read_text(encoding="utf-8")
        for expected in (
            "HISTORICAL ARCHIVE · URUGUAY",
            "Home · Discover IGNIS",
            "NAVIGATION",
            "Visible sensors",
            "Region / case",
        ):
            self.assertIn(expected, src)

    def test_scientific_methods_are_not_translated(self):
        src = (ROOT / "ignis_historico.py").read_text(encoding="utf-8")
        self.assertIn("instrumento", src)
        self.assertIn("latitud", src)

    def test_3d_status_and_errors_english(self):
        src = (ROOT / "ignis_espacio.py").read_text(encoding="utf-8")
        self.assertIn("WebGL is not available in this browser", src)
        self.assertIn("Full Earth", src)
        self.assertNotIn("WebGL no disponible en este navegador", src)


if __name__ == "__main__":
    unittest.main()
