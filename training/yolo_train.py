"""Fine-tune YOLO26 on the meter-digit dataset.

Usage:
    python training/yolo_train.py                            # defaults
    python training/yolo_train.py --model yolo26s.pt --epochs 80
    python training/yolo_train.py --resume                   # resume last run

The YOLO26 official recipe (MuSGD optimizer, close_mosaic, end2end head,
STAL for small objects) is enabled by the ultralytics defaults for this
model family. Train at the same model size you will deploy.
"""

import argparse
from pathlib import Path

from ultralytics import YOLO

BASE = Path(__file__).resolve().parent.parent
DEFAULT_DATA = BASE / "training" / "data.yaml"

# Per-size starting LR from the official YOLO26 COCO recipe (fine-tune
# schedules typically need lower values; zero means "use model default").
LR0_BY_SIZE = {"n": 0.0054, "s": 0.00038, "m": 0.00038, "l": 0.00038, "x": 0.00038}


def parse_args():
    p = argparse.ArgumentParser(description="Fine-tune YOLO26 on meter digits")
    p.add_argument("--data", type=Path, default=DEFAULT_DATA)
    p.add_argument("--model", default="yolo26n.pt",
                   help="pretrained weights to start from, e.g. yolo26n.pt / yolo26s.pt")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=-1, help="-1 = auto")
    p.add_argument("--name", default="meter_digits", help="experiment name (under runs/detect/)")
    p.add_argument("--lr0", type=float, default=None,
                   help="override initial LR; default per-size value if omitted")
    p.add_argument("--device", default=None, help="cuda:0 / cpu; auto if omitted")
    p.add_argument("--patience", type=int, default=30, help="early-stop patience")
    p.add_argument("--resume", action="store_true", help="resume the latest run")
    return p.parse_args()


def main():
    args = parse_args()

    if not args.data.exists():
        raise SystemExit(f"ไม่พบ data.yaml ที่ {args.data} - ตรวจสอบว่าสร้าง dataset แล้ว")

    model = YOLO(args.model)

    if args.resume:
        results = model.train(resume=True, name=args.name)
    else:
        size = args.model.lower().split("yolo26")[-1][0]  # n/s/m/l/x
        lr0 = args.lr0 if args.lr0 is not None else LR0_BY_SIZE.get(size)
        kwargs = dict(
            data=str(args.data),
            epochs=args.epochs,
            imgsz=args.imgsz,
            name=args.name,
            patience=args.patience,
            close_mosaic=10,
            lr0=lr0,
            device=args.device or "",
        )
        if args.batch > 0:
            kwargs["batch"] = args.batch
        results = model.train(**kwargs)

    # Evaluate the best weights on the validation split.
    best = Path(model.trainer.best) if model.trainer else None
    if best and best.exists():
        best_model = YOLO(str(best))
        metrics = best_model.val(data=str(args.data), device=args.device or "")
        print("\n===== ผลการประเมินบน val set =====")
        print(f"mAP@0.5     : {metrics.box.map50:.4f}")
        print(f"mAP@0.5:0.95: {metrics.box.map:.4f}")
        print(f"Precision   : {metrics.box.mp:.4f}")
        print(f"Recall      : {metrics.box.mr:.4f}")
        print(f"บันทึก best weights ไว้ที่: {best}")
    return results


if __name__ == "__main__":
    main()