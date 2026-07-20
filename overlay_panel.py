# -*- coding: utf-8 -*-
"""
Overlay window plumbing: the click-through, always-on-top panel windows and
the canvas wrapper that lets panel-local draw code use screen coordinates.

Separate from overlay_common because these need tk and the win32 API, and
overlay_common has to stay dependency-free so every mixin can import it.
"""
import ctypes
from ctypes import wintypes

import tkinter as tk

from overlay_common import CHROMA, GLASS, GLASS_ALPHA, WIN_ALPHA

user32 = ctypes.windll.user32
HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOMOVE_NOSIZE_NOACT = 0x1 | 0x2 | 0x10


class _TC:
    """Canvas wrapper that subtracts a panel's origin, so existing draw code
    written in game-relative coords lands correctly inside a small panel window."""
    def __init__(self, cv, ox, oy):
        self.cv, self.ox, self.oy = cv, ox, oy

    def create_rectangle(self, x1, y1, x2, y2, **kw):
        return self.cv.create_rectangle(x1 - self.ox, y1 - self.oy,
                                        x2 - self.ox, y2 - self.oy, **kw)

    def create_oval(self, x1, y1, x2, y2, **kw):
        return self.cv.create_oval(x1 - self.ox, y1 - self.oy,
                                   x2 - self.ox, y2 - self.oy, **kw)

    def create_text(self, x, y, **kw):
        return self.cv.create_text(x - self.ox, y - self.oy, **kw)

    def create_line(self, *a, **kw):
        pts = [a[i] - (self.ox if i % 2 == 0 else self.oy) for i in range(len(a))]
        return self.cv.create_line(*pts, **kw)

    def create_polygon(self, *a, **kw):
        pts = [a[i] - (self.ox if i % 2 == 0 else self.oy) for i in range(len(a))]
        return self.cv.create_polygon(*pts, **kw)


class _Panel:
    """One small always-on-top window (like the toggle, which composites
    reliably over the borderless game — a single big window does not)."""
    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            # near-opaque window so TEXT stays crisp; the see-through look comes
            # from CHROMA-keyed empty areas + stippled panel BACKGROUNDS, so the
            # background drops out to the game while numbers/text stay solid.
            self.win.attributes("-alpha", WIN_ALPHA)
            self.win.attributes("-transparentcolor", CHROMA)
        except Exception:
            pass
        self.win.configure(bg=CHROMA)
        self.cv = tk.Canvas(self.win, highlightthickness=0, bd=0, bg=CHROMA)
        self.cv.pack(fill="both", expand=True)
        self.win.withdraw()
        self.shown = False
        # GLASS: a second window BEHIND this one holding just the panel body,
        # at a lower alpha. Because alpha is per-window, the body can be
        # translucent while the text on the window above stays fully solid —
        # which no amount of per-item trickery in one window can do.
        self.bg_win = None
        self.bg_cv = None
        self.bg_hwnd = None
        if GLASS:
            try:
                bw = tk.Toplevel(root)
                bw.overrideredirect(True)
                bw.attributes("-topmost", True)
                bw.attributes("-alpha", GLASS_ALPHA)
                bw.attributes("-transparentcolor", CHROMA)
                bw.configure(bg=CHROMA)
                self.bg_cv = tk.Canvas(bw, highlightthickness=0, bd=0,
                                       bg=CHROMA)
                self.bg_cv.pack(fill="both", expand=True)
                bw.withdraw()
                bw.update_idletasks()
                bh = user32.GetAncestor(bw.winfo_id(), 2)
                bex = user32.GetWindowLongW(bh, -20)
                user32.SetWindowLongW(bh, -20, bex | 0x80 | 0x8000000)
                self.bg_win, self.bg_hwnd = bw, bh
            except Exception:
                self.bg_win = self.bg_cv = self.bg_hwnd = None
        self._geo = None
        self.hwnd = None
        try:
            self.win.update_idletasks()
            h = user32.GetAncestor(self.win.winfo_id(), 2)
            ex = user32.GetWindowLongW(h, -20)
            user32.SetWindowLongW(h, -20, ex | 0x80 | 0x8000000)  # TOOLWINDOW|NOACTIVATE
            self.hwnd = h
        except Exception:
            pass

    def place(self, x, y, w, h):
        w, h = max(1, int(w)), max(1, int(h))
        x, y = int(x), int(y)
        geo = (x, y, w, h)
        if geo != self._geo:
            self.win.geometry(f"{w}x{h}+{x}+{y}")
            self.cv.config(width=w, height=h)
            if self.bg_win is not None:
                self.bg_win.geometry(f"{w}x{h}+{x}+{y}")
                self.bg_cv.config(width=w, height=h)
            self._geo = geo
        self.cv.delete("all")
        if self.bg_cv is not None:
            self.bg_cv.delete("all")
        if not self.shown:
            if self.bg_win is not None:
                self.bg_win.deiconify()   # glass first, so it never flashes
            self.win.deiconify()          # show INSTANTLY (no fade)
            self.shown = True
        # Raise the glass first, then the content directly above it. Doing it
        # in this order every frame keeps the pair together in the z-order —
        # if the content ever slipped behind its own glass the panel would
        # look washed out.
        if self.bg_hwnd:
            user32.SetWindowPos(self.bg_hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE_NOSIZE_NOACT)
        if self.hwnd:
            user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE_NOSIZE_NOACT)
        return self.cv

    def hide(self):
        if self.shown:
            self.win.withdraw()           # hide INSTANTLY (no fade)
            if self.bg_win is not None:
                self.bg_win.withdraw()
            self.shown = False
