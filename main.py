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
        "name": "CriptoNoticias",
        "url": "https://www.criptonoticias.com/feed/",
    },
    {
        "name": "FXStreet",
        "url": "https://www.fxstreet.es/rss",
    },
]


def format_message(feed_name, entry):
    title = entry.get("title", "No title").strip()
    link = entry.get("link", "").strip()
    summary = entry.get("summary", "").strip()

    if summary:
        return {
            "content": f"**{title}**\n\n{summary}\n\n🔗 {link}"
        }

    return {
        "content": f"**{title}**\n\n🔗 {link}"
    }


def post_to_discord(payload):
    response = requests.post(
        DISCORD_WEBHOOK,
        json=payload,
        timeout=20
    )
    response.raise_for_status()


def fetch_feed(feed):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }

    response = requests.get(
        feed["url"],
        headers=headers,
        timeout=20,
        allow_redirects=True
    )

    print(f"[DEBUG] {feed['name']} HTTP status: {response.status_code}")
    print(f"[DEBUG] {feed['name']} content-type: {response.headers.get('Content-Type')}")

    response.raise_for_status()

    parsed = feedparser.parse(response.content)

    print(f"[DEBUG] {feed['name']} entries found: {len(parsed.entries)}")

    if getattr(parsed, "bozo", 0):
        print(f"[WARN] Feed issue: {feed['name']} | bozo={parsed.bozo}")
        print(f"[WARN] Feed exception: {getattr(parsed, 'bozo_exception', 'No exception')}")

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

        try:
            payload = format_message(feed["name"], latest_entry)
            post_to_discord(payload)

            print(f"[SENT] {feed['name']} - {latest_entry.get('title', 'No title')}")
            total_sent += 1

        except Exception as e:
            print(f"[ERROR] Failed posting latest article from {feed['name']}: {e}")

    print(f"[DONE] Sent {total_sent} test articles at {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
