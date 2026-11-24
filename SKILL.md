---
name: garbage-aptio-splash
description: Replace boot splash images in old AMI Aptio firmware found on miscellaneous motherboards. Supports dual-image replacement. B75 and B85 boards serve as verified reference cases.
license: MIT
---

# GAS (Garbage Aptio Splash)

GAS replaces two boot images in an old AMI Aptio firmware image.
The first image is the full-screen boot image.
The second image is the POST corner image at the top left.

GAS applies to miscellaneous boards with an old Aptio firmware.
B75 and B85 are verified reference cases, not templates.
Each board needs its own identification and backup.

## Terms

- Firmware image: the full data read from the flash chip.
- Flash chip: the SPI memory chip that holds the firmware.
- SPI: serial peripheral interface, the bus that connects the flash chip.
- JEDEC ID: the three-byte identity that the flash chip returns.
- PCH: platform controller hub, the chip that connects the CPU to the board devices.
- Descriptor: the partition table at the start of the firmware image.
- Region: a continuous area that the descriptor defines.
- FV: firmware volume, a container for FFS files.
- FFS: firmware file system file, a file with a header and sections.
- Section: a part inside an FFS file.
- GUID: a 16-byte identifier.
- BMP: a bitmap image format.
- FIT: firmware interface table, a table of absolute addresses for microcode and other components.
- NVRAM: non-volatile variable data, such as board configuration and runtime state.
- ROM area: the code area of the firmware, without the ME region and the NVRAM.
- LZMA: a compression method.
- Dithering: the use of a small color set to simulate more colors.
- Programmer: an external device that reads and writes the flash chip.
- POST: power-on self-test, the start test before the operating system starts.
- Full-screen boot image: the image that shows first at power-on. Some documents call it the Quiet Boot splash.
- POST corner image: the small image at the top left while POST text shows. Some documents call it the Verbose logo.

## Hard rules

1. Do not write or erase the flash chip before you have a full backup.
2. Do not restart, power off, or shut down during a write. The user and the agent must obey this rule.

## Stage 1: Decide the risk and the target

1. Ask the user one question: "Do you replace the image on this board or on another board?"
2. Record the target board. The backup comes from the target board. The write goes to the target board.
3. State the risk. The board can fail to start.
4. Ask the user to accept the risk.
5. Stop if the user does not accept the risk.
6. Enter Stage 2 after the user accepts the risk.

GAS strongly recommends a programmer and a second machine.
GAS does not make them a hard condition.

## Stage 2: Identify the flash chip and make a backup

1. Try software identification first.
2. Read the JEDEC ID with software.
3. Read the descriptor.
4. Record the chip model, the chip capacity, and the region layout.
5. Use flashrom first. You can also try another method that reaches the flash chip.

`FLOCKDN=1` does not always mean write protection.
`intel_spi_protected=1` can be a conservative kernel report for an unknown chip.
Make sure that the real read result agrees with your conclusion.

If software identification fails, ask the user for a photo.
Ask the user to find the SPI chip on the board.
Common packages are SOP8, SOIC8, SSOP8, WSON8, USON8, and DFN8.
The chip is usually near the PCH, the crystal, or the BIOS battery.

Give the user these photo instructions.

1. Use 2x or 3x zoom on the phone.
2. Keep the flash on.
3. Make sure that the silkscreen text is clear.

Show the package outlines in `assets/reference-chips/package-outlines.svg`.
The asset is original work under CC0.
Do not ask the user to find a reference image.

If flashrom does not support the chip, do these steps.

1. Search for the chip datasheet.
2. Read the JEDEC ID, the capacity, the sector size, and the erase and write commands.
3. Add the chip entry to the flashrom source.
4. Build a read-only flashrom first.
5. Make sure that the read-only build reads the chip.
6. Enable write support after the read-only build passes.

If you have no search tool, ask the user for the tavily MCP.
Do not guess the command set from memory.

Make the backup with these steps.

1. Read the full chip. The data must include the descriptor, the ME region, and the BIOS region.
2. Save the first read.
3. Read the full chip again.
4. Save the second read.
5. Compare the ROM area of the two reads.
6. Read again if the ROM area differs.
7. Record differences in the ME region and the NVRAM.
8. Save more than one copy.
9. Record the SHA-256 hash of each copy.
10. Make sure that each file size equals the chip capacity.

The ME region and the NVRAM can change during operation.
GAS requires only the ROM area to match.
GAS does not skip the backup for this reason.

Do not write or erase the flash chip before the backup passes.

## Stage 3: Parse the image and make the images

1. Run UEFIExtract with the CLI.
2. Open the report file.
3. Find the two GUIDs in the table.

| Image | GUID |
|---|---|
| Full-screen boot image | `7BB28B99-61BB-11D5-9A5D-0090273FC14D` |
| POST corner image | `63819805-67BB-46EF-AA8D-1524A19A01E4` |

Find each image file with these steps.

