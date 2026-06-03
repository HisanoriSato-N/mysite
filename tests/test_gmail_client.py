import base64

from gmail_draft_agent.gmail_client import GmailClient


def test_reply_subject_adds_prefix_once():
    assert GmailClient._reply_subject("Hello") == "Re: Hello"
    assert GmailClient._reply_subject("Re: Hello") == "Re: Hello"


def test_extract_text_from_nested_payload():
    client = object.__new__(GmailClient)
    text = "こんにちは"
    data = base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8")

    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": "PGgxPkhlbGxvPC9oMT4="}},
            {"mimeType": "text/plain", "body": {"data": data}},
        ],
    }

    assert client._extract_text(payload) == text
