"""End-to-end integration tests for Flask API endpoints."""
import unittest
import io
from PIL import Image
from app import app
import config


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        from core.vision_client import vision_client
        self.old_key = vision_client.api_key
        vision_client.api_key = ""

    def tearDown(self):
        from core.vision_client import vision_client
        vision_client.api_key = self.old_key
        self.app_context.pop()

    def test_health_endpoint(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["confidence_floor"], 0.70)

    def test_treatments_endpoint(self):
        res = self.client.get("/api/treatments")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("tar_spot", data)
        self.assertIn("CPN-2012", data["tar_spot"]["source_title"])

    def test_samples_list_endpoint(self):
        res = self.client.get("/api/samples")
        self.assertEqual(res.status_code, 200)
        samples = res.get_json()
        self.assertEqual(len(samples), 6)
        ids = [s["id"] for s in samples]
        self.assertIn("tar_spot", ids)
        self.assertIn("ambiguous", ids)

    def test_sample_diagnosis_tar_spot(self):
        res = self.client.post("/api/samples/test/tar_spot?field_id=Unit_Test_Field")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["diagnosis"]["disease_id"], "tar_spot")
        self.assertGreater(data["severity"]["severity_pct"], 0.0)
        self.assertIn("Phyllachora maydis", data["treatment"]["pathogen"])
        self.assertTrue(data["severity"]["segmentation_overlay_b64"].startswith("data:image/png;base64,"))

    def test_sample_diagnosis_ambiguous_calibration(self):
        res = self.client.post("/api/samples/test/ambiguous?field_id=Unit_Test_Field")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        # Must trigger unsure path
        self.assertEqual(data["diagnosis"]["disease_id"], "unsure")
        self.assertFalse(data["diagnosis"]["is_confident"])
        self.assertEqual(data["diagnosis"]["calibration_status"], "FLAGGED_NON_LEAF")
        self.assertGreater(len(data["diagnosis"]["retake_instructions"]), 0)

    def test_diagnose_image_upload(self):
        # Create a tiny in-memory green test leaf image
        img = Image.new("RGB", (100, 100), color=(50, 160, 40))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        data = {
            "image": (buf, "test_leaf.jpg"),
            "field_id": "Field_Upload_Test"
        }
        res = self.client.post("/api/diagnose", data=data, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 200)
        res_data = res.get_json()
        self.assertTrue(res_data["success"])
        self.assertEqual(res_data["field_id"], "Field_Upload_Test")
        self.assertIn("diagnosis", res_data)
        self.assertIn("treatment", res_data)


if __name__ == "__main__":
    unittest.main()
