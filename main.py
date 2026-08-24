"""
main.py — อ่านเลขมิเตอร์น้ำ (Velocity Type) แบบไฟล์เดียว + OOP
รวมทุกโมดูลไว้ในไฟล์เดียวตามคำขอดั้งเดิม แต่โครงเป็น OOP เพื่อสอนง่าย

ลำดับ 4 ขั้น:
  0) MeterVerifier.check_water_meter — คัดแยกด้วย SigLIP2
  1) DigitDetector.best — ลอง 4ทิศ×3ฟิลเตอร์ (orig/clahe/histeq)
  2) MeterReader.read — เรียง, dedup, กันแนวตั้ง
  3) กันกลับหัว — flip_guard + cross_check

รัน:  python main.py  →  http://127.0.0.1:8000/docs
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
# 1) Config — ค่าคงที่ทั้งหมด
# ================================================================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

YOLO_MODEL = "weights/MeterOCR.pt"
YOLO_IMGSZ = 960
YOLO_CONF  = 0.35
CONF_RELIABLE = 0.60

EXPECTED_MIN_DIGITS = 4
EXPECTED_MAX_DIGITS = 9

ROTATION_ANGLES = [0, 90, 180, 270]
PREP_LIST = ["orig", "clahe", "histeq"]
CLAHE_VARIANTS = [False, True]  # deprecated
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID  = (8, 8)

ORIENT_MARGIN    = 0.12
FLIP_MAP         = {0:0, 1:1, 2:5, 5:2, 6:9, 8:8, 9:6}
FLIP_GUARD_CONF  = 0.60
ALIGN_MAX_Y_SPREAD = 0.10
DIGIT_CROSS_CHECK = True

VERTICAL_MAX_X_SPREAD = 0.02
VERTICAL_MIN_Y_SPREAD = 0.03

RED_RATIO_THRESHOLD = 0.08
RED_RATIO_DOMINANCE = 2.0
MIN_CROP_PX = 4

SIGLIP_MODEL = "google/siglip2-base-patch16-224"
METER_LABELS = ["water meter", "electricity meter", "gas meter", "not a meter"]
METER_VERIFY_CONF = 0.50


@dataclass(frozen=True)
class MeterConfig:
    """OOP: รวมคอนฟิกเป็นออบเจ็กต์ ส่งต่อแบบ DI เทสง่าย"""
    device: str = DEVICE
    yolo_model: str = YOLO_MODEL
    yolo_imgsz: int = YOLO_IMGSZ
    yolo_conf: float = YOLO_CONF
    conf_reliable: float = CONF_RELIABLE
    expected_min_digits: int = EXPECTED_MIN_DIGITS
    expected_max_digits: int = EXPECTED_MAX_DIGITS
    rotation_angles: tuple[int, ...] = (0, 90, 180, 270)
    prep_list: tuple[str, ...] = ("orig", "clahe", "histeq")
    clahe_clip_limit: float = CLAHE_CLIP_LIMIT
    clahe_tile_grid: tuple[int, int] = (8, 8)
    orient_margin: float = ORIENT_MARGIN
    flip_map: dict[int, int] | None = None
    flip_guard_conf: float = FLIP_GUARD_CONF
    align_max_y_spread: float = ALIGN_MAX_Y_SPREAD
    digit_cross_check: bool = DIGIT_CROSS_CHECK
    vertical_max_x_spread: float = VERTICAL_MAX_X_SPREAD
    vertical_min_y_spread: float = VERTICAL_MIN_Y_SPREAD
    red_ratio_threshold: float = RED_RATIO_THRESHOLD
    red_ratio_dominance: float = RED_RATIO_DOMINANCE
    min_crop_px: int = MIN_CROP_PX
    siglip_model: str = SIGLIP_MODEL
    meter_labels: tuple[str, ...] = ("water meter", "electricity meter", "gas meter", "not a meter")
    meter_verify_conf: float = METER_VERIFY_CONF
    def __post_init__(self):
        if self.flip_map is None:
            object.__setattr__(self, "flip_map", dict(FLIP_MAP))

DEFAULT_CONFIG = MeterConfig()


# ================================================================
# 2) ImageProcessor — เครื่องมือภาพล้วน ๆ
# ================================================================

class ImageProcessor:
    """รวมงานภาพไว้ที่เดียว — แต่ละเมธอด pure function"""

    def __init__(self, clahe_clip: float = CLAHE_CLIP_LIMIT, clahe_grid: tuple[int,int] = CLAHE_TILE_GRID):
        self.clahe_clip = clahe_clip
        self.clahe_grid = clahe_grid

    def rotate(self, img_bgr: np.ndarray, angle: int) -> np.ndarray:
        if angle == 90: return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
        if angle == 180: return cv2.rotate(img_bgr, cv2.ROTATE_180)
        if angle == 270: return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return img_bgr

    def clahe(self, img_bgr: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.createCLAHE(self.clahe_clip, self.clahe_grid).apply(l)
        return cv2.cvtColor(cv2.merge([l,a,b]), cv2.COLOR_LAB2BGR)

    def histeq(self, img_bgr: np.ndarray) -> np.ndarray:
        ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        y = cv2.equalizeHist(y)
        return cv2.cvtColor(cv2.merge([y,cr,cb]), cv2.COLOR_YCrCb2BGR)

    def apply_prep(self, img_bgr: np.ndarray, prep: str) -> np.ndarray:
        if prep == "clahe": return self.clahe(img_bgr)
        if prep == "histeq": return self.histeq(img_bgr)
        return img_bgr

    @staticmethod
    def iou(b1: list[float], b2: list[float]) -> float:
        x1 = max(b1[0],b2[0]); y1 = max(b1[1],b2[1]); x2 = min(b1[2],b2[2]); y2 = min(b1[3],b2[3])
        inter = max(0, x2-x1)*max(0, y2-y1)
        a1 = (b1[2]-b1[0])*(b1[3]-b1[1]); a2 = (b2[2]-b2[0])*(b2[3]-b2[1])
        return inter/(a1+a2-inter) if a1+a2-inter>0 else 0.0

    def dedup(self, dets: list[dict[str,Any]], thresh: float=0.45) -> list[dict[str,Any]]:
        if not dets: return dets
        by_conf = sorted(dets, key=lambda d: d["confidence"], reverse=True)
        kept: list[dict[str,Any]] = []
        for d in by_conf:
            if not any(self.iou(d["bbox"], k["bbox"]) > thresh for k in kept):
                kept.append(d)
        kept.sort(key=lambda d: d["center_x"])
        return kept

    @staticmethod
    def remap_bbox(bbox: list[float], angle: int, img_w: int, img_h: int) -> list[float]:
        x1,y1,x2,y2 = bbox
        if angle==0: return bbox
        if angle==90: return [y1, img_h-x2, y2, img_h-x1]
        if angle==180: return [img_w-x2, img_h-y2, img_w-x1, img_h-y1]
        return [img_w-y2, x1, img_w-y1, x2]

    @staticmethod
    def red_ratio(img_bgr: np.ndarray, bbox: list[float]) -> float:
        x1,y1,x2,y2 = [int(v) for v in bbox]
        pad_x = max(1,int((x2-x1)*0.15)); pad_y = max(1,int((y2-y1)*0.15))
        crop = img_bgr[max(0,y1+pad_y):min(img_bgr.shape[0],y2-pad_y), max(0,x1+pad_x):min(img_bgr.shape[1],x2-pad_x)]
        if crop.size==0: return 0.0
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        h,s,v = cv2.split(hsv)
        red = ((h<=12)|(h>=165)) & (s>=40) & (v>=40)
        return float(np.sum(red))/float(crop.shape[0]*crop.shape[1])

    @staticmethod
    def pack_digits(dets: list[dict[str,Any]]) -> list[dict[str,Any]]:
        return [{"position":i, "digit":d["digit"], "confidence":d["confidence"], "bbox":d["bbox"], "reliable":d["confidence"]>=CONF_RELIABLE} for i,d in enumerate(dets,1)]


# ================================================================
# 3) ModelManager — โหลดโมเดลแบบ lazy
# ================================================================

class ModelManager:
    def __init__(self, config: MeterConfig | None = None):
        self.config = config or DEFAULT_CONFIG
        self._yolo: Any = None
        self._siglip: tuple[Any,Any] | None = None

    def get_yolo(self) -> Any:
        if self._yolo is None:
            from ultralytics import YOLO
            self._yolo = YOLO(self.config.yolo_model)
            self._yolo.predict(np.zeros((640,640,3),dtype=np.uint8), verbose=False)
        return self._yolo

    def get_siglip(self) -> tuple[Any,Any]:
        if self._siglip is None:
            from transformers import AutoModel, AutoProcessor
            self._siglip = (AutoProcessor.from_pretrained(self.config.siglip_model),
                            AutoModel.from_pretrained(self.config.siglip_model).to(DEVICE).eval())
        return self._siglip

    @property
    def yolo_loaded(self) -> bool: return self._yolo is not None
    @property
    def siglip_loaded(self) -> bool: return self._siglip is not None


# ================================================================
# 4) DigitDetector — หาตัวเลข
# ================================================================

class DigitDetector:
    def __init__(self, config: MeterConfig | None=None, models: ModelManager | None=None, img: ImageProcessor | None=None):
        self.config = config or DEFAULT_CONFIG
        self.models = models or ModelManager(self.config)
        self.img = img or ImageProcessor()

    def detect(self, image_bgr: np.ndarray) -> list[dict[str,Any]]:
        res = self.models.get_yolo().predict(image_bgr, imgsz=self.config.yolo_imgsz, conf=self.config.yolo_conf, device=DEVICE, verbose=False)
        dets: list[dict[str,Any]] = []
        for box in res[0].boxes:
            x1,y1,x2,y2 = box.xyxy[0].tolist()
            dets.append({"digit":int(box.cls[0].item()), "confidence":float(box.conf[0].item()), "bbox":[x1,y1,x2,y2], "center_x":(x1+x2)/2})
        dets.sort(key=lambda d: d["center_x"])
        return dets

    def is_vertical(self, dets: list[dict[str,Any]], img_w: int, img_h: int) -> dict[str,float|bool]:
        if len(dets)<2: return {"vertical":False,"x_spread":0.0,"y_spread":0.0}
        cx=[((d["bbox"][0]+d["bbox"][2])/2)/img_w for d in dets]
        cy=[((d["bbox"][1]+d["bbox"][3])/2)/img_h for d in dets]
        xs,ys=float(np.std(cx)),float(np.std(cy))
        is_vert = (ys >= xs * 0.8) or (xs <= self.config.vertical_max_x_spread and ys >= self.config.vertical_min_y_spread)
        return {"vertical": is_vert, "x_spread": round(xs, 4), "y_spread": round(ys, 4)}

    def is_aligned(self, dets: list[dict[str,Any]], img_w: int, img_h: int, angle:int=0) -> dict[str,float|bool]:
        if len(dets)<2: return {"ok":True,"y_spread":0.0}
        vals=[((d["bbox"][0]+d["bbox"][2])/2)/img_w for d in dets] if angle in (90,270) else [((d["bbox"][1]+d["bbox"][3])/2)/img_h for d in dets]
        return {"ok":float(np.std(vals))<=self.config.align_max_y_spread, "y_spread":round(float(np.std(vals)),4)}

    def best(self, image_rgb: np.ndarray) -> tuple[list[dict[str,Any]], dict[str,Any]|None, bool]:
        h,w=image_rgb.shape[:2]; bgr_all=cv2.cvtColor(image_rgb,cv2.COLOR_RGB2BGR)
        all_scores: dict[int,list] = {a:[] for a in self.config.rotation_angles}
        for angle in self.config.rotation_angles:
            rot=self.img.rotate(bgr_all,angle); rh,rw=rot.shape[:2]
            for prep in self.config.prep_list:
                proc=self.img.apply_prep(rot,prep)
                dets=self.img.dedup(self.detect(proc))
                vert=self.is_vertical(dets,rw,rh); n=len(dets)
                if dets and not vert["vertical"] and self.config.expected_min_digits<=n<=self.config.expected_max_digits:
                    mean=float(np.mean([d["confidence"] for d in dets])); score=mean*n
                    by_x=sorted(dets,key=lambda d:d["center_x"])
                    rf=self.img.red_ratio(proc,by_x[0]["bbox"]); rl=self.img.red_ratio(proc,by_x[-1]["bbox"])
                    if rf>self.config.red_ratio_threshold and rf>rl*self.config.red_ratio_dominance: score*=0.5
                    elif rl>self.config.red_ratio_threshold and rl>rf*self.config.red_ratio_dominance: score*=1.05
                elif dets and not vert["vertical"]:
                    mean=float(np.mean([d["confidence"] for d in dets])) if dets else 0.0; score=0.0
                else: mean,score=0.0,0.0
                all_scores[angle].append((prep,dets,mean,score,vert))
        def best_of(a): return max(all_scores[a],key=lambda x:x[3])
        p0,d0,m0,s0,v0=best_of(0)
        best_angle,best_prep,best_dets,best_mean,best_score=0,p0,d0,m0,s0
        for a in self.config.rotation_angles:
            prep,dets,mean,score,_=best_of(a)
            if score>best_score: best_angle,best_prep,best_dets,best_mean,best_score=a,prep,dets,mean,score
        has_zero=bool(d0) and not v0["vertical"]
        if best_angle!=0 and has_zero and best_score-s0<self.config.orient_margin:
            best_angle,margin=0,True; best_prep,best_dets,best_mean,best_score=p0,d0,m0,s0
        else: margin=False
        best_meta=None if not best_dets else {"angle":best_angle,"clahe":best_prep=="clahe","prep":best_prep}
        if best_meta:
            for d in best_dets: d["bbox"]=self.img.remap_bbox(d["bbox"],best_angle,w,h); d["center_x"]=(d["bbox"][0]+d["bbox"][2])/2
            # เก็บตามลำดับการอ่านแนวนอนเดิมใน rotated view ไม่ sort ซ้ำด้วยพิกัดภาพเดิม
        return best_dets,best_meta,margin


# ================================================================
# 5) MeterVerifier — ตรวจความน่าเชื่อถือ
# ================================================================

class MeterVerifier:
    def __init__(self, config: MeterConfig | None=None, models: ModelManager | None=None, img: ImageProcessor | None=None):
        self.config=config or DEFAULT_CONFIG; self.models=models or ModelManager(self.config); self.img=img or ImageProcessor()

    def check_water_meter(self, image_rgb: np.ndarray) -> dict[str,Any]:
        proc,model=self.models.get_siglip()
        inp=proc(text=list(self.config.meter_labels), images=Image.fromarray(image_rgb), padding="max_length", return_tensors="pt").to(DEVICE)
        with torch.no_grad(): probs=torch.softmax(model(**inp).logits_per_image, dim=1)[0].cpu().numpy()
        pred=self.config.meter_labels[int(np.argmax(probs))]
        return {"verified":pred=="water meter" and float(probs[0])>=self.config.meter_verify_conf, "predicted_class":pred, "confidence":float(probs[0]), "probabilities":{l:float(p) for l,p in zip(self.config.meter_labels,probs)}}

    def flip_compare(self, digits: list[dict[str,Any]], anti: list[dict[str,Any]]) -> tuple[bool,int]:
        if len(anti)!=len(digits): return False,1
        miss=0; n=len(digits)
        for j,a in enumerate(anti):
            exp=self.config.flip_map.get(digits[n-1-j]["digit"])
            if exp is not None and a["digit"]!=exp: miss+=1
        return miss==0,miss

    def flip_guard(self, image_rgb: np.ndarray, digits: list[dict[str,Any]], best_meta: dict[str,Any]|None, h:int,w:int) -> dict[str,Any]:
        out: dict[str,Any]={"consistent":True,"anti_reading":"","anti_digits":[],"anti_confidence":0.0,"warned":False,"applied":False,"anti_angle":(best_meta["angle"]+180)%360 if best_meta else None}
        if not digits or not best_meta: return out
        anti_angle=out["anti_angle"]; bgr=cv2.cvtColor(image_rgb,cv2.COLOR_RGB2BGR)
        rot=self.img.rotate(bgr,anti_angle); prep=best_meta.get("prep","clahe" if best_meta.get("clahe") else "orig")
        proc=self.img.apply_prep(rot,prep)
        det=DigitDetector(self.config,self.models,self.img); anti=self.img.dedup(det.detect(proc))
        if not anti: return out
        anti_sorted=sorted(anti,key=lambda d:d["center_x"])
        out["anti_reading"]="".join(str(d["digit"]) for d in anti_sorted)
        out["anti_mean_raw"]=float(np.mean([d["confidence"] for d in anti_sorted])); out["anti_confidence"]=round(out["anti_mean_raw"],4)
        if out["anti_confidence"]<self.config.flip_guard_conf: return out
        remapped: list[dict[str,Any]] = []
        for d in anti_sorted:
            b=self.img.remap_bbox(d["bbox"],anti_angle,w,h)
            remapped.append({"digit":d["digit"],"confidence":d["confidence"],"bbox":b,"center_x":(b[0]+b[2])/2})
        out["anti_digits"]=[{"digit":d["digit"],"confidence":d["confidence"],"bbox":d["bbox"]} for d in remapped]
        out["anti_reading_sorted"]="".join(str(d["digit"]) for d in remapped); out["anti_prep"]=prep
        out["consistent"],_=self.flip_compare(digits,anti_sorted); out["warned"]=not out["consistent"]
        return out

    def cross_check(self, image_rgb: np.ndarray, digits: list[dict[str,Any]], h:int,w:int, best_angle:int=0) -> dict[str,Any]:
        if not self.config.digit_cross_check or not digits: return {"enabled":self.config.digit_cross_check,"checked":0,"mismatches":[]}
        proc,model=self.models.get_siglip(); labels=[str(i) for i in range(10)]; bad=[]
        for d in digits:
            if d["confidence"]>=self.config.conf_reliable: continue
            x1,y1,x2,y2=[int(v) for v in d["bbox"]]; x1,y1,x2,y2=max(x1,0),max(y1,0),min(x2,w),min(y2,h)
            crop=image_rgb[y1:y2,x1:x2]
            if crop.shape[0]<self.config.min_crop_px or crop.shape[1]<self.config.min_crop_px: continue
            if best_angle!=0: crop=cv2.cvtColor(self.img.rotate(cv2.cvtColor(crop,cv2.COLOR_RGB2BGR),best_angle),cv2.COLOR_BGR2RGB)
            inp=proc(text=labels, images=Image.fromarray(crop), padding="max_length", return_tensors="pt").to(DEVICE)
            with torch.no_grad(): probs=torch.softmax(model(**inp).logits_per_image, dim=1)[0].cpu().numpy()
            pred=int(np.argmax(probs))
            if pred!=d["digit"]: bad.append({"position":d["position"],"yolo_digit":d["digit"],"siglip_digit":pred,"siglip_confidence":float(probs[pred])})
        return {"enabled":True,"checked":sum(1 for d in digits if d["confidence"]<self.config.conf_reliable),"mismatches":bad}


# ================================================================
# 6) MeterReader — ไปป์ไลน์หลัก (OOP)
# ================================================================

class MeterReader:
    """ประกอบ detector + verifier — จุดเดียวที่ UI/API เรียก"""
    def __init__(self, config: MeterConfig|None=None, detector: DigitDetector|None=None, verifier: MeterVerifier|None=None, img: ImageProcessor|None=None, models: ModelManager|None=None):
        self.config=config or DEFAULT_CONFIG
        self.img=img or ImageProcessor()
        self.models=models or ModelManager(self.config)
        self.detector=detector or DigitDetector(self.config,self.models,self.img)
        self.verifier=verifier or MeterVerifier(self.config,self.models,self.img)

    def read(self, image_rgb: np.ndarray) -> dict[str,Any]:
        t0=perf_counter(); h,w=image_rgb.shape[:2]
        meter=self.verifier.check_water_meter(image_rgb)
        if not meter["verified"]:
            return {"reading":"", "digits":[], "digit_count":0, "mean_confidence":0.0, "meter_check":meter, "processing":{"best":None,"margin_applied":False,"auto_corrected":False}, "warnings":[f"ภาพนี้ไม่ใช่มิเตอร์น้ำ (จำแนกว่า: {meter['predicted_class']}, {meter['confidence']:.2f})"], "elapsed_ms":(perf_counter()-t0)*1000, "image_size":[w,h]}
        dets,best_meta,margin=self.detector.best(image_rgb)
        processing={"best":best_meta,"margin_applied":margin,"auto_corrected":False}
        if not dets:
            return {"reading":"", "digits":[], "digit_count":0, "mean_confidence":0.0, "meter_check":meter, "processing":processing, "warnings":["ตรวจไม่พบตัวเลข (ลองหมุน+ฟิลเตอร์แล้ว)"], "elapsed_ms":(perf_counter()-t0)*1000, "image_size":[w,h]}
        digits=self.img.pack_digits(dets); reading="".join(str(d["digit"]) for d in digits); mean_conf=float(np.mean([d["confidence"] for d in digits]))
        flip=self.verifier.flip_guard(image_rgb,digits,best_meta,h,w)
        flip.pop("anti_mean_raw",None); flip.pop("anti_reading_sorted",None)
        vert={"vertical":False}
        if best_meta and best_meta["angle"]==0: vert=self.detector.is_vertical(digits,w,h)
        if vert["vertical"]:
            return {"reading":"", "digits":[], "digit_count":0, "mean_confidence":0.0, "meter_check":meter, "processing":processing, "warnings":[f"กล่องเรียงแนวตั้ง x={vert['x_spread']} y={vert['y_spread']} — ไม่ใช่ค่ามิเตอร์"], "elapsed_ms":(perf_counter()-t0)*1000, "image_size":[w,h]}
        warns: list[str]=[]; n=len(digits)
        if n<self.config.expected_min_digits or n>self.config.expected_max_digits: warns.append(f"จำนวนหลัก {n} นอกช่วง {self.config.expected_min_digits}-{self.config.expected_max_digits}")
        for d in digits:
            if not d["reliable"]: warns.append(f"หลักที่ {d['position']} ({d['digit']}) conf ต่ำ {d['confidence']:.2f} — ควรตรวจด้วยตา")
        if digits and digits[0]["digit"]==0: warns.append("หลักแรกเป็น 0 — อาจเกินมา 1 หลัก")
        if mean_conf<self.config.conf_reliable: warns.append(f"mean conf ต่ำ {mean_conf:.2f} — ภาพอาจเบลอ/เอียง")
        if flip["warned"]: warns.append(f"อาจกลับหัว! หมุน 180° ได้ {flip['anti_reading']} ({flip['anti_confidence']:.2f}) — ตรวจภาพก่อนบันทึก")
        align=self.detector.is_aligned(digits,w,h,angle=best_meta["angle"] if best_meta else 0)
        if not align["ok"]: warns.append(f"กล่องไม่เรียงแนว y_spread={align['y_spread']:.3f} — อาจเป็นป้าย/วันที่")
        cross=self.verifier.cross_check(image_rgb,digits,h,w,best_angle=best_meta["angle"] if best_meta else 0)
        for m in cross["mismatches"]: warns.append(f"หลักที่ {m['position']}: YOLO {m['yolo_digit']} vs SigLIP {m['siglip_digit']} ({m['siglip_confidence']:.2f})")
        return {"reading":reading,"digits":digits,"digit_count":n,"mean_confidence":mean_conf,"meter_check":meter,"processing":processing,"flip_check":flip,"alignment":align,"cross_check":cross,"warnings":warns,"elapsed_ms":(perf_counter()-t0)*1000,"image_size":[w,h]}


# Backward-compat ให้ `from main import read_meter` ยังใช้ได้ — เติม type hints ให้ครบ
_default_reader = MeterReader()

def read_meter(image_rgb: np.ndarray) -> dict[str, Any]:
    """wrapper เรียก MeterReader.read — คงไว้ให้โค้ดเก่าไม่พัง"""
    return _default_reader.read(image_rgb)

def check_water_meter(image_rgb: np.ndarray) -> dict[str, Any]:
    return _default_reader.verifier.check_water_meter(image_rgb)

def detect_digits(image_bgr: np.ndarray) -> list[dict[str, Any]]:
    return _default_reader.detector.detect(image_bgr)

def detect_digits_best(image_rgb: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    return _default_reader.detector.best(image_rgb)

def flip_guard(image_rgb: np.ndarray, digits: list[dict[str, Any]], best_meta: dict[str, Any] | None, h: int, w: int) -> dict[str, Any]:
    return _default_reader.verifier.flip_guard(image_rgb, digits, best_meta, h, w)

def cross_check_digits(image_rgb: np.ndarray, digits: list[dict[str, Any]], h: int, w: int, best_angle: int = 0) -> dict[str, Any]:
    return _default_reader.verifier.cross_check(image_rgb, digits, h, w, best_angle)

def is_vertical(dets: list[dict[str, Any]], img_w: int, img_h: int) -> dict[str, float | bool]:
    return _default_reader.detector.is_vertical(dets, img_w, img_h)

def is_aligned(dets: list[dict[str, Any]], img_w: int, img_h: int, angle: int = 0) -> dict[str, float | bool]:
    return _default_reader.detector.is_aligned(dets, img_w, img_h, angle)
# re-export ค่าคงที่และคลาส
get_yolo = _default_reader.models.get_yolo
get_siglip = _default_reader.models.get_siglip
rotate_image = _default_reader.img.rotate
clahe_filter = _default_reader.img.clahe
histeq_filter = _default_reader.img.histeq
apply_prep = _default_reader.img.apply_prep
iou = _default_reader.img.iou
dedup_detections = _default_reader.img.dedup
remap_bbox = _default_reader.img.remap_bbox
red_ratio = _default_reader.img.red_ratio
pack_digits = _default_reader.img.pack_digits

# ================================================================
# 7) FastAPI
# ================================================================

app = FastAPI(title="Meter Reader API", version="3.0-OOP", description="อ่านเลขมิเตอร์น้ำ — OOP ไฟล์เดียวสำหรับสื่อการสอน")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
ALLOWED_TYPES={"image/jpeg","image/png","image/webp","image/bmp"}

@app.get("/api/health")
def health() -> dict[str,Any]:
    return {"status":"ok","device":DEVICE,"yolo_loaded":_default_reader.models.yolo_loaded,"siglip_loaded":_default_reader.models.siglip_loaded}

@app.post("/api/read-meter")
async def read_meter_endpoint(file: UploadFile = File(...)) -> dict[str,Any]:
    if file.content_type not in ALLOWED_TYPES: raise HTTPException(status_code=415, detail="ชนิดไฟล์ไม่รองรับ")
    data=await file.read()
    try:
        img=Image.open(io.BytesIO(data)); img.load(); arr=np.asarray(img.convert("RGB"))
    except Exception: raise HTTPException(status_code=422, detail="อ่านไฟล์ภาพไม่ได้")
    return await run_in_threadpool(read_meter, arr)

if __name__=="__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
