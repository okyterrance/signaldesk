const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  LevelFormat, BorderStyle, convertInchesToTwip, Table, TableRow, TableCell,
  WidthType, ShadingType,
} = require('docx');
const fs = require('fs');

const NAVY = '0B3D66', GREY = '5A6470', INK = '14161A';

// **bold** and *italic* -> formatted runs
function runs(text, opts = {}) {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/).filter(Boolean).map(p => {
    if (p.startsWith('**')) return new TextRun({ text: p.slice(2, -2), bold: true, ...opts });
    if (p.startsWith('*')) return new TextRun({ text: p.slice(1, -1), italics: true, ...opts });
    return new TextRun({ text: p, ...opts });
  });
}

const bullet = t => new Paragraph({
  numbering: { reference: 'say', level: 0 },
  spacing: { after: 100, line: 264 },
  children: runs(t, { size: 23, color: INK }),
});

const beat = (title, time) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 260, after: 60 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: 'C3CAD2', space: 3 } },
  children: [
    new TextRun({ text: title, bold: true, size: 26, color: NAVY }),
    new TextRun({ text: '   ' + time, size: 20, color: GREY }),
  ],
});

const cue = (label, t) => new Paragraph({
  spacing: { after: 60 },
  indent: { left: convertInchesToTwip(0.02) },
  children: [
    new TextRun({ text: label + '  ', bold: true, size: 18, color: GREY }),
    new TextRun({ text: t, italics: true, size: 18, color: GREY }),
  ],
});

const body = [];

body.push(new Paragraph({
  spacing: { after: 40 },
  children: [new TextRun({ text: 'SignalDesk — Project Showcase Script', bold: true, size: 34, color: INK })],
}));
body.push(new Paragraph({
  spacing: { after: 40 },
  children: [new TextRun({
    text: 'Polymer Tech Expo 2026 · Part 2 of the video submission',
    size: 21, color: GREY,
  })],
}));
body.push(new Paragraph({
  spacing: { after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: INK, space: 6 } },
  children: [new TextRun({
    text: 'Runs 4:15 at 150 wpm, including the demo holds. Read one bullet per breath — each bullet is one sentence. Grey lines are for filming, not for saying.',
    size: 20, color: GREY, italics: true,
  })],
}));

