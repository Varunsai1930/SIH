"""
UnifyMat (SIH 26099) — data-contract smoke check.

Verifies the contract the dashboard's "spec diff matrix" and "why this
match" explainability rely on:

  bundle["records"]      base fields (cpse, material_code, description, uom)
                         + enriched fields (_attrs dict, _uom_std, _type,
                         _cat, _complete) on every record
  bundle["review_rows"]  six UI keys on every row; every kind="record" row
                         resolves via the (cpse, material_code) -> record
                         index; top_candidates parse with app.py's parser
                         (ui_widgets.parse_candidates — shared source) and
                         resolve to real records (10 sample "Matched on"
                         lines printed as a UI preview)
  bundle["master"]      non-empty national_material_code on every entry
  bundle["mapping"]      exactly one mapping row per ingested record

Note on review-row kinds (real contract, see pipeline.build_review_rows):
kind="record" rows are record-addressable; kind="cluster" rows are keyed by
the cluster's NMC (cpse holds a comma-joined CPSE list, top_candidates holds
a "CLUSTER (confidence 0.xx): …" string that app.py's parse_candidates
regex understands) and are deliberately NOT resolvable through the
records index.

Self-contained and stdlib-only; no network, no test framework.
Exit code 0 = all checks passed, 1 otherwise.

Run:  .venv/bin/python scripts/smoke_check.py
"""
import sys
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from normalize import MIN_ATTRS  # noqa: E402
from pipeline import run_pipeline  # noqa: E402
from ui_widgets import parse_candidates  # noqa: E402  — same parser app.py uses

RECORD_KEYS = ("cpse", "material_code", "description", "uom",
               "_attrs", "_uom_std", "_type", "_cat", "_complete")
REVIEW_KEYS = ("cpse", "material_code", "description", "kind",
               "suggested_nmc", "top_candidates")


def sval(v):
    """Stringified attr value — tuples/lists joined with '/' per contract."""
    if isinstance(v, (list, tuple)):
        return "/".join(str(x) for x in v)
    return str(v)


def agreed_keys(rec_a, rec_b):
    """Attr keys present in both records with equal stringified values."""
    return sorted(k for k in rec_a["_attrs"]
                  if k in rec_b["_attrs"]
                  and sval(rec_a["_attrs"][k]) == sval(rec_b["_attrs"][k]))


