"""
Stage 2: candidate matching + clustering.

Approach (explainable, scales to millions of rows):
  1. BLOCK by detected family/type (bolt vs valve never compared — O(n·k))
  2. RANK candidates with sentence embeddings (semantic similarity survives
     abbreviation / word-order / attribute-drop noise)
  3. VETO on conflicting hard engineering attributes (grade 8.8 vs 10.9,
     SS316 vs SS304, SCH40 vs SCH80 ...) — this is what makes near-miss
     traps safe
  4. CLUSTER via union-find; iteratively drop the weakest internal edge of
     any cluster that still contains a conflicting pair (transitivity repair)
  5. Low-confidence clusters get flagged for human review (governance)
"""
from collections import defaultdict

import numpy as np
from rapidfuzz import fuzz

from normalize import MIN_ATTRS

# rows per similarity-matrix chunk — bounds peak memory on large blocks
_CHUNK = 256


def embed(texts, model_name="all-MiniLM-L6-v2"):
    """Embedding backend. Falls back to char-ngram TF-IDF when the model
    cannot load (offline / no external downloads allowed)."""
    import os
    # CPU inference: macOS Metal (MPS) has crashed the demo server under
    # repeated sessions; 400 rows encode in ~2s on CPU anyway.
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name, device="cpu")
        emb = model.encode(texts, normalize_embeddings=True,
                           show_progress_bar=False)
        return np.asarray(emb), f"sentence-transformers/{model_name} (cpu)"
    except Exception as e:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)
        X = normalize(vec.fit_transform(texts))
        return np.asarray(X.todense()), f"tfidf-fallback ({type(e).__name__})"
    # for millions of rows, replace the dense dot product with a FAISS ANN index


def _inch_compatible(a, b):
    """Attr-drop tolerant: equal, or one side a subset of the other."""
    sa, sb = set(a), set(b)
    return sa <= sb or sb <= sa


def _values_agree(key, va, vb):
    if key == "inch":
        return _inch_compatible(va, vb)
    return va == vb


def record_complete(r):
    """A record is auto-mergeable only if it carries its family's identity
    attributes. Ambiguous rows go to human review instead."""
    t, at = r["_type"], r["_attrs"]
    for k in MIN_ATTRS.get(t, ["__none__"]):
        if k not in at:
            return False
    # stainless fasteners carry identity in material (SS316/SS304);
    # carbon-steel fasteners carry it in grade (8.8 vs 10.9, B7 vs B16)
    if t in ("hex bolt", "hex nut", "socket head cap screw"):
        if at.get("material") in ("SS316", "SS304"):
            pass
        elif "grade" not in at:
            return False
    return True


def pair_verdict(a, b, sim):
    """Decide a candidate pair. Returns (is_match, confidence, reason)."""
    conflicts = []
    shared, missing = 0, 0
    for key, va in a["_attrs"].items():
        if key in b["_attrs"]:
            shared += 1
            if not _values_agree(key, va, b["_attrs"][key]):
                conflicts.append(key)
        else:
            missing += 1
    for key in b["_attrs"]:
        if key not in a["_attrs"]:
            missing += 1
    if a["_type"] != "unknown" and b["_type"] != "unknown" and a["_type"] != b["_type"]:
        conflicts.append("type")
    if a["_cat"] != b["_cat"]:
        conflicts.append("category")
    if conflicts:
        return False, sim, "veto:" + ",".join(sorted(set(conflicts)))

    # safety gate: both rows must carry their family's identity attributes.
    # A bolt missing its grade is ambiguous against same-family variants
    # (8.8 vs 10.9) — never auto-merge; surface for human review instead.
    if not (record_complete(a) and record_complete(b)):
        return False, sim, "review:insufficient-attributes"

    # no conflict: combine semantic similarity with attribute evidence
    attr_frac = shared / (shared + missing) if (shared + missing) else 0.0
    score = 0.55 * sim + 0.30 * attr_frac + 0.15 * (fuzz.token_sort_ratio(a["_norm"], b["_norm"]) / 100)
    if sim >= 0.85:
        return True, score, "match:high-sim"
    if score >= 0.62 and sim >= 0.45:
        return True, score, "match"
    # strong semantic match with at least one shared hard attribute
    if sim >= 0.78 and shared >= 1:
        return True, score, "match:sim+attr"
    return False, score, f"no-match:score={score:.2f},sim={sim:.2f}"


