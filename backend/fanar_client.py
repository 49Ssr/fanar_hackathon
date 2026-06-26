import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR=Path(__file__).resolve().parent
load_dotenv(BASE_DIR/".env")
load_dotenv()

API_KEY=os.getenv("FANAR_API_KEY")


def ask_fanar(prompt:str,model:str,max_tokens=700):
    if not API_KEY:
        raise RuntimeError("FANAR_API_KEY is missing. Put it in backend/.env")

    headers={
        "Authorization":f"Bearer {API_KEY}",
        "Content-Type":"application/json",
    }

    payload={
        "model":model,
        "messages":[{"role":"user","content":prompt}],
        "max_tokens":max_tokens,
    }

    response=requests.post(
        "https://api.fanar.qa/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()
    data=response.json()
    return data["choices"][0]["message"]["content"]


def ask_fanar_timed(prompt:str,model:str,max_tokens=700):
    start=time.perf_counter()
    response=ask_fanar(prompt,model,max_tokens)
    elapsed_ms=round((time.perf_counter()-start)*1000,2)
    return response,elapsed_ms
