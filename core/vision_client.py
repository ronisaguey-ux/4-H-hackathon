"""Multimodal Vision Inference Client.

Connects to multimodal vision models (OpenRouter Gemini 3.8/3.1 Flash or direct Gemini API)
with strict JSON formatting, confidence floor enforcement, and automated fallback to the
local Computer Vision engine when no API key is present or offline.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from PIL import Image

import config
from .cv_analyzer import cv_analyzer

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are CornShield AI, an expert agricultural plant pathologist specializing in US Midwest corn (Zea mays) foliar diseases.
Your job is to examine photographs of corn leaves taken by farmers or verified botanical diagnostic reference specimens.

You diagnose specifically among:
1. "tar_spot" (Phyllachora maydis): small (0.5-2mm) raised, hard, black circular to oval fungal structures (stromata) scattered on the leaf blade, often with necrotic or chlorotic halos.
2. "gray_leaf_spot" (Cercospora zeae-maydis): rectangular, vein-delimited tan-to-gray necrotic lesions running parallel to leaf veins.
3. "northern_corn_leaf_blight" (Exserohilum turcicum): long, elliptical cigar-shaped grayish-green or tan lesions (1-6 inches).
4. "common_rust" (Puccinia sorghi): cinnamon-brown to golden powdery oval pustules scattered across both leaf surfaces.
5. "healthy": clean green corn leaf blade with normal parallel venation, free of pathogenic fungal lesions or pustules.
6. "unsure": for non-leaf objects, severely blurry images, heavy glare, or when visual symptoms are inconclusive / confidence is under 70%.

CRITICAL CALIBRATION RULES:
- Specimens may be outdoor field photographs or verified high-fidelity botanical reference specimens. Treat both as valid foliage to assess symptoms.
- If the image is NOT a plant leaf (e.g. coffee mug, granite rock, tool, vehicle, person), set "is_leaf": false, "disease_id": "unsure", and confidence <= 0.35.
- If you are not at least 70% certain of the specific pathogen, set "disease_id": "unsure" and explain what visual features are missing or ambiguous.
- Always provide top_3_candidates with their relative probabilities summing to ~1.0.

Respond strictly in valid JSON with this exact schema:
{
  "is_leaf": boolean,
  "disease_id": "tar_spot" | "gray_leaf_spot" | "northern_corn_leaf_blight" | "common_rust" | "healthy" | "unsure",
  "confidence": float between 0.0 and 1.0,
  "visual_symptoms": ["string description of observed visual traits"],
  "top_3_candidates": [
    {"disease_id": "string", "name": "string", "probability": float}
  ],
  "diagnostic_reasoning": "brief explanation of why this diagnosis was made and what makes it distinct from lookalikes"
}
"""


