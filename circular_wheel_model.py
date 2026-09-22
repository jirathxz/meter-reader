# -*- coding: utf-8 -*-
"""
circular_wheel_model.py
Module implementing Method 1: Circular Periodic Regression for Mechanical Water Meter Wheels.

Mathematical Formulation:
Each meter wheel is a 3D rotating cylinder divided into 10 decimal arc segments of 36° each.
Angle theta in [0°, 360°) corresponds to continuous decimal reading:
    R_cont = theta / 36.0 in [0.0, 10.0)

When a wheel is between two digits (e.g. 4 and 5), circular regression estimates the exact
rotational phase alpha in [0, 1] from vertical centroid offsets and confidence distributions:
    theta = (D_base * 36° + alpha * 36°) mod 360°
"""

import math
from typing import Any
import numpy as np

DEG_PER_DIGIT = 36.0  # 360° / 10 digits


def compute_wheel_angle(
    top_box: dict[str, Any] | None,
    bottom_box: dict[str, Any] | None,
    row_y: float,
    med_h: float
) -> dict[str, Any]:
    """
    Computes continuous circular angle theta and transition dynamics for a single wheel slot.
    """
    # Case 1: Both adjacent digits are detected (half-turned collision)
    if top_box is not None and bottom_box is not None:
        d_top = top_box["digit"]
        d_bot = bottom_box["digit"]
        y_top = top_box["cy"]
        y_bot = bottom_box["cy"]
        c_top = top_box["conf"]
        c_bot = bottom_box["conf"]

        total_dy = max(1.0, y_bot - y_top)
        # Fractional vertical displacement from top box towards bottom box
        alpha_geom = max(0.0, min(1.0, (row_y - y_top) / total_dy))
        # Confidence-based displacement
        alpha_conf = c_bot / max(1e-5, (c_top + c_bot))
        # Fused phase (60% geometric position relative to row axis, 40% model probability)
        alpha = 0.60 * alpha_geom + 0.40 * alpha_conf

        # Determine wheel rotation direction
        # Standard upward roll: bottom digit is next digit (e.g. top=4, bottom=5)
        if (d_top + 1) % 10 == d_bot:
            base_digit = d_top
            angle_deg = (base_digit * DEG_PER_DIGIT + alpha * DEG_PER_DIGIT) % 360.0
            r_cont = angle_deg / DEG_PER_DIGIT
            transition_pair = (d_top, d_bot)
        # Downward roll: top digit is next digit (e.g. bottom=4, top=5)
        elif (d_bot + 1) % 10 == d_top:
            base_digit = d_bot
            angle_deg = (base_digit * DEG_PER_DIGIT + (1.0 - alpha) * DEG_PER_DIGIT) % 360.0
            r_cont = angle_deg / DEG_PER_DIGIT
            transition_pair = (d_bot, d_top)
        else:
            # Non-sequential digits detected: pick dominant confidence
            chosen = top_box if c_top >= c_bot else bottom_box
            base_digit = chosen["digit"]
            angle_deg = (base_digit * DEG_PER_DIGIT) % 360.0
            r_cont = float(base_digit)
            transition_pair = (base_digit, base_digit)

        phase = r_cont - math.floor(r_cont)
        in_trans = 0.15 <= phase <= 0.85
        primary_digit = int(round(r_cont)) % 10
        secondary_digit = int(math.floor(r_cont)) if primary_digit != int(math.floor(r_cont)) else (primary_digit + 1) % 10

        return {
            "primary_digit": primary_digit,
            "secondary_digit": secondary_digit,
            "continuous_val": round(r_cont, 2),
            "angle_deg": round(angle_deg, 1),
            "in_transition": in_trans,
            "transition_pair": transition_pair,
            "phase": round(phase, 2),
            "dominant_conf": max(c_top, c_bot),
            "is_dual_detection": True
        }

    # Case 2: Only single box detected in this wheel slot
    box = top_box if top_box is not None else bottom_box
    if box is None:
        return {
            "primary_digit": 0,
            "secondary_digit": 0,
            "continuous_val": 0.0,
            "angle_deg": 0.0,
            "in_transition": False,
            "transition_pair": (0, 0),
            "phase": 0.0,
            "dominant_conf": 0.0,
            "is_dual_detection": False
        }

    digit = box["digit"]
    conf = box["conf"]
    dy = box["cy"] - row_y
    rel_dy = dy / max(1.0, med_h)

    # If box is vertically displaced from median line by > 0.20h, wheel has begun rolling
    if abs(rel_dy) > 0.20:
        # Box shifted upward (dy < 0): rolling towards next digit
        if rel_dy < -0.20:
            alpha = min(0.48, abs(rel_dy) * 0.6)
            angle_deg = (digit * DEG_PER_DIGIT + alpha * DEG_PER_DIGIT) % 360.0
            next_digit = (digit + 1) % 10
            trans_pair = (digit, next_digit)
        else:
            # Box shifted downward (dy > 0): entering from previous digit
            alpha = min(0.48, rel_dy * 0.6)
            angle_deg = (digit * DEG_PER_DIGIT - alpha * DEG_PER_DIGIT) % 360.0
            prev_digit = (digit - 1) % 10
            trans_pair = (prev_digit, digit)
        r_cont = angle_deg / DEG_PER_DIGIT
        in_trans = True
        phase = r_cont - math.floor(r_cont)
    else:
        angle_deg = (digit * DEG_PER_DIGIT) % 360.0
        r_cont = float(digit)
        in_trans = False
        trans_pair = (digit, digit)
        phase = 0.0

    primary_digit = int(round(r_cont)) % 10
    secondary_digit = trans_pair[1] if primary_digit == trans_pair[0] else trans_pair[0]

    return {
        "primary_digit": primary_digit,
        "secondary_digit": secondary_digit,
        "continuous_val": round(r_cont, 2),
        "angle_deg": round(angle_deg, 1),
        "in_transition": in_trans,
        "transition_pair": trans_pair,
        "phase": round(phase, 2),
        "dominant_conf": conf,
        "is_dual_detection": False
    }


