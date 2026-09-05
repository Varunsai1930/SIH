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
from match import match_all, cluster, record_complete, pair_verdict
from standardize import build_master

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
DECISIONS = OUT / "review_decisions.csv"

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


def evaluate_final(records, mapping):
    """Pairwise accuracy of the FINAL registry — machine merges + officer
    decisions — against ground truth. This is the number the governance
    workflow actually delivers (vs evaluate(), which is auto-merge only)."""
    idx = {(r["cpse"], r["material_code"]): i for i, r in enumerate(records)}
    labeled = {i for i, r in enumerate(records) if r.get("true_material_id")}

    idx_by_truth = defaultdict(list)
    for i in labeled:
        idx_by_truth[records[i]["true_material_id"]].append(i)
    same_truth = set()
    for members in idx_by_truth.values():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                same_truth.add(tuple(sorted((members[x], members[y]))))

    groups = defaultdict(list)
    for row in mapping:
        i = idx.get((row["cpse"], row["legacy_material_code"]))
        if i is not None:
            groups[row["national_material_code"]].append(i)
    pred_same = set()
    for members in groups.values():
        lab_m = sorted(i for i in members if i in labeled)
        for x in range(len(lab_m)):
            for y in range(x + 1, len(lab_m)):
                pred_same.add((lab_m[x], lab_m[y]))

    tp = len(same_truth & pred_same)
    fp = len(pred_same - same_truth)
    fn = len(same_truth - pred_same)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    trap_violations = 0
    for members in groups.values():
        ids = {records[i]["true_material_id"] for i in members if i in labeled}
        if any(x.startswith("X") for x in ids) and any(x.startswith("T") for x in ids):
            trap_violations += 1
    return {"final_precision": precision,
            "final_recall": recall, "final_trap_violations": trap_violations}


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

    decided = {}
    for d in load_officer_decisions():
        decided[(d["cpse"], d["material_code"])] = d["decision"]
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
            "decision": decided.get((rec["cpse"], rec["material_code"]), ""),
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


def shared_materials(master):
    """Master rows shared by 2+ CPSEs (the demand-aggregation set)."""
    return [m for m in master
            if m["num_legacy_codes"] >= 2 and "," in m["cpses_sharing"]]


def row_spread(m):
    """(max-min)/max for a master row with both rate bounds, else None."""
    try:
        if m["max_rate_inr"] and m["min_rate_inr"]:
            return ((float(m["max_rate_inr"]) - float(m["min_rate_inr"]))
                    / float(m["max_rate_inr"]))
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def price_spreads(master):
    """(row, spread) for shared materials with a computable price spread —
    one definition shared by the CLI report, the Overview KPI, and the
    Master-Catalog spotlight so the number a judge sees never drifts
    between tabs. Includes zero spreads (use row_spread(m) != 0 to
    exclude them, e.g. the 'with price spread' filter)."""
    return [(m, s) for m in shared_materials(master)
            if (s := row_spread(m)) is not None]


def load_officer_decisions():
    """Persistent officer decisions (outputs/review_decisions.csv), newest last."""
    if not DECISIONS.exists():
        return []
    import csv as _csv
    with open(DECISIONS, newline="", encoding="utf-8") as f:
        return [row for row in _csv.DictReader(f)
                if row.get("material_code") and row.get("decision")]


def _hard_conflict(rec_a, rec_b):
    """True when a conflicting hard engineering attribute makes ANY merge of
    the two records unsafe — for AI and officer alike (Lock 1)."""
    _, _, reason = pair_verdict(rec_a, rec_b, 1.0)
    return reason.startswith("veto")


