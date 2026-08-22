const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";          // 13.3 x 7.5
const W = 13.3, H = 7.5;

// --- palette: instrument panel. deep teal-slate dominant, amber signal ---
const INK      = "0E2A31";   // deep teal-slate (dark grounds)
const INK2     = "163A43";   // raised dark surface
const PAPER    = "FFFFFF";
const SUNK     = "F1F5F6";   // light card ground
const BODY     = "24343B";   // body text on light
const MUTED    = "5E7078";
const TEAL     = "0E5B69";   // structure accent
const AMBER    = "C2610F";   // signal / values on light
const AMBER_LT = "E8963C";   // signal on dark
const LINE     = "D5DFE2";
const SHOT     = "B9C6CA";   // screenshot placeholder frame

const TITLE_F = "Cambria";
const BODY_F  = "Calibri";
const MONO_F  = "Courier New";

// ---------- helpers ----------

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: INK };
  return s;
}

function lightSlide(titleText, kicker) {
  const s = pres.addSlide();
  s.background = { color: PAPER };
  if (kicker) {
    s.addText(kicker.toUpperCase(), {
      x: 0.62, y: 0.42, w: 8, h: 0.26,
      fontFace: MONO_F, fontSize: 11, bold: true, color: TEAL,
      charSpacing: 2, margin: 0,
    });
  }
  s.addText(titleText, {
    x: 0.6, y: 0.72, w: 11.6, h: 0.82,
    fontFace: TITLE_F, fontSize: 34, bold: true, color: INK,
    margin: 0, valign: "top",
  });
  return s;
}

// the repeated motif: a score chip
function chip(s, x, y, value, opts = {}) {
  const w = opts.w || 1.0, h = opts.h || 0.42;
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: opts.fill || SUNK },
    line: { color: opts.line || LINE, width: 1 },
  });
  s.addText(value, {
    x, y, w, h, align: "center", valign: "middle", margin: 0,
    fontFace: MONO_F, fontSize: opts.size || 15, bold: true,
    color: opts.color || AMBER,
  });
}

// screenshot placeholder people can drop an image onto
function shotBox(s, x, y, w, h, label, hint) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06,
    fill: { color: SUNK },
    line: { color: SHOT, width: 1.75, dashType: "dash" },
  });
  s.addText("📷  " + label, {
    x: x + 0.3, y: y + h / 2 - 0.52, w: w - 0.6, h: 0.42,
    align: "center", margin: 0,
    fontFace: BODY_F, fontSize: 17, bold: true, color: TEAL,
  });
  s.addText(hint, {
    x: x + 0.35, y: y + h / 2 - 0.06, w: w - 0.7, h: 0.72,
    align: "center", margin: 0,
    fontFace: MONO_F, fontSize: 11.5, color: MUTED,
  });
}

// ============================================================
// 1 — title
// ============================================================
{
  const s = darkSlide();
  s.addText("SignalDesk", {
    x: 0.9, y: 2.05, w: 9, h: 1.0,
    fontFace: TITLE_F, fontSize: 54, bold: true, color: PAPER, margin: 0,
  });
  s.addText("A news ranking engine that shows its work", {
    x: 0.92, y: 3.05, w: 10, h: 0.5,
    fontFace: BODY_F, fontSize: 21, color: AMBER_LT, margin: 0,
  });
  s.addText(
    "A Telegram bot that reads 12 news feeds, ranks every story with an\n" +
    "auditable eight-factor score, and writes the briefing.",
    { x: 0.92, y: 3.75, w: 8.6, h: 1.0,
      fontFace: BODY_F, fontSize: 15, color: "9FB4BB", lineSpacing: 24, margin: 0 });

  const facts = [["12", "feeds"], ["8", "factors"], ["18", "selected"], ["147", "tests"]];
  facts.forEach(([n, l], i) => {
    const x = 0.92 + i * 1.62;
    s.addText(n, { x, y: 5.35, w: 1.4, h: 0.5, margin: 0,
      fontFace: MONO_F, fontSize: 27, bold: true, color: AMBER_LT });
    s.addText(l, { x, y: 5.87, w: 1.4, h: 0.3, margin: 0,
      fontFace: BODY_F, fontSize: 11.5, color: "8AA3AB" });
  });

  s.addNotes(
    "Part 2. My project is SignalDesk — a Telegram bot that reads twelve crypto " +
    "and macro news feeds, ranks every story with an eight-factor score, and " +
    "writes a daily briefing. The interesting part isn't that an AI summarises " +
    "the news. It's which stories it picks, and the fact that you can audit that choice."
  );
}

