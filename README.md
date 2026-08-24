# Meter Reader — อ่านเลขมิเตอร์น้ำอัตโนมัติ (Velocity Type)

ระบบอ่านเลขจากมิเตอร์น้ำแบบใบพัด/อาศัยความเร็วของน้ำ (mechanical counter) จากภาพ
**SigLIP2 คัดแยกก่อนว่าภาพเป็นมิเตอร์น้ำจริงหรือไม่** (เทียบกับมิเตอร์รูปแบบอื่น เช่น
มิเตอร์ไฟ/แก๊ส และสิ่งที่ไม่ใช่มิเตอร์) จากนั้น **YOLO26 อ่านตัวเลข** — หา box รอบตัวเลข
แต่ละหลักพร้อมบอกค่า (class 0–9) ในโมเดลเดียว → เรียงซ้ายไปขวา → ค่าเลข
บริการผ่าน **FastAPI** และมี UI แบบ **Gradio**

```
[Gradio UI :7860] --HTTP--> [FastAPI :8000  (main.py)]
                              ├─ SigLIP2 : ภาพนี้เป็นมิเตอร์น้ำหรือไม่? (คัดแยกก่อน)
                              │    ไม่ใช่ → ตัดทิ้ง (ไม่ไปอ่านตัวเลข)
                              └─ YOLO26 : อ่านตัวเลข (class 0-9)
                                   ├─ ทดลอง 4 ทิศ (0/90/180/270) × 3 ฟิลเตอร์ (orig/CLAHE/HistEq)
                                   └─ เลือกชุดที่คะแนนรวมสูงสุด → เรียงซ้ายไปขวา → ค่าเลข
```

ออกแบบแบบ **OOP modular** เพื่อสื่อการสอน — แยกตามหน้าที่ ชัดเจนแต่ยังเรียกง่าย
`MeterConfig` → `ImageProcessor` → `ModelManager` → `DigitDetector`/`MeterVerifier` → `MeterReader` (`pipeline.py:18`)
ยังคงรันด้วย `python main.py` ไฟล์เดียวได้ (`main.py` เป็น thin facade re-export)

## โครงสร้าง — ไฟล์เดียวจบ (OOP ในไฟล์เดียว)

```
meter-reader/
├── main.py         # ไฟล์เดียวจบ: MeterConfig / ImageProcessor / ModelManager / DigitDetector / MeterVerifier / MeterReader + FastAPI
├── gradio_app.py   # UI (เรียก API) — พรีวิวตรงกับ prep ที่ชนะ (มุม+HistEq)
├── example_oop.py  # ตัวอย่างใช้แบบ OOP/DI สำหรับสอน
├── training/
│   ├── yolo_train.py
│   ├── data.yaml
│   └── dataset/
└── requirements.txt
```
> รวมกลับเป็นไฟล์เดียวดั่งเดิมตามคำขอ — แต่ภายในเป็น OOP แยกคลาสชัดเจน
> เปิด `main.py` อ่านบนลงล่าง: `1)Config → 2)ImageProcessor → 3)ModelManager → 4)DigitDetector → 5)MeterVerifier → 6)MeterReader → 7)FastAPI`

## ติดตั้ง (ใช้ uv — ติดตั้งเร็ว ดาวน์โหลดซ้ำอัตโนมัติผ่าน cache)

```powershell
uv venv --python 3.11
uv pip install -r requirements.txt
```

> ไม่มี uv? ติดตั้งได้จาก https://docs.astral.sh/uv/ (หรือใช้ `python -m venv .venv` +
> `pip install -r requirements.txt` แทนได้)

Model จะโหลดอัตโนมัติครั้งแรกที่ถูกเรียกใช้: `yolo26n.pt` (ultralytics ดาวน์โหลดให้)

## รัน

เทอร์มินัลที่ 1 — API (อยู่ใน `__main__` → uvicorn):
```powershell
python main.py
```
เทอร์มินัลที่ 2 — UI:
```powershell
python gradio_app.py     # เปิด http://127.0.0.1:7860
```

