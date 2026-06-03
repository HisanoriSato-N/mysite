from __future__ import annotations

from gmail_draft_agent.models import EmailMessage


class Notifier:
    """Sends a human-review notification after a draft is created."""

    def __init__(self, webhook_url: str | None, channel_name: str):
        self.webhook_url = webhook_url
        self.channel_name = channel_name

    def draft_created(self, message: EmailMessage, draft_id: str, reason: str) -> None:
        if not self.webhook_url:
            return
        text = (
            f"📩 Gmail reply draft created for review\n"
            f"Channel: {self.channel_name}\n"
            f"From: {message.sender}\n"
            f"Subject: {message.subject}\n"
            f"Draft ID: {draft_id}\n"
            f"Reason: {reason}"
        )
        import requests

        requests.post(self.webhook_url, json={"text": text}, timeout=10).raise_for_status()

    def skipped(self, message: EmailMessage, reason: str) -> None:
        if not self.webhook_url:
            return
        text = f"↪️ Gmail message skipped\nFrom: {message.sender}\nSubject: {message.subject}\nReason: {reason}"
        import requests

        requests.post(self.webhook_url, json={"text": text}, timeout=10).raise_for_status()
