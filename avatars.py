"""
Flat vector radio icons for the overlay: a per-driver helmet silhouette
(4 style variants, hash-assigned so it's stable across the race, tinted to
the driver's own colour) and a white race-engineer headset.
draw_helmet(canvas, ox, oy, size, color, seed) / draw_headset(canvas, ox, oy, size)
Run this file directly to preview every variant.
"""
import tkinter as tk

SKIN = "#e8b98c"
DARK = "#15191e"
WHITE = "#ffffff"
BROW = "#3a2a1f"
GLASS = "#dbe7f0"      # vent "cutout" ring/fill tint against the dark card bg
VISOR_TINT = "#0a0f14"  # dark visor glass — reads as a visor, not a slit

EMOTIONS = ["neutral", "happy", "smug", "angry", "worried", "sad", "shock", "fired"]


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


# traced from the user's reference art (motorcycle-helmet side profile,
# facing right: rounded dome/crown at back-upper-left, diagonal chin-guard
# cut at front-lower-right), fractional coords 0..1, normalised to fill the
# icon box. Visor is a shallow diagonal band; vent sits above it near the
# crown/chin-guard shoulder.
_SHELL = [(0.477, 0.060), (0.662, 0.074), (0.847, 0.202), (0.940, 0.372),
          (0.824, 0.543), (0.627, 0.741), (0.396, 0.912), (0.199, 0.940),
          (0.083, 0.770), (0.060, 0.486), (0.153, 0.230), (0.315, 0.088)]
# a shallow LENS curve (bowed top/bottom edges via smooth=1), not a flat
# parallelogram slit — reads as an actual visor rather than a stripe
_VISOR = [(0.153, 0.514), (0.390, 0.440), (0.627, 0.401), (0.685, 0.543),
          (0.454, 0.630), (0.222, 0.656)]
_VENT = (0.766, 0.230, 0.052)          # cx, cy, r (fractional)


def draw_helmet(c, ox, oy, s, color, seed=""):
    """One driver radio icon: the reference helmet silhouette (rounded dome,
    diagonal chin-guard cut, facing right) tinted to `color`, with a front
    visor slit and a small vent. Four style variants (outline+dark-visor /
    outline+slit / solid+ring-vent / solid+filled-vent — matching the 4
    reference variants) are hash-picked from `seed` (the driver's name) so
    each driver keeps the SAME variant all race, but the grid isn't a wall
    of identical icons."""
    variant = sum((seed or color).encode("utf-8", "ignore")) % 4
    dark = _shade(color, 0.55)

    def P(fx, fy):
        return (ox + s * fx, oy + s * fy)

    def poly(pts, **kw):
        flat = [v for p in pts for v in P(*p)]
        return c.create_polygon(*flat, **kw)

    if variant in (0, 1):                  # outline shell
        poly(_SHELL, fill="", outline=color, width=max(2, s * 0.055), smooth=1)
    else:                                  # solid shell
        poly(_SHELL, fill=color, outline=dark, width=max(1, s * 0.02), smooth=1)

    if variant == 1:                       # hollow visor outline only
        poly(_VISOR, fill="", outline=color, width=max(1, s * 0.04), smooth=1)
    else:                                  # 0/2/3: proper dark visor glass
        poly(_VISOR, fill=VISOR_TINT, outline="", smooth=1)

    vx, vy, vr = _VENT
    cx, cy, r = ox + s * vx, oy + s * vy, s * vr
    if variant in (0, 1):
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="",
                      outline=color, width=max(1, s * 0.035))
    elif variant == 2:
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="",
                      outline=GLASS, width=max(1, s * 0.035))
    else:                                   # variant 3: filled vent
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=GLASS, outline="")


