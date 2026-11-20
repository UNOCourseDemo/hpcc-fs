// IPCCC 2026 talk deck for RDMA-RCP (formerly HPCC-FS) — generated with pptxgenjs.
// Palette (semantic): navy 1E2761 dominant; ice CADCFC tint; RED C0504D = stock HPCC / problem;
// BLUE 4F81BD = RDMA-RCP / mode (matches the paper figures' series colors).
const pptxgen = require("pptxgenjs");

const NAVY = "1E2761", ICE = "CADCFC", RED = "C0504D", BLUE = "4F81BD";
const INK = "1F2733", MUT = "5B6675", PAPER = "FFFFFF";
const REDT = "F7E9E8", BLUET = "E9F0F8", ICET = "EEF3FB", GREENOK = "1A7F37";
// Run from talk/ so relative paths (stored as image alt-text in the pptx) stay portable.
const path = require("path");
const FIG = "../figures";
const sh = () => ({ type: "outer", color: "000000", blur: 7, offset: 2, angle: 45, opacity: 0.14 });

let p = new pptxgen();
p.layout = "LAYOUT_16x9"; // 10 x 5.625
p.author = "Haoyu Wang";
p.title = "Multi-Bottleneck Fairness on RDMA Fabrics: An Empirical Study (RDMA-RCP)";

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
  s.addText("Multi-Bottleneck Fairness on RDMA Fabrics:\nAn Empirical Study", {
    x: 0.7, y: 1.7, w: 8.6, h: 1.5, fontSize: 33, bold: true, color: PAPER, fontFace: "Cambria", align: "center" });
  s.addText("RDMA-RCP — an RCP service mode over INT: one fair-rate field, one scalar per port", {
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

// ============================================================ 2b · HPCC's track record
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Background", "Why HPCC is the bar to beat: the SIGCOMM ’19 fat-tree");
  // ---- left: the topology, drawn schematically
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.55, y: 1.35, w: 4.35, h: 3.3, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
  const rows = [["16 core", 1.72], ["20 agg", 2.42], ["20 ToR", 3.12]];
  const xs = [1.62, 2.05, 2.48, 2.91, 3.34, 3.77, 4.2];
  // representative links (drawn first, under the switches)
  for (let r = 0; r < 2; r++)
    xs.forEach((x, i) => [i, i + 1].filter((j) => j < xs.length).forEach((j) =>
      s.addShape(p.shapes.LINE, { x: x + 0.12, y: rows[r][1] + 0.2, w: xs[j] - x, h: rows[r + 1][1] - rows[r][1] - 0.2, line: { color: "B9C6DE", width: 0.75 } })));
  rows.forEach(([lab, y]) => {
    s.addText(lab, { x: 0.68, y: y - 0.02, w: 0.85, h: 0.24, fontSize: 10.5, bold: true, color: NAVY, fontFace: "Calibri", margin: 0, valign: "middle" });
    xs.forEach((x) => s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w: 0.24, h: 0.2, fill: { color: NAVY }, rectRadius: 0.03 }));
    s.addText("…", { x: 4.45, y: y - 0.04, w: 0.35, h: 0.26, fontSize: 13, bold: true, color: NAVY, fontFace: "Calibri", margin: 0, valign: "middle" });
  });
  // servers: a short stack under each ToR
  xs.forEach((x) => {
    s.addShape(p.shapes.LINE, { x: x + 0.12, y: 3.32, w: 0, h: 0.2, line: { color: "B9C6DE", width: 0.75 } });
    for (let k = 0; k < 3; k++) s.addShape(p.shapes.RECTANGLE, { x: x + 0.02, y: 3.53 + k * 0.1, w: 0.2, h: 0.07, fill: { color: BLUE } });
  });
  s.addText("320 servers", { x: 0.68, y: 3.6, w: 0.9, h: 0.24, fontSize: 10.5, bold: true, color: BLUE, fontFace: "Calibri", margin: 0, valign: "middle" });
  s.addText([
    { text: "100 G server NICs · 400 G fabric links · 376 nodes", options: { fontSize: 10.5, color: INK, breakLine: true } },
    { text: "WebSearch & Hadoop traffic at 30–70% load", options: { fontSize: 10.5, color: MUT } },
  ], { x: 0.7, y: 4.02, w: 4.1, h: 0.55, fontFace: "Calibri", margin: 0, align: "center" });
  // ---- right: short-flow tail latency
  s.addChart(p.charts.BAR, [{ name: "p99 short-flow slowdown", labels: ["HPCC", "HPCC-PINT", "DCTCP", "DCQCN", "TIMELY"], values: [1.92, 2.08, 5.66, 13.72, 18.26] }], {
    x: 5.1, y: 1.3, w: 4.4, h: 2.35, barDir: "col", chartColors: [NAVY],
    chartArea: { fill: { color: "FFFFFF" } }, catAxisLabelColor: MUT, valAxisLabelColor: MUT,
    valGridLine: { color: "E4E9F0", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 10.5,
    valAxisMaxVal: 20, valAxisMinVal: 0, showLegend: false, showTitle: false, dataLabelFormatCode: "0.00",
  });
  s.addText("p99 slowdown of short flows (<3 KB), WebSearch 50% load — lower is better", {
    x: 5.1, y: 3.65, w: 4.4, h: 0.28, fontSize: 10, italic: true, color: MUT, fontFace: "Calibri", align: "center", margin: 0 });
  const st = [["~7× lower", "short-flow tail than DCQCN"], ["≤ 0.6 MB", "peak queue (others: multi-MB)"], ["0 PFC", "any load (TIMELY: 1.1 M)"]];
  st.forEach(([big, small], i) => {
    const x = 5.1 + i * 1.5;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 4.02, w: 1.38, h: 0.63, fill: { color: BLUET }, rectRadius: 0.07 });
    s.addText([
      { text: big, options: { bold: true, fontSize: 13, color: NAVY, breakLine: true } },
      { text: small, options: { fontSize: 9, color: INK } },
    ], { x: x + 0.06, y: 4.04, w: 1.26, h: 0.6, fontFace: "Calibri", margin: 0, align: "center" });
  });
  s.addText("Our reproduction on the re-ported simulator: every signature of the original paper reproduces (details in backup).", {
    x: 0.55, y: 4.85, w: 8.95, h: 0.32, fontSize: 11.5, italic: true, color: MUT, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("Before I show where HPCC breaks, let me show why it's worth studying. This is the setting of the original SIGCOMM 2019 evaluation: a three-tier fat-tree with 16 core, 20 aggregation and 20 top-of-rack switches, 320 servers with 100-gigabit NICs and 400-gigabit fabric links, running realistic web-search and Hadoop traffic. We re-ran that experiment on our simulator, and HPCC wins clearly. On the right is the latency tail for short flows, the ones applications feel most: at 50 percent load HPCC's 99th-percentile slowdown is 1.9, about seven times lower than DCQCN's 13.7 and far below TIMELY's 18. It keeps switch queues under about 0.6 megabytes while DCQCN and TIMELY build multi-megabyte queues, and it never triggers a PFC pause, where TIMELY hits over a million pauses at 70 percent load. So on the benchmarks the field uses, HPCC is the state of the art. Notice what these benchmarks have in common, though: each flow's congestion is effectively at one link. The question for the rest of this talk is what happens when a flow has to cross several congested links in a row.\n\nREADING THE CHART (right). X axis: the five congestion-control schemes, HPCC on the left. Y axis: 99th-percentile FCT slowdown of short flows (under 3 KB). Slowdown = a flow’s completion time divided by its completion time alone on an empty network, so 1.0 is perfect; the p99 value is what the slowest 1% of short flows reach. Lower is better. Setting: WebSearch at 50% load on the 320-server fat-tree, our reproduction. HPCC 1.92 versus DCQCN 13.7 and TIMELY 18.3.");
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

// ============================================================ 3b · PRIMER: the parking lot
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Primer for everyone", "The parking lot: the simplest multi-bottleneck test");
  const xs = [0.95, 2.95, 4.95, 6.95, 8.95], yS = 2.0, d = 0.46;
  // long flow across all links
  s.addShape(p.shapes.LINE, { x: 0.75, y: 1.55, w: 8.75, h: 0, line: { color: BLUE, width: 4, endArrowType: "triangle" } });
  s.addText("long flow — crosses all 4 links", { x: 2.6, y: 1.18, w: 4.8, h: 0.3, fontSize: 12.5, bold: true, color: BLUE, fontFace: "Calibri", align: "center", margin: 0 });
  // links between switches
  for (let i = 0; i < 4; i++) {
    s.addShape(p.shapes.LINE, { x: xs[i] + d, y: yS + d / 2, w: xs[i + 1] - xs[i] - d, h: 0, line: { color: "8A98AC", width: 5 } });
    s.addText("25 Gbps", { x: xs[i] + d, y: yS - 0.3, w: xs[i + 1] - xs[i] - d, h: 0.26, fontSize: 10.5, color: MUT, fontFace: "Calibri", align: "center", margin: 0 });
    // cross flow i: occupies exactly one link
    s.addShape(p.shapes.LINE, { x: xs[i] + d / 2 + 0.12, y: 2.85, w: xs[i + 1] - xs[i] - 0.24, h: 0, line: { color: RED, width: 3.5, endArrowType: "triangle" } });
    s.addText(`cross flow ${i + 1}`, { x: xs[i] + d / 2, y: 2.92, w: xs[i + 1] - xs[i], h: 0.28, fontSize: 11, bold: true, color: RED, fontFace: "Calibri", align: "center", margin: 0 });
  }
  xs.forEach((x, i) => {
    s.addShape(p.shapes.OVAL, { x, y: yS, w: d, h: d, fill: { color: NAVY } });
    s.addText(`S${i + 1}`, { x, y: yS, w: d, h: d, fontSize: 11, bold: true, color: PAPER, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  });
  s.addText([
    { text: "Every link carries exactly two flows  ⇒  max-min: ", options: { fontSize: 15, bold: true, color: INK } },
    { text: "everyone gets 12.5 Gbps", options: { fontSize: 15, bold: true, color: GREENOK } },
    { text: " — including the long flow.", options: { fontSize: 15, bold: true, color: INK } },
  ], { x: 0.6, y: 3.3, w: 8.85, h: 0.45, fontFace: "Calibri", align: "center", margin: 0 });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 3.95, w: 8.85, h: 0.95, fill: { color: REDT }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Why it’s hard", options: { bold: true, fontSize: 13.5, color: NAVY, breakLine: true, paraSpaceAfter: 3 } },
    { text: "The long flow competes at every hop; each cross flow competes once. Being fair at each link separately can still squeeze it at all of them.", options: { fontSize: 12.5, color: INK } },
  ], { x: 0.85, y: 4.0, w: 8.35, h: 0.85, fontFace: "Calibri", margin: 0, valign: "middle" });
  s.addText("Score = long flow’s completion time ÷ cross flows’.  1.0 = perfectly fair;  2.0 = it took twice as long.", {
    x: 0.6, y: 5.1, w: 8.85, h: 0.32, fontSize: 11.5, italic: true, color: MUT, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("Now the test we use throughout, the parking lot. The long flow, in blue, crosses all four links. Each red cross flow uses just one link. Our yardstick is max-min fairness: raise every flow's rate together until links fill up, so nobody can get more without taking from someone who has less. Here every link is shared by exactly two flows, so the max-min answer is simple: everyone gets half, 12.5 gigabits — the long flow included. We compute that answer exactly and call it the oracle. That's what makes this the cleanest possible test. Any gap between the long flow and the others is pure multi-bottleneck unfairness, nothing else. Why is it hard? The long flow has to compete at every hop, while each local flow competes once. A congestion controller that is perfectly reasonable at each link in isolation can still lose the long flow at all of them, and those losses compound. Our score is just the long flow's completion time divided by the cross flows': 1.0 is perfect, 2.0 means it took twice as long. Keep 2.0 in mind — that's roughly what we'll see.");
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
    { name: "HPCC\u2019s multi-rate mode (per-hop rate, send at min)", labels: ["N=2", "N=3", "N=4"], values: [1.44, 1.5, 1.75] },
  ], {
    x: 0.55, y: 1.4, w: 5.5, h: 3.5, barDir: "col", chartColors: [RED, "9BBB59"],
    chartArea: { fill: { color: "FFFFFF" } }, catAxisLabelColor: MUT, valAxisLabelColor: MUT,
    valGridLine: { color: "E4E9F0", size: 0.5 }, catGridLine: { style: "none" },
    showValue: true, dataLabelPosition: "outEnd", dataLabelColor: INK, dataLabelFontSize: 11,
    valAxisMaxVal: 2.2, valAxisMinVal: 0, showLegend: true, legendPos: "b", legendColor: MUT,
    showTitle: false, dataLabelFormatCode: "0.00",
  });
  s.addText("unfairness ratio \u2014 max-min oracle = 1.0", { x: 0.55, y: 4.95, w: 5.5, h: 0.3, fontSize: 11, italic: true, color: MUT, fontFace: "Calibri", align: "center", margin: 0 });
  s.addText("HPCC\u2019s built-in multi-bottleneck option helps \u2014 but doesn\u2019t fix it.", { x: 0.55, y: 5.2, w: 5.5, h: 0.3, fontSize: 12, bold: true, color: "6E8B3D", fontFace: "Calibri", align: "center", margin: 0 });
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
  s.addNotes("The finding: stock HPCC starves the long flow by roughly 2x at N=2 through 4, and the effect grows. The green bars are HPCC's own multi-rate mode, its built-in answer to multiple bottlenecks: it keeps a separate rate for every hop and sends at the minimum. It helps, but doesn't fix it, and it gets worse with N, because each per-hop rate is still a private copy that freezes its startup share. It's worse — 3.5x — exactly where it hurts most: small, latency-sensitive flows. And past four bottlenecks the per-hop INT record overflows its hop cap and the control input is corrupted outright. Also robust: asymmetric sizes, staggered starts, and RTT equalization don't move it — this is not RTT unfairness.\n\nREADING THE CHART. X axis: N, the number of 25 Gbps bottleneck links the long flow crosses, each with its own cross flow. Y axis: unfairness ratio = long-flow completion time divided by the mean cross-flow completion time. The max-min oracle is exactly 1.0, so 1.9 means the long flow took about twice as long. Red = stock HPCC; green = HPCC’s built-in multi-rate mode. Both grow with N.");
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
  s.addNotes("Here's what it looks like inside: four cross flows sit at 23 Gbps each while the long flow is pinned at 0.4 — for the entire contention window. The crucial observation: nothing is broken. No PFC, no loss, links at target utilization. The starvation IS the equilibrium of the control law. That reframes the problem: you can't patch a symptom; you have to change what information the control loop has.\n\nREADING THE CHART (horizontal bars). Rows (vertical axis): the five flows at N = 4, four cross flows and the long flow. Horizontal axis: each flow’s average goodput in Gbps during the contention window, the first ~18 ms, under stock HPCC. Fair share is 12.5 Gbps for every flow. The cross flows sit at about 23.2 Gbps and the long flow at about 0.38, roughly a 60× gap.");
}

// ============================================================ 7 · sender-only fixes fail
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Negative result", "Six sender-only designs — none gets close");
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
  s.addNotes("Our first instinct — and probably yours — was to fix this at the sender, keeping HPCC's stateless-switch story intact. We built five heuristic variants spanning the design space — best case 1.63, target 1.0 — and then the strongest possible sender design: a full mirror of the RCP recursion, run privately per hop from the same INT-visible inputs the switch would use. The mirror still fails: 1.56 even with synchronized starts, 1.65 or 0.81 under staggered arrival — the direction of unfairness set by arrival order — while the identical law at the switch holds 1.0. That is the next slide's story.");
}

