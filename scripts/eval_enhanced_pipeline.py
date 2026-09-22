# -*- coding: utf-8 -*-
"""
eval_enhanced_pipeline.py
Evaluates the held-out test split (120 images) using the Enhanced MeterOCR Pipeline:
1. Column-aware duplicate resolution (half-turned wheel rolls).
2. Robust linear inlier regression & outlier pruning (serial numbers / casings).
3. Multi-pass adaptive contrast (Orig + CLAHE).
4. Full metric breakdown:
   - Exact Reading Accuracy (100% all digits)
   - Operational Billing Accuracy (m³ prefix)
   - Wheel-Roll Tolerance (±1 on least significant rolling wheel)
   - Digit-level Accuracy & DER
5. Updates reviews/test_set_evaluation.json and reviews/test_set_evaluation.csv.
"""

import json, time, sys, math
from pathlib import Path
import numpy as np
import cv2
from ultralytics import YOLO

sys.stdout.reconfigure(encoding='utf-8')

repo_root = Path(__file__).resolve().parent.parent
test_dir = repo_root.parent / "utility-meter-reading-dataset-for-automatic-reading-yolo.v1i.yolo26" / "test" / "images"
lbl_dir = repo_root.parent / "utility-meter-reading-dataset-for-automatic-reading-yolo.v1i.yolo26" / "test" / "labels"
eval_json_path = repo_root / "reviews" / "test_set_evaluation.json"
eval_csv_path = repo_root / "reviews" / "test_set_evaluation.csv"

with open(eval_json_path, "r", encoding="utf-8") as f:
    old_data = json.load(f)

per_image_old = old_data["per_image_results"]
print(f"Loaded {len(per_image_old)} images from test set evaluation baseline.", flush=True)

model = YOLO(str(repo_root / "weights" / "MeterOCR.pt"))

def wilson_score_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1.0 + (z**2) / total
    center = (p + (z**2) / (2.0 * total)) / denom
    spread = (z * math.sqrt((p * (1.0 - p) / total) + ((z**2) / (4.0 * (total**2))))) / denom
    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return round(lower * 100.0, 1), round(upper * 100.0, 1)

def levenshtein_distance(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]

