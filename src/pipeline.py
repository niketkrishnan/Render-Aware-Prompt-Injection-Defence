"""
End-to-end pipeline: run a PDF through all four layers and return a unified
risk score.

Usage:
    python -m src.pipeline --file path/to/document.pdf
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from src import layer1_virustotal as vt
from src import layer2_render_aware as render_aware
from src.fusion_xgboost import fuse, load_fusion_model
from src.layer3_semantic import SemanticClassifier

load_dotenv()


def analyze_document(file_path: str, semantic_text: str | None = None) -> dict:
    """
    Run the full 4-layer pipeline on a single PDF.

    `semantic_text` lets callers pass pre-extracted text for the semantic
    layer directly; otherwise the render-aware layer's extracted text is used.
    """
    # Layer 1 — file reputation
    vt_result = vt.analyze_document(file_path=file_path)
    vt_score = vt_result.risk_score if hasattr(vt_result, "risk_score") else 0.0

    # Layer 2 — render-aware structural analysis
    render_features = render_aware.extract_render_features(file_path)

    # Layer 3 — semantic classification
    classifier = SemanticClassifier()
    text_to_score = semantic_text or ""
    semantic_score = classifier.score(text_to_score) if text_to_score else 0.0

    # Fusion
    model = load_fusion_model()
    features = {
        "semantic_score": semantic_score,
        "min_font_size": render_features.min_font_size,
        "avg_font_size": render_features.avg_font_size,
        "has_tiny_font": render_features.has_tiny_font,
        "has_white_text": render_features.has_white_text,
        "hidden_score": render_features.hidden_score,
        "vt_score": vt_score,
    }
    result = fuse(model, features)
    result["features"] = features
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the render-aware injection-defence pipeline on a PDF.")
    parser.add_argument("--file", required=True, help="Path to the PDF to analyze.")
    parser.add_argument("--text", default=None, help="Optional pre-extracted text for the semantic layer.")
    args = parser.parse_args()

    result = analyze_document(args.file, semantic_text=args.text)
    print(f"Verdict:    {result['label']}")
    print(f"Risk score: {result['risk_score']}")
    print("Features:")
    for k, v in result["features"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
