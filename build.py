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
GRID_PX = 800        # long edge of images in the photo grids and small tiles
FULL_PX = 2000       # long edge of images in the full-screen viewer and the wide home tile
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


FONTS = ("https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500"
         "&family=Inter:wght@400;500&display=swap")

NOT_FOUND = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Not found - ephemera photo</title>
<style>body{margin:0;min-height:100vh;display:grid;place-content:center;text-align:center;background:#fbfaf7;color:#1d1d1b;font:15px/1.6 system-ui,sans-serif}h1{font:400 44px/1.1 Georgia,serif;margin:0 0 12px}a{color:inherit}</style>
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
    pages = slugs | {g["slug"] for g in site["groups"]} | {"about", "contact"}
    problems = []
    for s in site["series"]:
        problems += [f"series {s['slug']}: missing photo {n}" for n in s["photos"] if not (photos / n).is_file()]
        if s.get("cover") and s["cover"] not in s["photos"]:
            problems.append(f"series {s['slug']}: cover {s['cover']} is not one of its photos")
    for g in site["groups"]:
        problems += [f"group {g['slug']}: unknown series {x}" for x in g["series"] if x not in slugs]
    problems += [f"nav: unknown page {k}" for k in site["nav"] if k not in pages]
    problems += [f"redirect {o}: unknown page {n}" for o, n in site.get("redirects", {}).items() if n not in pages]
    if not (photos / site["about"]["portrait"]).is_file():
        problems.append(f"about: missing portrait {site['about']['portrait']}")
    if problems:
        raise ValueError("site.json problems:\n  " + "\n  ".join(problems))


def series_by_slug(site: dict) -> dict:
    return {s["slug"]: s for s in site["series"]}


def nav_label(site: dict, key: str) -> str:
    for item in site["groups"] + site["series"]:
        if item["slug"] == key:
            return item["title"]
    return key


def nav_key_for(site: dict, slug: str):
    """The nav item to highlight on a series page: itself, or the group it belongs to."""
    if slug in site["nav"]:
        return slug
    for g in site["groups"]:
        if slug in g["series"]:
            return g["slug"]
    return None


def social_list(site: dict) -> str:
    items = "".join(f'<li><a href="{esc(s["url"])}" rel="me">{esc(s["name"])}</a></li>' for s in site["social"])
    return f'<ul class="links">{items}</ul>'


def layout(site: dict, *, depth: int, title: str, body: str, active=None, scripts=()) -> str:
    """Wrap a page body in the shared <head>, header and footer. depth = folders below the site root."""
    rel = "../" * depth
    items = []
    for key in site["nav"]:
        on = ' class="on" aria-current="page"' if key == active else ""
        items.append(f'<a href="{rel}{key}/"{on}>{esc(nav_label(site, key))}</a>')
    links = "".join(items)
    social = "".join(f'<a href="{esc(s["url"])}" rel="me">{esc(s["name"])}</a>' for s in site["social"])
    page_title = f"{esc(title)} - {esc(site['site_title'])}" if title else esc(site["site_title"])
    tags = "".join(f'<script src="{rel}assets/{name}" defer></script>' for name in scripts)
    home = rel or "./"
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
<link rel="icon" href="{rel}assets/logo.png">
{tags}
</head>
<body>
<header class="top">
<a class="brand" href="{home}"><img src="{rel}assets/logo.png" alt=""><span>{esc(site['site_title'])}</span></a>
<nav class="nav" aria-label="Main">{links}</nav>
<details class="menu"><summary>menu</summary><nav aria-label="Main">{links}</nav></details>
</header>
{body}
<footer class="foot"><span>{esc(site['copyright'])}</span><span class="social">{social}</span></footer>
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


def tile(site: dict, slug: str, rel: str, big: bool, made: dict) -> str:
    s = series_by_slug(site)[slug]
    cover = s.get("cover") or s["photos"][0]
    grid, full, _, _ = made[slug][s["photos"].index(cover)]
    src = full if big else grid
    cls = "tile big" if big else "tile"
    return (f'<a class="{cls}" href="{rel}{slug}/"><span class="ph"><img src="{rel}{src}" alt="" loading="lazy"></span>'
            f'<span class="cap"><span>{esc(s["title"])}</span><span class="n">{len(s["photos"])} photographs</span></span></a>')


def home_page(site: dict, made: dict) -> str:
    tiles = "".join(tile(site, s["slug"], "", i == 0, made) for i, s in enumerate(site["series"]))
    body = f'<main><p class="statement">{esc(site["tagline"])}</p><div class="tiles">{tiles}</div></main>'
    return layout(site, depth=0, title="", body=body)


def group_page(site: dict, group: dict, made: dict) -> str:
    tiles = "".join(tile(site, slug, "../", False, made) for slug in group["series"])
    body = f'<main><div class="head"><h1>{esc(group["title"])}</h1></div><div class="tiles">{tiles}</div></main>'
    return layout(site, depth=1, title=group["title"], body=body, active=group["slug"])


def series_page(site: dict, s: dict, made: dict) -> str:
    n = len(s["photos"])
    cells = []
    for i, (grid, full, w, h) in enumerate(made[s["slug"]], 1):
        ar = w / h
        cells.append(
            f'<a class="ph" href="../{full}" data-full="../{full}" '
            f'style="flex-grow:{ar:.4f};flex-basis:calc({ar:.4f} * var(--row))">'
            f'<i style="padding-bottom:{100 / ar:.3f}%"></i>'
            f'<img src="../{grid}" width="{w}" height="{h}" loading="lazy" '
            f'alt="{esc(s["title"])}, photograph {i} of {n}"></a>')
    grid_html = "".join(cells)
    body = (f'<main><div class="head"><h1>{esc(s["title"])}</h1><p>{n} photographs</p></div>'
            f'<div class="grid">{grid_html}</div></main>')
    return layout(site, depth=1, title=s["title"], body=body,
                  active=nav_key_for(site, s["slug"]), scripts=("viewer.js",))


def about_page(site: dict, portrait: str) -> str:
    a = site["about"]
    paras = "".join(f"<p>{esc(p)}</p>" for p in a["paragraphs"])
    body = (f'<main class="prose"><img class="portrait" src="../{portrait}" alt="Portrait of {esc(site["author"])}">'
            f'<div><h1>{esc(a["title"])}</h1>{paras}{social_list(site)}</div></main>')
    return layout(site, depth=1, title=a["title"], body=body, active="about")


def contact_page(site: dict) -> str:
    c = site["contact"]
    paras = "".join(f"<p>{esc(p)}</p>" for p in c["paragraphs"])
    body = f'<main class="prose single"><div><h1>{esc(c["title"])}</h1>{paras}{social_list(site)}</div></main>'
    return layout(site, depth=1, title=c["title"], body=body, active="contact")


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
    shutil.copy2(content_dir / "logo.png", out_dir / "assets" / "logo.png")
    write(out_dir / ".nojekyll", "")
    if site.get("domain"):
        write(out_dir / "CNAME", site["domain"] + "\n")
    write(out_dir / "index.html", home_page(site, made))
    for g in site["groups"]:
        write(out_dir / g["slug"] / "index.html", group_page(site, g, made))
    for s in site["series"]:
        write(out_dir / s["slug"] / "index.html", series_page(site, s, made))
    write(out_dir / "about" / "index.html", about_page(site, portrait))
    write(out_dir / "contact" / "index.html", contact_page(site))
    for old, new in site.get("redirects", {}).items():
        write(out_dir / old / "index.html", redirect_page(new))
    write(out_dir / "404.html", NOT_FOUND)
    return {s["slug"]: len(s["photos"]) for s in site["series"]}


if __name__ == "__main__":
    counts = build()
    print("built:", ", ".join(f"{slug} ({n})" for slug, n in counts.items()))
