import os
import re
from html import unescape
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


def clean_html(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = " ".join(text.split())

    return text


def format_message(entry):
    title = entry.get("title", "No title").strip()
    link = entry.get("link", "").strip()

    summary = (
        entry.get("summary")
        or entry.get("description")
        or ""
    )

    summary = clean_html(summary)

    if len(summary) > 300:
        summary = summary[:297] + "..."

    embed = {
        "title": title,
        "url": link,
        "color": 0xF7931A,
    }

    if summary:
        embed["description"] = summary

    image_url = None

    if "media_content" in entry and entry.media_content:
        image_url = entry.media_content[0].get("url")

    if not image_url and "media_thumbnail" in entry and entry.media_thumbnail:
        image_url = entry.media_thumbnail[0].get("url")

    if image_url:
        embed["image"] = {
            "url": image_url
        }

    return {
        "embeds": [embed]
    }


def post_to_discord(payload):
    response = requests.post(
        DISCORD_WEBHOOK,
        json=payload,
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
        print(
            f"[WARN] Feed issue: "
            f"{feed['name']} | bozo={parsed.bozo}"
        )

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
            print(
                f"[ERROR] Failed reading "
                f"{feed['name']}: {e}"
            )
            continue

        if not entries:
            print(f"[WARN] No entries found for {feed['name']}")
            continue

        latest_entry = entries[0]

        try:
            payload = format_message(latest_entry)

            post_to_discord(payload)

            print(
                f"[SENT] "
                f"{feed['name']} - "
                f"{latest_entry.get('title', 'No title')}"
            )

            total_sent += 1

        except Exception as e:
            print(
                f"[ERROR] Failed posting "
                f"{feed['name']}: {e}"
            )

    print(
        f"[DONE] Sent {total_sent} test articles at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )


if __name__ == "__main__":
    main()