// ============================================================
// 2 — the problem
// ============================================================
{
  const s = lightSlide("Forty minutes of triage, every morning", "the problem");

  s.addShape(pres.ShapeType.roundRect, {
    x: 0.6, y: 1.95, w: 5.7, h: 2.05, rectRadius: 0.08,
    fill: { color: SUNK }, line: { color: LINE, width: 1 },
  });
  s.addText("~157", { x: 0.95, y: 2.2, w: 2.2, h: 0.72, margin: 0,
    fontFace: MONO_F, fontSize: 40, bold: true, color: AMBER });
  s.addText("headlines a day across 12 feeds —\nmostly listicles, price-prediction bait,\nand the same story told six times.",
    { x: 0.95, y: 2.98, w: 5.0, h: 0.9, margin: 0,
      fontFace: BODY_F, fontSize: 14, color: BODY, lineSpacing: 19 });

  s.addText("The obvious fix fails in a specific way", {
    x: 6.85, y: 1.98, w: 5.9, h: 0.36, margin: 0,
    fontFace: BODY_F, fontSize: 17, bold: true, color: INK });
  s.addText(
    "Hand it all to a language model and ask for a summary — and the " +
    "model's selection becomes unauditable.\n\n" +
    "When it leads with the wrong story you cannot find out why, cannot " +
    "reproduce it, and have nothing to correct.",
    { x: 6.85, y: 2.45, w: 5.85, h: 1.6, margin: 0,
      fontFace: BODY_F, fontSize: 14, color: MUTED, lineSpacing: 20 });

  s.addShape(pres.ShapeType.roundRect, {
    x: 0.6, y: 4.45, w: 12.1, h: 1.05, rectRadius: 0.08,
    fill: { color: INK }, line: { color: INK, width: 1 },
  });
  s.addText(
    "You would have traded forty minutes of reading for a black box you " +
    "must trust on a decision that matters.",
    { x: 1.0, y: 4.62, w: 11.3, h: 0.7, margin: 0, valign: "middle",
      fontFace: TITLE_F, fontSize: 18, italic: true, color: PAPER });

  s.addNotes(
    "The problem is volume. Twelve feeds produce about a hundred and fifty " +
    "headlines a day, and most of it is noise — listicles, price predictions, " +
    "and the same story told six times by six outlets.\n\n" +
    "The obvious fix is to hand it all to a language model. But that fails in a " +
    "specific way: the model's selection is unauditable. When it leads with the " +
    "wrong story, you can't find out why, you can't reproduce it, and you have " +
    "nothing to correct. You've traded forty minutes of reading for a black box."
  );
}

// ============================================================
// 3 — the core decision
// ============================================================
{
  const s = lightSlide("Split the job at its natural seam", "the core decision");

  const cards = [
    { x: 0.6, tag: "THE ALGORITHM", head: "decides what matters",
      body: "Deterministic and unit-tested. Same inputs, same ranking, every time. " +
            "Every score carries its factor breakdown, so “why is this first” " +
            "is an arithmetic answer.", accent: TEAL },
    { x: 6.85, tag: "THE MODEL", head: "writes it up",
      body: "It receives the already-ranked list, and its system prompt says " +
            "selection is not its job. It cannot re-order, add stories, or " +
            "introduce a number that was not in the input.", accent: AMBER },
  ];
  cards.forEach(c => {
    s.addShape(pres.ShapeType.roundRect, {
      x: c.x, y: 1.95, w: 5.85, h: 2.5, rectRadius: 0.08,
      fill: { color: SUNK }, line: { color: LINE, width: 1 },
    });
    s.addShape(pres.ShapeType.ellipse, {
      x: c.x + 0.38, y: 2.25, w: 0.34, h: 0.34, fill: { color: c.accent },
    });
    s.addText(c.tag, { x: c.x + 0.95, y: 2.26, w: 4.2, h: 0.3, margin: 0,
      fontFace: MONO_F, fontSize: 10.5, bold: true, color: c.accent, charSpacing: 1.6 });
    s.addText(c.head, { x: c.x + 0.4, y: 2.68, w: 5.0, h: 0.42, margin: 0,
      fontFace: TITLE_F, fontSize: 21, bold: true, color: INK });
    s.addText(c.body, { x: c.x + 0.4, y: 3.18, w: 5.1, h: 1.1, margin: 0,
      fontFace: BODY_F, fontSize: 13.5, color: MUTED, lineSpacing: 18 });
  });

  s.addText(
    "So when the briefing leads with the wrong thing, the fault is in a factor " +
    "weight — visible, reproducible, fixable — instead of in a sampling temperature.",
    { x: 0.6, y: 4.85, w: 12.1, h: 0.8, margin: 0,
      fontFace: BODY_F, fontSize: 15, color: BODY, lineSpacing: 22 });

  s.addNotes(
    "So I split the job at its natural seam.\n\n" +
    "An algorithm decides what matters. It's deterministic and unit-tested — " +
    "same inputs, same ranking, every time.\n\n" +
    "The model only writes it up. It receives the already-ranked list, and its " +
    "system prompt tells it explicitly that selection is not its job. It can't " +
    "re-order, can't add stories, and can't introduce a number that wasn't in the input.\n\n" +
    "That boundary is what makes the output auditable. When the briefing leads " +
    "with the wrong story, the fault is in a factor weight — something I can see, " +
    "test and fix — instead of in a sampling temperature."
  );
}

