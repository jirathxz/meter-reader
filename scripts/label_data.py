"""Helpers: capture meter photos + split dataset into train/val.

YOLO อ่านตัวเลขในตัวเดียว (class = ค่าของตัวเลข 0-9) — annotate box รอบ
ตัวเลขแต่ละหลัก แล้วใส่ class เป็นค่าของตัวเลขนั้น

Subcommands:
    photos  --out training/raw [--cam 0]
            Opens the webcam. Press SPACE to save a frame, Q to quit.
            Ideally photograph each meter from several angles/lighting.

    split   --raw training/raw --out training/dataset [--val 0.2] [--seed 42]
            Copies matching image (.jpg/.jpeg/.png) + label (.txt) pairs into
            training/dataset/images/{train,val} and labels/{train,val}.
            Existing .txt with YOLO format lines:  "class cx cy w h" (0-1).

    label_hint
            Prints the annotation workflow (YOLO label format + tool options).
"""

import argparse
import random
import shutil
import time
from pathlib import Path

import cv2

BASE = Path(__file__).resolve().parent.parent
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
LABEL_EXT = ".txt"


def cmd_photos(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(args.cam)
    if not cap.isOpened():
        raise SystemExit(f"เปิดกล้อง {args.cam} ไม่ได้")
    print(f"กล้องพร้อม - บันทึกไปที่ {out}  |  SPACE = บันทึก, Q = ออก")
    saves, last = 0, time.time()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            preview = cv2.putText(
                frame.copy(), f"saved: {saves}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2,
            )
            cv2.imshow("capture", preview)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord(" "):
                name = out / f"meter_{time.strftime('%Y%m%d_%H%M%S')}_{saves:03d}.jpg"
                cv2.imwrite(str(name), frame)
                saves += 1
                print(f"บันทึก: {name.name}  (หยุด 0.5 วิ กันภาพซ้ำ)")
                time.sleep(0.5)
    finally:
        cap.release()
        cv2.destroyAllWindows()
    print(f"จบ - บันทึกทั้งหมด {saves} ภาพ ที่ {out}")


def cmd_split(args):
    raw, out = Path(args.raw), Path(args.out)
    if not raw.exists():
        raise SystemExit(f"ไม่พบ {raw} - ไปเก็บภาพด้วยคำสั่ง photos ก่อน")
    images = sorted(p for p in raw.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not images:
        raise SystemExit(f"ไม่พบรูปภาพใน {raw}")
    pairs = []
    for img in images:
        lbl = img.with_suffix(LABEL_EXT)
        if not lbl.exists():
            print(f"!! {img.name} ไม่มี label (.txt) ข้ามไป")
            continue
        _check_yolo_label(lbl)
        pairs.append((img, lbl))
    missing = len(images) - len(pairs)
    if not pairs:
        raise SystemExit("ไม่มีคู่ภาพ+label เลย - annotate ก่อน (ดู label_hint)")
    rng = random.Random(args.seed)
    rng.shuffle(pairs)
    n_val = max(1, round(len(pairs) * args.val))
    val_set, train_set = pairs[:n_val], pairs[n_val:]

    for split_name, items in (("val", val_set), ("train", train_set)):
        img_dir = out / "images" / split_name
        lbl_dir = out / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)
        for img, lbl in items:
            shutil.copy2(img, img_dir / img.name)
            shutil.copy2(lbl, lbl_dir / lbl.name)

    print(f"แยกข้อมูล: train {len(train_set)} / val {len(val_set)}  (ข้าม {missing} ภาพ)"
          f"\ndataset พร้อมที่: {out}")
    print("จากนั้นรัน: python training/yolo_train.py")


def _check_yolo_label(lbl: Path, warn_small: float = 0.05):
    """Basic sanity check on YOLO label lines; warn on tiny/out-of-range boxes."""
    for line in lbl.read_text(encoding="utf-8").strip().splitlines():
        parts = line.split()
        if len(parts) != 5:
            raise SystemExit(f"{lbl.name}: บรรทัด '{line}' ไม่ใช่ YOLO format (class cx cy w h)")
        cls, cx, cy, w, h = parts
        try:
            cx, cy, w, h = float(cx), float(cy), float(w), float(h)
        except ValueError:
            raise SystemExit(f"{lbl.name}: พิกัดไม่ใช่ตัวเลขในบรรทัด '{line}'")
        if not (0 <= cx <= 1 and 0 <= cy <= 1):
            raise SystemExit(f"{lbl.name}: cx/cy ต้องอยู่ระหว่าง 0-1 ({line})")
        if cls not in map(str, range(10)):
            raise SystemExit(f"{lbl.name}: class '{cls}' ไม่ใช่เลข 0-9 - annotate ด้วยค่าของตัวเลขนั้น ({line})")
        if w < warn_small:
            print(f"!! {lbl.name}: box แคบมาก (w={w:.3f}) - ตัวเลขติดกัน? ตรวจสอบใหม่")


def cmd_label_hint(_args):
    print(
        """
== วิธี annotate ตัวเลขมิเตอร์ ==

1. เก็บภาพ:      python scripts/label_data.py photos
2. annotate box รอบตัวเลขแต่ละหลัก แล้วใส่ class = ค่าของตัวเลขนั้น (0-9):
     - ภาพมิเตอร์เลข "002486" => box รอบแต่ละหลัก 6 กล่อง
       class 0, 0, 2, 4, 8, 6 ตามลำดับ
     - เครื่องมือที่ใช้ได้:
         Label Studio  (export YOLO format)
         Roboflow  (export YOLO v5/v8 format)  https://roboflow.com
         LabelImg  (YOLO format)  https://github.com/HumanSignal/labelImg
         หรือยูทิลิตี้ built-in ของ ultralytics:
             yolo annotate data=<path>  (เปิดหน้า web annotation)

3. ไฟล์ label .txt แต่ละบรรทัด = 1 ตัวเลข:
        0 0.412 0.731 0.022 0.045
       (class cx cy w h — ค่าปกติ 0-1 เทียบกับภาพ)
4. แยก train/val: python scripts/label_data.py split
5. เทรน:          python training/yolo_train.py

เคล็ดลับคุณภาพ: ถ่ายหลายมุม/หลายแสง, ตัวเลขไม่เบลอ, ทุก class 0-9 ควรมี
ตัวอย่างครบ ถ้าเลขกำลังหมุนเปลี่ยนค่า ให้ annotate ด้วยค่า "ก่อนเปลี่ยน"
หรือตัดภาพนั้นทิ้ง
        """
    )


def main():
    p = argparse.ArgumentParser(description="Meter dataset helpers")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("photos", help="capture meter photos from webcam")
    sp.add_argument("--out", default=str(BASE / "training" / "raw"))
    sp.add_argument("--cam", type=int, default=0)
    sp.set_defaults(fn=cmd_photos)

    sp = sub.add_parser("split", help="split raw images+labels into train/val")
    sp.add_argument("--raw", default=str(BASE / "training" / "raw"))
    sp.add_argument("--out", default=str(BASE / "training" / "dataset"))
    sp.add_argument("--val", type=float, default=0.2)
    sp.add_argument("--seed", type=int, default=42)
    sp.set_defaults(fn=cmd_split)

    sp = sub.add_parser("label_hint", help="print annotation workflow")
    sp.set_defaults(fn=cmd_label_hint)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()