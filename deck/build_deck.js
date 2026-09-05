// UnifyMat — SIH 26099 pitch deck (9 slides, 16:9 13.33x7.5")
// Design: institutional blue dominant, amber accent, light content slides,
// dark-blue title & closing (sandwich). Fonts: Arial + Courier New.
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.layout = "LAYOUT_WIDE";
p.author = "Team UnifyMat";
p.title = "UnifyMat — One Nation, One Material Code";

const W = 13.33, H = 7.5, M = 0.55;
// palette — mirrors the dashboard design system
const BG = "F8FAFC";        // near-white slate background (content slides)
const DARK = "122A5C";     // deep institutional navy (title/close background)
const PRIMARY = "1E40AF";   // institutional blue
const PRIMARY_D = "1E3A8A"; // darker blue for text on light
const PRIMARY_L = "DBEAFE"; // light blue tint
const ACCENT = "D97706";    // amber accent
const ACCENT_D = "B45309";  // amber text-safe
const TEXT = "1E293B";      // body text
const MUTED = "64748B";     // secondary text
const BORDER = "E2E8F0";   // hairline
const WHITE = "FFFFFF";
const MONO = "Courier New";
const SANS = "Arial";

const shadow = () => ({ type: "outer", color: "1E293B", blur: 7, offset: 2, angle: 90, opacity: 0.14 });
const kpi = (s, x, y, w, h, val, label, sub, valColor = PRIMARY_D) => {
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.07, fill: { color: WHITE }, line: { color: BORDER, width: 1 }, shadow: shadow() });
  s.addText(val, { x, y: y + 0.16, w, h: 0.62, align: "center", fontFace: SANS, fontSize: 34, bold: true, color: valColor, margin: 0 });
  s.addText(label, { x: x + 0.1, y: y + 0.82, w: w - 0.2, h: 0.3, align: "center", fontFace: SANS, fontSize: 11.5, bold: true, color: MUTED, charSpacing: 2, margin: 0 });
  s.addText(sub, { x: x + 0.1, y: y + 1.12, w: w - 0.2, h: 0.3, align: "center", fontFace: SANS, fontSize: 10.5, color: MUTED, margin: 0 });
};
// evidence KPI row: 4 cards ending flush with the deck's right margin
const kpiRow = (s, items, y) => {
  const w = 2.86, pitch = 3.125;
  items.forEach((it, i) => kpi(s, M + i * pitch, y, w, 1.62, ...it));
};
const footer = (s, n, dark = false) => {
  s.addText("UnifyMat · SIH 26099 · Smart Automation", { x: M, y: H - 0.42, w: 6, h: 0.3, fontFace: SANS, fontSize: 9.5, color: dark ? "93A8D8" : "94A3B8", margin: 0 });
  s.addText(String(n).padStart(2, "0"), { x: W - 1.1, y: H - 0.42, w: 0.55, h: 0.3, fontFace: MONO, fontSize: 10, color: dark ? "93A8D8" : "94A3B8", align: "right", margin: 0 });
};
const title = (s, kicker, head) => {
  s.addText(kicker.toUpperCase(), { x: M, y: 0.42, w: 10, h: 0.3, fontFace: SANS, fontSize: 11, bold: true, color: ACCENT_D, charSpacing: 3, margin: 0 });
  s.addText(head, { x: M, y: 0.68, w: W - 2 * M, h: 0.62, fontFace: SANS, fontSize: 30, bold: true, color: PRIMARY_D, margin: 0 });
};