def draw_headset(c, ox, oy, s):
    """The race-engineer icon: clean WHITE over-ear headset with a boom mic
    (facing left, matching the driver helmets' orientation)."""
    HP = WHITE

    def P(fx, fy):
        return (ox + s * fx, oy + s * fy)

    # headband arc over the crown
    c.create_line(*P(.12, .55), *P(.16, .16), *P(.50, .05), *P(.84, .16),
                  *P(.88, .55), fill=HP, width=max(2, s * 0.09), smooth=1,
                  capstyle="round")
    # ear cups (rounded) with a dark inner cushion
    _rr(c, *P(.02, .46), *P(.24, .82), fill=HP, r=s * 0.08)
    _rr(c, *P(.76, .46), *P(.98, .82), fill=HP, r=s * 0.08)
    _rr(c, *P(.06, .52), *P(.18, .76), fill=DARK, r=s * 0.05)
    _rr(c, *P(.82, .52), *P(.94, .76), fill=DARK, r=s * 0.05)
    # boom mic arm sweeping down to a small foam tip
    c.create_line(*P(.10, .70), *P(.05, .86), *P(.30, .90), *P(.42, .80),
                  fill=HP, width=max(2, s * 0.06), smooth=1, capstyle="round")
    c.create_oval(*P(.36, .82), *P(.48, .94), fill=HP, outline="")


