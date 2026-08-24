# 📖 คู่มือการเรียนรู้: ระบบอ่านเลขมิเตอร์น้ำอัตโนมัติด้วย AI
## Deep Learning & Computer Vision Water Meter OCR Tutorial

> **สำหรับนักศึกษาและผู้เริ่มต้น:** เอกสารนี้ออกแบบมาเพื่อพาคุณสร้างและทำความเข้าใจระบบอ่านเลขมิเตอร์น้ำอัตโนมัติทีละขั้นตอน โดยอธิบาย **"ทำไมต้องทำ (WHY)"** ก่อน **"ทำอย่างไร (HOW)"** เพื่อให้เห็นภาพรวมและเข้าใจเหตุผลเบื้องหลังของแต่ละฟังก์ชัน สามารถหยุดพักและทดลองรันระบบได้ตลอดเวลา

---

## ⚡ 0. Quick Start (ทดลองรันระบบทันทีใน 5 นาที)

> **ใช้โมเดลสำเร็จรูปที่มีอยู่แล้ว:** ในโปรเจกต์มีไฟล์โมเดล `weights/MeterOCR.pt` ที่ฝึกฝนเสร็จแล้ว คุณสามารถทดลองรันระบบได้ทันทีโดยไม่ต้องฝึกโมเดลใหม่

