# Firmware structure

This document describes the firmware layout and the report fields.
Use it to find the two image files without a hard-coded offset.

## Descriptor and regions

The firmware image starts with the descriptor.
The descriptor is a partition table.
It defines the start and the end of each region.
Common regions are the descriptor region, the ME region, and the BIOS region.
Some boards also have a GbE region or a PDR region.

Read the descriptor before you use any offset.
Do not use an offset from another board.

## FV, FFS, and section

The BIOS region holds one or more FVs.
An FV is a container for FFS files.
An FFS file has a header and one or more sections.
A section is a part inside an FFS file.

The two image files have this hierarchy:

1. `File` row with `Subtype` equal to `Freeform`.
2. `Section` row with `Subtype` equal to `Compressed`.
3. `Section` row with `Subtype` equal to `Raw`.
4. BMP data inside the raw section.

The compression section can hold uncompressed data or compressed data.
The algorithm byte is `0x00` for uncompressed data.
The algorithm byte is `0x01` for LZMA data.
Make sure that the byte is `0x00` before you replace the BMP data.

The FV that holds the image file can also be compressed.
In that case, the GUID is not visible in the raw image bytes.
The report offsets are not file offsets in that case.

## Report columns

UEFIExtract writes six columns in this order:

`Type | Subtype | Base | Size | CRC32 | Name`

`Size` is the byte length of the item.
`Size` is not an offset.
`Base` shows `N/A` when the item is inside compressed content.
Do not use `Base` for these items.

The `Name` field has a dash prefix.
The dash count shows the nesting level.
The indent increases by one level on each child row.

## Find an image file

1. Find the `File` row with `Subtype` equal to `Freeform`.
2. Make sure that `Name` contains the target GUID.
3. Read the next row. It must have `Type` equal to `Section` and `Subtype` equal to `Compressed`.
4. Read the row after that. It must have `Type` equal to `Section` and `Subtype` equal to `Raw`.
5. Make sure that the dash count increases by one on each row.
6. Record the `Size` value from all three rows.

The GUIDs are:

| Image | GUID |
|---|---|
| Full-screen boot image | `7BB28B99-61BB-11D5-9A5D-0090273FC14D` |
| POST corner image | `63819805-67BB-46EF-AA8D-1524A19A01E4` |

## Size relations

The image file stores the BMP data at FFS offset `0x25`.
The FFS file has 2 zero bytes after the BMP data.
The raw section is padded to a 4-byte boundary.

For a 4bpp BMP with a 16-entry palette, the relations are:

| Item | Relation |
|---|---|
| Raw section size | BMP size + 4 |
| Raw padding | 0 to 3 bytes, to a 4-byte boundary |
| Compression section size | 9 + raw section size + raw padding |
| FFS size | 0x18 + compression section size |
| BMP start | FFS start + 0x25 |

Other bit depths have other palette and row sizes.
Use the BMP header to get the real values.

## BMP fields

Read the BMP header at FFS offset `0x25`.

| Field | Offset from BMP start | Meaning |
|---|---|---|
| Signature | 0 | `BM` |
| `bfSize` | 2 | BMP length in bytes |
| `bfOffBits` | 10 | Pixel data start |
| `biSize` | 14 | DIB header length |
| `biWidth` | 18 | Width in pixels |
| `biHeight` | 22 | Height in pixels. A positive value means bottom-up rows. |
| `biPlanes` | 26 | Plane count. The common value is 1. |
| `biBitCount` | 28 | Bit depth |
| `biCompression` | 30 | Compression method. The common value is 0. |
| `biSizeImage` | 34 | Pixel data length |
| `biClrUsed` | 46 | Palette entry count. The value can be 0 or 16. |

A 16-color 4bpp BMP has a 16-entry palette.
Each palette entry has 4 bytes in BGRA order.
Each row is padded to a 4-byte boundary.

Do not assume a bit depth.
Reference boards use 4bpp, 8bpp, and 32bpp images.
Use the BMP header from the target board.
