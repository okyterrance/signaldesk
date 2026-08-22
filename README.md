# SignalDesk

A Telegram bot that reads twelve crypto and macro news feeds, ranks every
story with a transparent, configurable eight-factor score, and pushes a
written
briefing — plus an immediate alert when something cannot wait for the
morning. Each reader picks which subjects reach them and whether they want
figures or analysis; the formula shifts to match, and stays inspectable.

The point is not that an AI summarises the news. The point is **which
stories it picks, and that you can audit the choice**. Ask the bot `/why 1`
and it shows you the arithmetic.

```
🔍 Why #1 scored 0.808

Curve Finance exploited for $62 million in reentrancy attack
DL News · crypto

factor            raw     wt   adds
───────────────────────────────────
keyword          1.00  0.200  0.200
source_quality   0.95  0.200  0.190
recency          0.94  0.200  0.188
topicality       1.00  0.140  0.140
numeric          1.00  0.065  0.065
asset            0.50  0.050  0.025
analysis         0.00  0.065  0.000
source_count     0.00  0.080  0.000
───────────────────────────────────
TOTAL                         0.808

What drove it
• keyword — tier-1 keyword 'exploit'
• source_quality — DL News
• recency — 1.5h old

What held it back
• source_count — single source
```

---

## The problem

Anyone following crypto markets is drowning. Twelve feeds produce a few
hundred headlines a day, most of it listicles, price-prediction bait, and
the same story told six times by six outlets. The signal is in there; the
cost of finding it is forty minutes every morning.

The obvious fix — hand it all to a language model and ask for a summary —
fails in a specific and dangerous way. The model's selection is
unauditable. When it leads with the wrong story you have no way to find
out why, no way to reproduce it, and nothing to correct. You have traded
forty minutes of reading for a black box you cannot trust.

## The approach

Split the job at its natural seam.

**An algorithm decides what matters.** Deterministic, inspectable,
unit-tested. Same inputs, same ranking, every time.

**A model writes it up.** It receives the already-ranked list and is told
in its system prompt that selection is not its job. It cannot re-order,
cannot add stories, and cannot introduce a number that was not in the
input.

So when the briefing leads with the wrong thing, the fault is in a factor
weight — visible, reproducible, and fixable — instead of in a sampling
temperature.

## The pipeline

```
12 RSS feeds (concurrent, independently timed out)
        │
        ▼
 Stage 0 · hard filters          clickbait / price ticks / macro noise
        │                        binary, not a penalty: a listicle cannot
        │                        out-vote its way back in
        ▼
 Stage 1 · dedupe                TF-IDF cosine ∪ proper-noun overlap,
        │                        grown to transitive closure
        ▼
 Stage 2 · 8-factor score        weighted sum, normalised to 0–1,
        │                        two of the weights are the reader's
        │                        every score carries its breakdown
        ▼
 Stage 3 · category filter       reader's subjects; a hard filter,
        │                        not a penalty
        ▼
 Stage 4 · adaptive top-N        quality gate, per-subject diversity
        │                        cap, fixed count only as a floor
        ▼
 LLM write-up  ──────────────►  Telegram
```

Crypto and macro are scored in **separate buckets** with separate quotas.
Pooled together, a Fed decision loses on the asset factor by construction
— it names no token — and macro would quietly vanish from the digest.

### The eight factors

| factor | weight | what it measures |
|---|---|---|
| `keyword` | 0.185 | 4 tiers, highest hit wins. `fed`/`cpi`/`hack` → 1.0, `btc`/`defi` → 0.25 |
| `recency` | 0.185 | linear decay to zero across 24h |
| `source_quality` | 0.185 | per-outlet, FT/Bloomberg/The Block 1.0 → unrated 0.60 |
| `topicality` | 0.130 | topical gate from feed tags; untagged scores neutral, not zero |
| `source_count` | 0.075 | corroboration across outlets, saturating at 5 |
| `numeric` | 0.100\* | how many concrete figures the headline carries |
| `analysis` | 0.100\* | how much it reads as commentary rather than a bare report |
| `asset` | 0.040 | BTC/ETH 1.0, large alts 0.7, memecoins 0.3 |

\* `numeric` and `analysis` share a fixed 0.200 budget that the reader
splits with `/weights` — see **Your settings** below. Keeping the pair's
total constant means changing the preference re-weights *style* without
quietly changing how much subject matter, freshness or source reputation
count.

The interesting number is **`source_count` at 0.080**. Corroboration is
real evidence, so it earns a place — but weight it heavily and a big story
wins every slot for three days running, because every outlet keeps
re-reporting it. Capping its influence at 8% buys the corroboration signal
without letting yesterday's news squat on today's digest. There is a test
that pins this: a stale, low-quality item carried by nine outlets must
still lose to fresh tier-1 reporting from a top desk.

`keyword` uses **highest-tier-wins rather than a sum**. A headline stuffed
with mid-tier terms should not beat a plain one about the Fed.

## Commands

