from __future__ import annotations

import argparse
import logging
import time

import uvicorn

from gmail_draft_agent.agent import GmailDraftAgent
from gmail_draft_agent.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Gmail reply draft agent")
    parser.add_argument("command", choices=["run-once", "daemon", "serve"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    if args.command == "serve":
        uvicorn.run("gmail_draft_agent.app:app", host=args.host, port=args.port)
        return

    agent = GmailDraftAgent(settings)
    if args.command == "run-once":
        print(agent.run_once())
        return

    while True:
        try:
            summary = agent.run_once()
            logging.info("Run complete: %s", summary)
        except Exception:
            logging.exception("Agent run failed")
        time.sleep(settings.poll_interval_seconds)
