"""
Reddit Search - Chocodata Reddit Scraper API

Runnable example. It calls the LIVE API and prints the real JSON response.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python reddit_scraper_api_codes/search.py

Docs: https://chocodata.com/docs
"""
import json
import os
import sys

import requests

API = "https://api.chocodata.com/api/v1/reddit/search"
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


def search(q: str, subreddit: str = None, sort: str = "relevance", t: str = None, limit: int = 25) -> dict:
    """Search Reddit site-wide, or inside one subreddit."""
    params = {"api_key": KEY, "q": q, "sort": sort, "limit": limit}
    if subreddit:
        params["subreddit"] = subreddit
    if t:
        params["t"] = t
    r = requests.get(API, params=params, timeout=90)
    _check(r)
    return r.json()


if __name__ == "__main__":
    data = search("web scraping")
    print(json.dumps(data, indent=2)[:1600])
    print()
    for r_ in data["results"][:8]:
        sub = f'r/{r_["subreddit"]}' if r_["subreddit"] else "-"
        print(f'  {r_["position"]:>2}. [{r_["result_type"]:9s}] {sub:22s} {(r_["title"] or "")[:46]}')
    print()
    posts = [r_ for r_ in data["results"] if r_["result_type"] == "post"]
    print(f'"{data["query"]}" | {data["total_results"]} results ({len(posts)} posts) | source={data["_source"]}')