### 0.1 สิ่งที่ต้องมีในเครื่อง (Prerequisites)
1. **Python 3.11** (รองรับ 3.10 – 3.12)
2. **`uv`** ตัวจัดการแพ็กเกจ Python ความเร็วสูง *(ติดตั้งได้จาก [astral.sh/uv](https://docs.astral.sh/uv/))*

---

### 0.2 การติดตั้งสภาพแวดล้อม (Installation)

> **ทำไมต้องทำ (WHY)?:** เพื่อสร้างสภาพแวดล้อมเสมือน (Virtual Environment) แยก Library ของโปรเจกต์นี้ออกจากเครื่องของคุณ ป้องกันปัญหาเวอร์ชันชนกัน

เปิด Terminal ในโฟลเดอร์ `meter-reader/` แล้วพิมพ์ 3 คำสั่ง:

```powershell
# 1. สร้าง Virtual Environment ด้วย Python 3.11
uv venv --python 3.11

# 2. เปิดใช้งาน Virtual Environment (สำหรับ Windows PowerShell)
.venv\Scripts\Activate.ps1
# (หากใช้ macOS/Linux ให้ใช้: source .venv/bin/activate)

# 3. ติดตั้ง Dependencies ทั้งหมด
uv pip install -r requirements.txt
```

**ผลลัพธ์ที่คาดหวัง (Expected Result):**
```text
Installed 12 packages in 1.42s
```

---

### 0.3 การสั่งรันระบบ (Run Application)

ระบบประกอบด้วย 2 ส่วนที่ทำงานร่วมกัน:

#### เทอร์มินัลที่ 1 — รัน Backend API:
```powershell
uv run python main.py
```
**ผลลัพธ์ที่คาดหวัง:**
```text
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

#### เทอร์มินัลที่ 2 — รัน Frontend Web UI:
```powershell
uv run python gradio_app.py
```
**ผลลัพธ์ที่คาดหวัง:**
```text
Running on local URL:  http://127.0.0.1:7860
```

---

### 0.4 ทดลองกับภาพตัวอย่าง (Test Image)

1. เปิดเว็บเบราว์เซอร์ไปที่ [http://127.0.0.1:7860](http://127.0.0.1:7860)
2. ลากรูปภาพจากโฟลเดอร์ `meter_img/` (เช่น `Water+meter.jpg` หรือ `IMG_7163.jpeg`) มาวางในช่องอัปโหลด
3. กดปุ่ม **"🔍 เริ่มอ่านเลขมิเตอร์"**

---

### 0.5 ผลลัพธ์ที่คาดหวัง (Expected Result)

```text
┌─────────────────────────────────────────────────────────────┐
│ 💧 Water Meter Reader Web Interface                         │
├──────────────────────────────┬──────────────────────────────┤
│ [ 📷 ภาพถ่ายมิเตอร์ที่อัปโหลด ] │ 📟 ตัวเลขที่อ่านได้: 05715     │
│                              │ 📊 ความมั่นใจ: 91.10%         │
│                              │ ⚠️ คำเตือน:                   │
│                              │   - หลักแรกเป็น 0 (อาจเกินมา) │
└──────────────────────────────┴──────────────────────────────┘
```

> 💡 **หากต้องการเข้าใจการทำงานเชิงลึกของระบบ:** เชิญศึกษาต่อใน **บทที่ 1** และ **บทที่ 2** ด้านล่างได้เลยครับ

---

# 📘 บทที่ 1: พื้นฐาน การออกแบบ และการประมวลผลภาพ (Fundamentals, Design, and Image Processing)

---

### 1.1 ปัญหาที่ระบบแก้ และภาพรวมการทำงาน (System Overview)

#### 1.1.1 ปัญหาที่พบในภาพถ่ายมิเตอร์จริง (The Problem)
การให้คอมพิวเตอร์อ่านตัวเลขจากภาพถ่ายมิเตอร์น้ำจริงหน้างานมีความท้าทายหลัก 4 ประการ:
1. **ภาพถ่ายเอียงหรือกลับหัว:** ผู้ใช้อาจถือโทรศัพท์ถ่ายในมุมที่สะดวก
2. **แสงสะท้อนและตัวเลขเลือนราง:** กระจกมิเตอร์มักมีคราบน้ำ หรืออยู่ในมุมมืด
3. **มีป้ายข้อความหลอกตา:** เช่น วันที่ผลิต หรือซีเรียลนัมเบอร์ปั๊มแนวตั้งบนตัวเรือน
4. **ตัวเลขกลับหัวหลอกตา:** เลข $6 \leftrightarrow 9$, $2 \leftrightarrow 5$, และ $0, 1, 8$ ที่มีลักษณะสมมาตรเมื่อหมุน 180°

#### 1.1.2 ข้อมูลขาเข้าและขาออก (Input & Output)
* **Input:** ภาพถ่ายมิเตอร์น้ำในรูปแบบ RGB (ไฟล์ JPEG, PNG)
* **Output:** ข้อความตัวเลข (String เช่น `"05715"`), ตำแหน่งของตัวเลขแต่ละหลัก (Bounding Box), ค่าความมั่นใจ (Confidence Score) และรายการคำเตือนความเสี่ยง (Warnings)

#### 1.1.3 แผนภาพการเดินทางของข้อมูล (Data Flow Architecture)

```text
[ 📷 Input Image ] (ภาพ RGB)
        │
        ▼
[ 1. SigLIP2 Verification ] ──> ภาพนี้ใช่มิเตอร์น้ำจริงหรือไม่? (ถ้าไม่ใช่ ปฏิเสธทันที)
        │ (ใช่)
        ▼
[ 2. Preprocessing & Search ] ──> ลองหมุน 4 ทิศ (0°, 90°, 180°, 270°) × ปรับแสง 3 แบบ (Orig, CLAHE, HistEq)
        │
        ▼
[ 3. YOLO Digit Detection ] ──> ตรวจจับตัวเลข 0-9 ทุกหลักบนภาพที่หมุน
        │
        ▼
[ 4. Candidate Filtering (IoU) ] ──> ตัดกรอบสี่เหลี่ยมที่ซ้อนทับกันทิ้ง (Dedup)
        │
        ▼
[ 5. Vertical Check (is_vertical) ] ──> ตรวจว่าแถวตัวเลขเป็นแนวนอนหรือไม่ (กรองป้ายวันที่ออก)
        │
        ▼
[ 6. Red Digit & Scoring ] ──> ตรวจหลักทศนิยมสีแดง (ต้องอยู่ขวาสุด) + ให้คะแนนมุมที่ดีที่สุด
        │
        ▼
[ 7. Coordinate Remapping ] ──> แปลงพิกัดกล่องตัวเลขจากภาพหมุน กลับสู่ภาพต้นฉบับเดิม
        │
        ▼
[ 8. Safety Guards ]
        ├─ flip_guard: ตรวจสอบการกลับหัว 180° แบบกระจกเงา
        └─ cross_check_digits: SigLIP2 ตรวจทานซ้ำเฉพาะหลักที่มั่นใจต่ำ (< 0.60)
        │
        ▼
[ ✅ Final Output ] (ตัวเลขมิเตอร์ + พิกัดกล่อง + คำเตือนความเสี่ยง)
```

#### 1.1.4 เทคโนโลยีหลักที่เลือกใช้
* **OpenCV (`cv2`):** ไลบรารีสำหรับจัดการภาพดิจิทัล (หมุนภาพ, ปรับคอนทราสต์, คำนวณสี)
* **YOLO (You Only Look Once):** โมเดล Deep Learning สำหรับตรวจจับตำแหน่งและค่าของตัวเลข 0–9
* **SigLIP2:** โมเดล Vision-Language จาก Google สำหรับคัดแยกประเภทมิเตอร์ และตรวจทานตัวเลข
* **FastAPI:** เว็บเฟรมเวิร์กสำหรับสร้าง REST API เชื่อมต่อกับระบบอื่น
* **Gradio:** ไลบรารีสำหรับสร้างหน้าเว็บส่วนติดต่อผู้ใช้ (Web UI) แบบ Interactive

---

### 1.2 สภาพแวดล้อมและการจัดการโปรเจกต์ (Environment Setup)

> **ทำไมต้องทำ (WHY)?:** เพื่อให้มั่นใจว่าเครื่องคอมพิวเตอร์ของคุณมีแพ็กเกจและไฟล์น้ำหนักโมเดลครบถ้วนก่อนเริ่มศึกษาโค้ด

#### โครงสร้างไฟล์ใน Repository:
```text
meter-reader/
├── main.py            # API หลัก และ Pipeline ประมวลผลภาพทั้งหมด
├── gradio_app.py      # หน้าเว็บ Web UI สำหรับทดสอบระบบ
├── TUTORIAL.md        # คู่มือการเรียนรู้ฉบับสมบูรณ์
├── requirements.txt   # รายการ Library dependencies
├── meter_img/         # ชุดภาพถ่ายมิเตอร์น้ำ 7 ภาพสำหรับทดสอบ
└── weights/
    └── MeterOCR.pt    # ไฟล์โมเดล YOLO สำหรับอ่านตัวเลข
```

#### ตรวจสอบความพร้อมของระบบ:
```powershell
uv run python -c "import cv2, torch, ultralytics; print('✅ Environment พร้อมใช้งาน | PyTorch:', torch.__version__)"
```
**ผลลัพธ์ที่คาดหวัง:**
```text
✅ Environment พร้อมใช้งาน | PyTorch: 2.x.x
```

---

### 1.3 ค่าคงที่และการโหลดโมเดล AI (Constants & Lazy Loaders)

#### 1.3.1 การกำหนดค่าคงที่ของระบบ (⚙️ Configuration)
ค่าคงที่ทั้งหมดถูกรวมไว้ที่ส่วนบนสุดของ `main.py` เพื่อให้ปรับแต่งพฤติกรรมได้ง่าย:

```python
# 📍 main.py (บรรทัดที่ 26-60)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# โมเดล YOLO และการตรวจจับตัวเลข
YOLO_MODEL = "weights/MeterOCR.pt"  # ตำแหน่งไฟล์น้ำหนักโมเดล
YOLO_IMGSZ = 960                   # ขนาดภาพที่ป้อนเข้าโมเดล
YOLO_CONF = 0.35                   # เกณฑ์ความมั่นใจขั้นต่ำของ YOLO
CONF_RELIABLE = 0.60               # เกณฑ์ความมั่นใจที่ถือว่าน่าเชื่อถือ
EXPECTED_MIN_DIGITS = 4            # จำนวนหลักขั้นต่ำของมิเตอร์น้ำ
EXPECTED_MAX_DIGITS = 9            # จำนวนหลักสูงสุด

# การค้นหามุมและปรับแสง
ROTATION_ANGLES = (0, 90, 180, 270)
PREP_LIST = ("orig", "clahe", "histeq")
CLAHE_CLIP = 2.0
CLAHE_GRID = (8, 8)

# ความปลอดภัย
ORIENT_MARGIN = 0.12               # มุมอื่นต้องชนะมุม 0° เกิน 0.12 ถึงจะยอมสลับมุม
FLIP_GUARD_CONF = 0.60             # เกณฑ์ความมั่นใจในการเริ่มตรวจจับกลับหัว 180°
FLIP_MAP = {0: 0, 1: 1, 2: 5, 5: 2, 6: 9, 8: 8, 9: 6} # ตารางเลขสมมาตร
ALIGN_MAX_SPREAD = 0.10
RED_THRESH = 0.08                  # สัดส่วนสีแดงขั้นต่ำของหลักทศนิยม
RED_DOMINANCE = 2.0
MIN_CROP_PX = 4

# โมเดล SigLIP2
SIGLIP_MODEL = "google/siglip2-base-patch16-224"
METER_LABELS = ("water meter", "electricity meter", "gas meter", "not a meter")
METER_VERIFY_CONF = 0.50
```

---

#### 1.3.2 การโหลดโมเดลแบบ Lazy Loading (⭐ Core)

* **Step 1 — Concept:** โมเดล AI มีขนาดใหญ่ หากโหลดทันทีที่รันสคริปต์ โปรแกรมจะเปิดช้า เราจึงโหลดเมื่อมี Request ภาพแรกเข้ามาเท่านั้น
* **Step 2 — Simplified Example:**
  ```python
  _model = None
  def get_model():
      global _model
      if _model is None:
          _model = load_model_from_disk()
      return _model
  ```
* **Step 3 — Real Implementation (`main.py`):**
  ```python
  _yolo = None
  _siglip = None

  def get_yolo() -> Any:
      """โหลดโมเดล YOLO เมื่อถูกเรียกใช้ครั้งแรก พร้อม warm-up 1 ครั้ง"""
      global _yolo
      if _yolo is None:
          from ultralytics import YOLO
          _yolo = YOLO(YOLO_MODEL)
          _yolo.predict(np.zeros((640, 640, 3), dtype=np.uint8), verbose=False)
      return _yolo

  def get_siglip() -> tuple[Any, Any]:
      """โหลดโมเดล SigLIP2 เข้า GPU/CPU"""
      global _siglip
      if _siglip is None:
          from transformers import AutoModel, AutoProcessor
          processor = AutoProcessor.from_pretrained(SIGLIP_MODEL)
          model = AutoModel.from_pretrained(SIGLIP_MODEL).to(DEVICE).eval()
          _siglip = (processor, model)
      return _siglip
  ```

---

### 1.4 การจัดการภาพและพิกัดเรขาคณิต (Image Preprocessing & Geometry)

#### 1.4.1 การหมุนภาพ (⭐ Core: `rotate_image`)
* **Concept:** หมุนภาพตามองศา 90°, 180°, 270° ตามเข็มนาฬิกา
* **Real Implementation (`main.py`):**
  ```python
  def rotate_image(img_bgr: np.ndarray, angle: int) -> np.ndarray:
      """หมุนภาพตามองศา 90, 180, 270 (0 = คงเดิม)"""
      if angle == 90:
          return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
      if angle == 180:
          return cv2.rotate(img_bgr, cv2.ROTATE_180)
      if angle == 270:
          return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
      return img_bgr
  ```

---

#### 1.4.2 การปรับคอนทราสต์แสง (⭐ Core: `apply_prep`)
* **Concept:** ภาพมืดหรือมีเงาตกกระทบทำให้มองไม่เห็นตัวเลข เราใช้ 2 เทคนิค:
  * **CLAHE (Contrast Limited Adaptive Histogram Equalization):** ปรับสมดุลแสงเฉพาะจุดบนช่องความสว่าง (L) ในระบบสี LAB
  * **HistEq (Histogram Equalization):** เกลี่ยความสว่างทั่วทั้งภาพบนช่อง Y ในระบบสี YCrCb
* **Real Implementation (`main.py`):**
  ```python
  def apply_prep(img_bgr: np.ndarray, prep: str) -> np.ndarray:
      """ปรับคอนทราสต์ภาพ: CLAHE หรือ HistEq"""
      if prep == "clahe":
          lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
          l, a, b = cv2.split(lab)
          l_clahe = cv2.createCLAHE(CLAHE_CLIP, CLAHE_GRID).apply(l)
          return cv2.cvtColor(cv2.merge([l_clahe, a, b]), cv2.COLOR_LAB2BGR)

      if prep == "histeq":
          ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
          y, cr, cb = cv2.split(ycrcb)
          y_eq = cv2.equalizeHist(y)
          return cv2.cvtColor(cv2.merge([y_eq, cr, cb]), cv2.COLOR_YCrCb2BGR)

      return img_bgr
  ```

---

#### 1.4.3 การแปลงพิกัดจุดเดี่ยวและกล่อง (🔧 Implementation: `remap_bbox`)
* **Problem:** เมื่อตรวจจับตัวเลขบนภาพที่หมุน 90° พิกัดสี่เหลี่ยมจะอยู่ในแกนของภาพหมุน หากต้องการนำไปวาดบนภาพต้นฉบับเดิม เราต้อง **แปลงพิกัดย้อนกลับ**
* **Real Implementation (`main.py`):**
  ```python
  def remap_point(x: float, y: float, angle: int, w: int, h: int) -> tuple[float, float]:
      """แปลงจุด (x, y) จากภาพที่หมุนแล้ว กลับสู่พิกัดภาพเดิมแบบทีละจุด"""
      if angle == 90:
          return y, h - x      # หมุนขวา 90° -> แกนสลับ x=y, y=h-x
      if angle == 180:
          return w - x, h - y  # กลับหัว 180° -> x=w-x, y=h-y
      if angle == 270:
          return w - y, x      # หมุนซ้าย 90° -> แกนสลับ x=w-y, y=x
      return x, y

  def remap_bbox(bbox: list[float], angle: int, w: int, h: int) -> list[float]:
      """แปลงกล่อง [x1, y1, x2, y2] จากภาพที่หมุนแล้ว กลับเป็นพิกัดภาพเดิม"""
      x1, y1, x2, y2 = bbox
      p1_x, p1_y = remap_point(x1, y1, angle, w, h)
      p2_x, p2_y = remap_point(x2, y2, angle, w, h)
      return [
          min(p1_x, p2_x),
          min(p1_y, p2_y),
          max(p1_x, p2_x),
          max(p1_y, p2_y),
      ]
  ```

---

#### 1.4.4 การตัดกล่องซ้อนด้วย IoU (⭐ Core: `dedup_detections`)
* **Concept:** **IoU (Intersection over Union)** คืออัตราส่วนพื้นที่ทับซ้อนของ 2 กล่อง หากกล่องซ้อนกันเกิน 45% ให้เลือกเฉพาะกล่องที่ AI มั่นใจสูงสุดไว้เพียงกล่องเดียว
* **Real Implementation (`main.py`):**
  ```python
  def iou(box1: list[float], box2: list[float]) -> float:
      """คำนวณพื้นที่ทับซ้อน (IoU) ระหว่าง 2 กล่อง"""
      x1, y1 = max(box1[0], box2[0]), max(box1[1], box2[1])
      x2, y2 = min(box1[2], box2[2]), min(box1[3], box2[3])

      intersection = max(0, x2 - x1) * max(0, y2 - y1)
      area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
      area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
      union = area1 + area2 - intersection

      return (intersection / union) if union > 0 else 0.0

  def dedup_detections(dets: list[dict[str, Any]], thresh: float = 0.45) -> list[dict[str, Any]]:
      """ตัดกล่องที่ซ้อนทับกันออก เหลือเฉพาะกล่องที่มั่นใจสูงสุด"""
      kept: list[dict[str, Any]] = []
      for d in sorted(dets, key=lambda x: x["confidence"], reverse=True):
        if not any(iou(d["bbox"], k["bbox"]) > thresh for k in kept):
            kept.append(d)
      return sorted(kept, key=lambda x: x["center_x"])
  ```

---

### 1.5 การตรวจจับตัวเลขและระบบความปลอดภัย (Detection & Safety Engine)

#### 1.5.1 การตรวจจับตัวเลขด้วย YOLO (⭐ Core: `detect_digits`)
* **Concept:** ป้อนภาพเข้าโมเดล YOLO เพื่อดึงพิกัด Bounding Box และค่าตัวเลข 0–9 แล้วเรียงลำดับจากซ้ายไปขวา
* **Real Implementation (`main.py`):**
  ```python
  def detect_digits(img_bgr: np.ndarray) -> list[dict[str, Any]]:
      """YOLO หาตัวเลข 0-9 เรียงจากซ้ายไปขวา"""
      res = get_yolo().predict(
          img_bgr,
          imgsz=YOLO_IMGSZ,
          conf=YOLO_CONF,
          device=DEVICE,
          verbose=False,
      )

      boxes = []
      for b in res[0].boxes:
          x1, y1, x2, y2 = b.xyxy[0].tolist()
          boxes.append({
              "digit": int(b.cls[0].item()),
              "confidence": float(b.conf[0].item()),
              "bbox": [x1, y1, x2, y2],
              "center_x": (x1 + x2) / 2.0,
              "center_y": (y1 + y2) / 2.0,
          })

      return sorted(boxes, key=lambda d: d["center_x"])
  ```

---

#### 1.5.2 การกรองคอลัมน์แนวตั้ง (⭐ Core: `is_vertical`)
* **Concept:** มิเตอร์น้ำจริงมีตัวเลขเรียงตัวเป็น **แนวนอน** ($\text{width\_span} > \text{height\_span}$) เสมอ หากความสูงมากกว่าความกว้าง แสดงว่าเป็นป้ายวันที่หรือซีเรียลนัมเบอร์แนวดิ่ง ซึ่งต้องปฏิเสธทิ้ง
* **Real Implementation (`main.py`):**
  ```python
  def is_vertical(dets: list[dict[str, Any]], img_w: int, img_h: int) -> dict[str, Any]:
      """ตรวจว่ากล่องเรียงเป็นแนวตั้งหรือไม่ (แถวมิเตอร์แนวนอน width_span ต้องมากกว่า height_span)"""
      if len(dets) < 2:
          return {"vertical": False}

      xs = [d["center_x"] / img_w for d in dets]
      ys = [d["center_y"] / img_h for d in dets]

      width_span = max(xs) - min(xs)   # ความกว้างของแถวตัวเลข
      height_span = max(ys) - min(ys)  # ความสูงของแถวตัวเลข

      # ถ้าความสูงมากกว่าหรือใกล้เคียงความกว้าง แสดงว่าเป็นคอลัมน์แนวดิ่ง (เช่น วันที่/รุ่น)
      is_vert = (height_span >= width_span * 0.8) or (width_span <= 0.05 and height_span >= 0.08)
      return {"vertical": is_vert}
  ```

---

#### 1.5.3 การค้นหามุมและฟิลเตอร์ที่ดีที่สุด (🧠 Advanced: `detect_digits_best`)

* **Problem (ปัญหา):** ภาพอาจถ่ายตะแคงหรือมีเงา การลองเพียงมุมเดียวทำให้ตรวจจับไม่ติด
* **Solution Idea (แนวคิด):** ทดลองนำภาพไปหมุน 4 ทิศ × ปรับแสง 3 แบบ รวม $4 \times 3 = 12$ รูปแบบ แล้วเลือกชุดที่ได้คะแนนสูงสุด
* **Scoring & Margin Rule:**
  * $\text{Score} = \text{Mean Confidence} \times \text{Number of Digits}$
  * กฎสีแดง (`red_ratio`): หลักทศนิยมสีแดงต้องอยู่ขวาสุด หากพบสีแดงอยู่ซ้ายแสดงว่าภาพกลับหัว จะถูกตัดคะแนนลงครึ่งหนึ่ง
  * **Margin Rule:** มุมอื่นต้องชนะมุมตั้งต้น (0°) เกิน `0.12` ถึงจะยอมเปลี่ยนมุม
* **Real Implementation (`main.py`):**
  ```python
  def red_ratio(img_bgr: np.ndarray, bbox: list[float]) -> float:
      """คำนวณสัดส่วนพิกเซลสีแดงภายในกล่องตัวเลข (หลักทศนิยม)"""
      x1, y1, x2, y2 = [int(v) for v in bbox]
      pad_x = max(1, int((x2 - x1) * 0.15))
      pad_y = max(1, int((y2 - y1) * 0.15))

      crop = img_bgr[
          max(0, y1 + pad_y): min(img_bgr.shape[0], y2 - pad_y),
          max(0, x1 + pad_x): min(img_bgr.shape[1], x2 - pad_x),
      ]
      if crop.size == 0:
          return 0.0

      hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
      mask1 = cv2.inRange(hsv, (0, 40, 40), (12, 255, 255))
      mask2 = cv2.inRange(hsv, (165, 40, 40), (180, 255, 255))
      return float(np.mean((mask1 | mask2) > 0))

  def eval_orientation(bgr_img: np.ndarray, angle: int, prep: str) -> dict[str, Any]:
      """ประเมินผลลัพธ์ของ 1 มุม × 1 ฟิลเตอร์"""
      rot = rotate_image(bgr_img, angle)
      proc = apply_prep(rot, prep)
      dets = dedup_detections(detect_digits(proc))

      rh, rw = rot.shape[:2]
      vert = is_vertical(dets, rw, rh)
      n = len(dets)

      if not dets or vert["vertical"] or not (EXPECTED_MIN_DIGITS <= n <= EXPECTED_MAX_DIGITS):
          return {"score": 0.0, "dets": dets, "prep": prep, "vert": vert}

      score = float(np.mean([d["confidence"] for d in dets])) * n

      # หลักทศนิยมสีแดงต้องอยู่ขวาสุดเสมอ
      r_first = red_ratio(proc, dets[0]["bbox"])
      r_last = red_ratio(proc, dets[-1]["bbox"])

      if r_first > RED_THRESH and r_first > r_last * RED_DOMINANCE:
          score *= 0.5   # แดงอยู่ซ้าย -> น่าจะกลับหัว
      elif r_last > RED_THRESH and r_last > r_first * RED_DOMINANCE:
          score *= 1.05  # แดงอยู่ขวา -> ทิศทางถูกต้อง

      return {"score": score, "dets": dets, "prep": prep, "vert": vert}

  def detect_digits_best(rgb_img: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
      """ทดลอง 4 ทิศ × 3 ฟิลเตอร์ แล้วเลือกชุดที่ได้คะแนนรวมสูงสุด"""
      h, w = rgb_img.shape[:2]
      bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)

      candidates = {}
      for angle in ROTATION_ANGLES:
          best_in_angle = max(
              [eval_orientation(bgr, angle, prep) for prep in PREP_LIST],
              key=lambda c: c["score"],
          )
          candidates[angle] = best_in_angle

      cand0 = candidates[0]
      best_angle, best_cand = max(candidates.items(), key=lambda item: item[1]["score"])

      # Margin Rule: มุมอื่นต้องชนะมุม 0° เกินกำหนด จึงยอมสลับมุม (กันพลิกฉิวเฉียด)
      if (
          best_angle != 0
          and cand0["dets"]
          and not cand0["vert"]["vertical"]
          and (best_cand["score"] - cand0["score"] < ORIENT_MARGIN)
      ):
          best_angle, best_cand = 0, cand0

      best_dets = best_cand["dets"]
      best_meta = None

      if best_dets:
          best_meta = {
              "angle": best_angle,
              "prep": best_cand["prep"],
              "clahe": best_cand["prep"] == "clahe",
          }
          for d in best_dets:
              d["bbox"] = remap_bbox(d["bbox"], best_angle, w, h)
              d["center_x"] = (d["bbox"][0] + d["bbox"][2]) / 2.0
              d["center_y"] = (d["bbox"][1] + d["bbox"][3]) / 2.0

      return best_dets, best_meta
  ```

---

#### 1.5.4 การตรวจสอบความปลอดภัยเพิ่มเติม (⭐ Core)

1. **SigLIP2 Zero-shot Verification (`check_water_meter`):** ตรวจสอบว่าภาพเป็น `"water meter"` หรือไม่
2. **การตรวจสอบภาพกลับหัวแบบกระจกเงา (`flip_guard`):** หมุนภาพไป 180° แล้วตรวจสอบว่าอ่านได้ตัวเลขสมมาตรตามตาราง `FLIP_MAP` หรือไม่
3. **การตรวจทานหลักที่มั่นใจต่ำ (`cross_check_digits`):** ใช้ SigLIP2 ช่วยอ่านซ้ำเฉพาะหลักที่ค่า Confidence ต่ำกว่า 0.60

```python
@torch.inference_mode()
def check_water_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    """SigLIP2 Zero-shot ตรวจสอบว่าเป็นภาพมิเตอร์น้ำจริง"""
    processor, model = get_siglip()

    inputs = processor(
        text=list(METER_LABELS),
        images=Image.fromarray(rgb_img),
        padding="max_length",
        return_tensors="pt",
    ).to(DEVICE)

    outputs = model(**inputs)
    probs = torch.softmax(outputs.logits_per_image, dim=1)[0].cpu().numpy()
    pred_idx = int(np.argmax(probs))
    pred_label = METER_LABELS[pred_idx]

    return {
        "verified": pred_label == "water meter" and float(probs[0]) >= METER_VERIFY_CONF,
        "predicted_class": pred_label,
        "confidence": float(probs[0]),
    }

def flip_guard(rgb_img: np.ndarray, digits: list[dict[str, Any]], meta: dict[str, Any] | None) -> dict[str, Any]:
    """ตรวจสอบความสมมาตร 180° ป้องกันอ่านกลับหัว (Mirror Check เช่น 6<->9, 2<->5)"""
    if not digits or not meta:
        return {"warned": False, "anti_reading": "", "anti_confidence": 0.0}

    anti_angle = (meta["angle"] + 180) % 360
    rot_bgr = rotate_image(cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR), anti_angle)
    anti_dets = dedup_detections(detect_digits(apply_prep(rot_bgr, meta["prep"])))

    if not anti_dets:
        return {"warned": False, "anti_reading": "", "anti_confidence": 0.0}

    anti_reading = "".join(str(d["digit"]) for d in anti_dets)
    mean_conf = float(np.mean([d["confidence"] for d in anti_dets]))

    # เปรียบเทียบเลขหัว-ท้ายแบบกระจกสะท้อนกับตาราง FLIP_MAP
    digits_rev = [d["digit"] for d in reversed(digits)]
    anti_vals = [d["digit"] for d in anti_dets]

    consistent = (
        len(anti_vals) == len(digits_rev)
        and all(
            FLIP_MAP.get(orig) == anti
            for orig, anti in zip(digits_rev, anti_vals)
            if orig in FLIP_MAP
        )
    )

    return {
        "warned": bool(mean_conf >= FLIP_GUARD_CONF and not consistent),
        "anti_reading": anti_reading,
        "anti_confidence": round(mean_conf, 4),
    }

@torch.inference_mode()
def cross_check_digits(rgb_img: np.ndarray, digits: list[dict[str, Any]], h: int, w: int, angle: int = 0) -> list[dict[str, Any]]:
    """SigLIP2 Cross-check ตรวจทานเฉพาะหลักที่ YOLO มั่นใจต่ำ (< 0.60)"""
    low_conf = [d for d in digits if d["confidence"] < CONF_RELIABLE]
    if not low_conf:
        return []

    processor, model = get_siglip()
    labels = [str(i) for i in range(10)]
    mismatches = []

    for d in low_conf:
        x1, y1, x2, y2 = [int(v) for v in d["bbox"]]
        crop = rgb_img[max(0, y1): min(h, y2), max(0, x1): min(w, x2)]

        if crop.shape[0] < MIN_CROP_PX or crop.shape[1] < MIN_CROP_PX:
            continue

        if angle != 0:
            crop_bgr = cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)
            crop = cv2.cvtColor(rotate_image(crop_bgr, angle), cv2.COLOR_BGR2RGB)

        inputs = processor(
            text=labels,
            images=Image.fromarray(crop),
            padding="max_length",
            return_tensors="pt",
        ).to(DEVICE)

        outputs = model(**inputs)
        probs = torch.softmax(outputs.logits_per_image, dim=1)[0].cpu().numpy()
        pred = int(np.argmax(probs))

        if pred != d["digit"]:
            mismatches.append({
                "position": d["position"],
                "yolo_digit": d["digit"],
                "siglip_digit": pred,
                "siglip_confidence": float(probs[pred]),
            })

    return mismatches
