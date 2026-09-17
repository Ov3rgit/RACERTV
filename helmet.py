# -*- coding: utf-8 -*-
"""
FACTORtv — THE HELMET.

*"I want it to be highly customisable — patterns, numbers, colours, shapes,
everything."*

Nine helmet icons shipped, one per driver, assigned from a stable hash of the
name. That is right for the AI — one driver, one face, for ever, which is what
makes a grid feel like twenty people — and arbitrary for the one man who ought
to be choosing.

THE NINE ICONS TURNED OUT TO BE ONE ICON. Every file is the same silhouette
(25,138 opaque pixels in all of them, to the pixel) flat-filled in a different
colour. So the artwork already contains exactly what a designer needs: a MASK.
Nothing here draws a helmet shape; it paints inside the one that shipped, which
means a custom helmet is guaranteed to sit on the card exactly like a stock
one and cannot drift from the art.

WHAT A HELMET IS
----------------
A dict, and every field is optional::

    {"base": "#ff3b3b",     # the shell
     "accent": "#ffffff",   # whatever the pattern draws in
     "pattern": "stripe",   # see PATTERNS
     "number": 44,          # 0-99, or None for none
     "ink": "#ffffff"}      # the number's colour

An empty dict means "not chosen", which is a real answer and the default: the
driver keeps the hashed icon like everybody else.

WHY IT RENDERS RATHER THAN PICKING A FILE
-----------------------------------------
Because the ask was patterns AND numbers AND colours together, and shipping
the combinations as artwork is thousands of PNGs. Rendered, the whole space is
eleven patterns by a palette by a hundred numbers, and it costs one small
image the first time each combination is seen.

EVERY DRAW IS INSIDE THE MASK. `_mask()` is the alpha channel of the shipped
art, and the last step of every pattern is to multiply back through it — so a
stripe cannot escape the shell and a number cannot sit on the background.
"""
import os

_DIR = os.path.dirname(os.path.abspath(__file__))

# THE PALETTE THE MENU OFFERS. A list, not a colour wheel: this is chosen from
# a keyboard on a list of rows, and sixteen nameable colours is a real choice
# where a hex field would be a chore.
PALETTE = [
    # THE FLUORO COLOURS ARE FIRST-CLASS, not approximations of the flat ones.
    # A helmet somebody actually wants to recreate is usually a fluoro: the
    # nearest the old palette had to Lando's was "yellow" at #ffe24d, which is
    # a custard colour and reads as nothing like it.
    ("neon", "#d4ff00"), ("fluoro", "#ccff33"), ("volt", "#eaff00"),
    ("hi-vis", "#ff5f00"), ("shocking", "#ff2d95"),
    ("red", "#e8202a"), ("crimson", "#a01020"), ("orange", "#ff7a1a"),
    ("amber", "#ffb300"), ("yellow", "#ffe24d"), ("lime", "#9ddc26"),
    ("green", "#22b04a"), ("forest", "#12572c"), ("teal", "#00a3a3"),
    ("cyan", "#4fe0e8"), ("ice", "#cfe9f5"), ("sky", "#3d9bff"),
    ("blue", "#2340d8"), ("navy", "#16205c"), ("purple", "#a24dff"),
    ("violet", "#4a2b7a"),
    ("magenta", "#ff4de0"), ("rose", "#ff3d7a"), ("white", "#f2f2f2"),
    ("black", "#161616"), ("gunmetal", "#3a4048"), ("silver", "#b8bec6"),
    ("gold", "#c8a33a"), ("bronze", "#8a5a2b"),
]
PALETTE_BY_NAME = dict(PALETTE)

# THE PATTERNS. Named for what a viewer would call them rather than for how
# they are drawn, because the menu shows these words.
PATTERNS = (
    # the originals
    "solid", "stripe", "twin", "band", "chevron", "quarters",
    "halo", "split", "spots", "flash", "tip",
    # ...and the vocabulary a real livery needs
    "arrow", "diagonal", "halves", "blocks", "fade", "rays", "bolt",
    "swoosh", "panel", "edge", "wave",
    # ...and the third wave, which is where the odd ones live
    "triple", "hoops", "cross", "target", "star", "flame", "camo",
    "shard", "crown", "scallop", "corner", "eclipse", "carbon",
    "zigzag", "dashes", "peak", "drop", "sunburst",
    # ...AND THE ONES THAT KNOW WHERE THE VISOR IS.
    #
    # These are the shapes real helmets are actually made of, written against
    # the anatomy above rather than centred on the canvas. They are the answer
    # to "none of them look alike": a blade that runs nose-to-tail reads as a
    # helmet graphic in a way a centred chevron never will.
    "visorband", "brow", "blade", "nose", "tail", "jaw", "sweep",
    "wrap", "spear", "delta", "flick", "sidepanel", "tricolour",
    "cap", "lash", "vent",
)

# THE TWO MODIFIERS, which are worth more than any of the shapes.
#
# `flip` mirrors the pattern -- an arrow pointing forward and one pointing
# back are different liveries. `weight` thins or fattens the shapes made of
# bands, because a pinstripe and a broad centre stripe are one pattern at two
# weights and shipping them separately would be shipping the same code twice.
WEIGHTS = {"thin": 0.55, "normal": 1.0, "bold": 1.65}

# ...and which patterns a weight actually changes. A menu row that does
# nothing on most of the catalogue is a menu that lies, which is the same rule
# the trim colour follows.
WEIGHTED = frozenset(("stripe", "twin", "triple", "band", "hoops", "chevron",
                      "diagonal", "cross", "halo", "edge", "wave", "zigzag",
                      "dashes", "pinstripe", "target", "arrow", "peak",
                      "visorband", "brow", "blade", "wrap", "spear", "lash",
                      "flick"))

# WHICH PATTERNS USE THE THIRD COLOUR. Most do not, and a trim slot that did
# nothing on nineteen of twenty-two patterns would be a menu row that lies.
TRIMMED = frozenset(("stripe", "twin", "band", "chevron", "arrow", "panel",
                     "diagonal", "halves", "swoosh",
                     "blade", "sweep", "cap", "delta", "sidepanel", "nose",
                     "tail", "spear", "wrap"))