// ---------------------------------------------------------------- S1 · TITLE (dark)
{
  const s = p.addSlide();
  s.background = { color: DARK };
  s.addText("SIH 26099 · MINISTRY OF PETROLEUM & NATURAL GAS · CPCL", { x: M, y: 1.15, w: 12, h: 0.35, fontFace: SANS, fontSize: 13, bold: true, color: "9DB8E8", charSpacing: 2.5, margin: 0 });
  s.addText("UnifyMat", { x: M, y: 1.85, w: 12, h: 1.15, fontFace: SANS, fontSize: 66, bold: true, color: WHITE, margin: 0 });
  s.addText([
    { text: "One Nation · One Material Code", options: { fontSize: 27, bold: true, color: "F4C883", breakLine: true } },
    { text: "AI-driven standardization and harmonization of material codes across CPSEs", options: { fontSize: 16.5, color: "C6D4F2" } },
  ], { x: M, y: 3.1, w: 11.5, h: 1.25, fontFace: SANS, margin: 0, lineSpacingMultiple: 1.25 });
  // proof chips
  const chips = [
    ["403", "records · 5 CPSEs"],
    ["267", "national codes issued"],
    ["100%", "auto-merge precision"],
    ["0", "near-miss merges"],
  ];
  chips.forEach((c, i) => {
    const cw = 2.62, gap = 0.32, x = M + i * (cw + gap), y = 5.05;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w: cw, h: 1.28, rectRadius: 0.08, fill: { color: "1B3568" }, line: { color: "2E4A86", width: 1 } });
    s.addText(c[0], { x, y: y + 0.14, w: cw, h: 0.55, align: "center", fontFace: SANS, fontSize: 28, bold: true, color: i === 2 ? "F4C883" : WHITE, margin: 0 });
    s.addText(c[1], { x: x + 0.1, y: y + 0.74, w: cw - 0.2, h: 0.4, align: "center", fontFace: SANS, fontSize: 10.5, color: "9DB8E8", margin: 0 });
  });
  s.addText("Smart India Hackathon 2026 · Team presentation", { x: M, y: H - 0.5, w: 8, h: 0.3, fontFace: SANS, fontSize: 10.5, color: "7C93C8", margin: 0 });
}

// ---------------------------------------------------------------- S2 · PROBLEM (light)
{
  const s = p.addSlide();
  s.background = { color: BG };
  title(s, "The problem", "The same bolt lives five lives across five ERPs");
  // left: five ERP rows
  const rows = [
    ["CPCL", "MAT100006", "HEX BOLT BLK OX, 8.8, M20x80", "NOS", "₹ 19"],
    ["IOCL", "RM-00006", "Hex Bolt – Black Oxide – DIN 933 – 8.8 – M20 X 80", "EA", "₹ 19"],
    ["NTPC", "EGW000004", "Hex Bolt, M20 x 80 mm, Blk Oxide, Gr.8.8, DIN 933", "NOS", "₹ 21"],
    ["SAIL", "S100028", "HEX BOLT / DIN-933 / M20x80MM / BLACK / 8.8 GR", "NUM", "₹ 16"],
    ["GAIL", "GLM-HB-0001", "HEX BOLT M20X80 GR 8.8 BLACK DIN 933", "NOS", "₹ 18"],
  ];
  const colX = [0.55, 1.75, 3.6, 8.75, 9.9], colW = [1.15, 1.8, 5.05, 1.1, 1.0];
  const heads = ["CPSE", "ERP code", "How the ERP describes it", "UOM", "Rate"];
  heads.forEach((h2, i) => s.addText(h2.toUpperCase(), { x: colX[i], y: 1.62, w: colW[i], h: 0.28, fontFace: SANS, fontSize: 10, bold: true, color: MUTED, charSpacing: 1.5, margin: 0 }));
  rows.forEach((r, ri) => {
    const y = 2.0 + ri * 0.62;
    if (ri % 2 === 0) s.addShape(p.shapes.RECTANGLE, { x: 0.5, y: y - 0.04, w: 10.5, h: 0.58, fill: { color: "EFF4FB" }, line: { type: "none" } });
    s.addText(r[0], { x: colX[0], y, w: colW[0], h: 0.45, fontFace: SANS, fontSize: 13, bold: true, color: PRIMARY_D, margin: 0, valign: "middle" });
    s.addText(r[1], { x: colX[1], y, w: colW[1], h: 0.45, fontFace: MONO, fontSize: 12, color: TEXT, margin: 0, valign: "middle" });
    s.addText(r[2], { x: colX[2], y, w: colW[2], h: 0.45, fontFace: SANS, fontSize: 12, color: TEXT, margin: 0, valign: "middle" });
    s.addText(r[3], { x: colX[3], y, w: colW[3], h: 0.45, fontFace: SANS, fontSize: 12, color: TEXT, margin: 0, valign: "middle" });
    s.addText(r[4], { x: colX[4], y, w: colW[4], h: 0.45, fontFace: SANS, fontSize: 13, bold: true, color: ri === 3 ? ACCENT_D : TEXT, margin: 0, valign: "middle" });
  });
  // right: consequence card
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 11.35, y: 1.62, w: 1.45, h: 3.6, rectRadius: 0.06, fill: { color: PRIMARY }, line: { type: "none" }, shadow: shadow() });
  s.addText("₹ 16\n–\n₹ 21", { x: 11.35, y: 2.0, w: 1.45, h: 1.5, align: "center", fontFace: SANS, fontSize: 21, bold: true, color: WHITE, margin: 0 });
  s.addText("price spread\non one bolt", { x: 11.35, y: 3.55, w: 1.45, h: 0.9, align: "center", fontFace: SANS, fontSize: 11, bold: true, color: "E2EBFB", margin: 0 });
  // bottom: three consequences (row list)
  const cons = [
    ["No aggregate demand", "each CPSE buys the same bolt separately — losing bulk pricing"],
    ["Duplicate inventory", "one material stocked many times across warehouses"],
    ["No spend visibility", "Ministry cannot answer \u201Chow much steel do we buy?\u201D"],
  ];
  cons.forEach((c, i) => {
    const x = M + i * 4.12;
    s.addShape(p.shapes.OVAL, { x, y: 5.78, w: 0.16, h: 0.16, fill: { color: ACCENT }, line: { type: "none" } });
    s.addText(c[0], { x: x + 0.3, y: 5.62, w: 3.6, h: 0.32, fontFace: SANS, fontSize: 14.5, bold: true, color: PRIMARY_D, margin: 0 });
    s.addText(c[1], { x: x + 0.3, y: 5.96, w: 3.55, h: 0.65, fontFace: SANS, fontSize: 11.5, color: MUTED, margin: 0 });
  });
  s.addText("Source: synthetic multi-CPSE dataset built for SIH 26099 (records generated to mirror real ERP description styles)", { x: M, y: 6.78, w: 11, h: 0.25, fontFace: SANS, fontSize: 9.5, color: "94A3B8", margin: 0 });
  footer(s, 2);
}

