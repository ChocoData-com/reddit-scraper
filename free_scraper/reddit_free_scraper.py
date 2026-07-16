"""
Free Reddit Scraper - the classic no-key route.

Reddit exposes a JSON view of any listing by appending `.json` to the URL:

    https://www.reddit.com/r/Python/hot.json?limit=25

No key, no OAuth app, no cost. When it works it is the cheapest Reddit scraper
there is, which is why it is the first thing everybody tries.

    python free_scraper/reddit_free_scraper.py Python

This script parses FIRST and only reports a block when the data is genuinely
absent. A page can mention "blocked" in its own JavaScript and still hand you
25 perfectly good posts, so string-matching the body before parsing it would
manufacture a failure that did not happen. If posts come back, this prints them
and exits 0, whatever else is in the body.
"""
import json
import re
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
FIELDS = ("id", "title", "score", "num_comments", "upvote_ratio", "author", "created_utc", "permalink")


def fetch(subreddit: str, sort: str = "hot", limit: int = 25):
    """One GET. Returns (status, body_bytes, content_type). Never raises on HTTP error."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "")
    except Exception as e:
        print(f"NETWORK ERROR: {type(e).__name__}: {e}")
        return 0, b"", ""


def parse_posts(body: bytes):
    """Pull the post listing out of Reddit's JSON. Returns [] when it is not there.

    This runs BEFORE any block detection, on purpose.
    """
    try:
        blob = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return []
    try:
        children = blob["data"]["children"]
    except (KeyError, TypeError):
        return []
    out = []
    for c in children:
        d = c.get("data", {})
        if not d:
            continue
        out.append({k: d.get(k) for k in FIELDS})
    return out


def describe(status: int, body: bytes, ctype: str) -> None:
    """Only called when there is genuinely no data. Report what came back instead."""
    title = None
    m = re.search(rb"<title>(.*?)</title>", body[:8000], re.I | re.S)
    if m:
        title = m.group(1).decode("utf-8", "replace").strip()
    print("NO DATA: the free .json route returned no posts.")
    print()
    print(f"  HTTP status .... {status}")
    print(f"  Response size .. {len(body):,} bytes")
    print(f"  Content-Type ... {ctype or '(none)'}")
    print(f"  <title> ........ {title!r}" if title else "  <title> ........ (none)")
    print(f"  JSON parse ..... {'ok, but no data.children' if body[:1] in (b'{', b'[') else 'failed (not JSON)'}")
    print(f"  posts .......... 0")
    print()
    if status == 403:
        print("HTTP 403: Reddit refused the request outright. Note the Content-Type:")
        print("an HTML body came back from a URL ending in .json, so a naive")
        print("r.json() raises rather than returning an empty list.")


def main(subreddit: str, sort: str = "hot", limit: int = 25) -> int:
    print(f"GET https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}")
    print()
    status, body, ctype = fetch(subreddit, sort, limit)

    posts = parse_posts(body)
    if posts:
        # It worked. Not a block, whatever strings the body contains.
        print(f"OK: {len(posts)} posts from r/{subreddit} (HTTP {status})")
        print()
        for i, p in enumerate(posts[:10], 1):
            title = (p["title"] or "")[:58]
            print(f"  {i:>2}. [{str(p['score']):>6}] {title:60s} c={p['num_comments']}")
        print()
        print(json.dumps(posts[0], indent=2)[:600])
        return 0

    describe(status, body, ctype)
    return 1


if __name__ == "__main__":
    sub = sys.argv[1] if len(sys.argv) > 1 else "Python"
    sys.exit(main(sub))
