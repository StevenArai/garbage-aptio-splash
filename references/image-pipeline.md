# Image pipeline

This document describes the two image routes and the default image rules.
Use the BMP header from the target board as the specification.

## Route A: The user gives a compliant image

1. Read the BMP header.
2. Make sure that the signature is `BM`.
3. Make sure that `bfSize` equals the file length.
4. Make sure that the width and the height equal the target values.
5. Make sure that the bit depth equals the target value.
6. Make sure that `biCompression` equals 0.
7. Make sure that the palette length matches the bit depth.
8. Make sure that `bfOffBits` equals 14 + the DIB header length + the palette length.
9. Make sure that each row is padded to a 4-byte boundary.
10. Make sure that the pixel data is not truncated.
11. Report each failed check to the user.
12. Do not use the image if a check fails. Offer Route B instead.

## Route B: The user gives any image

1. Open the image with Pillow.
2. Convert the image to RGB or RGBA.
3. If the image has an alpha channel, compose it onto a black background.
4. If the background is white, use one of these methods.
5. Invert the image, or replace near-white pixels with black.
6. Scale the image in proportion until both sides are at least the canvas size.
7. Center the image on the canvas.
8. Crop the overflow.
9. Do not stretch the image.
10. Resize the result to the exact canvas size.
11. Convert the result to the target palette.
12. Use dithering when the image has a gradient.
13. Save the result as a BMP with the target bit depth.
14. Make sure that the output BMP header matches the target header.

Do not upscale a small image to a large canvas.
Upscaling adds blur.
Ask the user for a larger image instead.

## Default rules

- Scale mode: proportional cover.
- Crop mode: center crop.
- Background: black.
- Transparent pixels: compose onto black.
- White background: invert, or replace near-white pixels with black.
- Canvas size: the original BMP size.
- Bit depth: the original bit depth.
- Palette: the original palette, or a generated palette with the same size.
- Dithering: on for gradients, off for flat logos.

The full-screen boot image and the POST corner image can use different rules.
Ask the user when the two images need different treatment.

## Dithering

Dithering mixes palette colors in a small pattern.
The eye sees more colors than the palette has.
Dithering can add visible noise to a flat logo.

Use Floyd and Steinberg error diffusion for photographs and gradients.
Use no dithering for text and flat shapes.
Make one candidate with dithering and one without.
Show both candidates to the user.

## Candidate set

Make at least two candidates for Route B.
Use these variants:

1. Proportional cover, black background, dithering on.
2. Proportional cover, black background, dithering off.
3. Optional: inverted or white-keyed variant for a white background source.

Send the candidates to the user as image attachments.
Record the chosen candidate and the rules that made it.

## 4bpp output

The reference boards use a 4bpp BMP with a 16-entry palette.
`scripts/gen_logo_variants.py` writes this format.

The 4bpp BMP has these properties:

- 16 palette entries.
- 4 bytes per palette entry in BGRA order.
- 4 bits per pixel.
- Bottom-up rows by default.
- Each row padded to a 4-byte boundary.
- `biClrUsed` equal to 16 or 0. Use 16 for a new file.

If the target BMP has another bit depth, use an encoder for that bit depth.
Do not write a 4bpp BMP into an 8bpp or 32bpp slot.
The boot firmware can reject the image or show a corrupted image.

## Report to the user

Report these values before the repack:

- Canvas width and height.
- Bit depth.
- Palette entry count.
- BMP length in bytes.
- Expected BMP length from the original file.
- The selected route and the applied rules.

Make sure that the new BMP length fits the slot.
The compression section can hold a different length, but the FV must hold the new file.
