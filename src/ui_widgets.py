"""Pure-rendering HTML widgets for the UnifyMat dashboard (SIH26099).

Both helpers return HTML strings — they never call Streamlit themselves;
the caller renders them with ``st.markdown(..., unsafe_allow_html=True)``.
No module-level side effects and no Streamlit import, so the module is
trivially importable from tests.

confidence_ring(score, size=32, percent=False)
    Inline SVG circular progress ring for a 0-1 similarity/confidence
    score. Emerald arc >= 0.90, amber 0.70-0.899, coral < 0.70; slate
    track; the numeric readout sits centred inside the ring in Fira Code
    ("0.87", or "94%" when percent=True). The score is clamped to [0, 1];
    None/NaN scores render an empty track with a "—" readout. Everything
    in the output is numeric, so nothing needs html.escape().

preflight_report(df, cpse_name)
    Pre-flight check for the sidebar upload flow: summarises a freshly
    uploaded CSV *before* harmonization runs. Renders total rows, missing
    counts for the required columns (material_code / description / uom),
    the case-insensitive duplicate material_code count, a raw UOM value
    inventory (top 5 distinct values with counts), description length
    stats (min/median/max chars) and a potential-issues line for
    sub-8-char descriptions — then a verdict banner: green
    "READY TO HARMONIZE" (every required column present, zero missing
    material_code, zero duplicates) or amber "FIX BEFORE UPLOAD" listing
    the first three concrete problems. Returns "" for an empty frame so
    the caller can show its own message; stats that cannot be computed
    (absent column) render as "—".

All data-derived strings (UOM values, the CPSE name, column names) go
through html.escape(). Design tokens follow app.py: #F8FAFC card
backgrounds, 1px #E2E8F0 borders, 10px card radius, Fira Sans body
text, Fira Code for codes, institutional blue #1E3A8A accents and amber
#92400E / #FDE68A warnings.

Run ``python src/ui_widgets.py`` for a self-test that prints sample
output for eyeball checking.
"""

import html
import math

import pandas as pd

# ------------------------------------------------------------------ tokens
_FONT_SANS = "'Fira Sans', -apple-system, 'Segoe UI', Roboto, sans-serif"
_FONT_MONO = "'Fira Code', ui-monospace, monospace"

_RING_TRACK = "#E2E8F0"    # slate-200 ring track
_RING_TEXT = "#0F172A"     # slate-900 numeric readout
_C_EMERALD = "#10B981"     # score >= 0.90
_C_AMBER = "#F59E0B"       # 0.70 <= score < 0.90
_C_CORAL = "#EF4444"       # score < 0.70

_BG_CARD = "#F8FAFC"       # slate-50 card fill
_BORDER = "#E2E8F0"        # slate-200 hairline border
_FG = "#1E3A8A"            # institutional blue-900 headline
_BODY = "#334155"          # slate-700 body text
_MUTED = "#64748B"         # slate-500 secondary
_MUTED_2 = "#94A3B8"       # slate-400 "not computable" dash
_WARN_FG = "#92400E"       # amber-800 warning text
_WARN_BG = "#FFFBEB"       # amber-50 banner fill
_WARN_BORDER = "#FDE68A"   # amber-200 banner border
_OK_FG = "#047857"         # emerald-700 success text
_OK_BG = "#ECFDF5"         # emerald-50 banner fill
_OK_BORDER = "#A7F3D0"     # emerald-200 banner border

_REQUIRED = ("material_code", "description", "uom")


# ------------------------------------------------------------------ confidence ring
def _ring_color(score):
    """Arc colour for a clamped 0-1 score: emerald / amber / coral."""
    if score >= 0.90:
        return _C_EMERALD
    if score >= 0.70:
        return _C_AMBER
    return _C_CORAL


