import tempfile
import unittest
from pathlib import Path

from helpers import (
    BLOCK_OFFSET,
    BLOCK_SIZE,
    FIT_OFFSET,
    NEW_BLOCK_OFFSET,
    REGION_SIZE,
    make_fit_case,
    run,
)

IMAGE_START = (1 << 32) - REGION_SIZE


class RelocateFitTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        path = self.dir / name
        path.write_bytes(data)
        return path

    def relocate(self, case, *extra):
        original = self.write("original.bin", case["original"])
        rebuilt = self.write("rebuilt.bin", case["rebuilt"])
        output = self.dir / "output.bin"
        result = run("relocate_fit.py", original, rebuilt, output, *extra)
        return result, output

    def test_with_table_checksum(self):
        case = make_fit_case(cv=True)
        result, output = self.relocate(case)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = output.read_bytes()
        table = data[FIT_OFFSET:FIT_OFFSET + 32]
        self.assertEqual(sum(table) & 0xFF, 0)
        address = int.from_bytes(data[FIT_OFFSET + 16:FIT_OFFSET + 24], "little")
        self.assertEqual(address, IMAGE_START + NEW_BLOCK_OFFSET)
        self.assertEqual(data[NEW_BLOCK_OFFSET:NEW_BLOCK_OFFSET + BLOCK_SIZE], case["block"])
        self.assertEqual(data[BLOCK_OFFSET:BLOCK_OFFSET + BLOCK_SIZE], bytes(BLOCK_SIZE))
        self.assertIn("checksum updated", result.stdout)

    def test_without_table_checksum(self):
        case = make_fit_case(cv=False)
        result, output = self.relocate(case)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = output.read_bytes()
        self.assertEqual(data[FIT_OFFSET + 15], 0)
        address = int.from_bytes(data[FIT_OFFSET + 16:FIT_OFFSET + 24], "little")
        self.assertEqual(address, IMAGE_START + NEW_BLOCK_OFFSET)
        self.assertIn("C_V=0", result.stdout)

    def test_invalid_table_checksum(self):
        case = make_fit_case(cv=True, invalid_checksum=True)
        result, _ = self.relocate(case)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid", result.stderr)

    def test_no_fit(self):
        original = self.write("original.bin", bytes(REGION_SIZE))
        rebuilt = self.write("rebuilt.bin", bytes(REGION_SIZE))
        output = self.dir / "output.bin"
        result = run("relocate_fit.py", original, rebuilt, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), bytes(REGION_SIZE))
        self.assertIn("absent", result.stdout)

    def test_ambiguous_match(self):
        case = make_fit_case(cv=True, duplicate=True)
        result, _ = self.relocate(case)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("near matches", result.stderr)

    def test_no_type1_entry(self):
        case = make_fit_case(cv=True, type1_type=0x02)
        result, _ = self.relocate(case)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no Type-1", result.stderr)

    def test_data_checksum_flag(self):
        case = make_fit_case(cv=True, data_flag=True)
        result, _ = self.relocate(case)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("data checksum flag", result.stderr)

    def test_data_checksum_not_aa(self):
        case = make_fit_case(cv=True, data_checksum=0x00)
        result, _ = self.relocate(case)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not 0xAA", result.stderr)

    def test_region_offset(self):
        case = make_fit_case(cv=True)
        original = bytearray(0x14000)
        original[0x4000:0x14000] = case["original"]
        rebuilt = bytearray(0x14000)
        rebuilt[0x4000:0x14000] = case["rebuilt"]
        original_path = self.write("original.bin", bytes(original))
        rebuilt_path = self.write("rebuilt.bin", bytes(rebuilt))
        output = self.dir / "output.bin"
        result = run(
            "relocate_fit.py",
            original_path,
            rebuilt_path,
            output,
            "--region-offset",
            "0x4000",
            "--region-size",
            "0x10000",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FIT offset=0xC000", result.stdout)
        data = output.read_bytes()
        address = int.from_bytes(data[0x4000 + FIT_OFFSET + 16:0x4000 + FIT_OFFSET + 24], "little")
        self.assertEqual(address, IMAGE_START + NEW_BLOCK_OFFSET)


if __name__ == "__main__":
    unittest.main()
