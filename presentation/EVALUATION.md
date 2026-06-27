# Qaarib Project Evaluation

## One-line summary

Qaarib is a Fanar-powered Qatar-local agent that understands what the user wants to do in Qatar, clarifies missing details, grounds the request in real places/events/services, and turns it into an actionable result through tools, memory, and widgets.

## Core idea

Qaarib is built around the idea that a useful Qatar assistant should not behave like a generic chatbot. It should understand local places, transit patterns, cultural context, and everyday convenience needs, then convert a natural user request into an actionable result.

Instead of only producing paragraphs, Qaarib combines Fanar-based language generation with tool use: local route planning, place lookup, web search, web scraping, time/calendar handling, location grounding, and frontend widgets. This makes the assistant more practical for common Qatar scenarios such as moving through Education City, reaching HIA, finding venues in Msheireb, checking nearby services, or planning around local events.

## What is agentic about Qaarib?

Qaarib is agentic because it does more than answer a single prompt. It can interpret the user’s goal, preserve conversation state, choose tools, call those tools, and format the result into an action-ready answer.

### Multi-turn clarification before acting

Qaarib is designed to ask for missing details instead of hallucinating when a task is underspecified. Examples include missing starting location, unclear destination, unknown live timing, or a vague request such as planning an evening.

### Intent classification

The backend classifies whether the user is asking for routing, places, web search, scraping, calendar/time handling, location resolution, or general conversation. The user does not need to manually choose a category.

### Task decomposition

A request like “plan my evening” can be decomposed into sub-tasks: identify preferences, find an event or place, ground the location, check route options, and prepare a calendar/event action if requested.

### Persistent memory across a session

Qaarib stores conversation history and uses it for follow-ups. For example, if the user says they are in Msheireb and later asks “how do I get there from here?”, the system can use the latest explicit location instead of treating the prompt as isolated.

### Tool orchestration

Qaarib can call multiple tools depending on the task: route planning, place lookup, web search, web scraping, calendar creation, time parsing, or location resolution. This turns Fanar from a text generator into the reasoning and language layer inside a broader assistant workflow.

### Autonomous action support

The project supports action-style outputs such as calendar/event creation through an importable `.ics` file and widget-ready route/place outputs. Full silent calendar write depends on the available OAuth configuration and user permission, but the product direction is clear: the user should not need to leave the conversation to act.

## Evaluate and advance Fanar

One judging goal is to show not only what we built with Fanar, but what we learned about Fanar’s strengths, limits, and future opportunities.

### Tasks Fanar handles effectively

- Natural language response generation in English and Arabic-flavoured Qatar contexts
- Rewriting tool results into concise user-facing answers
- Understanding broad user goals when prompts are conversational rather than structured
- Producing friendly assistant language around Qatar-local services
- Helping with general conversation and clarification when the tool path is not needed

### Situations requiring external tools or connectors

- Real or current events need web/search/scraper tools
- Real place grounding needs Maps/Places/location tools
- Route planning needs a transit graph or routing provider rather than model memory
- Calendar actions need calendar connectors or `.ics` generation
- Live timing, closures, disruption, or availability should not rely on model memory
- Current user location needs frontend geolocation or explicit user input

### Limitations encountered during development

- Model-only answers can hallucinate local transit facts, especially after the user corrects the assistant
- Fanar API latency can spike under shared hackathon load
- Large model routing can be too slow for a live judging demo
- Session memory must be carefully structured or stale route context can poison later answers
- Qatar-specific location grounding is not fully solved by the model alone
- Widget payloads need explicit schemas; free text is not enough for a polished assistant UI

### Opportunities for improving future Fanar capabilities

- Built-in tool/function calling for Fanar models
- Native multi-turn memory primitives
- Better Qatar-specific location and transit grounding
- Stronger Arabic dialect handling for Gulf/Qatari user intent
- Built-in evaluation traces showing which tasks Fanar solved vs which required tools
- Official connectors for calendar, maps, events, and Qatar services
- Faster small-model routing options optimized for agentic workflows

## Strengths

### 1. Qatar-first product focus

Qaarib is scoped around Qatar rather than being a broad generic assistant. It includes project logic for Doha Metro, Lusail Tram, Education City, Msheireb, HIA, QCRI/HBKU, Souq Waqif, and other local contexts. This makes the product easier to judge as a real local assistant rather than a standard wrapper around an LLM.

### 2. Fanar integration

Fanar is used as the main language layer for Qaarib. The backend uses Fanar for response generation and can also use model-based routing when enabled. The project therefore demonstrates a practical agentic workflow around Fanar rather than just a single prompt-response interface.

### 3. Agentic tool workflow

Qaarib separates user intent from final response generation. Depending on the prompt, it can call route planning, place lookup, web search, scraper, time/calendar, or local resolver tools. This allows the assistant to answer with concrete data and actions rather than relying only on model memory.

### 4. Local deterministic reliability layer

The project includes deterministic local rules for high-confidence cases such as greetings, route requests, known Qatar transit facts, and follow-up location context. This improves latency and resilience during model/API load, and prevents obvious tasks from depending on a slow model response.

### 5. Context-aware follow-ups

Qaarib keeps session history and uses it to resolve follow-up prompts such as “from here”, “give me directions”, or “what is nearby?”. The backend includes a route context guard to reduce stale-context mistakes and prefer the latest explicit user location.

### 6. Widget-oriented frontend direction

The frontend direction is not just chat bubbles. Qaarib is designed to surface visual cards/widgets for route guidance, places, maps, and actionable next steps. This makes the product feel closer to a local concierge or assistant layer than a plain LLM chat.

### 7. Graceful degradation under load

During shared API load, Qaarib can avoid unnecessary heavy model calls, switch to smaller Fanar models, use deterministic tool answers, and present high-load states cleanly. This is important for hackathon judging because it keeps the user experience from collapsing when model latency spikes.

### 8. Evaluation harness

The backend includes an evaluation workflow for testing prompts, comparing outputs, and scoring behavior. This helped the team identify weak cases such as route hallucinations, stale context, local transit errors, and overly generic assistant voice.

## Technical innovation

### Qatar-specific location grounding

Qaarib includes Qatar-specific location aliases, transit knowledge, and route context repair logic. This is important because current general-purpose model behavior is not enough for reliable Qatar-local navigation.

### Reusable connector layer

The project includes a reusable connector/tool layer for search, places, route planning, scraping, location resolution, time parsing, and calendar output. This makes Qaarib extensible beyond the current demo.

### Multi-turn state management

Qaarib adds session memory and follow-up resolution on top of a stateless model API. This allows it to remember user constraints and locations within the conversation.

### Presentation-ready resilience

The system includes runtime strategies for high-load conditions: deterministic pre-router answers, smaller Fanar model fallbacks, shorter timeouts, and preserved local tool outputs.

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
- fully autonomous external actions require user permission and connector authentication

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
- build first-class Fanar tool-calling patterns from this prototype

## Overall evaluation

Qaarib is strongest as a Qatar-specific agentic assistant prototype. Its value is not just that it uses Fanar, but that it places Fanar inside a practical workflow: local intent detection, tools, session memory, route/place context, and frontend widgets. The result is a product direction that feels useful for daily life in Qatar and clearly different from a generic chatbot.

For Fanar, the project is also useful as feedback: it shows where Fanar already works well as a language and reasoning layer, where external tools are still required, and what capabilities would make future Fanar-powered agents stronger.
