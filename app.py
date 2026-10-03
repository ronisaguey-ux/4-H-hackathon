"""CornShield AI - Midwest Corn Foliar Disease Early-Detection & Severity Engine.

Flask Application & RESTful API.
"""
from __future__ import annotations

import base64
import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, render_template, request, send_from_directory
from PIL import Image

import config
from core.calibration import calibrator
from core.cv_analyzer import cv_analyzer
from core.database import database
from core.knowledge_base import knowledge_base
from core.vision_client import vision_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cornshield")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB maximum upload


def _create_thumbnail_b64(image: Image.Image, size: int = 120) -> str:
    """Create a lightweight JPEG thumbnail encoded as base64."""
    thumb = image.copy().convert("RGB")
    thumb.thumbnail((size, size))
    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=75)
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"


def _load_image_from_request() -> Optional[Image.Image]:
    """Extract PIL Image from either multipart file upload or JSON base64."""
    # Check multipart files
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename:
            return Image.open(file.stream)

    # Check JSON payload
    if request.is_json:
        data = request.get_json() or {}
        b64_str = data.get("image_b64", "")
        if b64_str:
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_str)
            return Image.open(io.BytesIO(raw_bytes))

    return None


@app.route("/")
def index():
    """Render mobile-first diagnostic application."""
    fields = database.get_unique_fields()
    if not fields:
        fields = ["North 40 (Demo)", "Section 12 - South Pivot", "River Bottom 80"]
    return render_template("index.html", fields=fields)


@app.route("/health", methods=["GET"])
def health():
    """Healthcheck endpoint reporting system status."""
    return jsonify({
        "status": "healthy",
        "service": "CornShield AI",
        "cloud_vision_enabled": vision_client.is_cloud_enabled(),
        "vision_model": config.VISION_MODEL if vision_client.is_cloud_enabled() else "Local Heuristic CV Engine",
        "confidence_floor": config.CONFIDENCE_FLOOR,
        "database_connected": config.DATABASE_PATH.exists(),
    })


@app.route("/api/treatments", methods=["GET"])
def get_treatments():
    """Return all curated extension treatments and citations."""
    return jsonify(knowledge_base.get_all())


@app.route("/api/scans", methods=["GET"])
def get_scans():
    """Return scouting history log."""
    field_id = request.args.get("field_id")
    limit = int(request.args.get("limit", 50))
    scans = database.get_scans(field_id=field_id, limit=limit)
    return jsonify(scans)


@app.route("/api/scans/<int:scan_id>", methods=["DELETE"])
def delete_scan(scan_id: int):
    """Delete a scouting entry."""
    success = database.delete_scan(scan_id)
    return jsonify({"success": success})


@app.route("/api/field-analytics", methods=["GET"])
def get_field_analytics():
    """Return field severity progression trend and recommendations."""
    field_id = request.args.get("field_id", "North Pivot - Section 4")
    analytics = database.get_field_analytics(field_id)
    return jsonify(analytics)


@app.route("/api/samples", methods=["GET"])
def list_sample_specimens():
    """List pre-loaded field test specimens for instant judge evaluation."""
    samples = [
        {
            "id": "tar_spot",
            "filename": "tar_spot_specimen.jpg",
            "name": "Tar Spot (Severe Outbreak)",
            "expected_disease": "Tar Spot (Phyllachora maydis)",
            "description": "Scattered circular-oval black fungal stromata with necrotic halos."
        },
        {
            "id": "gray_leaf_spot",
            "filename": "gray_leaf_spot_specimen.jpg",
            "name": "Gray Leaf Spot (Moderate)",
            "expected_disease": "Gray Leaf Spot (Cercospora zeae-maydis)",
            "description": "Rectangular, vein-delimited tan necrotic lesions parallel to veins."
        },
        {
            "id": "northern_blight",
            "filename": "northern_blight_specimen.jpg",
            "name": "Northern Corn Leaf Blight",
            "expected_disease": "Northern Corn Leaf Blight (Exserohilum turcicum)",
            "description": "Large elliptical cigar-shaped lesions with grayish-tan blighted centers."
        },
        {
            "id": "common_rust",
            "filename": "common_rust_specimen.jpg",
            "name": "Common Rust (Puccinia sorghi)",
            "expected_disease": "Common Rust",
            "description": "Powdery cinnamon-brown pustules scattered across blade."
        },
        {
            "id": "healthy",
            "filename": "healthy_leaf_specimen.jpg",
            "name": "Healthy Corn Leaf",
            "expected_disease": "Healthy Corn Foliage",
            "description": "Vibrant chlorophyll green blade, clean parallel venation, zero lesions."
        },
        {
            "id": "ambiguous",
            "filename": "ambiguous_specimen.jpg",
            "name": "Non-Leaf / Ambiguous Object (Rock / Glare)",
            "expected_disease": "Unsure / Ambiguous Scan",
            "description": "Tests calibration floor: system must refuse confident guess and hedge honestly."
        }
    ]
    return jsonify(samples)