// ============================================================
// 4 — live output  [SCREENSHOT]
// ============================================================
{
  const s = lightSlide("This is what arrives at 08:30", "the product");

  shotBox(s, 0.6, 1.9, 6.2, 4.55, "Telegram — daily briefing",
    "Screenshot the /digest output.\nInclude the headline, a few bullets,\nand the ranked Sources list below.");

  s.addText("Every morning, unprompted", { x: 7.25, y: 2.0, w: 5.5, h: 0.36, margin: 0,
    fontFace: BODY_F, fontSize: 17, bold: true, color: INK });
  s.addText(
    "A written briefing at 08:30, plus an immediate alert for anything " +
    "scoring above a threshold — because a digest answers “what happened " +
    "yesterday” and an alert answers “this cannot wait”.",
    { x: 7.25, y: 2.48, w: 5.45, h: 1.35, margin: 0,
      fontFace: BODY_F, fontSize: 13.5, color: MUTED, lineSpacing: 19 });

  const rows = [
    ["08:30 daily", "full briefing, 2–3 messages"],
    ["every 15 min", "alert poll, score ≥ 0.72 pushes now"],
    ["any time", "/top  /digest  /weights"],
  ];
  rows.forEach(([a, b], i) => {
    const y = 4.0 + i * 0.72;
    s.addShape(pres.ShapeType.roundRect, {
      x: 7.25, y, w: 5.45, h: 0.6, rectRadius: 0.06,
      fill: { color: SUNK }, line: { color: LINE, width: 1 },
    });
    s.addText(a, { x: 7.45, y, w: 1.75, h: 0.6, margin: 0, valign: "middle",
      fontFace: MONO_F, fontSize: 11.5, bold: true, color: TEAL });
    s.addText(b, { x: 9.2, y, w: 3.35, h: 0.6, margin: 0, valign: "middle",
      fontFace: BODY_F, fontSize: 12.5, color: BODY });
  });

  s.addNotes(
    "Here's what actually arrives. A written briefing every morning at half " +
    "past eight, with the ranked sources underneath it.\n\n" +
    "And between briefings, the bot polls every fifteen minutes. Anything " +
    "scoring above the threshold gets pushed immediately, on its own. That's " +
    "where the scoring engine really earns its place — a digest answers what " +
    "happened yesterday, an alert answers this can't wait."
  );
}

