from datetime import datetime,UTC
from typing import Optional
from pydantic import BaseModel, Field
def utc_now():
    return datetime.now(UTC)



class Incident(BaseModel):
    incident_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    device: str
    site: str
    symptom: str
    telemetry_snippet: str
    severity: str = "warning"  # warning | major | critical
    root_cause: Optional[str] = None
    resolution: Optional[str] = None

    def to_memory_text(self) -> str:
        """Flatten the incident into text Cognee can ingest and cognify into graph entities."""
        parts = [
            f"Incident {self.incident_id} at site {self.site}, device {self.device}.",
            f"Symptom: {self.symptom}",
            f"Telemetry: {self.telemetry_snippet}",
            f"Severity: {self.severity}",
        ]
        if self.root_cause:
            parts.append(f"Root cause identified: {self.root_cause}")
        if self.resolution:
            parts.append(f"Resolution applied: {self.resolution}")
        return " ".join(parts)