def resolve_odometer_circular(
    boxes: list[dict[str, Any]],
    x_overlap_thresh: float = 0.60
) -> dict[str, Any]:
    """
    Applies Circular Periodic Wheel Regression across all detection columns:
    1. Clusters candidate boxes into discrete physical wheel columns.
    2. Estimates row axis y_row(x) = m*x + c.
    3. Solves continuous circular angle theta for each wheel.
    4. Returns exact string reading, continuous reading float, and transition diagnostics.
    """
    if not boxes:
        return {
            "reading_primary": "",
            "reading_secondary": "",
            "continuous_reading": 0.0,
            "wheels": [],
            "mean_confidence": 0.0,
            "has_transition": False
        }

    # Group boxes into column slots by horizontal overlap
    sorted_boxes = sorted(boxes, key=lambda b: b["cx"])
    cols: list[list[dict[str, Any]]] = []

    for b in sorted_boxes:
        placed = False
        for col in cols:
            # Check overlap with column representative
            rep = col[0]
            inter_x = max(0.0, min(b["bbox"][2], rep["bbox"][2]) - max(b["bbox"][0], rep["bbox"][0]))
            min_w = min(b["w"], rep["w"])
            if min_w > 0 and (inter_x / min_w) >= x_overlap_thresh:
                col.append(b)
                placed = True
                break
        if not placed:
            cols.append([b])

    # Sort columns from left to right
    cols.sort(key=lambda col: np.mean([b["cx"] for b in col]))

    # Compute baseline median height and row axis
    all_hs = [b["h"] for b in boxes]
    med_h = float(np.median(all_hs)) if all_hs else 25.0
    all_cxs = [b["cx"] for b in boxes]
    all_cys = [b["cy"] for b in boxes]

    if len(boxes) >= 3:
        poly = np.polyfit(all_cxs, all_cys, 1)
        m, c_fit = float(poly[0]), float(poly[1])
        if abs(m) > 0.45:
            m, c_fit = 0.0, float(np.median(all_cys))
    else:
        m, c_fit = 0.0, float(np.median(all_cys))

    # Resolve each column with circular regression
    wheels_data = []
    primary_digits = []
    secondary_digits = []

    for col in cols:
        col_cx = float(np.mean([b["cx"] for b in col]))
        expected_row_y = m * col_cx + c_fit

        if len(col) == 1:
            w_res = compute_wheel_angle(top_box=col[0], bottom_box=None, row_y=expected_row_y, med_h=med_h)
        else:
            # Sort vertically: top box has smaller cy
            col_sorted_y = sorted(col, key=lambda b: b["cy"])
            w_res = compute_wheel_angle(top_box=col_sorted_y[0], bottom_box=col_sorted_y[-1], row_y=expected_row_y, med_h=med_h)

        wheels_data.append(w_res)
        primary_digits.append(str(w_res["primary_digit"]))
        # For secondary reading: use secondary digit if in transition, else primary
        secondary_digits.append(str(w_res["secondary_digit"] if w_res["in_transition"] else w_res["primary_digit"]))

    read_primary = "".join(primary_digits)
    read_secondary = "".join(secondary_digits)
    mean_conf = float(np.mean([w["dominant_conf"] for w in wheels_data])) if wheels_data else 0.0
    has_trans = any(w["in_transition"] for w in wheels_data)

    # Construct high-precision continuous float reading
    # The last wheel's continuous_val provides fractional sub-digit precision
    if wheels_data:
        integer_prefix = "".join(primary_digits[:-1])
        last_wheel_val = wheels_data[-1]["continuous_val"]
        cont_reading_str = f"{integer_prefix}{last_wheel_val:04.2f}"
        try:
            cont_val = float(cont_reading_str)
        except ValueError:
            cont_val = float(read_primary) if read_primary else 0.0
    else:
        cont_val = 0.0

    return {
        "reading_primary": read_primary,
        "reading_secondary": read_secondary,
        "continuous_reading": cont_val,
        "wheels": wheels_data,
        "mean_confidence": round(mean_conf, 4),
        "has_transition": has_trans
    }
