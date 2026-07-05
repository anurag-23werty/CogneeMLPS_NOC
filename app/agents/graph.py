"""
Three-node LangGraph pipeline:

  ingest -> recall -> diagnose

ingest   writes the new incident into Cognee's permanent graph memory as it
         comes in (so it's available for recall on the *next* incident too).
recall   queries Cognee for graph-connected history relevant to this incident.
diagnose synthesizes a root cause + fix, explicitly grounded in what was
         recalled, then writes the diagnosis back into memory so the loop
         closes (next incident benefits from this one).
"""

from typing import TypedDict, Optional
import litellm

from app.config import LLM_MODEL, LLM_API_KEY
from app.memory import remember_incident, recall_related, record_diagnosis_qa
from app.schemas import Incident


class NOCState(TypedDict):
    incident: Incident
    recalled: list
    diagnosis: Optional[str]
    session_id: Optional[str]
    qa_id: Optional[str]


async def ingest_node(state: NOCState) -> NOCState:
    await remember_incident(state["incident"])
    return state


async def recall_node(state: NOCState) -> NOCState:
    session_id = state.get("session_id") or f"noc-session-{state['incident'].incident_id}"
    results = await recall_related(state["incident"], session_id=session_id)
    return {**state, "recalled": results, "session_id": session_id}


async def diagnose_node(state: NOCState) -> NOCState:
    incident = state["incident"]
    recalled = state.get("recalled", [])
    session_id = state["session_id"]
    recalled_text = "\n".join(str(r) for r in recalled) or "No related history found."

    prompt = f"""You are a NOC diagnosis assistant. A new incident has come in.

NEW INCIDENT
Device: {incident.device}
Site: {incident.site}
Symptom: {incident.symptom}
Telemetry: {incident.telemetry_snippet}
Severity: {incident.severity}

RELATED HISTORY FROM MEMORY
{recalled_text}

Give a short diagnosis: (1) most likely root cause, citing the specific past
incident if the history points to a repeat failure, (2) recommended fix,
(3) one line on whether this looks like a recurring pattern worth a permanent
runbook fix rather than a one-off patch. Be concise, no filler."""

    response = litellm.completion(
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        messages=[{"role": "user", "content": prompt}],
    )
    diagnosis = response["choices"][0]["message"]["content"]

    # Close the loop: this diagnosis becomes part of memory for future recall
    incident.root_cause = diagnosis
    await remember_incident(incident)

    # Store as a rateable QA turn so operator feedback can flow through
    # improve() later, rather than just writing raw text into memory.
    qa_id = await record_diagnosis_qa(
        question=f"Root cause and fix for {incident.device} at {incident.site}: {incident.symptom}",
        answer=diagnosis,
        context=recalled_text,
        session_id=session_id,
    )

    return {**state, "diagnosis": diagnosis, "qa_id": qa_id}


def build_graph():
    from langgraph.graph import StateGraph, END

    graph = StateGraph(NOCState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("recall", recall_node)
    graph.add_node("diagnose", diagnose_node)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "recall")
    graph.add_edge("recall", "diagnose")
    graph.add_edge("diagnose", END)

    return graph.compile()


async def run_incident(incident: Incident) -> NOCState:
    app = build_graph()
    result = await app.ainvoke({
        "incident": incident,
        "recalled": [],
        "diagnosis": None,
        "session_id": None,
        "qa_id": None,
    })
    return result
