# AI News Notifier

毎朝9時（JST）にAI関連ニュースをRSSから収集し、Webhookへ通知するプログラムです。GitHub Actionsで自動実行できます。

## できること

- MIT Technology Review、VentureBeat、The Verge、Google、OpenAI、MicrosoftなどのAI系RSSを取得
- 直近30時間の記事からAI関連キーワードに合うものを抽出
- 過去に通知したURLをキャッシュして重複通知を抑制
- Slack、Discord、Microsoft Teams、汎用Webhookに通知
- 手動実行とローカルのドライランに対応

## セットアップ

1. GitHubリポジトリの **Settings > Secrets and variables > Actions** を開きます。
2. Secretに `NEWS_WEBHOOK_URL` を追加します。
   - Slack Incoming Webhook、Discord Webhook、Teams Incoming Webhookなどを指定できます。
3. 必要に応じて Variables を追加します。
   - `NEWS_WEBHOOK_TYPE`: `auto` / `slack` / `discord` / `teams` / `generic`（既定値: `auto`）
   - `NEWS_MAX_ITEMS`: 1回の最大通知件数（既定値: `8`）
   - `NEWS_LOOKBACK_HOURS`: 何時間前までの記事を見るか（既定値: `30`）
   - `NEWS_SOURCES_JSON`: RSSソースを差し替えるJSON配列。例: `[{"name":"Example","url":"https://example.com/feed.xml"}]`
4. `.github/workflows/ai-news-notifier.yml` が毎日 09:00 JST に `scripts/ai-news-notifier.mjs` を実行します。

## ローカルで動作確認

```bash
npm run ai-news:dry-run
```

実際に通知する場合は以下のようにWebhook URLを指定します。

```bash
NEWS_WEBHOOK_URL="https://example.com/webhook" npm run ai-news
```

## カスタマイズ

RSSソースは `NEWS_SOURCES_JSON` で変更できます。未指定の場合は `scripts/ai-news-notifier.mjs` 内の既定ソースが使われます。

```json
[
  { "name": "OpenAI News", "url": "https://openai.com/news/rss.xml" },
  { "name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/" }
]
```

通知先の種類はURLから自動判定します。判定に失敗する場合は `NEWS_WEBHOOK_TYPE` を明示してください。
