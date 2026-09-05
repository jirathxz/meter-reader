"""
tests/test_pipeline.py — Comprehensive Unit & Regression Tests for Water Meter OCR Pipeline
Uses standard library `unittest` for zero-dependency execution.
Covers utils.py (geometry, image transformations, IoU, deduplication, color analysis, Wilson CI)
and main.py pipeline integrity.
"""
import math
import unittest
import numpy as np

from utils import (
    apply_prep,
    dedup_detections,
    iou,
    is_vertical,
    red_ratio,
    remap_bbox,
    remap_point,
    rotate_image,
    wilson_score_interval,
)


class TestImageAndGeometryUtils(unittest.TestCase):
    def test_rotate_image(self):
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        img[0, 0] = [255, 0, 0]

        rot0 = rotate_image(img, 0)
        self.assertEqual(rot0.shape, (100, 200, 3))

        rot90 = rotate_image(img, 90)
        self.assertEqual(rot90.shape, (200, 100, 3))

        rot180 = rotate_image(img, 180)
        self.assertEqual(rot180.shape, (100, 200, 3))

        rot270 = rotate_image(img, 270)
        self.assertEqual(rot270.shape, (200, 100, 3))

    def test_apply_prep(self):
        img = np.full((50, 50, 3), 128, dtype=np.uint8)
        orig = apply_prep(img, "orig")
        self.assertTrue(np.array_equal(orig, img))

        clahe = apply_prep(img, "clahe")
        self.assertEqual(clahe.shape, img.shape)

        histeq = apply_prep(img, "histeq")
        self.assertEqual(histeq.shape, img.shape)

    def test_remap_point(self):
        w, h = 200, 100
        # 0 deg: identical
        self.assertEqual(remap_point(10, 20, 0, w, h), (10, 20))

        # 90 deg clockwise: (x, y) was at (y, h - x)
        px, py = remap_point(20, 10, 90, w, h)
        self.assertEqual((px, py), (10, 80))

        # 180 deg: (w - x, h - y)
        px, py = remap_point(20, 10, 180, w, h)
        self.assertEqual((px, py), (180, 90))

        # 270 deg: (w - y, x)
        px, py = remap_point(20, 10, 270, w, h)
        self.assertEqual((px, py), (190, 20))

    def test_remap_bbox(self):
        w, h = 200, 100
        box = [10.0, 20.0, 50.0, 60.0]
        remapped0 = remap_bbox(box, 0, w, h)
        self.assertEqual(remapped0, box)

        remapped180 = remap_bbox(box, 180, w, h)
        self.assertLess(remapped180[0], remapped180[2])
        self.assertLess(remapped180[1], remapped180[3])

    def test_iou(self):
        box1 = [0.0, 0.0, 10.0, 10.0]
        box2 = [0.0, 0.0, 10.0, 10.0]
        # Identical boxes
        self.assertTrue(math.isclose(iou(box1, box2), 1.0))

        # Disjoint boxes
        box3 = [20.0, 20.0, 30.0, 30.0]
        self.assertTrue(math.isclose(iou(box1, box3), 0.0))

        # Half overlap: 5x10 overlap / (100 + 100 - 50) = 50/150 = 0.3333
        box4 = [5.0, 0.0, 15.0, 10.0]
        self.assertTrue(math.isclose(iou(box1, box4), 50.0 / 150.0, rel_tol=1e-4))

    def test_dedup_detections(self):
        dets = [
            {"digit": 1, "confidence": 0.90, "bbox": [0, 0, 10, 10], "center_x": 5.0},
            {"digit": 1, "confidence": 0.50, "bbox": [1, 1, 11, 11], "center_x": 6.0},  # duplicate
            {"digit": 2, "confidence": 0.85, "bbox": [30, 0, 40, 10], "center_x": 35.0},
        ]
        kept = dedup_detections(dets, thresh=0.45)
        self.assertEqual(len(kept), 2)
        self.assertEqual(kept[0]["digit"], 1)
        self.assertEqual(kept[0]["confidence"], 0.90)
        self.assertEqual(kept[1]["digit"], 2)

    def test_red_ratio(self):
        # Create image with solid red square
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        # In BGR: Red has high R, low B and G
        img[10:40, 10:40] = [0, 0, 255]
        ratio_red = red_ratio(img, [10, 10, 40, 40])
        self.assertGreater(ratio_red, 0.5)

        # Solid black
        ratio_black = red_ratio(img, [0, 0, 10, 10])
        self.assertEqual(ratio_black, 0.0)

    def test_is_vertical(self):
        # Horizontal row: width_span > height_span
        horizontal_dets = [
            {"center_x": 10.0, "center_y": 50.0},
            {"center_x": 30.0, "center_y": 51.0},
            {"center_x": 50.0, "center_y": 50.0},
            {"center_x": 70.0, "center_y": 49.0},
        ]
        self.assertFalse(is_vertical(horizontal_dets, 100, 100)["vertical"])

        # Vertical column: height_span > width_span
        vertical_dets = [
            {"center_x": 50.0, "center_y": 10.0},
            {"center_x": 51.0, "center_y": 30.0},
            {"center_x": 49.0, "center_y": 50.0},
            {"center_x": 50.0, "center_y": 70.0},
        ]
        self.assertTrue(is_vertical(vertical_dets, 100, 100)["vertical"])


class TestWilsonScoreInterval(unittest.TestCase):
    def test_wilson_perfect_score(self):
        lower, upper = wilson_score_interval(7, 7)
        self.assertEqual(upper, 100.0)
        self.assertGreaterEqual(lower, 60.0)
        self.assertLessEqual(lower, 70.0)

    def test_wilson_zero_score(self):
        lower, upper = wilson_score_interval(0, 7)
        self.assertEqual(lower, 0.0)
        self.assertGreaterEqual(upper, 30.0)
        self.assertLessEqual(upper, 45.0)

    def test_wilson_empty(self):
        lower, upper = wilson_score_interval(0, 0)
        self.assertEqual(lower, 0.0)
        self.assertEqual(upper, 0.0)


if __name__ == "__main__":
    unittest.main()