// ============================================================
// 5 — the pipeline
// ============================================================
{
  const s = lightSlide("Seven stages, each one testable", "how it works");

  const stages = [
    ["0", "Fetch", "12 feeds, concurrent,\nindependently timed out"],
    ["1", "Hard filter", "clickbait, bare price ticks,\nmacro noise — binary, not a penalty"],
    ["2", "Dedupe", "TF-IDF ∪ entity overlap,\ngrown to transitive closure"],
    ["3", "Classify", "5 categories, single-label,\npriority order"],
    ["4", "Score", "8 weighted factors,\nnormalised to 0–1"],
    ["5", "Select", "quality gate, per-subject cap,\nfixed count only as a floor"],
    ["6", "Write & send", "LLM writes the top 10,\nTelegram splits long messages"],
  ];

  const cw = 1.63, gap = 0.13;
  stages.forEach(([n, name, desc], i) => {
    const x = 0.6 + i * (cw + gap);
    const isKey = (n === "2" || n === "4");
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 1.95, w: cw, h: 2.85, rectRadius: 0.07,
      fill: { color: isKey ? INK : SUNK },
      line: { color: isKey ? INK : LINE, width: 1 },
    });
    s.addText(n, { x, y: 2.12, w: cw, h: 0.4, align: "center", margin: 0,
      fontFace: MONO_F, fontSize: 17, bold: true,
      color: isKey ? AMBER_LT : AMBER });
    s.addText(name, { x: x + 0.08, y: 2.56, w: cw - 0.16, h: 0.36, align: "center", margin: 0,
      fontFace: TITLE_F, fontSize: 14.5, bold: true, color: isKey ? PAPER : INK });
    s.addText(desc, { x: x + 0.1, y: 2.98, w: cw - 0.2, h: 1.6, align: "center", margin: 0,
      fontFace: BODY_F, fontSize: 10.5, color: isKey ? "A8C0C6" : MUTED, lineSpacing: 14 });
  });

  s.addText("~157 raw", { x: 0.6, y: 4.95, w: 2.2, h: 0.3, margin: 0,
    fontFace: MONO_F, fontSize: 12, color: MUTED });
  s.addText("18 selected", { x: 10.9, y: 4.95, w: 1.8, h: 0.3, align: "right", margin: 0,
    fontFace: MONO_F, fontSize: 12, bold: true, color: AMBER });

  s.addText(
    "Crypto and macro are scored in separate pools. Pooled together, a Fed " +
    "decision loses on the asset factor by construction — it names no token — " +
    "and macro quietly vanishes from the briefing.",
    { x: 0.6, y: 5.45, w: 12.1, h: 0.8, margin: 0,
      fontFace: BODY_F, fontSize: 13.5, color: BODY, lineSpacing: 19 });

  s.addNotes(
    "The pipeline is seven stages, and every one of them is separately testable.\n\n" +
    "Fetch twelve feeds concurrently. Hard-filter the clickbait and the bare " +
    "price ticks — binary, so a listicle can't out-vote its way back in. Dedupe, " +
    "because twelve feeds covering one market means the same story arrives six " +
    "times. Classify into five categories. Score. Select. Then write and send.\n\n" +
    "One detail worth calling out: crypto and macro are scored in separate pools. " +
    "If you pool them, a Fed decision loses on the asset factor by construction — " +
    "it names no token — and macro quietly disappears from the briefing."
  );
}

// ============================================================
// 6 — the eight factors
// ============================================================
{
  const s = lightSlide("Eight factors, and why each weight is what it is", "the formula");

  const rows = [
    ["keyword",        "0.185", "4 tiers, highest hit wins — not a sum"],
    ["recency",        "0.185", "linear decay to zero over 24h"],
    ["source_quality", "0.185", "FT / Bloomberg 1.00 → unrated 0.60"],
    ["topicality",     "0.130", "feed tags; untagged scores neutral, not zero"],
    ["numeric",        "0.100", "how many concrete figures the headline carries"],
    ["analysis",       "0.100", "how much it reads as commentary, not report"],
    ["source_count",   "0.075", "corroboration across outlets"],
    ["asset",          "0.040", "BTC/ETH 1.0, large alts 0.7, memecoins 0.3"],
  ];

  s.addText("score  =  Σ ( weight × factor )  ÷  Σ weight", {
    x: 0.6, y: 1.85, w: 7.4, h: 0.4, margin: 0,
    fontFace: MONO_F, fontSize: 14, bold: true, color: TEAL });

  rows.forEach(([name, w, desc], i) => {
    const y = 2.38 + i * 0.47;
    const hot = (name === "source_count");
    s.addShape(pres.ShapeType.rect, {
      x: 0.6, y, w: 7.55, h: 0.42,
      fill: { color: hot ? "FBEEDF" : (i % 2 ? SUNK : PAPER) },
      line: { color: LINE, width: 0.75 },
    });
    s.addText(name, { x: 0.75, y, w: 1.95, h: 0.42, margin: 0, valign: "middle",
      fontFace: MONO_F, fontSize: 11.5, bold: true, color: INK });
    s.addText(w, { x: 2.65, y, w: 0.75, h: 0.42, margin: 0, valign: "middle", align: "right",
      fontFace: MONO_F, fontSize: 11.5, bold: true, color: AMBER });
    s.addText(desc, { x: 3.6, y, w: 4.45, h: 0.42, margin: 0, valign: "middle",
      fontFace: BODY_F, fontSize: 11.5, color: MUTED });
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: 8.45, y: 2.38, w: 4.25, h: 3.24, rectRadius: 0.08,
    fill: { color: INK }, line: { color: INK, width: 1 },
  });
  s.addText("The counter-intuitive one", {
    x: 8.75, y: 2.62, w: 3.7, h: 0.32, margin: 0,
    fontFace: MONO_F, fontSize: 10.5, bold: true, color: AMBER_LT, charSpacing: 1.4 });
  s.addText("source_count is only 0.075", {
    x: 8.75, y: 3.0, w: 3.7, h: 0.5, margin: 0,
    fontFace: TITLE_F, fontSize: 17, bold: true, color: PAPER });
  s.addText(
    "Corroboration is real evidence, so it earns a place. But weight it " +
    "heavily and one big story wins every slot for three days running, " +
    "because every outlet keeps re-reporting it.\n\n" +
    "Capping it at 7.5% buys the signal without letting yesterday squat " +
    "on today.",
    { x: 8.75, y: 3.55, w: 3.7, h: 1.9, margin: 0,
      fontFace: BODY_F, fontSize: 12, color: "A8C0C6", lineSpacing: 17 });

  s.addNotes(
    "Here's the formula. Eight factors, each normalised to zero-to-one, then " +
    "weighted and summed.\n\n" +
    "The weights are a tuned set — changing one shifts the meaning of all the " +
    "others. The most counter-intuitive is corroboration, source_count, at only " +
    "seven and a half percent.\n\n" +
    "Corroboration is real evidence, so it earns a place. But weight it heavily " +
    "and one big story wins every slot for three days running, because every " +
    "outlet keeps re-reporting it. Capping it low buys the signal without letting " +
    "yesterday's news squat on today's briefing. There's a test that pins exactly " +
    "that."
  );
}