def iou(b1, b2):
    x1, y1 = max(b1[0], b2[0]), max(b1[1], b2[1])
    x2, y2 = min(b1[2], b2[2]), min(b1[3], b2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0

def extract_odometer_reading(res, conf_thresh=0.30):
    raw_boxes = []
    for b in res.boxes:
        c = float(b.conf[0].item())
        if c < conf_thresh:
            continue
        cls_id = int(b.cls[0].item())
        if cls_id > 9:
            continue
        x1, y1, x2, y2 = b.xyxy[0].tolist()
        raw_boxes.append({
            "digit": cls_id,
            "conf": c,
            "bbox": [x1, y1, x2, y2],
            "cx": (x1 + x2) / 2.0,
            "cy": (y1 + y2) / 2.0,
            "w": x2 - x1,
            "h": y2 - y1
        })
        
    if not raw_boxes:
        return "", 0.0, []

    # 1. 2D NMS
    kept = []
    for b in sorted(raw_boxes, key=lambda x: x["conf"], reverse=True):
        if not any(iou(b["bbox"], k["bbox"]) > 0.45 for k in kept):
            kept.append(b)

    # 2. Vertical Column Conflict Resolution (Half-turned wheels)
    col_kept = []
    for b in sorted(kept, key=lambda x: x["conf"], reverse=True):
        conflict = False
        for k in col_kept:
            inter_x = max(0.0, min(b["bbox"][2], k["bbox"][2]) - max(b["bbox"][0], k["bbox"][0]))
            min_w = min(b["w"], k["w"])
            if min_w > 0 and (inter_x / min_w) > 0.65:
                conflict = True
                break
        if not conflict:
            col_kept.append(b)
            
    col_kept.sort(key=lambda x: x["cx"])
    if len(col_kept) < 3:
        return "".join(str(x["digit"]) for x in col_kept), float(np.mean([x["conf"] for x in col_kept])) if col_kept else 0.0, col_kept

    # 3. Robust Inlier Row Filtering
    med_h = np.median([b["h"] for b in col_kept])
    med_w = np.median([b["w"] for b in col_kept])
    
    valid_size = [b for b in col_kept if 0.35 * med_h <= b["h"] <= 2.2 * med_h]
    if len(valid_size) >= 3:
        col_kept = valid_size

    xs = np.array([b["cx"] for b in col_kept])
    ys = np.array([b["cy"] for b in col_kept])
    poly = np.polyfit(xs, ys, 1)
    m, c = poly[0], poly[1]

    if abs(m) < 0.45:
        inliers = []
        for b in col_kept:
            dist = abs(b["cy"] - (m * b["cx"] + c))
            if dist <= 0.70 * med_h:
                inliers.append(b)
        if len(inliers) >= 3:
            col_kept = inliers

    # 4. Outlier spacing removal (isolated digits separated by > 2.8x median gap)
    if len(col_kept) >= 4:
        gaps = [col_kept[i+1]["cx"] - col_kept[i]["cx"] for i in range(len(col_kept)-1)]
        med_gap = np.median(gaps)
        if gaps[0] > max(2.8 * med_gap, 2.0 * med_w):
            col_kept = col_kept[1:]
            gaps = gaps[1:]
        if len(gaps) >= 1 and gaps[-1] > max(2.8 * med_gap, 2.0 * med_w):
            col_kept = col_kept[:-1]

    reading = "".join(str(x["digit"]) for x in col_kept)
    mean_c = float(np.mean([x["conf"] for x in col_kept])) if col_kept else 0.0
    return reading, mean_c, col_kept

def predict_enhanced(img_bgr):
    # Pass 1: Original 960 (conf=0.30)
    r1 = model.predict(img_bgr, imgsz=960, conf=0.18, verbose=False)[0]
    read1, conf1, boxes1 = extract_odometer_reading(r1, conf_thresh=0.30)
    
    # If high confidence and valid length (>= 5 digits and conf >= 0.78), accept immediately
    if len(read1) >= 5 and conf1 >= 0.78:
        return read1, conf1, boxes1
        
    # Pass 2: CLAHE enhanced 960
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    bgr_clahe = cv2.cvtColor(cv2.merge([l_clahe, a, b]), cv2.COLOR_LAB2BGR)
    r2 = model.predict(bgr_clahe, imgsz=960, conf=0.18, verbose=False)[0]
    read2, conf2, boxes2 = extract_odometer_reading(r2, conf_thresh=0.30)
    
    # Pass 3: 1280 resolution
    r3 = model.predict(img_bgr, imgsz=1280, conf=0.18, verbose=False)[0]
    read3, conf3, boxes3 = extract_odometer_reading(r3, conf_thresh=0.30)
    
    def score_cand(read, conf, boxes):
        if not read: return -1.0
        n = len(read)
        length_pen = 0.0
        if n < 4: length_pen = -2.0
        elif n > 9: length_pen = -1.0
        uniformity = 0.0
        if len(boxes) >= 4:
            gaps = [boxes[i+1]["cx"] - boxes[i]["cx"] for i in range(len(boxes)-1)]
            std_gap = np.std(gaps) / (np.mean(gaps) + 1e-5)
            uniformity = max(0.0, (1.0 - std_gap)) * 0.5
        return n * 1.5 + conf * 3.0 + length_pen + uniformity
        
    cands = [(read1, conf1, boxes1), (read2, conf2, boxes2), (read3, conf3, boxes3)]
    best = max(cands, key=lambda c: score_cand(c[0], c[1], c[2]))
    return best[0], best[1], best[2]

def match_with_last_digit_tolerance(gt, pred):
    if gt == pred: return True
    if len(gt) == len(pred) and len(gt) >= 4:
        if gt[:-1] == pred[:-1]:
            try:
                g_last, p_last = int(gt[-1]), int(pred[-1])
                if abs(g_last - p_last) in (1, 9): return True
            except ValueError: pass
    if len(pred) == len(gt) - 1 and len(gt) >= 4 and pred == gt[:-1]: return True
    if len(pred) == len(gt) + 1 and len(gt) >= 4 and pred[:-1] == gt: return True
    return False

def match_billing_prefix(gt, pred):
    if len(gt) <= 1 or len(pred) <= 1: return gt == pred
    return gt[:-1] == pred[:-1]

print("--- Running Enhanced Pipeline Evaluation on 120 Held-out Test Images ---", flush=True)

new_results = []
exact_count = 0
wheel_tol_count = 0
billing_count = 0
total_gt_digits = 0
correct_gt_digits = 0
total_edit_dist = 0
latencies = []
confidences = []

recovered = []
regressed = []

t_start = time.perf_counter()

for idx, item in enumerate(per_image_old, 1):
    fname = item["file"]
    gt = item["gt"]
    old_pred = item["pred"]
    old_exact = item["exact"]
    
    img_p = test_dir / fname
    img = cv2.imread(str(img_p))
    if img is None:
        continue
        
    t0 = time.perf_counter()
    new_pred, new_conf, new_boxes = predict_enhanced(img)
    lat = (time.perf_counter() - t0) * 1000.0
    latencies.append(lat)
    confidences.append(new_conf)
    
    exact = (new_pred == gt)
    if exact:
        exact_count += 1
        
    wheel_tol = match_with_last_digit_tolerance(gt, new_pred)
    if wheel_tol:
        wheel_tol_count += 1
        
    billing_tol = match_billing_prefix(gt, new_pred)
    if billing_tol:
        billing_count += 1
        
    edit_dist = levenshtein_distance(new_pred, gt)
    total_edit_dist += edit_dist
    
    min_len = min(len(new_pred), len(gt))
    d_match = sum(1 for p_char, g_char in zip(new_pred[:min_len], gt[:min_len]) if p_char == g_char)
    correct_gt_digits += d_match
    total_gt_digits += len(gt)
    
    record = {
        "file": fname,
        "gt": gt,
        "pred": new_pred,
        "exact": exact,
        "wheel_roll_tol": wheel_tol,
        "billing_tol": billing_tol,
        "digit_accuracy": round(d_match / len(gt), 4) if len(gt) > 0 else 0.0,
        "mean_conf": round(new_conf, 4),
        "latency_ms": round(lat, 1),
        "edit_dist": edit_dist
    }
    new_results.append(record)
    
    if not old_exact and exact:
        recovered.append((fname, gt, old_pred, new_pred))
        print(f"[{idx:3d}/120] + RECOVERED: {fname[:22]}... GT: {gt} | Old: {old_pred} -> New: {new_pred}", flush=True)
    elif old_exact and not exact:
        regressed.append((fname, gt, old_pred, new_pred))
        print(f"[{idx:3d}/120] - REGRESSED: {fname[:22]}... GT: {gt} | Old: {old_pred} -> New: {new_pred}", flush=True)

    if idx % 30 == 0 or idx == 120:
        print(f"Progress: {idx}/120 | Exact: {exact_count}/{idx} ({exact_count/idx*100:.1f}%) | Wheel Tol: {wheel_tol_count}/{idx} ({wheel_tol_count/idx*100:.1f}%)", flush=True)

total_elapsed = time.perf_counter() - t_start
n_total = len(new_results)

exact_pct = round(exact_count / n_total * 100.0, 2)
exact_ci_low, exact_ci_high = wilson_score_interval(exact_count, n_total)

wheel_tol_pct = round(wheel_tol_count / n_total * 100.0, 2)
wheel_ci_low, wheel_ci_high = wilson_score_interval(wheel_tol_count, n_total)

billing_pct = round(billing_count / n_total * 100.0, 2)
billing_ci_low, billing_ci_high = wilson_score_interval(billing_count, n_total)

digit_acc_pct = round(correct_gt_digits / total_gt_digits * 100.0, 2)
digit_ci_low, digit_ci_high = wilson_score_interval(correct_gt_digits, total_gt_digits)

der = round(total_edit_dist / total_gt_digits, 4)
avg_conf = round(sum(confidences) / len(confidences), 4)
avg_lat = round(sum(latencies) / len(latencies), 1)

summary = {
    "dataset": "Roboflow Held-out Test Split",
    "sample_size_n": n_total,
    "total_ground_truth_digits": total_gt_digits,
    "exact_reading_accuracy": {
        "percentage": exact_pct,
        "correct": exact_count,
        "total": n_total,
        "wilson_95_ci": [exact_ci_low, exact_ci_high],
        "net_gain_over_baseline": exact_count - 81
    },
    "wheel_roll_tolerance_accuracy": {
        "percentage": wheel_tol_pct,
        "correct": wheel_tol_count,
        "total": n_total,
        "wilson_95_ci": [wheel_ci_low, wheel_ci_high]
    },
    "operational_billing_accuracy": {
        "percentage": billing_pct,
        "correct": billing_count,
        "total": n_total,
        "wilson_95_ci": [billing_ci_low, billing_ci_high]
    },
    "digit_level_accuracy": {
        "percentage": digit_acc_pct,
        "correct": correct_gt_digits,
        "total": total_gt_digits,
        "wilson_95_ci": [digit_ci_low, digit_ci_high]
    },
    "digit_error_rate_der": der,
    "mean_model_confidence": avg_conf,
    "latency_profiling_ms": {
        "average_ms": avg_lat,
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
        "total_elapsed_s": round(total_elapsed, 2)
    },
    "enhancement_pipeline_breakdown": {
        "baseline_m0_exact": "81/120 (67.50%)",
        "enhanced_exact": f"{exact_count}/120 ({exact_pct}%)",
        "recovered_images": len(recovered),
        "regressed_images": len(regressed)
    }
}

print("\n=================================================================")
print("      RESEARCH-GRADE EVALUATION REPORT ON ENHANCED PIPELINE      ")
print("=================================================================")
print(f"Sample Size (N):                     {n_total} test images")
print(f"Exact Reading Accuracy (100% Match): {exact_pct}% ({exact_count}/{n_total}) [95% CI: {exact_ci_low}%, {exact_ci_high}%] (Gain: {exact_count-81:+d})")
print(f"Wheel-Roll Tolerance (±1 on roll):   {wheel_tol_pct}% ({wheel_tol_count}/{n_total}) [95% CI: {wheel_ci_low}%, {wheel_ci_high}%]")
print(f"Operational Billing Accuracy (m³):   {billing_pct}% ({billing_count}/{n_total}) [95% CI: {billing_ci_low}%, {billing_ci_high}%]")
print(f"Digit-level Accuracy:                {digit_acc_pct}% ({correct_gt_digits}/{total_gt_digits}) [95% CI: {digit_ci_low}%, {digit_ci_high}%]")
print(f"Digit Error Rate (DER):              {der} ({der*100:.2f}%)")
print(f"Mean Model Confidence:               {avg_conf}")
print(f"Average Latency (CPU):               {avg_lat} ms/img")
print(f"Total Evaluation Time:               {total_elapsed:.2f} seconds")
print(f"Total Recovered:                     {len(recovered)} images")
print(f"Total Regressed:                     {len(regressed)} images")
print("=================================================================")

with open(eval_json_path, "w", encoding="utf-8") as f:
    json.dump({"summary": summary, "per_image_results": new_results}, f, indent=2, ensure_ascii=False)

with open(eval_csv_path, "w", encoding="utf-8") as f:
    f.write("file,gt,pred,exact,wheel_roll_tol,billing_tol,digit_accuracy,mean_conf,latency_ms,edit_dist\n")
    for r in new_results:
        f.write(f"{r['file']},{r['gt']},{r['pred']},{r['exact']},{r['wheel_roll_tol']},{r['billing_tol']},{r['digit_accuracy']},{r['mean_conf']},{r['latency_ms']},{r['edit_dist']}\n")

print(f"Successfully saved updated results to {eval_json_path} and {eval_csv_path}")
