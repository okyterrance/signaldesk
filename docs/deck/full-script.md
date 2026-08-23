> **Superseded for Part 2.** Part 1 was recorded at 3:00 from this draft.
> The Part 2 now being filmed is the one-take screen recording in
> [`part2-script.md`](part2-script.md), against `docs/onepager.html`.
> Keep this file only for the Part 1 wording.

# Video Script — Part 1 + Part 2

**894 spoken words → 5:58 at 150 wpm.** With pauses at the demo, expect
**6:10 – 6:30**. Limit is 7:00.

| | | |
|---|---|---|
| **Part 1** · self-introduction | face to camera, full frame | **1:55** |
| **Part 2** · project showcase | slides + screen recording, you in the corner | **4:05** |

Part 2 follows the four Expo requirements in order, so a reviewer ticking
boxes never has to hunt.

---
---

# PART 1 · SELF-INTRODUCTION `0:00 – 1:55`

*Face to camera. No slides.*

## 1 · One line `0:00 – 0:20`

> Hi, I'm **[NAME]**, a **[YEAR]**-year Statistics student at CUHK.
>
> One line: **I research markets, and I build the tools research needs.**
>
> I've worked on research across **insurance, traditional finance, and crypto** —
> three industries that price risk in completely different ways.

*Subtitle: `Insurance · Traditional finance · Crypto`*

## 2 · What I'm interested in `0:20 – 0:45`

> What I keep coming back to is **long/short equity research**. Mapping a supply
> chain to find who actually captures the margin. Taking a theme and working out
> which companies are genuinely exposed to it, versus which ones just mention it
> on an earnings call.
>
> And the honest truth about that work: **the analysis isn't the slow part.
> Deciding what's worth reading is.**

*Pause. This line is the bridge to the project.*

## 3 · My AI journey `0:45 – 1:15`

> Which brings me to AI.
>
> The obvious thing to say is that it writes code. True — but not what changed
> things for me.
>
> **What changed is that AI made me think more logically.** Talking to a model
> forces you to build a complete logic chain before you speak: what you want, in
> what order, why each step follows the last.
>
> And the clearer that chain is, **the cleaner the project that comes out.**
> Vague instructions give you vague software.
>
> AI didn't replace the thinking. It moved the thinking to **structure instead
> of syntax.**

## 4 · Fun fact `1:15 – 1:40`

> My fun fact is slightly embarrassing.
>
> I once had a shot at an offer from **HKU Engineering** — and turned it down,
> because I thought coding was boring.
>
> Then JUPAS assigned me to **HKU Engineering anyway.**
>
> So I transferred out, to **Statistics at CUHK.** Still running.
>
> And now I build software for fun. *(beat)* I was wrong — but specifically:
> what I disliked was never the logic. It was the syntax. **AI removes exactly
> that part.**

*Subtitles: `Turned down HKU Engineering` → `Assigned to HKU Engineering` →
`Transferred to CUHK Statistics` → `Now builds software for fun`*

## 5 · Career aspiration `1:40 – 1:55`

> From a summer internship I want **research** — to find out what my curiosity
> looks like with real money and real deadlines attached. Next to people better
> than me, giving back to the team as I learn.
>
> Which is a good moment to show you what I built.

*Cut to Part 2.*

---
---

# PART 2 · PROJECT SHOWCASE `1:55 – 6:00`

## ① WHAT I BUILT `1:55 – 2:35`  *(requirement 1)*

*Slide: title + positioning.*

> This is **SignalDesk**.
>
> It's built for someone who needs to understand a market quickly, from several
> angles at once, and doesn't have forty minutes every morning to find out what
> actually happened.
>
> It reads **twelve news feeds** — six crypto, six macro — ranks every story with
> a transparent formula, and writes a briefing that arrives in Telegram at
> **half past eight, automatically.** You don't ask for it. It shows up.
>
> Today it's a Telegram bot. Where it's going is a **free subscription service** —
> a site where anyone subscribes, picks their subjects, and gets the same
> briefing. Free, because the data layer costs nothing to run: RSS feeds, a
> public price API, a public sentiment index.

## ② HOW IT WORKS `2:35 – 3:30`  *(requirement 2)*

*Screen recording: Telegram. Show each command as you name it.*

> Three commands, and that's the whole surface.

