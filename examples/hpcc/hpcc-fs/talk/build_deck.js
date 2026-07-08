// IPCCC 2026 talk deck for HPCC-FS — generated with pptxgenjs.
// Palette (semantic): navy 1E2761 dominant; ice CADCFC tint; RED C0504D = stock HPCC / problem;
// BLUE 4F81BD = HPCC-FS / fix (matches the paper figures' series colors).
const pptxgen = require("pptxgenjs");

const NAVY = "1E2761", ICE = "CADCFC", RED = "C0504D", BLUE = "4F81BD";
const INK = "1F2733", MUT = "5B6675", PAPER = "FFFFFF";
const REDT = "F7E9E8", BLUET = "E9F0F8", ICET = "EEF3FB", GREENOK = "1A7F37";
const FIG = "/Users/tiffanyzhang/uno-hpcc/examples/hpcc/hpcc-fs/figures";
const sh = () => ({ type: "outer", color: "000000", blur: 7, offset: 2, angle: 45, opacity: 0.14 });

let p = new pptxgen();
p.layout = "LAYOUT_16x9"; // 10 x 5.625
p.author = "Haoyu Wang";
p.title = "Multi-Bottleneck Fairness for High-Precision Congestion Control (HPCC-FS)";

// ---------- helpers ----------
function titleBar(s, kicker, title, dark = false) {
  const c = dark ? PAPER : NAVY;
  s.addText(kicker.toUpperCase(), { x: 0.55, y: 0.28, w: 8.9, h: 0.3, fontSize: 11, bold: true,
    color: dark ? ICE : MUT, fontFace: "Calibri", charSpacing: 3, margin: 0 });
  s.addText(title, { x: 0.55, y: 0.55, w: 8.9, h: 0.62, fontSize: 27, bold: true, color: c,
    fontFace: "Calibri", margin: 0 });
}
function numCircle(s, x, y, n, color) {
  s.addShape(p.shapes.OVAL, { x, y, w: 0.34, h: 0.34, fill: { color } });
  s.addText(String(n), { x, y: y - 0.015, w: 0.34, h: 0.36, align: "center", valign: "middle",
    fontSize: 14, bold: true, color: PAPER, fontFace: "Calibri", margin: 0 });
}
function chip(s, x, y, w, txt, fg, bg) {
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.34, fill: { color: bg }, rectRadius: 0.06 });
  s.addText(txt, { x, y: y - 0.01, w, h: 0.36, align: "center", valign: "middle", fontSize: 12,
    bold: true, color: fg, fontFace: "Calibri", margin: 0 });
}

// ============================================================ 1 · TITLE (dark)
{
  const s = p.addSlide(); s.background = { color: NAVY };
  // mini parking-lot motif: 5 switch dots, 4 red links, blue long-flow line above
  const y0 = 0.78, x0 = 2.9, dx = 1.05;
  s.addShape(p.shapes.LINE, { x: x0 + 0.12, y: y0 - 0.28, w: dx * 4 + 0.1, h: 0, line: { color: BLUE, width: 3 } });
  s.addText("long flow", { x: x0 + 1.3, y: y0 - 0.62, w: 1.8, h: 0.3, fontSize: 10, italic: true, color: "8FB0DC", fontFace: "Calibri", margin: 0, align: "center" });
  for (let i = 0; i < 4; i++)
    s.addShape(p.shapes.LINE, { x: x0 + 0.34 + i * dx, y: y0 + 0.17, w: dx - 0.34, h: 0, line: { color: RED, width: 4 } });
  for (let i = 0; i < 5; i++)
    s.addShape(p.shapes.OVAL, { x: x0 + i * dx, y: y0, w: 0.34, h: 0.34, fill: { color: ICE } });
  s.addText("Multi-Bottleneck Fairness for\nHigh-Precision Congestion Control", {
    x: 0.7, y: 1.7, w: 8.6, h: 1.5, fontSize: 33, bold: true, color: PAPER, fontFace: "Cambria", align: "center" });
  s.addText("HPCC-FS — one fair-rate field, one scalar per switch port", {
    x: 0.7, y: 3.12, w: 8.6, h: 0.45, fontSize: 17, italic: true, color: ICE, fontFace: "Calibri", align: "center" });
  s.addText([
    { text: "Haoyu Wang ¹ · Bo Sheng ¹ · Zerin Shaima Meem ² · Xiaoqian Zhang ²", options: { breakLine: true, fontSize: 14, color: PAPER } },
    { text: "¹ University of Massachusetts Boston      ² University of Nebraska Omaha", options: { fontSize: 11.5, color: "9DB2D8" } },
  ], { x: 0.7, y: 3.9, w: 8.6, h: 0.75, align: "center", fontFace: "Calibri" });
  s.addText("45th IEEE IPCCC · Austin, Texas · November 2026", {
    x: 0.7, y: 4.85, w: 8.6, h: 0.35, fontSize: 12, color: "8FA6CF", fontFace: "Calibri", align: "center" });
  s.addNotes("Thank you. This talk is about a fairness blind spot in HPCC — the SIGCOMM'19 INT-based congestion control — and a deliberately minimal switch-side alternative: an operating mode that coexists with stock HPCC on the same fabric. The one-line story: a flow crossing several bottlenecks gets half its fair share, no sender-side correction we tried can close the gap, and one fair-rate scalar per switch port — offered as a per-class mode, not a replacement — closes it completely.");
}

