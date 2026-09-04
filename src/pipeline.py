"""
SIH26099 pipeline orchestrator.

End-to-end: load CPSE files -> normalize -> match -> cluster -> standardize
-> generate National Material Code + mapping -> evaluate vs ground truth.

CLI:      .venv/bin/python src/pipeline.py
Library:  run_pipeline() -> artifacts dict (used by the Streamlit app)

Handles arbitrary CPSE files: any data/raw/*_materials.csv is ingested.
Ground truth (true_material_id) is optional — when absent, accuracy
metrics are computed over the labeled subset only ("production mode").
"""
import csv
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from normalize import normalize_text, detect_type, extract_attrs, normalize_uom
from match import match_all, cluster, record_complete
from standardize import build_master

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

REQUIRED_COLS = ["material_code", "description", "uom"]


def load_records():
    """Ingest every data/raw/*_materials.csv. Returns (records, ingest_report)."""
    records = []
    report = {}
    for path in sorted(RAW.glob("*_materials.csv")):
        n, skipped = 0, 0
        fallback_cpse = path.stem.split("_")[0].upper()
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if not row.get("material_code") or not row.get("description"):
                    skipped += 1
                    continue
                records.append({
                    "cpse": (row.get("cpse") or fallback_cpse).strip().upper(),
                    "material_code": row["material_code"],
                    "description": row["description"],
                    "uom": row.get("uom", ""),
                    "category_hint": row.get("category_hint", ""),
                    "hsn_code": row.get("hsn_code", ""),
                    "last_rate_inr": row.get("last_rate_inr", ""),
                    "true_material_id": row.get("true_material_id", ""),
                })
                n += 1
        report[path.stem] = {"rows": n, "skipped": skipped}
    return records, report


def enrich(records):
    for r in records:
        norm = normalize_text(r["description"])
        fine_type, cat = detect_type(norm)
        r["_norm"] = norm
        r["_type"] = fine_type
        r["_cat"] = cat
        r["_attrs"] = extract_attrs(norm, fine_type)
        r["_uom_std"] = normalize_uom(r["uom"])
        r["_complete"] = record_complete(r)
    return records


def evaluate(records, multi):
    """Pairwise precision/recall on the LABELED subset + trap safety."""
    labeled = [i for i, r in enumerate(records) if r.get("true_material_id")]
    lab = set(labeled)
    n_unlabeled = len(records) - len(labeled)

    idx_by_truth = defaultdict(list)
    for i in labeled:
        idx_by_truth[records[i]["true_material_id"]].append(i)
    same_truth = set()
    for members in idx_by_truth.values():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                same_truth.add((members[x], members[y]))

    pred_same = set()
    for members in multi:
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                if members[x] in lab and members[y] in lab:
                    pred_same.add((members[x], members[y]))

    tp = len(same_truth & pred_same)
    fp = len(pred_same - same_truth)
    fn = len(same_truth - pred_same)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    truth_multi_cpse = {t for t, idxs in idx_by_truth.items()
                        if len({records[i]["cpse"] for i in idxs}) >= 2}
    merged_multi = set()
    for members in multi:
        ids = {records[i]["true_material_id"] for i in members if i in lab}
        if len(ids) == 1 and len({records[i]["cpse"] for i in members}) >= 2:
            merged_multi |= ids

    trap_violations = 0
    for members in multi:
        ids = {records[i]["true_material_id"] for i in members if i in lab}
        if any(x.startswith("X") for x in ids) and any(x.startswith("T") for x in ids):
            trap_violations += 1

    return {
        "unlabeled": n_unlabeled,
        "pairs_total_truth": len(same_truth), "tp": tp,
        "precision": precision, "recall": recall, "f1": f1,
        "cross_cpse_truth": len(truth_multi_cpse), "cross_cpse_merged": len(merged_multi),
        "cross_cpse_recall": len(merged_multi) / len(truth_multi_cpse) if truth_multi_cpse else 0,
        "trap_violations": trap_violations,
        "has_ground_truth": len(labeled) > 0,
    }


def review_stats(records, reviews, tp, total_pairs):
    """How much recall the human-review workflow can recover (labeled pairs)."""
    correct = sum(1 for r in reviews
                  if records[r["a"]].get("true_material_id")
                  and records[r["a"]]["true_material_id"] == records[r["b"]]["true_material_id"])
    return {"review_pairs": len(reviews), "review_same_material": correct,
            "potential_recall": (tp + correct) / total_pairs if total_pairs else 0.0}


