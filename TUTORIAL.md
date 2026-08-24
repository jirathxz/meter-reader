# คู่มือการพัฒนาระบบอ่านค่ามาตรวัดน้ำอัตโนมัติด้วยปัญญาประดิษฐ์
## Automated Water Meter Reading System using Deep Learning & Computer Vision

&emsp;&emsp;คู่มือฉบับนี้จัดทำขึ้นสำหรับนักศึกษาและผู้เริ่มต้นที่มีพื้นฐานภาษา Python เพื่อเรียนรู้การสร้าง **ระบบอ่านตัวเลขมิเตอร์น้ำอัตโนมัติจากภาพถ่าย (Water Meter OCR)** โดยจะค่อยๆ พาทำความเข้าใจหลักการประมวลผลภาพ การใช้ AI ตรวจจับตัวเลข และการสร้างหน้าเว็บแสดงผลลัพธ์ทีละขั้นตอนอย่างเป็นลำดับ โดยโค้ดถูกออกแบบให้แบ่งการทำงานออกเป็นฟังก์ชันย่อยตามหน้าที่ เพื่อให้อ่านเข้าใจง่ายและทดสอบแยกชิ้นได้สะดวก

---

## สารบัญเนื้อหา (Table of Contents)

- [ข้อแนะนำเบื้องต้นสำหรับการศึกษา](#ข้อแนะนำเบื้องต้นสำหรับการศึกษา)
- [บทที่ 1: พื้นฐาน การออกแบบ และการประมวลผลภาพ (Fundamentals, Design, and Image Processing)](#บทที่-1-พื้นฐาน-การออกแบบ-และการประมวลผลภาพ-fundamentals-design-and-image-processing)
  - [1.1 ทฤษฎีและหลักการพื้นฐาน (Theory & Fundamentals)](#11-ทฤษฎีและหลักการพื้นฐาน-theory--fundamentals)
  - [1.2 การฝึกแบบจำลองสำหรับการอ่านตัวเลข (Model Training)](#12-การฝึกแบบจำลองสำหรับการอ่านตัวเลข-model-training)
  - [1.3 สภาพแวดล้อมและการจัดการโปรเจกต์ด้วย uv (Environment & Project Setup)](#13-สภาพแวดล้อมและการจัดการโปรเจกต์ด้วย-uv-environment--project-setup)
  - [1.4 การคัดกรองภาพแบบซีโร่ช็อตด้วย SigLIP2 (Zero-shot Classification)](#14-การคัดกรองภาพแบบซีโร่ช็อตด้วย-siglip2-zero-shot-classification)
  - [1.5 การตรวจจับและอ่านค่าตัวเลข (Computer Vision & Digit Detection Engine)](#15-การตรวจจับและอ่านค่าตัวเลข-computer-vision--digit-detection-engine)
- [บทที่ 2: การพัฒนาแอปพลิเคชันและส่วนติดต่อผู้ใช้ (Application & UI Development)](#บทที่-2-การพัฒนาแอปพลิเคชันและส่วนติดต่อผู้ใช้-application--ui-development)
  - [2.1 การบูรณาการระบบประมวลผลหลักและระบบความปลอดภัย (Core Pipeline & Safety Guards)](#21-การบูรณาการระบบประมวลผลหลักและระบบความปลอดภัย-core-pipeline--safety-guards)
  - [2.2 การพัฒนาส่วนเชื่อมต่อโปรแกรมประยุกต์ด้วย FastAPI (REST API Development)](#22-การพัฒนาส่วนเชื่อมต่อโปรแกรมประยุกต์ด้วย-fastapi-rest-api-development)
  - [2.3 การพัฒนาส่วนติดต่อผู้ใช้ด้วย Gradio (Frontend Development)](#23-การพัฒนาส่วนติดต่อผู้ใช้ด้วย-gradio-frontend-development)
  - [2.4 การรัน ทดสอบ และคู่มือแก้ปัญหา (Testing & Troubleshooting)](#24-การรัน-ทดสอบ-และคู่มือแก้ปัญหา-testing--troubleshooting)
  - [2.5 ข้อควรพิจารณาก่อนการใช้งานจริง (Production Readiness)](#25-ข้อควรพิจารณาก่อนการใช้งานจริง-production-readiness)
- [อภิธานศัพท์ (Glossary)](#อภิธานศัพท์-glossary)
- [บรรณานุกรมและเอกสารอ้างอิง (References)](#บรรณานุกรมและเอกสารอ้างอิง-references)

---

## ข้อแนะนำเบื้องต้นสำหรับการศึกษา

สำหรับผู้ที่เพิ่งเริ่มศึกษาการพัฒนาระบบด้วยไพทอน (Python) และคอมพิวเตอร์วิทัศน์ ขอแนะนำหลักการสำคัญก่อนลงมือปฏิบัติ:

1. **ทำไมต้องใช้ Python Virtual Environment (`venv`)?:** การสร้างสภาพแวดล้อมเสมือนเปรียบเสมือน "กล่องเครื่องมือเฉพาะงาน" ช่วยแยกชุด Library ของโปรเจกต์นี้ออกจากโปรเจกต์อื่น เพื่อไม่ให้เกิดปัญหา Library คนละเวอร์ชันตีกัน (Dependency Conflicts)
2. **ทำไมต้องใช้ `uv`?:** `uv` เป็นเครื่องมือจัดการ Python ยุคใหม่ที่เขียนด้วยภาษา Rust มีความเร็วในการติดตั้งแพ็กเกจเร็วกว่า `pip` ปกติถึง 10–100 เท่า ช่วยประหยัดเวลาอย่างมาก
3. **การรันคำสั่งที่โฟลเดอร์หลัก (Root Directory):** เมื่อเปิด Terminal โปรดตรวจสอบว่าคำสั่งกำลังทำงานอยู่ที่โฟลเดอร์หลักของโปรเจกต์ (`meter-reader/`) เสมอ
4. **การประมวลผลบนสภาพแวดล้อมจริง (Native Execution):** ระบบทำงานบนเครื่องโฮสต์โดยตรง ทำให้เข้าถึง GPU (CUDA) ได้เต็มประสิทธิภาพโดยไม่มี Overhead ของ Container
5. **โครงสร้างโค้ดแบบแบ่งฟังก์ชันตามหน้าที่ (Modular Design):** โค้ดในโปรเจกต์นี้ถูกออกแบบโดยแบ่งการทำงานออกเป็นฟังก์ชันย่อยตามหน้าที่อย่างตรงไปตรงมา (เช่น ฟังก์ชันหมุนภาพ, ฟังก์ชันปรับแสง, ฟังก์ชันตรวจจับตัวเลข) แต่ละฟังก์ชันรับข้อมูลเข้ามา ประมวลผล และส่งผลลัพธ์ต่อไปยังฟังก์ชันถัดไป ทำให้นักศึกษาสามารถอ่านทำความเข้าใจและทดสอบโค้ดทีละส่วนได้อย่างเป็นระบบ โดยไม่จำเป็นต้องมีความรู้เรื่อง Object-Oriented Programming (OOP) หรือ Functional Programming ชั้นสูงมาก่อน

> **💡 เคล็ดลับการเรียนรู้:** สามารถทดลองรันระบบจริงด้วยโมเดลสำเร็จรูปที่มีอยู่ในโปรเจกต์ได้ทันทีก่อนเริ่มอ่านโค้ด โดยเปิด Terminal แล้วรัน `uv run python main.py` (เทอร์มินัล 1) และ `uv run python gradio_app.py` (เทอร์มินัล 2) จากนั้นเปิดเบราว์เซอร์ที่ http://127.0.0.1:7860

---

# บทที่ 1: พื้นฐาน การออกแบบ และการประมวลผลภาพ (Fundamentals, Design, and Image Processing)

---

### 1.1 ทฤษฎีและหลักการพื้นฐาน (Theory & Fundamentals)

**ปัญหาที่ระบบนี้แก้ไข (The Real-world Problem):**  
การอ่านเลขมิเตอร์น้ำจากภาพถ่ายหน้างานจริงมีความท้าทายหลายประการ:
* **ภาพถ่ายเอียงหรือกลับหัว:** ผู้ใช้อาจถือโทรศัพท์ถ่ายในมุม 90° หรือ 180°
* **แสงสะท้อนและตัวเลขเลือนราง:** กระจกหน้าปัดมิเตอร์มักมีเงา คราบน้ำ หรืออยู่ในมุมมืด
* **มีป้ายข้อความหลอกตา:** เช่น วันที่ผลิต หรือซีเรียลนัมเบอร์ปั๊มแนวตั้งบนตัวเรือน
* **ตัวเลขสมมาตรหลอกตา:** เลข $6 \leftrightarrow 9$, $2 \leftrightarrow 5$, และ $0, 1, 8$ ที่อ่านได้แม้ภาพกลับหัว

**แผนภาพการทำงานของระบบ (Pipeline Data Flow):**

```text
[ 📷 ภาพถ่ายขาเข้า (Input Image) ]
              │
              ▼
[ 1. SigLIP2 Verification ]  ──> ภาพนี้ใช่มิเตอร์น้ำจริงหรือไม่? (ถ้าไม่ใช่ ปฏิเสธทันที)
              │ (ใช่)
              ▼
[ 2. Preprocessing & Search ] ──> ลองหมุน 4 ทิศ (0°, 90°, 180°, 270°) × ปรับแสง 3 แบบ (Orig, CLAHE, HistEq)
              │
              ▼
[ 3. YOLO Digit Detection ]  ──> ตรวจหากล่อง Bounding Box ของตัวเลข 0-9 ทุกหลัก
              │
              ▼
[ 4. Candidate Filtering ]   ──> ตัดกรอบสี่เหลี่ยมที่ซ้อนทับกันทิ้งด้วย IoU (Dedup)
              │
              ▼
[ 5. Vertical Check ]        ──> ตรวจว่าแถวตัวเลขเป็นแนวนอนหรือไม่ (กรองป้ายวันที่ออก)
              │
              ▼
[ 6. Red Digit & Scoring ]   ──> ตรวจหลักทศนิยมสีแดง (ต้องอยู่ขวาสุด) + ให้คะแนนเลือกมุมที่ดีที่สุด
              │
              ▼
[ 7. Coordinate Remapping ]  ──> แปลงพิกัดกล่องตัวเลขจากภาพหมุน กลับสู่ระนาบภาพต้นฉบับเดิม
              │
              ▼
[ 8. Safety Guards ]         ──> ตรวจกลับหัว 180° (flip_guard) + SigLIP2 ตรวจทานหลักที่ไม่มั่นใจ
              │
              ▼
[ ✅ ตัวเลขผลลัพธ์ (Final Output) ] ──> ได้ค่าตัวเลข พิกัดกล่อง ค่าความมั่นใจ และรายการคำเตือน
```

#### 1.1.1 คอมพิวเตอร์วิทัศน์และการตรวจจับวัตถุ (Computer Vision & Object Detection)
**คอมพิวเตอร์วิทัศน์ (Computer Vision)** คือสาขาของ AI ที่สอนให้คอมพิวเตอร์เข้าใจภาพถ่าย และ **OCR (Optical Character Recognition)** คือเทคโนโลยีการอ่านตัวเลขจากภาพแปลงเป็นข้อความดิจิทัล

ระบบเลือกใช้โมเดล **YOLO (You Only Look Once)** สถาปัตยกรรมล่าสุด (YOLO26 / YOLOv8 architecture) ในการตรวจจับตัวเลข ซึ่งมีจุดเด่นเรื่องความเร็วระดับ Real-time:
* **Bounding Box (`bbox`):** กรอบสี่เหลี่ยมพิกัด `[x1, y1, x2, y2]` ที่โมเดลตีกรอบล้อมรอบตัวเลขแต่ละหลัก
* **Confidence Score:** ค่าความมั่นใจของโมเดล (0.00 – 1.00 ยิ่งใกล้ 1.00 ยิ่งมั่นใจสูง)
* **Class:** หมวดหมู่ตัวเลขที่ตรวจพบ (0 ถึง 9)

#### 1.1.2 การจำแนกภาพแบบซีโร่ช็อต (Zero-shot Image Classification)
แทนที่จะต้องเสียเวลาเทรนโมเดลใหม่ทั้งหมดเพื่อแยกแยะภาพที่ไม่ใช่มิเตอร์น้ำ ระบบเลือกใช้ **SigLIP2** ซึ่งเป็นโมเดล Vision-Language ขนาดใหญ่จาก Google:
* **Zero-shot Classification:** ความสามารถของโมเดลในการจำแนกประเภทภาพตามคำอธิบายข้อความ (Text Prompt) เช่น `"water meter"`, `"electricity meter"`, `"not a meter"` ได้ทันทีโดยไม่ต้องใช้ภาพตัวอย่างมาเทรนเพิ่ม

#### 1.1.3 การประมวลผลภาพดิจิทัล (Digital Image Processing)
**การประมวลผลภาพล่วงหน้า (Image Preprocessing)** เปรียบเหมือนการเช็ดแว่นตาให้ใสก่อนอ่านหนังสือ เพื่อช่วยให้โมเดลมองเห็นตัวเลขที่จางได้ชัดเจนขึ้น:
* **CLAHE (Contrast Limited Adaptive Histogram Equalization):** การปรับสมดุลแสงเฉพาะจุดบนช่องความสว่าง (L) ในระบบสี LAB ช่วยดึงรายละเอียดตัวเลขในเงามืดโดยไม่ทำให้ส่วนอื่นสว่างจ้าเกินไป
* **Histogram Equalization (HistEq):** การเกลี่ยกระจายความสว่างทั่วทั้งภาพบนช่อง Y ในระบบสี YCrCb ช่วยให้ภาพมืดสว่างชัดเจนขึ้น

> **📌 สรุปความเข้าใจส่วนที่ 1.1:**
> * YOLO ทำหน้าที่ตีกรอบและอ่านค่าตัวเลข 0–9
> * SigLIP2 ทำหน้าที่ตรวจสอบว่าภาพเป็นมิเตอร์น้ำจริงหรือไม่
> * OpenCV ทำหน้าที่หมุนภาพและปรับแสงเพื่อช่วยให้ AI อ่านได้ง่ายขึ้น

---

### 1.2 การฝึกแบบจำลองสำหรับการอ่านตัวเลข (Model Training)

> [!NOTE]
> **⚡ ข้ามส่วนนี้ได้ทันที — มีโมเดลพร้อมใช้งานแล้ว:**  
> ในโปรเจกต์นี้มีไฟล์โมเดล `weights/MeterOCR.pt` ที่ฝึกฝนเสร็จสมบูรณ์พร้อมใช้งานอยู่แล้ว คุณสามารถข้ามหัวข้อ 1.2 นี้ไปยังหัวข้อ 1.3 ได้เลยทันที หัวข้อนี้เขียนไว้สำหรับผู้ที่ต้องการศึกษาขั้นตอนการเทรนโมเดลด้วยตนเอง

**ทำไมต้องเทรนบนคลาวด์ (WHY)?:** การเทรนโมเดล Deep Learning กินทรัพยากรการ์ดจอสูงมาก จึงแนะนำให้รันสคริปต์บน Google Colab หรือ Kaggle ที่มี GPU ให้ใช้งานฟรี

#### 1.2.1 การเตรียมชุดข้อมูลจาก Roboflow

**Dataset** หรือชุดข้อมูลภาพถ่ายมิเตอร์น้ำที่มีการตีกรอบ (Annotation) ระบุ Class 0–9 สามารถดาวน์โหลดผ่าน Roboflow:

```python
# 📍 train_model_colab.ipynb — ดาวน์โหลดชุดข้อมูลจาก Roboflow
from roboflow import Roboflow

rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("watermeter-jvlgr").project("utility-meter-reading-dataset-for-automatic-reading-yolo")
version = project.version(1)
dataset = version.download("yolov8")
```

#### 1.2.2 การฝึกโมเดล YOLO

```python
# 📍 train_model_colab.ipynb — ฝึกฝนโมเดล YOLO สำหรับอ่านตัวเลข
from ultralytics import YOLO

# โหลด Base Model
model = YOLO("yolo11n.pt")

# เริ่มต้นการฝึกฝน
results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=100,
    imgsz=960,
    batch=16,
    device=0,
    name="meter_ocr_model",
)

# ประเมินผลลัพธ์บน Validation Set
metrics = model.val()
print(f"mAP@50: {metrics.box.map50:.4f}, mAP@50-95: {metrics.box.map:.4f}")
```
**ผลลัพธ์ที่คาดหวัง:** จะได้ไฟล์น้ำหนักที่ดีที่สุด `best.pt` ในโฟลเดอร์ `runs/detect/meter_ocr_model/weights/` ให้นำไฟล์นี้มาวางที่ `weights/MeterOCR.pt` ในโปรเจกต์

---

### 1.3 สภาพแวดล้อมและการจัดการโปรเจกต์ด้วย `uv` (Environment & Project Setup)

> **ทำไมต้องทำ (WHY)?:** เพื่อเตรียมโฟลเดอร์โปรเจกต์และติดตั้ง Library ทั้งหมดให้พร้อมสำหรับการพัฒนาบนเครื่องของคุณ

#### 1.3.1 โครงสร้างไฟล์ของระบบ (Project Structure)
```text
meter-reader/
├── main.py            # โค้ดหลัก: API (FastAPI) และฟังก์ชันประมวลผลทั้งหมด
├── gradio_app.py      # หน้าเว็บ UI (Gradio) สำหรับทดสอบระบบ
├── TUTORIAL.md        # คู่มือการเรียนรู้ฉบับสมบูรณ์
├── requirements.txt   # รายการ Library dependencies
├── meter_img/         # ชุดภาพถ่ายมิเตอร์น้ำตัวอย่าง 7 ภาพ
└── weights/
    └── MeterOCR.pt    # ไฟล์โมเดล YOLO สำหรับตรวจจับตัวเลข
```

#### 1.3.2 การสร้างสภาพแวดล้อมและติดตั้ง Dependencies

เปิด Terminal ที่โฟลเดอร์ `meter-reader/` แล้วพิมพ์ตามลำดับ:

```powershell
# 1. สร้าง Virtual Environment ด้วย Python 3.11
uv venv --python 3.11

# 2. เปิดใช้งาน Virtual Environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

# 3. ติดตั้ง Library ทั้งหมดผ่าน uv
uv pip install -r requirements.txt
```

**ผลลัพธ์ที่คาดหวัง:** `uv` จะติดตั้งแพ็กเกจทั้งหมดสำเร็จ พร้อมข้อความ `Installed 12 packages`

รายการใน `requirements.txt`:
```text
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
python-multipart>=0.0.20
ultralytics>=8.3.0
transformers>=4.48.0
torch>=2.4.0
torchvision>=0.19.0
opencv-python-headless>=4.10.0
numpy>=1.26.0
pillow>=10.4.0
gradio>=5.0.0
httpx>=0.28.0
```

---

### 1.4 การคัดกรองภาพแบบซีโร่ช็อตด้วย SigLIP2 (Zero-shot Classification)

> **ทำไมต้องทำ (WHY)?:** ในการใช้งานจริง ผู้ใช้อาจส่งภาพที่ไม่ใช่มิเตอร์น้ำเข้ามา (เช่น ภาพมิเตอร์ไฟ เกจวัดแรงดัน หรือภาพถ่ายทั่วไป) หากไม่มีการตรวจคัดกรอง ระบบจะเสียเวลาพยายามหาตัวเลขและให้ผลลัพธ์ที่ผิดพลาด

**แนวคิดการทำงาน:**  
ใช้ **SigLIP2** ตรวจดูว่าภาพนี้มีความคล้ายคลึงกับคำว่า `"water meter"` มากที่สุดหรือไม่ หากคะแนนต่ำกว่า `0.50` ระบบจะปฏิเสธภาพทันที

```python
# 📍 main.py — SigLIP2 Zero-shot Verification
SIGLIP_MODEL = "google/siglip2-base-patch16-224"
METER_LABELS = ("water meter", "electricity meter", "gas meter", "not a meter")
METER_VERIFY_CONF = 0.50

_siglip = None

def get_siglip() -> tuple[Any, Any]:
    """โหลดโมเดล SigLIP2 (Processor + Model) เข้า GPU/CPU แบบ Lazy Loading"""
    global _siglip
    if _siglip is None:
        from transformers import AutoModel, AutoProcessor
        processor = AutoProcessor.from_pretrained(SIGLIP_MODEL)
        model = AutoModel.from_pretrained(SIGLIP_MODEL).to(DEVICE).eval()
        _siglip = (processor, model)
    return _siglip

@torch.inference_mode()
def check_water_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    """SigLIP2 ตรวจสอบว่าเป็นภาพมิเตอร์น้ำจริงหรือไม่"""
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
```
**ผลลัพธ์ที่คาดหวัง:** ถ้าภาพเป็นมิเตอร์น้ำ คืนค่า `{"verified": True, "predicted_class": "water meter", "confidence": 0.87}`

---

### 1.5 การตรวจจับและอ่านค่าตัวเลข (Computer Vision & Digit Detection Engine)

กระบวนการอ่านตัวเลขมิเตอร์น้ำประกอบด้วย 4 ขั้นตอนสำคัญ:

#### 1. การหมุนภาพและปรับคอนทราสต์ (Image Enhancement)
* **ปัญหา:** ภาพถ่ายเอียง และตัวเลขอาจจางหรืออยู่ในเงามืด
* **วิธีแก้:** หมุนภาพตามเข็มนาฬิกา 90°, 180°, 270° และปรับคอนทราสต์ด้วย CLAHE หรือ HistEq

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

def apply_prep(img_bgr: np.ndarray, prep: str) -> np.ndarray:
    """ปรับแสง: CLAHE (บนช่อง L) หรือ HistEq (บนช่อง Y)"""
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

#### 2. การแปลงพิกัดจุดเดี่ยว (`remap_point`) และกล่อง (`remap_bbox`)

**ทำไมเราต้องแปลงพิกัดย้อนกลับ? (WHY):**  
ลองจินตนาการว่าคุณเอียงหัว 90° เพื่ออ่านหนังสือ แล้วเอาปากกาไฮไลต์ขีดข้อความ... เมื่อคุณกลับมาตั้งหัวตรง รอยไฮไลต์จะอยู่คนละตำแหน่งกับบนหน้ากระดาษเดิม!

ในการประมวลผลภาพก็เช่นเดียวกัน:
1. เมื่อเรานำภาพไปหมุน 90° เพื่อให้ AI ตรวจจับตัวเลขได้ง่ายขึ้น
2. พิกัดกล่องสี่เหลี่ยม Bounding Box `[x1, y1, x2, y2]` ที่ AI หาได้ จะอยู่ใน **ระบบพิกัดของภาพที่หมุนแล้ว**
3. หากเราต้องการนำกล่องนี้ไปวาดแสดงผลบน **ภาพถ่ายต้นฉบับเดิมของผู้ใช้** เราจึงต้อง **แปลงพิกัดจุด (x, y) ย้อนกลับ** สู่ตำแหน่งเดิมบนภาพตั้งต้นเสมอ

```text
[ 📷 ภาพต้นฉบับ (กว้าง W, สูง H) ]
               │
               ▼ (หมุนขวา 90°)
[ 🔄 ภาพที่หมุนแล้ว (กว้าง H, สูง W) ]
               │
               ▼ (AI ตรวจจับได้กล่องที่พิกัด x, y)
[ 🎯 กล่องตัวเลขในภาพหมุน ]
               │
               ▼ (remap_point: แปลงจุดกลับตามองศา)
[ 📍 กล่องตัวเลขบนภาพต้นฉบับเดิมอย่างแม่นยำ ]
```

**หลักการแปลงพิกัดทีละจุด (`remap_point`):**
* **หมุน 90° (ตามเข็ม):** แกนสลับกัน จุด $(x, y)$ บนภาพหมุน จะตรงกับจุด $(y, H - x)$ บนภาพเดิม
* **หมุน 180° (กลับหัว):** จุด $(x, y)$ จะตรงกับจุด $(W - x, H - y)$ บนภาพเดิม
* **หมุน 270° (ทวนเข็ม):** แกนสลับกัน จุด $(x, y)$ จะตรงกับจุด $(W - y, x)$ บนภาพเดิม

```python
def remap_point(x: float, y: float, angle: int, w: int, h: int) -> tuple[float, float]:
    """แปลงจุด 1 จุดจากภาพหมุน กลับสู่พิกัดภาพเดิมแบบทีละจุด"""
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

#### 3. การกรองคอลัมน์แนวตั้ง (`is_vertical`) ด้วยระยะกว้าง vs ระยะสูง
* **ปัญหา:** ตัวเรือนมิเตอร์น้ำมักมีตัวเลขวันที่ผลิตหรือซีเรียลนัมเบอร์ปั๊มเป็น **แนวตั้ง** ซึ่งไม่ใช่ค่าหน้าปัดมิเตอร์
* **วิธีแก้:** หน้าปัดมิเตอร์น้ำจริงจะเรียงตัวเป็น **แนวนอน** เสมอ ดังนั้นระยะกว้าง ($\text{width\_span}$) ต้องมากกว่าระยะสูง ($\text{height\_span}$) หากพบว่าแถวมีความสูงมากกว่าความกว้าง ให้ตัดทิ้งทันที

```python
def is_vertical(dets: list[dict[str, Any]], img_w: int, img_h: int) -> dict[str, Any]:
    """ตรวจว่าแถวตัวเลขเรียงเป็นแนวตั้งหรือไม่ (แนวนอน width_span ต้องมากกว่า height_span)"""
    if len(dets) < 2:
        return {"vertical": False}

    xs = [d["center_x"] / img_w for d in dets]
    ys = [d["center_y"] / img_h for d in dets]

    width_span = max(xs) - min(xs)   # ความกว้างของแนวตัวเลข (ซ้ายสุดไปขวาสุด)
    height_span = max(ys) - min(ys)  # ความสูงของแนวตัวเลข (บนสุดไปล่างสุด)

    # ถ้าความสูงมากกว่าความกว้าง แสดงว่าเป็นคอลัมน์แนวดิ่ง (ไม่ใช่แถวหน้าปัดมิเตอร์)
    is_vert = (height_span >= width_span * 0.8) or (width_span <= 0.05 and height_span >= 0.08)
    return {"vertical": is_vert}
```

---

#### 4. การค้นหา 4 ทิศ × 3 ฟิลเตอร์ และกฎสีแดงของหลักทศนิยม (`detect_digits_best`)

**ทำความเข้าใจปัญหาก่อนเริ่มเขียนโค้ด (The Problem):**  
ในสถานการณ์จริง ภาพถ่ายมิเตอร์น้ำที่ผู้ใช้ส่งเข้ามามีความไม่แน่นอนสูงมาก:
1. ภาพอาจถูกถ่ายมาในมุมใดก็ได้ (ตั้งตรง 0°, ตะแคงขวา 90°, กลับหัว 180°, หรือตะแคงซ้าย 270°)
2. สภาพแสงแต่ละภาพไม่เหมือนกัน (บางภาพมืด บางภาพมีเงาตกกระทบ)

หากเราเลือกหมุนแค่มุมเดียว หรือปรับแสงแค่แบบเดียว แล้วโมเดล AI ตรวจไม่พบตัวเลข ระบบจะล้มเหลวทันที

---

**แนวคิดการแก้ปัญหา (Solution Idea):**  
ระบบจึงสร้างการทดสอบแบบ **"12 ผู้ท้าชิง (4 ทิศทาง × 3 ฟิลเตอร์ปรับแสง)"** แล้วนำผลลัพธ์ของแต่ละแบบมาให้คะแนน เพื่อเลือกรูปแบบที่ได้คะแนนสูงสุดและถูกต้องที่สุด

```text
[ 📷 ภาพถ่ายต้นฉบับ ]
          │
          ▼
[ ทดสอบ 12 รูปแบบ: 4 ทิศ (0°, 90°, 180°, 270°) × 3 ฟิลเตอร์ (Orig, CLAHE, HistEq) ]
          │
          ▼
[ แต่ละรูปแบบ: หมุนภาพ ──> ปรับแสง ──> YOLO ตรวจจับเลข ──> ตัดกล่องซ้อนด้วย IoU ]
          │
          ▼
[ ตรวจคัดกรอง: ต้องเป็นแนวนอน (is_vertical) และมีจำนวนตัวเลข 4-9 หลัก ]
          │
          ▼
[ ให้คะแนน: Score = ความมั่นใจเฉลี่ย × จำนวนหลัก ]
  - ถ้าหลักทศนิยมสีแดงอยู่ขวาสุด: ได้โบนัส +5% (ทิศทางถูกต้อง)
  - ถ้าหลักทศนิยมสีแดงอยู่ซ้ายสุด: ตัดคะแนน -50% (น่าจะกลับหัว)
          │
          ▼
[ ตัดสินใจเลือกผู้ชนะ + Margin Rule (มุมอื่นต้องชนะมุม 0° เกิน 0.12 ถึงจะยอมเปลี่ยนมุม) ]
          │
          ▼
[ แปลงพิกัดกล่องของมุมที่ชนะ กลับสู่ระนาบภาพต้นฉบับเดิมด้วย remap_bbox ]
```

---

**การทำงานแบ่งออกเป็น 3 ฟังก์ชันย่อยตามหน้าที่:**

1. **`red_ratio(img_bgr, bbox)` — ตรวจจับสีแดงของหลักทศนิยม:**
   * **หน้าที่:** หน้าปัดมิเตอร์น้ำจริงจะมีตัวเลขหลักทศนิยมเป็น **สีแดงอยู่ทางขวาสุด** เสมอ หากพบว่าสีแดงไปอยู่ทางซ้ายสุด แสดงว่าภาพกำลังกลับหัว 180°
   * **วิธีทำ:** ครอปเฉพาะพื้นที่กล่องตัวเลข แปลงเป็นระบบสี HSV แล้วนับสัดส่วนพิกเซลสีแดง

2. **`eval_orientation(bgr_img, angle, prep)` — ประเมินผลลัพธ์ของแต่ละผู้ท้าชิง:**
   * หมุนภาพและปรับแสงตามที่กำหนด
   * รัน YOLO หาตัวเลข และตัดกล่องซ้อนทับกันด้วย `dedup_detections`
   * ตรวจสอบว่าไม่เป็นแนวตั้ง (`is_vertical`) และมีจำนวนหลักครบ 4–9 หลัก (ถ้าไม่ผ่านให้คะแนนเป็น 0 ทันที)
   * คำนวณคะแนนพื้นฐาน ($\text{Score} = \text{Mean Confidence} \times \text{Number of Digits}$) และปรับคะแนนเพิ่ม/ลดตามตำแหน่งของสีแดง

3. **`detect_digits_best(rgb_img)` — ตัดสินใจเลือกรูปแบบที่ดีที่สุด:**
   * รัน `eval_orientation` ครบทั้ง 12 แบบ แล้วเลือกตัวแทนที่คะแนนสูงสุดของแต่ละมุม (4 มุม)
   * หามุมที่ได้คะแนนสูงสุด (`best_angle`)
   * **Margin Rule (กฎกันพลิกฉิวเฉียด):** หากมุมอื่นชนะมุมตั้งต้น (0°) เพียงเล็กน้อย (ไม่เกิน `ORIENT_MARGIN = 0.12`) ระบบจะเลือกมุม 0° ตามเดิม เพื่อป้องกันการสลับมุมเมื่อคะแนนสูสี
   * นำพิกัดกล่องตัวเลขของมุมที่ชนะ แปลงกลับมาเป็นพิกัดบนภาพเดิมด้วย `remap_bbox`

---

```python
def red_ratio(img_bgr: np.ndarray, bbox: list[float]) -> float:
    """คำนวณสัดส่วนสีแดงในกล่องตัวเลข (หลักทศนิยมสีแดงต้องอยู่ขวาสุดของหน้าปัด)"""
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

    # กฎสีแดง: หลักทศนิยมสีแดงต้องอยู่ขวาสุดเสมอ
    r_first = red_ratio(proc, dets[0]["bbox"])
    r_last = red_ratio(proc, dets[-1]["bbox"])

    if r_first > RED_THRESH and r_first > r_last * RED_DOMINANCE:
        score *= 0.5   # แดงอยู่ซ้าย -> น่าจะกลับหัว (ตัดคะแนน)
    elif r_last > RED_THRESH and r_last > r_first * RED_DOMINANCE:
        score *= 1.05  # แดงอยู่ขวา -> ทิศทางถูกต้อง (เพิ่มคะแนน)

    return {"score": score, "dets": dets, "prep": prep, "vert": vert}

def detect_digits_best(rgb_img: np.ndarray) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """ทดลอง 4 ทิศ × 3 ฟิลเตอร์ (12 รูปแบบ) แล้วเลือกชุดที่ได้คะแนนสูงสุด"""
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

> **📌 สรุปความเข้าใจส่วนที่ 1.5:**
> * ฟังก์ชัน `detect_digits_best` จะเลือกมุมหมุนและฟิลเตอร์ที่ทำให้ตรวจจับตัวเลขได้มั่นใจที่สุด
> * ฟังก์ชัน `remap_bbox` จะแปลงตำแหน่งกล่องสี่เหลี่ยมกลับมาบนภาพเดิมให้โดยอัตโนมัติ

---

# บทที่ 2: การพัฒนาแอปพลิเคชันและส่วนติดต่อผู้ใช้ (Application & UI Development)

---

### 2.1 การบูรณาการระบบประมวลผลหลักและระบบความปลอดภัย (Core Pipeline & Safety Guards)

#### 1. การตรวจจับภาพกลับหัวแบบกระจกเงา (`flip_guard`)
* **ปัญหา:** ตัวเลขอารบิกมีความสมมาตรเมื่อหมุน 180° เช่น $6 \leftrightarrow 9$, $2 \leftrightarrow 5$, และ $0, 1, 8$ ทำให้ AI อาจอ่านภาพคว่ำเป็นอีกตัวเลขหนึ่งได้โดยมั่นใจสูง
* **วิธีแก้:** หมุนภาพไปอีก 180° แล้วเปรียบเทียบผลลัพธ์กับตาราง `FLIP_MAP` หากพบว่าเข้าข่ายภาพกลับหัว จะส่งข้อความแจ้งเตือน `⚠️ อาจกลับหัว!`

```python
FLIP_MAP = {0: 0, 1: 1, 2: 5, 5: 2, 6: 9, 8: 8, 9: 6}

def flip_guard(rgb_img: np.ndarray, digits: list[dict[str, Any]], meta: dict[str, Any] | None) -> dict[str, Any]:
    """ตรวจสอบความสมมาตร 180° ป้องกันการอ่านกลับหัว (Mirror Check)"""
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

#### 2. ฟังก์ชันประมวลผลหลัก `read_meter(rgb_img)`

ฟังก์ชันนี้ทำหน้าที่เป็นตัวกลางเชื่อมต่อทุกขั้นตอนเข้าด้วยกัน และสร้างระบบแจ้งเตือน (Warnings) เพื่อแจ้งความผิดปกติให้เจ้าหน้าที่ทราบ:

```python
def read_meter(rgb_img: np.ndarray) -> dict[str, Any]:
    """รับภาพ RGB -> ประมวลผล 4 ขั้นตอน -> คืนค่าตัวเลขและคำเตือน"""
    t0 = perf_counter()
    h, w = rgb_img.shape[:2]

    # ขั้นที่ 1: ตรวจสอบประเภทมิเตอร์ (SigLIP2)
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

    # ขั้นที่ 2: ค้นหาทิศและตัวเลขที่ดีที่สุด (YOLO26)
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

    # ขั้นที่ 3: กรองคอลัมน์แนวตั้ง
    if meta and meta["angle"] == 0 and is_vertical(dets, w, h)["vertical"]:
        return {
            "reading": "",
            "digits": [],
            "meter_check": meter,
            "processing": meta,
            "warnings": ["กล่องเรียงแนวตั้ง — ไม่ใช่ค่ามิเตอร์"],
            "elapsed_ms": round((perf_counter() - t0) * 1000, 1),
        }

    # ขั้นที่ 4: ตรวจสอบความปลอดภัยและสร้างคำเตือน
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
            (
                not (EXPECTED_MIN_DIGITS <= len(digits) <= EXPECTED_MAX_DIGITS),
                f"จำนวนหลัก {len(digits)} นอกช่วง {EXPECTED_MIN_DIGITS}-{EXPECTED_MAX_DIGITS}",
            ),
            (digits[0]["digit"] == 0, "หลักแรกเป็น 0 — อาจเกินมา 1 หลัก"),
            (mean_conf < CONF_RELIABLE, f"mean conf ต่ำ {mean_conf:.2f} — ภาพอาจเบลอ/เอียง"),
            (
                flip["warned"],
                f"อาจกลับหัว! หมุน 180° ได้ {flip['anti_reading']} ({flip['anti_confidence']:.2f}) — ตรวจภาพก่อนบันทึก",
            ),
            (not align_ok, "กล่องไม่เรียงแนว — อาจเป็นป้าย/วันที่"),
        ]
        if cond
    ]
    warns += [
        f"หลักที่ {d['position']} ({d['digit']}) conf ต่ำ {d['confidence']:.2f} — ควรตรวจด้วยตา"
        for d in digits
        if not d["reliable"]
    ]
    warns += [
        f"หลักที่ {m['position']}: YOLO {m['yolo_digit']} vs SigLIP {m['siglip_digit']} ({m['siglip_confidence']:.2f})"
        for m in mismatches
    ]

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

### 2.2 การพัฒนาส่วนเชื่อมต่อโปรแกรมประยุกต์ด้วย FastAPI (REST API Development)

> **ทำไมต้องทำ (WHY)?:** เพื่อเปิดให้บริการฟังก์ชันอ่านมิเตอร์ผ่านระบบเครือข่าย HTTP ทำให้แอปพลิเคชันมือถือ เว็บไซต์ หรือระบบฐานข้อมูลสามารถส่งภาพเข้ามาอ่านค่าได้

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
    """ตรวจสอบสถานะความพร้อมของระบบและโมเดล AI"""
    return {
        "status": "ok",
        "device": DEVICE,
        "yolo_loaded": _yolo is not None,
        "siglip_loaded": _siglip is not None,
    }

@app.post("/api/read-meter")
async def read_meter_endpoint(file: UploadFile = File(...)) -> dict[str, Any]:
    """รับไฟล์ภาพมิเตอร์น้ำและประมวลผลผ่าน Threadpool (ไม่บล็อก Event Loop)"""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="ชนิดไฟล์ไม่รองรับ")

    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        arr = np.asarray(img.convert("RGB"))
    except Exception:
        raise HTTPException(status_code=422, detail="อ่านไฟล์ภาพไม่ได้")

    # รันบน Threadpool เพื่อไม่ให้งานประมวลผลภาพบล็อกการทำงานของเซิร์ฟเวอร์
    return await run_in_threadpool(read_meter, arr)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
```

---

### 2.3 การพัฒนาส่วนติดต่อผู้ใช้ด้วย Gradio (Frontend Development)

> **ทำไมต้องทำ (WHY)?:** เพื่อสร้างหน้าต่าง Web Interface ที่ใช้งานง่าย ให้ผู้ใช้ทั่วไปสามารถทดลองอัปโหลดภาพและเห็นผลลัพธ์ทันทีโดยไม่ต้องเขียนคำสั่ง API เอง

```python
# 📍 gradio_app.py — Gradio Web Interface
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
    """ส่งภาพไปยัง API และรับผลลัพธ์มาแสดงผล"""
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

### 2.4 การรัน ทดสอบ และคู่มือแก้ปัญหา (Testing & Troubleshooting)

#### 🚀 วิธีการรันระบบด้วย `uv`

1. **เปิด Terminal 1 — รัน FastAPI Backend:**
   ```powershell
   uv run python main.py
   ```
   **ผลลัพธ์ที่คาดหวัง:** Uvicorn เริ่มทำงานที่ `http://127.0.0.1:8000` *(สามารถเปิดดูเอกสาร API แบบ Interactive ได้ที่ [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs))*

2. **เปิด Terminal 2 — รัน Gradio Web UI:**
   ```powershell
   uv run python gradio_app.py
   ```
   **ผลลัพธ์ที่คาดหวัง:** หน้าเว็บเปิดใช้งานที่ `http://127.0.0.1:7860`

---

#### 🛠️ คู่มือวิเคราะห์และแก้ปัญหาเมื่อ AI อ่านผิด (Debugging Matrix)

| อาการที่พบ (Symptom) | สาเหตุที่เป็นไปได้ (Cause) | สิ่งที่ควรตรวจสอบ (Check) | วิธีแก้ไข (Action) | ผลลัพธ์ที่ควรได้ (Expected) |
|---|---|---|---|---|
| **ตอบว่า "ภาพนี้ไม่ใช่มิเตอร์น้ำ"** | SigLIP2 ให้คะแนนความมั่นใจต่ำกว่า 0.50 | ค่าใน `meter_check.confidence` | ครอปภาพให้เห็นหน้าปัดมิเตอร์ชัดขึ้น หรือปรับลด `METER_VERIFY_CONF = 0.40` ใน `main.py` | AI ยืนยันว่าเป็นมิเตอร์น้ำและเข้าสู่ขั้นตอนอ่านตัวเลข |
| **ตัวเลขหายไปบางหลัก (เช่น 5 หลักอ่านได้ 4 หลัก)** | ตัวเลขจาง แสงสะท้อน หรือโมเดลมั่นใจต่ำกว่า 0.35 | ตรวจดูว่าหลักที่หายไปมีความสว่างน้อยหรือไม่ | ปรับลด `YOLO_CONF = 0.30` หรือทดสอบเปิดฟิลเตอร์ `histeq` | ตรวจพบตัวเลขครบทุกหลักบนหน้าปัด |
| **อ่านได้เลขกลับหัว เช่น 9 เป็น 6** | ภาพถ่ายคว่ำ 180° และไม่มีทศนิยมสีแดงให้สังเกต | ตรวจสอบที่กล่องคำเตือน `warnings` | ระบบจะแจ้งเตือน `⚠️ อาจกลับหัว` เพื่อให้เจ้าหน้าที่ตรวจสอบด้วยตาก่อนบันทึก | มีข้อความแจ้งเตือนความเสี่ยงชัดเจน |
| **AI ไปอ่านป้ายวันที่ข้างตัวเรือน** | มีตัวเลขพิมพ์ในแนวตั้งบนตัวถังมิเตอร์ | ตรวจสอบค่าพิกัด `bbox` ของตัวเลข | ฟังก์ชัน `is_vertical()` จะคำนวณ `height_span >= width_span` และตัดทิ้งให้อัตโนมัติ | อ่านเฉพาะแถวตัวเลขมิเตอร์แนวนอน |
| **หน้าเว็บขึ้น "API ไม่พร้อม"** | Backend ยังไม่ได้เริ่มทำงาน หรือรันผิดพอร์ต | ตรวจดู Terminal 1 ว่า Uvicorn ทำงานอยู่หรือไม่ | รันคำสั่ง `uv run python main.py` ที่เทอร์มินัล 1 | หน้าเว็บขึ้นสถานะ `API: ok` |

> **คำอธิบายพารามิเตอร์สำคัญ:**
> * `YOLO_CONF` (ค่าเริ่มต้น 0.35): เกณฑ์คะแนนความมั่นใจขั้นต่ำ ยิ่งปรับต่ำลง AI ยิ่งอ่านตัวเลขที่จางได้ง่ายขึ้น แต่ก็อาจมีสัญญาณรบกวนมากขึ้น
> * `METER_VERIFY_CONF` (ค่าเริ่มต้น 0.50): เกณฑ์ความมั่นใจในการคัดแยกภาพมิเตอร์น้ำ หากภาพมีฉากหลังรกอาจปรับลดเหลือ 0.40 ได้

---

### 2.5 ข้อควรพิจารณาก่อนการใช้งานจริง (Production Readiness)

1. **สิทธิ์การใช้งาน (License):** YOLO (Ultralytics) ใช้สัญญาอนุญาต AGPL-3.0 สำหรับโครงการ Open Source หรือ Commercial License สำหรับการค้า, SigLIP2 อยู่ภายใต้ Apache 2.0
2. **ความเป็นส่วนตัวของข้อมูล (PDPA):** ภาพถ่ายมิเตอร์น้ำที่อาจติดภาพบ้านเรือนหรือข้อมูลระบุตัวตน ควรกำหนดนโยบายลบไฟล์ภาพชั่วคราว (Data Retention) ทันทีหลังการประมวลผลเสร็จสิ้น
3. **การเร่งความเร็วด้วย GPU:** การติดตั้งไดรเวอร์ NVIDIA CUDA บนเครื่องเซิร์ฟเวอร์จะช่วยลดเวลาในการประมวลผลเหลือเพียง **50–150 มิลลิวินาทีต่อภาพ**

> **📌 สรุปความเข้าใจส่วนที่ 2:**
> * FastAPI ทำหน้าที่รับคำขอและส่งผลลัพธ์ผ่านระบบเครือข่าย
> * Gradio ทำหน้าที่เป็นหน้าต่างให้ผู้ใช้กดทดสอบ
> * ระบบมีกลไกความปลอดภัยแจ้งเตือนความเสี่ยง (Warnings) ครบวงจร

---

## อภิธานศัพท์ (Glossary)

รวบรวมคำศัพท์ภาษาอังกฤษทางเทคนิคทั้งหมดที่ปรากฏในคู่มือฉบับนี้ พร้อมคำอธิบายที่เข้าใจง่าย:

### 1. หมวดปัญญาประดิษฐ์และการเรียนรู้เชิงลึก (AI & Deep Learning)
* **Annotation (การกำกับข้อมูล):** กระบวนการตีกรอบและระบุค่าของตัวเลขในภาพเพื่อสร้าง Dataset
* **Bounding Box (`bbox`):** กรอบสี่เหลี่ยมพิกัด `[x1, y1, x2, y2]` ล้อมรอบตำแหน่งของตัวเลขแต่ละหลัก
* **CNN (Convolutional Neural Network):** โครงข่ายประสาทเทียมแบบคอนโวลูชันที่ออกแบบมาเพื่อดึงคุณลักษณะและวิเคราะห์ภาพถ่าย
* **Confidence Score:** ค่าความเชื่อมั่น (0.00 – 1.00) ที่โมเดล AI มั่นใจในคำตอบที่ตรวจพบ
* **Cross-check:** กระบวนการตรวจทานซ้ำข้ามโมเดล (ใช้ SigLIP2 ตรวจทานตัวเลขที่ YOLO มั่นใจต่ำ) เพื่อเพิ่มความแม่นยำ
* **Dataset:** ชุดข้อมูลภาพถ่ายและไฟล์กำกับพิกัดที่ใช้สำหรับการฝึกฝนและประเมินผลโมเดล
* **Heuristic:** กฎการตัดสินใจเชิงตรรกะที่สร้างขึ้นจากพฤติกรรมจริง (เช่น หลักทศนิยมสีแดงต้องอยู่ขวาสุดเสมอ)
* **Intersection over Union (IoU):** อัตราส่วนพื้นที่ทับซ้อนของ 2 กล่อง ใช้สำหรับวัดความแม่นยำและตัดกล่องที่ซ้ำซ้อน
* **Lazy Loading:** เทคนิคการชะลอการโหลดโมเดลเข้าหน่วยความจำจนกว่าจะมีการเรียกใช้งานครั้งแรก เพื่อประหยัด RAM
* **mAP (Mean Average Precision):** ดัชนีชี้วัดความแม่นยำรวมของโมเดล Object Detection
* **Model Inference:** กระบวนการนำภาพส่งเข้าไปให้โมเดล AI ประมวลผลและส่งผลลัพธ์ออกมา
* **Non-Maximum Suppression (NMS / Dedup):** อัลกอริทึมคัดเลือกเฉพาะกล่องตรวจจับที่ดีที่สุด และกำจัดกล่องที่ซ้อนทับกันทิ้ง
* **Object Detection:** งานด้าน Computer Vision ที่ทำทั้งการระบุตำแหน่ง (Localization) และจำแนกประเภท (Classification) ของวัตถุในภาพ
* **OCR (Optical Character Recognition):** เทคโนโลยีการอ่านและแปลงภาพตัวเลขให้ออกมาเป็นข้อความดิจิทัล
* **Roboflow:** แพลตฟอร์มคลาวด์สำหรับจัดการชุดข้อมูลภาพ Computer Vision
* **SigLIP / SigLIP2:** โมเดล Vision-Language ขั้นสูงจาก Google สำหรับทำความเข้าใจภาพคู่กับข้อความ ใช้ในงาน Zero-shot Classification
* **Text Prompt:** ข้อความคำสั่งภาษาธรรมชาติที่ป้อนให้กับโมเดล (เช่น `"water meter"`)
* **YOLO (You Only Look Once):** สถาปัตยกรรมโมเดล Object Detection ความเร็วสูงสำหรับหาตำแหน่งตัวเลข
* **Zero-shot Classification:** การจำแนกประเภทภาพตามคำอธิบายข้อความโดยไม่ต้องฝึกฝนโมเดลด้วยภาพตัวอย่างนั้นมาก่อน

### 2. หมวดการประมวลผลภาพดิจิทัล (Digital Image Processing & OpenCV)
* **CLAHE (Contrast Limited Adaptive Histogram Equalization):** เทคนิคปรับสมดุลแสงเฉพาะจุดเพื่อดึงรายละเอียดในเงามืด
* **Color Spaces (ระบบสี):**
  * **RGB / BGR:** แดง-เขียว-น้ำเงิน (OpenCV เรียงลำดับช่องสีเป็น BGR เป็นค่าเริ่มต้น)
  * **LAB:** แยกช่องความสว่าง (L) ออกจากช่องสี (A, B) เหมาะสำหรับการปรับคอนทราสต์ด้วย CLAHE
  * **YCrCb:** แยกช่องสัญญาณความสว่าง (Y) ออกจากช่องสัญญาณสี (Cr, Cb) เหมาะสำหรับการทำ Histogram Equalization
  * **HSV:** ระบบสี Hue-Saturation-Value เหมาะสำหรับการตรวจจับเฉดสีเฉพาะ เช่น การตรวจหาสีแดงของหลักทศนิยม
* **Coordinate Remapping:** การแปลงพิกัดจุดเรขาคณิต $(X, Y)$ จากภาพที่ผ่านการหมุนกลับสู่ระนาบพิกัดเดิมของภาพต้นฉบับ
* **Histogram Equalization (HistEq):** เทคนิคการเกลี่ยและกระจายค่าความสว่างของภาพให้สมดุลทั่วทั้งภาพ
* **Image Preprocessing:** กระบวนการปรับแต่งภาพเบื้องต้น (เช่น หมุน ปรับแสง) ก่อนส่งให้โมเดล AI
* **Mirror Check (Flip Guard):** กลไกตรวจสอบภาพกลับหัว 180° โดยเปรียบเทียบการสะท้อนของตัวเลขสมมาตร ($6 \leftrightarrow 9, 2 \leftrightarrow 5, 0, 1, 8$)
* **OpenCV (`cv2`):** ไลบรารีมาตรฐานระดับโลกสำหรับการประมวลผลภาพ
* **ROI (Region of Interest):** พื้นที่เป้าหมายเฉพาะส่วนบนภาพที่เราสนใจ (เช่น กรอบตัวเลขมิเตอร์)
* **Span-based Alignment ($\Delta X$ vs $\Delta Y$):** การคำนวณระยะกว้างเทียบกับระยะสูงเพื่อแยกแยะระหว่างแถวแนวนอนและคอลัมน์แนวตั้ง

### 3. หมวดสถาปัตยกรรมซอฟต์แวร์และเว็บ (Software Architecture & Web)
* **CORS (Cross-Origin Resource Sharing):** มาตรการความปลอดภัยของเว็บเบราว์เซอร์ที่ควบคุมการเรียกใช้ API ข้ามโดเมน
* **CUDA / GPU:** สถาปัตยกรรมการประมวลผลแบบขนานบนการ์ดจอ NVIDIA สำหรับเร่งความเร็วโมเดล Deep Learning
* **Endpoint:** จุดเชื่อมต่อ URL ปลายทางของ API สำหรับรับคำขอและส่งข้อมูลกลับ (เช่น `/api/read-meter`)
* **FastAPI:** เว็บเฟรมเวิร์กภาษา Python สำหรับสร้าง REST API ความเร็วสูง
* **Gradio:** ไลบรารีสำหรับสร้างหน้าเว็บส่วนติดต่อผู้ใช้ (Web UI) แบบ Interactive สำหรับโมเดล AI ได้อย่างรวดเร็ว
* **JSON (JavaScript Object Notation):** รูปแบบมาตรฐานในการแลกเปลี่ยนข้อมูลแบบข้อความที่มีโครงสร้าง Key-Value
* **Payload:** ส่วนของข้อมูลสำคัญที่ส่งไปในคำขอหรือตอบกลับมาจาก API
* **PDPA (Personal Data Protection Act):** กฎหมายคุ้มครองข้อมูลส่วนบุคคลที่เกี่ยวข้องกับการจัดเก็บและรักษาความปลอดภัยของภาพถ่าย
* **REST API (Representational State Transfer API):** สถาปัตยกรรมการสื่อสารระหว่างระบบผ่านโปรโตคอล HTTP
* **Threadpool Execution:** การแยกงานประมวลผลหนักไปรันบนเธรดเบื้องหลัง เพื่อไม่ให้บล็อก Event Loop ของ FastAPI
* **`uv`:** เครื่องมือจัดการแพ็กเกจและสภาพแวดล้อม Python ความเร็วสูง พัฒนาด้วยภาษา Rust
* **Virtual Environment (`venv`):** โฟลเดอร์สภาพแวดล้อมเสมือนที่แยกชุด Library ของโปรเจกต์ออกจากระบบหลัก

---

## บรรณานุกรมและเอกสารอ้างอิง (References)

1. **Tschannen, M., et al. (2025).** *SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding.* Google Research.
2. **Li, X., et al. (2020).** *Water Meter Reading Recognition Based on Computer Vision and Deep Learning.* IEEE Access.
3. **Ultralytics (2024).** *YOLOv8 & YOLO11: Real-Time Object Detection and Image Segmentation.* [https://docs.ultralytics.com](https://docs.ultralytics.com)
4. **FastAPI Documentation (2024).** *FastAPI framework, high performance, easy to learn, fast to code.* [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
5. **Gradio Documentation (2024).** *Build and Share Delightful Machine Learning Apps.* [https://gradio.app](https://gradio.app)