// ============================================================ 2 · HPCC in 60s
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Background", "HPCC in 60 seconds: precision congestion control");
  const rows = [
    ["1", "Switch stamps raw per-hop state into INT", "tx bytes, queue length, link rate — stateless per flow", NAVY],
    ["2", "Sender computes exact utilization U", "multiplicative update toward target η = 95%", NAVY],
    ["3", "Near-zero queues, top-tier FCT", "beats DCQCN / TIMELY / DCTCP on single-bottleneck benchmarks", NAVY],
  ];
  rows.forEach((r, i) => {
    const y = 1.5 + i * 0.92;
    numCircle(s, 0.6, y + 0.06, r[0], r[3]);
    s.addText([
      { text: r[1], options: { bold: true, fontSize: 15.5, color: INK, breakLine: true } },
      { text: r[2], options: { fontSize: 12.5, color: MUT } },
    ], { x: 1.12, y: y - 0.05, w: 4.9, h: 0.9, fontFace: "Calibri", margin: 0 });
  });
  // right card: the INT wire
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.35, y: 1.45, w: 3.15, h: 2.75, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
  s.addText("the INT header", { x: 6.6, y: 1.62, w: 2.7, h: 0.3, fontSize: 11, bold: true, color: MUT, charSpacing: 2, fontFace: "Calibri", margin: 0 });
  ["hop 1: tx, qlen, rate", "hop 2: tx, qlen, rate", "hop 3: tx, qlen, rate", "… up to maxHop = 5"].forEach((t, i) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.6, y: 1.98 + i * 0.52, w: 2.65, h: 0.42, fill: { color: PAPER }, line: { color: "B9C6DE", width: 1 }, rectRadius: 0.05 });
    s.addText(t, { x: 6.72, y: 1.99 + i * 0.52, w: 2.45, h: 0.4, fontSize: 11.5, color: i === 3 ? MUT : INK, italic: i === 3, valign: "middle", fontFace: "Courier New", margin: 0 });
  });
  s.addText("8 bytes per hop — the record grows with path length", {
    x: 6.35, y: 4.35, w: 3.15, h: 0.55, fontSize: 11.5, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  s.addText("The catch: the sender sees load, not its fair share.", {
    x: 0.6, y: 4.55, w: 5.4, h: 0.6, fontSize: 15, bold: true, color: RED, fontFace: "Calibri", margin: 0 });
  s.addNotes("Quick recap of HPCC for those who haven't seen it: switches stamp raw telemetry into every packet, the sender computes a precise utilization estimate and drives it to 95%. It is excellent on the benchmarks it was designed for. Keep one detail in mind: the INT record is per-hop — 8 bytes per switch, capped at 5 hops — and it carries load, not entitlement.");
}

// ============================================================ 3 · the blind spot
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Motivation", "Modern traffic crosses many contended links in series");
  const cards = [
    ["Cross-pod ML", "allreduce spans aggregation + core layers"],
    ["Disaggregation", "memory / storage traffic transits multiple fabrics"],
    ["Multi-tenancy", "shared links at every tier of the DC"],
  ];
  cards.forEach((c, i) => {
    const x = 0.6 + i * 3.05;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: 2.8, h: 1.35, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
    s.addText([
      { text: c[0], options: { bold: true, fontSize: 15, color: NAVY, breakLine: true } },
      { text: c[1], options: { fontSize: 11.5, color: MUT } },
    ], { x: x + 0.22, y: 1.68, w: 2.4, h: 1.05, fontFace: "Calibri", margin: 0, valign: "top" });
  });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 3.25, w: 8.85, h: 1.7, fill: { color: NAVY }, rectRadius: 0.1, shadow: sh() });
  s.addText([
    { text: "Does HPCC still deliver fair service when a flow crosses", options: { breakLine: true } },
    { text: "multiple bottlenecks — not just one?", options: {} },
  ], { x: 0.95, y: 3.5, w: 8.15, h: 1.2, fontSize: 21, bold: true, color: PAPER, fontFace: "Cambria", align: "center", valign: "middle" });
  s.addText("Nobody had measured it carefully. We did — deterministically, against a max-min oracle.", {
    x: 0.6, y: 5.05, w: 8.85, h: 0.4, fontSize: 12.5, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  s.addNotes("Why care about multi-bottleneck paths? Three growing traffic classes cross several contended links in series. HPCC's evaluation — like most DC transport work — is single-bottleneck-centric. So the question of this paper is simply: does the fairness survive? Our methodology is deterministic simulation scored against a fluid max-min oracle, so every number you'll see is exactly reproducible.");
}

// ============================================================ 4 · methodology
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Methodology", "The parking lot, scored against a max-min oracle");
  s.addImage({ path: `${FIG}/fig_topo_parking.png`, x: 0.75, y: 1.35, w: 5.9, h: 3.2 });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.95, y: 1.35, w: 2.6, h: 3.2, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Setup", options: { bold: true, fontSize: 12, color: MUT, charSpacing: 2, breakLine: true } },
    { text: "N bottlenecks, 25 Gbps each. One long flow crosses all N; one cross flow per link.", options: { fontSize: 12, color: INK, breakLine: true, paraSpaceAfter: 8 } },
    { text: "Fair answer", options: { bold: true, fontSize: 12, color: MUT, charSpacing: 2, breakLine: true } },
    { text: "Every flow gets 12.5 Gbps (progressive filling, recomputed as flows finish).", options: { fontSize: 12, color: INK, breakLine: true, paraSpaceAfter: 8 } },
    { text: "Metric", options: { bold: true, fontSize: 12, color: MUT, charSpacing: 2, breakLine: true } },
    { text: "unfairness = long FCT / mean short FCT.  Oracle = 1.0", options: { fontSize: 12, color: INK } },
  ], { x: 7.15, y: 1.55, w: 2.25, h: 2.9, fontFace: "Calibri", margin: 0 });
  s.addText("Deterministic: every configuration reproduces byte-identical artifacts.", {
    x: 0.75, y: 4.75, w: 8.8, h: 0.4, fontSize: 12, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  s.addNotes("The classic parking lot: a long flow crosses every bottleneck, one cross flow per link. Because every link is equally contended, max-min says everyone gets the same 12.5 Gbps — so any gap between the long flow and the cross flows is pure multi-bottleneck unfairness. We score against an event-driven progressive-filling oracle, and everything is deterministic.");
}

// ============================================================ 5 · finding (problem chart, native)
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Finding 1", "The long flow is starved ≈ 2× — and it's structural");
  s.addChart(p.charts.BAR, [
    { name: "stock HPCC", labels: ["N=2", "N=3", "N=4"], values: [1.9, 1.92, 1.96] },
    { name: "multi-rate HPCC", labels: ["N=2", "N=3", "N=4"], values: [1.44, 1.5, 1.75] },
  ], {
    x: 0.55, y: 1.4, w: 5.5, h: 3.5, barDir: "col", chartColors: [RED, "9BBB59"],
    chartArea: { fill: { color: "FFFFFF" } }, catAxisLabelColor: MUT, valAxisLabelColor: MUT,
    valGridLine: { color: "E4E9F0", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 11,
    valAxisMaxVal: 2.2, valAxisMinVal: 0, showLegend: true, legendPos: "b", legendColor: MUT,
    showTitle: false, dataLabelFormatCode: "0.00",
  });
  s.addText("unfairness ratio \u2014 max-min oracle = 1.0", { x: 0.55, y: 4.95, w: 5.5, h: 0.3, fontSize: 11, italic: true, color: MUT, fontFace: "Calibri", align: "center", margin: 0 });
  const stats = [
    ["1.96×", "penalty at N = 4", RED, REDT],
    ["3.5×", "when the long flow is small (RPC-scale)", RED, REDT],
    ["N ≥ 5", "breaks outright: INT maxHop overflow", NAVY, ICET],
  ];
  stats.forEach((t, i) => {
    const y = 1.42 + i * 1.18;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.35, y, w: 3.15, h: 1.02, fill: { color: t[3] }, rectRadius: 0.09, shadow: sh() });
    s.addText(t[0], { x: 6.55, y: y + 0.1, w: 1.25, h: 0.82, fontSize: 26, bold: true, color: t[2], fontFace: "Cambria", valign: "middle", margin: 0 });
    s.addText(t[1], { x: 7.8, y: y + 0.1, w: 1.6, h: 0.82, fontSize: 11.5, color: INK, valign: "middle", fontFace: "Calibri", margin: 0 });
  });
  s.addNotes("The finding: stock HPCC starves the long flow by roughly 2x at N=2 through 4, and the effect grows. HPCC's own multi-rate mode helps but doesn't fix it. It's worse — 3.5x — exactly where it hurts most: small, latency-sensitive flows. And past four bottlenecks the per-hop INT record overflows its hop cap and the control input is corrupted outright. Also robust: asymmetric sizes, staggered starts, and RTT equalization don't move it — this is not RTT unfairness.");
}