```

---

### 📋 ตรวจสอบความเข้าใจบทที่ 1

- [ ] ฉันเข้าใจว่าทำไมต้องมี `remap_bbox` เมื่อหมุนภาพ
- [ ] ฉันเข้าใจว่า `is_vertical` ใช้หลักการ $\text{width\_span} > \text{height\_span}$ ในการกรองคอลัมน์แนวตั้ง
- [ ] ฉันเข้าใจว่าทำไมต้องตรวจหาสีแดงของหลักทศนิยม และตรวจการกลับหัว 180°
- [ ] ฉันเข้าใจหน้าที่ของ YOLO (หาตำแหน่งและตัวเลข) และ SigLIP2 (คัดแยกและตรวจทาน)

---

# 📗 บทที่ 2: การพัฒนาแอปพลิเคชันและส่วนติดต่อผู้ใช้ (Application & UI Development)

---

### 2.1 การบูรณาการระบบประมวลผลหลัก (⭐ Core: `read_meter`)

ฟังก์ชัน `read_meter(rgb_img)` ทำหน้าที่รวมทุกขั้นตอนเข้าด้วยกัน และสร้างข้อความแจ้งเตือนความเสี่ยง (Warnings System):

```python
# 📍 main.py — Main Pipeline Integration
def read_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    """รับภาพ RGB -> ตรวจชนิดมิเตอร์ -> หาตัวเลข -> ตรวจความถูกต้อง -> คืนผลลัพธ์"""
    t0 = perf_counter()
    h, w = rgb_img.shape[:2]

    # 1. ตรวจสอบว่าใช่มิเตอร์น้ำจริงไหม
    meter = check_water_meter(rgb_img)
    if not meter["verified"]:
        return {
            "reading": "",
            "digits": [],
            "meter_check": meter,
            "processing": None,
            "warnings": [f"ภาพนี้ไม่ใช่มิเตอร์น้ำ ({meter['predicted_class']})"],
            "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
        }

    # 2. ค้นหาตัวเลขและมุมที่ดีที่สุด
    dets, meta = detect_digits_best(rgb_img)
    if not dets:
        return {
            "reading": "",
            "digits": [],
            "meter_check": meter,
            "processing": meta,
            "warnings": ["ตรวจไม่พบตัวเลข"],
            "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
        }

    digits = [{
        "position": i,
        "digit": d["digit"],
        "confidence": round(d["confidence"], 4),
        "bbox": d["bbox"],
        "reliable": d["confidence"] >= CONF_RELIABLE,
    } for i, d in enumerate(dets, 1)]
    mean_conf = float(np.mean([d["confidence"] for d in digits]))

    # 3. ตรวจสอบว่าไม่ใช่คอลัมน์แนวตั้ง (เช่น วันที่)
    if meta and meta["angle"] == 0 and is_vertical(dets, w, h)["vertical"]:
        return {
            "reading": "",
            "digits": [],
            "meter_check": meter,
            "processing": meta,
            "warnings": ["กล่องเรียงแนวตั้ง — ไม่ใช่ค่ามิเตอร์"],
            "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
        }

    # 4. ตรวจสอบความถูกต้องและสร้างคำเตือน
    flip = flip_guard(rgb_img, digits, meta)
    align_vals = [
        (d["bbox"][0] + d["bbox"][2]) / (2 * w)
        if meta and meta["angle"] in (90, 270)
        else (d["bbox"][1] + d["bbox"][3]) / (2 * h)
        for d in digits
    ]
    align_ok = float(np.std(align_vals)) <= ALIGN_MAX_SPREAD
    mismatches = cross_check_digits(rgb_img, digits, h, w, meta["angle"] if meta else 0)

    warns = [
        msg
        for cond, msg in [
            (not (EXPECTED_MIN_DIGITS <= len(digits) <= EXPECTED_MAX_DIGITS), f"จำนวนหลัก {len(digits)} นอกช่วง {EXPECTED_MIN_DIGITS}-{EXPECTED_MAX_DIGITS}"),
            (digits[0]["digit"] == 0, "หลักแรกเป็น 0 — อาจเกินมา 1 หลัก"),
            (mean_conf < CONF_RELIABLE, f"mean conf ต่ำ {mean_conf:.2f} — ภาพอาจเบลอ/เอียง"),
            (flip["warned"], f"อาจกลับหัว! หมุน 180° ได้ {flip['anti_reading']} ({flip['anti_confidence']:.2f}) — ตรวจภาพก่อนบันทึก"),
            (not align_ok, "กล่องไม่เรียงแนว — อาจเป็นป้าย/วันที่"),
        ]
        if cond
    ]
    warns += [f"หลักที่ {d['position']} ({d['digit']}) conf ต่ำ {d['confidence']:.2f} — ควรตรวจด้วยตา" for d in digits if not d["reliable"]]
    warns += [f"หลักที่ {m['position']}: YOLO {m['yolo_digit']} vs SigLIP {m['siglip_digit']} ({m['siglip_confidence']:.2f})" for m in mismatches]

    return {
        "reading": "".join(str(d["digit"]) for d in digits),
        "digits": digits,
        "mean_confidence": round(mean_conf, 4),
        "meter_check": meter,
        "processing": {"best": meta},
        "warnings": warns,
        "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
    }
