# 🐉 Daily Dragon

**Daily Dragon** is a language-learning platform focused on daily translation practice.

Instead of fixed exercises, it **dynamically generates sentences for translation** based on a user's personal vocabulary — preventing memorization and encouraging real language production.

---

## Problem it solves

Most language apps reuse the same examples, which users quickly memorize. Daily Dragon:

- generates new sentences every time using AI
- reuses known words in fresh combinations
- checks user translations and provides feedback
- supports short, focused daily practice sessions

The focus is **active translation**, not passive recognition.

---

## System Architecture

```
                        ┌─────────────────────────────────────────┐
                        │              Amazon CloudFront           │
                        │         (single distribution)           │
                        └────────────┬──────────────┬─────────────┘
                                     │              │
                          /index.html │              │ /api/*
                          (UI assets) │              │ (API requests)
                                     ▼              ▼
                             ┌───────────┐   ┌──────────────────┐
                             │    S3     │   │   API Gateway    │
                             │  (React   │   │ (CloudFront-only │
                             │   SPA)    │   │ resource policy) │
                             └───────────┘   └────────┬─────────┘
                                                      │
                                          ┌───────────┴────────────┐
                                          │                        │
                                          ▼                        ▼
                                 ┌─────────────────┐   ┌─────────────────┐
                                 │  Vocabulary API  │   │   OpenAI API    │
                                 │  (AWS Lambda)    │   │  (AWS Lambda)   │
                                 └────────┬─────────┘   └────────┬────────┘
                                          │                      │
                                          ▼                      ▼
                                    ┌──────────┐          ┌──────────────┐
                                    │    S3    │          │  OpenAI API  │
                                    │ (vocab   │          │  (external)  │
                                    │  store)  │          └──────────────┘
                                    └──────────┘

                        ┌─────────────────────────────────────────┐
                        │           Amazon Cognito                 │
                        │  (User Pools — auth for all API calls)  │
                        └─────────────────────────────────────────┘
```

### Key architectural decisions

- **CloudFront as single entry point** — one distribution serves both the React SPA (from S3) and routes `/api/*` traffic to API Gateway. No CORS headaches, clean URLs.
- **CloudFront-only resource policy on API Gateway** — API Gateway rejects any request not originating from CloudFront. No direct API exposure.
- **Cognito for auth** — JWT tokens issued by Cognito User Pools are validated at the API Gateway level before any Lambda is invoked.
- **Lambda per service** — each API is independently deployable, no shared runtime.

---

## Repositories

| Repo | Purpose | Stack |
|---|---|---|
| [`daily-dragon`](https://github.com/daily-dragon/daily-dragon) | Architecture, diagrams, root docs | — |
| [`daily-dragon-ui`](https://github.com/daily-dragon/daily-dragon-ui) | React SPA served via CloudFront → S3 | React, Amazon Cognito |
| [`daily-dragon-vocabulary-api`](https://github.com/daily-dragon/daily-dragon-vocabulary-api) | Manage user vocabulary (CRUD) | Python, FastAPI, AWS Lambda, API Gateway, S3 |
| [`daily-dragon-openai-api`](https://github.com/daily-dragon/daily-dragon-openai-api) | Generate sentences, check translations | Python, FastAPI, AWS Lambda, API Gateway, OpenAI API |

---

## Services

### UI

The user-facing React SPA. Handles authentication via Cognito and communicates with all APIs through CloudFront.

→ [`daily-dragon-ui`](https://github.com/daily-dragon/daily-dragon-ui)

### Vocabulary API

Manages a user's personal vocabulary list. Words stored per user in S3.

→ [`daily-dragon-vocabulary-api`](https://github.com/daily-dragon/daily-dragon-vocabulary-api)

### OpenAI API

The AI core of the platform. Given a user's vocabulary, generates novel sentences for translation practice. Also accepts user translation attempts and returns feedback.

→ [`daily-dragon-openai-api`](https://github.com/daily-dragon/daily-dragon-openai-api)

---

## Auth Flow

```
User → CloudFront → UI (S3)
         │
         └──► Cognito (sign in / sign up)
                    │
                    └──► JWT token issued
                              │
                              ▼
              User request + JWT → CloudFront → API Gateway
                                                    │
                                              Cognito authorizer
                                              validates token
                                                    │
                                                    ▼
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

- [ ] Spaced repetition scheduling
- [ ] Multi-language support
- [ ] Progress tracking & streaks