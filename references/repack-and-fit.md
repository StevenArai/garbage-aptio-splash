# Repack and FIT

This document describes the repack steps and the checks after the repack.
Run the checks in order.
Do not skip a failed check.

## Build the compression section

1. Extract the original FFS file.
2. Extract the original BMP file from the FFS file.
3. Make the new BMP file with the same canvas and the same bit depth.
4. Run the build script.

```
python scripts/build_compression_section.py original.ffs new.bmp new_section.bin
```

The script checks these items:

- The FFS file has a compression section with type `0x01`.
- The compression algorithm is `0x00`.
- The raw section has type `0x19`.
- The BMP signature is `BM`.
- The raw section padding is correct.

The script keeps the original FFS layout.
It writes a section file, not a full firmware image.

## Replace the section

Run UEFIReplace for each target GUID.
Use type `01` for the compression section.

```
UEFIReplace base.bin 7BB28B99-61BB-11D5-9A5D-0090273FC14D 01 full_section.bin -o step1.bin
UEFIReplace step1.bin 63819805-67BB-46EF-AA8D-1524A19A01E4 01 post_section.bin -o result.bin
```

The order does not matter.
Use the output of the first command as the input of the second command.

If UEFIReplace reports that the GUID is not found, do these steps.

1. Make sure that the report row has `Subtype` equal to `Freeform`.
2. Make sure that the GUID text is exact.
3. Make sure that the input is the BIOS region or the full image that contains the BIOS region.
4. Do not guess a different GUID.

## File length

1. Compare the length of the base image and the result image.
2. Stop if the lengths differ.
3. Make sure that the new data does not cross the BIOS region boundary.
4. Make sure that the tail data after the target FV is not truncated.

UEFIReplace rebuilds the FV and can move the data after the FV.
A moved tail is not always an error.
A truncated tail is an error.

## Module offset check

1. Make a report for the base image.
2. Make a report for the result image.
3. Compare the rows by GUID and by name.
4. Make sure that the hierarchy and the order do not change.
5. Make sure that the target FFS files keep the expected size relation.
6. Make sure that the FIT FFS file and the NVRAM FFS file are present.

Offsets inside the changed FV can move.
Offsets of files outside the changed FV must not move unless the FV size changed.
If the FV size changed, record the new offsets.

## FIT relocation

The FIT is a table of absolute addresses.
A Type-1 entry points to a microcode block.
The FV rebuild can move the microcode block.
A moved block needs a new address in the FIT.

1. Search the BIOS region for the ASCII string `_FIT_   `.
2. Stop if the string occurs more than one time.
3. If the string does not occur, skip the relocation.
4. Read the entry count from offset 8 of the FIT header.
5. Process each Type-1 entry. The type is the low 7 bits of the byte at offset 14.
6. Run the relocation script.

```
python scripts/relocate_fit.py original_region.bin result_region.bin fit_fixed.bin
```

For a full chip input, give the region offset and the region size.

```
python scripts/relocate_fit.py original.bin result.bin fit_fixed.bin --region-offset 0x400000 --region-size 0x400000
```

The script does these steps:

1. Computes the mapped image start as `2^32 - region size`.
2. Reads the old address from the Type-1 entry.
3. Takes a 1024-byte sample at the old target.
4. Finds the same sample near the old position in the rebuilt region.
5. Writes the new address into the entry.
6. Makes sure that the FIT FFS file has no data checksum.

Stop if the sample has more than one near match.
Do not guess the new address.

Make sure that the FIT file checksum is still valid after the edit.
The reference B85 FIT FFS file has data checksum `0xAA` and no checksum flag.
Other boards can use a real checksum.
If the script stops on a checksum flag, update the FFS checksum with a tool.

## Variable area

The NVRAM can change between two reads.
The ME region can change between two reads.
These ranges are variable.

1. Read the current chip two times.
2. Compare the two reads.
3. Record each range that differs.
4. Record each range that is the same.
5. Use the current read, not an old backup.
6. Copy the current variable range into the new image.
7. Do not copy the whole ME region unless the write covers the ME region.

Do not hard-code a variable address.
Do not hard-code the NVRAM start or end.
Get the ranges from the current board.

If a variable range overlaps the target FV, stop.
Ask for help before you continue.

## Minimal change check

Run the diff script.

```
python scripts/verify_min_diff.py base.bin result.bin --ignore 0x400000:0x401000
```

Repeat `--ignore` for each variable range.

The expected differences are:

1. The content of the target FV.
2. The FIT entries that point to moved microcode.
3. The variable area that you copied from the current board.

Stop if a code area outside the target FV differs.
Stop if another FFS file changed.
A large raw diff is normal when the FV uses LZMA compression.
Do not use the raw diff size as a quality measure.

## Report the checks

Report these values to the user:

- Base length and result length.
- The two FFS sizes before and after.
- The FIT offset and each changed entry.
- The variable ranges.
- The diff count inside the allowed ranges.
- The diff count outside the allowed ranges. The value must be 0.