// ============================================================ 6 · winner-take-all diagnosis
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Finding 2", "Winner-take-all — and nothing is ‘wrong’");
  s.addChart(p.charts.BAR, [{
    name: "goodput during contention (Gbps)",
    labels: ["cross flow 1", "cross flow 2", "cross flow 3", "cross flow 4", "long flow"],
    values: [23.2, 23.2, 23.2, 23.2, 0.38],
  }], {
    x: 0.55, y: 1.45, w: 5.6, h: 3.35, barDir: "bar",
    chartColors: [RED], chartArea: { fill: { color: "FFFFFF" } },
    catAxisLabelColor: MUT, valAxisLabelColor: MUT,
    valGridLine: { color: "E4E9F0", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 11,
    showLegend: false, showTitle: false, valAxisMaxVal: 25, dataLabelFormatCode: "0.0#",
  });
  s.addText("stock HPCC, N = 4, first 18 ms — fair share is 12.5 Gbps for everyone", {
    x: 0.55, y: 4.85, w: 5.6, h: 0.35, fontSize: 11, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.45, y: 1.5, w: 3.05, h: 3.3, fill: { color: REDT }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Zero PFC. Zero loss.", options: { bold: true, fontSize: 15, color: RED, breakLine: true, paraSpaceAfter: 6 } },
    { text: "No pathology to point at — every link is at target utilization η.", options: { fontSize: 12.5, color: INK, breakLine: true, paraSpaceAfter: 10 } },
    { text: "The unfair allocation is the control law's equilibrium.", options: { bold: true, fontSize: 13.5, color: INK, breakLine: true, paraSpaceAfter: 10 } },
    { text: "At each shared link the local single-bottleneck flow wins; the long flow is squeezed at all of them.", options: { fontSize: 12, color: MUT } },
  ], { x: 6.7, y: 1.72, w: 2.55, h: 2.9, fontFace: "Calibri", margin: 0 });
  s.addNotes("Here's what it looks like inside: four cross flows sit at 23 Gbps each while the long flow is pinned at 0.4 — for the entire contention window. The crucial observation: nothing is broken. No PFC, no loss, links at target utilization. The starvation IS the equilibrium of the control law. That reframes the problem: you can't patch a symptom; you have to change what information the control loop has.");
}

// ============================================================ 7 · sender-only fixes fail
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Negative result", "Five sender-only fixes — none gets close");
  const rows = [
    [{ text: "sender-side variant (mb_mode)", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12.5 } },
     { text: "idea", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12.5 } },
     { text: "best penalty @ N=4", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12.5, align: "center" } }],
    ["k-aware additive increase", "scale AI by congested-hop count", { text: "1.63×", options: { align: "center", bold: true, color: RED } }],
    ["debiased max/mean blend", "soften the max-hop bias", { text: "1.95×", options: { align: "center", bold: true, color: RED } }],
    ["responsibility-weighted MD", "MD scaled by own share", { text: "1.89×", options: { align: "center", bold: true, color: RED } }],
    ["k-th-root MD", "split the decrease across hops", { text: "1.92×", options: { align: "center", bold: true, color: RED } }],
    ["global share-aware AI", "AI boosted by (1 − share)", { text: "1.71×", options: { align: "center", bold: true, color: RED } }],
  ];
  s.addTable(rows, { x: 0.6, y: 1.45, w: 8.85, colW: [3.15, 3.9, 1.8], fontFace: "Calibri", fontSize: 12.5,
    color: INK, border: { pt: 0.75, color: "D5DCE6" }, fill: { color: PAPER }, rowH: 0.42, valign: "middle", margin: 0.06 });
  s.addText([
    { text: "Each variant is a 1–2 line change in HPCC’s update ", options: { fontSize: 13, color: MUT } },
    { text: "(mb_mode 0 stays byte-identical to stock)", options: { fontSize: 13, italic: true, color: MUT } },
    { text: " — the target is 1.0×.", options: { fontSize: 13, color: MUT } },
  ], { x: 0.6, y: 4.62, w: 8.85, h: 0.4, fontFace: "Calibri", align: "center" });
  s.addNotes("Our first instinct — and probably yours — was to fix this at the sender, keeping HPCC's stateless-switch story intact. We built five variants spanning the design space: additive boosts, debiasing, decrease-side scaling, share-aware updates. Best case gets you 1.63; the target is 1.0. This is the paper's negative result, and it motivates everything after: why does every endpoint fix stall?");
}

