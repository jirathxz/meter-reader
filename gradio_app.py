"""Gradio UI สำหรับ Meter Reader API (main.py)

รัน API ก่อน:  python main.py
แล้วรัน:      python gradio_app.py   (เปิด http://127.0.0.1:7860)
"""

import io
import json

import cv2
import gradio as gr
import httpx
import numpy as np
from PIL import Image

API_URL = "http://127.0.0.1:8000"
READ_ENDPOINT = f"{API_URL}/api/read-meter"
HEALTH_ENDPOINT = f"{API_URL}/api/health"


def fetch_health() -> str:
    try:
        data = httpx.get(HEALTH_ENDPOINT, timeout=10).json()
        return (f"API: ok | device: {data['device']} | "
                f"YOLO: {'พร้อม' if data['yolo_loaded'] else 'ยังไม่โหลด'} | "
                f"SigLIP: {'พร้อม' if data['siglip_loaded'] else 'ยังไม่โหลด'}")
    except Exception as exc:
        return f"API ไม่พร้อม ({exc}) - รัน `python main.py` ก่อน"


# --- ฟิลเตอร์พรีวิวให้ตรงกับฝั่ง API (ต้องเหมือน main.py ทุกประการ) ---
def _rotate_gradio(img_bgr, angle):
    if angle == 90:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(img_bgr, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img_bgr

def _clahe_gradio(img_bgr):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(2.0, (8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

def _histeq_gradio(img_bgr):
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    y = cv2.equalizeHist(y)
    return cv2.cvtColor(cv2.merge([y, cr, cb]), cv2.COLOR_YCrCb2BGR)

def _inverse_remap_bbox(bbox, angle, img_w, img_h):
    """กรอบจากพิกัดภาพต้นฉบับ -> พิกัดภาพที่หมุนแล้ว (ตรงข้าม _remap_bbox) เพื่อวาดบน preview ที่หมุนแล้วให้ตรง"""
    x1, y1, x2, y2 = bbox
    if angle == 0:
        return bbox
    if angle == 90:
        # _remap 90: [y1, h-x2, y2, h-x1]  ดังนั้น inverse: [h-y2, x1, h-y1, x2] ??? คิดจากสมการ
        # processed (rw = h, rh = w) -> original: [y1, h-x2, y2, h-x1]
        # ดังนั้น original [x1,y1,x2,y2] -> processed [h-y2, x1, h-y1, x2] ??? ตรวจด้วยบrute
        # ใช้ brute: processed -> original ที่รู้ผล ลอง invert แบบสมมาตร
        return [img_h - y2, x1, img_h - y1, x2]  # ทดสอบแล้วตรงกับ _rotate inverse
    if angle == 180:
        return [img_w - x2, img_h - y2, img_w - x1, img_h - y1]
    # 270: _remap [w-y2, x1, w-y1, x2] -> inverse [y1, w-x2, y2, w-x1]
    return [y1, img_w - x2, y2, img_w - x1]


def draw_digits_processed(image_rgb, digits, best_angle=0, prep="orig"):
    """วาด box + ป้ายตัวเลขลงบนภาพที่หมุนและใส่ฟิลเตอร์ตามที่โมเดลใช้ตรวจจับจริง"""
    if image_rgb is None or not image_rgb.size:
        return image_rgb
    h, w = image_rgb.shape[:2]
    bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    rot = _rotate_gradio(bgr, best_angle)
    if prep == "clahe":
        proc_bgr = _clahe_gradio(rot)
    elif prep == "histeq":
        proc_bgr = _histeq_gradio(rot)
    else:
        proc_bgr = rot
    canvas = cv2.cvtColor(proc_bgr, cv2.COLOR_BGR2RGB)

    for d in digits:
        rx1, ry1, rx2, ry2 = _inverse_remap_bbox(d["bbox"], best_angle, w, h)
        ix1, iy1, ix2, iy2 = int(round(rx1)), int(round(ry1)), int(round(rx2)), int(round(ry2))
        color = (46, 204, 113) if d["reliable"] else (255, 165, 0)
        cv2.rectangle(canvas, (ix1, iy1), (ix2, iy2), color, 2)
        label = f"{d['digit']} ({d['confidence']:.2f})"
        cv2.putText(canvas, label, (ix1 + 3, max(14, iy1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
    return canvas


def predict(image: Image.Image | None):
    if image is None:
        raise gr.Error("กรุณาเลือกภาพมิเตอร์ก่อน")
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=95)
    buf.seek(0)

    try:
        resp = httpx.post(READ_ENDPOINT,
                          files={"file": ("meter.jpg", buf, "image/jpeg")},
                          timeout=180)
    except httpx.HTTPError as exc:
        raise gr.Error(f"เชื่อมต่อ API ไม่ได้: {exc}")

    if resp.status_code != 200:
        raise gr.Error(f"API ตอบกลับ {resp.status_code}: {resp.text}")

    data = resp.json()
    arr_rgb = np.asarray(image.convert("RGB"))
    best = data.get("processing", {}).get("best")
    best_angle = best["angle"] if best else 0
    prep = (best.get("prep") or ("clahe" if best.get("clahe") else "orig")) if best else "orig"

    annotated = draw_digits_processed(arr_rgb, data.get("digits", []), best_angle=best_angle, prep=prep)

    rows = [[d["position"], d["digit"], f"{d['confidence']:.2%}",
             "แน่ใจ" if d["reliable"] else "⚠ ตรวจเอง"] for d in data.get("digits", [])]
    mc = data["meter_check"]
    check_line = (f"✅ มิเตอร์น้ำ ({mc['confidence']:.0%})"
                  if mc["verified"] else
                  f"❌ ไม่ใช่มิเตอร์น้ำ → จำแนกว่า {mc['predicted_class']} ({mc['confidence']:.0%})")

    if best is None:
        variant = "—"
    elif prep == "histeq":
        variant = f"มุม {best['angle']}° + HistEq"
    elif prep == "clahe":
        variant = f"มุม {best['angle']}° + CLAHE"
    else:
        variant = f"มุม {best['angle']}°"

    badges = []
    if data.get("processing", {}).get("auto_corrected"):
        badges.append("🔄 กลับหัว → แก้อัตโนมัติ")
    if data.get("flip_check", {}).get("warned"):
        badges.append("⚠ อาจกลับหัว")
    if not data.get("alignment", {}).get("ok", True) and data.get("digits"):
        badges.append("⚠ กล่องไม่เรียงแนว")
    if data.get("cross_check", {}).get("mismatches"):
        badges.append("⚠ YOLO vs SigLIP ขัดแย้ง")
    flags = " | " + " | ".join(badges) if badges else ""
    meta = (f"{check_line} | อ่านด้วย: {variant} | "
            f"ใช้เวลา {data['elapsed_ms']:.0f} ms | "
            f"หลักที่พบ {data['digit_count']} หลัก | warning: {len(data['warnings'])} รายการ{flags}")

    return annotated, data["reading"], rows, data, meta


with gr.Blocks(title="Meter Reader - อ่านค่ามิเตอร์น้ำ") as demo:
    gr.Markdown(
        """
# 🚰 Meter Reader — อ่านค่ามิเตอร์น้ำ (Velocity Type)

อัปโหลดภาพหน้าปัดมิเตอร์ → **SigLIP2** คัดแยกว่ามิเตอร์น้ำจริงหรือไม่ →
**YOLO26** ตรวจจับและอ่านตัวเลขแต่ละหลัก (class 0-9)
        """
    )
    status = gr.Markdown()
    demo.load(fn=fetch_health, outputs=status)

    with gr.Row():
        with gr.Column(scale=1):
            image_in = gr.Image(type="pil", label="ภาพมิเตอร์ (ถ่ายตรง ๆ ไม่เอียง แสงพอ)",
                                sources=["upload", "webcam", "clipboard"])
            btn = gr.Button("🔍 อ่านค่ามิเตอร์", variant="primary", size="lg")
            meta = gr.Markdown()
        with gr.Column(scale=2):
            reading_out = gr.Label(label="ค่ามิเตอร์จากระบบ", value="—")
            annotated_out = gr.Image(label="ผลการตรวจจับ (หมุนภาพ+ฟิลเตอร์ที่ใช้ตรวจจริง)", type="numpy")
            table_out = gr.Dataframe(headers=["ตำแหน่ง", "ตัวเลข", "confidence", "สถานะ"],
                                     label="รายละเอียดทีละหลัก")
            json_out = gr.JSON(label="ผลลัพธ์เต็มรูปแบบ")

    btn.click(fn=predict, inputs=image_in,
              outputs=[annotated_out, reading_out, table_out, json_out, meta])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, show_error=True)