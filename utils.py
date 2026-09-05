"""
utils.py — Reusable Computer Vision and Geometry Utilities for Meter OCR Pipeline
Provides pure functions for image transformations, contrast enhancement,
coordinate remapping, bounding box deduplication, color analysis, and statistical evaluation.
"""
from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np


def rotate_image(img_bgr: np.ndarray, angle: int) -> np.ndarray:
    """
    Rotate BGR image by 90, 180, or 270 degrees clockwise.
    Returns original image unchanged if angle == 0.
    """
    if angle == 90:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(img_bgr, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img_bgr


def apply_prep(
    img_bgr: np.ndarray,
    prep: str,
    clahe_clip: float = 2.0,
    clahe_grid: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Apply image contrast enhancement:
    - 'clahe': Contrast Limited Adaptive Histogram Equalization on L channel (LAB color space)
    - 'histeq': Global Histogram Equalization on Y channel (YCrCb color space)
    - 'orig' or unknown: returns original image without modification
    """
    if prep == "clahe":
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=clahe_grid)
        l_clahe = clahe.apply(l)
        return cv2.cvtColor(cv2.merge([l_clahe, a, b]), cv2.COLOR_LAB2BGR)

    if prep == "histeq":
        ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        y_eq = cv2.equalizeHist(y)
        return cv2.cvtColor(cv2.merge([y_eq, cr, cb]), cv2.COLOR_YCrCb2BGR)

    return img_bgr


def remap_point(x: float, y: float, angle: int, w: int, h: int) -> tuple[float, float]:
    """
    Map coordinate (x, y) from a rotated image frame back to original image dimensions (w, h).
    """
    if angle == 90:
        return y, h - x      # Inverse of 90° clockwise
    if angle == 180:
        return w - x, h - y  # Inverse of 180° rotation
    if angle == 270:
        return w - y, x      # Inverse of 270° clockwise (90° CCW)
    return x, y


def remap_bbox(bbox: list[float], angle: int, w: int, h: int) -> list[float]:
    """
    Map bounding box [x1, y1, x2, y2] from rotated frame back to original image coordinates.
    Maintains [min_x, min_y, max_x, max_y] canonical ordering.
    """
    x1, y1, x2, y2 = bbox
    p1_x, p1_y = remap_point(x1, y1, angle, w, h)
    p2_x, p2_y = remap_point(x2, y2, angle, w, h)
    return [
        min(p1_x, p2_x),
        min(p1_y, p2_y),
        max(p1_x, p2_x),
        max(p1_y, p2_y),
    ]


def iou(box1: list[float], box2: list[float]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2].
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    union = area1 + area2 - intersection

    return (intersection / union) if union > 0.0 else 0.0


def dedup_detections(dets: list[dict[str, Any]], thresh: float = 0.45) -> list[dict[str, Any]]:
    """
    Filter overlapping detection boxes using greedy Non-Maximum Suppression (NMS).
    Keeps boxes with highest confidence, sorted horizontally left-to-right by center_x.
    """
    kept: list[dict[str, Any]] = []
    for d in sorted(dets, key=lambda x: x["confidence"], reverse=True):
        if not any(iou(d["bbox"], k["bbox"]) > thresh for k in kept):
            kept.append(d)
    return sorted(kept, key=lambda x: x["center_x"])


def red_ratio(img_bgr: np.ndarray, bbox: list[float]) -> float:
    """
    Compute ratio of red pixels within a bounding box crop using HSV thresholding.
    Used for decimal digit verification (red digits on water meters).
    """
    x1, y1, x2, y2 = [int(v) for v in bbox]
    pad_x = max(1, int((x2 - x1) * 0.15))
    pad_y = max(1, int((y2 - y1) * 0.15))

    crop = img_bgr[
        max(0, y1 + pad_y): min(img_bgr.shape[0], y2 - pad_y),
        max(0, x1 + pad_x): min(img_bgr.shape[1], x2 - pad_x),
    ]
    if crop.size == 0:
        return 0.0

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, (0, 40, 40), (12, 255, 255))
    mask2 = cv2.inRange(hsv, (165, 40, 40), (180, 255, 255))
    red_mask = mask1 | mask2

    return float(np.mean(red_mask > 0))


def is_vertical(dets: list[dict[str, Any]], img_w: int, img_h: int) -> dict[str, Any]:
    """
    Evaluate if detected digits form a vertical column rather than a horizontal meter row.
    Horizontal meter rows require width_span > height_span.
    """
    if len(dets) < 2:
        return {"vertical": False}

    xs = [d["center_x"] / img_w for d in dets]
    ys = [d["center_y"] / img_h for d in dets]

    width_span = max(xs) - min(xs)
    height_span = max(ys) - min(ys)

    is_vert = (height_span >= width_span * 0.8) or (width_span <= 0.05 and height_span >= 0.08)
    return {"vertical": is_vert}


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """
    Compute 95% Wilson Score Interval for binomial proportion.
    More reliable for small sample sizes (n < 30) than standard normal approximation.
    Returns (lower_bound_pct, upper_bound_pct) in percentage range [0.0, 100.0].
    """
    if total <= 0:
        return 0.0, 0.0
    z = 1.95996  # for 95% CI
    p = successes / total
    denom = 1.0 + (z ** 2) / total
    center = (p + (z ** 2) / (2.0 * total)) / denom
    spread = (z * math.sqrt((p * (1.0 - p) / total) + (z ** 2) / (4.0 * (total ** 2)))) / denom
    lower = max(0.0, (center - spread) * 100.0)
    upper = min(100.0, (center + spread) * 100.0)
    return round(lower, 1), round(upper, 1)
