# SIH26099 — One Nation, One Material Code

**Problem:** SIH26099 (MOP&NG / CPCL, Software, Smart Automation) — CPSEs each
maintain their own material master, so the same physical material exists as
different codes/descriptions across ERPs. Build an AI platform that matches
equivalent materials across CPSEs, standardizes them, assigns a Common
National Material Code, and keeps full traceability to legacy codes.

**Status: pipeline + dashboard COMPLETE. Demo-ready.**

---

## Quick start

```bash
cd sih26099
source .venv/bin/activate              # Python 3.13 venv, all deps installed
python src/generate_dataset.py         # optional: regenerate data (seeded, deterministic)
python src/pipeline.py                 # CLI run: ~10s, writes outputs/
streamlit run src/app.py               # dashboard: http://localhost:8501
```

Or from scratch (any machine):

```bash
pip install -r requirements.txt
streamlit run src/app.py
```

The embedding model (all-MiniLM-L6-v2) is cached in `~/.cache/huggingface`
after the first run. If campus WiFi blocks HuggingFace, the pipeline
**auto-falls back to TF-IDF matching** and still runs — good backup story.

## Dashboard (`src/app.py`)

A clean, minimal, government-style web app (institutional blue / amber,
Swiss layout, no decoration). Four tabs:

1. **Overview** — KPI cards (records, codes issued, unified across CPSEs,
   auto-merge precision, price spread, pending review), category chart,
   price-spread chart (the demand-aggregation story), and a status-chip
   breakdown of the master.
2. **Review Queue** — the records the AI refuses to guess: AI's top
   candidates with similarity scores, suggested NMC, Approve / Reject
   buttons. Decisions persist in `outputs/review_decisions.csv`
   (officer name + timestamp — audit trail).
3. **Code Lookup** — type any legacy code (e.g. `MAT100050`) or NMC →
   result card + equivalent codes across every CPSE with UOM and price band.
4. **Audit Trail** — persistent officer decisions + machine actions
   (every cluster creation, logged).

**CSV upload (live ingest)** — sidebar uploader accepts any CSV with
`material_code, description, uom` columns (the ERP-export shape). Enter the
CPSE's name, click Ingest — the file is stored in `data/raw/`, the pipeline
re-harmonizes immediately, and all numbers/tables update. Verified
end-to-end with a 5th CPSE (GAIL, 15 records): 403 records from 5 CPSEs,
267 codes, all 15 records matched into shared clusters, still precision
1.000 / 0 trap violations.

## Results (current run, on 403 records / 5 CPSEs incl. live GAIL upload)

| Metric | Value | What it means |
|---|---|---|
| Precision (auto-merge) | **1.000** | every auto-merged pair is correct |
| Trap violations | **0** | near-miss materials (8.8 vs 10.9 bolt) NEVER wrongly merged |
| Cross-CPSE materials merged | 67/105 (63.8%) auto | rest recoverable via review |
| Potential recall after officer approval | **89.7%** | governance workflow recovers ambiguity |
| Review queue | 155 items | the human-in-the-loop story the PS demands |
| Demand-aggregation | 68 shared materials, ~12.6% avg price spread | the savings pitch |

Accuracy metrics are computed on the 388 ground-truth-labeled benchmark
records; the 15 uploaded GAIL records run in production mode (excluded from
scoring) — demonstrating real-world ingest.

### Verified invariants (automated checks, all PASS)

- Every one of the 403 input records maps to exactly one NMC (403/403
  mappings, no gaps, no duplicates)
- All NMCs globally unique; no code ever represents two different real materials
- `num_legacy_codes` in the master matches actual mapping rows for every NMC
- Runs are deterministic: re-running pipeline produces byte-identical outputs
  (except audit-log timestamps)
- **Offline mode verified**: with sentence-transformers unavailable (no
  HuggingFace access), the TF-IDF fallback delivers precision 1.000, 0 trap
  violations, cross-CPSE 65/105 — matching quality holds on this dataset.
  Records whose ERP text is genuinely indistinguishable (the differentiating
  attribute was never captured) are marked PROVISIONAL and routed to officer
  review instead of being guessed.

## How it works (the 3-stage story for judges)

