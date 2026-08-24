"""
main.py — ระบบอ่านเลขมิเตอร์น้ำอัตโนมัติ (Automated Water Meter Reader)
เวอร์ชัน 1.1: โครงสร้างกระชับ สะอาด และประสิทธิภาพสูง (Concise & Production Ready)

ลำดับการทำงาน 4 ขั้นตอน:
  1. Meter Verification: SigLIP2 Zero-Shot ตรวจสอบว่าเป็นภาพมิเตอร์น้ำจริง
  2. Multi-orientation Search: หมุน 4 ทิศ × 3 ฟิลเตอร์ ค้นหามุมและภาพที่ดีที่สุด
  3. Deduplication & Line Alignment: กรองกล่องซ้อนและแยกแยะแถวแนวนอนออกจากคอลัมน์แนวตั้ง
  4. Consistency & Reliability Guard: ตรวจสอบความถูกต้อง (Flip-guard, Dial Cross-check, Red Dial Ratio)

รัน API:     python main.py   →  http://127.0.0.1:8000/docs
รัน Gradio:  python gradio_app.py
"""

from __future__ import annotations

import io
from dataclasses import dataclass
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
# 1) Config — แหล่งรวมค่าคงที่ทั้งหมด (Single Source of Truth)
# ================================================================

@dataclass(frozen=True)
class MeterConfig:
    """คอนฟิกของระบบ ปรับแต่งพารามิเตอร์ทั้งหมดได้ที่นี่"""
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    yolo_model: str = "weights/MeterOCR.pt"
    yolo_imgsz: int = 960
    yolo_conf: float = 0.35
    conf_reliable: float = 0.60
    min_digits: int = 4
    max_digits: int = 9
    angles: tuple[int, ...] = (0, 90, 180, 270)
    preps: tuple[str, ...] = ("orig", "clahe", "histeq")
    clahe_clip: float = 2.0
    clahe_grid: tuple[int, int] = (8, 8)
    orient_margin: float = 0.12
    flip_map: tuple[tuple[int, int], ...] = ((0,0), (1,1), (2,5), (5,2), (6,9), (8,8), (9,6))
    flip_conf: float = 0.60
    align_max_spread: float = 0.10
    vert_max_x: float = 0.02
    vert_min_y: float = 0.03
    red_thresh: float = 0.08
    red_dominance: float = 2.0
    min_crop: int = 4
    siglip_model: str = "google/siglip2-base-patch16-224"
    meter_labels: tuple[str, ...] = ("water meter", "electricity meter", "gas meter", "not a meter")
    meter_verify_conf: float = 0.50

CFG = MeterConfig()
FLIP_DICT = dict(CFG.flip_map)

# Export ตัวแปรระดับ module เพื่อ backward compatibility
DEVICE = CFG.device
YOLO_MODEL = CFG.yolo_model
YOLO_IMGSZ = CFG.yolo_imgsz
YOLO_CONF = CFG.yolo_conf
CONF_RELIABLE = CFG.conf_reliable
EXPECTED_MIN_DIGITS = CFG.min_digits
EXPECTED_MAX_DIGITS = CFG.max_digits
ROTATION_ANGLES = list(CFG.angles)
PREP_LIST = list(CFG.preps)
ORIENT_MARGIN = CFG.orient_margin
FLIP_MAP = FLIP_DICT


# ================================================================
# 2) Image Operations — เครื่องมือจัดการภาพแบบกระชับ
# ================================================================

