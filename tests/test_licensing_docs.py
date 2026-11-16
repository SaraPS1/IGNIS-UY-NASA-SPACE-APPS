"""Basic licensing documentation consistency checks for NASA Space Apps."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LicensingDocumentsTests(unittest.TestCase):
    def test_standard_apache_license_present(self):
        s = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", s[:120])
        self.assertIn("Version 2.0, January 2004", s)
        self.assertIn("END OF TERMS AND CONDITIONS", s)
        self.assertIn("APPENDIX: How to apply the Apache License", s)
        self.assertNotIn("APACHE AIRFLOW SUBCOMPONENTS", s)

    def test_notice_and_scope(self):
        notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        inventory = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("NASA FIRMS", notice)
        self.assertIn("contributor approval", notice)
        self.assertIn("not automatically licensed", inventory.lower())
        for path in ("LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md"):
            self.assertIn(f"]({path})", readme)

    def test_all_direct_dependencies_listed(self):
        req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        inventory = (ROOT / "THIRD_PARTY_LICENSES.md").read_text(encoding="utf-8").lower()
        for line in req.splitlines():
            if line and not line.startswith("#"):
                pkg=line.split("=")[0].split("<")[0].split(">")[0].strip().lower()
                with self.subTest(package=pkg):
                    self.assertIn(pkg, inventory)

if __name__ == "__main__":
    unittest.main()
