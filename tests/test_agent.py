from pathlib import Path

from gmail_draft_agent.agent import GmailDraftAgent
from gmail_draft_agent.config import Settings
from gmail_draft_agent.models import EmailMessage, ReplyDecision
from gmail_draft_agent.store import Store


class FakeGmailClient:
    def __init__(self):
        self.created = []

    def list_message_ids(self, query, max_results):
        return ["m1", "m2"]

    def get_message(self, message_id):
        return EmailMessage(
            message_id=message_id,
            thread_id=f"t-{message_id}",
            subject="確認お願いします" if message_id == "m1" else "FYI",
            sender="sender@example.com",
            recipient="me@example.com",
            date="Wed, 03 Jun 2026 00:00:00 +0000",
            snippet="snippet",
            body_text="body",
        )

    def create_reply_draft(self, original, body_text, signature=""):
        self.created.append((original.message_id, body_text, signature))
        return f"draft-{original.message_id}"


class FakeDecider:
    def decide(self, message):
        if message.message_id == "m1":
            return ReplyDecision(True, "質問への回答が必要", "承知しました。確認します。")
        return ReplyDecision(False, "情報共有のみ", None)


class FakeNotifier:
    def __init__(self):
        self.drafts = []
        self.skips = []

    def draft_created(self, message, draft_id, reason):
        self.drafts.append((message.message_id, draft_id, reason))

    def skipped(self, message, reason):
        self.skips.append((message.message_id, reason))


def test_run_once_creates_draft_and_records_skip(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "agent.sqlite3", dry_run=False)
    gmail = FakeGmailClient()
    notifier = FakeNotifier()
    agent = GmailDraftAgent(
        settings,
        gmail_client=gmail,
        decider=FakeDecider(),
        notifier=notifier,
        store=Store(settings.database_path),
    )

    summary = agent.run_once()

    assert summary.found == 2
    assert summary.processed == 2
    assert summary.drafted == 1
    assert summary.skipped == 1
    assert gmail.created == [("m1", "承知しました。確認します。", "")]
    assert notifier.drafts == [("m1", "draft-m1", "質問への回答が必要")]
    assert notifier.skips == [("m2", "情報共有のみ")]

    second_summary = agent.run_once()
    assert second_summary.processed == 0
