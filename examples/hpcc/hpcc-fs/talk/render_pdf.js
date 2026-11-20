// Render the deck defined in build_deck.js straight to PDF, without PowerPoint.
//
// build_deck.js is executed against a recording stand-in for pptxgenjs; every
// slide element (text, shapes, lines, images, tables, bar charts, notes) is laid
// out as absolutely-positioned HTML at 96 px/in, then headless Chrome prints:
//   ipccc2026-talk.pdf        one 10 x 5.625 in page per slide
//   ipccc2026-talk-notes.pdf  letter pages: slide on top, speaker notes below
// It also rebuilds ipccc2026-talk.pptx (via build_deck.js) so all three stay in sync.
// Usage (from talk/): node render_pdf.js
const fs = require("fs");
const path = require("path");
const os = require("os");
const { execFileSync } = require("child_process");
const Module = require("module");

const HERE = __dirname;
const PX = 96; // px per inch
const PT = 96 / 72; // px per point
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const DFONTS = "/Applications/Microsoft PowerPoint.app/Contents/Resources/DFonts";

// ---------------------------------------------------------------- recorder
let PRES = null;
class Slide {
  constructor() { this.items = []; this.background = null; this.notes = ""; }
  addText(t, o) { this.items.push({ k: "text", t, o: o || {} }); }
  addShape(type, o) { this.items.push({ k: "shape", type, o: o || {} }); }
  addImage(o) { this.items.push({ k: "image", o }); }
  addTable(rows, o) { this.items.push({ k: "table", rows, o: o || {} }); }
  addChart(type, data, o) { this.items.push({ k: "chart", type, data, o: o || {} }); }
  addNotes(n) { this.notes = n; }
}
class Pres {
  constructor() {
    PRES = this; this.slides = [];
    this.shapes = { RECTANGLE: "rect", ROUNDED_RECTANGLE: "roundRect", OVAL: "ellipse", LINE: "line" };
    this.charts = { BAR: "bar" };
  }
  addSlide() { const s = new Slide(); this.slides.push(s); return s; }
  writeFile() { return { then: () => {} }; }
}
const origLoad = Module._load;
Module._load = function (req, ...rest) {
  return req === "pptxgenjs" ? Pres : origLoad.call(this, req, ...rest);
};
process.chdir(HERE);
require(path.join(HERE, "build_deck.js"));
Module._load = origLoad;

// ---------------------------------------------------------------- helpers
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const col = (c, d = "000000") => "#" + (c || d);
const fam = (f) => {
  if (!f || f === "Calibri") return "'Calibri', 'Helvetica Neue', Arial, sans-serif";
  if (f === "Cambria") return "'Cambria', Georgia, serif";
  if (f === "Courier New") return "'Courier New', Courier, monospace";
  return `'${f}', sans-serif`;
};
const b64 = (p) => fs.readFileSync(p).toString("base64");
const imgCache = {};
const imgURI = (p) => {
  const abs = path.resolve(HERE, p);
  if (!imgCache[abs]) imgCache[abs] = "data:image/png;base64," + b64(abs);
  return imgCache[abs];
};

function runStyle(o) {
  const st = [];
  st.push(`font-size:${(o.fontSize || 18) * PT}px`);
  if (o.bold) st.push("font-weight:700");
  if (o.italic) st.push("font-style:italic");
  st.push(`color:${col(o.color)}`);
  st.push(`font-family:${fam(o.fontFace)}`);
  if (o.charSpacing) st.push(`letter-spacing:${o.charSpacing * PT}px`);
  return st.join(";");
}

// split pptxgenjs text content into paragraphs of styled runs
function paragraphs(content, base) {
  const paras = []; let cur = [];
  const close = () => { paras.push(cur); cur = []; };
  const runs = Array.isArray(content) ? content : [{ text: content, options: {} }];
  runs.forEach((r, i) => {
    const o = Object.assign({}, base, r.options || {});
    if (o.softBreakBefore) cur.push({ br: true, o });
    const lines = String(r.text).split("\n");
    lines.forEach((ln, j) => {
      cur.push({ text: ln, o });
      if (j < lines.length - 1) close();
    });
    if (o.breakLine && i < runs.length - 1) close();
  });
  if (cur.length) close();
  return paras;
}

