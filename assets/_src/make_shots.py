"""Render developer-journey screenshots from REAL captured session output.

Follows the pattern oxylabs/amazon-scraper uses: a terminal shot of the command
actually running, then a table shot of the data it retrieved.

The text rendered here is the verbatim stdout of a real run (captured to
$QA/*.out) and the real committed JSON. The shell prompt is deliberately generic
so no local username or path is exposed.
"""
import json
import os
import re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..")
DATA = os.path.join(OUT, "..", "reddit_scraper_api_data")
QA = os.environ.get("QA_DIR") or os.path.expandvars(r"%TEMP%\qa")
F = "C:/Windows/Fonts/"

MONO = ImageFont.truetype(F + "consola.ttf", 15)
MONOB = ImageFont.truetype(F + "consolab.ttf", 15)
UI = ImageFont.truetype(F + "segoeui.ttf", 14)
UIB = ImageFont.truetype(F + "seguisb.ttf", 14)

BG, FG, DIM = (13, 15, 19), (208, 205, 200), (110, 106, 100)
GREEN, BLUE, AMBER, RED, CYAN = (126, 209, 138), (127, 178, 255), (255, 196, 138), (232, 118, 118), (120, 205, 210)

SECRET = re.compile(r"asa_live_[A-Za-z0-9_\-]+")


def sanitize(s: str) -> str:
    """Never leak a key, a local path, or a username into an image."""
    s = SECRET.sub("$CHOCODATA_API_KEY", s)
    s = re.sub(r"[A-Za-z]:\\Users\\[^\\\s]+", "~", s)
    s = re.sub(r"/c/Users/[^/\s]+", "~", s)
    s = s.replace(os.environ.get("USERNAME", "\0"), "dev")
    return s


def terminal(lines, path, width=1180, title="bash"):
    pad, lh = 18, 23
    h = 46 + pad * 2 + lh * len(lines)
    img = Image.new("RGB", (width, h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 38], fill=(24, 26, 31))
    for i, c in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]):
        d.ellipse([16 + i * 20, 14, 26 + i * 20, 24], fill=c)
    d.text((width // 2 - 30, 11), title, font=UI, fill=DIM)
    y = 38 + pad
    for text, color, bold in lines:
        d.text((pad, y), text, font=MONOB if bold else MONO, fill=color)
        y += lh
    img.save(os.path.join(OUT, path))
    print("wrote assets/" + path, img.size)


def read_out(name):
    p = os.path.join(QA, name)
    return sanitize(open(p, encoding="utf-8", errors="replace").read()) if os.path.exists(p) else ""


def shot_run():
    """The API call actually running: what a developer sees."""
    out = read_out("subreddit.out").strip().splitlines()
    body = [l for l in out if l.strip()]
    head, tail = body[:14], body[-1]
    lines = [('$ export CHOCODATA_API_KEY="your_key"', GREEN, True),
             ("$ python reddit_scraper_api_codes/subreddit.py", GREEN, True), ("", FG, False)]
    for l in head:
        c = FG
        if re.search(r'"\w+":', l):
            c = BLUE
        if re.search(r": \d", l):
            c = AMBER
        lines.append((l[:110], c, False))
    lines += [("  ...", DIM, False), ("", FG, False), (tail[:110], CYAN, True)]
    terminal(lines, "run-subreddit.png", title="reddit-scraper")


def shot_blocked():
    """The free scraper hitting the wall, verbatim."""
    out = read_out("free.out").strip().splitlines()
    lines = [("$ python free_scraper/reddit_free_scraper.py Python", GREEN, True), ("", FG, False)]
    for l in out[:12]:
        hot = "NO DATA" in l
        lines.append((l[:105], RED if hot else FG, hot))
    terminal(lines, "run-blocked.png", title="reddit-scraper")


def shot_table():
    """Retrieved data as a table, the way oxylabs shows it."""
    s = json.load(open(os.path.join(DATA, "subreddit.json"), encoding="utf-8"))["posts"][:9]
    cols = [("#", 30), ("title", 316), ("id", 96), ("score", 56), ("comments", 76), ("ratio", 60), ("author", 130)]
    W = sum(c[1] for c in cols) + 40
    rh, hh = 30, 34
    H = 52 + hh + rh * len(s)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 14), "reddit_subreddit_posts  (r/Python, sort=hot)", font=UIB, fill=(30, 30, 30))
    x0, y0 = 20, 46
    d.rectangle([x0, y0, W - 20, y0 + hh], fill=(238, 238, 238))
    x = x0
    for name, w in cols:
        d.text((x + 9, y0 + 9), name, font=UIB, fill=(20, 20, 20))
        x += w
    y = y0 + hh
    for i, r in enumerate(s):
        if i % 2:
            d.rectangle([x0, y, W - 20, y + rh], fill=(250, 250, 250))
        ratio = f'{r["upvote_ratio"]:.2f}' if r["upvote_ratio"] is not None else "-"
        vals = [str(i), (r["title"] or "")[:42] + ("..." if len(r["title"] or "") > 42 else ""),
                r["id"], str(r["score"]), str(r["num_comments"]), ratio, (r["author"] or "-")[:16]]
        x = x0
        for (name, w), v in zip(cols, vals):
            d.text((x + 9, y + 7), v, font=MONO if name in ("id", "score", "comments", "ratio") else UI,
                   fill=(60, 60, 60) if name != "#" else (150, 150, 150))
            x += w
        d.line([(x0, y), (W - 20, y)], fill=(226, 226, 226))
        y += rh
    d.line([(x0, y), (W - 20, y)], fill=(226, 226, 226))
    for i in range(len(cols) + 1):
        xx = x0 + sum(c[1] for c in cols[:i])
        d.line([(xx, y0), (xx, y)], fill=(226, 226, 226))
    img.save(os.path.join(OUT, "retrieved-data.png"))
    print("wrote assets/retrieved-data.png", img.size)


