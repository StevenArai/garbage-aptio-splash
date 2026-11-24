import tempfile
import unittest
from pathlib import Path

from helpers import run

try:
    from PIL import Image
except ImportError:
    Image = None


@unittest.skipUnless(Image is not None, "Pillow is not installed")
class GenLogoVariantsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.source = self.dir / "source.png"
        image = Image.new("RGB", (640, 480), (40, 80, 120))
        for y in range(0, 480, 40):
            for x in range(0, 640, 40):
                image.paste((220, 200, 40), (x, y, x + 20, y + 20))
        image.save(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, *args):
        return run("gen_logo_variants.py", self.source, *args)

    def test_crop(self):
        outdir = self.dir / "candidates"
        result = self.run_script(
            "-o",
            outdir,
            "--width",
            "568",
            "--height",
            "151",
            "--geometries",
            "crop",
            "--quantizers",
            "mediancut",
            "--dithers",
            "none",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = outdir / "crop_mediancut_none.bmp"
        self.assertTrue(output.exists())
        self.assertEqual(output.stat().st_size, 43002)
        with Image.open(output) as image:
            self.assertEqual(image.size, (568, 151))
            self.assertEqual(image.mode, "P")
            colors = image.convert("RGB").getcolors(maxcolors=256) or []
            self.assertLessEqual(len(colors), 16)

    def test_letterbox(self):
        outdir = self.dir / "letterbox"
        result = self.run_script(
            "-o",
            outdir,
            "--width",
            "568",
            "--height",
            "151",
            "--geometries",
            "letterbox",
            "--quantizers",
            "mediancut",
            "--dithers",
            "none",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((outdir / "letterbox_mediancut_none.bmp").exists())

    def test_invert_white(self):
        outdir = self.dir / "invert"
        result = self.run_script(
            "-o",
            outdir,
            "--width",
            "568",
            "--height",
            "151",
            "--geometries",
            "crop",
            "--quantizers",
            "mediancut",
            "--dithers",
            "none",
            "--white-mode",
            "invert",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((outdir / "crop_mediancut_none.bmp").stat().st_size, 43002)

    def test_stretch_is_rejected(self):
        result = self.run_script(
            "-o",
            self.dir / "stretch",
            "--width",
            "568",
            "--height",
            "151",
            "--geometries",
            "stretch",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown geometry", result.stderr)

    def test_small_source_is_rejected(self):
        small = self.dir / "small.png"
        Image.new("RGB", (100, 100), (255, 255, 255)).save(small)
        result = run(
            "gen_logo_variants.py",
            small,
            "-o",
            self.dir / "small",
            "--width",
            "568",
            "--height",
            "151",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Do not upscale", result.stderr)

    def test_unknown_quantizer(self):
        result = self.run_script(
            "-o",
            self.dir / "bad",
            "--width",
            "568",
            "--height",
            "151",
            "--quantizers",
            "bogus",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown quantizer", result.stderr)


if __name__ == "__main__":
    unittest.main()
