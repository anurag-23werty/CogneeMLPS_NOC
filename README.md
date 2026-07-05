# NOC Copilot — a network ops assistant that doesn't forget

Built for the Cognee memory hackathon. Cuts the AetherNOC (ISRO BAH 2026) concept
down to the one thing that matters for this theme: an agent that recalls
graph-connected incident history across sessions instead of diagnosing every
alert cold.

## The pitch

LLM agents are stateless. A NOC copilot that forgets last month's outage is
useless the second time the same router does the same thing. This wires
[Cognee](https://github.com/topoteretes/cognee) in as the memory layer for a
3-agent LangGraph pipeline:

1. **Ingest** — every incident, resolved or not, gets written into Cognee's
   permanent graph + vector memory.
2. **Recall** — a new incident triggers a graph-aware query (`GRAPH_COMPLETION_COT`)
   that pulls related history by shared entities (device, site, failure
   pattern), not just text similarity.
3. **Diagnose** — an LLM call grounded in the recalled history proposes a root
   cause and fix, then writes its own diagnosis back into memory. The loop
   closes: incident N+1 benefits from incident N.

## Demo script (30 seconds, this is the whole point)

1. Seed 6 historical incidents across 3 sites. One of them: `MPLS-RTR-07` at
   `DEL-CORE` had BGP flapping after a firmware upgrade, root cause was an
   MTU mismatch, fixed 3 weeks ago.
2. Submit a *new* incident: same router, same symptom, after another
   firmware patch.
3. Watch the agent recall INC-1003 unprompted and flag it as a likely repeat
   of the same failure mode, rather than re-deriving the diagnosis from
   scratch — and flag it as a runbook gap, not a one-off.

That's "no more amnesia" made concrete instead of asserted.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env: add your LLM_API_KEY (Mistral, or any litellm-supported provider)
```

Embeddings run locally via `fastembed` — no separate embedding API key needed.
Graph + vector storage are local (Cognee's embedded Kuzu + LanceDB defaults) —
no Docker, no external DB required for the demo.

## Run

Seed history, then either the UI or the API:

```bash
python scripts/seed_memory.py

# Option A: interactive demo UI
python -m app.ui

# Option B: API
uvicorn app.api:app --reload
# POST /incident with an Incident JSON body
```

Smoke test (no API key required, checks imports/schema/graph compile only):

```bash
python -m pytest tests/test_smoke.py -v
```

## Project layout

```
app/
  config.py           cognee provider/model setup
  schemas.py           Incident model
  memory.py             remember_incident / recall_related wrappers over cognee.remember/recall
  agents/graph.py       LangGraph: ingest -> recall -> diagnose
  data/seed_incidents.py  synthetic historical incidents + the "repeat failure" demo incident
  api.py                FastAPI endpoints
  ui.py                 Gradio demo UI
scripts/seed_memory.py  one-shot seeding script
tests/test_smoke.py     structural smoke test
```

## What got cut from the ISRO version, on purpose

Containerlab simulation, Kafka/InfluxDB telemetry pipeline, the TFT/GAT/
Isolation Forest ML ensemble, Grafana dashboard, offline Mistral 7B. All real
work, none of it provable in 12 hours solo, and none of it is what this
hackathon is judging. What's left is the memory story, built on the real
thing instead of asserted in a slide.

## Known gaps / what to do with remaining time

- Diagnosis quality depends entirely on the LLM you point `LLM_MODEL` at —
  test with your actual Mistral key before recording the demo, tune the
  prompt in `agents/graph.py` if the recall summary comes back too verbose.
- `recall_related` currently asks Cognee for `GRAPH_COMPLETION_COT`. If
  recall feels weak on your data, try `SearchType.TEMPORAL` (built for
  "when did this last happen" queries) or `GRAPH_COMPLETION_DECOMPOSITION`
  as an alternative and compare.
- No feedback loop into `cognee.improve()` yet — session Q&A -> permanent
  graph promotion is a real Cognee 1.x feature and would be a strong "bonus"
  addition if you have an extra hour: after a diagnosis, let the operator
  rate it, and feed the rating back so future recall weights toward what
  actually worked.
