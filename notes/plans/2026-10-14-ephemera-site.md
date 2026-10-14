# ephemera.photography static site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the new "gallery wall" ephemera.photography site as plain static files, preview it locally, then publish it on GitHub Pages.

**Architecture:** `content/site.json` + `content/photos/` describe the site. `build.py` (Python + Pillow) resizes photos and writes HTML into `docs/`, which GitHub Pages serves from the `main` branch. One stylesheet and one small script (the full-screen viewer) live in `assets/`. All links are relative so the site works both at `wliao1.github.io/ephemera.photography/` and at the domain root.

**Tech Stack:** Python 3.8+ (`python3` on this Mac is Anaconda 3.8.5 with Pillow 8.0.1), Pillow, stdlib `unittest` and `html.parser`, plain HTML/CSS/JS, `git`, `gh`.

**Spec:** `notes/specs/2026-10-14-ephemera-site-design.md`

## Global Constraints

- Code must run on Python 3.8 and Pillow 8.0.1: no f-string expressions containing backslashes, no `str.removeprefix`, no `Path.is_relative_to`, no runtime `list[str]` (annotations only, with `from __future__ import annotations`).
- Grid images: long edge 800 px. Viewer images: long edge 2000 px. Portrait: long edge 1200 px. JPEG quality 82, progressive, no EXIF; keep the ICC colour profile.
- Every link inside the site is relative; no `href`/`src` starts with `/` except in `404.html`.
- Series and counts: here 39, somewhere-else 11, perturbed 33, unperturbed 32, matcha-sketches 47 (slug kept for old links; title "matcha creations").
- Groups: beings = here + somewhere-else; settings = perturbed + unperturbed.
- Nav order: beings, settings, matcha-sketches, about, contact.
- Old address `/contact-1` redirects to `/contact/`.
- Social links: Instagram https://www.instagram.com/ephemera_photo/, LinkedIn https://www.linkedin.com/in/william-liao/, Medium http://willsblog.medium.com
- Colours/type: background #fbfaf7, text #1d1d1b, muted #8a877f; Cormorant Garamond (statement, titles) and Inter (UI), with system fallbacks.
- Repo: public `wliao1/ephemera.photography`; Pages source `main` branch, `/docs` folder. Publishing waits for the user's go-ahead after the local preview.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Structure

| Path | Responsibility |
|---|---|
| `content/site.json` | All site text, nav, groups, series (photo order, cover), redirects, optional domain |
| `content/photos/` | Source photos, flat folder, original Squarespace file names |
| `content/logo.png` | EP logo |
| `build.py` | Validate site.json, make images, write every page into `docs/` |
| `check_site.py` | Verify a built site: links resolve, stay inside the site, photo counts match |
| `assets/style.css` | All styling (desktop + phone) |
| `assets/viewer.js` | Full-screen photo viewer on series pages |
| `tests/test_build.py` | Unit tests for build.py and check_site.py, using a generated fixture site |
| `docs/` | Generated site (committed; served by GitHub Pages) |
| `notes/` | Spec and this plan (not published) |
| `README.md` | How to build, add photos, go live |

Run all commands from the repo root: `<session folder>/ephemera.photography/`.

---

### Task 1: Repository and content

**Files:**
- Create: `.gitignore`, `content/site.json`, `content/photos/*`, `content/logo.png`
- Move: `../notes/` → `notes/`

**Interfaces:**
- Produces: `content/site.json` with keys `site_title`, `author`, `tagline`, `copyright`, `social[] {name,url}`, `nav[]`, `groups[] {slug,title,series[]}`, `series[] {slug,title,cover,photos[]}`, `about {title,portrait,paragraphs[]}`, `contact {title,paragraphs[]}`, `redirects {old: new}`; every file named in it exists in `content/photos/`.

- [ ] **Step 1: Create the repo and move the notes in**

```bash
mkdir -p ephemera.photography && cd ephemera.photography && git init -b main
mv ../notes ./notes
printf '.DS_Store\n__pycache__/\n*.pyc\n' > .gitignore
```

- [ ] **Step 2: Import photos and write site.json**

