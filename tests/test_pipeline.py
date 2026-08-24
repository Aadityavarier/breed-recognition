"""
tests/test_pipeline.py
======================
Validates the mock-ready inference engine (src/inference_engine.py).

Run with:
    pytest tests/test_pipeline.py -v
"""

import sys
import json
from pathlib import Path
import io
import numpy as np

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_pil_image(width=224, height=224, mode="RGB"):
    """Create a random PIL Image for testing without needing real image files."""
    from PIL import Image as PILImage
    arr = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    return PILImage.fromarray(arr, mode)


def _make_solid_image(color=(128, 64, 32), size=(224, 224)):
    """Create a solid-colour PIL image (deterministic for hash-based mock)."""
    from PIL import Image as PILImage
    return PILImage.new("RGB", size, color)


# ---------------------------------------------------------------------------
# Breed Mapping Tests
# ---------------------------------------------------------------------------

class TestBreedMapping:
    def test_mapping_file_exists(self):
        mapping_path = REPO_ROOT / "models" / "breed_mapping.json"
        assert mapping_path.exists(), "models/breed_mapping.json must exist"

    def test_mapping_has_60_breeds(self):
        mapping_path = REPO_ROOT / "models" / "breed_mapping.json"
        with open(mapping_path) as f:
            data = json.load(f)
        classes = data.get("classes", {})
        assert len(classes) == 60, (
            f"Expected 60 breeds in mapping, got {len(classes)}"
        )

    def test_mapping_keys_are_integers(self):
        mapping_path = REPO_ROOT / "models" / "breed_mapping.json"
        with open(mapping_path) as f:
            data = json.load(f)
        classes = data.get("classes", {})
        for k in classes:
            assert str(int(k)) == str(k), f"Key {k!r} is not an integer string"

    def test_mapping_has_required_keys(self):
        mapping_path = REPO_ROOT / "models" / "breed_mapping.json"
        with open(mapping_path) as f:
            data = json.load(f)
        assert "classes" in data
        assert "categories" in data
        assert "rare_breeds" in data

    def test_sahiwal_and_murrah_present(self):
        """Core breeds must always be present."""
        mapping_path = REPO_ROOT / "models" / "breed_mapping.json"
        with open(mapping_path) as f:
            data = json.load(f)
        all_breeds = set(data["classes"].values())
        assert "Sahiwal"   in all_breeds, "Sahiwal must be in mapping"
        assert "Murrah"    in all_breeds, "Murrah must be in mapping"
        assert "Gir"       in all_breeds, "Gir must be in mapping"
        assert "Holstein_Friesian" in all_breeds


# ---------------------------------------------------------------------------
# Preprocessing Tests
# ---------------------------------------------------------------------------

class TestPreprocessing:
    def test_preprocess_output_shape(self):
        from src.inference_engine import preprocess_image
        img = _make_pil_image()
        result = preprocess_image(img)
        assert result.shape == (1, 224, 224, 3), f"Unexpected shape: {result.shape}"

    def test_preprocess_dtype(self):
        from src.inference_engine import preprocess_image
        img = _make_pil_image()
        result = preprocess_image(img)
        assert result.dtype == np.float32, f"Expected float32, got {result.dtype}"

    def test_preprocess_normalised_range(self):
        from src.inference_engine import preprocess_image
        img = _make_pil_image()
        result = preprocess_image(img)
        assert result.min() >= 0.0,  f"Min value {result.min()} is below 0"
        assert result.max() <= 1.01, f"Max value {result.max()} exceeds 1 (normalisation error)"

    def test_preprocess_non_square_input(self):
        """Non-square images should be resized to 224×224."""
        from src.inference_engine import preprocess_image
        img = _make_pil_image(width=640, height=480)
        result = preprocess_image(img)
        assert result.shape == (1, 224, 224, 3)

    def test_preprocess_rgba_converted(self):
        """RGBA images should be handled gracefully (converted to RGB)."""
        from PIL import Image as PILImage
        from src.inference_engine import preprocess_image
        arr  = np.random.randint(0, 256, (100, 100, 4), dtype=np.uint8)
        img  = PILImage.fromarray(arr, "RGBA")
        result = preprocess_image(img)
        assert result.shape == (1, 224, 224, 3)


# ---------------------------------------------------------------------------
# Mock Inference Output Structure Tests
# ---------------------------------------------------------------------------

