#!/usr/bin/env python3
"""Build the ephemera.photography site: reads content/, writes the static site to docs/.

Usage: python3 build.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
GRID_PX = 800        # long edge of images in the photo grids
FULL_PX = 2000       # long edge of images in the one-photo-at-a-time view
PORTRAIT_PX = 1200   # long edge of the about-page portrait
JPEG_QUALITY = 82


def process_image(src: Path, dest: Path, max_px: int) -> tuple[int, int]:
    """Save src as a JPEG at most max_px on its long edge, without camera metadata.

    Skips the work when dest is already newer than src. Returns dest's (width, height).
    """
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        with Image.open(dest) as done:
            return done.size
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as original:
        icc = original.info.get("icc_profile")
        im = ImageOps.exif_transpose(original)
        if im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((max_px, max_px), Image.LANCZOS)
        im.save(dest, "JPEG", quality=JPEG_QUALITY, progressive=True, optimize=True, icc_profile=icc)
        return im.size


# Figtree stands in for Proxima Nova, the Squarespace site's (Adobe-licensed) font.
FONTS = "https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&display=swap"

ICONS = {
    "instagram": ('<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" '
                  'stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/>'
                  '<circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1.2" fill="currentColor" '
                  'stroke="none"/></svg>'),
    "linkedin": ('<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">'
                 '<path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9.5h4V21H3zm6.5 0h3.8v1.6h.05'
                 'c.53-1 1.83-2.05 3.77-2.05 4.03 0 4.78 2.65 4.78 6.1V21h-4v-5.1c0-1.22-.02-2.78-1.7-2.78'
                 '-1.7 0-1.96 1.33-1.96 2.7V21h-4z"/></svg>'),
    "substack": ('<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">'
                 '<path d="M4 3h16v2.4H4zm0 4.4h16v2.4H4zm0 4.4h16V21l-8-4.4L4 21z"/></svg>'),
}

NOT_FOUND = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Not found - ephemera photo</title>
<style>body{margin:0;min-height:100vh;display:grid;place-content:center;text-align:center;background:#fff;color:#444;font:14px/1.6 "Helvetica Neue",Helvetica,Arial,sans-serif}h1{font-weight:400;font-size:26px;color:#111;margin:0 0 12px}a{color:inherit}</style>
</head><body><h1>Nothing here</h1><p>This page doesn't exist. <a id="home" href="/">Go to the home page</a>.</p>
<script>
// The site lives either at a domain root or under /ephemera.photography/ on github.io.
document.getElementById('home').href =
  location.pathname.indexOf('/ephemera.photography/') === 0 ? '/ephemera.photography/' : '/';
</script></body></html>
"""


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def safe_name(name: str) -> str:
    """'L1060421-nb 2 (3).jpg' -> 'l1060421-nb-2-3'"""
    return re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")


def photo_path(slug: str, index: int, name: str, px: int) -> str:
    """Site-relative path of a series photo at one size; index is 1-based."""
    return f"img/{slug}/{index:02d}-{safe_name(name)}-{px}.jpg"


def load_site(content_dir: Path) -> dict:
    return json.loads((content_dir / "site.json").read_text(encoding="utf-8"))


def validate(site: dict, content_dir: Path) -> None:
    """Raise ValueError listing every photo or page site.json names that doesn't exist."""
    photos = content_dir / "photos"
    slugs = {s["slug"] for s in site["series"]}
    pages = slugs | {g["slug"] for g in site["groups"]} | {"about"} | ({"contact"} if "contact" in site else set())
    problems = []
    for s in site["series"]:
        problems += [f"series {s['slug']}: missing photo {n}" for n in s["photos"] if not (photos / n).is_file()]
    for g in site["groups"]:
        problems += [f"group {g['slug']}: unknown series {x}" for x in g["series"] if x not in slugs]
    problems += [f"nav: unknown page {k}" for k in site["nav"] if k not in pages]
    problems += [f"redirect {o}: unknown page {n}" for o, n in site.get("redirects", {}).items() if n not in pages]
    if site.get("home") not in slugs:
        problems.append(f"home: {site.get('home')} is not a series")
    if not (photos / site["about"]["portrait"]).is_file():
        problems.append(f"about: missing portrait {site['about']['portrait']}")
    if problems:
        raise ValueError("site.json problems:\n  " + "\n  ".join(problems))


