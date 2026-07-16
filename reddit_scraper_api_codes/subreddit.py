"""
Reddit Subreddit listing - Chocodata Reddit Scraper API

Runnable example. It calls the LIVE API and prints the real JSON response.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python reddit_scraper_api_codes/subreddit.py

Docs: https://chocodata.com/docs
"""
import json
import os
import sys

import requests

API = "https://api.chocodata.com/api/v1/reddit/subreddit"
KEY = os.environ.get("CHOCODATA_API_KEY")

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
        sys.exit(f"404 item_not_found: {r.json().get('message', 'does not exist')} (not retryable, not charged)")
    if r.status_code == 502:
        sys.exit("502: Reddit refused every attempt for this request. Retryable, and you were not charged.")
    r.raise_for_status()


def subreddit(name: str, sort: str = "hot", limit: int = 25, t: str = None, after: str = None) -> dict:
    """Fetch a subreddit listing with real scores, comment counts and upvote ratios."""
    params = {"api_key": KEY, "subreddit": name, "sort": sort, "limit": limit}
    if t:
        params["t"] = t
    if after:
        params["after"] = after
    r = requests.get(API, params=params, timeout=90)
    _check(r)
    return r.json()


if __name__ == "__main__":
    data = subreddit("Python", sort="hot")
    print(json.dumps(data, indent=2)[:1800])
    print()
    for p in data["posts"][:8]:
        print(f'  [{str(p["score"]):>6}] {(p["title"] or "")[:56]:58s} c={p["num_comments"]} ratio={p["upvote_ratio"]}')
    print()
    print(f'r/{data["subreddit"]} | {data["total_results"]} posts | sort={data["sort"]} | source={data["_source"]}')
