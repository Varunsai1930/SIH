"""Build the SIH 2026 idea-presentation deck from the official template.

Fills SIH2026-IDEA-Presentation-Format.pptx (7 slides) with UnifyMat
content: slide titles/structure stay exactly as the template mandates,
body guidance text is replaced with real verified numbers, small native
diagrams are added in the template's visual language (Arial, 1F497D /
0070C0), and the instructions slide is deleted (template rule: max 6
slides). Team ID / Team Name are left for the student to fill.

Run:  .venv/bin/python deck/build_sih_deck.py
Out:  deck/UnifyMat-SIH2026-Idea.pptx
"""
import copy
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

DECK = Path(__file__).resolve().parent
SRC = DECK / "SIH2026-IDEA-Presentation-Format.pptx"
OUT = DECK / "UnifyMat-SIH2026-Idea.pptx"

PRIMARY = RGBColor(0x1F, 0x49, 0x7D)   # template dk2 — diagram fills
ACCENT = RGBColor(0x00, 0x70, 0xC0)    # template accent — arrows/highlights
MUTED = RGBColor(0x80, 0x80, 0x80)
TINT = RGBColor(0xEA, 0xF1, 0xF9)      # light chip fill
DARK = RGBColor(0x1F, 0x29, 0x37)
FONT = "Arial"

prs = Presentation(SRC)


def iter_tf(shapes):
    for s in shapes:
        if s.shape_type == 6:
            yield from iter_tf(s.shapes)
        elif getattr(s, "has_text_frame", False):
            yield s, s.text_frame


def _norm(s):
    return s.replace("\x0b", "").replace("\r", "").strip()


def replace_para(p, new_text):
    """First-run replace: keeps the template's font/size/bold."""
    runs = p.runs
    if not runs:
        p.add_run().text = new_text
        return
    runs[0].text = new_text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def replace_texts(slide, mapping):
    m = {_norm(k): v for k, v in mapping.items()}
    hit = set()
    for _, tf in iter_tf(slide.shapes):
        full = "\n".join(p.text for p in tf.paragraphs)
        if _norm(full) in m:
            parts = m[_norm(full)].split("\n")
            for i, p in enumerate(tf.paragraphs):
                replace_para(p, parts[i] if i < len(parts) else "")
            hit.add(_norm(full))
            continue
        for p in tf.paragraphs:
            key = _norm(p.text)
            if key in m:
                replace_para(p, m[key])
                hit.add(key)  # captured BEFORE replace_para mutates p.text
    missed = set(m) - hit
    assert not missed, f"unmatched replacements: {missed}"


