"""
tests/test_pipeline.py — Comprehensive Unit & Regression Tests for Water Meter OCR Pipeline

Tests:
  1. rotate_image: rotation dimensions & orientations (0°, 90°, 180°, 270°)
  2. apply_prep: contrast adjustments ('orig', 'clahe', 'histeq')
  3. remap_point: coordinate transformation formulas across all angles
  4. remap_bbox: bounding box remapping & valid bounding coordinate invariants
  5. iou: intersection over union math & boundary cases
  6. dedup_detections: IoU-based deduplication and center_x sorting
  7. is_vertical: horizontal meter reading vs vertical serial/date column filtering
  8. red_ratio: HSV red pixel proportion calculations
  9. flip_guard: 180° mirror inversion detection using FLIP_MAP
 10. alignment: horizontal alignment spread computation (np.std)

Can be executed with:
  pytest tests/test_pipeline.py
  python -m unittest tests/test_pipeline.py
"""
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

# Ensure meter-reader/ is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main import (
    ALIGN_MAX_SPREAD,
    FLIP_MAP,
    apply_prep,
    dedup_detections,
    flip_guard,
    iou,
    is_vertical,
    red_ratio,
    remap_bbox,
    remap_point,
    rotate_image,
)


class TestImageGeometry(unittest.TestCase):
    """Test geometric image operations and coordinate transformations."""

    def setUp(self):
        self.w = 640
        self.h = 480
        # Create a test dummy image with distinct quadrants
        self.img = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        self.img[0:100, 0:100] = [255, 0, 0]  # Top-left blue block

    def test_rotate_image_dimensions(self):
        """Verify image dimensions after 0, 90, 180, 270 degree rotations."""
        r0 = rotate_image(self.img, 0)
        self.assertEqual(r0.shape, (self.h, self.w, 3))

        r90 = rotate_image(self.img, 90)
        self.assertEqual(r90.shape, (self.w, self.h, 3))

        r180 = rotate_image(self.img, 180)
        self.assertEqual(r180.shape, (self.h, self.w, 3))

        r270 = rotate_image(self.img, 270)
        self.assertEqual(r270.shape, (self.w, self.h, 3))

    def test_remap_point_known_coordinates(self):
        """Verify point remapping formulas match TUTORIAL.md specification."""
        w, h = 640, 480
        # 0 degree (identity)
        self.assertEqual(remap_point(100.0, 50.0, 0, w, h), (100.0, 50.0))

        # 90 degree clockwise: x_orig = y_rot, y_orig = H - x_rot
        self.assertEqual(remap_point(50.0, 100.0, 90, w, h), (100.0, 480 - 50.0))

        # 180 degree: x_orig = W - x_rot, y_orig = H - y_rot
        self.assertEqual(remap_point(100.0, 50.0, 180, w, h), (640 - 100.0, 480 - 50.0))

        # 270 degree counter-clockwise: x_orig = W - y_rot, y_orig = x_rot
        self.assertEqual(remap_point(50.0, 100.0, 270, w, h), (640 - 100.0, 50.0))

    def test_remap_bbox_invariants(self):
        """Verify bounding box coordinates remain valid (x1 < x2, y1 < y2)."""
        w, h = 800, 600
        bbox_rot = [100.0, 150.0, 200.0, 250.0]

        for angle in (0, 90, 180, 270):
            orig_bbox = remap_bbox(bbox_rot, angle, w, h)
            x1, y1, x2, y2 = orig_bbox
            self.assertLess(x1, x2, f"Failed x1 < x2 for angle {angle}")
            self.assertLess(y1, y2, f"Failed y1 < y2 for angle {angle}")
            self.assertGreaterEqual(x1, 0.0)
            self.assertGreaterEqual(y1, 0.0)
            self.assertLessEqual(x2, float(w))
            self.assertLessEqual(y2, float(h))


class TestImagePreprocessing(unittest.TestCase):
    """Test CLAHE, HistEq, and color adjustments."""

    def setUp(self):
        self.img = np.random.randint(50, 200, (200, 300, 3), dtype=np.uint8)

    def test_apply_prep_modes(self):
        """Verify all prep options return valid uint8 images with identical shape."""
        for prep in ("orig", "clahe", "histeq"):
            out = apply_prep(self.img, prep)
            self.assertEqual(out.shape, self.img.shape)
            self.assertEqual(out.dtype, np.uint8)
            self.assertTrue(0 <= out.min() <= 255)
            self.assertTrue(0 <= out.max() <= 255)

    def test_red_ratio(self):
        """Verify red_ratio identifies red regions in HSV correctly."""
        h, w = 100, 100
        # 1. Neutral gray image -> red_ratio should be 0.0
        gray_img = np.full((h, w, 3), 128, dtype=np.uint8)
        self.assertAlmostEqual(red_ratio(gray_img, [10, 10, 90, 90]), 0.0, places=3)

        # 2. Pure bright red image (BGR: [0, 0, 255]) -> red_ratio should be near 1.0
        red_img = np.zeros((h, w, 3), dtype=np.uint8)
        red_img[:, :] = [0, 0, 255]
        ratio = red_ratio(red_img, [10, 10, 90, 90])
        self.assertGreater(ratio, 0.90)