def confidence_ring(score: float, size: int = 32, percent: bool = False) -> str:
    """Inline SVG circular progress ring for a similarity/confidence score.

    Pure HTML/SVG string — the caller does
    ``st.markdown(confidence_ring(s), unsafe_allow_html=True)``.

    - viewBox 0 0 36 36, track stroke #E2E8F0 width 3, arc stroke width 3,
      stroke-linecap round, circle r=15.9155 at 18,18 rotated -90deg so
      the arc starts at 12 o'clock; dasharray "<score*100> 100".
    - Colour by threshold: >= 0.90 #10B981, 0.70-0.899 #F59E0B,
      < 0.70 #EF4444.
    - Centred readout <text> at 18,22.5 — "0.87" (2 decimals), or "94%"
      when percent=True. Font 'Fira Code', monospace, fill #0F172A.
    - size sets the svg width/height attributes (default 32).
    - score is clamped to [0, 1]; None/NaN/unparseable render an empty
      ring with a "—" readout.
    """
    try:
        val = float(score)
    except (TypeError, ValueError):
        val = float("nan")
    try:
        px = max(1, int(size))
    except (TypeError, ValueError):
        px = 32

    if math.isnan(val):  # None, NaN or unparseable — no arc to draw
        arc, label = "", "&#8212;"
    else:
        s = min(1.0, max(0.0, val))  # clamp to [0, 1]
        label = f"{s * 100:.0f}%" if percent else f"{s:.2f}"
        arc = (f'<circle cx="18" cy="18" r="15.9155" fill="none" '
               f'stroke="{_ring_color(s)}" stroke-width="3" stroke-linecap="round" '
               f'stroke-dasharray="{round(s * 100, 2):g} 100" '
               f'transform="rotate(-90 18 18)"/>')
    return (f'<svg width="{px}" height="{px}" viewBox="0 0 36 36" role="img" '
            f'aria-label="confidence {label}" style="vertical-align:middle">'
            f'<circle cx="18" cy="18" r="15.9155" fill="none" '
            f'stroke="{_RING_TRACK}" stroke-width="3"/>{arc}'
            f'<text x="18" y="22.5" font-size="9" font-family="{_FONT_MONO}" '
            f'fill="{_RING_TEXT}" text-anchor="middle">{label}</text></svg>')


# ------------------------------------------------------------------ pre-flight report
def _blank_mask(series: pd.Series) -> pd.Series:
    """Boolean Series: True where a value is None/NaN/NA or whitespace-only."""
    return series.map(
        lambda v: bool(pd.isna(v)) or str(v).strip() == "").astype(bool)


def _clean(series: pd.Series) -> pd.Series:
    """Stripped, non-missing values of a column as plain strings."""
    return series[~_blank_mask(series)].map(lambda v: str(v).strip())