def add_box(slide, x, y, w, h, fill, line=None, radius=0.08):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    try:
        sh.adjustments[0] = radius
    except Exception:
        pass
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line:
        sh.line.color.rgb = line
        sh.line.width = Pt(1)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def set_text(shape, lines, size=18, color=RGBColor(0xFF, 0xFF, 0xFF),
             bold_first=True, align=PP_ALIGN.CENTER):
    """lines: list of (text, size_override, bold_override)."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = Inches(0.06)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    for i, (txt, sz, bd) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = txt
        r.font.name = FONT
        r.font.size = Pt(sz or size)
        r.font.bold = bd if bd is not None else (i == 0 and bold_first)
        r.font.color.rgb = color


def add_arrow(slide, x, y, w, h):
    sh = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = ACCENT
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def add_caption(slide, x, y, w, text, size=14, color=MUTED, align=PP_ALIGN.CENTER):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.color.rgb = color
    return tb


# ------------------------------------------------------------------ S1 title page
s1 = prs.slides[0]
replace_texts(s1, {"TITLE PAGE": "UnifyMat — One Nation, One Material Code"})
for _, tf in iter_tf(s1.shapes):
    vals = {
        "Problem Statement ID –": "Problem Statement ID – SIH26099",
        "Problem Statement Title-": "Problem Statement Title- AI-Driven Standardization and Harmonization of Material Codes Across CPSEs",
        "Theme-": "Theme- Smart Automation",
        "PS Category- Software/Hardware": "PS Category- Software",
        # Team ID- / Team Name left as-is for the student to fill
    }
    for p in tf.paragraphs:
        key = _norm(p.text)
        if key in vals:
            replace_para(p, vals[key])

# ------------------------------------------------------------------ S2 idea + solution
s2 = prs.slides[1]
replace_texts(s2, {
    "IDEA TITLE": "UnifyMat",
    "Proposed Solution (Describe your Idea/Solution/Prototype)":
        "Proposed Solution",
    "Detailed explanation of the proposed solution":
        "One National Material Code (NMC) per real material, all CPSEs",
    "How it addresses the problem":
        "Same bolt today: 5 codes, 5 prices (₹16–₹21) — merged safely",
    "Innovation and uniqueness of the solution":
        "AI proposes · hard facts veto · humans approve",
})
# idea title on two centered lines — one line at 36pt hits the team badge
# (left) and the SIH logo (right); duplicate the styled paragraph so both
# lines inherit the template's run formatting
for sh in s2.shapes:
    if getattr(sh, "is_placeholder", False) and getattr(sh, "has_text_frame", False) \
            and sh.text_frame.text.strip() == "UnifyMat":
        tf = sh.text_frame
        for para in tf.paragraphs:
            for br in para._p.findall(
                    "{http://schemas.openxmlformats.org/drawingml/2006/main}br"):
                para._p.remove(br)
        from copy import deepcopy as _dd
        p0 = tf.paragraphs[0]
        p0.alignment = PP_ALIGN.CENTER
        p0.runs[0].text = "UnifyMat"
        p1 = _dd(p0._p)
        p0._p.addnext(p1)
        tf.paragraphs[1].runs[0].text = "One Nation, One Material Code"
# the template's two empty spacer paragraphs push the body text into the
# band below — drop them (this box's content is fully restyled anyway)
for sh, tf in list(iter_tf(s2.shapes)):
    if any("NMC) per real material" in p.text for p in tf.paragraphs):
        for p in [p for p in tf.paragraphs if not p.runs]:
            p._p.getparent().remove(p._p)
# proven-numbers line (28pt, same style family as the body)
num = add_box(s2, 0.0, 4.50, 13.33, 0.55, TINT)
set_text(num, [("Proven on 403 records · 5 CPSEs: precision 1.000 · 0 wrong merges · "
                "~10 s on CPU", 18, True)], color=PRIMARY, bold_first=True)
# 5 CPSEs -> 1 NMC mini-diagram
add_caption(s2, 0.0, 5.22, 13.33, "5 CPSE material masters  →  one national code", 16, MUTED)
cpses = ["CPCL", "IOCL", "NTPC", "SAIL", "GAIL"]
x = 0.95
for name in cpses:
    b = add_box(s2, x, 5.72, 1.15, 0.62, PRIMARY)
    set_text(b, [(name, 16, True)])
    x += 1.45
add_arrow(s2, 8.05, 5.82, 1.05, 0.42)
nmc = add_box(s2, 9.35, 5.52, 3.55, 1.05, ACCENT)
set_text(nmc, [("ONE NATIONAL MATERIAL CODE", 14, True),
               ("NMC-FAST-BOLT-9BF0ABAC", 16, True)])

# ------------------------------------------------------------------ S3 technical approach
s3 = prs.slides[2]
replace_texts(s3, {
    "Technologies to be used (e.g. programming languages, frameworks, hardware)":
        "Tech: Python, Streamlit, MiniLM embeddings, TF-IDF fallback, RapidFuzz",
    "Methodology and process for implementation (Flow Charts/Images/ working prototype)":
        "Flow: normalize → 35 attrs → match & veto → deterministic NMC + audit",
})
steps = [
    ("1 · NORMALIZE", "~35 attributes from free text"),
    ("2 · MATCH & VETO", "embeddings rank · hard facts decide"),
    ("3 · ISSUE NMC", "legacy mapping + audit trail"),
]
x = 0.67
for head, sub in steps:
    b = add_box(s3, x, 5.05, 3.6, 1.15, PRIMARY)
    set_text(b, [(head, 17, True), (sub, 13, False)])
    if x < 8:
        add_arrow(s3, x + 3.68, 5.42, 0.42, 0.4)
    x += 4.1

# ------------------------------------------------------------------ S4 feasibility
s4 = prs.slides[3]
replace_texts(s4, {
    "Analysis of the feasibility of the idea":
        "Feasible: any ERP CSV in; ~10 s per run",
    "Potential challenges and risks":
        "Risk: wrong merges — veto + officer gate",
    "Strategies for overcoming these challenges":
        "Proved on ground-truthed synthetic data",
})
chips = [("403 → 264", "national codes issued"),
         ("0", "trap violations (8.8 vs 10.9)"),
         ("7,951", "unsafe pairs auto-rejected")]
x = 0.67
for big, small in chips:
    b = add_box(s4, x, 4.75, 3.2, 1.15, TINT, line=PRIMARY)
    set_text(b, [(big, 26, True), (small, 13, False)], color=PRIMARY)
    x += 3.55

# ------------------------------------------------------------------ S5 impact
s5 = prs.slides[4]
replace_texts(s5, {
    "Potential impact on the target audience":
        "300+ CPSEs on one national material language",
    "Benefits of the solution (social, economic, environmental, etc.)":
        "Safety: 8.8 vs 10.9 mix-up now impossible",
})
extra = add_box(s5, 0.67, 4.45, 10.26, 0.55, TINT)
set_text(extra, [("Economic: 12.8% avg price spread exposed — pump ₹26,674 vs ₹54,000 (51%); "
                  "aggregated demand → national rate contracts", 18, True)],
         color=PRIMARY, bold_first=True)
stats = [("1.000", "auto-merge precision"), ("0", "wrong merges"),
         ("89.7%", "recall with approvals")]
x = 0.67
for big, small in stats:
    b = add_box(s5, x, 5.35, 3.2, 1.15, PRIMARY)
    set_text(b, [(big, 26, True), (small, 13, False)])
    x += 3.55
add_caption(s5, 0.67, 6.62, 10.26,
            "Every merge is officer-approved — named, timestamped, fully auditable.",
            13, MUTED, align=PP_ALIGN.LEFT)

# ------------------------------------------------------------------ S6 references
s6 = prs.slides[5]
replace_texts(s6, {
    "Details / Links of the reference and research work":
        "Problem Statement SIH26099 — MoP&NG / CPCL",
})
refs = [
    "Reimers & Gurevych (2019) — Sentence-BERT sentence embeddings · arXiv:1908.10084",
    "all-MiniLM-L6-v2 model · huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
    "Papadakis et al. (2020) — Blocking & Filtering for Entity Resolution · ACM CSUR",
    "ISO 898-1 — fastener property classes 8.8 / 10.9 (the grade trap in our data)",
    "Government e-Marketplace (GeM) · gem.gov.in — national public-procurement context",
    "Working prototype, benchmark + verified outputs · github.com/Varunsai1930/SIH",
]
tb = s6.shapes.add_textbox(Inches(0.67), Inches(3.85), Inches(10.9), Inches(2.9))
tf = tb.text_frame
tf.word_wrap = True
tf.margin_left = tf.margin_top = 0
for i, ref in enumerate(refs):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(10)
    r1 = p.add_run()
    r1.text = "▪  "
    r1.font.name = FONT
    r1.font.size = Pt(18)
    r1.font.color.rgb = ACCENT
    r2 = p.add_run()
    r2.text = ref
    r2.font.name = FONT
    r2.font.size = Pt(18)
    r2.font.color.rgb = DARK

# ------------------------------------------------------------------ delete instructions slide
sld = list(prs.slides._sldIdLst)[6]
prs.part.drop_rel(sld.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
prs.slides._sldIdLst.remove(sld)

prs.save(OUT)
print(f"saved {OUT} — {len(prs.slides.__iter__.__self__._sldIdLst)} slides")
