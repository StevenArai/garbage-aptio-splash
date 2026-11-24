#!/usr/bin/env python3
"""Report byte differences between a base image and a modified image.

Use --ignore to exclude variable ranges such as the NVRAM. The script exits 0
when every difference is inside an ignored range. It exits 1 when a difference
is outside the ignored ranges.
"""
import argparse
import sys
from pathlib import Path


def parse_range(text: str) -> tuple[int, int]:
    parts = text.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("range must be START:END")
    start = int(parts[0], 0)
    end = int(parts[1], 0)
    if start < 0 or end <= start:
        raise argparse.ArgumentTypeError("range must have START < END")
    return start, end


def make_mask(length: int, ranges: list[tuple[int, int]]) -> bytearray:
    mask = bytearray(length)
    for start, end in ranges:
        if end > length:
            raise ValueError(f"range 0x{start:X}:0x{end:X} is outside the image")
        mask[start:end] = b"\x01" * (end - start)
    return mask


def find_runs(indices: list[int]) -> list[tuple[int, int]]:
    if not indices:
        return []
    runs = []
    start = indices[0]
    previous = indices[0]
    for index in indices[1:]:
        if index != previous + 1:
            runs.append((start, previous + 1))
            start = index
        previous = index
    runs.append((start, previous + 1))
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description="Report byte differences.")
    parser.add_argument("base", type=Path)
    parser.add_argument("modified", type=Path)
    parser.add_argument(
        "--ignore",
        type=parse_range,
        action="append",
        default=[],
        help="start:end range to exclude. Repeat for each range.",
    )
    parser.add_argument("--max-runs", type=int, default=20)
    args = parser.parse_args()

    base = args.base.read_bytes()
    modified = args.modified.read_bytes()
    if len(base) != len(modified):
        print(f"length mismatch: base={len(base)} modified={len(modified)}")
        sys.exit(2)

    mask = make_mask(len(base), args.ignore)
    outside = [
        index
        for index in range(len(base))
        if base[index] != modified[index] and not mask[index]
    ]
    total_diff = sum(1 for index in range(len(base)) if base[index] != modified[index])
    ignored_diff = total_diff - len(outside)

    print(f"base={args.base} modified={args.modified}")
    print(f"length={len(base)} total_diff={total_diff} ignored_diff={ignored_diff}")
    for start, end in args.ignore:
        print(f"ignore: 0x{start:X}:0x{end:X} ({end - start} bytes)")
    print(f"outside_diff={len(outside)}")

    runs = find_runs(outside)
    print(f"outside_runs={len(runs)}")
    for start, end in sorted(runs, key=lambda item: item[1] - item[0], reverse=True)[
        : args.max_runs
    ]:
        print(f"  0x{start:X}:0x{end:X} ({end - start} bytes)")

    if outside:
        sys.exit(1)


if __name__ == "__main__":
    main()
