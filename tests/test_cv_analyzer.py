"""Unit tests for Computer Vision color-space lesion segmentation."""
import unittest
from PIL import Image
from pathlib import Path
from core.cv_analyzer import LeafCVAnalyzer
import config


class TestCVAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = LeafCVAnalyzer()
        self.samples_dir = config.SAMPLE_DIR

    def test_analyze_tar_spot_specimen(self):
        img_path = self.samples_dir / "tar_spot_specimen.jpg"
        self.assertTrue(img_path.exists())
        img = Image.open(img_path)
        res = self.analyzer.analyze_leaf_image(img)

        self.assertTrue(res["is_leaf"])
        self.assertGreaterEqual(res["leaf_coverage_pct"], 50.0)
        self.assertGreater(res["severity_pct"], 0.0)
        self.assertIn(res["severity_grade"], ["Early", "Moderate", "Severe"])
        self.assertTrue(res["segmentation_overlay_b64"].startswith("data:image/png;base64,"))

    def test_analyze_healthy_leaf(self):
        img_path = self.samples_dir / "healthy_leaf_specimen.jpg"
        img = Image.open(img_path)
        res = self.analyzer.analyze_leaf_image(img)

        self.assertTrue(res["is_leaf"])
        self.assertLess(res["severity_pct"], 2.0)
        self.assertEqual(res["severity_grade"], "Early")
        self.assertEqual(res["local_diagnosis"]["disease_id"], "healthy")

    def test_analyze_ambiguous_non_leaf(self):
        img_path = self.samples_dir / "ambiguous_specimen.jpg"
        img = Image.open(img_path)
        res = self.analyzer.analyze_leaf_image(img)

        # Ambiguous rock has no green chlorophyll
        self.assertFalse(res["is_leaf"])
        self.assertLess(res["leaf_coverage_pct"], config.MIN_LEAF_COVERAGE_PCT)
        self.assertEqual(res["local_diagnosis"]["disease_id"], "unsure")
        self.assertEqual(res["local_diagnosis"]["status"], "unsure")


if __name__ == "__main__":
    unittest.main()
