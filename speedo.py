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
import threading

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
FACE_EDGE = "#2a1d1e"
TRACK = "#231818"          # the unlit part of the sweep
ACCENT = "#e8807f"         # RacerTV pastel red — the lit sweep
SHIFT = "#b36bff"          # the shift light: purple, whole ring
RED = "#ff3b3b"            # the redline MARKING on the face
# THE LIMITER. Kept for the tick marks past the redline. The SWEEP no longer
# changes colour at the limiter at all: the whole ring is already purple from
# the shift point, and draw_speedo FLASHES it on the limiter instead, so one
# colour means "shift" and that colour blinking means "you are late".
#
# The unlit TRACK, FACE_EDGE, TICK_DIM and SCANLINE above were slate blues
# left from the cyan theme; the flash's off-phase showed them as a blue ring.
LIMIT = "#b36bff"          # sweep colour past the redline
TICK = "#e8807f"
TICK_DIM = "#3a2a2c"
SCANLINE = "#0b0707"

# THE COST CEILING ON A RENDER. The face is supersampled SS times and then
# resized down, so a screen-sized dial was rendering a 1467x1467 image: 58ms
# each, against a 50ms frame. Accelerating walks through a new rev bucket
# almost every frame, so every cold bucket blew the frame budget and the dial
# visibly trailed the engine ("it looks like the speedo is lagging"). Capping
# the supersample buffer keeps the antialiasing (still 2x or better at every
# size the overlay uses) and bounds the worst render at roughly 29ms.
MAX_SS_PX = 1000

_photo_cache = {}
# Flattened RGB faces built OFF the UI thread by prewarm(). ImageTk.PhotoImage
# must be made on the Tk thread, so the expensive half (PIL) is done ahead of
# time here and photo() only does the cheap half when the bucket is first seen.
_img_cache = {}
_img_lock = threading.Lock()
_warm_key = None


def _rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# How strongly the face takes the shift colour. Enough to be unmistakable,
# little enough that the speed stays white-on-dark.
FACE_SHIFT_TINT = 0.26


def _mix(a, b, f):
    """Colour `a` moved fraction `f` of the way towards colour `b`."""
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    return (int(ra + (rb - ra) * f), int(ga + (gb - ga) * f),
            int(ba + (bb - ba) * f))


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
    # THE WHOLE RING LIGHTS AT THE SHIFT POINT. Asked for directly: "i want
    # the whole circle in the speedo to light up purple when it is time to
    # shift". A sweep that only changed colour up to the needle was a cue you
    # had to read; a full ring is one you see without looking, which is the
    # entire job of a shift light. The limiter FLASHES this same ring (see
    # draw_speedo) rather than turning another colour, so there is one colour
    # for "shift" and its blinking means "you are late".
    if lit >= shift_at:
        arc(0.0, 1.0, _rgb(SHIFT), ring_w)
    else:
        arc(0.0, lit, _rgb(ACCENT), ring_w)

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
    #
    # AND IT TURNS PURPLE AT THE SHIFT POINT. Asked for with a screenshot: "you
    # see the inside circle, the big one, i want that whole thing to turn a tint
    # of purple when it is time to shift". The ring alone is a thin band at the
    # edge of vision; the face is most of the dial, so washing it purple is the
    # cue you catch without looking at it. A TINT, not a fill -- the same 26%
    # mix FACTORtv's gauge uses -- so the white speed digits stay readable. The
    # limiter's flash blanks the whole dial on its off beat, so the face blinks
    # with the ring.
    shifting = lit >= shift_at
    face = _mix(FACE, SHIFT, FACE_SHIFT_TINT) if shifting else _rgb(FACE)
    edge = _rgb(SHIFT) if shifting else _rgb(FACE_EDGE)
    d.ellipse((cx - ir, cy - ir, cx + ir, cy + ir),
              fill=face, outline=edge, width=int(1.5 * s))

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
    big = min(int(size) * SS, MAX_SS_PX)
    im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    _face(ImageDraw.Draw(im), big, rev, shift_at, redline_at)
    return im.resize((int(size), int(size)), Image.LANCZOS)


def _flat(size, b, shift_at, redline_at, ground):
    """One bucket, flattened onto the card colour. Safe off the Tk thread."""
    im = render(size, b / float(BUCKETS), shift_at, redline_at)
    flat = Image.new("RGB", im.size, _rgb(ground))
    flat.paste(im, (0, 0), im)
    return flat


def prewarm(size, shift_at, redline_at, ground):
    """Render every rev bucket for this dial in the background.

    A cold bucket costs tens of milliseconds and the overlay has 50ms for the
    WHOLE frame, so paying for it mid-corner is what made the dial lag the
    engine. The set of faces a car needs is fully known the moment its shift
    point is (73 buckets, nothing else varies), so it is all rendered on a
    daemon thread while the car is still on the grid and the UI thread never
    renders anything again. Changing car or dial size starts a new set and
    abandons the old one, so memory stays at one car's worth.
    """
    global _warm_key
    if not HAVE_PIL:
        return
    key = (int(size), round(shift_at, 3), round(redline_at, 3), ground)
    if key == _warm_key:
        return                       # already warming, or warm
    _warm_key = key

    def _work(k=key):
        sz, sa, ra, gr = k
        with _img_lock:
            for ck in [c for c in _img_cache if c[0:1] + c[2:] != k]:
                del _img_cache[ck]   # last car's faces, no longer wanted
        for b in range(BUCKETS + 1):
            if _warm_key != k:
                return               # superseded mid-sweep; drop this one
            ck = (sz, b, sa, ra, gr)
            with _img_lock:
                if ck in _img_cache:
                    continue
            im = _flat(sz, b, sa, ra, gr)
            with _img_lock:
                if _warm_key == k:
                    _img_cache[ck] = im

    threading.Thread(target=_work, daemon=True).start()


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
        with _img_lock:
            flat = _img_cache.pop(key, None)     # prewarmed, almost always
        if flat is None:
            flat = _flat(*key)
        p = _photo_cache[key] = ImageTk.PhotoImage(flat)
        if len(_photo_cache) > (BUCKETS + 1) * 2:
            # one car's dial plus the one it replaced; older sets are dead
            for k in list(_photo_cache)[:BUCKETS + 1]:
                del _photo_cache[k]
    return p


def clear_cache():
    global _warm_key
    _warm_key = None
    _photo_cache.clear()
    with _img_lock:
        _img_cache.clear()
