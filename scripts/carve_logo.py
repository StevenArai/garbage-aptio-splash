#!/usr/bin/env python3
"""Find BMP data in a firmware image or an FFS file and save it as PNG.

The script scans for valid BMP headers and validates the basic geometry.
Use it to inspect an extracted image and to compare the result with the source.
Add --save-bmp to keep the exact BMP bytes.

Requires Pillow. Run: python -m pip install pillow
"""
import argparse
import io
import os
import struct
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is not installed. Run: python -m pip install pillow")


def carve(data: bytes, label: str, outdir: str, save_bmp: bool) -> int:
    offset = 0
    index = 0
    while True:
        position = data.find(b"BM", offset)
        if position < 0:
            break
        offset = position + 2
        if position + 54 > len(data):
            continue
        bmp_size = struct.unpack_from("<I", data, position + 2)[0]
        dib_size = struct.unpack_from("<I", data, position + 14)[0]
        if dib_size not in (40, 108, 124):
            continue
        width = struct.unpack_from("<i", data, position + 18)[0]
        height = struct.unpack_from("<i", data, position + 22)[0]
        bit_count = struct.unpack_from("<H", data, position + 28)[0]
        colors_used = struct.unpack_from("<I", data, position + 46)[0]
        if not (0 < abs(width) <= 4096 and 0 < abs(height) <= 4096):
            continue
        if bit_count not in (1, 4, 8, 16, 24, 32):
            continue
        if not (100 < bmp_size <= len(data) - position):
            continue
        blob = data[position:position + bmp_size]
        try:
            image = Image.open(io.BytesIO(blob))
            image.load()
        except Exception as error:
            print(
                f"  @0x{position:X} {width}x{abs(height)} {bit_count}bpp "
                f"size={bmp_size} is not a BMP: {error}"
            )
            continue

        name = f"{label}_{index}_{image.width}x{image.height}"
        png_path = os.path.join(outdir, name + ".png")
        image.convert("RGB").save(png_path)
        colors = image.convert("RGB").getcolors(maxcolors=1 << 20) or []
        blank = " blank" if len(colors) == 1 else ""
        print(
            f"  @0x{position:X} {image.width}x{image.height} {bit_count}bpp "
            f"clrUsed={colors_used} size={bmp_size} -> {os.path.basename(png_path)}{blank}"
        )
        if save_bmp:
            bmp_path = os.path.join(outdir, name + ".bmp")
            with open(bmp_path, "wb") as handle:
                handle.write(blob)
            print(f"  saved: {bmp_path}")
        index += 1

    if index == 0:
        print("  no valid BMP found")
    return index


def iter_inputs(paths: list[str]):
    for path in paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for name in files:
                    if name.lower().endswith((".bin", ".ffs", ".rom", ".fd")):
                        yield os.path.join(root, name)
        else:
            yield path


def main() -> None:
    parser = argparse.ArgumentParser(description="Carve BMP data to PNG.")
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("-o", "--outdir", default="carved_logos")
    parser.add_argument("--save-bmp", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    total = 0
    for path in iter_inputs(args.inputs):
        label = os.path.splitext(os.path.basename(path))[0]
        with open(path, "rb") as handle:
            data = handle.read()
        print(f"=== {label} ({len(data)} bytes) ===")
        total += carve(data, label, args.outdir, args.save_bmp)
    print(f"done: {total} image(s) -> {args.outdir}")


if __name__ == "__main__":
    main()
