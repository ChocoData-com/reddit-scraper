"""
Reddit Post + comment tree - Chocodata Reddit Scraper API

Runnable example. It calls the LIVE API and prints the real JSON response.

    pip install requests
    export CHOCODATA_API_KEY="your_key"      # free: 1,000 requests, one-time
    python reddit_scraper_api_codes/post.py

NOTE on `subreddit`: pass it exactly as Reddit spells it ("Python", not
"python"). The casing is used to build the post-page URL, and the wrong casing
returns HTTP 200 with a null post object (the comment tree still arrives).
Passing the full post `url` instead avoids the issue entirely.

Docs: https://chocodata.com/docs
"""
import json
import os
import sys

import requests

API = "https://api.chocodata.com/api/v1/reddit/post"
KEY = os.environ.get("CHOCODATA_API_KEY")

if not KEY:
    sys.exit("Set CHOCODATA_API_KEY first. Free key (1,000 requests, one-time): https://chocodata.com")


def _check(r) -> None:
    """Map the API's documented errors onto actionable messages instead of a traceback."""
    if r.status_code == 400:
        sys.exit(f"400 invalid_params: {r.json().get('issues', 'pass post_id (+ subreddit) or a full url')}")
    if r.status_code == 401:
        sys.exit("401 INVALID_API_KEY: key missing or not recognised. Get one: https://chocodata.com")
    if r.status_code == 402:
        sys.exit("402 INSUFFICIENT_CREDITS: balance exhausted. Top up or upgrade: https://chocodata.com/pricing")
    if r.status_code == 429:
        sys.exit("429 RATE_LIMITED: over your plan's concurrency. Back off and retry.")
    if r.status_code == 404:
        sys.exit(f"404 item_not_found: {r.json().get('message', 'post removed or does not exist')} (not charged)")
    if r.status_code == 502:
        sys.exit("502: Reddit refused every attempt for this request. Retryable, and you were not charged.")
    r.raise_for_status()


def post(post_id: str = None, subreddit: str = None, url: str = None, sort: str = "top") -> dict:
    """Fetch one post plus its nested comment tree."""
    params = {"api_key": KEY, "sort": sort}
    if url:
        params["url"] = url
    else:
        params["post_id"] = post_id
        if subreddit:
            params["subreddit"] = subreddit
    r = requests.get(API, params=params, timeout=90)
    _check(r)
    return r.json()


def walk(comments, depth=0):
    """Print the nested tree the way it actually nests."""
    for c in comments:
        body = " ".join((c["body"] or "").split())[:60]
        print(f'{"    " * depth}- [{str(c["score"]):>5}] u/{c["author"]["username"]}: {body}')
        walk(c["replies"], depth + 1)


if __name__ == "__main__":
    data = post(post_id="1uuuf9c", subreddit="Python")
    p = data["post"]

    if p["title"] is None:
        print("WARNING: null post object. Check the subreddit casing, or retry.")

    print(json.dumps(data, indent=2)[:1500])
    print()
    print(f'{p["title"]}')
    print(f'  u/{p["author"]["username"]} | score {p["score"]} | ratio {p["upvote_ratio"]} | {p["num_comments"]} comments')
    print()
    walk(data["comments"])
    print()
    print(f'{data["comments_returned"]} of {p["num_comments"]} comments returned '
          f'(truncated={data["_meta"]["truncated"]})')
