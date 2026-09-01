"""
validate.py — Auto-validate Water Meter OCR with dataset images
Usage:
  Local:  uv run python validate.py                          # uses meter_img/ (all)
          uv run python validate.py --limit 3                # only 3 images (for quick test)
          uv run python validate.py --dir meter_img --limit 5 --out reviews/validation_results.json
          uv run python validate.py --no-progress            # disable tqdm
  HF Space will import this as batch validation tab.

Metrics (per spec TUTORIAL.md 3.4.3):
  - Detection: per-image elapsed_ms, num_digits, mean_confidence
  - Application: reading (exact), meter_check.verified, warnings, processing.best (angle, prep)
  - Summary: success rate, verified rate, avg confidence, avg latency
No fabricated mAP — use model.val() separately for detection mAP.
"""
from __future__ import annotations
import argparse, json, csv, time
from pathlib import Path
from PIL import Image
import numpy as np

def run_validation(image_dir: Path, output_json: Path, output_csv: Path | None = None, limit: int | None = None, show_progress: bool = True):
    from main import read_meter, DEVICE, YOLO_IMGSZ
    print(f"DEVICE={DEVICE} YOLO_IMGSZ={YOLO_IMGSZ} image_dir={image_dir}")
    image_dir = Path(image_dir)
    images = sorted([p for p in image_dir.iterdir() if p.suffix.lower() in {".jpg",".jpeg",".png",".bmp",".webp"}])
    if limit is not None and limit > 0:
        images = images[:limit]
        print(f"Limit: {limit} images (from {len(list(image_dir.iterdir()))} total)")
    if not images:
        print(f"No images found in {image_dir}")
        return []
    print(f"Found {len(images)} images to validate")
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
        measured = (time.perf_counter()-t0)*1000
        row = {
            "file": p.name,
            "path": str(p),
            "reading": out.get("reading",""),
            "num_digits": len(out.get("digits",[])),
            "digits": out.get("digits",[]),
            "mean_confidence": out.get("mean_confidence"),
            "meter_check": out.get("meter_check",{}),
            "processing": out.get("processing",{}),
            "warnings": out.get("warnings",[]),
            "elapsed_ms_reported": out.get("elapsed_ms"),
            "elapsed_ms_measured": round(measured,1),
            "success": bool(out.get("reading")),
            "verified": bool(out.get("meter_check",{}).get("verified")),
        }
        results.append(row)
        best = (out.get("processing") or {}).get("best") or {}
        if not (show_progress and has_tqdm):
            print(f"  -> reading='{row['reading']}' digits={row['num_digits']} mean_conf={row['mean_confidence']} verified={row['verified']} best={best} elapsed={row['elapsed_ms_measured']}ms warnings={len(row['warnings'])}")
        elif has_tqdm:
            iterator.set_postfix_str(f"{p.name[:12]} -> {row['reading'] or '—'}")

    # Save JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved JSON to {output_json}")

    # Save CSV (flat)
    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["file","reading","num_digits","mean_confidence","verified","predicted_class","confidence","angle","prep","elapsed_ms_reported","elapsed_ms_measured","warnings"])
            w.writeheader()
            for r in results:
                mc = r.get("meter_check",{})
                best = (r.get("processing") or {}).get("best") or {}
                w.writerow({
                    "file": r["file"],
                    "reading": r["reading"],
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
    print(f"Total: {total}")
    print(f"Successful readings: {success}/{total} ({success/total*100:.1f}%)" if total else "0")
    print(f"Meter verified: {verified}/{total} ({verified/total*100:.1f}%)" if total else "0")
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
    ap.add_argument("--out", type=str, default="reviews/validation_results.json", help="output JSON")
    ap.add_argument("--csv", type=str, default="reviews/validation_results.csv", help="output CSV (empty to skip)")
    ap.add_argument("--limit", type=int, default=None, help="limit number of images to validate (e.g., 5, 20)")
    ap.add_argument("--no-progress", action="store_true", help="disable progress bar")
    args = ap.parse_args()
    run_validation(Path(args.dir), Path(args.out), Path(args.csv) if args.csv else None, limit=args.limit, show_progress=not args.no_progress)
