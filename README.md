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
