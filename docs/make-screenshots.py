#!/usr/bin/env python3
"""Turn real Obsidian window captures into the Plainpage README images.

Drop the captures in ~/Desktop/plainpage-shots/ under ANY filename. Each one is
identified by sampling its note background and matching that against the
--nt-bg token every palette declares in theme.css, so nothing has to be renamed
by hand.

Outputs <theme>/docs/screenshots/hero.png (a cascade, darkest at the back) and
palettes.png (every capture in a labelled grid).

Composition is HTML rendered by macOS Quick Look, which is built in. Two of its
quirks set the layout: the viewport is about 1006 CSS px wide, and the canvas is
always square, so each page here is exactly 1000x1000 and needs no cropping.
Captures made with Cmd+Shift+4 then Space already carry a drop shadow, so none
is added.
"""
import pathlib, re, struct, subprocess, sys, shutil, collections

SRC = pathlib.Path.home() / "Desktop" / "plainpage-shots"
THEME = (pathlib.Path.home() / "Library/Mobile Documents/iCloud~md~obsidian"
         / "Documents/work_notes/.obsidian/themes/Plainpage")
OUT = THEME / "docs" / "screenshots"
WORK = pathlib.Path("/tmp/pp-compose")
PAGE, BG = 1000, "#c9d1cd"
HERO_COUNT = 5
# The captures include a sliver of desktop wallpaper around the window, so a
# little is trimmed off every edge before compositing. The rounded corners and
# shadow are then added here rather than relying on the capture's own.
CROP = 0.010

# The order the companion plugin lists palettes in, which is the order they
# get captured in. Used to identify each shot; see identify().
PLUGIN_ORDER = ["default", "graphite", "sepia", "everforest", "nord",
                "rose-pine", "dim", "blush", "terracotta", "goodnotes", "mono"]

# The cascade, back to front. Chosen by hand for a light and dark mix rather
# than derived, so the hero always looks the same from one run to the next.
HERO = [("blush", "dark"), ("everforest", "dark"), ("nord", "dark"),
        ("terracotta", "light"), ("sepia", "light")]

LABELS = {"default": "Plainpage", "graphite": "Graphite", "sepia": "Sepia",
          "everforest": "Everforest", "nord": "Nord", "rose-pine": "Rose Pine",
          "dim": "Dim", "blush": "Blush", "terracotta": "Terracotta",
          "goodnotes": "Goodnotes", "mono": "Monochrome"}


def parse_hex(v):
    v = v.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return tuple(int(v[i:i+2], 16) for i in (0, 2, 4))


def palette_fingerprints():
    """{(palette, mode): (bg_rgb, accent_rgb)} from the theme's own tokens.

    Background alone is not enough: Plainpage, Graphite and Monochrome are all
    #ffffff in light mode. The accent separates them.
    """
    css = (THEME / "theme.css").read_text(encoding="utf-8")
    # The default palette declares its accent once at the top, outside any
    # body.theme-* block, so it needs a fallback.
    base = re.search(r"--nt-accent:\s*(#[0-9a-fA-F]{3,6})\s*;", css)
    base_accent = parse_hex(base.group(1)) if base else (0, 0, 0)
    out = {}
    for m in re.finditer(
            r"body\.theme-(light|dark)(?:\.plainpage-palette-([a-z-]+))?\s*\{(.*?)\}",
            css, re.S):
        mode, pal, block = m.group(1), m.group(2) or "default", m.group(3)
        bg = re.search(r"--nt-bg:\s*(#[0-9a-fA-F]{3,6})\s*;", block)
        ac = re.search(r"--nt-accent:\s*(#[0-9a-fA-F]{3,6})\s*;", block)
        if bg:
            prev = out.get((pal, mode), (None, None))
            out[(pal, mode)] = (parse_hex(bg.group(1)),
                                parse_hex(ac.group(1)) if ac
                                else (prev[1] or base_accent))
    return out


def saturation(rgb):
    hi, lo = max(rgb), min(rgb)
    return 0 if hi == 0 else (hi - lo) / hi