// ============================================================ 8 · structural reason (dark emphasis)
{
  const s = p.addSlide(); s.background = { color: NAVY };
  titleBar(s, "Why", "Where the rate state lives: what the RCP mirror proves", true);
  const card = (x, head, lines, tint) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.55, w: 4.25, h: 2.55, fill: { color: PAPER }, rectRadius: 0.1, shadow: sh() });
    s.addText(head, { x: x + 0.28, y: 1.78, w: 3.7, h: 0.4, fontSize: 16, bold: true, color: tint, fontFace: "Calibri", margin: 0 });
    s.addText(lines, { x: x + 0.28, y: 2.25, w: 3.7, h: 1.7, fontFace: "Calibri", margin: 0 });
  };
  card(0.6, "1 · The η-hold equilibrium", [
    { text: "Links settle at target utilization → HPCC’s multiplicative term ≈ 1.", options: { fontSize: 12.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Every flow holds whatever rate it grabbed at startup. Additive nudges need ~10⁴ RTTs to redistribute.", options: { fontSize: 12.5, color: MUT } },
  ], RED);
  card(5.15, "2 · Private estimates never agree", [
    { text: "RCP’s inputs (C, y, q) ARE in INT. A sender-side RCP mirror (mb_mode 6) still fails: 1.56× synced, 1.65×/0.81× staggered — direction set by arrival order.", options: { fontSize: 12.5, color: INK, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Private copies of the explicit-rate recursion preserve arrival-history asymmetry; ONE shared per-link register erases it. Per-flow fair queueing: 1.97× windowed, equal-but-idle (13× oracle FCT) windowless.", options: { fontSize: 12.5, color: MUT } },
  ], RED);
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.35, w: 8.8, h: 0.85, fill: { color: BLUE }, rectRadius: 0.1, shadow: sh() });
  s.addText("A shared per-port register carries the history a private copy cannot replicate. That is why it belongs at the switch.", {
    x: 0.85, y: 4.42, w: 8.3, h: 0.72, fontSize: 16.5, bold: true, color: PAPER, fontFace: "Cambria", align: "center", valign: "middle" });
  s.addNotes("Two reasons. First, at eta-hold, HPCC's multiplicative machinery goes idle — everyone holds what they grabbed. Second — and this is the paper's sharpest experiment — the obstacle is NOT information. RCP's inputs are all sender-visible in INT, so we ran the most direct sender design: a private per-hop RCP mirror. Same law, same inputs, same gains. It still fails, and the direction of unfairness flips with arrival order — because independently maintained rate state preserves arrival-history asymmetry forever, while a shared register erases it. Per-flow fair queueing sharpens it: windowed senders leave 1.97 times; remove the window and DRR equalizes — but at thirteen times every flow's oracle completion time, equal but idle. Scheduling enforces equality; the max-min allocation — equal shares at full utilization — also needs a rate signal telling senders how much to offer. That is the corrected placement result, and it is why the rate belongs in the switch.");
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

// ============================================================ 11 · RDMA-RCP design
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "RDMA-RCP", "The whole mechanism: three small pieces");
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

// ============================================================ 11b · textbook RCP -> RDMA-RCP
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "RDMA-RCP", "What we changed from textbook RCP — and why");
  const H = (t, al) => ({ text: t, options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 11.5, align: al || "left" } });
  const ok = (t) => ({ text: t, options: { color: BLUE, bold: true, fontSize: 10 } });
  const rows = [
    [H("change vs. textbook RCP"), H("why it was needed"), H("what it bought")],
    ["Fair rate rides in one 64-bit INT field, min-aggregated per hop",
     "RDMA fabrics already speak INT; stock HPCC’s per-hop record grows with path length and overflows at 5 hops",
     ok("8 B/packet at any length; N = 5–6 still 1.006–1.007×; stock HPCC wire untouched")],
    ["Rate-only sender (or window = R · baseRTT)",
     "HPCC’s window is sized from the NIC, not the path: it caps the long flow below its fair share",
     ok("NIC window: 1.50 / 2.00 / 2.49×  →  rate-only 1.003–1.005×, R·RTT window 1.004–1.006×")],
    ["Separate cold-start rate (1 Gbps) from the rate floor (100 Mbps)",
     "Tied together, they cap fan-in at C / R = 25 senders; at 64 senders PFC fires 2,045 times",
     ok("PFC = 0 through 128 senders; bound moves to 250; every fairness result unchanged")],
    ["Control interval d = 2 × RTTmax",
     "At high fan-in the rate oscillates: only 25–50% link utilization at the default d",
     ok("utilization 0.84 / 0.70 at 64 / 128 senders, PFC-free, all fairness results kept")],
    ["Switch starts at R = C/2; integer (Q16) update, rate kept in Kbps",
     "R = C would make the first stamp line rate; ASICs have no divider; integer Mbps deadlocks floor recovery",
     ok("no startup blast; fixed point matches float (1.001–1.004×); 1 Kbps granularity")],
  ];
  s.addTable(rows, { x: 0.45, y: 1.3, w: 9.1, colW: [2.75, 3.35, 3.0], fontFace: "Calibri", fontSize: 10,
    color: INK, border: { pt: 0.75, color: "D5DCE6" }, fill: { color: PAPER }, rowH: 0.55, valign: "middle", margin: 0.05 });
  s.addText([
    { text: "Kept from textbook RCP: ", options: { bold: true, color: NAVY } },
    { text: "the update law and its defaults α = 0.4, β = 0.226 — untuned. Remaining gap: fan-in efficiency (stock HPCC 0.92).", options: { color: MUT } },
  ], { x: 0.45, y: 4.95, w: 9.1, h: 0.4, fontSize: 11.5, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("A fair question is how much of this is just RCP. The control law is textbook RCP, with its published defaults, untuned. What we had to change was everything around it, to make it work on an RDMA fabric. Five changes. One: transport. Instead of RCP's own header field, the fair rate rides in a single 64-bit INT field that each switch min-aggregates. It costs 8 bytes at any path length, so it keeps working at five and six bottlenecks, where stock HPCC's per-hop record overflows. Two: the sender runs rate-only. HPCC's window is sized from the NIC line rate, not the path, so it caps the long flow below its fair share: 1.5, 2.0, 2.5 times at two to four bottlenecks. A window that scales with the fair rate, R times base RTT, works just as well as rate-only. Three, a bug a reviewer caught: our first version used the same 1 gigabit value as both the cold-start rate and the minimum rate. That quietly limits a link to 25 senders, and at 64 senders it caused a PFC storm. Splitting them, 1 gigabit to start and a 100 megabit floor, removed it with no change to any fairness result. Four: at very high fan-in the rate oscillates and utilization drops to 25 to 50 percent. Doubling the control interval brings it to 84 and 70 percent at 64 and 128 senders, and keeps every fairness result. I'll be honest that stock HPCC still does better there, 0.92. Five: switch practicalities. The switch starts at half capacity so the first packets don't blast at line rate, and the update runs in integer fixed point with the rate stored in kilobits. Storing it in megabits deadlocks recovery from the floor, which we only found because we built the integer version.");
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
  s.addText("HPCC-PINT (compressed INT): 1.77–1.88× · PowerTCP (NSDI’22): 1.79–1.86× — neither a smaller footprint nor a newer law is the fix; a fair-share signal is.", {
    x: 0.7, y: 4.9, w: 8.8, h: 0.42, fontSize: 12.5, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  s.addNotes("The headline — and it is not just HPCC: on the same benchmark DCQCN runs 1.7 to 2.3, TIMELY 1.8 to 2.0, DCTCP 1.6 to 1.8, PowerTCP — ported from the authors' own code — 1.8 to 1.9, all growing with N. Multi-bottleneck unfairness is endemic to deployable RDMA CC. Blue bars: RDMA-RCP sits at 1.003 to 1.007 across the entire sweep — including N of 5 and 6 where stock HPCC's wire format breaks, because one field doesn't grow with path length. Zero PFC everywhere. And an important control: HPCC-PINT, which also carries a single compressed field but still carries *load*, stays at 1.8x — so it's not about telemetry size, it's about carrying a fair share instead of a load sample.\n\nREADING THE CHART. X axis: N = 2 to 6 bottleneck links. Y axis: unfairness ratio, long-flow completion time divided by short-flow completion time; the dashed line at 1.0 is the max-min oracle. Red = stock HPCC, green = multi-rate HPCC, blue = RDMA-RCP. Blue sits on the dashed line at every N (1.003–1.007). At N = 5 and 6 red and green drop to about 0.5. That is not an improvement: the 6-switch path overflows HPCC’s 5-hop INT header, and the long flow ends up favored.");
}

// ============================================================ 13 · generalization + robustness
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Results", "It generalizes — and holds under asymmetry");
  s.addImage({ path: `${FIG}/fig_robustness.png`, x: 0.55, y: 1.55, w: 5.7, h: 2.85 });
  s.addText("six asymmetric-size / staggered-start variants at N = 4: RDMA-RCP within 1.0 ± 0.012 (worst stock case 3.53× → 1.012×); start-jitter ensembles: stock 1.96–1.99×, RDMA-RCP 1.008–1.017×", {
    x: 0.55, y: 4.5, w: 5.7, h: 0.62, fontSize: 11, italic: true, color: MUT, fontFace: "Calibri", align: "center" });
  const rows2 = [
    [{ text: "topology", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12 } },
     { text: "stock", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } },
     { text: "RDMA-RCP", options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: "center" } }],
    ["3-tier tree fabric", { text: "1.36×", options: { align: "center", color: RED, bold: true } }, { text: "1.003×", options: { align: "center", color: BLUE, bold: true } }],
    ["k=4 ECMP fat-tree †", { text: "1.34×", options: { align: "center", color: RED, bold: true } }, { text: "1.001×", options: { align: "center", color: BLUE, bold: true } }],
    ["parking lot N=5,6", { text: "breaks", options: { align: "center", color: RED, bold: true } }, { text: "1.006–1.007×", options: { align: "center", color: BLUE, bold: true } }],
  ];
  s.addTable(rows2, { x: 6.45, y: 1.6, w: 3.1, colW: [1.5, 0.7, 0.9], fontFace: "Calibri", fontSize: 11.5,
    color: INK, border: { pt: 0.75, color: "D5DCE6" }, fill: { color: PAPER }, rowH: 0.44, valign: "middle", margin: 0.04 });
  s.addText("† oracle-normalized (removes ECMP placement luck). Across 5 hash seeds the raw ratio is placement-dominated; RDMA-RCP ≤ stock at 4 of 5 seeds (the 5th is uncontended).", {
    x: 6.45, y: 3.75, w: 3.1, h: 1.1, fontSize: 10.5, italic: true, color: MUT, fontFace: "Calibri", margin: 0 });
  s.addNotes("Robustness and generalization. Left: six perturbations — asymmetric sizes, staggered starts, including the 3.5x small-flow worst case — RDMA-RCP stays within about one percent of the oracle. Right: a 3-tier tree and a k=4 ECMP fat-tree, where the oracle-normalized penalty lands at 1.001; the path-min aggregation is inherently path-invariant, so ECMP needed no design work. Zero PFC across all of it.\n\nREADING THE CHART (left, horizontal bars). Rows: six N = 4 workload variants, from top: symmetric 50 MB; a big 200 MB long flow; a small 10 MB long flow; a 200 MB long flow against 10 MB cross flows; the long flow starting 3 ms early; the long flow joining late. Horizontal axis: relative penalty = the long-path flow’s slowdown divided by the short-path flows’ slowdown; the dashed line at 1.0 is the oracle. Red = stock HPCC, blue = RDMA-RCP. Blue stays within 1.0 ± 0.012 in every row. Red is about 1.8–2.0, and 3.53 for the small long flow.");
}

