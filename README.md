# aditya-xr.github.io

Source of my portfolio site, **<https://aditya-xr.github.io>**.

Plain HTML and CSS, no build step. The open-source list in `index.html` is regenerated daily by
[`scripts/update_oss.py`](scripts/update_oss.py) from the GitHub GraphQL API, through the
[`refresh` workflow](.github/workflows/refresh.yml); it only commits when something changed.

```bash
GITHUB_TOKEN=$(gh auth token) python3 scripts/update_oss.py   # refresh locally
python3 -m http.server 8000                                   # preview at http://localhost:8000
```
