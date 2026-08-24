# Meter Reader — ระบบอ่านเลขมิเตอร์น้ำอัตโนมัติ (Velocity Type)

ระบบอ่านเลขจากมิเตอร์น้ำแบบใบพัด (mechanical counter) จากภาพถ่ายด้วย AI ทำงานบน **Python 3.11**
1. **SigLIP2**: คัดแยกก่อนว่าภาพเป็นมิเตอร์น้ำจริงหรือไม่ (Zero-shot classification)
2. **YOLO26**: ตรวจจับและอ่านตัวเลขแต่ละหลัก (class 0–9) ในโมเดลเดียว
3. **Multi-orientation & Safety Guards**: ค้นหา 4 ทิศ × 3 ฟิลเตอร์ ป้องกันอ่านกลับหัว 180° และกรองแถวแนวตั้ง
4. **FastAPI & Gradio**: ให้บริการผ่าน REST API และหน้าเว็บ UI ที่ใช้งานง่าย

```
[Gradio UI :7860] --HTTP--> [FastAPI :8000  (main.py)]
                              ├─ SigLIP2 : ภาพนี้เป็นมิเตอร์น้ำหรือไม่? (คัดแยกก่อน)
                              │    ไม่ใช่ → ตัดทิ้ง (ไม่ไปอ่านตัวเลข)
                              └─ YOLO26 : อ่านตัวเลข (class 0-9)
                                   ├─ ทดลอง 4 ทิศ (0/90/180/270) × 3 ฟิลเตอร์ (orig/CLAHE/HistEq)
                                   └─ เลือกชุดที่คะแนนรวมสูงสุด → เรียงซ้ายไปขวา → ค่าเลข
```

---

## 📁 โครงสร้างโปรเจกต์ (Pure Functional Pipeline)

```
meter-reader/
├── main.py            # API หลัก (FastAPI) และ Pipeline การอ่านมิเตอร์ (Pure Functions)
├── gradio_app.py      # หน้าเว็บ UI (Gradio) สำหรับทดสอบระบบ
├── TUTORIAL.md        # คู่มือสอนเขียนระบบทีละขั้นตอน (Step-by-Step Guide)
├── requirements.txt   # รายการ Library dependencies
├── meter_img/         # ตัวอย่างภาพมิเตอร์น้ำสำหรับทดสอบ
└── weights/           # น้ำหนักโมเดล YOLO (MeterOCR.pt)
```

---

## 🛠️ การติดตั้งสภาพแวดล้อมด้วย `uv` (Python 3.11)

> **ข้อกำหนดระบบ:** แนะนำ **Python 3.11** (รองรับ Python 3.10 – 3.12) และใช้เครื่องมือ **uv** เพื่อความรวดเร็ว

### 1. สร้าง Virtual Environment ด้วย Python 3.11
```powershell
uv venv --python 3.11
```

เปิดใช้งาน Virtual Environment:
* **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
* **Windows (CMD):** `.venv\Scripts\activate.bat`
* **macOS / Linux:** `source .venv/bin/activate`

### 2. ติดตั้ง Dependencies
```powershell
uv pip install -r requirements.txt
```

---

## 🚀 การรันระบบ (Running the Application)

### เทอร์มินัลที่ 1 — รัน FastAPI Backend:
```powershell
uv run python main.py
```
* **API Documentation (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### เทอร์มินัลที่ 2 — รัน Gradio Web UI:
```powershell
uv run python gradio_app.py
```
* **Web UI URL:** [http://127.0.0.1:7860](http://127.0.0.1:7860)

### ทดสอบส่งภาพผ่าน cURL:
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/read-meter -F "file=@meter_img/Water+meter.jpg"
```

---

## 📦 รูปแบบผลลัพธ์ของ API (Response Payload)

```json
{
  "reading": "05715",
  "digits": [
    {"position": 1, "digit": 0, "confidence": 0.8921, "bbox": [120, 45, 150, 95], "reliable": true},
    {"position": 2, "digit": 5, "confidence": 0.9412, "bbox": [152, 45, 182, 95], "reliable": true},
    {"position": 3, "digit": 7, "confidence": 0.9105, "bbox": [184, 45, 214, 95], "reliable": true},
    {"position": 4, "digit": 1, "confidence": 0.8876, "bbox": [216, 45, 246, 95], "reliable": true},
    {"position": 5, "digit": 5, "confidence": 0.9234, "bbox": [248, 45, 278, 95], "reliable": true}
  ],
  "mean_confidence": 0.911,
  "meter_check": {
    "verified": true,
    "predicted_class": "water meter",
    "confidence": 0.8712
  },
  "processing": {
    "best": {
      "angle": 0,
      "prep": "orig",
      "clahe": false
    }
  },
  "warnings": [
    "หลักแรกเป็น 0 — อาจเกินมา 1 หลัก"
  ],
  "elapsed_ms": 135.2
}
```

*กรณีไม่ใช่ภาพมิเตอร์น้ำ:* คืนค่า `reading: ""` และ `meter_check.verified: false` พร้อมระบุประเภทวัตถุที่ตรวจพบ

---

## 💡 ระบบความปลอดภัยและความแม่นยำ (Safety Features)

1. **คัดแยกภาพแปลกปลอม (SigLIP2 Zero-shot)**: กรองภาพที่ไม่ใช่มิเตอร์น้ำทิ้งทันที
2. **ค้นหา 4 ทิศ × 3 ฟิลเตอร์**: รองรับภาพถ่ายตะแคง (0°, 90°, 180°, 270°) และภาพแสงน้อย/เลขจางด้วย CLAHE และ HistEq
3. **ป้องกันการอ่านเลขกลับหัว 180° (`flip_guard` & `red_ratio`)**:
   - ใช้หลักการสะท้อนกระจกตรวจสอบคู่ตัวเลขสมมาตร ($6 \leftrightarrow 9, 2 \leftrightarrow 5, 0, 1, 8$)
   - ตรวจจับสัดส่วนสีแดงของหลักทศนิยม ซึ่งต้องอยู่ขวาสุดของหน้าปัดมิเตอร์เสมอ
4. **กรองคอลัมน์แนวตั้ง (`is_vertical`)**: วัด $\text{width\_span}$ vs $\text{height\_span}$ เพื่อตัดตัวเลขวันที่/ซีเรียลนัมเบอร์ที่เป็นแนวดิ่ง
5. **Cross-check หลักที่ความมั่นใจต่ำ**: ใช้ SigLIP2 ช่วยตรวจทานหลักที่ค่า confidence ต่ำกว่า 0.60