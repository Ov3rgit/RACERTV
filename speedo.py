# -*- coding: utf-8 -*-
"""
RacerTV — the speedometer face.

WHY IT IS AN IMAGE AND NOT CANVAS PRIMITIVES
--------------------------------------------
Tk's canvas has no antialiasing. None: every arc, line and oval it draws has
hard pixel edges, and a dial is almost entirely arcs, lines and ovals. Drawn
with tk primitives this reads as pixel art, which is not a palette problem or
a layout problem — it is the renderer.

So the face is drawn with PIL at SS times the final size and downscaled with
LANCZOS, which is real antialiasing, then handed to the canvas as a single
image. The numbers stay with Tk, whose font rendering is already antialiased
by the platform. (This technique is lifted from FACTORtv's gauge.py, which
solved the same problem against the same toolkit.)

It also cuts item churn. Every panel does `delete("all")` and rebuilds at
20 Hz, and a ring gauge is ~50 of those items on its own; here it is one
`create_image`.

WHY IT LOOKS NOTHING LIKE FACTORtv's
------------------------------------
FACTORtv chooses an instrument from the car's era and discipline — a 1962
Lotus gets a cream Smiths dial, a modern LMP gets an LED ladder — because it
has a career model that knows what year it is. RacerTV reads a live RaceRoom
session and has no era to ask.

That is the useful part, because RacerTV is not a cockpit, it is a CHANNEL.
A broadcast uses one graphic for every car on the grid: the graphic belongs
to the programme, not to the vehicle. So there is exactly one face here, it
wears the show's red, and it is built from the same dark slab as the timing
tower and the chyron — furniture that was always there, rather than an
instrument borrowed from the car.

THE CACHE
---------
The image depends only on the REV FRACTION, quantised to 1/BUCKETS. A car
sweeping the range reuses images almost every frame once a bucket has been
seen, so the steady-state cost is a dictionary lookup.

Images are flattened to RGB over the panel's background before they reach Tk.
Handing Tk an RGBA image with varied alpha is pathologically slow (FACTORtv
measured ~65ms against 0.3ms for the same picture as RGB), and because the
ground is the card the dial sits on, the antialiased edges blend toward it
and there is no fringe.
"""
import math

try:
    from PIL import Image, ImageDraw, ImageTk
    HAVE_PIL = True
except Exception:                        # pragma: no cover - PIL is bundled
    HAVE_PIL = False

# Supersample factor. 3 is the knee: 2 still shows stair-stepping on the thin
# tick marks, 4 costs twice the render for no visible gain at this size.
SS = 3

# Rev quantisation, and therefore the cache ceiling: at most BUCKETS+1 images
# per size. 1/72nd of the range is ~130 rpm on a 9,500 rpm engine, finer than
# the eye resolves on a 170px dial.
BUCKETS = 72

# Dial geometry. 240 degrees of sweep with the gap at the bottom, which is
# where the speed readout and the gear live — a full circle would put the
# scale behind the numbers.
START_DEG = 210.0
SWEEP_DEG = -240.0
MARKS = 37                 # ticks around the sweep
MAJOR_EVERY = 6


def _ANG(f):
    """Rev fraction -> PIL arc angle, unwrapped so it always increases.

    Screen angle is START_DEG + SWEEP_DEG * f measured counter-clockwise;
    PIL wants it clockwise, hence the negation, and +360 lifts the whole
    range above zero so the pair passed to d.arc() is always ordered.
    """
    return -(START_DEG + SWEEP_DEG * f) + 360.0

# The palette is RacerTV's, deliberately. See the module docstring: this is a
# broadcast graphic, so it uses the broadcast colours rather than the
# near-black-and-amber of a real instrument.
FACE = "#16100f"       # CARD_BG
FACE_EDGE = "#1b2534"
TRACK = "#141c28"          # the unlit part of the sweep
ACCENT = "#ff3b47"         # RacerTV red — the lit sweep
SHIFT = "#ffb000"          # upshift zone
RED = "#ff3b3b"            # the redline MARKING on the face
# THE SWEEP AT THE LIMITER, and it cannot be RED any more.
#
# The sweep used to be cyan, so red meant one thing: you are on the limiter.
# Re-theming the overlay red made the NORMAL sweep red too, and the two states
# became the same picture {D} a dial that looks identical at 224km/h and on the
# rev limiter is not telling you anything.
#
# Violet is not an arbitrary third colour: a real F1 shift ladder runs
# green -> red -> violet, so the top of the range reading violet is what the
# cue already looks like to anyone who races. The printed redline arc stays
# red, because that is a MARKING on the face rather than a state.
LIMIT = "#b36bff"          # sweep colour past the redline
TICK = "#ff3b47"
TICK_DIM = "#2a3341"
SCANLINE = "#070b10"

_photo_cache = {}


def _rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _dim(col, f):
    r, g, b = _rgb(col) if isinstance(col, str) else col
    return (int(r * f), int(g * f), int(b * f))


