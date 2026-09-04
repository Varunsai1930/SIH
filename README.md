# SIH26099 — One Nation, One Material Code

**Problem:** SIH26099 (MOP&NG / CPCL, Software, Smart Automation) — CPSEs each
maintain their own material master, so the same physical material exists as
different codes/descriptions across ERPs. Build an AI platform that matches
equivalent materials across CPSEs, standardizes them, assigns a Common
National Material Code, and keeps full traceability to legacy codes.

**Status: pipeline COMPLETE and evaluated. Tomorrow's job = UI + demo + pitch.**

---

## Quick start

```bash
cd /Users/varun/Downloads/Varun/SIH/sih26099
source .venv/bin/activate              # Python 3.13 venv, all deps installed
python src/generate_dataset.py         # optional: regenerate data (seeded, deterministic)
python src/pipeline.py                 # full run: ~9s, writes outputs/
```

The embedding model (all-MiniLM-L6-v2) is cached in `~/.cache/huggingface`
after the first run. If campus WiFi blocks HuggingFace, the pipeline
**auto-falls back to TF-IDF matching** and still runs — good backup story.

## Results (current run, on 388 records / 4 CPSEs)

| Metric | Value | What it means |
|---|---|---|
| Precision (auto-merge) | **1.000** | every auto-merged pair is correct |
| Trap violations | **0** | near-miss materials (8.8 vs 10.9 bolt) NEVER wrongly merged |
| Cross-CPSE materials merged | 66/105 (62.9%) auto | rest recoverable via review |
| Potential recall after officer approval | **89.7%** | governance workflow recovers ambiguity |
| Review queue | 151 items | the human-in-the-loop story the PS demands |
| Demand-aggregation | 67 shared materials, ~11.5% avg price spread | the savings pitch |

### Verified invariants (automated checks, all PASS)

- Every one of the 388 input records maps to exactly one NMC (no gaps, no duplicates)
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
├── .venv/                  # Python 3.13 env (pandas, sklearn, rapidfuzz, sentence-transformers)
├── data/raw/*.csv          # 4 synthetic CPSE extracts, ground-truthed (true_material_id)
├── src/
│   ├── generate_dataset.py # seeded generator: 4 CPSE styles, duplicates, typos, traps (X-ids)
│   ├── normalize.py        # stage 1 + MIN_ATTRS safety table + synonym dictionaries
│   ├── match.py            # stage 2: blocking, embeddings, veto, review gate, clustering
│   ├── standardize.py      # stage 3: NMC generation, mapping, master
│   └── pipeline.py         # orchestrator + evaluation metrics
└── outputs/*.csv           # all deliverables listed above
```

## Tomorrow's build plan (in priority order)

1. **Streamlit dashboard** (`streamlit run app.py`) — three tabs:
   a. Overview: total records, materials unified, CPSEs sharing, savings chart
   b. Review queue: pick a row, show AI candidates, Approve/Reject buttons
      (append decision to review_queue.csv, re-run merge for that pair)
   c. Lookup: type any legacy code → get NMC + all equivalent codes across CPSEs
2. **Demo script** (rehearse!):
   - Load 4 CPSE files → "these CPSEs have never shared data before"
   - Show two descriptions of the same bolt side by side → AI matches them
   - Show a trap: 8.8 vs 10.9 bolt → AI refuses, cites conflicting grade
   - Approve one review item live (the human-governance moment)
   - Reveal price spread across CPSEs for a shared material → negotiation ammo
   - Close on "One Nation, One Material Code" with full legacy traceability
3. **Pitch deck** — the numbers table above is your evidence slide.
4. Stretch: SAP integration slide (mock REST `/sap/material/{code}` endpoint),
   never live SAP.

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