DEFAULT = {"base": "#e8202a", "accent": "#f2f2f2", "pattern": "stripe",
           "trim": "", "number": None, "ink": "#f2f2f2",
           "flip": False, "weight": "normal",
           # THE SECOND LAYER. "none" is the default and the common case --
           # most liveries are a shell and one shape -- and it is what keeps
           # every helmet designed before this one looking exactly as it did.
           "pattern2": "none", "accent2": "#161616", "flip2": False,
           "weight2": "normal"}

# THE HELMET'S ANATOMY, measured off the mask (see the third-wave patterns).
#
#     shell        x 0.113..0.883   y 0.102..0.836
#     visor hole   x 0.121..0.617   y 0.383..0.676
#     jaw          x 0.156..0.410   at y 0.80
#
# So it FACES LEFT: visor front-left, crown on top, jaw bottom-left, tail
# right. Any pattern written without knowing that is a shape sitting ON a
# helmet rather than a graphic designed FOR one, which is exactly why the
# first forty looked nothing like real liveries.
FRONT = 0.12        # the leading edge of the shell
NOSE = 0.36         # ...and where the nose stops being the nose
VISOR_X = (0.121, 0.617)
VISOR_Y = (0.383, 0.676)
TAIL = 0.66         # behind this is the back of the head
CROWN_Y = 0.34      # above this is the top of the helmet
JAW_Y = 0.70        # below this is the chin bar

# WHERE A NUMBER FITS, MEASURED OFF THE ART RATHER THAN JUDGED BY EYE.
#
# The shell is not a solid blob: the VISOR is a HOLE in the mask, running
# diagonally across the middle, and a number placed anywhere near it comes out
# sliced. Three placements were tried by eye and all three clipped -- and the
# scan that finally settled it showed why the nudging was pointless, because
# the fit did not change with vertical position AT ALL. It was the visor, and
# no amount of moving up or down escapes a diagonal.
#
# So the largest all-opaque rectangle in the mask was computed directly:
#
#     x 0.301..0.746   y 0.172..0.352   (114 x 46 of 256)
#
# ...which is the brow of the helmet, and is also where a real race number
# goes. These are that rectangle with a little margin. If the art is ever
# replaced, re-run the measurement rather than adjusting these by feel.
# RE-MEASURED, ALLOWING THE SHELL'S OWN EDGE. Demanding a perfectly solid
# rectangle gave 114x46; allowing 2% of the box to fall outside -- which costs
# a pixel or two off a corner and nothing a viewer can see -- gives 132x47 at
# x 0.270..0.785, y 0.152..0.352. Thirty per cent more room for the same
# guarantee, and the difference between a sticker and a race number.
PLATE_CX = 0.527
PLATE_CY = 0.252
PLATE_W = 0.50
PLATE_H = 0.19

_MASK_CACHE = [None]
_RENDER_CACHE = {}
_RIM_CACHE = [None]   # the shell's light edge: mask-derived, so computed once


def _pil():
    """Pillow, or None. Every caller degrades to the shipped PNG without it."""
    try:
        from PIL import Image, ImageDraw
        return Image, ImageDraw
    except Exception:
        return None


def _mask():
    """The shell shape, as an 8-bit alpha mask at the art's own size.

    Taken from the shipped icon rather than drawn, so a custom helmet is the
    same silhouette as a stock one to the pixel. Cached: it is one file read
    for the life of the process.
    """
    if _MASK_CACHE[0] is not None:
        return _MASK_CACHE[0]
    mods = _pil()
    if not mods:
        return None
    Image, _ = mods
    for i in range(1, 10):
        p = os.path.join(_DIR, "icon_helmet_%d.png" % i)
        if not os.path.exists(p):
            continue
        try:
            _MASK_CACHE[0] = Image.open(p).convert("RGBA").split()[3]
            return _MASK_CACHE[0]
        except Exception:
            continue
    return None


def _rgb(c, fallback=(232, 32, 42)):
    """'#rrggbb' or a palette name to a tuple. Never raises."""
    if isinstance(c, (tuple, list)) and len(c) >= 3:
        return tuple(int(x) for x in c[:3])
    s = str(c or "").strip()
    s = PALETTE_BY_NAME.get(s.lower(), s)
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except Exception:
        return fallback


def normalise(spec):
    """Any stored value to a full spec dict. Accepts the legacy integer.

    A career saved before this existed holds an int 1..9 -- the old picker's
    index -- and that has to keep meaning what it meant: the stock icon in
    that colour, with nothing drawn on it.
    """
    if not spec:
        return {}
    if isinstance(spec, int):
        try:
            from overlay_common import HELMET_COLORS
            col = HELMET_COLORS[(spec - 1) % len(HELMET_COLORS)]
        except Exception:
            col = "#e8202a"
        return {"base": col, "accent": "#f2f2f2", "pattern": "solid",
                "number": None, "ink": "#f2f2f2"}
    if not isinstance(spec, dict):
        return {}
    out = dict(DEFAULT)
    out.update({k: v for k, v in spec.items() if v is not None or k == "number"})
    # THE TRIM IS OPTIONAL AND USUALLY ABSENT. "" means the pattern draws
    # without it, which is what most liveries are.
    if out.get("trim") and out.get("pattern") not in TRIMMED:
        out["trim"] = ""
    out["flip"] = bool(out.get("flip"))
    out["flip2"] = bool(out.get("flip2"))
    # "none" IS A REAL VALUE HERE, not an absence. The second layer is off by
    # default and has to be able to say so, because "solid" would paint the
    # whole shell in the second colour and hide the first layer entirely.
    if out.get("pattern2") not in PATTERNS and out.get("pattern2") != "none":
        out["pattern2"] = "none"
    if out.get("weight2") not in WEIGHTS:
        out["weight2"] = "normal"
    if out["pattern2"] not in WEIGHTED:
        out["weight2"] = "normal"
    if out.get("weight") not in WEIGHTS:
        out["weight"] = "normal"
    if out["pattern"] not in WEIGHTED:
        out["weight"] = "normal"
    if out.get("pattern") not in PATTERNS:
        out["pattern"] = "solid"
    n = out.get("number")
    try:
        n = int(n) if n not in (None, "") else None
    except Exception:
        n = None
    out["number"] = n if (n is not None and 0 <= n <= 99) else None
    return out


