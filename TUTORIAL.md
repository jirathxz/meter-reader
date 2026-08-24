# 📖 คู่มือการเรียนรู้: ระบบอ่านเลขมิเตอร์น้ำอัตโนมัติด้วย AI
## Deep Learning & Computer Vision Water Meter OCR Tutorial

> **สำหรับนักศึกษาและผู้เริ่มต้น:** เอกสารนี้ออกแบบมาเพื่อพาคุณสร้างและทำความเข้าใจระบบอ่านเลขมิเตอร์น้ำอัตโนมัติทีละระดับ โดยอธิบาย **"ทำไมต้องทำ"** ก่อน **"ทำอย่างไร"** สามารถหยุดพักและทดลองรันระบบได้ตลอดเวลา

---

## 🧭 แผนผังการเรียนรู้ 4 ระดับ (Learning Roadmap)

```text
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ Quick Start: รันระบบและทดลองอ่านภาพมิเตอร์ทันทีใน 5 นาที        │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 🚀 Level 1: เริ่มต้นและรันระบบ (สำหรับผู้เริ่มต้น — ยังไม่ต้องรู้ AI ลึก)  │
│   • เตรียม Environment (uv) • ติดตั้ง Library • ทดสอบรันภาพตัวอย่าง │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 🧠 Level 2: เข้าใจ Pipeline และการประมวลผล (Computer Vision & AI)│
│   • Preprocessing • YOLO Detection • Remapping • Safety Guards  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 🌐 Level 3: การพัฒนา API และหน้าเว็บ UI (FastAPI & Gradio)       │
│   • REST API Backend • Interactive Web Interface                │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 🎓 Level 4: การฝึกโมเดลด้วยตัวเองและขั้นสูง (Training & Advanced) │
│   • Roboflow Dataset • YOLO Training • Troubleshooting Matrix   │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start (ทดลองรันระบบทันทีใน 5 นาที)

หากคุณต้องการทดลองใช้งานระบบทันทีโดยใช้โมเดลสำเร็จรูปที่มีอยู่แล้ว (`weights/MeterOCR.pt`):

```powershell
# 1. สร้าง Environment และติดตั้ง Library (ใช้ Python 3.11)
uv venv --python 3.11
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt

# 2. รัน FastAPI Backend (เปิดทิ้งไว้ที่เทอร์มินัล 1)
uv run python main.py

# 3. รัน Gradio Frontend (เปิดที่เทอร์มินัล 2)
uv run python gradio_app.py
```
เปิดเบราว์เซอร์ที่ [http://127.0.0.1:7860](http://127.0.0.1:7860) แล้วลากรูปภาพจากโฟลเดอร์ `meter_img/` มาวางเพื่อดูผลลัพธ์ได้ทันที!

> 💡 **ต้องการเข้าใจว่าแต่ละขั้นตอนทำงานอย่างไร?** เชิญเริ่มเรียนรู้จาก **Level 1** ด้านล่างได้เลยครับ

---

# 🚀 Level 1: เริ่มต้นและรันระบบ

> **เป้าหมาย Level 1:** สามารถติดตั้งและรันระบบจนได้ผลลัพธ์จากภาพตัวอย่าง โดยยังไม่จำเป็นต้องเข้าใจคณิตศาสตร์หรือโครงข่ายประสาทเทียมเชิงลึก

---

### 1.1 ระบบนี้ทำอะไร? (WHAT)

ระบบนี้ทำหน้าที่อ่านตัวเลข 0–9 จากภาพถ่ายหน้าปัด **มิเตอร์น้ำ (Water Meter)** โดยอัตโนมัติ ซึ่งในชีวิตจริงภาพถ่ายมักมีปัญหา:
* ภาพเอียง ตะแคง 90° หรือกลับหัว 180°
* มีแสงสะท้อนจากกระจก ตัวเลขเลือนราง หรือมีคราบน้ำ
* มีตัวเลขอื่นที่ไม่ใช่ค่ามิเตอร์ เช่น วันที่ผลิต หรือเลขซีเรียลปั๊มแนวตั้ง

ระบบนี้จะทำการ **ปรับปรุงภาพ ค้นหาทิศทางที่ถูกต้อง ตรวจจับตัวเลขทุกหลัก และตรวจสอบความปลอดภัย** เพื่อให้ได้ตัวเลขมิเตอร์ที่ถูกต้องแม่นยำ

---

### 1.2 ภาพรวมการทำงาน (HOW IT WORKS)

เมื่อเราป้อนภาพถ่ายเข้าไป 1 ภาพ ระบบจะประมวลผลผ่าน 4 ด่านตรวจ:

```text
[ 📷 ภาพถ่าย ]
      ↓
[ 1. SigLIP2 ]  ──> ภาพนี้ใช่มิเตอร์น้ำจริงไหม? (ถ้าไม่ใช่ ปฏิเสธทันที)
      ↓
[ 2. OpenCV ]   ──> ลองหมุน 4 ทิศ (0°, 90°, 180°, 270°) × ปรับแสง 3 แบบ
      ↓
[ 3. YOLO26 ]   ──> ตรวจหากล่องตัวเลข 0-9 ทุกหลักบนหน้าปัด
      ↓
[ 4. Safety ]   ──> กรองเลขแนวตั้ง + ตรวจกลับหัว + ตรวจหลักทศนิยมสีแดง
      ↓