def main():
    print("=" * 66)
    print("UnifyMat smoke check — data contract for spec-diff / why-this-match")
    print("=" * 66)
    print("note: first run_pipeline() may load the embedding model (~10s)\n")

    try:
        bundle = run_pipeline()
    except Exception as e:
        print("[!!] run_pipeline() raised — full traceback:\n")
        traceback.print_exc()
        print(f"\nSMOKE CHECK: FAIL — pipeline could not run "
              f"({type(e).__name__}: {e})")
        return 1

    records = bundle["records"]
    review_rows = bundle["review_rows"]
    master = bundle["master"]
    mapping = bundle["mapping"]
    print(f"pipeline ok: {len(records)} records, {len(review_rows)} review rows, "
          f"{len(master)} master entries, {len(mapping)} mappings\n")

    results = []

    def check(name, ok, detail=""):
        print(f"[{'PASS' if ok else 'FAIL'}] {name}"
              + (f" — {detail}" if not ok and detail else ""))
        results.append((name, ok, detail))

    # (a) records: base + enriched fields present, _attrs is a dict ---------
    bad = []
    for i, r in enumerate(records):
        missing = [k for k in RECORD_KEYS if k not in r]
        if not missing and not isinstance(r["_attrs"], dict):
            missing = ["_attrs is not a dict"]
        if missing:
            bad.append(f"record[{i}] ({r.get('cpse')}/{r.get('material_code')}) "
                       f"missing {missing}")
    check(f"records carry base + enriched fields ({len(records)} records)",
          not bad, "; ".join(bad[:3]))

    # (b) review rows: the six UI keys --------------------------------------
    bad = []
    for i, row in enumerate(review_rows):
        missing = [k for k in REVIEW_KEYS if k not in row]
        if missing:
            bad.append(f"row[{i}] missing {missing}")
    check(f"every review row has the six UI keys ({len(review_rows)} rows)",
          not bad, "; ".join(bad[:3]))

    # (c) records index; every kind="record" review row resolves in it ------
    index = {(r["cpse"], r["material_code"]): r for r in records}
    rec_rows = [row for row in review_rows if row.get("kind") == "record"]
    kinds = Counter(row.get("kind", "<none>") for row in review_rows)
    print(f"[i ] review row kinds: {dict(kinds)} "
          "(only kind='record' rows are record-addressable)")
    unresolved = [f"{row['cpse']}/{row['material_code']}" for row in rec_rows
                  if (row["cpse"], row["material_code"]) not in index]
    check(f'all kind="record" review rows resolve in the records index '
          f"({len(rec_rows)} rows)",
          not unresolved, "unresolved: " + ", ".join(unresolved[:3]))

    # (d) first 10 record-kind rows: parse + resolve the TOP candidate ------
    sample = rec_rows[:10]
    print(f"[i ] why-this-match preview — top candidate of the first "
          f"{len(sample)} review records:")
    bad = []
    for row in sample:
        own = index.get((row["cpse"], row["material_code"]))
        cands = parse_candidates(row["top_candidates"])
        cand = cand_id = None
        if len(cands) and str(cands.iloc[0]["candidate"]):
            cand_id = str(cands.iloc[0]["candidate"])
            if "/" in cand_id:
                cand_cpse, _, cand_code = cand_id.partition("/")
                cand = index.get((cand_cpse, cand_code))
        if own is None or cand_id is None or cand is None:
            why = ("own record unresolved" if own is None else
                   "top candidate did not parse" if cand_id is None else
                   f"candidate {cand_id} unresolved in records index")
            bad.append(f"{row['cpse']}/{row['material_code']}: {why}")
            continue
        agreed = agreed_keys(own, cand)
        matched = (" · ".join(f"{k}={sval(own['_attrs'][k])}" for k in agreed)
                   or "no shared attrs")
        print(f"      {row['cpse']}/{row['material_code']} → {cand_id} "
              f"— Matched on: {matched}")
    check(f"top candidate of first {len(sample)} review records parses + resolves",
          not bad, "; ".join(bad[:3]))

    # (e) MIN_ATTRS identity coverage — informational, non-fatal ------------
    by_type = {}
    for r in records:
        by_type.setdefault(r["_type"], r)
    print(f"[i ] MIN_ATTRS identity coverage "
          f"(first 5 of {len(by_type)} distinct _types):")
    for t, r in list(by_type.items())[:5]:
        req = MIN_ATTRS.get(t)
        if req is None:
            print(f"      {t:<20} {r['cpse']}/{r['material_code']}: "
                  f"no MIN_ATTRS entry (type is never auto-merged)")
        else:
            missing = [k for k in req if k not in r["_attrs"]]
            state = "complete" if not missing else "missing " + ", ".join(missing)
            print(f"      {t:<20} {r['cpse']}/{r['material_code']}: {state}")

    # (f) master NMCs non-empty + mapping covers all records ----------------
    empty = [i for i, m in enumerate(master)
             if not str(m.get("national_material_code", "")).strip()]
    check(f"every master entry has a non-empty national_material_code "
          f"({len(master)} entries)",
          not empty, f"{len(empty)} empty NMC(s), first at index {empty[0] if empty else '-'}")
    check(f"mapping covers all records ({len(mapping)} mappings == "
          f"{len(records)} records)",
          len(mapping) == len(records),
          f"mismatch: {len(mapping)} mappings vs {len(records)} records")

    # summary ----------------------------------------------------------------
    n_pass = sum(1 for _, ok, _ in results if ok)
    print()
    failed = [f"{name} — {detail}" if detail else name
              for name, ok, detail in results if not ok]
    if failed:
        print(f"SMOKE CHECK: FAIL — {failed[0]}")
        return 1
    print(f"SMOKE CHECK: PASS ({n_pass} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
