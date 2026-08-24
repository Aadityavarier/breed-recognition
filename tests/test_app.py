"""
tests/test_app.py
=================
Flask integration tests for the expert-dashboard API endpoints.

Run with:
    pytest tests/test_app.py -v
"""

import sys
import io
import json
import tempfile
import os
from pathlib import Path

import numpy as np
import pytest

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Override DB and uploads paths to use temp files during tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tmp_dirs(tmp_path_factory):
    """Create isolated temp dirs for DB and uploads during testing."""
    base = tmp_path_factory.mktemp("dashboard_test")
    uploads = base / "uploads"
    uploads.mkdir()
    return {"base": base, "uploads": uploads, "db": base / "test.db"}


@pytest.fixture(scope="module")
def app(tmp_dirs):
    """Create a Flask test app with isolated DB and upload paths."""
    import data.db as db_module

    # Point DB to temp file
    db_module.DB_PATH = tmp_dirs["db"]
    if hasattr(db_module._local, "conn") and db_module._local.conn:
        db_module._local.conn.close()
        db_module._local.conn = None

    import importlib.util
    spec = importlib.util.spec_from_file_location("dashboard_app", str(REPO_ROOT / "expert-dashboard" / "app.py"))
    dashboard_app = importlib.util.module_from_spec(spec)
    sys.modules["expert_dashboard.app"] = dashboard_app
    spec.loader.exec_module(dashboard_app)
    flask_app = dashboard_app.app

    # Patch upload folder
    dashboard_app.UPLOAD_FOLDER = tmp_dirs["uploads"]
    flask_app.config["TESTING"] = True
    flask_app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

    # Re-initialise DB
    db_module.init_db()

    return flask_app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Helper: create a minimal valid JPEG in memory
# ---------------------------------------------------------------------------

def _minimal_jpeg() -> bytes:
    """Return bytes of a tiny valid JPEG without needing files on disk."""
    from PIL import Image
    buf = io.BytesIO()
    img = Image.fromarray(
        np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8), "RGB"
    )
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200

    def test_health_returns_json(self, client):
        res  = client.get("/health")
        data = json.loads(res.data)
        assert "status" in data
        assert data["status"] == "ok"

    def test_health_has_engine_key(self, client):
        res  = client.get("/health")
        data = json.loads(res.data)
        assert "engine"   in data
        assert "mock_mode" in data


# ---------------------------------------------------------------------------
# Root / Dashboard
# ---------------------------------------------------------------------------

class TestRoot:
    def test_index_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200

    def test_index_contains_html(self, client):
        res = client.get("/")
        assert b"<!DOCTYPE html" in res.data or b"CattleAI" in res.data


# ---------------------------------------------------------------------------
# Stats Endpoint
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_returns_200(self, client):
        res = client.get("/api/stats")
        assert res.status_code == 200

    def test_stats_returns_json(self, client):
        res  = client.get("/api/stats")
        data = json.loads(res.data)
        assert isinstance(data, dict)

    def test_stats_required_fields(self, client):
        res  = client.get("/api/stats")
        data = json.loads(res.data)
        for field in ("total", "by_status", "by_breed",
                      "avg_confidence", "needs_expert_count"):
            assert field in data, f"Missing field '{field}' in /api/stats"

    def test_stats_total_is_int(self, client):
        res  = client.get("/api/stats")
        data = json.loads(res.data)
        assert isinstance(data["total"], int)


# ---------------------------------------------------------------------------
# History Endpoint
# ---------------------------------------------------------------------------

class TestHistory:
    def test_history_returns_200(self, client):
        res = client.get("/api/history")
        assert res.status_code == 200

    def test_history_pagination_structure(self, client):
        res  = client.get("/api/history?page=1&limit=5")
        data = json.loads(res.data)
        assert "scans"       in data
        assert "total"       in data
        assert "page"        in data
        assert "limit"       in data
        assert "total_pages" in data

    def test_history_records_is_list(self, client):
        res  = client.get("/api/history")
        data = json.loads(res.data)
        assert isinstance(data["scans"], list)

    def test_history_limit_respected(self, client):
        res  = client.get("/api/history?limit=3")
        data = json.loads(res.data)
        assert len(data["scans"]) <= 3

    def test_history_invalid_page_returns_400(self, client):
        res = client.get("/api/history?page=abc")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Predict Endpoint
# ---------------------------------------------------------------------------

