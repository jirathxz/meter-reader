"""
main.py — ระบบอ่านเลขมิเตอร์น้ำอัตโนมัติ (Automated Water Meter Reader v1.1)
Functional Pipeline ล้วน — ออกแบบให้อ่านและทำความเข้าใจตามได้ง่ายที่สุด (Intuitive & Clean)
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
# 1) ค่าคงที่ (Constants)
# ================================================================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# โมเดล YOLO และการตรวจจับตัวเลข
YOLO_MODEL = "weights/MeterOCR.pt"
YOLO_IMGSZ = 960
YOLO_CONF = 0.35
CONF_RELIABLE = 0.60
EXPECTED_MIN_DIGITS = 4
EXPECTED_MAX_DIGITS = 9

# รูปแบบการค้นหามุมและปรับภาพ
ROTATION_ANGLES = (0, 90, 180, 270)
PREP_LIST = ("orig", "clahe", "histeq")
CLAHE_CLIP = 2.0
CLAHE_GRID = (8, 8)

# ตัวช่วยความปลอดภัย (Safety Guards)
ORIENT_MARGIN = 0.12
FLIP_GUARD_CONF = 0.60
FLIP_MAP = {0: 0, 1: 1, 2: 5, 5: 2, 6: 9, 8: 8, 9: 6}
ALIGN_MAX_SPREAD = 0.10
RED_THRESH = 0.08
RED_DOMINANCE = 2.0
MIN_CROP_PX = 4

# โมเดล SigLIP2 สำหรับคัดแยกประเภทมิเตอร์
SIGLIP_MODEL = "google/siglip2-base-patch16-224"
METER_LABELS = ("water meter", "electricity meter", "gas meter", "not a meter")
METER_VERIFY_CONF = 0.50

# ================================================================
# 2) โหลดโมเดล (Lazy Loaders)
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
# 3) ฟังก์ชันจัดการภาพและพิกัดเรขาคณิต (Image & Geometry Utils)
# ================================================================
def rotate_image(img_bgr: np.ndarray, angle: int) -> np.ndarray:
    """หมุนภาพตามองศา 90, 180, 270 (0 = คงเดิม)"""
    if angle == 90: return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180: return cv2.rotate(img_bgr, cv2.ROTATE_180)
    if angle == 270: return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img_bgr

def apply_prep(img_bgr: np.ndarray, prep: str) -> np.ndarray:
    """ปรับคอนทราสต์ภาพ: CLAHE หรือ HistEq"""
    if prep == "clahe":
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_clahe = cv2.createCLAHE(CLAHE_CLIP, CLAHE_GRID).apply(l)
        return cv2.cvtColor(cv2.merge([l_clahe, a, b]), cv2.COLOR_LAB2BGR)
    if prep == "histeq":
        ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        y_eq = cv2.equalizeHist(y)
        return cv2.cvtColor(cv2.merge([y_eq, cr, cb]), cv2.COLOR_YCrCb2BGR)
    return img_bgr

def remap_point(x: float, y: float, angle: int, w: int, h: int) -> tuple[float, float]:
    """แปลงจุด (x, y) จากภาพที่หมุนแล้ว กลับสู่พิกัดภาพเดิมแบบทีละจุด"""
    if angle == 90:  return y, h - x      # หมุนขวา 90° -> ย้อนกลับ x=y, y=h-x
    if angle == 180: return w - x, h - y  # กลับหัว 180° -> ย้อนกลับ x=w-x, y=h-y
    if angle == 270: return w - y, x      # หมุนซ้าย 90° -> ย้อนกลับ x=w-y, y=x
    return x, y

def remap_bbox(bbox: list[float], angle: int, w: int, h: int) -> list[float]:
    """แปลงกล่อง [x1, y1, x2, y2] จากภาพที่หมุนแล้ว กลับเป็นพิกัดภาพเดิม"""
    x1, y1, x2, y2 = bbox
    p1_x, p1_y = remap_point(x1, y1, angle, w, h)
    p2_x, p2_y = remap_point(x2, y2, angle, w, h)
    return [min(p1_x, p2_x), min(p1_y, p2_y), max(p1_x, p2_x), max(p1_y, p2_y)]

def iou(box1: list[float], box2: list[float]) -> float:
    """คำนวณพื้นที่ทับซ้อน (IoU) ระหว่าง 2 กล่อง"""
    x1, y1 = max(box1[0], box2[0]), max(box1[1], box2[1])
    x2, y2 = min(box1[2], box2[2]), min(box1[3], box2[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    return (intersection / union) if union > 0 else 0.0

def dedup_detections(dets: list[dict[str, Any]], thresh: float = 0.45) -> list[dict[str, Any]]:
    """ตัดกล่องที่ซ้อนทับกันออก เหลือเฉพาะกล่องที่มั่นใจสูงสุด"""
    kept: list[dict[str, Any]] = []
    for d in sorted(dets, key=lambda x: x["confidence"], reverse=True):
        if not any(iou(d["bbox"], k["bbox"]) > thresh for k in kept):
            kept.append(d)
    return sorted(kept, key=lambda x: x["center_x"])

def red_ratio(img_bgr: np.ndarray, bbox: list[float]) -> float:
    """คำนวณสัดส่วนพิกเซลสีแดงภายในกล่องตัวเลข (หลักทศนิยม)"""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    pad_x, pad_y = max(1, int((x2 - x1) * 0.15)), max(1, int((y2 - y1) * 0.15))
    crop = img_bgr[max(0, y1 + pad_y):min(img_bgr.shape[0], y2 - pad_y), max(0, x1 + pad_x):min(img_bgr.shape[1], x2 - pad_x)]
    if crop.size == 0: return 0.0
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, (0, 40, 40), (12, 255, 255))
    mask2 = cv2.inRange(hsv, (165, 40, 40), (180, 255, 255))
    return float(np.mean((mask1 | mask2) > 0))

# ================================================================
# 4) ตรวจจับตัวเลขและประเมินทิศทาง (Detection & Search)
# ================================================================
def detect_digits(img_bgr: np.ndarray) -> list[dict[str, Any]]:
    """YOLO หาตัวเลข 0-9 เรียงจากซ้ายไปขวา"""
    res = get_yolo().predict(img_bgr, imgsz=YOLO_IMGSZ, conf=YOLO_CONF, device=DEVICE, verbose=False)
    boxes = []
    for b in res[0].boxes:
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        boxes.append({
            "digit": int(b.cls[0].item()), "confidence": float(b.conf[0].item()),
            "bbox": [x1, y1, x2, y2], "center_x": (x1 + x2) / 2.0, "center_y": (y1 + y2) / 2.0,
        })
    return sorted(boxes, key=lambda d: d["center_x"])

def is_vertical(dets: list[dict[str, Any]], img_w: int, img_h: int) -> dict[str, Any]:
    """ตรวจว่ากล่องเรียงเป็นแนวตั้งหรือไม่ (แถวมิเตอร์แนวนอน ความกว้าง width_span ต้องมากกว่า height_span)"""
    if len(dets) < 2: return {"vertical": False}
    xs = [d["center_x"] / img_w for d in dets]
    ys = [d["center_y"] / img_h for d in dets]
    width_span = max(xs) - min(xs)   # ความกว้างของแถวตัวเลข
    height_span = max(ys) - min(ys)  # ความสูงของแถวตัวเลข
    # ถ้าความสูงมากกว่าหรือใกล้เคียงความกว้าง แสดงว่าเป็นคอลัมน์แนวดิ่ง (เช่น วันที่/รุ่น)
    is_vert = (height_span >= width_span * 0.8) or (width_span <= 0.05 and height_span >= 0.08)
    return {"vertical": is_vert}

def eval_orientation(bgr_img: np.ndarray, angle: int, prep: str) -> dict[str, Any]:
    """ประเมินผลลัพธ์ของ 1 มุม × 1 ฟิลเตอร์"""
    rot = rotate_image(bgr_img, angle)
    proc = apply_prep(rot, prep)
    dets = dedup_detections(detect_digits(proc))
    rh, rw = rot.shape[:2]
    vert = is_vertical(dets, rw, rh)
    n = len(dets)

    if not dets or vert["vertical"] or not (EXPECTED_MIN_DIGITS <= n <= EXPECTED_MAX_DIGITS):
        return {"score": 0.0, "dets": dets, "prep": prep, "vert": vert}

    mean_conf = float(np.mean([d["confidence"] for d in dets]))
    score = mean_conf * n

    # หลักทศนิยมสีแดงต้องอยู่ขวาสุดเสมอ
    r_first = red_ratio(proc, dets[0]["bbox"])
    r_last = red_ratio(proc, dets[-1]["bbox"])
    if r_first > RED_THRESH and r_first > r_last * RED_DOMINANCE:
        score *= 0.5   # แดงอยู่ซ้าย -> น่าจะกลับหัว
    elif r_last > RED_THRESH and r_last > r_first * RED_DOMINANCE:
        score *= 1.05  # แดงอยู่ขวา -> ทิศทางถูกต้อง

    return {"score": score, "dets": dets, "prep": prep, "vert": vert}

def detect_digits_best(rgb_img: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """ทดลอง 4 ทิศ × 3 ฟิลเตอร์ แล้วเลือกชุดที่ได้คะแนนรวมสูงสุด"""
    h, w = rgb_img.shape[:2]
    bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)

    candidates = {}
    for angle in ROTATION_ANGLES:
        best_in_angle = max([eval_orientation(bgr, angle, prep) for prep in PREP_LIST], key=lambda c: c["score"])
        candidates[angle] = best_in_angle

    cand0 = candidates[0]
    best_angle, best_cand = max(candidates.items(), key=lambda item: item[1]["score"])

    # Margin Rule: มุมอื่นต้องชนะมุม 0° เกินกำหนด จึงยอมสลับมุม (กันพลิกฉิวเฉียด)
    if best_angle != 0 and cand0["dets"] and not cand0["vert"]["vertical"] and (best_cand["score"] - cand0["score"] < ORIENT_MARGIN):
        best_angle, best_cand = 0, cand0

    best_dets = best_cand["dets"]
    best_meta = {"angle": best_angle, "prep": best_cand["prep"], "clahe": best_cand["prep"] == "clahe"} if best_dets else None

    if best_meta:
        for d in best_dets:
            d["bbox"] = remap_bbox(d["bbox"], best_angle, w, h)
            d["center_x"] = (d["bbox"][0] + d["bbox"][2]) / 2.0
            d["center_y"] = (d["bbox"][1] + d["bbox"][3]) / 2.0

    return best_dets, best_meta

# ================================================================
# 5) ตรวจสอบความถูกต้องและป้องกันข้อผิดพลาด (Safety Guards)
# ================================================================
@torch.inference_mode()
def check_water_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    """SigLIP2 Zero-shot ตรวจสอบว่าเป็นภาพมิเตอร์น้ำจริง"""
    proc, model = get_siglip()
    inp = proc(text=list(METER_LABELS), images=Image.fromarray(rgb_img), padding="max_length", return_tensors="pt").to(DEVICE)
    probs = torch.softmax(model(**inp).logits_per_image, dim=1)[0].cpu().numpy()
    pred = METER_LABELS[int(np.argmax(probs))]
    return {
        "verified": pred == "water meter" and float(probs[0]) >= METER_VERIFY_CONF,
        "predicted_class": pred, "confidence": float(probs[0]),
    }

def flip_guard(rgb_img: np.ndarray, digits: list[dict[str, Any]], meta: dict[str, Any] | None) -> dict[str, Any]:
    """ตรวจสอบความสมมาตร 180° ป้องกันอ่านกลับหัว (Mirror Check เช่น 6<->9, 2<->5)"""
    if not digits or not meta:
        return {"warned": False, "anti_reading": "", "anti_confidence": 0.0}

    anti_angle = (meta["angle"] + 180) % 360
    rot_bgr = rotate_image(cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR), anti_angle)
    anti_dets = dedup_detections(detect_digits(apply_prep(rot_bgr, meta["prep"])))
    if not anti_dets:
        return {"warned": False, "anti_reading": "", "anti_confidence": 0.0}

    anti_reading = "".join(str(d["digit"]) for d in anti_dets)
    mean_conf = float(np.mean([d["confidence"] for d in anti_dets]))

    # เปรียบเทียบเลขหัว-ท้ายแบบกระจกสะท้อนกับตาราง FLIP_MAP
    digits_rev = [d["digit"] for d in reversed(digits)]
    anti_vals = [d["digit"] for d in anti_dets]
    consistent = len(anti_vals) == len(digits_rev) and all(
        FLIP_MAP.get(orig) == anti for orig, anti in zip(digits_rev, anti_vals) if orig in FLIP_MAP
    )

    return {
        "warned": bool(mean_conf >= FLIP_GUARD_CONF and not consistent),
        "anti_reading": anti_reading, "anti_confidence": round(mean_conf, 4),
    }

@torch.inference_mode()
def cross_check_digits(rgb_img: np.ndarray, digits: list[dict[str, Any]], h: int, w: int, angle: int = 0) -> list[dict[str, Any]]:
    """SigLIP2 Cross-check ตรวจทานเฉพาะหลักที่ YOLO มั่นใจต่ำ (< 0.60)"""
    low_conf = [d for d in digits if d["confidence"] < CONF_RELIABLE]
    if not low_conf: return []

    proc, model = get_siglip()
    labels, mismatches = [str(i) for i in range(10)], []

    for d in low_conf:
        x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
        crop = rgb_img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if crop.shape[0] < MIN_CROP_PX or crop.shape[1] < MIN_CROP_PX: continue
        if angle != 0:
            crop = cv2.cvtColor(rotate_image(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), angle), cv2.COLOR_BGR2RGB)

        inp = proc(text=labels, images=Image.fromarray(crop), padding="max_length", return_tensors="pt").to(DEVICE)
        probs = torch.softmax(model(**inp).logits_per_image, dim=1)[0].cpu().numpy()
        pred = int(np.argmax(probs))

        if pred != d["digit"]:
            mismatches.append({"position": d["position"], "yolo_digit": d["digit"], "siglip_digit": pred, "siglip_confidence": float(probs[pred])})

    return mismatches

# ================================================================
# 6) ฟังก์ชันอ่านมิเตอร์หลัก (Main Pipeline)
# ================================================================
def read_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    """รับภาพ RGB -> ตรวจชนิดมิเตอร์ -> หาตัวเลข -> ตรวจความถูกต้อง -> คืนผลลัพธ์"""
    t0, (h, w) = perf_counter(), rgb_img.shape[:2]

    # 1. ตรวจสอบว่าใช่มิเตอร์น้ำจริงไหม
    meter = check_water_meter(rgb_img)
    if not meter["verified"]:
        return {"reading": "", "digits": [], "meter_check": meter, "processing": None, "warnings": [f"ภาพนี้ไม่ใช่มิเตอร์น้ำ ({meter['predicted_class']})"], "elapsed_ms": round((perf_counter() - t0) * 1000, 1)}

    # 2. ค้นหาตัวเลขและมุมที่ดีที่สุด
    dets, meta = detect_digits_best(rgb_img)
    if not dets:
        return {"reading": "", "digits": [], "meter_check": meter, "processing": meta, "warnings": ["ตรวจไม่พบตัวเลข"], "elapsed_ms": round((perf_counter() - t0) * 1000, 1)}

    digits = [{
        "position": i, "digit": d["digit"], "confidence": round(d["confidence"], 4),
        "bbox": d["bbox"], "reliable": d["confidence"] >= CONF_RELIABLE,
    } for i, d in enumerate(dets, 1)]
    mean_conf = float(np.mean([d["confidence"] for d in digits]))

    # 3. ตรวจสอบว่าไม่ใช่คอลัมน์แนวตั้ง (เช่น วันที่)
    if meta and meta["angle"] == 0 and is_vertical(dets, w, h)["vertical"]:
        return {"reading": "", "digits": [], "meter_check": meter, "processing": meta, "warnings": ["กล่องเรียงแนวตั้ง — ไม่ใช่ค่ามิเตอร์"], "elapsed_ms": round((perf_counter() - t0) * 1000, 1)}

    # 4. ตรวจสอบความถูกต้องและสร้างคำเตือน
    flip = flip_guard(rgb_img, digits, meta)
    align_vals = [(d["bbox"][0] + d["bbox"][2]) / (2 * w) if meta and meta["angle"] in (90, 270) else (d["bbox"][1] + d["bbox"][3]) / (2 * h) for d in digits]
    align_ok = float(np.std(align_vals)) <= ALIGN_MAX_SPREAD
    mismatches = cross_check_digits(rgb_img, digits, h, w, meta["angle"] if meta else 0)

    warns = [msg for cond, msg in [
        (not (EXPECTED_MIN_DIGITS <= len(digits) <= EXPECTED_MAX_DIGITS), f"จำนวนหลัก {len(digits)} นอกช่วง {EXPECTED_MIN_DIGITS}-{EXPECTED_MAX_DIGITS}"),
        (digits[0]["digit"] == 0, "หลักแรกเป็น 0 — อาจเกินมา 1 หลัก"),
        (mean_conf < CONF_RELIABLE, f"mean conf ต่ำ {mean_conf:.2f} — ภาพอาจเบลอ/เอียง"),
        (flip["warned"], f"อาจกลับหัว! หมุน 180° ได้ {flip['anti_reading']} ({flip['anti_confidence']:.2f}) — ตรวจภาพก่อนบันทึก"),
        (not align_ok, "กล่องไม่เรียงแนว — อาจเป็นป้าย/วันที่"),
    ] if cond]
    warns += [f"หลักที่ {d['position']} ({d['digit']}) conf ต่ำ {d['confidence']:.2f} — ควรตรวจด้วยตา" for d in digits if not d["reliable"]]
    warns += [f"หลักที่ {m['position']}: YOLO {m['yolo_digit']} vs SigLIP {m['siglip_digit']} ({m['siglip_confidence']:.2f})" for m in mismatches]

    return {
        "reading": "".join(str(d["digit"]) for d in digits),
        "digits": digits,
        "mean_confidence": round(mean_conf, 4),
        "meter_check": meter,
        "processing": {"best": meta},
        "warnings": warns,
        "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
    }

# ================================================================
# 7) FastAPI Web Service
# ================================================================
app = FastAPI(title="Meter Reader API", version="1.1", description="API อ่านเลขมิเตอร์น้ำอัตโนมัติ (Intuitive Functional Pipeline)")
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