Reads the gallery data saved earlier (scratchpad `series.json`, built from Squarespace's page data) and the backup folder. Run with the Anaconda interpreter in isolated mode:

```bash
SP="/private/tmp/claude-501/-Users-williamliao-Library-Application-Support-Claude-scratch-workspaces-d6bb7898-9bfb-424c-b360-a47e8e27ec3e-036b9d05-9098-48c6-9889-fd5ea8fdf9c2-scratch-2026-10-14-248724/c686aaf8-ce95-4db1-baf4-8aee35d65e87/scratchpad"   # holds series.json
~/opt/anaconda3/bin/python3 -I - "$SP" <<'EOF'
import json, os, re, shutil, sys, html
from pathlib import Path
from PIL import Image
sp = Path(sys.argv[1]); dl = Path.home() / "Downloads"
src = dl / "Squarespace Images"; backup = dl / "Squarespace Site Backup"
photos = Path("content/photos"); photos.mkdir(parents=True, exist_ok=True)
gal = json.load(open(sp / "series.json"))
titles = {"here": "here", "somewhere-else": "somewhere else", "perturbed": "perturbed",
          "unperturbed": "unperturbed", "matcha-sketches": "matcha creations"}
series = []
for slug, title in titles.items():
    names = [it["local"] for it in gal[slug]["items"]]
    for n in names: shutil.copy2(src / n, photos / n)
    cover = names[0]
    if slug == "here":   # first tile on the home page is wide (2:1): use the first landscape photo
        for n in names:
            with Image.open(photos / n) as im:
                if im.width / im.height >= 1.4: cover = n; break
    series.append({"slug": slug, "title": title, "cover": cover, "photos": names})
shutil.copy2(src / "Adjustments.jpeg", photos / "Adjustments.jpeg")
shutil.copy2(src / "logo.png", Path("content/logo.png"))
def paras(page):
    body = json.load(open(backup / "page-data" / f"{page}.json"))["mainContent"]
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S)
    out = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S)]
    return [" ".join(p.split()) for p in out if p.strip()]
about = paras("about")
contact = [p.replace("or through this form!", "or Instagram.") for p in paras("contact-1") if p.lower() != "contact us"]
site = {
  "site_title": "ephemera photo", "author": "William Liao",
  "tagline": "sights, sounds, smells, metaphors, emotions and other phenomena gently cupped and mediated through photography.",
  "copyright": "All images and content copyright William Liao 2019+.",
  "social": [{"name": "Instagram", "url": "https://www.instagram.com/ephemera_photo/"},
             {"name": "LinkedIn", "url": "https://www.linkedin.com/in/william-liao/"},
             {"name": "Medium", "url": "http://willsblog.medium.com"}],
  "nav": ["beings", "settings", "matcha-sketches", "about", "contact"],
  "groups": [{"slug": "beings", "title": "beings", "series": ["here", "somewhere-else"]},
             {"slug": "settings", "title": "settings", "series": ["perturbed", "unperturbed"]}],
  "series": series,
  "about": {"title": "About", "portrait": "Adjustments.jpeg", "paragraphs": about},
  "contact": {"title": "Contact", "paragraphs": contact},
  "redirects": {"contact-1": "contact"},
}
Path("content/site.json").write_text(json.dumps(site, indent=2, ensure_ascii=False) + "\n")
print({s["slug"]: len(s["photos"]) for s in series}); print("about:", about); print("contact:", contact)
EOF
```

- [ ] **Step 3: Verify the import**

Expected output: `{'here': 39, 'somewhere-else': 11, 'perturbed': 33, 'unperturbed': 32, 'matcha-sketches': 47}`, three about paragraphs starting "William Liao is a 2nd generation…", and one contact paragraph ending "…over LinkedIn or Instagram." Then:

```bash
~/opt/anaconda3/bin/python3 -I -c "import json,os; s=json.load(open('content/site.json')); names={n for x in s['series'] for n in x['photos']}|{s['about']['portrait']}; print('missing:', [n for n in names if not os.path.isfile('content/photos/'+n)])"
```
Expected: `missing: []`

- [ ] **Step 4: Commit**

```bash
git add .gitignore notes content
git commit -m "Add site content: photos, text and structure from Squarespace

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Image processing

**Files:**
- Create: `build.py` (constants, `process_image`)
- Test: `tests/test_build.py`

**Interfaces:**
- Produces: `build.process_image(src: Path, dest: Path, max_px: int) -> tuple[int, int]`; constants `GRID_PX=800`, `FULL_PX=2000`, `PORTRAIT_PX=1200`, `JPEG_QUALITY=82`.

- [ ] **Step 1: Write the failing tests**

`tests/test_build.py`:

```python
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import build  # noqa: E402


def make_photo(path, size, mode="RGB", camera=False):
    colour = (120, 140, 160) if mode == "RGB" else (120, 140, 160, 128)
    im = Image.new(mode, size, colour)
    if camera:
        exif = Image.Exif()
        exif[0x010F] = "TestMaker"
        exif[0x0110] = "TestModel"
        im.save(path, "JPEG", exif=exif.tobytes())
    else:
        im.save(path)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.content = self.tmp / "content"
        photos = self.content / "photos"
        photos.mkdir(parents=True)
        make_photo(photos / "a1.jpg", (3000, 2000), camera=True)
        make_photo(photos / "a2.png", (200, 300), mode="RGBA")
        make_photo(photos / "b1.jpg", (500, 500))
        make_photo(photos / "p.jpg", (1600, 2000))
        make_photo(self.content / "logo.png", (64, 64))
        self.assets = self.tmp / "assets"
        self.assets.mkdir()
        (self.assets / "style.css").write_text("body{}")
        (self.assets / "viewer.js").write_text("")
        self.out = self.tmp / "docs"

    def tearDown(self):
        shutil.rmtree(self.tmp)


class ProcessImageTest(Fixture):
    def test_resizes_and_strips_camera_data(self):
        src = self.content / "photos" / "a1.jpg"
        with Image.open(src) as im:
            self.assertGreater(len(im.getexif()), 0)  # the fixture really carries metadata
        size = build.process_image(src, self.tmp / "out.jpg", 800)
        self.assertEqual(size, (800, 533))
        with Image.open(self.tmp / "out.jpg") as im:
            self.assertEqual(im.format, "JPEG")
            self.assertEqual(len(im.getexif()), 0)

    def test_converts_transparent_png_and_never_upscales(self):
        size = build.process_image(self.content / "photos" / "a2.png", self.tmp / "out.jpg", 800)
        self.assertEqual(size, (200, 300))
        with Image.open(self.tmp / "out.jpg") as im:
            self.assertEqual(im.mode, "RGB")

    def test_reuses_up_to_date_output(self):
        src = self.content / "photos" / "b1.jpg"
        dest = self.tmp / "out.jpg"
        build.process_image(src, dest, 100)
        first = dest.stat().st_mtime_ns
        self.assertEqual(build.process_image(src, dest, 100), (100, 100))
        self.assertEqual(dest.stat().st_mtime_ns, first)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'build'`

- [ ] **Step 3: Write `build.py` with `process_image`**

```python
#!/usr/bin/env python3
"""Build the ephemera.photography site: reads content/, writes the static site to docs/.

Usage: python3 build.py
"""
from __future__ import annotations

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
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: 3 tests, OK

- [ ] **Step 5: Commit**

```bash
git add build.py tests/test_build.py
git commit -m "Add image processing for the site build

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Pages and site checker

**Files:**
- Modify: `build.py` (add everything below `process_image`)
- Create: `check_site.py`
- Test: `tests/test_build.py` (add `BuildTest`)

**Interfaces:**
- Consumes: `build.process_image`, constants from Task 2.
- Produces: `build.build(content_dir: Path, assets_dir: Path, out_dir: Path) -> dict[str, int]` (series slug → photo count); `build.photo_path(slug: str, index: int, name: str, px: int) -> str`; `check_site.check(site_dir: Path, site: dict) -> list[str]` (empty list = OK). Generated markup that Task 4 styles and scripts depend on: `header.top`, `a.brand`, `nav.nav`, `details.menu`, `p.statement`, `div.tiles > a.tile[.big] > span.ph + span.cap > span + span.n`, `div.head > h1 + p`, `div.grid > a.ph[data-full] > i + img`, `main.prose[.single] > img.portrait`, `ul.links`, `footer.foot`; nav link for the current section has `class="on"`; `viewer.js` loaded with `defer` only on series pages.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_build.py` (before the `if __name__` line), and add `import check_site  # noqa: E402` under `import build`:

```python
SITE = {
    "site_title": "test site", "author": "Test Person", "tagline": "a tagline",
    "copyright": "(c) test",
    "social": [{"name": "Instagram", "url": "https://instagram.com/x"}],
    "nav": ["g", "b", "about", "contact"],
    "groups": [{"slug": "g", "title": "group g", "series": ["a"]}],
    "series": [
        {"slug": "a", "title": "series a", "cover": "a2.png", "photos": ["a1.jpg", "a2.png"]},
        {"slug": "b", "title": "series b", "photos": ["b1.jpg"]},
    ],
    "about": {"title": "About", "portrait": "p.jpg", "paragraphs": ["hello"]},
    "contact": {"title": "Contact", "paragraphs": ["write"]},
    "redirects": {"old-contact": "contact"},
}


class BuildTest(Fixture):
    def setUp(self):
        super().setUp()
        self.site = json.loads(json.dumps(SITE))
        self.save_site()

    def save_site(self):
        (self.content / "site.json").write_text(json.dumps(self.site))

    def run_build(self):
        return build.build(self.content, self.assets, self.out)

    def test_writes_every_page(self):
        self.assertEqual(self.run_build(), {"a": 2, "b": 1})
        for rel in ["index.html", "g/index.html", "a/index.html", "b/index.html",
                    "about/index.html", "contact/index.html", "old-contact/index.html",
                    "404.html", ".nojekyll", "assets/style.css", "assets/viewer.js",
                    "assets/logo.png"]:
            self.assertTrue((self.out / rel).is_file(), rel)

    def test_series_page_lists_photos_in_order_with_viewer(self):
        self.run_build()
        page = (self.out / "a" / "index.html").read_text()
        self.assertEqual(page.count('class="ph"'), 2)
        self.assertLess(page.index("01-a1-800.jpg"), page.index("02-a2-800.jpg"))
        self.assertIn('data-full="../img/a/01-a1-2000.jpg"', page)
        self.assertIn("assets/viewer.js", page)

    def test_home_uses_cover_and_marks_current_section(self):
        self.run_build()
        home = (self.out / "index.html").read_text()
        self.assertIn('src="img/a/02-a2-2000.jpg"', home)  # wide first tile, chosen cover
        self.assertIn('href="g/"', home)
        page = (self.out / "a" / "index.html").read_text()
        self.assertIn('href="../g/" class="on"', page)      # series a belongs to group g

    def test_every_local_link_resolves(self):
        self.run_build()
        self.assertEqual(check_site.check(self.out, self.site), [])

    def test_checker_reports_broken_and_absolute_links(self):
        self.run_build()
        page = self.out / "b" / "index.html"
        page.write_text(page.read_text() + '<a href="../nowhere/">x</a><a href="/about/">y</a>')
        problems = check_site.check(self.out, self.site)
        self.assertTrue(any("broken link ../nowhere/" in p for p in problems), problems)
        self.assertTrue(any("absolute link /about/" in p for p in problems), problems)

    def test_redirect_points_at_new_page(self):
        self.run_build()
        self.assertIn("url=../contact/", (self.out / "old-contact" / "index.html").read_text())

    def test_missing_photo_is_reported(self):
        self.site["series"][1]["photos"].append("nope.jpg")
        self.save_site()
        with self.assertRaisesRegex(ValueError, "nope.jpg"):
            self.run_build()

    def test_rebuild_drops_removed_pages_and_images(self):
        self.run_build()
        self.site["series"].pop()
        self.site["nav"].remove("b")
        self.save_site()
        self.run_build()
        self.assertFalse((self.out / "b").exists())
        self.assertFalse((self.out / "img" / "b").exists())

    def test_domain_writes_cname(self):
        self.site["domain"] = "example.com"
        self.save_site()
        self.run_build()
        self.assertEqual((self.out / "CNAME").read_text().strip(), "example.com")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: ERROR `No module named 'check_site'`

- [ ] **Step 3: Write `check_site.py`**

```python
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
```

- [ ] **Step 4: Add the page-building code to `build.py`**

Add `import html`, `import json`, `import re`, `import shutil` to the imports, then append:

```python
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
```

- [ ] **Step 5: Run to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: 12 tests, OK

- [ ] **Step 6: Commit**

```bash
git add build.py check_site.py tests/test_build.py
git commit -m "Generate site pages and add a link and photo-count checker

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Look and photo viewer

**Files:**
- Create: `assets/style.css`, `assets/viewer.js`

**Interfaces:**
- Consumes: the markup listed in Task 3's Produces block; `--row` CSS variable drives grid row height.

- [ ] **Step 1: Write `assets/style.css`**

```css
:root {
  --bg: #fbfaf7; --ink: #1d1d1b; --muted: #8a877f; --line: #e7e4dc;
  --pad: 56px; --gap: 28px; --row: 300px;
  --serif: "Cormorant Garamond", Georgia, "Times New Roman", serif;
  --sans: Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.6 var(--sans); }
a { color: inherit; text-decoration: none; }
img { display: block; max-width: 100%; }

.top { display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 28px var(--pad); }
.brand { display: flex; align-items: center; gap: 14px; font-size: 13px; letter-spacing: .18em; text-transform: uppercase; }
.brand img { height: 34px; width: auto; }
.nav a { margin-left: 32px; font-size: 14px; color: #555; }
.nav a:hover, .nav a.on { color: var(--ink); }
.nav a.on { text-decoration: underline; text-underline-offset: 6px; }
.menu { display: none; }

.statement { margin: 0; padding: 70px var(--pad) 60px; max-width: 1100px; font: 400 46px/1.18 var(--serif); }
.tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--gap); padding: 0 var(--pad) 80px; }
.tile .ph { display: block; overflow: hidden; aspect-ratio: 4 / 5; background: var(--line); }
.tile.big { grid-column: span 2; }
.tile.big .ph { aspect-ratio: 2 / 1; }
.tile img { width: 100%; height: 100%; object-fit: cover; transition: transform .6s ease; }
.tile:hover img { transform: scale(1.02); }
.cap { display: flex; justify-content: space-between; padding: 12px 2px; font-size: 15px; }
.n { color: var(--muted); font-size: 13px; }

.head { padding: 50px var(--pad) 30px; }
.head h1, .prose h1 { margin: 0; font: 400 44px/1.1 var(--serif); }
.head p { margin: 8px 0 0; color: var(--muted); font-size: 13px; }

.grid { display: flex; flex-wrap: wrap; gap: 10px; padding: 0 var(--pad) 80px; }
.grid::after { content: ""; flex-grow: 999999; }
.grid .ph { position: relative; display: block; overflow: hidden; background: var(--line); cursor: zoom-in; }
.grid .ph i { display: block; }
.grid .ph img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }

.prose { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 56px; padding: 50px var(--pad) 80px; align-items: start; }
.prose.single { grid-template-columns: minmax(0, 680px); }
.prose h1 { margin-bottom: 20px; }
.prose p { max-width: 60ch; }
.links { display: flex; flex-wrap: wrap; gap: 22px; margin: 28px 0 0; padding: 0; list-style: none; }
.links a { border-bottom: 1px solid var(--line); padding-bottom: 2px; }
.links a:hover { border-color: var(--ink); }

.foot { display: flex; justify-content: space-between; gap: 20px; margin: 0 var(--pad); padding: 24px 0 40px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }
.foot .social a { margin-left: 18px; }
.foot .social a:hover { color: var(--ink); }

.viewer { position: fixed; inset: 0; z-index: 10; display: flex; align-items: center; justify-content: center; background: rgba(18, 18, 17, .96); }
.viewer[hidden] { display: none; }
.viewer img { max-width: 94vw; max-height: 88vh; width: auto; height: auto; user-select: none; }
.viewer button { position: absolute; padding: 18px; border: 0; background: none; color: #e8e6e0; font: 300 34px/1 var(--sans); cursor: pointer; opacity: .75; }
.viewer button:hover, .viewer button:focus-visible { opacity: 1; }
.viewer .close { top: 8px; right: 12px; }
.viewer .prev, .viewer .next { top: 50%; transform: translateY(-50%); }
.viewer .prev { left: 6px; }
.viewer .next { right: 6px; }
.viewer .count { position: absolute; right: 0; bottom: 16px; left: 0; color: #a9a69e; font-size: 13px; letter-spacing: .08em; text-align: center; }

@media (max-width: 760px) {
  :root { --pad: 20px; --gap: 18px; --row: 170px; }
  .nav { display: none; }
  .menu { display: block; position: relative; font-size: 14px; }
  .menu summary { padding: 6px 0; list-style: none; cursor: pointer; }
  .menu summary::-webkit-details-marker { display: none; }
  .menu nav { position: absolute; top: 36px; right: 0; z-index: 5; display: flex; flex-direction: column; gap: 6px; min-width: 180px; padding: 10px 18px; border: 1px solid var(--line); background: var(--bg); }
  .statement { padding: 36px var(--pad); font-size: 30px; }
  .tiles { grid-template-columns: minmax(0, 1fr); }
  .tile.big { grid-column: auto; }
  .tile.big .ph { aspect-ratio: 4 / 5; }
  .head h1, .prose h1 { font-size: 34px; }
  .prose { grid-template-columns: minmax(0, 1fr); gap: 28px; }
  .grid { gap: 6px; }
  .foot { flex-direction: column; gap: 6px; }
  .foot .social a { margin: 0 18px 0 0; }
}
```

- [ ] **Step 2: Write `assets/viewer.js`**

```js
// Full-screen photo viewer for series pages: click a photo; arrows/swipe to move; Esc or × to close.
// Each open photo gets an address like #12, so it can be shared and the back button closes it.
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll('.grid .ph'));
  if (!links.length) return;
  var total = links.length;
  var index = -1;
  var pushed = false; // true when we added a history entry by opening a photo
  var startX = null;

  var box = document.createElement('div');
  box.className = 'viewer';
  box.hidden = true;
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', 'Photo viewer');
  box.innerHTML = '<img alt="">' +
    '<button class="prev" type="button" aria-label="Previous photo">&#8249;</button>' +
    '<button class="next" type="button" aria-label="Next photo">&#8250;</button>' +
    '<button class="close" type="button" aria-label="Close">&times;</button>' +
    '<div class="count" aria-live="polite"></div>';
  document.body.appendChild(box);
  var img = box.querySelector('img');
  var count = box.querySelector('.count');

  function preload(i) {
    new Image().src = links[(i + total) % total].getAttribute('data-full');
  }

  function show(i) {
    index = (i + total) % total;
    var a = links[index];
    img.src = a.getAttribute('data-full');
    img.alt = a.querySelector('img').alt;
    count.textContent = (index + 1) + ' / ' + total;
    box.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    preload(index + 1);
    preload(index - 1);
  }

  function hide() {
    box.hidden = true;
    index = -1;
    document.documentElement.style.overflow = '';
  }

  function open(i) {
    show(i);
    history.pushState({ photo: true }, '', '#' + (index + 1));
    pushed = true;
    box.querySelector('.close').focus();
  }

  function go(step) {
    show(index + step);
    history.replaceState({ photo: true }, '', '#' + (index + 1));
  }

  function close() {
    if (pushed) {
      pushed = false;
      history.back(); // the popstate handler hides the viewer
    } else {
      hide();
      history.replaceState(null, '', location.pathname + location.search);
    }
  }

  function fromHash() {
    var n = parseInt(location.hash.slice(1), 10);
    if (n >= 1 && n <= total) show(n - 1); else hide();
  }

  links.forEach(function (a, i) {
    a.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // keep open-in-new-tab
      e.preventDefault();
      open(i);
    });
  });
  box.querySelector('.prev').addEventListener('click', function (e) { e.stopPropagation(); go(-1); });
  box.querySelector('.next').addEventListener('click', function (e) { e.stopPropagation(); go(1); });
  box.querySelector('.close').addEventListener('click', function (e) { e.stopPropagation(); close(); });
  box.addEventListener('click', function (e) { if (e.target === box) close(); });
  document.addEventListener('keydown', function (e) {
    if (box.hidden) return;
    if (e.key === 'ArrowRight') go(1);
    else if (e.key === 'ArrowLeft') go(-1);
    else if (e.key === 'Escape') close();
  });
  box.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
  box.addEventListener('touchend', function (e) {
    if (startX === null) return;
    var dx = e.changedTouches[0].clientX - startX;
    startX = null;
    if (Math.abs(dx) > 40) go(dx < 0 ? 1 : -1);
  });
  window.addEventListener('popstate', function () { pushed = false; fromHash(); });
  fromHash();
})();
```

- [ ] **Step 3: Build and check**

Run: `python3 build.py && python3 check_site.py && python3 -m unittest discover -s tests`
Expected: `built: here (39), somewhere-else (11), perturbed (33), unperturbed (32), matcha-sketches (47)`, then `site OK`, then 12 tests OK.

- [ ] **Step 4: Check it in the browser**

Serve `docs/` locally (`python3 -m http.server 8765 --directory docs`, as a `.claude/launch.json` entry for the built-in browser) and verify:
- Home, beings, settings, each series, about, contact render with no console errors; screenshots at 1440 px and 390 px wide.
- On a series page: click photo 1 → viewer shows "1 / N"; ArrowRight → "2 / N"; Esc → closed and address has no `#`; open `…/perturbed/#5` directly → viewer shows "5 / 33"; browser Back after opening a photo closes it.
- `/contact-1/` lands on `/contact/`.

- [ ] **Step 5: Commit**

```bash
git add assets
git commit -m "Add gallery-wall styling and full-screen photo viewer

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Full build, README, user review

**Files:**
- Create: `README.md`, `docs/` (generated)

- [ ] **Step 1: Write `README.md`**

```markdown
# ephemera.photography

William Liao's photography site. Plain static files served by GitHub Pages from `docs/`.

## Build

    python3 build.py        # writes docs/ from content/
    python3 check_site.py   # checks links and photo counts
    python3 -m unittest discover -s tests

Needs Python 3.8+ and Pillow (`pip install Pillow`).

## Change the site

- Text, menu, series order and cover photos: `content/site.json`.
- Add a photo: put the file in `content/photos/`, add its file name to the
  series' `photos` list in `site.json`, run `python3 build.py`, commit.
- Photos are resized (800 px and 2000 px) and camera metadata is removed
  during the build.

## Domain

Set `"domain": "ephemera.photography"` in `site.json` (the build writes
`docs/CNAME`), point DNS at GitHub Pages (A records 185.199.108.153,
185.199.109.153, 185.199.110.153, 185.199.111.153; CNAME `www` →
`wliao1.github.io`), then turn on "Enforce HTTPS" in the repo's Pages settings.
```

- [ ] **Step 2: Build, check and commit the generated site**

```bash
python3 build.py && python3 check_site.py
du -sh docs content
git add README.md docs
git commit -m "Build the site

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `site OK`; `docs` around 120 MB.

- [ ] **Step 3: User review**

Show the user the local preview (built-in browser) and desktop/phone screenshots. Apply requested changes (covers, order, text) in `site.json` or `style.css`, rebuild, re-check, commit. Ask for the go-ahead to publish.

---

### Task 6: Publish the preview on GitHub Pages (after the user's go-ahead)

- [ ] **Step 1: Create the public repo and push**

```bash
gh repo create wliao1/ephemera.photography --public --source . --remote origin --push \
  --description "ephemera photo: photography by William Liao"
```

- [ ] **Step 2: Turn on Pages from `main` / `docs`**

```bash
gh api -X POST repos/wliao1/ephemera.photography/pages -f "source[branch]=main" -f "source[path]=/docs"
```

- [ ] **Step 3: Verify the preview**

```bash
gh api repos/wliao1/ephemera.photography/pages --jq '.status, .html_url'
curl -s -o /dev/null -w '%{http_code}\n' https://wliao1.github.io/ephemera.photography/
curl -s -o /dev/null -w '%{http_code}\n' https://wliao1.github.io/ephemera.photography/perturbed/
```
Expected: status `built`, URL `https://wliao1.github.io/ephemera.photography/`, both `200` (the first deploy can take a few minutes). Open it in the browser and spot-check a series page and the viewer.
