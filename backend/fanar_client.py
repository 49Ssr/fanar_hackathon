import os
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("FANAR_API_KEY")
MODEL = os.getenv("FANAR_MODEL", "Fanar-Sadiq")

def ask_fanar(prompt:str):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        }
    payload = {
        "model":MODEL,
        "messages":[{"role":"user","content":prompt}],
        "max_tokens":500
        }
    response = requests.post("https://api.fanar.qa/v1/chat/completions",json=payload,headers=headers,timeout=60)
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]