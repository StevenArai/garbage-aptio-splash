"""Helpers for the GAS script tests."""
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

REGION_SIZE = 0x10000
FIT_OFFSET = 0x8000
FFS_OFFSET = FIT_OFFSET - 0x18
BLOCK_OFFSET = 0x9000
NEW_BLOCK_OFFSET = 0x9800
BLOCK_SIZE = 1024


def run(script: str, *args, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def build_bmp4(width: int = 8, height: int = 8, clr_used: int = 0) -> bytes:
    colors = clr_used if clr_used else 16
    palette = b"".join(
        bytes([(index * 13) & 0xFF, (index * 29) & 0xFF, (index * 47) & 0xFF, 0])
        for index in range(colors)
    )
    row_bytes = (width + 1) // 2
    padded = (row_bytes + 3) & ~3
    rows = []
    for y in range(height - 1, -1, -1):
        buffer = bytearray(padded)
        for x in range(0, width, 2):
            high = (x + y) % colors
            low = (x + 1 + y) % colors if x + 1 < width else 0
            buffer[x // 2] = (high << 4) | low
        rows.append(bytes(buffer))
    pixels = b"".join(rows)
    off_bits = 14 + 40 + colors * 4
    total = off_bits + len(pixels)
    file_header = struct.pack("<2sIHHI", b"BM", total, 0, 0, off_bits)
    dib_header = struct.pack(
        "<IiiHHIIiiII", 40, width, height, 1, 4, 0, len(pixels), 2835, 2835, clr_used, 0
    )
    return file_header + dib_header + palette + pixels


def build_bmp24(width: int = 8, height: int = 8) -> bytes:
    row_bytes = ((width * 24 + 31) // 32) * 4
    rows = []
    for y in range(height - 1, -1, -1):
        buffer = bytearray(row_bytes)
        for x in range(width):
            offset = x * 3
            buffer[offset] = (x * 17 + y) & 0xFF
            buffer[offset + 1] = (x * 31 + y) & 0xFF
            buffer[offset + 2] = (x * 47 + y) & 0xFF
        rows.append(bytes(buffer))
    pixels = b"".join(rows)
    off_bits = 54
    total = off_bits + len(pixels)
    file_header = struct.pack("<2sIHHI", b"BM", total, 0, 0, off_bits)
    dib_header = struct.pack(
        "<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0
    )
    return file_header + dib_header + pixels


def build_section(bmp: bytes) -> bytes:
    raw_size = 4 + len(bmp)
    padding = (-raw_size) % 4
    uncompressed = raw_size + padding
    size = 9 + uncompressed
    section = bytearray()
    section += size.to_bytes(3, "little")
    section.append(0x01)
    section += struct.pack("<I", uncompressed)
    section.append(0x00)
    section += raw_size.to_bytes(3, "little")
    section.append(0x19)
    section += bmp
    section += bytes(padding)
    return bytes(section)


def build_ffs(bmp: bytes) -> bytes:
    section = build_section(bmp)
    total = 0x18 + len(section)
    header = bytearray(0x18)
    header[0:16] = b"LOGO-TEST-000001"
    header[0x11] = 0xAA
    header[0x12] = 0x02
    header[0x13] = 0x00
    header[0x14:0x17] = total.to_bytes(3, "little")
    header[0x17] = 0x07
    return bytes(header) + section


def make_fit_case(
    cv: bool = True,
    type1_type: int = 0x01,
    duplicate: bool = False,
    invalid_checksum: bool = False,
    data_flag: bool = False,
    data_checksum: int = 0xAA,
) -> dict:
    block = bytes(((index * 37 + 11) & 0xFF) for index in range(BLOCK_SIZE))
    region = bytearray(REGION_SIZE)
    region[BLOCK_OFFSET:BLOCK_OFFSET + BLOCK_SIZE] = block

    header = bytearray(0x18)
    header[0:16] = b"FIT-TEST-0000001"
    header[0x11] = data_checksum
    header[0x12] = 0x02
    header[0x13] = 0x40 if data_flag else 0x00
    header[0x14:0x17] = (0x18 + 0x20).to_bytes(3, "little")
    header[0x17] = 0x07
    region[FFS_OFFSET:FFS_OFFSET + 0x18] = header

    fit = bytearray(0x20)
    fit[0:8] = b"_FIT_   "
    fit[8:12] = (2).to_bytes(4, "little")
    fit[12:14] = (0x0100).to_bytes(2, "little")
    fit[14] = 0x80 if cv else 0x00
    fit[15] = 0
    address = (1 << 32) - REGION_SIZE + BLOCK_OFFSET
    fit[16:24] = address.to_bytes(8, "little")
    fit[24:28] = (64).to_bytes(4, "little")
    fit[28:30] = (0x0100).to_bytes(2, "little")
    fit[30] = type1_type
    fit[31] = 0
    if cv:
        fit[15] = (-(sum(fit) & 0xFF)) & 0xFF
        if sum(fit) & 0xFF != 0:
            raise AssertionError("test FIT table checksum is not zero")
    region[FIT_OFFSET:FIT_OFFSET + 0x20] = fit

    rebuilt = bytearray(region)
    rebuilt[BLOCK_OFFSET:BLOCK_OFFSET + BLOCK_SIZE] = bytes(BLOCK_SIZE)
    rebuilt[NEW_BLOCK_OFFSET:NEW_BLOCK_OFFSET + BLOCK_SIZE] = block
    if duplicate:
        rebuilt[0x9200:0x9200 + BLOCK_SIZE] = block
    if invalid_checksum:
        region[FIT_OFFSET + 15] ^= 0xFF
        rebuilt[FIT_OFFSET + 15] ^= 0xFF

    return {
        "original": bytes(region),
        "rebuilt": bytes(rebuilt),
        "block": block,
    }
