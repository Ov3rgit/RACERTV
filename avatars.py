"""
Radio-card icons for the overlay: a per-driver race helmet and the race
engineer's headset.

Two sources, PNG first:
  * user art — `icon_helmet_1..N.png` (pre-coloured, used as drawn, one
    assigned per driver) or a single `icon_helmet.png` (tinted per driver),
    plus `icon_engineer.png`. See helmet_variants()/variant_icon()/
    custom_icon(). Needs Pillow.
  * built-in flat vectors — draw_helmet()/draw_headset(), the fallback when
    there's no art (or no Pillow).

Run this file directly to preview the vector icons.
"""
import os
import sys
import tkinter as tk

if getattr(sys, "frozen", False):        # PyInstaller: assets sit next to the exe
    _DIR = os.path.dirname(sys.executable)
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))

DARK = "#15191e"
WHITE = "#ffffff"


def _shade(hexc, f):
    h = hexc.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    cl = lambda v: max(0, min(255, int(v)))
    return f"#{cl(r*f):02x}{cl(g*f):02x}{cl(b*f):02x}"


def _rr(c, x1, y1, x2, y2, fill, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    c.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=fill)
    c.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline=fill)
    for cx, cy in ((x1, y1), (x2 - 2 * r, y1), (x1, y2 - 2 * r), (x2 - 2 * r, y2 - 2 * r)):
        c.create_oval(cx, cy, cx + 2 * r, cy + 2 * r, fill=fill, outline=fill)


# ---- OPTIONAL user-drawn PNG icons --------------------------------------
# Drop `icon_helmet.png` and/or `icon_engineer.png` next to the app (the exe
# when frozen, avatars.py otherwise) and the radio cards use THEM instead of
# the vector drawings. Square, transparent background. The helmet PNG should
# be drawn in WHITE/greys — it gets multiplied by each driver's colour at
# runtime, so one file covers every driver tint. The engineer PNG is used
# as-is. Requires Pillow; silently falls back to vectors without it.
_PNG_SRC = {}      # kind -> PIL.Image | None (miss)
_PNG_CACHE = {}    # (kind, color, size) -> ImageTk.PhotoImage (also GC anchor)


def _is_dark_silhouette(img):
    """True when the artwork is essentially a BLACK silhouette — every
    visible pixel is dark. Such an icon is invisible on the dark radio card,
    so custom_icon() recolours it instead of drawing it as-is."""
    small = img.copy()
    small.thumbnail((32, 32))
    vis = [p for p in small.getdata() if p[3] > 128]
    if not vis:
        return False
    return sum(1 for r, g, b, _ in vis if max(r, g, b) < 70) > len(vis) * 0.9


def helmet_variants():
    """Paths of the user's pre-coloured helmet PNGs — `icon_helmet_*.png`
    next to the app, natural-sorted (so _10 follows _9). Empty when none.
    These are used AS DRAWN (no tinting); the plain `icon_helmet.png`
    single-file form stays tint-mode, see custom_icon()."""
    v = _PNG_SRC.get("__variants__")
    if v is None:
        import glob
        import re as _re

        def natkey(p):
            m = _re.findall(r"\d+", os.path.basename(p))
            return (int(m[-1]) if m else 0, p)
        v = sorted(glob.glob(os.path.join(_DIR, "icon_helmet_*.png")),
                   key=natkey)
        _PNG_SRC["__variants__"] = v
    return v


