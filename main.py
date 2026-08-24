"""
main.py — ระบบอ่านเลขมิเตอร์น้ำอัตโนมัติ (Automated Water Meter Reader v1.1)
Functional Pipeline ล้วน (ไม่มี OOP) — กระชับ อ่านจากบนลงล่างได้ทันที (230-240 บรรทัด)
รัน API: python main.py → http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import io
from time import perf_counter
from typing import Any

import cv2
import numpy as np
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from starlette.concurrency import run_in_threadpool
import uvicorn

# ================================================================
# 1) Config Constants — แหล่งรวมค่าคงที่ทั้งหมด
# ================================================================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
YOLO_MODEL, YOLO_IMGSZ, YOLO_CONF, CONF_RELIABLE = "weights/MeterOCR.pt", 960, 0.35, 0.60
EXPECTED_MIN_DIGITS, EXPECTED_MAX_DIGITS = 4, 9
ROTATION_ANGLES, PREP_LIST = (0, 90, 180, 270), ("orig", "clahe", "histeq")
CLAHE_CLIP, CLAHE_GRID = 2.0, (8, 8)
ORIENT_MARGIN, FLIP_GUARD_CONF = 0.12, 0.60
FLIP_MAP = {0: 0, 1: 1, 2: 5, 5: 2, 6: 9, 8: 8, 9: 6}
ALIGN_MAX_SPREAD, VERTICAL_MAX_X, VERTICAL_MIN_Y = 0.10, 0.02, 0.03
RED_THRESH, RED_DOMINANCE, MIN_CROP_PX = 0.08, 2.0, 4
SIGLIP_MODEL = "google/siglip2-base-patch16-224"
METER_LABELS = ("water meter", "electricity meter", "gas meter", "not a meter")
METER_VERIFY_CONF = 0.50

# ================================================================
# 2) Model Lazy Loaders
# ================================================================
_yolo, _siglip = None, None

def get_yolo() -> Any:
    global _yolo
    if _yolo is None:
        from ultralytics import YOLO
        _yolo = YOLO(YOLO_MODEL)
        _yolo.predict(np.zeros((640, 640, 3), dtype=np.uint8), verbose=False)
    return _yolo

def get_siglip() -> tuple[Any, Any]:
    global _siglip
    if _siglip is None:
        from transformers import AutoModel, AutoProcessor
        _siglip = (AutoProcessor.from_pretrained(SIGLIP_MODEL), AutoModel.from_pretrained(SIGLIP_MODEL).to(DEVICE).eval())
    return _siglip

# ================================================================
# 3) Image Processing Functions
# ================================================================
def rotate_image(img_bgr: np.ndarray, angle: int) -> np.ndarray:
    rot_map = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    return cv2.rotate(img_bgr, rot_map[angle]) if angle in rot_map else img_bgr

def apply_prep(img_bgr: np.ndarray, prep: str) -> np.ndarray:
    if prep == "clahe":
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = cv2.createCLAHE(CLAHE_CLIP, CLAHE_GRID).apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    if prep == "histeq":
        ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
        return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    return img_bgr

def iou(b1: list[float], b2: list[float]) -> float:
    inter = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0])) * max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
    union = (b1[2] - b1[0]) * (b1[3] - b1[1]) + (b2[2] - b2[0]) * (b2[3] - b2[1]) - inter
    return inter / union if union > 0 else 0.0

def dedup_detections(dets: list[dict[str, Any]], thresh: float = 0.45) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for d in sorted(dets, key=lambda x: x["confidence"], reverse=True):
        if not any(iou(d["bbox"], k["bbox"]) > thresh for k in kept):
            kept.append(d)
    return sorted(kept, key=lambda x: x["center_x"])

def remap_bbox(bbox: list[float], angle: int, w: int, h: int) -> list[float]:
    x1, y1, x2, y2 = bbox
    remap = {0: bbox, 90: [y1, h - x2, y2, h - x1], 180: [w - x2, h - y2, w - x1, h - y1], 270: [w - y2, x1, w - y1, x2]}
    return remap.get(angle, bbox)

def red_ratio(img_bgr: np.ndarray, bbox: list[float]) -> float:
    x1, y1, x2, y2 = [int(v) for v in bbox]
    px, py = max(1, int((x2 - x1) * 0.15)), max(1, int((y2 - y1) * 0.15))
    crop = img_bgr[max(0, y1 + py):min(img_bgr.shape[0], y2 - py), max(0, x1 + px):min(img_bgr.shape[1], x2 - px)]
    if crop.size == 0: return 0.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 0] <= 12) | (hsv[:, :, 0] >= 165)) & (hsv[:, :, 1] >= 40) & (hsv[:, :, 2] >= 40)
    return float(np.mean(mask))

# ================================================================
# 4) Digit Detection & Orientation Evaluation
# ================================================================
def detect_digits(img_bgr: np.ndarray) -> list[dict[str, Any]]:
    res = get_yolo().predict(img_bgr, imgsz=YOLO_IMGSZ, conf=YOLO_CONF, device=DEVICE, verbose=False)
    return sorted([{
        "digit": int(b.cls[0].item()), "confidence": float(b.conf[0].item()),
        "bbox": b.xyxy[0].tolist(), "center_x": (b.xyxy[0][0].item() + b.xyxy[0][2].item()) / 2.0,
    } for b in res[0].boxes], key=lambda d: d["center_x"])

def is_vertical(dets: list[dict[str, Any]], w: int, h: int) -> dict[str, Any]:
    if len(dets) < 2: return {"vertical": False, "x_spread": 0.0, "y_spread": 0.0}
    xs = float(np.std([((d["bbox"][0] + d["bbox"][2]) / 2) / w for d in dets]))
    ys = float(np.std([((d["bbox"][1] + d["bbox"][3]) / 2) / h for d in dets]))
    is_vert = (ys >= xs * 0.8) or (xs <= VERTICAL_MAX_X and ys >= VERTICAL_MIN_Y)
    return {"vertical": is_vert, "x_spread": round(xs, 4), "y_spread": round(ys, 4)}

def eval_orientation(bgr_img: np.ndarray, angle: int, prep: str) -> tuple[float, list[dict[str, Any]], float, str, dict[str, Any]]:
    rot = rotate_image(bgr_img, angle)
    proc = apply_prep(rot, prep)
    dets = dedup_detections(detect_digits(proc))
    rh, rw = rot.shape[:2]
    vert = is_vertical(dets, rw, rh)
    n = len(dets)
    if not dets or vert["vertical"] or not (EXPECTED_MIN_DIGITS <= n <= EXPECTED_MAX_DIGITS):
        return 0.0, dets, 0.0, prep, vert
    mean = float(np.mean([d["confidence"] for d in dets]))
    score = mean * n
    r_first, r_last = red_ratio(proc, dets[0]["bbox"]), red_ratio(proc, dets[-1]["bbox"])
    if r_first > RED_THRESH and r_first > r_last * RED_DOMINANCE: score *= 0.5
    elif r_last > RED_THRESH and r_last > r_first * RED_DOMINANCE: score *= 1.05
    return score, dets, mean, prep, vert

def detect_digits_best(rgb_img: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    h, w = rgb_img.shape[:2]
    bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
    candidates = {a: max([eval_orientation(bgr, a, p) for p in PREP_LIST], key=lambda x: x[0]) for a in ROTATION_ANGLES}
    s0, d0, m0, p0, v0 = candidates[0]
    best_a, (best_s, best_d, best_m, best_p, best_v) = max(candidates.items(), key=lambda x: x[1][0])
    margin = bool(best_a != 0 and d0 and not v0["vertical"] and (best_s - s0 < ORIENT_MARGIN))
    if margin: best_a, best_d, best_m, best_p = 0, d0, m0, p0
    meta = {"angle": best_a, "clahe": best_p == "clahe", "prep": best_p} if best_d else None
    if meta:
        for d in best_d:
            d["bbox"] = remap_bbox(d["bbox"], best_a, w, h)
            d["center_x"] = (d["bbox"][0] + d["bbox"][2]) / 2.0
    return best_d, meta, margin

# ================================================================
# 5) Verification & Safety Guards
# ================================================================
@torch.inference_mode()
def check_water_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    proc, model = get_siglip()
    inp = proc(text=list(METER_LABELS), images=Image.fromarray(rgb_img), padding="max_length", return_tensors="pt").to(DEVICE)
    probs = torch.softmax(model(**inp).logits_per_image, dim=1)[0].cpu().numpy()
    pred = METER_LABELS[int(np.argmax(probs))]
    return {"verified": pred == "water meter" and float(probs[0]) >= METER_VERIFY_CONF, "predicted_class": pred, "confidence": float(probs[0]), "probabilities": dict(zip(METER_LABELS, probs.astype(float)))}

def flip_guard(rgb_img: np.ndarray, digits: list[dict[str, Any]], meta: dict[str, Any] | None, h: int, w: int) -> dict[str, Any]:
    if not digits or not meta:
        return {"consistent": True, "anti_reading": "", "anti_digits": [], "anti_confidence": 0.0, "warned": False, "anti_angle": None}
    anti_a = (meta["angle"] + 180) % 360
    anti_dets = dedup_detections(detect_digits(apply_prep(rotate_image(cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR), anti_a), meta["prep"])))
    if not anti_dets:
        return {"consistent": True, "anti_reading": "", "anti_digits": [], "anti_confidence": 0.0, "warned": False, "anti_angle": anti_a}
    anti_reading, mean_conf = "".join(str(d["digit"]) for d in anti_dets), float(np.mean([d["confidence"] for d in anti_dets]))
    consistent = len(anti_dets) == len(digits) and all(FLIP_MAP.get(digits[-1-j]["digit"]) == a["digit"] for j, a in enumerate(anti_dets) if digits[-1-j]["digit"] in FLIP_MAP)
    return {"consistent": consistent, "anti_reading": anti_reading, "anti_confidence": round(mean_conf, 4), "warned": bool(mean_conf >= FLIP_GUARD_CONF and not consistent), "anti_angle": anti_a}

@torch.inference_mode()
def cross_check_digits(rgb_img: np.ndarray, digits: list[dict[str, Any]], h: int, w: int, angle: int = 0) -> dict[str, Any]:
    low_conf = [d for d in digits if d["confidence"] < CONF_RELIABLE]
    if not low_conf: return {"enabled": True, "checked": 0, "mismatches": []}
    proc, model = get_siglip()
    labels, mismatches = [str(i) for i in range(10)], []
    for d in low_conf:
        x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
        crop = rgb_img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if crop.shape[0] < MIN_CROP_PX or crop.shape[1] < MIN_CROP_PX: continue
        if angle: crop = cv2.cvtColor(rotate_image(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), angle), cv2.COLOR_BGR2RGB)
        inp = proc(text=labels, images=Image.fromarray(crop), padding="max_length", return_tensors="pt").to(DEVICE)
        probs = torch.softmax(model(**inp).logits_per_image, dim=1)[0].cpu().numpy()
        pred = int(np.argmax(probs))
        if pred != d["digit"]:
            mismatches.append({"position": d["position"], "yolo_digit": d["digit"], "siglip_digit": pred, "siglip_confidence": float(probs[pred])})
    return {"enabled": True, "checked": len(low_conf), "mismatches": mismatches}

# ================================================================
# 6) Pipeline Response Factory & Main Entry
# ================================================================
def _build_result(reading: str, digits: list, mean_conf: float, meter: dict, meta: dict | None, margin: bool, warns: list[str], t0: float, w: int, h: int, flip=None, align=None, cross=None) -> dict[str, Any]:
    return {
        "reading": reading, "digits": digits, "digit_count": len(digits), "mean_confidence": mean_conf,
        "meter_check": meter, "processing": {"best": meta, "margin_applied": margin, "auto_corrected": False},
        "flip_check": flip or {}, "alignment": align or {}, "cross_check": cross or {},
        "warnings": warns, "elapsed_ms": (perf_counter() - t0) * 1000, "image_size": [w, h],
    }

def read_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    t0, (h, w) = perf_counter(), rgb_img.shape[:2]
    meter = check_water_meter(rgb_img)
    if not meter["verified"]:
        return _build_result("", [], 0.0, meter, None, False, [f"ภาพนี้ไม่ใช่มิเตอร์น้ำ ({meter['predicted_class']})"], t0, w, h)
    dets, meta, margin = detect_digits_best(rgb_img)
    if not dets:
        return _build_result("", [], 0.0, meter, meta, margin, ["ตรวจไม่พบตัวเลข"], t0, w, h)
    digits = [{"position": i, "digit": d["digit"], "confidence": d["confidence"], "bbox": d["bbox"], "reliable": d["confidence"] >= CONF_RELIABLE} for i, d in enumerate(dets, 1)]
    mean_conf = float(np.mean([d["confidence"] for d in digits]))
    if meta and meta["angle"] == 0 and is_vertical(digits, w, h)["vertical"]:
        return _build_result("", [], 0.0, meter, meta, margin, ["กล่องเรียงแนวตั้ง — ไม่ใช่ค่ามิเตอร์"], t0, w, h)
    flip = flip_guard(rgb_img, digits, meta, h, w)
    align_spread = float(np.std([((d['bbox'][0]+d['bbox'][2])/2)/w if meta and meta['angle'] in (90,270) else ((d['bbox'][1]+d['bbox'][3])/2)/h for d in digits]))
    align = {"ok": align_spread <= ALIGN_MAX_SPREAD, "y_spread": round(align_spread, 4)}
    cross = cross_check_digits(rgb_img, digits, h, w, meta["angle"] if meta else 0)
    warns = [msg for cond, msg in [
        (not (EXPECTED_MIN_DIGITS <= len(digits) <= EXPECTED_MAX_DIGITS), f"จำนวนหลัก {len(digits)} นอกช่วง {EXPECTED_MIN_DIGITS}-{EXPECTED_MAX_DIGITS}"),
        (digits[0]["digit"] == 0, "หลักแรกเป็น 0 — อาจเกินมา 1 หลัก"),
        (mean_conf < CONF_RELIABLE, f"mean conf ต่ำ {mean_conf:.2f} — ภาพอาจเบลอ/เอียง"),
        (flip["warned"], f"อาจกลับหัว! หมุน 180° ได้ {flip['anti_reading']} ({flip['anti_confidence']:.2f}) — ตรวจภาพก่อนบันทึก"),
        (not align["ok"], f"กล่องไม่เรียงแนว y_spread={align['y_spread']:.3f} — อาจเป็นป้าย/วันที่"),
    ] if cond]
    warns += [f"หลักที่ {d['position']} ({d['digit']}) conf ต่ำ {d['confidence']:.2f} — ควรตรวจด้วยตา" for d in digits if not d["reliable"]]
    warns += [f"หลักที่ {m['position']}: YOLO {m['yolo_digit']} vs SigLIP {m['siglip_digit']} ({m['siglip_confidence']:.2f})" for m in cross["mismatches"]]
    return _build_result("".join(str(d["digit"]) for d in digits), digits, mean_conf, meter, meta, margin, warns, t0, w, h, flip, align, cross)

# ================================================================
# 7) FastAPI Application
# ================================================================
app = FastAPI(title="Meter Reader API", version="1.1", description="API อ่านเลขมิเตอร์น้ำอัตโนมัติ (Functional Pipeline)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "device": DEVICE, "yolo_loaded": _yolo is not None, "siglip_loaded": _siglip is not None}

@app.post("/api/read-meter")
async def read_meter_endpoint(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.content_type not in ALLOWED_TYPES: raise HTTPException(status_code=415, detail="ชนิดไฟล์ไม่รองรับ")
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)); img.load(); arr = np.asarray(img.convert("RGB"))
    except Exception: raise HTTPException(status_code=422, detail="อ่านไฟล์ภาพไม่ได้")
    return await run_in_threadpool(read_meter, arr)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
