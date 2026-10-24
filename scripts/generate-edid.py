#!/usr/bin/env python3
"""Generate a minimal, standards-compliant 128-byte EDID binary for a forced
resolution, for use with the Linux kernel's drm.edid_firmware= parameter when
a real display reports no EDID (0 bytes) and the KMS driver therefore refuses
any mode outside its built-in no-EDID safe list ("Configure crtc 0 failed").

Usage:
    scripts/generate-edid.py 1920x1080 --refresh 60 --out /tmp/1920x1080.bin
    scripts/generate-edid.py 1920x1080 --refresh 60 --base64

Validate the result before deploying (needs the edid-decode package, e.g. on
the target host):
    edid-decode -c /tmp/1920x1080.bin

Only resolutions with a known-good CEA-861/DMT detailed timing in TIMINGS
below are supported; add an entry (pixel clock + blanking/sync values from
the CEA-861 or DMT spec) to support another one.
"""
import argparse
import base64
import struct
import sys

# (width, height, refresh_hz): (pixel_clock_hz, h_blank, h_sync_off, h_sync_width,
#                                v_blank, v_sync_off, v_sync_width)
TIMINGS = {
    (1920, 1080, 60): (148500000, 280, 88, 44, 45, 4, 5),  # CEA-861 VIC 16 / DMT
}


def mfg_id(three_letters):
    a, b, c = (ord(ch) - ord("A") + 1 for ch in three_letters.upper())
    return struct.pack(">H", (a << 10) | (b << 5) | c)


def dummy_descriptor():
    return bytes([0x00, 0x00, 0x00, 0x10, 0x00]) + bytes([0x00] * 13)


def detailed_timing(width, height, refresh_hz, size_mm):
    key = (width, height, refresh_hz)
    if key not in TIMINGS:
        raise SystemExit(
            f"Keine bekannte Timing fuer {width}x{height}@{refresh_hz} - "
            "TIMINGS in diesem Skript ergaenzen."
        )
    pixel_clock_hz, h_blank, h_sync_off, h_sync_width, v_blank, v_sync_off, v_sync_width = TIMINGS[key]
    h_size_mm, v_size_mm = size_mm

    b = bytearray(18)
    b[0], b[1] = struct.pack("<H", pixel_clock_hz // 10000)
    b[2] = width & 0xFF
    b[3] = h_blank & 0xFF
    b[4] = ((width >> 8) & 0x0F) << 4 | ((h_blank >> 8) & 0x0F)
    b[5] = height & 0xFF
    b[6] = v_blank & 0xFF
    b[7] = ((height >> 8) & 0x0F) << 4 | ((v_blank >> 8) & 0x0F)
    b[8] = h_sync_off & 0xFF
    b[9] = h_sync_width & 0xFF
    b[10] = ((v_sync_off & 0x0F) << 4) | (v_sync_width & 0x0F)
    b[11] = (
        (((h_sync_off >> 8) & 0x03) << 6)
        | (((h_sync_width >> 8) & 0x03) << 4)
        | (((v_sync_off >> 4) & 0x03) << 2)
        | ((v_sync_width >> 4) & 0x03)
    )
    b[12] = h_size_mm & 0xFF
    b[13] = v_size_mm & 0xFF
    b[14] = (((h_size_mm >> 8) & 0x0F) << 4) | ((v_size_mm >> 8) & 0x0F)
    b[15] = 0  # h border
    b[16] = 0  # v border
    b[17] = 0b00011110  # non-interlaced, digital separate sync, +hsync +vsync
    return bytes(b)


def build_edid(width, height, refresh_hz, size_mm=(480, 270), vendor="PKR"):
    e = bytearray(128)
    e[0:8] = bytes([0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00])
    e[8:10] = mfg_id(vendor)
    e[10:12] = struct.pack("<H", 0x0001)  # product code
    e[12:16] = struct.pack("<I", 0)  # serial
    e[16] = 1  # week
    e[17] = 34  # year 1990+34 = 2024
    e[18] = 1  # EDID version
    e[19] = 4  # EDID revision

    e[20] = 0b10000000 | (0b010 << 4) | 0b0010  # digital, 8bpc, HDMI-a
    e[21] = size_mm[0] // 10  # max horiz size cm
    e[22] = size_mm[1] // 10  # max vert size cm
    e[23] = 120  # gamma 2.2
    e[24] = 0b00000110  # sRGB signaled + preferred timing mode bit set

    e[25:35] = bytes([0xEE, 0x91, 0xA3, 0x54, 0x4C, 0x99, 0x26, 0x0F, 0x50, 0x54])  # ~sRGB chromaticity
    e[35:38] = bytes([0x00, 0x00, 0x00])  # no established timings

    for i in range(8):  # no standard timings
        e[38 + i * 2] = 0x01
        e[39 + i * 2] = 0x01

    e[54:72] = detailed_timing(width, height, refresh_hz, size_mm)
    e[72:90] = dummy_descriptor()
    e[90:108] = dummy_descriptor()
    e[108:126] = dummy_descriptor()

    e[126] = 0  # no extensions
    e[127] = (256 - (sum(e[0:127]) % 256)) % 256
    return bytes(e)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resolution", help="z.B. 1920x1080")
    parser.add_argument("--refresh", type=int, default=60)
    parser.add_argument("--size-mm", default="480x270", help="physische Groesse B x H in mm")
    parser.add_argument("--out", help="Ausgabedatei (.bin)")
    parser.add_argument("--base64", action="store_true", help="Base64 auf stdout statt Binaerdatei")
    args = parser.parse_args()

    width, height = (int(x) for x in args.resolution.lower().split("x"))
    size_mm = tuple(int(x) for x in args.size_mm.lower().split("x"))
    data = build_edid(width, height, args.refresh, size_mm)
    assert len(data) == 128 and sum(data) % 256 == 0

    if args.base64:
        print(base64.b64encode(data).decode())
    elif args.out:
        with open(args.out, "wb") as f:
            f.write(data)
        print(f"{args.out}: {len(data)} Bytes geschrieben", file=sys.stderr)
    else:
        parser.error("--out oder --base64 angeben")


if __name__ == "__main__":
    main()