const beats = [
  {
    title: '1 · What it is, and who it’s for', time: '0:00 – 0:33',
    shot: 'Title card “SignalDesk”, then cut to the Telegram window sitting idle, before anything is typed.',
    sub: 'Free subscription briefing · crypto + macro in one place',
    lines: [
      'This is **SignalDesk**.',
      'It’s for someone who needs to get across a market quickly, from several angles at once — **crypto and macro in one place**.',
      'Without spending forty minutes on headlines to find the five that matter.',
      'Today it’s a **Telegram bot**, and that’s what I’ll demo.',
      'What I’m building toward is a **free subscription site**.',
      'Readers subscribe, a ranked briefing is pushed every morning, and it costs them nothing.',
      'Which makes the list itself a distribution channel for the desk behind it.',
    ],
  },
  {
    title: '2 · How you actually use it', time: '0:33 – 1:16',
    shot: 'Record each command as its own take. Cut the loading wait every time: type → cut → reply lands. Highlight story 1’s score and its “drivers:” line. End on the Sources list at the bottom of /digest.',
    sub: '/top — the ranking right now  ·  /digest — the written briefing  ·  08:30 daily, alerts every 15 min',
    lines: [
      'Three commands, and that’s all of it.',
      '**/top** is the ranking right now — every story with its score, and the three factors that pushed it up.',
      '**/digest** writes the briefing: one headline, one line per story, market snapshot on top.',
      'And every source underneath, so you can check any claim yourself.',
      'But you don’t have to type anything.',
      'The digest goes out on its own at **half past eight every morning**.',
      'In between, the bot polls every fifteen minutes and pushes anything scoring **0.72 or above** immediately.',
      'A digest answers *what happened yesterday*; an alert answers *this can’t wait*.',
    ],
  },
  {
    title: '3 · Where the numbers come from', time: '1:16 – 2:23',
    shot: 'Two seconds on the feed list in src/fetchers/rss.py. Then /weights — record yourself tapping a subject toggle off and moving depth to Analysis, and show the two weight numbers changing. Then /why 1: HOLD FIVE SECONDS, zoomed in. This is the most important frame in the video.',
    sub: '12 RSS feeds · Binance · Fear & Greed — no paid data  ·  /why — arithmetic, not the model’s opinion',
    lines: [
      'So where do the numbers come from?',
      '**Twelve RSS feeds** — CoinDesk, The Block and DL News on crypto; FT, Bloomberg and the ECB press feed on macro.',
      'Plus **Binance’s public ticker** and the **Fear and Greed index**.',
      '**None of it is paid data.**',
      'Every story is scored on **eight factors**: keyword tier, recency, source quality, topicality, corroboration, figures, analysis, asset.',
      '**/weights** hands part of that formula to the reader.',
      'Five subject toggles — and switching one off is a **hard filter**, not a penalty.',
      'Plus a depth setting that shifts weight between *numbers* and *analysis*.',
      'And this is the command I care most about.',
      '**/why 1** prints the arithmetic: every factor, its raw value, its weight, what it contributed.',
      'That’s deliberately **not** the model explaining itself.',
      'Ask a model why it chose something and you get a plausible story, not the cause.',
      'This is the cause — and it adds up.',
    ],
  },
  {
    title: '4 · Use of AI — and where it deliberately isn’t', time: '2:23 – 3:21',
    shot: 'Cut to SYSTEM_PROMPT in src/llm/digest.py and highlight “Selection is not your job.” Then the terminal: python -m pytest tests/ -q, cut to the green 148 passed. Then two seconds of a real Claude Code session.',
    sub: 'Algorithm ranks · model only writes  ·  “Selection is not your job”  ·  Kimi K3 → Grok 4.3 · built with Claude Code',
    lines: [
      'So where is the AI, and where is it deliberately not?',
      '**The ranking is not AI.**',
      'It’s a deterministic algorithm — same inputs, same output — with **148 offline tests** on that path.',
      'The model only **writes**.',
      'It’s handed the ranked list, and the system prompt says it plainly: *selection is not your job, don’t re-order, never invent a number.*',
      'If every provider is down, it falls back to a template of the top headlines.',
      'Degraded, but still correctly ordered.',
      'The models are **Moonshot’s Kimi K3**, falling back to **xAI’s Grok 4.3**.',
      'Cross-vendor on purpose, because two models from one provider are a retry, not a fallback.',
      'And I built all of it with **Claude Code**.',
      'Working at the level of “here are the stages, here’s why this weight is low, here’s the test that has to pass.”',
      '**My job was the logic chain.**',
    ],
  },
  {
    title: '5 · Iterations and reflections', time: '3:21 – 4:15',
    shot: 'Terminal: python scripts/show_regex_bug.py — it prints the broken and fixed rankings side by side. Let the flip land, highlight the row moving 7th → 2nd. Then CUT BACK TO YOUR FACE for the last two bullets.',
    sub: 'Every real bug found by reading the factor table  ·  Next: fit the weights, ship the site',
    lines: [
      'Two reflections.',
      '**What worked** was making the score explain itself.',
      '/why started as a nice-to-have and became my debugging tool.',
      'Every real bug in this codebase was found by reading the factor table next to a ranking — and **not one was caught by a test**.',
      'The clearest example: a regex looking for the word *exploit* couldn’t match *exploited*.',
      'So a **sixty-two-million-dollar** protocol hack scored zero on the keyword factor and ranked seventh.',
      'After the fix, second.',
      '**What I’d improve given more time:** the weights are **reasoned, not fitted**.',
      'I can defend every one; none is measured.',
      'The next step is logging each ranking against what readers actually open, and fitting the weights to that.',
      'And then the site itself: subscriptions, and per-reader profiles.',
      '**Thank you.**',
    ],
  },
];

