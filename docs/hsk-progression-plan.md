# HSK Progression & Automatic Advancement — Migration Plan

> **Status:** Planned  
> **Scope:** `daily-dragon-vocabulary-api`, `daily-dragon-openai-api`, `daily-dragon-ui`  
> **Replaces:** Manual vocabulary management (add word / remove word)

---

## Table of Contents

1. [Vision](#1-vision)
2. [Core Principles](#2-core-principles)
3. [What Changes](#3-what-changes)
4. [Key Design Decisions](#4-key-design-decisions)
5. [Migration Phases](#5-migration-phases)
   - [Phase 0 — HSK Data Preparation](#phase-0--hsk-data-preparation)
   - [Phase 1 — User Settings](#phase-1--user-settings)
   - [Phase 2 — HSK Seeding & Progression Logic](#phase-2--hsk-seeding--progression-logic)
   - [Phase 3 — Placement Test](#phase-3--placement-test)
   - [Phase 4 — Sentence Generation Update](#phase-4--sentence-generation-update)
   - [Phase 5 — UI Overhaul](#phase-5--ui-overhaul)
   - [Phase 6 — Cleanup & Testing](#phase-6--cleanup--testing)
6. [Timeline Estimate](#6-timeline-estimate)
7. [Affected Repositories](#7-affected-repositories)

---

## 1. Vision

Daily Dragon currently asks users to build and manage their vocabulary list manually. This friction is replaced with a **structured, automatic curriculum** based on the **New HSK standard (2021, levels 1-9)**.

The core learning loop becomes:

> The system seeds words from the user's current HSK level → the LLM generates fresh, unpredictable sentences using those words at the right complexity  → the user practises translation → SRS schedules reviews → when enough words are mastered, the next level is unlocked automatically.

No manual curation. No decision fatigue. Just daily practice.

---

## 2. Core Principles

### Curriculum-anchored vocabulary
All words come from the **New HSK word lists** (levels 1-9, ~11,000 words total). This provides a clear, proven learning path aligned with internationally recognised proficiency standards.

### One unified vocabulary list per user
There is no separation between "current level words" and "old level words". A user has a single flat vocabulary file. When a new level is unlocked, its words are **merged into the same list**.k
Spaced repetition naturally keeps older words in rotation — they resurface as mature cards every few weeks without any special recapitulation mode.

### Gradual word introduction
New words are **seeded in small batches** (default: 20 words at a time), not all at once. This prevents overwhelm and ensures each new word gets adequate attention before the next batch arrives.

### Automatic level progression
The system tracks mastery per word using the existing SM-2 SRS fields. When **>=80%tof the current HSK level's words are mastered**, the next level is unlocked automatically and the first batch is seeded. The user does not need to manually request advancement.

### Level-aware sentence generation
Every sentence generation request includes the user's current HSK level. The LLM is instructed to keep surrounding vocabulary and grammar complexity appropriate for that level — ensuring the sentences are challenging but comprehensible.

### Mastery defined by SRSinterval
A word is considered **mastered** when its SRS `interval` reaches **>=21 days** (a mature card in SM-2 terms). This reflects genuine long-term retention, not a single correct answer.

### Placement test for new users
tNew users are shown a quick binary placement test (know it / don't know it) across a sample of words from each HSK level. This sets their starting level correctly and avoids wasting time on material they already know.

### HSK data is shared and static
HSK word lists are stored as **9 separate read-only JSON files in S3** (`hsk-data/hsk1.json` ... `hsk-data/hsk9.json`), shared across all users. They are never modified at runtime.

### User settings stored like vocabulary
User-level preferences (current HSK level, placement test status) are stored in a per-user settings JSON file in S3 — following the same pattern already used for vocabulary files.

### Manual vocabulary management retired
The add word / remove word workflow is fully removed. The vocabulary page is replaced by a **Progress page** that shows word mastery per HSK level.

---

## 3. What Changes

### Removed

| Component | Location |
|---|---|
| `POST /daily-dragon/vocabulary` -- add word | `vocabulary-api` |
| `DEMETE /daily-dragon/vocabulary/{word}` -- remove word | `vocabulary-api` |
| `VocabularyPage` | `daily-dragon-ui` |
| `AddWordDialog` | `daily-dragon-ui` |
| `RemoveWordDialog` | `daily-dragon-ui` |
| `VocabularyList` | `daily-dragon-ui` |
| Vocabulary nav link | `daily-dragon-ui` |

### Added

| Component | Location |
|---|---|
| `GET/PATCH /daily-dragon/settings` | `vocabulary-api` |
| `GET /daily-dragon/hsk/progress` | `vocabulary-api` |
| `GET /daily-dragon/placement/words` | `vocabulary-api` |
| `POST /daily-dragon/placement/submit` | `vocabulary-api` |
| HSK seeding & progression service | `vocabulary-api` |
| `hsk_level` + `source` fields on word entries | vocabulary S3 files |
| `{user_id}_settings.json` in S3 | S3 vocabulary bucket |
| Static `hsk-data/hsk1.json` ... `hsk9.json` in S3 | S3 (shared, read-only) |
| `hsk_level` field in sentence generation request | `openai-api` |
| `ProgressPage` | `daily-dragon-ui` |
| `PlacementTestPage` | `daily-dragon-ui` |
| First-login placement guard | `daily-dragon-ui` |

### Updated

| Component | Change | Location |
|---|---|---|
| Word entry schema | Add `hsk_level` (int) and `source` ("hsk") fields | vocabulary S3 files |
| `POST /practice/sentences` request | Add optional `hsk_level` field | `openai-api` |
| Sentence generation prompt | Inject `${hskLevel}` into prompt template | `openai-api` |
| `PracticePage` | Fetch settings; pass `hsk_level` to sentence request | `daily-dragon-ui` |
| `Header` nav | "Vocabulary" --> "Progress" | `daily-dragon-ui` |
| `/vocabulary` route | Redirect to `/progress` | `daily-dragon-ui` |
| Review submission handler | Trigger `check_and_promote` after each batch | `vocabulary-api` |

---

## 4. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| HSK standard | New HSK (2021), levels 1-9 | Future-proof; more granular than old 1-6 |
| HSK storage | 9 separate S3 JSON files under `hsk-data/` | Independent versioning per level; lazy loading; mirrors existing patterns |
| User vocabulary | Same JSON structure + `hsk_level` + `source` fields | Zero-migration risk; existing SRS fields untouched |
| User settings | `{user_id}_settings.json` in same S3 bucket | Consistent with vocabulary storage pattern |
| Mastery threshold | `interval >= 21 days` | SM-27 definition of a mature card; proven long-term retention signal |
| Level promotion trigger | >=80} of current level words mastered | Allows progression without 100% perfection; avoids stalling |
| New word batch size | 20 words per seeding call | Prevents overwhelm; keeps daily session size manageable |
| Manual vocabulary | Fully removed | Removes friction and maintenance surface; HSK covers all needed vocabulary |
| Progress visibility | Dedicated `/progress` page showing mastery per HSK level | Replaces the removed vocabulary management page |
| Placement test | Required on first login; skippable --> defaults to HSK 1 | Respects existing knowledge without blocking new users |

---

## 5. Migration Phases

---

### Phase 0 -- HSK Data Preparation
> **~1-2 days | No code changes to any service**

- Source the New HSK (2021) word lists for all 9 levels
- Each entry format: `{ "hanzi": "你好", "pinyin": "ni\u01d0 h\u01ceo", "meaning": "hello", "hsk_level": 1 }`
- Format as 9 JSON files: `hsk1.json` through `hsk9.json`
- Upload to S3 under shared `hsk-data/` prefix (not user-scoped, never modified at runtime)
- These files become the ground truth the backend seeds from

**Done when:** All 9 files are in S3 and manually spot-checked.

---

### Phase 1 -- User Settings
> **~1-2 days | `daily-dragon-vocabulary-api`**

- Add `SettingsRepository`: reads/writes `{user_id}_settings.json` from S3
- Add `SettingsService`: wraps repository, provides defaults for new users
- Settings schema:
  ```json
  {
    "hsk_level": 1,
    "placement_completed": false
  }
  ```
- New endpoints:
  - `GET /daily-dragon/settings` -- fetch current user's settings
  - `PATCH /daily-dragon/settings` -- update settings
- Follows the exact same structural pattern as `VocabularyRepository` / `VocabularyService`

**Done when:** A new user gets a default settings file on first call; an existing user can read and update their settings.

---

### Phase 2 -- HSK Seeding & Progression Logic
> **~2-3 days | `daily-dragon-vocabulary-api`**

- Add `HskRepository`: loads HSK level files from S3 `hsk-data/` prefix
- Add `HskService` with the following responsibilities:
  - `get_hsk_words(level)` -- returns full word list for a given HSK level
  - `get_unseeded_words(user_id, level)` -- diff between HSK level words and user's current vocabulary
  - `seed_next_batch(user_id, level, batch_size=20)` -- adds the next N unseen HSK words to the user's vocabulary JSON with `hsk_level` and `source` fields; SRS fields initialised to defaults
  - `get_level_progress(user_id, level)` -- returns `{ total, mastered, in_progress, new }` counts for a level
  - `check_and_promote(user_id)` -- if >=80% of the current level is mastered, bumps `hsk_level` in settings and seeds the first batch of the next level
- New endpoint:
  - `GET /daily-dragon/hsk/progress` -- returns mastery breakdown per level (consumed by the Progress page)
- `check_and_promote` is called at the end of every batch review submission (existing `POST /daily-dragon/vocabulary/review` endpoint)

**Done when:** Submitting a successful review batch triggers progression checks; a user completing 80% of HSK 1 automatically receives HSK 2 words.

---

### Phase 3 -- Placement Test
> **~1-2 days | `daily-dragon-vocabulary-api`**

- New endpoints:
  - `GET /daily-dragon/placement/words` -- returns a sample of words across all levels (e.g. 5 words x 9 levels = 45 words)
  - `POST /daily-dragon/placement/submit` -- receives `{ word: known (bool) }` map; scores by level; finds the highest level where >=70% are known; sets `hsk_level` in settings; seeds that level's first batch into vocabulary; sets `placement_completed: true`
- If a user skips the test, they default to HSK level 1
- Placement words are sampled to cover representative vocabulary for each level (not the easiest or hardest words)

**Done when:** A new user completing the test lands on the correct starting level and immediately has their first word batch ready for practice.

---

### Phase 4 -- Sentence Generation Update
> **~0.5 days | `daily-dragon-openai-api`**

- `POST /daily-dragon/practice/sentences` request body gains an optional `hsk_level` field
- The `get_sentences_for_translation` prompt template is updated to inject `hsk_level` as a variable
- The LLM is instructed to keep surrounding vocabulary and grammar complexity appropriate for the stated HSK level
- No structural changes to the response -- same `SentencesResponse` model

**Done when:** Sentence generation requests include level context and the LLM adjusts difficulty accordingly.

---

### Phase 5 -- UI Overhaul
> **~2-3 days | `daily-dragon-ui`**

#### Remove
- `VocabularyPage`, `AddWordDialog`, `RemoveWordDialog`, `VocabularyList`
- All vocabulary add/delete service calls
- Vocabulary nav link and route

#### Add: `ProgressPage` (`/progress`)
- Calls `GET /daily-dragon/hsk/progress`
- Shows per-level breakdown: total words, mastered, in-progress, new
- Visual progress bars per HSK level
- Current active level highlighted prominently

#### Add: `PlacementTestPage` (`/placement`)
- Shown automatically to new users on first login (when `placement_completed: false`)
- Binary card UI: show hanzi, user taps "Know it" / "Don't know it"
- On submit, calls `POST /daily-dragon/placement/submit`
- Redirects to Practice on completion
- Skippable -- skip defaults the user to HSK 1

#### Update: `PracticePage`
- On load, fetch settings to get `hsk_level`
- Pass `hsk_level` alongside `words` when calling `/practice/sentences`
- Remove any references to manual add/remove vocabulary

#### Update: routing & navigation
- `/vocabulary` --> redirect to `/progress`
- Add `/placement` route
- Add first-login guard: if `!placement_completed`, redirect to `/placement` before allowing access to Practice
- Swap "Vocabulary" nav link for "Progress"

**Done when:** A new user lands on placement test; an existing user sees their HSK progress; practice sessions use level-aware sentence generation.

---

### Phase 6 -- Cleanup & Testing
> **~1 day | all repos**

- Remove or deprecate dead API endpoints (`POST /vocabulary`, `DELETE /vocabulary/{word}`)
- Add unit tests for `HskService.check_and_promote` (highest-risk logic)
- Add unit tests for placement test scoring
- Integration test: full review loop --> promotion trigger --> new words seeded --> appear in next due session
- Update `README.md` in each affected repo to reflect removed endpoints and new ones
- Update the root `daily-dragon` README roadmap to mark completed items and add new ones

**Done when:** CI passes, dead code removed, docs updated.

---

## 6. Timeline Estimate

```
Phase 0  | HSK data files prepared & uploaded to S3            | ~1-2 days
Phase 1  | User settings file + endpoints                       | ~1-2 days
Phase 2  | HSK seeding + progression logic                     | ~2-3 days
Phase 3  | Placement test endpoints                             | ~1-2 days
Phase 4  | OpenAI prompt gains hsk_level                       | ~0.5 days
Phase 5  | UI: remove vocab mgmt, add Progress & Placement    | ~2-3 days
Phase 6  | Cleanup, tests, integration verification            | ~1 day
─────────+|Total   |                                                        | ~9-14 days
```

Phases 1 and 2 are the critical path -- everything else depends on settings and seeding being in place.

---

## 7. Affected Repositories

| Repository | Changes |
|---|---|
| [`daily-dragon`](https://github.com/daily-dragon/daily-dragon) | This doc; README roadmap update |
| [`daily-dragon-vocabulary-api`](https://github.com/daily-dragon/daily-dragon-vocabulary-api) | New settings, HSK, placement endpoints and services; remove add/delete word endpoints; progression logic hooked into review submission |
| [`daily-dragon-openai-api`](https://github.com/daily-dragon/daily-dragon-openai-api) | `hsk_level` added to sentence generation request and prompt |
| [`daily-dragon-ui`](https://github.com/daily-dragon/daily-dragon-ui) | Remove vocabulary management UI; add Progress page, Placement test page, first-login guard; update practice to pass level |