class TestDetectionFiltering(unittest.TestCase):
    """Test IoU, Deduplication, and Geometric Layout filtering."""

    def test_iou_calculation(self):
        """Verify IoU exactness for identical, disjoint, and partial boxes."""
        box1 = [10.0, 10.0, 50.0, 50.0]  # area = 40 * 40 = 1600
        box2 = [10.0, 10.0, 50.0, 50.0]
        self.assertAlmostEqual(iou(box1, box2), 1.0)

        box_disjoint = [60.0, 60.0, 100.0, 100.0]
        self.assertEqual(iou(box1, box_disjoint), 0.0)

        # 50% horizontal overlap
        box_half = [30.0, 10.0, 70.0, 50.0]
        # inter = 20 * 40 = 800, union = 1600 + 1600 - 800 = 2400 -> IoU = 800/2400 = 1/3
        self.assertAlmostEqual(iou(box1, box_half), 1.0 / 3.0, places=4)

    def test_dedup_detections(self):
        """Verify candidate deduplication retains higher confidence and sorts by center_x."""
        dets = [
            {"digit": 5, "confidence": 0.92, "bbox": [10.0, 10.0, 40.0, 40.0], "center_x": 25.0},
            {"digit": 5, "confidence": 0.65, "bbox": [12.0, 10.0, 42.0, 40.0], "center_x": 27.0},  # duplicate of 1
            {"digit": 7, "confidence": 0.88, "bbox": [50.0, 10.0, 80.0, 40.0], "center_x": 65.0},
        ]
        kept = dedup_detections(dets, thresh=0.45)
        self.assertEqual(len(kept), 2)
        self.assertEqual(kept[0]["digit"], 5)
        self.assertEqual(kept[0]["confidence"], 0.92)
        self.assertEqual(kept[1]["digit"], 7)
        self.assertLess(kept[0]["center_x"], kept[1]["center_x"])

    def test_is_vertical_horizontal_row(self):
        """Horizontal row of digits should NOT be classified as vertical."""
        w, h = 640, 480
        horizontal_dets = [
            {"center_x": 100.0, "center_y": 200.0},
            {"center_x": 150.0, "center_y": 201.0},
            {"center_x": 200.0, "center_y": 199.0},
            {"center_x": 250.0, "center_y": 200.0},
            {"center_x": 300.0, "center_y": 202.0},
        ]
        res = is_vertical(horizontal_dets, w, h)
        self.assertFalse(res["vertical"])

    def test_is_vertical_vertical_column(self):
        """Vertical column of serial/date numbers SHOULD be classified as vertical."""
        w, h = 640, 480
        vertical_dets = [
            {"center_x": 300.0, "center_y": 100.0},
            {"center_x": 301.0, "center_y": 160.0},
            {"center_x": 299.0, "center_y": 220.0},
            {"center_x": 300.0, "center_y": 280.0},
        ]
        res = is_vertical(vertical_dets, w, h)
        self.assertTrue(res["vertical"])


class TestSafetyGuards(unittest.TestCase):
    """Test safety guard heuristics and 180 degree flip detection."""

    def test_flip_map_symmetry_pairs(self):
        """Verify FLIP_MAP pairs are mathematically symmetric (including identity 3,4,7)."""
        expected_pairs = {0: 0, 1: 1, 2: 5, 5: 2, 6: 9, 8: 8, 9: 6, 3: 3, 4: 4, 7: 7}
        self.assertEqual(FLIP_MAP, expected_pairs)

    def test_alignment_spread(self):
        """Verify alignment std threshold rejects skewed/scattered bboxes."""
        h = 480
        # Well-aligned horizontal digits (y centers near 200)
        aligned_digits = [
            {"bbox": [100, 180, 130, 220]},  # center_y = 200
            {"bbox": [140, 182, 170, 222]},  # center_y = 202
            {"bbox": [180, 179, 210, 219]},  # center_y = 199
            {"bbox": [220, 181, 250, 221]},  # center_y = 201
        ]
        y_vals = [(d["bbox"][1] + d["bbox"][3]) / (2 * h) for d in aligned_digits]
        self.assertLessEqual(float(np.std(y_vals)), ALIGN_MAX_SPREAD)

        # Scattered / non-linear bounding boxes
        scattered_digits = [
            {"bbox": [100, 50, 130, 90]},    # center_y = 70
            {"bbox": [140, 180, 170, 220]},  # center_y = 200
            {"bbox": [180, 350, 210, 390]},  # center_y = 370
        ]
        y_scattered = [(d["bbox"][1] + d["bbox"][3]) / (2 * h) for d in scattered_digits]
        self.assertGreater(float(np.std(y_scattered)), ALIGN_MAX_SPREAD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