[ ✅ ตัวเลขมิเตอร์ เช่น "05715" พร้อมคำเตือนความเสี่ยง ]
```

---

### 1.3 สิ่งที่ต้องเตรียม (Prerequisites)

1. **Python 3.11:** (รองรับ 3.10 – 3.12) ภาษาหลักที่ใช้พัฒนา
2. **`uv` (แนะนำ):** เครื่องมือจัดการ Python ยุคใหม่ ติดตั้ง Library ได้เร็วกว่า `pip` 10–100 เท่า
   *(หากยังไม่มี `uv` สามารถดาวน์โหลดได้ที่ [astral.sh/uv](https://docs.astral.sh/uv/))*

---

### 1.4 เตรียม Virtual Environment

> **ทำไมต้องทำ (WHY)?:** เพื่อสร้าง "กล่องเครื่องมือเฉพาะงาน" แยกไลบรารีของโปรเจกต์นี้ออกจากเครื่องคอมพิวเตอร์ของคุณ ป้องกันปัญหาเวอร์ชันตีกับโปรเจกต์อื่น

เปิด Terminal ในโฟลเดอร์ `meter-reader/` แล้วรันคำสั่ง:

```powershell
uv venv --python 3.11
```

**เปิดใช้งาน Virtual Environment:**
* **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
* **Windows (Command Prompt):** `.venv\Scripts\activate.bat`
* **macOS / Linux:** `source .venv/bin/activate`

**ผลลัพธ์ที่ควรเห็น (Expected Result):**
มีโฟลเดอร์ชื่อ `.venv/` ปรากฏขึ้นในโปรเจกต์ และที่หน้า Terminal จะมีข้อความ `(.venv)` นำหน้าบรรทัดคำสั่ง

---

### 1.5 ติดตั้ง Dependencies

> **ทำไมต้องทำ (WHY)?:** เพื่อติดตั้งเครื่องมือภายนอก เช่น OpenCV (แต่งภาพ), PyTorch/Ultralytics (สมอง AI), และ FastAPI/Gradio (ระบบเว็บ)

รันคำสั่งติดตั้งแพ็กเกจจากไฟล์ `requirements.txt`:

```powershell
uv pip install -r requirements.txt
```

**ผลลัพธ์ที่ควรเห็น (Expected Result):**
`uv` จะดาวน์โหลดและติดตั้ง Library ทั้งหมดเสร็จสิ้นภายในเวลาไม่กี่วินาที พร้อมขึ้นข้อความ `Installed xx packages`

---

### 1.6 ตรวจสอบความถูกต้องของการติดตั้ง

> **ทำไมต้องทำ (WHY)?:** เพื่อยืนยันว่าโปรแกรมมองเห็น Library และไฟล์โมเดล AI ครบถ้วนก่อนสั่งรันจริง

สร้างคำสั่งทดสอบสั้นๆ ใน Terminal:

```powershell
uv run python -c "import cv2, torch, ultralytics; print('✅ PyTorch version:', torch.__version__, '| CUDA Available:', torch.cuda.is_available())"
```

**ผลลัพธ์ที่ควรเห็น (Expected Result):**
```text
✅ PyTorch version: 2.x.x | CUDA Available: True (หรือ False หากใช้ CPU)
```

---

### 1.7 สั่งรันระบบ (Running the Application)

ระบบแบ่งออกเป็น 2 ส่วนที่ทำงานร่วมกัน:

#### 1. รัน Backend API (เปิดทิ้งไว้ที่เทอร์มินัลที่ 1):
```powershell
uv run python main.py
```
**ผลลัพธ์ที่ควรเห็น:**
```text
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```
*(คุณสามารถเปิดดู Interactive API Docs ได้ที่ [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs))*

#### 2. รัน Frontend Web UI (เปิดที่เทอร์มินัลที่ 2):
```powershell
uv run python gradio_app.py
```
**ผลลัพธ์ที่ควรเห็น:**
```text
Running on local URL:  http://127.0.0.1:7860
```

---

### 1.8 ทดลองอ่านภาพมิเตอร์ตัวอย่าง

เปิดเบราว์เซอร์ไปที่ [http://127.0.0.1:7860](http://127.0.0.1:7860):
1. กดปุ่ม **"อัปโหลดภาพมิเตอร์น้ำ"** แล้วเลือกภาพจากโฟลเดอร์ `meter_img/` (เช่น `Water+meter.jpg` หรือ `bangkok-...-212500741.jpg`)
2. กดปุ่ม **"🔍 เริ่มอ่านเลขมิเตอร์"**

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

---

### 1.9 การอ่านและตีความผลลัพธ์

เมื่อส่งภาพผ่าน API ผลลัพธ์จะตอบกลับมาในรูปแบบ JSON ที่เข้าใจง่าย:

```json
{
  "reading": "05715",
  "digits": [
    {"position": 1, "digit": 0, "confidence": 0.89, "bbox": [120, 45, 150, 95], "reliable": true},
    {"position": 2, "digit": 5, "confidence": 0.94, "bbox": [152, 45, 182, 95], "reliable": true}
  ],
  "mean_confidence": 0.911,
  "meter_check": {
    "verified": true,
    "predicted_class": "water meter"
  },
  "warnings": [
    "หลักแรกเป็น 0 — อาจเกินมา 1 หลัก"
  ],
  "elapsed_ms": 135.2
}
```

> **คำอธิบายผลลัพธ์:**
> * `reading`: ตัวเลขหน้าปัดที่อ่านได้เรียงจากซ้ายไปขวา
> * `confidence` / `mean_confidence`: **ค่าความมั่นใจ** ของโมเดล (0.00 – 1.00 ยิ่งใกล้ 1.00 ยิ่งมั่นใจสูง)
> * `bbox`: **Bounding Box** พิกัด `[x1, y1, x2, y2]` ล้อมรอบตัวเลขแต่ละหลัก
> * `warnings`: คำเตือนข้อสังเกตเพื่อช่วยให้เจ้าหน้าที่ตรวจสอบด้วยตาซ้ำ

---

### 📋 ตรวจสอบความเข้าใจ Level 1

ก่อนไปต่อใน Level 2 ลองตอบคำถามเหล่านี้กับตัวเอง:
- [ ] ฉันสามารถสร้าง Virtual Environment ด้วย `uv venv` และเปิดใช้งานได้แล้ว
- [ ] ฉันเข้าใจว่าระบบนี้ใช้โมเดลอ่านตัวเลขมิเตอร์น้ำและมีระบบแจ้งเตือนความเสี่ยง
- [ ] ฉันสามารถรันทั้ง `main.py` (Backend) และ `gradio_app.py` (Frontend) จนแสดงหน้าเว็บได้สำเร็จ
- [ ] ฉันสามารถทดลองอัปโหลดภาพใน `meter_img/` และเห็นผลลัพธ์ตัวเลขบนหน้าจอแล้ว

---

# 🧠 Level 2: เข้าใจ Pipeline และการประมวลผลภาพ

> **เป้าหมาย Level 2:** เข้าใจการเดินทางของข้อมูล (Data Flow) ว่าคอมพิวเตอร์แปลงภาพถ่าย 1 ใบให้ออกมาเป็นตัวเลขได้อย่างไร ผ่านการผ่าดูโค้ดทีละฟังก์ชัน

---

### 2.1 แผนภาพการเดินทางของข้อมูล (Detailed Data Flow)

```text
Input Image (ภาพ RGB)
    │
    ▼
