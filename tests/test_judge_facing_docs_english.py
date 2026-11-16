"""Guard the language and targets of every technical document linked by README."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "docs/METODO_CIENTIFICO.md": "Scientific methodology",
    "docs/VALIDACION_Y_LIMITES.md": "Validation, sensitivity, and limitations",
    "docs/V5_CALIDAD_Y_PAREO.md": "data-quality audit, unique matching",
    "docs/FUENTES_DATOS.md": "Data sources and provenance",
    "docs/USO_DE_IA.md": "Artificial intelligence usage",
    "docs/HOJA_DE_RUTA.md": "Phased roadmap",
    "docs/SI_USAGE.md": "Super Intelligence",
    "TEAM_IGNIS_CONTRIBUCIONES.md": "Questions and contributions",
}
SPANISH_PHRASES = (
    "Unidad de análisis", "Coincidencia por celda-día",
    "Pareos espaciales y temporales", "Evidencia disponible",
    "Qué valida", "Qué no valida", "Riesgos conocidos",
    "Qué sigue pendiente", "Alcance de esta entrega",
    "Auditoría", "Fuentes de datos y procedencia",
    "Uso de inteligencia artificial", "Hoja de ruta por fases",
    "Próximos experimentos de validación",
)

class EnglishDocumentationTests(unittest.TestCase):
    def test_readme_links_to_existing_english_documents(self):
        readme=(ROOT/"README.md").read_text(encoding="utf-8")
        for path,title in DOCS.items():
            with self.subTest(path=path):
                self.assertIn(f"]({path})",readme)
                full=ROOT/path
                self.assertTrue(full.is_file())
                contents=full.read_text(encoding="utf-8")
                self.assertIn(title,contents.splitlines()[0])
                prose=re.sub(r"```.*?```","",contents,flags=re.S)
                for phrase in SPANISH_PHRASES:
                    self.assertNotIn(phrase,prose)

    def test_scientific_details_remain_explicit(self):
        m=(ROOT/"docs/METODO_CIENTIFICO.md").read_text(encoding="utf-8")
        v=(ROOT/"docs/VALIDACION_Y_LIMITES.md").read_text(encoding="utf-8")
        p=(ROOT/"docs/V5_CALIDAD_Y_PAREO.md").read_text(encoding="utf-8")
        for term in ("0.20°","5 km","30 minutes","cKDTree","not a confirmed wildfire"):
            self.assertIn(term,m)
        self.assertIn("not implemented yet",v)
        self.assertIn("greedy",p)
        self.assertIn("UTC midnight",p)

if __name__=="__main__":
    unittest.main()