def shot_post():
    """The comment tree: a different data shape, rendered from the real run."""
    body = [l for l in read_out("post.out").strip().splitlines() if l.strip()]
    # skip the raw JSON dump head; start at the human summary
    start = next((i for i, l in enumerate(body) if l.startswith("Will PEP")), 0)
    sel = body[start:start + 15]
    lines = [("$ python reddit_scraper_api_codes/post.py", GREEN, True), ("", FG, False)]
    for l in sel:
        c = FG
        if l.strip().startswith("- ["):
            c = AMBER
        if l.startswith("Will PEP") or l.startswith("  u/"):
            c = BLUE
        lines.append((l[:110], c, l.startswith("Will PEP")))
    lines += [("", FG, False), (body[-1][:110], CYAN, True)]
    terminal(lines, "run-post.png", title="reddit-scraper")


def shot_monitor():
    """The use case: brand mention monitoring, real first run."""
    body = [l for l in read_out("monitor.out").strip().splitlines() if l.strip()]
    lines = [('$ python reddit_scraper_api_codes/mention_monitor.py "duckdb"', GREEN, True), ("", FG, False)]
    for l in body[:13]:
        c = FG
        if "NEW" in l:
            c = AMBER
        if l.strip().startswith("https://"):
            c = DIM
        lines.append((l[:108], c, l.startswith('"duckdb"')))
    lines += [("  ...", DIM, False)]
    terminal(lines, "run-monitor.png", title="reddit-scraper")


def shot_error():
    """The error UX: what a bad key actually gives you. Trust-building."""
    out = read_out("badkey.out").strip().splitlines()
    lines = [('$ export CHOCODATA_API_KEY="wrong_key"', GREEN, True),
             ("$ python reddit_scraper_api_codes/subreddit.py", GREEN, True), ("", FG, False)]
    for l in out[:4]:
        lines.append((l[:105], RED, True))
    lines += [("", FG, False),
              ("# no traceback, no silent empty list: every documented error", DIM, False),
              ("# maps to a message that tells you what to do next.", DIM, False)]
    terminal(lines, "run-error.png", title="reddit-scraper")


if __name__ == "__main__":
    shot_run()
    shot_blocked()
    shot_table()
    shot_post()
    shot_monitor()
    shot_error()
