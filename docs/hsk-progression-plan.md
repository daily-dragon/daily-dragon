# HSK Progression & Automatic Advancement — Migration Plan

> **Status:** Phases 0-2, 4, 5 complete — Phase 3 next  
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
HSK word lists are stored as **7 separate read-only JSON files in S3** (`hsk/hsk1.json` ... `hsk/hsk7.json`), shared across all users. They are never modified at runtime. Levels 8 and 9 share the same word list as level 7 and are therefore not stored separately. Each file is a plain JSON array of hanzi strings — pinyin and English meanings are not included in the source data and will be looked up at runtime if needed.

### User settings stored like vocabulary
User-level preferences (current HSK level, placement test status) are stored in a per-user settings JSON file in S3 — following the same pattern already used for vocabulary files.

### Manual vocabulary management retired
The add word / remove word workflow is fully removed. The vocabulary page is replaced by a **Progress page** that shows word mastery per HSK level.

---

## 3. What Changes

### Removed

| Component | Status | Location |
|---|---|---|
| `POST /daily-dragon/vocabulary` — add word | ✅ done | `vocabulary-api` |
| `DELETE /daily-dragon/vocabulary/{word}` — remove word | ✅ done | `vocabulary-api` |
| `VocabularyPage` | ✅ done | `daily-dragon-ui` |
| `AddWordDialog` | ✅ done | `daily-dragon-ui` |
| `RemoveWordDialog` | ✅ done | `daily-dragon-ui` |
| `VocabularyList` | ✅ done | `daily-dragon-ui` |
| Vocabulary nav link | ✅ done | `daily-dragon-ui` |

### Added

| Component | Status | Location |
|---|---|---|
| `GET/PATCH /daily-dragon/settings` | ✅ done | `vocabulary-api` |
| `GET /daily-dragon/hsk/progress` | ✅ done | `vocabulary-api` |
| `GET /daily-dragon/placement/words` | ⏳ Phase 3 | `vocabulary-api` |
| `POST /daily-dragon/placement/submit` | ⏳ Phase 3 | `vocabulary-api` |
| HSK seeding & progression service | ✅ done | `vocabulary-api` |
| `hsk_level` field on word entries | ✅ done | vocabulary S3 files |
| `{user_id}_settings.json` in S3 | ✅ done | S3 vocabulary bucket |
| Static `hsk/hsk1.json` ... `hsk7.json` in S3 | ✅ done | S3 (shared, read-only) |
| `hsk_level` field in sentence generation request | ✅ done | `openai-api` |
| `ProgressPage` | ✅ done | `daily-dragon-ui` |
| `settingsService.js` / `hskService.js` | ✅ done | `daily-dragon-ui` |
| `PlacementTestPage` | ⏳ Phase 3 | `daily-dragon-ui` |
| First-login placement guard | ⏳ Phase 3 | `daily-dragon-ui` |

### Updated

| Component | Change | Status | Location |
|---|---|---|---|
| Word entry schema | Add `hsk_level` (int) field | ✅ done | vocabulary S3 files |
| `GET /daily-dragon/vocabulary/due` | Auto-seed from HSK when below limit | ✅ done | `vocabulary-api` |
| `POST /practice/sentences` request | Add optional `hsk_level` field | ✅ done | `openai-api` |
| Sentence generation prompt | Inject `${hskLevelInstruction}` into template | ✅ done | `openai-api` |
| `App.jsx` | Fetch settings on load; pass `hskLevel` to Practice | ✅ done | `daily-dragon-ui` |
| `Header` | Display HSK level badge; "Vocabulary" → "Progress" | ✅ done | `daily-dragon-ui` |
| `aiService.js` | Pass `hsk_level` in sentence request | ✅ done | `daily-dragon-ui` |
| `renderSentence` | Extracted to shared module; used by Practice and Review | ✅ done | `daily-dragon-ui` |
| Review submission handler | Trigger `check_and_promote` after each batch | ✅ done | `vocabulary-api` |

---

## 4. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| HSK standard | New HSK (2021), levels 1-9 | Future-proof; more granular than old 1-6 |
| HSK storage | 7 S3 JSON files under `hsk/` in `daily-dragon-bucket` | Levels 8-9 share level 7's word list; each file contains only words unique to that level; lazy loading; mirrors existing patterns |
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

### ✅ Phase 0 -- HSK Data Preparation
> **COMPLETE | No code changes to any service**

- Sourced New HSK (2021) word lists for levels 1-7
  - Complete word lists were difficult to obtain online; this was the main effort of this phase
  - Levels 8 and 9 share the same vocabulary as level 7, so no separate files were created
  - Each file contains **only the words unique to that level** — lists are not cumulative
