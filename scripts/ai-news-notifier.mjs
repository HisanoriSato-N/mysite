#!/usr/bin/env node
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const DEFAULT_SOURCES = [
  { name: 'MIT Technology Review AI', url: 'https://www.technologyreview.com/topic/artificial-intelligence/feed/' },
  { name: 'VentureBeat AI', url: 'https://venturebeat.com/category/ai/feed/' },
  { name: 'The Verge AI', url: 'https://www.theverge.com/ai-artificial-intelligence/rss/index.xml' },
  { name: 'Google AI Blog', url: 'https://blog.google/technology/ai/rss/' },
  { name: 'OpenAI News', url: 'https://openai.com/news/rss.xml' },
  { name: 'Microsoft AI Blog', url: 'https://blogs.microsoft.com/ai/feed/' }
];

const AI_KEYWORDS = [
  'ai', 'artificial intelligence', '生成ai', '人工知能', '機械学習', 'machine learning',
  'deep learning', 'llm', 'large language model', 'chatgpt', 'openai', 'anthropic',
  'gemini', 'copilot', 'nvidia', 'gpu', 'agent', 'agents', 'robotics', 'model'
];

const config = {
  dryRun: readBooleanEnv('DRY_RUN', false),
  webhookUrl: process.env.NEWS_WEBHOOK_URL || '',
  webhookType: (process.env.NEWS_WEBHOOK_TYPE || 'auto').toLowerCase(),
  timezone: process.env.NEWS_TIMEZONE || 'Asia/Tokyo',
  maxItems: readIntegerEnv('NEWS_MAX_ITEMS', 8),
  lookbackHours: readIntegerEnv('NEWS_LOOKBACK_HOURS', 30),
  stateFile: process.env.NEWS_STATE_FILE || '.cache/ai-news-state.json',
  sources: readSources()
};

main().catch((error) => {
  console.error(`AI news notifier failed: ${error.stack || error.message}`);
  process.exitCode = 1;
});

async function main() {
  const state = await loadState(config.stateFile);
  const since = Date.now() - config.lookbackHours * 60 * 60 * 1000;
  const settledFeeds = await Promise.allSettled(config.sources.map(fetchFeed));
  const feedErrors = [];

  const items = settledFeeds.flatMap((result, index) => {
    if (result.status === 'fulfilled') return result.value;
    feedErrors.push(`${config.sources[index].name}: ${result.reason.message}`);
    return [];
  });

  const freshItems = dedupeByLink(items)
    .filter((item) => item.publishedAt.getTime() >= since)
    .filter((item) => matchesAiTopic(item))
    .filter((item) => !state.seenLinks.includes(item.link))
    .sort((a, b) => b.publishedAt - a.publishedAt)
    .slice(0, config.maxItems);

  if (freshItems.length === 0) {
    const message = [
      `AIニュース通知: 新着記事はありませんでした（${formatDate(new Date(), config.timezone)}）。`,
      feedErrors.length ? `取得できなかったRSS: ${feedErrors.join('; ')}` : ''
    ].filter(Boolean).join('\n');
    await notify(message);
    return;
  }

  const message = buildDigest(freshItems, feedErrors);
  await notify(message);

  const nextSeenLinks = [...new Set([...freshItems.map((item) => item.link), ...state.seenLinks])].slice(0, 300);
  await saveState(config.stateFile, { seenLinks: nextSeenLinks, updatedAt: new Date().toISOString() });
}

async function fetchFeed(source) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const xml = await fetchText(source.url, controller.signal);
    return parseFeed(xml, source);
  } finally {
    clearTimeout(timeout);
  }
}


