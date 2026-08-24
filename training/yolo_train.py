"""training/yolo_train.py — สคริปต์เทรน YOLO26 ตรงกับ TUTORIAL.md 1.2.1–1.2.2

รันบน Colab/Kaggle ที่มี GPU (Tesla T4 แนะนำ) หรือเครื่องที่มี CUDA
ตรงกับโค้ดใน TUTORIAL.md ทุกบรรทัด (yolo26n.pt, yolo26 dataset, พารามิเตอร์ครบ)

Usage:
    python training/yolo_train.py
"""

from roboflow import Roboflow
from ultralytics import YOLO

# 1.2.1 — ดาวน์โหลดชุดข้อมูลจาก Roboflow (yolo26)
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("watermeter-jvlgr").project("utility-meter-reading-dataset-for-automatic-reading-yolo")
version = project.version(1)
dataset = version.download("yolo26")

# 1.2.2 — กำหนดพารามิเตอร์และเริ่มกระบวนการเทรน (YOLO26 Nano)
model = YOLO("yolo26n.pt")
results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=100,                # จำนวนรอบการฝึกฝนสูงสุด
    patience=30,               # กลไกหยุดอัตโนมัติหากค่า mAP ไม่ดีขึ้น
    imgsz=640,                 # ความละเอียดของภาพ
    batch=64,                  # ขนาดชุดข้อมูลต่อรอบ (Nano ใช้ VRAM น้อย เพิ่ม batch ได้)
    amp=True,                  # ใช้ Mixed Precision (FP16) ลดการใช้ VRAM
    optimizer="AdamW",         # อัลกอริทึมสำหรับปรับค่าน้ำหนัก
    lr0=0.001,                 # อัตราการเรียนรู้เริ่มต้น
    mosaic=1.0,                # รวม 4 ภาพเพื่อสร้างความหลากหลาย
    mixup=0.15,                # ซ้อนทับภาพป้องกัน Overfitting
    degrees=15.0,              # หมุนภาพชดเชยมุมเอียง
    hsv_v=0.4,                 # ปรับความสว่างจำลองสภาพแสงน้อย
)

# ประเมินบนชุด validation (ตรงกับ TUTORIAL.md)
metrics = model.val()
print(f"mAP50: {metrics.box.map50:.4f}, mAP50-95: {metrics.box.map:.4f}")
print(f"best.pt อยู่ที่ runs/detect/train/weights/best.pt — คัดลอกไป weights/MeterOCR.pt แล้วรันระบบได้ทันที")
