import os
import json
import hashlib
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


def format_message(entry):
    title = entry.get("title", "No title").strip()
    link = entry.get("link", "").strip()

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
    parsed = feedparser.parse(
        feed["url"],
        request_headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    entries_count = len(parsed.entries)
    print(f"[DEBUG] {feed['name']} entries found: {entries_count}")

    if entries_count > 0:
        first_title = parsed.entries[0].get("title", "No title")
        first_link = parsed.entries[0].get("link", "No link")
        print(f"[DEBUG] {feed['name']} first title: {first_title}")
        print(f"[DEBUG] {feed['name']} first link: {first_link}")

    if getattr(parsed, "bozo", 0):
        print(f"[WARN] Feed issue: {feed['name']} | bozo={parsed.bozo}")
        print(f"[WARN] Feed exception: {getattr(parsed, 'bozo_exception', 'No exception')}")

    return parsed.entries


def main():
    if not DISCORD_WEBHOOK:
        raise ValueError(
            "Missing DISCORD_WEBHOOK environment variable"
        )

    seen = load_seen()
    seen_set = set(seen)
    new_seen = list(seen)

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

        entries = list(entries[:5])
        entries.reverse()

        sent_for_feed = 0

        for entry in entries:

            article_id = make_id(entry)

            if article_id in seen_set:
                continue

            try:
                payload = format_message(entry)

                post_to_discord(payload)

                print(
                    f"[SENT] "
                    f"{entry.get('title', 'No title')}"
                )

                seen_set.add(article_id)
                new_seen.append(article_id)

                total_sent += 1
                sent_for_feed += 1

            except Exception as e:
                print(
                    f"[ERROR] Failed posting article: {e}"
                )

        print(f"[DEBUG] {feed['name']} sent this run: {sent_for_feed}")

    save_seen(new_seen)

    print(
        f"[DONE] Sent {total_sent} new articles at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )


if __name__ == "__main__":
    main()
