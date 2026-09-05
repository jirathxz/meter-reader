"""
eval_yolo_metrics.py — Calculate YOLO Detection Metrics on Test Dataset
Computes Precision, Recall, F1-Score, mAP@50, and mAP@50:95 for the digit detector.
Outputs research-grade summary table and saves results to reviews/yolo_metrics.json.
"""
from __future__ import annotations

import json
from pathlib import Path
import torch
from ultralytics import YOLO

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
WEIGHTS_PATH = Path(__file__).parent / "weights" / "MeterOCR.pt"
DATA_YAML = Path(__file__).parent / "meter_dataset.yaml"
OUTPUT_JSON = Path(__file__).parent / "reviews" / "yolo_metrics.json"


def evaluate_yolo():
    print(f"Evaluating YOLO model: {WEIGHTS_PATH}")
    print(f"Dataset config: {DATA_YAML}")
    print(f"Device: {DEVICE}")

    model = YOLO(str(WEIGHTS_PATH))

    # Run validation on the test split
    metrics = model.val(
        data=str(DATA_YAML),
        split="test",
        imgsz=960,
        conf=0.35,
        iou=0.45,
        device=DEVICE,
        verbose=True,
    )

    mp = float(metrics.box.mp)
    mr = float(metrics.box.mr)
    map50 = float(metrics.box.map50)
    map50_95 = float(metrics.box.map)
    f1 = float(2 * (mp * mr) / (mp + mr)) if (mp + mr) > 0 else 0.0

    class_names = metrics.names
    per_class = {}
    if hasattr(metrics.box, "p") and len(metrics.box.p) > 0:
        for idx, cls_id in enumerate(metrics.box.ap_class_index):
            name = class_names[cls_id]
            p = float(metrics.box.p[idx])
            r = float(metrics.box.r[idx])
            ap50 = float(metrics.box.ap50[idx])
            ap = float(metrics.box.ap[idx])
            f1_c = float(2 * (p * r) / (p + r)) if (p + r) > 0 else 0.0
            per_class[name] = {
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1": round(f1_c, 4),
                "map50": round(ap50, 4),
                "map50_95": round(ap, 4),
            }

    summary = {
        "model": "MeterOCR.pt",
        "dataset": "utility-meter-reading-dataset (Roboflow CC BY 4.0)",
        "split": "test (n=194 images)",
        "imgsz": 960,
        "conf_threshold": 0.35,
        "iou_threshold": 0.45,
        "overall_metrics": {
            "precision": round(mp, 4),
            "recall": round(mr, 4),
            "f1_score": round(f1, 4),
            "map50": round(map50, 4),
            "map50_95": round(map50_95, 4),
        },
        "per_class_metrics": per_class,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("YOLO DETECTION METRICS ON TEST DATASET (n=194)")
    print("=" * 60)
    print(f"Precision:  {mp * 100:.2f}%")
    print(f"Recall:     {mr * 100:.2f}%")
    print(f"F1-Score:   {f1 * 100:.2f}%")
    print(f"mAP@50:     {map50 * 100:.2f}%")
    print(f"mAP@50:95:  {map50_95 * 100:.2f}%")
    print("=" * 60)
    print(f"Saved full report to: {OUTPUT_JSON}")
    return summary


if __name__ == "__main__":
    evaluate_yolo()
