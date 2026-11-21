"""Detect and extract individual receipts from scanned PDF pages."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image


@dataclass
class ReceiptCrop:
    index: int
    page: int
    image_bgr: np.ndarray
    bbox: tuple[int, int, int, int]  # x, y, w, h


def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> list[np.ndarray]:
    """Render each PDF page to a BGR OpenCV image."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    images: list[np.ndarray] = []
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        images.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    doc.close()
    return images


def _ink_mask(gray: np.ndarray) -> np.ndarray:
    """Binary mask of dark ink / printed content on the page."""
    # Adaptive handles uneven scanner lighting; fixed threshold catches bold print.
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    adaptive = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 12
    )
    _, fixed = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY_INV)
    return cv2.bitwise_or(adaptive, fixed)


def _gap_ranges(projection: np.ndarray, min_gap: int, content_ratio: float = 0.04) -> list[tuple[int, int]]:
    smooth = np.convolve(projection.astype(float), np.ones(7) / 7.0, mode="same")
    maxv = float(smooth.max()) if len(smooth) else 0.0
    if maxv <= 0:
        return []
    is_gap = smooth < max(1.0, maxv * content_ratio)
    ranges: list[tuple[int, int]] = []
    i = 0
    n = len(smooth)
    while i < n:
        if is_gap[i]:
            j = i
            while j < n and is_gap[j]:
                j += 1
            if j - i >= min_gap:
                ranges.append((i, j))
            i = j
        else:
            i += 1
    return ranges


def _merge_nearby_gaps(ranges: list[tuple[int, int]], max_bridge: int = 25) -> list[tuple[int, int]]:
    if not ranges:
        return []
    merged = [[ranges[0][0], ranges[0][1]]]
    for a, b in ranges[1:]:
        if a - merged[-1][1] <= max_bridge:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def _interior_gutters(
    ranges: list[tuple[int, int]], length: int, edge_margin_ratio: float = 0.03
) -> list[tuple[int, int]]:
    margin = int(length * edge_margin_ratio)
    return [(a, b) for a, b in ranges if a > margin and b < length - margin]


def _content_bbox(mask: np.ndarray, pad: int = 8) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    h, w = mask.shape
    x0 = max(0, int(xs.min()) - pad)
    y0 = max(0, int(ys.min()) - pad)
    x1 = min(w - 1, int(xs.max()) + pad)
    y1 = min(h - 1, int(ys.max()) + pad)
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1


def _split_mask_along_axis(mask: np.ndarray, axis: str) -> list[np.ndarray]:
    """Split an ink mask into parts separated by white gutters along v or h."""
    height, width = mask.shape
    if axis == "v":
        projection = (mask > 0).sum(axis=0)
        length = width
        min_gap = max(8, int(width * 0.025))
    else:
        projection = (mask > 0).sum(axis=1)
        length = height
        min_gap = max(8, int(height * 0.02))

    gaps = _interior_gutters(_merge_nearby_gaps(_gap_ranges(projection, min_gap)), length)
    if not gaps:
        return [mask]

    cuts = [0] + [(a + b) // 2 for a, b in gaps] + [length]
    parts: list[np.ndarray] = []
    for a, b in zip(cuts, cuts[1:]):
        if b - a < 15:
            continue
        part = np.zeros_like(mask)
        if axis == "v":
            part[:, a:b] = mask[:, a:b]
        else:
            part[a:b, :] = mask[a:b, :]
        if (part > 0).sum() < 80:
            continue
        parts.append(part)
    return parts or [mask]


def _boxes_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


def _dedupe_boxes(boxes: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    boxes = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
    kept: list[tuple[int, int, int, int]] = []
    for box in boxes:
        if any(_boxes_iou(box, k) > 0.55 for k in kept):
            continue
        kept.append(box)
    return kept


def detect_receipts(image_bgr: np.ndarray, min_area_ratio: float = 0.015) -> list[tuple[int, int, int, int]]:
    """
    Return axis-aligned bounding boxes (x, y, w, h) for each receipt-like region.

    Strategy: ink projection profiling — split the page into columns by vertical
    white gutters, then each column into rows by horizontal gutters. This matches
    how receipts are usually laid out on a scanner bed.
    """
    h, w = image_bgr.shape[:2]
    page_area = h * w
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    ink = _ink_mask(gray)

    boxes: list[tuple[int, int, int, int]] = []

    # Column-first, then row; one extra vertical pass catches side-by-side slips in a band.
    for column in _split_mask_along_axis(ink, "v"):
        for row in _split_mask_along_axis(column, "h"):
            nested = _split_mask_along_axis(row, "v")
            for part in nested:
                bbox = _content_bbox(part, pad=max(6, int(min(h, w) * 0.01)))
                if bbox is None:
                    continue
                _, _, bw, bh = bbox
                if bw * bh < page_area * min_area_ratio:
                    continue
                if bw < 40 or bh < 40:
                    continue
                boxes.append(bbox)

    boxes = _dedupe_boxes(boxes)
    # Reading order: top-to-bottom, then left-to-right
    boxes.sort(key=lambda b: (b[1] // max(1, h // 25), b[0]))
    return boxes


def extract_receipts_from_images(images: list[np.ndarray]) -> list[ReceiptCrop]:
    crops: list[ReceiptCrop] = []
    global_idx = 1
    for page_idx, img in enumerate(images, start=1):
        boxes = detect_receipts(img)
        if not boxes:
            # Fallback: treat the whole page as a single receipt
            height, width = img.shape[:2]
            boxes = [(0, 0, width, height)]
        for x, y, bw, bh in boxes:
            crop = img[y : y + bh, x : x + bw].copy()
            crops.append(
                ReceiptCrop(index=global_idx, page=page_idx, image_bgr=crop, bbox=(x, y, bw, bh))
            )
            global_idx += 1
    return crops


def image_to_pdf_bytes(image_bgr: np.ndarray) -> bytes:
    """Wrap a single BGR image as a one-page PDF."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buf = io.BytesIO()
    pil.save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()


def build_zip(crops: list[ReceiptCrop]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for crop in crops:
            name = f"recibo_{crop.index:02d}_pagina_{crop.page}.pdf"
            zf.writestr(name, image_to_pdf_bytes(crop.image_bgr))
    return buf.getvalue()


def process_pdf(pdf_bytes: bytes, dpi: int = 200) -> tuple[bytes, int]:
    """
    Full pipeline: PDF in → ZIP of per-receipt PDFs out.
    Returns (zip_bytes, receipt_count).
    """
    images = pdf_to_images(pdf_bytes, dpi=dpi)
    if not images:
        raise ValueError("O PDF não contém páginas.")
    crops = extract_receipts_from_images(images)
    return build_zip(crops), len(crops)


def process_pdf_file(path: str | Path, dpi: int = 200) -> tuple[bytes, int]:
    return process_pdf(Path(path).read_bytes(), dpi=dpi)