class ImageOps:
    """ฟังก์ชันพื้นฐานด้าน Image Processing"""

    @staticmethod
    def rotate(img: np.ndarray, angle: int) -> np.ndarray:
        """หมุนภาพตามองศา 90, 180, 270"""
        rot_map = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
        return cv2.rotate(img, rot_map[angle]) if angle in rot_map else img

    @staticmethod
    def apply_prep(img: np.ndarray, prep: str) -> np.ndarray:
        """ฟิลเตอร์ปรับคอนทราสต์: CLAHE (LAB) หรือ HistEq (YCrCb)"""
        if prep == "clahe":
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            lab[:, :, 0] = cv2.createCLAHE(CFG.clahe_clip, CFG.clahe_grid).apply(lab[:, :, 0])
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        if prep == "histeq":
            ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
            return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
        return img

    @staticmethod
    def iou(b1: list[float], b2: list[float]) -> float:
        """คำนวณ Intersection over Union ของ 2 Bounding Box"""
        inter = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0])) * max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
        union = (b1[2] - b1[0]) * (b1[3] - b1[1]) + (b2[2] - b2[0]) * (b2[3] - b2[1]) - inter
        return inter / union if union > 0 else 0.0

    @classmethod
    def dedup(cls, dets: list[dict[str, Any]], thresh: float = 0.45) -> list[dict[str, Any]]:
        """ลบ Bounding Box ที่ซ้อนทับกันโดยเก็บกล่องที่มีความมั่นใจสูงสุด"""
        kept = []
        for d in sorted(dets, key=lambda x: x["confidence"], reverse=True):
            if not any(cls.iou(d["bbox"], k["bbox"]) > thresh for k in kept):
                kept.append(d)
        return sorted(kept, key=lambda x: x["center_x"])

    @staticmethod
    def remap_bbox(bbox: list[float], angle: int, w: int, h: int) -> list[float]:
        """แปลงพิกัดจากภาพที่หมุนกลับสู่พิกัดภาพต้นฉบับ"""
        x1, y1, x2, y2 = bbox
        remap_dict = {
            0: bbox,
            90: [y1, h - x2, y2, h - x1],
            180: [w - x2, h - y2, w - x1, h - y1],
            270: [w - y2, x1, w - y1, x2],
        }
        return remap_dict.get(angle, bbox)

    @staticmethod
    def red_ratio(img: np.ndarray, bbox: list[float]) -> float:
        """คำนวณสัดส่วนพิกเซลสีแดงภายในกล่องตัวเลข"""
        x1, y1, x2, y2 = [int(v) for v in bbox]
        px, py = max(1, int((x2 - x1) * 0.15)), max(1, int((y2 - y1) * 0.15))
        crop = img[max(0, y1 + py):min(img.shape[0], y2 - py), max(0, x1 + px):min(img.shape[1], x2 - px)]
        if crop.size == 0: return 0.0
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        mask = ((hsv[:, :, 0] <= 12) | (hsv[:, :, 0] >= 165)) & (hsv[:, :, 1] >= 40) & (hsv[:, :, 2] >= 40)
        return float(np.mean(mask))


# ================================================================
# 3) Core Reader Pipeline — โมเดลและการอนุมานผล
# ================================================================

