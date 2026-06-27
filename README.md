# Qaarib

Qaarib is a Fanar-powered Qatar companion that turns everyday local needs — routes, places, events, culture, and services — into actionable answers with tools, context, and visual widgets.

Built for the Fanar Hackathon 2026, Qaarib explores how a Qatar-aware assistant can go beyond generic chatbot answers. It combines Fanar LLMs with local routing rules, lookup tools, Qatar transit knowledge, session memory, and a widget-oriented frontend layer so users can ask naturally and receive practical next steps.

## Why Qaarib

Generic assistants can answer broad questions, but they often struggle with local details: which metro line to take, how a follow-up connects to the previous request, whether a place is in Education City or elsewhere in Doha, and how to turn a recommendation into action.

Qaarib focuses on Qatar-specific convenience:

* navigating Doha Metro, Lusail Tram, Education City, Msheireb, HIA, and common local destinations
* finding nearby cafés, qahwa, restaurants, cultural venues, and service points
* surfacing events, activities, and local context in a way that fits Qatar's culture and daily life
* combining map links, cards, and concise instructions instead of returning only paragraphs
* keeping enough session context to handle follow-ups like "give me directions" or "what is nearby?"

## Where Fanar is used

Fanar is used as Qaarib's language layer. The backend calls Fanar for response generation and, when enabled, intent routing. During high-load conditions, Qaarib can reduce unnecessary model calls by using deterministic local routing for obvious tool requests, then calling Fanar only when language generation is needed.

Relevant files:

```txt
backend/fanar_client.py
backend/router.py
backend/server.py
backend/app.py
backend/chat_session.py
```

## Core capabilities

* Fanar API integration
* Fanar-based and local intent routing paths
* Google Places lookup
* Google Routes lookup
* web search integration
* local Qatar transit topology under `backend/data/`
* session history tracking
* response formatting for route/place/tool answers
* evaluation harness under `backend/evaluation/`
* synchronized presentation runtime under `demo_fallback/`

## Qatar transit awareness

Qaarib includes a local transit topology file:

```txt
backend/data/qatar_transit_network.json
```

This improves awareness of Doha Metro Red, Green, and Gold lines; Msheireb and Al Bidda interchanges; the HIA T1 airport branch; Education City/QNL/Al Shaqab access; Lusail Tram links; and local tram contexts.

This data is not a live schedule source. Live timings, disruptions, pricing, access changes, or official announcements should still be checked through live and official sources.

## Setup

Create a local environment file:

```bash
cp backend/.env.example backend/.env
```

Fill in the required keys:

```env
FANAR_API_KEY=...
FANAR_ROUTER_MODEL=Fanar-C-1-8.7B
FANAR_RESPONDER_MODEL=Fanar-C-1-8.7B
FANAR_BACKUP_MODEL=Fanar-C-1-8.7B
FANAR_ALLOW_BIG_MODELS=0
QAARIB_USE_FANAR_ROUTER=0

GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...

GEMINI_API_KEY=...
GEMINI_JUDGE_MODEL=gemini-3.5-flash
```

Install requirements:

```bash
cd backend
python -m pip install -r requirements.txt
```

Run the Flask backend used by the frontend:

```bash
python server.py
```

Run the CLI backend:

```bash
python app.py
```

## Evaluation

```bash
cd backend
python evaluation/run_eval.py
```

Evaluation outputs are written to `backend/evaluation/outputs/` and ignored by Git.

## Presentation runtime

The `demo_fallback/` folder contains a synchronized browser-and-terminal runtime view for presenting Qaarib's internal flow: local intent detection, Fanar model selection, route/tool planning, widget preparation, and graceful handling of high server load.

```bash
python demo_fallback/run_synced_demo.py
```

The launcher asks for the scenario, interval, and loop setting, then opens the browser view and terminal trace on the same timer.

## Example scenarios

* finding nearby qahwa / dates / café options around Msheireb
* correcting vague follow-up questions like "give me directions"
* routing through Qatar's metro/tram network
* handling HIA / Ras Bu Aboud / Lusail / Education City transit scenarios
* helping users discover cultural venues, events, and local activities
* avoiding overconfident answers when a tool does not confirm prices, menus, or facilities

## Disclaimer

Qaarib is a hackathon prototype. It demonstrates how Fanar can power a Qatar-aware assistant, but live schedules, official policies, service availability, and venue details should still be verified through authoritative sources before real-world use.
