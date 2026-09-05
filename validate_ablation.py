"""
validate_ablation.py — Ablation for OpenCV parts (rotate / CLAHE-HistEq / is_vertical / red_ratio)
Compares modes on same dataset, reports proxy metrics (success rate, mean_conf, latency).

Modes:
  1) single-orig        : YOLO single pass (0° + orig) — no rotate, no CLAHE/HistEq
  2) rotate-4           : 4 rotations (0/90/180/270) + orig only — tests rotate_image alone
  3) full-12            : 4 rotations × 3 preps (orig/clahe/histeq) — current pipeline core
  4) no-is-vertical     : full-12 but is_vertical disabled — tests is_vertical filter
  5) no-red-bonus       : full-12 but red_ratio bonus disabled — tests red_ratio alone

Usage:
  uv run python validate_ablation.py --dir meter_img --limit 5
  uv run python validate_ablation.py --dir meter_img --csv reviews/ablation.csv --json reviews/ablation.json

Notes:
  - Exact Reading Accuracy requires ground-truth CSV (file,reading). If --gt provided, will compute it.
  - Without GT, reports success_rate (non-empty reading), verified_rate, avg mean_conf, avg latency — comparable across modes.
  - All modes reuse same YOLO/SigLIP models (loaded once) — fair comparison.
"""
from __future__ import annotations
import argparse, json, csv, time, contextlib
from pathlib import Path
from PIL import Image
import numpy as np

