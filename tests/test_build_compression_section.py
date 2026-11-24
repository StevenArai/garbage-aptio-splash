import struct
import tempfile
import unittest
from pathlib import Path

from helpers import build_bmp4, build_bmp24, build_ffs, build_section, run


class BuildCompressionSectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def build(self, bmp, original=None, name="logo.bmp"):
        if original is None:
            original = build_bmp4()
        ffs_path = self.write("original.ffs", build_ffs(original))
        bmp_path = self.write(name, bmp)
        output = self.dir / "section.bin"
        result = run("build_compression_section.py", ffs_path, bmp_path, output)
        return result, output

    def test_round_trip(self):
        bmp = build_bmp4()
        ffs = build_ffs(bmp)
        ffs_path = self.write("original.ffs", ffs)
        bmp_path = self.write("logo.bmp", bmp)
        output = self.dir / "section.bin"
        result = run("build_compression_section.py", ffs_path, bmp_path, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), ffs[0x18:])
        self.assertEqual(build_section(bmp), ffs[0x18:])

    def test_other_pixels_same_structure(self):
        original = build_bmp4()
        changed = bytearray(original)
        changed[0x76] ^= 0x0F
        result, output = self.build(bytes(changed), original)
        self.assertEqual(result.returncode, 0, result.stderr)
        section = output.read_bytes()
        self.assertEqual(len(section), len(build_section(original)))
        self.assertEqual(section[0x0D + 0x76], changed[0x76])

    def test_bad_signature(self):
        bad = bytearray(build_bmp4())
        bad[0:2] = b"ZZ"
        result, _ = self.build(bytes(bad))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BMP signature is absent", result.stderr)

    def test_bad_file_size(self):
        bad = bytearray(build_bmp4())
        struct.pack_into("<I", bad, 2, len(bad) + 1)
        result, _ = self.build(bytes(bad))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bfSize", result.stderr)

    def test_bad_palette(self):
        bad = bytearray(build_bmp4())
        struct.pack_into("<I", bad, 46, 8)
        result, _ = self.build(bytes(bad))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bfOffBits", result.stderr)

    def test_width_mismatch(self):
        result, _ = self.build(build_bmp4(10, 8))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("width 10 does not match the original 8", result.stderr)

    def test_height_mismatch(self):
        result, _ = self.build(build_bmp4(8, 10))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("height 10 does not match the original 8", result.stderr)

    def test_bit_depth_mismatch(self):
        result, _ = self.build(build_bmp24())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bit depth 24 does not match the original 4", result.stderr)

    def test_truncated_ffs(self):
        bmp = build_bmp4()
        ffs = build_ffs(bmp)
        ffs_path = self.write("original.ffs", ffs[:-1])
        bmp_path = self.write("logo.bmp", bmp)
        result = run("build_compression_section.py", ffs_path, bmp_path, self.dir / "out.bin")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FFS file size field", result.stderr)

    def test_bad_original_padding(self):
        bmp = build_bmp4()
        ffs = bytearray(build_ffs(bmp))
        ffs[-1] = 0x55
        ffs_path = self.write("original.ffs", bytes(ffs))
        bmp_path = self.write("logo.bmp", bmp)
        result = run("build_compression_section.py", ffs_path, bmp_path, self.dir / "out.bin")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("padding is not zero", result.stderr)


if __name__ == "__main__":
    unittest.main()