// ---------------------------------------------------------------- S3 · SOLUTION (light)
{
  const s = p.addSlide();
  s.background = { color: BG };
  title(s, "The solution", "A three-stage harmonization pipeline");
  const stages = [
    ["1", "Normalize & extract", "Tames every house style into canonical text, then regex-extracts ~35 engineering attributes (grade, class, schedule, size, material)."],
    ["2", "Match — with a veto", "Blocks by category, ranks candidates by sentence-embedding similarity, then hard-vetoes any conflicting attribute. Missing identity data goes to an officer, never auto-merged."],
    ["3", "Standardize & code", "Deterministic standardized description + stable National Material Code + full legacy-code mapping and audit trail."],
  ];
  const cw = 3.75, gap = 0.55;
  stages.forEach((st, i) => {
    const x = M + i * (cw + gap), y = 1.75;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w: cw, h: 3.1, rectRadius: 0.08, fill: { color: WHITE }, line: { color: BORDER, width: 1 }, shadow: shadow() });
    s.addShape(p.shapes.OVAL, { x: x + 0.28, y: y + 0.28, w: 0.62, h: 0.62, fill: { color: i === 1 ? ACCENT : PRIMARY }, line: { type: "none" } });
    s.addText(st[0], { x: x + 0.28, y: y + 0.28, w: 0.62, h: 0.62, align: "center", fontFace: SANS, fontSize: 22, bold: true, color: WHITE, margin: 0 });
    s.addText(st[1], { x: x + 1.08, y: y + 0.33, w: cw - 1.3, h: 0.62, fontFace: SANS, fontSize: 16.5, bold: true, color: PRIMARY_D, margin: 0, valign: "middle" });
    s.addText(st[2], { x: x + 0.3, y: y + 1.15, w: cw - 0.6, h: 1.8, fontFace: SANS, fontSize: 12.5, color: TEXT, margin: 0, lineSpacingMultiple: 1.15 });
    if (i < 2) s.addText("\u2192", { x: x + cw + 0.06, y: y + 1.25, w: 0.45, h: 0.6, align: "center", fontFace: SANS, fontSize: 26, bold: true, color: "94A3B8", margin: 0 });
  });
  // outcome band
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.35, w: W - 2 * M, h: 1.15, rectRadius: 0.08, fill: { color: "EFF4FB" }, line: { type: "none" } });
  s.addText([
    { text: "In:  ", options: { bold: true, color: MUTED } },
    { text: "MAT100006 · RM-00006 · EGW000004 · S100028 · GLM-HB-0001", options: { fontFace: MONO, color: TEXT } },
    { text: "     Out:  ", options: { bold: true, color: MUTED } },
    { text: "NMC-FAST-BOLT-DEE61ADC", options: { fontFace: MONO, bold: true, color: PRIMARY } },
    { text: "  \u2014 one national material, five traceable legacy codes", options: { color: TEXT } },
  ], { x: M + 0.3, y: 5.35, w: W - 2 * M - 0.6, h: 1.15, fontFace: SANS, fontSize: 13.5, margin: 0, valign: "middle" });
  footer(s, 3);
}

