#!/usr/bin/env python3
"""Render one monochrome metrics panel for the profile README."""

import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "altrml")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "assets")
OUT_FILE = os.path.join(OUT_DIR, "stats.svg")

W, H = 880, 220
BG = "#0d1117"
FG = "#ffffff"
MUTED = "#8a8a8a"
DIM = "#c9d1d9"
LINE = "#262626"
TRACK = "#181818"
FONT = 'ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace'

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 6, orderBy: { field: SIZE, direction: DESC }) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def gql(query, variables):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": "bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "altrml-profile-stats",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def esc(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def trim(value):
    text = "%.1f" % value
    return text[:-2] if text.endswith(".0") else text


def fmt(number):
    n = int(number)
    if n >= 1000000:
        return trim(n / 1000000.0) + "M"
    if n >= 1000:
        return trim(n / 1000.0) + "k"
    return str(n)


STYLE = (
    "<defs><style>"
    ".mono{font-family:" + FONT + "}"
    ".lbl{font-size:9.5px;letter-spacing:2.4px;fill:" + MUTED + "}"
    ".val{font-size:30px;font-weight:700;letter-spacing:1px;fill:" + FG + "}"
    ".sub{font-size:10.5px;letter-spacing:1.4px;fill:" + MUTED + "}"
    ".col{font-size:9px;letter-spacing:2px;fill:#6e7681}"
    ".row{animation:rise .6s cubic-bezier(.2,.7,.3,1) both}"
    "@keyframes rise{from{opacity:.3;transform:translateY(6px)}to{opacity:1;transform:none}}"
    ".scan{animation:sweep 7s linear infinite}"
    "@keyframes sweep{0%{transform:translateY(-50px)}100%{transform:translateY(230px)}}"
    "</style>"
    '<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#ffffff" stop-opacity="0"/>'
    '<stop offset=".5" stop-color="#ffffff" stop-opacity=".04"/>'
    '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/>'
    "</linearGradient></defs>"
)


def frame():
    return (
        '<rect x="0.5" y="0.5" width="' + str(W - 1) + '" height="' + str(H - 1)
        + '" rx="10" fill="' + BG + '" stroke="' + LINE + '"/>'
        '<rect x="0" y="0" width="' + str(W) + '" height="' + str(H)
        + '" rx="10" fill="url(#scan)" class="scan" opacity=".9"/>'
    )


def stat_cell(label, value, x, y, delay):
    return (
        '<g class="row" style="animation-delay:' + str(delay) + 'ms">'
        '<text class="mono lbl" x="' + str(x) + '" y="' + str(y - 26) + '">' + label + "</text>"
        '<text class="mono val" x="' + str(x) + '" y="' + str(y) + '">' + esc(value) + "</text>"
        "</g>"
    )


def lang_row(name, percent, y, delay):
    width = max(6.0, min(150.0, percent * 1.5))
    return (
        '<g class="row" style="animation-delay:' + str(delay) + 'ms">'
        '<text class="mono sub" x="480" y="' + str(y) + '" fill="' + DIM + '">' + esc(name) + "</text>"
        '<rect x="650" y="' + str(y - 9) + '" width="150" height="6" rx="3" fill="' + TRACK + '"/>'
        '<rect x="650" y="' + str(y - 9) + '" width="0" height="6" rx="3" fill="' + FG + '" fill-opacity=".9">'
        '<animate attributeName="width" from="0" to="' + ("%.1f" % width) + '" dur="1.1s" begin="'
        + str(delay) + 'ms" fill="freeze"/>'
        "</rect>"
        '<text class="mono sub" x="852" y="' + str(y) + '" text-anchor="end">' + ("%.0f" % percent) + "%</text>"
        "</g>"
    )


def build(user):
    repos = user["repositories"]["totalCount"]
    stars = sum(node["stargazerCount"] for node in user["repositories"]["nodes"])
    followers = user["followers"]["totalCount"]
    cc = user["contributionsCollection"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]

    totals = {}
    for node in user["repositories"]["nodes"]:
        for edge in node["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
    grand = sum(totals.values()) or 1

    body = '<text class="mono lbl" x="28" y="34">METRICS</text>'
    body += '<text class="mono sub" x="852" y="34" text-anchor="end">@' + esc(USER) + "</text>"
    body += '<line x1="28" y1="48" x2="852" y2="48" stroke="' + LINE + '"/>'
    body += '<line x1="214" y1="72" x2="214" y2="182" stroke="' + LINE + '"/>'
    body += '<line x1="455" y1="66" x2="455" y2="196" stroke="' + LINE + '"/>'

    body += stat_cell("REPOS", fmt(repos), 28, 100, 0)
    body += stat_cell("STARS", fmt(stars), 240, 100, 70)
    body += stat_cell("COMMITS 1Y", fmt(commits), 28, 172, 140)
    body += stat_cell("FOLLOWERS", fmt(followers), 240, 172, 210)

    body += '<text class="mono lbl" x="480" y="76">STACK</text>'
    body += '<text class="mono sub" x="852" y="76" text-anchor="end">BY BYTES</text>'

    if ranked:
        y = 106
        for index, (name, size) in enumerate(ranked):
            body += lang_row(name, size * 100.0 / grand, y, 120 + index * 90)
            y += 22
    else:
        body += '<text class="mono sub" x="480" y="110">awaiting first commit</text>'

    body += '<text class="mono sub" x="28" y="206">' + fmt(prs) + " pr / " + fmt(issues) + " issues</text>"
    body += (
        '<text class="mono sub" x="852" y="206" text-anchor="end">'
        + fmt(repos) + (" repo tracked" if repos == 1 else " repos tracked") + "</text>"
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(W) + '" height="' + str(H)
        + '" viewBox="0 0 ' + str(W) + " " + str(H)
        + '" role="img" aria-label="altrml metrics">'
        + STYLE + frame() + body + "</svg>"
    )


LEVELS = ("#161b22", "#2a2a2a", "#454545", "#8a8a8a", "#ffffff")


def level_of(count):
    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
ACT_H = 196


def streaks(days):
    best = 0
    run = 0
    for day in days:
        if day["contributionCount"] > 0:
            run += 1
            best = max(best, run)
        else:
            run = 0

    current = 0
    for day in reversed(days):
        if day["contributionCount"] > 0:
            current += 1
        else:
            break
    return current, best


def build_activity(user):
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"][-53:]
    total = calendar["totalContributions"]

    days = [day for week in weeks for day in week["contributionDays"]]
    current, best = streaks(days)

    x0, y0, pitch, size = 28.0, 74.0, 15.6, 12.0
    body = '<text class="mono lbl" x="28" y="34">ACTIVITY</text>'
    body += '<text class="mono sub" x="852" y="34" text-anchor="end">LAST 12 MONTHS</text>'
    body += '<line x1="28" y1="48" x2="852" y2="48" stroke="' + LINE + '"/>'

    previous_month = None
    for week_index, week in enumerate(weeks):
        stamp = week["contributionDays"][0]["date"]
        month = int(stamp[5:7])
        if month != previous_month:
            previous_month = month
            body += (
                '<text class="mono col" x="' + ("%.0f" % (x0 + week_index * pitch))
                + '" y="64">' + MONTHS[month - 1] + "</text>"
            )

    body += '<g class="row">'
    for week_index, week in enumerate(weeks):
        for day_index, day in enumerate(week["contributionDays"]):
            shade = LEVELS[level_of(day["contributionCount"])]
            body += (
                '<rect x="' + ("%.0f" % (x0 + week_index * pitch)) + '" y="'
                + ("%.0f" % (y0 + day_index * 13)) + '" width="' + ("%.0f" % size)
                + '" height="' + ("%.0f" % size) + '" rx="2" fill="' + shade + '"/>'
            )
    body += "</g>"

    label = "%d contribution" % total if total == 1 else "%d contributions" % total
    body += '<text class="mono sub" x="28" y="186">' + label + "</text>"

    body += '<text class="mono sub" x="470" y="186">LESS</text>'
    for index in range(4):
        body += (
            '<rect x="' + str(510 + index * 13) + '" y="177" width="9" height="9" rx="2" fill="'
            + LEVELS[index + 1] + '"/>'
        )
    body += '<text class="mono sub" x="566" y="186">MORE</text>'

    streak = "current %dd / best %dd" % (current, best)
    body += '<text class="mono sub" x="852" y="186" text-anchor="end">' + streak + "</text>"

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(W) + '" height="' + str(ACT_H)
        + '" viewBox="0 0 ' + str(W) + " " + str(ACT_H) + '" role="img" aria-label="altrml activity">'
        + STYLE + frame_activity() + body + "</svg>"
    )


def frame_activity():
    return (
        '<rect x="0.5" y="0.5" width="' + str(W - 1) + '" height="' + str(ACT_H - 1)
        + '" rx="10" fill="' + BG + '" stroke="' + LINE + '"/>'
    )


def main():
    if not TOKEN:
        print("missing GH_TOKEN", file=sys.stderr)
        return 1

    user = gql(QUERY, {"login": USER})["user"]
    os.makedirs(OUT_DIR, exist_ok=True)

    outputs = (
        ("stats.svg", build(user)),
        ("activity.svg", build_activity(user)),
    )
    for name, content in outputs:
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        print("%s %d bytes" % (name, len(content)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