[ 1. check_water_meter ] ──> SigLIP2 ตรวจว่าเป็นภาพมิเตอร์น้ำจริงไหม?
    │ (ถ้าใช่ ไปต่อ)
    ▼
[ 2. Orientation & Filter Search ]
    ├─ หมุน 4 ทิศ: 0°, 90°, 180°, 270° (rotate_image)
    ├─ ปรับแสง 3 แบบ: Orig, CLAHE, HistEq (apply_prep)
    ▼
[ 3. detect_digits (YOLO) ] ──> ตรวจจับตัวเลข 0-9 ทุกมุม ทุกฟิลเตอร์
    │
    ▼
[ 4. dedup_detections (IoU) ] ──> ตัดกล่องที่ตีกรอบซ้อนทับกันทิ้ง
    │
    ▼
[ 5. is_vertical ] ──> กรองคอลัมน์แนวตั้งทิ้ง (หน้าปัดมิเตอร์ต้องเป็นแนวนอน)
    │
    ▼
[ 6. red_ratio & Scoring ] ──> ตรวจหลักทศนิยมสีแดง (ต้องอยู่ขวาสุด) + ให้คะแนนมุมที่ดีที่สุด
    │
    ▼
[ 7. remap_bbox ] ──> แปลงพิกัดกล่องจากภาพหมุน กลับมายังระนาบภาพเดิม
    │
    ▼
[ 8. Safety Guards ]
    ├─ flip_guard: ตรวจสอบการกลับหัว 180° แบบกระจกเงา
    └─ cross_check_digits: SigLIP2 ตรวจทานซ้ำเฉพาะหลักที่มั่นใจต่ำ (< 0.60)
    │
    ▼
Final Output (reading, digits, warnings, elapsed_ms)
```

---

### 2.2 โครงสร้างโค้ด (Code Architecture)

โค้ดใน `main.py` ถูกออกแบบโดย **แบ่งการทำงานออกเป็นฟังก์ชันย่อยตามหน้าที่อย่างเป็นเส้นตรง** เพื่อให้อ่านเข้าใจง่าย ทดสอบแยกชิ้นได้สะดวก และไม่มีความซับซ้อนของ Class หรือ OOP

---

### 2.3 ค่าคงที่ของระบบ (⚙️ Configuration)

อยู่ที่ส่วนบนสุดของ `main.py` เพื่อให้ปรับเปลี่ยนพฤติกรรมของระบบได้จากจุดเดียว:

```python
# ⭐ Core Settings
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
YOLO_MODEL = "weights/MeterOCR.pt"  # ไฟล์สมองกลอ่านตัวเลข
YOLO_IMGSZ = 960                   # ขนาดภาพที่ป้อนเข้าโมเดล (ภาพยิ่งใหญ่ ยิ่งเห็นเลขเล็กชัด)
YOLO_CONF = 0.35                   # เกณฑ์ความมั่นใจขั้นต่ำในการตรวจจับ
CONF_RELIABLE = 0.60               # ถ้าความมั่นใจเกิน 0.60 ถือว่าน่าเชื่อถือ
EXPECTED_MIN_DIGITS = 4            # มิเตอร์น้ำทั่วไปมีตัวเลข 4-9 หลัก
EXPECTED_MAX_DIGITS = 9

# ⚙️ Search Space & Safety
ROTATION_ANGLES = (0, 90, 180, 270)
PREP_LIST = ("orig", "clahe", "histeq")
ORIENT_MARGIN = 0.12               # มุมอื่นต้องชนะมุม 0° เกิน 0.12 จึงจะยอมเปลี่ยนมุม
FLIP_MAP = {0: 0, 1: 1, 2: 5, 5: 2, 6: 9, 8: 8, 9: 6} # ตารางเลขสมมาตรกลับหัว
```

---

### 2.4 การโหลดโมเดลแบบ Lazy Loading (⭐ Core)

#### Step 1 — Concept
> **ทำไมต้องทำ (WHY)?:** โมเดล AI มีขนาดใหญ่ (SigLIP2 ~800MB) หากโหลดทันทีที่เปิดไฟล์ โปรแกรมจะเปิดช้าและกิน RAM ตลอดเวลา เราจึงใช้เทคนิค **Lazy Loading** คือโหลดเข้าหน่วยความจำเมื่อมีภาพแรกส่งเข้ามาเท่านั้น

#### Step 2 — Simplified Example
```python
_model = None
def get_model():
    global _model
    if _model is None:
        _model = load_heavy_ai_model() # โหลดเฉพาะรอบแรก
    return _model