def apply_officer_decisions(records, decisions, master, mapping, audit, review_rows):
    """Close the human-in-the-loop: officer decisions change the registry.

    APPROVED record-kind decisions merge the held record into the exact NMC
    the officer confirmed. The record's mapping row is re-pointed to that
    code (mapped onto it — the target's identity is never re-derived, so
    the officer's decision stays valid across runs), the target master row
    grows by it, and the record's retired singleton code disappears from
    the master. A conflicting hard engineering attribute against ANY member
    of the target cluster still blocks the merge — an officer cannot put a
    grade 8.8 bolt into a 10.9 code — and the refusal is audited as
    OFFICER_MERGE_BLOCKED.

    REJECTED decisions leave the record standing alone under its own code:
    the officer has ruled the AI's proposal wrong, so it is never re-merged.

    Mutates master/mapping/audit/review_rows in place; returns stats.
    """
    idx = {(r["cpse"], r["material_code"]): i for i, r in enumerate(records)}
    latest = {}
    for d in decisions:  # a record decided twice: the newest decision wins
        latest[(d["cpse"], d["material_code"])] = d

    maps_by_nmc = defaultdict(list)
    row_by_record = {}
    for row in mapping:
        maps_by_nmc[row["national_material_code"]].append(row)
        row_by_record[(row["cpse"], row["legacy_material_code"])] = row
    master_by_nmc = {m["national_material_code"]: m for m in master}

    # officer merges applied this run, per target: a second merge into the
    # same code must veto-check against the first officer's record too
    added = defaultdict(list)
    merges, blocked, stale = 0, 0, 0

    for (cpse, code), d in sorted(latest.items()):
        if d["decision"] != "APPROVED" or d.get("kind") != "record":
            continue
        target_nmc = d.get("suggested_nmc", "")
        mrow = master_by_nmc.get(target_nmc)
        i = idx.get((cpse, code))
        if i is None or mrow is None or target_nmc not in maps_by_nmc:
            stale += 1     # record or approved code no longer in the registry
            continue
        my_row = row_by_record.get((cpse, code))
        if my_row is None:
            continue
        old_nmc = my_row["national_material_code"]
        if old_nmc == target_nmc:
            continue        # already mapped onto the approved code
        members = [idx[(m["cpse"], m["legacy_material_code"])]
                   for m in maps_by_nmc[target_nmc]
                   if (m["cpse"], m["legacy_material_code"]) in idx]
        members += added[target_nmc]
        if i in members:
            continue
        rec = records[i]
        if any(_hard_conflict(rec, records[m]) for m in members):
            blocked += 1
            audit.append({"national_material_code": target_nmc,
                          "action": "OFFICER_MERGE_BLOCKED",
                          "members": len(members), "confidence": 1.0,
                          "auto": False, "timestamp": d.get("timestamp", "")})
            for rr in review_rows:
                if rr["kind"] == "record" and \
                        (rr["cpse"], rr["material_code"]) == (cpse, code):
                    rr["decision"] = "APPROVED — BLOCKED (hard-attribute conflict)"
            continue

        # merge: re-point the mapping row, retire the old singleton code,
        # grow the target master row (legacy count, sharing CPSEs, price band)
        member_recs = [records[m] for m in members] + [rec]
        rates = [float(r.get("last_rate_inr") or 0) for r in member_recs
                 if r.get("last_rate_inr")]
        mrow["num_legacy_codes"] += 1
        cpes = set(mrow["cpses_sharing"].split(","))
        cpes.add(rec["cpse"])
        mrow["cpses_sharing"] = ",".join(sorted(cpes))
        mrow["avg_rate_inr"] = round(sum(rates) / len(rates), 2) if rates else mrow["avg_rate_inr"]
        mrow["min_rate_inr"] = min(rates) if rates else mrow["min_rate_inr"]
        mrow["max_rate_inr"] = max(rates) if rates else mrow["max_rate_inr"]
        mrow["status"] = "OFFICER_MERGED"
        my_row["national_material_code"] = target_nmc
        # retire the merged record's now-empty singleton code (a review-kind
        # record is never auto-merged, so its old code always holds exactly
        # itself; guard anyway so a multi-member code is never stranded)
        old_row = master_by_nmc.get(old_nmc)
        if old_row is not None and old_row["num_legacy_codes"] == 1:
            master[:] = [m for m in master
                         if m["national_material_code"] != old_nmc]
        audit.append({"national_material_code": target_nmc,
                      "action": "OFFICER_MERGED", "members": len(member_recs),
                      "confidence": 1.0, "auto": False,
                      "timestamp": d.get("timestamp", "")})
        added[target_nmc].append(i)
        merges += 1

    return {"merges_applied": merges, "merges_blocked": blocked, "stale": stale}


def guard_formula_cell(v):
    """CSV-injection guard: a STRING cell that Excel/LibreOffice would treat
    as a formula (=, +, -, @, or a leading tab/CR) gets a leading apostrophe
    so officer workbooks show it as text, never execute it. Numbers (e.g. a
    legitimate negative rate) pass through untouched."""
    if isinstance(v, str) and v and v[0] in "=+-@\t\r":
        return "'" + v
    return v


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: guard_formula_cell(v) for k, v in row.items()})


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

    # officer decisions change the registry itself — after the machine pass
    # (metrics stay "auto-merge only" so the 1.000 precision claim remains
    # strictly about the machine; officer merges are reported separately)
    officer = apply_officer_decisions(records, load_officer_decisions(),
                                     master, mapping, audit, review_rows)
    metrics["officer_merges_applied"] = officer["merges_applied"]
    if metrics["has_ground_truth"]:
        metrics.update(evaluate_final(records, mapping))

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
        "officer_merges": officer,
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
        if "final_recall" in m:
            print(f"    FINAL registry (machine + officer decisions): "
                  f"precision {m['final_precision']:.3f} · recall {m['final_recall']:.3f} · "
                  f"trap violations {m['final_trap_violations']}")
        if m.get("officer_merges_applied"):
            print(f"    officer merges applied this run: {m['officer_merges_applied']}"
                  + (f" ({b['officer_merges']['merges_blocked']} blocked by hard-attribute "
                     f"veto)" if b["officer_merges"]["merges_blocked"] else ""))
        if m["unlabeled"]:
            print(f"    production mode: {m['unlabeled']} uploaded record(s) without ground truth "
                  f"excluded from accuracy metrics")
    else:
        print("    no ground-truth labels present (production ingest) — accuracy metrics skipped")

    print(f"\n[5] Standardization: {len(b['master'])} national materials, "
          f"{len(b['mapping'])} legacy mappings")

    spreads = [p for _, p in price_spreads(b["master"])]
    if spreads:
        print(f"\n[6] Demand-aggregation: {len(shared_materials(b['master']))} materials "
              f"shared across CPSEs, avg price spread {sum(spreads)/len(spreads):.1%}")

    print(f"\nDone in {b['runtime_s']}s. Outputs in outputs/")
    if m["has_ground_truth"] and m["trap_violations"] > 0:
        print("\n!! WARNING: trap violations detected — veto layer needs tuning", file=sys.stderr)
    return b


if __name__ == "__main__":
    main()
