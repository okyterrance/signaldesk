# Polymer Tech Expo 2026 — Video Script

**Format:** talking head for Part 1 → screen recording (Telegram + terminal) with
voice-over for Part 2.
**Runtime: 6:20.** Part 1 = 2:05, Part 2 = 4:15. The cap is 7:00, so there is
40 seconds of headroom.

**911 spoken words**, counted. That is 6:04 at 150 wpm, plus ~16 seconds of
deliberate demo silence (the `/why` hold, the ranking flip) — 6:20 in total. The
timestamps on each beat assume that pace; if you read slower than 150 wpm, add
about 25 seconds and you are still inside the cap. Only if you land over 6:45 cut
the two blocks marked **CUT-1** and **CUT-2** — together they cost 30 words and
no argument.

**Language.** Written for an English read. Say it in your own words rather than
reciting — the sentences are shaped to be spoken, not read aloud verbatim.

This replaces the slide-based `docs/deck/part2-script.md` for a live-demo format;
that deck and its script still stand if you'd rather present slides.

**Placeholders:** `[NAME]`, `[YEAR]` (e.g. "third-year"), `[RESEARCH TOPIC]` —
one concrete phrase for what your research project was about.

---

# PART 1 — Self-introduction  `0:00 – 2:05`

Shot: you on camera, framed chest-up, one clean light source. No slides here —
the face is the point. Subtitles are short key phrases, never full transcript.

---

### Beat 1 · Branding line `0:00 – 0:16`

> 🎬 **SHOT** — straight to camera, no title card yet.
> 💬 **SUBTITLE**: `Researcher who builds his own tools`

> Hi, I'm **[NAME]**, a [YEAR] Statistics student at CUHK.
>
> My one line: I'm a **researcher who builds his own tools**. I look at markets
> bottom-up — supply chains, themes, who actually benefits — and I build the
> software that research needs.

---

### Beat 2 · Background `0:16 – 0:40`

> 🎬 **SHOT** — same frame. Optional: corner cards fading in for `Insurance` /
> `Traditional finance` / `Crypto` as you name them.
> 💬 **SUBTITLE**: `Insurance · Traditional finance · Crypto`

> My background is deliberately broad: my own research project on [RESEARCH
> TOPIC], plus exposure across insurance, traditional finance and crypto — three
> industries that price risk in completely different languages.
>
> They all push you toward one question, and it's the one that draws me to
> **long/short equity**: who actually benefits from a theme, and who is just being
> repriced alongside it.