// ============================================================ 8 · structural reason (dark emphasis)
{
  const s = p.addSlide(); s.background = { color: NAVY };
  titleBar(s, "Why", "Two structural reasons sender-only cannot work", true);
  const card = (x, head, lines, tint) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.55, w: 4.25, h: 2.55, fill: { color: PAPER }, rectRadius: 0.1, shadow: sh() });
    s.addText(head, { x: x + 0.28, y: 1.78, w: 3.7, h: 0.4, fontSize: 16, bold: true, color: tint, fontFace: "Calibri", margin: 0 });
    s.addText(lines, { x: x + 0.28, y: 2.25, w: 3.7, h: 1.7, fontFace: "Calibri", margin: 0 });
  };
  card(0.6, "1 · The η-hold equilibrium", [
    { text: "Links settle at target utilization → HPCC’s multiplicative term ≈ 1.", options: { fontSize: 12.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Every flow holds whatever rate it grabbed at startup. Additive nudges need ~10⁴ RTTs to redistribute.", options: { fontSize: 12.5, color: MUT } },
  ], RED);
  card(5.15, "2 · N is not observable", [
    { text: "Fair share is C / N. INT tells the sender C — never N, the link’s flow count.", options: { fontSize: 12.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Without N there is no strong multiplicative move toward fair share — only slow AIMD nudging.", options: { fontSize: 12.5, color: MUT } },
  ], RED);
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.35, w: 8.8, h: 0.85, fill: { color: BLUE }, rectRadius: 0.1, shadow: sh() });
  s.addText("The information isn’t at the sender — so the fix can’t be either. It belongs at the link.", {
    x: 0.85, y: 4.42, w: 8.3, h: 0.72, fontSize: 16.5, bold: true, color: PAPER, fontFace: "Cambria", align: "center", valign: "middle" });
  s.addNotes("Two reasons, and they compose. First, at equilibrium HPCC's multiplicative machinery goes idle — everyone just holds. Second, even if you wanted a strong corrective move, the fair share is C over N, and N — the flow count — simply is not in the INT signal. The only N-free sender mechanism is additive nudging, which we just showed is hopelessly slow. Conclusion: put the fair-share computation where N is implicitly visible — the link. That's a 20-year-old idea: RCP.");
}

// ============================================================ 9 · RCP in 60s
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "The alternative, part 1", "RCP: the link advertises one fair rate to every flow");
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.5, w: 8.85, h: 1.0, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
  s.addText("R ← R · (1 + (α·(C − y) − β·q/d) / C)", {
    x: 0.85, y: 1.6, w: 8.35, h: 0.8, fontSize: 19, bold: true, color: NAVY, fontFace: "Courier New", align: "center", valign: "middle" });
  const ann = [
    ["α·(C − y)", "chases spare capacity — link under-full ⇒ R rises", BLUE, BLUET],
    ["β·q/d", "brakes on backlog — queue forms ⇒ R falls", RED, REDT],
    ["fixed point", "y = C, q = 0  ⇒  N·R = C  ⇒  R = C/N", GREENOK, "E9F4EC"],
  ];
  ann.forEach((a, i) => {
    const x = 0.6 + i * 3.05;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 2.85, w: 2.8, h: 1.35, fill: { color: a[3] }, rectRadius: 0.09, shadow: sh() });
    s.addText([
      { text: a[0], options: { bold: true, fontSize: 15, color: a[2], fontFace: "Courier New", breakLine: true, paraSpaceAfter: 4 } },
      { text: a[1], options: { fontSize: 11.5, color: INK } },
    ], { x: x + 0.22, y: 3.03, w: 2.4, h: 1.05, fontFace: "Calibri", margin: 0, valign: "top" });
  });
  s.addText([
    { text: "The link converges to the max-min share ", options: { fontSize: 15, color: INK, bold: true } },
    { text: "without ever counting flows", options: { fontSize: 15, color: BLUE, bold: true, italic: true } },
    { text: " — N is implicit in the observed load y.", options: { fontSize: 15, color: INK, bold: true } },
  ], { x: 0.6, y: 4.5, w: 8.85, h: 0.65, fontFace: "Calibri", align: "center" });
  s.addNotes("RCP in one equation. Each link keeps a single rate R — the rate every flow crossing it should send at. Alpha chases spare capacity upward, beta brakes on queue. Those balance only when the link is exactly full with no standing queue — which with N flows each sending R means N times R equals C. So R converges to C over N without the switch ever counting flows: N is implicit in the load. This is exactly the missing ingredient from the previous slide, computed exactly where it's observable.");
}

