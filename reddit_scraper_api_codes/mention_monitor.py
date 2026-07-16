"""
Reddit brand / keyword mention monitoring - Chocodata Reddit Scraper API

Social listening is the main commercial reason to scrape Reddit: you want to
know when somebody mentions your product, and where, while the thread is still
live enough to reply to.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python reddit_scraper_api_codes/mention_monitor.py "kubernetes"

Every observation is stored in a local SQLite dataset (reddit_mentions.db), so
each run prints only what is NEW since the last one. Export to CSV with:

    sqlite3 reddit_mentions.db ".mode csv" ".headers on" \
            "select * from mentions order by first_seen desc" > mentions.csv

Schedule it (cron / GitHub Actions) and it becomes a mention feed.

Cost: 1 request for the search, plus 1 per post enriched with its real score
(--enrich N, default 3). Docs: https://chocodata.com/docs
"""
import os
import sqlite3
import sys
import time

import requests

BASE = "https://api.chocodata.com/api/v1/reddit"
KEY = os.environ.get("CHOCODATA_API_KEY")
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reddit_mentions.db")

if not KEY:
    sys.exit("Set CHOCODATA_API_KEY first. Free key (1,000 requests, one-time): https://chocodata.com")


def _check(r) -> None:
    """Map the API's documented errors onto actionable messages instead of a traceback."""
    if r.status_code == 400:
        sys.exit(f"400 invalid_params: {r.json().get('issues', 'check your query string')}")
    if r.status_code == 401:
        sys.exit("401 INVALID_API_KEY: key missing or not recognised. Get one: https://chocodata.com")
    if r.status_code == 402:
        sys.exit("402 INSUFFICIENT_CREDITS: balance exhausted. Top up or upgrade: https://chocodata.com/pricing")
    if r.status_code == 429:
        sys.exit("429 RATE_LIMITED: over your plan's concurrency. Back off and retry.")
    if r.status_code == 404:
        sys.exit("404 item_not_found: not retryable, and you were not charged.")
    if r.status_code == 502:
        sys.exit("502: Reddit refused every attempt for this request. Retryable, and you were not charged.")
    r.raise_for_status()


def db():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS mentions (
                    id TEXT PRIMARY KEY, keyword TEXT, result_type TEXT, title TEXT,
                    author TEXT, subreddit TEXT, permalink TEXT, created TEXT,
                    score INTEGER, num_comments INTEGER, first_seen REAL)""")
    return c


def search(q: str, sort: str = "new", limit: int = 25) -> dict:
    """Most recent mentions of `q` anywhere on Reddit."""
    r = requests.get(f"{BASE}/search", params={"api_key": KEY, "q": q, "sort": sort, "limit": limit}, timeout=90)
    _check(r)
    return r.json()


def enrich(post_id: str, subreddit: str) -> dict | None:
    """reddit/search runs on a surface that carries no vote data, so `score` is
    null on every search hit. One reddit/post call per thread fills it in."""
    r = requests.get(f"{BASE}/post",
                     params={"api_key": KEY, "post_id": post_id.replace("t3_", ""), "subreddit": subreddit},
                     timeout=90)
    if r.status_code != 200:
        return None
    return r.json().get("post")


def main(keyword: str, enrich_n: int = 3) -> int:
    con = db()
    data = search(keyword)
    hits = [r for r in data["results"] if r["result_type"] == "post"]

    known = {row[0] for row in con.execute("SELECT id FROM mentions WHERE keyword = ?", (keyword,))}
    fresh = [h for h in hits if h["id"] not in known]

    # Fill in real scores for the newest few. `subreddit` comes back canonically
    # cased from search, which is exactly what reddit/post needs.
    scored = 0
    for h in fresh[:enrich_n]:
        if not h["subreddit"]:
            continue
        p = enrich(h["id"], h["subreddit"])
        if p and p["score"] is not None:
            h["score"], h["num_comments"] = p["score"], p["num_comments"]
            scored += 1
        time.sleep(0.2)

    now = time.time()
    for h in fresh:
        con.execute("INSERT OR IGNORE INTO mentions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (h["id"], keyword, h["result_type"], h["title"], h["author"], h["subreddit"],
                     h["permalink"], h["created"], h.get("score"), h.get("num_comments"), now))
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM mentions WHERE keyword = ?", (keyword,)).fetchone()[0]

    print(f'"{keyword}": {len(hits)} post results this run | {len(fresh)} new | '
          f'{scored} enriched with a live score | {total} tracked in {os.path.basename(DB)}')
    print()
    if not fresh:
        print("No new mentions since the last run. Schedule it (cron / GitHub Actions) and")
        print("this becomes a feed of every new Reddit thread that names your keyword.")
        return 0
    for h in fresh:
        score = f'[{h["score"]:>5}]' if h.get("score") is not None else "[  n/a]"
        print(f'  NEW {score} r/{h["subreddit"]:<22s} {(h["title"] or "")[:52]}')
        print(f'              {h["permalink"]}')
    return 0


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "kubernetes"
    sys.exit(main(kw))
