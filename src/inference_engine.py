"""
src/inference_engine.py — Offline Cattle Breed Inference Engine (Multimodal & XAI)
==================================================================================

Priority loading order:
  1. ONNX model via onnxruntime  (CPU only)
  2. TFLite model via tflite_runtime / tensorflow.lite
  3. Mock inference pipeline      (deterministic, no model files required)

All paths are resolved dynamically — no hardcoded absolutes.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
import random
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ENGINE_DIR  = Path(__file__).resolve().parent          # src/
_REPO_ROOT   = _ENGINE_DIR.parent                       # project root
_MODELS_DIR  = _REPO_ROOT / "models"
_MAPPING_FILE = _MODELS_DIR / "breed_mapping.json"

# Preferred model file locations (checked in order)
_ONNX_CANDIDATES = [
    _MODELS_DIR / "cattle_breed.onnx",
    _MODELS_DIR / "cattle_breed_mobilenet.onnx",
    _MODELS_DIR / "breed_classifier.onnx",
]
_TFLITE_CANDIDATES = [
    _MODELS_DIR / "tflite" / "cattle_breed_pro_v1_int8.tflite",
    _MODELS_DIR / "cattle_breed.tflite",
    _MODELS_DIR / "breed_classifier.tflite",
]

# Inference parameters
INPUT_SIZE   = 224          # MobileNetV2 standard input
MEAN         = 0.0          # Pre-normalised to [0,1]; adjust if needed
STD          = 1.0
EXPERT_THRESHOLD = 0.70     # confidence below this → needs_expert = True

# ---------------------------------------------------------------------------
# Breed mapping
# ---------------------------------------------------------------------------

def _load_breed_mapping() -> Dict[int, str]:
    """Load idx→breed mapping from models/breed_mapping.json."""
    if not _MAPPING_FILE.exists():
        logger.warning("breed_mapping.json not found — using sequential fallback labels")
        return {i: f"Breed_{i:02d}" for i in range(60)}
    with open(_MAPPING_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    classes = data.get("classes", {})
    return {int(k): v for k, v in classes.items()}


BREED_MAP: Dict[int, str] = _load_breed_mapping()
NUM_CLASSES = len(BREED_MAP)

# Rare breeds that require higher expert validation threshold
_RARE_BREEDS = set(json.loads(
    _MAPPING_FILE.read_text(encoding="utf-8")
).get("rare_breeds", [])) if _MAPPING_FILE.exists() else set()


# ---------------------------------------------------------------------------
# Preprocessing & XAI
# ---------------------------------------------------------------------------

def preprocess_image(image: Image.Image) -> np.ndarray:
    """Resize a PIL Image to INPUT_SIZE×INPUT_SIZE and normalise to [0, 1]."""
    img = image.convert("RGB")
    img = img.resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)


def preprocess_image_int8(image: Image.Image, input_scale: float, input_zero_point: int) -> np.ndarray:
    """Quantised INT8 preprocessing for TFLite INT8 models."""
    arr = preprocess_image(image)[0]
    arr_q = (arr / input_scale + input_zero_point).astype(np.int8)
    return np.expand_dims(arr_q, axis=0)


def generate_mock_gradcam(image: Image.Image, output_dir: Path) -> str:
    """
    Generates a simulated Grad-CAM heatmap overlay for Explainable AI (XAI)
    and saves it to the specified directory.
    Returns the generated filename.
    """
    # Deterministic blob position based on image hash to ensure consistency
    img_arr = np.array(image.convert("RGB").resize((32, 32)))
    seed = int(img_arr.mean() * 1000 + img_arr.std() * 100) % (2**31)
    rng = np.random.default_rng(seed)

    w, h = image.size
    heatmap = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(heatmap)

    # Draw 1-2 "attention" regions (e.g., focusing on hump, forehead, or dewlap)
    num_blobs = rng.integers(1, 3)
    for _ in range(num_blobs):
        cx = rng.integers(w // 4, 3 * w // 4)
        cy = rng.integers(h // 4, 3 * h // 4)
        r_x = rng.integers(w // 8, w // 3)
        r_y = rng.integers(h // 8, h // 3)
        # Red/orange transparent heatmap color
        draw.ellipse((cx - r_x, cy - r_y, cx + r_x, cy + r_y), fill=(255, 69, 0, 110))

    # Composite over original
    out_img = Image.alpha_composite(image.convert("RGBA"), heatmap).convert("RGB")
    
    filename = f"xai_{uuid.uuid4().hex[:8]}.jpg"
    out_path = output_dir / filename
    out_img.save(out_path, format="JPEG", quality=85)
    return filename


def generate_vet_estimates(breed: str, age_input: str) -> dict:
    """
    Simulates Veterinary Health & Growth Estimation.
    """
    # Deterministic generation based on breed string
    rng = np.random.default_rng(sum(ord(c) for c in breed))
    
    # Basic weight heuristic
    base_weight = 350
    if "Buffalo" in breed or breed in ["Murrah", "Jaffrabadi", "Nili_Ravi"]:
        base_weight = 550
    elif breed in ["Kankrej", "Gir", "Ongole"]:
        base_weight = 450
        
    estimated_weight = int(rng.normal(base_weight, 50))
    
    health_status = "Healthy"
    # Small chance to simulate an active learning / health flag
    if rng.random() < 0.15:
        health_status = "Flagged: Skin lesions / Potential LSD risk"
        
    return {
        "estimated_weight_kg": str(estimated_weight),
        "health_status": health_status,
        "age_estimation": age_input if age_input else f"{rng.integers(2, 6)} years"
    }


# ---------------------------------------------------------------------------
# Model loaders
# ---------------------------------------------------------------------------

class _ONNXBackend:
    def __init__(self, model_path: Path):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 2
        self.session = ort.InferenceSession(
            str(model_path), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        logger.info(f"[Engine] ONNX backend loaded: {model_path.name}")

    def predict(self, image: Image.Image, **kwargs) -> np.ndarray:
        arr = preprocess_image(image)
        outputs = self.session.run(None, {self.input_name: arr})
        logits = outputs[0][0]
        exp = np.exp(logits - logits.max())
        return exp / exp.sum()


class _TFLiteBackend:
    def __init__(self, model_path: Path):
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            import tensorflow as tf
            Interpreter = tf.lite.Interpreter

        self.interpreter = Interpreter(model_path=str(model_path))
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        logger.info(f"[Engine] TFLite backend loaded: {model_path.name}")

    def predict(self, image: Image.Image, **kwargs) -> np.ndarray:
        input_detail = self.input_details[0]
        if input_detail["dtype"] == np.int8:
            scale = input_detail["quantization_parameters"]["scales"][0]
            zp = input_detail["quantization_parameters"]["zero_points"][0]
            arr = preprocess_image_int8(image, scale, zp)
        else:
            arr = preprocess_image(image)

        self.interpreter.set_tensor(input_detail["index"], arr)
        self.interpreter.invoke()

        output = self.interpreter.get_tensor(self.output_details[0]["index"])
        logits = output[0].astype(np.float32)

        if self.output_details[0]["dtype"] == np.int8:
            out_scale = self.output_details[0]["quantization_parameters"]["scales"][0]
            out_zp = self.output_details[0]["quantization_parameters"]["zero_points"][0]
            logits = (logits - out_zp) * out_scale

        exp = np.exp(logits - logits.max())
        return exp / exp.sum()


class _MockBackend:
    def __init__(self):
        logger.warning("[Engine] No model weights found. Running in MOCK MODE.")

    def predict(self, image: Image.Image, region: str = "", color: str = "") -> np.ndarray:
        arr = np.array(image.convert("RGB").resize((32, 32)))
        seed = int(arr.mean() * 1000 + arr.std() * 100) % (2**31)
        rng = np.random.default_rng(seed)
        raw = rng.exponential(scale=0.3, size=NUM_CLASSES)
        
        region_low = region.lower()
        color_low = color.lower()
        
        # Determine forced breed based on rules
        forced_breed = None
        conf_min, conf_max = 2.5, 5.0
        
        if "gujarat" in region_low or "brown" in color_low or "red" in color_low:
            forced_breed = "Gir"
            conf_min, conf_max = 5.0, 7.5 # Maps to roughly 88-94%
        elif "punjab" in region_low or "haryana" in region_low:
            forced_breed = rng.choice(["Sahiwal", "Murrah"])
            conf_min, conf_max = 4.5, 7.0 # Maps to roughly 86-93%
        elif "maharashtra" in region_low or "karnataka" in region_low:
            forced_breed = rng.choice(["Khillari", "Deoni"])
            conf_min, conf_max = 4.2, 6.5 # Maps to roughly 85-91%
        elif "tamil nadu" in region_low:
            forced_breed = "Kangayam"
            conf_min, conf_max = 5.2, 8.0 # Maps to roughly 89-95%
            
        top_idx = None
        if forced_breed:
            # Find index of forced breed
            for idx, name in BREED_MAP.items():
                if name == forced_breed:
                    top_idx = idx
                    break
                    
        if top_idx is None:
            top_idx = int(rng.integers(0, NUM_CLASSES))
            
        raw[top_idx] += rng.uniform(conf_min, conf_max)
        exp = np.exp(raw - raw.max())
        return exp / exp.sum()


def _build_backend():
    for path in _ONNX_CANDIDATES:
        if path.exists():
            try: return _ONNXBackend(path), "onnx"
            except Exception as exc: logger.warning(f"[Engine] ONNX load failed: {exc}")

    for path in _TFLITE_CANDIDATES:
        if path.exists():
            try: return _TFLiteBackend(path), "tflite"
            except Exception as exc: logger.warning(f"[Engine] TFLite load failed: {exc}")

    return _MockBackend(), "mock"


_backend, BACKEND_TYPE = _build_backend()


# ---------------------------------------------------------------------------
# Public inference API
# ---------------------------------------------------------------------------

def run_inference(
    image: Image.Image,
    region: str = "",
    age: str = "",
    color: str = "",
    xai_output_dir: Path = None
) -> Dict:
    """
    Run multimodal breed inference on a PIL Image with XAI generation.
    """
    t0 = time.perf_counter()

    # 1. Base Image Inference
    probabilities = _backend.predict(image, region=region, color=color)
    
    # 2. Multimodal Metadata Fusion (Heuristic)
    # If the user specified a region, we boost breeds native to that region.
    # In a real app, this would use the breed_encyclopedia table. 
    # For speed/isolation here, we do a quick heuristic mock boost.
    if region:
        region_lower = region.lower()
        for idx, breed_name in BREED_MAP.items():
            b_lower = breed_name.lower()
            # Simple heuristic: if region name is somewhat related (e.g., Gujarat -> Gir/Kankrej)
            if ("gujarat" in region_lower and b_lower in ["gir", "kankrej"]) or \
               ("punjab" in region_lower and b_lower in ["sahiwal", "murrah"]) or \
               ("kerala" in region_lower and b_lower in ["vechur", "kasargod"]):
                # Boost probability significantly
                probabilities[idx] *= 1.5 
        # Re-normalize
        probabilities /= probabilities.sum()

    # 3. Extract Top-3
    top3_idx = np.argsort(probabilities)[::-1][:3]
    top3: List[Dict] = [
        {
            "breed": BREED_MAP.get(int(idx), f"Unknown_{idx}"),
            "confidence": float(round(float(probabilities[idx]), 4)),
        }
        for idx in top3_idx
    ]

    top1_breed = top3[0]["breed"]
    top1_confidence = top3[0]["confidence"]

    # 4. Generate XAI Grad-CAM if requested
    xai_image_filename = ""
    if xai_output_dir and xai_output_dir.exists():
        xai_image_filename = generate_mock_gradcam(image, xai_output_dir)

    # 5. Generate Veterinary Estimations
    vet_data = generate_vet_estimates(top1_breed, age)

    # 6. Dynamic Expert Threshold
    threshold = EXPERT_THRESHOLD
    if top1_breed in _RARE_BREEDS:
        threshold = max(threshold, 0.75)

    inference_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "top1_breed": top1_breed,
        "top1_confidence": top1_confidence,
        "top3": top3,
        "needs_expert": bool(top1_confidence < threshold),
        "backend": BACKEND_TYPE,
        "inference_ms": inference_ms,
        "xai_image_filename": xai_image_filename,
        "vet_data": vet_data
    }


def get_engine_status() -> Dict:
    return {
        "backend": BACKEND_TYPE,
        "mock_mode": BACKEND_TYPE == "mock",
        "num_breeds": NUM_CLASSES,
        "input_size": INPUT_SIZE,
        "expert_threshold": EXPERT_THRESHOLD,
        "models_dir": str(_MODELS_DIR),
    }
