# Optional advanced path: add flash chip support

This document is optional.
Use it only when the user agrees to an advanced path.
The normal paths are a supported flashrom build, a programmer, or another access method that reaches the same chip.
Do not modify flashrom by default.
Do not compile flashrom during a splash replacement without the user's agreement.

## When to use it

- flashrom does not know the chip.
- A programmer is not available.
- The user accepts the build work and the risk.

## Steps

1. Get the chip model from the photo.
2. Get the JEDEC ID from a read attempt. Read all bytes, including a continuation byte.
3. Find the chip datasheet. Search the vendor site first.
4. Record the capacity, the sector size, the page size, the erase commands, and the write commands.
5. Read the status register and record the block protection bits.
6. Find the closest existing flashrom chip entry.
7. Add a new entry. Do not change an existing entry.
8. Build a read-only flashrom first.
9. Read the full chip. Save the data.
10. Read the full chip again. Compare the ROM area of the two reads.
11. Enable write support only after the read passes.
12. Build again.
13. Write only the BIOS region with the layout file.
14. Read back and compare the ROM area.

## Rules

- Do not guess the command set.
- Do not copy a command set from a different chip.
- Do not enable write before a correct read.
- Do not use `--force`.
- Do not write the descriptor or the ME region.
- Keep the source patch, the build log, and the read-only result with the rescue files.

## Notes

- A wrong read is worse than no read. Stop on a read mismatch.
- The status register can differ between chips with the same JEDEC ID.
- A read-only build is the proof that the command set is correct.
- If the write path is still not stable, stop. Use a programmer.
