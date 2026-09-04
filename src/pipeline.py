"""
SIH26099 pipeline orchestrator.

End-to-end: load CPSE files -> normalize -> match -> cluster -> standardize
-> generate National Material Code + mapping -> evaluate vs ground truth.

Run:  .venv/bin/python src/pipeline.py
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

CPSES = ["cpcl", "iocl", "ntpc", "sail"]


def load_records():
    records = []
    for c in CPSES:
        with open(RAW / f"{c}_materials.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                records.append({
                    "cpse": row["cpse"],
                    "material_code": row["material_code"],
                    "description": row["description"],
                    "uom": row["uom"],
                    "category_hint": row["category_hint"],
                    "hsn_code": row["hsn_code"],
                    "last_rate_inr": row["last_rate_inr"],
                    "true_material_id": row["true_material_id"],
                })
    return records


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


def evaluate(records, multi, singles):
    """Pairwise precision/recall on ground truth + trap safety."""
    same_truth = set()
    idx_by_truth = defaultdict(list)
    for i, r in enumerate(records):
        idx_by_truth[r["true_material_id"]].append(i)
    for members in idx_by_truth.values():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                same_truth.add((min(members[x], members[y]), max(members[x], members[y])))

    pred_same = set()
    for members in multi:
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
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
        ids = {records[i]["true_material_id"] for i in members}
        if len(ids) == 1 and len({records[i]["cpse"] for i in members}) >= 2:
            merged_multi |= ids

    trap_violations = 0
    for members in multi:
        ids = {records[i]["true_material_id"] for i in members}
        if any(x.startswith("X") for x in ids) and any(x.startswith("T") for x in ids):
            trap_violations += 1

    return {
        "pairs_total_truth": len(same_truth), "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "cross_cpse_truth": len(truth_multi_cpse), "cross_cpse_merged": len(merged_multi),
        "cross_cpse_recall": len(merged_multi) / len(truth_multi_cpse) if truth_multi_cpse else 0,
        "trap_violations": trap_violations,
    }


def review_stats(records, reviews, tp, total_pairs):
    """How much recall the human-review workflow can recover."""
    correct = sum(1 for r in reviews
                  if records[r["a"]]["true_material_id"] == records[r["b"]]["true_material_id"])
    return {"review_pairs": len(reviews), "review_same_material": correct,
            "review_recovery": correct / len(reviews) if reviews else 0.0,
            "potential_recall": (tp + correct) / total_pairs if total_pairs else 0.0}


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    t0 = time.time()
    print("=" * 62)
    print("SIH26099 — One Nation, One Material Code: pipeline run")
    print("=" * 62)

    records = enrich(load_records())
    complete = sum(1 for r in records if r["_complete"])
    print(f"\n[1] Loaded + enriched {len(records)} records from {len(CPSES)} CPSEs")
    print(f"    auto-mergeable (identity attrs complete): {complete} | "
          f"flagged incomplete: {len(records) - complete}")
    print("    categories:", dict(Counter(r["_cat"] for r in records)))

    matches, vetoes, reviews, nomatches, emb_info = match_all(records)
    print(f"\n[2] Matching (embeddings: {emb_info})")
    print(f"    auto-matched pairs: {len(matches)} | attribute-veto rejections: {len(vetoes)}")
    print(f"    sent to human review: {len(reviews)} | below threshold: {len(nomatches)}")

    multi, singles, cluster_conf, exclude = cluster(records, matches)
    print(f"\n[3] Clustering: {len(multi)} merged groups, {len(singles)} unique materials")
    if exclude:
        print(f"    transitivity repair dropped {len(exclude)} weak edge(s)")

    metrics = evaluate(records, multi, singles)
    rvw = review_stats(records, reviews, metrics["tp"], metrics["pairs_total_truth"])
    print(f"\n[4] Evaluation vs ground truth (auto-merge only)")
    print(f"    precision: {metrics['precision']:.3f} | recall: {metrics['recall']:.3f} | F1: {metrics['f1']:.3f}")
    print(f"    cross-CPSE materials merged: {metrics['cross_cpse_merged']}/{metrics['cross_cpse_truth']}"
          f" ({metrics['cross_cpse_recall']:.1%})")
    print(f"    TRAP violations (X merged with T): {metrics['trap_violations']}  <- must be 0")
    print(f"    human-review queue: {rvw['review_pairs']} pairs, "
          f"{rvw['review_same_material']} are true matches")
    print(f"    potential recall after officer approval: {rvw['potential_recall']:.1%}")

    master, mapping, audit = build_master(records, multi, singles, cluster_conf)
    print(f"\n[5] Standardization: {len(master)} national materials, "
          f"{len(mapping)} legacy mappings")

    # ---- review queue: one row per ambiguous record, with its top candidates ----
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
    review_rows = []
    for key, cands in rev_by_rec.items():
        rec = records[key]
        cands.sort(reverse=True)
        top = cands[:3]
        cand_str = " || ".join(
            f"{records[o]['cpse']}/{records[o]['material_code']} (sim {sim:.2f}): {records[o]['description']}"
            for sim, o in top)
        review_rows.append({
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
            review_rows.append({
                "kind": "cluster", "reason": "low-confidence",
                "cpse": m["cpses_sharing"], "material_code": m["national_material_code"],
                "description": m["standardized_description"],
                "top_candidates": f"confidence {cluster_conf[ci]:.2f}",
                "suggested_nmc": m["national_material_code"], "decision": "",
            })

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

    # demand-aggregation story: shared materials + price spread
    shared = [m for m in master if m["num_legacy_codes"] >= 2 and "," in m["cpses_sharing"]]
    spreads = []
    for s in shared:
        try:
            if s["max_rate_inr"] and s["min_rate_inr"]:
                spreads.append((float(s["max_rate_inr"]) - float(s["min_rate_inr"]))
                               / float(s["max_rate_inr"]))
        except Exception:
            pass
    if spreads:
        print(f"\n[6] Demand-aggregation story: {len(shared)} materials shared across CPSEs, "
              f"avg price spread {sum(spreads)/len(spreads):.1%}")

    print(f"\nDone in {time.time()-t0:.1f}s. Outputs in outputs/")
    return metrics, rvw


if __name__ == "__main__":
    m, _ = main()
    if m["trap_violations"] > 0:
        print("\n!! WARNING: trap violations detected — veto layer needs tuning", file=sys.stderr)
