"""
Stage 3: standardization + Common National Material Code + mapping.

- Standardized description: deterministic template from extracted attrs
  (auditable — same inputs always produce the same output, unlike an LLM).
- National Material Code (NMC): hashed canonical form => stable, collision-
  resistant, and readable by humans: NMC-<FAM>-<HASH8>
- Every legacy CPSE code maps to exactly one NMC (traceability, PS requires).
"""
import hashlib
from datetime import datetime

from normalize import detect_type

FAM_CODE = {
    "hex bolt": "FAST-BOLT", "stud bolt": "FAST-STUD", "socket head cap screw": "FAST-SHCS",
    "hex nut": "FAST-NUT", "flat washer": "FAST-WSHR",
    "ball bearing": "BRG-BALL", "roller bearing": "BRG-ROLL",
    "gate valve": "VLV-GATE", "ball valve": "VLV-BALL", "globe valve": "VLV-GLOBE",
    "check valve": "VLV-CHECK", "butterfly valve": "VLV-BFLY", "safety valve": "VLV-SAFETY",
    "pipe": "PIPE", "cable": "ELEC-CABLE", "induction motor": "ELEC-MOTOR",
    "contactor": "ELEC-CONTR", "mcb": "ELEC-MCB",
    "grease": "LUB-GREASE", "hydraulic oil": "LUB-HYDOIL", "turbine oil": "LUB-TURBOIL",
    "gear oil": "LUB-GEAROIL",
    "centrifugal pump": "PMP-CENT", "gear pump": "PMP-GEAR",
    "pressure gauge": "INS-PGAUGE", "thermowell": "INS-THRMW", "level indicator": "INS-LEVEL",
    "elbow": "FIT-ELBOW", "tee": "FIT-TEE", "reducer": "FIT-REDUCER", "flange": "FIT-FLANGE",
    "unknown": "GEN",
}

LABEL = {
    "thread": "THRD", "grade": "GRD", "material": "MAT", "finish": "FIN",
    "class": "CLS", "schedule": "SCH", "seal": "SEAL", "designation": "DSG",
    "end": "END", "flange_type": "FTYP", "voltage": "VLT", "cable_size": "CABL",
    "amps": "AMP", "poles": "POL", "hp": "HP", "rpm": "RPM", "mount": "MNT",
    "nlgi": "NLGI", "viscosity": "VSC", "pack": "PACK", "range": "RNG",
    "flow": "FLOW", "drive": "DRV", "head": "HEAD", "pressure": "PRES",
    "flow_lpm": "FLPM", "seal_type": "SELT", "connection": "CONN", "angle": "ANG",
    "length": "LEN", "insulation": "INSUL", "curve": "CRV", "gauge_type": "GTYP",
    "phase": "PH", "inch": "SIZE",
}

ATTR_ORDER = ["thread", "inch", "designation", "grade", "material", "finish", "class",
              "schedule", "end", "flange_type", "seal", "voltage", "insulation",
              "cable_size", "amps", "poles", "curve", "hp", "rpm", "mount", "phase",
              "nlgi", "viscosity", "pack", "flow", "flow_lpm", "head", "pressure",
              "drive", "seal_type", "range", "gauge_type", "connection", "angle",
              "length", "std"]

UOM_STD = {"NOS": "NOS", "MTR": "MTR", "PKT": "PKT", "KG": "KG", "L": "L"}


PRETTY = {"caststeel": "CAST STEEL", "forgedsteel": "FORGED STEEL", "castiron": "CAST IRON",
          "lithiumep": "LITHIUM EP", "lithium": "LITHIUM", "mineral": "MINERAL", "ep": "EP"}


def _fmt_val(k, v):
    if k == "inch":
        vals = v if isinstance(v, (list, tuple)) else [v]
        return "-".join(f"{x}IN" for x in sorted(vals))
    if k == "std":
        vals = v if isinstance(v, (list, tuple)) else [v]
        return "/".join(s.upper() for s in sorted(vals))
    s = str(v)
    if s.lower() in PRETTY:
        return PRETTY[s.lower()]
    return s.upper().replace(" ", "")


def std_description(fine_type, attrs, uom_std):
    """Deterministic standardized description from canonical attrs."""
    parts = [fine_type.upper()]
    for k in ATTR_ORDER:
        if k in attrs:
            # don't show material and finish when they carry the same value (HDG|HDG)
            if k == "material" and attrs.get("finish") == attrs[k]:
                continue
            parts.append(_fmt_val(k, attrs[k]))
    parts.append(uom_std)
    return " | ".join(parts)


_issued_nmc = {}


def nmc_code(fine_type, attrs, uom_std, issue_key=None):
    """Stable Common National Material Code: NMC-<FAM>-<HASH8>.

    Deterministic: identical canonical forms produce identical codes.
    When the same code would be issued for a *different* record/cluster,
    it is extended so one NMC can never silently mean two materials.
    """
    canon = [FAM_CODE.get(fine_type, "GEN"), uom_std]
    canon += [f"{LABEL.get(k, k)}={_fmt_val(k, attrs[k])}" for k in ATTR_ORDER if k in attrs]
    digest = hashlib.sha1("|".join(canon).encode()).hexdigest()[:8].upper()
    nmc = f"NMC-{FAM_CODE.get(fine_type, 'GEN')}-{digest}"
    if nmc in _issued_nmc and _issued_nmc[nmc] != issue_key:
        n = 1
        while True:
            ext = hashlib.sha1((str(n) + "|").encode() + "|".join(canon).encode()).hexdigest()[:2].upper()
            cand = f"{nmc}{ext}"
            if cand not in _issued_nmc or _issued_nmc[cand] == issue_key:
                nmc = cand
                break
            n += 1
    _issued_nmc[nmc] = issue_key
    return nmc, canon


