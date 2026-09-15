"""Refresh the open profile header using only publicly visible GitHub data."""

import argparse
from collections import Counter
from datetime import date, datetime, timezone
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "theablemo"
PALETTES = {
    "light": {"fg": "1f2328", "muted": "59636e", "line": "d1d9e0", "colors": ["0969da", "bc4c00", "8250df", "216e39", "59636e"]},
    "dark": {"fg": "f0f6fc", "muted": "a5aeb9", "line": "3d444d", "colors": ["79c0ff", "ffa657", "d2a8ff", "39d353", "a5aeb9"]},
}


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = {}
        self.tooltips = {}
        self.target = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-date") and attrs.get("id"):
            self.dates[attrs["id"]] = attrs["data-date"]
        if tag == "tool-tip":
            self.target = attrs.get("for")
            if self.target:
                self.tooltips[self.target] = ""

    def handle_data(self, value):
        if self.target:
            self.tooltips[self.target] += value

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.target = None


def parse_calendar(html, as_of):
    parser = CalendarParser()
    parser.feed(html)
    start = as_of.replace(month=1, day=1)
    days = {}
    for key, date_text in parser.dates.items():
        day = date.fromisoformat(date_text)
        if not start <= day <= as_of:
            continue
        tooltip = parser.tooltips.get(key, "").strip()
        match = re.match(r"(No|[\d,]+) contributions? on\b", tooltip)
        if not match:
            raise ValueError(f"Unrecognized contribution data for {date_text}")
        if date_text in days:
            raise ValueError(f"Duplicate contribution day: {date_text}")
        days[date_text] = 0 if match[1] == "No" else int(match[1].replace(",", ""))
    if len(days) != (as_of - start).days + 1:
        raise ValueError("Incomplete calendar; keeping the previous header")
    return days


def language_groups(repos):
    counts = Counter(r["language"] for r in repos if not r.get("fork") and not r.get("private") and r.get("language"))
    featured = ["Python", "Jupyter Notebook", "Java", "Dart"]
    groups = [(name, counts[name]) for name in featured]
    groups.append(("Other", sum(n for name, n in counts.items() if name not in featured)))
    return groups


def fetch(url):
    # No token is sent: these figures match what an anonymous profile visitor sees.
    return subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "3",
         "--max-time", "60", "-H", "Accept-Language: en-US", url],
        check=True, capture_output=True, text=True,
    ).stdout


def collect(as_of):
    year = as_of.year
    html = fetch(f"https://github.com/users/{USERNAME}/contributions?from={year}-01-01&to={as_of.isoformat()}")
    days = parse_calendar(html, as_of)
    repos = []
    for page in range(1, 101):
        batch = json.loads(fetch(f"https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}"))
        if not isinstance(batch, list):
            raise ValueError("Unexpected repository response")
        repos.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError("Repository pagination exceeded its limit")
    groups = language_groups(repos)
    if not sum(n for _, n in groups):
        raise ValueError("No language data; keeping the previous header")
    return {
        "as_of": as_of.isoformat(), "contributions": sum(days.values()),
        "active_days": sum(n > 0 for n in days.values()), "languages": groups,
        "contribution_scope": "Year-to-date activity visible on the public GitHub profile",
        "language_scope": "Primary language per public, non-fork repository with a detected language",
    }


def render(data, palette):
    from math import pi
    width, height = 740, 218
    split, left = width // 4, width // 4 + 22
    as_of = date.fromisoformat(data["as_of"])
    month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][as_of.month - 1]
    groups = data["languages"]
    total = sum(n for _, n in groups)
    parts = []

    def text(x, y, value, size=12, color=None, weight=400, anchor="start"):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="#{color or palette["muted"]}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')

    parts.append(f'<path d="M{split} 12V206" stroke="#{palette["line"]}"/>')
    text(4, 27, "GitHub activity", 14, palette["fg"], 600)
    text(4, 48, f"{as_of.year} · to {month} {as_of.day}", 11)
    text(4, 94, data["contributions"], 32, palette["fg"], 600)
    text(4, 114, "contributions")
    text(4, 153, data["active_days"], 20, palette["fg"], 600)
    text(4, 173, "active days")
    text(left, 27, "Across my public repositories", 14, palette["fg"], 600)
    text(left, 47, f"Primary language · {total} original repos", 11)
    cx, cy, radius = left + 58, 127, 47
    circumference, offset = 2 * pi * radius, 0
    for index, (name, count) in enumerate(groups):
        arc = count / total * circumference
        if count:
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#{palette["colors"][index]}" stroke-width="11" stroke-dasharray="{max(arc - 2, .1):.3f} {circumference - max(arc - 2, .1):.3f}" stroke-dashoffset="{-offset:.3f}" transform="rotate(-90 {cx} {cy})"/>')
        offset += arc
        y, x = 78 + index * 25, left + 136
        parts.append(f'<circle cx="{x}" cy="{y-4}" r="3.5" fill="#{palette["colors"][index]}"/>')
        text(x + 11, y, name, 12, palette["fg"])
        text(width - 7, y, count, anchor="end")
    text(cx, cy - 3, "Code", 12, palette["fg"], anchor="middle")
    text(cx, cy + 14, "mix", anchor="middle")
    text(width - 7, 203, "Repository count", 11, anchor="end")
    description = f'{as_of.year} through {month} {as_of.day}: {data["contributions"]} contributions on {data["active_days"]} active days. Primary languages: ' + ", ".join(f"{name}: {count} repositories" for name, count in groups)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">\n'
            '<title id="title">GitHub activity and public code mix</title>\n'
            f'<desc id="description">{escape(description)}</desc>\n'
            '<g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Arial, sans-serif">\n'
            + "\n".join(parts) + '\n</g>\n</svg>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Render an existing public data snapshot without fetching")
    args = parser.parse_args()
    data = json.loads(args.snapshot.read_text()) if args.snapshot else collect(datetime.now(timezone.utc).date())
    # Finish fetching and rendering before overwriting any existing assets.
    rendered = {theme: render(data, palette) for theme, palette in PALETTES.items()}
    for theme, svg in rendered.items():
        (ROOT / "profile" / f"header-{theme}.svg").write_text(svg)
    (ROOT / "profile" / "header-data.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f'Updated header through {data["as_of"]}: {data["contributions"]} contributions, {data["active_days"]} active days')


if __name__ == "__main__":
    main()
