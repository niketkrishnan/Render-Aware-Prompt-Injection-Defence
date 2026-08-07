# Beyond Text: Render-Aware, Semantically-Fused Defence Against Indirect Prompt Injection

**A 4-layer hybrid detection framework for catching prompt-injection attacks hidden in PDFs before they reach an LLM/RAG pipeline — including attacks invisible to human reviewers but fully machine-extractable (zero-point fonts, white-on-white text, off-page placement).**

📄 **Accepted at IEEE ICIMIA 2026** — camera-ready included in [`paper/`](./paper) for reference. Presentation and formal IEEE Xplore publication still pending.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

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
├── paper/                # camera-ready PDF
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

This paper is accepted and pending IEEE publication (copyright transfer to IEEE applies to the manuscript once published — the camera-ready PDF in [`paper/`](./paper) is shared here for reference ahead of that, not for redistribution). A formal citation (DOI/BibTeX) will be added once the paper is indexed by IEEE Xplore.

The **code** in this repository is separate from the paper's copyright and is licensed under MIT — see [LICENSE](./LICENSE).
