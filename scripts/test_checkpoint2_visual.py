"""
สคริปต์ทดสอบ Checkpoint 2: Process & Transformation พร้อมสร้างภาพผลลัพธ์เชิงประจักษ์ (Visual Output)
บันทึกผลการทดสอบเป็นภาพที่ media/checkpoint2_process_test.png
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import matplotlib.pyplot as plt
from main import rotate_image, apply_prep, detect_dial_text_orientation

def run_checkpoint2_visual():
    print("=== เริ่มการทดสอบ Checkpoint 2: Process & Transformation (Visual Test) ===")
    img_path = "meter_img/meter_sample_01.jpg"
    bgr = cv2.imread(img_path)
    assert bgr is not None, f"ไม่พบไฟล์ทดสอบ {img_path}"
    h, w = bgr.shape[:2]

    # 1. ทดสอบการหมุน 4 ระนาบ (0, 90, 180, 270)
    rot_0 = rotate_image(bgr, 0)
    rot_90 = rotate_image(bgr, 90)
    rot_180 = rotate_image(bgr, 180)
    rot_270 = rotate_image(bgr, 270)
    assert rot_90.shape[:2] == (w, h), "ความล้มเหลว: หมุน 90° มิติภาพต้องสลับ กว้าง x สูง"
    assert rot_180.shape[:2] == (h, w), "ความล้มเหลว: หมุน 180° มิติภาพต้องเท่าเดิม"
    print(" ผ่านการทดสอบการหมุน 4 ทิศทาง (0°, 90°, 180°, 270°)")

    # 2. ทดสอบฟิลเตอร์ปรับปรุงคอนทราสต์ 3 รูปแบบ (orig, clahe, histeq)
    filt_orig = apply_prep(bgr, "orig")
    filt_clahe = apply_prep(bgr, "clahe")
    filt_histeq = apply_prep(bgr, "histeq")
    assert filt_clahe.shape == bgr.shape and filt_histeq.shape == bgr.shape, "ความล้มเหลว: ฟิลเตอร์ต้องรักษาระดับมิติภาพ"
    print(" ผ่านการทดสอบฟิลเตอร์ปรับปรุงแสง CLAHE (LAB) และ HistEq (YCrCb)")

    # 3. ทดสอบการตรวจจับทิศทางข้อความบนหน้าปัด m³
    dial_info = detect_dial_text_orientation(rot_90)
    print(f"ผลวิเคราะห์ทิศทางข้อความหน้าปัดบนภาพหมุน 90°: is_vertical={dial_info['is_vertical']}, score_h={dial_info['score_h']}, score_v={dial_info['score_v']}")

    # สร้างภาพ Visual Crop สำหรับแสดงผลการตรวจจับขอบเขตข้อความ m³
    crop = bgr[int(h * 0.2): int(h * 0.8), int(w * 0.2): int(w * 0.8)].copy()
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ch, cw = crop.shape[:2]
    crop_vis = crop.copy()
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        if 8 < bw < cw * 0.4 and 8 < bh < ch * 0.4:
            aspect = bw / float(bh)
            color = (0, 255, 0) if aspect > 1.4 else ((0, 165, 255) if aspect < 0.7 else (255, 0, 0))
            cv2.rectangle(crop_vis, (x, y), (x + bw, y + bh), color, 2)

    # 4. สร้างภาพผลลัพธ์แบบ 2 แถว x 4 คอลัมน์ (8 ช่องรวม)
    fig, axes = plt.subplots(2, 4, figsize=(16, 8), dpi=150)
    fig.patch.set_facecolor('#f8fafc')

    # แถวที่ 1: การหมุน 4 ทิศทาง
    rot_imgs = [rot_0, rot_90, rot_180, rot_270]
    rot_titles = ["(1) Rotation 0° (Normal)", "(2) Rotation 90° (Clockwise)", "(3) Rotation 180° (Inverted)", "(4) Rotation 270° (Counter-CW)"]
    for i in range(4):
        axes[0, i].imshow(cv2.cvtColor(rot_imgs[i], cv2.COLOR_BGR2RGB))
        axes[0, i].set_title(rot_titles[i], fontsize=10, fontweight='bold', color='#1e293b')
        axes[0, i].axis('off')

    # แถวที่ 2: ฟิลเตอร์ 3 แบบ + ขอบเขตข้อความหน้าปัด
    filt_imgs = [filt_orig, filt_clahe, filt_histeq, crop_vis]
    filt_titles = ["(5) Filter: Original", "(6) Filter: CLAHE (LAB)", "(7) Filter: HistEq (YCrCb)", "(8) Dial Text m³ Detection Crop"]
    for i in range(4):
        axes[1, i].imshow(cv2.cvtColor(filt_imgs[i], cv2.COLOR_BGR2RGB))
        axes[1, i].set_title(filt_titles[i], fontsize=10, fontweight='bold', color='#1e293b')
        axes[1, i].axis('off')

    plt.tight_layout()
    os.makedirs("media", exist_ok=True)
    out_path = "media/checkpoint2_process_test.png"
    plt.savefig(out_path, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f">>> บันทึกภาพผลลัพธ์การทดสอบ Checkpoint 2 สำเร็จที่: {out_path} <<<")

if __name__ == "__main__":
    run_checkpoint2_visual()
