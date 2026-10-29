# Beyond Text: Render-Aware, Semantically-Fused Defence Against Indirect Prompt Injection

**A 4-layer hybrid detection framework for catching prompt-injection attacks hidden in PDFs before they reach an LLM/RAG pipeline — including attacks invisible to human reviewers but fully machine-extractable (zero-point fonts, white-on-white text, off-page placement).**

**Published at IEEE ICIMIA 2026.** The paper is © IEEE; see the IEEE Xplore page for the official version (link/DOI to be added).

[![CI](https://github.com/niketkrishnan/render-aware-prompt-injection-defence/actions/workflows/ci.yml/badge.svg)](https://github.com/niketkrishnan/render-aware-prompt-injection-defence/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23755370.svg)](https://doi.org/10.5281/zenodo.23755370)

---

## Results

| Method | F1 (Macro) | ROC-AUC |
|---|---|---|
| Keyword Rules (baseline) | 0.60 | — |
| Semantic-only (DistilBERT) | 0.83 | 0.938 |
| Render-aware-only | 0.39 | — |
| VirusTotal-only | 0.34 | — |
| **XGBoost Fusion (ours)** | **0.877** | **0.939** |
| — 10-fold CV | 0.885 ± 0.011 | 0.946 ± 0.008 |

- Multilingual (29 languages, 514 samples): **F1 = 0.914**
- End-to-end latency: **837 ms** (target < 2,000 ms)
- Adversarial robustness: single-technique obfuscation evades the model; **2+ simultaneous render techniques are caught 100%** of the time.

Full breakdowns, SHAP analysis, and per-modality error analysis are in the paper.

## The problem

RAG pipelines ingest untrusted documents. Text extractors (and the LLMs reading their output) see whatever text is embedded in a PDF — including text a human reviewer would never see: zero-point fonts, white-on-white text, off-page coordinates. Existing defences are blind to one threat class or the other:

- File-reputation scanners (VirusTotal) catch known malware, not semantic manipulation.
- Text/semantic classifiers see extracted text but have no visibility into *how* that text was rendered.

This project closes that gap with a **render-aware structural detector** — the first component (to our knowledge) that applies font-size/colour/bounding-box metadata analysis specifically to prompt-injection concealment.

## Architecture

```
                         INPUT DOCUMENT (PDF/DOCX)
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                            ▼                            ▼
   Layer 1                      Layer 2                      Layer 3
File Reputation           Render-Aware Detector         Semantic Classifier
 (VirusTotal API)          (PyMuPDF metadata)             (DistilBERT)
        │                            │                            │
        └───────────────────────────┼───────────────────────────┘
                                    ▼
                        Fusion Classifier (XGBoost)
                          Unified risk score [0,1]
                                    │
                         REJECT (log/alert)  or  ALLOW → LLM
```

- **Layer 1 — VirusTotal**: SHA-256 hash reputation lookup across 70+ AV engines.
- **Layer 2 — Render-aware detector**: extracts per-span font size, colour, and bounding-box metadata via PyMuPDF; flags tiny fonts, white/near-white text, low-contrast text, and off-page placement.
- **Layer 3 — Semantic classifier**: DistilBERT fine-tuned on 100k HackAPrompt samples.
- **Fusion**: XGBoost combines all 9 features into a single calibrated risk score, with SHAP for explainability.

## Key engineering decisions

- **XGBoost fusion over a weighted average.** Each layer's signal is only meaningful within its own threat class (semantic score for text injection, hidden_score for formatting concealment, vt_score for known malware) — a linear blend would dilute a strong single-layer signal with two near-zero ones. A tree-based fusion model lets each layer fire independently without being averaged down; SHAP confirms this modality-specific complementarity (Table V in the paper).
- **DistilBERT over full BERT for Layer 3.** The 2,000 ms end-to-end latency target is dominated by the VirusTotal API round-trip (~768 ms), leaving a tight budget for local inference. DistilBERT gives ~97% of BERT's accuracy at roughly half the parameters, which keeps Layer 3 under 40 ms per document instead of contending for the remaining latency budget.
- **Raw content-stream parsing instead of `get_text()` for off-page detection.** PyMuPDF's `get_text()` silently clips spans positioned outside the visible viewport — exactly the injection technique it needed to catch. Off-page detection required dropping to raw PDF content-stream coordinate parsing (see `notebooks/dev_offpage_detection_exploration.ipynb` for the debugging trail).
- **Fixed colour-threshold indicators over a continuous luminance metric — a known limitation.** The shipped detector flags specific near-white/low-contrast hex values rather than computing perceptual luminance (`L = 0.299R + 0.587G + 0.114B`), so a novel off-list colour could evade it. This is called out explicitly in the paper as a direction for follow-up work rather than silently left as a gap.

## Repo layout

```
├── src/                  # production-style modules extracted from the research notebooks
│   ├── layer1_virustotal.py
│   ├── layer2_render_aware.py
│   ├── layer3_semantic.py
│   ├── fusion_xgboost.py
│   └── pipeline.py       # end-to-end analyze_document()
├── notebooks/            # original research notebooks (exploratory, kept for reproducibility)
├── data/                 # dataset construction notes (raw data not included — see below)
├── results/              # metrics, SHAP plots, latency charts from the paper
├── tests/                # unit tests for the render-aware detector
└── requirements.txt
```

## Quickstart

```bash
git clone https://github.com/<your-username>/render-aware-prompt-injection-defence.git
cd render-aware-prompt-injection-defence
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in your own VT_API_KEY
python -m src.pipeline --file path/to/document.pdf
```

## Dataset

Built from three sources (11,050 samples total): [HackAPrompt](https://arxiv.org/abs/2311.16119) (10,000 text injections), 1,000 synthetically obfuscated PDFs across 6 render-obfuscation techniques, and ~50 VirusTotal-verified malware hashes. Raw data is not redistributed here (HackAPrompt license, malware hashes); `data/README.md` documents exactly how to reconstruct it.

## Authors

Abu Nasar, Niket Krishnan, Devi Rajeev, Vysakh Kani Kolil — Center for Cybersecurity Systems and Networks, Amrita Vishwa Vidyapeetham, Amritapuri, India.

## License & paper status

The paper is published at IEEE ICIMIA 2026. Copyright in the paper belongs to IEEE and it is not redistributed here. A formal citation (DOI/BibTeX) will be added once the paper is indexed on IEEE Xplore.

Code archive: https://doi.org/10.5281/zenodo.23755370. The paper's own DOI/BibTeX will be added once it is indexed on IEEE Xplore.
