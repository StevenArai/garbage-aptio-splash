# Case studies

This document records the B75 and B85 observations.
Use the observations as references.
Do not use them as templates.
Each board needs its own report and its own backup.

## B75

- Full chip size: 4 MiB.
- BIOS region: `0x180000` to `0x3FFFFF`.
- Descriptor: 4 KiB.
- ME region: about 1.5 MiB.
- GbE region and PDR region: absent.
- Full-screen boot image: 640x480, 4bpp, blank black in the backup image.
- POST corner image: 400x100, 4bpp.
- POST corner FFS size: 20157 bytes.
- POST corner BMP size: 20118 bytes.
- FIT signature: not found in the tested images.
- The backup image is a white-label B75NA00C build.
- The official images are HUANANZHI builds.
- The backup shares 16 FFS modules with each official image.
- The official images share 48 to 49 FFS modules with each other.
- The backup is a different lineage from the official images.

The official images use other full-screen formats:

- One official image uses 568x151, 32bpp.
- Other official images use 1200x900, 8bpp.
- Two official images have a byte-identical full-screen image.

A splash replacement on the backup changed the raw bytes from `0x1D0058` to `0x3205FB`.
The changed range is 1.37 MiB.
The FV uses LZMA compression.
The whole FV was compressed again.
This is a normal result, not a sign of a bad edit.

## B85

- Flash chip: EN25QX64A.
- JEDEC ID: `1C 71 17`.
- Full chip size: 8 MiB.
- BIOS region: `0x400000` to `0x7FFFFF`.
- Full-screen boot image: 568x151, 4bpp, 16 colors.
- Full-screen FFS size: 43041 bytes.
- Full-screen BMP size: 43002 bytes.
- Full-screen `bfOffBits`: `0x76`.
- Full-screen `biSize`: 40.
- Full-screen `biClrUsed`: 0. The palette has 16 entries.
- POST corner image: 400x100, 4bpp, 16 colors.
- POST corner FFS size: 20157 bytes.
- POST corner BMP size: 20118 bytes.
- POST corner `biClrUsed`: 16.
- FIT offset in the BIOS region: `0x320060`.
- FIT Type-1 microcode entries: 3.

Both boards contain the two GUIDs:

| Image | GUID |
|---|---|
| Full-screen boot image | `7BB28B99-61BB-11D5-9A5D-0090273FC14D` |
| POST corner image | `63819805-67BB-46EF-AA8D-1524A19A01E4` |

## Lessons

1. The same GUID does not mean the same BMP format. Read the BMP header.
2. The same brand can use different formats in different firmware versions.
3. A board can have a FIT with microcode entries. Another board can have no FIT. Detect it.
4. A small image change can recompress a whole FV. A large raw diff is normal.
5. A backup image and an official image can come from different lineages. Do not mix them.
6. Do not write an official image on a board with a different lineage. The board can fail to start.
7. The ME region and the NVRAM can change during operation. Compare only the ROM area.
8. Two firmware versions can have byte-identical image files. Make sure that the target file is the one you want.
9. A POST corner image can have the same size on two boards. Still extract it from the target board.
10. The variable area can change after the first read. Use the current read, not an old backup.
