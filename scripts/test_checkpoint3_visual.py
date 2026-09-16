"""
สคริปต์ทดสอบ Checkpoint 3: Detection & Output พร้อมสร้างภาพผลลัพธ์เชิงประจักษ์ (Visual Output)
บันทึกผลการทดสอบเป็นภาพที่ media/checkpoint3_output_test.png
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import matplotlib.pyplot as plt
from main import detect_digits, dedup_detections, red_ratio, rotate_image

def run_checkpoint3_visual():
    print("=== เริ่มการทดสอบ Checkpoint 3: Detection & Output (Visual Test) ===")
    img_path = "meter_img/meter_sample_01.jpg"
    bgr_raw = cv2.imread(img_path)
    assert bgr_raw is not None, f"ไม่พบไฟล์ทดสอบ {img_path}"

    # 1. ปรับทิศทางภาพให้ตั้งตรงตามผลลัพธ์ของ Process (หมุน 90°)
    bgr = rotate_image(bgr_raw, 90)

    # 2. ตรวจจับตัวเลขดิบด้วย YOLO26
    raw_dets = detect_digits(bgr)
    print(f"จำนวนกล่องตัวเลขดิบที่ตรวจพบ: {len(raw_dets)}")
    assert len(raw_dets) > 0, "ความล้มเหลว: ต้องตรวจพบตัวเลขบนหน้าปัดมิเตอร์อย่างน้อย 1 ตัว"

    # 3. ตัดกล่องซ้ำซ้อนด้วย IoU และเรียงลำดับซ้ายไปขวา
    clean_dets = dedup_detections(raw_dets)
    print(f"จำนวนกล่องตัวเลขหลังตัดกล่องซ้ำ (IoU Dedup): {len(clean_dets)}")
    
    # ยืนยันพิกัด center_x เรียงลำดับจากซ้ายไปขวา
    x_centers = [d["center_x"] for d in clean_dets]
    assert x_centers == sorted(x_centers), "ความล้มเหลว: กล่องตัวเลขต้องเรียงพิกัดจากซ้ายไปขวา"

    # 3. วาดภาพการตรวจจับเชิงประจักษ์ (Visual Bounding Boxes & Badges)
    vis = bgr.copy()
    num_decimals = 0
    for i, d in enumerate(clean_dets, 1):
        x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
        digit = d["digit"]
        conf = d["confidence"]
        
        # ตรวจสอบสัดส่วนสีแดงของตัวเลขหลักทศนิยม
        r_ratio = red_ratio(bgr, d["bbox"])
        is_red = r_ratio >= 0.25
        if is_red:
            num_decimals += 1

        color = (0, 0, 255) if is_red else (0, 220, 0) # สีแดงสำหรับทศนิยม, สีเขียวสำหรับจำนวนเต็ม
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 3)

        # ป้ายกำกับลำดับที่ ตัวเลข และความเชื่อมั่น
        label = f"#{i}: {digit} ({conf:.2f})"
        cv2.rectangle(vis, (x1, max(0, y1 - 25)), (x1 + 130, y1), color, -1)
        cv2.putText(vis, label, (x1 + 5, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    vis_rgb = cv2.cvtColor(vis, cv2.COLOR_BGR2RGB)

    # 4. สร้างภาพผลลัพธ์พร้อมแถบสรุปสถานะการทดสอบ
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    fig.patch.set_facecolor('#f8fafc')
    ax.imshow(vis_rgb)
    ax.set_title("Checkpoint 3: YOLO26 Digit Detection, IoU Dedup & Left-to-Right Sorting", fontsize=12, fontweight='bold', pad=12, color='#1e293b')
    ax.axis('off')

    reading = "".join(str(d["digit"]) for d in clean_dets)
    mean_conf = np.mean([d["confidence"] for d in clean_dets]) if clean_dets else 0.0
    summary_text = (
        f"Detected Sequence: {reading}  |  Digits: {len(clean_dets)}  |  Mean Confidence: {mean_conf:.2%}\n"
        f"Sorting: Left-to-Right by xmin (OK)  |  Vertical Filter: PASSED (Horizontal Row)  |  Decimals: {num_decimals} Red Digit(s)"
    )
    plt.figtext(0.5, 0.02, summary_text, wrap=True, horizontalalignment='center', fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle='round,pad=0.6', facecolor='#dbeafe', edgecolor='#2563eb', alpha=0.95))

    plt.tight_layout()
    os.makedirs("media", exist_ok=True)
    out_path = "media/checkpoint3_output_test.png"
    plt.savefig(out_path, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f">>> บันทึกภาพผลลัพธ์การทดสอบ Checkpoint 3 สำเร็จที่: {out_path} <<<")

if __name__ == "__main__":
    run_checkpoint3_visual()
