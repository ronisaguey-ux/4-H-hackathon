"""Truth-table specimen accuracy and non-vacuity test suite.

Verifies:
1. Per-specimen diagnostic accuracy across all benchmark specimens.
2. Non-vacuity of the confidence floor and calibration guardrails.
Runs against the offline deterministic CV engine for 100% reproducibility.
"""
import unittest
from pathlib import Path
from PIL import Image

import config
from core.cv_analyzer import LeafCVAnalyzer
from core.calibration import DiagnosticCalibrator


class TestSpecimenAccuracy(unittest.TestCase):
    def setUp(self):
        self.analyzer = LeafCVAnalyzer()
        self.calibrator = DiagnosticCalibrator(confidence_floor=0.70)
        self.samples_dir = config.SAMPLE_DIR

    def test_specimen_truth_table(self):
        """Verify each benchmark specimen against its expected clinical ground truth."""
        cases = [
            ("tar_spot_specimen", "tar_spot", "confident"),
            ("common_rust_specimen", "common_rust", "confident"),
            ("northern_blight_specimen", "northern_corn_leaf_blight", "confident"),
            ("healthy_leaf_specimen", "healthy", "confident"),
            ("gray_leaf_spot_specimen", "gray_leaf_spot", "confident_or_hedge"),
            ("ambiguous_specimen", "unsure", "must_hedge"),
        ]

        for base_name, expected_disease, expectation in cases:
            img_path = self.samples_dir / f"{base_name}.jpg"
            self.assertTrue(img_path.exists(), f"Missing test specimen: {img_path}")
            img = Image.open(img_path)

            res = self.analyzer.analyze_leaf_image(img)
            loc = res["local_diagnosis"]
            cal = self.calibrator.calibrate_diagnosis(
                raw_disease_id=loc["disease_id"],
                raw_confidence=loc["confidence"],
                is_leaf=res["is_leaf"],
                leaf_coverage_pct=res["leaf_coverage_pct"],
                top_candidates=loc.get("top_3_candidates")
            )

            msg = f"Failed on {base_name}: got {cal['disease_id']} (conf={cal['confidence']}, is_confident={cal['is_confident']})"

            if expectation == "confident":
                self.assertTrue(cal["is_confident"], msg)
                self.assertEqual(cal["disease_id"], expected_disease, msg)
            elif expectation == "must_hedge":
                self.assertFalse(cal["is_confident"], msg)
                self.assertEqual(cal["disease_id"], "unsure", msg)
            elif expectation == "confident_or_hedge":
                if cal["is_confident"]:
                    # If confident, it MUST be the correct disease, NEVER a confident wrong disease
                    self.assertEqual(cal["disease_id"], expected_disease, msg)
                else:
                    # If hedged, it must hedge to 'unsure' and list the candidate in differentials
                    self.assertEqual(cal["disease_id"], "unsure", msg)
                    cand_ids = [c["disease_id"] for c in cal.get("top_candidates", [])]
                    self.assertIn(expected_disease, cand_ids, msg)

    def test_non_vacuity_confidence_floor(self):
        """Assert that if confidence floor is disabled (0.0), below-floor hedging fails.
        A test suite that cannot fail measures nothing."""
        floor_zero_calibrator = DiagnosticCalibrator(confidence_floor=0.0)

        # Low-confidence specimen (0.62) with normal calibrator (0.70 floor) hedges to unsure
        normal_res = self.calibrator.calibrate_diagnosis(
            raw_disease_id="tar_spot",
            raw_confidence=0.62,
            is_leaf=True,
            leaf_coverage_pct=85.0
        )
        self.assertFalse(normal_res["is_confident"])
        self.assertEqual(normal_res["disease_id"], "unsure")

        # But with floor at 0.0, the guardrail is vacated
        vacated_res = floor_zero_calibrator.calibrate_diagnosis(
            raw_disease_id="tar_spot",
            raw_confidence=0.62,
            is_leaf=True,
            leaf_coverage_pct=85.0
        )
        # Vacated calibrator falsely claims confidence
        self.assertTrue(vacated_res["is_confident"])
        self.assertEqual(vacated_res["disease_id"], "tar_spot")


if __name__ == "__main__":
    unittest.main()
