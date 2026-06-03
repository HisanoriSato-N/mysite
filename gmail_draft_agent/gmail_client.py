from __future__ import annotations

import base64
from email.message import EmailMessage as MimeEmailMessage
from pathlib import Path

from gmail_draft_agent.models import EmailMessage

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


class GmailClient:
    """Thin wrapper around Gmail API operations used by the agent."""

    def __init__(self, credentials_file: Path, token_file: Path):
        self.credentials_file = credentials_file
        self.token_file = token_file
        from googleapiclient.discovery import build

        self.service = build("gmail", "v1", credentials=self._load_credentials())

    def _load_credentials(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        credentials = None
        if self.token_file.exists():
            credentials = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        if credentials and credentials.valid:
            return credentials
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_file), SCOPES)
            credentials = flow.run_local_server(port=0)
        self.token_file.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def list_message_ids(self, query: str, max_results: int) -> list[str]:
        response = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        return [message["id"] for message in response.get("messages", [])]

    def get_message(self, message_id: str) -> EmailMessage:
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = {header["name"].lower(): header["value"] for header in message["payload"].get("headers", [])}
        return EmailMessage(
            message_id=message["id"],
            thread_id=message["threadId"],
            subject=headers.get("subject", ""),
            sender=headers.get("from", ""),
            recipient=headers.get("to", "me"),
            date=headers.get("date", ""),
            snippet=message.get("snippet", ""),
            body_text=self._extract_text(message.get("payload", {})),
            references=headers.get("references"),
            in_reply_to=headers.get("in-reply-to"),
            rfc_message_id=headers.get("message-id"),
        )

    def create_reply_draft(self, original: EmailMessage, body_text: str, signature: str = "") -> str:
        draft_body = body_text.strip()
        if signature.strip():
            draft_body = f"{draft_body}\n\n{signature.strip()}"

        mime = MimeEmailMessage()
        mime.set_content(draft_body)
        mime["To"] = original.sender
        mime["Subject"] = self._reply_subject(original.subject)
        if original.rfc_message_id:
            mime["In-Reply-To"] = original.rfc_message_id
            references = " ".join(
                value for value in [original.references, original.rfc_message_id] if value
            )
            mime["References"] = references

        encoded = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
        draft = (
            self.service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": encoded, "threadId": original.thread_id}})
            .execute()
        )
        return draft["id"]

    def _extract_text(self, payload: dict) -> str:
        mime_type = payload.get("mimeType", "")
        body = payload.get("body", {})
        data = body.get("data")
        if mime_type == "text/plain" and data:
            return self._decode_body(data)
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return self._decode_body(part["body"]["data"])
        for part in parts:
            nested_text = self._extract_text(part)
            if nested_text:
                return nested_text
        return ""

    @staticmethod
    def _decode_body(data: str) -> str:
        return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")

    @staticmethod
    def _reply_subject(subject: str) -> str:
        cleaned = subject.strip()
        if cleaned.lower().startswith("re:"):
            return cleaned
        return f"Re: {cleaned}" if cleaned else "Re:"