def read_bmp(png, width):
    WORK.mkdir(parents=True, exist_ok=True)
    bmp = WORK / f"{png.stem}-{width}.bmp"
    subprocess.run(["sips", "-Z", str(width), "-s", "format", "bmp", str(png),
                    "--out", str(bmp)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = bmp.read_bytes()
    off = struct.unpack("<I", d[10:14])[0]
    w, h = struct.unpack("<ii", d[18:26])
    bpp = struct.unpack("<H", d[28:30])[0] // 8
    top_down, h = (h < 0), abs(h)
    stride = ((w * bpp + 3) // 4) * 4

    def px(x, y):
        row = y if top_down else h - 1 - y
        i = off + row * stride + x * bpp
        return d[i+2], d[i+1], d[i]        # BMP stores BGR

    return w, h, px


def sample(png):
    """(background, accent) from the note pane.

    Sampled at 700px rather than 200px: headings are only a few pixels tall
    once the window is downscaled, and at 200px the accent washes out into the
    background, which made every palette look the same.
    """
    w, h, px = read_bmp(png, 700)
    x0, x1 = int(w * 0.28), int(w * 0.74)      # note pane, clear of both sidebars
    y0, y1 = int(h * 0.10), int(h * 0.92)

    counts = collections.Counter()
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            counts[px(x, y)] += 1
    bg = counts.most_common(1)[0][0]

    # The accent is the headings. Score each colour by how saturated it is and
    # how far it sits from the background, weighted by how often it appears, so
    # a big block of near-background pixels cannot win.
    # Heading pixels are anti-aliased across hundreds of near-identical RGB
    # values, so each exact colour is rare. Quantise before counting or the
    # frequency floor throws every one of them away and the accent collapses
    # back onto the background.
    q = collections.Counter()
    for c, n in counts.items():
        q[(c[0] & 0xF0, c[1] & 0xF0, c[2] & 0xF0)] += n

    def score(c, n):
        far = sum((a - b) ** 2 for a, b in zip(c, bg)) ** 0.5
        return saturation(c) * min(far, 160) * (n ** 0.5)

    cands = [(score(c, n), c) for c, n in q.items()
             if n >= 8 and saturation(c) > 0.20
             and sum((a - b) ** 2 for a, b in zip(c, bg)) ** 0.5 > 40]
    accent = max(cands)[1] if cands else bg
    return bg, accent


def identify(shots, table):
    """Identify each capture by the order it was taken, checked against colour.

    Colour alone cannot do it. Plainpage, Graphite and Monochrome are all pure
    white in light mode, and Rose Pine, Blush and Goodnotes sit within 5 units
    of each other. Trying to break those ties on the accent failed: the
    strongest saturated block in the note is the ==highlight==, not a heading.

    Captures are taken by walking the plugin's palette list, so position says
    which palette a shot is. Every non-ambiguous shot is then verified against
    its expected --nt-bg, and the run aborts if any is off. That makes the
    ordering assumption checkable rather than merely assumed.
    """
    shots = sorted(shots, key=lambda p: p.stat().st_mtime)
    got = {p: sample(p) for p in shots}
    dark = [p for p in shots if luminance(got[p][0]) < 128]
    light = [p for p in shots if luminance(got[p][0]) >= 128]

    out, problems = [], []
    for group, mode in ((light, "light"), (dark, "dark")):
        if not group:
            continue
        if len(group) != len(PLUGIN_ORDER):
            problems.append(f"{len(group)} {mode} captures, expected "
                            f"{len(PLUGIN_ORDER)}; cannot use capture order")
            continue
        for pal, p in zip(PLUGIN_ORDER, group):
            bg = got[p][0]
            want = table[(pal, mode)][0]
            d = sum((a - b) ** 2 for a, b in zip(want, bg)) ** 0.5
            if d > 8:
                problems.append(
                    f"{p.name}: position says {pal} {mode} (#{want[0]:02x}"
                    f"{want[1]:02x}{want[2]:02x}) but it sampled "
                    f"#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}, off by {d:.0f}")
            out.append((p, pal, mode, bg, got[p][1], d))
    if problems:
        sys.exit("capture order does not line up:\n  " + "\n  ".join(problems))
    return out


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def png_size(p):
    return struct.unpack(">II", p.read_bytes()[16:24])


def render(name, html):
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / f"{name}.html").write_text(html, encoding="utf-8")
    png = WORK / f"{name}.html.png"
    png.unlink(missing_ok=True)
    subprocess.run(["qlmanage", "-t", "-s", "1600", "-o", str(WORK),
                    str(WORK / f"{name}.html")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(png, OUT / f"{name}.png")
    print(f"  {name}.png  {'x'.join(map(str, png_size(OUT / f'{name}.png')))}")


def shell(body, extra=""):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'html,body{{margin:0;padding:0;overflow:hidden}}'
            f'body{{width:{PAGE}px;height:{PAGE}px;background:{BG};'
            f'font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif}}'
            f'img{{display:block}}{extra}</style></head><body>{body}</body></html>')


def frame(png, disp_w, w0, h0, style):
    """One capture as a rounded, shadowed window with its wallpaper edge cut."""
    cx, cy = int(w0 * CROP), int(h0 * CROP)
    iw, ih = w0 - 2 * cx, h0 - 2 * cy
    sc = disp_w / iw
    return (f'<div style="{style};width:{disp_w}px;height:{int(ih*sc)}px;'
            f'overflow:hidden;border-radius:9px;'
            f'box-shadow:0 20px 44px rgba(0,0,0,0.30),0 2px 7px rgba(0,0,0,0.14)">'
            f'<img src="{png.as_posix()}" style="width:{int(w0*sc)}px;'
            f'margin:{-int(cy*sc)}px 0 0 {-int(cx*sc)}px">'
            f'</div>')


def spread(items, n):
    """Pick n items evenly across a sorted list, always keeping both ends."""
    if len(items) <= n:
        return items
    step = (len(items) - 1) / (n - 1)
    return [items[round(i * step)] for i in range(n)]


def hero(found):
    by_key = {(f[1], f[2]): f for f in found}
    missing = [k for k in HERO if k not in by_key]
    if missing:
        print(f"  hero.png skipped: no capture for {missing}")
        return
    # Darkest at the back, lightest in front.
    ordered = sorted((by_key[k] for k in HERO), key=lambda f: luminance(f[3]))
    n = len(ordered)
    w0, h0 = png_size(ordered[0][0])
    ih = h0 - 2 * int(h0 * CROP)
    span = 1 + 0.11 * (n - 1)
    disp_w = int((PAGE - 60) / span)
    disp_h = int(ih * disp_w / (w0 - 2 * int(w0 * CROP)))
    step_x, step_y = int(disp_w * 0.11), int(disp_h * 0.20)
    sw, sh = disp_w + step_x * (n - 1), disp_h + step_y * (n - 1)
    imgs = "".join(
        frame(f[0], disp_w, w0, h0,
              f"position:absolute;left:{i*step_x}px;top:{i*step_y}px;z-index:{i+1}")
        for i, f in enumerate(ordered))
    body = (f'<div style="position:relative;width:{sw}px;height:{sh}px;'
            f'margin:{(PAGE-sh)//2}px {(PAGE-sw)//2}px">{imgs}</div>')
    render("hero", shell(body))


def grid(name, items, title):
    """A labelled grid on the square page, sized to fill it.

    The column count is chosen rather than fixed: all 22 palettes in four
    columns needs six rows, which overflows the square canvas and clips the top
    and bottom. Splitting light from dark and fitting the columns keeps every
    cell legible.
    """
    if not items:
        print(f"  {name}.png skipped: nothing to show")
        return
    w0, h0 = png_size(items[0][0])
    ar = (h0 - 2 * int(h0 * CROP)) / (w0 - 2 * int(w0 * CROP))
    margin, gap, cap = 18, 12, 20

    best = None
    for cols in range(2, 6):
        rows = -(-len(items) // cols)
        cw = (PAGE - 2 * margin - gap * (cols - 1)) // cols
        total = rows * (cw * ar + cap) + gap * (rows - 1) + 2 * margin + 6   # the title line
        # Keep 12px in hand: the captures are Retina, and a slightly
        # different aspect ratio would otherwise clip the bottom row.
        if total <= PAGE - 12 and (best is None or cw > best[1]):
            best = (cols, cw, rows)
    if best is None:
        best = (5, (PAGE - 2 * margin - gap * 4) // 5, -(-len(items) // 5))
    cols, cw, _ = best

    cells = "".join(
        f'<figure style="margin:0">'
        + frame(p, cw, w0, h0, "position:relative")
        + f'<figcaption>{LABELS.get(pal, pal)}</figcaption></figure>'
        for p, pal, mode, *_ in items)
    extra = ("figcaption{margin-top:7px;font-size:13px;text-align:center;"
             "color:rgba(30,38,35,0.75)}"
             "h2{margin:0 0 18px;font-size:15px;font-weight:600;text-align:center;"
             "letter-spacing:0.06em;text-transform:uppercase;"
             "color:rgba(30,38,35,0.55)}")
    body = (f'<div style="display:flex;flex-direction:column;justify-content:center;'
            f'height:100%;box-sizing:border-box;padding:{margin}px 0"><h2>{title}</h2>'
            f'<div style="display:grid;grid-template-columns:repeat({cols},{cw}px);'
            f'gap:{gap}px;justify-content:center">{cells}</div></div>')
    render(name, shell(body, extra))


def palettes(found):
    for mode, name in (("light", "palettes-light"), ("dark", "palettes-dark")):
        items = sorted((f for f in found if f[2] == mode),
                       key=lambda f: PLUGIN_ORDER.index(f[1]))
        grid(name, items, f"Plainpage palettes, {mode} mode")


if __name__ == "__main__":
    # Two ways to leave a capture out, because at least one of them will be
    # stale: the pre-rename shot still titled "Notion Theme Showcase".
    #   * rename the file so it starts with an underscore, or
    #   * pass --exclude with part of its filename (repeatable).
    excludes = [a for i, a in enumerate(sys.argv[1:])
                if i > 0 and sys.argv[i] == "--exclude"]
    shots, skipped = [], []
    for f in sorted(SRC.glob("*.png")):
        if f.name.startswith("_") or any(x.lower() in f.name.lower() for x in excludes):
            skipped.append(f)
        else:
            shots.append(f)
    if skipped:
        print("skipped: " + ", ".join(f.name for f in skipped))
    if not shots:
        sys.exit(f"no usable .png files in {SRC}")
    table = palette_fingerprints()
    print(f"{len(table)} palette fingerprints parsed from theme.css")
    found = identify(shots, table)
    print("\nidentified:")
    for p, pal, mode, bg, ac, d in sorted(found, key=lambda f: (f[2], f[1])):
        print(f"  {p.name[-16:-4]:<14} {LABELS.get(pal, pal):<11} {mode:<5} "
              f"bg #{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}  off by {d:.0f}")
    print("\ncomposing:")
    hero(found)
    palettes(found)
