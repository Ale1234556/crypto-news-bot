import os
import json
import hashlib
import requests
import feedparser
from datetime import datetime, timezone

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

FEEDS = [
    {
        "name": "Bitcoin Magazine",
        "url": "https://bitcoinmagazine.com/.rss/full/",
        "emoji": "🟠",
    },
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
        "emoji": "🌍",
    },
]

SEEN_FILE = "seen_articles.json"
MAX_SEEN = 500


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return []
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_seen(seen):
    seen = seen[-MAX_SEEN:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def make_id(entry):
    raw = (
        entry.get("id")
        or entry.get("link")
        or (entry.get("title", "") + entry.get("published", ""))
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def format_message(source_name, emoji, entry):
    title = entry.get("title", "No title").strip()
    link = entry.get("link", "").strip()

   return {
    "content": f"**{title}**\n\n🔗 {link}"
}


def post_to_discord(payload):
    response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=20)
    response.raise_for_status()


def fetch_feed(feed):
    parsed = feedparser.parse(feed["url"])
    if getattr(parsed, "bozo", 0):
        print(f"[WARN] Feed issue: {feed['name']} | bozo={parsed.bozo}")
    return parsed.entries


def main():
    if not DISCORD_WEBHOOK:
        raise ValueError("Missing DISCORD_WEBHOOK environment variable")

    seen = load_seen()
    seen_set = set(seen)
    new_seen = list(seen)

    total_sent = 0

    for feed in FEEDS:
        print(f"[INFO] Checking {feed['name']}...")
        try:
            entries = fetch_feed(feed)
        except Exception as e:
            print(f"[ERROR] Failed reading {feed['name']}: {e}")
            continue

        # publicar solo las más recientes primero
        entries = list(entries[:5])
        entries.reverse()

        for entry in entries:
            article_id = make_id(entry)

            if article_id in seen_set:
                continue

            try:
                payload = format_message(feed["name"], feed["emoji"], entry)
                post_to_discord(payload)
                print(f"[SENT] {feed['name']} - {entry.get('title', 'No title')}")
                seen_set.add(article_id)
                new_seen.append(article_id)
                total_sent += 1
            except Exception as e:
                print(f"[ERROR] Failed posting article: {e}")

    save_seen(new_seen)
    print(f"[DONE] Sent {total_sent} new articles at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