**`/digest`**

> This is what arrives every morning on its own. A headline, one bullet per
> story, and the **ranked source list** underneath — each with the score that put
> it there.

**`/top`**

> When you don't want to wait for tomorrow, the ranking right now. Same engine,
> on demand.

**`/weights`**

> Where the reader takes control. **Five subjects** — security, regulation,
> institutional flows, macro, protocol. Switch one off and it's a hard filter,
> not a nudge.
>
> Below that, a **depth setting**: hard numbers, or analysis? Choosing one
> physically moves two weights in the formula — and the screen shows you the two
> numbers that changed.

> There's also an **alert**. The bot re-checks every fifteen minutes, and
> anything above your threshold arrives immediately. A briefing answers *what
> happened yesterday.* An alert answers *this can't wait.*

## ③ HOW AI WAS USED `3:30 – 4:50`  *(requirement 3)*

*Slide: the eight-factor table, then the system prompt.*

> Now the part I most want to explain.
>
> **The data.** Twelve RSS feeds — CoinDesk, The Block, DL News and Unchained on
> crypto; FT, Bloomberg, CNBC and the ECB press feed on macro. Prices from
> **Binance's public API**, sentiment from the **alternative.me Fear and Greed
> index.** All free, no keys.
>
> **The ranking.** Every story scores on **eight factors** — how consequential the
> subject is, how recent, how good the outlet, how many outlets corroborate it,
> how many figures it carries, how much it reads as analysis. Weighted, and
> normalised to a number between zero and one.
>
> That formula is **an algorithm, not a model.** Deterministic — same input, same
> ranking, every time — and covered by **148 offline tests.**
>
> **The language model does exactly one job: it writes up the list the algorithm
> already chose.** Here's the system prompt that enforces it — *the list is
> already ranked, selection is not your job, never invent a number.*
>
> The models are **Moonshot Kimi K3**, falling back to **xAI Grok 4.3** — two
> vendors on purpose, because two models from one provider give you a retry, not
> a fallback. And the whole thing was built with **Claude Code**.
>
> The reason for that split: if the model picks the stories and picks wrong,
> **you can't find out why.** Here, a wrong lead story means a wrong factor
> weight — something I can see, test, and fix.

## ④ ITERATIONS & REFLECTIONS `4:50 – 6:00`  *(requirement 4)*

*Screen recording: `python scripts/show_regex_bug.py`*

> **What worked:** making the score explain itself.
>
> A command called `/why` prints the arithmetic behind any ranking — every
> factor, its weight, what it contributed. It started as a nice-to-have and
> became the debugging tool. **Every real bug in this project was found by
> reading that table next to a ranking. Not one was caught by a test.**
>
> Here's the clearest. *(run the script)* A pattern looking for the word
> *exploit* could not match *exploited* — one letter of English grammar. So a
> **sixty-two-million-dollar hack** scored **zero** on the most important factor
> and ranked seventh. After the fix, top tier. Every test was green throughout.
>
> **What I'd improve:** the eight weights are **reasoned, not fitted.** I can
> defend every one of them; none of them is measured. Given more time, I'd log
> every ranking against which stories readers actually open, and fit the weights
> to that — turning eight arguments into eight numbers.
>
> Thanks for watching.

---
---

# Production notes

**Film Part 2 first**, while the bot is fresh in your head. Part 1 is easier and
you'll be warmer by then.

**Pre-record the screen segments** — don't demo live. If the bot is slow or the
news is dull that day you'd have to retake the whole section.

**Telegram: light theme, `Cmd +` to zoom** before capturing. Dark screens lose
the factor table to video compression.

**If you overrun 7:00**, cut in this order:
1. the depth-setting paragraph in ② *(~20s)*
2. the "two vendors on purpose" sentence in ③ *(~12s)*
3. the supply-chain sentence in Part 1 §2 *(~10s)*

**Subtitles** — auto-generate, then fix only the proper nouns: SignalDesk,
Kimi K3, Grok, JUPAS, CUHK, HKU, Binance, Telegram.

**The two lines to land**

1. *"The analysis isn't the slow part. Deciding what's worth reading is."*
   — Part 1. It's the bridge into the project.
2. *"Every real bug was found by reading that table next to a ranking. Not one
   was caught by a test."* — Part 2. **Pause after it.**