def build_review_rows(records, reviews, multi, singles, cluster_conf, master):
    """One row per ambiguous record, with its top candidates + suggested NMC."""
    idx_to_nmc = {}
    for ci, members in enumerate(multi):
        for i in members:
            idx_to_nmc[i] = master[ci]["national_material_code"]
    for k, i in enumerate(singles):
        idx_to_nmc[i] = master[len(multi) + k]["national_material_code"]

    rev_by_rec = defaultdict(list)
    for r in reviews:
        ra, rb = records[r["a"]], records[r["b"]]
        key = r["a"] if not ra["_complete"] else r["b"]
        other = r["b"] if key == r["a"] else r["a"]
        rev_by_rec[key].append((r["sim"], other))
    rows = []
    for key, cands in rev_by_rec.items():
        rec = records[key]
        cands.sort(reverse=True)
        top = cands[:3]
        cand_str = " || ".join(
            f"{records[o]['cpse']}/{records[o]['material_code']} (sim {sim:.2f}): {records[o]['description']}"
            for sim, o in top)
        rows.append({
            "kind": "record", "reason": "missing-identity-attribute",
            "cpse": rec["cpse"], "material_code": rec["material_code"],
            "description": rec["description"],
            "top_candidates": cand_str,
            "suggested_nmc": idx_to_nmc.get(top[0][1], "") if top else "",
            "decision": "",
        })
    for ci, members in enumerate(multi):
        if cluster_conf[ci] < 0.70:
            m = master[ci]
            rows.append({
                "kind": "cluster", "reason": "low-confidence",
                "cpse": m["cpses_sharing"], "material_code": m["national_material_code"],
                "description": m["standardized_description"],
                "top_candidates": f"CLUSTER (confidence {cluster_conf[ci]:.2f}): low-confidence merge held for review",
                "suggested_nmc": m["national_material_code"], "decision": "",
            })
    return rows


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def run_pipeline():
    """Full run. Returns artifacts for the CLI printer and the Streamlit app."""
    t0 = time.time()
    records, ingest_report = load_records()
    records = enrich(records)

    matches, vetoes, reviews, emb_info = match_all(records)
    multi, singles, cluster_conf = cluster(records, matches)

    metrics = evaluate(records, multi)
    rvw = review_stats(records, reviews, metrics["tp"], metrics["pairs_total_truth"])
    master, mapping, audit = build_master(records, multi, singles, cluster_conf)
    review_rows = build_review_rows(records, reviews, multi, singles, cluster_conf, master)

    write_csv(OUT / "unified_master.csv", master,
              ["national_material_code", "standardized_description", "category", "material_type",
               "uom", "cpses_sharing", "num_legacy_codes", "avg_rate_inr", "min_rate_inr",
               "max_rate_inr", "confidence", "status"])
    write_csv(OUT / "code_mapping.csv", mapping,
              ["national_material_code", "cpse", "legacy_material_code", "legacy_description",
               "legacy_uom", "mapped_at"])
    write_csv(OUT / "review_queue.csv", review_rows,
              ["kind", "reason", "cpse", "material_code", "description",
               "top_candidates", "suggested_nmc", "decision"])
    write_csv(OUT / "audit_log.csv", audit,
              ["national_material_code", "action", "members", "confidence", "auto", "timestamp"])
    write_csv(OUT / "rejected_pairs.csv", vetoes,
              ["a_cpse", "a_code", "a_desc", "b_cpse", "b_code", "b_desc", "sim", "reason"])

    return {
        "records": records, "ingest_report": ingest_report,
        "master": master, "mapping": mapping, "audit": audit,
        "review_rows": review_rows, "vetoes": vetoes,
        "metrics": metrics, "review": rvw, "emb_info": emb_info,
        "multi": multi, "singles": singles, "cluster_conf": cluster_conf,
        "n_matches": len(matches), "n_review_pairs": len(reviews),
        "runtime_s": round(time.time() - t0, 1),
    }


def main():
    print("=" * 62)
    print("SIH26099 — One Nation, One Material Code: pipeline run")
    print("=" * 62)
    b = run_pipeline()

    print(f"\n[1] Ingested {len(b['records'])} records from {len(b['ingest_report'])} CPSE files")
    for name, r in b["ingest_report"].items():
        print(f"    {name:<28} {r['rows']:4d} rows" + (f" ({r['skipped']} skipped)" if r["skipped"] else ""))
    complete = sum(1 for r in b["records"] if r["_complete"])
    print(f"    auto-mergeable (identity attrs complete): {complete} | flagged incomplete: {len(b['records']) - complete}")
    print("    categories:", dict(Counter(r["_cat"] for r in b["records"])))

    print(f"\n[2] Matching (embeddings: {b['emb_info']})")
    print(f"    auto-matched pairs: {b['n_matches']} | attribute-veto rejections: {len(b['vetoes'])}")
    print(f"    sent to human review: {b['n_review_pairs']}")

    print(f"\n[3] Clustering: {len(b['multi'])} merged groups, {len(b['singles'])} unique materials")

    m = b["metrics"]
    print(f"\n[4] Evaluation vs ground truth (auto-merge only)")
    if m["has_ground_truth"]:
        print(f"    precision: {m['precision']:.3f} | recall: {m['recall']:.3f} | F1: {m['f1']:.3f}")
        print(f"    cross-CPSE materials merged: {m['cross_cpse_merged']}/{m['cross_cpse_truth']}"
              f" ({m['cross_cpse_recall']:.1%})")
        print(f"    TRAP violations (X merged with T): {m['trap_violations']}  <- must be 0")
        print(f"    human-review queue: {b['review']['review_pairs']} pairs, "
              f"{b['review']['review_same_material']} are true matches")
        print(f"    potential recall after officer approval: {b['review']['potential_recall']:.1%}")
        if m["unlabeled"]:
            print(f"    production mode: {m['unlabeled']} uploaded record(s) without ground truth "
                  f"excluded from accuracy metrics")
    else:
        print("    no ground-truth labels present (production ingest) — accuracy metrics skipped")

    print(f"\n[5] Standardization: {len(b['master'])} national materials, "
          f"{len(b['mapping'])} legacy mappings")

    shared = [x for x in b["master"] if x["num_legacy_codes"] >= 2 and "," in x["cpses_sharing"]]
    spreads = []
    for s in shared:
        try:
            if s["max_rate_inr"] and s["min_rate_inr"]:
                spreads.append((float(s["max_rate_inr"]) - float(s["min_rate_inr"]))
                               / float(s["max_rate_inr"]))
        except Exception:
            pass
    if spreads:
        print(f"\n[6] Demand-aggregation: {len(shared)} materials shared across CPSEs, "
              f"avg price spread {sum(spreads)/len(spreads):.1%}")

    print(f"\nDone in {b['runtime_s']}s. Outputs in outputs/")
    if m["has_ground_truth"] and m["trap_violations"] > 0:
        print("\n!! WARNING: trap violations detected — veto layer needs tuning", file=sys.stderr)
    return b


if __name__ == "__main__":
    main()
