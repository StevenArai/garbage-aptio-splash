# GAS (Garbage Aptio Splash)

GAS replaces the two boot images in an old AMI Aptio firmware image.
It works on miscellaneous motherboards with an old Aptio firmware.
B75 and B85 are verified reference cases.

The two images are:

- The full-screen boot image at power-on. GUID `7BB28B99-61BB-11D5-9A5D-0090273FC14D`.
- The small POST corner image. GUID `63819805-67BB-46EF-AA8D-1524A19A01E4`.

## What it covers

- Flash chip identification and full backup.
- UEFI module parsing with UEFIExtract.
- Two image routes: a compliant image, or any image with Pillow.
- 4bpp BMP generation with a 16-color palette.
- Compression section rebuild and UEFIReplace.
- FIT Type-1 microcode relocation.
- BIOS region write with a layout file.
- Hash checks and recovery steps.
- A rescue summary template.

## Quick start

Read `SKILL.md` first.
It has the hard rules and the six stages.
The stage order is mandatory.

Run the scripts with Python 3.10 or later.
Install Pillow for the image scripts.

```
python -m pip install pillow
```

The scripts use these arguments:

```
python scripts/carve_logo.py firmware.bin --save-bmp
python scripts/gen_logo_variants.py source.png --width 640 --height 480
python scripts/build_compression_section.py original.ffs new.bmp section.bin
python scripts/relocate_fit.py original.bin rebuilt.bin fixed.bin
python scripts/verify_min_diff.py base.bin result.bin --ignore 0x400000:0x401000
```

## Tests

The tests use synthetic images. They do not need a board or a firmware file.

```
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The tests cover the BMP checks, the FFS section checks, the FIT relocation with both checksum cases, the minimal diff exit codes, the image generator, and the carve step.

## Safety

A firmware write can stop the board from starting.
Make a full backup before any write.
Keep the power stable during a write.
Do not restart, power off, or shut down during a write.

## Contents

- `SKILL.md`: the workflow and the hard rules.
- `references/`: structure, image rules, repack, flash recovery, case studies, and the summary template.
- `scripts/`: the helper scripts.
- `tests/`: the automated checks.
- `assets/reference-chips/`: an original CC0 package outline diagram.

## License

MIT. See `LICENSE`.
The package outline diagram is CC0 1.0. See `assets/reference-chips/README.md`.