@app.route("/api/samples/image/<filename>")
def get_sample_image(filename: str):
    """Serve a sample specimen image file."""
    return send_from_directory(config.SAMPLE_DIR, filename)


@app.route("/api/diagnose", methods=["POST"])
def diagnose():
    """Main diagnostic pipeline: Image -> CV Severity -> Vision AI -> Calibration -> Treatment."""
    try:
        image = _load_image_from_request()
        if not image:
            return jsonify({"error": "No image provided in request."}), 400

        field_id = request.form.get("field_id") or "Main Field"
        notes = request.form.get("notes") or ""

        # Check if caller provided field info in JSON
        if request.is_json:
            data = request.get_json() or {}
            field_id = data.get("field_id", field_id)
            notes = data.get("notes", notes)

        # 1. Computer Vision Segmentation & Severity Analysis
        cv_results = cv_analyzer.analyze_leaf_image(image)

        # 2. Vision Model Diagnostic Inference (Cloud LLM or Local CV)
        vis_results = vision_client.diagnose_image(image, cv_results)

        # 3. Calibration & Guardrail Enforcement (Confidence Floor 0.70 & Non-Leaf Check)
        calibration = calibrator.calibrate_diagnosis(
            raw_disease_id=vis_results.get("disease_id", "unsure"),
            raw_confidence=vis_results.get("confidence", 0.50),
            is_leaf=cv_results.get("is_leaf", False),
            leaf_coverage_pct=cv_results.get("leaf_coverage_pct", 0.0),
            top_candidates=vis_results.get("top_3_candidates")
        )

        final_disease_id = calibration["disease_id"]
        final_confidence = calibration["confidence"]
        is_confident = calibration["is_confident"]

        # 4. Authoritative Extension Treatment Lookup
        treatment_card = knowledge_base.format_treatment_card(
            disease_id=final_disease_id,
            severity_grade=cv_results.get("severity_grade", "Early")
        )

        # 5. Persist to SQLite Database
        thumbnail_b64 = _create_thumbnail_b64(image)
        action_taken = "Scouted"
        if not is_confident:
            action_taken = "Needs Retake / Verification"
        elif cv_results.get("severity_grade") == "Severe":
            action_taken = "Urgent Treatment Action"
        elif cv_results.get("severity_grade") == "Moderate":
            action_taken = "Fungicide Scheduled"

        scan_id = database.save_scan(
            field_id=field_id,
            disease_id=final_disease_id,
            disease_name=treatment_card["disease_name"],
            confidence=final_confidence,
            severity_pct=cv_results["severity_pct"],
            severity_grade=cv_results["severity_grade"],
            is_confident=is_confident,
            thumbnail_b64=thumbnail_b64,
            notes=notes,
            action_taken=action_taken
        )

        # 6. Retrieve Updated Field Analytics
        field_analytics = database.get_field_analytics(field_id)

        response_data = {
            "success": True,
            "scan_id": scan_id,
            "field_id": field_id,
            "diagnosis": {
                "disease_id": final_disease_id,
                "disease_name": treatment_card["disease_name"],
                "pathogen": treatment_card["pathogen"],
                "confidence": final_confidence,
                "is_confident": is_confident,
                "calibration_status": calibration["calibration_status"],
                "hedge_reason": calibration["hedge_reason"],
                "retake_instructions": calibration["retake_instructions"],
                "top_candidates": calibration["top_candidates"],
                "visual_symptoms": vis_results.get("visual_symptoms", []),
                "diagnostic_reasoning": vis_results.get("diagnostic_reasoning", ""),
                "inference_engine": vis_results.get("source", "local_engine")
            },
            "severity": {
                "severity_pct": cv_results["severity_pct"],
                "severity_grade": cv_results["severity_grade"],
                "leaf_coverage_pct": cv_results["leaf_coverage_pct"],
                "leaf_pixels": cv_results["leaf_pixels"],
                "lesion_pixels": cv_results["lesion_pixels"],
                "segmentation_overlay_b64": cv_results["segmentation_overlay_b64"]
            },
            "treatment": treatment_card,
            "field_analytics": field_analytics
        }
        return jsonify(response_data)

    except Exception as e:
        logger.exception("Error in diagnose endpoint")
        return jsonify({"error": str(e)}), 500