def draw_avatar(c, ox, oy, s, emotion="neutral", helmet="#e23b3b"):
    H = helmet
    Hd = _shade(H, 0.66)     # shadowed helmet (chin bar / lower shell)
    Hl = _shade(H, 1.18)     # top sheen
    VISOR = "#0c0f13"        # smoked visor / dark trim

    def P(fx, fy):           # fractional -> pixel point
        return (ox + s * fx, oy + s * fy)

    def poly(pts, **kw):
        flat = [v for p in pts for v in P(*p)]
        return c.create_polygon(*flat, **kw)

    # --- full-face helmet shell (egg-shaped dome narrowing to a chin) ---
    shell = [(.50, .03), (.69, .06), (.84, .18), (.90, .37), (.89, .56),
             (.83, .72), (.69, .85), (.50, .91), (.31, .85), (.17, .72),
             (.11, .56), (.10, .37), (.16, .18), (.31, .06)]
    poly(shell, fill=H, outline=Hd, width=max(1, s * 0.02), smooth=1)
    # top sheen across the crown
    poly([(.30, .07), (.50, .04), (.70, .07), (.74, .22), (.50, .27),
          (.26, .22)], fill=Hl, outline="", smooth=1)
    # racing stripes down the crown (centre white stripe + flanking accents)
    poly([(.435, .045), (.565, .045), (.55, .33), (.45, .33)],
         fill=WHITE, outline="", smooth=1)
    poly([(.40, .05), (.43, .05), (.42, .33), (.395, .33)], fill=Hd, outline="", smooth=1)
    poly([(.60, .05), (.57, .05), (.58, .33), (.605, .33)], fill=Hd, outline="", smooth=1)
    # crown vents (centre slot + two side intakes) — sells the helmet
    c.create_oval(*P(.43, .12), *P(.57, .17), fill=Hd, outline="")
    poly([(.30, .20), (.40, .22), (.38, .26), (.29, .25)], fill=VISOR, outline="", smooth=1)
    poly([(.70, .20), (.60, .22), (.62, .26), (.71, .25)], fill=VISOR, outline="", smooth=1)

    # --- visor opening: a WIDE horizontal-oval protective shield that
    #     stretches almost the full width of the helmet (driver's view port) ---
    vx1, vy1, vx2, vy2 = .11, .35, .89, .695      # visor opening bounds
    c.create_oval(*P(vx1 - .02, vy1 - .02), *P(vx2 + .02, vy2 + .02),
                  fill=VISOR, outline="")          # dark rubber gasket ring
    c.create_oval(*P(vx1, vy1), *P(vx2, vy2), fill=SKIN, outline="")  # face port
    # raised visor edge (glossy highlight along the top of the opening)
    c.create_line(*P(.18, .40), *P(.50, .355), *P(.82, .40),
                  fill="#2b3138", width=max(2, s * 0.045), smooth=1)

    # --- chin bar with vent slots + white spoiler chevron ---
    poly([(.30, .69), (.70, .69), (.63, .82), (.50, .88), (.37, .82)],
         fill=Hd, outline="", smooth=1)
    for vx in (.43, .50, .57):
        c.create_line(*P(vx, .745), *P(vx, .81), fill=VISOR, width=max(1, s * 0.022))
    poly([(.41, .86), (.50, .84), (.59, .86), (.50, .915)],
         fill=WHITE, outline="", smooth=1)                    # chin spoiler

    cxl, cxr = ox + s * 0.40, ox + s * 0.60      # eye centres
    ey = oy + s * 0.49
    er = s * 0.068
    by = oy + s * 0.425                           # brow line
    bw = s * 0.085
    my = oy + s * 0.615                           # mouth line
    mw = s * 0.105

    def eye(cx, big=False, happy=False):
        r = er * (1.5 if big else 1.0)
        if happy:                                 # ^ shaped (curved closed eye)
            c.create_arc(cx - r, ey - r, cx + r, ey + r, start=20, extent=140,
                         style="arc", outline=DARK, width=max(2, s * 0.04))
        else:
            c.create_oval(cx - r, ey - r, cx + r, ey + r, fill=DARK, outline=DARK)
            c.create_oval(cx - r * 0.2, ey - r * 0.6, cx + r * 0.5, ey,
                          fill=WHITE, outline="")   # glint

    def brow(cx, inner_down):
        # inner_down>0: angry (inner low), <0: sad/worried (inner high)
        ix = cx + (bw if cx < ox + s / 2 else -bw)   # inner end
        oxx = cx - (bw if cx < ox + s / 2 else -bw)  # outer end
        c.create_line(oxx, by - inner_down, ix, by + inner_down,
                      fill=BROW, width=max(2, s * 0.045))

    def mouth(kind):
        w = max(2, s * 0.045)
        if kind == "smile":
            c.create_arc(cxl, my - mw, cxr, my + mw, start=200, extent=140,
                         style="arc", outline=DARK, width=w)
        elif kind == "frown":
            c.create_arc(cxl, my, cxr, my + 2 * mw, start=20, extent=140,
                         style="arc", outline=DARK, width=w)
        elif kind == "open":
            c.create_oval(ox + s * 0.44, my - mw, ox + s * 0.56, my + mw,
                          fill="#5a1a1a", outline=DARK)
        elif kind == "grit":
            c.create_rectangle(ox + s * 0.42, my - mw * 0.5, ox + s * 0.58, my + mw * 0.5,
                               fill=WHITE, outline=DARK)
            c.create_line(ox + s * 0.5, my - mw * 0.5, ox + s * 0.5, my + mw * 0.5, fill=DARK)
        else:  # flat
            c.create_line(cxl + s * 0.02, my, cxr - s * 0.02, my, fill=DARK, width=w)

    if emotion == "happy":
        eye(cxl, happy=True); eye(cxr, happy=True); mouth("smile")
    elif emotion == "smug":
        eye(cxl); eye(cxr); brow(cxl, -1); brow(cxr, -1); mouth("smile")
    elif emotion == "angry":
        eye(cxl); eye(cxr); brow(cxl, s * 0.05); brow(cxr, s * 0.05); mouth("grit")
    elif emotion == "worried":
        eye(cxl, big=True); eye(cxr, big=True); brow(cxl, -s * 0.04); brow(cxr, -s * 0.04); mouth("flat")
    elif emotion == "sad":
        eye(cxl); eye(cxr); brow(cxl, -s * 0.05); brow(cxr, -s * 0.05); mouth("frown")
    elif emotion == "shock":
        eye(cxl, big=True); eye(cxr, big=True); mouth("open")
    elif emotion == "fired":
        eye(cxl); eye(cxr); brow(cxl, s * 0.03); brow(cxr, s * 0.03); mouth("open")
    else:  # neutral
        eye(cxl); eye(cxr); mouth("flat")

    # --- transparent visor glass (drawn last; emotion shows clearly through) ---
    # clear shield: only a faint tint across the TOP third + a diagonal gloss
    # sweep, so the face/eyes/mouth stay fully readable.
    c.create_arc(*P(vx1, vy1), *P(vx2, vy1 + (vy2 - vy1) * 1.0),
                 start=35, extent=110, style="chord",
                 fill="#cfeaff", stipple="gray12", outline="")
    poly([(.16, .47), (.44, .38), (.50, .41), (.22, .53)],
         fill=WHITE, stipple="gray25", outline="", smooth=1)
    poly([(.56, .42), (.70, .45), (.66, .50), (.53, .47)],
         fill=WHITE, stipple="gray12", outline="", smooth=1)


