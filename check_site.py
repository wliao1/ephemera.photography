#!/usr/bin/env python3
"""Check a built site: local links and images resolve, nothing points outside the site,
and every series page shows as many photos as site.json lists.

Usage: python3 check_site.py [site_dir] [content_dir]
"""
from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class _Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src", "data-full") and value:
                self.refs.append(value)


def local_refs(page: Path) -> list:
    """Every link/image reference in page that points at a file of this site."""
    parser = _Refs()
    parser.feed(page.read_text(encoding="utf-8"))
    refs = []
    for ref in parser.refs:
        parts = urlsplit(ref)
        if parts.scheme or parts.netloc or not parts.path:  # external, mailto:, or #anchor
            continue
        refs.append(ref)
    return refs


def check(site_dir: Path, site: dict) -> list:
    root = site_dir.resolve()
    problems = []
    for page in sorted(root.rglob("*.html")):
        name = page.relative_to(root).as_posix()
        if name == "404.html":  # finds the home page at runtime, see build.NOT_FOUND
            continue
        for ref in local_refs(page):
            path = unquote(urlsplit(ref).path)
            if path.startswith("/"):
                problems.append(f"{name}: absolute link {ref} breaks the github.io preview")
                continue
            target = (page.parent / path).resolve()
            if target != root and root not in target.parents:
                problems.append(f"{name}: {ref} points outside the site")
                continue
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                problems.append(f"{name}: broken link {ref}")
    for s in site["series"]:
        page = root / s["slug"] / "index.html"
        shown = page.read_text(encoding="utf-8").count('class="ph"') if page.is_file() else 0
        if shown != len(s["photos"]):
            problems.append(f"{s['slug']}: page shows {shown} photos, site.json lists {len(s['photos'])}")
    return problems


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    site_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "docs"
    content_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else here / "content"
    site = json.loads((content_dir / "site.json").read_text(encoding="utf-8"))
    found = check(site_dir, site)
    print("\n".join(found) if found else "site OK")
    sys.exit(1 if found else 0)
