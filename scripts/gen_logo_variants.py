#!/usr/bin/env python3
"""Generate 16-color 4bpp BMP boot image candidates from a source image.

Pillow cannot write 4bpp BMP files, so this script writes the BMP structure
directly: a BITMAPINFOHEADER, a 16-entry BGRA palette, and bottom-up rows with
two pixels per byte.

The canvas must match the target BMP header. Use --width and --height.
"""
import argparse
import os
import struct
import sys

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is not installed. Run: python -m pip install pillow")

NCOLORS = 16
GEOMETRIES = ("crop", "letterbox")
QUANTIZERS = {
    "mediancut": Image.Quantize.MEDIANCUT,
    "maxcoverage": Image.Quantize.MAXCOVERAGE,
    "fastoctree": Image.Quantize.FASTOCTREE,
}
DITHERS = {
    "none": Image.Dither.NONE,
    "floyd": Image.Dither.FLOYDSTEINBERG,
    "ordered": Image.Dither.ORDERED,
}


def prepare(path: str, white_mode: str) -> Image.Image:
    image = Image.open(path)
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        image = image.convert("RGBA")
        canvas = Image.new("RGB", image.size, (0, 0, 0))
        canvas.paste(image, mask=image.getchannel("A"))
        image = canvas
    else:
        image = image.convert("RGB")

    if white_mode == "invert":
        image = ImageOps.invert(image)
    elif white_mode == "key":
        rgba = image.convert("RGBA")
        pixels = rgba.load()
        for y in range(rgba.height):
            for x in range(rgba.width):
                red, green, blue, alpha = pixels[x, y]
                if red >= 240 and green >= 240 and blue >= 240:
                    pixels[x, y] = (0, 0, 0, 0)
        canvas = Image.new("RGB", rgba.size, (0, 0, 0))
        canvas.paste(rgba, mask=rgba.getchannel("A"))
        image = canvas
    return image


def fit(image: Image.Image, width: int, height: int, mode: str) -> Image.Image:
    source_width, source_height = image.size
    if mode == "stretch":
        return image.resize((width, height), Image.LANCZOS)
    if mode == "crop":
        scale = max(width / source_width, height / source_height)
        resized_width = round(source_width * scale)
        resized_height = round(source_height * scale)
        resized = image.resize((resized_width, resized_height), Image.LANCZOS)
        left = (resized_width - width) // 2
        top = (resized_height - height) // 2
        return resized.crop((left, top, left + width, top + height))
    if mode == "letterbox":
        scale = min(width / source_width, height / source_height)
        resized_width = round(source_width * scale)
        resized_height = round(source_height * scale)
        resized = image.resize((resized_width, resized_height), Image.LANCZOS)
        canvas = Image.new("RGB", (width, height), (0, 0, 0))
        canvas.paste(resized, ((width - resized_width) // 2, (height - resized_height) // 2))
        return canvas
    raise ValueError(mode)


def quantize(image: Image.Image, quantizer: str, dither: str) -> Image.Image:
    method = QUANTIZERS[quantizer]
    dither_mode = DITHERS[dither]
    if method == Image.Quantize.FASTOCTREE:
        return image.quantize(colors=NCOLORS, method=method, dither=dither_mode)
    palette_image = image.quantize(colors=NCOLORS, method=method)
    return image.quantize(palette=palette_image, dither=dither_mode)


def write_bmp4(image: Image.Image, path: str) -> int:
    width, height = image.size
    pixels = image.load()
    palette_data = (image.getpalette() or [])[: NCOLORS * 3]
    palette_data += [0] * (NCOLORS * 3 - len(palette_data))
    palette = b"".join(
        struct.pack(
            "<BBBB",
            palette_data[index * 3 + 2],
            palette_data[index * 3 + 1],
            palette_data[index * 3],
            0,
        )
        for index in range(NCOLORS)
    )

    row_bytes = (width + 1) // 2
    padded = (row_bytes + 3) & ~3
    rows = []
    for y in range(height - 1, -1, -1):
        buffer = bytearray(padded)
        for x in range(0, width, 2):
            high = pixels[x, y] & 0x0F
            low = pixels[x + 1, y] & 0x0F if x + 1 < width else 0
            buffer[x // 2] = (high << 4) | low
        rows.append(bytes(buffer))
    pixel_data = b"".join(rows)

    offset_bits = 14 + 40 + len(palette)
    total = offset_bits + len(pixel_data)
    file_header = struct.pack("<2sIHHI", b"BM", total, 0, 0, offset_bits)
    dib_header = struct.pack(
        "<IiiHHIIiiII",
        40,
        width,
        height,
        1,
        4,
        0,
        len(pixel_data),
        2835,
        2835,
        NCOLORS,
        0,
    )
    with open(path, "wb") as handle:
        handle.write(file_header + dib_header + palette + pixel_data)
    return total


def verify_bmp4(path: str, width: int, height: int) -> str | None:
    with Image.open(path) as image:
        image.load()
        if image.size != (width, height):
            return f"geometry {image.size} != ({width},{height})"
        colors = image.convert("RGB").getcolors(maxcolors=1 << 16) or []
        if len(colors) > NCOLORS:
            return f"{len(colors)} colors decoded, more than {NCOLORS}"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 4bpp BMP boot image candidates.")
    parser.add_argument("source")
    parser.add_argument("-o", "--outdir", default="logo_candidates")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--white-mode", choices=("none", "invert", "key"), default="none")
    parser.add_argument("--budget", type=int, default=None, help="expected BMP length in bytes")
    parser.add_argument("--geometries", default="crop,letterbox")
    parser.add_argument("--quantizers", default="mediancut,maxcoverage,fastoctree")
    parser.add_argument("--dithers", default="none,floyd,ordered")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    source = prepare(args.source, args.white_mode)
    geometries = [item.strip() for item in args.geometries.split(",") if item.strip()]
    quantizers = [item.strip() for item in args.quantizers.split(",") if item.strip()]
    dithers = [item.strip() for item in args.dithers.split(",") if item.strip()]

    print(f"source: {args.source} {source.width}x{source.height}")
    print(f"target: {args.width}x{args.height} 4bpp {NCOLORS} colors")
    print(f"white mode: {args.white_mode}")

    written = 0
    broken = 0
    size_seen = None
    for geometry in geometries:
        base = fit(source, args.width, args.height, geometry)
        for quantizer in quantizers:
            for dither in dithers:
                name = f"{geometry}_{quantizer}_{dither}.bmp"
                output = os.path.join(args.outdir, name)
                palette_image = quantize(base, quantizer, dither)
                used = len(set(palette_image.getdata()))
                if max(set(palette_image.getdata())) >= NCOLORS:
                    print(f"  {name}: palette index is outside 0..{NCOLORS - 1}")
                    broken += 1
                    continue
                total = write_bmp4(palette_image, output)
                size_seen = total
                error = verify_bmp4(output, args.width, args.height)
                if error:
                    print(f"  {name}: broken: {error}")
                    broken += 1
                    continue
                print(f"  {name}: {total} bytes, {used} colors, verified")
                written += 1

    print(f"{written} written, {broken} broken, output={args.outdir}")
    if args.budget is not None and size_seen is not None:
        print(f"budget={args.budget} actual={size_seen} delta={size_seen - args.budget:+#d}")


if __name__ == "__main__":
    main()