// ============================================================ 13b · coflow JCT
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Results", "The job is gated by its slowest flow: \u221218\u201323% JCT");
  s.addChart(p.charts.BAR, [
    { name: "stock HPCC", labels: ["seed 0", "seed 101", "seed 202", "seed 303", "seed 404"], values: [23.27, 22.44, 23.22, 22.33, 23.11] },
    { name: "RDMA-RCP", labels: ["seed 0", "seed 101", "seed 202", "seed 303", "seed 404"], values: [17.99, 17.96, 17.99, 17.97, 17.92] },
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
    ["\u221218\u201323%", "JCT, every seed tested \u2014 \u221218% with the INT header padded to stock size", BLUE, BLUET],
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
  s.addNotes("So what does fairness buy on a workload operators care about? Collective communication: an allreduce step finishes when its slowest flow finishes, and the slowest flows are exactly the cross-pod multi-bottleneck ones stock HPCC starves. A 16-flow ring coflow — one phase of a ring allreduce — across five ECMP hash seeds: RDMA-RCP cuts completion time 18 to 23 percent at every seed tested, and 18 percent survives padding the INT header to stock size, so the gain is fairness, not header thinness. On a saturating k-equals-6 fabric with 108 inter-pod flows, makespan improves 14 percent — 11 with the header padded — with Jain's index rising and zero PFC at 45 switches. And it compounds: the full 30-phase allreduce, scheduled with real per-rank pipelined dependencies rather than global barriers, finishes 21 percent sooner end-to-end — 22 barrier-synchronized, 17 with the padded header — stable across three ECMP placements. And the short background flows got three times faster — under near-winner-take-all dynamics, a short flow's fate is a placement lottery; max-min removes it.\n\nREADING THE CHART. X axis: five ECMP hash seeds; each seed is a different placement of the 16 flows onto fat-tree paths. Y axis: job completion time (JCT) of one ring-allreduce phase in milliseconds, i.e. when the slowest of the 16 flows finishes. Lower is better. Red = stock HPCC, 22.3–23.3 ms; blue = RDMA-RCP, 17.9–18.0 ms at every seed. That is a 19.5–22.7% cut, nearly identical across placements.");
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
  s.addNotes("Three defensibility checks. One: disabling the window is necessary, not a convenience — put it back and the penalty returns, growing with path length, because HPCC's window is sized for the NIC, not the path. Two: we did not tune RCP — the textbook defaults, and one-at-a-time sweeps barely move the result. Three: the cost question — on HPCC's home turf, a single-bottleneck incast, a moderate startup rate makes RDMA-RCP match or beat HPCC's FCT while holding a quarter of the queue. On what we measured, the fairness mode is not a trade-off.");
}

// ============================================================ 14b · head-to-head: who is better at what
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Head to head", "HPCC vs. RDMA-RCP: each wins somewhere");
  const col = (x, head, tint, bg, items) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.3, w: 4.35, h: 2.95, fill: { color: bg }, rectRadius: 0.09, shadow: sh() });
    s.addText(head, { x: x + 0.22, y: 1.42, w: 3.9, h: 0.36, fontSize: 15, bold: true, color: tint, fontFace: "Calibri", margin: 0 });
    s.addText(items.map(([a, b], j) => [
      { text: a, options: { bullet: true, bold: true, fontSize: 12.5, color: INK, paraSpaceAfter: 5 } },
      { text: b, options: { softBreakBefore: true, fontSize: 11, color: MUT, breakLine: j < items.length - 1 } },
    ]).flat(), { x: x + 0.22, y: 1.85, w: 3.95, h: 2.3, fontFace: "Calibri", margin: 0, valign: "top" });
  };
  col(0.55, "RDMA-RCP is better at", BLUE, BLUET, [
    ["Multi-bottleneck fairness", "1.003–1.007× vs. 1.9–2.0× (3.5× small flows)"],
    ["Every flow near its fair share", "within 5–13% of oracle vs. 1.4–2.9× spread"],
    ["Collective job time", "−18–23% ring step; −21% full allreduce"],
    ["Long paths", "one 8 B field at any length; HPCC breaks at 5 hops"],
    ["Predictability", "same job time at every ECMP placement"],
  ]);
  col(5.1, "Stock HPCC is better at", RED, REDT, [
    ["High fan-in (64–128 senders)", "0.92 utilization vs. 0.25–0.47 (0.70–0.84 tuned)"],
    ["Reaction speed", "per-ACK, within one RTT vs. ~0.6 ms to settle"],
    ["Short flows at default settings", "line-rate start vs. 1 Gbps cold start (~15% FCT)"],
    ["Simple switches", "stateless INT stamping vs. per-port rate logic"],
    ["Sharing a link", "runs alone; RCP needs its own slice"],
  ]);
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.55, y: 4.4, w: 8.9, h: 0.85, fill: { color: NAVY }, rectRadius: 0.09 });
  s.addText([
    { text: "One real trade-off: ", options: { bold: true, color: ICE } },
    { text: "fairness needs shared per-link rate state, which costs reaction speed and switch logic. ", options: { color: PAPER } },
    { text: "The rest are tunable: control interval, startup rate, window, per-class telemetry.", options: { color: "9DB2D8" } },
  ], { x: 0.8, y: 4.4, w: 8.4, h: 0.85, fontSize: 12.5, fontFace: "Calibri", valign: "middle", margin: 0 });
  s.addNotes("So which is better? Neither, across the board. RDMA-RCP wins on everything fairness touches: the multi-bottleneck penalty drops from about two times to about one percent, every flow lands within 5 to 13 percent of its fair completion time, collective jobs finish 18 to 23 percent sooner, it keeps working on long paths where HPCC's telemetry overflows, and job time stops depending on where ECMP happened to place the flows. HPCC wins on speed and simplicity: under heavy incast, 64 or more senders into one link, it keeps the link 92 percent busy while our mode drops well below that; it reacts within one round trip instead of settling over about half a millisecond; short flows start at line rate; and its switches only stamp telemetry, with no per-port computation. Are these trade-offs? Only one is fundamental. Fairness across several bottlenecks needs one shared fair rate per link, and that shared state costs reaction speed and switch logic. Everything else is an engineering knob we measured: a longer control interval recovers most of the fan-in loss, a faster startup beats HPCC on its own incast benchmark, a fair-rate-sized window restores a hard cap, and per-class telemetry would let the two coexist.");
}

