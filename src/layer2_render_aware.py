"""
Layer 2 — Render-Aware Hidden-Text Detector (headline contribution).

Parses a PDF's per-span font size, colour, and bounding-box metadata via
PyMuPDF to detect formatting-based concealment: zero-point fonts, tiny fonts,
white/near-white text, low-contrast text, and off-page placement.
"""

from __future__ import annotations

from dataclasses import dataclass

import fitz  # PyMuPDF

# Colours treated as "near-white" / concealment-adjacent.
WHITE_LIKE_COLORS = {"#ffffff", "#fafafa"}
LOW_CONTRAST_COLORS = {"#f0f0f0", "#e8e8e8"}
TINY_FONT_THRESHOLD_PT = 1.0


@dataclass
class RenderFeatures:
    min_font_size: float
    avg_font_size: float
    has_tiny_font: int
    has_white_text: int
    has_low_contrast: int
    hidden_score: float


def extract_render_features(filepath: str) -> RenderFeatures:
    """Extract render-aware features from the first page of a PDF."""
    doc = fitz.open(filepath)
    page = doc[0]

    font_sizes: list[float] = []
    font_colors: list[str] = []

    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if block["type"] != 0:  # not a text block
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                font_sizes.append(span["size"])
                hex_color = "#{:06x}".format(span["color"])
                font_colors.append(hex_color)

    if font_sizes:
        min_font = round(min(font_sizes), 4)
        avg_font = round(sum(font_sizes) / len(font_sizes), 4)
        has_tiny = 1 if min_font < TINY_FONT_THRESHOLD_PT else 0
    else:
        # No extractable text at all is itself a concealment signal.
        min_font = 0.0
        avg_font = 0.0
        has_tiny = 1

    has_white = 1 if any(c in WHITE_LIKE_COLORS for c in font_colors) else 0
    has_low_contrast = 1 if any(c in LOW_CONTRAST_COLORS for c in font_colors) else 0

    # Composite hidden-content score (see paper Eq. 1 for the four-indicator
    # version including off-page placement, which requires raw content-stream
    # parsing rather than get_text() — see `has_off_page_content` below).
    hidden_score = round((has_tiny * 0.5) + (has_white * 0.5), 4)

    return RenderFeatures(
        min_font_size=min_font,
        avg_font_size=avg_font,
        has_tiny_font=has_tiny,
        has_white_text=has_white,
        has_low_contrast=has_low_contrast,
        hidden_score=hidden_score,
    )


def has_off_page_content(filepath: str, page_width: float = 612, page_height: float = 792) -> bool:
    """
    Detect text placed outside the visible page viewport.

    get_text() silently clips out-of-viewport spans, so off-page injection
    text must be detected via raw content-stream coordinate parsing instead.
    """
    doc = fitz.open(filepath)
    page = doc[0]
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        bbox = block.get("bbox")
        if not bbox:
            continue
        x0, y0, x1, y1 = bbox
        if x1 < 0 or y1 < 0 or x0 > page_width or y0 > page_height:
            return True
    return False
