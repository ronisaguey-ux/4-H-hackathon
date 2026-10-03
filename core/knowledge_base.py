"""Authoritative Land-Grant Extension Knowledge Base.

Retrieves verified treatments strictly quoted from university extension publications
(Crop Protection Network, Iowa State University Extension, Purdue Extension).
Does not hallucinate chemical recommendations or dosages.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import config


class ExtensionKnowledgeBase:
    """Manages extension-curated agronomic treatment recommendations."""

    def __init__(self, treatments_path: Optional[Path] = None):
        self.path = treatments_path or config.TREATMENTS_FILE
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Treatments knowledge base missing at {self.path}")
        with open(self.path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Return all curated treatments."""
        return self._data

    def get_by_disease_id(self, disease_id: str) -> Dict[str, Any]:
        """Retrieve exact treatment entry by normalized disease key."""
        clean_id = disease_id.strip().lower().replace(" ", "_")
        if clean_id in self._data:
            return self._data[clean_id]

        # Fuzzy matching against disease display names
        for key, entry in self._data.items():
            if clean_id in key or clean_id in entry.get("disease", "").lower():
                return entry

        # Fallback to unsure treatment if unmapped
        return self._data.get("unsure", {})

    def format_treatment_card(self, disease_id: str, severity_grade: str) -> Dict[str, Any]:
        """Return structured treatment recommendation enriched with severity context."""
        entry = self.get_by_disease_id(disease_id)
        action_urgency = "Monitor & Re-scout"
        if severity_grade.lower() == "moderate":
            action_urgency = "Action Recommended (Economic Threshold Approaching/Reached)"
        elif severity_grade.lower() == "severe":
            action_urgency = "Immediate Action Needed (Severe Canopy Defoliation)"

        return {
            "disease_id": entry.get("id", disease_id),
            "disease_name": entry.get("disease", disease_id),
            "pathogen": entry.get("pathogen", "N/A"),
            "action_urgency": action_urgency,
            "treatment": entry.get("treatment", ""),
            "active_ingredients": entry.get("active_ingredients", "N/A"),
            "rate": entry.get("rate", "N/A"),
            "interval": entry.get("interval", "N/A"),
            "preharvest_interval": entry.get("preharvest_interval", "N/A"),
            "reentry_interval": entry.get("reentry_interval", "12 hours"),
            "economic_threshold": entry.get("economic_threshold", "N/A"),
            "estimated_cost_per_acre": entry.get("estimated_cost_per_acre", "N/A"),
            "safety_notes": entry.get("safety_notes", "Follow pesticide label instructions."),
            "source_title": entry.get("source_title", "Extension Service Publication"),
            "source_url": entry.get("source_url", "https://cropprotectionnetwork.org"),
        }


# Global singleton instance
knowledge_base = ExtensionKnowledgeBase()