def describe(spec):
    """The design in words, for a caption. Short enough for a menu row."""
    spec = normalise(spec)
    if not spec:
        return "default"
    name = {h.lower(): n for n, h in PALETTE}

    def word(c):
        return name.get(str(c or "").lower(), str(c or ""))

    bits = [word(spec.get("base"))]
    if (spec.get("pattern") or "solid") != "solid":
        bits.append("%s %s" % (word(spec.get("accent")), spec["pattern"]))
    if (spec.get("pattern2") or "none") != "none":
        bits.append("%s %s" % (word(spec.get("accent2")), spec["pattern2"]))
    if spec.get("number") is not None:
        bits.append("no. %d" % spec["number"])
    return ", ".join(bits)


# THE SHAPES A GENERATED HELMET MAY USE.
#
# Deliberately NOT all fifty-six. The catalogue contains centred geometry --
# `quarters`, `diagonal`, `halves` -- that reads as a sticker rather than as a
# livery, and a generated grid drawing from all of it would put the worst of
# the set on sixteen of twenty cars. These are the shapes that suit a helmet,
# which is the same list the driver colourways are held to.
# MEASURED, NOT CHOSEN BY EYE. Each shape was rendered at every weight and
# both mirrors and its coverage of the shell measured:
#
#     flick   0%..3%    -- invisible; two 1988 drivers got a plain shell
#     wrap    0%..25%   -- vanishes at thin weight, mirrored
#
# Both are out. They are still available in the designer, where a person can
# see what they are getting; a GENERATOR may not hand somebody a pattern that
# renders as nothing, because the result reads as the feature being broken.
GENERATED_SHAPES = ("visorband", "brow", "blade", "nose", "tail", "jaw",
                    "sweep", "spear", "delta", "sidepanel",
                    "tricolour", "cap", "panel", "crown")
# `lash` is a separator line and is meant to be subtle, which is fine as a
# DETAIL over a layer that is already carrying the design.
GENERATED_DETAIL = ("visorband", "vent", "lash", "brow", "none", "none")


