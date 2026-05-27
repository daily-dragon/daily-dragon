# Daily Dragon — Feature Ideas

> **Date:** 2026-05-27  
> **Scope:** All three sub-repos  
> **Status:** Backlog candidates — not committed to any sprint

---

## Table of Contents

1. [Philosophy Anchors](#1-philosophy-anchors)
2. [Features by Category](#2-features-by-category)
   - [A. Practice Modes](#a-practice-modes)
   - [B. Sentence & Content Quality](#b-sentence--content-quality)
   - [C. In-Session Learning Support](#c-in-session-learning-support)
   - [D. Progress & Motivation](#d-progress--motivation)
   - [E. Platform & Reach](#e-platform--reach)
3. [Prioritised Backlog](#3-prioritised-backlog)

---

## 1. Philosophy Anchors

Every feature idea below is measured against these principles before being considered worth building:

| Principle | What it means in practice |
|---|---|
| **Active production** | The user produces language (writes Chinese), not just recognises it. Features that are purely passive (tapping flashcards) are weaker candidates. |
| **AI-generated, always fresh** | Content should never feel like a fixed deck. The LLM generates unpredictable sentences contextualised to the user's current vocabulary and level. |
| **SRS-driven curriculum** | Word exposure and review frequency is controlled by SM-2. Features should feed into the SRS, not bypass it. |
| **HSK-structured progression** | Vocabulary is anchored to the New HSK standard. Difficulty is level-aware, not user-tuned. |
| **Zero friction** | No manual curation, no decision fatigue. The system should do the right thing by default. |

Features are tagged with their primary alignment:

- `[production]` — directly exercises translating into Chinese  
- `[srs]` — feeds data into or benefits from the spaced-repetition schedule  
- `[ai]` — leverages the LLM for fresh, contextual content  
- `[motivation]` — keeps the user coming back  
- `[accessibility]` — lowers the barrier for different learner types  

---

## 2. Features by Category

---

### A. Practice Modes

---

#### A-1 · Study / Warm-up Mode `[production]` `[srs]`

> _The one the user specifically called out._

**What it is:** A dedicated "study" step before the translation practice. The user sees each due word one at a time: the Chinese character, its pinyin (already available from `target_word_pinyin` in evaluation responses), its English meaning, and a short AI-generated example sentence. After reviewing all due words the user enters the normal translation practice with the same words.

**Why it fits:** The current flow throws the user straight into translation with no warm-up — hard for genuinely new words (interval = 0). A study step bridges the gap between "just seeded" and "being tested". It does not replace the translation test; it precedes it.

**How it works end-to-end:**
1. Before calling `POST /practice/sentences`, show a study carousel for each word in `due_words`.
2. Each card shows: hanzi (large), pinyin, English meaning (new backend call), one short example sentence (reuse existing LLM call or pre-fetch).
3. User taps "Got it" / "Skip" — skipped words are surfaced first in the practice order.
4. After all cards, proceed to normal translation practice.

**New backend needed:**
- `GET /daily-dragon/vocabulary/word-detail?word=X` — returns pinyin + English meaning for a single word. Meaning can be looked up via OpenAI (single call: "give me the English meaning of 学习 in one short phrase") or a dictionary JSON bundled with the HSK data.
- Alternatively, batch: include `meanings` in the `GET /vocabulary/due` response by enriching at query time.

**Complexity:** Medium. The UI carousel is self-contained. The main cost is the new dictionary lookup — which if done via OpenAI adds latency and cost. Better approach: bundle a small CC-CEDICT-derived JSON for the ~11,000 HSK words into the Lambda layer at build time (one-time cost, static data, ~5 MB).

**Dependencies:** None. Can be built in isolation and toggled via a settings flag.

---

#### A-2 · Cloze (Fill-in-the-blank) Practice `[production]` `[ai]`

**What it is:** An alternative to full-sentence translation. The AI generates a Chinese sentence with the due word replaced by a blank (`___`). The user fills in the missing word. Exercises recall in context without requiring full sentence production.

**Example:**  
Prompt: `我每天早上都___新的汉字。` → User types `学习`

**Why it fits:** Cloze is active production (the user must recall the correct word) but at lower cognitive load than composing an entire sentence. It is a natural intermediate step for new or low-interval words before they appear in full translation sessions. SRS quality can be derived from whether the user filled it in correctly on the first attempt.

**How it works:**
1. New prompt instruction: "Generate a Chinese sentence using `{word}`. Replace `{word}` with `___` in the sentence and return the full sentence with the blank."
2. New response schema: `ClozeItem { sentence_with_blank: str, answer: str, sentence_full: str }`
3. UI renders a text input in place of the blank; evaluates locally (exact match or AI-evaluated for near-matches).
4. Score maps to SRS quality: correct first try → quality 5, hint used → quality 3, revealed → quality 1.

**New backend needed:** New endpoint or a `mode: "cloze"` parameter on `POST /practice/sentences`. New Pydantic model. New prompt file.

**Complexity:** Medium. Logic is self-contained; no new external services. The main design question is where cloze sessions are triggered vs full translation sessions — suggesting: new words (interval 0–1) get cloze, mature words (interval ≥ 6) get full translation.

---

#### A-3 · Listening Comprehension Mode `[production]` `[accessibility]`

**What it is:** The user *hears* the English sentence spoken aloud and must produce the Chinese translation without ever seeing the English text. Exercises the ear-to-production pathway alongside the reading-to-production pathway already covered.

**Why it fits:** Real Chinese use involves listening as much as reading. The app already generates English sentences; adding audio is a thin layer on top. This is still active production — the user still writes Chinese.

**How it works:**
1. Use the browser's built-in `window.speechSynthesis` API to speak the English sentence aloud (zero backend cost, zero latency).
2. The sentence text is hidden; a "play" button replays it up to 3 times.
3. User types the Chinese translation as normal; evaluation is identical to the existing flow.
4. A settings toggle enables/disables this mode.

**New backend needed:** None. `speechSynthesis` is a browser API. Optional: a "replay count" limit enforced client-side.

**Complexity:** Low. Purely a UI addition on top of the existing practice flow. `window.speechSynthesis.speak(new SpeechSynthesisUtterance(sentence))` is three lines of code.

---

#### A-4 · Multiple Attempts with Progressive Hints `[production]` `[srs]`

**What it is:** Instead of a single translation attempt, the user gets up to three tries per sentence. Each failed attempt (score < 5) reveals a progressively bigger hint:
- Attempt 1: no hint
- Attempt 2: pinyin of the target word is revealed
- Attempt 3: the correct Chinese sentence is shown; user copies it as a final attempt

SRS quality is reduced for each hint used: attempt 1 success → full quality score, attempt 2 → quality capped at 3, attempt 3 → quality 1.

**Why it fits:** Reduces frustration for new words while still requiring active production. Graduated hints are a proven pedagogical pattern (scaffolded learning). The SRS still records reduced quality, ensuring the word resurfaces sooner.

**How it works:**
- Client-side only: a `attempts` counter per sentence.
- On score < 5, show "Try again?" with the appropriate hint.
- On final attempt, evaluate normally; pass the lowest quality to the reviews endpoint.
- No backend change required — only the quality values sent to `POST /vocabulary/reviews` change.

**New backend needed:** None. Purely client-side logic.

**Complexity:** Low. Self-contained UI state per sentence card.

---

#### A-5 · Speaking Practice Mode `[production]` `[accessibility]`

**What it is:** Instead of typing the Chinese translation, the user speaks it. The browser's `SpeechRecognition` API (with `lang: "zh-CN"`) transcribes the speech to text, which is then sent to the evaluation endpoint as normal.

**Why it fits:** Speaking is active production — arguably the most active. Users who are learning Chinese for oral communication benefit directly. The evaluation pipeline is identical; only the input method changes.

**How it works:**
1. On "Start Recording" tap, use `window.SpeechRecognition` with `lang: "zh-CN"`.
2. Transcribed text fills the input field; user can edit before submitting.
3. Falls back to keyboard input if the browser doesn't support `SpeechRecognition` or the user is on a noisy environment.
4. A settings toggle enables/disables this mode.

**New backend needed:** None.

**Complexity:** Low-Medium. `SpeechRecognition` is well-supported on Chrome/Android; iOS Safari has limitations. Graceful fallback to text input is required.

---

### B. Sentence & Content Quality

---

#### B-1 · Adaptive Sentence Difficulty `[ai]` `[srs]`

**What it is:** The difficulty of generated sentences scales within the user's HSK level based on their recent performance. After a session with average score ≥ 8, the next session asks the AI for longer, more complex sentences. After a session with average score ≤ 5, it asks for simpler, shorter ones.

**Why it fits:** Currently the AI receives `hsk_level` as the only complexity signal. Within level 2, for example, sentences could range from 6 to 15 words with varying grammar complexity. Adapting this dynamically makes each session appropriately challenging — the core premise of effective SRS.

**How it works:**
1. Store `session_difficulty: 1–5` in user settings (default: 3).
2. After each session, adjust: `+1` if avg score ≥ 8, `-1` if avg score ≤ 5, no change otherwise.
3. Pass `session_difficulty` to `POST /practice/sentences`.
4. The prompt gains a difficulty qualifier: "Use [simple 6–8 word / moderate 8–12 word / complex 12–18 word] sentences."

**New backend needed:**
- Add `session_difficulty: int` (1–5) to settings schema.
- Update `POST /practice/sentences` request to accept `difficulty: int | None`.
- Update prompt template.

**Complexity:** Low. A single new field, a small prompt addition, and post-session update logic in the reviews endpoint.

---

#### B-2 · Themed Sessions `[ai]`

**What it is:** Sentences in a single practice session share a topic theme (food, travel, work, family, etc.). All sentences use due words but the AI is told to situate them within a consistent context — making the session feel like a coherent micro-story rather than disconnected sentences.

**Example session theme: "At a restaurant"** → sentences reference ordering food, paying, asking for the menu — even though the due words might be 学习, 时间, 朋友.

**Why it fits:** Contextual clustering is a well-established memory technique (episodic encoding). The app's AI-generated content already enables this — it is a prompt change, not an architecture change. Themes can be HSK-level-appropriate (HSK 1 themes: home/school/greetings; HSK 4 themes: business/travel/news).

**How it works:**
1. Backend maintains a list of themes per HSK level (static dict or S3 JSON).
2. On each session, randomly select a theme for the current level.
3. Append to prompt: "Set all sentences within the theme of: `{theme}`. The sentences should feel connected."
4. Theme name is shown to the user at the top of the practice screen.

**New backend needed:**
- Static theme list per HSK level (data file, no endpoint needed).
- Optional `theme` field in sentence generation response so the UI can display it.

**Complexity:** Low. Mostly a prompt change and a small data file.

---

#### B-3 · Grammar Focus Mode `[ai]` `[production]`

**What it is:** Occasionally (e.g., every 5th session), instead of unconstrained sentences, the AI generates sentences that all demonstrate a specific grammar pattern common at the user's HSK level. The user still translates them, but the session is thematically a grammar drill.

**Example HSK 2 grammar focus:** 的 adjective modifier → all sentences use `的` to describe something.  
**Example HSK 3:** 把 sentence structure → all sentences require the `把` construction.  
**Example HSK 4:** Complement of result → sentences require `verb + 得 + result`.

**Why it fits:** Grammar is the invisible scaffolding around vocabulary. The HSK standard specifies which grammar points are expected at each level — this feature makes those points explicit and practised. The user still produces full sentences; the focus just gives coherence to the session's difficulty.

**How it works:**
1. Backend maintains a `grammar_points` list per HSK level (static data, based on official HSK syllabus).
2. `POST /practice/sentences` accepts an optional `grammar_focus: str`.
3. The prompt appends: "All sentences must require the use of: `{grammar_point}`. Briefly note in the sentence text (in parentheses) the grammar pattern being practised."
4. Session selection: a backend counter (`grammar_session_count`) determines when to trigger a grammar session (e.g., every 5th session).

**New backend needed:**
- Grammar point data per level (static JSON).
- `grammar_focus` field on sentence generation request.
- Session counter in user settings or derived from review history.

**Complexity:** Medium. Data preparation (curating grammar points per level) is the main effort. Code change is small.

---

#### B-4 · Sentence Difficulty Rating Feedback `[ai]` `[srs]`

**What it is:** After each session, the user rates whether the sentences felt too easy / about right / too hard with a single tap. This feedback is stored and fed back into adaptive difficulty (B-1) and potentially surfaced to improve the prompt.

**Why it fits:** Human perception of difficulty is the most direct signal the system can collect. Combining this with score-based difficulty (B-1) makes the adaptation more accurate.

**How it works:** A three-button widget on the ReviewPage: "Too easy" / "Just right" / "Too hard". The rating is stored as part of the session record (or as `difficulty_feedback` in user settings). No new endpoint required if piggy-backed onto the existing `PATCH /settings`.

**Complexity:** Low. Mostly UI.

---

### C. In-Session Learning Support

---

#### C-1 · Inline Word Lookup `[accessibility]`

**What it is:** During practice, the user can tap the teal-highlighted target word in any sentence to see a popover with its pinyin, English meaning, and HSK level — without leaving the practice flow or disrupting the session.

**Why it fits:** Reduces the urge to open a dictionary app and break focus. The meaning is already available from the evaluation response (`target_word_pinyin`); the English meaning is the missing piece. Kept strictly optional so it does not become a crutch.

**How it works:**
1. The teal word in each sentence card is made tappable (currently just styled text via `renderSentence`).
2. On tap, a Chakra `Popover` shows: hanzi (large), pinyin, English meaning, HSK level.
3. English meaning is either pre-fetched via the new word-detail endpoint (see A-1) or looked up on demand.
4. A small "ℹ️ lookup used" note is added to the session log (optional — to eventually inform adaptive difficulty).

**New backend needed:** Same word-detail endpoint as A-1 (`GET /vocabulary/word-detail?word=X`). If A-1 is built first, this is a pure UI addition.

**Complexity:** Low. The popover is a standard Chakra component; the data source is shared with A-1.

---

#### C-2 · AI-Generated Mnemonics for Struggling Words `[ai]` `[srs]`

**What it is:** For words the user has reviewed three or more times with an average score below 5, the app automatically generates a mnemonic — a short memorable story, a visual description, or a character component breakdown — and shows it in the ReviewPage card for that word.

**Example:** 忘 (wàng, to forget) → "The heart (心) under a dead branch (亡) — the memory died."

**Why it fits:** Mnemonics are most valuable for words that SM-2 has already identified as troublesome (low ease factor, short interval). Generating them automatically and just-in-time is exactly the kind of zero-friction intelligent assist the app should provide.

**How it works:**
1. Backend identifies "struggling words" from vocabulary metadata: `repetition >= 3 AND ease_factor < 2.0`.
2. For those words, `POST /practice/evaluate-translations` response includes an extra `mnemonic: str | null` field.
3. The mnemonic is generated as part of the evaluation prompt: "For words with ease_factor < 2.0, also provide a short memorable mnemonic (one sentence, focus on the character shape or sound)."
4. The ReviewPage card shows the mnemonic in a distinct block below the feedback.

**New backend needed:**
- Pass `ease_factor` context to the evaluation prompt for flagged words.
- Add `mnemonic: str | null` to `TranslationEvaluationItem` response model.
- Update evaluation prompt.

**Complexity:** Low-Medium. The main change is to the evaluation prompt and response schema. No new endpoints.

---

#### C-3 · Post-Session Replay `[srs]`

**What it is:** After completing a practice session, the user can optionally enter a "replay" mode that shows each sentence again — Chinese due word, the English sentence, the correct Chinese translation, the user's attempt, and the AI's feedback — as a read-through review without re-submitting to SRS. Useful for learning from mistakes without inflating the review count.

**Why it fits:** The current ReviewPage is card-heavy but read-once. A linear replay that can be scrolled at leisure (perhaps with a "copy correct sentence" button) reinforces the session's content without requiring re-evaluation.

**How it works:** Pure client-side. The `review` data passed to `ReviewPage` already contains everything needed. A "Replay session" button renders a scrollable read-only transcript. No new API calls.

**New backend needed:** None.

**Complexity:** Low. Pure UI; uses data already in component state.

---

#### C-4 · Correct Sentence Handwriting Trace `[production]` `[accessibility]`

**What it is:** For sentences where score ≤ 5, after viewing the correct sentence, the user can optionally trace the correct Chinese characters using a finger or stylus. A simple canvas element shows a ghost of the correct character; the user draws over it.

**Why it fits:** Motor memory (writing) is a distinct and powerful memory pathway. This is especially useful for users preparing for the actual HSK exam which requires handwriting. Strictly optional (button in the review card).

**New backend needed:** None. Stroke-order data for ~500 most common characters can be bundled as a static JSON (the `hanzi-writer` library contains this data and is MIT-licensed).

**Complexity:** Medium. The `hanzi-writer` JavaScript library handles stroke rendering and animation. The canvas integration requires care on mobile. High payoff for serious learners.

---

### D. Progress & Motivation

---

#### D-1 · Daily Streak & Practice Goal `[motivation]`

**What it is:** A visible streak counter (🔥 N days) on the Home page and Header. The streak increments when the user completes at least one practice session per day. An optional daily goal ("complete X sessions") can be set. Missing a day resets the streak.

**Why it fits:** Streaks are among the most effective app retention mechanics in language-learning (Duolingo's core loop). The cost is minimal; the motivational effect is disproportionate.

**How it works:**
1. Add `streak: int` and `last_practice_date: int (unix date)` to user settings.
2. `POST /vocabulary/reviews` checks `last_practice_date`; if today > last_practice_date + 1, reset streak to 0; if today > last_practice_date, increment streak; save.
3. `GET /settings` response now includes `streak`.
4. Home page and Header display the streak badge.

**New backend needed:**
- Two new fields in `settings.json`.
- Streak update logic in `record_reviews` (a few lines).
- `streak` included in `GET /settings` response.

**Complexity:** Low. Most of the logic is in the reviews endpoint. The UI is a badge.

---

#### D-2 · Enhanced Progress Dashboard `[srs]` `[motivation]`

**What it is:** Extend the existing `/progress` page with richer statistics beyond per-level word counts:

- **Upcoming review forecast:** how many words are due in the next 7 days (calculated from `next_review_date` across the vocabulary file)
- **Score trend:** average score per session over the last 10 sessions (requires session history)
- **Weakest words:** top 5 words with the lowest `ease_factor` — with their pinyin
- **SRS distribution:** a bar chart showing how many words are at each interval bracket (new, 1–3 days, 4–7 days, 8–21 days, mature 21+ days)

**Why it fits:** The ProgressPage currently shows mastered/in-progress/new per level — useful but static. The dashboard data is all derivable from the existing vocabulary JSON; no new storage is needed for most of these. Learners who can see their own data are more motivated.

**How it works:**
- Most calculations are done in a new or extended `GET /hsk/progress` response.
- Session history (for score trend) requires a new lightweight store: append a `{ date, avg_score }` entry per session to a `{user_id}_sessions.json` file. Max 30 entries (rolling window).
- All new UI is on the existing `/progress` route.

**New backend needed:**
- Extended `GET /hsk/progress` response with `upcoming_due_forecast`, `weakest_words`, `srs_distribution` fields.
- New `{user_id}_sessions.json` file written to at review submission.

**Complexity:** Medium. The forecast and SRS distribution are pure in-memory calculations on the vocabulary dict. The score trend requires session history storage.

---

#### D-3 · Session History & Weekly Summary `[motivation]` `[srs]`

**What it is:** A simple history view showing past sessions: date, words practised, average score, level at time of session. On the home page or via a "This week" card, show a weekly summary: total sessions, total words reviewed, average score, streak.

**Why it fits:** Seeing progress over time (not just instantaneous progress) is motivating. It answers the question "am I actually improving?" with data.

**How it works:**
- Uses the `{user_id}_sessions.json` introduced in D-2.
- New endpoint `GET /daily-dragon/sessions` returns the last 30 session records.
- A `/history` route or modal in the app renders the list.

**New backend needed:** Session storage (shared with D-2), one new endpoint.

**Complexity:** Low-Medium.

---

#### D-4 · HSK Level Unlock Celebration `[motivation]`

**What it is:** When a user is promoted to a new HSK level (triggered by `check_and_promote` returning `True`), the next time they load the app, they are shown a brief celebration screen: "You've reached HSK Level X! Your first new words are ready." with a visual flourish.

**Why it fits:** Level promotion is the core milestone of the app's progression system. It should feel like an event, not a silent background update. Currently the user has no idea it happened until they notice the header badge changed.

**How it works:**
1. When `check_and_promote` promotes the user, set a `pending_level_celebration: int` field in settings.
2. On `GET /settings`, if `pending_level_celebration` is set, include it in the response and clear it.
3. `App.jsx` checks on load: if `pending_level_celebration` is present, navigate to a celebration screen before the home page.

**New backend needed:** One new settings field; clear-on-read logic in `GET /settings`.

**Complexity:** Low. The main work is the celebratory UI component.

---

#### D-5 · Placement Test (Phase 3) `[srs]`

> _Already planned in the HSK progression plan (Phase 3). Listed here for completeness._

**What it is:** A first-login placement test that samples words from each HSK level (5 words × 9 levels = 45 cards). For each word the user taps "Know it" / "Don't know it". The highest level where ≥70% are known becomes the starting level. Skippable (defaults to HSK 1).

**New backend needed:** `GET /placement/words`, `POST /placement/submit` (see Phase 3 in hsk-progression-plan.md).

**Complexity:** Medium. Already fully specced.

---

### E. Platform & Reach

---

#### E-1 · Vocabulary Enrichment Export `[accessibility]`

**What it is:** Export the user's current HSK level words (or due words) as a structured file: CSV with hanzi/pinyin/meaning/interval, or an Anki-compatible `.apkg` deck. Useful for users who want to study outside the app, use a different SRS tool in parallel, or share their wordlist.

**Why it fits:** The app is the primary learning environment but should not be a walled garden. Users who use Anki for reading vocabulary and Daily Dragon for production practice benefit from synergy.

**New backend needed:** `GET /daily-dragon/vocabulary/export?format=csv|anki` — generates a file download.

**Complexity:** Medium. CSV is trivial. Anki `.apkg` requires a SQLite builder (the `genanki` Python library); the Anki format is well-documented.

---

#### E-2 · PWA / Offline Practice `[accessibility]`

**What it is:** Service worker + manifest to make the app installable as a Progressive Web App. Pre-fetch the current session's sentences so the translation practice works offline (on a plane, in the subway). Reviews are queued and submitted when connectivity returns.

**Why it fits:** Language practice happens in stolen moments — commutes, queues, travel. Requiring an internet connection for practice limits those moments.

**New backend needed:** None. All offline behaviour is client-side (service worker, IndexedDB queue).

**Complexity:** High. PWA with offline queue is non-trivial. Vite has PWA plugins (`vite-plugin-pwa`) that reduce the boilerplate, but the offline review queue and conflict resolution require careful design.

---

#### E-3 · Shareable Session Card `[motivation]`

**What it is:** After a high-scoring session (average ≥ 8), the app offers to generate a shareable image card: "I just scored 9/10 on HSK Level 2 Chinese in Daily Dragon." Suitable for social media or messaging. Generated client-side via `html2canvas`.

**Why it fits:** Social proof and sharing is a lightweight viral mechanism. It is opt-in and only triggered on good sessions — it celebrates the user's achievement rather than spamming.

**New backend needed:** None. `html2canvas` captures the ReviewPage summary div as a PNG.

**Complexity:** Low.

---

#### E-4 · Notification / Reminder `[motivation]`

**What it is:** Browser push notification (or email) when the user has words due for review and has not practiced in more than 24 hours. "You have 5 words due — 5 minutes is all it takes."

**Why it fits:** SRS only works if the user reviews on schedule. Missing a review is the most common failure mode. Reminders directly protect the SRS integrity.

**New backend needed:**
- `POST /daily-dragon/push-subscription` to store browser push endpoint.
- A scheduled Lambda (EventBridge cron, daily) that checks each user's due-word count and sends a push via Web Push API if count > 0 and last practice > 24 h ago.

**Complexity:** Medium-High. Web Push requires VAPID keys, a service worker, and a scheduled Lambda. The browser permission UX is delicate (prompt too early = denied).

---

## 3. Prioritised Backlog

Features are ordered by **philosophy fit × user value × implementation cost** — not just size. Low-complexity high-fit items come first.

### Tier 1 — Build these next

| # | Feature | Complexity | Key dependency | Primary benefit |
|---|---|---|---|---|
| 1 | **A-4 · Multiple Attempts with Hints** | Low | Nothing | Reduces frustration for new words; no backend change |
| 2 | **D-1 · Daily Streak & Practice Goal** | Low | Nothing | Retention; tiny backend addition |
| 3 | **A-3 · Listening Practice Mode** | Low | Nothing | New modality; 3 lines of JS |
| 4 | **D-4 · HSK Level Unlock Celebration** | Low | Phase 3 settings field | Turns silent promotion into a milestone |
| 5 | **B-4 · Sentence Difficulty Rating** | Low | Nothing | User signal for adaptive difficulty |
| 6 | **C-3 · Post-Session Replay** | Low | Nothing | Reinforces session learning; pure UI |
| 7 | **A-1 · Study / Warm-up Mode** | Medium | Word detail data source | Core learning loop improvement (user requested) |
| 8 | **B-1 · Adaptive Sentence Difficulty** | Low | B-4 (rating) or score history | Keeps sessions calibrated to the user |

### Tier 2 — Build after Tier 1

| # | Feature | Complexity | Key dependency | Primary benefit |
|---|---|---|---|---|
| 9 | **D-5 · Placement Test** | Medium | Phase 3 backend | Correct starting level for new users |
| 10 | **C-1 · Inline Word Lookup** | Low | A-1 word detail endpoint | Reduces mid-practice friction |
| 11 | **D-2 · Enhanced Progress Dashboard** | Medium | Session history store | Deeper progress visibility |
| 12 | **C-2 · Mnemonics for Struggling Words** | Low-Med | Nothing | Targeted help for low ease-factor words |
| 13 | **B-2 · Themed Sessions** | Low | Theme data file | More cohesive, memorable sessions |
| 14 | **A-2 · Cloze Practice** | Medium | Nothing | Alternative exercise type for new words |
| 15 | **D-3 · Session History** | Low-Med | D-2 session store | "Am I improving?" answered with data |

### Tier 3 — Consider later

| # | Feature | Complexity | Notes |
|---|---|---|---|
| 16 | **B-3 · Grammar Focus Mode** | Medium | Needs curated grammar point data per level |
| 17 | **A-5 · Speaking Practice** | Med | Browser SpeechRecognition limitations on iOS |
| 18 | **E-3 · Shareable Session Card** | Low | Nice-to-have; low strategic value |
| 19 | **E-1 · Export to CSV/Anki** | Medium | Useful for power users |
| 20 | **C-4 · Character Handwriting Trace** | Medium | High value for exam-focused learners; `hanzi-writer` library handles the hard part |
| 21 | **E-4 · Push Notifications** | Med-High | Significant infra; browser permission UX is tricky |
| 22 | **E-2 · PWA / Offline Practice** | High | High value, high effort; justified once core loop is stable |
