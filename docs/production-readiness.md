# Daily Dragon — Production-Readiness Audit

> **Date:** 2026-05-27  
> **Scope:** `daily-dragon-vocabulary-api`, `daily-dragon-openai-api`, `daily-dragon-ui`  
> **Overall verdict:** Not production-ready. Several launch-blocking issues exist across all three repos.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Critical Launch Blockers](#2-critical-launch-blockers)
3. [Findings by Area](#3-findings-by-area)
   - [Security](#31-security)
   - [Error Handling](#32-error-handling)
   - [Logging & Observability](#33-logging--observability)
   - [Testing](#34-testing)
   - [Infrastructure & Deployment](#35-infrastructure--deployment)
   - [Resilience & Data Integrity](#36-resilience--data-integrity)
   - [Performance](#37-performance)
   - [UX & Usability](#38-ux--usability)
   - [Configuration Management](#39-configuration-management)
   - [Dead Code & Incomplete Features](#310-dead-code--incomplete-features)
4. [Prioritised Gap List](#4-prioritised-gap-list)

---

## 1. Executive Summary

| Area | vocabulary-api | openai-api | ui | Overall |
|---|---|---|---|---|
| Security | 🟡 Medium | 🔴 Critical | 🟡 Medium | 🔴 |
| Error Handling | 🟡 Medium | 🔴 Critical | 🟡 Medium | 🔴 |
| Logging & Observability | 🟡 Medium | 🔴 Critical | 🟢 N/A | 🔴 |
| Testing | 🔴 Gaps | 🔴 Broken | 🔴 Gaps | 🔴 |
| Infrastructure / CI | 🟡 Medium | 🔴 No IaC | 🟡 Outdated | 🔴 |
| Resilience / Data Integrity | 🔴 Critical | 🟡 Medium | 🟡 Medium | 🔴 |
| Performance | 🟡 Medium | 🟢 Low risk | 🟡 Medium | 🟡 |
| UX / Usability | 🟢 N/A | 🟢 N/A | 🟡 Medium | 🟡 |
| Configuration Management | 🟡 Medium | 🟡 Medium | 🟡 Medium | 🟡 |

The most damaging issues are:

- **Core feature broken** — HSK level promotion is mathematically unreachable via normal use (`vocabulary-api`)
- **OpenAI key committed to git** — must be rotated before any further pushes (`openai-api`)
- **Zero error handling + zero logging** in the OpenAI service — the API is a black box in production (`openai-api`)
- **Lambda timeout** is almost certainly the AWS default of 3 s — GPT-4o calls take 5–30 s (`openai-api`)
- **Infinite spinner** when any API call fails — no error state in `PracticePage` (`ui`)

---

## 2. Critical Launch Blockers

These must be resolved before exposing the app to real users.

### B-1 · HSK promotion is mathematically unreachable
**Repo:** `vocabulary-api` | **File:** `service/hsk_service.py:15-18, 68, 99`

`check_and_promote` computes `mastered / HSK_LEVEL_WORD_COUNT[level]`. For level 1 that denominator is **300**. The due-words endpoint seeds in batches of 20. A user who reviews all 20 words to mastery achieves `20/300 = 6.7%` — far below the 80% threshold. Promotion is only theoretically possible after all 300 level-1 words are seeded and 80% mastered, but no mechanism automatically seeds the remaining 280 words. The core progression loop does not work.

**Fix:** Either (a) change `total` in `get_level_progress` to the seeded count (not the full level size) when computing the promotion ratio, or (b) treat the 80% threshold as "80% of seeded words" and accept users are promoted based on their exposure so far, or (c) add logic in `get_due_words` to progressively seed more words before promotion check. Option (b) is the lowest-risk change.

### B-2 · OpenAI API key committed to `.env`
**Repo:** `openai-api` | **File:** `.env:1`

A live `sk-proj-…` key is present in `.env`. The file is not in `.gitignore`. Even if the file is currently untracked, it must never be committed. The key must be **rotated immediately**, `.env` added to `.gitignore`, and the key set as a Lambda environment variable through a secret store.

### B-3 · Lambda timeout is almost certainly 3 s (default)
**Repo:** `openai-api` | **File:** no IaC exists

There is no IaC file for this Lambda. The default AWS Lambda timeout is 3 seconds. GPT-4o completions typically take 5–30 seconds. The function times out on virtually every request in production.

**Fix:** Set Lambda timeout to at minimum 60 s (ideally 120 s) via IaC or manually in the AWS console.

### B-4 · Zero error handling in OpenAI service
**Repo:** `openai-api` | **File:** `openai_service.py:19-25`

`send_prompt` has no `try/except`. Any `openai.RateLimitError`, `APITimeoutError`, `AuthenticationError`, or `InternalServerError` propagates as an unhandled exception, returning a raw Python traceback to the client as a 500 body. The `choices[0]` access on line 25 will throw `IndexError` on content-policy refusals.

### B-5 · Zero logging in OpenAI service
**Repo:** `openai-api` | **File:** entire codebase

There is not a single `import logging` or log statement anywhere in `openai-api`. CloudWatch receives zero structured output. Token usage (`response.usage`) is never read. Debugging production failures is impossible. Cost tracking is impossible.

### B-6 · Infinite spinner on PracticePage API failure
**Repo:** `ui` | **File:** `src/components/practice/PracticePage.jsx:20-50`

The `useEffect` IIFE has no `try/catch`. If `getDueVocabulary()` or `getPracticeSentences()` fails for any reason (network, 5xx, expired token), `gettingSentences` stays `true` forever and the spinner never stops. Users are stuck with no error message and no recovery path.

### B-7 · Double-encoded JSON response from OpenAI API
**Repo:** `openai-api` | **File:** `openai_service.py:25`

`send_prompt` returns `response.choices[0].message.content` — a raw JSON **string**. FastAPI then JSON-encodes that string a second time, so clients receive `"{\"sentences\": [...]}"` instead of `{"sentences": [...]}`. The UI works around this by calling `JSON.parse` in `PracticePage`, but this is a contract violation and any new client will be surprised by it.

---

## 3. Findings by Area

### 3.1 Security

#### `vocabulary-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| SEC-V1 | Cognito `token_use` claim never validated — an access token passes auth as readily as an id token | High | `auth/cognito.py:22,36-41` |
| SEC-V2 | Cognito pool ID and client ID hardcoded in source; no env-var fallback | Medium | `auth/cognito.py:29-33` |
| SEC-V3 | `.env` not in `.gitignore`; `S3_BUCKET` value committed | Medium | `.env`, `.gitignore` |
| SEC-V4 | `WordEntry.word` has no `max_length` — arbitrarily long strings stored in S3 | Low | `daily_dragon_app.py:49-50` |
| SEC-V5 | `BatchReviewRequest.reviews` has no `max_length` — unbounded batch abuse | Medium | `daily_dragon_app.py:61` |
| SEC-V6 | CORS allows `http://localhost:5173` in the production allow-list | Low | `daily_dragon_app.py:28-36` |
| SEC-V7 | S3 bucket security posture (encryption, public-access-block) not defined in IaC | Medium | `cdk/app.py:8` |
| SEC-V8 | CI IAM policy uses `"Resource": "*"` for all actions including `s3:DeleteBucket`, `iam:PassRole`, `lambda:InvokeFunction` | High | `scripts/cdk_permissions_policy.json` |
| SEC-V9 | `from pydantic.types import Any` is non-standard; fragile across Pydantic versions — breaks auth on import if it ever stops re-exporting | High | `auth/cognito.py:5` |

#### `openai-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| SEC-O1 | **OpenAI API key in `.env` (not gitignored)** | Critical | `.env:1` |
| SEC-O2 | Cognito credentials hardcoded in source | High | `auth/cognito.py:29-33` |
| SEC-O3 | User-supplied text inserted verbatim into LLM prompts — prompt injection risk | High | `openai_service.py:37,49-54` |
| SEC-O4 | No input size constraints on `WordsList.words` or `SentenceTranslationsToEvaluate.translations` | Medium | `openai_api_app.py:24-26`, `models.py:28-35` |
| SEC-O5 | CORS allows `localhost:5173` in production allow-list | Medium | `openai_api_app.py:16` |

#### `ui`

| ID | Finding | Severity | Location |
|---|---|---|---|
| SEC-U1 | Cognito `aws_user_pools_id` and `aws_user_pools_web_client_id` committed to source; not excluded by `.gitignore` | Medium | `src/aws-exports.js:3-6` |
| SEC-U2 | API Gateway URL (including stage name) hardcoded in source | Medium | `src/config.js:1` |
| SEC-U3 | `session.tokens.idToken.toString()` — no null guard; throws `TypeError` on expired/missing session | High | `src/services/auth.js:5` |
| SEC-U4 | No Content Security Policy configured in app or CloudFront | Medium | `index.html` |
| SEC-U5 | No `X-Frame-Options`, `X-Content-Type-Options`, or other security headers | Low | CloudFront (not configured) |
| SEC-U6 | No token expiry handling; expired sessions silently fail all API calls with no redirect to re-auth | Medium | All service files |

---

### 3.2 Error Handling

#### `vocabulary-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| ERR-V1 | `save_vocabulary` / `save_settings` S3 errors propagate as unhandled 500 — no logging at point of failure | High | `vocabulary_repository.py:38`, `settings_repository.py:39` |
| ERR-V2 | `DELETE /vocabulary/{word}` returns 200 `"deleted"` even when word did not exist | Medium | `daily_dragon_app.py:129-134` |
| ERR-V3 | `HskRepository.get_hsk_words` raises `ValueError` that is uncaught in the progress endpoint | Medium | `hsk_repository.py:27`, `daily_dragon_app.py:102` |
| ERR-V4 | `check_and_promote` failure in `submit_reviews` causes a 500 even though the reviews were already saved | Medium | `daily_dragon_app.py:175-178` |
| ERR-V5 | No `response_model` on `GET /vocabulary`, `/vocabulary/due`, `POST /vocabulary/reviews` | Low | `daily_dragon_app.py:118,142,153` |

#### `openai-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| ERR-O1 | **No `try/except` around OpenAI API call** — all errors become 500 with traceback in response | Critical | `openai_service.py:19-25` |
| ERR-O2 | `response.choices[0]` accessed without bounds check — `IndexError` on content-policy refusals | High | `openai_service.py:25` |
| ERR-O3 | No HTTP status mapping (`RateLimitError` → 429, `AuthenticationError` → 502) | High | `openai_service.py` |
| ERR-O4 | Prompt file read failures (`FileNotFoundError`) are unhandled | Medium | `openai_service.py:29-30,47` |
| ERR-O5 | Missing `OPENAI_API_KEY` causes Lambda cold start crash with no diagnostic message | Medium | `openai_service.py:16` |

#### `ui`

| ID | Finding | Severity | Location |
|---|---|---|---|
| ERR-U1 | **`useEffect` IIFE in `PracticePage` has no error handler — infinite spinner on any API failure** | Critical | `PracticePage.jsx:20-50` |
| ERR-U2 | `doSubmit` has no `catch` — failures silent, no user feedback | High | `PracticePage.jsx:63-77` |
| ERR-U3 | JSON parse failure leaves `sentencesArray` empty with no error message | Medium | `PracticePage.jsx:27-34` |
| ERR-U4 | `App.jsx` settings fetch failure silently defaults to `hskLevel=1` with no indication to user | Medium | `App.jsx:23` |
| ERR-U5 | No 401/403 interception at the service layer — expired sessions silently fail | High | All service files |

---

### 3.3 Logging & Observability

#### `vocabulary-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| LOG-V1 | Plaintext log format — CloudWatch Insights queries require JSON structured logging | Medium | `daily_dragon_app.py:15-20` |
| LOG-V2 | No request/response middleware logging — method, path, user ID, latency, status | Medium | `daily_dragon_app.py` |
| LOG-V3 | `logger` imported but never called in `settings_service.py` | Low | `settings_service.py:1,8` |
| LOG-V4 | No cold start log — impossible to measure cold start frequency from CloudWatch | Low | `daily_dragon_handler.py` |
| LOG-V5 | Two log calls use f-strings (evaluated even when filtered) vs `%`-style lazy formatting | Low | `vocabulary_service.py:37,114` |

#### `openai-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| LOG-O1 | **Zero logging across the entire codebase** | Critical | All files |
| LOG-O2 | **`response.usage` never read** — no token count, no cost tracking per request | Critical | `openai_service.py:25` |
| LOG-O3 | No request-level logging (words sent, HSK level, latency) | High | `openai_api_app.py` |
| LOG-O4 | No auth event logging (success/failure) | High | `auth/cognito.py` |

---

### 3.4 Testing

#### `vocabulary-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| TEST-V1 | `--cov-fail-under` not in CI command; `.coveragerc` threshold silently unenforced | High | `.github/workflows/build.yml:14` |
| TEST-V2 | Zero auth tests — no test verifies that a missing/invalid/expired token is rejected with 401 | High | `tests/conftest.py` |
| TEST-V3 | `test_delete_word_not_exists` asserts `mock_repository.save_vocab.assert_not_called()` — wrong method name; assertion always passes | High | `tests/service/test_vocabulary_service.py:48` |
| TEST-V4 | No tests for missing `S3_BUCKET` env var at startup | Medium | `tests/repository/` |
| TEST-V5 | Integration tests are manual-only (documented in INTEGRATION_TESTS.md); nothing runs in CI | Medium | `tests/INTEGRATION_TESTS.md` |
| TEST-V6 | `pytest.ini` sets `--maxfail=1` — CI reports only first failure; rest of suite is invisible | Low | `pytest.ini:2` |

#### `openai-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| TEST-O1 | Service tests mock `builtins.open` but `openai_service.py` reads files via `Path.read_text()` — mocks are never invoked; tests use real prompt files silently | Critical | `tests/test_openai_service.py` |
| TEST-O2 | Endpoint tests make requests but assert nothing on the response (no status code, no body check) | High | `tests/test_openai_api_app.py:80-116` |
| TEST-O3 | Auth bypass tests never make an HTTP request and assert nothing | High | `tests/test_openai_api_app.py:312-324` |
| TEST-O4 | **Double-encoded JSON response bug is never caught** by any test | High | `tests/test_openai_api_app.py` |
| TEST-O5 | Zero error-path tests (rate limit, timeout, auth error, empty choices, missing prompt file) | Medium | `tests/test_openai_service.py` |
| TEST-O6 | CI `testpaths` points to `tests/` (relative to root) but tests live in `openai_api/tests/` | Medium | `pytest.ini`, `.github/workflows/build.yml:17` |

#### `ui`

| ID | Finding | Severity | Location |
|---|---|---|---|
| TEST-U1 | No tests for `App.jsx`, `Header.jsx`, `Home.jsx`, `WelcomePage.jsx`, `Practice.jsx` | High | `src/tests/` |
| TEST-U2 | **`ReviewPage` has zero tests** despite being the most complex display component | High | `src/tests/` |
| TEST-U3 | `renderSentence.jsx` has zero tests — regex parsing untested for edge cases | High | `src/tests/` |
| TEST-U4 | `auth.js` (`getToken`) has zero tests — null-access crash on expired session is uncaught | High | `src/tests/` |
| TEST-U5 | `PracticePage` test has no error-path cases (API failure, empty vocabulary, parse failure) | High | `PracticePage.test.jsx` |
| TEST-U6 | `eslint-plugin-react-hooks` installed but not registered in `eslint.config.js` — hooks rules inactive | Medium | `eslint.config.js` |

---

### 3.5 Infrastructure & Deployment

#### `vocabulary-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| INFRA-V1 | Lambda memory and timeout not defined anywhere in IaC — default is 128 MB / 3 s | High | `cdk/app.py` |
| INFRA-V2 | `S3_BUCKET` set via `.env` bundled into Lambda layer — changing it requires a layer redeploy | High | `.env`, `daily_dragon_handler.py` |
| INFRA-V3 | CI only updates the Lambda layer ARN; memory, timeout, env vars, handler are never touched | Medium | `.github/workflows/build.yml:62-64` |
| INFRA-V4 | No deployment rollback — no previous layer ARN captured, no Lambda aliases/traffic shifting | Medium | `.github/workflows/build.yml` |
| INFRA-V5 | `cdk bootstrap` runs on every production deploy — adds unnecessary latency | Low | `.github/workflows/build.yml:46` |

#### `openai-api`

| ID | Finding | Severity | Location |
|---|---|---|---|
| INFRA-O1 | **No IaC of any kind** — Lambda function, API Gateway, IAM role all created manually | High | repo root |
| INFRA-O2 | **Lambda timeout unknown/unmanaged** — almost certainly default 3 s | Critical | no IaC |
| INFRA-O3 | **`OPENAI_API_KEY` not injected by any automation** — unclear how it reaches Lambda | Critical | no IaC |
| INFRA-O4 | GitHub Actions use `checkout@v2` / `setup-python@v2` (EOL Node 12/16) | Medium | `.github/workflows/build.yml` |
| INFRA-O5 | `openai_api_handler.py` (at repo root) excluded from the packaged layer — its deployment is undocumented | Medium | `.github/workflows/build.yml` |

#### `ui`

| ID | Finding | Severity | Location |
|---|---|---|---|
| INFRA-U1 | `actions/checkout@v2` (EOL); `jakejarvis/s3-sync-action@v0.5.1` (unmaintained, 2020) | High | `.github/workflows/build.yml:7,33` |
| INFRA-U2 | AWS credentials passed as env vars to a third-party action — supply chain risk | High | `.github/workflows/build.yml:34-38` |
| INFRA-U3 | No `--cache-control` on S3 sync — all assets served with `no-cache` by default | High | `.github/workflows/build.yml:33` |
| INFRA-U4 | CloudFront `--paths "/*"` invalidates everything on every deploy — expensive and unnecessary with content-hashed assets | Medium | `.github/workflows/build.yml:46` |
| INFRA-U5 | Build targets Node 25 (non-LTS "current"); should use LTS (Node 22) | Medium | `.github/workflows/build.yml:11,28` |

---

### 3.6 Resilience & Data Integrity

| ID | Repo | Finding | Severity | Location |
|---|---|---|---|---|
| RES-1 | vocab-api | Read-modify-write race condition on vocabulary S3 file — concurrent requests from same user cause lost updates | Medium | `vocabulary_repository.py` |
| RES-2 | vocab-api | `S3_BUCKET=None` passed to boto3 gives `ParamValidationError` at runtime rather than clear startup failure | Medium | All repository `__init__` |
| RES-3 | vocab-api | boto3 client created on every request (per DI injection) — TCP connection pool not reused | Low | All repository `__init__` |
| RES-4 | vocab-api | `check_and_promote` is non-atomic — if Lambda dies between `save_settings` and `seed_next_batch`, user is promoted but gets no new words | Medium | `hsk_service.py:104-110` |
| RES-5 | openai-api | No timeout set on `OpenAI()` client — SDK default is 600 s; Lambda execution budget consumed by a hung call | Critical | `openai_service.py:16` |
| RES-6 | openai-api | No retry on `RateLimitError`, `APIConnectionError`, `InternalServerError` | High | `openai_service.py` |
| DATA-1 | vocab-api | **Promotion ratio computed against full level word count (300), not seeded count — promotion unreachable** | Critical | `hsk_service.py:15-18,68,99` |
| DATA-2 | vocab-api | `update_settings` persists arbitrary unknown keys from the PATCH body | Medium | `settings_service.py:19-24` |
| DATA-3 | vocab-api | `hsk_level` in settings has no `ge=1, le=7` constraint — PATCH `hsk_level: 999` is accepted | Medium | `daily_dragon_app.py:44-47` |
| DATA-4 | vocab-api | Lazy migration writes to S3 on every `get_due_words` call for old-format users (forever, no migration-complete flag) | Low | `vocabulary_repository.py:71-78` |

---

### 3.7 Performance

| ID | Repo | Finding | Severity | Location |
|---|---|---|---|---|
| PERF-1 | vocab-api | Full vocabulary JSON read from S3 on **every** operation regardless of size | Medium | All repositories |
| PERF-2 | vocab-api | `GET /vocabulary/due` with seeding triggers up to **5 S3 GETs + 2 S3 PUTs** in series | High | `vocabulary_service.py:44-57` |
| PERF-3 | vocab-api | `GET /hsk/progress` makes **8 sequential S3 GETs** (settings + 7× vocabulary for level loop) | High | `daily_dragon_app.py:100-103` |
| PERF-4 | vocab-api | HSK word lists (read-only, static) fetched from S3 on every seeding call — no in-process cache | Medium | `hsk_repository.py:20-29` |
| PERF-5 | openai-api | No `max_tokens` cap — model generates as many tokens as it wants | Medium | `openai_service.py:20-24` |
| PERF-6 | openai-api | `N=5` sentences requested regardless of word count — mismatched when fewer/more words sent | Medium | `openai_service.py:13` |
| PERF-7 | ui | No code splitting — entire app bundled and loaded on first visit | Medium | `src/main.jsx` |
| PERF-8 | ui | `aws-amplify` full monolith imported — pulls in Analytics, DataStore, Kinesis, Firehose clients never used | Medium | `package.json` |
| PERF-9 | ui | Google Fonts loaded via runtime network request to third-party CDN — render-blocking, GDPR consideration | Low | `src/App.css:1` |

---

### 3.8 UX & Usability

| ID | Finding | Severity | Location |
|---|---|---|---|
| UX-01 | **Infinite spinner** when any API call in `PracticePage` fails — no timeout, no retry, no error message | Critical | `PracticePage.jsx:20-50` |
| UX-02 | No empty state when zero words are due for review | High | `PracticePage.jsx` |
| UX-03 | `ev.score` from AI response may be the string `"5/10"` (prompt example uses this format) — all score comparisons return `false`, everything renders red | High | `aiService.js`, `prompts.js:13` |
| UX-04 | No `/vocabulary` redirect — users who bookmarked the old page get a blank screen | Medium | `App.jsx:32-36` |
| UX-05 | No catch-all 404 route | Medium | `App.jsx:32-36` |
| UX-06 | Placement test / first-login guard not implemented — new users land directly on Practice with no onboarding | High | `App.jsx` (Phase 3 pending) |
| UX-07 | Translation `<Input>` has no associated `<label>` — inaccessible to screen readers | Medium | `PracticePage.jsx:116-119` |
| UX-08 | No SRS schedule visibility — no display of when words are next due, no "nothing due today" state | Medium | No component |
| UX-09 | `ReviewPage` is an anonymous default export — invisible in DevTools and error stacks | Low | `ReviewPage.jsx:19` |

---

### 3.9 Configuration Management

| ID | Repo | Finding | Severity |
|---|---|---|---|
| CFG-1 | vocab-api | Cognito region, pool ID, client ID hardcoded in source | Medium |
| CFG-2 | vocab-api | CORS allowed origins list hardcoded (prod CloudFront + localhost together) | Medium |
| CFG-3 | vocab-api | `S3_BUCKET`, Lambda function name, layer name hardcoded in CDK and CI scripts | Low |
| CFG-4 | vocab-api | `S3_FILE_PATH=vocabulary.json` set in `.env` but never read by any code | Low |
| CFG-5 | vocab-api | `SEED_BATCH_SIZE`, `PROMOTION_THRESHOLD`, `MAX_HSK_LEVEL`, `DUE_WORDS_LIMIT` are code constants not configurable by environment | Low |
| CFG-6 | openai-api | `MODEL_NAME = "gpt-4o-2024-08-06"` hardcoded — model upgrade requires code change + redeploy | High |
| CFG-7 | openai-api | `TARGET_LANGUAGE = "English"` hardcoded | Medium |
| CFG-8 | openai-api | `N = 5` (sentence count) hardcoded | Low |
| CFG-9 | openai-api | No temperature, seed, or sampling parameters — response variability uncontrolled | Medium |
| CFG-10 | openai-api | All `requirements.txt` dependencies unpinned — `pip install` on fresh system may get breaking major versions | High |
| CFG-11 | ui | API Gateway URL and Cognito credentials hardcoded in source files | Medium |
| CFG-12 | ui | No staging environment; all main-branch pushes deploy to production | Medium |

---

### 3.10 Dead Code & Incomplete Features

| ID | Repo | Finding | Location |
|---|---|---|---|
| DEAD-1 | vocab-api | `@app.options("/daily-dragon/vocabulary")` — redundant with CORSMiddleware, missing for other routes | `daily_dragon_app.py:137-139` |
| DEAD-2 | vocab-api | `S3_FILE_PATH` env var loaded but never consumed | `.env:2` |
| DEAD-3 | vocab-api | `logger` imported but never used in `settings_service.py` | `settings_service.py:1,8` |
| DEAD-4 | vocab-api | `pydantic-settings` used in `cognito.py` but not listed in `requirements.txt` — implicit transitive dep | `auth/cognito.py:4` |
| DEAD-5 | vocab-api | `INTEGRATION_TESTS.md` mentions `source: "hsk"` field that is never set by `seed_next_batch` | `tests/INTEGRATION_TESTS.md:44` |
| DEAD-6 | openai-api | `SentencesResponse` and `TranslationEvaluationResponse` imported in `openai_api_app.py` but never used | `openai_api_app.py:7` |
| DEAD-7 | openai-api | `WordsList` defined inline in `openai_api_app.py` rather than in `models.py` | `openai_api_app.py:24` |
| DEAD-8 | openai-api | `openai_api_handler.py` (root-level) excluded from the packaged layer; deployment is undocumented | `openai_api_handler.py` |
| DEAD-9 | ui | `src/services/ai/prompts.js` — both exports unused; client-side prompts were moved to backend | `src/services/ai/prompts.js` |
| DEAD-10 | ui | Empty ghost directory `src/tests/components/vocabulary/` | `src/tests/components/vocabulary/` |
| DEAD-11 | ui | `'use client'` directive in `toaster.jsx` — Next.js artifact, meaningless in Vite SPA | `src/components/ui/toaster.jsx:1` |
| DEAD-12 | ui | `updateSettings` service function implemented but called from no component | `src/services/settingsService.js:14-24` |
| DEAD-13 | ui | `react-hook-form` installed but never imported | `package.json` |
| DEAD-14 | ui | Testing libraries in `dependencies` instead of `devDependencies` | `package.json:33-38` |
| INC-1 | ui | Placement test UI not implemented (Phase 3 dependency) | — |
| INC-2 | ui | First-login guard not implemented | `App.jsx` |
| INC-3 | ui | `/vocabulary` route removed but no redirect or 404 route added | `App.jsx:32-36` |
| INC-4 | vocab-api | `POST /vocabulary` and `DELETE /vocabulary/{word}` endpoints still exist (planned for removal in Phase 6) | `daily_dragon_app.py:106,129` |

---

## 4. Prioritised Gap List

### P0 — Launch Blockers (fix before any real traffic)

| # | Task | Repo | Refs |
|---|---|---|---|
| 1 | **Rotate OpenAI API key** and add `.env` to all three `.gitignore` files | openai-api | B-2, SEC-O1 |
| 2 | **Fix HSK promotion math** — compute mastery ratio against seeded count, not full level size | vocab-api | B-1, DATA-1 |
| 3 | **Set Lambda timeout** for `openai-api` to ≥60 s | openai-api | B-3, INFRA-O2 |
| 4 | **Set OpenAI client timeout** (`OpenAI(timeout=30)`) and add `try/except` around `send_prompt` with mapped HTTP status codes | openai-api | B-4, RES-5, ERR-O1 |
| 5 | **Add logging** to `openai-api` — at minimum: request params, token usage, errors | openai-api | B-5, LOG-O1, LOG-O2 |
| 6 | **Fix `PracticePage` error state** — catch API failures, show error message, reset spinner | ui | B-6, ERR-U1 |
| 7 | **Fix double-encoded JSON** — return a proper object from `send_prompt` or set correct `response_model` on endpoint | openai-api | B-7, TEST-O4 |

### P1 — High-priority (fix within first week after launch)

| # | Task | Repo | Refs |
|---|---|---|---|
| 8 | Add `try/except` to `save_vocabulary` / `save_settings` with logging and clean HTTP error responses | vocab-api | ERR-V1 |
| 9 | Guard `session.tokens?.idToken?.toString()` — add null check and proper auth error throw | ui | SEC-U3, ERR-U5 |
| 10 | Move `OPENAI_API_KEY`, `S3_BUCKET`, Cognito config to Lambda environment variables (not bundled `.env` files) | both APIs | INFRA-V2, INFRA-O3 |
| 11 | Add `max_tokens` cap to OpenAI calls and log `response.usage` per request | openai-api | PERF-5, LOG-O2 |
| 12 | Add `hsk_level` constraint `ge=1, le=7` to `SettingsUpdateRequest` | vocab-api | DATA-3 |
| 13 | Fix broken test assertion (`save_vocab` → `save_vocabulary`) and add endpoint test for 404 on delete | vocab-api | TEST-V3 |
| 14 | Fix service test mocks in `openai-api` — patch `pathlib.Path.read_text` not `builtins.open`; add assertions to endpoint tests | openai-api | TEST-O1, TEST-O2 |
| 15 | Add empty-state handling to `PracticePage` when no words are due | ui | UX-02 |
| 16 | Fix `doSubmit` error handling — show toast/error on `submitTranslations` or `submitReviews` failure | ui | ERR-U2 |
| 17 | Pin all dependencies in `requirements.txt` (both API repos) | both APIs | CFG-10 |
| 18 | Update GitHub Actions to `checkout@v4` and replace `jakejarvis/s3-sync-action` with OIDC-based `aws-actions/configure-aws-credentials` + `aws s3 sync` | ui | INFRA-U1, INFRA-U2 |
| 19 | Add `--cache-control` to S3 sync: hashed assets `max-age=31536000,immutable`; `index.html` `no-cache` | ui | INFRA-U3 |
| 20 | Validate and coerce `ev.score` to a number in `aiService.js` before building review data | ui | UX-03 |

### P2 — Medium-priority (fix within first month)

| # | Task | Repo | Refs |
|---|---|---|---|
| 21 | Add request/response logging middleware to `vocabulary-api` (user ID, method, path, latency, status) | vocab-api | LOG-V2 |
| 22 | Switch to JSON structured logging in both API Lambdas | both APIs | LOG-V1 |
| 23 | Add auth tests — verify 401 on missing/invalid token for each protected endpoint | vocab-api | TEST-V2 |
| 24 | Add tests for `ReviewPage`, `renderSentence`, `auth.js`, `App.jsx` | ui | TEST-U2, TEST-U3, TEST-U4, TEST-U1 |
| 25 | Cache HSK word list files in Lambda module-level dict (they are static, never change at runtime) | vocab-api | PERF-4 |
| 26 | Reduce S3 calls in `get_due_words` — pass vocabulary through seeding call rather than re-fetching | vocab-api | PERF-2 |
| 27 | Add 404 catch-all route and `/vocabulary` redirect in `App.jsx` | ui | UX-04, UX-05, INC-3 |
| 28 | Add `max_length` to `WordEntry.word` and `max_length` to `BatchReviewRequest.reviews` | vocab-api | SEC-V4, SEC-V5 |
| 29 | Wrap `check_and_promote` in its own `try/except` in the reviews endpoint so a promotion failure does not fail the review response | vocab-api | ERR-V4 |
| 30 | Add `response_model` to `GET /vocabulary`, `/vocabulary/due`, `POST /vocabulary/reviews` | vocab-api | ERR-V5 |
| 31 | Move `MODEL_NAME`, `TARGET_LANGUAGE`, Cognito config to environment variables | openai-api | CFG-6, CFG-7, SEC-O2 |
| 32 | Add retry with backoff on `openai.RateLimitError` and `openai.APIConnectionError` | openai-api | RES-6 |
| 33 | Validate `token_use == "id"` in Cognito auth | vocab-api | SEC-V1 |
| 34 | Scope CI IAM policy to specific resource ARNs; remove `Resource: *` | vocab-api | SEC-V8 |
| 35 | Move test libraries from `dependencies` to `devDependencies`; remove `react-hook-form`; register `eslint-plugin-react-hooks` | ui | DEAD-14, DEP-02, TEST-U6 |
| 36 | Remove unused `prompts.js`, empty vocabulary test directory | ui | DEAD-9, DEAD-10 |
| 37 | Enforce coverage threshold in CI (`--cov-fail-under=80` in pytest command) | vocab-api | TEST-V1 |
| 38 | Fix `pytest.ini` `testpaths` in `openai-api` to point to `openai_api/tests/` | openai-api | TEST-O6 |

### P3 — Low-priority / quality improvements

| # | Task | Repo | Refs |
|---|---|---|---|
| 39 | Make `SEED_BATCH_SIZE`, `PROMOTION_THRESHOLD`, `DUE_WORDS_LIMIT` configurable via env var | vocab-api | CFG-5 |
| 40 | Remove redundant `@app.options("/vocabulary")` handler (CORSMiddleware handles it) | vocab-api | DEAD-1 |
| 41 | Make CORS allowed origins environment-driven; remove `localhost` from production list | both APIs | SEC-V6, SEC-O5 |
| 42 | Create a SAM template or minimal CDK stack for `openai-api` Lambda — document timeout, memory, env vars | openai-api | INFRA-O1 |
| 43 | Add `Lambda memory` and `timeout` to `vocabulary-api` CDK stack | vocab-api | INFRA-V1 |
| 44 | Self-host Inter font or replace with `system-ui` fallback | ui | PERF-9 |
| 45 | Add `aria-label` to translation inputs; add `role="list"` to sentence items | ui | UX-07, UX-08 |
| 46 | Move `aws-exports.js` and API URL to `VITE_` env vars built at CI time | ui | SEC-U1, SEC-U2 |
| 47 | Add CloudFront response-headers policy for `X-Frame-Options`, `X-Content-Type-Options`, CSP | ui | SEC-U4, SEC-U5 |
| 48 | Add temperature/seed parameters to OpenAI call for reproducibility | openai-api | CFG-9 |
| 49 | Remove `S3_FILE_PATH` from `.env`; add `pydantic-settings` explicitly to `requirements.txt` | vocab-api | CFG-4, DEAD-4 |
| 50 | Add `score: int = Field(ge=0, le=10)` to `TranslationEvaluationItem` | openai-api | TEST-O5 |
| 51 | Add `boto3.client` as module-level singleton instead of per-request instantiation | vocab-api | RES-3 |
| 52 | Reduce `GET /hsk/progress` from 8 sequential S3 GETs — read vocabulary once and filter per level in memory | vocab-api | PERF-3 |
| 53 | Replace `--maxfail=1` in `pytest.ini` with no limit so full test suite runs in CI | vocab-api | TEST-V6 |