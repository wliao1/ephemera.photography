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
import check_site  # noqa: E402


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
        make_photo(self.content / "favicon.png", (32, 32))
        self.assets = self.tmp / "assets"
        self.assets.mkdir()
        (self.assets / "style.css").write_text("body{}")
        (self.assets / "gallery.js").write_text("")
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


SITE = {
    "site_title": "test site", "author": "Test Person", "tagline": "a tagline",
    "copyright": "(c) test",
    "social": [{"name": "Instagram", "icon": "instagram", "url": "https://instagram.com/x"}],
    "nav": ["about", "contact", "g", "b"],
    "home": "a",
    "groups": [{"slug": "g", "title": "group g", "series": ["a"]}],
    "series": [
        {"slug": "a", "title": "series a", "photos": ["a1.jpg", "a2.png"]},
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
                    "404.html", ".nojekyll", "assets/style.css", "assets/gallery.js",
                    "assets/logo.png", "assets/favicon.png"]:
            self.assertTrue((self.out / rel).is_file(), rel)

    def test_series_page_lists_photos_in_order_with_gallery_script(self):
        self.run_build()
        page = (self.out / "a" / "index.html").read_text()
        self.assertEqual(page.count('class="ph"'), 2)
        self.assertLess(page.index("01-a1-800.jpg"), page.index("02-a2-800.jpg"))
        self.assertIn('data-full="../img/a/01-a1-2000.jpg"', page)
        self.assertIn("assets/gallery.js", page)

    def test_home_page_is_the_home_series(self):
        self.run_build()
        home = (self.out / "index.html").read_text()
        self.assertEqual(home.count('class="ph"'), 2)
        self.assertIn('src="img/a/01-a1-800.jpg"', home)
        self.assertIn('data-full="img/a/01-a1-2000.jpg"', home)
        self.assertIn('href="a/" class="on"', home)

    def test_folders_open_only_around_the_current_page(self):
        self.run_build()
        page_a = (self.out / "a" / "index.html").read_text()
        self.assertIn('<details class="folder" open><summary>group g</summary>', page_a)
        self.assertIn('href="../a/" class="on"', page_a)
        page_b = (self.out / "b" / "index.html").read_text()
        self.assertIn('<details class="folder"><summary>group g</summary>', page_b)

    def test_group_address_redirects_to_its_first_series(self):
        self.run_build()
        self.assertIn("url=../a/", (self.out / "g" / "index.html").read_text())

    def test_social_icons_on_every_page(self):
        self.run_build()
        for rel in ["index.html", "a/index.html", "about/index.html", "contact/index.html"]:
            page = (self.out / rel).read_text()
            self.assertIn('aria-label="Instagram"', page, rel)
            self.assertIn("<svg", page, rel)

    def test_unknown_home_is_reported(self):
        self.site["home"] = "nope"
        self.save_site()
        with self.assertRaisesRegex(ValueError, "home"):
            self.run_build()

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
        self.site["series"].pop()  # series b
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


if __name__ == "__main__":
    unittest.main()
