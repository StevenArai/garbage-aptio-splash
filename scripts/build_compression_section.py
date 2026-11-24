#!/usr/bin/env python3
"""Build an Aptio compression section from an original FFS file and a BMP file.

The FFS file must contain a compression section (type 0x01) that holds an
uncompressed raw section (type 0x19) with BMP data at offset 0x25.

The output is the compression section for UEFIReplace type 01.

The original FFS file and both BMP files are checked before the build. The new
BMP must keep the width, height, bit depth, palette length, header size and
compression method of the original BMP.
"""
import argparse
import hashlib
import struct
from pathlib import Path

BMP_HEADER_SIZES = (40, 108, 124)
BMP_BIT_DEPTHS = (1, 4, 8, 16, 24, 32)


def u24(value: int) -> bytes:
    if not 0 <= value < 1 << 24:
        raise ValueError(f"value does not fit 24 bits: {value}")
    return value.to_bytes(3, "little")


def parse_bmp(data: bytes, label: str) -> dict:
    """Parse and validate one BMP file. Return the fields used for comparison."""
    if len(data) < 54:
        raise ValueError(f"{label}: BMP is shorter than 54 bytes")
    if data[:2] != b"BM":
        raise ValueError(f"{label}: BMP signature is absent")

    file_size = struct.unpack_from("<I", data, 2)[0]
    if file_size != len(data):
        raise ValueError(f"{label}: bfSize {file_size} does not equal the file length {len(data)}")

    off_bits = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size not in BMP_HEADER_SIZES:
        raise ValueError(f"{label}: DIB header size {dib_size} is not 40, 108 or 124")
    if len(data) < 14 + dib_size:
        raise ValueError(f"{label}: DIB header is truncated")

    width, height = struct.unpack_from("<ii", data, 18)
    planes, bpp = struct.unpack_from("<HH", data, 26)
    compression = struct.unpack_from("<I", data, 30)[0]
    size_image = struct.unpack_from("<I", data, 34)[0]
    clr_used = struct.unpack_from("<I", data, 46)[0]

    if width <= 0 or width > 16384:
        raise ValueError(f"{label}: width {width} is outside 1..16384")
    if height == 0 or abs(height) > 16384:
        raise ValueError(f"{label}: height {height} is outside -16384..-1 and 1..16384")
    if planes != 1:
        raise ValueError(f"{label}: plane count {planes} is not 1")
    if bpp not in BMP_BIT_DEPTHS:
        raise ValueError(f"{label}: bit depth {bpp} is not supported")
    if compression != 0:
        raise ValueError(f"{label}: compression {compression} is not 0 (BI_RGB)")

    if bpp <= 8:
        colors = clr_used if clr_used else 1 << bpp
        if colors > 1 << bpp:
            raise ValueError(f"{label}: palette entry count {colors} is too large for {bpp} bpp")
    else:
        colors = clr_used
    palette_bytes = colors * 4
    expected_off_bits = 14 + dib_size + palette_bytes
    if off_bits != expected_off_bits:
        raise ValueError(
            f"{label}: bfOffBits {off_bits} does not match the header and palette size {expected_off_bits}"
        )

    row_bytes = ((width * bpp + 31) // 32) * 4
    pixel_bytes = row_bytes * abs(height)
    if size_image not in (0, pixel_bytes):
        raise ValueError(f"{label}: biSizeImage {size_image} is not 0 or {pixel_bytes}")
    if off_bits + pixel_bytes != len(data):
        raise ValueError(
            f"{label}: bfOffBits plus pixel bytes is {off_bits + pixel_bytes}, not the file length {len(data)}"
        )

    return {
        "width": width,
        "height": height,
        "bpp": bpp,
        "colors": colors,
        "dib_size": dib_size,
        "compression": compression,
        "off_bits": off_bits,
        "pixel_bytes": pixel_bytes,
        "file_size": len(data),
    }


def parse_original_ffs(ffs: bytes, label: str) -> tuple[bytes, dict, int]:
    """Validate the original FFS file and return its BMP, BMP fields and padding."""
    if len(ffs) < 0x25:
        raise ValueError(f"{label}: FFS file is too short")
    if int.from_bytes(ffs[0x14:0x17], "little") != len(ffs):
        raise ValueError(f"{label}: FFS file size field does not equal the file length")
    if ffs[0x1B] != 0x01:
        raise ValueError(f"{label}: section at 0x18 is not a compression section")
    if ffs[0x20] != 0x00:
        raise ValueError(f"{label}: compression algorithm is not 0x00")
    if ffs[0x24] != 0x19:
        raise ValueError(f"{label}: child section is not a raw section")
    if int.from_bytes(ffs[0x18:0x1B], "little") != len(ffs) - 0x18:
        raise ValueError(f"{label}: compression section size does not fit the FFS file")
    if ffs[0x25:0x27] != b"BM":
        raise ValueError(f"{label}: BMP signature is absent at 0x25")

    bmp_size = struct.unpack_from("<I", ffs, 0x25 + 2)[0]
    if 0x25 + bmp_size > len(ffs):
        raise ValueError(f"{label}: BMP length {bmp_size} does not fit the FFS file")
    padding = len(ffs) - (0x25 + bmp_size)
    if padding > 3:
        raise ValueError(f"{label}: {padding} trailing bytes are not a section padding")
    if any(ffs[0x25 + bmp_size:]):
        raise ValueError(f"{label}: section padding is not zero")

    uncompressed = int.from_bytes(ffs[0x1C:0x20], "little")
    raw_size = int.from_bytes(ffs[0x21:0x24], "little")
    if raw_size != 4 + bmp_size:
        raise ValueError(f"{label}: raw section size {raw_size} does not fit the BMP")
    if uncompressed != raw_size + padding:
        raise ValueError(f"{label}: uncompressed length {uncompressed} does not fit the raw section")
    if int.from_bytes(ffs[0x18:0x1B], "little") != 9 + uncompressed:
        raise ValueError(f"{label}: compression section size does not fit the raw section")

    bmp = ffs[0x25:0x25 + bmp_size]
    fields = parse_bmp(bmp, f"{label} BMP")
    return bmp, fields, padding


def validate_section(section: bytes, bmp: bytes) -> None:
    """Validate the built compression section."""
    if len(section) < 13 + len(bmp):
        raise AssertionError("section is shorter than its header and BMP")
    if section[3] != 0x01:
        raise AssertionError("section type is not 0x01")
    if int.from_bytes(section[0:3], "little") != len(section):
        raise AssertionError("section size field does not equal the section length")
    if section[8] != 0x00:
        raise AssertionError("compression algorithm is not 0x00")
    if section[12] != 0x19:
        raise AssertionError("child section type is not 0x19")
    raw_size = int.from_bytes(section[9:12], "little")
    if raw_size != 4 + len(bmp):
        raise AssertionError("raw section size does not fit the BMP")
    if section[13:13 + len(bmp)] != bmp:
        raise AssertionError("BMP bytes are not at section offset 0x0D")
    padding = len(section) - 13 - len(bmp)
    if padding < 0 or padding > 3:
        raise AssertionError("section padding is not 0..3 bytes")
    if any(section[13 + len(bmp):]):
        raise AssertionError("section padding is not zero")
    uncompressed = int.from_bytes(section[4:8], "little")
    if uncompressed != raw_size + padding:
        raise AssertionError("uncompressed length does not fit the raw section and padding")


def build(ffs_path: Path, bmp_path: Path, output: Path) -> None:
    ffs = ffs_path.read_bytes()
    new_bmp = bmp_path.read_bytes()

    original_bmp, original, _ = parse_original_ffs(ffs, str(ffs_path))
    new = parse_bmp(new_bmp, str(bmp_path))
    for field, name in (
        ("width", "width"),
        ("height", "height"),
        ("bpp", "bit depth"),
        ("colors", "palette entry count"),
        ("dib_size", "DIB header size"),
        ("compression", "compression method"),
        ("off_bits", "bfOffBits"),
    ):
        if new[field] != original[field]:
            raise ValueError(
                f"{bmp_path}: {name} {new[field]} does not match the original {original[field]}"
            )
    if new["file_size"] != original["file_size"]:
        raise ValueError(
            f"{bmp_path}: BMP length {new['file_size']} does not match the original {original['file_size']}"
        )

    raw_size = 4 + len(new_bmp)
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
    section += new_bmp
    section += bytes(padding)
    validate_section(bytes(section), new_bmp)

    if len(section) != compression_size:
        raise AssertionError("section length mismatch")

    output.write_bytes(section)
    new_ffs = 0x18 + len(section)
    print(f"original_bmp={len(original_bmp)} new_bmp={len(new_bmp)} raw={raw_size} pad={padding}")
    print(f"section={len(section)} new_ffs={new_ffs}")
    print(f"original_ffs={len(ffs)} delta={new_ffs - len(ffs):+#d}")
    print(f"bmp={new['width']}x{new['height']} {new['bpp']}bpp {new['colors']} colors")
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