def merge_attrs(records_in_cluster):
    """Merge extracted attrs across cluster members; prefer the most common value,
    prefer fully-specified rows. Conflicts resolved by majority + first-seen."""
    keys = {}
    for r in records_in_cluster:
        for k, v in r["_attrs"].items():
            keys.setdefault(k, []).append(v)
    merged = {}
    for k, vals in keys.items():
        if k == "std":
            flat = sorted({v for tup in vals for v in (tup if isinstance(tup, (list, tuple)) else [tup])})
            if flat:
                merged[k] = tuple(flat)
            continue
        # majority value; ties broken by order of appearance
        counts = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        merged[k] = max(counts, key=lambda v: (counts[v], -vals.index(v)))
    return merged


def build_master(records, multi, singles, cluster_conf):
    """Produce unified material master, mapping table, review queue, audit log."""
    ts = datetime.now().isoformat(timespec="seconds")
    master, mapping, audit = [], [], []

    for ci, members in enumerate(multi):
        recs = [records[i] for i in members]
        fine_type = recs[0]["_type"]
        cat = recs[0]["_cat"]
        merged = merge_attrs(recs)
        uoms = {}
        for r in recs:
            uoms[r["_uom_std"]] = uoms.get(r["_uom_std"], 0) + 1
        uom_std = max(uoms, key=uoms.get)
        desc = std_description(fine_type, merged, uom_std)
        # issue key = the cluster's member set: distinct clusters can never
        # collide onto one NMC, identical clusters never diverge
        nmc, canon = nmc_code(fine_type, merged, uom_std, issue_key=("cluster", tuple(members)))
        cpse_list = sorted({r["cpse"] for r in recs})
        rep = {}
        for r in recs:
            rep.setdefault(r["cpse"], r["material_code"])
        rates = [float(r.get("last_rate_inr") or 0) for r in recs if r.get("last_rate_inr")]
        master.append({
            "national_material_code": nmc,
            "standardized_description": desc,
            "category": cat,
            "material_type": fine_type,
            "uom": uom_std,
            "cpses_sharing": ",".join(cpse_list),
            "num_legacy_codes": len(recs),
            "avg_rate_inr": round(sum(rates) / len(rates), 2) if rates else "",
            "min_rate_inr": min(rates) if rates else "",
            "max_rate_inr": max(rates) if rates else "",
            "confidence": round(cluster_conf[ci], 4),
            "status": "AUTO_MATCHED" if all(r["_complete"] for r in recs) else "NEEDS_REVIEW",
        })
        for r in recs:
            mapping.append({"national_material_code": nmc,
                            "cpse": r["cpse"],
                            "legacy_material_code": r["material_code"],
                            "legacy_description": r["description"],
                            "legacy_uom": r["uom"],
                            "mapped_at": ts})
        audit.append({"national_material_code": nmc, "action": "CLUSTER_CREATED",
                      "members": len(members), "confidence": round(cluster_conf[ci], 4),
                      "auto": True, "timestamp": ts})

    # singletons -> keep with legacy identity, generate NMC too.
    # Two-pass: records whose canonical form appears more than once are
    # indistinguishable from ERP text alone (the differentiating attribute
    # was never captured). Both get PROVISIONAL codes — the officer review
    # workflow decides whether they are one material or two.
    canon_counts = {}
    for i in singles:
        r = records[i]
        canon = (FAM_CODE.get(r["_type"], "GEN"), r["_uom_std"],
                 tuple(sorted((k, _fmt_val(k, r["_attrs"][k]))
                              for k in r["_attrs"] if k != "std")))
        canon_counts[tuple(canon)] = canon_counts.get(tuple(canon), 0) + 1

    issued = {}
    for i in singles:
        r = records[i]
        fine_type, cat = r["_type"], r["_cat"]
        merged = dict(r["_attrs"])
        uom_std = r["_uom_std"]
        desc = std_description(fine_type, merged, uom_std)
        canon = (FAM_CODE.get(fine_type, "GEN"), uom_std,
                 tuple(sorted((k, _fmt_val(k, merged[k]))
                              for k in merged if k != "std")))
        duplicate_form = canon_counts[tuple(canon)] > 1
        if duplicate_form:
            nmc = (f"PROVISIONAL-{fine_type.upper().replace(' ', '-')[:14]}"
                   f"-{r['cpse']}-{r['material_code']}")
            status = "PROVISIONAL — OFFICER REVIEW (indistinguishable twin)"
        else:
            nmc, _ = nmc_code(fine_type, merged, uom_std, issue_key=("single", i))
            status = "UNIQUE" if r["_complete"] else "NEEDS_REVIEW"
        rates = [float(r.get("last_rate_inr") or 0) for _ in [r] if r.get("last_rate_inr")]
        master.append({
            "national_material_code": nmc,
            "standardized_description": desc,
            "category": cat,
            "material_type": fine_type,
            "uom": uom_std,
            "cpses_sharing": r["cpse"],
            "num_legacy_codes": 1,
            "avg_rate_inr": r.get("last_rate_inr") or "",
            "min_rate_inr": "", "max_rate_inr": "",
            "confidence": 1.0 if not duplicate_form else 0.5,
            "status": status,
        })
        mapping.append({"national_material_code": nmc, "cpse": r["cpse"],
                        "legacy_material_code": r["material_code"],
                        "legacy_description": r["description"],
                        "legacy_uom": r["uom"], "mapped_at": ts})

    return master, mapping, audit
