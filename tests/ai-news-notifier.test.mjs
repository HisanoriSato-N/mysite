import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
const tempDir = await mkdtemp(path.join(tmpdir(), 'ai-news-test-'));

try {
  const feed = `<?xml version="1.0" encoding="UTF-8" ?>
  <rss version="2.0">
    <channel>
      <title>Test AI Feed</title>
      <item>
        <title>OpenAI releases a new AI agent workflow</title>
        <link>https://example.com/news/ai-agent?utm_source=test</link>
        <description>Artificial intelligence teams are testing new agent automation.</description>
        <pubDate>${new Date().toUTCString()}</pubDate>
      </item>
    </channel>
  </rss>`;

  const { stdout } = await execFileAsync('node', ['scripts/ai-news-notifier.mjs'], {
    env: {
      ...process.env,
      DRY_RUN: 'true',
      NEWS_SOURCES_JSON: JSON.stringify([{ name: 'Fixture Feed', url: `data:application/rss+xml,${encodeURIComponent(feed)}` }]),
      NEWS_STATE_FILE: path.join(tempDir, 'state.json')
    },
    maxBuffer: 1024 * 1024
  });

  assert.match(stdout, /AIニュースまとめ/);
  assert.match(stdout, /OpenAI releases a new AI agent workflow/);
  assert.match(stdout, /https:\/\/example\.com\/news\/ai-agent/);
} finally {
  await rm(tempDir, { recursive: true, force: true });
}