def draw_engineer(c, ox, oy, s, emotion="neutral", cap="#f5a623"):
    """The RACE ENGINEER — a human head on the pit wall: backwards cap, stubble,
    over-ear headphones with a boom mic. NOT a helmet. Reuses the same
    eyes/brows/mouth emotion engine as draw_avatar so ENG_EMOTION still maps."""
    CAP = cap
    CAPd = _shade(CAP, 0.78)          # cap rim / shadow
    JKT = "#2f6db5"                   # jacket blue
    JKTd = _shade(JKT, 0.70)
    HP = "#16181d"                    # headphone black
    HPl = "#3a3e46"                   # headphone cushion / sheen
    SKINd = _shade(SKIN, 0.86)        # neck / shadowed skin

    def P(fx, fy):
        return (ox + s * fx, oy + s * fy)

    def poly(pts, **kw):
        flat = [v for p in pts for v in P(*p)]
        return c.create_polygon(*flat, **kw)

    def line(pts, **kw):
        flat = [v for p in pts for v in P(*p)]
        return c.create_line(*flat, **kw)

    # --- jacket / shoulders + collar + neck ---
    poly([(.06, 1.0), (.12, .80), (.30, .73), (.50, .71), (.70, .73),
          (.88, .80), (.94, 1.0)], fill=JKT, outline="", smooth=1)
    poly([(.43, .73), (.50, .86), (.57, .73)], fill=JKTd, outline="", smooth=1)
    _rr(c, *P(.40, .70), *P(.60, .86), fill=SKINd, r=s * 0.05)

    # --- ears, then face on top ---
    c.create_oval(*P(.10, .42), *P(.20, .58), fill=SKIN, outline="")
    c.create_oval(*P(.80, .42), *P(.90, .58), fill=SKIN, outline="")
    c.create_oval(*P(.17, .12), *P(.83, .86), fill=SKIN, outline="")

    # --- stubble beard along the lower jaw ---
    poly([(.22, .50), (.27, .76), (.50, .84), (.73, .76), (.78, .50),
          (.68, .70), (.50, .76), (.32, .70)],
         fill=_shade(SKIN, 0.72), outline="", stipple="gray50", smooth=1)

    # --- brim peeking out the back (worn backwards), then the cap dome ---
    poly([(.36, .045), (.50, -.01), (.64, .045), (.50, .07)],
         fill=CAPd, outline="", smooth=1)
    poly([(.18, .34), (.20, .10), (.50, .035), (.80, .10), (.82, .34),
          (.66, .25), (.50, .24), (.34, .25)],
         fill=CAP, outline="", smooth=1)
    poly([(.18, .34), (.34, .26), (.50, .25), (.66, .26), (.82, .34),
          (.80, .30), (.50, .285), (.20, .30)],
         fill=CAPd, outline="", smooth=1)          # cap rim across forehead
    # snapback strap + adjuster holes at the front
    _rr(c, *P(.43, .18), *P(.57, .27), fill=_shade(CAP, 0.9), r=s * 0.015)
    for hx in (.465, .50, .535):
        c.create_oval(*P(hx - .012, .215), *P(hx + .012, .24),
                      fill=CAPd, outline="")

    # --- headphone band: a THIN arc sitting on the cap (kept slim so the orange
    #     cap still reads as the top of the head, not a helmet dome) ---
    line([(.05, .50), (.09, .10), (.50, .04), (.91, .10), (.95, .50)],
         fill=HP, width=max(2, s * 0.038), smooth=1, capstyle="round")
    # --- BIG over-ear cups — the unmistakable "engineer headset" signifier.
    #     Drawn large and breaking the head silhouette so they read clearly even
    #     at tiny bubble size. Outer shell + lighter cushion + connecting yoke. ---
    for ex in (-.04, .76):
        cxm = ex + .14
        c.create_line(*P(cxm, .12), *P(cxm, .40),
                      fill=HP, width=max(2, s * 0.05))          # yoke down to cup
        c.create_oval(*P(ex, .36), *P(ex + .28, .72), fill=HP, outline="")
        c.create_oval(*P(ex + .05, .42), *P(ex + .23, .66),
                      fill=HPl, outline="")                     # ear cushion
        c.create_oval(*P(ex + .105, .49), *P(ex + .175, .59),
                      fill=HP, outline="")                      # speaker centre
    # --- boom mic: thick arm sweeping from the left cup to a big foam tip at
    #     the mouth (the other dead giveaway that this is a headset) ---
    line([(.08, .64), (.00, .84), (.24, .82), (.36, .74)],
         fill=HP, width=max(2, s * 0.05), smooth=1, capstyle="round")
    c.create_oval(*P(.30, .68), *P(.42, .80), fill="#2b2f36", outline=HP,
                  width=max(1, s * 0.015))

    # --- eyes / brows / mouth (shared emotion engine) ---
    cxl, cxr = ox + s * 0.40, ox + s * 0.60
    ey = oy + s * 0.46
    er = s * 0.055
    by = oy + s * 0.385
    bw = s * 0.075
    my = oy + s * 0.605
    mw = s * 0.085
    midx = ox + s * 0.5

    def eye(cx, big=False, happy=False):
        r = er * (1.4 if big else 1.0)
        if happy:
            c.create_arc(cx - r, ey - r, cx + r, ey + r, start=20, extent=140,
                         style="arc", outline=DARK, width=max(2, s * 0.04))
        else:
            c.create_oval(cx - r, ey - r, cx + r, ey + r, fill=DARK, outline=DARK)
            c.create_oval(cx - r * 0.2, ey - r * 0.6, cx + r * 0.5, ey,
                          fill=WHITE, outline="")

    def brow(cx, inner_down):
        ix = cx + (bw if cx < midx else -bw)
        oxx = cx - (bw if cx < midx else -bw)
        c.create_line(oxx, by - inner_down, ix, by + inner_down,
                      fill=BROW, width=max(2, s * 0.045))

    def mouth(kind):
        w = max(2, s * 0.045)
        if kind == "smile":
            c.create_arc(cxl, my - mw, cxr, my + mw, start=200, extent=140,
                         style="arc", outline=DARK, width=w)
        elif kind == "frown":
            c.create_arc(cxl, my, cxr, my + 2 * mw, start=20, extent=140,
                         style="arc", outline=DARK, width=w)
        elif kind == "open":
            c.create_oval(ox + s * 0.45, my - mw, ox + s * 0.55, my + mw,
                          fill="#5a1a1a", outline=DARK)
        elif kind == "grit":
            c.create_rectangle(ox + s * 0.43, my - mw * 0.5,
                               ox + s * 0.57, my + mw * 0.5, fill=WHITE, outline=DARK)
            c.create_line(ox + s * 0.5, my - mw * 0.5,
                          ox + s * 0.5, my + mw * 0.5, fill=DARK)
        else:
            c.create_line(cxl + s * 0.02, my, cxr - s * 0.02, my,
                          fill=DARK, width=w)

    if emotion == "happy":
        eye(cxl, happy=True); eye(cxr, happy=True); mouth("smile")
    elif emotion == "smug":
        eye(cxl); eye(cxr); brow(cxl, -1); brow(cxr, -1); mouth("smile")
    elif emotion == "angry":
        eye(cxl); eye(cxr); brow(cxl, s * 0.05); brow(cxr, s * 0.05); mouth("grit")
    elif emotion == "worried":
        eye(cxl, big=True); eye(cxr, big=True)
        brow(cxl, -s * 0.04); brow(cxr, -s * 0.04); mouth("flat")
    elif emotion == "sad":
        eye(cxl); eye(cxr); brow(cxl, -s * 0.05); brow(cxr, -s * 0.05); mouth("frown")
    elif emotion == "shock":
        eye(cxl, big=True); eye(cxr, big=True); mouth("open")
    elif emotion == "fired":
        eye(cxl); eye(cxr); brow(cxl, s * 0.03); brow(cxr, s * 0.03); mouth("open")
    else:
        eye(cxl); eye(cxr); mouth("flat")


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
