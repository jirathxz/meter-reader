# Meter Reader — ระบบอ่านค่ามาตรวัดน้ำอัตโนมัติด้วยปัญญาประดิษฐ์ (Automated Water Meter Reading System)

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Version v2.15](https://img.shields.io/badge/Release-v2.15-blue.svg)](https://github.com/jirathxz/meter-reader/releases/tag/v2.15)
[![YOLO26m](https://img.shields.io/badge/Detector-YOLO26m-00FFFF.svg)](https://docs.ultralytics.com/)
[![SigLIP2](https://img.shields.io/badge/Zero--shot-SigLIP2--Base-4285F4.svg)](https://huggingface.co/google/siglip2-base-patch16-224)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gradio](https://img.shields.io/badge/UI-Gradio-FF7C00.svg)](https://gradio.app)
[![Unit Tests](https://img.shields.io/badge/Tests-11%2F11%20Passed-brightgreen.svg)]()

ระบบอ่านค่าตัวเลขบนหน้าปัดมาตรวัดน้ำแบบกลไกลูกล้อแนวนอน (Mechanical Velocity Meter) จากภาพถ่ายด้วยการเรียนรู้เชิงลึก (Deep Learning) และการประมวลผลภาพดิจิทัล (Digital Image Processing) พัฒนาบน **Python 3.11** ภายใต้สถาปัตยกรรมแบบ Functional Modular Pipeline พร้อมทั้งมีระบบความปลอดภัยทางเรขาคณิต (Geometric Safety Guards) และการประเมินผลเชิงประจักษ์อย่างเป็นระบบ (Empirical Evaluation)

---

## 🎯 จุดเด่นของระบบ (Key Highlights)

1. **การคัดกรองภาพนำเข้าแบบ Zero-shot (SigLIP2 Gatekeeper):** ตรวจสอบว่าเป็นภาพมาตรวัดน้ำจริงหรือไม่ก่อนเริ่มการประมวลผล ช่วยป้องกันการสิ้นเปลืองทรัพยากรการคำนวณและลดผลบวกลวง (False Positives) จากภาพสิ่งแปลกปลอม
2. **การค้นหาเชิงสมมติฐานพหุคูณ 12 รูปแบบ (Multi-hypothesis 12-Combination Search):** ประมวลผลภาพ 4 ทิศทางการหมุน (0°, 90°, 180°, 270°) ร่วมกับ 3 ฟิลเตอร์ปรับปรุงคอนทราสต์ (Original, CLAHE, Histogram Equalization) ชดเชยความแปรปรวนของมุมกล้องและสภาพแสงภาคสนาม
3. **ตัวตรวจจับวัตถุ YOLO26m แบบ Single-stage:** ตรวจจับตำแหน่งและระบุค่าตัวเลขแต่ละหลัก (Class 0–9) มีค่า Precision 93.53% และ Recall 89.30% (mAP@50 87.86%) บนชุดข้อมูลทดสอบอิสระ 194 ภาพ
4. **กลไกความปลอดภัยและการยืนยันความถูกต้อง (Safety Guards):**
   * `is_vertical`: กรองกลุ่มตัวเลขที่เรียงในแนวตั้ง ป้องกันการตรวจจับป้ายวันที่หรือหมายเลขซีเรียลข้างตัวเรือน
   * `red_ratio`: ตรวจวัดสัดส่วนสีแดงในระบบสี HSV เพื่อยืนยันว่าหลักทศนิยมต้องอยู่ทางขวาสุดเสมอ
   * `flip_guard`: ตรวจสอบความสอดคล้องของการหมุนกลับหัว 180° ตามตารางความสมมาตร `FLIP_MAP`
   * `cross_check_digits`: ใช้แบบจำลอง SigLIP2 ตรวจทานซ้ำเฉพาะหลักที่ค่าความเชื่อมั่นต่ำกว่าเกณฑ์ (< 0.60)
5. **ส่วนเชื่อมต่อพร้อมใช้งาน (Production-ready Interfaces):** ให้บริการผ่าน REST API ด้วย FastAPI (รองรับ Asynchronous Threadpool) พร้อม Interactive Swagger UI และเว็บแอปพลิเคชันสำหรับสาธิตด้วย Gradio

---

## 🏗️ สถาปัตยกรรมการประมวลผล (Pipeline Architecture)

1. **ภาพถ่ายมาตรวัดน้ำ RGB:** ข้อมูลภาพนำเข้าจากอุปกรณ์เคลื่อนที่หรือส่วนติดต่อผู้ใช้
2. **ขั้นตอนที่ 1: SigLIP2 Zero-shot Gatekeeper:**
   - ตรวจสอบชนิดวัตถุว่าเป็นมาตรวัดน้ำจริงหรือไม่ หากค่าความเชื่อมั่นต่ำกว่า 0.50 จะปฏิเสธคำขอทันที
   - อนุมัติภาพที่ผ่านเกณฑ์เข้าสู่ขั้นตอนถัดไป
3. **ขั้นตอนที่ 2: Multi-hypothesis Search (YOLO26):**
   - ประเมิน 12 สมมติฐาน (หมุน 4 ทิศทางร่วมกับ 3 ฟิลเตอร์ปรับคอนทราสต์แสง)
   - กำจัดกรอบซ้อนทับด้วย IoU Deduplication
   - คัดเลือกสมมติฐานที่ดีที่สุดด้วยคะแนนถ่วงน้ำหนัก
4. **ขั้นตอนที่ 3: Geometric Layout Filtering (`is_vertical`):**
   - ตรวจสอบอัตราส่วนความสูงต่อความกว้างของกลุ่มกล่องตัวเลข
   - กรองแถวแนวตั้งทิ้งเพื่อรักษาเฉพาะแถวตัวเลขหน้าปัดแนวนอน
5. **ขั้นตอนที่ 4: Safety Guards & Warnings Generation:**
   - ตรวจสอบการกลับหัว 180 องศาด้วยฟังก์ชัน `flip_guard` ร่วมกับตาราง `FLIP_MAP`
   - คำนวณความตรงของแนวแถวตัวเลข (Alignment Spread)
   - ตรวจทานหลักที่ค่าความเชื่อมั่นต่ำกว่าเกณฑ์ด้วย SigLIP2 Cross-check
   - แปลงพิกัด Bounding Box กลับสู่ระนาบภาพต้นฉบับด้วยฟังก์ชัน `remap_bbox`
6. **ผลลัพธ์ JSON:** ส่งออกค่าตัวเลขที่อ่านได้ ค่าความเชื่อมั่นเฉลี่ย และรายการแจ้งเตือนความเสี่ยงครบถ้วน


---

## 📁 โครงสร้างโปรเจกต์ (Project Directory Structure)

```text
meter-reader/
├── main.py                     # เว็บเซอร์วิสหลัก FastAPI และท่อส่งข้อมูล read_meter()
├── gradio_app.py               # หน้าต่างส่วนติดต่อผู้ใช้บนเว็บด้วย Gradio
├── utils.py                    # โมดูลฟังก์ชันส่วนกลางสำหรับการประมวลผลภาพและเรขาคณิต (DRY)
├── validate.py                 # สคริปต์ประเมิน End-to-End พร้อมช่วงความเชื่อมั่น Wilson Score 95% CI
├── validate_ablation.py        # สคริปต์ทดสอบการศึกษาเชิงตัดทอน 8 ขั้นตอน (Progressive Ablation M0–M7)
├── eval_yolo_metrics.py        # สคริปต์ประเมินประสิทธิภาพตัวตรวจจับ YOLO26m บน Held-out Test Split
├── meter_dataset.yaml          # ไฟล์คอนฟิกูเรชันชุดข้อมูลสำหรับ Ultralytics YOLO
├── requirements.txt            # รายการไลบรารีและแพ็กเกจที่ต้องติดตั้ง
├── LICENSE                     # สัญญาอนุญาตการใช้งานซอฟต์แวร์ (GNU AGPLv3)
├── TUTORIAL.md                 # คู่มือฉบับเต็มภาษาไทยตามมาตรฐานงานวิจัยเชิงประจักษ์ (v2.15)
├── meter_img/                  # ชุดภาพตัวอย่างสาธิตมาตรวัดน้ำ (Demo Set, n=7)
│   └── ground_truth.csv        # ค่าเฉลยตัวเลขของชุดภาพสาธิต
├── tests/                      # ชุดทดสอบอัตโนมัติ (Automated Unit Tests)
│   ├── __init__.py
│   └── test_pipeline.py        # ชุดทดสอบ 11 รายการ ครอบคลุมการหมุนภาพ แปลงพิกัด และฟังก์ชันตรรกะ
├── reviews/                    # รายงานผลการประเมินและเบঞ্চมาร์กเชิงประจักษ์
│   ├── ablation.json           # ข้อมูลผลการรัน Progressive Ablation M0–M7 (JSON)
│   ├── ablation.csv            # ข้อมูลผลการรัน Progressive Ablation M0–M7 (CSV)
│   ├── validation_results.json # ผลการทดสอบ End-to-End รายภาพ (JSON)
│   ├── validation_results.csv  # ผลการทดสอบ End-to-End รายภาพ (CSV)
│   └── yolo_metrics.json       # ผลการวัด Precision, Recall, mAP@50, mAP@50:95 รายคลาส
├── weights/                    # ที่จัดเก็บไฟล์น้ำหนักแบบจำลอง
│   └── MeterOCR.pt             # ไฟล์น้ำหนัก YOLO26m ที่ผ่านการฝึกแล้ว (132 layers, 20.36M params)
└── training/                   # โค้ดสำหรับการฝึกฝนแบบจำลอง
    └── yolo_train.py           # สคริปต์การฝึก YOLO บน Roboflow Dataset
```

---

## 🛠️ การติดตั้งสภาพแวดล้อม (Installation with `uv`)

> **ข้อกำหนดระบบ:** แนะนำ **Python 3.11** (รองรับ Python 3.10 – 3.12) และใช้เครื่องมือ **uv** เพื่อประสิทธิภาพและความรวดเร็ว

### 1. ติดตั้งเครื่องมือ `uv` (หากยังไม่มี)
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. สร้าง Virtual Environment และติดตั้ง Dependencies
```powershell
# สร้างสภาพแวดล้อมเสมือนด้วย Python 3.11
uv venv --python 3.11

# ติดตั้งแพ็กเกจทั้งหมดตาม requirements.txt
uv pip install -r requirements.txt
```

---

## 🚀 การสั่งทำงานระบบ (Running the Application)

### เทอร์มินัลที่ 1 — เริ่มต้นการทำงานของ FastAPI Backend:
```powershell
uv run python main.py
```
* **API Service:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Interactive Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **สถานะความพร้อมของระบบ:** `GET http://127.0.0.1:8000/api/health`

### เทอร์มินัลที่ 2 — เริ่มต้นการทำงานของ Gradio Web UI:
```powershell
uv run python gradio_app.py
```
* **Web UI URL:** [http://127.0.0.1:7860](http://127.0.0.1:7860)

### ตัวอย่างการทดสอบส่งภาพผ่าน cURL:
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/read-meter -F "file=@meter_img/meter_sample_07.jpg"
```

---

## 📊 ผลการประเมินประสิทธิภาพเชิงประจักษ์ (Empirical Evaluation)

### 1. ประสิทธิภาพการอ่านค่ามิเตอร์ทั้งระบบบนชุดทดสอบมาตรฐาน (Held-out Test Split, N=120 ภาพ)
ประเมินแบบ End-to-End บนชุดข้อมูลทดสอบอิสระขนาดใหญ่ ($N=120$ ภาพ ประกอบด้วยตัวเลขเฉลย Ground Truth 941 หลัก) ที่สกัดจาก Roboflow Test Split:

| ตัวชี้วัดประสิทธิภาพ (Metric) | ผลการวัดจริง | ช่วงความเชื่อมั่น Wilson 95% CI | คำอธิบายเชิงวิชาการ |
|---|:---:|:---:|---|
| **Exact Reading Accuracy** | **67.5%** (81/120) | [58.7%, 75.2%] | สัดส่วนภาพที่อ่านค่าตรงกับเฉลยครบทุกหลัก 100% |
| **Digit-level Accuracy** | **90.44%** (851/941) | [88.4%, 92.2%] | สัดส่วนตำแหน่งตัวเลขที่ทำนายถูกต้องต่อจำนวนหลักทั้งหมด |
| **Digit Error Rate (DER)** | **7.33%** (0.0733) | - | อัตราความผิดพลาด คำนวณจาก $(S+D+I)/N_{\text{ref}}$ |
| **Mean Model Confidence** | **0.8566** | [0.798, 0.895] | ค่าความเชื่อมั่นเฉลี่ยของกล่องตัวเลขจากแบบจำลอง YOLO |
| **Reading Success Rate** | **100.0%** (120/120) | [96.9%, 100.0%] | สัดส่วนภาพที่ระบบส่งคืนผลลัพธ์โดยไม่ล้มเหลว |
| **เวลาประมวลผลเฉลี่ย (CPU)** | **533.2 ms ต่อภาพ** | [490.2, 661.0] ms | วัดบน CPU AMD Ryzen 5 8645HS ที่ความละเอียด 960x960 |

*(ข้อมูลและผลลัพธ์รายภาพบันทึกใน `reviews/test_ground_truth.csv`, `reviews/test_set_evaluation.json`, และ `reviews/test_set_evaluation.csv`)*

---

### 2. ประสิทธิภาพตัวตรวจจับวัตถุ YOLO26m บนชุดทดสอบอิสระ (Held-out Test Split, N=194 ภาพ)
ประเมินบนชุดข้อมูลทดสอบมาตรฐานที่ถูกแยกไว้ต่างหาก ($N=194$ ภาพ ประกอบด้วยตัวอย่างตัวเลข 1,508 ตัวเลข) ที่ขนาดความละเอียดภาพ $960 \times 960$ พิกเซล เกณฑ์ความเชื่อมั่น $Conf \ge 0.35$ และ $IoU \ge 0.45$:

| ตัวชี้วัด (Metric) | ผลลัพธ์ภาพรวม (All Classes) | คลาสตัวเลข '0' (Leading Zeros) |
|---|:---:|:---:|
| **Precision** | **93.53%** | 95.60% |
| **Recall** | **89.30%** | 96.37% |
| **F1-Score** | **91.37%** | 95.98% |
| **mAP@50** | **87.86%** | 95.93% |
| **mAP@50:95** | **47.71%** | 56.48% |

*(รันซ้ำได้ด้วยคำสั่ง `uv run python eval_yolo_metrics.py` ข้อมูลบันทึกใน `reviews/yolo_metrics.json`)*

---

### 3. ผลการศึกษาเชิงตัดทอนแบบก้าวหน้า 8 ขั้นตอน (Progressive Ablation Benchmark)
ประเมินคุณูปการส่วนเพิ่มของแต่ละองค์ประกอบบนชุดภาพสาธิต ($N=7$ ภาพ, CPU AMD Ryzen 5 8645HS, 960x960):

| ขั้นตอน (Stage) | องค์ประกอบที่เปิดใช้งาน | Exact Reading Acc | ช่วงความเชื่อมั่น Wilson 95% CI | Latency เฉลี่ย | ผลกระทบเชิงประจักษ์ |
|:---:|---|:---:|:---:|:---:|---|
| **M0** | Baseline (0° เดี่ยว, ภาพต้นฉบับ) | **42.9%** (3/7) | [15.8%, 75.0%] | **421.1 ms** | อ่านผิด 4 จาก 7 ภาพเมื่อภาพถ่ายเอียง |
| **M1** | + Multi-Angle Search (หมุน 4 ทิศ) | **57.1%** (4/7) | [25.0%, 84.2%] | 1,710.3 ms | **+14.2%** กู้คืนภาพที่ถ่ายเอียง 270° |
| **M2** | + Contrast Preprocessing (CLAHE + HistEq = 12 สมมติฐาน) | **71.4%** (5/7) | [35.9%, 91.8%] | 5,492.6 ms | **+14.3%** กู้คืนภาพที่มีคราบสกปรก |
| **M3** | + Vertical Layout Guard (`is_vertical`) | **85.7%** (6/7) | [48.7%, 97.4%] | 5,561.3 ms | **+14.3%** กรองมุมที่ตัวเลขเรียงแนวตั้งออก |
| **M4** | + Red Digit Bonus (`red_ratio` & `score_reading`) | **100.0%** (7/7) | [64.6%, 100.0%] | 4,952.6 ms | **+14.3%** แยกแยะหลักทศนิยมสีแดงได้ถูกต้อง |
| **M5** | + Symmetry Inversion Guard (`flip_guard`) | **100.0%** (7/7) | [64.6%, 100.0%] | 5,578.6 ms | ป้องกันข้อผิดพลาดจากตัวเลขกลับหัวสมมาตร |
| **M6** | + Consistency Cross-Check (`cross_check_digits`) | **100.0%** (7/7) | [64.6%, 100.0%] | 5,664.7 ms | ตรวจทานตัวเลขความเชื่อมั่นต่ำร่วมกับ SigLIP2 |
| **M7** | + Full Pipeline (SigLIP2 Gatekeeper + Full Guards) | **100.0%** (7/7) | [64.6%, 100.0%] | 5,828.8 ms | บูรณาการไปป์ไลน์เต็มรูปแบบสำหรับ Production |

> [!NOTE]
> **ข้อพิจารณาทางสถิติ:** แม้ผลลัพธ์ในขั้น M4–M7 จะได้อัตราการอ่านค่าถูกต้อง 100.0% (7/7 ภาพ) บนชุดสาธิต แต่ช่วงความเชื่อมั่นทางสถิติ Wilson 95% CI มีขอบเขตกว้าง $[64.6\%, 100.0\%]$ เนื่องจากขนาดตัวอย่าง $N=7$ ยังมีจำกัด การสรุปความสามารถในการนำไปใช้งานจริงภาคสนามจำเป็นต้องขยายชุดทดสอบเป็น $N \ge 100$ ภาพตามที่ระบุไว้ในเอกสารคู่มือ

---

## 🧪 การทดสอบระบบและการตรวจสอบความถูกต้อง (Verification Suite)

### 1. การรัน Unit Tests
```powershell
uv run python -m unittest discover -s tests
```
*(ผ่านการทดสอบ 11/11 รายการ ครอบคลุมการหมุนภาพ แปลงพิกัดเรขาคณิต ฟังก์ชันคัดกรองแนวตั้ง ฟังก์ชันคำนวณ Wilson Score CI)*

### 2. การประเมิน End-to-End Pipeline
```powershell
uv run python validate.py --dir meter_img --gt meter_img/ground_truth.csv
```

### 3. การรัน Progressive Ablation Study (M0–M7)
```powershell
uv run python validate_ablation.py --dir meter_img --gt meter_img/ground_truth.csv
```

### 4. การประเมินผลตัวตรวจจับ YOLO บน Test Split
```powershell
uv run python eval_yolo_metrics.py
```

---

## 📦 รูปแบบผลลัพธ์ของ API (Response Payload Example)

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
  "mean_confidence": 0.9110,
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
  "elapsed_ms": 5828.8
}
```

*กรณีไม่ใช่ภาพมาตรวัดน้ำ:* คืนค่า `"reading": ""` และ `"meter_check": {"verified": false, ...}` พร้อมคำเตือน `"ภาพนี้ไม่ใช่มิเตอร์น้ำ (predicted_class)"`

---

## 📖 เอกสารคู่มือฉบับเต็มและงานวิจัยที่เกี่ยวข้อง (Documentation)

* **คู่มือการพัฒนาระบบและรายงานวิจัยฉบับสมบูรณ์ (v2.15):** [TUTORIAL.md](file:///d:/_Work/Guidebook-RE/meter-reader/TUTORIAL.md)
* **การอ้างอิงและบรรณานุกรมสำคัญ:**
  * **Ultralytics YOLO:** Ultralytics (2024), Jocher et al. (2023)
  * **SigLIP / SigLIP2:** Zhai et al. (2023), Tschannen et al. (2025)
  * **Automatic Water Meter Reading:** Liang et al. (2022), Wang & Xiang (2024), Salomon et al. (2022)

---

## 📜 ลิขสิทธิ์และการใช้งาน (License)

โปรเจกต์นี้เผยแพร่ภายใต้สัญญาอนุญาต **GNU Affero General Public License v3.0 (AGPL-3.0)** ดูรายละเอียดฉบับเต็มได้ที่ไฟล์ [LICENSE](file:///d:/_Work/Guidebook-RE/meter-reader/LICENSE)

* **ความเข้ากันได้กับไลบรารีภายนอก:**
  * **Ultralytics YOLO:** AGPL-3.0 (สอดคล้องตามข้อกำหนดของ Ultralytics)
  * **SigLIP2 (Google):** Apache License 2.0 (เข้ากันได้กับ AGPLv3)
  * **FastAPI & Gradio:** MIT / Apache License 2.0 (เข้ากันได้กับ AGPLv3)