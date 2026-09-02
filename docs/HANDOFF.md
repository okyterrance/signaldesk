# SignalDesk — handoff prompt

Paste this whole file as your first message in a new session. It is written to
work in two places: a **Claude Code session with the repo attached** (do the
work) and a **plain LLM chat with no file access** (reason about the design).
Both paths are marked below.

---

## 0 · What you are being asked to do

You are picking up a project mid-flight. Read everything below, then wait for
the user's instruction — do not start changing things on your own.

**If you have the repo:** `github.com/okyterrance/signaldesk`, branch
`claude/add-more-repos-c9xlpt` (HEAD `b0515b6`). Everything described here is
in that branch. Run `python -m pytest -q` first — it should report **148
passed** in about 10s, fully offline. If it doesn't, say so before anything
else.

**If you don't have the repo:** everything you need to reason about the design
is written out below. Do not guess at file contents; ask.

---

## 1 · The person and the deadline

Terrance (okyterrance). CUHK Statistics, transferred in from HKU Engineering.
Interning on an OTC desk at HashKey. Wants a research career — long/short
equity, supply-chain and thematic work.

He is submitting to the **Polymer Capital Tech Expo 2026** (Hong Kong). The
submission is exactly two files:

1. a video, **≤ 7 minutes**, Part 1 self-introduction + Part 2 project showcase
2. a **1-page PDF** write-up, minimum 11pt font

Part 2 must cover, in order: what you built · how it works · how AI was used
(coding tools, system prompts with examples, models/APIs) · iterations and
reflections. The write-up must cover: problem statement · solution overview ·
use of AI · impact & value · reflections.

⚠️ **Unresolved and important.** The deadline recorded from the Expo page was
**23 Aug 2026**, and the session where that was noted ran on **28 Aug 2026**.
Either the note is wrong or the date moved. Confirm this before recommending
any multi-day work — it changes every recommendation below.

---

## 2 · The project: SignalDesk

A Telegram bot that reads 12 crypto and macro RSS feeds, ranks every story with
an auditable eight-factor score, and lets an LLM write up **only what the
algorithm already selected**. Pushes a briefing at 08:30 Asia/Hong_Kong daily.

### The design thesis — this is the whole point

> **The algorithm selects. The model only writes.**

Hand the pile to an LLM and ask for a summary, and its selection is
unauditable: when it leads with the wrong story you cannot find out why,
reproduce it, or correct it. So the job is split at that seam. A deterministic,
unit-tested scorer decides what matters; the model receives the already-ranked
list and is told in its system prompt that selection is not its job.

Consequence: a wrong lead story is a **wrong factor weight** — visible,
testable, fixable — instead of a sampling temperature.

### Pipeline (`src/pipeline.py:41`)

```
fetch → hard filters → dedupe → classify → score → adaptive top-N → LLM → Telegram
```

- **Hard filters** (`src/scoring/filters.py`) are binary, not penalties:
  clickbait, bare price ticks, off-topic macro. A listicle cannot out-vote its
  way back in.
- **Dedupe** (`src/scoring/dedup.py`): TF-IDF cosine ∪ proper-noun entity
  overlap ∪ rare-entity match, grown to **transitive closure** by BFS.
  Threshold 0.50.
- **Separate crypto/macro pools.** Pooled together, a Fed decision loses on the
  asset factor by construction — it names no token — and macro silently
  disappears from the briefing.
- **Adaptive top-N** (`select_top`): quality gate at 0.30 first, per-subject
  diversity cap `max_per_subject=3`, `min_n` as a floor only.
  crypto 6–12, macro 3–6.

### The eight factors (`src/scoring/weights.py`)

```
score = Σ(weight_i × factor_i) / Σ(weight_i)      → normalised to [0, 1]

keyword         0.185   how consequential the subject is (4 tier table)
recency         0.185
source_quality  0.185
topicality      0.130   from the category classifier
numeric         0.100 ┐ style budget, see below
analysis        0.100 ┘
source_count    0.075   corroboration — deliberately light
asset           0.040   tie-breaker
```

Every score carries a full `ScoreBreakdown` (`src/models.py`), which is what
`/why` prints.

**Why `source_count` is light (0.075):** corroboration is genuine evidence, so
it earns a place — but weight it heavily and one big story wins every slot for
three days running, because every outlet keeps re-reporting it. Capping it low
buys the signal without letting yesterday's news squat on today's briefing.

