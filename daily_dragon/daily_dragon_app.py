import logging
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from daily_dragon.auth.authenticate import authenticate
from daily_dragon.exceptions import WordAlreadyExistsError
from daily_dragon.service.vocabulary_service import VocabularyService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:5173"],
                   allow_credentials=True,
                   allow_methods=["GET", "POST", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type"]
                   )


class WordEntry(BaseModel):
    word: str = Field(max_length=256)


@app.post("/daily-dragon/vocabulary", status_code=201)
def add_word(word_entry: WordEntry, vocabulary_service: VocabularyService = Depends(),
             username: str = Depends(authenticate)):
    word = word_entry.word
    try:
        vocabulary_service.add_word(word_entry.word)
        return {"message": f"Word {word} added to vocabulary"}
    except WordAlreadyExistsError:
        raise HTTPException(status_code=409, detail=f"Word {word} already exists")


@app.get("/daily-dragon/vocabulary")
def get_vocabulary(vocabulary_service: VocabularyService = Depends(), username: str = Depends(authenticate),
                   count: Optional[int] = Query(None, gt=0)):
    if count is not None:
        vocabulary = vocabulary_service.get_random_vocabulary(count)
    else:
        vocabulary = vocabulary_service.get_vocabulary()
    return vocabulary


@app.delete("/daily-dragon/vocabulary/{word}")
def delete_word(word: str, vocabulary_service: VocabularyService = Depends(), username: str = Depends(authenticate)):
    vocabulary_service.delete_word(word)
    return {"message": f"Word {word} deleted"}


@app.options("/daily-dragon/vocabulary")
def options_vocabulary():
    return Response(status_code=200)