```

---

### 2.2 การสร้าง REST API ด้วย FastAPI (⭐ Core)

เรานำฟังก์ชัน `read_meter` มาเปิดให้บริการผ่าน REST API เพื่อให้ระบบอื่นสามารถเรียกใช้ผ่าน HTTP ได้:

```python
# 📍 main.py — FastAPI Application
app = FastAPI(
    title="Meter Reader API",
    version="1.1",
    description="API อ่านเลขมิเตอร์น้ำอัตโนมัติ (Intuitive Functional Pipeline)",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

@app.get("/api/health")
def health() -> dict[str, Any]:
    """ตรวจสอบสถานะการทำงานของ API และโมเดล"""
    return {
        "status": "ok",
        "device": DEVICE,
        "yolo_loaded": _yolo is not None,
        "siglip_loaded": _siglip is not None,
    }

@app.post("/api/read-meter")
async def read_meter_endpoint(file: UploadFile = File(...)) -> dict[str, Any]:
    """รับไฟล์ภาพและประมวลผลผ่าน Threadpool (ไม่บล็อก Event Loop)"""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="ชนิดไฟล์ไม่รองรับ")

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        arr = np.asarray(img.convert("RGB"))
    except Exception:
        raise HTTPException(status_code=422, detail="อ่านไฟล์ภาพไม่ได้")

    return await run_in_threadpool(read_meter, arr)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
