"""Checks that judge-facing README documentation remains in English.

Filenames are deliberately stable legacy identifiers and need not be translated.
Technical source labels in code blocks/quotes are allowed.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES = [
    "docs/METODO_CIENTIFICO.md",
    "docs/VALIDACION_Y_LIMITES.md",
    "docs/V5_CALIDAD_Y_PAREO.md",
    "docs/FUENTES_DATOS.md",
    "docs/USO_DE_IA.md",
    "docs/HOJA_DE_RUTA.md",
]
SPANISH_HEADINGS = (
    "# Método científico", "# Validación", "# Fuentes de datos",
    "# Uso de inteligencia artificial", "# Hoja de ruta",
    "## Qué sigue pendiente", "## Reproducibilidad",
)


class JudgeFacingGuidesTests(unittest.TestCase):
    def test_guide_links_exist_and_have_english_titles(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for path in GUIDES:
            with self.subTest(path=path):
                doc = ROOT / path
                self.assertTrue(doc.is_file())
                content = doc.read_text(encoding="utf-8")
                self.assertTrue(content.startswith("# "))
                self.assertNotIn(content.splitlines()[0], SPANISH_HEADINGS)
                self.assertIn(path, readme)

    def test_critical_scientific_disclaimers_preserved(self):
        method = (ROOT / GUIDES[0]).read_text(encoding="utf-8")
        limits = (ROOT / GUIDES[1]).read_text(encoding="utf-8")
        matching = (ROOT / GUIDES[2]).read_text(encoding="utf-8")
        self.assertIn("not a confirmed wildfire", method)
        self.assertIn("5 km", method)
        self.assertIn("30 minutes", method)
        self.assertIn("0.20°", method)
        self.assertIn("does not establish an optimal grid size", method)
        self.assertIn("not implemented yet", limits)
        self.assertIn("greedy", matching)
        self.assertIn("across the year boundary", matching)


if __name__ == "__main__":
    unittest.main()
