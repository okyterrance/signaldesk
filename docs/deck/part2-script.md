# Part 2 — Project Showcase · Speaking Script

**Target: 4:30.** ~660 words at a steady 150 wpm, with pauses at the demo slides.
The same text is in each slide's speaker notes, so you can read from Presenter View.

Timings are cumulative. If you are running long, the slide marked **CUT** below is
the one to drop — it costs the least.

---

## Slide 1 · Title — SignalDesk `0:00 – 0:25`

> My project is **SignalDesk** — a Telegram bot that reads twelve crypto and macro
> news feeds, ranks every story with an eight-factor score, and writes a daily
> briefing.
>
> The interesting part isn't that an AI summarises the news. It's **which stories
> it picks** — and the fact that you can audit that choice.

---

## Slide 2 · The problem `0:25 – 1:00`

> The problem is volume. Twelve feeds produce about a hundred and fifty headlines
> a day, and most of it is noise — listicles, price predictions, and the same
> story told six times by six outlets.
>
> The obvious fix is to hand it all to a language model. But that fails in a
> specific way: **the model's selection is unauditable.** When it leads with the
> wrong story, you can't find out why, you can't reproduce it, and you have
> nothing to correct.
>
> You've traded forty minutes of reading for a black box.

---

## Slide 3 · The core decision `1:00 – 1:35`

> So I split the job at its natural seam.
>
> **An algorithm decides what matters.** Deterministic, unit-tested — same inputs,
> same ranking, every time.
>
> **The model only writes it up.** It receives the already-ranked list, and its
> system prompt tells it explicitly that selection is not its job. It can't
> re-order, can't add stories, can't introduce a number that wasn't in the input.
>
> That boundary is what makes the output auditable. When the briefing leads with
> the wrong story, the fault is in a **factor weight** — something I can see, test
> and fix — instead of in a sampling temperature.

---

## Slide 4 · What arrives `1:35 – 2:00`  📷

> Here's what actually arrives. *(gesture to screenshot)* A written briefing every
> morning at half past eight, with the ranked sources underneath it.
>
> And between briefings the bot polls every fifteen minutes. Anything above the
> threshold gets pushed immediately, on its own — because a digest answers *what
> happened yesterday*, and an alert answers *this can't wait*.

---

## Slide 5 · The pipeline `2:00 – 2:30`

> The pipeline is seven stages, and each one is separately testable.
>
> Fetch. Hard-filter the clickbait and the bare price ticks — binary, so a listicle
> can't out-vote its way back in. Dedupe, because twelve feeds covering one market
> means the same story arrives six times. Classify, score, select, then write and send.
>
> One detail worth calling out: crypto and macro are scored in **separate pools**.
> Pool them together and a Fed decision loses on the asset factor by construction —
> it names no token — and macro quietly disappears from the briefing.

---

## Slide 6 · The eight factors `2:30 – 3:00`

> Here's the formula. Eight factors, each normalised to zero-to-one, then weighted.
>
> They're a tuned set — change one and you shift the meaning of all the others. The
> most counter-intuitive is corroboration, at only seven and a half percent.
>
> Corroboration is real evidence, so it earns a place. But weight it heavily and
> one big story wins every slot for **three days running**, because every outlet
> keeps re-reporting it. Capping it low buys the signal without letting yesterday's
> news squat on today's briefing.

---

## Slide 7 · `/why` `3:00 – 3:25`  📷

> This command is the heart of the project. Ask it why story one is first, and it
> prints the arithmetic — every factor, its raw verdict, its weight, and what it
> contributed.
>
> That's deliberately **not** the model explaining itself. Asking a language model
> why it chose something gets you a plausible story, not the actual cause. This is
> the actual cause. And it adds up.

---

## Slide 8 · The reader's controls `3:25 – 3:50`  📷  **← CUT if running long**

> The reader also owns part of the formula.
>
> Five subject categories, and switching one off is a hard filter — "only show me
> security news" isn't a request to rank macro *slightly* lower.
>
> And depth. Two of the eight factors share a fixed budget that the reader splits.
> Because the total never changes, choosing a style never quietly alters how much
> subject matter or freshness count.

---

## Slide 9 · Use of AI `3:50 – 4:15`

> So where is the AI, and where is it deliberately not?
>
> In the product: **Moonshot's Kimi K3**, falling back to **xAI's Grok 4.3**. The
> chain is cross-vendor on purpose — two models from one provider give you a retry,
> not a fallback, because an outage takes out both.
>
> Building it: **Claude Code**, as a pair programmer throughout.
>
> And this is the system prompt that enforces the boundary — the list is already
> ranked, selection is not your job, never invent a number. When every provider
> fails, the bot falls back to template output from the top-ranked headlines.
> Degraded, honest, and still correctly ordered — because the ranking never
> depended on the model.

---

## Slide 10 · The bug the factor table found `4:15 – 4:45`  📷

> Now the part I'd most like you to take away.
>
> That transparency command started as a nice-to-have. It became the debugging
> tool — **every real bug in this codebase was found by reading the factor table
> next to a ranking, and not one was caught by a test.**
>
> The clearest example: a regex looking for the word *exploit* could not match
> *exploited*. So a sixty-two-million-dollar protocol hack scored **zero** on the
> keyword factor — untiered noise — and ranked seventh. After the fix it scores
> one, top tier, and ranks second.
>
> Invisible in aggregate. Obvious the moment the intermediate state was on screen.

---

## Slide 11 · Reflections `4:45 – 5:00`

> What worked was making the score explain itself. It changed how I built the whole
> thing, and it's the decision I'd repeat.
>
> What I'd change: the weights are **reasoned, not fitted**. Every one is
> defensible; none is measured. The next step is logging each ranking against which
> stories readers actually open, and fitting them — turning eight arguments into
> eight numbers.
>
> And I'd be honest that the classifier will keep having gaps. It's regular
> expressions over open-ended language — I've fixed five rounds of them, each one
> found by looking at real output. That's not a thing that finishes. Thank you.

---

# Screenshots to take

Take these on your own machine with the bot running, then drop each image on top of
its dashed placeholder in the deck and delete the placeholder box.

| Slide | What to capture | How |
|---|---|---|
| **4** | Telegram — the daily briefing | `/digest`. Capture the headline, several bullets, and the ranked Sources list. Two stitched screenshots is fine. |
| **7** | Telegram — `/why 1` | Run `/top` first, then `/why 1`. The factor table must be legible — this is the most important image in the deck. |
| **8** | Telegram — `/weights` | The settings screen with the five toggles, the depth buttons, and the weight table below them. |
| **10** | The ranking flip | `python scripts/show_regex_bug.py` — it rebuilds the broken matcher and prints both rankings side by side. One terminal window is the whole slide. |

**Two things that make the screenshots read on video**

1. Use Telegram's **light** theme — dark screenshots lose detail after video compression.
2. Zoom the Telegram window before capturing (`Cmd +`) so the mono factor table is
   large. Legibility beats fitting everything in one frame.

**Optional extra credit:** a short screen recording instead of a static image on
slide 4 or 7 — an actual command going out and the reply arriving is more convincing
than any still.

---

# Notes on delivery

- **Slides 3 and 10 carry the argument.** If you rehearse only two, rehearse those.
- Say the numbers out loud — "sixty-two million", "seven and a half percent". Read
  aloud they land; skimmed off a slide they don't.
- On slide 10, pause after "*and not one was caught by a test*". That sentence is
  the strongest thing in the whole submission — give it a beat.
- Don't apologise for the limitations on slide 11. Stating them plainly reads as
  engineering judgement; hedging around them reads as uncertainty.
