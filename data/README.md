# Dataset

The paper's 11,050-sample hybrid benchmark is built from three sources. Raw data
is **not redistributed in this repo** (HackAPrompt's own license terms, and
malware hashes should not be casually re-shared) — this file documents exactly
how to reconstruct each subset.

## 1. HackAPrompt text injections (10,000 samples)

- Source: [HackAPrompt](https://arxiv.org/abs/2311.16119) (Schulhoff et al., 2024), `hackaprompt.parquet`.
- Fine-tuning split: 100,000 rows (50k malicious / 50k benign), sampled with `random_state=42`.
- Evaluation split: a further 5,000 rows sampled from **rows 100,000+** specifically to avoid overlap with the fine-tuning data.

## 2. Synthetic obfuscated PDFs (1,000 samples)

Generated programmatically with `reportlab` — 500 malicious + 500 benign, saved
to `synthetic_pdfs/malicious/` and `synthetic_pdfs/benign/` (gitignored, not
committed). Regenerate via the notebook in `notebooks/` (PDF Dataset Builder
section) or by scripting `src/layer2_render_aware.py`'s companion generator.

Six obfuscation technique families used for the malicious set:

| Technique | Font size | Colour |
|---|---|---|
| White text | 12pt | `#FFFFFF` on `#FFFFFF` |
| Zero-point font | 0.1pt | `#000000` |
| Off-page placement | 12pt | `#000000`, coords outside viewport |
| Tiny white text | 0.5pt | `#FFFFFF` |
| Light grey | 8pt | `#F0F0F0` |
| Low contrast | — | `#E8E8E8` |

## 3. VirusTotal-verified malware (~50 samples)

Confirmed malicious file hashes drawn from public security research (VirusTotal
blog, ANY.RUN public reports, abuse.ch). Benign hashes are well-known
"empty/minimal file" hashes used as universally-safe negative controls
(e.g. the empty-file MD5, EICAR test string).

**Do not commit real malware or a VirusTotal API key to this repo.** Query
hashes live via `src/layer1_virustotal.py`, using your own `VT_API_KEY` from
`.env` (see `.env.example`).

## Rebuilding `fusion_dataset_final.csv`

The three subsets above are concatenated, shuffled (`random_state=42`), and
split 80/20 for train/test (`sklearn.model_selection.train_test_split`,
`stratify=y`). See the "VirusTotal Dataset Builder & Final Dataset Compilation"
notebook for the exact merge/fill logic.