1. Find the `File` row with `Subtype` equal to `Freeform` and the target GUID in `Name`.
2. Make sure that the next row has `Type` equal to `Section` and `Subtype` equal to `Compressed`.
3. Make sure that the row after that has `Type` equal to `Section` and `Subtype` equal to `Raw`.
4. Make sure that the indent increases by one level on each row.
5. Extract both FFS files.
6. Read the BMP header at FFS offset `0x25` in each file.
7. Report the resolution, the bit depth, the palette, and the byte length to the user.

Read `references/firmware-structure.md` for the report columns and the BMP fields.

Let the user choose one image route.

- Route A: The user gives an image that already meets the specification. You make sure that the image meets the specification. You use the image after it passes.
- Route B: The user gives any image. You process the image with Pillow.

For Route A, make sure that the canvas size, the bit depth, and the palette are correct.
Make sure that the BMP fields, the file length, and the row alignment are correct.
Route B applies proportional scaling, centered cropping, indexed color conversion, dithering, and black background composition.

Use these default image rules.

1. Scale the image in proportion.
2. Scale the image until both sides are at least the canvas size.
3. Center the image and crop the overflow.
4. Do not stretch the image.
5. Use a black background.
6. Compose a transparent background onto black.
7. You can invert a white background image.
8. You can also replace near-white pixels with black.
9. Keep the canvas size.
10. Keep the bit depth.

Make more than one candidate.
Show the candidates to the user.
Enter Stage 4 after the user chooses a candidate.

Read `references/image-pipeline.md` for the Pillow rules.

## Stage 4: Repack and make sure of the result

1. Build a new compression section from the original FFS file.
2. Replace only the BMP bytes.
3. Keep the padding.
4. Run UEFIReplace for each target GUID.
5. Make sure that the BIOS region length does not change.
6. Make sure that the new data stays inside the BIOS region.
7. Make sure that the data after the target FV stays inside the BIOS region.
8. Make sure that the tail data is not cut off.
9. Compare the module offsets before and after the replacement.
10. Search the BIOS region for the ASCII string `_FIT_`.
11. If `_FIT_` exists, relocate the Type-1 entries that point to moved microcode.
12. If `_FIT_` does not exist, skip the relocation. Do not assume that the image is safe.
13. Compare two independent reads to find the variable area.
14. Put the current variable area from the board into the new image.
15. Run the minimal change checks in `references/repack-and-fit.md`.

The logo change can cause a full recompression of the FV.
The raw byte difference can be large.
Do not use the raw byte difference to measure the change.
Use the structure to measure the change.

## Stage 5: Write back

1. Get this promise from the user: stable power, no restart, no power-off, and no shutdown.
2. Stop the workflow if the user does not give the promise.
3. Write only the BIOS region.
4. Use a layout file for the write.
5. Do not write the descriptor or the ME region.
6. Do not use `--force`.
7. Do not use `--noverify`.
8. Do not use a false chip model.
9. Read the current board image.
10. Build the write image with the current variable area.
11. Write the BIOS region.
12. Read the BIOS region again.
13. Compute the hash of the ROM area.
14. Compare the hash with the expected hash.

If a write error or a hash mismatch occurs, do these steps.

1. Tell the user the current state in direct words.
2. Forbid the user to restart, power off, or shut down.
3. Read the current flash state.
4. State the next step. The usual next step is to write the original BIOS region.
5. Ask the user to agree to the next step.
6. Write the original BIOS region after the user agrees.
7. Read the region again.
8. Make sure that the hash matches.
9. Report the result to the user immediately.
10. Stop the write if a safe recovery is not possible. Tell the user to keep the power on.

Do not give only the instruction "do not restart".
State the forbidden actions and your next step.

Read `references/flashing-and-recovery.md` for the write commands.

## Stage 6: Export a rescue summary

1. Ask the user about the summary before the restart.
2. Tell the user to keep the summary with the original firmware image.
3. Include the board model, the firmware version, the flash model, the JEDEC ID, and the region layout.
4. Include the two GUIDs, the canvas values, the backup paths, and the SHA-256 hashes.
5. Include the change, the offsets, the write command, and the hash results.
6. Include the rescue steps and the cautions.

Read `references/rescue-summary-template.md` for the template.

## References

- `references/firmware-structure.md`: descriptor, FV, FFS, section, report columns, and BMP fields.
- `references/image-pipeline.md`: two image routes, Pillow rules, dithering, and candidates.
- `references/repack-and-fit.md`: size checks, offset checks, FIT relocation, variable area, and minimal change checks.
- `references/flashing-and-recovery.md`: write commands, hash checks, and error recovery.
- `references/case-studies.md`: B75 and B85 observations. Use them as references, not as templates.
- `references/rescue-summary-template.md`: the Markdown summary template.
- `scripts/carve_logo.py`: find BMP data inside an image or an FFS file.
- `scripts/build_compression_section.py`: build a compression section from an FFS file and a BMP file.
- `scripts/relocate_fit.py`: relocate FIT Type-1 microcode addresses.
- `scripts/gen_logo_variants.py`: make 4bpp BMP candidates.
- `scripts/verify_min_diff.py`: report byte differences and ignored ranges.