// ============================================================
// 7 — /why  [SCREENSHOT]
// ============================================================
{
  const s = lightSlide("Ask it why, and it shows the arithmetic", "transparency");

  shotBox(s, 0.6, 1.9, 6.5, 4.15, "Telegram — /why 1",
    "Screenshot the factor breakdown table:\nfactor / raw / weight / contribution,\nplus “What drove it” underneath.");

  s.addText("Not the model explaining itself", {
    x: 7.5, y: 2.0, w: 5.2, h: 0.36, margin: 0,
    fontFace: BODY_F, fontSize: 17, bold: true, color: INK });
  s.addText(
    "Asking a language model why it chose something gets you a plausible " +
    "story, not the actual cause.\n\n" +
    "This is the real arithmetic: every factor, its raw verdict, its weight, " +
    "and what it contributed.",
    { x: 7.5, y: 2.48, w: 5.2, h: 1.5, margin: 0,
      fontFace: BODY_F, fontSize: 13.5, color: MUTED, lineSpacing: 19 });

  chip(s, 7.5, 4.12, "1.00", { w: 0.82, size: 13 });
  s.addText("×  0.185  keyword", { x: 8.5, y: 4.12, w: 4.2, h: 0.42, margin: 0, valign: "middle",
    fontFace: MONO_F, fontSize: 12, color: BODY });
  chip(s, 7.5, 4.66, "0.94", { w: 0.82, size: 13 });
  s.addText("×  0.185  recency", { x: 8.5, y: 4.66, w: 4.2, h: 0.42, margin: 0, valign: "middle",
    fontFace: MONO_F, fontSize: 12, color: BODY });
  chip(s, 7.5, 5.2, "0.734", { w: 0.82, size: 12, fill: INK, line: INK, color: AMBER_LT });
  s.addText("=  total, and it adds up", { x: 8.5, y: 5.2, w: 4.2, h: 0.42, margin: 0, valign: "middle",
    fontFace: MONO_F, fontSize: 12, bold: true, color: INK });

  s.addNotes(
    "This command is the heart of the project. Ask it why story one is first, " +
    "and it prints the arithmetic — every factor, its raw verdict, its weight, " +
    "and what it contributed to the total.\n\n" +
    "That's deliberately not the model explaining itself. Asking a language " +
    "model why it chose something gets you a plausible story, not the actual " +
    "cause. This is the actual cause, and it adds up."
  );
}

