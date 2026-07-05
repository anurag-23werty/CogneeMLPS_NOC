"""
NOC-specific wrapper around Cognee's memory API.

Deliberately thin — Cognee already does the hard part (chunking, entity
extraction, graph construction, hybrid retrieval). This module pins the
dataset name and exposes all four lifecycle verbs the hackathon judging
rubric names explicitly: remember, recall, improve, forget.

    remember  -> remember_incident / bootstrap_history
    recall    -> recall_related
    improve   -> record_diagnosis_qa + rate_diagnosis (feedback loop)
    forget    -> forget_incident
"""

import cognee
from cognee import QAEntry, FeedbackEntry
from app.config import DATASET_NAME
from app.schemas import Incident

# Maps incident_id -> content_hash so a specific incident can be located and
# forgotten later. This is local bookkeeping only; the actual memory lives
# entirely in Cognee's graph + vector store, not here.
_incident_hashes: dict[str, str] = {}


async def remember_incident(incident: Incident) -> None:
    """Write a resolved (or in-progress) incident into permanent graph memory."""
    result = await cognee.remember(
        data=incident.to_memory_text(),
        dataset_name=DATASET_NAME,
        self_improvement=False,  # avoid a full-graph LLM pass on every single write;
                                  # we trigger improvement deliberately via rate_diagnosis()
    )
    if result.content_hash:
        _incident_hashes[incident.incident_id] = result.content_hash


async def recall_related(incident: Incident, top_k: int = 5, session_id: str | None = None) -> list[dict]:
    """
    Pull related history for a new incident.

    GRAPH_COMPLETION_COT walks the graph with a chain-of-thought pass rather
    than pure vector similarity, so it can surface a past incident connected
    via shared device/site/symptom nodes even if the wording differs.
    """
    query_text = (
        f"Past incidents related to device {incident.device} at site {incident.site} "
        f"with symptom: {incident.symptom}"
    )
    results = await cognee.recall(
        query_text=query_text,
        query_type=cognee.SearchType.GRAPH_COMPLETION_COT,
        datasets=[DATASET_NAME],
        session_id=session_id,
    )
    if isinstance(results, list):
        return results[:top_k]
    return [results]


async def bootstrap_history(incidents: list[Incident]) -> None:
    """Seed permanent memory with historical incidents before the demo starts."""
    for incident in incidents:
        await remember_incident(incident)


async def record_diagnosis_qa(question: str, answer: str, context: str, session_id: str) -> str | None:
    """
    Store a diagnosis as a session QA turn, not just a text blob.

    This is what makes the diagnosis rateable later: `improve()` needs a
    qa_id to attach feedback to, and a session_id to know which turns to
    fold back into the permanent graph.
    """
    result = await cognee.remember(
        data=QAEntry(question=question, answer=answer, context=context),
        session_id=session_id,
    )
    return result.entry_id


async def rate_diagnosis(session_id: str, qa_id: str, correct: bool, note: str = "") -> None:
    """
    Attach operator feedback to a diagnosis, then fold it into permanent
    memory via improve().

    improve() does two things here: (1) reweights the graph nodes/edges
    that produced this diagnosis based on the feedback score, so future
    recall favors what actually worked, and (2) persists this session's
    Q&A into permanent memory so the diagnosis itself becomes recallable
    context for the next incident.
    """
    await cognee.remember(
        data=FeedbackEntry(
            qa_id=qa_id,
            feedback_score=1 if correct else -1,
            feedback_text=note,
        ),
        session_id=session_id,
    )
    await cognee.improve(dataset=DATASET_NAME, session_ids=[session_id])


async def _resolve_dataset_id(dataset_name: str):
    all_datasets = await cognee.datasets.list_datasets()
    for ds in all_datasets:
        if getattr(ds, "name", None) == dataset_name:
            return ds.id
    return None


async def forget_incident(incident_id: str) -> bool:
    """
    Remove a specific incident from permanent memory.

    Demonstrates that memory here is curated, not just append-only: a
    stale or superseded incident can be deleted from the graph + vector
    store, not merely hidden from future prompts.
    """
    content_hash = _incident_hashes.get(incident_id)
    if not content_hash:
        return False

    dataset_id = await _resolve_dataset_id(DATASET_NAME)
    if not dataset_id:
        return False

    items = await cognee.datasets.list_data(dataset_id)
    match = next((d for d in items if getattr(d, "content_hash", None) == content_hash), None)
    if not match:
        return False

    await cognee.forget(data_id=match.id, dataset_id=dataset_id)
    del _incident_hashes[incident_id]
    return True
