# Daily Dragon

Mandarin language-learning platform with an HSK-structured curriculum. Words are seeded from New HSK (2021) levels 1-7 via SRS; the LLM generates translation sentences at the user's current level. Focus is active translation, not passive recognition. Manual vocabulary management has been removed.

## This repo

Docs and architecture only. No application code lives here.

- `README.md` — full project documentation
- `diagrams/` — architecture diagrams (Mermaid + draw.io)

## Sub-repos

| Repo | Stack |
|---|---|
| [`daily-dragon-ui`](https://github.com/daily-dragon/daily-dragon-ui) | React, Amazon Cognito |
| [`daily-dragon-vocabulary-api`](https://github.com/daily-dragon/daily-dragon-vocabulary-api) | Python, FastAPI, AWS Lambda, S3 |
| [`daily-dragon-openai-api`](https://github.com/daily-dragon/daily-dragon-openai-api) | Python, FastAPI, AWS Lambda, OpenAI API |
