"""
สคริปต์ทดสอบ Checkpoint 1: Preprocessing & Gatekeeper พร้อมสร้างภาพผลลัพธ์เชิงประจักษ์ (Visual Output)
บันทึกผลการทดสอบเป็นภาพที่ media/checkpoint1_preprocessing_test.png
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from main import check_water_meter

def run_checkpoint1_visual():
    print("=== เริ่มการทดสอบ Checkpoint 1: Preprocessing & Gatekeeper (Visual Test) ===")
    
    # 1. ทดสอบภาพบวก (Positive Case: ภาพมาตรวัดน้ำจริง)
    pos_path = "meter_img/meter_sample_01.jpg"
    bgr_pos = cv2.imread(pos_path)
    assert bgr_pos is not None, f"ไม่พบไฟล์ทดสอบ {pos_path}"
    rgb_pos = cv2.cvtColor(bgr_pos, cv2.COLOR_BGR2RGB)
    res_pos = check_water_meter(rgb_pos)
    assert res_pos["verified"] is True, "ความล้มเหลว: ภาพมาตรวัดน้ำจริงต้องผ่านการคัดกรอง"
    print(f"Positive Case: verified={res_pos['verified']}, class={res_pos['predicted_class']}, conf={res_pos['confidence']:.4f}")

    # 2. ทดสอบภาพลบ (Negative Case: ภาพสัญญาณรบกวน / วัตถุอื่นที่ไม่ใช่มิเตอร์)
    neg_img = np.zeros((bgr_pos.shape[0], bgr_pos.shape[1], 3), dtype=np.uint8)
    cv2.circle(neg_img, (neg_img.shape[1]//2, neg_img.shape[0]//2), 200, (100, 100, 100), -1)
    cv2.rectangle(neg_img, (100, 100), (neg_img.shape[1]-100, neg_img.shape[0]-100), (60, 60, 60), 10)
    for i in range(10):
        cv2.line(neg_img, (0, i*50), (neg_img.shape[1], i*50), (40, 40, 40), 2)
    rgb_neg = cv2.cvtColor(neg_img, cv2.COLOR_BGR2RGB)
    res_neg = check_water_meter(rgb_neg)
    assert res_neg["verified"] is False, "ความล้มเหลว: ภาพรบกวนต้องถูกคัดกรองทิ้ง"
    print(f"Negative Case: verified={res_neg['verified']}, class={res_neg['predicted_class']}, conf={res_neg['confidence']:.4f}")

    # 3. สร้างภาพแสดงผลลัพธ์เชิงประจักษ์แบบ 2 ฝั่ง (Positive vs Negative Panel)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), dpi=150)
    fig.patch.set_facecolor('#f8fafc')

    # ฝั่งซ้าย: Positive Case
    axes[0].imshow(rgb_pos)
    axes[0].set_title("Positive Case: Valid Water Meter Image", fontsize=12, fontweight='bold', pad=10, color='#1e293b')
    axes[0].axis('off')
    rect1 = patches.Rectangle((20, 20), 460, 140, linewidth=2, edgecolor='#16a34a', facecolor='#dcfce7', alpha=0.9)
    axes[0].add_patch(rect1)
    axes[0].text(35, 55, "[CHECKPOINT 1: PASSED]", fontsize=11, fontweight='bold', color='#15803d')
    axes[0].text(35, 85, "MIME: image/jpeg | Valid RGB 3-Channels", fontsize=9, color='#1e293b')
    axes[0].text(35, 110, f"SigLIP2 Class: '{res_pos['predicted_class']}'", fontsize=9, fontweight='bold', color='#1e293b')
    axes[0].text(35, 135, f"Water Meter Confidence: {res_pos['confidence']:.2%} >= 50.00%", fontsize=9, color='#15803d')

    # ฝั่งขวา: Negative Case
    axes[1].imshow(rgb_neg)
    axes[1].set_title("Negative Case: Non-meter / Corrupted Input", fontsize=12, fontweight='bold', pad=10, color='#1e293b')
    axes[1].axis('off')
    rect2 = patches.Rectangle((20, 20), 460, 140, linewidth=2, edgecolor='#dc2626', facecolor='#fee2e2', alpha=0.9)
    axes[1].add_patch(rect2)
    axes[1].text(35, 55, "[CHECKPOINT 1: REJECTED]", fontsize=11, fontweight='bold', color='#b91c1c')
    axes[1].text(35, 85, "MIME: Checked | Invalid Water Meter Feature", fontsize=9, color='#1e293b')
    axes[1].text(35, 110, f"SigLIP2 Class: '{res_neg['predicted_class']}'", fontsize=9, fontweight='bold', color='#1e293b')
    axes[1].text(35, 135, f"Water Meter Confidence: {res_neg['confidence']:.2%} < 50.00% (Early Exit)", fontsize=9, color='#b91c1c')

    plt.tight_layout()
    os.makedirs("media", exist_ok=True)
    out_path = "media/checkpoint1_preprocessing_test.png"
    plt.savefig(out_path, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f">>> บันทึกภาพผลลัพธ์การทดสอบ Checkpoint 1 สำเร็จที่: {out_path} <<<")

if __name__ == "__main__":
    run_checkpoint1_visual()
