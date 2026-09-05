"""
validate.py — Auto-validate Water Meter OCR with dataset images
Usage:
  Local:  uv run python validate.py                          # uses meter_img/ and auto-loads ground_truth.csv
          uv run python validate.py --limit 3                # only 3 images (for quick test)
          uv run python validate.py --dir meter_img --gt meter_img/ground_truth.csv
          uv run python validate.py --dir meter_img --limit 5 --out reviews/validation_results.json
          uv run python validate.py --no-progress            # disable tqdm

Metrics (per spec TUTORIAL.md 3.4.3):
  - Detection: per-image elapsed_ms, num_digits, mean_confidence
  - Application: reading (exact vs GT), digit_accuracy, meter_check.verified, warnings, processing.best (angle, prep)
  - Summary: success rate, verified rate, avg confidence, avg latency, exact reading accuracy, digit accuracy
No fabricated mAP — use model.val() separately for detection mAP.
"""
from __future__ import annotations
import argparse, json, csv, time
from pathlib import Path
from PIL import Image
import numpy as np


def load_gt(gt_path: Path | None) -> dict[str, str]:
    if not gt_path or not Path(gt_path).exists():
        return {}
    gt = {}
    with Path(gt_path).open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            file = (row.get("file") or row.get("filename") or "").strip()
            reading = (row.get("reading") or row.get("ground_truth") or "").strip()
            if file:
                gt[Path(file).name] = reading
    return gt


def compute_digit_accuracy(pred: str, gt: str) -> float:
    if not gt:
        return 0.0
    matches = sum(1 for p, g in zip(pred, gt) if p == g)
    return matches / max(len(pred), len(gt))


