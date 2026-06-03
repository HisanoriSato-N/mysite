FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY gmail_draft_agent ./gmail_draft_agent

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1

CMD ["gmail-draft-agent", "daemon"]