def wilson_score_interval(k: int, n: int, z: float = 1.95996) -> tuple[float, float]:
    """Computes Wilson Score Interval (default 95% confidence, z=1.96)."""
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    margin = (z * ((p * (1.0 - p) / n + (z**2) / (4 * (n**2))) ** 0.5)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def patch_main_for_mode(mode: str):
    """Monkey-patch main.py globals for ablation. Returns restore fn.
    Supports 8 progressive ablation modes (M0 to M7) + legacy modes.
    """
    import main as m
    orig = {
        "ROTATION_ANGLES": m.ROTATION_ANGLES,
        "PREP_LIST": m.PREP_LIST,
        "is_vertical": m.is_vertical,
        "red_ratio": m.red_ratio,
        "flip_guard": m.flip_guard,
        "cross_check_digits": m.cross_check_digits,
        "check_water_meter": m.check_water_meter,
    }

    def is_vertical_noop(dets, img_w, img_h):
        return {"vertical": False}

    def red_ratio_zero(img_bgr, bbox):
        return 0.0

    def flip_guard_noop(rgb_img, digits, meta):
        return {"warned": False, "anti_reading": "", "anti_confidence": 0.0}

    def cross_check_noop(rgb_img, digits, h, w, angle=0):
        return []

    def check_water_meter_noop(rgb_img):
        return {"verified": True, "predicted_class": "water meter", "confidence": 1.0}

    # Reset all to no-op baseline first if in progressive mode
    if mode in {"M0_baseline", "single-orig"}:
        m.ROTATION_ANGLES = (0,)
        m.PREP_LIST = ("orig",)
        m.is_vertical = is_vertical_noop
        m.red_ratio = red_ratio_zero
        m.flip_guard = flip_guard_noop
        m.cross_check_digits = cross_check_noop
        m.check_water_meter = check_water_meter_noop
    elif mode in {"M1_rotate", "rotate-4"}:
        m.ROTATION_ANGLES = (0, 90, 180, 270)
        m.PREP_LIST = ("orig",)
        m.is_vertical = is_vertical_noop
        m.red_ratio = red_ratio_zero
        m.flip_guard = flip_guard_noop
        m.cross_check_digits = cross_check_noop
        m.check_water_meter = check_water_meter_noop
    elif mode == "M2_prep":
        m.ROTATION_ANGLES = (0, 90, 180, 270)
        m.PREP_LIST = ("orig", "clahe", "histeq")
        m.is_vertical = is_vertical_noop
        m.red_ratio = red_ratio_zero
        m.flip_guard = flip_guard_noop
        m.cross_check_digits = cross_check_noop
        m.check_water_meter = check_water_meter_noop
    elif mode == "M3_is_vertical":
        m.ROTATION_ANGLES = (0, 90, 180, 270)
        m.PREP_LIST = ("orig", "clahe", "histeq")
        m.is_vertical = orig["is_vertical"]
        m.red_ratio = red_ratio_zero
        m.flip_guard = flip_guard_noop
        m.cross_check_digits = cross_check_noop
        m.check_water_meter = check_water_meter_noop
    elif mode == "M4_red_ratio":
        m.ROTATION_ANGLES = (0, 90, 180, 270)
        m.PREP_LIST = ("orig", "clahe", "histeq")
        m.is_vertical = orig["is_vertical"]
        m.red_ratio = orig["red_ratio"]
        m.flip_guard = flip_guard_noop
        m.cross_check_digits = cross_check_noop
        m.check_water_meter = check_water_meter_noop
    elif mode == "M5_flip_guard":
        m.ROTATION_ANGLES = (0, 90, 180, 270)
        m.PREP_LIST = ("orig", "clahe", "histeq")
        m.is_vertical = orig["is_vertical"]
        m.red_ratio = orig["red_ratio"]
        m.flip_guard = orig["flip_guard"]
        m.cross_check_digits = cross_check_noop
        m.check_water_meter = check_water_meter_noop
    elif mode == "M6_cross_check":
        m.ROTATION_ANGLES = (0, 90, 180, 270)
        m.PREP_LIST = ("orig", "clahe", "histeq")
        m.is_vertical = orig["is_vertical"]
        m.red_ratio = orig["red_ratio"]
        m.flip_guard = orig["flip_guard"]
        m.cross_check_digits = orig["cross_check_digits"]
        m.check_water_meter = check_water_meter_noop
    elif mode in {"M7_full_pipeline", "full-12"}:
        m.ROTATION_ANGLES = orig["ROTATION_ANGLES"]
        m.PREP_LIST = orig["PREP_LIST"]
        m.is_vertical = orig["is_vertical"]
        m.red_ratio = orig["red_ratio"]
        m.flip_guard = orig["flip_guard"]
        m.cross_check_digits = orig["cross_check_digits"]
        m.check_water_meter = orig["check_water_meter"]
    elif mode == "no-is-vertical":
        m.ROTATION_ANGLES = (0, 90, 180, 270)
        m.PREP_LIST = ("orig", "clahe", "histeq")
        m.is_vertical = is_vertical_noop
    elif mode == "no-red-bonus":
        m.ROTATION_ANGLES = (0, 90, 180, 270)
        m.PREP_LIST = ("orig", "clahe", "histeq")
        m.red_ratio = red_ratio_zero
    else:
        raise ValueError(f"Unknown mode: {mode}")

    def restore():
        m.ROTATION_ANGLES = orig["ROTATION_ANGLES"]
        m.PREP_LIST = orig["PREP_LIST"]
        m.is_vertical = orig["is_vertical"]
        m.red_ratio = orig["red_ratio"]
        m.flip_guard = orig["flip_guard"]
        m.cross_check_digits = orig["cross_check_digits"]
        m.check_water_meter = orig["check_water_meter"]

    return restore

def load_gt(gt_path: Path | None):
    if not gt_path or not Path(gt_path).exists():
        return {}
    gt = {}
    import csv
    with Path(gt_path).open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # expect columns: file,reading
            file = (row.get("file") or row.get("filename") or "").strip()
            reading = (row.get("reading") or row.get("ground_truth") or "").strip()
            if file:
                gt[Path(file).name] = reading
    return gt

def run_one_mode(mode: str, image_dir: Path, gt: dict, limit: int | None, show_progress: bool):
    import main as m
    from main import read_meter
    images = sorted([p for p in Path(image_dir).iterdir() if p.suffix.lower() in {".jpg",".jpeg",".png",".bmp",".webp"}])
    if limit:
        images = images[:limit]
    if not images:
        return {"mode": mode, "results": [], "summary": {}}
    restore = patch_main_for_mode(mode)
    try:
        try:
            from tqdm import tqdm
            has_tqdm = True
        except ImportError:
            has_tqdm = False
        results = []
        iterator = tqdm(images, desc=mode, unit="img", ncols=90) if (show_progress and has_tqdm) else images
        for p in iterator:
            try:
                img = Image.open(p)
                img.load()
                arr = np.asarray(img.convert("RGB"))
            except Exception as e:
                print(f"SKIP {p.name}: {e}")
                continue
            t0 = time.perf_counter()
            out = read_meter(arr)
            elapsed = (time.perf_counter()-t0)*1000
            # Exact Reading Accuracy if GT available
            gt_reading = gt.get(p.name)
            exact = (gt_reading is not None and out.get("reading") == gt_reading) if gt_reading is not None else None
            row = {
                "file": p.name,
                "reading": out.get("reading",""),
                "gt": gt_reading,
                "exact": exact,
                "num_digits": len(out.get("digits",[])),
                "mean_confidence": out.get("mean_confidence"),
                "verified": bool(out.get("meter_check",{}).get("verified")),
                "processing": out.get("processing",{}),
                "warnings": out.get("warnings",[]),
                "elapsed_ms": round(elapsed,1),
            }
            results.append(row)
            if has_tqdm and show_progress:
                iterator.set_postfix_str(f"{p.name[:14]} -> {row['reading'] or '—'}")
        # summary
        total = len(results)
        success = sum(1 for r in results if r["reading"])
        verified = sum(1 for r in results if r["verified"])
        avg_conf = sum(r["mean_confidence"] for r in results if r["mean_confidence"] is not None) / max(1, sum(1 for r in results if r["mean_confidence"] is not None)) if results else 0
        avg_lat = sum(r["elapsed_ms"] for r in results)/total if total else 0
        succ_ci = wilson_score_interval(success, total) if total else (0.0, 0.0)
        summary = {
            "mode": mode,
            "total": total,
            "success_rate": round(success/total*100,1) if total else 0,
            "success_ci95": [round(succ_ci[0]*100, 1), round(succ_ci[1]*100, 1)],
            "verified_rate": round(verified/total*100,1) if total else 0,
            "avg_mean_conf": round(avg_conf,3) if results else None,
            "avg_latency_ms": round(avg_lat,1) if results else None,
        }
        if gt:
            exact_total = sum(1 for r in results if r["gt"] is not None)
            exact_ok = sum(1 for r in results if r["exact"] is True)
            exact_ci = wilson_score_interval(exact_ok, exact_total) if exact_total else (0.0, 0.0)
            summary["exact_reading_accuracy"] = round(exact_ok/exact_total*100,1) if exact_total else None
            summary["exact_ci95"] = [round(exact_ci[0]*100, 1), round(exact_ci[1]*100, 1)]
            summary["exact_n"] = f"{exact_ok}/{exact_total}"
        return {"mode": mode, "results": results, "summary": summary}
    finally:
        restore()

def main():
    ap = argparse.ArgumentParser(description="8-Stage Progressive Ablation for Meter Reader Pipeline (TUTORIAL.md 3.4.6)")
    ap.add_argument("--dir", type=str, default="meter_img", help="image folder")
    ap.add_argument("--limit", type=int, default=None, help="limit images per mode")
    ap.add_argument("--gt", type=str, default=None, help="ground truth CSV with columns file,reading (optional for Exact Accuracy)")
    ap.add_argument("--out", type=str, default="reviews/ablation.json", help="output JSON")
    ap.add_argument("--csv", type=str, default="reviews/ablation.csv", help="output CSV")
    ap.add_argument(
        "--modes",
        nargs="*",
        default=["M0_baseline", "M1_rotate", "M2_prep", "M3_is_vertical", "M4_red_ratio", "M5_flip_guard", "M6_cross_check", "M7_full_pipeline"],
        help="modes to compare (M0_baseline..M7_full_pipeline or legacy single-orig..full-12)"
    )
    ap.add_argument("--no-progress", action="store_true")
    args = ap.parse_args()

    gt = load_gt(Path(args.gt) if args.gt else None)
    if gt:
        print(f"Loaded GT: {len(gt)} entries from {args.gt}")
    else:
        print("No GT provided — will report success_rate / mean_conf / latency only (no Exact Accuracy)")

    # Warmup models once (load YOLO+SigLIP before timing modes)
    print("Warming up models...")
    import main as m
    m.get_yolo()
    try:
        m.get_siglip()
        print("SigLIP ready")
    except Exception as e:
        print(f"SigLIP warmup failed: {e}")

    all_summaries = []
    all_details = {}
    for mode in args.modes:
        print(f"\n=== Mode: {mode} ===")
        res = run_one_mode(mode, Path(args.dir), gt, args.limit, show_progress=not args.no_progress)
        all_summaries.append(res["summary"])
        all_details[mode] = res["results"]
        print(f"Summary {mode}: {res['summary']}")

    # Save JSON
    out_json = Path(args.out)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"summaries": all_summaries, "details": all_details, "gt_file": args.gt}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved JSON to {out_json}")

    if args.csv:
        out_csv = Path(args.csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="", encoding="utf-8-sig") as f:
            # header = mode,total,success_rate,verified_rate,avg_mean_conf,avg_latency,exact_accuracy
            fieldnames = ["mode","total","success_rate","verified_rate","avg_mean_conf","avg_latency_ms","exact_reading_accuracy","exact_n"]
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for s in all_summaries:
                w.writerow({k: s.get(k) for k in fieldnames})
        print(f"Saved CSV to {out_csv}")

    # Print comparison table to console
    print("\n=== Ablation Comparison ===")
    print(f"{'mode':<16} {'succ%':<6} {'ver%':<6} {'conf':<6} {'lat ms':<7} {'exact%':<7}")
    for s in all_summaries:
        print(f"{s['mode']:<16} {s['success_rate']:<6} {s['verified_rate']:<6} {s.get('avg_mean_conf','—'):<6} {s['avg_latency_ms']:<7} {s.get('exact_reading_accuracy','—'):<7}")

if __name__ == "__main__":
    main()
