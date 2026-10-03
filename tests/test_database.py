"""Unit tests for SQLite scouting history database."""
import unittest
import tempfile
from pathlib import Path
from core.database import ScoutingDatabase


class TestScoutingDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_scans.db"
        self.db = ScoutingDatabase(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_retrieve_scan(self):
        scan_id = self.db.save_scan(
            field_id="North 40",
            disease_id="tar_spot",
            disease_name="Tar Spot",
            confidence=0.94,
            severity_pct=12.5,
            severity_grade="Moderate",
            is_confident=True,
            notes="Observed on ear leaf"
        )
        self.assertGreater(scan_id, 0)

        scans = self.db.get_scans(field_id="North 40")
        self.assertEqual(len(scans), 1)
        self.assertEqual(scans[0]["disease_id"], "tar_spot")
        self.assertEqual(scans[0]["severity_pct"], 12.5)
        self.assertEqual(scans[0]["severity_grade"], "Moderate")

    def test_field_analytics_trend(self):
        # Insert two scans: first at 4%, second at 12% (rapid spread)
        self.db.save_scan("Plot 1", "tar_spot", "Tar Spot", 0.90, 4.0, "Early", timestamp="2026-09-01T10:00:00Z")
        self.db.save_scan("Plot 1", "tar_spot", "Tar Spot", 0.92, 12.0, "Moderate", timestamp="2026-09-05T10:00:00Z")

        analytics = self.db.get_field_analytics("Plot 1")
        self.assertEqual(analytics["scan_count"], 2)
        self.assertIn("Rapidly Spreading", analytics["trend"])
        self.assertEqual(analytics["latest_severity_pct"], 12.0)

    def test_delete_scan(self):
        s_id = self.db.save_scan("Test Field", "healthy", "Healthy", 0.95, 0.0, "Early")
        self.assertTrue(self.db.delete_scan(s_id))
        scans = self.db.get_scans("Test Field")
        self.assertEqual(len(scans), 0)


if __name__ == "__main__":
    unittest.main()
