import tempfile
import unittest
from pathlib import Path

from helpers import run


class VerifyMinDiffTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.base = bytes(range(256))
        self.base_path = self.dir / "base.bin"
        self.base_path.write_bytes(self.base)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def test_equal(self):
        same = self.write("same.bin", self.base)
        result = run("verify_min_diff.py", self.base_path, same)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("outside_diff=0", result.stdout)

    def test_outside_difference(self):
        changed = bytearray(self.base)
        changed[10] = 0xFF
        changed[200] = 0x00
        modified = self.write("modified.bin", bytes(changed))
        result = run("verify_min_diff.py", self.base_path, modified)
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside_diff=2", result.stdout)

    def test_ignored_difference(self):
        changed = bytearray(self.base)
        changed[10] = 0xFF
        changed[200] = 0x00
        modified = self.write("modified.bin", bytes(changed))
        result = run(
            "verify_min_diff.py",
            self.base_path,
            modified,
            "--ignore",
            "0x08:0x10",
            "--ignore",
            "0xC0:0xD0",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("outside_diff=0", result.stdout)
        self.assertIn("ignored_diff=2", result.stdout)

    def test_length_mismatch(self):
        short = self.write("short.bin", self.base[:128])
        result = run("verify_min_diff.py", self.base_path, short)
        self.assertEqual(result.returncode, 2)
        self.assertIn("length mismatch", result.stdout)

    def test_bad_range(self):
        same = self.write("same.bin", self.base)
        result = run("verify_min_diff.py", self.base_path, same, "--ignore", "0x10:0x08")
        self.assertEqual(result.returncode, 2)
        self.assertIn("range must have START < END", result.stderr)


if __name__ == "__main__":
    unittest.main()