```

---

### 2.3 การสร้าง Web Interface ด้วย Gradio (`gradio_app.py`)

Gradio ช่วยให้เราสร้างหน้าเว็บ Interactive ได้อย่างรวดเร็ว โดยเรียกใช้ API ที่เราสร้างไว้ใน `main.py`:

```python
# 📍 gradio_app.py — Gradio Interface
import io
import cv2
import gradio as gr
import httpx
import numpy as np
from PIL import Image

API_URL = "http://127.0.0.1:8000"
READ_ENDPOINT = f"{API_URL}/api/read-meter"
HEALTH_ENDPOINT = f"{API_URL}/api/health"

def fetch_health() -> str:
    """เช็คสถานะการเชื่อมต่อกับ Backend"""
    try:
        data = httpx.get(HEALTH_ENDPOINT, timeout=10).json()
        return (f"API: ok | device: {data['device']} | "
                f"YOLO: {'พร้อม' if data['yolo_loaded'] else 'ยังไม่โหลด'} | "
                f"SigLIP: {'พร้อม' if data['siglip_loaded'] else 'ยังไม่โหลด'}")
    except Exception as exc:
        return f"API ไม่พร้อม ({exc}) - กรุณารัน `uv run python main.py` ก่อน"

def predict(image: Image.Image | None):
    """ส่งภาพไปยัง API และแสดงผลลัพธ์"""
    if image is None:
        raise gr.Error("กรุณาเลือกภาพมิเตอร์ก่อน")

    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=95)
    buf.seek(0)

    try:
        resp = httpx.post(
            READ_ENDPOINT,
            files={"file": ("meter.jpg", buf, "image/jpeg")},
            timeout=180,
        )
    except httpx.HTTPError as exc:
        raise gr.Error(f"เชื่อมต่อ API ไม่ได้: {exc}")

    if resp.status_code != 200:
        raise gr.Error(f"API ตอบกลับ {resp.status_code}: {resp.text}")

    data = resp.json()
    reading = data.get("reading", "")
    mean_conf = data.get("mean_confidence", 0.0)
    warnings = data.get("warnings", [])

    warn_text = "\n".join(f"- ⚠️ {w}" for w in warnings) if warnings else "✅ ไม่พบข้อผิดพลาด"

    return reading, f"{mean_conf:.2%}", warn_text