class MeterReader:
    """คลาสหลักสำหรับโหลดโมเดลและอ่านค่าตัวเลขมิเตอร์น้ำ"""

    def __init__(self, config: MeterConfig = CFG):
        self.cfg = config
        self._yolo: Any = None
        self._siglip: tuple[Any, Any] | None = None

    @property
    def yolo(self) -> Any:
        if self._yolo is None:
            from ultralytics import YOLO
            self._yolo = YOLO(self.cfg.yolo_model)
            self._yolo.predict(np.zeros((640, 640, 3), dtype=np.uint8), verbose=False)
        return self._yolo

    @property
    def siglip(self) -> tuple[Any, Any]:
        if self._siglip is None:
            from transformers import AutoModel, AutoProcessor
            self._siglip = (
                AutoProcessor.from_pretrained(self.cfg.siglip_model),
                AutoModel.from_pretrained(self.cfg.siglip_model).to(self.cfg.device).eval(),
            )
        return self._siglip

    @property
    def yolo_loaded(self) -> bool: return self._yolo is not None
    @property
    def siglip_loaded(self) -> bool: return self._siglip is not None

    def detect(self, img_bgr: np.ndarray) -> list[dict[str, Any]]:
        """ใช้ YOLO26 ตรวจจับตัวเลข 0-9 ในภาพ"""
        res = self.yolo.predict(img_bgr, imgsz=self.cfg.yolo_imgsz, conf=self.cfg.yolo_conf, device=self.cfg.device, verbose=False)
        return sorted([{
            "digit": int(b.cls[0].item()),
            "confidence": float(b.conf[0].item()),
            "bbox": b.xyxy[0].tolist(),
            "center_x": (b.xyxy[0][0].item() + b.xyxy[0][2].item()) / 2.0,
        } for b in res[0].boxes], key=lambda d: d["center_x"])

    @staticmethod
    def is_vertical(dets: list[dict[str, Any]], w: int, h: int) -> dict[str, Any]:
        """ตรวจสอบว่าตัวเลขเรียงกันเป็นคอลัมน์แนวตั้งหรือไม่"""
        if len(dets) < 2: return {"vertical": False, "x_spread": 0.0, "y_spread": 0.0}
        xs = float(np.std([((d["bbox"][0] + d["bbox"][2]) / 2) / w for d in dets]))
        ys = float(np.std([((d["bbox"][1] + d["bbox"][3]) / 2) / h for d in dets]))
        is_vert = (ys >= xs * 0.8) or (xs <= CFG.vert_max_x and ys >= CFG.vert_min_y)
        return {"vertical": is_vert, "x_spread": round(xs, 4), "y_spread": round(ys, 4)}

    def eval_orientation(self, bgr_img: np.ndarray, angle: int, prep: str):
        """ประเมินคุณภาพการตรวจจับใน 1 มุม และ 1 ฟิลเตอร์"""
        rot = ImageOps.rotate(bgr_img, angle)
        proc = ImageOps.apply_prep(rot, prep)
        dets = ImageOps.dedup(self.detect(proc))
        rh, rw = rot.shape[:2]
        vert = self.is_vertical(dets, rw, rh)
        n = len(dets)
        if not dets or vert["vertical"] or not (self.cfg.min_digits <= n <= self.cfg.max_digits):
            return 0.0, dets, 0.0, prep, vert

        mean = float(np.mean([d["confidence"] for d in dets]))
        score = mean * n

        # วิเคราะห์สีแดง: ตัวเลขสีแดง (ทศนิยม) ต้องอยู่ขวาสุดของมิเตอร์เสมอ
        r_first, r_last = ImageOps.red_ratio(proc, dets[0]["bbox"]), ImageOps.red_ratio(proc, dets[-1]["bbox"])
        if r_first > self.cfg.red_thresh and r_first > r_last * self.cfg.red_dominance:
            score *= 0.5   # แดงอยู่ซ้าย แปลว่าภาพกลับหัว
        elif r_last > self.cfg.red_thresh and r_last > r_first * self.cfg.red_dominance:
            score *= 1.05  # แดงอยู่ขวา ยืนยันว่าทิศทางถูกต้อง

        return score, dets, mean, prep, vert

    def detect_best(self, rgb_img: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
        """ค้นหามุมที่ดีที่สุดจาก 4 ทิศ × 3 ฟิลเตอร์"""
        h, w = rgb_img.shape[:2]
        bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)

        candidates = {a: max([self.eval_orientation(bgr, a, p) for p in self.cfg.preps], key=lambda x: x[0]) for a in self.cfg.angles}
        s0, d0, m0, p0, v0 = candidates[0]
        best_a, (best_s, best_d, best_m, best_p, best_v) = max(candidates.items(), key=lambda x: x[1][0])

        # ป้องกันการกลับหัวโดยไม่จำเป็นด้วย Margin Rule
        margin = bool(best_a != 0 and d0 and not v0["vertical"] and (best_s - s0 < self.cfg.orient_margin))
        if margin:
            best_a, best_d, best_m, best_p = 0, d0, m0, p0

        meta = {"angle": best_a, "clahe": best_p == "clahe", "prep": best_p} if best_d else None
        if meta:
            for d in best_d:
                d["bbox"] = ImageOps.remap_bbox(d["bbox"], best_a, w, h)
                d["center_x"] = (d["bbox"][0] + d["bbox"][2]) / 2.0
            # คงลำดับการอ่านแนวนอนตาม rotated view เดิม

        return best_d, meta, margin

    @torch.inference_mode()
    def check_water_meter(self, rgb_img: np.ndarray) -> dict[str, Any]:
        """SigLIP2 Zero-shot ตรวจสอบว่าเป็นภาพมิเตอร์น้ำ"""
        proc, model = self.siglip
        inp = proc(text=list(self.cfg.meter_labels), images=Image.fromarray(rgb_img), padding="max_length", return_tensors="pt").to(self.cfg.device)
        probs = torch.softmax(model(**inp).logits_per_image, dim=1)[0].cpu().numpy()
        pred = self.cfg.meter_labels[int(np.argmax(probs))]
        return {
            "verified": pred == "water meter" and float(probs[0]) >= self.cfg.meter_verify_conf,
            "predicted_class": pred,
            "confidence": float(probs[0]),
            "probabilities": dict(zip(self.cfg.meter_labels, probs.astype(float))),
        }

    def flip_guard(self, rgb_img: np.ndarray, digits: list[dict[str, Any]], meta: dict[str, Any] | None, h: int, w: int) -> dict[str, Any]:
        """ตรวจสอบความสมมาตร 180° ป้องกันการอ่านเลขกลับหัว (เช่น 6<->9, 2<->5)"""
        if not digits or not meta:
            return {"consistent": True, "anti_reading": "", "anti_digits": [], "anti_confidence": 0.0, "warned": False, "anti_angle": None}
        anti_a = (meta["angle"] + 180) % 360
        rot = ImageOps.rotate(cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR), anti_a)
        anti_dets = ImageOps.dedup(self.detect(ImageOps.apply_prep(rot, meta["prep"])))
        if not anti_dets:
            return {"consistent": True, "anti_reading": "", "anti_digits": [], "anti_confidence": 0.0, "warned": False, "anti_angle": anti_a}

        anti_reading = "".join(str(d["digit"]) for d in anti_dets)
        mean_conf = float(np.mean([d["confidence"] for d in anti_dets]))
        consistent = len(anti_dets) == len(digits) and all(FLIP_DICT.get(digits[-1-j]["digit"]) == a["digit"] for j, a in enumerate(anti_dets) if digits[-1-j]["digit"] in FLIP_DICT)

        return {
            "consistent": consistent,
            "anti_reading": anti_reading,
            "anti_confidence": round(mean_conf, 4),
            "warned": bool(mean_conf >= self.cfg.flip_conf and not consistent),
            "anti_angle": anti_a,
        }

    @torch.inference_mode()
    def cross_check(self, rgb_img: np.ndarray, digits: list[dict[str, Any]], h: int, w: int, angle: int = 0) -> dict[str, Any]:
        """SigLIP2 Cross-check เฉพาะหลักที่ YOLO มีความมั่นใจต่ำ (< 0.60)"""
        low_conf = [d for d in digits if d["confidence"] < self.cfg.conf_reliable]
        if not low_conf: return {"enabled": True, "checked": 0, "mismatches": []}
        proc, model = self.siglip
        labels = [str(i) for i in range(10)]
        mismatches = []
        for d in low_conf:
            x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
            crop = rgb_img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            if crop.shape[0] < self.cfg.min_crop or crop.shape[1] < self.cfg.min_crop: continue
            if angle:
                crop = cv2.cvtColor(ImageOps.rotate(cv2.cvtColor(crop, cv2.COLOR_RGB2BGR), angle), cv2.COLOR_BGR2RGB)
            inp = proc(text=labels, images=Image.fromarray(crop), padding="max_length", return_tensors="pt").to(self.cfg.device)
            probs = torch.softmax(model(**inp).logits_per_image, dim=1)[0].cpu().numpy()
            pred = int(np.argmax(probs))
            if pred != d["digit"]:
                mismatches.append({"position": d["position"], "yolo_digit": d["digit"], "siglip_digit": pred, "siglip_confidence": float(probs[pred])})
        return {"enabled": True, "checked": len(low_conf), "mismatches": mismatches}

    def read_meter(self, rgb_img: np.ndarray) -> dict[str, Any]:
        """ไปป์ไลน์หลัก: รับภาพ RGB → ประมวลผล → คืนค่าผลการอ่านพร้อมคำเตือน"""
        t0 = perf_counter()
        h, w = rgb_img.shape[:2]

        meter = self.check_water_meter(rgb_img)
        if not meter["verified"]:
            return self._build_result("", [], 0.0, meter, None, False, [f"ภาพนี้ไม่ใช่มิเตอร์น้ำ ({meter['predicted_class']})"], t0, w, h)

        dets, meta, margin = self.detect_best(rgb_img)
        if not dets:
            return self._build_result("", [], 0.0, meter, meta, margin, ["ตรวจไม่พบตัวเลข"], t0, w, h)

        digits = [{
            "position": i, "digit": d["digit"], "confidence": d["confidence"],
            "bbox": d["bbox"], "reliable": d["confidence"] >= self.cfg.conf_reliable
        } for i, d in enumerate(dets, 1)]
        mean_conf = float(np.mean([d["confidence"] for d in digits]))

        if meta and meta["angle"] == 0 and self.is_vertical(digits, w, h)["vertical"]:
            return self._build_result("", [], 0.0, meter, meta, margin, ["กล่องเรียงแนวตั้ง — ไม่ใช่ค่ามิเตอร์"], t0, w, h)

        flip = self.flip_guard(rgb_img, digits, meta, h, w)
        align_spread = float(np.std([((d['bbox'][0]+d['bbox'][2])/2)/w if meta and meta['angle'] in (90,270) else ((d['bbox'][1]+d['bbox'][3])/2)/h for d in digits]))
        align = {"ok": align_spread <= self.cfg.align_max_spread, "y_spread": round(align_spread, 4)}
        cross = self.cross_check(rgb_img, digits, h, w, meta["angle"] if meta else 0)

        warns = [msg for cond, msg in [
            (not (self.cfg.min_digits <= len(digits) <= self.cfg.max_digits), f"จำนวนหลัก {len(digits)} นอกช่วง {self.cfg.min_digits}-{self.cfg.max_digits}"),
            (digits[0]["digit"] == 0, "หลักแรกเป็น 0 — อาจเกินมา 1 หลัก"),
            (mean_conf < self.cfg.conf_reliable, f"mean conf ต่ำ {mean_conf:.2f} — ภาพอาจเบลอ/เอียง"),
            (flip["warned"], f"อาจกลับหัว! หมุน 180° ได้ {flip['anti_reading']} ({flip['anti_confidence']:.2f}) — ตรวจภาพก่อนบันทึก"),
            (not align["ok"], f"กล่องไม่เรียงแนว y_spread={align['y_spread']:.3f} — อาจเป็นป้าย/วันที่"),
        ] if cond]
        warns += [f"หลักที่ {d['position']} ({d['digit']}) conf ต่ำ {d['confidence']:.2f} — ควรตรวจด้วยตา" for d in digits if not d["reliable"]]
        warns += [f"หลักที่ {m['position']}: YOLO {m['yolo_digit']} vs SigLIP {m['siglip_digit']} ({m['siglip_confidence']:.2f})" for m in cross["mismatches"]]

        return self._build_result("".join(str(d["digit"]) for d in digits), digits, mean_conf, meter, meta, margin, warns, t0, w, h, flip, align, cross)

    @staticmethod
    def _build_result(reading: str, digits: list, mean_conf: float, meter: dict, meta: dict | None, margin: bool, warns: list[str], t0: float, w: int, h: int, flip=None, align=None, cross=None) -> dict[str, Any]:
        return {
            "reading": reading, "digits": digits, "digit_count": len(digits), "mean_confidence": mean_conf,
            "meter_check": meter, "processing": {"best": meta, "margin_applied": margin, "auto_corrected": False},
            "flip_check": flip or {}, "alignment": align or {}, "cross_check": cross or {},
            "warnings": warns, "elapsed_ms": (perf_counter() - t0) * 1000, "image_size": [w, h],
        }