// ---------------------------------------------------------------- S4 · LIVE DEMO (light)
{
  const s = p.addSlide();
  s.background = { color: BG };
  title(s, "Working prototype", "Live in the dashboard");
  // screenshot left
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.55, y: 1.7, w: 7.6, h: 4.28, rectRadius: 0.06, fill: { color: WHITE }, line: { color: BORDER, width: 1 }, shadow: shadow() });
  s.addImage({ path: "gui-test-screenshots/tab1_overview.png", x: 0.73, y: 1.86, w: 7.24, h: 4.07 * (720 / 1280) * (1280 / 720) * (4.07 / (1280 * 720 / 1280)) * (1280 / 720) * (720 / 1280) * (1280 / 1280) * (720 / 720) * (4.07 * 0) + 4.07, sizing: { type: "contain", w: 7.24, h: 3.9 } });
  s.addText("Overview tab — verified capture of the running app", { x: 0.55, y: 6.05, w: 7.6, h: 0.25, fontFace: SANS, fontSize: 10, color: MUTED, align: "center", margin: 0 });
  // right: what we will show
  const beats = [
    ["Same-bolt match", "side-by-side CPSE descriptions resolved to one NMC"],
    ["Near-miss refusal", "butterfly vs gate valve at 0.63 similarity — vetoed on 5 attributes"],
    ["Officer approval", "human-in-the-loop decision, logged with name & timestamp"],
    ["5th CPSE upload", "pre-flight quality check, then live ingest — numbers update on screen"],
    ["Price spread", "negotiation-ready spread on 68 shared materials"],
  ];
  beats.forEach((b, i) => {
    const y = 1.78 + i * 0.94;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 8.55, y: y, w: 0.5, h: 0.5, rectRadius: 0.08, fill: { color: i === 1 ? ACCENT : PRIMARY }, line: { type: "none" } });
    s.addText(String(i + 1), { x: 8.55, y: y, w: 0.5, h: 0.5, align: "center", fontFace: SANS, fontSize: 15, bold: true, color: WHITE, margin: 0 });
    s.addText(b[0], { x: 9.22, y: y - 0.02, w: 3.5, h: 0.3, fontFace: SANS, fontSize: 13.5, bold: true, color: PRIMARY_D, margin: 0 });
    s.addText(b[1], { x: 9.22, y: y + 0.28, w: 3.55, h: 0.55, fontFace: SANS, fontSize: 10.5, color: MUTED, margin: 0 });
  });
  footer(s, 4);
}