// ============================================================ 10 · worked example
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "The alternative, part 2", "Worked example: path-min gives network-wide max-min");
  const yS = 1.75;
  // switches
  const sw = (x, label) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: yS, w: 1.0, h: 0.72, fill: { color: NAVY }, rectRadius: 0.08, shadow: sh() });
    s.addText(label, { x, y: yS, w: 1.0, h: 0.72, align: "center", valign: "middle", fontSize: 15, bold: true, color: PAPER, fontFace: "Calibri", margin: 0 });
  };
  // long flow line through both links
  s.addShape(p.shapes.LINE, { x: 0.75, y: yS + 0.36, w: 1.35, h: 0, line: { color: BLUE, width: 3.5, endArrowType: "triangle" } });
  sw(2.1, "S1");
  s.addShape(p.shapes.LINE, { x: 3.1, y: yS + 0.36, w: 1.9, h: 0, line: { color: RED, width: 5 } });
  sw(5.0, "S2");
  s.addShape(p.shapes.LINE, { x: 6.0, y: yS + 0.36, w: 1.9, h: 0, line: { color: RED, width: 5 } });
  s.addShape(p.shapes.OVAL, { x: 7.9, y: yS + 0.2, w: 0.34, h: 0.34, fill: { color: BLUE } });
  s.addText("ℓ dst", { x: 8.28, y: yS + 0.18, w: 0.9, h: 0.4, fontSize: 11, color: MUT, fontFace: "Calibri", valign: "middle", margin: 0 });
  s.addText("long flow ℓ", { x: 0.6, y: yS - 0.42, w: 1.6, h: 0.3, fontSize: 11.5, bold: true, color: BLUE, fontFace: "Calibri", margin: 0 });
  // link labels
  s.addText([{ text: "L1 (100G): ℓ, a, b → 3 flows", options: { bold: true, fontSize: 12, color: RED, breakLine: true } },
             { text: "R₁ settles at C/3 = 33.3 G", options: { fontSize: 12, color: INK } }],
    { x: 2.75, y: yS + 0.62, w: 2.6, h: 0.75, fontFace: "Calibri", margin: 0 });
  s.addText([{ text: "L2 (100G): ℓ (capped 33.3) + c", options: { bold: true, fontSize: 12, color: RED, breakLine: true } },
             { text: "R₂ rises until full: 66.7 G", options: { fontSize: 12, color: INK } }],
    { x: 5.75, y: yS + 0.62, w: 2.6, h: 0.75, fontFace: "Calibri", margin: 0 });
  // cross flows in
  s.addShape(p.shapes.LINE, { x: 2.3, y: yS + 1.6, w: 0.3, h: -0.85, line: { color: "8A98AC", width: 2, endArrowType: "triangle" } });
  s.addText("a, b", { x: 2.02, y: yS + 1.62, w: 0.9, h: 0.3, fontSize: 11.5, color: MUT, fontFace: "Calibri", margin: 0 });
  s.addShape(p.shapes.LINE, { x: 5.2, y: yS + 1.6, w: 0.3, h: -0.85, line: { color: "8A98AC", width: 2, endArrowType: "triangle" } });
  s.addText("c", { x: 4.95, y: yS + 1.62, w: 0.5, h: 0.3, fontSize: 11.5, color: MUT, fontFace: "Calibri", margin: 0 });
  // stamping strip
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 3.85, w: 5.55, h: 0.72, fill: { color: BLUET }, rectRadius: 0.08 });
  s.addText([
    { text: "ℓ pkt: fairRate 0 ", options: { fontSize: 12, color: MUT, fontFace: "Courier New" } },
    { text: "→ 33.3 ", options: { fontSize: 12, bold: true, color: NAVY, fontFace: "Courier New" } },
    { text: "→ min(33.3,66.7) = ", options: { fontSize: 12, color: MUT, fontFace: "Courier New" } },
    { text: "33.3", options: { fontSize: 13, bold: true, color: BLUE, fontFace: "Courier New" } },
  ], { x: 0.8, y: 3.85, w: 5.25, h: 0.72, valign: "middle", fontFace: "Courier New", margin: 0 });
  chip(s, 6.35, 3.9, 1.45, "ℓ = a = b = 33.3", PAPER, BLUE);
  chip(s, 7.9, 3.9, 1.15, "c = 66.7", PAPER, GREENOK);
  s.addText("Exactly the max-min allocation — both links 100% full, no per-flow state anywhere.", {
    x: 0.6, y: 4.85, w: 8.85, h: 0.4, fontSize: 13.5, bold: true, color: INK, fontFace: "Calibri", align: "center" });
  s.addNotes("A worked example with asymmetric contention. Link 1 carries three flows, so its RCP loop settles at a third of capacity. On link 2, the long flow arrives already capped at 33 — it offers less load, so R2 keeps rising until the link fills at 66.7 for the local cross flow. The packet picks up the minimum along its path. Result: exactly max-min — the long flow equalized where it's tightest, and the slack it can't use is automatically handed to c. No switch counted flows; no switch kept per-flow state.");
}

// ============================================================ 11 · HPCC-FS design
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "HPCC-FS", "The whole mechanism: three small pieces");
  const cols = [
    ["Switch", ["one scalar fair rate per egress port", "RCP update once per control interval (≈ RTT)", "state: 3 numbers — no per-flow data"]],
    ["Wire", ["new INT mode: one 64-bit fairRate field", "8 B / packet, independent of hop count", "each hop min-aggregates; receiver echoes"]],
    ["Sender", ["new ACK handler: rate ← path-min fairRate", "clamped to [minRate, NIC]", "rate-only: per-flow window cap off"]],
  ];
  cols.forEach((c, i) => {
    const x = 0.6 + i * 3.05;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: 2.8, h: 2.6, fill: { color: i === 1 ? BLUET : ICET }, rectRadius: 0.09, shadow: sh() });
    s.addText(c[0], { x: x + 0.24, y: 1.7, w: 2.3, h: 0.38, fontSize: 16.5, bold: true, color: NAVY, fontFace: "Calibri", margin: 0 });
    s.addText(c[1].map((t, j) => ({ text: t, options: { bullet: true, fontSize: 12, color: INK, breakLine: j < c[1].length - 1, paraSpaceAfter: 7 } })),
      { x: x + 0.24, y: 2.14, w: 2.35, h: 1.85, fontFace: "Calibri", margin: 0 });
  });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.4, w: 4.3, h: 0.55, fill: { color: NAVY }, rectRadius: 0.08 });
  s.addText("stock HPCC (cc_mode 3): byte-for-byte unchanged", { x: 0.6, y: 4.4, w: 4.3, h: 0.55, align: "center", valign: "middle", fontSize: 12, bold: true, color: PAPER, fontFace: "Calibri", margin: 0 });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 5.15, y: 4.4, w: 4.3, h: 0.55, fill: { color: ICE }, rectRadius: 0.08 });
  s.addText("an operating mode selected per traffic class — not a replacement", { x: 5.15, y: 4.4, w: 4.3, h: 0.55, align: "center", valign: "middle", fontSize: 12, bold: true, color: NAVY, fontFace: "Calibri", margin: 0 });
  s.addNotes("The full mechanism fits on one slide, and that's the point. Per egress port: one fair-rate scalar updated by the RCP rule. On the wire: a new INT mode carrying a single 64-bit field, min-aggregated hop by hop — 8 bytes per packet regardless of path length, versus 8 bytes per hop for stock HPCC. At the sender: one new ACK handler that adopts the path minimum. Two honest notes: FS mode runs rate-only — the per-flow window cap is off, and we'll show that's necessary, not incidental — and the stock code path is untouched, byte for byte.");
}

