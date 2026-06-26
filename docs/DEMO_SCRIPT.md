# Qaarib Demo Script - stable path

Goal: show Qaarib as a Qatar-native agentic assistant, not a generic chatbot.

## Demo beats

### 1. No-tool personality check
Prompt:
`salam alikum`

Expected:
- No tools.
- Friendly short greeting.
- No generic tourist dump.

### 2. Nearby recommendation with place tool
Prompt:
`im in msheireb, any spot nearby for some highly rated qahwa and dates?`

Expected:
- place_lookup, maybe web_search.
- Search query should include venue type + Msheireb, not just `Msheireb`.
- Response recommends from actual returned places only.

### 3. Context follow-up
Prompt:
`which place do you recommend for budget friendliness`

Expected:
- Stays anchored to qahwa/dates near Msheireb.
- Does not drift into generic budget things in Doha.

### 4. Route planning
Prompt:
`how do i get from qcri to education city metro without melting outside?`

Expected:
- route_plan + web_search.
- Gives walking route distance/duration/map.
- Mentions covered/indoor route as a heads-up unless confirmed by source.

## Pitch line
Qaarib is a Qatar-focused agentic assistant that combines Fanar with local tools for places, routes, and live Qatar information. The key value is not just answering: it remembers context, chooses tools, grounds responses in local sources, and behaves like a practical Qatar companion.

## Do not demo
- Random global knowledge questions.
- Long multi-hop legal/religious questions unless already tested.
- Anything requiring guaranteed live opening hours unless Places returns it.
- Voice/image unless integrated and rehearsed.
