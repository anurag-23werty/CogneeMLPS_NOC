"""
Run once before the demo:

    python scripts/seed_memory.py

Loads HISTORICAL_INCIDENTS into Cognee's permanent graph so the agent has
something to recall when NEW_INCIDENT comes in through the UI or API.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import configure_cognee
from app.memory import bootstrap_history
from app.data.seed_incidents import HISTORICAL_INCIDENTS


async def main():
    configure_cognee()
    print(f"Seeding {len(HISTORICAL_INCIDENTS)} historical incidents into memory...")
    await bootstrap_history(HISTORICAL_INCIDENTS)
    print("Done. Historical incidents are now in Cognee's graph + vector memory.")
    for inc in HISTORICAL_INCIDENTS:
        print(f"  - {inc.incident_id}: {inc.device} @ {inc.site} — {inc.symptom[:60]}...")


if __name__ == "__main__":
    asyncio.run(main())