@app.route("/api/samples/test/<sample_id>", methods=["POST"])
def test_sample(sample_id: str):
    """Run diagnostic pipeline on pre-loaded specimen."""
    filename_map = {
        "tar_spot": "tar_spot_specimen.jpg",
        "gray_leaf_spot": "gray_leaf_spot_specimen.jpg",
        "northern_blight": "northern_blight_specimen.jpg",
        "common_rust": "common_rust_specimen.jpg",
        "healthy": "healthy_leaf_specimen.jpg",
        "ambiguous": "ambiguous_specimen.jpg"
    }
    filename = filename_map.get(sample_id)
    if not filename:
        return jsonify({"error": f"Unknown sample ID: {sample_id}"}), 404

    sample_path = config.SAMPLE_DIR / filename
    if not sample_path.exists():
        return jsonify({"error": f"Sample file not found: {filename}"}), 404

    image = Image.open(sample_path)
    field_id = request.args.get("field_id", "Test Plot A")

    cv_results = cv_analyzer.analyze_leaf_image(image)
    vis_results = vision_client.diagnose_image(image, cv_results)
    calibration = calibrator.calibrate_diagnosis(
        raw_disease_id=vis_results.get("disease_id", "unsure"),
        raw_confidence=vis_results.get("confidence", 0.50),
        is_leaf=cv_results.get("is_leaf", False),
        leaf_coverage_pct=cv_results.get("leaf_coverage_pct", 0.0),
        top_candidates=vis_results.get("top_3_candidates")
    )

    final_disease_id = calibration["disease_id"]
    final_confidence = calibration["confidence"]
    is_confident = calibration["is_confident"]

    treatment_card = knowledge_base.format_treatment_card(
        disease_id=final_disease_id,
        severity_grade=cv_results.get("severity_grade", "Early")
    )

    thumbnail_b64 = _create_thumbnail_b64(image)
    scan_id = database.save_scan(
        field_id=field_id,
        disease_id=final_disease_id,
        disease_name=treatment_card["disease_name"],
        confidence=final_confidence,
        severity_pct=cv_results["severity_pct"],
        severity_grade=cv_results["severity_grade"],
        is_confident=is_confident,
        thumbnail_b64=thumbnail_b64,
        notes=f"Test specimen: {filename}",
        action_taken="Specimen Verification"
    )

    field_analytics = database.get_field_analytics(field_id)

    return jsonify({
        "success": True,
        "scan_id": scan_id,
        "sample_id": sample_id,
        "field_id": field_id,
        "diagnosis": {
            "disease_id": final_disease_id,
            "disease_name": treatment_card["disease_name"],
            "pathogen": treatment_card["pathogen"],
            "confidence": final_confidence,
            "is_confident": is_confident,
            "calibration_status": calibration["calibration_status"],
            "hedge_reason": calibration["hedge_reason"],
            "retake_instructions": calibration["retake_instructions"],
            "top_candidates": calibration["top_candidates"],
            "visual_symptoms": vis_results.get("visual_symptoms", []),
            "diagnostic_reasoning": vis_results.get("diagnostic_reasoning", ""),
            "inference_engine": vis_results.get("source", "local_engine")
        },
        "severity": {
            "severity_pct": cv_results["severity_pct"],
            "severity_grade": cv_results["severity_grade"],
            "leaf_coverage_pct": cv_results["leaf_coverage_pct"],
            "leaf_pixels": cv_results["leaf_pixels"],
            "lesion_pixels": cv_results["lesion_pixels"],
            "segmentation_overlay_b64": cv_results["segmentation_overlay_b64"]
        },
        "treatment": treatment_card,
        "field_analytics": field_analytics
    })


if __name__ == "__main__":
    # Ensure database is seeded with demo history
    database.seed_demo_history()
    print("=" * 65)
    print(" CornShield AI - 4-H AI in Agriculture Platform")
    print(f" Server starting on http://{config.HOST}:{config.PORT}")
    print(f" Cloud Vision Enabled: {vision_client.is_cloud_enabled()}")
    print("=" * 65)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