// ---------------------------------------------------------------- S5 · EVIDENCE (light)
{
  const s = p.addSlide();
  s.background = { color: BG };
  title(s, "Evidence", "Precision first — the system never guesses");
  kpiRow(s, [
    ["100%", "AUTO-MERGE PRECISION", "every auto-merged pair is correct", "0E7A3E"],
    ["0", "NEAR-MISS VIOLATIONS", "grade 8.8 vs 10.9 never merged"],
    ["89.7%", "POTENTIAL RECALL", "after officer approval of flagged pairs"],
    ["388", "RECORDS EVALUATED", "vs ground truth, 4 CPSEs"],
  ], 1.75);
  // trap example band
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: M, y: 3.75, w: W - 2 * M, h: 2.4, rectRadius: 0.08, fill: { color: WHITE }, line: { color: BORDER, width: 1 }, shadow: shadow() });
  s.addText("THE TRAP THAT MUST NEVER SLIP THROUGH", { x: M + 0.35, y: 4.0, w: 8, h: 0.28, fontFace: SANS, fontSize: 10.5, bold: true, color: ACCENT_D, charSpacing: 2, margin: 0 });
  s.addText([
    { text: "CPCL  ", options: { bold: true, color: MUTED } },
    { text: "MAT100050  ", options: { fontFace: MONO, color: PRIMARY } },
    { text: "\u201CBUTTERFLY VALVE 6\u2033, WAFER, CL 150, CI\u201D", options: { color: TEXT, breakLine: true } },
    { text: "CPCL  ", options: { bold: true, color: MUTED } },
    { text: "MAT100044  ", options: { fontFace: MONO, color: PRIMARY } },
    { text: "\u201CGATE VALVE CL 800, FS, SW, 1.5\u2033\u201D", options: { color: TEXT } },
  ], { x: M + 0.35, y: 4.32, w: 7.2, h: 1.05, fontFace: SANS, fontSize: 12.5, margin: 0, lineSpacingMultiple: 1.3 });
  // verdict
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 8.35, y: 4.35, w: 4.15, h: 1.45, rectRadius: 0.07, fill: { color: "FDF6EC" }, line: { color: "F0D9B5", width: 1 } });
  s.addText([
    { text: "0.63 similarity \u2192 REJECTED.  ", options: { bold: true, color: ACCENT_D } },
    { text: "Five conflicting attributes: class, end, inch, material, type.", options: { color: TEXT } },
  ], { x: 8.55, y: 4.42, w: 3.8, h: 1.3, fontFace: SANS, fontSize: 12, margin: 0, valign: "middle", lineSpacingMultiple: 1.15 });
  s.addText("Checked automatically across 7,951 candidate pairs \u00B7 2,798 attribute vetoes issued \u00B7 Source: outputs/rejected_pairs.csv, pipeline run of 04 Sep 2026", { x: M, y: 6.45, w: 12, h: 0.28, fontFace: SANS, fontSize: 10, color: "94A3B8", margin: 0 });
  footer(s, 5);
}

// ---------------------------------------------------------------- S6 · GOVERNANCE (light)
{
  const s = p.addSlide();
  s.background = { color: BG };
  title(s, "Governance by design", "AI proposes, hard facts dispose, humans approve");
  const flow = [
    ["AI", "proposes", "embedding similarity + attribute agreement produce a suggested NMC and confidence score"],
    ["VETO", "disposes", "any single conflicting hard attribute (grade, schedule, seal, size\u2026) kills the merge \u2014 no exceptions"],
    ["OFFICER", "approves", "records missing identity attributes land in the review queue; every decision is logged with name and timestamp"],
  ];
  const cw = 3.75, gap = 0.55;
  flow.forEach((f, i) => {
    const x = M + i * (cw + gap), y = 1.8;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w: cw, h: 2.9, rectRadius: 0.08, fill: { color: WHITE }, line: { color: BORDER, width: 1 }, shadow: shadow() });
    s.addText(f[0], { x: x + 0.3, y: y + 0.25, w: cw - 0.6, h: 0.42, fontFace: SANS, fontSize: 19, bold: true, color: i === 1 ? ACCENT_D : PRIMARY, margin: 0 });
    s.addText(f[1].toUpperCase(), { x: x + 0.3, y: y + 0.68, w: cw - 0.6, h: 0.3, fontFace: SANS, fontSize: 11.5, bold: true, color: MUTED, charSpacing: 3, margin: 0 });
    s.addText(f[2], { x: x + 0.3, y: y + 1.05, w: cw - 0.6, h: 1.7, fontFace: SANS, fontSize: 12.5, color: TEXT, margin: 0, lineSpacingMultiple: 1.18 });
    if (i < 2) s.addText("\u2192", { x: x + cw + 0.06, y: y + 1.1, w: 0.45, h: 0.6, align: "center", fontFace: SANS, fontSize: 26, bold: true, color: "94A3B8", margin: 0 });
  });
  // audit band
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.15, w: W - 2 * M, h: 1.35, rectRadius: 0.08, fill: { color: "EFF4FB" }, line: { type: "none" } });
  s.addText([
    { text: "Every action leaves a trail.  ", options: { bold: true, color: PRIMARY_D } },
    { text: "Cluster creations, officer approvals and rejections persist to outputs/audit_log.csv and review_decisions.csv \u2014 the audit trail the problem statement demands. Nothing is a black box: same inputs always produce the same codes.", options: { color: TEXT } },
  ], { x: M + 0.35, y: 5.15, w: W - 2 * M - 0.7, h: 1.35, fontFace: SANS, fontSize: 13, margin: 0, valign: "middle", lineSpacingMultiple: 1.2 });
  footer(s, 6);
}

