import os
import requests
import feedparser
from datetime import datetime, timezone

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

FEEDS = [
    {
        "name": "DiarioBitcoin",
        "url": "https://www.diariobitcoin.com/feed/",
    },
    {
        "name": "Yahoo Finance S&P 500",
        "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=es-ES",
    },
    {
        "name": "Yahoo Finance Dow Jones",
        "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EDJI&region=US&lang=es-ES",
    },
]


def post_to_discord(link):
    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": link},
        timeout=20
    )
    response.raise_for_status()


def fetch_feed(feed):
    parsed = feedparser.parse(
        feed["url"],
        request_headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    print(f"[DEBUG] {feed['name']} entries found: {len(parsed.entries)}")

    if getattr(parsed, "bozo", 0):
        print(f"[WARN] Feed issue: {feed['name']} | bozo={parsed.bozo}")

    return parsed.entries


def main():
    if not DISCORD_WEBHOOK:
        raise ValueError("Missing DISCORD_WEBHOOK environment variable")

    total_sent = 0

    for feed in FEEDS:
        print(f"[INFO] Checking {feed['name']}...")

        try:
            entries = fetch_feed(feed)
        except Exception as e:
            print(f"[ERROR] Failed reading {feed['name']}: {e}")
            continue

        if not entries:
            print(f"[WARN] No entries found for {feed['name']}")
            continue

        latest_entry = entries[0]
        link = latest_entry.get("link", "").strip()

        if not link:
            print(f"[WARN] No link found for {feed['name']}")
            continue

        try:
            post_to_discord(link)
            print(f"[SENT] {feed['name']} - {latest_entry.get('title', 'No title')}")
            total_sent += 1
        except Exception as e:
            print(f"[ERROR] Failed posting {feed['name']}: {e}")

    print(f"[DONE] Sent {total_sent} test articles at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
