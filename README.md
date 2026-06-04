# 🐩 Daily Dragon

**Daily Dragon** is a language-learning platform focused on daily translation practice.

Instead of fixed exercises, it **dynamically generates sentences for translation** based on a user's personal vocabulary -- preventing memorization and encouraging real language production.

A dedicated **Learn page** also lets users study due words -- seeing hanzi, pinyin, English meaning, and an example sentence -- before entering practice, so users are never dropped cold into translation.

---

## Problem it solves

Most language apps reuse the same examples, which users quickly memorize. Daily Dragon:

- generates new sentences every time using AI
- reuses known words in fresh combinations
- checks user translations and provides feedback
- supports a dedicated **Learn** step to study due words before practice
- supports short, focused daily practice sessions

The focus is **active translation**, not passive recognition.

---

## System Architecture

```
                        +------------------------------------------+
                        |              Amazon CloudFront           |
                        |         (single distribution)            |
                        +------------+--------------+-------------+
                                     |              |
                  /index.html |              | /api/*
                  (UI assets) |              | (API requests)
                              |              |
                              v              v
                     +-----------+   +------------------+
                     |    S3     |   |   API Gateway    |
                     |  (React   |   | (CloudFront-only |
                     |   SPA)    |   | resource policy) |
                     +-----------+   +--------+---------+
                                              |
                                     +---------+------------+
                                     |                      |
                                     v                      v
                         +-------------------+   +------------------+
                         |  Vocabulary API  |   |   OpenAI API     |
                         |  (AWS Lambda)    |   |  (AWS Lambda)    |
                         +--------+---------+   +--------+---------+
                                  |                      |
                                  v                      v
                            +----------+          +--------------+
                            |    S3    |          |  OpenAI API  |
                            | (vocab   |          |  (external)  |
                            |  store)  |          +--------------+
                            +----------+

                        +------------------------------------------+
                        |           Amazon Cognito                  |
                        |  (User Pools -- auth for all API calls)  |
                        +-------------------------------------------+
```

### Key architectural decisions

- **CloudFront as single entry point** -- one distribution serves both the React SPA (from S3) and routes `/api/*` traffic to API Gateway. No CORS headaches, clean URLs.
- **CloudFront-only resource policy on API Gateway** -- API Gateway rejects any request not originating from CloudFront. No direct API exposure.
- **Cognito for auth** -- JWT tokens issued by Cognito User Pools are validated at the API Gateway level before any Lambda is invoked.
- **Lambda per service** -- each API is independently deployable, no shared runtime.

---

## Repositories

| Repo | Purpose | Stack |
|---|---|---|
| [`daily-dragon`](https://github.com/daily-dragon/daily-dragon) | Architecture, diagrams, root docs | -- |
| [`daily-dragon-ui`](https://github.com/daily-dragon/daily-dragon-ui) | React SPA served via CloudFront → S3 | React, Amazon Cognito |
| [`daily-dragon-vocabulary-api`](https://github.com/daily-dragon/daily-dragon-vocabulary-api) | Manage user vocabulary (CRUD) | Python, FastAPI, AWS Lambda, API Gateway, S3 |
| [`daily-dragon-openai-api`](https://github.com/daily-dragon/daily-dragon-openai-api) | Generate sentences, check translations, fetch word detail for Learn page | Python, FastAPI, AWS Lambda, API Gateway, OpenAI APE|

---

## Services

### UI

The user-facing React SPA. Handles authentication via Cognito and communicates with all APIs through CloudFront. Includes a dedicated **Learn page** that presents due words in a study carousel (hanzi, pinyin, English meaning, example sentence) before each practice session.

&#10132; [`daily-dragon-ui`](https://github.com/daily-dragon/daily-dragon-ui)

### Vocabulary API

Manages a user's personal vocabulary list. Words stored per user in S3.

&#10132; [`daily-dragon-vocabulary-api`](https://github.com/daily-dragon/daily-dragon-vocabulary-api)

### OpenAI API

The AI core of the platform. Given a user's vocabulary, generates novel sentences for translation practice. Also accepts user translation attempts and returns feedback. Additionally, powers the **Learn page** by returning structured word detail (hanzi, pinyin, English meaning, example sentence) for any requested vocabulary word via `GET /word-detail`.

&#10132; [`daily-dragon-openai-api`](https://github.com/daily-dragon/daily-dragon-openai-api)

---

## Auth Flow

```
User → CloudFront → UI (S3)
         |
         |--> Cognito (sign in / sign up)
                    |
                    |--> JWT token issued
                              |
                              v
              User request + JWT -> CloudFront -> API GatKay
                                                    |
                                           Cognito authorizer
                                           validates token
                                                    |
                                                    v
                                            Lambda handler
```

---

## Infrastructure

All infrastructure is managed per-service. Each Lambda-backed API is deployed independently.

- **Runtime:** Python 3.x (Lambda)
- **Framework:** FastAPI (via Mangum adapter for Lambda)
- **Auth:** Amazon Cognito User Pools + API Gateway authorizer
- **Storage:** S3 (vocabulary data, UI assets)
- **CDN / routing:** CloudFront

---

## Local Development

Each service has its own setup instructions. See the README in each repository.

For the UI:
```bash
git clone https://github.com/daily-dragon/daily-dragon-ui
cd daily-dragon-ui
npm install
npm start
```

For APIs (example):
```bash
git clone https://github.com/daily-dragon/daily-dragon-vocabulary-api
cd daily-dragon-vocabulary-api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Diagrams

Architecture diagrams are maintained in the [`/diagrams`](./diagrams) directory of this repo.

---

## Roadmap

- [x] **Learn page** -- a pre-practice study carousel that shows each due word with its hanzi, pinyin, English meaning, and an AI-generated example sentence before translation practice begins
- [ ] **Hints system** -- a "?" button next to each sentence that reveals a contextual hint (e.g. *"uses the word for 'to run'"*) rather than giving away the answer directly
- [ ] **Sentence type variety** -- intentionally vary generated sentences across questions, negations, past/future tense, and other structures to broaden grammar practice
- [ ] **Usage analytics & admin view** -- a page showing vocabulary grouped by user knowledge level, session frequency, and accuracy trends over time
- [ ] **Progress tracking & streaks** -- daily streak counter, session history, and words-mastered count to support habit formation
- [ ] **Migrate vocabulary storage to a database** -- replace per-user S3 files with a proper DB (e.g. DynamoDB) to enable querying, spaced repetition, and user settings storage
- Y[] ] **Multi-language support** -- allow users to practice translation into languages other than their first; mainly a vocabulary API and prompt concern