def match_all(records, sim_floor=0.40, top_k=128):
    """Returns (matches, rejects, embedding_backend_info).

    Candidates per record are bounded (top_k strongest neighbors) and the
    block's similarity matrix is computed in row chunks, so a large
    single-category upload costs O(n·top_k) verdicts and O(n·chunk)
    memory instead of a dense n x n matrix. With top_k >= the largest
    category block (128 > every block in the benchmark data) the pair set
    and enumeration order are exactly those of the original full upper-
    triangle pass — outputs are byte-identical (verified).
    """
    texts = [r["_norm"] for r in records]
    emb, emb_info = embed(texts)

    blocks = defaultdict(list)
    for i, r in enumerate(records):
        blocks[r["_cat"]].append(i)

    matches, vetoes, reviews = [], [], []
    seen = set()  # (a, b) with a < b — each pair verdicted exactly once
    for idxs in blocks.values():
        n = len(idxs)
        if n < 2:
            continue
        M = emb[idxs]
        for start in range(0, n, _CHUNK):
            stop = min(start + _CHUNK, n)
            sims = M[start:stop] @ M.T          # chunk x block — bounded memory
            for ci in range(stop - start):
                ii = start + ci
                row = sims[ci]
                if n > top_k:  # bound the pair count only when it can bite
                    cand = np.sort(np.argpartition(-row, top_k)[:top_k])
                else:
                    cand = np.arange(n)
                for jj in cand:
                    if jj <= ii:
                        continue
                    s = float(row[jj])
                    if s < sim_floor:
                        continue
                    ia, ib = idxs[ii], idxs[jj]
                    pair = (ia, ib)
                    if pair in seen:
                        continue
                    seen.add(pair)
                    ok, conf, reason = pair_verdict(records[ia], records[ib], s)
                    rec = {
                        "a": ia, "b": ib, "sim": round(s, 4), "confidence": round(conf, 4),
                        "reason": reason,
                        "a_cpse": records[ia]["cpse"], "a_code": records[ia]["material_code"],
                        "a_desc": records[ia]["description"],
                        "b_cpse": records[ib]["cpse"], "b_code": records[ib]["material_code"],
                        "b_desc": records[ib]["description"],
                    }
                    if ok:
                        matches.append(rec)
                    elif reason.startswith("review"):
                        reviews.append(rec)
                    elif reason.startswith("veto"):
                        vetoes.append(rec)
    return matches, vetoes, reviews, emb_info


class DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def _has_conflict(records, members):
    for x in range(len(members)):
        for y in range(x + 1, len(members)):
            ok, _, reason = pair_verdict(records[members[x]], records[members[y]], 1.0)
            if not ok and reason.startswith("veto"):
                return True
    return False


def cluster(records, matches, max_iter=25):
    """Union-find + weakest-link repair of transitivity conflicts."""
    n = len(records)
    edges = sorted(((m["confidence"], m["a"], m["b"]) for m in matches), key=lambda e: -e[0])
    exclude = set()

    for _ in range(max_iter):
        dsu = DSU(n)
        for conf, a, b in edges:
            if (a, b) not in exclude:
                dsu.union(a, b)
        groups = defaultdict(list)
        for i in range(n):
            groups[dsu.find(i)].append(i)

        bad_groups = [g for g in groups.values() if len(g) > 1 and _has_conflict(records, g)]
        if not bad_groups:
            break
        removed = False
        for members in bad_groups:
            internal = [e for e in edges
                        if (e[1], e[2]) not in exclude
                        and e[1] in members and e[2] in members]
            if internal:
                weakest = min(internal, key=lambda e: e[0])
                exclude.add((weakest[1], weakest[2]))
                removed = True
        if not removed:
            break
    else:
        # loop exhausted max_iter without a clean break — rebuild final groups
        dsu = DSU(n)
        for conf, a, b in edges:
            if (a, b) not in exclude:
                dsu.union(a, b)
        groups = defaultdict(list)
        for i in range(n):
            groups[dsu.find(i)].append(i)

    multi = [sorted(g) for g in groups.values() if len(g) > 1]
    singles = [g[0] for g in groups.values() if len(g) == 1]

    # cluster confidence = weakest internal accepted edge
    edge_conf = {(m["a"], m["b"]): m["confidence"] for m in matches}
    cluster_conf = []
    for members in multi:
        mset = set(members)
        confs = [c for (a, b), c in edge_conf.items() if a in mset and b in mset]
        cluster_conf.append(min(confs) if confs else 0.5)
    return multi, singles, cluster_conf