- Each file is a plain JSON array of hanzi strings:
  ```
  ["一", "一下", "一些", "一半", "一点儿", "七", ...]
  ```
- 7 files uploaded: `hsk1.json` through `hsk7.json`
- S3 location: `s3://daily-dragon-bucket/hsk/` (not user-scoped, never modified at runtime)
- These files are the ground truth the backend seeds from

> **Note:** The files contain hanzi only — no pinyin or English meanings. The `HskService` and vocabulary entries will need to either look up meanings at seed time (e.g. via dictionary API or OpenAI) or store hanzi-only entries and enrich lazily.

**Done when:** ✅ All 7 files are in S3 and manually spot-checked.

---

### ✅ Phase 1 -- User Settings
> **COMPLETE | `daily-dragon-vocabulary-api`**

- `SettingsRepository`: reads/writes `{user_id}_settings.json` from S3
- `SettingsService`: wraps repository, provides defaults for new users
- Settings schema:
  ```json
  {
    "hsk_level": 1,
    "placement_completed": false
  }
  ```
- Endpoints delivered:
  - `GET /daily-dragon/settings` -- fetch current user's settings
  - `PATCH /daily-dragon/settings` -- update settings
- Follows the exact same structural pattern as `VocabularyRepository` / `VocabularyService`
- New user receives default settings file on first call; existing users can read and update their settings

---

### ✅ Phase 2 -- HSK Seeding & Progression Logic
> **COMPLETE | `daily-dragon-vocabulary-api` | branch: `wire-level-progress` → merged to main**

- `HskRepository` (`repository/hsk_repository.py`): reads `hsk/hsk{level}.json` from S3; raises `ValueError` on missing level, re-raises other `ClientError`s
- `HskService` (`service/hsk_service.py`) with constants `MAX_HSK_LEVEL = 7`, `PROMOTION_THRESHOLD = 0.8`, `SEED_BATCH_SIZE = 20`:
  - `get_hsk_words(level)` -- delegates to `HskRepository`
  - `get_unseeded_words(user_id, level)` -- set diff between HSK level words and existing vocabulary keys
  - `seed_next_batch(user_id, level, batch_size=SEED_BATCH_SIZE)` -- slices the first N unseeded words, initialises SM-2 metadata via `SpacedRepetitionService.initialize_word_metadata()`, adds `hsk_level` field, merges into vocabulary and saves in a **single write**; returns 0 and skips write if nothing to seed; accepts dynamic `batch_size`
  - `seed_words(user_id, count)` -- convenience wrapper: reads current `hsk_level` from settings, delegates to `seed_next_batch`; used by `VocabularyService` to top up the due-words queue
  - `get_level_progress(user_id, level)` -- filters vocabulary by `hsk_level == level`; counts `mastered` (`interval >= 21`), `new` (`interval == 0`), `in_progress` (remainder); words without `hsk_level` are excluded; `total` is taken from `HSK_LEVEL_WORD_COUNT` (static dict), not the seeded count — ensuring the mastery ratio in `check_and_promote` is computed against the whole level, not just the words introduced so far
  - `check_and_promote(user_id)` -- short-circuits at `MAX_HSK_LEVEL`; computes mastery ratio for current level; if `>= 0.80`, increments `hsk_level` in settings, saves, and immediately seeds first 20 words of the new level; returns `True` on promotion
- `HSK_LEVEL_WORD_COUNT = {1: 300, 2: 197, 3: 493, 4: 990, 5: 1579, 6: 1777, 7: 5562}` — hardcoded static dict used by `get_level_progress`; derived from the actual JSON files in S3
- New Pydantic models: `LevelProgress`, `HskProgressResponse`
- New endpoint: `GET /daily-dragon/hsk/progress` -- calls `get_level_progress` for levels 1–7, returns `current_level` + per-level `{ total, mastered, in_progress, new }` breakdown
- `POST /daily-dragon/vocabulary/reviews` -- `HskService` added as dependency; `check_and_promote` called unconditionally after every review batch (promotion is a side effect; review result always returned)
- `GET /daily-dragon/vocabulary/due` (due words) -- auto-seeds from current HSK level when due-word count is below the limit; shortfall calculated as `limit - len(due_words)`; calls `seed_words(user_id, shortfall)` and re-fetches if any words were seeded
- Tests added:
  - `tests/repository/test_hsk_repository.py` — 4 tests (success, level 7 key, `NoSuchKey` → `ValueError`, other errors re-raised)
  - `tests/service/test_hsk_service.py` — 15+ tests across 5 classes covering all `HskService` methods including `seed_words`
  - `tests/test_hsk_endpoints.py` — 5 endpoint tests (progress shape, field presence, correct user ID, promotion side effect, review result unaffected)
  - `tests/conftest.py` — `mock_hsk_service` fixture added; wired into `test_client` via `dependency_overrides`