// ============================================================ 14c · which to use when
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Which to use when", "Match the controller to the traffic");
  const card = (x, w, head, tint, bg, items, foot) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.3, w, h: 3.4, fill: { color: bg }, rectRadius: 0.09, shadow: sh() });
    s.addText(head, { x: x + 0.2, y: 1.42, w: w - 0.4, h: 0.36, fontSize: 14.5, bold: true, color: tint, fontFace: "Calibri", margin: 0 });
    s.addText(items.map(([a, b], j) => [
      { text: a, options: { bullet: true, bold: true, fontSize: 12, color: INK, paraSpaceAfter: 14 } },
      { text: b, options: { softBreakBefore: true, fontSize: 11, color: MUT, breakLine: j < items.length - 1 } },
    ]).flat(), { x: x + 0.2, y: 1.85, w: w - 0.35, h: 2.3, fontFace: "Calibri", margin: 0, valign: "top" });
    s.addText(foot, { x: x + 0.2, y: 4.2, w: w - 0.4, h: 0.42, fontSize: 10, italic: true, color: tint, fontFace: "Calibri", margin: 0, valign: "middle" });
  };
  card(0.55, 3.0, "Choose RDMA-RCP for", BLUE, BLUET, [
    ["ML collectives across pods", "a step ends with its slowest flow"],
    ["Many contended hops per path", "multi-tier, long paths"],
    ["Tenants that need a predictable share", "fair rate, placement-independent"],
  ], "on its own fabric or slice");
  card(3.7, 3.0, "Choose stock HPCC for", RED, REDT, [
    ["Incast-heavy storage & aggregation", "64+ senders into one link"],
    ["Latency-critical short RPCs", "line-rate start, per-RTT reaction"],
    ["Switches without stateful per-port logic", "INT stamping only"],
  ], "the single-bottleneck regime it was built for");
  card(6.85, 2.6, "Need both? Slice it", NAVY, ICET, [
    ["Per-class telemetry", "each controller sees only its class"],
    ["Collectives → RCP class", "incast and RPCs → HPCC class"],
    ["Future: one hybrid", "rate = min(HPCC rate, fair rate)"],
  ], "unsliced sharing fails, even under DRR");
  s.addText("Guidance follows from what we measured in simulation; a hardware deployment is the next step.", {
    x: 0.55, y: 4.85, w: 8.9, h: 0.35, fontSize: 11.5, italic: true, color: MUT, fontFace: "Calibri", align: "center", margin: 0 });
  s.addNotes("Turning those differences into advice. Use RDMA-RCP where fairness across several links decides the outcome. The clearest case is ML training across pods: an allreduce step finishes only when its slowest flow does, and the slow flows are exactly the multi-bottleneck ones HPCC squeezes. The same goes for any traffic that crosses many contended tiers, and for multi-tenant fabrics where a tenant should get a predictable share no matter where ECMP puts it. Run it on its own fabric or slice. Keep stock HPCC where its strengths matter: incast-heavy storage and partition-aggregate traffic with dozens of senders into one link, latency-critical short RPCs that benefit from line-rate start and per-round-trip reaction, and switches that can stamp telemetry but can't run per-port rate logic. If one fabric needs both, slice it: give each class its own telemetry so neither controller is misled by the other's traffic, send collectives to the RCP class and incast and RPCs to the HPCC class. We measured that simply sharing a link fails, even with a weighted scheduler. Longer term, the hybrid in our future work would cap HPCC at the fair rate and keep both properties. To be clear, this guidance comes from our simulation results; validating it on hardware is the next step.");
}

