#!/usr/bin/env python3
"""Generate monochrome profile stat cards from the GitHub GraphQL API."""

import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "altrml")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "assets")

BG = "#0d1117"
FG = "#ffffff"
MUTED = "#8a8a8a"
DIM = "#c9d1d9"
LINE = "#262626"
TRACK = "#1a1a1a"
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
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Authorization": "bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "altrml-profile-stats",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
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


def fmt(number):
    n = int(number)
    if n >= 1000000:
        return "%sM" % trim(n / 1000000.0)
    if n >= 1000:
        return "%sk" % trim(n / 1000.0)
    return str(n)


def trim(value):
    text = "%.1f" % value
    return text[:-2] if text.endswith(".0") else text


STYLE = (
    '<defs><style>'
    ".mono{font-family:" + FONT + "}"
    ".lbl{font-size:9.5px;letter-spacing:2.4px;fill:" + MUTED + "}"
    ".val{font-size:26px;font-weight:700;letter-spacing:1px;fill:" + FG + "}"
    ".sub{font-size:10.5px;letter-spacing:1.4px;fill:" + MUTED + "}"
    ".cell{animation:rise .55s cubic-bezier(.2,.7,.3,1) both}"
    "@keyframes rise{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}"
    ".scan{animation:sweep 7s linear infinite}"
    "@keyframes sweep{0%{transform:translateY(-40px)}100%{transform:translateY(170px)}}"
    "</style>"
    '<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#ffffff" stop-opacity="0"/>'
    '<stop offset=".5" stop-color="#ffffff" stop-opacity=".045"/>'
    '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/>'
    "</linearGradient></defs>"
)

FRAME = (
    '<rect x="0.5" y="0.5" width="419" height="161" rx="8" fill="' + BG
    + '" stroke="' + LINE + '"/>'
    '<rect x="0" y="0" width="420" height="162" fill="url(#scan)" class="scan" opacity=".9"/>'
)


def shell(label, body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="420" height="162" '
        'viewBox="0 0 420 162" role="img" aria-label="' + esc(label) + '">'
        + STYLE
        + FRAME
        + body
        + "</svg>"
    )


def header(title, right):
    out = '<text class="mono lbl" x="22" y="30">' + title + "</text>"
    out += '<text class="mono sub" x="398" y="30" text-anchor="end">' + right + "</text>"
    out += '<line x1="22" y1="42" x2="398" y2="42" stroke="' + LINE + '"/>'
    return out


def stats_svg(user):
    repos = user["repositories"]["totalCount"]
    stars = sum(node["stargazerCount"] for node in user["repositories"]["nodes"])
    followers = user["followers"]["totalCount"]
    cc = user["contributionsCollection"]
    commits = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    prs = cc["totalPullRequestContributions"]
    issues = cc["totalIssueContributions"]

    body = header("STATS", "@" + USER)
    body += '<line x1="210" y1="58" x2="210" y2="146" stroke="' + LINE + '"/>'

    cells = (
        ("REPOS", fmt(repos), 22, 82, 0),
        ("STARS", fmt(stars), 216, 82, 90),
        ("COMMITS 1Y", fmt(commits), 22, 136, 180),
        ("FOLLOWERS", fmt(followers), 216, 136, 270),
    )

    for label, value, x, y, delay in cells:
        body += (
            '<g class="cell" style="animation-delay:' + str(delay) + 'ms">'
            '<text class="mono lbl" x="' + str(x) + '" y="' + str(y - 16) + '">' + label + "</text>"
            '<text class="mono val" x="' + str(x) + '" y="' + str(y) + '">' + esc(value) + "</text>"
            "</g>"
        )

    body += (
        '<text class="mono sub" x="398" y="152" text-anchor="end">'
        + fmt(prs) + " pr / " + fmt(issues) + " issues</text>"
    )
    return shell("altrml stats", body)


def langs_svg(user):
    totals = {}
    for node in user["repositories"]["nodes"]:
        for edge in node["languages"]["edges"]:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"]

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
    grand = sum(totals.values()) or 1

    body = header("STACK", "BY BYTES")

    if not ranked:
        body += '<text class="mono sub" x="210" y="104" text-anchor="middle">awaiting first commit</text>'
        return shell("altrml languages", body)

    y = 76
    for index, (name, size) in enumerate(ranked):
        pct = size * 100.0 / grand
        width = max(5.0, min(150.0, (pct / 100.0) * 150.0))
        delay = index * 110
        body += (
            '<g class="cell" style="animation-delay:' + str(delay) + 'ms">'
            '<text class="mono sub" x="22" y="' + str(y - 4) + '" fill="' + DIM + '">'
            + esc(name) + "</text>"
            '<rect x="150" y="' + str(y - 10) + '" width="150" height="6" rx="3" fill="' + TRACK + '"/>'
            '<rect x="150" y="' + str(y - 10) + '" width="' + ("%.1f" % width) + '" height="6" rx="3" fill="' + FG + '" fill-opacity="0.9"/>'
            '<text class="mono sub" x="398" y="' + str(y - 4) + '" text-anchor="end">'
            + ("%.0f" % pct) + "%</text>"
            "</g>"
        )
        y += 22

    return shell("altrml languages", body)


def main():
    if not TOKEN:
        print("missing GH_TOKEN", file=sys.stderr)
        return 1

    user = gql(QUERY, {"login": USER})["user"]
    os.makedirs(OUT_DIR, exist_ok=True)

    for name, content in (("stats.svg", stats_svg(user)), ("langs.svg", langs_svg(user))):
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        print("%s %d bytes" % (name, len(content)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
