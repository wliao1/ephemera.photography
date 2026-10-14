# ephemera.photography — new site design

Date: 2026-10-14
Status: draft for approval

## Goal

Replace the Squarespace site with a static site on GitHub Pages, served at
ephemera.photography once the domain finishes moving to Porkbun. Same content
as the live site, new "gallery wall" look (direction A).

## Content

In scope (matches what is public today):

| Page | Source | Photos |
|---|---|---|
| here | gallery "here" (current home page) | 39 |
| somewhere else | gallery "somewhere else" | 11 |
| perturbed | gallery "perturbed" | 33 |
| unperturbed | gallery "unperturbed" | 32 |
| matcha creations | gallery "matcha creations" | 47 |
| about | about page: portrait (Adjustments.jpeg) + bio text | 1 |
| contact | existing intro text + social links (no form) | 0 |

Groupings carry over: **beings** = here + somewhere else; **settings** =
perturbed + unperturbed.

Out of scope (kept in the backup folder and XML export only): the blog and
its 9 posts, Read Me, the unlisted "images" and "impressions" pages, the
contact form, analytics, any CMS.

Photo order, and which photo belongs to which series, come from Squarespace's
page data (`Squarespace Site Backup/page-data/*.json`). Photo files are the
Squarespace web copies (`~/Downloads/Squarespace Images`), because they carry
the edits that are live today (e.g. the drawn-on matcha series).

## Pages and navigation

- **Header (all pages):** EP logo + "EPHEMERA PHOTO" wordmark, left; links
  right: beings, settings, matcha creations, about, contact. On phones the
  links collapse into a simple menu button.
- **Home (`/`):** the tagline as a large serif statement, then one cover tile
  per series (a large first tile, then two columns), each with title and
  photo count. Clicking a tile opens the series.
- **Group pages (`/beings/`, `/settings/`):** the same tiles, for just that
  group's two series.
- **Series pages:** title, count, then a justified-row grid that shows every
  photo uncropped, in the original order. Clicking a photo opens a
  full-screen viewer: next/previous (arrows, swipe, keyboard), close (Esc),
  "12 / 39" counter, and a link-able address per photo.
- **About:** portrait beside the bio text, social links below.
- **Contact:** the current "Open to collaborations…" text with the same three
  links the live site uses: Instagram (instagram.com/ephemera_photo),
  LinkedIn (linkedin.com/in/william-liao) and Medium (willsblog.medium.com).
- **404 page** in the same style.

Old addresses keep working: `/here`, `/somewhere-else`, `/perturbed`,
`/unperturbed`, `/matcha-sketches` and `/about` stay the same; `/contact-1`
redirects to `/contact/`.

## Look

- Off-white background (#fbfaf7), near-black text, generous spacing.
- Type: Cormorant Garamond for the statement and titles; Inter for menus and
  small text (Google Fonts, with system fallbacks).
- Responsive: tiles go to one column and grid rows get shorter on phones.
- The existing EP logo, unchanged.

## How it is built

- **Repo:** public `wliao1/ephemera.photography` (GitHub Pages on a free plan
  needs a public repo; same setup as williamcliao.com).
- **Layout:**
  - `content/site.json`: series list, titles, order, cover photo per series,
    page text.
  - `content/photos/`: the source photos in one folder, under their original
    Squarespace file names (`site.json` says which series each belongs to).
  - `build.py` (Python 3 + Pillow): makes two sizes of each photo (about
    800 px for grids, 2000 px for the viewer), strips camera/location
    metadata, writes the HTML pages into `docs/`.
  - `docs/`: the generated site; GitHub Pages serves this folder from `main`.
  - `notes/`: this spec and the plan (not published).
- All links inside the site are relative, so it works both at the preview
  address (`wliao1.github.io/ephemera.photography/`) and on the real domain.
- Plain HTML and CSS plus one small script for the photo viewer. No frameworks,
  no build step on GitHub's side.
- **Adding photos later:** drop files into `content/photos/`, list them in
  the series in `site.json`, run `python3 build.py`, commit.

## Going live (after the domain transfer)

1. Add a `CNAME` file containing `ephemera.photography` and set the custom
   domain in the repo's Pages settings.
2. At Porkbun DNS: `A` records for `@` → 185.199.108.153, 185.199.109.153,
   185.199.110.153, 185.199.111.153; `CNAME www` → `wliao1.github.io`.
3. Turn on "Enforce HTTPS" once GitHub issues the certificate.
4. Cancel the Squarespace website plan only after the new site is live.

## Testing

- Every series page shows the same photo count as the live site
  (39 / 11 / 33 / 32 / 47) in the same order.
- A link checker confirms every page, image and link inside the site
  resolves, both at the preview address and at the root.
- Full-page screenshots at desktop and phone width for every page, reviewed
  before publishing.
- The viewer works with mouse, keyboard and touch; Esc and back button close it.
- No generated image keeps GPS or camera metadata.
