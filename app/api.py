"""
FastAPI app with the Gradio UI mounted at "/" — single process, single
service. Deploy this one file (uvicorn app.api:app) and both the demo UI
and the API routes are served together.

    uvicorn app.api:app --host 0.0.0.0 --port 8000

GET  /              the Gradio demo UI (seed, submit, rate, forget, visualize)
POST /seed           remember: load synthetic historical incidents into memory
POST /incident        recall + diagnose: submit a new incident
POST /rate            improve: attach feedback to a diagnosis and fold it back in
POST /forget          forget: remove a specific incident from memory
GET  /graph           render the live knowledge graph as HTML
GET  /health          sanity check
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import gradio as gr

from app.config import DATASET_NAME
from app.schemas import Incident
from app.agents.graph import run_incident
from app.memory import bootstrap_history, rate_diagnosis, forget_incident
from app.data.seed_incidents import HISTORICAL_INCIDENTS
# Importing app.ui runs configure_cognee() at module load (see app/ui.py),
# so Cognee is configured before any request hits this app. GRAPH_DIR is
# reused here so the mounted UI is allowed to serve its graph HTML files.
from app.ui import demo as gradio_demo, GRAPH_DIR


app = FastAPI(title="NOC Copilot with Persistent Memory")


class RatingRequest(BaseModel):
    session_id: str
    qa_id: str
    correct: bool
    note: str = ""


class ForgetRequest(BaseModel):
    incident_id: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/seed")
async def seed():
    await bootstrap_history(HISTORICAL_INCIDENTS)
    return {"seeded": [i.incident_id for i in HISTORICAL_INCIDENTS]}


@app.post("/incident")
async def submit_incident(incident: Incident):
    result = await run_incident(incident)
    return {
        "incident_id": incident.incident_id,
        "recalled": result["recalled"],
        "diagnosis": result["diagnosis"],
        "session_id": result["session_id"],
        "qa_id": result["qa_id"],
    }


@app.post("/rate")
async def rate(req: RatingRequest):
    await rate_diagnosis(req.session_id, req.qa_id, req.correct, req.note)
    return {"status": "recorded", "correct": req.correct}


@app.post("/forget")
async def forget(req: ForgetRequest):
    ok = await forget_incident(req.incident_id)
    return {"forgotten": ok, "incident_id": req.incident_id}


@app.get("/graph", response_class=HTMLResponse)
async def graph():
    import cognee

    html = await cognee.visualize_graph(dataset=DATASET_NAME)
    return HTMLResponse(content=html)


# Mount last so FastAPI's own routes above take precedence over Gradio's
# catch-all at "/".
app = gr.mount_gradio_app(app, gradio_demo, path="/", allowed_paths=[GRAPH_DIR])


class RatingRequest(BaseModel):
    session_id: str
    qa_id: str
    correct: bool
    note: str = ""


class ForgetRequest(BaseModel):
    incident_id: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/seed")
async def seed():
    await bootstrap_history(HISTORICAL_INCIDENTS)
    return {"seeded": [i.incident_id for i in HISTORICAL_INCIDENTS]}


@app.post("/incident")
async def submit_incident(incident: Incident):
    result = await run_incident(incident)
    return {
        "incident_id": incident.incident_id,
        "recalled": result["recalled"],
        "diagnosis": result["diagnosis"],
        "session_id": result["session_id"],
        "qa_id": result["qa_id"],
    }


@app.post("/rate")
async def rate(req: RatingRequest):
    await rate_diagnosis(req.session_id, req.qa_id, req.correct, req.note)
    return {"status": "recorded", "correct": req.correct}


@app.post("/forget")
async def forget(req: ForgetRequest):
    ok = await forget_incident(req.incident_id)
    return {"forgotten": ok, "incident_id": req.incident_id}


@app.get("/graph", response_class=HTMLResponse)
async def graph():
    import cognee

    html = await cognee.visualize_graph(dataset=DATASET_NAME)
    return HTMLResponse(content=html)
