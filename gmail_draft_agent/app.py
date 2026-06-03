from fastapi import Depends, FastAPI

from gmail_draft_agent.agent import GmailDraftAgent, RunSummary
from gmail_draft_agent.config import Settings, get_settings
from gmail_draft_agent.store import ProcessedMessage, Store

app = FastAPI(title="Gmail Draft Agent", version="0.1.0")


def get_agent(settings: Settings = Depends(get_settings)) -> GmailDraftAgent:
    return GmailDraftAgent(settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run-once")
def run_once(agent: GmailDraftAgent = Depends(get_agent)) -> RunSummary:
    return agent.run_once()


@app.get("/processed")
def processed(settings: Settings = Depends(get_settings), limit: int = 20) -> list[ProcessedMessage]:
    return Store(settings.database_path).recent(limit)
