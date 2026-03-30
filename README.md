# Daily Dragon

**Daily Dragon** is a language-learning project focused on daily translation practice.

Instead of fixed exercises, it **dynamically generates sentences for translation** based on a user’s personal vocabulary.  
This prevents memorization and encourages real language production.

---

## Problem it solves

Problem: Most language apps reuse the same examples, which users quickly memorize.

Daily Dragon:
- generates new sentences every time
- reuses known words in new combinations
- supports short, daily practice sessions

The focus is **active translation**, not passive recognition.

---

## UI

**Repository:** [https://github.com/daily-dragon/daily-dragon-ui](https://github.com/daily-dragon/daily-dragon-ui)

The actual user-facing website that allows to work with the APIs.

Technology stack:
- React
- AWS Amplify
- Amazon Cognito

---

## Vocabulary API

**Repository:** [https://github.com/daily-dragon/daily-dragon-vocabulary-api](https://github.com/daily-dragon/daily-dragon-vocabulary-api)

Responsible for:
- working with user's vocabulary

Technology stack:
- AWS Lambda
- API Gateway
- S3
- Python
- FastAPI

---

## OpenAI API

**Repository:** [https://github.com/daily-dragon/daily-dragon-openai-api](https://github.com/daily-dragon/daily-dragon-openai-api)

Responsible for:
- generating sentences for translation
- checking user translations

Technology stack:
- AWS Lambda
- API Gateway
- FastAPI
- OpenAI API
