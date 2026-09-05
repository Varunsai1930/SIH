# Security Checkup — UnifyMat (SIH 26099)

Date: 2026-09-05 · Scope: the full repo (`src/`, `scripts/`, `data/`,
`.streamlit/`, docs) · Methodology: adapted from the ecc repository's
security guides and CI gates (`rules/common|python|web/security.md`,
`skills/security-review`, `the-security-guide.md`: secrets scan, bandit,
pip-audit, injection/XSS/upload-validation checks, hidden-unicode sweeps).

## Verdict

**No open HIGH or MEDIUM findings.** One stored-XSS class and one
CSV-injection class were found by the audit and **fixed and regression-tested**
the same day; three LOW/informational items are reviewed and accepted below.

## Checks performed

| Check | Tool / method | Result |
|---|---|---|
| Secrets in source/config | ecc `SECURITY.md` grep pattern over `src/ scripts/ data/`; `.env` file hunt | **clean** — no keys/tokens/passwords; no `.env` exists |
| Hidden unicode / payloads | ecc `the-security-guide.md` ripgrep patterns (zero-width, bidi, `data:text/html`, `base64,`) | **clean** |
| Static analysis (SAST) | `bandit -r src scripts -ll -ii` | **clean** (see LOW notes) |
| Dependency audit | `pip-audit -r requirements.txt` | **no known vulnerabilities**; requirements now **pinned** to the verified build |
| Unsafe deserialization / eval / shell | grep: `eval(`, `exec(`, `pickle`, `yaml.load(`, `os.system`, `subprocess`, `shell=True`, `torch.load` | **clean** — none present |
| Path traversal / arbitrary write | audit of the upload slug path (`app.py`) | **clean** — slug regex keeps only `[a-z0-9]`; collision guard added (below) |
| XSS in `unsafe_allow_html` sinks | full audit of every `st.markdown(..., unsafe_allow_html=True)` call site | **2 sink groups fixed** (below) |
| CSV/formula injection | audit of `write_csv` + all download buttons | **guard added** (below) |
| Resource exhaustion | audit of upload path + `match_all` | **row cap + chunked/bounded matching added** (below) |
| E2E hostile-input test | malicious CSV through the real pipeline (`=HYPERLINK` formula, `<img onerror>` payload) | formula cell exported guarded; XSS payload inert; UI renders it escaped |

## Findings fixed (this session)

1. **Stored XSS (HIGH)** — `suggested_nmc`, lookup-card `nmc`,
   `standardized_description`, and `uom` were interpolated into
   `st.markdown(..., unsafe_allow_html=True)` unescaped. A `PROVISIONAL-…`
   NMC embeds the raw `material_code` from an uploaded CSV, so a hostile
   upload could execute script in an officer's browser. **Fix:** `html.escape`
   at all four sinks (+ `kpi_card` hardened as a sink). Regression-tested
   (the `<img src=x onerror=…>` payload renders escaped).
2. **CSV/formula injection (HIGH)** — exported CSVs officers open in Excel
   carried raw cells; a code/description like `=HYPERLINK(...)` would
   execute on open. **Fix:** `guard_formula_cell()` in `pipeline.write_csv`
   (all `outputs/` files) + `safe_csv_bytes()` on all in-app download
   buttons + the officer-decisions file. Strings starting with
   `= + - @` or a leading tab/CR get a leading apostrophe; numbers are
   untouched (negative rates stay numeric). E2E-tested; outputs remain
   byte-identical on the real data (no cell needed guarding).
3. **Resource exhaustion (HIGH)** — an unbounded CSV upload could OOM/hang
   the single-threaded app (dense n×n similarity matrix per category
   block). **Fix:** `MAX_UPLOAD_ROWS = 5000` refusal (E2E-tested with a
   5,001-row upload) **and** `match_all` rewritten to chunked similarity
   computation with a top-k candidate bound — outputs proven
   byte-identical in exact order on the benchmark data.
4. **Silent slug-collision overwrite (LOW)** — `"GAIL!"` slugs onto
   `gail_materials.csv` and would have overwritten GAIL's ingested data.
   **Fix:** exact-name re-uploads are allowed; a name that merely slugs
   onto another CPSE's file is refused with an explanation.
5. **Bandit B324 SHA1 (HIGH by tool, non-issue by design)** — the NMC hash
   is a content fingerprint, not a security primitive. **Fix:**
   `usedforsecurity=False` on both `hashlib.sha1` calls; digest unchanged
   (NMCs byte-identical), intent now explicit and the finding cleared.

## Reviewed and accepted (LOW / informational)

- **`try/except/pass`** in `load_decisions()` and the lookup price guard
  (bandit B110): intentional graceful degradation — a corrupt decisions
  file must not take the dashboard down.
- **`random` module in `generate_dataset.py`** (bandit B311): dev-only,
  seeded synthetic data generation; not used at runtime or for anything
  cryptographic.
- **Officer identity is a free-text field** (no auth). The dashboard is a
  single-tenant demo tool; decisions are logged with name + timestamp and
  are reversible (audit trail). Real deployment requires SSO/role binding
  before the NMC registry is write-capable — noted as a production
  requirement, not a demo gap.
- **`audit_log.csv` is regenerated per run** (machine actions), while
  officer decisions persist. Only the officer's decision file is
  append-only; for a tamper-evident trail in production, sign/append-only
  storage is the next step.
- **Model download on first run** — `all-MiniLM-L6-v2` is fetched from
  HuggingFace; the pipeline falls back to TF-IDF offline. Supply-chain
  trust rests on HF + the pinned `sentence-transformers`/`torch` versions.

## Re-run this checkup locally

```bash
source .venv/bin/activate
bandit -r src scripts -ll -ii          # SAST — expect: no issues identified
pip-audit -r requirements.txt          # dependencies — expect: no vulnerabilities
grep -rEn '(TOKEN|SECRET|KEY|PASSWORD|PASSWD|API_)[A-Z_]*\s*[:=]\s*["'"'"'][A-Za-z0-9_-]{16,}["'"'"']' \
     src/ scripts/ data/               # secrets — expect: no output
python src/pipeline.py                 # outputs regenerate deterministically
python scripts/smoke_check.py          # 6 checks
python scripts/apptest_check.py       # 13 UI checks
```