def _face(d, size, rev, shift_at, redline_at):
    """The dial, drawn at supersampled scale into `d`."""
    s = SS
    cx = cy = size / 2.0
    r = (size / 2.0) - 4 * s          # room for the outer ring
    ring_w = int(9 * s)
    t_out = r - ring_w - int(3 * s)   # ticks live inside the sweep
    t_in = t_out - int(7 * s)
    ir = t_in - int(6 * s)            # the face proper

    rr = r - ring_w / 2.0
    box = (cx - rr, cy - rr, cx + rr, cy + rr)

    # THE SWEEP. PIL measures arc angles CLOCKWISE from 3 o'clock and always
    # draws start -> end in that direction. Our sweep is counter-clockwise, so
    # every angle negates AND the two ends swap — getting only the negation
    # right draws the complement, a ring around five-sixths of the dial
    # instead of the sixth that was asked for.
    def arc(f0, f1, col, width):
        """Paint the sweep between two rev fractions.

        PIL measures arc angles CLOCKWISE from 3 o'clock, always draws
        start -> end in that direction, and normalises an end that is less
        than its start by adding 360. So handing it the negated screen angles
        in their natural order silently drew the COMPLEMENT — a 120 degree
        stub across the top instead of the 240 degree sweep asked for.
        _ANG maps a rev fraction to an unwrapped PIL angle that only ever
        increases, which makes a0 < a1 true by construction.
        """
        if f1 <= f0:
            return
        d.arc(box, start=_ANG(f0), end=_ANG(f1), fill=col, width=width)

    arc(0.0, 1.0, _rgb(TRACK), ring_w)
    lit = max(0.0, min(1.0, rev))

    # THE WHOLE SWEEP CHANGES COLOUR, not just the part inside the zone.
    #
    # Painting only the segment past the shift point in amber is literally
    # accurate and useless: the upshift point sits around 0.85, so the cue
    # was a three-percent sliver on the rim — something you would have to go
    # looking for at exactly the moment you have no attention to spare. A
    # shift light works because the whole thing changes at once and you see
    # it without moving your eyes. The zones are still legible: they are
    # marked on the TICKS below, which do not move.
    if lit >= redline_at:
        sweep_col = LIMIT
    elif lit >= shift_at:
        sweep_col = SHIFT
    else:
        sweep_col = ACCENT
    arc(0.0, lit, _rgb(sweep_col), ring_w)

    # the redline is marked whether or not you have reached it, so its
    # position is readable before you get there
    arc(redline_at, 1.0, _dim(RED, 0.34), int(3 * s))

    # TICKS
    for i in range(MARKS):
        f = i / float(MARKS - 1)
        a = math.radians(START_DEG + SWEEP_DEG * f)
        ca, sa = math.cos(a), -math.sin(a)
        major = (i % MAJOR_EVERY == 0)
        on = f <= lit
        if f >= redline_at:
            col = _rgb(RED) if on else _dim(RED, 0.30)
        elif f >= shift_at:
            col = _rgb(SHIFT) if on else _dim(SHIFT, 0.30)
        else:
            col = _rgb(TICK) if on else _rgb(TICK_DIM)
        w = int((2 if major else 1) * s)
        inner = t_in if major else t_in + int(3 * s)
        d.line((cx + inner * ca, cy + inner * sa,
                cx + t_out * ca, cy + t_out * sa), fill=col, width=w)

    # FACE. Drawn after the ticks so it covers their inner ends cleanly.
    d.ellipse((cx - ir, cy - ir, cx + ir, cy + ir),
              fill=_rgb(FACE), outline=_rgb(FACE_EDGE), width=int(1.5 * s))

    # CRT SCANLINES across the face — the same retro-camcorder tell the chyron
    # carries, and the detail that stops the dial reading as a generic gauge
    # dropped onto the screen. Clipped to the face by walking only the rows
    # inside it and shortening each to the circle's chord.
    step = int(3 * s)
    y = int(cy - ir)
    while y < cy + ir:
        dy = y - cy
        half = math.sqrt(max(0.0, ir * ir - dy * dy))
        if half > 2:
            # one final pixel per line: width s at supersampled scale.
            # s // 2 rendered a third of a pixel after the downscale, which
            # is to say nothing at all.
            d.line((cx - half + 1, y, cx + half - 1, y),
                   fill=_rgb(SCANLINE), width=s)
        y += step


def render(size, rev, shift_at, redline_at):
    """The dial as an RGB image, antialiased by supersampling."""
    big = int(size) * SS
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    _face(ImageDraw.Draw(im), big, rev, shift_at, redline_at)
    return im.resize((int(size), int(size)), Image.LANCZOS)


def photo(size, rev, shift_at, redline_at, ground):
    """A cached Tk PhotoImage of the dial.

    The PhotoImage is held BY THE CACHE and that is not incidental: a canvas
    image item does not own its image, so dropping the last Python reference
    blanks the dial on the next garbage collection.
    """
    if not HAVE_PIL:
        return None
    b = int(round(max(0.0, min(1.0, rev)) * BUCKETS))
    key = (int(size), b, round(shift_at, 3), round(redline_at, 3), ground)
    p = _photo_cache.get(key)
    if p is None:
        im = render(size, b / float(BUCKETS), shift_at, redline_at)
        flat = Image.new("RGB", im.size, _rgb(ground))
        flat.paste(im, (0, 0), im)
        p = _photo_cache[key] = ImageTk.PhotoImage(flat)
    return p


def clear_cache():
    _photo_cache.clear()
