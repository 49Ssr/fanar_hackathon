# Qaarib Project Evaluation

## One-line summary

Qaarib is a Fanar-powered Qatar-local assistant that turns routes, places, events, culture, and daily services into practical answers with tools, memory, and visual widgets.

## Core idea

Qaarib is built around the idea that a useful Qatar assistant should not behave like a generic chatbot. It should understand local places, transit patterns, cultural context, and everyday convenience needs, then convert a natural user request into an actionable result.

Instead of only producing paragraphs, Qaarib combines language generation with tool use: local route planning, place lookup, web search, time/calendar handling, and frontend widgets. This makes the assistant more practical for common Qatar scenarios such as moving through Education City, reaching HIA, finding venues in Msheireb, checking nearby services, or planning around local events.

## Strengths

### 1. Qatar-first product focus

Qaarib is scoped around Qatar rather than being a broad generic assistant. It includes project logic for Doha Metro, Lusail Tram, Education City, Msheireb, HIA, QCRI/HBKU, Souq Waqif, and other local contexts. This makes the product easier to judge as a real local assistant rather than a standard wrapper around an LLM.

### 2. Fanar integration

Fanar is used as the main language layer for Qaarib. The backend uses Fanar for response generation and can also use model-based routing when enabled. The project therefore demonstrates a practical agentic workflow around Fanar rather than just a single prompt-response interface.

### 3. Agentic tool workflow

Qaarib separates user intent from final response generation. Depending on the prompt, it can call route planning, place lookup, web search, scraper, time/calendar, or local resolver tools. This allows the assistant to answer with concrete data and actions rather than relying only on model memory.

### 4. Local deterministic fallbacks

The project includes deterministic local rules for high-confidence cases such as greetings, route requests, known Qatar transit facts, and follow-up location context. This improves latency and resilience during model/API load, and prevents obvious tasks from depending on a slow model response.

### 5. Context-aware follow-ups

Qaarib keeps session history and uses it to resolve follow-up prompts such as “from here”, “give me directions”, or “what is nearby?”. The backend includes a route context guard to reduce stale-context mistakes and prefer the latest explicit user location.

### 6. Widget-oriented frontend direction

The frontend direction is not just chat bubbles. Qaarib is designed to surface visual cards/widgets for route guidance, places, maps, and actionable next steps. This makes the product feel closer to a local concierge or assistant layer than a plain LLM chat.

### 7. Graceful degradation under load

During shared API load, Qaarib can avoid unnecessary heavy model calls, switch to smaller Fanar models, use deterministic tool answers, and present high-load states cleanly. This is important for hackathon judging because it keeps the user experience from collapsing when model latency spikes.

### 8. Evaluation harness

The backend includes an evaluation workflow for testing prompts, comparing outputs, and scoring behavior. This helped the team identify weak cases such as route hallucinations, stale context, local transit errors, and overly generic assistant voice.

## Technical architecture

At a high level, Qaarib follows this flow:

```text
User prompt
→ local pre-router checks
→ intent/router decision
→ tool calls when needed
→ route/place/web/time/calendar results
→ deterministic formatter or Fanar response generation
→ frontend chat/widgets
```

Important backend areas:

```text
backend/server.py              Flask API used by frontend
backend/app.py                 CLI/runtime orchestration and tool execution
backend/fanar_client.py        Fanar API client and model fallback chain
backend/router.py              routing prompt/parser
backend/rules/local_rules.py   local intent and query improvement rules
backend/route_client.py        route planning and transit graph handling
backend/route_context_guard.py follow-up route context repair
backend/places_client.py       place lookup
backend/search_client.py       web search
backend/chat_session.py        session memory and prompt assembly
backend/evaluation/            regression/evaluation tooling
```

## What makes it different

Many LLM assistants can answer “What should I do in Qatar?” in a generic way. Qaarib is designed to go further by turning the request into an action:

- identify the local intent
- remember the relevant context
- call a tool if needed
- produce a concise answer
- attach map/widget-ready output
- avoid overconfident answers when live data is missing

The project is especially strong when the user asks for something practical: routes, nearby places, Qatar-specific venue context, transport decisions, or quick local planning.

## Current limitations

Qaarib is still a hackathon prototype. Known limitations include:

- live transit timing is not fully integrated
- GPS/current-location access depends on the frontend passing location or the user stating it
- some route logic is deterministic and needs broader coverage
- widget integration is still evolving
- local Qatar knowledge needs continuous expansion and validation
- API load can still affect model-generated answers

## Future improvements

Strong next steps would be:

- add real frontend geolocation with user permission
- connect official/live transit APIs where available
- expand the Qatar transit and landmark knowledge base
- formalize a location-state resolver separate from chat history
- add stronger widget payload schemas
- add more regression tests for Qatar-specific prompts
- improve Arabic/English code-switching and Gulf Arabic tone
- evaluate Fanar model variants systematically for routing vs response generation

## Overall evaluation

Qaarib is strongest as a Qatar-specific agentic assistant prototype. Its value is not just that it uses Fanar, but that it places Fanar inside a practical workflow: local intent detection, tools, session memory, route/place context, and frontend widgets. The result is a product direction that feels useful for daily life in Qatar and clearly different from a generic chatbot.