// ============================================================
// 8 — user controls  [SCREENSHOT]
// ============================================================
{
  const s = lightSlide("The reader owns two of the weights", "control");

  shotBox(s, 0.6, 1.9, 5.9, 4.15, "Telegram — /weights",
    "Screenshot the settings screen:\nthe five category toggles, the depth\nbuttons, and the weight table below.");

  s.addText("Subjects", { x: 6.95, y: 1.95, w: 5.7, h: 0.34, margin: 0,
    fontFace: TITLE_F, fontSize: 17, bold: true, color: INK });
  s.addText(
    "Five categories: security, regulation, institutional flows, macro, " +
    "protocol. Switching one off is a hard filter — “only show me " +
    "security” is not a request to rank macro slightly lower.",
    { x: 6.95, y: 2.36, w: 5.7, h: 1.05, margin: 0,
      fontFace: BODY_F, fontSize: 13, color: MUTED, lineSpacing: 18 });

  s.addText("Depth", { x: 6.95, y: 3.55, w: 5.7, h: 0.34, margin: 0,
    fontFace: TITLE_F, fontSize: 17, bold: true, color: INK });
  s.addText("Two factors share a 0.200 budget you split:", {
    x: 6.95, y: 3.95, w: 5.7, h: 0.36, margin: 0,
    fontFace: BODY_F, fontSize: 13, color: MUTED });

  const dep = [["Numbers", "0.170", "0.030"], ["Balanced", "0.100", "0.100"], ["Analysis", "0.030", "0.170"]];
  dep.forEach(([n, a, b], i) => {
    const y = 4.42 + i * 0.5;
    s.addShape(pres.ShapeType.rect, {
      x: 6.95, y, w: 5.7, h: 0.44,
      fill: { color: i === 1 ? SUNK : PAPER }, line: { color: LINE, width: 0.75 },
    });
    s.addText(n, { x: 7.12, y, w: 1.6, h: 0.44, margin: 0, valign: "middle",
      fontFace: MONO_F, fontSize: 12, bold: true, color: TEAL });
    s.addText("numeric " + a, { x: 8.75, y, w: 1.85, h: 0.44, margin: 0, valign: "middle",
      fontFace: MONO_F, fontSize: 11.5, color: AMBER });
    s.addText("analysis " + b, { x: 10.65, y, w: 1.9, h: 0.44, margin: 0, valign: "middle",
      fontFace: MONO_F, fontSize: 11.5, color: AMBER });
  });

  s.addText(
    "The budget total never changes, so choosing a style never quietly alters " +
    "how much subject matter, freshness or source reputation count.",
    { x: 6.95, y: 6.0, w: 5.7, h: 0.6, margin: 0,
      fontFace: BODY_F, fontSize: 12, italic: true, color: BODY, lineSpacing: 16 });

  s.addNotes(
    "The reader also owns part of the formula. Two dials.\n\n" +
    "Subjects — five categories, and switching one off is a hard filter. " +
    "“Only show me security news” isn't a request to rank macro " +
    "slightly lower.\n\n" +
    "And depth. Two of the eight factors — how many figures a headline carries, " +
    "and how much it reads as commentary — share a fixed budget that the reader " +
    "splits. Because the total never changes, choosing a style never quietly " +
    "alters how much subject matter or freshness count. The settings screen " +
    "shows you the two numbers that moved."
  );
}

// ============================================================
// 9 — AI used
// ============================================================
{
  const s = lightSlide("Where the AI is, and where it deliberately isn’t", "use of ai");

  const cards = [
    ["Models", "Moonshot Kimi K3\n→ xAI Grok 4.3", TEAL,
     "Cross-vendor on purpose. Two models from one provider are a retry, not a fallback — an outage takes out both."],
    ["Built with", "Claude Code", AMBER,
     "Pair programmer throughout. The whole pipeline, the tests, and every bug fix in this deck."],
    ["When it fails", "Template output", TEAL,
     "Every provider down → the top-ranked headlines verbatim. Degraded, honest, still correctly ordered."],
  ];
  cards.forEach(([tag, head, col, body], i) => {
    const x = 0.6 + i * 4.15;
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 1.9, w: 3.85, h: 2.2, rectRadius: 0.08,
      fill: { color: SUNK }, line: { color: LINE, width: 1 },
    });
    s.addText(tag.toUpperCase(), { x: x + 0.3, y: 2.1, w: 3.3, h: 0.28, margin: 0,
      fontFace: MONO_F, fontSize: 10, bold: true, color: col, charSpacing: 1.5 });
    s.addText(head, { x: x + 0.3, y: 2.42, w: 3.3, h: 0.66, margin: 0,
      fontFace: TITLE_F, fontSize: 15.5, bold: true, color: INK, lineSpacing: 19 });
    s.addText(body, { x: x + 0.3, y: 3.12, w: 3.3, h: 0.9, margin: 0,
      fontFace: BODY_F, fontSize: 11.5, color: MUTED, lineSpacing: 15 });
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: 0.6, y: 4.32, w: 12.1, h: 2.0, rectRadius: 0.08,
    fill: { color: INK }, line: { color: INK, width: 1 },
  });
  s.addText("SYSTEM PROMPT — the boundary, in its own words", {
    x: 0.95, y: 4.5, w: 8, h: 0.3, margin: 0,
    fontFace: MONO_F, fontSize: 10, bold: true, color: AMBER_LT, charSpacing: 1.4 });
  s.addText(
    "“You will be given a numbered list of stories that has ALREADY been\n" +
    " selected and ranked by a scoring engine. Selection is not your job.\n" +
    " Do not re-order them, do not add stories that are not in the list.”\n" +
    "\n" +
    "“Never invent a number. Prices, percentages and dollar amounts may only\n" +
    " appear if they appear in the input.”",
    { x: 0.95, y: 4.84, w: 11.4, h: 1.3, margin: 0,
      fontFace: MONO_F, fontSize: 11.5, color: "C6DADF", lineSpacing: 16 });

  s.addNotes(
    "So where is the AI, and where is it deliberately not?\n\n" +
    "In the product: Moonshot's Kimi K3, falling back to xAI's Grok 4.3, through " +
    "an OpenAI-compatible proxy. The chain is cross-vendor on purpose — two " +
    "models from one provider give you a retry, not a fallback, because an " +
    "outage takes out both.\n\n" +
    "Building it: Claude Code, as a pair programmer throughout.\n\n" +
    "And this is the system prompt that enforces the boundary. It tells the " +
    "model the list is already ranked, that selection is not its job, and that " +
    "it may never invent a number. When every provider fails, the bot falls back " +
    "to template output built from the top-ranked headlines — degraded, but " +
    "honest, and still correctly ordered, because the ranking never depended on " +
    "the model."
  );
}

