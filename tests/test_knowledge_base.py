"""Unit tests for the Land-Grant Extension Knowledge Base."""
import unittest
from pathlib import Path
from core.knowledge_base import ExtensionKnowledgeBase


class TestKnowledgeBase(unittest.TestCase):
    def setUp(self):
        self.kb = ExtensionKnowledgeBase()

    def test_load_all_treatments(self):
        all_treatments = self.kb.get_all()
        self.assertIn("tar_spot", all_treatments)
        self.assertIn("gray_leaf_spot", all_treatments)
        self.assertIn("northern_corn_leaf_blight", all_treatments)
        self.assertIn("common_rust", all_treatments)
        self.assertIn("healthy", all_treatments)
        self.assertIn("unsure", all_treatments)

    def test_tar_spot_citations_and_specs(self):
        entry = self.kb.get_by_disease_id("tar_spot")
        self.assertEqual(entry["disease"], "Tar Spot")
        self.assertIn("Phyllachora maydis", entry["pathogen"])
        self.assertTrue(len(entry["treatment"]) > 20)
        self.assertTrue(len(entry["active_ingredients"]) > 5)
        self.assertTrue(len(entry["rate"]) > 3)
        self.assertTrue(len(entry["source_title"]) > 10)
        self.assertTrue(entry["source_url"].startswith("http"))
        self.assertIn("CPN-2012", entry["source_title"])

    def test_unmapped_disease_fallback_to_unsure(self):
        entry = self.kb.get_by_disease_id("unknown_alien_fungus")
        self.assertEqual(entry["id"], "unsure")
        self.assertIn("Unsure", entry["disease"])

    def test_format_treatment_card_urgency(self):
        card_early = self.kb.format_treatment_card("tar_spot", "Early")
        self.assertEqual(card_early["action_urgency"], "Monitor & Re-scout")

        card_severe = self.kb.format_treatment_card("tar_spot", "Severe")
        self.assertIn("Immediate Action", card_severe["action_urgency"])


if __name__ == "__main__":
    unittest.main()
