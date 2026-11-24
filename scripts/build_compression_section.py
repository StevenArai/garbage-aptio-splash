#!/usr/bin/env python3
"""Build an Aptio compression section from an original FFS file and a BMP file.

The FFS file must contain a compression section (type 0x01) that holds an
uncompressed raw section (type 0x19) with BMP data at offset 0x25.

The output is the compression section for UEFIReplace type 01.
"""
import argparse
import hashlib
import struct
from pathlib import Path


def u24(value: int) -> bytes:
    if not 0 <= value < 1 << 24:
        raise ValueError(f"value does not fit 24 bits: {value}")
    return value.to_bytes(3, "little")


def build(ffs_path: Path, bmp_path: Path, output: Path) -> None:
    ffs = ffs_path.read_bytes()
    bmp = bmp_path.read_bytes()

    if len(ffs) < 0x25:
        raise ValueError(f"{ffs_path}: FFS file is too short")
    if ffs[0x1B] != 0x01:
        raise ValueError(f"{ffs_path}: section at 0x18 is not a compression section")
    if ffs[0x20] != 0x00:
        raise ValueError(f"{ffs_path}: compression algorithm is not 0x00")
    if ffs[0x24] != 0x19:
        raise ValueError(f"{ffs_path}: child section is not a raw section")
    if ffs[0x25:0x27] != b"BM":
        raise ValueError(f"{ffs_path}: BMP signature is absent at 0x25")
    if bmp[:2] != b"BM":
        raise ValueError(f"{bmp_path}: BMP signature is absent")
    if struct.unpack_from("<I", bmp, 2)[0] != len(bmp):
        raise ValueError(f"{bmp_path}: bfSize does not equal the file length")
    if int.from_bytes(ffs[0x18:0x1B], "little") != len(ffs) - 0x18:
        raise ValueError(f"{ffs_path}: compression section size does not fit the FFS file")

    raw_size = 4 + len(bmp)
    padding = (-raw_size) % 4
    uncompressed = raw_size + padding
    compression_size = 9 + uncompressed

    section = bytearray()
    section += u24(compression_size)
    section.append(0x01)
    section += struct.pack("<I", uncompressed)
    section.append(0x00)
    section += u24(raw_size)
    section.append(0x19)
    section += bmp
    section += bytes(padding)

    if len(section) != compression_size:
        raise AssertionError("section length mismatch")

    output.write_bytes(section)
    new_ffs = 0x18 + len(section)
    print(f"bmp={len(bmp)} raw={raw_size} pad={padding} section={len(section)} new_ffs={new_ffs}")
    print(f"original_ffs={len(ffs)} delta={new_ffs - len(ffs):+#d}")
    print(f"output={output} sha256={hashlib.sha256(section).hexdigest()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an Aptio compression section.")
    parser.add_argument("original_ffs", type=Path)
    parser.add_argument("new_bmp", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.original_ffs, args.new_bmp, args.output)


if __name__ == "__main__":
    main()