// ============================================================ 15 · honesty
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Positioning", "What this is — and what it isn’t");
  const L = [
    ["The mechanism is RCP; RDMA-RCP is a mode, not a repair.", "We claim the measurement and the placement. Coexistence needs sliced telemetry: even a 50/50 DWRR reservation cannot help a class whose controller reads port-global signals."],
    ["Simulation-only, three topology families.", "No testbed; no head-to-head with Bolt. PowerTCP — ported from the authors’ reference code and port-validated — is in the endemic table at 1.79–1.86×. The simulator re-port reproduces the original HPCC baselines end-to-end."],
    ["Convergence is sub-ms, not one RTT.", "Within 5% of fair share in ~0.6 ms (~30 RTTs); path-length-independent."],
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
  s.addNotes("We are deliberately explicit about scope. The mechanism is RCP — our contribution is showing where the fix has to live and that placing it there is cheap. The evaluation is simulation-only; we re-ported the HPCC simulator onto modern ns-3 and verified it reproduces the original paper's baselines before building on it. If asked about PowerTCP: it IS evaluated — we ported the authors' reference implementation, validated it solo and pairwise, and it shows the same multi-bottleneck gap, 1.79 to 1.86. Bolt remains the one modern scheme we did not port. Convergence is milliseconds, not one round trip. And the natural next step is a hybrid that keeps HPCC's per-flow precision under a fair-rate ceiling — the obstacle is HPCC's NIC-sized window, which is its own interesting problem.");
}

