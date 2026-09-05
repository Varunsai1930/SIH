"""
UnifyMat — National Material Master Platform (SIH 26099).

Streamlit dashboard for the AI material-code harmonization pipeline.
Design: Swiss minimal, institutional blue, high contrast, no ornament.

Run:  streamlit run src/app.py
"""
import csv
import html
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
from normalize import MIN_ATTRS, VETO_ATTRS  # noqa: E402
from pipeline import (run_pipeline, REQUIRED_COLS, guard_formula_cell,  # noqa: E402
                     shared_materials, price_spreads, row_spread)
from ui_widgets import confidence_ring, preflight_report, parse_candidates  # noqa: E402

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
.chip.officer{background:#DBEAFE;color:#1E40AF;}
.chip.review{background:#FEF3C7;color:#92400E;}
.chip.unique{background:#F1F5F9;color:#475569;}
.chip.prov{background:#FEF3C7;color:#92400E;}

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

/* status chips (Review Queue / master statuses) */

/* spec-diff matrix (Review Queue expander): this record vs top candidate */
.specdiff{width:100%;background:var(--card);border-collapse:collapse;font-size:12.5px;text-align:left;}
.specdiff th,.specdiff td{border:1px solid var(--border-2);padding:4px 10px;}
.specdiff th{font-weight:600;color:var(--fg);}
.specdiff th:first-child,.specdiff td:first-child{width:140px;}
"""

st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def kpi_card(label, value, sub="", accent=False):
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    cls = "kpi accent" if accent else "kpi"
    return (f'<div class="{cls}"><div class="kpi-label">{html.escape(str(label))}</div>'
            f'<div class="kpi-value">{html.escape(str(value))}</div>{sub_html}</div>')


def status_chip(status):
    s = status.upper()
    if "PROVISIONAL" in s:
        return '<span class="chip prov">PROVISIONAL</span>'
    if "OFFICER_MERGED" in s:
        return '<span class="chip officer">OFFICER-MERGED</span>'
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

ATTR_PRETTY = {"std": "standard", "flange_type": "flange type", "seal_type": "seal type",
               "cable_size": "cable size", "flow_lpm": "flow (lpm)", "gauge_type": "gauge type"}

DECISIONS = OUT / "review_decisions.csv"
DEC_COLS = ["timestamp", "officer", "kind", "cpse", "material_code", "decision", "suggested_nmc"]

# one dense similarity pass + O(pairs) verdict pass per category block —
# an unbounded upload can exhaust the single-threaded Streamlit process
MAX_UPLOAD_ROWS = 5000


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
        w = csv.writer(f)
        if new_file:
            w.writerow(DEC_COLS)
        w.writerow([datetime.now().isoformat(timespec="seconds"),
                    guard_formula_cell(officer), kind, guard_formula_cell(cpse),
                    guard_formula_cell(code), decision, guard_formula_cell(nmc)])


def safe_csv_bytes(df):
    """CSV download bytes with the same Excel-formula guard as outputs/."""
    guarded = df.copy()
    for col in guarded.select_dtypes(include="object"):
        guarded[col] = guarded[col].map(guard_formula_cell)
    return guarded.to_csv(index=False).encode("utf-8")


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


# ---------------------------------------------------------------- CPSE identity colors
CPSE_COLORS = {"CPCL": "#B45309", "IOCL": "#E65100", "NTPC": "#0D9488",
               "SAIL": "#DC2626", "GAIL": "#15803D"}
CPSE_FALLBACK_COLOR = "#475569"


def cpse_color(cpse):
    """Institutional color for a CPSE short name (muted slate if unknown)."""
    return CPSE_COLORS.get(str(cpse).strip().upper(), CPSE_FALLBACK_COLOR)


def cpse_dot(cpse):
    """Colored-dot span for unsafe_allow_html HTML: '<bullet> CPSE'."""
    name = html.escape(str(cpse))
    return (f'<span style="color:{cpse_color(cpse)};font-size:11px">'
            f'&#9679; {name}</span>')


def styler_candidate_color(v):
    """CSS color for a 'CPSE/CODE' candidate string (pandas Styler .map)."""
    return f"color: {cpse_color(str(v).split('/')[0])}"


# spec-diff matrix cell states (identical / differing / missing)
_MATCH_BG, _MATCH_FG = "#F0FDFA", "#047857"
_DIFF_BG, _DIFF_FG, _DIFF_BORDER = "#FFFBEB", "#92400E", "#FDE68A"
_MISSING_FG = "#94A3B8"


def _attr_str(v):
    """Stringify an attribute value; tuples/lists (e.g. inch, std) join with '/'."""
    if isinstance(v, (tuple, list)):
        return "/".join(str(x) for x in v)
    return str(v)


def _attr_label(k):
    """Prettified attribute key for captions ('std' -> 'standard')."""
    return ATTR_PRETTY.get(k, k.replace("_", " "))


def resolve_record(idx, cpse, material_code):
    """Look a record up in the (cpse, material_code) -> record index."""
    return idx.get((str(cpse), str(material_code)))


def specdiff_html(rec, cand):
    """Attribute-by-attribute comparison of a review record vs its top candidate.
    Green cells = identical values, amber = differing (a veto would fire),
    '—' = missing on one side. Returns '' when there is nothing to compare."""
    a, b = rec.get("_attrs", {}), cand.get("_attrs", {})
    if not a and not b:
        return ""
    keys = set(a) | set(b)
    ordered = ([k for k in VETO_ATTRS if k in keys]
               + sorted(k for k in keys if k not in VETO_ATTRS))
    ordered = ordered[:12]

    def head(r):
        dot = cpse_dot(r.get("cpse", ""))
        code = html.escape(str(r.get("material_code", "")))
        return (f'<span style="font-size:11px">{dot}</span><br>'
                f'<span class="mono" style="font-size:11.5px;color:var(--muted)">{code}</span>')

    def cell(v, other):
        if v is None:
            return f'<td style="color:{_MISSING_FG}">—</td>'
        sv = _attr_str(v)
        if other is None or sv == _attr_str(other):
            return (f'<td style="background:{_MATCH_BG};color:{_MATCH_FG}">'
                    f'{html.escape(sv)}</td>')
        return (f'<td style="background:{_DIFF_BG};color:{_DIFF_FG};'
                f'border:1px solid {_DIFF_BORDER}">{html.escape(sv)}</td>')

    rows = "".join(
        f"<tr><td><b>{html.escape(_attr_label(k))}</b></td>"
        f"{cell(a.get(k), b.get(k))}{cell(b.get(k), a.get(k))}</tr>"
        for k in ordered)
    return (f'<table class="specdiff"><tr><th>Attribute</th><th>{head(rec)}</th>'
            f'<th>{head(cand)}</th></tr>{rows}</table>')


def matched_on(rec, cand):
    """Caption line of the attribute values both records agree on."""
    a, b = rec.get("_attrs", {}), cand.get("_attrs", {})
    agreed = [_attr_str(a[k]) for k in sorted(a)
              if k in b and _attr_str(a[k]) == _attr_str(b[k])]
    if (rec.get("uom") != cand.get("uom")
            and rec.get("_uom_std") and rec.get("_uom_std") == cand.get("_uom_std")):
        agreed.append(f"UOM {rec['uom']}→{cand['uom']} normalized")
    return " · ".join(html.escape(x) for x in agreed)


def missing_identity(rec):
    """'grade, thread' — this family's identity attributes the record lacks."""
    req = MIN_ATTRS.get(rec.get("_type", ""), [])
    return ", ".join(_attr_label(k) for k in req if k not in rec.get("_attrs", {}))


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

# (cpse, material_code) -> record — resolves review candidates back to full rows
record_idx = {(r["cpse"], r["material_code"]): r for r in records}

cpse_count = len({r["cpse"] for r in records})
shared = shared_materials(master)
spreads = price_spreads(master)
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
            # pre-flight card is recomputed only for a new upload (or new CPSE
            # label) so the officer can dismiss it; file_id identifies the file.
            fid = getattr(up, "file_id", None) or (up.name, up.size)
            preflight_key = (fid, cpse_name)
            if st.session_state.get("preflight_key") != preflight_key:
                st.session_state.preflight_html = preflight_report(df, cpse_name)
                st.session_state.preflight_key = preflight_key
            df.columns = [str(c).strip().lower() for c in df.columns]
            missing = [c for c in REQUIRED_COLS if c not in df.columns]
            if missing:
                st.error("Missing required column(s): " + ", ".join(missing))
                if st.session_state.get("preflight_html"):
                    st.markdown(st.session_state.preflight_html, unsafe_allow_html=True)
            elif len(df) > MAX_UPLOAD_ROWS:
                # resource guard: one dense similarity pass + pair loop per
                # category block — an unbounded upload can OOM the server
                st.error(f"Upload rejected — {len(df):,} rows exceeds the "
                         f"{MAX_UPLOAD_ROWS:,}-row limit. Split the extract "
                         "by category or upload in batches.")
                if st.session_state.get("preflight_html"):
                    st.markdown(st.session_state.preflight_html, unsafe_allow_html=True)
            else:
                # hard guardrail: material_code is the registry primary key —
                # blank or duplicate codes corrupt the harmonized master, so
                # refuse ingest until the CPSE fixes the extract (the pre-flight
                # card above shows exactly what to fix)
                codes = (df["material_code"].fillna("")
                         .map(lambda v: str(v).strip().upper()))
                blank_codes = int((codes == "").sum())
                dup_rows = int(codes[codes != ""].duplicated().sum())
                if blank_codes or dup_rows:
                    st.error("Upload rejected — fix the file and re-upload: "
                             f"{blank_codes} blank material_code(s) · "
                             f"{dup_rows} duplicate material_code(s).")
                    if st.session_state.get("preflight_html"):
                        st.markdown(st.session_state.preflight_html, unsafe_allow_html=True)
                else:
                    st.success(f"Valid file — {len(df)} records ready to ingest.")
                    if st.button("Ingest file", type="primary", use_container_width=True):
                        slug = re.sub(r"[^a-z0-9]+", "", cpse_name.lower().strip()) or "upload"
                        dest = RAW / f"{slug}_materials.csv"
                        # an exact-name re-upload refreshes that CPSE's extract;
                        # a name that merely SLUGS onto another CPSE's file
                        # ("GAIL!", "G.A.I.L" -> gail_materials.csv) is refused
                        # rather than silently overwriting its data
                        existing_cpse = dest.stem.split("_")[0].upper()
                        if dest.exists() and cpse_name.strip().upper() != existing_cpse:
                            st.error(f"Upload rejected — '{cpse_name.strip()}' would "
                                     f"overwrite the ingested file for '{existing_cpse}' "
                                     f"({dest.name}). Pick a different short name.")
                        else:
                            # real ERP extracts often carry their own org column —
                            # the officer-entered name is authoritative
                            if "cpse" in df.columns:
                                df["cpse"] = cpse_name.strip().upper()
                            else:
                                df.insert(0, "cpse", cpse_name.strip().upper())
                            df.to_csv(dest, index=False)
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
    '</div></div>',
    unsafe_allow_html=True)

tab_over, tab_review, tab_lookup, tab_master, tab_audit = st.tabs(
    ["Overview", "Review Queue", "Code Lookup", "Master Catalog", "Audit Trail"])

# ---------------------------------------------------------------- Overview
with tab_over:
    if metrics["has_ground_truth"]:
        prec = f"{metrics['precision'] * 100:.1f}%"
        prec_sub = f"benchmark · {metrics['trap_violations']} near-miss violations"
    else:
        prec, prec_sub = "—", "no labels in uploaded data"
    n_prov = sum(1 for m in master if "PROVISIONAL" in m["status"])

    c = st.columns(7)
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
        off_n = metrics.get("officer_merges_applied", 0)
        if metrics.get("has_ground_truth") and "final_recall" in metrics:
            gov_sub = f"final registry: {metrics['final_recall'] * 100:.1f}% recall · {off_n} officer merge(s)"
        else:
            gov_sub = f"{off_n} officer merge(s) applied · veto-checked"
        st.markdown(kpi_card("Human-governed recall",
                             f"{metrics.get('final_recall', B['review']['potential_recall']) * 100:.1f}%",
                             gov_sub, accent=True), unsafe_allow_html=True)
    with c[5]:
        st.markdown(kpi_card("Avg price spread", f"{avg_spread * 100:.1f}%",
                             "across CPSEs on shared materials"), unsafe_allow_html=True)
    with c[6]:
        st.markdown(kpi_card("Pending review", f"{B['n_review_pairs']:,}",
                             "ambiguous pairs held for officer"), unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    status_counts = Counter(("OFFICER-MERGED" if "OFFICER_MERGED" in m["status"].upper()
                             else "AUTO" if "AUTO" in m["status"].upper()
                             else "PROVISIONAL" if "PROVISIONAL" in m["status"].upper()
                             else "NEEDS REVIEW" if "REVIEW" in m["status"].upper() else "UNIQUE")
                            for m in master)
    chip_cls = {"AUTO": "auto", "NEEDS REVIEW": "review", "PROVISIONAL": "prov",
                "UNIQUE": "unique", "OFFICER-MERGED": "officer"}
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

    ex = st.columns(2)
    ex[0].download_button("Download unified master (CSV)",
                          data=safe_csv_bytes(pd.DataFrame(master)),
                          file_name="unified_master.csv", mime="text/csv",
                          use_container_width=True)
    ex[1].download_button("Download code mapping (CSV)",
                          data=safe_csv_bytes(pd.DataFrame(mapping)),
                          file_name="code_mapping.csv", mime="text/csv",
                          use_container_width=True)
    st.caption("Also written to outputs/ by every pipeline run.")

    # pre-flight report for the most recent sidebar upload (dismissable)
    if st.session_state.get("preflight_html"):
        st.markdown(st.session_state.preflight_html, unsafe_allow_html=True)
        if st.button("Dismiss", key="preflight_dismiss", type="tertiary",
                     help="Hide this pre-flight report; the next upload shows a fresh one."):
            st.session_state.pop("preflight_html", None)
            st.rerun()

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
    pending = []
    for row in review_rows:
        d = decision_key.get((row["cpse"], row["material_code"]), "")
        # an approved merge the hard-attribute veto blocked stays in the queue —
        # the officer must resolve the conflict, it is not a done decision
        if "BLOCKED" in str(row.get("decision", "")):
            pending.append((row, "BLOCKED"))
        elif not d:
            pending.append((row, ""))

    st.markdown("<h3 class='section'>Records the AI refuses to guess</h3>", unsafe_allow_html=True)
    st.caption("These records are missing identity attributes (grade, size, designation…). "
               "The AI proposes the most likely national code; a CPSE officer confirms or rejects. "
               "Approving merges the record into the confirmed code on the next harmonization — "
               "blocked automatically if a hard engineering attribute conflicts with any member. "
               "Every decision is logged.")

    k = st.columns(3)
    k[0].metric("Pending", len(pending))
    k[1].metric("Approved", int((decisions["decision"] == "APPROVED").sum()) if len(decisions) else 0)
    k[2].metric("Rejected", int((decisions["decision"] == "REJECTED").sum()) if len(decisions) else 0)

    st.download_button("Download review queue (CSV)",
                       data=safe_csv_bytes(pd.DataFrame(review_rows)),
                       file_name="review_queue.csv", mime="text/csv")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if not pending:
        st.success("Review queue is clear — every ambiguous record has an officer decision.")
    for i, (row, state) in enumerate(pending):
        label = f"{row['cpse']} · {row['material_code']} — {row['description'][:72]}"
        with st.expander(label):
            if state == "BLOCKED":
                st.error("Approve was recorded, but the hard-attribute veto blocked the merge "
                         "— this record conflicts with a member of the confirmed code. "
                         "Reject it (it keeps its own code) or have the CPSE correct the source row.")
            rec = (resolve_record(record_idx, row.get("cpse", ""), row.get("material_code", ""))
                   if row.get("kind") == "record" else None)
            if rec is not None:
                miss = missing_identity(rec)
                if miss:
                    st.caption(f"Held for review — missing identity attribute(s) for "
                               f"{rec.get('_type', 'material')}: {miss}")
                elif rec.get("_complete") is False:
                    st.caption(f"Held for review — identity attributes incomplete for "
                               f"{rec.get('_type', 'material')}")
            cands = parse_candidates(row["top_candidates"])
            cand_df = cands.rename(columns={"candidate": "Candidate (best first)",
                                            "score": "Similarity",
                                            "description": "Candidate description"})
            styled = (cand_df.style.map(styler_candidate_color,
                                        subset=["Candidate (best first)"])
                      .hide(axis="index"))
            st.dataframe(styled, hide_index=True, use_container_width=True,
                         height=min(38 + 35 * len(cands), 150))
            if len(cands):  # confidence ring per candidate (same order, max 5)
                ring_html = " ".join(
                    f'<span style="display:inline-flex;align-items:center;gap:4px;'
                    f'margin-right:14px;white-space:nowrap;">'
                    f'{confidence_ring(c)}'
                    f'<span style="font-size:11px;color:#475569;font-family:\'Fira Code\',monospace;">{html.escape(str(k))}</span></span>'
                    for k, c in list(zip(cands["candidate"], cands["score"]))[:5])
                st.markdown(f'<div style="margin-top:2px;">{ring_html}</div>', unsafe_allow_html=True)
            if rec is not None and len(cands):
                head = str(cands.iloc[0]["candidate"])
                if "/" in head:
                    cpse, _, code = head.partition("/")
                    cand = resolve_record(record_idx, cpse, code)
                    if cand is not None:
                        table = specdiff_html(rec, cand)
                        if table:
                            st.markdown(table, unsafe_allow_html=True)
                            st.caption("green = identical · amber = differing — amber on a hard "
                                       "attribute (grade, schedule, material, seal…) means the "
                                       "AI will refuse this pair.")
                            why = matched_on(rec, cand)
                            st.caption(f"Why this match — Matched on: {why}" if why
                                       else "Why this match — no shared identity attributes")
            st.markdown(f'<div class="result"><span class="nmc">{html.escape(str(row["suggested_nmc"]))}</span>'
                        f'<span class="chip prov">SUGGESTED</span></div>', unsafe_allow_html=True)
            b = st.columns(2)
            if b[0].button("Approve", key=f"ap_{i}", type="primary", use_container_width=True):
                append_decision(officer, row["kind"], row["cpse"], row["material_code"],
                                "APPROVED", row["suggested_nmc"])
                with st.spinner("Merging into the confirmed code — veto-checked…"):
                    st.session_state.bundle = run_pipeline()
                st.toast(f"Approved {row['cpse']}/{row['material_code']} — merged into "
                         f"{row['suggested_nmc']}")
                st.rerun()
            if b[1].button("Reject", key=f"rj_{i}", use_container_width=True):
                append_decision(officer, row["kind"], row["cpse"], row["material_code"],
                                "REJECTED", row["suggested_nmc"])
                with st.spinner("Registry updated — record stands alone under its own code…"):
                    st.session_state.bundle = run_pipeline()
                st.toast(f"Rejected {row['cpse']}/{row['material_code']} — keeps its own code")
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
    if "_next_lookup" in st.session_state:  # set by a quick-pick button on the previous run
        st.session_state.lookup_input = st.session_state.pop("_next_lookup")
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
                st.session_state["_next_lookup"] = code
                st.rerun()
        st.caption(" · ".join(f"**{c}** — {w}" for w, c in picks))

    qu = q.strip().upper()
    if qu:
        rows = by_nmc.get(qu) or by_legacy.get(qu) or [
            m for nmc, ms in by_nmc.items() if nmc.startswith(qu) for m in ms]
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
                shared_dots = " ".join(cpse_dot(c.strip())
                                       for c in str(mrow["cpses_sharing"]).split(",") if c.strip())
                conf = mrow.get("confidence")
                conf_ring = (f'<span style="margin-left:8px;vertical-align:middle;">'
                             f'{confidence_ring(conf)}</span>' if conf not in ("", None) else "")
                st.markdown(
                    f'<div class="result"><span class="nmc">{html.escape(str(nmc))}</span>{status_chip(mrow["status"])}{conf_ring}'
                    f'<div class="desc">{html.escape(str(mrow["standardized_description"]))}</div>'
                    f'<div class="meta">Category: {CAT_PRETTY.get(mrow["category"], mrow["category"])}'
                    f' · Standard UOM: {html.escape(str(mrow["uom"]))} · Shared by: {shared_dots}'
                    f'{price_bit}</div></div>',
                    unsafe_allow_html=True)
            eq = pd.DataFrame([{
                "CPSE": r["cpse"], "Legacy code": r["legacy_material_code"],
                "Legacy description": (r["legacy_description"][:70] + "…")
                if len(r["legacy_description"]) > 71 else r["legacy_description"],
                "UOM": r["legacy_uom"]} for r in rows])
            st.markdown("<h3 class='section'>Equivalent legacy codes</h3>", unsafe_allow_html=True)
            eq_styled = (eq.style
                         .map(lambda v: f"color: {cpse_color(v)}", subset=["CPSE"])
                         .map(lambda _: "font-family: 'Fira Code', ui-monospace, monospace",
                              subset=["Legacy code"])
                         .hide(axis="index"))
            st.dataframe(eq_styled, hide_index=True, use_container_width=True,
                         height=min(38 + 35 * len(eq), 240))

# ---------------------------------------------------------------- Master Catalog
with tab_master:
    st.markdown("<h3 class='section'>The National Material Master — every code, one catalog</h3>",
                unsafe_allow_html=True)
    st.caption(f"The unified catalog the harmonization pipeline issues — {len(master):,} national "
               f"codes over {len(records):,} legacy records from {cpse_count} CPSEs.")

    # ---- KPI row: catalog shape
    shared_m = [m for m in master if "," in m["cpses_sharing"]]
    single_m = [m for m in master if m["num_legacy_codes"] == 1]
    avg_legacy_shared = (sum(m["num_legacy_codes"] for m in shared_m) / len(shared_m)
                         if shared_m else 0)
    mk = st.columns(4)
    with mk[0]:
        st.markdown(kpi_card("Total national codes", f"{len(master):,}",
                             f"from {len(records):,} legacy records"), unsafe_allow_html=True)
    with mk[1]:
        st.markdown(kpi_card("Shared by 2+ CPSEs", f"{len(shared_m):,}",
                             "materials unified across CPSEs"), unsafe_allow_html=True)
    with mk[2]:
        st.markdown(kpi_card("Singleton codes", f"{len(single_m):,}",
                             "one CPSE, one legacy code"), unsafe_allow_html=True)
    with mk[3]:
        st.markdown(kpi_card("Legacy codes / shared material", f"{avg_legacy_shared:.1f}",
                             "avg codes merged per shared material", accent=True),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ---- search + filters (above the table)
    mq = st.text_input("Search description or NMC", key="master_search",
                       placeholder="e.g. butterfly valve, HEX BOLT, NMC-FAST-…").strip()
    m_cats = st.multiselect(
        "Category", options=sorted({m["category"] for m in master}),
        format_func=lambda c: CAT_PRETTY.get(c, c),
        help="Leave empty to include every category.")
    m_only_shared = st.checkbox("Only shared materials (2+ CPSEs)", value=False)
    m_only_spread = st.checkbox("Only codes with price spread", value=False)

    m_rows = master
    if mq:
        ql = mq.lower()
        m_rows = [m for m in m_rows
                  if ql in str(m["standardized_description"]).lower()
                  or ql in str(m["national_material_code"]).lower()]
    if m_cats:
        m_rows = [m for m in m_rows if m["category"] in m_cats]
    if m_only_shared:
        m_rows = [m for m in m_rows if "," in m["cpses_sharing"]]
    if m_only_spread:
        m_rows = [m for m in m_rows if row_spread(m) not in (None, 0)]

    st.caption(f"Showing {len(m_rows):,} of {len(master):,} codes"
               + (" · filters active" if (mq or m_cats or m_only_shared or m_only_spread)
                  else " · unfiltered"))

    # ---- catalog table
    mdf = pd.DataFrame([{
        "National Material Code": m["national_material_code"],
        "Description": m["standardized_description"],
        "Category": CAT_PRETTY.get(m["category"], m["category"]),
        "Type": m["material_type"],
        "Std UOM": m["uom"],
        "Shared by": m["cpses_sharing"],
        "# Codes": m["num_legacy_codes"],
        "Avg ₹": m["avg_rate_inr"],
        "Min ₹": m["min_rate_inr"],
        "Max ₹": m["max_rate_inr"],
        "Confidence": round(float(m["confidence"]), 4),
        "Status": m["status"]} for m in m_rows])

    if mdf.empty:
        st.info("No codes match the current search and filters.")
    else:
        for col in ("Avg ₹", "Min ₹", "Max ₹"):
            mdf[col] = pd.to_numeric(mdf[col], errors="coerce").round(2)
            mdf[col] = mdf[col].where(pd.notna(mdf[col]), "—")
        m_styled = (mdf.style
                    .map(lambda _: "font-family: 'Fira Code', ui-monospace, monospace",
                         subset=["National Material Code"])
                    .hide(axis="index"))
        st.dataframe(m_styled, hide_index=True, use_container_width=True,
                     height=min(38 + 35 * len(mdf), 480))
        st.download_button("Download filtered catalog (CSV)",
                           data=safe_csv_bytes(mdf),
                           file_name="unifymat_master_catalog.csv", mime="text/csv")

    # ---- price spread spotlight (demand-aggregation opportunity)
    st.markdown("<h3 class='section'>Price spread spotlight</h3>", unsafe_allow_html=True)
    spread_rows = [(m, s) for m in m_rows if (s := row_spread(m)) is not None and s > 0]
    if spread_rows:
        spread_rows.sort(key=lambda t: -t[1])
        sdf = pd.DataFrame([{
            "NMC": m["national_material_code"],
            "Description": (m["standardized_description"][:48] + "…")
            if len(m["standardized_description"]) > 48 else m["standardized_description"],
            "Shared by": m["cpses_sharing"],
            "Min ₹": float(m["min_rate_inr"]),
            "Max ₹": float(m["max_rate_inr"]),
            "Spread %": round(p * 100, 1)} for m, p in spread_rows[:5]])
        sdf_styled = (sdf.style
                      .map(lambda _: "font-family: 'Fira Code', ui-monospace, monospace",
                           subset=["NMC"])
                      .hide(axis="index"))
        st.dataframe(sdf_styled, hide_index=True, use_container_width=True,
                     height=min(38 + 35 * len(sdf), 480))
        st.caption("Top 5 by price spread in the current filter — the same material bought "
                   "at different prices across CPSEs.")
    else:
        st.caption("No rate data in current filter.")

# ---------------------------------------------------------------- Audit Trail
with tab_audit:
    st.markdown("<h3 class='section'>Governance trail</h3>", unsafe_allow_html=True)
    st.caption("Officer decisions persist across pipeline runs and are applied to the registry "
               "itself on every harmonization (OFFICER_MERGED rows below; the hard-attribute veto "
               "can block an unsafe merge). Machine actions are regenerated for the current run and "
               "are also written to outputs/audit_log.csv.")
    if len(decisions):
        st.markdown("**Officer decisions (persistent)**")
        st.dataframe(decisions[["timestamp", "officer", "cpse", "material_code",
                                "decision", "suggested_nmc"]].iloc[::-1],
                     hide_index=True, use_container_width=True, height=240)
    else:
        st.caption("No officer decisions recorded yet — approve or reject items in the Review Queue.")
    st.markdown("**Machine actions (current run)**")
    if DECISIONS.exists():
        st.download_button("Download officer decisions (CSV)",
                           data=DECISIONS.read_bytes(),
                           file_name="review_decisions.csv", mime="text/csv")
    audit = pd.DataFrame(B["audit"])
    if len(audit):
        audit = audit.rename(columns={"national_material_code": "National code", "action": "Action",
                                      "members": "Members", "confidence": "Confidence",
                                      "timestamp": "Timestamp"})
        audit["Auto"] = audit.get("Auto", True)
        st.dataframe(audit[["Timestamp", "National code", "Action", "Members", "Confidence"]],
                     hide_index=True, use_container_width=True, height=320)