| command | does |
|---|---|
| `/top [n]` | highest-ranked stories right now |
| `/digest` | generate and send the briefing immediately |
| `/weights` | your settings — subjects, depth, and the resulting formula |

`/why <n>` prints the full factor breakdown for story *n*. It is kept off
the help screen to hold the command surface at three, but it is the thing
to reach for when a ranking looks wrong.

### Your settings

`/weights` is an inline keyboard, and everything on it is per-chat — two
readers of the same bot hold different settings.

**Subjects.** Five categories, single-label and first-match-wins in
priority order: 🔓 Security & risk, ⚖️ Regulation & policy, 🏦
Institutional flows, 📉 Macro & rates, ⚙️ Protocol & tech. An exploit at
an ETF custodian is a *security* story — the fact that moves a position
decides the label, so one story cannot occupy several of your slots.
Switching a subject off is a hard filter, not a penalty.

**Depth.** *Numbers* favours stories carrying hard figures; *Analysis*
favours commentary, explainers and attributed views; *Balanced* sits
between. The choice moves the two style weights and nothing else, and the
settings screen shows you the two numbers that changed.

Automatically: a **daily briefing** at a configured time, and an
**immediate alert** for anything scoring at or above the threshold — the
alert loop is where the scoring engine earns its keep, since a digest
answers "what happened yesterday" and an alert answers "this cannot wait".

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in three values
python main.py
```

Three keys, and one of them is optional to get started:

| variable | where | cost |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/botfather) → `/newbot` | free |
| `TELEGRAM_CHAT_ID` | run `python scripts/get_chat_id.py` | free |
| `TOKENROUTER_API_KEY` | TokenRouter console | ~cents/day |

**Everything else needs no key at all.** Twelve RSS feeds, Binance's public
ticker, and the alternative.me Fear & Greed index are all free and
unauthenticated. The bot's entire marginal cost is one LLM call per
digest.

### Without a bot token

```bash
python main.py --once     # live feeds, print the ranking, exit
python main.py --demo     # bundled sample data, no network at all
```

`--demo` runs the real parse → filter → dedupe → score → select path over
a fixed set of headlines. Only the network is faked; every number is
genuinely computed. It exists because conference wifi is not a thing to
bet a demo on.

### Tests

```bash
python -m pytest tests/ -q      # 122 tests, no network, no API key
```

The whole ranking path is deterministic, so a bad ranking is reproducible
in a test rather than something you re-run the bot and hope to see again.

## AI used

**Models** — Moonshot Kimi K3, falling back to xAI Grok 4.3, both via
TokenRouter's OpenAI-compatible endpoint. The chain is deliberately
*cross-family*: two models from one vendor give you a retry, not a
fallback, because an outage takes out both links at once.

Model slugs are entitlement-specific — a key answers HTTP 403 "no access
to model X" for anything outside its plan, and slugs do not transfer
between keys. `scripts/list_models.py` asks the provider what a given key
can actually call, which beats discovering it one failed run at a time.

**Where the model is and isn't** — it writes the briefing. It does not
select, rank, re-order, or fetch. The system prompt says so explicitly,
and the digest is assembled from an already-ranked list.

**Anti-hallucination** — the system prompt forbids any claim not grounded
in the supplied titles and summaries, and any number not present in the
input. When every provider fails, or returns 200 OK with empty content,
the bot falls back to template output built from the top-ranked headlines
verbatim. Degraded, honest, and still correctly ordered — the ranking
never depended on the model.

**AI coding tool** — built with Claude Code. Two bugs in this README's
"what worked" list below were found by Claude Code reading its own output,
not by a test.

## What I'd do differently

**What worked.** Making the score explain itself changed how I built it.
`/why` started as a nice-to-have and became the debugging tool: printing
the factor table next to a ranking is how both real bugs in this codebase
were caught.

The first was a `\b(exploit)\b` regex that could not match the word
*"exploited"*. A $62m protocol hack — the biggest story in the sample —
scored as untiered noise and ranked 7th. `ETFs` missed an `etf` entry that
only matched the singular. The tier table now stores stems and matches
inflections, with a parametrised regression test.

The second showed up in a rendered digest preview: the same Solana ETF
story appeared twice, from three outlets. Clusters were only compared
against their seed, so with A~B and B~C but A≁C, C was left orphaned.
Clusters are now grown to their transitive closure.

Both were invisible in aggregate and obvious the moment the intermediate
state was on screen. That is the argument for the whole design.

**What I'd improve.** The weights are hand-tuned, and honestly reasoned
rather than fitted. The right next step is to log every ranking alongside
which stories readers actually opened, then fit the weights against that —
turning seven defensible guesses into seven measured ones. Beyond that:
per-user topic profiles so the threshold means something different to a
DeFi desk than to a macro desk, and a second pass that scores *narrative
novelty*, so the fourth day of a running story is ranked lower than the
first even when every other factor is unchanged.

## Disclaimer

Educational and demonstrative. Nothing this bot outputs is financial
advice.