def preflight_report(df: pd.DataFrame, cpse_name: str) -> str:
    """Pre-flight check card for an uploaded CSV, before harmonization.

    Renders a compact table-free HTML block: row/missing/duplicate stats,
    raw UOM inventory, description length stats, a potential-issues line
    and a verdict banner ("READY TO HARMONIZE" green / "FIX BEFORE
    UPLOAD" amber with the first three concrete problems). Column lookup
    is case/whitespace-insensitive (app.py normalises headers the same
    way). Returns "" for an empty (0-row) frame; uncomputable stats
    (required column absent) render as "—". Every data-derived string is
    html.escape()d.
    """
    if df is None or len(df) == 0:
        return ""

    # case/whitespace-insensitive required-column lookup
    actual: dict = {}
    for c in df.columns:
        actual.setdefault(str(c).strip().lower(), c)
    col = {name: actual.get(name) for name in _REQUIRED}

    n_rows = len(df)

    def missing_count(name):
        return None if col[name] is None else int(_blank_mask(df[col[name]]).sum())

    miss_code = missing_count("material_code")
    miss_desc = missing_count("description")
    miss_uom = missing_count("uom")

    # duplicate material_code: case-insensitive, stripped, missing excluded
    if col["material_code"] is None:
        dup_rows = dup_codes = None
    else:
        codes = _clean(df[col["material_code"]]).map(str.upper)
        dup_rows = int(codes.duplicated().sum())
        dup_codes = int(codes[codes.duplicated(keep=False)].nunique())

    # description length stats (stripped lengths, missing excluded)
    lens = None if col["description"] is None else _clean(
        df[col["description"]]).map(len)
    if lens is None or len(lens) == 0:
        dmin = dmed = dmax = None
    else:
        dmin, dmax = int(lens.min()), int(lens.max())
        med = float(lens.median())
        dmed = f"{med:.0f}" if med.is_integer() else f"{med:.1f}"
    junk = None if lens is None else int((lens < 8).sum())

    # raw UOM inventory (values exactly as uploaded, blanks excluded)
    if col["uom"] is None:
        uom_counts = None
    else:
        uom_series = df[col["uom"]]
        uom_counts = uom_series[~_blank_mask(uom_series)].value_counts()

    # ---------------------------------------------------------------- verdict
    absent = [name for name in _REQUIRED if col[name] is None]
    problems = []
    if absent:
        problems.append("Missing required column"
                        + ("s" if len(absent) > 1 else "") + ": " + ", ".join(absent))
    if miss_code:
        problems.append(f"{miss_code} row(s) missing material_code")
    if dup_rows:
        problems.append(f"{dup_rows} duplicate material_code row(s) across "
                        f"{dup_codes} code{'s' if dup_codes != 1 else ''}")
    if miss_desc:
        problems.append(f"{miss_desc} row(s) missing description")
    if miss_uom:
        problems.append(f"{miss_uom} row(s) missing uom")
    if junk:
        problems.append(f"{junk} description(s) under 8 chars (likely junk)")

    ready = (not absent) and miss_code == 0 and dup_rows == 0
    if ready:
        banner = (f'<div style="background:{_OK_BG};border:1px solid {_OK_BORDER};'
                  f'border-radius:8px;padding:8px 12px;margin-bottom:10px;'
                  f'color:{_OK_FG};font-size:12px;font-weight:700;">'
                  f'READY TO HARMONIZE<span style="font-weight:400;"> &#8212; '
                  f'{n_rows:,} rows · all required columns present · no missing codes '
                  f'· no duplicates</span></div>')
    else:
        items = "".join(
            f'<div style="margin-top:2px;font-weight:400;">&#8226; '
            f'{html.escape(p)}</div>' for p in problems[:3])
        more = (f'<div style="margin-top:2px;font-weight:400;">'
                f'+ {len(problems) - 3} more</div>' if len(problems) > 3 else "")
        banner = (f'<div style="background:{_WARN_BG};border:1px solid {_WARN_BORDER};'
                  f'border-radius:8px;padding:8px 12px;margin-bottom:10px;'
                  f'color:{_WARN_FG};font-size:12px;font-weight:700;">'
                  f'FIX BEFORE UPLOAD{items}{more}</div>')

    # ---------------------------------------------------------------- header
    name = html.escape(str(cpse_name).strip().upper() or "&#8212;")
    head = (f'<div style="display:flex;justify-content:space-between;'
            f'align-items:baseline;gap:12px;">'
            f'<div style="font-size:12px;font-weight:700;color:{_FG};'
            f'letter-spacing:.02em;">PRE-FLIGHT CHECK'
            f'<span style="color:{_MUTED};font-weight:400;"> &#183; {name}</span></div>'
            f'<div style="font-size:11px;color:{_MUTED};font-family:{_FONT_MONO};'
            f'white-space:nowrap;">{n_rows:,} rows &#183; {len(df.columns)} columns'
            f'</div></div>')

    # ---------------------------------------------------------------- stat chips
    def count_value(v):
        if v is None:
            return "&#8212;", _MUTED_2
        return (f"{v:,}", _FG if v == 0 else _WARN_FG)

    def chip(label, value, color):
        return (f'<div style="flex:1 1 100px;min-width:100px;background:#FFFFFF;'
                f'border:1px solid {_BORDER};border-radius:8px;padding:6px 9px;">'
                f'<div style="font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;'
                f'color:{_MUTED};font-weight:600;">{label}</div>'
                f'<div style="font-size:15px;font-weight:700;color:{color};margin-top:2px;'
                f'font-family:{_FONT_MONO};">{value}</div></div>')

    mc_v, mc_c = count_value(miss_code)
    md_v, md_c = count_value(miss_desc)
    mu_v, mu_c = count_value(miss_uom)
    dp_v, dp_c = count_value(dup_rows)
    jk_v, jk_c = count_value(junk)
    stats = (f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 2px;">'
             + chip("Rows", f"{n_rows:,}", _FG)
             + chip("Missing code", mc_v, mc_c)
             + chip("Missing desc", md_v, md_c)
             + chip("Missing uom", mu_v, mu_c)
             + chip("Duplicate rows", dp_v, dp_c)
             + chip("Short descs", jk_v, jk_c)
             + '</div>')

    # ---------------------------------------------------------------- detail lines
    if uom_counts is None:
        uom_html = f'<span style="color:{_MUTED_2}">&#8212;</span>'
    elif len(uom_counts) == 0:
        uom_html = f'<span style="color:{_MUTED_2}">none present</span>'
    else:
        parts = []
        for val, cnt in uom_counts.head(5).items():
            parts.append(
                f'<span style="font-family:{_FONT_MONO};background:#FFFFFF;'
                f'border:1px solid {_BORDER};border-radius:6px;padding:0 6px;">'
                f'{html.escape(str(val))}</span>'
                f'<span style="color:{_MUTED};">&#215; {cnt}</span>')
        if len(uom_counts) > 5:
            parts.append(f'<span style="color:{_MUTED};">'
                          f'+ {len(uom_counts) - 5} more</span>')
        uom_html = "&nbsp; ".join(parts)

    if dmin is None:
        lens_html = f'<span style="color:{_MUTED_2}">&#8212;</span>'
    else:
        lens_html = (f'min <span style="font-family:{_FONT_MONO};">{dmin}</span> '
                     f'&#183; median <span style="font-family:{_FONT_MONO};">{dmed}</span> '
                     f'&#183; max <span style="font-family:{_FONT_MONO};">{dmax}</span> chars')

    if junk is None:
        issue_html = f'<span style="color:{_MUTED_2}">&#8212;</span>'
    elif junk == 0:
        issue_html = f'<span style="color:{_OK_FG};">none &#8212; descriptions ' \
                     f'look healthy</span>'
    else:
        issue_html = (f'<span style="color:{_WARN_FG};font-weight:600;">{junk} '
                      f'description(s) under 8 chars &#8212; likely junk</span>')

    lines = (f'<div style="margin-top:9px;font-size:11.5px;color:{_BODY};">'
             f'<b style="color:{_FG};">UOM inventory</b> (top 5 raw values): '
             f'{uom_html}</div>'
             f'<div style="margin-top:9px;font-size:11.5px;color:{_BODY};">'
             f'<b style="color:{_FG};">Description length</b>: {lens_html}</div>'
             f'<div style="margin-top:9px;font-size:11.5px;color:{_BODY};">'
             f'<b style="color:{_FG};">Potential issues</b>: {issue_html}</div>')

    return (f'<div style="background:{_BG_CARD};border:1px solid {_BORDER};'
            f'border-radius:10px;padding:12px 14px;font-size:12.5px;color:{_BODY};'
            f'font-family:{_FONT_SANS};">{head}{banner}{stats}{lines}</div>')


