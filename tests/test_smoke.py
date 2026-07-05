"""
Structural smoke test — no API key required. Confirms imports resolve,
the Incident schema behaves, and the LangGraph pipeline compiles.

Run: python -m pytest tests/test_smoke.py -v
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas import Incident
from app.data.seed_incidents import HISTORICAL_INCIDENTS, NEW_INCIDENT
from app.agents.graph import build_graph


def test_incident_to_memory_text():
    inc = Incident(
        incident_id="TEST-1",
        device="RTR-1",
        site="SITE-A",
        symptom="test symptom",
        telemetry_snippet="test telemetry",
    )
    text = inc.to_memory_text()
    assert "TEST-1" in text
    assert "RTR-1" in text
    assert "test symptom" in text


def test_seed_data_shape():
    assert len(HISTORICAL_INCIDENTS) >= 5
    assert all(isinstance(i, Incident) for i in HISTORICAL_INCIDENTS)
    assert NEW_INCIDENT.device == "MPLS-RTR-07"
    # the whole demo hinges on this incident matching a historical one on device+site
    matching = [i for i in HISTORICAL_INCIDENTS if i.device == NEW_INCIDENT.device]
    assert len(matching) == 1, "demo relies on exactly one historical incident sharing the device"


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


if __name__ == "__main__":
    test_incident_to_memory_text()
    test_seed_data_shape()
    test_graph_compiles()
    print("All smoke tests passed.")