// ============================================================ 16 · conclusion (dark)
{
  const s = p.addSlide(); s.background = { color: NAVY };
  titleBar(s, "Conclusion", "One field, one scalar — a coexisting fairness mode", true);
  const rows = [
    ["Diagnosis", "Every evaluated scheme is unfair to the multi-bottleneck flow (1.6–2.3× — DCQCN, TIMELY, DCTCP, HPCC, PowerTCP); HPCC is near-winner-take-all (3.5× small flows), breaks past 4 hops. Zero PFC — it’s the equilibrium.", RED],
    ["Negative result", "Six sender-only designs fail — incl. a full RCP mirror. Per-flow FQ equalizes only what senders offer: 1.97× windowed, equal-but-idle windowless.", ICE],
    ["RDMA-RCP", "A fabric/slice mode alongside HPCC: 1.005×, flows within 5–13% of oracle (hetero cases), zero PFC, −18–23% coflow JCT. Q16 fixed-point verified; high fan-in needs a longer control interval.", BLUE],
  ];
  rows.forEach((r, i) => {
    const y = 1.55 + i * 1.0;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 2.0, h: 0.8, fill: { color: r[2] }, rectRadius: 0.08 });
    s.addText(r[0], { x: 0.6, y, w: 2.0, h: 0.8, align: "center", valign: "middle", fontSize: 13.5, bold: true,
      color: r[2] === ICE ? NAVY : PAPER, fontFace: "Calibri", margin: 0 });
    s.addText(r[1], { x: 2.85, y: y - 0.02, w: 6.6, h: 0.9, fontSize: 13, color: PAPER, fontFace: "Calibri", valign: "middle", margin: 0 });
  });
  s.addText([
    { text: "Artifact: ", options: { fontSize: 12.5, color: "9DB2D8" } },
    { text: "github.com/UNOCourseDemo/hpcc-fs", options: { fontSize: 12.5, bold: true, color: ICE, fontFace: "Courier New" } },
    { text: "   ·   raw data DOI ", options: { fontSize: 12.5, color: "9DB2D8" } },
    { text: "10.6084/m9.figshare.34330836", options: { fontSize: 12.5, bold: true, color: ICE, fontFace: "Courier New" } },
  ], { x: 0.6, y: 4.75, w: 8.85, h: 0.4, fontFace: "Calibri", align: "center" });
  s.addText("Thank you — questions?", { x: 0.6, y: 5.12, w: 8.85, h: 0.4, fontSize: 15, bold: true, color: PAPER, fontFace: "Cambria", align: "center" });
  s.addNotes("To close: a real, robust fairness failure in the state of the art; evidence that the endpoint can't fix it because the endpoint can't see the flow count; and a deliberately minimal switch mode — one field, one scalar — that lands within about one percent of the max-min oracle with zero PFC, leaving stock HPCC byte-for-byte intact. One caveat we measured and report: on an unreserved shared queue the two modes do not each get a fair share, and even a weighted-DRR reservation cannot fix it — both controllers still read port-global telemetry. Coexistence needs sliced signals or a separate fabric. Everything is in the artifact, including a full reproduction of the original HPCC baselines. Happy to take questions.");
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
    { text: "The 0.51× ‘advantage’ is corrupted control input, not fairness. RDMA-RCP is immune: one field, any path length.", options: { fontSize: 12, color: MUT } },
  ], { x: 5.41, y: 1.72, w: 3.8, h: 2.9, fontFace: "Calibri", margin: 0, valign: "top" });
  s.addNotes("Two common questions. Mixed sizes: yes, short flows lose some of the headroom they were borrowing from the starved long flow — that's what fairness means; policy beyond max-min is future work. And the odd N>=5 numbers for stock HPCC are an artifact: the INT record physically overflows at 5 hops, so the controller is reading garbage — that's a bug surface our single-field format simply doesn't have.");
}

