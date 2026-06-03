from __future__ import annotations

import logging
from dataclasses import dataclass

from gmail_draft_agent.config import Settings
from gmail_draft_agent.gmail_client import GmailClient
from gmail_draft_agent.notifier import Notifier
from gmail_draft_agent.responder import ReplyDecider
from gmail_draft_agent.store import Store

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunSummary:
    found: int
    processed: int
    drafted: int
    skipped: int


class GmailDraftAgent:
    """Coordinates Gmail polling, reply drafting, persistence, and notifications."""

    def __init__(
        self,
        settings: Settings,
        gmail_client: GmailClient | None = None,
        decider: ReplyDecider | None = None,
        notifier: Notifier | None = None,
        store: Store | None = None,
    ):
        self.settings = settings
        self.gmail_client = gmail_client or GmailClient(
            settings.google_credentials_file,
            settings.google_token_file,
        )
        self.decider = decider or ReplyDecider(
            settings.openai_api_key,
            settings.openai_model,
            settings.responder_language,
            settings.responder_tone,
        )
        self.notifier = notifier or Notifier(
            settings.notification_webhook_url,
            settings.notification_channel_name,
        )
        self.store = store or Store(settings.database_path)

    def run_once(self) -> RunSummary:
        message_ids = self.gmail_client.list_message_ids(
            self.settings.gmail_query,
            self.settings.max_messages_per_run,
        )
        processed = 0
        drafted = 0
        skipped = 0
        for message_id in message_ids:
            if self.store.has_processed(message_id):
                continue
            processed += 1
            message = self.gmail_client.get_message(message_id)
            decision = self.decider.decide(message)
            if not decision.needs_reply or not decision.draft_body:
                skipped += 1
                self.store.record(
                    message_id=message.message_id,
                    thread_id=message.thread_id,
                    draft_id=None,
                    status="skipped",
                    reason=decision.reason,
                )
                self.notifier.skipped(message, decision.reason)
                continue
            if self.settings.dry_run:
                draft_id = "dry-run"
            else:
                draft_id = self.gmail_client.create_reply_draft(
                    message,
                    decision.draft_body,
                    self.settings.draft_signature,
                )
            drafted += 1
            self.store.record(
                message_id=message.message_id,
                thread_id=message.thread_id,
                draft_id=draft_id,
                status="drafted",
                reason=decision.reason,
            )
            self.notifier.draft_created(message, draft_id, decision.reason)
            LOGGER.info("Created draft %s for message %s", draft_id, message.message_id)
        return RunSummary(found=len(message_ids), processed=processed, drafted=drafted, skipped=skipped)
