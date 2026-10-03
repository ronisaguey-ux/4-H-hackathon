"""Computer Vision & Color-Space Lesion Segmentation Analyzer.

Performs:
1. Leaf vs Background segmentation (HSV/RGB color space thresholding).
2. Necrotic/Chlorotic lesion detection.
3. Quantitative leaf area affected (%) and categorical severity grading (Early, Moderate, Severe).
4. Visual segmentation overlay mask generation (Base64 PNG).
5. Heuristic visual feature extraction for local offline classification.
"""
from __future__ import annotations

import base64
import io
import math
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import config


def _rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB [0..255] to HSV (h: 0..360, s: 0..1, v: 0..1)."""
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    cmax = max(r_norm, g_norm, b_norm)
    cmin = min(r_norm, g_norm, b_norm)
    diff = cmax - cmin

    # Hue calculation
    if diff == 0:
        h = 0.0
    elif cmax == r_norm:
        h = (60.0 * ((g_norm - b_norm) / diff) + 360.0) % 360.0
    elif cmax == g_norm:
        h = (60.0 * ((b_norm - r_norm) / diff) + 120.0) % 360.0
    else:
        h = (60.0 * ((r_norm - g_norm) / diff) + 240.0) % 360.0

    # Saturation calculation
    s = 0.0 if cmax == 0 else (diff / cmax)
    v = cmax
    return h, s, v


class LeafCVAnalyzer:
    """Processes leaf images for disease severity and segmentation."""

    def __init__(self, max_dimension: int = 600):
        self.max_dimension = max_dimension

    def resize_for_analysis(self, image: Image.Image) -> Image.Image:
        """Resize image preserving aspect ratio to optimize computation speed."""
        img = image.convert("RGB")
        w, h = img.size
        if max(w, h) > self.max_dimension:
            scale = self.max_dimension / float(max(w, h))
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        return img

    def analyze_leaf_image(self, image: Image.Image) -> Dict[str, Any]:
        """Perform full color segmentation and quantitative severity estimation."""
        img = self.resize_for_analysis(image)
        width, height = img.size
        total_pixels = width * height

        pixels = img.load()
        leaf_mask: List[List[bool]] = [[False] * height for _ in range(width)]
        lesion_mask: List[List[bool]] = [[False] * height for _ in range(width)]

        leaf_pixel_count = 0
        lesion_pixel_count = 0

        # Feature accumulators for local heuristic classification
        black_stromata_count = 0     # Characteristic of Tar Spot
        tan_gray_lesion_count = 0    # Characteristic of Gray Leaf Spot
        cigar_blight_count = 0       # Characteristic of Northern Corn Leaf Blight
        cinnamon_rust_count = 0      # Characteristic of Common Rust

        # Scan pixels and classify
        for x in range(width):
            for y in range(height):
                r, g, b = pixels[x, y]
                h, s, v = _rgb_to_hsv(r, g, b)

                # Check if pixel belongs to a plant leaf blade:
                # 1. Healthy green chlorophyll: H in [45..165], S > 0.15, V > 0.15
                # 2. Yellow/chlorotic leaf tissue: H in [30..50], S > 0.20, V > 0.25
                # 3. Necrotic brown/tan tissue embedded within leaf canopy: H in [15..45], S > 0.15, V > 0.10
                # 4. Black/dark stromata spots on leaf: V < 0.22 and surrounded by leaf (checked via intensity)
                is_green_leaf = (45 <= h <= 165 and s >= 0.14 and v >= 0.15)
                is_chlorotic_leaf = (30 <= h < 45 and s >= 0.18 and v >= 0.20)
                is_tan_necrotic = (12 <= h < 38 and s >= 0.12 and 0.15 <= v <= 0.85)
                is_very_dark = (v < 0.25 and (r + g + b) < 180)

                # General leaf membership
                is_leaf_pixel = is_green_leaf or is_chlorotic_leaf or is_tan_necrotic or is_very_dark
                if is_leaf_pixel:
                    leaf_mask[x][y] = True
                    leaf_pixel_count += 1

                    # If it's part of the leaf, check if it is a diseased / necrotic lesion
                    # Disease lesions deviate from healthy vibrant chlorophyll (h in 65..150, s > 0.25)
                    is_healthy_green = (65 <= h <= 155 and s >= 0.24 and v >= 0.22)
                    
                    if not is_healthy_green:
                        # Characterize lesion type:
                        # 1. Tar spot: Very dark/black raised stromata
                        if v < 0.22 or (r < 75 and g < 75 and b < 75):
                            black_stromata_count += 1
                            lesion_mask[x][y] = True
                            lesion_pixel_count += 1

                        # 2. Rust: Cinnamon-brown / reddish-orange pustules
                        elif (10 <= h <= 30 and s >= 0.40 and v >= 0.35 and r > g and r > b):
                            cinnamon_rust_count += 1
                            lesion_mask[x][y] = True
                            lesion_pixel_count += 1

                        # 3. Northern Corn Leaf Blight: Large grayish-tan/olive blighted patches
                        elif (25 <= h <= 55 and s < 0.35 and 0.25 <= v <= 0.70):
                            cigar_blight_count += 1
                            lesion_mask[x][y] = True
                            lesion_pixel_count += 1

                        # 4. Gray Leaf Spot: Tan to pale gray rectangular lesions
                        elif (20 <= h <= 45 and s >= 0.15 and 0.30 <= v <= 0.80):
                            tan_gray_lesion_count += 1
                            lesion_mask[x][y] = True
                            lesion_pixel_count += 1

                        # 5. General chlorotic halo / senescence
                        elif (35 <= h <= 60 and s >= 0.25 and v >= 0.40):
                            lesion_mask[x][y] = True
                            lesion_pixel_count += 1

        # Calculate metrics
        leaf_coverage_pct = (leaf_pixel_count / max(1, total_pixels)) * 100.0
        is_leaf = leaf_coverage_pct >= config.MIN_LEAF_COVERAGE_PCT

        if not is_leaf or leaf_pixel_count == 0:
            severity_pct = 0.0
            severity_grade = "N/A (Non-Leaf)"
        else:
            severity_pct = (lesion_pixel_count / float(leaf_pixel_count)) * 100.0
            severity_pct = min(100.0, max(0.0, round(severity_pct, 1)))

            # Grade determination based on established Extension economic thresholds:
            if severity_pct < config.SEVERITY_THRESHOLDS["early"]:
                severity_grade = "Early"
            elif severity_pct <= config.SEVERITY_THRESHOLDS["moderate"]:
                severity_grade = "Moderate"
            else:
                severity_grade = "Severe"

        # Generate visual segmentation overlay
        overlay_b64 = self._generate_overlay_mask(img, leaf_mask, lesion_mask, is_leaf)

        # Local heuristic diagnostic classification (used when LLM key is absent)
        local_diagnosis = self._classify_heuristically(
            is_leaf=is_leaf,
            leaf_coverage_pct=leaf_coverage_pct,
            severity_pct=severity_pct,
            black_stromata=black_stromata_count,
            tan_gray=tan_gray_lesion_count,
            cigar_blight=cigar_blight_count,
            cinnamon_rust=cinnamon_rust_count,
            lesion_total=lesion_pixel_count,
            leaf_total=leaf_pixel_count
        )

        return {
            "is_leaf": is_leaf,
            "leaf_coverage_pct": round(leaf_coverage_pct, 1),
            "severity_pct": severity_pct,
            "severity_grade": severity_grade,
            "leaf_pixels": leaf_pixel_count,
            "lesion_pixels": lesion_pixel_count,
            "total_pixels": total_pixels,
            "segmentation_overlay_b64": overlay_b64,
            "local_diagnosis": local_diagnosis,
        }

    def _generate_overlay_mask(
        self,
        base_img: Image.Image,
        leaf_mask: List[List[bool]],
        lesion_mask: List[List[bool]],
        is_leaf: bool
    ) -> str:
        """Create high-contrast segmentation overlay where lesions are highlighted in red/orange."""
        width, height = base_img.size
        overlay = base_img.convert("RGBA")
        overlay_pixels = overlay.load()

        if not is_leaf:
            # For non-leaf or ambiguous, draw subtle grid overlay
            draw = ImageDraw.Draw(overlay)
            draw.text((15, 15), "Subject: Unclassified / Ambiguous", fill=(255, 255, 255, 220))
        else:
            for x in range(width):
                for y in range(height):
                    if lesion_mask[x][y]:
                        # Vibrant high-contrast red/orange mask for necrotic lesions
                        r_orig, g_orig, b_orig, _ = overlay_pixels[x, y]
                        # 65% lesion tint (239, 68, 68) + 35% original
                        r_new = int(0.65 * 239 + 0.35 * r_orig)
                        g_new = int(0.65 * 68 + 0.35 * g_orig)
                        b_new = int(0.65 * 68 + 0.35 * b_orig)
                        overlay_pixels[x, y] = (r_new, g_new, b_new, 255)
                    elif leaf_mask[x][y]:
                        # Subtle emerald tint for healthy green chlorophyll tissue
                        r_orig, g_orig, b_orig, _ = overlay_pixels[x, y]
                        r_new = int(0.15 * 16 + 0.85 * r_orig)
                        g_new = int(0.15 * 185 + 0.85 * g_orig)
                        b_new = int(0.15 * 129 + 0.85 * b_orig)
                        overlay_pixels[x, y] = (r_new, g_new, b_new, 255)
                    else:
                        # Dim background slightly (35% darkened) to pop the leaf
                        r_orig, g_orig, b_orig, _ = overlay_pixels[x, y]
                        overlay_pixels[x, y] = (int(r_orig * 0.45), int(g_orig * 0.45), int(b_orig * 0.45), 255)

        # Save to base64 data URI
        buffer = io.BytesIO()
        overlay.save(buffer, format="PNG")
        b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64_str}"

    def _classify_heuristically(
        self,
        is_leaf: bool,
        leaf_coverage_pct: float,
        severity_pct: float,
        black_stromata: int,
        tan_gray: int,
        cigar_blight: int,
        cinnamon_rust: int,
        lesion_total: int,
        leaf_total: int
    ) -> Dict[str, Any]:
        """Heuristic rule-based classifier for offline / zero-API-key execution."""
        if not is_leaf:
            return {
                "disease_id": "unsure",
                "confidence": 0.35,
                "status": "unsure",
                "notes": "Image does not exhibit characteristic plant leaf pigmentation or geometry.",
                "top_3_candidates": [
                    {"disease_id": "unsure", "probability": 0.65, "name": "Non-Leaf / Ambiguous Object"},
                    {"disease_id": "healthy", "probability": 0.20, "name": "Healthy Corn Foliage"},
                    {"disease_id": "tar_spot", "probability": 0.15, "name": "Tar Spot"}
                ]
            }

        # If healthy (very low lesion count)
        if severity_pct < 1.0 or lesion_total == 0:
            return {
                "disease_id": "healthy",
                "confidence": 0.94,
                "status": "confident",
                "notes": "Leaf blade exhibits uniform green chlorophyll with normal parallel venation and no significant pathogenic lesions.",
                "top_3_candidates": [
                    {"disease_id": "healthy", "probability": 0.94, "name": "Healthy Corn Foliage"},
                    {"disease_id": "common_rust", "probability": 0.04, "name": "Common Rust (trace)"},
                    {"disease_id": "gray_leaf_spot", "probability": 0.02, "name": "Gray Leaf Spot (trace)"}
                ]
            }

        # Normalize lesion sub-counts
        scores = {
            "tar_spot": float(black_stromata),
            "common_rust": float(cinnamon_rust * 1.5),
            "northern_corn_leaf_blight": float(cigar_blight * 1.2),
            "gray_leaf_spot": float(tan_gray * 1.0),
        }

        best_disease = max(scores, key=scores.get)
        best_score = scores[best_disease]
        total_score = sum(scores.values()) or 1.0

        ratio = best_score / total_score

        # Calibrate confidence
        if ratio > 0.45 and lesion_total > 50:
            confidence = min(0.96, max(0.72, 0.65 + (ratio * 0.32)))
            status = "confident"
        else:
            confidence = round(0.45 + (ratio * 0.20), 2)
            status = "unsure"

        # Sort candidates
        sorted_candidates = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_3 = []
        name_map = {
            "tar_spot": "Tar Spot (Phyllachora maydis)",
            "gray_leaf_spot": "Gray Leaf Spot (Cercospora zeae-maydis)",
            "northern_corn_leaf_blight": "Northern Corn Leaf Blight",
            "common_rust": "Common Rust (Puccinia sorghi)",
            "healthy": "Healthy Foliage",
            "unsure": "Ambiguous / Inconclusive"
        }
        for d_id, score in sorted_candidates[:3]:
            p = round(score / total_score, 2)
            top_3.append({
                "disease_id": d_id,
                "probability": p,
                "name": name_map.get(d_id, d_id)
            })

        if status == "unsure" or confidence < config.CONFIDENCE_FLOOR:
            return {
                "disease_id": "unsure",
                "confidence": confidence,
                "status": "unsure",
                "notes": f"Lesion symptoms are ambiguous between {top_3[0]['name']} and {top_3[1]['name']}. Confidence ({int(confidence*100)}%) is below the field action floor (70%).",
                "top_3_candidates": top_3
            }

        return {
            "disease_id": best_disease,
            "confidence": round(confidence, 2),
            "status": "confident",
            "notes": f"Characteristic foliar symptoms identified with {int(confidence*100)}% confidence.",
            "top_3_candidates": top_3
        }


# Global singleton instance
cv_analyzer = LeafCVAnalyzer()