// ============================================================ 19 · BACKUP: dataplane feasibility
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Backup", "Can a switch ASIC run this? The Q16 fixed-point check");
  const cards = [
    ["What the port needs", [
      "3 registers: fair rate R, timestamp, byte snapshot",
      "dequeue-triggered update: 2 multiplies, 2 subtractions, a clamp",
      "per packet: one 64-bit compare-and-write (path-min)"]],
    ["Fixed-point build (fs_fixed_point)", [
      "Q16 multiplier; precomputed 1/C and \u03b2/(dC)",
      "reciprocal of the elapsed interval: shift + 8-entry mantissa LUT (\u2264 25% max error)",
      "no divider anywhere on the update path"]],
    ["Same results as float", [
      "N-sweep 1.001\u20131.004\u00d7 (float: 1.003\u20131.005\u00d7)",
      "ring JCT within 0.9%; damped fan-in 0.81 vs 0.84",
      "idle ports: update idles to 2\u00b2\u2070\u00b7d \u2014 probe 0.378 vs 0.373 ms"]],
  ];
  cards.forEach((c, i) => {
    const x = 0.6 + i * 3.05;
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: 2.8, h: 2.75, fill: { color: i === 2 ? BLUET : ICET }, rectRadius: 0.09, shadow: sh() });
    s.addText(c[0], { x: x + 0.22, y: 1.68, w: 2.4, h: 0.55, fontSize: 13.5, bold: true, color: NAVY, fontFace: "Calibri", margin: 0 });
    s.addText(c[1].map((t, j) => ({ text: t, options: { bullet: true, fontSize: 10.5, color: INK, breakLine: j < c[1].length - 1, paraSpaceAfter: 6 } })),
      { x: x + 0.22, y: 2.2, w: 2.45, h: 1.95, fontFace: "Calibri", margin: 0 });
  });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.45, w: 8.85, h: 0.75, fill: { color: REDT }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "One real hazard found: ", options: { bold: true, fontSize: 12.5, color: RED } },
    { text: "an R register in integer Mbps deadlocks floor recovery (growth truncates below ~2.5 Mbps). Kbps units remove it \u2014 we make 1 Kbps the required granularity; 32-bit unsigned Kbps spans 4.3 Tbps.", options: { fontSize: 12, color: INK } },
  ], { x: 0.85, y: 4.5, w: 8.35, h: 0.65, fontFace: "Calibri", valign: "middle", margin: 0 });
  s.addNotes("For the dataplane-feasibility question: we did not build a Tofino prototype, and we say so \u2014 whether the interval test and rate update serialize inside one atomic stage is explicitly unverified, as is dequeue-time queue-depth access. What we did do is remove every arithmetic excuse: a divider-free Q16 integer build of the whole update \u2014 shift-plus-mantissa reciprocal, max error twenty-five percent \u2014 reproduces the headline results within a tenth of a percent penalty. And the exercise caught a genuine deployment hazard: keep the rate register in integer megabits and the floor-recovery path deadlocks \u2014 growth truncates to zero below about 2.5 megabits. Units, not width, were the binding choice: kilobit granularity fixes it, and 32 bits of Kbps still spans 4.3 terabits. That hazard is exactly the kind of thing you want to find in simulation before tape-out.");
}

