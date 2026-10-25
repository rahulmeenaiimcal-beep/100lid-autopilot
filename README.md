# 100LID Autopilot 🎬

A free robot that makes **animated Hindi exam-prep explainer videos** for the
**100LID - EDUCATION** YouTube channel, and uploads them for your approval.

## What it does, in plain words

Every hour it checks: *"Is a video due in the next 2 days?"* If yes, it:

1. **Picks a topic** from the topic bank (government schemes, banking laws, RBI & economy), keeping the monthly mix and never repeating a topic within 6 months.
2. **Researches it** from official websites and Wikipedia.
3. **Writes a story-led script** with the free Gemini AI: a hook, chapters, an Exam Corner, a 5-question quiz, a recap, and 3 Shorts.
4. **Has a second, separate AI fact-check** every statement against the research and fix mistakes.
5. **Records the Hindi voices** (each character has their own voice).
6. **Animates everything** with Remotion: 6 recurring cartoon characters, 7 backgrounds, and eye-catching moments (exploded view, knolling, cutaway, anatomy dissection, stats, timelines, comparisons, steps). These are placed where viewers usually drift away (around 25%, 50% and 70% of the video).
7. **Adds original background music** (made by code, so there are never copyright claims), sound effects, Hindi + English subtitles, chapters, a click-worthy thumbnail, an SEO title, a description and tags.
8. **Uploads it as PRIVATE** and **emails you** (through a GitHub issue). Reply **ok**, **now** or **no**.
9. **Learns** from YouTube's numbers every day, and sends you a plain-language **report every 3 days**.
10. **Around the 20th of each month** it emails you next month's topics with a 1-minute tip script for each, for **you** to record. Your clips go into their own videos automatically (see `docs/RECORDING.md`).

**Schedule:** 3 long videos a week (Tue & Thu 6 pm, Sat 11 am) + 1 Short every day at 8 pm, India time.

**Cost:** ₹0. The repository is public, so GitHub's machines are free and unlimited, and every service used has a free tier. Your passwords and keys stay secret, because GitHub never shows them.

## Your everyday jobs
- **Review videos:** when an email "Review: …" arrives, open the private link, watch it, and reply **ok** (schedule it), **now** (publish now) or **no** (keep it private).
- **Read the 3-day report** email.
- That's it.

## Changing things
Everything you'd normally change is in **`config.yaml`** (pencil icon → edit → Commit): times, review mode, characters, voices, video length.
Topics are in **`topics/bank.yaml`**.

## Files
| File | What it is |
|---|---|
| `config.yaml` | All settings |
| `topics/bank.yaml` | The list of topics |
| `docs/SETUP.md` | One-time setup guide |
| `docs/STRATEGY.md` | The month-1 plan and what to check after a month |
| `docs/RECORDING.md` | How to record and upload your own clips |
| `robot/` | The robot's Python code |
| `video/` | The animation project (Remotion) |
| `samples/ssy_episode.json` | A hand-written example episode (the style guide for the AI) |
| `data/` | The robot's memory: what was posted and how it performed |