*(**CUT-1** = the clause "— three industries that price risk in completely
different languages.")*

---

### Beat 3 · AI journey `0:40 – 1:17`

> 🎬 **SHOT** — hold on your face. Don't cut away during this beat; it's the one
> they'll remember.
> 💬 **SUBTITLE**: `Prompting = building the logic chain first`

> AI changed how I work, and not the way I expected.
>
> I don't come from a coding background, and AI makes the distance between an idea
> and a working thing very short. But the real lesson was this: **prompting a model
> well means building the whole logic chain in your own head first.**
>
> If my thinking is vague, the code comes out messy. If I can state the structure —
> the stages, what each does, and why — the output is clean. AI didn't make
> thinking optional; it made thinking the job.

---

### Beat 4 · Fun fact `1:17 – 1:44`

> 🎬 **SHOT** — lighter delivery, allow the smile. Hard cut in and out; this beat
> earns a punchy subtitle.
> 💬 **SUBTITLE**: `Turned down HKU Engineering → got assigned there anyway`

> Fun fact. I once had the chance at an offer for Engineering at HKU, and I turned
> it down — because I thought coding was boring.
>
> Then JUPAS assigned me to HKU Engineering anyway. I later transferred to CUHK
> Statistics.
>
> I was wrong. What was boring was the mechanical part — exactly the part AI
> handles now. What's left is the logic: the part I actually wanted.

---

### Beat 5 · Career aspiration `1:44 – 2:05`

> 🎬 **SHOT** — straight to camera, then hold one beat of silence before the cut
> to Part 2. That silence is what makes the transition feel deliberate.
> 💬 **SUBTITLE**: `Research · learn fast · give it back to the team`

> From a summer internship I want **research work**: to test my ideas against a
> real desk, learn fast enough to give something back to the team, and sit next to
> people better than me.
>
> The project I'm about to show you started exactly that way.

---

# PART 2 — Project showcase  `2:05 – 6:20`

Shot: full screen recording from here. Your face can stay in a corner bubble or
disappear — pick one and keep it.

---

### Beat 6 · What it is, and who it's for `2:05 – 2:38`

> 🎬 **SHOT** — title card `SignalDesk`, then cut to the Telegram window idle,
> before anything is typed.
> 💬 **SUBTITLE**: `Free subscription briefing · crypto + macro in one place`

> This is **SignalDesk**.
>
> It's for someone who needs to get across a market quickly, from several angles
> at once — crypto and macro in one place — without forty minutes of headlines to
> find the five that matter.
>
> Today it's a **Telegram bot**, and that's what I'll demo. What I'm building
> toward is a **free subscription site**: readers subscribe, a ranked briefing is
> pushed every morning, it costs them nothing — and it becomes a distribution
> channel for the desk behind it.

---

### Beat 7 · Demo 1 — how you actually use it `2:38 – 3:21`

> 🎬 **SHOT LIST** — record each command as a clean take, then cut:
> 1. Type `/top` → **cut the loading wait** → the ranked list arriving.
> 2. Slow scroll. Highlight box (in editing) around story 1's score and its
>    `drivers:` line.
> 3. Type `/digest` → **cut the wait** → the briefing. Scroll to the Sources
>    list at the bottom and stop there.
> 4. Optional: a push notification on a phone lock screen. Skip if you don't
>    have one — the words carry it.
> 💬 **SUBTITLES**: `/top — the ranking right now` · `/digest — the written
> briefing` · `08:30 daily · alerts every 15 min`

> Three commands, and that's all of it.
>
> `/top` is the ranking right now — every story with its score and the three
> factors that pushed it up.
>
> `/digest` writes the briefing: one headline, one line per story, market snapshot
> on top, every source underneath so you can check any claim yourself.
>
> And you don't have to type anything. The digest goes out on its own at half past
> eight every morning; in between, the bot polls every fifteen minutes and pushes
> anything scoring **0.72 or above** immediately. A digest answers *what happened
> yesterday*; an alert answers *this can't wait*.

---

### Beat 8 · Demo 2 — where the numbers come from `3:21 – 4:28`

> 🎬 **SHOT LIST**:
> 1. Two seconds on the feed list in `src/fetchers/rss.py` — twelve rows on
>    screen. Don't scroll; just let it be seen.
> 2. Type `/weights` → **record yourself tapping a subject toggle off and moving
>    depth to `Analysis`**, then show the two weight numbers below changing.
>    Speed-ramp the tapping to ~1.5×.
> 3. Type `/why 1` → **hold on the factor table for a full five seconds, zoomed
>    in.** This is the most important frame in the video.
> 💬 **SUBTITLES**: `12 RSS feeds · Binance · Fear & Greed — no paid data` ·
> `Subject toggles are hard filters` · `/why — arithmetic, not the model's opinion`

> So where do the numbers come from?
>
> Twelve RSS feeds — CoinDesk, The Block and DL News on crypto; FT, Bloomberg and
> the ECB press feed on macro — plus Binance's public ticker and the Fear and Greed
> index. **None of it is paid data.**
>
> Every story is scored on **eight factors**: keyword tier, recency, source
> quality, topicality, corroboration, figures, analysis, asset.
>
> `/weights` hands part of that formula to the reader: five subject toggles —
> switching one off is a **hard filter**, not a penalty — and a depth setting that
> shifts weight between *numbers* and *analysis*.
>
> And this is the command I care most about. `/why 1` prints **the arithmetic**:
> every factor, its raw value, its weight, what it contributed.
>
> That's deliberately *not* the model explaining itself. Ask a model why it chose
> something and you get a plausible story, not the cause. This is the cause — and
> it adds up.

---

### Beat 9 · Use of AI — and where it deliberately isn't `4:28 – 5:26`

> 🎬 **SHOT LIST**:
> 1. Cut to `SYSTEM_PROMPT` in `src/llm/digest.py`. Highlight the line
>    *"Selection is not your job."*
> 2. Terminal: `python -m pytest tests/ -q` → cut to the green `148 passed`.
> 3. Two seconds of a real Claude Code session in your terminal.
> 💬 **SUBTITLES**: `Algorithm ranks · model only writes` · `"Selection is not
> your job"` · `Kimi K3 → Grok 4.3 · built with Claude Code`

> So where is the AI, and where is it deliberately not?
>
> **The ranking is not AI.** It's a deterministic algorithm — same inputs, same
> output — with **148 offline tests** on that path.
>
> The model only **writes**. It's handed the ranked list, and the system prompt
> says it plainly: *selection is not your job, don't re-order, never invent a
> number.* If every provider is down, it falls back to a template of the top
> headlines — degraded, but still correctly ordered.
>
> The models are **Moonshot's Kimi K3**, falling back to **xAI's Grok 4.3** —
> cross-vendor on purpose, because two models from one provider are a retry, not a
> fallback.
>
> And I built all of it with **Claude Code**, working at the level of "here are the
> stages, here's why this weight is low, here's the test that has to pass." My job
> was the logic chain.

---

### Beat 10 · Iterations and reflections `5:26 – 6:20`

> 🎬 **SHOT LIST**:
> 1. Terminal: `python scripts/show_regex_bug.py` — prints the broken and fixed
>    rankings side by side. Let the flip land.
> 2. Highlight the row moving from 7th to 2nd.
> 3. **Cut back to your face** for the last two sentences. Closing on a person
>    rather than a terminal is worth the extra cut.
> 💬 **SUBTITLES**: `Every real bug found by reading the factor table` ·
> `` `exploit` didn't match `exploited` `` · `Next: fit the weights, ship the site`

> Two reflections.
>
> **What worked** was making the score explain itself. `/why` started as a
> nice-to-have and became my debugging tool — every real bug here was found by
> reading the factor table next to a ranking, and **not one was caught by a
> test.**
>
> The clearest example: a regex looking for the word *exploit* couldn't match
> *exploited*. So a sixty-two-million-dollar protocol hack scored **zero** on the
> keyword factor and ranked seventh. After the fix, second.
>
> **What I'd improve given more time:** the weights are **reasoned, not fitted**.
> I can defend every one; none is measured. The next step is logging each ranking
> against what readers actually open, and fitting the weights to that — and then
> the site itself: subscriptions, and per-reader profiles.
>
> Thank you.

---

# Recording checklist

**Before recording the screen**

- Telegram in **light** theme. Dark screenshots lose the mono factor table after
  video compression.
- Zoom Telegram up two or three steps (`Cmd/Ctrl +`). Legibility beats fitting
  more in frame.
- Clear the chat first, so the demo reads top-to-bottom with nothing stale above.
- `python main.py` on live feeds if the wifi is good; `python main.py --demo` is
  the safe fallback and every number in it is genuinely computed.
- 1080p minimum. The factor table is the one thing that must survive compression.

**Captures needed**

| Beat | Capture | Command |
|---|---|---|
| 7 | Ranked list | `/top` |
| 7 | Briefing + Sources list | `/digest` |
| 8 | Feed list, ~2s | open `src/fetchers/rss.py` |
| 8 | Settings, **with a toggle being tapped** | `/weights` |
| 8 | Factor table — hold 5s, zoomed | `/why 1` |
| 9 | System prompt, `Selection is not your job` | open `src/llm/digest.py` |
| 9 | Green test line | `python -m pytest tests/ -q` |
| 10 | Ranking flip, 7th → 2nd | `python scripts/show_regex_bug.py` |

**Editing**

- **Cut every loading wait.** Type → cut → reply lands. This alone saves 30–40
  seconds across the demo.
- Head and tail each clip tight: start on the frame the command is sent, end one
  beat after the reply is fully visible.
- Subtitles: key phrases only, 3–6 words, bottom third. Full-transcript subtitles
  make it look like a lecture.
- One hard cut back to your face at the end of Beat 10.

**Trims, if you land over 6:45**

- **CUT-1** — Beat 2, the "— three industries that price risk in completely
  different languages" clause (−12 words).
- **CUT-2** — Beat 8, the depth-setting clause ("— and a depth setting that
  shifts weight between *numbers* and *analysis*"), keeping the subject toggles
  (−18 words). The `/why` table is the argument; depth is a detail.
- Do **not** cut Beat 3 or the `/why` explanation in Beat 8. Those two are what
  the submission is judged on.