def nav_label(site: dict, key: str) -> str:
    for item in site["groups"] + site["series"]:
        if item["slug"] == key:
            return item["title"]
    return key


def nav_html(site: dict, rel: str, active) -> str:
    """Sidebar menu. Groups are folders, open when they hold the current page."""
    groups = {g["slug"]: g for g in site["groups"]}

    def link(slug: str) -> str:
        on = ' class="on" aria-current="page"' if slug == active else ""
        return f'<a href="{rel}{slug}/"{on}>{esc(nav_label(site, slug))}</a>'

    parts = []
    for key in site["nav"]:
        if key in groups:
            g = groups[key]
            is_open = " open" if active in g["series"] else ""
            inner = "".join(link(slug) for slug in g["series"])
            parts.append(f'<details class="folder"{is_open}><summary>{esc(g["title"])}</summary>{inner}</details>')
        else:
            parts.append(link(key))
    return "".join(parts)


def social_icons(site: dict) -> str:
    links = "".join(
        f'<a href="{esc(s["url"])}" rel="me" aria-label="{esc(s["name"])}" title="{esc(s["name"])}">'
        f'{ICONS.get(s.get("icon", ""), esc(s["name"]))}</a>'
        for s in site["social"])
    return f'<div class="social">{links}</div>'


def layout(site: dict, *, depth: int, title: str, body: str, active=None, scripts=(), narrow=False) -> str:
    """Wrap a page body in the shared <head>, sidebar and social icons. depth = folders below the site root."""
    rel = "../" * depth
    nav = nav_html(site, rel, active)
    page_title = f"{esc(title)} - {esc(site['site_title'])}" if title else esc(site["site_title"])
    tags = "".join(f'<script src="{rel}assets/{name}" defer></script>' for name in scripts)
    home = rel or "./"
    main_class = "content narrow" if narrow else "content"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<meta name="description" content="{esc(site['tagline'])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{esc(FONTS)}">