def variant_color(i):
    """The dominant SATURATED colour of helmet variant `i`, as '#rrggbb' —
    so the card accent strip, driver name and timing tower all match the
    helmet the user drew. Ignores near-white/near-black pixels (stripes,
    visor, outline) which would otherwise wash the average out to grey."""
    key = ("__vcol__", i)
    if key in _PNG_CACHE:
        return _PNG_CACHE[key]
    col = None
    try:
        from PIL import Image
        vs = helmet_variants()
        img = Image.open(vs[i % len(vs)]).convert("RGBA")
        img.thumbnail((64, 64))
        best, bw = (0, 0, 0), -1.0
        counts = {}
        for r, g, b, a in img.getdata():
            if a < 128:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            sat = (mx - mn) / 255.0
            if sat < 0.25 or mx < 60:          # grey/white/black — skip
                continue
            q = (r // 32 * 32, g // 32 * 32, b // 32 * 32)
            counts[q] = counts.get(q, 0) + 1
        for q, n in counts.items():
            w = n * (max(q) - min(q))          # frequency x colourfulness
            if w > bw:
                best, bw = q, w
        if bw > 0:
            col = "#%02x%02x%02x" % tuple(min(255, v + 16) for v in best)
    except Exception:
        col = None
    _PNG_CACHE[key] = col
    return col


# The radio card sits on a colour-keyed window, so any pixel left PARTIALLY
# transparent blends toward the key colour and shows up as a dirty halo round
# the artwork. Flattening onto the card background first removes every
# partial alpha, so edges land clean instead of fringed.
FLATTEN_BG = "#0d1320"          # CARD_BG — what the icons actually sit on


def _flatten(img, bg=FLATTEN_BG):
    """Composite RGBA art onto an opaque background, killing partial alpha."""
    from PIL import Image
    h = bg.lstrip("#")
    rgb = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    flat = Image.new("RGB", img.size, rgb)
    flat.paste(img, mask=img.split()[3])
    return flat


def variant_icon(i, size):
    """PhotoImage of helmet variant `i` at `size` (used as drawn), or None."""
    key = ("__var__", i, int(size))
    if key in _PNG_CACHE:
        return _PNG_CACHE[key]
    try:
        from PIL import Image, ImageTk
        vs = helmet_variants()
        img = Image.open(vs[i % len(vs)]).convert("RGBA")
        img = img.resize((int(size), int(size)), Image.LANCZOS)
        ph = ImageTk.PhotoImage(_flatten(img))
    except Exception:
        ph = None
    _PNG_CACHE[key] = ph                       # ref kept or tk drops the image
    return ph


def custom_icon(kind, size, color=None):
    """Tinted PhotoImage of the user's icon_<kind>.png at `size`, or None if
    there's no such file / no Pillow. Cached per (kind, colour, size)."""
    key = (kind, color, int(size))
    if key in _PNG_CACHE:
        return _PNG_CACHE[key]
    try:
        from PIL import Image, ImageTk
    except Exception:
        return None
    if kind not in _PNG_SRC:
        p = os.path.join(_DIR, f"icon_{kind}.png")
        try:
            _PNG_SRC[kind] = Image.open(p).convert("RGBA") \
                if os.path.exists(p) else None
        except Exception:
            _PNG_SRC[kind] = None
    src = _PNG_SRC[kind]
    if src is None:
        return None
    img = src.resize((int(size), int(size)), Image.LANCZOS)
    # A near-BLACK silhouette would vanish against the dark radio card, so
    # recolour it to `color` (or white) keeping the alpha — this is what
    # makes a plain black-on-transparent icon usable as-is.
    if _is_dark_silhouette(src):
        h = (color or "#ffffff").lstrip("#")
        cr, cg, cb = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        a = img.split()[3]
        img = Image.merge("RGBA", (Image.new("L", img.size, cr),
                                   Image.new("L", img.size, cg),
                                   Image.new("L", img.size, cb), a))
    elif color:                              # multiply by the driver colour
        h = color.lstrip("#")
        cr, cg, cb = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        r, g, b, a = img.split()
        img = Image.merge("RGBA", (r.point(lambda v: v * cr // 255),
                                   g.point(lambda v: v * cg // 255),
                                   b.point(lambda v: v * cb // 255), a))
    ph = ImageTk.PhotoImage(_flatten(img))   # opaque: no key-colour fringe
    _PNG_CACHE[key] = ph                     # keep a ref or tk drops the image
    return ph


def draw_helmet(c, ox, oy, s, color, seed=""):
    """One driver radio icon: a CLEAN front-face full-face race helmet,
    flat-filled with the driver's assigned colour. Deliberately few shapes —
    the old version stacked three unsmoothed 30+ point polygons, which
    aliased into a mess at bubble size. Now: one smoothed shell, a centre
    racing stripe, a wide rounded visor with pivot bolts, a visor gleam and
    chin vents. Reads as a race helmet from 30px up.
    `seed` kept for call-site compat only."""
    dark = _shade(color, 0.55)          # visor band / outline — darker SAME hue
    stripe = _shade(color, 1.45)        # centre racing stripe (lighter tint)
    gleam = _shade(color, 1.75)         # visor glass gleam

    def P(fx, fy):
        return (ox + s * fx, oy + s * fy)

    def poly(pts, **kw):
        flat = [v for p in pts for v in P(*p)]
        return c.create_polygon(*flat, **kw)

    # shell: domed crown, widest just above the visor, tapering to a rounded
    # chin bar — SMOOTHED so tk renders clean bezier edges at any size
    shell = [(.50, .06), (.66, .095), (.78, .19), (.84, .33), (.85, .48),
             (.83, .63), (.78, .76), (.70, .86), (.58, .92), (.50, .93),
             (.42, .92), (.30, .86), (.22, .76), (.17, .63), (.15, .48),
             (.16, .33), (.22, .19), (.34, .095)]
    poly(shell, fill=color, outline=dark, width=max(1.0, s * 0.025), smooth=1)
    # centre racing stripe over the crown, stopping at the visor
    poly([(.44, .065), (.56, .065), (.55, .36), (.45, .36)],
         fill=stripe, outline="", smooth=1)
    # visor: one wide rounded band across the eye line
    _rr(c, *P(.19, .365), *P(.81, .595), fill=dark, r=s * 0.10)
    # visor pivot bolts OUTSIDE the band ends — the classic race-helmet cue
    for bx in (.185, .815):
        c.create_oval(*P(bx - .045, .44), *P(bx + .045, .53),
                      fill=_shade(color, 0.38), outline="")
        c.create_oval(*P(bx - .018, .467), *P(bx + .018, .503),
                      fill=_shade(color, 0.75), outline="")
    # glass gleam: single thin bar along the visor top
    _rr(c, *P(.27, .40), *P(.58, .44), fill=gleam, r=s * 0.018)
    # chin-bar vent: one small rounded slot (kept single — clean at 30px)
    _rr(c, *P(.42, .72), *P(.58, .77), fill=dark, r=s * 0.02)


def draw_headset(c, ox, oy, s):
    """The race-engineer icon: clean WHITE over-ear headset with a boom mic.
    Symmetric band, two rounded cups with dark cushions, one smooth boom arc
    to a mic tip — few shapes, all rounded, so it stays crisp at bubble size."""
    HP = WHITE

    def P(fx, fy):
        return (ox + s * fx, oy + s * fy)

    # headband: one smooth arc, ends landing on the CENTRE of each cup
    c.create_line(*P(.13, .52), *P(.15, .22), *P(.50, .08), *P(.85, .22),
                  *P(.87, .52), fill=HP, width=max(2, s * 0.085), smooth=1,
                  capstyle="round")
    # ear cups: rounded, symmetric, with an inset dark cushion
    _rr(c, *P(.04, .44), *P(.26, .80), fill=HP, r=s * 0.09)
    _rr(c, *P(.74, .44), *P(.96, .80), fill=HP, r=s * 0.09)
    _rr(c, *P(.09, .50), *P(.21, .74), fill=DARK, r=s * 0.05)
    _rr(c, *P(.79, .50), *P(.91, .74), fill=DARK, r=s * 0.05)
    # boom mic: one smooth sweep from the left cup down to the mouth line,
    # ending in a round foam tip (kept clear of the cup so it reads distinctly)
    c.create_line(*P(.15, .78), *P(.18, .90), *P(.38, .93),
                  fill=HP, width=max(2, s * 0.055), smooth=1, capstyle="round")
    c.create_oval(*P(.36, .86), *P(.50, 1.00), fill=HP, outline="")


if __name__ == "__main__":
    import ctypes
    u = ctypes.windll.user32
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#0c1014")
    W, H = 8 * 96 + 20, 300
    sw = root.winfo_screenwidth()
    root.geometry(f"{W}x{H}+{(sw - W) // 2}+120")
    cv = tk.Canvas(root, width=W, height=H, bg="#0c1014", highlightthickness=0)
    cv.pack()
    colors = ["#e23b3b", "#36a3ff", "#ffd23f", "#54e36a"]
    cv.create_text(W // 2, 16, text="Helmet variants (large)", fill="#9aa3ad",
                   font=("Segoe UI", 12))
    for i in range(4):
        x = 16 + i * 96
        draw_helmet(cv, x, 30, 80, colors[i], seed=f"seed{i}")
        cv.create_text(x + 40, 130, text=f"variant {i}", fill="#f2f4f7",
                       font=("Segoe UI", 11, "bold"))
    draw_headset(cv, 16 + 4 * 96, 30, 80)
    cv.create_text(16 + 4 * 96 + 40, 130, text="engineer", fill="#f2f4f7",
                   font=("Segoe UI", 11, "bold"))
    cv.create_text(W // 2, 165, text="At radio-bubble size (~44px):",
                   fill="#9aa3ad", font=("Segoe UI", 10))
    for i in range(4):
        bx = W // 2 - 220 + i * 96
        draw_helmet(cv, bx, 180, 44, colors[i], seed=f"seed{i}")
    draw_headset(cv, W // 2 - 220 + 4 * 96, 180, 44)
    cv.create_text(W // 2, 250, text="click anywhere to close",
                   fill="#9aa3ad", font=("Segoe UI", 11))
    cv.bind("<Button-1>", lambda e: root.destroy())

    def topmost():
        try:
            h = u.GetAncestor(root.winfo_id(), 2)
            u.SetWindowPos(h, -1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10)
            root.after(500, topmost)
        except Exception:
            pass
    root.after(80, topmost)
    root.mainloop()
