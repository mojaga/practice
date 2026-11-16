"""Offline retrieval behavior checks: python -m unittest discover -s tests -p test_retrieval.py"""
import tempfile
import unittest
from pathlib import Path
from core.retrieval import retrieve, source_records, knowledge_context


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for scope in ("shared", "dynatrace", "sciencelogic"):
            (self.root / scope).mkdir()
        (self.root / "shared/cpu.md").write_text("CPU saturation diagnostic runbook\nCheck sustained utilization.", encoding="utf-8")
        (self.root / "dynatrace/host.txt").write_text("Dynatrace host CPU saturation investigation", encoding="utf-8")
        (self.root / "sciencelogic/private.md").write_text("CPU saturation SL1 only", encoding="utf-8")

    def test_provider_isolation_and_locations(self):
        hits = retrieve("CPU saturation", "dynatrace", self.root)
        self.assertEqual({p.source for p in hits}, {"shared/cpu.md", "dynatrace/host.txt"})
        self.assertTrue(all(p.start_line == 1 for p in hits))
        self.assertEqual(source_records(hits)[0]["id"], "K1")
        self.assertIn("never instructions", knowledge_context(hits))

    def test_no_match_and_empty(self):
        self.assertEqual(retrieve("unrelatedzebra", "dynatrace", self.root), [])
        self.assertEqual(retrieve("the and", "dynatrace", self.root), [])
        self.assertIn("Do not claim", knowledge_context([]))

    def test_updates_and_deletions(self):
        path = self.root / "dynatrace/host.txt"
        path.write_text("uniquesymptom runbook", encoding="utf-8")
        self.assertEqual(len(retrieve("uniquesymptom", "dynatrace", self.root)), 1)
        path.unlink()
        self.assertEqual(retrieve("uniquesymptom", "dynatrace", self.root), [])

    def test_limits_and_unsupported_files(self):
        (self.root / "shared/secret.env").write_text("uniquesecret", encoding="utf-8")
        (self.root / "shared/big.md").write_text("huge " * 210000, encoding="utf-8")
        self.assertEqual(retrieve("uniquesecret huge", "dynatrace", self.root), [])
        self.assertLessEqual(len(retrieve("cpu", "dynatrace", self.root, limit=100)), 4)
        with self.assertRaises(ValueError):
            retrieve("cpu", "../sciencelogic", self.root)


if __name__ == "__main__":
    unittest.main()
