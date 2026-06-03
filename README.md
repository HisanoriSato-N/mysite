# Gmail Draft Agent

Gmailの受信箱を定期監視し、返信が必要なメールだけAIで返信案を作成して、Gmailの下書きとして保存し、必要に応じてSlack/Discord互換Webhookへ通知する常駐プログラムです。

> 安全のため、このエージェントはメールを自動送信しません。作成するのは下書きだけです。

## 機能

- Gmail INBOXなど任意のGmail検索クエリをポーリング監視
- 処理済みメールをSQLiteに保存して重複処理を防止
- OpenAI APIで返信要否を判定し、返信案を生成
- Gmail APIで元スレッドに紐づく返信下書きを作成
- Slack/Discord互換Webhookへレビュー通知
- CLI、常駐daemon、FastAPI HTTP APIの3通りで起動可能

## セットアップ

1. Google Cloud ConsoleでOAuthクライアントを作成し、Gmail APIを有効化します。
2. OAuthクライアントのJSONを `credentials.json` として保存します。
3. `.env.example` を `.env` にコピーして値を設定します。
4. 依存関係をインストールします。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Gmail権限

このアプリは最小限の用途として以下のスコープを使います。

- `https://www.googleapis.com/auth/gmail.readonly`: メール検索と本文取得
- `https://www.googleapis.com/auth/gmail.compose`: Gmail下書き作成

初回起動時にブラウザでOAuth認可が実行され、取得したトークンは `token.json` に保存されます。

## 起動方法

1回だけ処理します。

```bash
gmail-draft-agent run-once
```

24時間常駐して `POLL_INTERVAL_SECONDS` ごとに処理します。

```bash
gmail-draft-agent daemon
```

HTTP APIとして起動します。

```bash
gmail-draft-agent serve --host 0.0.0.0 --port 8000
```

HTTP APIでは以下が使えます。

- `GET /health`: ヘルスチェック
- `POST /run-once`: 1回だけGmail処理を実行
- `GET /processed`: 直近の処理履歴を取得


## Dockerで24時間常駐する

OAuth認可を済ませて `token.json` を作成した後は、Docker Composeでdaemonを常駐できます。

```bash
docker compose up -d --build
```

停止する場合は以下を実行します。

```bash
docker compose down
```

## 運用メモ

最初は `DRY_RUN=true` で動作確認してください。dry runではGmail下書きを作らず、処理履歴には `draft_id=dry-run` として保存します。

本番で24時間運用する場合は、Cloud Run Jobs、VPSのsystemd、Docker Compose、Railway、Render、Fly.ioなどでdaemonまたはHTTP APIを常駐させてください。

Gmail APIのPush Notification + Cloud Pub/Sub構成へ拡張すると、ポーリングではなくメールボックス変更通知をトリガーにできます。その場合も、返信要否判定、下書き作成、通知、処理済み管理の中核ロジックはこのパッケージを流用できます。

## セキュリティ方針

- メール本文に含まれる「AIへの命令」はシステム命令として扱いません。
- 返信案は人間レビュー前提で作り、自動送信しません。
- `credentials.json`、`token.json`、`.env`、SQLite DBはGit管理対象外です。
- 通知には本文全体を載せず、送信者・件名・下書きID・理由だけを送ります。