// ============================================================ 12 · headline result
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Results", "Flat at 1.0 across the whole sweep — zero PFC");
  s.addImage({ path: `${FIG}/fig_nsweep.png`, x: 0.7, y: 1.4, w: 5.85, h: 3.31 });
  const stats = [
    ["1.005×", "penalty at N = 4  (was 1.96×)", BLUE, BLUET],
    ["1.003–1.007×", "across N = 2…6, incl. the overflow regime", BLUE, BLUET],
    ["0 PFC", "every workload, every N", GREENOK, "E9F4EC"],
  ];
  stats.forEach((t, i) => {
    const y = 1.45 + i * 1.13;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.75, y, w: 2.75, h: 0.98, fill: { color: t[3] }, rectRadius: 0.09, shadow: sh() });
    s.addText([
      { text: t[0], options: { bold: true, fontSize: 19, color: t[2], fontFace: "Cambria", breakLine: true } },
      { text: t[1], options: { fontSize: 10.5, color: INK } },
    ], { x: 6.95, y: y + 0.09, w: 2.4, h: 0.84, fontFace: "Calibri", margin: 0, valign: "middle" });
  });
  s.addText("HPCC-PINT (compressed INT) still shows 1.77–1.88× — a smaller footprint is not the fix; a fair-share signal is.", {
    x: 0.7, y: 4.9, w: 8.8, h: 0.42, fontSize: 12.5, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  s.addNotes("The headline. Blue bars: HPCC-FS sits at 1.003 to 1.007 across the entire sweep — including N of 5 and 6 where stock HPCC's wire format breaks, because one field doesn't grow with path length. Zero PFC everywhere. And an important control: HPCC-PINT, which also carries a single compressed field but still carries *load*, stays at 1.8x — so it's not about telemetry size, it's about carrying a fair share instead of a load sample.");
}

// ============================================================ 13 · generalization + robustness
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Results", "It generalizes — and holds under asymmetry");
  s.addImage({ path: `${FIG}/fig_robustness.png`, x: 0.55, y: 1.55, w: 5.7, h: 2.85 });
  s.addText("six asymmetric-size / staggered-start variants at N = 4: HPCC-FS within 1.0 ± 0.012 (worst stock case 3.53× → 1.012×)", {
    x: 0.55, y: 4.5, w: 5.7, h: 0.62, fontSize: 11, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  const rows2 = [
    [{ text: "topology", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12 } },
     { text: "stock", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } },
     { text: "HPCC-FS", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } }],
    ["3-tier tree fabric", { text: "1.36×", options: { align: "center", color: RED, bold: true } }, { text: "1.003×", options: { align: "center", color: BLUE, bold: true } }],
    ["k=4 ECMP fat-tree †", { text: "1.34×", options: { align: "center", color: RED, bold: true } }, { text: "1.001×", options: { align: "center", color: BLUE, bold: true } }],
    ["parking lot N=5,6", { text: "breaks", options: { align: "center", color: RED, bold: true } }, { text: "1.006–1.007×", options: { align: "center", color: BLUE, bold: true } }],
  ];
  s.addTable(rows2, { x: 6.45, y: 1.6, w: 3.1, colW: [1.5, 0.7, 0.9], fontFace: "Calibri", fontSize: 11.5,
    color: INK, border: { pt: 0.75, color: "D5DCE6" }, fill: { color: PAPER }, rowH: 0.44, valign: "middle", margin: 0.04 });
  s.addText("† oracle-normalized (removes ECMP placement luck). Across 5 hash seeds the raw ratio is placement-dominated; HPCC-FS ≤ stock at every seed.", {
    x: 6.45, y: 3.75, w: 3.1, h: 1.1, fontSize: 10.5, italic: true, color: MUT, fontFace: "Calibri", margin: 0 });
  s.addNotes("Robustness and generalization. Left: six perturbations — asymmetric sizes, staggered starts, including the 3.5x small-flow worst case — HPCC-FS stays within about one percent of the oracle. Right: a 3-tier tree and a k=4 ECMP fat-tree, where the oracle-normalized penalty lands at 1.001; the path-min aggregation is inherently path-invariant, so ECMP needed no design work. Zero PFC across all of it.");
}

// ============================================================ 13b · coflow JCT
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Results", "The job is gated by its slowest flow: \u221221% JCT");
  s.addChart(p.charts.BAR, [
    { name: "stock HPCC", labels: ["seed 0", "seed 101", "seed 202", "seed 303", "seed 404"], values: [23.27, 22.44, 23.22, 22.33, 23.11] },
    { name: "HPCC-FS", labels: ["seed 0", "seed 101", "seed 202", "seed 303", "seed 404"], values: [17.99, 17.96, 17.99, 17.97, 17.92] },
  ], {
    x: 0.55, y: 1.45, w: 5.6, h: 3.3, barDir: "col", chartColors: [RED, BLUE],
    chartArea: { fill: { color: "FFFFFF" } }, catAxisLabelColor: MUT, valAxisLabelColor: MUT,
    valGridLine: { color: "E4E9F0", size: 0.5 }, catGridLine: { style: "none" },
    showValue: false, valAxisMaxVal: 26, valAxisMinVal: 0,
    showLegend: true, legendPos: "b", legendColor: MUT, showTitle: false,
  });
  s.addText("16-flow ring allreduce, k=4 fat-tree \u2014 JCT = slowest flow (ms), 5 ECMP hash seeds", {
    x: 0.35, y: 4.83, w: 6.0, h: 0.35, fontSize: 10.5, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  const stats = [
    ["\u221221%", "mean JCT \u2014 improves at every seed (+19.5\u2026+22.7%)", BLUE, BLUET],
    ["17.9\u201318.0 ms", "FS JCT is placement-invariant (stock 22.3\u201323.3)", BLUE, BLUET],
    ["~3\u00d7 faster", "short background flows in this mix \u2014 max-min removes the placement lottery", GREENOK, "E9F4EC"],
  ];
  stats.forEach((t, i) => {
    const y = 1.45 + i * 1.13;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.35, y, w: 3.15, h: 0.98, fill: { color: t[3] }, rectRadius: 0.09, shadow: sh() });
    s.addText([
      { text: t[0], options: { bold: true, fontSize: 17, color: t[2], fontFace: "Cambria", breakLine: true } },
      { text: t[1], options: { fontSize: 10.5, color: INK } },
    ], { x: 6.55, y: y + 0.08, w: 2.8, h: 0.86, fontFace: "Calibri", margin: 0, valign: "middle" });
  });
  s.addNotes("So what does fairness buy on a workload operators care about? Collective communication: an allreduce step finishes when its slowest flow finishes, and the slowest flows are exactly the cross-pod multi-bottleneck ones stock HPCC starves. A 16-flow ring allreduce across five ECMP hash seeds: HPCC-FS cuts job completion time about 21 percent at every seed, and makes it placement-invariant. And a nuance we like being honest about: in this mix the short background flows also got three times faster — under winner-take-all, whether a short flow wins or loses is a placement lottery; max-min removes the lottery.");
}

