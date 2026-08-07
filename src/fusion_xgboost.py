"""
Fusion Layer — XGBoost combining Layer 1/2/3 signals into one risk score.

Trained on the 9-feature vector:
[semantic_score, min_font_size, avg_font_size, has_tiny_font,
 has_white_text, has_low_contrast, has_off_page, hidden_score, vt_score]

(the shipped model uses the 7-feature subset actually used in the paper's
released experiments — see notebooks/ for the exact training run).
"""

from __future__ import annotations

from xgboost import XGBClassifier

FEATURE_ORDER = [
    "semantic_score",
    "min_font_size",
    "avg_font_size",
    "has_tiny_font",
    "has_white_text",
    "hidden_score",
    "vt_score",
]

DEFAULT_MODEL_PATH = "xgboost_fusion_model.json"


def load_fusion_model(model_path: str = DEFAULT_MODEL_PATH) -> XGBClassifier:
    model = XGBClassifier()
    model.load_model(model_path)
    return model


def build_feature_vector(features: dict) -> list:
    """Order a feature dict into the vector the fusion model expects."""
    return [features[name] for name in FEATURE_ORDER]


def fuse(model: XGBClassifier, features: dict) -> dict:
    """
    Run the fusion classifier on a single document's feature dict and
    return a unified risk score plus the binary verdict.
    """
    vector = [build_feature_vector(features)]
    risk_score = float(model.predict_proba(vector)[0][1])
    label = int(model.predict(vector)[0])
    return {
        "risk_score": round(risk_score, 4),
        "label": "malicious" if label == 1 else "benign",
    }
