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
