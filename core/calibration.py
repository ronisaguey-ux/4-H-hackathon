"""Calibration & Guardrail Engine for Crop Disease Diagnosis.

Enforces:
1. Strict Confidence Floor (0.70): Below this, the model hedges with "unsure".
2. Subject Verification: Detects non-leaf or low-quality imagery.
3. Differential Ranking: Formulates top-3 candidates with relative likelihoods.
4. Field Retake Protocols: Provides physical verification instructions (e.g. water-rub test).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import config


class DiagnosticCalibrator:
    """Ensures diagnoses are strictly calibrated and avoids dangerous overconfidence."""

    def __init__(self, confidence_floor: float = config.CONFIDENCE_FLOOR):
        self.confidence_floor = confidence_floor

    def calibrate_diagnosis(
        self,
        raw_disease_id: str,
        raw_confidence: float,
        is_leaf: bool,
        leaf_coverage_pct: float,
        top_candidates: Optional[List[Dict[str, Any]]] = None,
        llm_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Apply calibration guardrails to incoming raw diagnosis."""
        # Normalize inputs
        disease_id = (raw_disease_id or "unsure").strip().lower().replace(" ", "_")
        confidence = max(0.0, min(1.0, float(raw_confidence)))

        # Rule 1: Non-leaf subjects MUST trigger the unsure path
        if not is_leaf or leaf_coverage_pct < config.MIN_LEAF_COVERAGE_PCT:
            return {
                "disease_id": "unsure",
                "is_confident": False,
                "confidence": round(min(confidence, 0.45), 2),
                "calibration_status": "FLAGGED_NON_LEAF",
                "hedge_reason": (
                    "Subject does not appear to be a crop leaf blade. "
                    f"Only {leaf_coverage_pct}% of the frame exhibited plant tissue characteristics."
                ),
                "retake_instructions": [
                    "Photograph an individual symptomatic corn leaf blade directly.",
                    "Position the camera 6 to 8 inches from the leaf surface.",
                    "Ensure leaf tissue fills at least 50% of the viewfinder frame."
                ],
                "top_candidates": top_candidates or [
                    {"disease_id": "unsure", "name": "Non-Leaf / Ambiguous", "probability": 0.70},
                    {"disease_id": "healthy", "name": "Healthy Corn Foliage", "probability": 0.15},
                    {"disease_id": "tar_spot", "name": "Tar Spot (trace)", "probability": 0.15},
                ]
            }

        # Rule 2: Confidence below floor triggers the unsure path
        if confidence < self.confidence_floor:
            candidates = top_candidates or self._default_candidates_for(disease_id, confidence)
            return {
                "disease_id": "unsure",
                "is_confident": False,
                "confidence": round(confidence, 2),
                "calibration_status": "CONFIDENCE_BELOW_FLOOR",
                "hedge_reason": (
                    f"Diagnostic confidence ({int(confidence * 100)}%) is below the safe field action threshold "
                    f"({int(self.confidence_floor * 100)}%). A misdiagnosis could lead to wasted fungicide costs or crop damage."
                ),
                "retake_instructions": [
                    "Hold phone camera 6 to 8 inches away and tap the screen to lock sharp macro focus on the spots.",
                    "Avoid harsh midday sun glare or deep shadows; shade the leaf with your body if necessary.",
                    "Include both diseased spots and surrounding healthy green leaf tissue for contrast.",
                    "Perform the 'Water Rub Test': wipe spots with a damp cloth. If they smear or wash off, it is harmless insect frass, not tar spot."
                ],
                "top_candidates": candidates
            }

        # Rule 3: Confident diagnosis passed calibration
        return {
            "disease_id": disease_id,
            "is_confident": True,
            "confidence": round(confidence, 2),
            "calibration_status": "CONFIDENT_DIAGNOSIS",
            "hedge_reason": None,
            "retake_instructions": [],
            "top_candidates": top_candidates or [
                {"disease_id": disease_id, "name": disease_id.replace("_", " ").title(), "probability": round(confidence, 2)}
            ]
        }

    def _default_candidates_for(self, disease_id: str, conf: float) -> List[Dict[str, Any]]:
        primary_prob = round(conf, 2)
        secondary_prob = round((1.0 - primary_prob) * 0.6, 2)
        tertiary_prob = round(1.0 - primary_prob - secondary_prob, 2)

        mapping = {
            "tar_spot": [
                {"disease_id": "tar_spot", "name": "Tar Spot (Phyllachora maydis)", "probability": primary_prob},
                {"disease_id": "common_rust", "name": "Common Rust / Teliospores", "probability": secondary_prob},
                {"disease_id": "unsure", "name": "Insect Frass / Saprophyte", "probability": tertiary_prob},
            ],
            "gray_leaf_spot": [
                {"disease_id": "gray_leaf_spot", "name": "Gray Leaf Spot (Cercospora zeae-maydis)", "probability": primary_prob},
                {"disease_id": "northern_corn_leaf_blight", "name": "Northern Corn Leaf Blight", "probability": secondary_prob},
                {"disease_id": "healthy", "name": "Healthy / Sunscald", "probability": tertiary_prob},
            ],
            "northern_corn_leaf_blight": [
                {"disease_id": "northern_corn_leaf_blight", "name": "Northern Corn Leaf Blight", "probability": primary_prob},
                {"disease_id": "gray_leaf_spot", "name": "Gray Leaf Spot", "probability": secondary_prob},
                {"disease_id": "unsure", "name": "Diplodia Leaf Streak", "probability": tertiary_prob},
            ],
            "common_rust": [
                {"disease_id": "common_rust", "name": "Common Rust (Puccinia sorghi)", "probability": primary_prob},
                {"disease_id": "tar_spot", "name": "Tar Spot", "probability": secondary_prob},
                {"disease_id": "healthy", "name": "Normal Pollen / Flecking", "probability": tertiary_prob},
            ]
        }
        return mapping.get(disease_id, [
            {"disease_id": "tar_spot", "name": "Tar Spot", "probability": 0.40},
            {"disease_id": "gray_leaf_spot", "name": "Gray Leaf Spot", "probability": 0.35},
            {"disease_id": "common_rust", "name": "Common Rust", "probability": 0.25},
        ])


# Global singleton instance
calibrator = DiagnosticCalibrator()