for (const b of beats) {
  body.push(beat(b.title, b.time));
  body.push(cue('SHOT', b.shot));
  body.push(cue('SUBTITLE', b.sub));
  body.push(new Paragraph({ spacing: { after: 40 }, children: [] }));
  for (const l of b.lines) body.push(bullet(l));
}

// --- capture checklist ---
body.push(new Paragraph({
  heading: HeadingLevel.HEADING_2,
  pageBreakBefore: true,
  spacing: { after: 120 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: 'C3CAD2', space: 3 } },
  children: [new TextRun({ text: 'Recording checklist', bold: true, size: 26, color: NAVY })],
}));

const W = [1000, 4900, 3300];
const cellP = t => new Paragraph({ spacing: { before: 40, after: 40 }, children: runs(t, { size: 20 }) });
const row = (a, b, c, head = false) => new TableRow({
  children: [a, b, c].map((t, i) => new TableCell({
    width: { size: W[i], type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: 'EEF1F4' } : undefined,
    children: [cellP(head ? '**' + t + '**' : t)],
  })),
});
body.push(new Table({
  columnWidths: W,
  width: { size: W[0] + W[1] + W[2], type: WidthType.DXA },
  rows: [
    row('Beat', 'What to capture', 'Command', true),
    row('2', 'The ranked list', '/top'),
    row('2', 'The briefing, plus the Sources list', '/digest'),
    row('3', 'The feed list, about 2 seconds', 'open src/fetchers/rss.py'),
    row('3', 'Settings, with a toggle being tapped', '/weights'),
    row('3', 'Factor table — hold 5s, zoomed in', '/why 1'),
    row('4', 'System prompt: “Selection is not your job”', 'open src/llm/digest.py'),
    row('4', 'The green test line', 'python -m pytest tests/ -q'),
    row('5', 'The ranking flip, 7th → 2nd', 'python scripts/show_regex_bug.py'),
  ],
}));

const note = t => new Paragraph({
  numbering: { reference: 'say', level: 0 },
  spacing: { after: 90, line: 264 },
  children: runs(t, { size: 21 }),
});
body.push(new Paragraph({
  spacing: { before: 240, after: 80 },
  children: [new TextRun({ text: 'Before you record', bold: true, size: 22, color: NAVY })],
}));
[
  'Telegram in **light** theme — dark screenshots lose the factor table after video compression.',
  'Zoom Telegram up two or three steps. Legibility beats fitting more in frame.',
  'Clear the chat first, so the demo reads top-to-bottom with nothing stale above.',
  '**python main.py** on live feeds if the wifi is good; **python main.py --demo** is the safe fallback, and every number in it is genuinely computed.',
  '1080p minimum.',
].forEach(t => body.push(note(t)));

body.push(new Paragraph({
  spacing: { before: 200, after: 80 },
  children: [new TextRun({ text: 'Editing', bold: true, size: 22, color: NAVY })],
}));
[
  '**Cut every loading wait.** Type → cut → reply lands. That alone saves 30–40 seconds across the demo.',
  'Head and tail each clip tight: start on the frame the command is sent, end one beat after the reply is fully visible.',
  'Subtitles: key phrases only, 3–6 words, bottom third. Full-transcript subtitles make it look like a lecture.',
  'One hard cut back to your face for the last two bullets, so you close on a person and not a terminal.',
  'If you run long, drop the depth-setting bullet in Beat 3. The /why table is the argument; depth is a detail.',
].forEach(t => body.push(note(t)));

const doc = new Document({
  creator: 'SignalDesk',
  title: 'SignalDesk — Project Showcase Script',
  numbering: {
    config: [{
      reference: 'say',
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: convertInchesToTwip(0.28), hanging: convertInchesToTwip(0.18) } } },
      }],
    }],
  },
  styles: {
    default: { document: { run: { font: 'Calibri', size: 23, color: INK } } },
  },
  sections: [{
    properties: { page: { margin: { top: 900, bottom: 900, left: 1000, right: 1000 } } },
    children: body,
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync('/home/user/signaldesk/docs/SignalDesk_Part2_Script.docx', b);
  console.log('written');
});
