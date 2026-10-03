"""Unit tests for diagnostic calibration and confidence floor enforcement."""
import unittest
from core.calibration import DiagnosticCalibrator


class TestCalibration(unittest.TestCase):
    def setUp(self):
        self.calibrator = DiagnosticCalibrator(confidence_floor=0.70)

    def test_confident_diagnosis_above_floor(self):
        res = self.calibrator.calibrate_diagnosis(
            raw_disease_id="tar_spot",
            raw_confidence=0.92,
            is_leaf=True,
            leaf_coverage_pct=95.0
        )
        self.assertTrue(res["is_confident"])
        self.assertEqual(res["disease_id"], "tar_spot")
        self.assertEqual(res["calibration_status"], "CONFIDENT_DIAGNOSIS")
        self.assertIsNone(res["hedge_reason"])
        self.assertEqual(len(res["retake_instructions"]), 0)

    def test_hedge_when_confidence_below_floor(self):
        res = self.calibrator.calibrate_diagnosis(
            raw_disease_id="tar_spot",
            raw_confidence=0.62,  # Below 0.70 floor
            is_leaf=True,
            leaf_coverage_pct=90.0
        )
        self.assertFalse(res["is_confident"])
        self.assertEqual(res["disease_id"], "unsure")
        self.assertEqual(res["calibration_status"], "CONFIDENCE_BELOW_FLOOR")
        self.assertIn("below the safe field action threshold", res["hedge_reason"])
        self.assertGreater(len(res["retake_instructions"]), 0)
        self.assertGreater(len(res["top_candidates"]), 0)

    def test_hedge_when_subject_is_non_leaf(self):
        res = self.calibrator.calibrate_diagnosis(
            raw_disease_id="healthy",
            raw_confidence=0.88,
            is_leaf=False,  # Detected non-leaf
            leaf_coverage_pct=4.0
        )
        self.assertFalse(res["is_confident"])
        self.assertEqual(res["disease_id"], "unsure")
        self.assertEqual(res["calibration_status"], "FLAGGED_NON_LEAF")
        self.assertIn("does not appear to be a crop leaf blade", res["hedge_reason"])


if __name__ == "__main__":
    unittest.main()