async function fetchText(url, signal) {
  try {
    const response = await fetch(url, {
      signal,
      headers: { 'user-agent': 'mysite-ai-news-notifier/1.0 (+https://github.com/)' }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.text();
  } catch (error) {
    if (!hasProxyEnv()) throw error;
    return curlText(url);
  }
}

async function postJson(url, payload) {
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Webhook notification failed: HTTP ${response.status} ${text}`);
    }
  } catch (error) {
    if (!hasProxyEnv()) throw error;
    await curlPostJson(url, payload);
  }
}

async function curlText(url) {
  const { stdout } = await execFileAsync('curl', [
    '--fail', '--silent', '--show-error', '--location',
    '--max-time', '20',
    '--user-agent', 'mysite-ai-news-notifier/1.0 (+https://github.com/)',
    url
  ], { maxBuffer: 10 * 1024 * 1024 });
  return stdout;
}

async function curlPostJson(url, payload) {
  await execFileAsync('curl', [
    '--fail', '--silent', '--show-error', '--location',
    '--max-time', '20',
    '--header', 'content-type: application/json',
    '--data', JSON.stringify(payload),
    url
  ], { maxBuffer: 1024 * 1024 });
}

function hasProxyEnv() {
  return Boolean(process.env.HTTPS_PROXY || process.env.HTTP_PROXY || process.env.https_proxy || process.env.http_proxy);
}

function parseFeed(xml, source) {
  const itemBlocks = matchBlocks(xml, 'item');
  const entryBlocks = matchBlocks(xml, 'entry');
  const blocks = itemBlocks.length ? itemBlocks : entryBlocks;

  return blocks.map((block) => {
    const title = cleanText(readTag(block, 'title'));
    const link = cleanText(readTag(block, 'link')) || readAtomLink(block);
    const description = cleanText(readTag(block, 'description') || readTag(block, 'summary') || readTag(block, 'content:encoded'));
    const published = cleanText(readTag(block, 'pubDate') || readTag(block, 'published') || readTag(block, 'updated'));
    const publishedAt = published ? new Date(published) : new Date();

    return {
      source: source.name,
      title,
      link,
      description,
      publishedAt: Number.isNaN(publishedAt.getTime()) ? new Date() : publishedAt
    };
  }).filter((item) => item.title && item.link);
}

function matchBlocks(xml, tag) {
  const matches = [...xml.matchAll(new RegExp(`<${tag}\\b[^>]*>([\\s\\S]*?)<\\/${tag}>`, 'gi'))];
  return matches.map((match) => match[1]);
}

function readTag(block, tag) {
  const escapedTag = tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = block.match(new RegExp(`<${escapedTag}\\b[^>]*>([\\s\\S]*?)<\\/${escapedTag}>`, 'i'));
  return match?.[1] || '';
}

function readAtomLink(block) {
  const hrefMatch = block.match(/<link\b[^>]*href=["']([^"']+)["'][^>]*>/i);
  return cleanText(hrefMatch?.[1] || '');
}

function cleanText(value) {
  return decodeHtml(stripCdata(value || '').replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
}

function stripCdata(value) {
  return value.replace(/^\s*<!\[CDATA\[/, '').replace(/\]\]>\s*$/, '');
}

function decodeHtml(value) {
  const entities = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
  return value
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(Number.parseInt(code, 16)))
    .replace(/&([a-z]+);/gi, (_, entity) => entities[entity.toLowerCase()] || `&${entity};`);
}

function matchesAiTopic(item) {
  const haystack = `${item.title} ${item.description} ${item.source}`.toLowerCase();
  return AI_KEYWORDS.some((keyword) => haystack.includes(keyword.toLowerCase()));
}

function dedupeByLink(items) {
  const seen = new Set();
  return items.filter((item) => {
    const normalized = normalizeLink(item.link);
    if (seen.has(normalized)) return false;
    seen.add(normalized);
    item.link = normalized;
    return true;
  });
}

function normalizeLink(link) {
  try {
    const url = new URL(link);
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'].forEach((param) => url.searchParams.delete(param));
    url.hash = '';
    return url.toString();
  } catch {
    return link;
  }
}

function buildDigest(items, feedErrors) {
  const lines = [
    `AIニュースまとめ（${formatDate(new Date(), config.timezone)}）`,
    `直近${config.lookbackHours}時間の新着から${items.length}件を抽出しました。`,
    ''
  ];

  items.forEach((item, index) => {
    lines.push(`${index + 1}. ${item.title}`);
    lines.push(`   ${item.source} / ${formatDate(item.publishedAt, config.timezone)}`);
    lines.push(`   ${item.link}`);
    if (item.description) lines.push(`   ${truncate(item.description, 140)}`);
    lines.push('');
  });

  if (feedErrors.length) {
    lines.push(`取得できなかったRSS: ${feedErrors.join('; ')}`);
  }

  return lines.join('\n').trim();
}

async function notify(message) {
  if (config.dryRun || !config.webhookUrl) {
    console.log(message);
    if (!config.webhookUrl) console.log('\nNEWS_WEBHOOK_URL が未設定のため、通知は送信していません。');
    return;
  }

  const type = detectWebhookType(config.webhookUrl, config.webhookType);
  const payload = buildWebhookPayload(type, message);
  await postJson(config.webhookUrl, payload);
}

function detectWebhookType(url, configuredType) {
  if (configuredType !== 'auto') return configuredType;
  if (url.includes('discord.com/api/webhooks') || url.includes('discordapp.com/api/webhooks')) return 'discord';
  if (url.includes('hooks.slack.com')) return 'slack';
  return 'generic';
}

function buildWebhookPayload(type, message) {
  if (type === 'discord') return { content: message.slice(0, 1900) };
  if (type === 'slack') return { text: message };
  if (type === 'teams') return { text: message };
  return { text: message, content: message };
}

async function loadState(stateFile) {
  try {
    const raw = await readFile(stateFile, 'utf8');
    const parsed = JSON.parse(raw);
    return { seenLinks: Array.isArray(parsed.seenLinks) ? parsed.seenLinks : [] };
  } catch {
    return { seenLinks: [] };
  }
}

async function saveState(stateFile, state) {
  await mkdir(path.dirname(stateFile), { recursive: true });
  await writeFile(stateFile, `${JSON.stringify(state, null, 2)}\n`);
}

function readSources() {
  if (!process.env.NEWS_SOURCES_JSON) return DEFAULT_SOURCES;
  const parsed = JSON.parse(process.env.NEWS_SOURCES_JSON);
  if (!Array.isArray(parsed)) throw new Error('NEWS_SOURCES_JSON must be an array');
  return parsed.map((source) => {
    if (!source.name || !source.url) throw new Error('Each NEWS_SOURCES_JSON source needs name and url');
    return { name: source.name, url: source.url };
  });
}

function readIntegerEnv(name, fallback) {
  const value = Number.parseInt(process.env[name] || '', 10);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function readBooleanEnv(name, fallback) {
  if (!process.env[name]) return fallback;
  return ['1', 'true', 'yes', 'on'].includes(process.env[name].toLowerCase());
}

function formatDate(date, timezone) {
  return new Intl.DateTimeFormat('ja-JP', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: timezone
  }).format(date);
}

function truncate(value, maxLength) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}