# สร้างหน้าเว็บ
with gr.Blocks(title="Water Meter Reader") as demo:
    gr.Markdown("# 💧 ระบบอ่านเลขมิเตอร์น้ำอัตโนมัติ (Water Meter Reader)")

    with gr.Row():
        status_box = gr.Textbox(value=fetch_health, label="สถานะระบบ", interactive=False)
        refresh_btn = gr.Button("🔄 เช็คสถานะ", size="sm")
        refresh_btn.click(fn=fetch_health, outputs=status_box)

    with gr.Row():
        with gr.Column():
            input_img = gr.Image(type="pil", label="อัปโหลดภาพมิเตอร์น้ำ")
            submit_btn = gr.Button("🔍 เริ่มอ่านเลขมิเตอร์", variant="primary")

        with gr.Column():
            reading_out = gr.Textbox(label="ตัวเลขที่อ่านได้", scale=2)
            conf_out = gr.Textbox(label="ความมั่นใจเฉลี่ย")
            warn_out = gr.Markdown(label="คำเตือนและการตรวจสอบ")

    submit_btn.click(
        fn=predict,
        inputs=[input_img],
        outputs=[reading_out, conf_out, warn_out],
    )

if __name__ == "__main__":
    demo.launch(server_port=7860)
```

---

### 2.4 การรัน ทดสอบ และคู่มือวิเคราะห์แก้ปัญหา (Testing & Troubleshooting)

#### 🚀 วิธีการทดสอบระบบ:
1. เปิด Terminal 1: `uv run python main.py`
2. เปิด Terminal 2: `uv run python gradio_app.py`
3. เปิดเบราว์เซอร์: [http://127.0.0.1:7860](http://127.0.0.1:7860)

---

#### 🛠️ คู่มือวิเคราะห์และแก้ปัญหา (Troubleshooting Matrix)

| อาการที่พบ (Symptom) | สาเหตุที่เป็นไปได้ (Cause) | สิ่งที่ควรตรวจสอบ (Check) | วิธีแก้ไข (Action) | ผลลัพธ์ที่ควรได้ (Expected) |
|---|---|---|---|---|
| **ตอบว่า "ภาพนี้ไม่ใช่มิเตอร์น้ำ"** | SigLIP2 ให้คะแนนความมั่นใจต่ำกว่า 0.50 | ค่าใน `meter_check.confidence` | ครอปภาพให้เห็นหน้าปัดมิเตอร์ชัดขึ้น หรือปรับลด `METER_VERIFY_CONF = 0.40` ใน `main.py` | AI ยืนยันว่าเป็นมิเตอร์น้ำและเข้าสู่ขั้นตอนอ่านตัวเลข |
| **ตัวเลขหายไปบางหลัก (เช่น 5 หลักอ่านได้ 4 หลัก)** | ตัวเลขจาง แสงสะท้อน หรือโมเดลมั่นใจต่ำกว่า 0.35 | ตรวจดูว่าหลักที่หายไปมีความสว่างน้อยหรือไม่ | ปรับลด `YOLO_CONF = 0.30` หรือทดสอบเปิดฟิลเตอร์ `histeq` | ตรวจพบตัวเลขครบทุกหลักบนหน้าปัด |
| **อ่านได้เลขกลับหัว เช่น 9 เป็น 6** | ภาพถ่ายคว่ำ 180° และไม่มีทศนิยมสีแดงให้สังเกต | ตรวจสอบที่กล่องคำเตือน `warnings` | ระบบจะแจ้งเตือน `⚠️ อาจกลับหัว` เพื่อให้เจ้าหน้าที่ตรวจสอบด้วยตาก่อนบันทึก | มีข้อความแจ้งเตือนความเสี่ยงชัดเจน |
| **AI ไปอ่านป้ายวันที่ข้างตัวเรือน** | มีตัวเลขพิมพ์ในแนวตั้งบนตัวถังมิเตอร์ | ตรวจสอบค่าพิกัด `bbox` ของตัวเลข | ฟังก์ชัน `is_vertical()` จะคำนวณ `height_span >= width_span` และตัดทิ้งให้อัตโนมัติ | อ่านเฉพาะแถวตัวเลขมิเตอร์แนวนอน |
| **หน้าเว็บขึ้น "API ไม่พร้อม"** | Backend ยังไม่ได้เริ่มทำงาน หรือรันผิดพอร์ต | ตรวจดู Terminal 1 ว่า Uvicorn ทำงานอยู่หรือไม่ | รันคำสั่ง `uv run python main.py` ที่เทอร์มินัล 1 | หน้าเว็บขึ้นสถานะ `API: ok` |

---

### 2.5 การฝึกโมเดลด้วยตัวเอง (🧠 Training Your Own Model — Advanced / Optional)

> [!NOTE]
> **ข้ามส่วนนี้ได้:** หากต้องการใช้งานระบบ คุณมีไฟล์โมเดล `weights/MeterOCR.pt` พร้อมใช้งานอยู่แล้ว หัวข้อนี้จำเป็นเฉพาะผู้ที่ต้องการฝึกฝนโมเดลด้วยชุดข้อมูลของตนเองเท่านั้น

1. สมัครบัญชีฟรีที่ [Roboflow](https://app.roboflow.com) และสร้าง Dataset ตีกรอบระบุ Class ตัวเลข $0-9$
2. ส่งออกชุดข้อมูลในรูปแบบ YOLO Format
3. รันสคริปต์ฝึกโมเดลบน Google Colab หรือเครื่องที่มี GPU:

```python
# 📍 train_colab.ipynb — ฝึกฝนโมเดล YOLO
from ultralytics import YOLO

