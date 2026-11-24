#!/usr/bin/env python3
"""Relocate FIT Type-1 microcode addresses after an FV rebuild.

The BIOS region is mapped at 0x100000000 minus the region size. A Type-1 FIT
entry stores an absolute address. This script finds the moved microcode block
by a 1024-byte sample and writes the new address into the entry.

Inputs can be BIOS regions or full chip images. For a full chip image, give the
region offset and the region size.
"""
import argparse
import hashlib
import struct
from pathlib import Path

FIT_SIGNATURE = b"_FIT_   "
SAMPLE_BYTES = 1024


def fit_table_checksum(region: bytes, fit: int, count: int) -> int:
    """Return the 8-bit checksum of the complete FIT table."""
    return sum(region[fit:fit + count * 16]) & 0xFF


def fit_has_table_checksum(region: bytes, fit: int) -> bool:
    """Return True when the FIT header C_V bit requires a table checksum."""
    return bool(region[fit + 14] & 0x80)


def update_fit_checksum(rebuilt: bytearray, offset: int, fit: int, count: int) -> int:
    """Set the FIT header checksum byte so the complete table sums to zero."""
    checksum_at = offset + fit + 15
    rebuilt[checksum_at] = 0
    total = sum(rebuilt[offset + fit:offset + fit + count * 16]) & 0xFF
    rebuilt[checksum_at] = (-total) & 0xFF
    if sum(rebuilt[offset + fit:offset + fit + count * 16]) & 0xFF != 0:
        raise AssertionError("FIT table checksum is not zero after the update")
    return rebuilt[checksum_at]


def find_fit(region: bytes) -> int:
    offsets = [i for i in range(len(region)) if region.startswith(FIT_SIGNATURE, i)]
    if not offsets:
        return -1
    if len(offsets) != 1:
        raise ValueError(f"FIT signature count is not 1: {[hex(x) for x in offsets]}")
    return offsets[0]


def relocate(original: bytes, rebuilt: bytearray, offset: int, size: int) -> list[tuple]:
    if offset < 0 or size <= 0 or offset + size > len(original):
        raise ValueError("region range is outside the image")
    if len(original) != len(rebuilt):
        raise ValueError("original length and rebuilt length differ")

    original_region = original[offset:offset + size]
    rebuilt_region = rebuilt[offset:offset + size]
    fit = find_fit(original_region)
    if fit < 0:
        print("FIT signature is absent. No relocation is necessary.")
        return []
    if rebuilt_region[fit:fit + 8] != FIT_SIGNATURE:
        raise ValueError("rebuilt image has no FIT at the original position")

    count = int.from_bytes(original_region[fit + 8:fit + 12], "little")
    if count < 2 or count > 0x100 or fit + count * 16 > size:
        raise ValueError(f"FIT entry count is invalid: {count}")

    version = int.from_bytes(original_region[fit + 12:fit + 14], "little")
    if version != 0x0100:
        print(f"warning: FIT version is 0x{version:04X}, expected 0x0100")
    if original_region[fit + 14] & 0x7F != 0:
        raise ValueError("FIT header type is not 0")

    table_checksum = fit_table_checksum(original_region, fit, count)
    has_table_checksum = fit_has_table_checksum(original_region, fit)
    if has_table_checksum:
        if table_checksum != 0:
            raise ValueError(
                "FIT header C_V=1 but the table checksum is invalid: "
                f"sum=0x{table_checksum:02X}"
            )
        print(f"FIT header C_V=1. Table checksum is valid. checksum_byte=0x{original_region[fit + 15]:02X}")
    else:
        print(
            "FIT header C_V=0. The table checksum is not used. "
            f"checksum_byte=0x{original_region[fit + 15]:02X} table_sum=0x{table_checksum:02X}"
        )

    image_start = (1 << 32) - size
    changes = []
    for index in range(1, count):
        entry = fit + index * 16
        if original_region[entry + 14] & 0x7F != 1:
            continue
        old_address = struct.unpack_from("<Q", original_region, entry)[0]
        old_offset = old_address - image_start
        if old_offset < 0 or old_offset + SAMPLE_BYTES > size:
            raise ValueError(f"FIT[{index}] address is outside the region: 0x{old_address:016X}")
        needle = original_region[old_offset:old_offset + SAMPLE_BYTES]
        matches = []
        start = 0
        while True:
            position = rebuilt_region.find(needle, start)
            if position < 0:
                break
            matches.append(position)
            start = position + 1
        near = [item for item in matches if abs(item - old_offset) <= 0x10000]
        if len(near) != 1:
            raise ValueError(
                f"FIT[{index}] has {len(matches)} matches and {len(near)} near matches: "
                f"{[hex(item) for item in matches]}"
            )
        new_offset = near[0]
        new_address = image_start + new_offset
        struct.pack_into("<Q", rebuilt, offset + entry, new_address)
        changes.append((index, old_address, new_address, old_offset, new_offset))

    if not changes:
        raise ValueError("FIT has no Type-1 entry")

    if has_table_checksum:
        new_checksum = update_fit_checksum(rebuilt, offset, fit, count)
        print(f"FIT table checksum updated to 0x{new_checksum:02X} (table sum is zero)")

    ffs = fit - 0x18
    if ffs < 0:
        raise ValueError("FIT FFS header is outside the region")
    if original_region[ffs + 19] & 0x40:
        raise ValueError("FIT FFS file has a data checksum flag. This script does not update it.")
    if original_region[ffs + 17] != 0xAA:
        raise ValueError("FIT FFS file checksum is not 0xAA")

    print(f"FIT offset=0x{offset + fit:X} region_offset=0x{offset:X} size=0x{size:X}")
    print(f"entries={count} image_start=0x{image_start:X}")
    for index, old_address, new_address, old_offset, new_offset in changes:
        print(
            f"FIT[{index}] 0x{old_address:016X} -> 0x{new_address:016X} "
            f"file 0x{offset + old_offset:X} -> 0x{offset + new_offset:X} "
            f"delta={new_offset - old_offset:+#x}"
        )
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description="Relocate FIT Type-1 microcode addresses.")
    parser.add_argument("original", type=Path)
    parser.add_argument("rebuilt", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--region-offset", type=lambda x: int(x, 0), default=0)
    parser.add_argument("--region-size", type=lambda x: int(x, 0), default=None)
    args = parser.parse_args()

    original = args.original.read_bytes()
    rebuilt = bytearray(args.rebuilt.read_bytes())
    size = args.region_size if args.region_size is not None else len(original) - args.region_offset
    relocate(original, rebuilt, args.region_offset, size)
    args.output.write_bytes(rebuilt)
    print(f"output={args.output} size={len(rebuilt)} sha256={hashlib.sha256(rebuilt).hexdigest()}")


if __name__ == "__main__":
    main()