# ================================================================
# 4) Default Instance & Function Aliases (Backward Compatibility)
# ================================================================

_default_reader = MeterReader()

def read_meter(image_rgb: np.ndarray) -> dict[str, Any]:
    return _default_reader.read_meter(image_rgb)

def check_water_meter(image_rgb: np.ndarray) -> dict[str, Any]:
    return _default_reader.check_water_meter(image_rgb)

def detect_digits(image_bgr: np.ndarray) -> list[dict[str, Any]]:
    return _default_reader.detect(image_bgr)

def detect_digits_best(image_rgb: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    return _default_reader.detect_best(image_rgb)

def is_vertical(dets: list[dict[str, Any]], img_w: int, img_h: int) -> dict[str, float | bool]:
    return _default_reader.is_vertical(dets, img_w, img_h)

rotate_image = ImageOps.rotate
apply_prep = ImageOps.apply_prep
iou = ImageOps.iou
dedup_detections = ImageOps.dedup
remap_bbox = ImageOps.remap_bbox
red_ratio = ImageOps.red_ratio
get_yolo = lambda: _default_reader.yolo
get_siglip = lambda: _default_reader.siglip


# ================================================================
# 5) FastAPI Application
# ================================================================

app = FastAPI(title="Meter Reader API", version="1.1", description="API อ่านเลขมิเตอร์น้ำอัตโนมัติ")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "device": CFG.device,
        "yolo_loaded": _default_reader.yolo_loaded,
        "siglip_loaded": _default_reader.siglip_loaded,
    }

@app.post("/api/read-meter")
async def read_meter_endpoint(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="ชนิดไฟล์ไม่รองรับ")
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        arr = np.asarray(img.convert("RGB"))
    except Exception:
        raise HTTPException(status_code=422, detail="อ่านไฟล์ภาพไม่ได้")
    return await run_in_threadpool(read_meter, arr)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