# โหลด Base Model
model = YOLO("yolo11n.pt")

# เริ่มต้นการฝึกฝน 100 รอบ (Epochs)
model.train(
    data="path/to/dataset/data.yaml",
    epochs=100,
    imgsz=960,
    batch=16,
    device=0,
    name="meter_ocr",
)
```

หลังฝึกเสร็จ ให้นำไฟล์ `runs/detect/meter_ocr/weights/best.pt` มาวางแทนที่ `weights/MeterOCR.pt`

---

### 2.6 ข้อควรพิจารณาก่อนการใช้งานจริง (Production Readiness)

1. **สิทธิ์การใช้งาน (License):** YOLO (Ultralytics) ใช้ AGPL-3.0 สำหรับ Open Source หรือ Commercial License สำหรับการค้า, SigLIP2 อยู่ภายใต้ Apache 2.0
2. **ความเป็นส่วนตัวของข้อมูล (PDPA):** ภาพถ่ายมิเตอร์น้ำที่ติดบ้านเรือนหรือเลขทะเบียนผู้ใช้น้ำ ควรกำหนดระยะเวลาลบไฟล์ชั่วคราว (Retention Policy) ทันทีหลังประมวลผลเสร็จ
3. **การประมวลผลบนคลาวด์/เซิร์ฟเวอร์:** หากต้องการความเร็วสูง แนะนำให้ติดตั้งไดรเวอร์ NVIDIA CUDA ซึ่งจะช่วยลดเวลาประมวลผลเหลือเพียง **50–150 ms ต่อภาพ**

---

### 📋 ตรวจสอบความเข้าใจบทที่ 2

- [ ] ฉันเข้าใจการเชื่อมต่อระหว่าง Gradio Frontend (พอร์ต 7860) และ FastAPI Backend (พอร์ต 8000)
- [ ] ฉันเข้าใจว่าทำไมต้องใช้ `run_in_threadpool` เพื่อไม่ให้งานประมวลผลภาพบล็อก Event Loop ของเซิร์ฟเวอร์
- [ ] ฉันสามารถวิเคราะห์และแก้ไขปัญหาเมื่อโมเดลอ่านค่าผิดพลาดตามตาราง Troubleshooting ได้

---

## 📖 อภิธานศัพท์ (Glossary)

รวบรวมคำศัพท์ภาษาอังกฤษทางเทคนิคทั้งหมดที่ปรากฏในคู่มือฉบับนี้:

### 1. หมวดปัญญาประดิษฐ์และการเรียนรู้เชิงลึก (AI & Deep Learning)
* **Annotation (การกำกับข้อมูล):** กระบวนการตีกรอบและระบุค่าของตัวเลขในภาพเพื่อสร้าง Dataset
* **Bounding Box (`bbox`):** กรอบสี่เหลี่ยมพิกัด `[x1, y1, x2, y2]` ล้อมรอบตำแหน่งของตัวเลขแต่ละหลัก
* **CNN (Convolutional Neural Network):** โครงข่ายประสาทเทียมแบบคอนโวลูชันที่ออกแบบมาเพื่อวิเคราะห์ภาพถ่าย
* **Confidence Score:** ค่าความเชื่อมั่น (0.00 – 1.00) ที่โมเดล AI มั่นใจในคำตอบ
* **Cross-check:** กระบวนการตรวจทานซ้ำข้ามโมเดล (ใช้ SigLIP2 ตรวจทานตัวเลขที่ YOLO มั่นใจต่ำ)
* **Dataset:** ชุดข้อมูลภาพถ่ายและไฟล์กำกับพิกัดที่ใช้สำหรับการฝึกฝนโมเดล
* **Heuristic:** กฎการตัดสินใจเชิงตรรกะที่สร้างขึ้นจากพฤติกรรมจริง (เช่น หลักทศนิยมสีแดงต้องอยู่ขวาสุด)
* **Intersection over Union (IoU):** อัตราส่วนพื้นที่ทับซ้อนของ 2 กล่อง ใช้สำหรับตัดกล่องที่ซ้ำซ้อน
* **Lazy Loading:** เทคนิคการชะลอการโหลดโมเดลเข้าหน่วยความจำจนกว่าจะมีการเรียกใช้งานครั้งแรก เพื่อประหยัด RAM
* **mAP (Mean Average Precision):** ดัชนีชี้วัดความแม่นยำรวมของโมเดล Object Detection
* **Model Inference:** กระบวนการนำภาพส่งเข้าไปให้โมเดล AI ประมวลผลและส่งผลลัพธ์ออกมา
* **Non-Maximum Suppression (NMS / Dedup):** อัลกอริทึมคัดเลือกเฉพาะกล่องตรวจจับที่ดีที่สุด และกำจัดกล่องซ้ำ
* **OCR (Optical Character Recognition):** เทคโนโลยีการอ่านและแปลงภาพตัวเลขให้ออกมาเป็นข้อความดิจิทัล
* **Roboflow:** แพลตฟอร์มคลาวด์สำหรับจัดการชุดข้อมูลภาพ Computer Vision
* **SigLIP / SigLIP2:** โมเดล Vision-Language ขั้นสูงจาก Google สำหรับทำความเข้าใจภาพคู่กับข้อความ
* **Text Prompt:** ข้อความคำสั่งภาษาธรรมชาติที่ป้อนให้กับโมเดล (เช่น `"water meter"`)
* **YOLO (You Only Look Once):** สถาปัตยกรรมโมเดล Object Detection ความเร็วสูงสำหรับหาตำแหน่งตัวเลข
* **Zero-shot Classification:** การจำแนกประเภทภาพตามคำอธิบายข้อความโดยไม่ต้องฝึกฝนโมเดลด้วยภาพตัวอย่างนั้นมาก่อน

### 2. หมวดการประมวลผลภาพดิจิทัล (Digital Image Processing & OpenCV)
* **CLAHE (Contrast Limited Adaptive Histogram Equalization):** เทคนิคปรับสมดุลแสงเฉพาะจุดเพื่อดึงรายละเอียดในเงามืด
* **Color Spaces (ระบบสี):**
  * **RGB / BGR:** แดง-เขียว-น้ำเงิน (OpenCV เรียงลำดับช่องสีเป็น BGR เป็นค่าเริ่มต้น)
  * **LAB:** แยกช่องความสว่าง (L) ออกจากช่องสี (A, B) เหมาะสำหรับการปรับคอนทราสต์ด้วย CLAHE
  * **YCrCb:** แยกช่องสัญญาณความสว่าง (Y) ออกจากช่องสัญญาณสี (Cr, Cb) เหมาะสำหรับการทำ Histogram Equalization
  * **HSV:** ระบบสี Hue-Saturation-Value เหมาะสำหรับการตรวจจับเฉดสี เช่น สีแดงของหลักทศนิยม
* **Coordinate Remapping:** การแปลงพิกัดจุดเรขาคณิต $(X, Y)$ จากภาพที่หมุนกลับสู่พิกัดเดิมของภาพต้นฉบับ
* **Histogram Equalization (HistEq):** เทคนิคการเกลี่ยและกระจายค่าความสว่างของภาพให้สมดุลทั่วทั้งภาพ
* **Image Preprocessing:** กระบวนการปรับแต่งภาพเบื้องต้น (เช่น หมุน ปรับแสง) ก่อนส่งให้โมเดล AI
* **Mirror Check (Flip Guard):** กลไกตรวจสอบภาพกลับหัว 180° โดยเปรียบเทียบตัวเลขสมมาตร ($6 \leftrightarrow 9, 2 \leftrightarrow 5, 0, 1, 8$)
* **OpenCV (`cv2`):** ไลบรารีมาตรฐานระดับโลกสำหรับการประมวลผลภาพ
* **ROI (Region of Interest):** พื้นที่เป้าหมายเฉพาะส่วนบนภาพที่เราสนใจ (เช่น กรอบตัวเลขมิเตอร์)
* **Span-based Alignment ($\Delta X$ vs $\Delta Y$):** การคำนวณระยะกว้างเทียบกับระยะสูงเพื่อแยกแถวแนวนอนออกจากแนวตั้ง

### 3. หมวดสถาปัตยกรรมซอฟต์แวร์และเว็บ (Software Architecture & Web)
* **CORS (Cross-Origin Resource Sharing):** มาตรการความปลอดภัยของเว็บเบราว์เซอร์ที่ควบคุมการเรียกใช้ API ข้ามโดเมน
* **CUDA / GPU:** สถาปัตยกรรมการประมวลผลบนการ์ดจอ NVIDIA สำหรับเร่งความเร็วโมเดล Deep Learning
* **Endpoint:** จุดเชื่อมต่อ URL ปลายทางของ API สำหรับรับคำขอและส่งข้อมูลกลับ (เช่น `/api/read-meter`)
* **FastAPI:** เว็บเฟรมเวิร์กภาษา Python สำหรับสร้าง REST API ความเร็วสูง
* **Gradio:** ไลบรารีสำหรับสร้างหน้าเว็บส่วนติดต่อผู้ใช้ (Web UI) แบบ Interactive ได้อย่างรวดเร็ว
* **JSON (JavaScript Object Notation):** รูปแบบมาตรฐานในการแลกเปลี่ยนข้อมูลแบบข้อความที่มีโครงสร้าง Key-Value
* **Payload:** ส่วนของข้อมูลสำคัญที่ส่งไปในคำขอหรือตอบกลับมาจาก API
* **PDPA (Personal Data Protection Act):** กฎหมายคุ้มครองข้อมูลส่วนบุคคลที่เกี่ยวข้องกับการจัดเก็บภาพถ่าย
* **REST API (Representational State Transfer API):** สถาปัตยกรรมการสื่อสารระหว่างระบบผ่านโปรโตคอล HTTP
* **Threadpool Execution:** การแยกงานประมวลผลหนักไปรันบนเธรดเบื้องหลัง เพื่อไม่ให้บล็อก Event Loop
* **`uv`:** เครื่องมือจัดการแพ็กเกจและสภาพแวดล้อม Python ความเร็วสูง พัฒนาด้วยภาษา Rust
* **Virtual Environment (`venv`):** สภาพแวดล้อมเสมือนที่แยกชุด Library ของโปรเจกต์ออกจากระบบหลัก

---

## 📚 บรรณานุกรมและเอกสารอ้างอิง (References)

1. **Tschannen, M., et al. (2025).** *SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding.* Google Research.
2. **Li, X., et al. (2020).** *Water Meter Reading Recognition Based on Computer Vision and Deep Learning.* IEEE Access.
3. **Ultralytics (2024).** *YOLOv8 & YOLO11: Real-Time Object Detection and Image Segmentation.* [https://docs.ultralytics.com](https://docs.ultralytics.com)
4. **FastAPI Documentation (2024).** *FastAPI framework, high performance, easy to learn, fast to code.* [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
5. **Gradio Documentation (2024).** *Build and Share Delightful Machine Learning Apps.* [https://gradio.app](https://gradio.app)