function textBlock(content, o) {
  const paras = paragraphs(content, o);
  return paras.map((p) => {
    const po = p[0] ? p[0].o : o;
    const st = [`text-align:${po.align === "center" ? "center" : po.align === "right" ? "right" : "left"}`, "margin:0"];
    if (po.paraSpaceAfter) st.push(`margin-bottom:${po.paraSpaceAfter * PT}px`);
    let inner = p.map((r) => r.br ? "<br>" : `<span style="${runStyle(r.o)}">${esc(r.text) || "&#8203;"}</span>`).join("");
    if (po.bullet) {
      st.push(`padding-left:${16 * PT}px;text-indent:${-10 * PT}px`);
      inner = `<span style="${runStyle(po)}">•&nbsp;&nbsp;</span>` + inner;
    }
    return `<p style="${st.join(";")}">${inner}</p>`;
  }).join("");
}

function box(o, inner, extra = "") {
  const v = o.valign === "top" ? "flex-start" : o.valign === "bottom" ? "flex-end" : "center";
  const m = o.margin === undefined ? [0.05, 0.1] : [0, 0];
  return `<div style="position:absolute;left:${o.x * PX}px;top:${o.y * PX}px;width:${o.w * PX}px;height:${o.h * PX}px;` +
    `display:flex;flex-direction:column;justify-content:${v};padding:${m[0] * PX}px ${m[1] * PX}px;box-sizing:border-box;` +
    `line-height:1.17;overflow:visible;${extra}">${inner}</div>`;
}

const SHADOW = "box-shadow:2px 2px 7px rgba(0,0,0,0.14);";
function shape(type, o) {
  if (type === "line") {
    const x1 = o.x * PX, y1 = o.y * PX, x2 = (o.x + o.w) * PX, y2 = (o.y + o.h) * PX;
    const ln = o.line || {}; const c = col(ln.color); const w = (ln.width || 1) * PT;
    const id = "a" + Math.random().toString(36).slice(2, 8);
    const marker = ln.endArrowType
      ? `<defs><marker id="${id}" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L4,2 L0,4 z" fill="${c}"/></marker></defs>` : "";
    return `<svg style="position:absolute;left:0;top:0;overflow:visible" width="1" height="1">${marker}` +
      `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${c}" stroke-width="${w}"${ln.endArrowType ? ` marker-end="url(#${id})"` : ""}/></svg>`;
  }
  const st = [`position:absolute;left:${o.x * PX}px;top:${o.y * PX}px;width:${o.w * PX}px;height:${o.h * PX}px;box-sizing:border-box`];
  if (o.fill) st.push(`background:${col(o.fill.color)}`);
  if (o.line) st.push(`border:${(o.line.width || 1) * PT}px solid ${col(o.line.color)}`);
  if (type === "roundRect") st.push(`border-radius:${(o.rectRadius || 0.1) * PX}px`);
  if (type === "ellipse") st.push("border-radius:50%");
  if (o.shadow) st.push(SHADOW);
  return `<div style="${st.join(";")}"></div>`;
}

function table(rows, o) {
  const cw = o.colW || [];
  const m = (o.margin !== undefined ? o.margin : 0.05) * PX;
  const bd = o.border ? `${(o.border.pt || 1) * PT}px solid ${col(o.border.color)}` : "none";
  const trs = rows.map((r) => "<tr>" + r.map((c) => {
    const cell = typeof c === "object" && c !== null && "text" in c ? c : { text: String(c), options: {} };
    const co = Object.assign({}, { fontSize: o.fontSize, color: o.color, fontFace: o.fontFace }, cell.options || {});
    const bg = co.fill ? col(co.fill.color) : (o.fill ? col(o.fill.color) : "transparent");
    const va = (co.valign || o.valign) === "top" ? "top" : (co.valign || o.valign) === "bottom" ? "bottom" : "middle";
    return `<td style="border:${bd};background:${bg};vertical-align:${va};padding:${m}px;` +
      `text-align:${co.align === "center" ? "center" : co.align === "right" ? "right" : "left"};height:${(o.rowH || 0.3) * PX}px;box-sizing:border-box">` +
      `<span style="${runStyle(co)}">${esc(cell.text)}</span></td>`;
  }).join("") + "</tr>").join("");
  const cg = cw.map((w) => `<col style="width:${w * PX}px">`).join("");
  return `<table style="position:absolute;left:${o.x * PX}px;top:${o.y * PX}px;width:${o.w * PX}px;border-collapse:collapse;table-layout:fixed;line-height:1.17">` +
    `<colgroup>${cg}</colgroup>${trs}</table>`;
}