**Done when:** ✅ Submitting a successful review batch triggers progression checks; a user completing 80% of HSK 1 automatically receives HSK 2 words; due-words endpoint auto-seeds when vocabulary runs low.

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

### ✅ Phase 4 -- Sentence Generation Update
> **COMPLETE | `daily-dragon-openai-api`**

- `WordsList` model gains `hsk_level: int | None = None` optional field
- `get_sentences_for_translation(words, hsk_level)` conditionally builds an `hsk_instruction` string injected as `${hskLevelInstruction}` in the prompt template; empty string when `hsk_level` is `None`
- Prompt template updated to include the `${hskLevelInstruction}` placeholder
- No structural changes to the response — same `SentencesResponse` model
- Tests updated in `test_openai_api_app.py` and `test_openai_service.py`

**Done when:** ✅ Sentence generation requests include level context and the LLM adjusts difficulty accordingly.

---

### ✅ Phase 5 -- UI Overhaul
> **COMPLETE (placement test UI deferred to Phase 3) | `daily-dragon-ui`**

#### ✅ Removed
- `VocabularyPage`, `AddWordDialog`, `RemoveWordDialog`, `VocabularyList` and their tests
- `addWord`, `deleteWord`, `fetchVocabulary` from `vocabularyService.js`
- Vocabulary nav link and route

#### ✅ Added: `ProgressPage` (`/progress`)
- `hskService.js` — calls `GET /daily-dragon/hsk/progress`
- `settingsService.js` — `getSettings` / `updateSettings` calling `GET|PATCH /daily-dragon/settings`
- `ProgressPage` shows per-level breakdown: total words, mastered, in-progress, new
- `ProgressBar` component renders stacked mastered + in-progress percentages visually
- Current active level highlighted prominently
- Tests: `ProgressPage.test.jsx`, `hskService.test.js`, `settingsService.test.js`

#### ⏳ Deferred: `PlacementTestPage` (`/placement`)
- Depends on Phase 3 backend endpoints; not yet implemented
- Will be added once `GET /daily-dragon/placement/words` and `POST /daily-dragon/placement/submit` exist

#### ✅ Updated: `PracticePage` / `App`
- `App.jsx` fetches settings on load; `hskLevel` state threaded down to `Practice` and `Header`
- `Header` displays HSK level badge
- `aiService.js` passes `hsk_level` in the sentence generation request body
- `renderSentence` extracted to shared module `practice/renderSentence.jsx`; consumed by both `PracticePage` and `ReviewPage`

#### ✅ Updated: routing & navigation
- `/progress` route added; "Vocabulary" nav link replaced with "Progress"
- `TextEncoder` polyfill added to `setupTests.js` for router-using component tests

#### ⏳ Deferred: first-login guard
- Redirect to `/placement` when `placement_completed: false` — deferred until Phase 3 is done

**Done when:** ✅ Existing users see their HSK progress; practice sessions use level-aware sentence generation. Placement test UI pending Phase 3.

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
Phase 0  ✅ | HSK data files prepared & uploaded to S3            | complete
Phase 1  ✅ | User settings file + endpoints                       | complete
Phase 2  ✅ | HSK seeding + progression logic                     | complete
Phase 3  ⏳ | Placement test endpoints                             | ~1-2 days
Phase 4  ✅ | OpenAI prompt gains hsk_level                       | complete
Phase 5  ✅ | UI: remove vocab mgmt, add Progress page            | complete (placement UI in Phase 3)
Phase 6  ⏳ | Cleanup, tests, integration verification            | ~1 day
────────────+──────────────────────────────────────────────────────+──────────
Remaining                                                          | ~2-3 days
```

Phase 3 (placement test) is the only remaining blocker — Phase 6 cleanup follows after.

---

## 7. Affected Repositories

| Repository | Changes |
|---|---|
| [`daily-dragon`](https://github.com/daily-dragon/daily-dragon) | This doc; README roadmap update |
| [`daily-dragon-vocabulary-api`](https://github.com/daily-dragon/daily-dragon-vocabulary-api) | New settings, HSK, placement endpoints and services; remove add/delete word endpoints; progression logic hooked into review submission |
| [`daily-dragon-openai-api`](https://github.com/daily-dragon/daily-dragon-openai-api) | `hsk_level` added to sentence generation request and prompt |
| [`daily-dragon-ui`](https://github.com/daily-dragon/daily-dragon-ui) | Remove vocabulary management UI; add Progress page, Placement test page, first-login guard; update practice to pass level |