<link rel="stylesheet" href="{rel}assets/style.css">
<link rel="icon" href="{rel}assets/favicon.png">
{tags}
</head>
<body>
<div class="site">
<aside class="side">
<a class="logo" href="{home}"><img src="{rel}assets/logo.png" alt="{esc(site['site_title'])}"></a>
<p class="tagline">{esc(site['tagline'])} {esc(site['copyright'])}</p>
<nav class="nav" aria-label="Main">{nav}</nav>
<details class="mobile-menu"><summary>Menu</summary><nav aria-label="Main">{nav}</nav></details>
</aside>
<main class="{main_class}">
{body}
{social_icons(site)}
</main>
</div>
</body>
</html>
"""


def render_photos(site: dict, content_dir: Path, out_dir: Path) -> dict:
    """Make grid and full-size files for every series photo.

    Returns {slug: [(grid_path, full_path, grid_w, grid_h), ...]} in photo order.
    """
    made = {}
    for s in site["series"]:
        rows = []
        for i, name in enumerate(s["photos"], 1):
            src = content_dir / "photos" / name
            grid = photo_path(s["slug"], i, name, GRID_PX)
            full = photo_path(s["slug"], i, name, FULL_PX)
            w, h = process_image(src, out_dir / grid, GRID_PX)
            process_image(src, out_dir / full, FULL_PX)
            rows.append((grid, full, w, h))
        made[s["slug"]] = rows
    return made


def gallery_page(site: dict, s: dict, made: dict, depth: int, title=None) -> str:
    """A series as a photo grid; assets/gallery.js arranges the columns and the one-photo view."""
    rel = "../" * depth
    n = len(s["photos"])
    cells = []
    for i, (grid, full, w, h) in enumerate(made[s["slug"]], 1):
        cells.append(
            f'<a class="ph" href="{rel}{full}" data-full="{rel}{full}">'
            f'<img src="{rel}{grid}" width="{w}" height="{h}" loading="lazy" '
            f'alt="{esc(s["title"])}, photograph {i} of {n}"></a>')
    grid_html = "".join(cells)
    body = f'<h1 class="visually-hidden">{esc(s["title"])}</h1><div class="gallery">{grid_html}</div>'
    return layout(site, depth=depth, title=s["title"] if title is None else title, body=body,
                  active=s["slug"], scripts=("gallery.js",))


def about_page(site: dict, portrait: str) -> str:
    a = site["about"]
    paras = "".join(f"<p>{esc(p)}</p>" for p in a["paragraphs"])
    body = (f'<div class="page about"><img class="portrait" src="../{portrait}" alt="Portrait of {esc(site["author"])}">'
            f'<div class="text"><h1>{esc(a["title"])}</h1>{paras}</div></div>')
    return layout(site, depth=1, title=a["title"], body=body, active="about", narrow=True)


def contact_page(site: dict) -> str:
    c = site["contact"]
    paras = "".join(f"<p>{esc(p)}</p>" for p in c["paragraphs"])
    body = f'<div class="page contact"><h1>{esc(c["title"])}</h1>{paras}</div>'
    return layout(site, depth=1, title=c["title"], body=body, active="contact", narrow=True)


def redirect_page(target: str) -> str:
    url = f"../{target}/"
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved</title>'
            f'<meta http-equiv="refresh" content="0; url={url}"><link rel="canonical" href="{url}"></head>'
            f'<body><p>This page moved to <a href="{url}">{url}</a>.</p></body></html>\n')


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def clean(out_dir: Path) -> None:
    """Delete the previous build except the image cache (docs/img)."""
    if not out_dir.exists():
        return
    for child in out_dir.iterdir():
        if child.name == "img":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def prune_images(out_dir: Path, keep: set) -> None:
    """Delete cached images this build didn't produce, then empty folders."""
    img_dir = out_dir / "img"
    for f in img_dir.rglob("*.jpg"):
        if f.relative_to(out_dir).as_posix() not in keep:
            f.unlink()
    for d in sorted(img_dir.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def build(content_dir: Path = ROOT / "content", assets_dir: Path = ROOT / "assets",
          out_dir: Path = ROOT / "docs") -> dict:
    """Write the whole site into out_dir. Returns {series slug: photo count}."""
    site = load_site(content_dir)
    validate(site, content_dir)
    clean(out_dir)
    made = render_photos(site, content_dir, out_dir)
    portrait_name = site["about"]["portrait"]
    portrait = f"img/about/{safe_name(portrait_name)}-{PORTRAIT_PX}.jpg"
    process_image(content_dir / "photos" / portrait_name, out_dir / portrait, PORTRAIT_PX)
    keep = {portrait} | {p for rows in made.values() for row in rows for p in row[:2]}
    prune_images(out_dir, keep)

    (out_dir / "assets").mkdir(parents=True, exist_ok=True)
    for f in assets_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, out_dir / "assets" / f.name)
    for name in ("logo.png", "favicon.png"):
        shutil.copy2(content_dir / name, out_dir / "assets" / name)
    write(out_dir / ".nojekyll", "")
    if site.get("domain"):
        write(out_dir / "CNAME", site["domain"] + "\n")

    series = {s["slug"]: s for s in site["series"]}
    write(out_dir / "index.html", gallery_page(site, series[site["home"]], made, depth=0, title=""))
    for s in site["series"]:
        write(out_dir / s["slug"] / "index.html", gallery_page(site, s, made, depth=1))
    for g in site["groups"]:  # like Squarespace folders: the folder's address opens its first series
        write(out_dir / g["slug"] / "index.html", redirect_page(g["series"][0]))
    write(out_dir / "about" / "index.html", about_page(site, portrait))
    if "contact" in site:  # optional page
        write(out_dir / "contact" / "index.html", contact_page(site))
    for old, new in site.get("redirects", {}).items():
        write(out_dir / old / "index.html", redirect_page(new))
    write(out_dir / "404.html", NOT_FOUND)
    return {s["slug"]: len(s["photos"]) for s in site["series"]}


if __name__ == "__main__":
    counts = build()
    print("built:", ", ".join(f"{slug} ({n})" for slug, n in counts.items()))
