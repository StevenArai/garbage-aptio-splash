# Rescue summary template

Fill this template after the write.
Give the result to the user before the restart.
Tell the user to keep this file with the original firmware image.

```markdown
# Boot image replacement summary

## Board

- Board model: <model>
- Board version: <version>
- BIOS version: <version>
- SIO model: <model or unknown>

## Flash chip

- Model: <model>
- JEDEC ID: <1C 71 17>
- Capacity: <bytes>
- Package: <package>
- Access method: <internal flashrom or programmer or other>

## Region layout

- Descriptor: <start> to <end>
- ME region: <start> to <end>
- BIOS region: <start> to <end>
- GbE region: <start> to <end or absent>
- PDR region: <start> to <end or absent>

## Images

- Full-screen GUID: 7BB28B99-61BB-11D5-9A5D-0090273FC14D
- Full-screen canvas: <width>x<height>, <bpp>bpp, <colors> colors
- Full-screen FFS size: <bytes>
- POST corner GUID: 63819805-67BB-46EF-AA8D-1524A19A01E4
- POST corner canvas: <width>x<height>, <bpp>bpp, <colors> colors
- POST corner FFS size: <bytes>

## Backup files

- Full backup 1: <path> sha256=<hash>
- Full backup 2: <path> sha256=<hash>
- Pre-write read: <path> sha256=<hash>
- Original BIOS region: <path> sha256=<hash>

## Change

- Full-screen source image: <path>
- Full-screen route: <A or B>
- Full-screen rules: <scale, crop, background, dither>
- POST corner source image: <path>
- POST corner route: <A or B>
- POST corner rules: <scale, crop, background, dither>
- New full-screen BMP size: <bytes>
- New POST corner BMP size: <bytes>

## Repack record

- Base image: <path>
- UEFIReplace full-screen command: <command>
- UEFIReplace POST corner command: <command>
- Result image: <path> sha256=<hash>
- Result length: <bytes>
- FIT offset: <offset or none>
- FIT changes: <entry list or none>
- Variable ranges: <ranges>
- Diff bytes inside allowed ranges: <count>
- Diff bytes outside allowed ranges: <count>

## Write record

- Write image: <path> sha256=<hash>
- Layout file: <contents>
- Write command: <command>
- Write result: <success or error text>
- After-write read: <path> sha256=<hash>
- ROM area hash before write: <hash>
- ROM area hash after write: <hash>
- Hash match: <yes or no>

## Result

- Board starts: <yes or no or not tested>
- Full-screen image shows: <yes or no>
- POST corner image shows: <yes or no>
- Notes: <text>

## Rescue steps

1. Keep the power on after a failed write.
2. Do not restart. Do not power off. Do not shut down.
3. Read the chip again.
4. Write the original BIOS region from the pre-write read.
5. If the internal write path fails, use a programmer.
6. Write the full backup with the programmer.
7. Read the chip again and compare the full image.

## Cautions

- Do not write the descriptor or the ME region during a boot image change.
- Do not use --force.
- Do not use --noverify.
- Do not write a partial image.
- Keep more than one backup copy.
```