```

#### Step 3 — Real Implementation (`main.py`)
```python
_yolo = None
_siglip = None

def get_yolo() -> Any:
    global _yolo
    if _yolo is None:
        from ultralytics import YOLO
        _yolo = YOLO(YOLO_MODEL)
        _yolo.predict(np.zeros((640, 640, 3), dtype=np.uint8), verbose=False)
    return _yolo

def get_siglip() -> tuple[Any, Any]:
    global _siglip
    if _siglip is None:
        from transformers import AutoModel, AutoProcessor
        processor = AutoProcessor.from_pretrained(SIGLIP_MODEL)
        model = AutoModel.from_pretrained(SIGLIP_MODEL).to(DEVICE).eval()
        _siglip = (processor, model)
    return _siglip
```

---

### 2.5 การประมวลผลและปรับปรุงคุณภาพภาพ (⭐ Core: OpenCV)

```text
[ ภาพมืด/มีเงา ] ──> apply_prep(CLAHE) ──> [ ตัวเลขสว่างชัดเจน ดึงรายละเอียดในเงามืด ]
[ ภาพตะแคง 90° ] ──> rotate_image(90)   ──> [ ภาพตั้งตรงพร้อมให้อ่าน ]
```

#### 1. การหมุนภาพ (`rotate_image`)
* **Concept:** หมุนภาพตามเข็มนาฬิกาทีละ 90° ด้วยคำสั่งมาตรฐานของ OpenCV

```python
def rotate_image(img_bgr: np.ndarray, angle: int) -> np.ndarray:
    """หมุนภาพ 90°, 180°, 270° ตามเข็มนาฬิกา"""
    if angle == 90:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(img_bgr, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img_bgr
```

#### 2. การปรับคอนทราสต์แสง (`apply_prep`)
* **Concept:** ภาพมิเตอร์จริงมักมืดหรือมีเงาตกกระทบ:
  * **CLAHE:** ปรับสมดุลแสงเฉพาะจุดบนช่อง L (ความสว่าง) ในระบบสี LAB
  * **HistEq:** กระจายความสว่างทั่วทั้งภาพบนช่อง Y ในระบบสี YCrCb

```python
def apply_prep(img_bgr: np.ndarray, prep: str) -> np.ndarray:
    """ปรับแสง: CLAHE (เพิ่มคอนทราสต์เฉพาะจุด) หรือ HistEq (เกลี่ยแสงทั่วทั้งภาพ)"""
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

### 2.6 การแปลงพิกัดเรขาคณิตย้อนกลับ (🔧 Implementation: `remap_bbox`)

#### Step 1 — Concept
> **ทำไมต้องทำ (WHY)?:** เมื่อเราหมุนภาพ 90° เพื่ออ่านตัวเลข พิกัดกล่องสี่เหลี่ยมที่ YOLO หาได้จะอยู่บนระนาบของภาพหมุน หากเราต้องการนำกล่องนี้ไปวาดบนภาพต้นฉบับ เราต้อง **แปลงพิกัดจุด $(x, y)$ ย้อนกลับ**

```text
[ ภาพหมุน 90° ]                              [ ภาพต้นฉบับเดิม ]
(x=100, y=50) ─── remap_point(angle=90) ───> (x=50, y = Height - 100)
```

#### Step 2 — Real Implementation (`main.py`)
```python
def remap_point(x: float, y: float, angle: int, w: int, h: int) -> tuple[float, float]:
    """แปลงจุด 1 จุดจากภาพหมุน กลับสู่พิกัดภาพเดิม"""
    if angle == 90:
        return y, h - x      # หมุนขวา 90° -> แกนสลับ x=y, y=h-x
    if angle == 180:
        return w - x, h - y  # กลับหัว 180° -> x=w-x, y=h-y
    if angle == 270:
        return w - y, x      # หมุนซ้าย 90° -> แกนสลับ x=w-y, y=x
    return x, y

def remap_bbox(bbox: list[float], angle: int, w: int, h: int) -> list[float]:
    """แปลงจุดมุม 2 จุด แล้วหา min/max เพื่อสร้าง Bounding Box ในพิกัดภาพเดิม"""
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

### 2.7 การตรวจจับตัวเลขและการตัดกล่องซ้อน (⭐ Core: YOLO & IoU)

#### 1. ตรวจจับตัวเลขด้วย YOLO (`detect_digits`)
* **Concept:** ป้อนภาพเข้าโมเดล YOLO เพื่อดึงพิกัดกล่องและ Class ตัวเลข 0–9 แล้วเรียงลำดับจากซ้ายไปขวาตามแกน $X$

```python
def detect_digits(img_bgr: np.ndarray) -> list[dict[str, Any]]:
    """YOLO หาตัวเลข 0-9 เรียงจากซ้ายไปขวา"""
    res = get_yolo().predict(img_bgr, imgsz=YOLO_IMGSZ, conf=YOLO_CONF, device=DEVICE, verbose=False)
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

#### 2. ตัดกล่องที่ซ้อนทับกันด้วย IoU (`dedup_detections`)
* **IoU (Intersection over Union):** เปรียบเหมือนการดูว่ากระดาษสองแผ่นวางทับกันกี่เปอร์เซ็นต์ หากทับกันเกิน 45% ให้เลือกเก็บเฉพาะกล่องที่ AI มั่นใจที่สุดไว้เพียงกล่องเดียว

```python
def iou(box1: list[float], box2: list[float]) -> float:
    """คำนวณอัตราส่วนพื้นที่ทับซ้อนของ 2 กล่อง"""
    x1, y1 = max(box1[0], box2[0]), max(box1[1], box2[1])
    x2, y2 = min(box1[2], box2[2]), min(box1[3], box2[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    return (intersection / union) if union > 0 else 0.0

def dedup_detections(dets: list[dict[str, Any]], thresh: float = 0.45) -> list[dict[str, Any]]:
    """ตัดกล่องที่ซ้อนทับกันออก เหลือเฉพาะตัวที่มั่นใจสูงสุด"""
    kept: list[dict[str, Any]] = []
    for d in sorted(dets, key=lambda x: x["confidence"], reverse=True):
        if not any(iou(d["bbox"], k["bbox"]) > thresh for k in kept):
            kept.append(d)
    return sorted(kept, key=lambda x: x["center_x"])
```

---

### 2.8 การกรองคอลัมน์แนวตั้ง (⭐ Core: `is_vertical`)

#### Step 1 — Concept
> **ทำไมต้องทำ (WHY)?:** ตัวเรือนมิเตอร์น้ำมักมีตัวเลขวันที่ผลิตหรือซีเรียลนัมเบอร์ปั๊มเป็น **แนวตั้ง** หากไม่กรองออก AI อาจเผลอไปอ่านป้ายเหล่านั้นแทนตัวเลขมิเตอร์ แถวตัวเลขมิเตอร์น้ำจริงจะต้องวางตัวเป็น **แนวนอน** เสมอ ($\text{width\_span} > \text{height\_span}$)

```text
[ แถวแนวนอน: มิเตอร์จริง ]         [ คอลัมน์แนวตั้ง: วันที่/รุ่น ]
  ┌───┐ ┌───┐ ┌───┐ ┌───┐            ┌───┐
  │ 0 │ │ 5 │ │ 7 │ │ 1 │            │ 2 │
  └───┘ └───┘ └───┘ └───┘            └───┘
  ◄──── width_span ────►             ┌───┐
  (ความกว้าง > ความสูง = ผ่าน ✅)       │ 0 │ height_span
                                     └───┘ (ความสูง > ความกว้าง = ตัดทิ้ง ❌)
```

#### Step 2 — Real Implementation (`main.py`)
```python
def is_vertical(dets: list[dict[str, Any]], img_w: int, img_h: int) -> dict[str, Any]:
    """ตรวจว่าแถวตัวเลขเรียงเป็นแนวตั้งหรือไม่ (แนวนอน width_span ต้องมากกว่า height_span)"""
    if len(dets) < 2:
        return {"vertical": False}

    xs = [d["center_x"] / img_w for d in dets]
    ys = [d["center_y"] / img_h for d in dets]

    width_span = max(xs) - min(xs)   # ระยะกว้าง (ซ้ายสุดไปขวาสุด)
    height_span = max(ys) - min(ys)  # ระยะสูง (บนสุดไปล่างสุด)

    # ถ้าความสูงมากกว่าความกว้าง แสดงว่าเป็นคอลัมน์แนวตั้ง (ไม่ใช่แถวมิเตอร์)
    is_vert = (height_span >= width_span * 0.8) or (width_span <= 0.05 and height_span >= 0.08)
    return {"vertical": is_vert}
```

---

### 2.9 การค้นหามุมและฟิลเตอร์ที่ดีที่สุด (🧠 Advanced: `detect_digits_best`)

#### 1. ที่มาของปัญหา (Problem)
ภาพถ่ายจากผู้ใช้อาจถ่ายตะแคงมาในมุมใดก็ได้ (0°, 90°, 180°, 270°) และสภาพแสงแต่ละภาพก็แตกต่างกัน การใช้การหมุนมุมเดียวหรือฟิลเตอร์เดียวจึงไม่สามารถครอบคลุมภาพถ่ายทุกสถานการณ์ได้

#### 2. แนวคิดการแก้ไข (Solution Idea)
ทดลองนำภาพไปหมุน **4 ทิศทาง** และปรับแต่งแสง **3 รูปแบบ** รวมเป็น $4 \times 3 = 12$ รูปแบบ จากนั้นคำนวณคะแนนรวมของแต่ละรูปแบบ และเลือกชุดที่ได้คะแนนสูงสุด

#### 3. กฎการให้คะแนน (Scoring Algorithm & Margin Rule)
* **คะแนนพื้นฐาน:** $\text{Score} = \text{Mean Confidence} \times \text{Number of Digits}$
* **กฎสีแดงของหลักทศนิยม (`red_ratio`):** หลักทศนิยมสีแดงต้องอยู่ **ขวาสุด** ของหน้าปัดเสมอ หากพบสีแดงอยู่ทางซ้าย แสดงว่าภาพกำลังกลับหัว 180° จะถูกตัดคะแนนลงครึ่งหนึ่ง
* **Margin Rule:** มุมอื่น (90°, 180°, 270°) ต้องชนะมุมตั้งต้น (0°) เกิน `ORIENT_MARGIN = 0.12` จึงจะยอมเปลี่ยนทิศ เพื่อป้องกันการสลับมุมโดยไม่จำเป็นเมื่อคะแนนสูสีกัน

```python
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

    # Margin Rule: มุมอื่นต้องชนะมุม 0° เกินกำหนด จึงยอมสลับมุม
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

### 2.10 กลไกความปลอดภัยและความแม่นยำ (⭐ Core: Safety Guards)

#### 1. ยืนยันประเภทมิเตอร์ด้วย SigLIP2 (`check_water_meter`)
* **Zero-shot Classification:** ตรวจสอบว่าภาพนี้คือ `"water meter"` หรือไม่ หากเป็นมิเตอร์ไฟฟ้าหรือวัตถุอื่น ระบบจะปฏิเสธการอ่านทันที

#### 2. ป้องกันการอ่านเลขกลับหัวแบบกระจกเงา (`flip_guard`)
* **Concept:** ตัวเลขอารบิกมีความสมมาตรเมื่อหมุน 180° เช่น เลข 6 จะอ่านเป็น 9, เลข 2 จะอ่านเป็น 5, และเลข 0, 1, 8 จะยังคงรูปเดิม ฟังก์ชัน `flip_guard` จะหมุนภาพไปอีก 180° แล้วตรวจดูว่าผลลัพธ์ตรงกับตาราง `FLIP_MAP` หรือไม่ หากอ่านได้เลขกลับหัว จะส่งข้อความแจ้งเตือน `⚠️ อาจกลับหัว!`

```python
FLIP_MAP = {0: 0, 1: 1, 2: 5, 5: 2, 6: 9, 8: 8, 9: 6}

def flip_guard(rgb_img: np.ndarray, digits: list[dict[str, Any]], meta: dict[str, Any] | None) -> dict[str, Any]:
    """ตรวจสอบความสมมาตร 180° ป้องกันอ่านกลับหัว (Mirror Check)"""
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
```

#### 3. ตรวจทานซ้ำเฉพาะหลักที่มั่นใจต่ำ (`cross_check_digits`)
* ใช้ SigLIP2 ครอปเฉพาะกล่องตัวเลขที่ค่า Confidence ต่ำกว่า 0.60 เพื่ออ่านซ้ำอีกครั้ง หากผลลัพธ์ของ YOLO และ SigLIP2 ไม่ตรงกัน จะสร้างข้อความแจ้งเตือนเตือนเจ้าหน้าที่

---

### 📋 ตรวจสอบความเข้าใจ Level 2

- [ ] ฉันสามารถอธิบายได้ว่าทำไมต้องมี `remap_bbox` เมื่อหมุนภาพ
- [ ] ฉันเข้าใจว่า `is_vertical` ใช้หลักการ $\text{width\_span} > \text{height\_span}$ เพื่อกรองป้ายวันที่ออก
- [ ] ฉันเข้าใจว่าทำไมต้องตรวจหาสีแดงของหลักทศนิยม และตรวจการกลับหัว 180°
- [ ] ฉันเข้าใจบทบาทของ YOLO (หาตำแหน่งกล่องตัวเลข) และ SigLIP2 (คัดแยกภาพและตรวจทานซ้ำ)

---

# 🌐 Level 3: การพัฒนา REST API และ Web UI

> **เป้าหมาย Level 3:** นำ Pipeline ทั้งหมดมาประกอบเข้าด้วยกัน และเปิดให้บริการผ่าน Web Service (FastAPI) พร้อมสร้างหน้าเว็บส่วนติดต่อผู้ใช้ (Gradio)

---

### 3.1 การประกอบ Pipeline รวม (`read_meter`)

ฟังก์ชัน `read_meter(rgb_img)` ทำหน้าที่เป็นหัวหน้างาน เรียงลำดับการทำงานตั้งแต่รับภาพจนได้ผลลัพธ์พร้อมกล่องคำเตือน:

```python
def read_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    """รับภาพ RGB -> ประมวลผล 4 ขั้นตอน -> คืนค่าตัวเลขและคำเตือน"""
    t0 = perf_counter()
    h, w = rgb_img.shape[:2]

    # 1. ตรวจสอบชนิดมิเตอร์ (SigLIP2)
    meter = check_water_meter(rgb_img)
    if not meter["verified"]:
        return {
            "reading": "", "digits": [], "meter_check": meter, "processing": None,
            "warnings": [f"ภาพนี้ไม่ใช่มิเตอร์น้ำ ({meter['predicted_class']})"],
            "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
        }

    # 2. ค้นหาทิศและตรวจจับตัวเลข (YOLO26)
    dets, meta = detect_digits_best(rgb_img)
    if not dets:
        return {
            "reading": "", "digits": [], "meter_check": meter, "processing": meta,
            "warnings": ["ตรวจไม่พบตัวเลข"],
            "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
        }

    digits = [{
        "position": i, "digit": d["digit"], "confidence": round(d["confidence"], 4),
        "bbox": d["bbox"], "reliable": d["confidence"] >= CONF_RELIABLE,
    } for i, d in enumerate(dets, 1)]
    mean_conf = float(np.mean([d["confidence"] for d in digits]))

    # 3. กรองคอลัมน์แนวตั้ง
    if meta and meta["angle"] == 0 and is_vertical(dets, w, h)["vertical"]:
        return {
            "reading": "", "digits": [], "meter_check": meter, "processing": meta,
            "warnings": ["กล่องเรียงแนวตั้ง — ไม่ใช่ค่ามิเตอร์"],
            "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
        }

    # 4. ตรวจสอบความปลอดภัยและสร้างคำเตือน
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
        ] if cond
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

