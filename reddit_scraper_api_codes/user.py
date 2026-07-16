"""
Reddit User profile feed - Chocodata Reddit Scraper API

Runnable example. It calls the LIVE API and prints the real JSON response.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python reddit_scraper_api_codes/user.py

This example uses u/spez (Reddit's CEO), a public figure whose account is
public by definition. Point it at whatever public account your use case needs.

Docs: https://chocodata.com/docs
"""
import json
import os
import sys

import requests

API = "https://api.chocodata.com/api/v1/reddit/user"
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
        sys.exit("404 item_not_found: no such user, or the account is suspended/deleted. Not charged.")
    if r.status_code == 502:
        sys.exit("502: Reddit refused every attempt for this request. Retryable, and you were not charged.")
    r.raise_for_status()


def user(username: str, kind: str = "overview", limit: int = 25) -> dict:
    """Fetch a public user's recent submissions and/or comments."""
    params = {"api_key": KEY, "username": username, "kind": kind, "limit": limit}
    r = requests.get(API, params=params, timeout=90)
    _check(r)
    return r.json()


if __name__ == "__main__":
    data = user("spez")
    print(json.dumps(data, indent=2)[:1500])
    print()
    for it in data["items"][:8]:
        where = f'r/{it["subreddit"]}' if it["subreddit"] else "-"
        text = (it["title"] or it["body"] or "")
        print(f'  [{it["type"]:10s}] {where:20s} {" ".join(text.split())[:46]}')
    print()
    kinds = {}
    for it in data["items"]:
        kinds[it["type"]] = kinds.get(it["type"], 0) + 1
    print(f'u/{data["profile"]["username"]} | {data["total_results"]} items {kinds} | source={data["_source"]}')