function fmt(v, code) {
  if (code === "0.00") return v.toFixed(2);
  if (code === "0.0#") return String(Math.round(v * 100) / 100);
  return String(v);
}

function chart(data, o) {
  const W = o.w * PX, H = o.h * PX;
  const legendH = o.showLegend ? 22 : 0;
  const horiz = o.barDir === "bar";
  const labels = data[0].labels;
  const maxV = o.valAxisMaxVal !== undefined ? o.valAxisMaxVal : Math.max(...data.flatMap((d) => d.values)) * 1.15;
  const minV = o.valAxisMinVal !== undefined ? o.valAxisMinVal : 0;
  const L = horiz ? 92 : 38, R = 14, T = 12, B = 26 + legendH;
  const pw = W - L - R, ph = H - T - B;
  const colors = o.chartColors || ["4F81BD"];
  const lc = col(o.catAxisLabelColor || "5B6675"), vc = col(o.valAxisLabelColor || "5B6675");
  const grid = col((o.valGridLine && o.valGridLine.color) || "E4E9F0");
  let g = "";
  // value gridlines at "nice" steps (1, 2, 2.5, 5 x 10^k), like PowerPoint's axis
  const raw = (maxV - minV) / 5, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const stepV = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  const steps = Math.floor((maxV - minV) / stepV + 1e-9);
  for (let i = 0; i <= steps; i++) {
    const v = minV + stepV * i;
    if (horiz) {
      const x = L + pw * (v - minV) / (maxV - minV);
      g += `<line x1="${x}" y1="${T}" x2="${x}" y2="${T + ph}" stroke="${grid}" stroke-width="1"/>`;
      g += `<text x="${x}" y="${T + ph + 14}" font-size="10" fill="${vc}" text-anchor="middle">${Math.round(v * 10) / 10}</text>`;
    } else {
      const y = T + ph - ph * (v - minV) / (maxV - minV);
      g += `<line x1="${L}" y1="${y}" x2="${L + pw}" y2="${y}" stroke="${grid}" stroke-width="1"/>`;
      g += `<text x="${L - 6}" y="${y + 3}" font-size="10" fill="${vc}" text-anchor="end">${Math.round(v * 10) / 10}</text>`;
    }
  }
  const nC = labels.length, nS = data.length;
  const slot = (horiz ? ph : pw) / nC, bw = slot * 0.7 / nS;
  labels.forEach((lab, ci) => {
    data.forEach((d, si) => {
      const v = d.values[ci], frac = (v - minV) / (maxV - minV);
      const c = col(colors[si % colors.length]);
      if (horiz) {
        const y = T + ci * slot + slot * 0.15 + si * bw, len = pw * frac;
        g += `<rect x="${L}" y="${y}" width="${len}" height="${bw}" fill="${c}"/>`;
        if (o.showValue) g += `<text x="${L + len + 4}" y="${y + bw / 2 + 4}" font-size="${o.dataLabelFontSize || 10}" fill="${col(o.dataLabelColor)}">${fmt(v, o.dataLabelFormatCode)}</text>`;
      } else {
        const x = L + ci * slot + slot * 0.15 + si * bw, hgt = ph * frac;
        g += `<rect x="${x}" y="${T + ph - hgt}" width="${bw}" height="${hgt}" fill="${c}"/>`;
        if (o.showValue) g += `<text x="${x + bw / 2}" y="${T + ph - hgt - 4}" font-size="${o.dataLabelFontSize || 10}" fill="${col(o.dataLabelColor)}" text-anchor="middle">${fmt(v, o.dataLabelFormatCode)}</text>`;
      }
    });
    if (horiz) g += `<text x="${L - 6}" y="${T + ci * slot + slot / 2 + 4}" font-size="11" fill="${lc}" text-anchor="end">${esc(lab)}</text>`;
    else g += `<text x="${L + ci * slot + slot / 2}" y="${T + ph + 15}" font-size="11" fill="${lc}" text-anchor="middle">${esc(lab)}</text>`;
  });
  if (o.showLegend) {
    let lx = W / 2 - nS * 60;
    data.forEach((d, si) => {
      g += `<rect x="${lx}" y="${H - 15}" width="10" height="10" fill="${col(colors[si % colors.length])}"/>` +
        `<text x="${lx + 14}" y="${H - 6}" font-size="11" fill="${col(o.legendColor || "5B6675")}">${esc(d.name)}</text>`;
      lx += 120;
    });
  }
  return `<svg style="position:absolute;left:${o.x * PX}px;top:${o.y * PX}px;background:#fff;font-family:Calibri,Arial" width="${W}" height="${H}">${g}</svg>`;
}

