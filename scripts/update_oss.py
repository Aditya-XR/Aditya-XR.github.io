"""Refresh the open-source section of index.html from GitHub.

Lists the pull requests I opened in repositories owned by someone else: merged ones
first, then the ones still in review. Closed-without-merge and draft PRs are left out.
Only the HTML between the marker comments is rewritten (the list between OSS:START and
OSS:END, the merged count between MERGED:START and MERGED:END).

Usage: GITHUB_TOKEN=... python3 scripts/update_oss.py
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

USER = os.environ.get("PROFILE_USER", "Aditya-XR")
PAGE = Path(__file__).resolve().parent.parent / "index.html"

QUERY = """
query($q: String!, $cursor: String) {
  search(query: $q, type: ISSUE, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number title url state isDraft merged mergedAt createdAt
        repository { nameWithOwner url stargazerCount }
      }
    }
  }
}
"""


def graphql(token: str, variables: dict) -> dict:
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{USER}-portfolio",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if body.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {body['errors']}")
    return body["data"]["search"]


def fetch_pull_requests(token: str) -> list[dict]:
    pulls, cursor = [], None
    while True:
        page = graphql(token, {"q": f"is:pr author:{USER} -user:{USER}", "cursor": cursor})
        pulls += [node for node in page["nodes"] if node]
        if not page["pageInfo"]["hasNextPage"]:
            return pulls
        cursor = page["pageInfo"]["endCursor"]


def split(pulls: list[dict]) -> tuple[list[dict], list[dict]]:
    merged = [p for p in pulls if p["merged"]]
    in_review = [p for p in pulls if p["state"] == "OPEN" and not p["isDraft"]]
    # Bigger projects first, newest first within a project.
    merged.sort(key=lambda p: p["mergedAt"], reverse=True)
    merged.sort(key=lambda p: p["repository"]["stargazerCount"], reverse=True)
    in_review.sort(key=lambda p: p["createdAt"], reverse=True)
    in_review.sort(key=lambda p: p["repository"]["stargazerCount"], reverse=True)
    return merged, in_review


def stars(count: int) -> str:
    if count >= 1000:
        return f"★ {count / 1000:.1f}k".replace(".0k", "k")
    return f"★ {count}" if count else ""


def clean_title(title: str) -> str:
    """Drop project-convention prefixes such as "Python:", "fix(redis):" or "[SourceKit]"."""
    title = re.sub(r"^(\[[^\]]+\]\s*)+", "", title.strip())
    title = re.sub(r"^[A-Za-z.]+(\([^)]*\))?!?:\s+", "", title).rstrip(".")
    title = title[:1].upper() + title[1:]
    # Backticked names in titles become <code>, everything else is escaped.
    parts = title.split("`")
    return "".join(f"<code>{html.escape(p)}</code>" if i % 2 else html.escape(p) for i, p in enumerate(parts))


def render_group(heading: str, pulls: list[dict], pill: str, pill_class: str) -> list[str]:
    if not pulls:
        return []
    lines = [
        "        <div>",
        f'          <h3>{heading} <span class="count">{len(pulls)}</span></h3>',
        '          <ul class="pr-list">',
    ]
    for p in pulls:
        repo = p["repository"]
        star_text = stars(repo["stargazerCount"])
        repo_html = f'<a href="{repo["url"]}">{html.escape(repo["nameWithOwner"])}</a>'
        if star_text:
            repo_html += f" · {star_text}"
        lines += [
            '            <li class="pr">',
            f'              <span class="pr-repo">{repo_html}</span>',
            f'              <span class="pr-title"><a href="{p["url"]}">{clean_title(p["title"])}</a></span>',
            f'              <span class="pill {pill_class}">{pill}</span>',
            "            </li>",
        ]
    return lines + ["          </ul>", "        </div>"]


def render_list(merged: list[dict], in_review: list[dict]) -> str:
    lines = render_group("Merged", merged, "Merged", "merged")
    lines += render_group("In review", in_review, "In review", "review")
    lines.append('        <p class="oss-note">This list refreshes itself daily from the GitHub API.</p>')
    return "\n".join(lines)


def replace_between(text: str, name: str, content: str) -> str:
    start, end = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
    head, found_start, rest = text.partition(start)
    _, found_end, tail = rest.partition(end)
    if not (found_start and found_end):
        raise ValueError(f"index.html is missing the {start} / {end} markers")
    return f"{head}{start}{content}{end}{tail}"


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set", file=sys.stderr)
        return 1
    page = PAGE.read_text(encoding="utf-8")
    merged, in_review = split(fetch_pull_requests(token))
    updated = replace_between(page, "MERGED", str(len(merged)))
    updated = replace_between(updated, "OSS", f"\n{render_list(merged, in_review)}\n")
    if updated == page:
        print("Open-source section is already up to date")
        return 0
    PAGE.write_text(updated, encoding="utf-8", newline="\n")
    print("Open-source section updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
