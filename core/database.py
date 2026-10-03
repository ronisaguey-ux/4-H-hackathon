"""SQLite Scouting History & Field Database.

Persists scouting scans, tracks disease progression over time across fields,
and computes spread velocity and action recommendations.
"""
from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
import config


class ScoutingDatabase:
    """Manages the local SQLite database for crop health history."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize tables and indices."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    field_id TEXT NOT NULL DEFAULT 'Main Field',
                    timestamp TEXT NOT NULL,
                    disease_id TEXT NOT NULL,
                    disease_name TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    severity_pct REAL NOT NULL,
                    severity_grade TEXT NOT NULL,
                    is_confident INTEGER NOT NULL DEFAULT 1,
                    thumbnail_b64 TEXT,
                    notes TEXT,
                    action_taken TEXT DEFAULT 'Scouted'
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_field ON scans(field_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(timestamp)")
            conn.commit()

    def save_scan(
        self,
        field_id: str,
        disease_id: str,
        disease_name: str,
        confidence: float,
        severity_pct: float,
        severity_grade: str,
        is_confident: bool = True,
        thumbnail_b64: Optional[str] = None,
        notes: str = "",
        action_taken: str = "Scouted",
        timestamp: Optional[str] = None
    ) -> int:
        """Insert a scouting record and return its row ID."""
        ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scans (
                    field_id, timestamp, disease_id, disease_name, confidence,
                    severity_pct, severity_grade, is_confident, thumbnail_b64, notes, action_taken
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    field_id.strip() or "Main Field",
                    ts,
                    disease_id,
                    disease_name,
                    float(confidence),
                    float(severity_pct),
                    severity_grade,
                    1 if is_confident else 0,
                    thumbnail_b64 or "",
                    notes or "",
                    action_taken
                )
            )
            conn.commit()
            return cursor.lastrowid

    def get_scans(self, field_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent scans, optionally filtered by field ID."""
        with self._get_connection() as conn:
            if field_id and field_id.strip().lower() != "all":
                cur = conn.execute(
                    "SELECT * FROM scans WHERE field_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (field_id.strip(), limit)
                )
            else:
                cur = conn.execute("SELECT * FROM scans ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def get_unique_fields(self) -> List[str]:
        """Return list of distinct field names in the database."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT DISTINCT field_id FROM scans ORDER BY field_id ASC")
            return [row["field_id"] for row in cur.fetchall()]

    def get_field_analytics(self, field_id: str) -> Dict[str, Any]:
        """Compute severity progression trend and action status for a field."""
        clean_id = field_id.strip()
        scans = self.get_scans(field_id=clean_id, limit=20)
        if not scans:
            return {
                "field_id": clean_id,
                "scan_count": 0,
                "latest_severity_pct": 0.0,
                "latest_grade": "N/A",
                "trend": "Insufficient Data",
                "trajectory_description": "No prior scans recorded for this field plot.",
                "action_recommendation": "Begin weekly baseline scouting at VT (tasseling)."
            }

        scans_chronological = list(reversed(scans))
        latest = scans[0]
        latest_sev = latest["severity_pct"]
        latest_disease = latest["disease_name"]

        # Calculate severity trend
        if len(scans_chronological) >= 2:
            prev_sev = scans_chronological[-2]["severity_pct"]
            diff = latest_sev - prev_sev
            if diff > 3.0:
                trend = "Rapidly Spreading (+{:.1f}%)".format(diff)
                trajectory_desc = f"Pathogen severity increased from {prev_sev}% to {latest_sev}%. Favorable weather is accelerating sporulation."
                action_rec = "Fungicide application window is active. Check pre-harvest interval before application."
            elif diff > 0.5:
                trend = "Slight Increase (+{:.1f}%)".format(diff)
                trajectory_desc = f"Minor disease progression noted ({prev_sev}% -> {latest_sev}%). Canopy microclimate humid."
                action_rec = "Re-scout in 48 hours. Prepare sprayer if lesions reach ear leaf."
            elif diff < -0.5:
                trend = "Decreasing (-{:.1f}%)".format(abs(diff))
                trajectory_desc = "Foliar damage contained. Dry weather or fungicide application arrested spread."
                action_rec = "Maintain scouting interval every 7 days through R4."
            else:
                trend = "Stable (±0.5%)"
                trajectory_desc = f"Severity holding steady at {latest_sev}%."
                action_rec = "Continue standard scouting protocol."
        else:
            trend = "Baseline Scan Recorded"
            trajectory_desc = f"Initial field inspection established baseline at {latest_sev}% severity."
            action_rec = "Conduct follow-up scan in 3 to 5 days to establish spread rate."

        return {
            "field_id": clean_id,
            "scan_count": len(scans),
            "latest_disease": latest_disease,
            "latest_severity_pct": latest_sev,
            "latest_grade": latest["severity_grade"],
            "trend": trend,
            "trajectory_description": trajectory_desc,
            "action_recommendation": action_rec,
            "history_points": [
                {
                    "timestamp": s["timestamp"][:10],
                    "severity_pct": s["severity_pct"],
                    "disease": s["disease_name"],
                    "grade": s["severity_grade"]
                }
                for s in scans_chronological[-7:]
            ]
        }

    def delete_scan(self, scan_id: int) -> bool:
        """Delete a single scan record."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
            conn.commit()
            return cur.rowcount > 0

    def seed_demo_history(self) -> None:
        """Seed realistic scouting progression for demonstration."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) as count FROM scans")
            count = cur.fetchone()["count"]
            if count > 0:
                return  # Already seeded or has data

        # Add 3 progression points for demo field "North Pivot - Section 4"
        now = datetime.datetime.now(datetime.timezone.utc)
        demo_points = [
            (
                "North Pivot - Section 4",
                (now - datetime.timedelta(days=12)).isoformat(),
                "healthy",
                "Healthy Corn Foliage",
                0.95,
                0.2,
                "Early",
                "VT Scout: Clean canopy, no lesions detected on lower or middle leaves.",
                "Routine Scout"
            ),
            (
                "North Pivot - Section 4",
                (now - datetime.timedelta(days=6)).isoformat(),
                "tar_spot",
                "Tar Spot",
                0.89,
                3.4,
                "Early",
                "R1 Silking: Trace punctate black stromata observed on 3rd leaf below ear leaf.",
                "Monitoring Spread"
            ),
            (
                "North Pivot - Section 4",
                (now - datetime.timedelta(days=1)).isoformat(),
                "tar_spot",
                "Tar Spot",
                0.94,
                14.2,
                "Moderate",
                "R2 Blister: Stromata rapidly spreading onto ear leaf following 3 humid rain days.",
                "Fungicide Recommended"
            ),
        ]
        with self._get_connection() as conn:
            for field, ts, d_id, d_name, conf, sev, grade, note, act in demo_points:
                conn.execute(
                    """
                    INSERT INTO scans (
                        field_id, timestamp, disease_id, disease_name, confidence,
                        severity_pct, severity_grade, is_confident, thumbnail_b64, notes, action_taken
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)
                    """,
                    (field, ts, d_id, d_name, conf, sev, grade, 1, note, act)
                )
            conn.commit()


# Global singleton instance
database = ScoutingDatabase()
