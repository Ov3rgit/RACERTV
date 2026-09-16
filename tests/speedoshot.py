"""Render the RacerTV speedo face to a PNG, straight from the real renderer.

A mockup can lie; this cannot. It calls speedo.render() — the same function
the overlay calls every frame — so what comes out is exactly what goes on
screen, minus the Tk text drawn over it.

    python tests/speedoshot.py [out.png]
"""
import sys

sys.path.insert(0, r"D:\R3EOverlay")

from PIL import Image, ImageDraw, ImageFont

import speedo

OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\R3EOverlay\_previews\_speedo_preview.png"

SIZE = 168
SHIFT_AT = 0.82          # where the game says to upshift
REDLINE_AT = 0.93

# A sweep through the range, plus the three states that matter: cold, at the
# shift point, and over the redline.
SHOTS = [(0.00, "IDLE"), (0.35, "PART"), (0.62, "ON IT"),
         (0.85, "SHIFT"), (0.97, "RED")]

GROUND = "#0a0d12"       # the card the dial sits on, and the flatten ground
PAGE = "#05080d"

pad = 26
w = pad + (SIZE + pad) * len(SHOTS)
h = SIZE + pad * 3
sheet = Image.new("RGB", (w, h), speedo._rgb(PAGE))
d = ImageDraw.Draw(sheet)

# The READOUT is drawn here in the same faces the overlay uses (Tk draws it
# over the image at runtime, so it is not part of render()). Without it the
# preview shows an empty dial and you cannot judge the thing you will
# actually be looking at.
def _font(name, size):
    try:
        return ImageFont.truetype(rf"D:\R3EOverlay\{name}", size)
    except Exception:
        return ImageFont.load_default()


F_SPEED = _font("Michroma-Regular.ttf", 30)
F_GEAR = _font("Michroma-Regular.ttf", 21)
F_UNIT = _font("ChakraPetch-Bold.ttf", 12)
F_MARK = _font("ChakraPetch-Bold.ttf", 9)
F_CAP = _font("ChakraPetch-Regular.ttf", 12)

# a plausible speed for each rev fraction, so the sheet reads like a lap
SPEEDS = [0, 118, 196, 262, 289]

for i, (rev, label) in enumerate(SHOTS):
    im = speedo.render(SIZE, rev, SHIFT_AT, REDLINE_AT)
    flat = Image.new("RGB", im.size, speedo._rgb(GROUND))
    flat.paste(im, (0, 0), im)
    fd = ImageDraw.Draw(flat)
    c = SIZE / 2.0
    fd.text((c, c - 6), str(SPEEDS[i]), font=F_SPEED,
            fill=speedo._rgb("#f2f4f7"), anchor="mm")
    fd.text((c, c + 16), "KM/H", font=F_UNIT,
            fill=speedo._rgb("#9aa3ad"), anchor="mm")
    gear = ["N", "2", "4", "6", "7"][i]
    gcol = "#ff3b3b" if rev >= REDLINE_AT else (
        "#ffb000" if rev >= SHIFT_AT else "#39d0e0")
    fd.text((c, c + 44), gear, font=F_GEAR, fill=speedo._rgb(gcol), anchor="mm")
    fd.text((c, c - 40), "RACERTV", font=F_MARK,
            fill=speedo._rgb("#3f4b5c"), anchor="mm")
    x = pad + i * (SIZE + pad)
    sheet.paste(flat, (x, pad))
    d.text((x, pad + SIZE + 10), f"{label}   rev {rev:.2f}",
           font=F_CAP, fill=speedo._rgb("#9aa3ad"))

sheet.save(OUT)
print(f"wrote {OUT}  ({w}x{h})")
print(f"cache entries after {len(SHOTS)} renders: {len(speedo._photo_cache)}"
      "  (render() bypasses the cache; photo() fills it)")