### 3.2 การสร้าง REST API ด้วย FastAPI

```python
# 📍 main.py — FastAPI Application
app = FastAPI(title="Meter Reader API", version="1.1")

# เปิด CORS เพื่อให้ Frontend เรียกใช้ API ข้ามพอร์ตได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}

@app.get("/api/health")
def health() -> dict[str, Any]:
    """Endpoint ตรวจสอบความพร้อมของเซิร์ฟเวอร์"""
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
```

---

### 3.3 การสร้าง Web Interface ด้วย Gradio (`gradio_app.py`)

```python
# 📍 gradio_app.py — Interactive Web UI
import io, cv2, gradio as gr, httpx, numpy as np
from PIL import Image

API_URL = "http://127.0.0.1:8000"
READ_ENDPOINT = f"{API_URL}/api/read-meter"
HEALTH_ENDPOINT = f"{API_URL}/api/health"

def fetch_health() -> str:
    try:
        data = httpx.get(HEALTH_ENDPOINT, timeout=10).json()
        return f"API: พร้อมใช้งาน | Device: {data['device']}"
    except Exception:
        return "API ไม่พร้อม — กรุณารัน `uv run python main.py` ก่อน"

def predict(image: Image.Image | None):
    if image is None:
        raise gr.Error("กรุณาเลือกภาพมิเตอร์ก่อน")

    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=95)
    buf.seek(0)

    resp = httpx.post(READ_ENDPOINT, files={"file": ("meter.jpg", buf, "image/jpeg")}, timeout=180)
    data = resp.json()

    reading = data.get("reading", "")
    mean_conf = data.get("mean_confidence", 0.0)
    warnings = data.get("warnings", [])
    warn_text = "\n".join(f"- ⚠️ {w}" for w in warnings) if warnings else "✅ ไม่พบข้อผิดพลาด"

    return reading, f"{mean_conf:.2%}", warn_text

with gr.Blocks(title="Water Meter Reader") as demo:
    gr.Markdown("# 💧 ระบบอ่านเลขมิเตอร์น้ำอัตโนมัติ (Water Meter Reader)")
    status_box = gr.Textbox(value=fetch_health, label="สถานะระบบ", interactive=False)
    
    with gr.Row():
        with gr.Column():
            input_img = gr.Image(type="pil", label="อัปโหลดภาพมิเตอร์น้ำ")
            submit_btn = gr.Button("🔍 เริ่มอ่านเลขมิเตอร์", variant="primary")
        with gr.Column():
            reading_out = gr.Textbox(label="ตัวเลขที่อ่านได้", scale=2)
            conf_out = gr.Textbox(label="ความมั่นใจเฉลี่ย")
            warn_out = gr.Markdown(label="คำเตือนและการตรวจสอบ")

    submit_btn.click(fn=predict, inputs=[input_img], outputs=[reading_out, conf_out, warn_out])

if __name__ == "__main__":
    demo.launch(server_port=7860)
```