function slideHTML(s) {
  const bg = s.background && s.background.color ? col(s.background.color) : "#ffffff";
  const parts = s.items.map((it) => {
    if (it.k === "text") return box(it.o, textBlock(it.t, it.o));
    if (it.k === "shape") return shape(it.type, it.o);
    if (it.k === "image") return `<img src="${imgURI(it.o.path)}" style="position:absolute;left:${it.o.x * PX}px;top:${it.o.y * PX}px;width:${it.o.w * PX}px;height:${it.o.h * PX}px">`;
    if (it.k === "table") return table(it.rows, it.o);
    if (it.k === "chart") return chart(it.data, it.o);
    return "";
  });
  return `<div class="slide" style="background:${bg}">${parts.join("")}</div>`;
}

// ---------------------------------------------------------------- fonts
function fontFaces() {
  const f = [
    ["Calibri", "Calibri.ttf", 400, "normal"], ["Calibri", "Calibrib.ttf", 700, "normal"],
    ["Calibri", "Calibrii.ttf", 400, "italic"], ["Calibri", "Calibriz.ttf", 700, "italic"],
    ["Cambria", "Cambriab.ttf", 700, "normal"], ["Cambria", "Cambriai.ttf", 400, "italic"],
  ];
  return f.filter(([, file]) => fs.existsSync(path.join(DFONTS, file))).map(([name, file, w, st]) =>
    `@font-face{font-family:'${name}';src:url(data:font/ttf;base64,${b64(path.join(DFONTS, file))}) format('truetype');font-weight:${w};font-style:${st}}`
  ).join("\n");
}

// ---------------------------------------------------------------- output
const FONTS = fontFaces();
const slidesBody = PRES.slides.map(slideHTML);
const head = (page) => `<!doctype html><html><head><meta charset="utf-8"><style>
${FONTS}
@page{size:${page};margin:0}
html,body{margin:0;padding:0}
.slide{position:relative;width:${10 * PX}px;height:${5.625 * PX}px;overflow:hidden;page-break-after:always;break-after:page}
</style></head><body>`;

const slidesHTML = head("10in 5.625in") + slidesBody.join("") + "</body></html>";
const scale = 7.1 / 10;
const notesHTML = head("8.5in 11in") + `<style>
.np{width:8.5in;height:11in;box-sizing:border-box;padding:0.6in 0.7in;page-break-after:always;break-after:page;font-family:Calibri,Arial;color:#1F2733}
.np .frame{width:${10 * PX * scale}px;height:${5.625 * PX * scale}px;overflow:hidden;border:1px solid #B9C6DE;margin:0 auto}
.np .frame .slide{transform:scale(${scale});transform-origin:0 0;page-break-after:auto;break-after:auto}
.np .num{color:#8A98AC;font-size:12px;margin:10px 0 8px}
.np .txt{font-size:15px;line-height:1.5;white-space:pre-wrap}
</style>` + PRES.slides.map((s, i) =>
  `<div class="np"><div class="frame">${slidesBody[i]}</div><div class="num">Slide ${i + 1} of ${PRES.slides.length}</div>` +
  `<div class="txt">${s.notes ? esc(s.notes) : "<em>(no speaker notes)</em>"}</div></div>`).join("") + "</body></html>";

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "deck-"));
function print(html, out) {
  const f = path.join(tmp, path.basename(out, ".pdf") + ".html");
  fs.writeFileSync(f, html);
  execFileSync(CHROME, ["--headless=new", "--disable-gpu", "--no-pdf-header-footer",
    "--virtual-time-budget=8000", `--print-to-pdf=${out}`, "file://" + f], { stdio: "ignore" });
}
print(slidesHTML, path.join(HERE, "ipccc2026-talk.pdf"));
print(notesHTML, path.join(HERE, "ipccc2026-talk-notes.pdf"));
fs.rmSync(tmp, { recursive: true, force: true });
// Rebuild the .pptx from the same source so its speaker notes never drift from the PDFs.
execFileSync(process.execPath, [path.join(HERE, "build_deck.js")], { cwd: HERE, stdio: "ignore" });
console.log(`rendered ${PRES.slides.length} slides -> ipccc2026-talk.pdf, ipccc2026-talk-notes.pdf, ipccc2026-talk.pptx`);