// ---------------------------------------------------------------- S7 · SAVINGS (light, shape-drawn chart)
{
  const s = p.addSlide();
  s.background = { color: BG };
  title(s, "The savings story", "Price spread on materials shared across CPSEs");
  s.addText("Difference between the highest and lowest CPSE rate for the identical material", { x: M, y: 1.28, w: 7.6, h: 0.3, fontFace: SANS, fontSize: 12, color: MUTED, margin: 0 });
  // shape-drawn horizontal bars (renders identically in PowerPoint, Keynote and PDF)
  const bars = [
    ["Centrifugal pump", 50.6], ["Ball bearing 6205", 32.6], ["Pipe 4\u2033 SCH40", 29.2],
    ["Tee 2\u2033 SCH40", 27.4], ["Flat washer M16", 25.0], ["Lithium grease NLGI-3", 24.3],
  ];
  const labX = M, labW = 2.35, barX = 3.05, barMax = 4.7, barH = 0.44, pitch = 0.72, y0 = 1.95;
  bars.forEach((b, i) => {
    const y = y0 + i * pitch, wBar = (b[1] / 50.6) * barMax;
    s.addText(b[0], { x: labX, y, w: labW, h: barH, align: "right", fontFace: SANS, fontSize: 11.5, color: TEXT, margin: 0, valign: "middle" });
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: barX, y, w: wBar, h: barH, rectRadius: 0.04, fill: { color: i === 0 ? ACCENT : PRIMARY }, line: { type: "none" } });
    s.addText(b[1].toFixed(1) + "%", { x: barX + wBar + 0.08, y, w: 0.85, h: barH, fontFace: SANS, fontSize: 12.5, bold: true, color: i === 0 ? ACCENT_D : PRIMARY_D, margin: 0, valign: "middle" });
  });
  s.addText("identical material, bought at up to 1.5\u00D7 the lowest CPSE rate", { x: barX, y: y0 + 5 * pitch + 0.62, w: 6, h: 0.3, fontFace: SANS, fontSize: 11.5, italic: true, color: MUTED, margin: 0 });
  // right: the math
  kpi(s, 8.55, 1.75, 4.25, 1.5, "12.6%", "AVERAGE PRICE SPREAD", "on 68 materials shared by 2+ CPSEs", ACCENT_D);
  s.addText([
    { text: "What one national code unlocks:", options: { bold: true, color: PRIMARY_D, breakLine: true } },
    { text: "Aggregate demand across CPSEs into single, bulk tenders", options: { bullet: { code: "2022", indent: 12 }, breakLine: true } },
    { text: "Flag over-paying CPSEs against peers on identical materials", options: { bullet: { code: "2022", indent: 12 }, breakLine: true } },
    { text: "Give the Ministry a true total-spend picture per material", options: { bullet: { code: "2022", indent: 12 } } },
  ], { x: 8.6, y: 3.55, w: 4.15, h: 2.5, fontFace: SANS, fontSize: 12.5, color: TEXT, margin: 0, paraSpaceAfter: 10, lineSpacingMultiple: 1.1 });
  s.addText("Source: outputs/unified_master.csv — min/max last-rate per NMC on shared materials (rates in ₹)", { x: M, y: 6.55, w: 11, h: 0.25, fontFace: SANS, fontSize: 9.5, color: "94A3B8", margin: 0 });
  footer(s, 7);
}