---

### 📋 ตรวจสอบความเข้าใจ Level 3

- [ ] ฉันเข้าใจการเชื่อมต่อระหว่าง Gradio Frontend (พอร์ต 7860) และ FastAPI Backend (พอร์ต 8000)
- [ ] ฉันเข้าใจว่าทำไมต้องใช้ `run_in_threadpool` เพื่อไม่ให้งานประมวลผลภาพบล็อกการทำงานของเซิร์ฟเวอร์
- [ ] ฉันสามารถทดสอบส่งภาพผ่าน Swagger Docs (`/docs`) และผ่านหน้าเว็บ Gradio ได้อย่างคล่องแคล่ว

---

# 🎓 Level 4: การฝึกโมเดลด้วยตัวเองและหัวข้อขั้นสูง

> [!NOTE]
> **ข้ามส่วนนี้ได้:** หากคุณต้องการเพียงนำระบบไปใช้งาน สามารถข้ามส่วนนี้ได้ทันที เพราะในโปรเจกต์มีไฟล์โมเดล `weights/MeterOCR.pt` ที่ฝึกฝนเสร็จสมบูรณ์พร้อมใช้งานอยู่แล้ว

---

### 4.1 การเตรียม Dataset จาก Roboflow

1. สมัครบัญชีฟรีที่ [Roboflow](https://app.roboflow.com) และสร้าง Workspace
2. ทำการตีกรอบ Bounding Box ระบุ Class ตัวเลข $0-9$ (Annotation)
3. ส่งออกชุดข้อมูลในรูปแบบ **YOLOv8 / YOLO11 Format**

```python
# 📍 train_colab.ipynb — ดาวน์โหลด Dataset
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("watermeter-jvlgr").project("utility-meter-reading-yolo")
dataset = project.version(1).download("yolov8")
```

---

### 4.2 การฝึกโมเดล YOLO บน Google Colab

```python
# 📍 train_colab.ipynb — ฝึกฝนโมเดล YOLO
from ultralytics import YOLO

# โหลด Base Model ขนาดเล็ก (Nano)
model = YOLO("yolo11n.pt")

# เริ่มต้นการเทรน 100 รอบ (Epochs)
model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=100,
    imgsz=960,
    batch=16,
    device=0,
    name="meter_ocr",
)
```

หลังเทรนเสร็จ ให้นำไฟล์ `runs/detect/meter_ocr/weights/best.pt` มาวางแทนที่ไฟล์ `weights/MeterOCR.pt` ในโปรเจกต์

---

### 4.3 คู่มือวิเคราะห์และแก้ปัญหาเมื่อ AI อ่านผิด (Step-by-Step Troubleshooting)

| อาการที่พบ (Symptom) | สาเหตุที่เป็นไปได้ (Cause) | จุดที่ต้องตรวจสอบ (Check) | วิธีแก้ไข (Action) | ผลลัพธ์ที่ควรได้ (Expected) |
|---|---|---|---|---|
| **ตอบว่า "ภาพนี้ไม่ใช่มิเตอร์น้ำ"** | ถ่ายภาพไกลเกินไป หรือเห็นฉากหลังเยอะกว่าหน้าปัด | ค่าความมั่นใจใน `meter_check.confidence` | ครอปภาพให้เห็นหน้าปัดมิเตอร์ชัดขึ้น หรือปรับลด `METER_VERIFY_CONF = 0.40` ใน `main.py` | AI ยืนยันว่าเป็นมิเตอร์น้ำและเข้าสู่ขั้นตอนอ่านตัวเลข |
| **ตัวเลขหายไปบางหลัก (เช่น 5 หลักอ่านได้ 4 หลัก)** | ตัวเลขจาง แสงสะท้อน หรือโมเดลมั่นใจต่ำกว่า 0.35 | ตรวจดูว่าหลักที่หายไปมีความสว่างน้อยหรือไม่ | ปรับลด `YOLO_CONF = 0.30` หรือทดสอบเปิดฟิลเตอร์ `histeq` | ตรวจพบตัวเลขครบทุกหลักบนหน้าปัด |
| **อ่านได้เลขกลับหัว เช่น 9 เป็น 6** | ภาพถ่ายคว่ำ 180° และไม่มีทศนิยมสีแดงให้สังเกต | ตรวจสอบที่กล่องคำเตือน `warnings` | ระบบจะแจ้งเตือน `⚠️ อาจกลับหัว` เพื่อให้เจ้าหน้าที่ตรวจสอบด้วยตาก่อนบันทึก | มีข้อความแจ้งเตือนความเสี่ยงชัดเจน |
| **AI ไปอ่านป้ายวันที่ข้างตัวเรือน** | มีตัวเลขพิมพ์ในแนวตั้งบนตัวถังมิเตอร์ | ตรวจสอบค่าพิกัด `bbox` ของตัวเลข | ฟังก์ชัน `is_vertical()` จะตัดคอลัมน์แนวตั้งทิ้งให้อัตโนมัติ | อ่านเฉพาะแถวตัวเลขมิเตอร์แนวนอน |
| **หน้าเว็บขึ้น "API ไม่พร้อม"** | Backend ยังไม่ได้เริ่มทำงาน หรือรันผิดพอร์ต | ตรวจดู Terminal 1 ว่า Uvicorn ทำงานอยู่หรือไม่ | รันคำสั่ง `uv run python main.py` ที่เทอร์มินัล 1 | หน้าเว็บขึ้นสถานะ `API: พร้อมใช้งาน` |

---

### 4.4 ข้อควรพิจารณาก่อนขึ้นระบบจริง (Production Readiness)

1. **สิทธิ์การใช้งาน (License):** YOLO (Ultralytics) ใช้ AGPL-3.0 สำหรับ Open Source หรือ Commercial License สำหรับการค้า, SigLIP2 อยู่ภายใต้ Apache 2.0
2. **ความเป็นส่วนตัวของข้อมูล (PDPA):** ภาพถ่ายมิเตอร์น้ำที่ติดบ้านเรือนหรือเลขทะเบียนผู้ใช้น้ำ ควรกำหนดระยะเวลาลบไฟล์ชั่วคราว (Retention Policy) ทันทีหลังประมวลผลเสร็จ
3. **การเร่งความเร็วด้วย GPU:** หากต้องการความเร็วสูง แนะนำให้ติดตั้งไดรเวอร์ NVIDIA CUDA ซึ่งจะช่วยลดเวลาประมวลผลเหลือเพียง **50–150 ms ต่อภาพ**

---

## 📖 อภิธานศัพท์ (Glossary)

* **Annotation (การกำกับข้อมูล):** กระบวนการตีกรอบและระบุค่าของตัวเลขในภาพเพื่อสร้าง Dataset
* **Bounding Box (`bbox`):** กรอบสี่เหลี่ยมพิกัด `[x1, y1, x2, y2]` ล้อมรอบตัวเลขแต่ละหลัก
* **CLAHE:** เทคนิคปรับสมดุลแสงเฉพาะจุดเพื่อดึงรายละเอียดตัวเลขในเงามืด
* **Confidence Score:** ค่าความเชื่อมั่น (0.00 – 1.00) ที่โมเดล AI มั่นใจในคำตอบ
* **Intersection over Union (IoU):** อัตราส่วนพื้นที่ทับซ้อนของ 2 กล่อง ใช้ตัดกล่องที่ซ้ำซ้อน
* **Lazy Loading:** การชะลอการโหลดโมเดลเข้าหน่วยความจำจนกว่าจะมีการเรียกใช้งานครั้งแรก
* **Non-Maximum Suppression (NMS / Dedup):** อัลกอริทึมคัดเลือกเฉพาะกล่องตรวจจับที่ดีที่สุด
* **OCR (Optical Character Recognition):** เทคโนโลยีแปลงภาพตัวเลขให้ออกมาเป็นข้อความดิจิทัล
* **ROI (Region of Interest):** พื้นที่เป้าหมายเฉพาะส่วนบนภาพที่เราสนใจ
* **Span-based Alignment:** การวัดระยะกว้าง vs ระยะสูง ($\Delta X$ vs $\Delta Y$) เพื่อแยกแถวแนวนอนออกจากแนวตั้ง
* **YOLO (You Only Look Once):** สถาปัตยกรรมโมเดล Object Detection ความเร็วสูงสำหรับหาตำแหน่งตัวเลข
* **Zero-shot Classification:** การจำแนกประเภทภาพตาม Text Prompt โดยไม่ต้องฝึกฝนโมเดลด้วยภาพตัวอย่างนั้นมาก่อน

---

## 📚 เอกสารอ้างอิง (References)

1. **Tschannen, M., et al. (2025).** *SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding.* Google Research.
2. **Li, X., et al. (2020).** *Water Meter Reading Recognition Based on Computer Vision and Deep Learning.* IEEE Access.
3. **Ultralytics (2024).** *YOLOv8 & YOLO11: Real-Time Object Detection and Image Segmentation.* [https://docs.ultralytics.com](https://docs.ultralytics.com)
4. **FastAPI Documentation (2024).** *FastAPI framework, high performance, easy to learn, fast to code.* [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
5. **Gradio Documentation (2024).** *Build and Share Delightful Machine Learning Apps.* [https://gradio.app](https://gradio.app)