def wilson_score_interval(k: int, n: int, z: float = 1.95996) -> tuple[float, float]:
    """Computes Wilson Score Interval (default 95% confidence, z=1.96).

    Handles boundary cases (k=0, k=n) correctly without degenerating.
    """
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    margin = (z * ((p * (1.0 - p) / n + (z**2) / (4 * (n**2))) ** 0.5)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def run_validation(
    image_dir: Path,
    output_json: Path,
    output_csv: Path | None = None,
    gt_path: Path | None = None,
    limit: int | None = None,
    show_progress: bool = True,
):
    from main import read_meter, DEVICE, YOLO_IMGSZ
    print(f"DEVICE={DEVICE} YOLO_IMGSZ={YOLO_IMGSZ} image_dir={image_dir}")
    image_dir = Path(image_dir)
    images = sorted([p for p in image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}])
    if limit is not None and limit > 0:
        images = images[:limit]
        print(f"Limit: {limit} images (from {len(list(image_dir.iterdir()))} total)")
    if not images:
        print(f"No images found in {image_dir}")
        return []
    print(f"Found {len(images)} images to validate")

    # Load Ground Truth
    if gt_path is None:
        default_gt = image_dir / "ground_truth.csv"
        if default_gt.exists():
            gt_path = default_gt

    gt = load_gt(gt_path)
    if gt:
        print(f"Loaded Ground Truth: {len(gt)} entries from {gt_path}")
    else:
        print("No Ground Truth provided/found — Exact Reading Accuracy will be skipped.")

    # progress helper
    try:
        from tqdm import tqdm
        has_tqdm = True
    except ImportError:
        has_tqdm = False

    results = []
    iterator = tqdm(images, desc="Validating", unit="img", ncols=80) if (show_progress and has_tqdm) else images
    for idx, p in enumerate(iterator, 1):
        if not has_tqdm and show_progress:
            print(f"[{idx}/{len(images)}] Processing {p.name} ...")
        elif has_tqdm and show_progress:
            iterator.set_postfix_str(p.name[:20])

        try:
            img = Image.open(p)
            img.load()
            arr = np.asarray(img.convert("RGB"))
        except Exception as e:
            print(f"SKIP {p.name}: {e}")
            continue

        t0 = time.perf_counter()
        out = read_meter(arr)
        measured = (time.perf_counter() - t0) * 1000

        pred_reading = out.get("reading", "")
        gt_reading = gt.get(p.name)
        exact_match = (pred_reading == gt_reading) if gt_reading is not None else None
        digit_acc = compute_digit_accuracy(pred_reading, gt_reading) if gt_reading is not None else None

        row = {
            "file": p.name,
            "path": str(p),
            "reading": pred_reading,
            "gt": gt_reading,
            "exact": exact_match,
            "digit_accuracy": round(digit_acc, 4) if digit_acc is not None else None,
            "num_digits": len(out.get("digits", [])),
            "digits": out.get("digits", []),
            "mean_confidence": out.get("mean_confidence"),
            "meter_check": out.get("meter_check", {}),
            "processing": out.get("processing", {}),
            "warnings": out.get("warnings", []),
            "elapsed_ms_reported": out.get("elapsed_ms"),
            "elapsed_ms_measured": round(measured, 1),
            "success": bool(pred_reading),
            "verified": bool(out.get("meter_check", {}).get("verified")),
        }
        results.append(row)
        best = (out.get("processing") or {}).get("best") or {}

        if not (show_progress and has_tqdm):
            exact_str = f" exact={exact_match}" if exact_match is not None else ""
            print(
                f"  -> reading='{row['reading']}'{exact_str} digits={row['num_digits']} "
                f"mean_conf={row['mean_confidence']} verified={row['verified']} best={best} "
                f"elapsed={row['elapsed_ms_measured']}ms warnings={len(row['warnings'])}"
            )
        elif has_tqdm:
            iterator.set_postfix_str(f"{p.name[:12]} -> {row['reading'] or '—'}")

    # Save JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved JSON to {output_json}")

    # Save CSV (flat)
    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "file", "reading", "gt", "exact", "digit_accuracy", "num_digits",
            "mean_confidence", "verified", "predicted_class", "confidence",
            "angle", "prep", "elapsed_ms_reported", "elapsed_ms_measured", "warnings"
        ]
        with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in results:
                mc = r.get("meter_check", {})
                best = (r.get("processing") or {}).get("best") or {}
                w.writerow({
                    "file": r["file"],
                    "reading": r["reading"],
                    "gt": r["gt"],
                    "exact": r["exact"],
                    "digit_accuracy": r["digit_accuracy"],
                    "num_digits": r["num_digits"],
                    "mean_confidence": r["mean_confidence"],
                    "verified": r["verified"],
                    "predicted_class": mc.get("predicted_class"),
                    "confidence": mc.get("confidence"),
                    "angle": best.get("angle"),
                    "prep": best.get("prep"),
                    "elapsed_ms_reported": r["elapsed_ms_reported"],
                    "elapsed_ms_measured": r["elapsed_ms_measured"],
                    "warnings": " | ".join(r["warnings"]),
                })
        print(f"Saved CSV to {output_csv}")

    # Summary
    total = len(results)
    success = sum(1 for r in results if r["success"])
    verified = sum(1 for r in results if r["verified"])
    print("\n=== Summary ===")
    print(f"Total images: {total}")
    
    succ_ci = wilson_score_interval(success, total) if total else (0.0, 0.0)
    print(f"Successful readings (non-empty): {success}/{total} ({success/total*100:.1f}%) [95% CI: {succ_ci[0]*100:.1f}%–{succ_ci[1]*100:.1f}%]" if total else "0")
    print(f"Meter verified (SigLIP2): {verified}/{total} ({verified/total*100:.1f}%)" if total else "0")

    if gt:
        gt_count = sum(1 for r in results if r["gt"] is not None)
        exact_count = sum(1 for r in results if r["exact"] is True)
        digit_accs = [r["digit_accuracy"] for r in results if r["digit_accuracy"] is not None]
        avg_digit_acc = sum(digit_accs) / len(digit_accs) if digit_accs else 0.0
        exact_ci = wilson_score_interval(exact_count, gt_count) if gt_count else (0.0, 0.0)
        print(f"Exact Reading Accuracy: {exact_count}/{gt_count} ({exact_count/gt_count*100:.1f}%) [95% Wilson CI: {exact_ci[0]*100:.1f}%–{exact_ci[1]*100:.1f}%]" if gt_count else "0")
        print(f"Digit-level Accuracy: {avg_digit_acc*100:.1f}%")

    if success:
        mcs = [r["mean_confidence"] for r in results if r["success"] and r["mean_confidence"] is not None]
        if mcs:
            print(f"Avg mean_confidence (success): {sum(mcs)/len(mcs):.3f}")

    if results:
        els = [r["elapsed_ms_measured"] for r in results]
        print(f"Latency measured: min {min(els):.1f} / avg {sum(els)/len(els):.1f} / max {max(els):.1f} ms")
        print(f"Hardware: {DEVICE} | YOLO_IMGSZ={YOLO_IMGSZ} | 12 hypotheses (4x3)")

    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=str, default="meter_img", help="image folder")
    ap.add_argument("--gt", type=str, default=None, help="ground truth CSV (file,reading)")
    ap.add_argument("--out", type=str, default="reviews/validation_results.json", help="output JSON")
    ap.add_argument("--csv", type=str, default="reviews/validation_results.csv", help="output CSV (empty to skip)")
    ap.add_argument("--limit", type=int, default=None, help="limit number of images to validate (e.g., 5, 20)")
    ap.add_argument("--no-progress", action="store_true", help="disable progress bar")
    args = ap.parse_args()

    run_validation(
        Path(args.dir),
        Path(args.out),
        Path(args.csv) if args.csv else None,
        gt_path=Path(args.gt) if args.gt else None,
        limit=args.limit,
        show_progress=not args.no_progress,
    )
