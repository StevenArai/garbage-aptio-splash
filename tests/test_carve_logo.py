import tempfile
import unittest
from pathlib import Path

from helpers import build_bmp4, run

try:
    from PIL import Image  # noqa: F401
except ImportError:
    Image = None


@unittest.skipUnless(Image is not None, "Pillow is not installed")
class CarveLogoTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_carve_bmp(self):
        bmp = build_bmp4()
        wrapper = self.dir / "wrapper.bin"
        wrapper.write_bytes(b"prefix" + bmp + b"tail")
        outdir = self.dir / "carved"
        result = run("carve_logo.py", wrapper, "-o", outdir, "--save-bmp")
        self.assertEqual(result.returncode, 0, result.stderr)
        png = outdir / "wrapper_0_8x8.png"
        saved = outdir / "wrapper_0_8x8.bmp"
        self.assertTrue(png.exists())
        self.assertTrue(saved.exists())
        self.assertEqual(saved.read_bytes(), bmp)

    def test_no_bmp(self):
        wrapper = self.dir / "empty.bin"
        wrapper.write_bytes(bytes(256))
        outdir = self.dir / "carved"
        result = run("carve_logo.py", wrapper, "-o", outdir)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no valid BMP found", result.stdout)


if __name__ == "__main__":
    unittest.main()
