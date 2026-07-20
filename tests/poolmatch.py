"""Match an EMITTED (already-formatted) line back to the pool it came from.

Why this exists: tests used to assert with hand-written keyword lists
("does the text contain 'nose-to-tail' or 'glued to'..."). That inverts the
project's whole incentive — every line ADDED to a pool to reduce repetition
raised the chance a test picked a variant its keyword list didn't know, so
growing the dialogue made the suite flakier. These helpers compare against
the real pool instead, so a pool can grow without touching any test.

Templates carry {placeholders}, emitted text doesn't, so we match on each
template's longest literal run.

    from poolmatch import from_pool, pick_from
    assert from_pool(line, ENGINEER_LINES["warn_offtrack"])
    fired = pick_from(spoken, COMMENTARY_LINES["battle_sustained"])
"""
import re

_MIN = 10          # ignore chunks too short to identify a line


def chunks(pool, min_len=_MIN):
    """Longest literal run of each template in `pool` (text between
    {placeholders}), keeping only runs long enough to be distinctive."""
    out = []
    for tpl in pool:
        parts = (p.strip() for p in re.split(r"\{[^}]*\}", tpl))
        longest = max(parts, key=len)
        if len(longest) >= min_len:
            out.append(longest)
    return out


def from_pool(text, pool, min_len=_MIN):
    """True if `text` looks like a formatted instance of any line in `pool`."""
    return any(c in text for c in chunks(pool, min_len))


def pick_from(spoken, pool, persona=None, min_len=_MIN):
    """Every line in `spoken` that came from `pool`.

    `spoken` may be a list of plain strings, or of (persona, text) pairs as
    the FakeTts harness records them — pass `persona` to filter those."""
    cs = chunks(pool, min_len)
    out = []
    for item in spoken:
        if isinstance(item, (tuple, list)):
            p, t = item[0], item[1]
            if persona is not None and p != persona:
                continue
        else:
            t = item
        if any(c in t for c in cs):
            out.append(t)
    return out


def unformatted(lines):
    """Lines that still contain a {placeholder} — a formatting bug."""
    return [t for t in lines if "{" in t and "}" in t]
