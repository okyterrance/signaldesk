# PART 2 · Project Showcase — one-take screen recording

**Budget.** Part 1 ran **3:00**; the cap is **7:00**. This script measures
**521 spoken words = 3:28** at 150 wpm. Add ~18s of on-camera waiting while the
bot replies in Step 2 and it lands at **~3:46** — **total 6:46**, with 14
seconds of slack. That slack is thin: if you tend to speak slowly, take the
first cut in the delivery notes before you record, not after.

**Format.** No face. One continuous screen recording, voice over. Two windows
only:

| Window | What | When |
|---|---|---|
| **A · Browser** | `docs/onepager.html`, fullscreen (`F11` / `⌃⌘F`) | Steps 1, 3, 4 |
| **B · Telegram** | your chat with the bot, light theme, zoomed in | Step 2 |

The one-pager is built as **four panels, one screenful each** — so moving on is
one `Page Down`, never a hunt for the right scroll position.

**Before you hit record**
1. Bot running, `/digest` already sent in the chat so there's something to
   scroll back to.
2. Telegram: light theme, `⌘ +` twice. Browser: fullscreen, `⌘ 0` to reset zoom.
3. Clear the chat of failed attempts — you'll be scrolling through it live.
4. `⌘ Tab` between exactly two apps, so the switch is instant and predictable.

---

## STEP 1 · What I built `0:00 – 0:36`

*Screen: one-pager, panel 1.*

> This is **SignalDesk**.
>
> It's for someone who wants to understand a market quickly, from several
> angles they choose themselves — instead of spending forty minutes across a
> dozen news sites every morning.
>
> Right now it's a Telegram bot: twelve feeds in, one ranked briefing out,
> pushed automatically every morning.
>
> Where it's going is a **free subscription site** — you subscribe, pick your
> subjects, and the briefing comes to you. Free is the point: the entire data
> layer costs nothing to run, so the free tier *is* the growth channel.

*`Page Down` →*

---

## STEP 2 · How it works — the reader's side `0:36 – 1:41`

*Screen: one-pager, panel 2 — read the four lines off it, then `⌘ Tab` to Telegram.*

> Three commands, and that's the whole surface.

**→ Switch to Telegram. Scroll up to this morning's 08:30 digest.**

> This is `/digest` — and I didn't ask for it. It arrived on its own at half
> past eight. A headline, one bullet per story, and underneath, the **ranked
> source list** with the score that put each story there.

**→ Type `/top`, send.**

> `/top` is the same engine on demand, when you don't want to wait for
> tomorrow. Same ranking, live.

**→ Type `/weights`, send. Tap one subject off, then tap a depth button.**

> `/weights` is where the reader takes control. **Five subjects** — security,
> regulation, institutional flows, macro, protocol. Switching one off is a
> **hard filter**, not a hint.
>
> And a **depth setting**: hard numbers, or analysis. Choosing one physically
> moves two weights in the formula — and it shows you the two numbers that
> changed.

**→ `⌘ Tab` back to the browser, `Page Down`.**

---

## STEP 3 · How AI was used `1:41 – 2:48`

*Screen: one-pager, panel 3 — the factor table on the left, sources and system
prompt on the right.*

> Now the part that matters most.
>
> **The data** is twelve RSS feeds, six crypto and six macro, prices from
> **Binance's public API**, sentiment from the **Fear and Greed index.** All
> free, no keys.
>
> **The ranking** is these eight factors — how consequential the subject is,
> how recent, how good the outlet, how many outlets corroborate it, how many
> hard figures it carries. Weighted, normalised to zero-to-one.
>
> That is **an algorithm, not a model.** Same input, same ranking, every time,
> covered by **148 offline tests.**
>
> **The model does exactly one job: it writes up the list the algorithm already
> chose.** That's the system prompt on the right — *already ranked; selection
> is not your job; never invent a number.*
>
> Two models, **Kimi K3** falling back to **Grok 4.3**. Built with **Claude
> Code.**
>
> The reason for the split: if a model picks the stories and picks wrong,
> **you can't find out why.** Here, a wrong lead story is a wrong factor
> weight — something I can see, test, and fix.

*`Page Down` →*

---

## STEP 4 · Iterations & reflections `2:48 – 3:47`

*Screen: one-pager, panel 4 — the two rankings side by side.*

> **What worked** was making the score explain itself. A hidden command prints
> the arithmetic behind any ranking — every factor, its weight, what it
> contributed. It became the debugging tool: **every real bug in this project
> was found by reading that table next to a ranking. Not one was caught by a
> test.**
>
> The clearest one: a pattern looking for the word *exploit* could not match
> *exploited* — one letter of English grammar. So a
> **sixty-two-million-dollar hack** scored **zero** on the heaviest factor and
> ranked seventh, below an NFT press release. After the fix, second.
>
> *(beat)*
>
> **What I'd improve:** the eight weights are **reasoned, not fitted.** I can
> defend every one of them; none of them is measured. Given more time I'd log
> every ranking against which stories readers actually open, and fit the
> weights to that — turning eight arguments into eight numbers.
>
> Thank you for watching.

---

# Delivery notes

**Say the numbers out loud** — "sixty-two million", "one hundred and forty-eight
tests". Read aloud they land; skimmed off a slide they don't.

**Pause after** *"Not one was caught by a test."* It's the strongest sentence in
the submission. Give it a full beat before moving on.

**Don't hedge the limitation** in Step 4. Stated plainly it reads as engineering
judgement; apologised for, it reads as doubt.

**If a command is slow on camera**, keep talking — the next sentence is always
safe to say while the reply lands. Don't narrate the waiting.

**If you overrun 7:00**, cut in this order:
1. the depth-setting paragraph in Step 2 *(~18s)*
2. "Two models… cross-vendor on purpose" in Step 3 *(~10s)*
3. "below an NFT press release" in Step 4 *(~3s)*

**One-take insurance:** record Steps 1–2 and Steps 3–4 as two takes if the
single pass keeps breaking. A cut at the `Page Down` between panel 2 and panel 3
is invisible — same window, same zoom.