**The style budget.** `numeric + analysis` share a fixed **0.200**, split by
the reader's depth preference: `data` 85/15, `balanced` 50/50, `analysis`
15/85. Because the pair's total never changes, choosing a style never quietly
alters how much subject matter, freshness or source reputation count. The
budget was raised from 0.130 after measuring that the smaller share could not
move the top of a real ranking — adjacent items sat 0.04–0.06 apart while the
largest swing the pair could produce was 0.035. *An explicit reader preference
that cannot reorder anything is not a preference.*

### Five reader categories (`src/scoring/categories.py`)

Single-label, first-match-wins, in priority order:
`security` → `regulation` → `flows` → `macro` → `protocol`.

Switching one off in `/weights` is a **hard filter**, not a nudge. Category
filtering runs *after* dedupe (so corroboration counts over the whole feed) and
*before* scoring (so top-N thresholds apply to the slice the reader sees).

`src/bot/format.py` and the preference layer read `CATEGORY_IDS` /
`CATEGORY_LABELS` / `CATEGORY_EMOJI` — they are **name-agnostic**, so changing
the category set does not touch the bot layer.

### Data and models

- **12 RSS feeds** (`src/fetchers/rss.py`) — crypto: CoinDesk, The Block,
  Decrypt, The Defiant, DL News, Unchained · macro: CNBC, FT Markets,
  Bloomberg, SCMP Business, Channel News Asia, ECB Press.
- **Binance** 24h ticker + **alternative.me Fear & Greed**. Free, no keys.
- **LLM:** `moonshotai/kimi-k3` → `x-ai/grok-4.3`, via TokenRouter's
  OpenAI-compatible endpoint. Cross-vendor on purpose: two models from one
  provider are a retry, not a fallback. When every provider fails the bot emits
  template output from the top-ranked headlines — degraded, honest, still
  correctly ordered.

System prompt (`src/llm/digest.py:20`), abridged:

> "You will be given a numbered list of stories that has **ALREADY been
> selected and ranked** by a scoring engine. **Selection is not your job.** Do
> not re-order them… **Never invent a number.** Prices, percentages and dollar
> amounts may only appear if they appear in the input… The headline MUST be
> about story 1 — choosing a different story to headline is a selection
> decision."

### Command surface

`/top` · `/weights` · `/digest`. `/why` stays registered but is hidden from
`/help` — the surface is three, the audit path stays available.

`/weights` is an interactive settings screen: five category toggles plus a
numbers-vs-analysis depth setting, persisted per chat with atomic JSON writes.
The digest cache is keyed by `(categories, depth)`.

### Config worth knowing

`digest_time 08:30` Asia/Hong_Kong · `alert_threshold 0.72` ·
`alert_poll_minutes 15` · `digest_bullet_max 10` · `select_threshold 0.30` ·
`dedupe_threshold 0.50`.

---

## 3 · Submission artefacts already built

| File | What |
|---|---|
| `docs/writeup.html` → `writeup.pdf` | **The submission.** Expo's five headings, Polymer house style, verified 1 page (1034px of 1047px usable), body at the 11pt minimum |
| `docs/onepager.html` | On-screen aid for the recording: **four full-viewport panels**, one per Expo requirement. Page Down between them |
| `docs/deck/cue-card.html` → `cue-card.pdf` | 1-page bullet cue card used while recording — timings, which screen to show, the 5 lines to say verbatim, one pause marker, cut-order |
| `docs/deck/part2-script.md` | The prose Part 2 script, for rehearsal. Measured 521 words = 3:28 |
| `docs/deck/full-script.md` | Part 1 wording only. **Its Part 2 is superseded** (banner at the top of the file) |
| `scripts/build_pdf.py` | Renders `docs/<stem>.html` to PDF via Playwright and **fails loudly** if it exceeds the page budget. `python scripts/build_pdf.py` / `... deck/cue-card 1` |
| `scripts/show_regex_bug.py` | Rebuilds the broken keyword matcher from the live tier table and prints both rankings side by side |
| `docs/deck/SignalDesk_Part2.pptx` | **Obsolete.** Older slide ordering, wrong format for a no-face one-take. Do not use |

### The video plan

No face. One continuous screen recording, voice over, two windows only:
browser (`onepager.html`, fullscreen) and Telegram (light theme, zoomed).

- **Part 1 already recorded at 3:00.**
- Part 2 script runs 3:28 of narration + ~18s of on-camera waiting ≈ **3:46**.
- **Total ≈ 6:45 against a 7:00 cap — only ~15s of slack.** If he speaks
  slowly, the first cut (the depth sub-bullets in step 2, ~18s) should be taken
  *before* recording.