// ============================================================
// 10 — the bug  [SCREENSHOT]
// ============================================================
{
  const s = lightSlide("The factor table found every real bug", "iteration");

  s.addShape(pres.ShapeType.roundRect, {
    x: 0.6, y: 1.9, w: 12.1, h: 1.1, rectRadius: 0.08,
    fill: { color: "FBEEDF" }, line: { color: "E8C39A", width: 1 },
  });
  s.addText(
    "A  \\b(exploit)\\b  regex could not match the word “exploited”.",
    { x: 1.0, y: 2.05, w: 11.3, h: 0.4, margin: 0,
      fontFace: MONO_F, fontSize: 15, bold: true, color: INK });
  s.addText(
    "So a $62 million protocol hack — the biggest story in the set — scored as untiered noise.",
    { x: 1.0, y: 2.48, w: 11.3, h: 0.36, margin: 0,
      fontFace: BODY_F, fontSize: 13.5, color: BODY });

  // before / after
  const pairs = [
    ["BEFORE", "#7", "0.701", SUNK, LINE, MUTED, INK],
    ["AFTER",  "#1", "0.867", INK,  INK,  AMBER_LT, PAPER],
  ];
  pairs.forEach(([tag, rank, score, fill, line, accent, txt], i) => {
    const x = 0.6 + i * 3.1;
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 3.2, w: 2.85, h: 1.75, rectRadius: 0.08,
      fill: { color: fill }, line: { color: line, width: 1 },
    });
    s.addText(tag, { x: x + 0.25, y: 3.38, w: 2.3, h: 0.28, margin: 0,
      fontFace: MONO_F, fontSize: 10, bold: true, color: accent, charSpacing: 1.5 });
    s.addText(rank, { x: x + 0.25, y: 3.7, w: 2.3, h: 0.78, margin: 0,
      fontFace: MONO_F, fontSize: 38, bold: true, color: accent });
    s.addText("score " + score, { x: x + 0.25, y: 4.5, w: 2.3, h: 0.32, margin: 0,
      fontFace: MONO_F, fontSize: 13, color: txt });
  });

  shotBox(s, 7.0, 3.2, 5.7, 2.6, "Terminal — the ranking flip",
    "Screenshot --once output before and\nafter the fix, or the /why table showing\nkeyword = 1.00 on the exploit story.");

  s.addText(
    "Invisible in aggregate. Obvious the moment the intermediate state was on screen — " +
    "which is the argument for the whole design.",
    { x: 0.6, y: 5.25, w: 6.1, h: 0.9, margin: 0,
      fontFace: BODY_F, fontSize: 13, italic: true, color: BODY, lineSpacing: 18 });

  s.addNotes(
    "Now the part I'd most like you to take away.\n\n" +
    "That transparency command started as a nice-to-have. It became the debugging " +
    "tool — every real bug in this codebase was found by reading the factor table " +
    "next to a ranking, and not one of them was caught by a test.\n\n" +
    "Here's the clearest example. A regex looking for the word “exploit” " +
    "could not match “exploited”. So a sixty-two million dollar protocol " +
    "hack — the biggest story in the set — scored as untiered noise and ranked " +
    "seventh. After the fix it ranked first.\n\n" +
    "That bug was invisible in aggregate and obvious the moment the intermediate " +
    "state was on screen. Which is the argument for the whole design."
  );
}