**Stage 1 — Normalize + extract** (`src/normalize.py`): each CPSE's house style
(CPCL abbreviates everything, SAIL uses slashes, NTPC drops attributes,
IOCL writes full English) is normalized to canonical tokens, then ~35
engineering attributes (thread, grade, class, schedule, seal, material...)
are regex-extracted into structured form.

**Stage 2 — Match** (`src/match.py`): block by category (bolts never compare
to valves → scales to millions), rank candidates by sentence-embedding
similarity (survives typos/word order/missing text), then **veto on any
conflicting hard attribute** (grade 8.8 vs 10.9 = different material, full
stop). Records missing identity attributes (a bolt with no grade) are
**never auto-merged** — they go to the officer review queue. This is the
key insight: AI proposes, hard engineering facts dispose, humans approve.

**Stage 3 — Standardize + code** (`src/standardize.py`): deterministic
standardized description from merged attributes + stable National Material
Code (`NMC-FAST-BOLT-9BF0ABAC`, hash of canonical attributes) + full
legacy-code mapping + audit trail.

## Output files (`outputs/`)

| File | Demo use |
|---|---|
| `unified_master.csv` | the unified catalog — show NMC + standardized desc + which CPSEs share it + price spread |
| `code_mapping.csv` | traceability: every legacy CPSE code → its NMC (388/388 mapped) |
| `review_queue.csv` | governance: ambiguous records + top AI candidates + decision column (officer approves/rejects) |
| `rejected_pairs.csv` | THE DEMO MOMENT: near-misses caught by veto, e.g. butterfly vs ball valve at 0.71 similarity, rejected on 4 conflicting attributes |
| `audit_log.csv` | every cluster creation logged — audit trail requirement |

## Repo map

```
sih26099/
├── .streamlit/config.toml   # theme: institutional blue, minimal toolbar
├── requirements.txt
├── data/raw/*.csv          # 4 synthetic CPSE extracts, ground-truthed (true_material_id)
│                           #   + gail_materials.csv — the 5th-CPSE upload demo (unlabeled, production-style)
├── src/
│   ├── generate_dataset.py # seeded generator: 4 CPSE styles, duplicates, typos, traps (X-ids)
│   ├── normalize.py        # stage 1 + MIN_ATTRS safety table + synonym dictionaries
│   ├── match.py            # stage 2: blocking, embeddings, veto, review gate, clustering
│   ├── standardize.py      # stage 3: NMC generation, mapping, master
│   ├── pipeline.py         # orchestrator + evaluation metrics (library + CLI)
│   └── app.py              # Streamlit dashboard (4 tabs + CSV upload)
├── gui-test-screenshots/   # verified captures of all 4 tabs
└── outputs/*.csv           # all deliverables listed above
```

## Demo script (rehearse!)

- Open the dashboard → "these 5 CPSEs have never shared data before"
- Show two descriptions of the same bolt side by side → AI matched them
- Show a trap: 8.8 vs 10.9 bolt → AI refuses, cites conflicting grade
  (see `outputs/rejected_pairs.csv`)
- Approve one review item live (the human-governance moment) → shows up in
  Audit Trail, persists across runs
- Upload demo: drop in a CPSE CSV (or point at `data/raw/gail_materials.csv`)
  → numbers update live
- Reveal price spread across CPSEs for a shared material → negotiation ammo
- Close on "One Nation, One Material Code" with full legacy traceability

## Judge Q&A prep

- *"How does it scale?"* — blocking keeps comparisons within category; for
  millions of rows swap the dense similarity matrix for a FAISS ANN index
  (one line of concept, code stub mentioned in match.py).
- *"Why not just an LLM?"* — deterministic + auditable: same input always
  gives same NMC; embeddings rank but hard attributes decide; every change
  is logged. LLMs hallucinate codes; procurement can't audit that.
- *"What about real data?"* — synthetic generator mirrors real ERP noise
  (abbreviations, missing attrs, UOM variants); PS says CPSEs provide data
  later; architecture is data-agnostic (any CSV with code+description+UOM).
- *"Who owns the NMC?"* — mapped, not replaced: legacy codes stay live in
  each ERP; NMC is the cross-CPSE join key. Zero migration risk.