# ------------------------------------------------------------------ self-test
if __name__ == "__main__":
    print("=" * 72)
    print("confidence_ring - emerald / amber / coral / invalid / percent")
    print("=" * 72)
    for s in (0.97, 0.87, 0.55, None, float("nan")):
        print(f"score={s!r:>8} -> {confidence_ring(s)}")
    print(f"percent=True   -> {confidence_ring(0.9412, size=44, percent=True)}")

    print()
    print("=" * 72)
    print("preflight_report - messy upload (duplicates, missing, junk, raw UOMs)")
    print("=" * 72)
    messy = pd.DataFrame({
        "Material_Code": ["F-100", "f-100 ", "V-200", "V-201", "", None, "P-300", "P-301"],
        "description": ["HEX BOLT M10 X 60", "hex bolt M10x60", "GATE VALVE 2IN CL150",
                        "x", "", "SQUARE PIPE 40 MM", "ELBOW 90DEG 25MM", "cable"],
        "UOM": ["NOS", "NOS", " nos", "EA", None, "KGS", "MT", "nos"],
    })
    print(preflight_report(messy, "GAIL"))

    print()
    print("=" * 72)
    print("preflight_report - required column absent (uom missing)")
    print("=" * 72)
    no_uom = pd.DataFrame({
        "material_code": ["A-1", "A-2", "A-3"],
        "description": ["HEX BOLT M10", "GATE VALVE 2 INCH CLASS 150 FLANGED",
                        "NUT M10"],
    })
    print(preflight_report(no_uom, "ntpc"))

    print()
    print("=" * 72)
    print("preflight_report - clean upload (ready) and empty frame")
    print("=" * 72)
    clean = pd.DataFrame({
        "material_code": ["N-01", "N-02", "N-03", "N-04", "N-05", "N-06"],
        "description": ["HEX BOLT M10 X 60 GRADE 8.8", "GATE VALVE 2 INCH CLASS 150 FLANGED",
                        "BALL BEARING 6205 2RS", "CABLE 4C X 1.5 SQMM COPPER",
                        "HYDRAULIC HOSE 12MM 2WIRE", "ELBOW 90 DEG 25MM SCH40"],
        "uom": ["NOS", "EA", "NOS", "MTR", "NOS", "EA"],
    })
    print(preflight_report(clean, "SAIL"))
    print(f"empty df -> {preflight_report(pd.DataFrame(columns=['material_code']), 'GAIL')!r}")