---

## 4 · Bug history — read this before touching the classifier

Every real bug in this project was found by **reading the factor table next to
a ranking**. Not one was caught by a test. That is the single most important
fact about this codebase.

| Bug | Fix |
|---|---|
| `\b(exploit)\b` cannot match *"exploited"*; `ETFs` missed an `etf` entry | Stems + inflection suffixes `(?:s\|es\|ed\|d\|ing\|er\|ers\|cy)?`. A $62m hack scored **0.00** on the heaviest factor and ranked **7th of 8**; after the fix, 1.00 and **2nd** |
| Dedupe wasn't transitive — A~B, B~C but A≁C left duplicates | BFS transitive closure |
| `treasur\w+` in `flows` stole "Treasury yields climb" | Only `corporate treasury` / `treasury holdings` in flows; bare form to macro |
| `fund\|funds` in `flows` swallowed three equity stories in one digest | Qualified as crypto vehicles only, one intervening word allowed; macro gained broad-market vocabulary |
| `sanction\|tariff` in `regulation` returned Iran/India geopolitics | Moved to macro. OFAC stays — it is enforcement against a named entity |
| `institution\w*` lost in a rewrite; `suing` missing beside `sued` | Restored qualified; `tax` qualified so it can't outrank macro |
| Silent 4096-char Telegram truncation — a 12-story digest rendered 6 sources | `split_messages()` on blank lines; every send goes through `src/bot/send.py` |
| `numeric` had mean 0.72 and one zero in twelve — no discrimination | Regraded (0/1/2/3+ figures → 0.0/0.35/0.75/1.0), stricter regex ("S&P 500" is no longer a figure), budget 0.130 → 0.200 |
| `0.649` displayed as "Notable 0.65" against a 0.65 band boundary | Band on the **rounded** value |
| `.env` had `# DIGEST_TIME=11:43` — `#` **is** a comment in `.env` | Remove the `#` |

**The root-cause habit behind three of these:** adding a broad word to a
category tested early, then verifying only that the intended headline matched.
The fix is **bidirectional tests** — assert what a term must catch *and* what
it must leave alone. Do this for every regex you touch.

