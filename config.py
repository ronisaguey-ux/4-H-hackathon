"""Application configuration for CornShield AI."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
SAMPLE_DIR = DATA_DIR / "sample_specimens"
TREATMENTS_FILE = DATA_DIR / "treatments.json"
DATABASE_PATH = DATA_DIR / "scans.db"

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Diagnostic & Calibration parameters
CONFIDENCE_FLOOR = 0.70  # Explicit threshold: below this, return "unsure" path
MIN_LEAF_COVERAGE_PCT = 15.0  # Image must have at least 15% leaf tissue to be considered a leaf
SEVERITY_THRESHOLDS = {
    "early": 5.0,      # < 5% leaf area affected
    "moderate": 20.0,  # 5% to 20% leaf area affected
    # > 20% is severe
}

# API Keys resolution (Checks environment and local .env files)
def _find_api_key(key_name: str) -> str:
    """Find API key from environment, current .env, or known workspace locations."""
    # 1. Direct environment variable
    val = os.getenv(key_name)
    if val:
        return val.strip()

    # 2. Local .env file
    local_env = BASE_DIR / ".env"
    if local_env.exists():
        with open(local_env, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{key_name}="):
                    return line.strip().split("=", 1)[1].strip("\"' ")

    # 3. Known workspace locations on developer box
    candidate_envs = [
        Path("/home/roni/Roni_workspace/helpotron/.env"),
        Path("/home/roni/Roni_workspace/t2b/.env"),
    ]
    for env_path in candidate_envs:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith(f"{key_name}="):
                            k = line.strip().split("=", 1)[1].strip("\"' ")
                            if k:
                                return k
            except Exception:
                pass
    return ""

OPENROUTER_API_KEY = _find_api_key("OPENROUTER_API_KEY")
GEMINI_API_KEY = _find_api_key("GEMINI_API_KEY")

# Default multimodal vision model for OpenRouter
VISION_MODEL = os.getenv("VISION_MODEL", "google/gemini-3.8-flash")
FALLBACK_VISION_MODEL = "google/gemini-3.1-flash-lite"