class TestPredict:
    def test_predict_no_image_returns_400(self, client):
        res = client.post("/api/predict")
        assert res.status_code == 400

    def test_predict_empty_field_returns_400(self, client):
        res = client.post(
            "/api/predict",
            data={"image": (io.BytesIO(b""), "")},
            content_type="multipart/form-data",
        )
        assert res.status_code == 400

    def test_predict_invalid_format_returns_415(self, client):
        res = client.post(
            "/api/predict",
            data={"image": (io.BytesIO(b"hello"), "test.txt")},
            content_type="multipart/form-data",
        )
        assert res.status_code == 415

    def test_predict_valid_image_returns_200(self, client):
        jpeg_bytes = _minimal_jpeg()
        res = client.post(
            "/api/predict",
            data={"image": (io.BytesIO(jpeg_bytes), "cow.jpg")},
            content_type="multipart/form-data",
        )
        assert res.status_code == 200

    def test_predict_result_structure(self, client):
        jpeg_bytes = _minimal_jpeg()
        res  = client.post(
            "/api/predict",
            data={"image": (io.BytesIO(jpeg_bytes), "cow.jpg")},
            content_type="multipart/form-data",
        )
        data = json.loads(res.data)
        required = {
            "scan_id", "top1_breed", "top1_confidence",
            "top3", "needs_expert", "status", "backend",
            "inference_ms", "image_url", "timestamp",
            "xai_image_url", "qr_code_url", "blockchain_hash",
            "region_boosted"
        }
        missing = required - set(data.keys())
        assert not missing, f"Missing keys in /api/predict response: {missing}"

    def test_predict_scan_persisted_in_db(self, client):
        """After a predict call, the scan should appear in /api/history."""
        jpeg_bytes = _minimal_jpeg()
        client.post(
            "/api/predict",
            data={"image": (io.BytesIO(jpeg_bytes), "test_persist.jpg"),
                  "notes": "pytest-test"},
            content_type="multipart/form-data",
        )
        res  = client.get("/api/history?limit=1")
        data = json.loads(res.data)
        assert data["total"] >= 1, "DB should have at least 1 scan after predict"

    def test_predict_confidence_in_range(self, client):
        jpeg_bytes = _minimal_jpeg()
        res  = client.post(
            "/api/predict",
            data={"image": (io.BytesIO(jpeg_bytes), "conf_test.jpg")},
            content_type="multipart/form-data",
        )
        data = json.loads(res.data)
        conf = data.get("top1_confidence", -1)
        assert 0.0 <= conf <= 1.0, f"Confidence {conf} out of range"

    def test_predict_top3_is_list(self, client):
        jpeg_bytes = _minimal_jpeg()
        res  = client.post(
            "/api/predict",
            data={"image": (io.BytesIO(jpeg_bytes), "top3_test.jpg")},
            content_type="multipart/form-data",
        )
        data = json.loads(res.data)
        assert isinstance(data["top3"], list)
        assert 1 <= len(data["top3"]) <= 3


# ---------------------------------------------------------------------------
# Status Update Endpoint
# ---------------------------------------------------------------------------

class TestStatusUpdate:
    def _create_scan(self, client):
        jpeg_bytes = _minimal_jpeg()
        res  = client.post(
            "/api/predict",
            data={"image": (io.BytesIO(jpeg_bytes), "status_test.jpg")},
            content_type="multipart/form-data",
        )
        return json.loads(res.data)["scan_id"]

    def test_update_status_to_verified(self, client):
        scan_id = self._create_scan(client)
        res = client.post(
            "/api/verify",
            json={"scan_id": scan_id},
        )
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["success"] is True

    def test_update_status_to_retrain(self, client):
        scan_id = self._create_scan(client)
        res = client.post(
            "/api/retrain",
            json={"scan_id": scan_id},
        )
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["success"] is True

    def test_update_status_missing_fields(self, client):
        res = client.post("/api/verify", json={})
        assert res.status_code == 400

    def test_update_nonexistent_scan(self, client):
        res = client.post(
            "/api/verify",
            json={"scan_id": 999999},
        )
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Export Endpoint
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_returns_200(self, client):
        res = client.get("/api/export/audit_log")
        assert res.status_code == 200

    def test_export_content_type_json(self, client):
        res = client.get("/api/export/audit_log")
        assert "application/json" in res.content_type

    def test_export_is_list(self, client):
        res  = client.get("/api/export/audit_log")
        data = json.loads(res.data)
        assert isinstance(data, list)