// ============================================================ 20 · BACKUP: HPCC's rate update
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Backup", "How HPCC lowers and raises its rate");
  // the rule
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.35, w: 8.85, h: 0.85, fill: { color: ICET }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "R_new = R_ref · (η / U) + R_AI", options: { fontSize: 22, bold: true, color: NAVY, fontFace: "Cambria", breakLine: true } },
    { text: "U = max over hops of u_i (from INT), EWMA over one RTT · η = 0.95 · R_AI = 40 Mb/s", options: { fontSize: 11.5, color: MUT, fontFace: "Calibri" } },
  ], { x: 0.85, y: 1.38, w: 8.4, h: 0.8, valign: "middle", margin: 0 });
  // down / up / hold table
  const hdr = (t, al) => ({ text: t, options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 12, align: al || "left" } });
  const rows = [
    [hdr("case"), hdr("what happens"), hdr("example", "center")],
    [{ text: "Down: U > η", options: { bold: true, color: RED } }, "factor η/U < 1 — cut in proportion to the overload", { text: "U = 1.10 → ×0.86", options: { align: "center" } }],
    [{ text: "Up: U < η", options: { bold: true, color: BLUE } }, "factor η/U > 1 — multiplicative growth into the headroom, plus R_AI", { text: "U = 0.50 → ×1.9", options: { align: "center" } }],
    [{ text: "Hold: U ≈ η", options: { bold: true, color: NAVY } }, "factor ≈ 1 — only +40 Mb/s; the small overshoot is cut back (~×0.99)", { text: "η-hold", options: { align: "center", bold: true } }],
  ];
  s.addTable(rows, { x: 0.6, y: 2.38, w: 8.85, colW: [1.75, 5.35, 1.75], fontFace: "Calibri", fontSize: 11.5,
    color: INK, border: { pt: 0.75, color: "D5DCE6" }, fill: { color: PAPER }, rowH: 0.4, valign: "middle", margin: 0.06 });
  s.addText("Timing: one committed update per RTT (reference R_ref); every other ACK reacts against R_ref without compounding. Packets are paced at R, in-flight bytes capped by W = W_max · R / NIC.", {
    x: 0.6, y: 4.08, w: 8.85, h: 0.4, fontSize: 10.5, italic: true, color: MUT, fontFace: "Calibri", margin: 0 });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 4.6, w: 8.85, h: 0.72, fill: { color: REDT }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Why the long flow loses: ", options: { bold: true, fontSize: 12.5, color: RED } },
    { text: "down — U is the max over its N hops, so any link’s overshoot cuts it; up — everyone grows by the same factor + the same R_AI, so ratios persist; hold — the factor is 1, nothing redistributes.", options: { fontSize: 12, color: INK } },
  ], { x: 0.85, y: 4.63, w: 8.35, h: 0.66, fontFace: "Calibri", valign: "middle", margin: 0 });
  s.addNotes("If someone asks how HPCC actually moves its rate: it is one rule for both directions. The sender takes the utilization of the busiest hop on its path from INT, divides the target eta by it, and scales its reference rate by that factor, plus a small 40 megabit additive step. Over target, the factor is below one and the cut is proportional to the overload. Under target, the factor is above one and the rate grows multiplicatively into the headroom. At exactly eta the factor is one and only the additive step remains — that is the eta-hold. The rate is committed once per RTT; intermediate ACKs react against the committed value so one congestion event is not counted many times. For the multi-bottleneck flow, all three cases work against it: it takes the max over N hops on the way down, gets only the same proportional growth on the way up, and at hold nothing moves.");
}

// ============================================================ 21 · BACKUP: the six sender-only designs
{
  const s = p.addSlide(); s.background = { color: PAPER };
  titleBar(s, "Backup", "Inside the six sender-only designs");
  const hdr = (t, al) => ({ text: t, options: { bold: true, color: PAPER, fill: { color: NAVY }, fontSize: 11, align: al || "left" } });
  const res = (t) => ({ text: t, options: { align: "center", bold: true, color: RED } });
  const rows = [
    [hdr("mb_mode · design"), hdr("change to R = R·(1/c) + R_AI"), hdr("N=4", "center"), hdr("why it fails")],
    ["1 · k-aware AI", "R_AI × γ·k  (k = congested hops on the path)", res("1.63×"), "additive: ~10⁴ RTTs to close the gap (best at γ = 50)"],
    ["2 · max/mean blend", "U = (1−γ)·max u_i + γ·mean u_i", res("1.95×"), "at hold every u_i ≈ η — blend changes nothing"],
    ["3 · responsibility MD", "cut = 1 − share·(1 − 1/c)", res("1.89×"), "MD rarely fires at η-hold"],
    ["4 · k-th-root MD", "cut = (1/c)^(1/k)", res("1.92×"), "MD rarely fires at η-hold"],
    ["5 · share-aware AI", "R_AI × 2γ(1 − share) for every flow", res("1.71×"), "still additive — too slow"],
    ["6 · private RCP mirror", "run the switch’s RCP law per hop from own INT samples; send at min R̂_i", res("1.56×"), "private state keeps arrival history: 1.65× / 0.81× staggered"],
  ];
  s.addTable(rows, { x: 0.45, y: 1.35, w: 9.1, colW: [2.0, 3.4, 0.75, 2.95], fontFace: "Calibri", fontSize: 10.5,
    color: INK, border: { pt: 0.75, color: "D5DCE6" }, fill: { color: PAPER }, rowH: 0.42, valign: "middle", margin: 0.05 });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.45, y: 4.5, w: 9.1, h: 0.75, fill: { color: BLUET }, rectRadius: 0.09, shadow: sh() });
  s.addText([
    { text: "Same RCP law at the switch: 1.003–1.008×. ", options: { bold: true, fontSize: 12.5, color: BLUE } },
    { text: "Modes 1–5 fight η-hold with knobs it ignores; mode 6 has the right law but private state. mb_mode 0 is byte-identical to stock HPCC.", options: { fontSize: 12, color: INK } },
  ], { x: 0.7, y: 4.55, w: 8.6, h: 0.65, fontFace: "Calibri", valign: "middle", margin: 0 });
  s.addNotes("If asked what exactly we tried at the sender: every design is a small change to HPCC's own update, behind an mb_mode knob, with mode zero byte-identical to stock. Modes one and five boost the additive step — for multi-hop flows, or for flows with a small share — but additive recovery needs on the order of ten thousand RTTs; best case 1.63. Mode two blends the max-hop utilization with the mean, but at eta-hold every hop reads about eta, so the blend changes nothing: 1.95. Modes three and four soften the multiplicative decrease for the multi-hop flow, but the decrease barely fires at the hold point: 1.89 and 1.92. Mode six is the strongest: the sender runs the switch's exact RCP recursion privately, per hop, from its own INT samples, and sends at the minimum. It still reaches only 1.56 synchronized, and 1.65 or 0.81 when one side arrives late — the direction set by arrival order. The identical law in the switch holds 1.0. That is the placement result: same law, same inputs, different location of state.");
}

p.writeFile({ fileName: "ipccc2026-talk.pptx" })
  .then(() => console.log("deck written"));