// ---------------------------------------------------------------- S8 · SCALE & ROADMAP (light)
{
  const s = p.addSlide();
  s.background = { color: BG };
  title(s, "Built to scale", "From 400 records to a national registry");
  const lanes = [
    ["Today \u2014 verified", ["403 records \u00B7 5 CPSE house styles ingested live", "Blocking keeps comparisons within category \u2014 O(n\u00B7k), not O(n\u00B2)", "Offline mode: TF-IDF fallback matches with zero internet"] ],
    ["Near term", ["FAISS approximate-nearest-neighbour index for millions of rows", "Batch ERP connectors \u2014 scheduled CSV/API pulls from each CPSE", "Officer worklist with roles, comments and sign-off levels"] ],
    ["National rollout", ["NMC issued alongside legacy codes \u2014 zero ERP migration risk", "GeM / SAP integration via the mapping layer", "Department-wise spend dashboards on live procurement data"] ],
  ];
  const cw2 = 3.75, gap = 0.55;
  lanes.forEach((ln, i) => {
    const x = M + i * (cw2 + gap), y = 1.75;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w: cw2, h: 4.0, rectRadius: 0.08, fill: { color: i === 0 ? "EFF4FB" : WHITE }, line: { color: i === 0 ? "C9D9F2" : BORDER, width: 1 }, shadow: shadow() });
    s.addText(ln[0], { x: x + 0.28, y: y + 0.24, w: cw2 - 0.56, h: 0.35, fontFace: SANS, fontSize: 15, bold: true, color: i === 0 ? ACCENT_D : PRIMARY_D, margin: 0 });
    ln[1].forEach((it, j) => {
      const iy = y + 0.78 + j * 1.0;
      s.addShape(p.shapes.OVAL, { x: x + 0.3, y: iy + 0.09, w: 0.12, h: 0.12, fill: { color: i === 0 ? ACCENT : PRIMARY }, line: { type: "none" } });
      s.addText(it, { x: x + 0.56, y: iy, w: cw2 - 0.85, h: 0.95, fontFace: SANS, fontSize: 11.5, color: TEXT, margin: 0, lineSpacingMultiple: 1.1 });
    });
  });
  s.addText("Architecture is data-agnostic: any CSV with material code, description and UOM can be harmonized \u2014 the ERP export every CPSE already produces.", { x: M, y: 6.1, w: W - 2 * M, h: 0.5, fontFace: SANS, fontSize: 12.5, italic: true, color: MUTED, margin: 0, align: "center" });
  footer(s, 8);
}

// ---------------------------------------------------------------- S9 · CLOSE (dark)
{
  const s = p.addSlide();
  s.background = { color: DARK };
  s.addText("ONE NATION · ONE MATERIAL CODE", { x: M, y: 1.7, w: 12, h: 0.35, fontFace: SANS, fontSize: 13, bold: true, color: "9DB8E8", charSpacing: 3, margin: 0 });
  s.addText("Every material a single code.\nEvery code fully traceable.", { x: M, y: 2.3, w: 11.5, h: 2.0, fontFace: SANS, fontSize: 40, bold: true, color: WHITE, margin: 0, lineSpacingMultiple: 1.15 });
  // traceability chain
  const chain = ["CPSE legacy codes", "National Material Code", "Standardized description", "Officer-approved audit trail"];
  const cw3 = 2.85, gap3 = 0.32;
  chain.forEach((c, i) => {
    const x = M + i * (cw3 + gap3);
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 4.75, w: cw3, h: 0.75, rectRadius: 0.07, fill: { color: "1B3568" }, line: { color: "2E4A86", width: 1 } });
    s.addText(c, { x: x + 0.12, y: 4.75, w: cw3 - 0.24, h: 0.75, align: "center", fontFace: SANS, fontSize: 12.5, bold: true, color: WHITE, margin: 0, valign: "middle" });
    if (i < 3) s.addText("\u2192", { x: x + cw3, y: 4.75, w: gap3, h: 0.75, align: "center", fontFace: SANS, fontSize: 15, bold: true, color: "7C93C8", margin: 0, valign: "middle" });
  });
  s.addText("Legacy codes never die \u2014 the NMC is the join key between them.", { x: M, y: 5.9, w: 11, h: 0.35, fontFace: SANS, fontSize: 14, color: "C6D4F2", margin: 0 });
  s.addText("Team UnifyMat · Smart India Hackathon 2026 · github.com/Varunsai1930/SIH", { x: M, y: H - 0.5, w: 9, h: 0.3, fontFace: SANS, fontSize: 10.5, color: "7C93C8", margin: 0 });
}

p.writeFile({ fileName: "deck/UnifyMat-pitch.pptx" }).then(() => console.log("deck written: deck/UnifyMat-pitch.pptx"));
