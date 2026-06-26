# Qaarib

Qaarib is a Qatar-focused assistant built for the Fanar Hackathon 2026.

The goal is to make local navigation, transport, places, and Qatar-specific service discovery feel more natural than a generic chatbot. Qaarib combines Fanar LLMs with tool-based lookup for routes, places, web search, and a local Qatar transit knowledge layer.

> **Status:** Work in progress. Features, prompts, routing rules, UI flow, and demo scenarios are still being finalised before the hackathon presentation.

## Core idea

Qaarib acts as a local companion for Qatar. Instead of only answering from model memory, it can route user requests through backend tools and return grounded answers for:

* nearby places and recommendations
* Doha Metro / tram-aware routing
* Education City navigation
* airport and transit questions
* Qatar-specific web/service lookups
* follow-up questions with session context

## Current backend features

The backend currently includes:

* Fanar API integration
* model-based router for tool selection
* local deterministic guardrails for fragile demo-critical cases
* Google Places lookup
* Google Routes lookup
* web search fallback
* session history tracking through `chat_history.md`
* Qatar transit network data under `backend/data/`
* evaluation harness under `backend/evaluation/`

## Qatar transit awareness

Qaarib includes a local transit topology file:

```txt
backend/data/qatar_transit_network.json
```

This is used to improve awareness of:

* Doha Metro Red, Green, and Gold lines
* Msheireb interchange
* Al Bidda interchange
* HIA T1 Red Line airport branch
* Al Wakra / Ras Bu Fontas branch context
* Education City / QNL / Al Shaqab Green Line access
* Lusail Tram connection through Legtaifiya
* Msheireb Tram as a local downtown loop
* Education City Tram as a campus network

This data is not a live schedule source. Live timings, access changes, disruptions, or official announcements should still be checked through live/official sources.

## Project structure

```txt
backend/
  app.py
  fanar_client.py
  router.py
  chat_session.py
  places_client.py
  route_client.py
  search_client.py
  data/
    qatar_transit_network.json
  rules/
    local_rules.py
  evaluation/
    run_eval.py
    eval_cases.jsonl
    gemini_judge.py
    fanar_client_eval.py
    scoring.py
```

## Setup

Create a local environment file:

```bash
cp backend/.env.example backend/.env
```

Fill in the required keys:

```env
FANAR_API_KEY=...
FANAR_ROUTER_MODEL=Fanar-C-2-27B
FANAR_RESPONDER_MODEL=Fanar

GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...

GEMINI_API_KEY=...
GEMINI_JUDGE_MODEL=gemini-3.5-flash

FANAR_EVAL_MODELS=Fanar,Fanar-C-1-8.7B,Fanar-C-2-27B
EVAL_TIME_LIMIT_MINUTES=60
```

Install requirements:

```bash
cd backend
python -m pip install -r requirements.txt
```

Run the backend:

```bash
python app.py
```

## Evaluation

The evaluation harness is separate from the main app runtime.

```bash
cd backend
python evaluation/run_eval.py
```

Evaluation outputs are written to:

```txt
backend/evaluation/outputs/
```

These outputs are ignored by Git.

## Demo direction

The intended demo is to show Qaarib handling realistic Qatar-local situations, for example:

* finding nearby qahwa / dates / café options around Msheireb
* correcting vague follow-up questions like “give me directions”
* routing through Qatar’s metro/tram network
* handling Al Wakra / HIA / Lusail / Education City transit scenarios
* avoiding overconfident answers when a tool does not confirm prices, menus, or facilities

## Important disclaimer

This repository is currently in active hackathon development.

Some behaviours may still change before the final demo, including:

* routing prompts
* local rule guardrails
* transit graph details
* evaluation cases
* frontend integration
* final demo script
* UI/UX flow

The current backend should be treated as a working prototype, not a polished production assistant.
