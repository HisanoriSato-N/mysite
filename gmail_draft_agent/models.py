from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    date: str
    snippet: str
    body_text: str
    references: str | None = None
    in_reply_to: str | None = None
    rfc_message_id: str | None = None


@dataclass(frozen=True)
class ReplyDecision:
    needs_reply: bool
    reason: str
    draft_body: str | None = None