// ============================================================
// 11 — reflections
// ============================================================
{
  const s = darkSlide();

  s.addText("What worked, and what I’d do next", {
    x: 0.9, y: 0.85, w: 11, h: 0.7,
    fontFace: TITLE_F, fontSize: 32, bold: true, color: PAPER, margin: 0 });

  s.addShape(pres.ShapeType.roundRect, {
    x: 0.9, y: 1.85, w: 5.5, h: 2.5, rectRadius: 0.08,
    fill: { color: INK2 }, line: { color: "27505A", width: 1 } });
  s.addText("WORKED", { x: 1.25, y: 2.08, w: 4.6, h: 0.28, margin: 0,
    fontFace: MONO_F, fontSize: 10.5, bold: true, color: AMBER_LT, charSpacing: 1.6 });
  s.addText("Making the score explain itself", {
    x: 1.25, y: 2.42, w: 4.8, h: 0.6, margin: 0,
    fontFace: TITLE_F, fontSize: 18, bold: true, color: PAPER, lineSpacing: 22 });
  s.addText(
    "It changed how I built the thing. Printing the factor table beside a " +
    "ranking is how every real bug surfaced — not one came from a test.",
    { x: 1.25, y: 3.15, w: 4.8, h: 1.0, margin: 0,
      fontFace: BODY_F, fontSize: 13, color: "A8C0C6", lineSpacing: 18 });

  s.addShape(pres.ShapeType.roundRect, {
    x: 6.9, y: 1.85, w: 5.5, h: 2.5, rectRadius: 0.08,
    fill: { color: INK2 }, line: { color: "27505A", width: 1 } });
  s.addText("NEXT", { x: 7.25, y: 2.08, w: 4.6, h: 0.28, margin: 0,
    fontFace: MONO_F, fontSize: 10.5, bold: true, color: AMBER_LT, charSpacing: 1.6 });
  s.addText("Fit the weights instead of reasoning them", {
    x: 7.25, y: 2.42, w: 4.8, h: 0.74, margin: 0,
    fontFace: TITLE_F, fontSize: 18, bold: true, color: PAPER, lineSpacing: 22 });
  s.addText(
    "Every weight is defensible; none is measured. Logging each ranking " +
    "against which stories readers actually open would turn eight arguments " +
    "into eight numbers.",
    { x: 7.25, y: 3.26, w: 4.8, h: 1.0, margin: 0,
      fontFace: BODY_F, fontSize: 13, color: "A8C0C6", lineSpacing: 18 });

  s.addText(
    "The classifier will keep having gaps — it is regex over open-ended " +
    "language, and I have fixed five rounds of them. That is not a thing that " +
    "finishes; it is a thing you keep feeding real output.",
    { x: 0.9, y: 4.7, w: 11.5, h: 0.9, margin: 0,
      fontFace: BODY_F, fontSize: 14, color: "8AA3AB", lineSpacing: 20 });

  s.addText("github.com/okyterrance/signaldesk", {
    x: 0.9, y: 6.15, w: 7, h: 0.36, margin: 0,
    fontFace: MONO_F, fontSize: 13, bold: true, color: AMBER_LT });
  s.addText("3,289 lines · 147 offline tests · zero-key data layer", {
    x: 0.9, y: 6.55, w: 8, h: 0.32, margin: 0,
    fontFace: BODY_F, fontSize: 12, color: "6E8A93" });

  s.addNotes(
    "To close — what worked and what I'd change.\n\n" +
    "What worked was making the score explain itself. It changed how I built " +
    "the whole thing, and it's the single decision I'd repeat.\n\n" +
    "What I'd change: the weights are reasoned, not fitted. Every one is " +
    "defensible and none is measured. The right next step is to log each " +
    "ranking against which stories readers actually open, and fit them — " +
    "turning eight arguments into eight numbers.\n\n" +
    "And I'd be honest that the classifier will keep having gaps. It's regular " +
    "expressions over open-ended language. I've fixed five rounds of them, each " +
    "one found by looking at real output. That's not a thing that finishes — " +
    "it's a thing you keep feeding real data. Thank you."
  );
}

pres.writeFile({ fileName: "/home/user/signaldesk/docs/deck/SignalDesk_Part2.pptx" })
  .then(f => console.log("wrote", f));