**Second recurring lesson:** a correct engine that lets the reader think it is
broken costs the same as a bug. Hence `scope_note()` ("Filtered to 🏦
Institutional flows — 2 of 47 stories matched") and `depth_note()` ("Only 4 of
12 stories carry analyst framing today, so Analysis had little to reorder").

---

## 5 · The open decision: pivot to RWA / tokenisation / ETF

Under discussion, **not started**. The argument, the design, and the honest
costs:

### Why it's strategically better

Part 1 is about long/short equity theme research — mapping a supply chain to
find who actually captures the margin versus who just mentions it on an
earnings call. Part 2 is currently "a crypto news bot." Two stories.

Tokenisation/RWA **is** a theme with real public-market exposure (BlackRock,
Franklin Templeton, Circle, Coinbase, DTCC, Broadridge, custodians, transfer
agents). Narrowing to it makes Part 1 and Part 2 **one story**.

### Why news alone won't work

RWA news volume is thin — one live run showed a single category matching **2 of
47** stories. A briefing that says "nothing happened" three days a week demos
badly. The market is small *in news* but rich *in data*.

### The design: make data a first-class ranked item

Today market data is a decorative panel at the top of the digest — not scored,
not ranked, not part of selection. Invert that. Turn each tracked time series
into a synthetic item that competes with news in the same ranking:

```
title:  "BUIDL AUM +$340m in 7d to $2.9bn (+13.3%)"
source: "onchain · Ethereum"
kind:   "data"
```

It then flows through the **same** eight-factor engine, dedupe and top-N.
`NewsItem` gains a `kind` field; the pipeline gains a bucket. Nothing else
moves.

**The key algorithm — `surprise` as a z-score.** News uses keyword tiers to
judge "how consequential." Data's equivalent is "how unusual":

```
surprise = (today's delta − trailing 30d mean of deltas) / trailing stdev
```

This makes series of wildly different sizes comparable without hand-tuning a
threshold per series. **And it is measured, not reasoned** — which directly
repairs the project's stated weakness ("the eight weights are reasoned, not
fitted"). The pitch becomes: the news half is reasoned, the data half is
measured, and that is the direction I'd take the rest.

**Cross-modality corroboration.** `source_count` today means "how many outlets
ran this." Extend it to link a data move and a news item about the same entity:
BUIDL AUM +$340m (on-chain) + "BlackRock expands BUIDL to a new chain" (news)
= one story, two **independent** confirmations. Outlets copy each other; the
chain does not. This is what rescues thin-news days — 3 headlines, but 20 data
series still producing signal.

**New requirement: state.** A z-score needs a trailing window, and the bot is
stateless today apart from `preferences.json`. You need a small persisted time
series (SQLite or per-series JSON). ~150 lines plus tests. Side benefit: with
history you can finally fit the weights against what readers actually open.

### Proposed category set

```
issuance        new tokenised products, chain expansions, new asset classes
flows           AUM changes, net in/outflows, supply             ← data-led
infrastructure  custody, transfer agents, settlement, cross-chain
regulation      SFC / SEC / MiCA / licensing
collateral      tokenised treasuries as collateral, repo, MMFs
```

### Data sources — ALL UNVERIFIED

The environment where this was designed had **all outbound web access
blocked**, so none of these were tested. Confirm each endpoint exists and its
shape before building on it:

- **DefiLlama** (`api.llama.fi`) — free, no key. RWA category TVL, protocol
  TVL, stablecoin supply. **Start here**; it's the only one likely to be both
  free and keyless.
- **On-chain token supply** for BUIDL / BENJI / OUSG / PAXG / XAUT.
  supply × NAV ≈ AUM, and it is the most authoritative source because it is the
  chain itself. Etherscan-class API, free tier needs a key.
- **rwa.xyz** — the sector's standard tracker; the good endpoints are believed
  to be gated.
- **Issuer primary disclosures** — Franklin Templeton (BENJI), Ondo,
  Securitize. First-party, no licensing problem.

News feeds would change too: drop Decrypt, The Defiant, CNA, SCMP; add Ledger
Insights (highest RWA density in English), issuer blogs, and SFC / SEC / MAS
press feeds.

### A design decision to make deliberately

On genuinely quiet days, **do not let the bot pad**. Drop `min_n` entirely,
keep the quality gate, and display honestly: *"3 signals today · 12 series
unchanged."* A product that knows when to shut up is a feature worth
demonstrating.

### Cost

**3–4 days**, not the ~1 day a pure vocabulary swap would take — the state
layer, verifying every new source live, and the certainty that new category
regexes will produce fresh over-match bugs.

---

## 6 · Constraints and rules

- **Never paste API keys or the Telegram bot token into a chat.** They live
  only in the local `.env`, which is gitignored and has never been committed.
  Verified.
- **Do not use the company's SoSoValue key.** Paid market-data licences are
  typically per-entity, and this bot *redistributes* data to third parties
  (Telegram users today, a public site later), which most such licences forbid.
  If SoSoValue is wanted, get a separate personal key.
- **Adding any paid, licence-restricted source breaks the product's own
  argument.** The write-up's case for a free subscription site rests on the
  data layer costing nothing and carrying no redistribution limits. The free
  data layer is not a compromise — it is the business model.
- The originating environment had **no outbound network** (RSS, Binance,
  Telegram, TokenRouter all blocked), so everything was verified offline with
  fixtures plus the user's own live runs. If you have network, **re-verify
  anything that touches a live endpoint** rather than trusting a claim here.
- The user runs **zsh**, where `interactive_comments` is off by default: a
  pasted multi-line block containing `#` comments fails. Give one command per
  code block, no inline comments.
- All work goes on branch `claude/add-more-repos-c9xlpt`. Do not open a PR
  unless asked.

---

## 7 · Where things stand

Done: the engine, 148 passing tests, the live bot (12/12 feeds, real digests
written by Kimi K3, the 08:30 scheduled push fired unattended), the 1-page
write-up PDF, the on-screen one-pager, the cue card, the Part 2 script.

Outstanding, in priority order:

1. **Confirm the Expo deadline.** Everything else depends on it.
2. Record Part 2 (Part 1 is done at 3:00) and edit.
3. Decide the RWA pivot — the honest fallback if time is short is to keep the
   product as-is and add one line to the reflections: *"the engine is
   theme-agnostic; swap the category set and the feeds and the same ranking
   runs over a narrower, higher-value vertical — tokenisation, RWA and ETF
   flows, a theme with real public-market exposure."* Zero code, and it makes
   the stronger claim: this is a platform, not a bot.
4. If the pivot is on: start with `src/models.py` (`kind` field) + the time
   series store, and a DefiLlama fetcher — confirm that source actually carries
   the data before investing in the rest.