// ============================================================ 14 · defensibility
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Is it a trick?", "Ablation, sensitivity, and HPCC’s home turf");
  // card 1: window ablation
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.45, w: 2.85, h: 3.0, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Rate-only is necessary", options: { bold: true, fontSize: 13.5, color: NAVY, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Re-enable the per-flow window cap → 1.5–2.5×, worse with path length.", options: { fontSize: 11.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "var_win sizes the window from NIC line rate, not the path — the long flow gets window-bound below fair.", options: { fontSize: 11, color: MUT } },
  ], { x: 0.84, y: 1.65, w: 2.4, h: 2.6, fontFace: "Calibri", margin: 0, valign: "top" });
  // card 2: sensitivity
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 3.6, y: 1.45, w: 2.85, h: 3.0, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Parameters not load-bearing", options: { bold: true, fontSize: 13.5, color: NAVY, breakLine: true, paraSpaceAfter: 6 } },
    { text: "RCP defaults α = 0.4, β = 0.226 — untuned.", options: { fontSize: 11.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Sweeping α, β, startup fraction, minRate one-at-a-time: penalty stays 1.004–1.008×, PFC = 0 throughout.", options: { fontSize: 11, color: MUT } },
  ], { x: 3.84, y: 1.65, w: 2.4, h: 2.6, fontFace: "Calibri", margin: 0, valign: "top" });
  // card 3: home turf
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.6, y: 1.45, w: 2.85, h: 3.0, fill: { color: BLUET }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Home turf: not a trade-off", options: { bold: true, fontSize: 13.5, color: NAVY, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Single-bottleneck incast, 8 Gbps startup:", options: { fontSize: 11.5, color: INK, breakLine: true, paraSpaceAfter: 4 } },
    { text: "mean FCT 242 vs 259 μs", options: { bold: true, fontSize: 12, color: BLUE, breakLine: true } },
    { text: "peak queue 38 vs 143 KB", options: { bold: true, fontSize: 12, color: BLUE, breakLine: true, paraSpaceAfter: 4 } },
    { text: "beats HPCC’s FCT at ¼ the queue — fairness headline unchanged.", options: { fontSize: 11, color: MUT } },
  ], { x: 6.84, y: 1.65, w: 2.4, h: 2.6, fontFace: "Calibri", margin: 0, valign: "top" });
  s.addText("Everything regenerates deterministically from the artifact — figures and tables are built from live runs.", {
    x: 0.6, y: 4.75, w: 8.85, h: 0.4, fontSize: 12, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  s.addNotes("Three defensibility checks. One: disabling the window is necessary, not a convenience — put it back and the penalty returns, growing with path length, because HPCC's window is sized for the NIC, not the path. Two: we did not tune RCP — the textbook defaults, and one-at-a-time sweeps barely move the result. Three: the cost question — on HPCC's home turf, a single-bottleneck incast, a moderate startup rate makes HPCC-FS match or beat HPCC's FCT while holding a quarter of the queue. On what we measured, the fairness fix is not a trade-off.");
}

// ============================================================ 15 · honesty
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Positioning", "What this is — and what it isn’t");
  const L = [
    ["The mechanism is RCP; HPCC-FS is a mode, not a repair.", "We claim the diagnosis and the placement. HPCC-FS coexists with stock HPCC per traffic class; mixed classes sharing links are future work."],
    ["Simulation-only, three topology families.", "No testbed; no head-to-head with Bolt / PowerTCP (would require re-implementing them). The simulator re-port reproduces the original HPCC baselines end-to-end."],
    ["Convergence is ~4 ms, not one RTT.", "Fast and path-length-independent — the per-port estimate needs ~10² RTTs to settle."],
  ];
  L.forEach((r, i) => {
    const y = 1.5 + i * 0.98;
    numCircle(s, 0.6, y + 0.04, i + 1, NAVY);
    s.addText([
      { text: r[0] + "  ", options: { bold: true, fontSize: 14, color: INK } },
      { text: r[1], options: { fontSize: 12.5, color: MUT } },
    ], { x: 1.12, y: y - 0.06, w: 8.3, h: 0.95, fontFace: "Calibri", margin: 0 });
  });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.4, w: 8.85, h: 0.85, fill: { color: BLUET }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Future: a hybrid overlay — ", options: { bold: true, fontSize: 13.5, color: NAVY } },
    { text: "rate = min(rate_HPCC, fairRate)", options: { fontSize: 13.5, color: NAVY, fontFace: "Courier New" } },
    { text: " — keep HPCC’s precision and the fairness; needs a path-aware window.", options: { fontSize: 13.5, color: NAVY } },
  ], { x: 0.85, y: 4.47, w: 8.35, h: 0.72, fontFace: "Calibri", valign: "middle", margin: 0 });
  s.addNotes("We are deliberately explicit about scope. The mechanism is RCP — our contribution is showing where the fix has to live and that placing it there is cheap. The evaluation is simulation-only; we re-ported the HPCC simulator onto modern ns-3 and verified it reproduces the original paper's baselines before building on it. Convergence is milliseconds, not one round trip. And the natural next step is a hybrid that keeps HPCC's per-flow precision under a fair-rate ceiling — the obstacle is HPCC's NIC-sized window, which is its own interesting problem.");
}

