# Flashing and recovery

This document describes the write flow and the recovery flow.
The write flow applies to an internal flash write with flashrom.
You can use another access method if it reaches the same chip and gives the same result.

## Write-time promise

1. Ask the user for this promise before the write.
2. Stable power for the full write.
3. No restart.
4. No power-off.
5. No shutdown.
6. No sleep or hibernation.
7. Stop if the user does not give the promise.

The agent must also obey the promise.
Do not start a write near a known power event.
Do not start a write when the battery is low on a laptop.

## Write only the BIOS region

1. Read the descriptor.
2. Get the BIOS region start and end.
3. Make a layout file with the BIOS range.
4. Use the current full chip read as the base.
5. Replace the BIOS region in the base with the new BIOS region.
6. Keep the descriptor and the ME region from the current read.

Example layout for a 4 MiB BIOS region at `0x400000`:

```
0x00400000:0x007fffff bios
```

The values come from the target descriptor.
Do not use these example values on another board.

## Write flow

1. Read the current chip to `pre.bin`.
2. Read the current chip again to `current.bin`.
3. Compare the ROM area of `pre.bin` and `current.bin`.
4. Stop if the ROM area differs. Read again.
5. Build `write.bin` from `pre.bin` and the new BIOS region.
6. Write with the layout file.

```
./flashrom -p internal -l bios.layout -i bios -w write.bin
```

`-w` needs a full chip image.
The layout and `-i bios` limit the write to the BIOS region.

Do not use `--force`.
Do not use `--noverify`.
Do not use a false chip model.
Do not write the descriptor.
Do not write the ME region.

## Read back and make sure of the result

1. Read the chip to `after.bin`.
2. Read the chip again to `after2.bin`.
3. Compare the ROM area of `after.bin` and `after2.bin`.
4. Stop if the ROM area differs. Read again.
5. Compute the SHA-256 hash of the ROM area in `after.bin`.
6. Compare the hash with the ROM area hash of `write.bin`.
7. Report the result to the user.

The ME region and the NVRAM can differ after the write.
Compare only the ROM area for the write result.

## Error flow

Use this flow after a write error, an erase error, or a hash mismatch.

1. Tell the user the current state in direct words.
2. Forbid the user to restart, power off, or shut down.
3. Read the chip state if a read is possible.
4. State the next step. The usual next step is to restore the original BIOS region.
5. Ask the user to agree to the next step.
6. Restore after the user agrees.
7. Read the region again.
8. Make sure that the hash matches.
9. Report the result to the user immediately.
10. Tell the user to keep the power on if a safe recovery is not possible.

Do not tell the user only that a restart is not required.
State the forbidden actions and your next step.

## Restore the original BIOS region

1. Use the BIOS region from `pre.bin`. It is the last known good state.
2. If `pre.bin` is not available, use the BIOS region from the full backup.
3. Put the original BIOS region into a full chip image.
4. Write with the layout file.
5. Read the chip again.
6. Compute the hash of the ROM area.
7. Compare the hash with the original BIOS region hash.

If the write path is still not stable, stop the writes.
Tell the user that a programmer is necessary.
A programmer can write the full backup without the board firmware.

## Programmer path

1. Use the full backup from Stage 2.
2. Connect the programmer to the flash chip.
3. Read the chip and save the current data.
4. Compare the current data with the failed state.
5. Write the full backup.
6. Read the chip again.
7. Compare the full image with the backup.
8. Tell the user to start the board after the compare passes.

Do not write a partial image with a programmer.
Do not use a programmer clip on a powered board.

## Recovery files

Keep these files together until the board starts correctly:

- The full backup.
- The two pre-write reads.
- The new BIOS region.
- The full write image.
- The after-write reads.
- The rescue summary.
- The original BIOS region file.

Keep the files on a second machine too.