ทดสอบ API ตรง ๆ:
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/read-meter -F "file=@path/to/meter.jpg"
```

API docs อัตโนมัติ: http://127.0.0.1:8000/docs

## การทำงานแบบ OOP (ทีละขั้น) — ดู `example_oop.py`

```python
from config import MeterConfig
from pipeline import MeterReader

# แบบง่าย
reader = MeterReader()  # ใช้ config/model ดีฟอลต์
reader.read(image_rgb)  # → {reading, digits, warnings}

# แบบ DI สำหรับสอน — สลับ config/model ได้
config = MeterConfig(yolo_imgsz=960, orient_margin=0.12)
reader2 = MeterReader(config)
```

ลำดับภายใน `MeterReader.read()` (`pipeline.py:18`):
```python
check_water_meter()      # 0. SigLIP2 คัดแยก
detect_digits_best()     # 1. YOLO ลอง 4ทิศ×3ฟิลเตอร์ (orig/clahe/histeq) + margin
flip_guard()             # 2. กันกลับหัว FLIP_MAP
is_aligned()/cross_check # 3. ตรวจแนว + SigLIP ซ้ำหลักไม่มั่นใจ
# 4. รวม warnings → reading
```

ปรับเปลี่ยนง่าย: ค่าคงที่ทั้งหมดอยู่บนสุดของ `main.py`
(ขนาดโมเดล, threshold, มุมหมุน `ROTATION_ANGLES`, ฟิลเตอร์ `PREP_LIST` = orig/clahe/histeq
(`CLAHE_VARIANTS` ยังคงไว้เพื่อ backward-compat), `ORIENT_MARGIN`, `FLIP_GUARD_CONF`,
`ALIGN_MAX_Y_SPREAD`, `DIGIT_CROSS_CHECK`, `RED_RATIO_THRESHOLD`/`RED_RATIO_DOMINANCE`/`MIN_CROP_PX`)

## วิธีเทรน YOLO26 ด้วยข้อมูลของคุณ

1. เก็บภาพ: `python scripts/label_data.py photos` (กล้องเว็บ) หรือใช้มือถือ
2. Annotate box รอบตัวเลข **แต่ละหลัก** แล้วใส่ **class = ค่าของตัวเลขนั้น (0-9)**
   เช่น มิเตอร์เลข "002486" → box 6 กล่อง class 0, 0, 2, 4, 8, 6
   (Label Studio / Roboflow / LabelImg — export เป็น YOLO format)
3. วางภาพ+label ใน `training/raw/` แล้วแยก train/val:
   ```powershell
   python scripts/label_data.py split
   ```
4. เทรน:
   ```powershell
   python training/yolo_train.py --model yolo26n.pt --epochs 100
   ```
   (มี `--model`, `--epochs`, `--imgsz`, `--lr0`, `--resume`, `--patience` ให้ปรับ)
5. หลังเทรน script ประเมิน mAP@0.5 / mAP@0.5:0.95 / P / R บน val set
6. ใช้ผลลัพธ์ใน API: แก้บรรทัดบนสุดของ `main.py`
   ```python
   YOLO_MODEL = "runs/detect/meter_digits/weights/best.pt"
   ```

> เทรนขนาดเดียวกับที่จะ deploy (รัน `yolo26n` ก็เทรน `yolo26n`) และทุก class 0-9
> ควรมีตัวอย่างครบ

## Response ของ API

```json
{
  "reading": "002486",
  "digits": [
    {"position": 1, "digit": 0, "confidence": 0.98, "bbox": [100, 50, 130, 90], "reliable": true}
  ],
  "digit_count": 6,
  "mean_confidence": 0.92,
  "meter_check": {
    "verified": true,
    "predicted_class": "water meter",
    "confidence": 0.87,
    "probabilities": {"water meter": 0.87, "electricity meter": 0.09, "gas meter": 0.03, "not a meter": 0.01}
  },
  "processing": {
    "best": {"angle": 0, "clahe": true},
    "margin_applied": false
  },
  "flip_check": {"consistent": true, "anti_reading": "", "anti_confidence": 0.0, "warned": false},
  "alignment": {"ok": true, "y_spread": 0.012},
  "cross_check": {"enabled": true, "checked": 1, "mismatches": []},
  "warnings": ["หลักที่ 4 (ค่า 8) confidence ต่ำ (0.42) - ควรตรวจสอบด้วยตา"],
  "elapsed_ms": 850.0,
  "image_size": [1280, 720]
}
```

เมื่อ **ไม่ใช่มิเตอร์น้ำ** (คัดแยกออก): `reading` เป็นค่าว่าง `digits` ว่าง มี
`meter_check.verified = false` + warning อธิบายว่าจำแนกว่าเป็นอะไร

## ข้อควรรู้

- **การคัดแยก (SigLIP2)**: ภาพจะถูกตัดทิ้งทันทีถ้าไม่ใช่มิเตอร์น้ำ (เทียบกับมิเตอร์ไฟ/
  แก๊ส/สิ่งอื่น) — ลองเปิดภาพอย่างอื่นดูได้ ป้ายเปรียบเทียบอยู่ใน `METER_LABELS` ของ
  `main.py` (เช่น เพิ่ม "pressure gauge" ถ้าอยากคัดแยกเกจวัดความดันด้วย)
- **หมุนภาพ + CLAHE**: ทุกภาพจะถูกทดลองอ่าน **4 ทิศ (0°/90°/180°/270° — ภาพจากกล้องอาจ
  ตะแคงจริงและไม่มี EXIF tag)** × เปิด/ปิด CLAHE แล้วใช้ผลที่ confidence เฉลี่ยสูงสุด
  (ผลที่กล่องเรียงแนวตั้งในมุมมองนั้น ถูกตัดออกก่อนเลือก — กันอ่านคอลัมน์ที่มิใช่ค่ามิเตอร์;
  ภาพตะแคง 90° จะถูกอ่านได้เมื่อหมุนเข้าท่า) — ช่วยได้ทั้งภาพกลับหัว/ตะแคง และภาพแสงน้อย
  เลขจาง; `reading` ออกมา พร้อม `processing.best` บอกว่าชนะด้วยมุม/ฟิลเตอร์ใด
- **กันอ่านตัวเลขกลับหัว (3 ชั้น)**:
  1. `ORIENT_MARGIN`: มุมที่ไม่ใช่ 0° ต้องชนะมุม 0° เกิน 0.05 จึงจะถูกเลือก (กัน
     "พลิก" ผลฉิวเฉียด) — ดูได้จาก `processing.margin_applied`
  2. `flip_check`: อ่านซ้ำแบบหมุน 180° — ถ้า "อ่านกลับหัว" ก็ได้ confidence สูง
     (≥ `FLIP_GUARD_CONF`) แต่ไม่ตรงรูปแบบ 6↔9 / 2↔5 / 0,1,8 คงเดิม → warning
     "ผลลัพธ์อาจอ่านกลับหัว" (ตัวเลขคว่ำทั่วไปอ่านไม่ออก → ไม่รบกวนภาพปกติ)
     **อัตโนมัติแก้**: ถ้าภาพถ่ายไม่ตรงแนวจริง (มุมที่ชนะได้เปรียบแค่ฉิวเฉียด
     ≤ `ORIENT_MARGIN` แล้ว flip ไม่ตรงกัน — ทั้งนี้ใช้ได้กับทุกมุม 0/90/180/270°)
     ระบบสลับไปใช้ผลอ่านแบบหมุน 180° ตรงข้ามแทน —
     ดูได้จาก `processing.auto_corrected` / `flip_check.applied` + warning
     "ภาพถ่ายไม่ตรงแนว - สลับไปใช้ผลอ่านแบบหมุน X°"
  3. `cross_check` (เปิด default — ปิดได้ที่ `DIGIT_CROSS_CHECK=False` ถ้าให้ความเร็ว):
     SigLIP2 ตรวจทานหลักที่ YOLO ไม่มั่นใจ (conf < 0.60) ตัวเลขที่ต่างกัน → warning;
     `alignment` เพิ่มกัน "อ่านข้อความ/ป้ายข้างมิเตอร์" ที่กล่องไม่เรียงแนว
- **กันอ่านผิดชิ้น**: กล่องตัวเลขต้องเรียงเป็นแนวนอน —
  ถ้าเรียงเป็นแนวตั้ง (แกน x แคบ + แกน y กว้าง เช่น วันที่/เลขรุ่น/ป้ายข้างมิเตอร์
  ที่พิมพ์เป็นคอลัมน์) → **ปฏิเสธผลทิ้ง** คืน `reading: ""` พร้อม warning
  (`VERTICAL_MAX_X_SPREAD` / `VERTICAL_MIN_Y_SPREAD` ปรับเกณฑ์ได้); ส่วนแนวเอียง
  เบา ๆ ไม่ถูกตัด (`alignment` แยกตรวจว่ากล่องเรียงแนวเดียวกัน)
- **เลขกำลังหมุนเปลี่ยนค่า** (เช่น 3↔4 กลางคัน) เป็นเคสยาก: ระบบจะ flag หลักที่
  confidence ต่ำใน `warnings` ให้ตรวจสอบ
- **เลขนำหน้า 0**: ระบบแจ้งเตือนถ้าหลักแรกเป็น 0 (มิเตอร์จริงไม่ขึ้นต้น 0)
- **ก่อนเทรน**: YOLO26n (COCO) ยังไม่รู้จักตัวเลขมิเตอร์ — ผลลัพธ์จะ "ตรวจไม่พบตัวเลข"
  จนกว่าจะ fine-tune ด้วยข้อมูลจริงแล้วแก้ `YOLO_MODEL` ชี้ไปที่ `best.pt`
- **โหลด SigLIP2 ครั้งแรกใช้เวลา ~50 วินาที** (ดาวน์โหลด weights) — ปกติ ครั้งถัดไปเร็ว
- CPU: YOLO26n fast (~39ms/ภาพ) — เหมาะกับรันเครื่องเดียว; GPU เร็วขึ้นหลายเท่า
  (เปลี่ยน device ได้ใน `main.py` ที่ `DEVICE`)

## Troubleshooting

| อาการ | วิธีแก้ |
|---|---|
| API ตอบ "ภาพนี้ไม่ใช่มิเตอร์น้ำ" ทั้งที่ใช่ | ลองถ่ายใหม่ให้เห็นหน้าปัดชัด ๆ (ไม่เอียง/มีแสง) ถ้ายังผิด ลด `METER_VERIFY_CONF` หรือปรับ `METER_LABELS` |
| API ตอบ "ตรวจไม่พบตัวเลข" | ยังไม่ได้ fine-tune หรือภาพไกลเกิน/เอียง/เบลอ — ถ่ายใกล้ ๆ ตรงหน้าปัด |
| ได้ warning "อาจอ่านกลับหัว" | ภาพกลับหัวจริง → หมุนภาพให้ตัวเลขตั้งตรงก่อนถ่าย; ถ้าภาพตั้งตรงแล้วยังขึ้น ลองถ่ายใหม่หรือพิจารณา `FLIP_GUARD_CONF` |
| โหลด model ช้าเป็นนาทีตอนแรก | ปกติ — กำลังดาวน์โหลด weights ครั้งแรก (SigLIP ~50s) |
| ใช้ model ยังไม่เทรน | แก้ `YOLO_MODEL` ใน `main.py` ไปที่ `best.pt` ของคุณ |
| เปิด Gradio แล้วขึ้น "API ไม่พร้อม" | รัน `python main.py` ก่อน |