class TestMockInference:
    def _run(self, img=None):
        from src.inference_engine import run_inference
        if img is None:
            img = _make_pil_image()
        return run_inference(img)

    def test_returns_dict(self):
        result = self._run()
        assert isinstance(result, dict)

    def test_required_keys(self):
        result = self._run()
        required = {"top1_breed", "top1_confidence", "top3",
                    "needs_expert", "backend", "inference_ms",
                    "xai_image_filename", "region_boosted"}
        missing = required - set(result.keys())
        assert not missing, f"Missing keys in result: {missing}"

    def test_top1_breed_is_string(self):
        result = self._run()
        assert isinstance(result["top1_breed"], str)
        assert len(result["top1_breed"]) > 0

    def test_confidence_in_range(self):
        result = self._run()
        conf = result["top1_confidence"]
        assert 0.0 <= conf <= 1.0, f"Confidence {conf} out of [0,1] range"

    def test_top3_structure(self):
        result = self._run()
        top3 = result["top3"]
        assert isinstance(top3, list), "top3 must be a list"
        assert 1 <= len(top3) <= 3, f"Expected 1-3 top predictions, got {len(top3)}"
        for item in top3:
            assert "breed"      in item, "Each top3 item must have 'breed'"
            assert "confidence" in item, "Each top3 item must have 'confidence'"
            assert isinstance(item["breed"], str)
            assert 0.0 <= item["confidence"] <= 1.0

    def test_top3_sorted_descending(self):
        result = self._run()
        confs  = [t["confidence"] for t in result["top3"]]
        assert confs == sorted(confs, reverse=True), "top3 must be sorted by confidence desc"

    def test_needs_expert_flag_true_when_low_confidence(self):
        """Manually patch to check the flag logic."""
        from src.inference_engine import EXPERT_THRESHOLD
        # A result with confidence below threshold must set needs_expert=True
        result = self._run()
        conf   = result["top1_confidence"]
        expected_flag = conf < EXPERT_THRESHOLD
        assert result["needs_expert"] == expected_flag, (
            f"needs_expert should be {expected_flag} for confidence {conf}"
        )

    def test_backend_key_is_valid(self):
        result = self._run()
        assert result["backend"] in {"onnx", "tflite", "mock"}, (
            f"Invalid backend: {result['backend']}"
        )

    def test_inference_ms_non_negative(self):
        result = self._run()
        assert result["inference_ms"] >= 0.0

    def test_deterministic_for_same_image(self):
        """Same image must always return same top-1 breed (mock is seeded)."""
        img = _make_solid_image(color=(100, 150, 200))
        r1  = self._run(img)
        r2  = self._run(img)
        assert r1["top1_breed"] == r2["top1_breed"], (
            "Mock inference is not deterministic for the same image"
        )

    def test_top1_in_top3(self):
        result = self._run()
        top3_breeds = [t["breed"] for t in result["top3"]]
        assert result["top1_breed"] == top3_breeds[0], (
            "top1_breed must match the first entry of top3"
        )

    def test_breed_name_in_mapping(self):
        """Returned breed must be one of the 60 known breeds."""
        from src.inference_engine import BREED_MAP
        result    = self._run()
        all_breeds = set(BREED_MAP.values())
        assert result["top1_breed"] in all_breeds, (
            f"'{result['top1_breed']}' is not in the 60-breed mapping"
        )


# ---------------------------------------------------------------------------
# Engine Status Tests
# ---------------------------------------------------------------------------

class TestEngineStatus:
    def test_get_engine_status_returns_dict(self):
        from src.inference_engine import get_engine_status
        s = get_engine_status()
        assert isinstance(s, dict)

    def test_engine_status_keys(self):
        from src.inference_engine import get_engine_status
        s = get_engine_status()
        for key in ("backend", "mock_mode", "num_breeds", "input_size",
                    "expert_threshold", "models_dir"):
            assert key in s, f"Missing key '{key}' in engine status"

    def test_num_breeds_is_60(self):
        from src.inference_engine import get_engine_status
        s = get_engine_status()
        assert s["num_breeds"] == 60, f"Expected 60 breeds, got {s['num_breeds']}"

    def test_input_size_is_224(self):
        from src.inference_engine import get_engine_status
        s = get_engine_status()
        assert s["input_size"] == 224

    def test_expert_threshold_is_reasonable(self):
        from src.inference_engine import get_engine_status
        s = get_engine_status()
        assert 0.5 <= s["expert_threshold"] <= 0.9
