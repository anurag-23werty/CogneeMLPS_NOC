"""
Demo UI:

    python -m app.ui

Walks through the full Cognee memory lifecycle, not just remember+recall:

  1. "Seed historical memory" — loads 18 past incidents across 13 devices.
  2. "Submit new incident" — pre-filled with a repeat BGP flap on the SAME
     router as INC-1003. Watch the agent recall that one specific incident
     out of the other 17, not the whole history.
  3. "Rate this diagnosis" — mark it correct/incorrect. This calls
     cognee.improve() under the hood, folding operator feedback into the
     graph so future recall is weighted by what actually worked.
  4. "Forget an incident" — remove a stale/superseded incident from the
     graph + vector store entirely, proving memory here is curated, not
     append-only.
  5. "Visualize memory graph" — renders Cognee's actual knowledge graph
     (entities + relationships extracted from the incidents) so the
     graph-vector claim is shown, not just asserted.
"""

import gradio as gr

from app.config import configure_cognee, DATASET_NAME
from app.memory import bootstrap_history, rate_diagnosis, forget_incident
from app.data.seed_incidents import HISTORICAL_INCIDENTS, NEW_INCIDENT
from app.schemas import Incident
from app.agents.graph import run_incident

configure_cognee()


async def seed_history():
    await bootstrap_history(HISTORICAL_INCIDENTS)
    lines = [f"- {i.incident_id}: {i.device} @ {i.site} — {i.symptom[:70]}..." for i in HISTORICAL_INCIDENTS]
    return "Seeded " + str(len(HISTORICAL_INCIDENTS)) + " historical incidents into memory:\n" + "\n".join(lines)


async def submit_incident(device, site, symptom, telemetry, severity):
    incident = Incident(
        incident_id="INC-LIVE-" + str(abs(hash(symptom)) % 10000),
        device=device,
        site=site,
        symptom=symptom,
        telemetry_snippet=telemetry,
        severity=severity,
    )
    result = await run_incident(incident)
    recalled = result["recalled"]
    recalled_str = "\n\n".join(str(r) for r in recalled) if recalled else "Nothing related found in memory."
    # session_id/qa_id are threaded through as hidden state so the rating
    # buttons below know which diagnosis they're rating.
    return recalled_str, result["diagnosis"], result["session_id"], result["qa_id"]


def load_prefilled_new_incident():
    inc = NEW_INCIDENT
    return inc.device, inc.site, inc.symptom, inc.telemetry_snippet, inc.severity


async def submit_rating(session_id, qa_id, correct: bool):
    if not session_id or not qa_id:
        return "Submit an incident first before rating its diagnosis."
    await rate_diagnosis(session_id, qa_id, correct)
    verdict = "correct" if correct else "incorrect"
    return f"Feedback recorded as '{verdict}' and folded into memory via improve()."


async def submit_rating_correct(session_id, qa_id):
    return await submit_rating(session_id, qa_id, True)


async def submit_rating_incorrect(session_id, qa_id):
    return await submit_rating(session_id, qa_id, False)


async def run_forget(incident_id: str):
    if not incident_id:
        return "Enter an incident ID to forget, e.g. INC-1031."
    ok = await forget_incident(incident_id.strip())
    if ok:
        return f"{incident_id.strip()} removed from graph + vector memory."
    return f"Couldn't find {incident_id.strip()} in this session's tracked incidents (must have been remembered in this process run)."


import tempfile
import os

GRAPH_DIR = tempfile.mkdtemp(prefix="noc_graph_")


async def render_graph():
    import cognee

    path = os.path.join(GRAPH_DIR, "graph.html")
    await cognee.visualize_graph(destination_file_path=path, dataset=DATASET_NAME)
    # gr.HTML injects via innerHTML, which never executes <script> tags regardless
    # of how they're wrapped. Pointing an iframe at a real file on disk instead
    # gives the graph's JS its own document to load and run in normally.
    return f'<iframe src="/gradio_api/file={path}" style="width:100%;height:700px;border:none;"></iframe>'


with gr.Blocks(title="NOC Copilot — Persistent Memory Demo") as demo:
    gr.Markdown(
        "# NOC Copilot with persistent memory\n"
        "Cognee stores incidents as a graph+vector memory that survives across sessions. "
        "Walk through remember -> recall -> improve -> forget below."
    )

    session_state = gr.State(None)
    qa_state = gr.State(None)

    with gr.Row():
        seed_btn = gr.Button("1. Seed historical memory (remember)", variant="secondary")
    seed_output = gr.Textbox(label="Seed result", lines=8)
    seed_btn.click(seed_history, outputs=seed_output)

    gr.Markdown("---")

    with gr.Row():
        with gr.Column():
            device = gr.Textbox(label="Device")
            site = gr.Textbox(label="Site")
            symptom = gr.Textbox(label="Symptom")
            telemetry = gr.Textbox(label="Telemetry snippet")
            severity = gr.Dropdown(["warning", "major", "critical"], value="major", label="Severity")
            prefill_btn = gr.Button("Load demo incident (repeat failure on MPLS-RTR-07)")
            submit_btn = gr.Button("2. Submit new incident (recall + diagnose)", variant="primary")

        with gr.Column():
            recalled_box = gr.Textbox(label="Recalled from memory", lines=10)
            diagnosis_box = gr.Textbox(label="Diagnosis", lines=10)

    prefill_btn.click(
        load_prefilled_new_incident,
        outputs=[device, site, symptom, telemetry, severity],
    )
    submit_btn.click(
        submit_incident,
        inputs=[device, site, symptom, telemetry, severity],
        outputs=[recalled_box, diagnosis_box, session_state, qa_state],
    )

    gr.Markdown("---")

    with gr.Row():
        correct_btn = gr.Button("3a. Mark diagnosis correct (improve)")
        incorrect_btn = gr.Button("3b. Mark diagnosis incorrect (improve)")
    rating_output = gr.Textbox(label="Feedback result", lines=2)

    correct_btn.click(
        submit_rating_correct,
        inputs=[session_state, qa_state],
        outputs=rating_output,
    )
    incorrect_btn.click(
        submit_rating_incorrect,
        inputs=[session_state, qa_state],
        outputs=rating_output,
    )

    gr.Markdown("---")

    with gr.Row():
        forget_id_input = gr.Textbox(label="Incident ID to forget", placeholder="e.g. INC-1031")
        forget_btn = gr.Button("4. Forget this incident")
    forget_output = gr.Textbox(label="Forget result", lines=2)
    forget_btn.click(run_forget, inputs=forget_id_input, outputs=forget_output)

    gr.Markdown("---")

    graph_btn = gr.Button("5. Visualize memory graph")
    graph_output = gr.HTML()
    graph_btn.click(render_graph, outputs=graph_output)

if __name__ == "__main__":
    demo.launch(allowed_paths=[GRAPH_DIR])