class VisionClient:
    """Manages multimodal vision requests with graceful local fallback."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or config.OPENROUTER_API_KEY
        self.model = model or config.VISION_MODEL

    def is_cloud_enabled(self) -> bool:
        """Return True if a valid API key is present."""
        return bool(self.api_key and len(self.api_key.strip()) > 10)

    def diagnose_image(self, image: Image.Image, cv_results: Dict[str, Any]) -> Dict[str, Any]:
        """Diagnose leaf image via Vision LLM if key is available, else local CV."""
        if not self.is_cloud_enabled():
            logger.info("No cloud vision API key configured. Executing local CV diagnostic engine.")
            local_res = cv_results.get("local_diagnosis", {})
            return {
                "source": "local_cv_engine",
                "disease_id": local_res.get("disease_id", "unsure"),
                "confidence": local_res.get("confidence", 0.50),
                "is_leaf": cv_results.get("is_leaf", False),
                "visual_symptoms": [
                    f"Leaf coverage: {cv_results.get('leaf_coverage_pct', 0)}%",
                    f"Measured lesion severity: {cv_results.get('severity_pct', 0)}% ({cv_results.get('severity_grade')})",
                    local_res.get("notes", "")
                ],
                "top_3_candidates": local_res.get("top_3_candidates", []),
                "diagnostic_reasoning": local_res.get("notes", "Classified using local color-space and lesion morphology engine.")
            }

        # Try cloud vision call
        try:
            return self._call_openrouter_vision(image, cv_results)
        except Exception as exc:
            logger.warning(f"Cloud vision call failed ({exc}). Falling back to local CV engine.")
            local_res = cv_results.get("local_diagnosis", {})
            return {
                "source": "local_cv_fallback_after_error",
                "disease_id": local_res.get("disease_id", "unsure"),
                "confidence": local_res.get("confidence", 0.50),
                "is_leaf": cv_results.get("is_leaf", False),
                "visual_symptoms": [
                    f"Leaf coverage: {cv_results.get('leaf_coverage_pct', 0)}%",
                    f"Measured lesion severity: {cv_results.get('severity_pct', 0)}% ({cv_results.get('severity_grade')})",
                    f"Cloud fallback note: {str(exc)[:100]}"
                ],
                "top_3_candidates": local_res.get("top_3_candidates", []),
                "diagnostic_reasoning": f"Local CV fallback activated: {local_res.get('notes', '')}"
            }

    def _call_openrouter_vision(self, image: Image.Image, cv_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute OpenRouter chat completion with image payload."""
        # Convert image to compressed JPEG data URL for optimal token efficiency
        rgb_img = image.convert("RGB")
        # Resize to max 800px on longest side for fast mobile upload
        max_dim = 800
        w, h = rgb_img.size
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))
            rgb_img = rgb_img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)

        import io
        buf = io.BytesIO()
        rgb_img.save(buf, format="JPEG", quality=85)
        b64_data = base64.b64encode(buf.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_data}"

        severity_info = f"Preliminary Computer Vision scan: Leaf coverage {cv_results.get('leaf_coverage_pct')}% | Affected lesion area {cv_results.get('severity_pct')}% ({cv_results.get('severity_grade')})."

        user_content = [
            {"type": "text", "text": f"Examine this corn leaf specimen. {severity_info}\nEvaluate leaf tissue, parallel venation, lesion morphology, and stromata/pustules. If non-plant, mark is_leaf=false. Respond with valid JSON matching the schema."},
            {"type": "image_url", "image_url": {"url": data_url}}
        ]

        payload = {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": 600,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"}
        }

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ronisaguey-ux/4-H-hackathon",
            "X-Title": "CornShield AI 4-H Ag Challenge"
        }

        with httpx.Client(timeout=25.0) as client:
            resp = client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            res_data = resp.json()

        raw_text = res_data["choices"][0]["message"]["content"]
        parsed = self._extract_json(raw_text)

        return {
            "source": f"cloud_vision_{self.model}",
            "disease_id": parsed.get("disease_id", "unsure"),
            "confidence": float(parsed.get("confidence", 0.50)),
            "is_leaf": bool(parsed.get("is_leaf", True)),
            "visual_symptoms": parsed.get("visual_symptoms", []),
            "top_3_candidates": parsed.get("top_3_candidates", []),
            "diagnostic_reasoning": parsed.get("diagnostic_reasoning", "")
        }

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Robustly extract and normalize JSON dictionary from model response."""
        text = text.strip()
        parsed: Dict[str, Any] = {}

        # 1. Direct parse
        try:
            parsed = json.loads(text)
        except Exception:
            # 2. Match markdown block ```json ... ```
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                except Exception:
                    pass

        # 3. Match first { to last }
        if not parsed:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    parsed = json.loads(text[start : end + 1])
                except Exception:
                    pass

        if not parsed or not isinstance(parsed, dict):
            return {
                "is_leaf": False,
                "disease_id": "unsure",
                "confidence": 0.35,
                "visual_symptoms": ["Unparseable model output"],
                "top_3_candidates": [
                    {"disease_id": "unsure", "name": "Ambiguous Scan", "probability": 0.70}
                ],
                "diagnostic_reasoning": "Could not parse JSON output from vision model."
            }

        # Normalize fields
        disease = (
            parsed.get("disease_id")
            or parsed.get("disease")
            or parsed.get("diagnosis")
            or "unsure"
        )
        is_leaf = parsed.get("is_leaf")
        if is_leaf is None:
            is_leaf = parsed.get("is_corn_leaf", True)

        confidence = parsed.get("confidence")
        if confidence is None:
            confidence = parsed.get("confidence_score") or parsed.get("probability", 0.50)

        # Normalize disease string
        clean_disease = str(disease).strip().lower().replace(" ", "_")
        if "tar" in clean_disease:
            clean_disease = "tar_spot"
        elif "gray" in clean_disease or "gls" in clean_disease or "cercospora" in clean_disease:
            clean_disease = "gray_leaf_spot"
        elif "blight" in clean_disease or "northern" in clean_disease or "turcicum" in clean_disease:
            clean_disease = "northern_corn_leaf_blight"
        elif "rust" in clean_disease or "puccinia" in clean_disease:
            clean_disease = "common_rust"
        elif "healthy" in clean_disease or "clean" in clean_disease or "normal" in clean_disease:
            clean_disease = "healthy"
        elif "unsure" in clean_disease or not is_leaf:
            clean_disease = "unsure"

        parsed["disease_id"] = clean_disease
        parsed["is_leaf"] = bool(is_leaf)
        try:
            parsed["confidence"] = float(confidence)
            if parsed["confidence"] > 1.0 and parsed["confidence"] <= 100.0:
                parsed["confidence"] /= 100.0
        except Exception:
            parsed["confidence"] = 0.50

        if "diagnostic_reasoning" not in parsed:
            parsed["diagnostic_reasoning"] = parsed.get("explanation") or parsed.get("reasoning") or ""

        return parsed


# Global singleton instance
vision_client = VisionClient()