// ============================================================ 16 · conclusion (dark)
{
  const s = p.addSlide(); s.background = { color: NAVY };
  titleBar(s, "Conclusion", "One field, one scalar — a coexisting fairness mode", true);
  const rows = [
    ["Diagnosis", "HPCC starves multi-bottleneck flows ~2× (3.5× small flows); breaks past 4 hops. Zero PFC — it’s the equilibrium.", RED],
    ["Negative result", "Five sender-only fixes fail: at η-hold, no strong move exists without the flow count N.", ICE],
    ["HPCC-FS", "A per-class mode alongside HPCC: 1.005×, zero PFC, −21% coflow JCT, stock path untouched.", BLUE],
  ];
  rows.forEach((r, i) => {
    const y = 1.55 + i * 1.0;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 2.0, h: 0.8, fill: { color: r[2] }, rectRadius: 0.08 });
    s.addText(r[0], { x: 0.6, y, w: 2.0, h: 0.8, align: "center", valign: "middle", fontSize: 13.5, bold: true,
      color: r[2] === ICE ? NAVY : PAPER, fontFace: "Calibri", margin: 0 });
    s.addText(r[1], { x: 2.85, y: y - 0.02, w: 6.6, h: 0.9, fontSize: 13, color: PAPER, fontFace: "Calibri", valign: "middle", margin: 0 });
  });
  s.addText([
    { text: "Artifact (code · paper · reproduction · data):  ", options: { fontSize: 12.5, color: "9DB2D8" } },
    { text: "github.com/UNOCourseDemo/hpcc-fs", options: { fontSize: 12.5, bold: true, color: ICE, fontFace: "Courier New" } },
  ], { x: 0.6, y: 4.75, w: 8.85, h: 0.4, fontFace: "Calibri", align: "center" });
  s.addText("Thank you — questions?", { x: 0.6, y: 5.12, w: 8.85, h: 0.4, fontSize: 15, bold: true, color: PAPER, fontFace: "Cambria", align: "center" });
  s.addNotes("To close: a real, robust fairness failure in the state of the art; evidence that the endpoint can't fix it because the endpoint can't see the flow count; and a deliberately minimal switch fix — one field, one scalar — that lands within half a percent of the max-min oracle with zero PFC, leaving stock HPCC byte-for-byte intact. Everything is in the artifact, including a full reproduction of the original HPCC baselines. Happy to take questions.");
}

// ============================================================ 17 · BACKUP: reproduction
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Backup", "The re-ported simulator reproduces SIGCOMM ’19");
  const rows = [
    [{ text: "short-flow p99 slowdown", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12 } },
     { text: "HPCC", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } },
     { text: "DCQCN", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } },
     { text: "TIMELY", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } },
     { text: "DCTCP", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } },
     { text: "PINT", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } }],
    ["WebSearch 50% load", { text: "1.9", options: { align: "center", bold: true, color: BLUE } }, { text: "13.7", options: { align: "center" } }, { text: "18.3", options: { align: "center" } }, { text: "5.7", options: { align: "center" } }, { text: "2.1", options: { align: "center" } }],
    ["FB-Hadoop 70% load", { text: "6.1", options: { align: "center", bold: true, color: BLUE } }, { text: "30.6", options: { align: "center" } }, { text: "221.9", options: { align: "center", color: RED, bold: true } }, { text: "8.4", options: { align: "center" } }, { text: "5.0", options: { align: "center" } }],
    ["PFC events (fb 70%)", { text: "0", options: { align: "center", bold: true, color: GREENOK } }, { text: "0", options: { align: "center" } }, { text: "1.12 M", options: { align: "center", color: RED, bold: true } }, { text: "0", options: { align: "center" } }, { text: "0", options: { align: "center" } }],
  ];
  s.addTable(rows, { x: 0.6, y: 1.5, w: 8.85, colW: [2.85, 1.2, 1.2, 1.2, 1.2, 1.2], fontFace: "Calibri", fontSize: 12.5,
    color: INK, border: { pt: 0.75, color: "D5DCE6" }, fill: { color: PAPER }, rowH: 0.46, valign: "middle", margin: 0.05 });
  s.addText([
    { text: "5 schemes × 2 workloads × 3 loads on a 376-node fat-tree (320 servers, 100 G NICs). ", options: { fontSize: 12.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "All of the paper’s signatures reproduce: HPCC’s short-flow tail far below DCQCN/TIMELY, sub-MB queues, zero PFC; TIMELY’s PFC explosion at load; DCTCP intermediate. Along the way we found and fixed a latent uninitialized-member bug (Node::m_node_type) exposed only at scale.", options: { fontSize: 12.5, color: MUT } },
  ], { x: 0.6, y: 3.6, w: 8.85, h: 1.5, fontFace: "Calibri", margin: 0 });
  s.addNotes("Backup: if asked whether our refactored simulator is faithful — we ran the original paper's full comparison matrix, 30 configurations, and every qualitative signature reproduces. The raw per-run configs and results are publicly archived and linked from the artifact.");
}

// ============================================================ 18 · BACKUP: mixed-size + overflow
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Backup", "Mixed-size workloads · the INT-overflow artifact");
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.5, w: 4.3, h: 3.3, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Mixed sizes (WebSearch dist.)", options: { bold: true, fontSize: 14, color: NAVY, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Long-flow mean slowdown −15%; short-path mean +45%.", options: { fontSize: 12.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "This is correct max-min: stock’s starvation of the long flow was inflating headroom that short flows enjoyed.", options: { fontSize: 12, color: MUT, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Per-class targets (beyond pure max-min) are application policy — future work.", options: { fontSize: 12, italic: true, color: MUT } },
  ], { x: 0.86, y: 1.72, w: 3.8, h: 2.9, fontFace: "Calibri", margin: 0, valign: "top" });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 5.15, y: 1.5, w: 4.3, h: 3.3, fill: { color: REDT }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Why stock ‘improves’ at N ≥ 5", options: { bold: true, fontSize: 14, color: RED, breakLine: true, paraSpaceAfter: 6 } },
    { text: "The INT header holds maxHop = 5 per-hop records. Longer paths overflow the record; the utilization estimate is computed over the wrong hops.", options: { fontSize: 12.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "The 0.51× ‘advantage’ is corrupted control input, not fairness. HPCC-FS is immune: one field, any path length.", options: { fontSize: 12, color: MUT } },
  ], { x: 5.41, y: 1.72, w: 3.8, h: 2.9, fontFace: "Calibri", margin: 0, valign: "top" });
  s.addNotes("Two common questions. Mixed sizes: yes, short flows lose some of the headroom they were borrowing from the starved long flow — that's what fairness means; policy beyond max-min is future work. And the odd N>=5 numbers for stock HPCC are an artifact: the INT record physically overflows at 5 hops, so the controller is reading garbage — that's a bug surface our single-field format simply doesn't have.");
}

p.writeFile({ fileName: "/Users/tiffanyzhang/uno-hpcc/examples/hpcc/hpcc-fs/talk/ipccc2026-talk.pptx" })
  .then(() => console.log("deck written"));
