"""Fine-tune YOLO26 on the meter-digit dataset — แบบเดียวกับสคริปต์ในคู่มือ (Guidebook)

อิงตาม Guidebook/docs/Water_Meter_OCR_Guidebook-Draft.md 1.2.3
รันบน Colab/Kaggle ที่มี GPU (Tesla T4 แนะนำ) หรือเครื่องที่มี CUDA

Usage:
    python training/yolo_train.py
    # หรือระบุพารามิเตอร์เอง:
    #   python training/yolo_train.py --epochs 100 --batch 64 --imgsz 640
"""

import argparse
from pathlib import Path

from ultralytics import YOLO

BASE = Path(__file__).resolve().parent.parent
DEFAULT_DATA = BASE / "training" / "data.yaml"


def parse_args():
    p = argparse.ArgumentParser(description="Fine-tune YOLO26 Nano on meter digits (Guidebook recipe)")
    p.add_argument("--data", type=Path, default=DEFAULT_DATA, help="path to data.yaml")
    p.add_argument("--model", default="yolo26n.pt", help="pretrained weights, e.g. yolo26n.pt")
    p.add_argument("--epochs", type=int, default=100, help="จำนวนรอบการฝึกฝนสูงสุด")
    p.add_argument("--patience", type=int, default=30, help="หยุดอัตโนมัติหาก mAP ไม่ดีขึ้น")
    p.add_argument("--imgsz", type=int, default=640, help="ความละเอียดภาพ")
    p.add_argument("--batch", type=int, default=64, help="ขนาด batch (Nano ใช้ VRAM น้อย เพิ่มได้)")
    p.add_argument("--name", default="train", help="ชื่อ experiment ใต้ runs/detect/")
    return p.parse_args()


def main():
    args = parse_args()

    if not args.data.exists():
        raise SystemExit(f"ไม่พบ {args.data} — ตรวจสอบว่าได้รัน 1.2.1 ดาวน์โหลด dataset แล้ว")

    # โหลดโมเดลฐาน YOLO26 Nano
    model = YOLO(args.model)

    # เทรนตามสูตร Guidebook 1.2.3 — ครบทุกพารามิเตอร์ที่สอนใน TUTORIAL.md
    results = model.train(
        data=str(args.data),
        epochs=args.epochs,
        patience=args.patience,
        imgsz=args.imgsz,
        batch=args.batch,
        amp=True,               # Mixed Precision (FP16) ลด VRAM
        optimizer="AdamW",
        lr0=0.001,
        mosaic=1.0,
        mixup=0.15,
        degrees=15.0,
        hsv_v=0.4,
        name=args.name,
    )

    # ประเมินบนชุด validation
    best = Path(model.trainer.best) if getattr(model, "trainer", None) and getattr(model.trainer, "best", None) else None
    if best and best.exists():
        print(f"\nบันทึก best weights ไว้ที่: {best}")
        print("คัดลอกไป weights/MeterOCR.pt แล้วรันระบบได้ทันที")
        m = YOLO(str(best))
        metrics = m.val(data=str(args.data))
        print(f"mAP50: {metrics.box.map50:.4f}, mAP50-95: {metrics.box.map:.4f}")

    return results


if __name__ == "__main__":
    main()