def generated(name):
    """A helmet for a driver nobody wrote one for. Deterministic from `name`.

    THE GRID WAS TWO PRODUCTS. Twenty hand-written colourways rendered with
    patterns and layers and a race number, and everybody else -- the whole
    1988 field, most of 2025, and every AI on every third-party mod -- wearing
    one of nine flat single-colour PNGs. Side by side on the same timing
    tower that does not read as a style, it reads as half the feature being
    broken.

    So every driver gets a real helmet. This is not a random one: it is a hash
    of the name, so ONE DRIVER HAS ONE FACE FOR EVER, which is the rule that
    made the original nine icons worth having. It is simply a much better face
    than a flat disc.

    HAND-WRITTEN ALWAYS WINS. `overlay_rival.spec_for` asks for a real
    colourway first and only falls back here, so adding Senna to the data file
    replaces his generated helmet with his actual one.
    """
    key = (name or "").strip()
    if not key:
        return {}
    h = 0
    for ch in key:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF

    def pick(seq, salt):
        return seq[(h // (7 ** salt)) % len(seq)]

    cols = [c for _n, c in PALETTE]
    base = pick(cols, 1)
    # CONTRAST IS NOT LEFT TO THE HASH. A generated accent landing on a
    # near-identical colour produces an invisible pattern, which reads as the
    # renderer being broken rather than as a plain helmet.
    ok = [c for c in cols if contrast(base, c) > 2.6] or cols
    accent = ok[(h // 11) % len(ok)]
    detail = pick(GENERATED_DETAIL, 3)
    out = {
        "base": base, "accent": accent,
        "pattern": pick(GENERATED_SHAPES, 2),
        "flip": bool((h >> 5) & 1),
        "weight": ("thin", "normal", "bold")[(h >> 6) % 3],
        "pattern2": detail,
        "accent2": ("#161616" if contrast(base, "#161616") > 2.0
                    else "#f2f2f2"),
        # NO NUMBER. A race number is a fact about a driver and this function
        # knows nothing about him -- inventing one would put a wrong number on
        # a real person's card, which is exactly the kind of confident
        # fabrication the rest of this product refuses.
        "number": None,
        "ink": "#f2f2f2",
    }
    return normalise(out)


def readable(colour, bg, want=4.0):
    """`colour` lifted or darkened until it can be READ on `bg`.

    THE CARD USES THE SHELL COLOUR TWICE AND THE TWO USES WANT DIFFERENT
    THINGS. The 4px spine down the edge is IDENTITY -- it should be the shell
    colour exactly, however dark. The driver's NAME is text, and Verstappen's
    navy on the panel measures 1.16:1, which is not a name, it is a rumour.

    So the spine keeps the true colour and the text gets this: the same hue,
    walked towards white (or black, on a light ground) only as far as it has
    to go. The card still reads as his colour -- it is his colour -- and the
    name is legible, which is the whole point of writing it down.
    """
    r, g, b = _rgb(colour)
    if contrast(colour, bg) >= want:
        return "#%02x%02x%02x" % (r, g, b)
    # Towards whichever end of the range the background is NOT.
    up = contrast("#ffffff", bg) >= contrast("#000000", bg)
    for i in range(1, 21):
        t = i / 20.0
        if up:
            c = (int(r + (255 - r) * t), int(g + (255 - g) * t),
                 int(b + (255 - b) * t))
        else:
            c = (int(r * (1 - t)), int(g * (1 - t)), int(b * (1 - t)))
        if contrast(c, bg) >= want:
            return "#%02x%02x%02x" % c
    return "#ffffff" if up else "#000000"


def contrast(a, b):
    """WCAG contrast ratio between two colours, 1.0 (same) to 21.0 (extremes).

    Used by the random designer, which without it lands on a near-identical
    accent often enough that the pattern is invisible -- and an invisible
    pattern reads as the button being broken rather than as a choice.
    """
    def lum(c):
        out = []
        for v in _rgb(c):
            v = v / 255.0
            out.append(v / 12.92 if v <= 0.03928
                       else ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def card_colour(spec, fallback="#b8bec6"):
    """The colour the driver's NAME appears in, which is his shell colour.

    The card's colour and its picture come from one place on purpose: they
    used to be two independent hashes of the same name, and a driver ended up
    with a red card and a green helmet. A custom helmet has to honour the same
    rule, so the card reads its base colour from the same spec the picture is
    drawn from.
    """
    spec = normalise(spec)
    if not spec:
        return fallback
    r, g, b = _rgb(spec.get("base"))
    return "#%02x%02x%02x" % (r, g, b)


# ---------------------------------------------------------------- the patterns
#
# Each takes a draw context over a SQUARE canvas of side `n` and paints in the
# accent colour. None of them worries about the shell edge: the caller
# multiplies the result back through the mask afterwards, so anything that
# runs over the side of the helmet is simply cut off.
def _p_solid(d, n, a):
    return


def _p_stripe(d, n, a, k=1.0):
    w = n * 0.08 * k
    d.rectangle([n * 0.5 - w, 0, n * 0.5 + w, n], fill=a)


def _p_twin(d, n, a, k=1.0):
    w = n * 0.05 * k
    for cx in (0.35, 0.65):
        d.rectangle([n * cx - w, 0, n * cx + w, n], fill=a)


def _p_band(d, n, a, k=1.0):
    h = n * 0.08 * k
    d.rectangle([0, n * 0.52 - h, n, n * 0.52 + h], fill=a)


def _p_chevron(d, n, a, k=1.0):
    # A BAND, not a filled wedge. The first version was a solid polygon and
    # the mask trimmed it into a blob -- measured against the shell, the only
    # region wide enough to read a shape in is the CROWN (y 0.28-0.42), so the
    # chevron lives there and stays thin enough to be a chevron.
    # TWO LINES, NOT A POLYGON. A six-point polygon for a V is self-closing
    # across the middle, so it filled the whole crown and read as a blob
    # rather than as a chevron. A polyline with a width is what the shape
    # actually is.
    d.line([(n * 0.02, n * 0.56), (n * 0.5, n * 0.20), (n * 0.98, n * 0.56)],
           fill=a, width=max(2, int(n * 0.11 * k)), joint="curve")


def _p_quarters(d, n, a):
    d.rectangle([0, 0, n * 0.5, n * 0.5], fill=a)
    d.rectangle([n * 0.5, n * 0.5, n, n], fill=a)


def _p_halo(d, n, a, k=1.0):
    d.ellipse([n * 0.10, n * 0.10, n * 0.90, n * 0.90], outline=a,
              width=max(2, int(n * 0.09 * k)))


def _p_split(d, n, a):
    d.polygon([(0, n), (n, 0), (n, n)], fill=a)


def _p_spots(d, n, a):
    r = n * 0.09
    for cx, cy in ((0.28, 0.30), (0.62, 0.24), (0.44, 0.52),
                   (0.74, 0.58), (0.24, 0.66)):
        d.ellipse([n * cx - r, n * cy - r, n * cx + r, n * cy + r], fill=a)


def _p_flash(d, n, a):
    d.polygon([(n * 0.05, n * 0.58), (n * 0.55, n * 0.20),
               (n * 0.48, n * 0.46), (n * 0.95, n * 0.34),
               (n * 0.40, n * 0.86), (n * 0.50, n * 0.56)], fill=a)


def _p_tip(d, n, a):
    d.rectangle([0, 0, n, n * 0.30], fill=a)


# ---------------------------------------------------------- the second set
#
# ELEVEN MORE, because eleven was enough to prove the idea and not enough to
# build a livery anybody has actually seen. What was missing was diagonals,
# blocks, a gradient and anything asymmetric -- the shapes real helmets are
# made of.
def _p_arrow(d, n, a, k=1.0):
    t = 0.12 * k
    d.polygon([(n * 0.10, n * (0.42 - t)), (n * 0.55, n * (0.42 - t)),
               (n * 0.55, n * 0.14), (n * 0.95, n * 0.42),
               (n * 0.55, n * 0.70), (n * 0.55, n * (0.42 + t)),
               (n * 0.10, n * (0.42 + t))], fill=a)


def _p_diagonal(d, n, a, k=1.0):
    w = 0.24 * k
    d.polygon([(n * 0.10, n * 1.05), (n * 0.46, n * -0.05),
               (n * (0.46 + w), n * -0.05), (n * (0.10 + w), n * 1.05)],
              fill=a)


def _p_halves(d, n, a):
    d.rectangle([n * 0.5, 0, n, n], fill=a)


def _p_blocks(d, n, a):
    k = n / 8.0
    for r in range(8):
        for cc in range(8):
            if (r + cc) % 2 == 0:
                d.rectangle([cc * k, r * k, (cc + 1) * k, (r + 1) * k], fill=a)


def _p_rays(d, n, a):
    import math
    cx, cy = n * 0.52, n * 0.30
    for i in range(9):
        ang = math.radians(-96 + i * 24)
        d.polygon([(cx, cy),
                   (cx + math.cos(ang - 0.09) * n * 1.4,
                    cy + math.sin(ang - 0.09) * n * 1.4),
                   (cx + math.cos(ang + 0.09) * n * 1.4,
                    cy + math.sin(ang + 0.09) * n * 1.4)], fill=a)


def _p_bolt(d, n, a):
    d.polygon([(n * 0.60, n * 0.06), (n * 0.30, n * 0.50),
               (n * 0.48, n * 0.50), (n * 0.28, n * 0.96),
               (n * 0.72, n * 0.44), (n * 0.52, n * 0.44)], fill=a)


def _p_swoosh(d, n, a):
    d.chord([n * -0.30, n * 0.10, n * 0.95, n * 1.20], 250, 350, fill=a)


def _p_panel(d, n, a):
    d.polygon([(n * 0.62, n * 0.02), (n * 1.02, n * 0.02),
               (n * 1.02, n * 1.02), (n * 0.44, n * 1.02)], fill=a)


def _p_edge(d, n, a, k=1.0):
    d.ellipse([n * 0.02, n * 0.02, n * 0.98, n * 0.98], outline=a,
              width=max(3, int(n * 0.07 * k)))


def _p_wave(d, n, a, k=1.0):
    pts = []
    import math
    for i in range(0, 101):
        x = n * i / 100.0
        pts.append((x, n * (0.46 + 0.10 * math.sin(i / 100.0 * 6.28 * 1.5))))
    d.line(pts, fill=a, width=max(3, int(n * 0.12 * k)), joint="curve")


def _p_triple(d, n, a, k=1.0):
    w = n * 0.055 * k
    for cx in (0.34, 0.5, 0.66):
        d.rectangle([n * cx - w, 0, n * cx + w, n], fill=a)


def _p_hoops(d, n, a, k=1.0):
    h = n * 0.055 * k
    for cy in (0.24, 0.44, 0.64, 0.84):
        d.rectangle([0, n * cy - h, n, n * cy + h], fill=a)


def _p_cross(d, n, a, k=1.0):
    w = n * 0.075 * k
    d.rectangle([n * 0.5 - w, 0, n * 0.5 + w, n], fill=a)
    d.rectangle([0, n * 0.5 - w, n, n * 0.5 + w], fill=a)


def _p_target(d, n, a, k=1.0):
    wd = max(2, int(n * 0.055 * k))
    for r in (0.16, 0.30, 0.44):
        d.ellipse([n * (0.52 - r), n * (0.42 - r),
                   n * (0.52 + r), n * (0.42 + r)], outline=a, width=wd)


def _p_star(d, n, a):
    import math
    cx, cy, R, r = n * 0.52, n * 0.40, n * 0.30, n * 0.13
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rad = R if i % 2 == 0 else r
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    d.polygon(pts, fill=a)


def _p_flame(d, n, a):
    pts = [(0, n)]
    for i, t in enumerate((0.86, 0.60, 0.80, 0.52, 0.74, 0.46, 0.70)):
        pts.append((n * i / 6.0, n * t))
    pts.append((n, n))
    d.polygon(pts, fill=a)


def _p_camo(d, n, a):
    for cx, cy, r in ((0.22, 0.28, 0.16), (0.50, 0.18, 0.13),
                      (0.72, 0.36, 0.18), (0.34, 0.54, 0.15),
                      (0.64, 0.66, 0.14), (0.16, 0.72, 0.12),
                      (0.86, 0.60, 0.11)):
        d.ellipse([n * (cx - r), n * (cy - r * 0.78),
                   n * (cx + r), n * (cy + r * 0.78)], fill=a)


def _p_shard(d, n, a):
    for x0, x1 in ((0.06, 0.20), (0.30, 0.40), (0.54, 0.62)):
        d.polygon([(n * x0, n * 1.05), (n * (x0 + 0.22), n * -0.05),
                   (n * (x1 + 0.22), n * -0.05), (n * x1, n * 1.05)], fill=a)


def _p_crown(d, n, a):
    # THE POINTS HAVE TO BE INSIDE THE SHELL. The first version put them
    # between y -0.05 and 0.34, and the shell does not START until 0.13 and is
    # narrow there -- so every point was outside the mask and the pattern
    # rendered as a plain dark cap. Sunk into the crown where the shell is
    # actually wide.
    d.polygon([(n * 0.02, n * 0.46), (n * 0.20, n * 0.22),
               (n * 0.38, n * 0.42), (n * 0.56, n * 0.18),
               (n * 0.74, n * 0.40), (n * 0.92, n * 0.22),
               (n * 1.02, n * 0.46), (n * 1.02, n * 0.02),
               (n * 0.02, n * 0.02)], fill=a)


def _p_scallop(d, n, a):
    r = n * 0.13
    for i in range(5):
        cx = n * (0.08 + i * 0.21)
        d.ellipse([cx - r, n * 0.30 - r, cx + r, n * 0.30 + r], fill=a)


def _p_corner(d, n, a):
    d.polygon([(n * 1.02, n * -0.05), (n * 1.02, n * 0.62),
               (n * 0.34, n * -0.05)], fill=a)


def _p_eclipse(d, n, a):
    d.pieslice([n * 0.14, n * 0.02, n * 0.94, n * 0.82], 180, 360, fill=a)


def _p_carbon(d, n, a):
    # A WEAVE, NOT A DOT SCREEN. The first version drew a gap between every
    # cell, which at icon size reads as noise rather than as carbon. Woven in
    # pairs, alternating direction, with no gaps -- which is what the material
    # actually looks like.
    k = n / 12.0
    for r in range(12):
        for cc in range(12):
            if ((r // 2) + (cc // 2)) % 2 == 0:
                d.rectangle([cc * k, r * k, (cc + 1) * k, (r + 1) * k], fill=a)


def _p_zigzag(d, n, a, k=1.0):
    pts = []
    for i in range(9):
        pts.append((n * i / 8.0, n * (0.36 if i % 2 else 0.56)))
    d.line(pts, fill=a, width=max(2, int(n * 0.09 * k)), joint="curve")


def _p_dashes(d, n, a, k=1.0):
    h = n * 0.07 * k
    for i in range(5):
        x0 = n * (0.04 + i * 0.20)
        d.rectangle([x0, n * 0.46 - h, x0 + n * 0.13, n * 0.46 + h], fill=a)


def _p_peak(d, n, a, k=1.0):
    w = max(2, int(n * 0.13 * k))
    d.line([(n * 0.04, n * 0.40), (n * 0.52, n * 0.10),
            (n * 1.00, n * 0.40)], fill=a, width=w, joint="curve")


def _p_drop(d, n, a):
    d.polygon([(n * 0.52, n * 0.06), (n * 0.80, n * 0.46),
               (n * 0.52, n * 0.78), (n * 0.24, n * 0.46)], fill=a)


def _p_sunburst(d, n, a):
    import math
    cx, cy = n * 0.50, n * 0.92
    for i in range(11):
        ang = math.radians(-172 + i * 16)
        d.polygon([(cx, cy),
                   (cx + math.cos(ang - 0.055) * n * 1.5,
                    cy + math.sin(ang - 0.055) * n * 1.5),
                   (cx + math.cos(ang + 0.055) * n * 1.5,
                    cy + math.sin(ang + 0.055) * n * 1.5)], fill=a)


# ------------------------------------------------- the shapes a helmet has
#
# Written against FRONT/NOSE/VISOR/TAIL/CROWN/JAW above. Each is asymmetric,
# because a helmet is: the front is not the back and a graphic that ignores
# that reads as a sticker rather than as a livery.
def _p_visorband(d, n, a, k=1.0):
    """The dark surround almost every real helmet has around the opening."""
    t = n * 0.075 * k
    x0, x1 = n * (VISOR_X[0] - 0.03), n * (VISOR_X[1] + 0.05)
    y0, y1 = n * (VISOR_Y[0] - 0.04), n * (VISOR_Y[1] + 0.03)
    d.rounded_rectangle([x0 - t, y0 - t, x1 + t, y1 + t],
                        radius=n * 0.16, fill=a)
    d.rounded_rectangle([x0, y0, x1, y1], radius=n * 0.13, fill=(0, 0, 0, 0))


def _p_brow(d, n, a, k=1.0):
    """A band across the brow, just above the opening."""
    t = n * 0.07 * k
    cy = n * (VISOR_Y[0] - 0.06)
    d.polygon([(n * FRONT, cy + t), (n * 0.92, cy - t * 1.6),
               (n * 0.92, cy + t * 0.4), (n * FRONT, cy + t * 2.4)], fill=a)


def _p_blade(d, n, a, k=1.0):
    """A tapered sweep from the nose to the tail -- THE helmet shape."""
    t = n * 0.10 * k
    d.polygon([(n * 0.10, n * 0.50), (n * 0.42, n * 0.30),
               (n * 0.90, n * 0.26), (n * 0.90, n * 0.26 + t * 1.5),
               (n * 0.44, n * 0.30 + t * 1.4), (n * 0.10, n * 0.50 + t)],
              fill=a)


def _p_nose(d, n, a):
    """The front section, ahead of the visor's leading edge."""
    d.polygon([(n * 0.02, n * 1.05), (n * NOSE, n * 1.05),
               (n * (NOSE - 0.10), n * -0.05), (n * 0.02, n * -0.05)], fill=a)


def _p_tail(d, n, a):
    """The back of the head."""
    d.polygon([(n * TAIL, n * -0.05), (n * 1.05, n * -0.05),
               (n * 1.05, n * 1.05), (n * (TAIL + 0.12), n * 1.05)], fill=a)


def _p_jaw(d, n, a):
    """The chin bar, under the opening."""
    d.polygon([(n * -0.05, n * JAW_Y), (n * 1.05, n * (JAW_Y - 0.10)),
               (n * 1.05, n * 1.05), (n * -0.05, n * 1.05)], fill=a)


def _p_sweep(d, n, a):
    """A wide curved field, low at the nose and high at the tail."""
    d.polygon([(n * -0.05, n * 0.86), (n * 0.30, n * 0.60),
               (n * 0.70, n * 0.34), (n * 1.05, n * 0.16),
               (n * 1.05, n * 1.05), (n * -0.05, n * 1.05)], fill=a)


def _p_wrap(d, n, a, k=1.0):
    """A band curving around the shell, following its shoulder."""
    d.arc([n * 0.02, n * 0.04, n * 1.02, n * 1.10], 200, 340, fill=a,
          width=max(3, int(n * 0.11 * k)))


def _p_spear(d, n, a, k=1.0):
    """A sharp point driven back from the nose."""
    t = n * 0.13 * k
    d.polygon([(n * 0.06, n * 0.44), (n * 0.98, n * 0.20),
               (n * 0.98, n * 0.20 + t), (n * 0.06, n * 0.44 + t * 1.5)],
              fill=a)


def _p_delta(d, n, a):
    """A triangle over the crown, pointing back."""
    d.polygon([(n * 0.20, n * 0.30), (n * 0.98, n * 0.06),
               (n * 0.98, n * 0.46)], fill=a)


def _p_flick(d, n, a, k=1.0):
    """A hook at the tail, the way a lot of liveries finish a stripe."""
    d.arc([n * 0.46, n * 0.08, n * 1.08, n * 0.70], 250, 30, fill=a,
          width=max(3, int(n * 0.12 * k)))


def _p_sidepanel(d, n, a):
    """The big flat area above and behind the opening."""
    d.polygon([(n * 0.30, n * 0.34), (n * 0.92, n * 0.22),
               (n * 0.92, n * 0.66), (n * 0.34, n * 0.62)], fill=a)


def _p_tricolour(d, n, a):
    """Three fields across the shell -- the national helmet, in one shape.

    Only the OUTER two are painted; the middle is left as the shell, so one
    pattern gives a three-colour helmet without needing a third slot.
    """
    d.polygon([(n * -0.05, n * -0.05), (n * 0.30, n * -0.05),
               (n * 0.22, n * 1.05), (n * -0.05, n * 1.05)], fill=a)
    d.polygon([(n * 0.62, n * -0.05), (n * 1.05, n * -0.05),
               (n * 1.05, n * 1.05), (n * 0.54, n * 1.05)], fill=a)


def _p_cap(d, n, a):
    """The crown, cut on a curve rather than a straight line."""
    d.chord([n * -0.10, n * -0.55, n * 1.10, n * (CROWN_Y + 0.30)],
            0, 180, fill=a)


def _p_lash(d, n, a, k=1.0):
    """A thin line along the top of the opening, as a separator."""
    t = max(2, int(n * 0.035 * k))
    d.line([(n * FRONT, n * (VISOR_Y[0] - 0.01)),
            (n * 0.50, n * (VISOR_Y[0] - 0.07)),
            (n * 0.95, n * (VISOR_Y[0] - 0.16))], fill=a, width=t,
           joint="curve")


def _p_vent(d, n, a):
    """Vent slots on the crown, which nearly every real helmet shows."""
    for i in range(3):
        x0 = n * (0.44 + i * 0.15)
        d.rounded_rectangle([x0, n * 0.16, x0 + n * 0.09, n * 0.27],
                            radius=n * 0.03, fill=a)


def _p_fade(d, n, a):
    # HANDLED IN `render`, because a gradient is a per-pixel composite rather
    # than a shape. Present here so the table is complete and a lookup can
    # never miss.
    return


_PAINT = {"solid": _p_solid, "stripe": _p_stripe, "twin": _p_twin,
          "band": _p_band, "chevron": _p_chevron, "quarters": _p_quarters,
          "halo": _p_halo, "split": _p_split, "spots": _p_spots,
          "flash": _p_flash, "tip": _p_tip,
          "arrow": _p_arrow, "diagonal": _p_diagonal, "halves": _p_halves,
          "blocks": _p_blocks, "rays": _p_rays, "bolt": _p_bolt,
          "swoosh": _p_swoosh, "panel": _p_panel, "edge": _p_edge,
          "wave": _p_wave, "fade": _p_fade,
          "triple": _p_triple, "hoops": _p_hoops, "cross": _p_cross,
          "target": _p_target, "star": _p_star, "flame": _p_flame,
          "camo": _p_camo, "shard": _p_shard, "crown": _p_crown,
          "scallop": _p_scallop, "corner": _p_corner, "eclipse": _p_eclipse,
          "carbon": _p_carbon, "zigzag": _p_zigzag, "dashes": _p_dashes,
          "peak": _p_peak, "drop": _p_drop, "sunburst": _p_sunburst,
          "visorband": _p_visorband, "brow": _p_brow, "blade": _p_blade,
          "nose": _p_nose, "tail": _p_tail, "jaw": _p_jaw,
          "sweep": _p_sweep, "wrap": _p_wrap, "spear": _p_spear,
          "delta": _p_delta, "flick": _p_flick, "sidepanel": _p_sidepanel,
          "tricolour": _p_tricolour, "cap": _p_cap, "lash": _p_lash,
          "vent": _p_vent}

# THE TRIM IS THE SAME SHAPE, DRAWN FATTER, UNDERNEATH.
#
# Which is how a real trimmed stripe is made: a wide band in the trim colour
# with a narrower one in the accent on top of it. Written as a scale factor
# rather than as eleven more pattern functions, so a trim can never disagree
# with the shape it is edging.
TRIM_SCALE = 1.30


def _paint(d, n, pat, colour, weight="normal"):
    """Run one pattern, at a weight if it takes one.

    THE WEIGHT IS PASSED, NOT APPLIED AFTERWARDS. Scaling a finished layer
    would move the shape as well as thicken it -- a bolder centre stripe would
    also drift off centre -- so the shapes that have a thickness take it as an
    argument and the rest ignore it. `WEIGHTED` is the list of which, and
    `normalise` refuses a weight on anything else so the menu cannot offer a
    control that does nothing.
    """
    fn = _PAINT.get(pat, _p_solid)
    k = WEIGHTS.get(weight, 1.0)
    if k != 1.0 and pat in WEIGHTED:
        try:
            return fn(d, n, colour, k)
        except TypeError:
            pass
    return fn(d, n, colour)


def render(spec, size=28):
    """The helmet as an RGBA image, or None without Pillow.

    Cached by (spec, size): a card is drawn every frame it is on screen and
    re-rendering a helmet sixty times a second for a picture that cannot have
    changed would be absurd.
    """
    spec = normalise(spec)
    if not spec:
        return None
    mods = _pil()
    mask = _mask()
    if not mods or mask is None:
        return None
    Image, ImageDraw = mods
    key = (tuple(sorted((k, str(v)) for k, v in spec.items())), int(size))
    hit = _RENDER_CACHE.get(key)
    if hit is not None:
        return hit

    n = mask.size[0]
    base, accent = _rgb(spec.get("base")), _rgb(spec.get("accent"), (242,) * 3)
    pat = spec.get("pattern") or "solid"
    im = Image.new("RGBA", (n, n), base + (255,))

    if pat == "fade":
        # A GRADIENT IS NOT A SHAPE. Composited per pixel from the base to the
        # accent down the shell, which is the one livery effect that cannot be
        # expressed as a polygon.
        grad = Image.new("RGBA", (n, n), accent + (255,))
        ramp = Image.linear_gradient("L").resize((n, n))
        im = Image.composite(grad, im, ramp)
        d = ImageDraw.Draw(im)
    else:
        d = ImageDraw.Draw(im)
        # THE TRIM GOES DOWN FIRST, FATTER, so the accent sits on top of it and
        # the result is an edged shape rather than two shapes fighting.
        trim = spec.get("trim")
        if trim and pat in TRIMMED:
            fat = Image.new("RGBA", (n, n), (0, 0, 0, 0))
            _paint(ImageDraw.Draw(fat), n, pat, _rgb(trim) + (255,),
                   spec.get("weight"))
            k = int(n * TRIM_SCALE)
            fat = fat.resize((k, k), Image.LANCZOS)
            off = (n - k) // 2
            im.alpha_composite(fat, (off, off))
            d = ImageDraw.Draw(im)
        _paint(d, n, pat, accent + (255,), spec.get("weight"))

    if spec.get("flip"):
        im = im.transpose(Image.FLIP_LEFT_RIGHT)

    # ---- THE SECOND LAYER ------------------------------------------------
    #
    # Drawn on its own transparent sheet and composited over the first, which
    # is the only way it can have its OWN mirror: flipping the finished shell
    # would flip layer one as well, and two shapes that must mirror together
    # are one shape.
    #
    # It uses the same forty patterns, so this costs no new drawing code and
    # multiplies the catalogue by forty rather than adding to it.
    pat2 = spec.get("pattern2") or "none"
    if pat2 != "none":
        lay = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        _paint(ImageDraw.Draw(lay), n, pat2,
               _rgb(spec.get("accent2"), (22,) * 3) + (255,),
               spec.get("weight2"))
        if spec.get("flip2"):
            lay = lay.transpose(Image.FLIP_LEFT_RIGHT)
        im.alpha_composite(lay)

    # THE MIRROR, APPLIED TO THE WHOLE PAINTED SHELL AND NOT TO EACH SHAPE.
    #
    # One transpose here instead of a mirrored variant of forty pattern
    # functions -- and because it happens BEFORE the mask goes on, the helmet
    # itself never flips. The shell keeps facing the way the art faces and
    # only the livery on it turns round, which is the point: an arrow pointing
    # forward and one pointing back are different liveries, and a helmet
    # facing backwards is a bug.
    # ...AND IT IS APPLIED BEFORE THE SECOND LAYER GOES ON, above, so the two
    # layers mirror independently. Flipping here after compositing would turn
    # them together, which makes the second layer's own switch meaningless.
    pass

    # THE NUMBER GOES ON AFTER THE MIRROR, AND THAT ORDER IS THE WHOLE POINT.
    #
    # Drawn before it, the transpose reversed the digits along with the
    # livery: the variations sheet came out with a backwards "4" on every
    # mirrored helmet. A pattern is a shape and may be flipped; a number is
    # TEXT and may not. Still before the mask, so the shell trims it like
    # everything else.
    num = spec.get("number")
    if num is not None:
        _draw_number(Image, ImageDraw, im, n, str(int(num)),
                     _rgb(spec.get("ink"), (242,) * 3))

    # EVERY DRAW GOES BACK THROUGH THE SHELL. Nothing above worried about the
    # silhouette; this is what makes that safe.
    im.putalpha(mask)

    # ...AND THE SHELL GETS A RIM, because the panel behind it is dark.
    #
    # The shipped nine had no dark colours in them, so this never came up. Add
    # black, navy, gunmetal and forest to the palette and a black stripe on a
    # dark radio card reads as a HOLE IN THE HELMET rather than as a stripe --
    # the sheet of twenty-two patterns showed exactly that, with `quarters`
    # and `halves` looking like the icon had chunks bitten out of it.
    #
    # A faint light rim fixes it for every dark colour at once and is
    # invisible on a light one, which is why it is unconditional: a rule that
    # decided WHEN to draw a rim would have to judge the whole composited
    # image, and would be wrong on a helmet that is half black and half white.
    im = _rim(Image, ImageDraw, im, mask, n)
    out = im.resize((int(size), int(size)), Image.LANCZOS)
    _RENDER_CACHE[key] = out
    return out


def _rim(Image, ImageDraw, im, mask, n):
    """A faint light edge, so a dark helmet still has a silhouette.

    Drawn from the MASK rather than from the artwork, so it follows the shell
    exactly and costs nothing on a light helmet, where it disappears into the
    colour it is drawn over.
    """
    try:
        # CACHED, BECAUSE IT IS THE SAME RING EVERY TIME. Nothing in this
        # layer depends on the helmet — it is derived purely from the shell
        # mask, so twenty drivers were computing one identical image twenty
        # times.
        #
        # It matters because the erode is a RANK FILTER over 256x256, and it
        # measured at 76% of the entire cost of rendering a helmet: a grid of
        # twenty cost ~370ms of stall on first sighting, ~280ms of it here.
        # Cached, a cold grid is a third of that and a warm one is free.
        glow = _RIM_CACHE[0]
        if glow is None:
            from PIL import ImageFilter
            # The rim is the mask minus an eroded copy of itself: the outline,
            # in other words, without needing to know anything about the shape.
            inner = mask.filter(ImageFilter.MinFilter(5))
            edge = Image.new("L", (n, n))
            edge.paste(mask)
            edge = Image.composite(Image.new("L", (n, n), 0), edge, inner)
            glow = Image.new("RGBA", (n, n), (255, 255, 255, 90))
            glow.putalpha(edge.point(lambda v: int(v * 0.35)))
            _RIM_CACHE[0] = glow
        im.alpha_composite(glow)
    except Exception:
        pass
    return im


def _draw_number(Image, ImageDraw, im, n, text, ink):
    """The race number, centred on the shell, as big as it will go.

    A PLATE BEHIND IT, because a number in white on a white stripe is not a
    number. The plate is the shell colour at its darkest, which reads on every
    palette entry without needing a per-colour rule.
    """
    try:
        from PIL import ImageFont
    except Exception:
        return
    font = None
    for name in ("ChakraPetch-Bold.ttf", "chakrapetch-semibold.ttf",
                 "ChakraPetch-SemiBold.ttf",
                 "arialbd.ttf", "impact.ttf", "arial.ttf",
                 "DejaVuSans-Bold.ttf"):
        for where in (_DIR, os.path.join(os.environ.get("WINDIR", ""),
                                         "Fonts")):
            p = os.path.join(where, name)
            if os.path.exists(p):
                try:
                    # A STARTING SIZE ONLY. It is fitted to the box below --
                    # one digit and two digits cannot share a fixed size, and
                    # the whole point of the rework is that the number FILLS
                    # the space it is given.
                    font = ImageFont.truetype(p, int(n * PLATE_H))
                    break
                except Exception:
                    pass
        if font is not None:
            break
    if font is None:
        return
    d = ImageDraw.Draw(im)
    try:
        box = d.textbbox((0, 0), text, font=font)
    except Exception:
        return
    w, h = box[2] - box[0], box[3] - box[1]
    # GROWN TO FILL THE BOX, not merely shrunk to survive it.
    #
    # The old version only ever scaled DOWN, so a single digit sat at whatever
    # size the constant happened to be and looked like a sticker. A race
    # number is legible because it is BIG; it is fitted to whichever of the
    # two dimensions binds first.
    if w > 0 and h > 0:
        want = min((n * PLATE_W) / float(w), (n * PLATE_H) / float(h))
        try:
            font = ImageFont.truetype(font.path,
                                      max(6, int(font.size * want)))
            box = d.textbbox((0, 0), text, font=font)
            w, h = box[2] - box[0], box[3] - box[1]
        except Exception:
            pass
    x = (n * PLATE_CX) - w / 2.0 - box[0]
    y = (n * PLATE_CY) - h / 2.0 - box[1]

    # NO PLATE. A dark rounded rectangle behind the digits was doing the work
    # of making them legible on any shell, which is backwards: it was there to
    # compensate for the number being small, and a number that fills its box
    # does not need it.
    #
    # A CONTRAST STROKE INSTEAD, and its colour is chosen from the ink's own
    # luminance rather than from a per-colour table -- so black digits get a
    # white edge and neon-yellow digits get a black one, on any shell, with no
    # rule to keep in step.
    lum = (0.299 * ink[0] + 0.587 * ink[1] + 0.114 * ink[2]) / 255.0
    edge = (16, 16, 18) if lum > 0.5 else (245, 245, 245)
    stroke = max(1, int(n * 0.014))
    try:
        d.text((x, y), text, font=font, fill=ink + (255,),
               stroke_width=stroke, stroke_fill=edge + (255,))
    except TypeError:
        # Pillow before 6.2 has no stroke. The number is still drawn, just
        # without its edge -- a worse helmet, never a crash (LAW 22).
        d.text((x, y), text, font=font, fill=ink + (255,))
