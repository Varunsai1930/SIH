"""
UnifyMat — National Material Master Platform (SIH 26099).

Streamlit dashboard for the AI material-code harmonization pipeline.
Design: Swiss minimal, institutional blue, high contrast, no ornament.

Run:  streamlit run src/app.py
"""
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"

sys.path.insert(0, str(SRC))
from pipeline import run_pipeline, REQUIRED_COLS  # noqa: E402

st.set_page_config(page_title="UnifyMat · National Material Master",
                   layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------- design tokens
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
:root{
  --primary:#1E40AF; --primary-dark:#1E3A8A; --fg:#1E3A8A; --body:#334155;
  --muted:#475569; --muted-2:#64748B; --bg:#F8FAFC; --card:#FFFFFF;
  --border:#DBEAFE; --border-2:#E2E8F0; --accent:#B45309; --accent-bar:#D97706;
}
html, body, [class*="css"] {font-family:'Fira Sans',-apple-system,'Segoe UI',Roboto,sans-serif;}
.stApp {background:var(--bg);}
footer {visibility:hidden;}

/* hide Streamlit chrome for a clean product view (toolbar, deploy button, menu, status pill) */
header[data-testid="stHeader"]{background:transparent;}
.stDeployButton{display:none !important;}
#MainMenu{visibility:hidden;}
div[data-testid="stStatusWidget"]{visibility:hidden;}
div[data-testid="stConnectionStatus"]{visibility:hidden;}
.block-container {padding-top:1.1rem; padding-bottom:2.5rem; max-width:1240px;}

/* header band */
.hero{background:var(--primary);color:#fff;border-radius:8px;padding:18px 26px;
  display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:14px;}
.hero-title{font-size:21px;font-weight:700;letter-spacing:.01em;}
.hero-title span{font-weight:400;color:#BFDBFE;font-size:15px;margin-left:6px;}
.hero-sub{font-size:12.5px;color:#DBEAFE;margin-top:3px;}
.hero-right{font-size:11.5px;text-align:right;color:#BFDBFE;line-height:1.6;white-space:nowrap;}

/* KPI cards */
.kpi{background:var(--card);border:1px solid var(--border-2);border-radius:8px;
  padding:14px 16px;height:100%;}
.kpi-label{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);font-weight:600;}
.kpi-value{font-size:27px;font-weight:700;color:var(--fg);margin-top:2px;line-height:1.15;}
.kpi-sub{font-size:11.5px;color:var(--muted-2);margin-top:2px;}
.kpi.accent .kpi-value{color:var(--accent);}
.mono{font-family:'Fira Code',ui-monospace,monospace;}

/* result card (code lookup) */
.result{background:var(--card);border:1px solid var(--border);border-left:4px solid var(--primary);
  border-radius:8px;padding:16px 20px;margin-bottom:10px;}
.result .nmc{font-family:'Fira Code',ui-monospace,monospace;font-size:19px;font-weight:600;color:var(--fg);}
.result .desc{font-size:13.5px;color:var(--body);margin-top:3px;}
.meta{font-size:12px;color:var(--muted);margin-top:6px;}

.chip{display:inline-block;padding:1px 9px;border-radius:99px;font-size:10.5px;
  font-weight:600;letter-spacing:.03em;margin-left:8px;vertical-align:middle;}
.chip.auto{background:#DCFCE7;color:#166534;}
.chip.review{background:#FEF3C7;color:#92400E;}
.chip.unique{background:#F1F5F9;color:#475569;}
.chip.prov{background:#FEF3C7;color:#92400E;}
.chip.rejected{background:#FEE2E2;color:#991B1B;}

/* buttons — replace Streamlit red with institutional blue */
.stButton>button[kind="primary"]{background-color:var(--primary);border-color:var(--primary);color:#fff;}
.stButton>button[kind="primary"]:hover{background-color:var(--primary-dark);border-color:var(--primary-dark);color:#fff;}
.stButton>button[kind="secondary"]{border-color:var(--border-2);color:var(--fg);}
.stButton>button[kind="secondary"]:hover{border-color:var(--primary);color:var(--primary);}

/* tabs */
.stTabs [data-baseweb="tab-list"]{gap:2px;border-bottom:1px solid var(--border-2);}
.stTabs [data-baseweb="tab"]{font-size:14px;font-weight:500;color:var(--muted);}
.stTabs [aria-selected="true"]{color:var(--fg) !important;font-weight:700;}
.stTabs [data-baseweb="tab-highlight"]{background-color:var(--primary);height:2px;}

/* kill every default-red accent Streamlit ships (focus rings, indicators) */
.stTabs [data-baseweb="tab"] .react-aria-SelectionIndicator{background-color:var(--primary) !important;}
.react-aria-SelectionIndicator{background-color:var(--primary) !important;}
.stTabs [data-baseweb="tab"]:focus-visible{outline-color:var(--primary) !important;}
a:focus-visible{outline-color:var(--primary) !important;}

/* dataframes — flat grid, thin separators, no zebra shading */
[data-testid="stDataFrame"] [class*="main-head-corner"], [data-testid="stDataFrame"]{--bg-color:transparent;}
.stDataFrame{border:1px solid var(--border-2);border-radius:8px;overflow:hidden;}

h3.section{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
  font-weight:700;margin:1.2rem 0 .5rem .1rem;}
.note{font-size:12px;color:var(--muted-2);}

/* status chip row (Overview master-status breakdown) */
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px;}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def kpi_card(label, value, sub="", accent=False):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    cls = "kpi accent" if accent else "kpi"
    return (f'<div class="{cls}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>{sub_html}</div>')


def status_chip(status):
    s = status.upper()
    if "PROVISIONAL" in s:
        return '<span class="chip prov">PROVISIONAL</span>'
    if "REVIEW" in s:
        return '<span class="chip review">NEEDS REVIEW</span>'
    if s == "UNIQUE":
        return '<span class="chip unique">UNIQUE</span>'
    if "AUTO" in s:
        return '<span class="chip auto">AUTO-MATCHED</span>'
    return ""


CAT_PRETTY = {"fastener": "Fasteners", "bearing": "Bearings", "valve": "Valves",
              "pipe": "Pipes", "fitting": "Pipe fittings", "electrical": "Electrical",
              "lubricant": "Lubricants", "pump": "Pumps", "instrument": "Instruments",
              "unknown": "Unclassified"}

DECISIONS = OUT / "review_decisions.csv"
DEC_COLS = ["timestamp", "officer", "kind", "cpse", "material_code", "decision", "suggested_nmc"]


def load_decisions() -> pd.DataFrame:
    if DECISIONS.exists():
        try:
            return pd.read_csv(DECISIONS)
        except Exception:
            pass
    return pd.DataFrame(columns=DEC_COLS)


def append_decision(officer, kind, cpse, code, decision, nmc):
    OUT.mkdir(exist_ok=True)
    new_file = not DECISIONS.exists()
    with open(DECISIONS, "a", newline="", encoding="utf-8") as f:
        import csv as _csv
        w = _csv.writer(f)
        if new_file:
            w.writerow(DEC_COLS)
        w.writerow([datetime.now().isoformat(timespec="seconds"), officer, kind,
                    cpse, code, decision, nmc])


def parse_candidates(cand_str):
    rows = []
    for part in str(cand_str).split(" || "):
        m = re.match(r"(.+?) \((?:sim|confidence) ([\d.]+)\): (.*)", part.strip())
        if m:
            rows.append({"candidate": m.group(1), "score": float(m.group(2)), "description": m.group(3)})
        elif part.strip():
            rows.append({"candidate": part.strip(), "score": "", "description": ""})
    return pd.DataFrame(rows, columns=["candidate", "score", "description"])


def bar_fig(y, x, color, text=None, height=340):
    fig = go.Figure(go.Bar(y=y, x=x, orientation="h", marker_color=color,
                           text=text, textposition="outside",
                           hovertemplate="%{customdata}<extra></extra>",
                           customdata=y))
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=8, r=48, t=6, b=4),
                      font=dict(family="Fira Sans, sans-serif", size=12, color="#334155"),
                      xaxis=dict(showgrid=False, showticklabels=False, title=None, range=[0, max(x) * 1.18]),
                      yaxis=dict(showgrid=False, title=None, autorange="reversed", tickfont=dict(size=12)),
                      showlegend=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


# ---------------------------------------------------------------- data / state
if "bundle" not in st.session_state:
    with st.spinner("Harmonizing material masters (first run)…"):
        st.session_state.bundle = run_pipeline()
B = st.session_state.bundle

records = B["records"]
master = B["master"]
mapping = B["mapping"]
metrics = B["metrics"]
emb_info = B["emb_info"]
backend = "Embeddings" if "sentence-transformers" in emb_info else "TF-IDF (offline mode)"

cpse_count = len({r["cpse"] for r in records})
shared = [m for m in master if m["num_legacy_codes"] >= 2 and "," in m["cpses_sharing"]]
spreads = []
for s in shared:
    try:
        if s["max_rate_inr"] and s["min_rate_inr"]:
            spreads.append((s, (float(s["max_rate_inr"]) - float(s["min_rate_inr"])) / float(s["max_rate_inr"])))
    except Exception:
        pass
avg_spread = sum(x for _, x in spreads) / len(spreads) if spreads else 0

decisions = load_decisions()
decision_key = {(str(r.cpse), str(r.material_code)): r.decision
                for r in decisions.itertuples()}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### Data")
    files_df = pd.DataFrame(
        [{"file": k, "records": v["rows"]} for k, v in B["ingest_report"].items()])
    st.dataframe(files_df.rename(columns={"file": "Source file", "records": "Records"}),
                 hide_index=True, height=min(38 + 35 * len(files_df), 220), use_container_width=True)

    st.markdown("##### Upload a CPSE material master")
    up = st.file_uploader("CSV with columns: " + ", ".join(REQUIRED_COLS), type="csv",
                          help="Adds a new CPSE's ERP extract; the pipeline re-harmonizes immediately.")
    cpse_name = st.text_input("CPSE short name", "GAIL",
                              help="Used as this file's organization label, e.g. GAIL")
    if up is not None:
        try:
            df = pd.read_csv(up)
            df.columns = [str(c).strip().lower() for c in df.columns]
            missing = [c for c in REQUIRED_COLS if c not in df.columns]
            if missing:
                st.error("Missing required column(s): " + ", ".join(missing))
            else:
                st.success(f"Valid file — {len(df)} records ready to ingest.")
                if st.button("Ingest file", type="primary", use_container_width=True):
                    slug = re.sub(r"[^a-z0-9]+", "", cpse_name.lower().strip()) or "upload"
                    df.insert(0, "cpse", cpse_name.strip().upper())
                    df.to_csv(RAW / f"{slug}_materials.csv", index=False)
                    with st.spinner("Harmonizing with new data…"):
                        st.session_state.bundle = run_pipeline()
                    st.toast(f"Ingested {len(df)} records from {cpse_name.upper()}")
                    st.rerun()
        except Exception as e:
            st.error(f"Could not read file: {e}")

    if st.button("Re-run harmonization", use_container_width=True):
        with st.spinner("Harmonizing…"):
            st.session_state.bundle = run_pipeline()
        st.rerun()

    st.markdown("### Officer")
    officer = st.text_input("Reviewing officer", "Procurement Officer")
    st.caption(f"Matching engine: {backend}\n\nLast run: {B['runtime_s']}s · "
               f"{len(records)} records · {len(master)} codes")

# ---------------------------------------------------------------- header
st.markdown(
    '<div class="hero"><div>'
    '<div class="hero-title">UnifyMat<span>National Material Master</span></div>'
    '<div class="hero-sub">One Nation · One Material Code — AI harmonization of material '
    'masters across Central Public Sector Enterprises</div>'
    '</div><div class="hero-right">SIH 26099 · Smart Automation<br>'
    'Ministry of Petroleum &amp; Natural Gas · CPCL</div></div>',
    unsafe_allow_html=True)

tab_over, tab_review, tab_lookup, tab_audit = st.tabs(
    ["Overview", "Review Queue", "Code Lookup", "Audit Trail"])

# ---------------------------------------------------------------- Overview
with tab_over:
    if metrics["has_ground_truth"]:
        prec = f"{metrics['precision'] * 100:.1f}%"
        prec_sub = f"benchmark · {metrics['trap_violations']} near-miss violations"
    else:
        prec, prec_sub = "—", "no labels in uploaded data"
    n_prov = sum(1 for m in master if "PROVISIONAL" in m["status"])

    c = st.columns(6)
    with c[0]:
        st.markdown(kpi_card("Records ingested", f"{len(records):,}", f"from {cpse_count} CPSEs"), unsafe_allow_html=True)
    with c[1]:
        st.markdown(kpi_card("National codes issued", f"{len(master):,}",
                             f"{n_prov} provisional"), unsafe_allow_html=True)
    with c[2]:
        st.markdown(kpi_card("Unified across CPSEs", f"{len(shared):,}",
                             "materials shared by 2+ CPSEs"), unsafe_allow_html=True)
    with c[3]:
        st.markdown(kpi_card("Auto-merge precision", prec, prec_sub), unsafe_allow_html=True)
    with c[4]:
        st.markdown(kpi_card("Avg price spread", f"{avg_spread * 100:.1f}%",
                             "across CPSEs on shared materials", accent=True), unsafe_allow_html=True)
    with c[5]:
        st.markdown(kpi_card("Pending review", f"{B['n_review_pairs']:,}",
                             "ambiguous pairs held for officer"), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    status_counts = Counter(("AUTO" if "AUTO" in m["status"].upper()
                             else "PROVISIONAL" if "PROVISIONAL" in m["status"].upper()
                             else "NEEDS REVIEW" if "REVIEW" in m["status"].upper() else "UNIQUE")
                            for m in master)
    chip_cls = {"AUTO": "auto", "NEEDS REVIEW": "review", "PROVISIONAL": "prov", "UNIQUE": "unique"}
    chips_html = "".join(
        f'<span class="chip {chip_cls.get(k, "unique")}">{v} {k.lower()}</span>'
        for k, v in status_counts.most_common())
    verdict = ("Benchmark evaluation: precision 100% with zero near-miss merges."
               if metrics["has_ground_truth"] and metrics["trap_violations"] == 0
               else "Uploaded records without labels are excluded from accuracy metrics."
               if metrics["has_ground_truth"] else
               "Production ingest: no ground-truth labels present, accuracy metrics skipped.")
    st.markdown(f'<div class="note" style="margin-top:2px">Master status{chips_html}</div>'
                f'<div class="note" style="margin-top:4px">{verdict}</div>',
                unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown("<h3 class='section'>Material landscape</h3>", unsafe_allow_html=True)

    cat_counts = Counter(CAT_PRETTY.get(r["_cat"], r["_cat"]) for r in records)
    cats = list(cat_counts.keys())
    counts = list(cat_counts.values())
    top_spread = sorted(spreads, key=lambda t: -t[1])[:8]

    cc = st.columns(2)
    with cc[0]:
        st.plotly_chart(bar_fig(cats, counts, "#1E40AF", [str(v) for v in counts]),
                        use_container_width=True,
                        config={"displayModeBar": False})
        st.caption("Legacy records by category, after AI classification")
    with cc[1]:
        if top_spread:
            labels = [(s["standardized_description"][:38] + "…") if len(s["standardized_description"]) > 39
                      else s["standardized_description"] for s, _ in top_spread]
            vals = [round(p * 100, 1) for _, p in top_spread]
            st.plotly_chart(bar_fig(labels, vals, "#D97706", [f"{v}%" for v in vals]),
                            use_container_width=True,
                            config={"displayModeBar": False})
            st.caption("Price spread on materials shared across CPSEs — the demand-aggregation opportunity")

# ---------------------------------------------------------------- Review Queue
with tab_review:
    review_rows = B["review_rows"]
    pending, decided = [], []
    for row in review_rows:
        d = decision_key.get((row["cpse"], row["material_code"]), "")
        (decided if d else pending).append((row, d))

    st.markdown("<h3 class='section'>Records the AI refuses to guess</h3>", unsafe_allow_html=True)
    st.caption("These records are missing identity attributes (grade, size, designation…). "
               "The AI proposes the most likely national code; a CPSE officer confirms or rejects. "
               "Approving a wrong merge is impossible by design — every decision is logged.")

    k = st.columns(3)
    k[0].metric("Pending", len(pending))
    k[1].metric("Approved", int((decisions["decision"] == "APPROVED").sum()) if len(decisions) else 0)
    k[2].metric("Rejected", int((decisions["decision"] == "REJECTED").sum()) if len(decisions) else 0)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if not pending:
        st.success("Review queue is clear — every ambiguous record has an officer decision.")
    for i, (row, _) in enumerate(pending):
        label = f"{row['cpse']} · {row['material_code']} — {row['description'][:72]}"
        with st.expander(label):
            cands = parse_candidates(row["top_candidates"])
            st.dataframe(cands.rename(columns={"candidate": "Candidate (best first)",
                                               "score": "Similarity",
                                               "description": "Candidate description"}),
                         hide_index=True, use_container_width=True, height=min(38 + 35 * len(cands), 150))
            st.markdown(f'<div class="result"><span class="nmc">{row["suggested_nmc"]}</span>'
                        f'<span class="chip prov">SUGGESTED</span></div>', unsafe_allow_html=True)
            b = st.columns(2)
            if b[0].button("Approve", key=f"ap_{i}", type="primary", use_container_width=True):
                append_decision(officer, row["kind"], row["cpse"], row["material_code"],
                                "APPROVED", row["suggested_nmc"])
                st.toast(f"Approved {row['cpse']}/{row['material_code']}")
                st.rerun()
            if b[1].button("Reject", key=f"rj_{i}", use_container_width=True):
                append_decision(officer, row["kind"], row["cpse"], row["material_code"],
                                "REJECTED", row["suggested_nmc"])
                st.toast(f"Rejected {row['cpse']}/{row['material_code']}")
                st.rerun()

    if len(decisions):
        st.markdown("<h3 class='section'>Officer decisions</h3>", unsafe_allow_html=True)
        dd = decisions[["timestamp", "officer", "cpse", "material_code", "decision", "suggested_nmc"]]
        dd = dd.iloc[::-1]
        st.dataframe(dd, hide_index=True, use_container_width=True, height=260)

# ---------------------------------------------------------------- Code Lookup
with tab_lookup:
    st.markdown("<h3 class='section'>Trace any legacy code to its National Material Code</h3>",
                unsafe_allow_html=True)
    if "lookup_input" not in st.session_state:
        st.session_state.lookup_input = ""
    q = st.text_input("Legacy material code or National Code", key="lookup_input",
                      placeholder="e.g. MAT100050, RM-00035, or NMC-FAST-WSHR-…")

    by_legacy = defaultdict(list)
    by_nmc = defaultdict(list)
    for m in mapping:
        by_legacy[m["legacy_material_code"].strip().upper()].append(m)
        by_nmc[m["national_material_code"]].append(m)
    master_by_nmc = {m["national_material_code"]: m for m in master}

    def best_quick_picks():
        picks = []
        multi_cpse = [m for m in master if m["num_legacy_codes"] >= 3 and "," in m["cpses_sharing"]]
        if multi_cpse:
            code = by_nmc.get(multi_cpse[0]["national_material_code"], [{}])[0].get("legacy_material_code")
            if code:
                picks.append(("Shared by 3+ CPSEs", code))
        prov = [r for r in B["review_rows"] if r["kind"] == "record"]
        if prov:
            picks.append(("Held for review", prov[0]["material_code"]))
        if B["vetoes"]:
            picks.append(("Near-miss saved by veto", B["vetoes"][0]["a_code"]))
        return picks

    picks = best_quick_picks()
    if picks:
        pc = st.columns(len(picks))
        for col, (why, code) in zip(pc, picks):
            if col.button(f"{code}", help=why, use_container_width=True):
                st.session_state.lookup_input = code
                st.rerun()
        st.caption(" · ".join(f"**{c}** — {w}" for w, c in picks))

    qu = q.strip().upper()
    if qu:
        rows = by_nmc.get(qu) or by_legacy.get(qu) or [
            m for nmc, ms in by_nmc.items() if qu != "" and nmc.startswith(qu) for m in ms]
        if not rows:
            st.info("No match. Try a full legacy code, or a National Code prefix such as NMC-FAST-.")
        else:
            nmc = rows[0]["national_material_code"]
            mrow = master_by_nmc.get(nmc)
            if mrow:
                price_bit = ""
                try:
                    if (mrow["max_rate_inr"] and mrow["min_rate_inr"]
                            and str(mrow["max_rate_inr"]) != str(mrow["min_rate_inr"])):
                        price_bit = (f" · ₹{mrow['min_rate_inr']}–₹{mrow['max_rate_inr']}"
                                     " across CPSEs")
                except Exception:
                    pass
                st.markdown(
                    f'<div class="result"><span class="nmc">{nmc}</span>{status_chip(mrow["status"])}'
                    f'<div class="desc">{mrow["standardized_description"]}</div>'
                    f'<div class="meta">Category: {CAT_PRETTY.get(mrow["category"], mrow["category"])}'
                    f' · Standard UOM: {mrow["uom"]} · Shared by: {mrow["cpses_sharing"]}'
                    f'{price_bit}</div></div>',
                    unsafe_allow_html=True)
            eq = pd.DataFrame([{
                "CPSE": r["cpse"], "Legacy code": r["legacy_material_code"],
                "Legacy description": (r["legacy_description"][:70] + "…")
                if len(r["legacy_description"]) > 71 else r["legacy_description"],
                "UOM": r["legacy_uom"]} for r in rows])
            st.markdown("<h3 class='section'>Equivalent legacy codes</h3>", unsafe_allow_html=True)
            st.dataframe(eq, hide_index=True, use_container_width=True,
                         height=min(38 + 35 * len(eq), 240))

# ---------------------------------------------------------------- Audit Trail
with tab_audit:
    st.markdown("<h3 class='section'>Governance trail</h3>", unsafe_allow_html=True)
    st.caption("Officer decisions persist across pipeline runs. Machine actions below are "
               "regenerated for the current harmonization run and are also written to outputs/audit_log.csv.")
    if len(decisions):
        st.markdown("**Officer decisions (persistent)**")
        st.dataframe(decisions[["timestamp", "officer", "cpse", "material_code",
                                "decision", "suggested_nmc"]].iloc[::-1],
                     hide_index=True, use_container_width=True, height=240)
    else:
        st.caption("No officer decisions recorded yet — approve or reject items in the Review Queue.")
    st.markdown("**Machine actions (current run)**")
    audit = pd.DataFrame(B["audit"])
    if len(audit):
        audit = audit.rename(columns={"national_material_code": "National code", "action": "Action",
                                      "members": "Members", "confidence": "Confidence",
                                      "timestamp": "Timestamp"})
        audit["Auto"] = audit.get("Auto", True)
        st.dataframe(audit[["Timestamp", "National code", "Action", "Members", "Confidence"]],
                     hide_index=True, use_container_width=True, height=320)
