#!/usr/bin/env python3
"""Build the Plainpage README images from real Obsidian window captures.

Capture recipe
--------------
Open `Archives/Plainpage Theme Showcase`, scroll to the top, then walk the
companion plugin's palette list IN ITS OWN ORDER, capturing each palette with
Cmd+Shift+4, Space, click. Do the whole list in light mode, then the whole list
in dark. Keep the window the same size throughout. Drop the files in
~/Desktop/plainpage-shots/ under any names.

Output, into <theme>/docs/screenshots/
--------------------------------------
  hero.png             five windows cascading, dark at the back
  palettes-light.png   every palette, light mode, labelled
  palettes-dark.png    every palette, dark mode, labelled
  palettes/<mode>-<palette>.png    each capture on its own

Two things this had to solve
----------------------------
1. Identification. Colour alone cannot tell the palettes apart: Plainpage,
   Graphite and Monochrome are all #ffffff in light mode, and Rose Pine, Blush
   and Goodnotes sit within 5 units of each other. Matching on the accent
   failed too, because the most saturated block in the note is the
   ==highlight==, not a heading. So each capture is identified by the order it
   was taken and then VERIFIED against the --nt-bg its palette declares; the
   run aborts if any capture is more than 8 units from where it should be.

2. The shadow margin. A Cmd+Shift+4 window capture pads the window with its
   drop shadow as transparent pixels, and the padding is not symmetric (about
   1.8% left, 3.8% bottom). Trimming a flat percentage left a transparent halo
   inside the rounded frame. Each capture's opaque bounds are now measured and
   it is cropped to exactly the window, once, up front.

Rendering is macOS Quick Look, which is built in, so there is no browser to
install. Its viewport is about 1006 CSS px wide and its canvas is always
square, so every page here is exactly 1000x1000 and needs no cropping.
"""
import collections, os, pathlib, re, struct, subprocess, shutil, sys

SRC = pathlib.Path.home() / "Desktop" / "plainpage-shots"
# The theme folder this script reads theme.css from and writes screenshots
# into. Defaults to the repo it lives in, so a clone needs no configuration.
THEME = pathlib.Path(os.environ.get(
    "PLAINPAGE_THEME", str(pathlib.Path(__file__).resolve().parent.parent)))
OUT = THEME / "docs" / "screenshots"
WORK = pathlib.Path("/tmp/pp-compose")
CLEAN = WORK / "clean"
PAGE, BG = 1000, "#c9d1cd"
SINGLE_W = 1400          # width of the per-palette images

# The order the plugin lists palettes in, which is the order they get captured.
PLUGIN_ORDER = ["default", "graphite", "sepia", "everforest", "nord",
                "rose-pine", "dim", "blush", "terracotta", "goodnotes", "mono"]

# The cascade, back to front. Chosen by hand for a light and dark mix so the
# hero looks the same from one run to the next.
HERO = [("blush", "dark"), ("everforest", "dark"), ("nord", "dark"),
        ("terracotta", "light"), ("sepia", "light")]

LABELS = {"default": "Plainpage", "graphite": "Graphite", "sepia": "Sepia",
          "everforest": "Everforest", "nord": "Nord", "rose-pine": "Rose Pine",
          "dim": "Dim", "blush": "Blush", "terracotta": "Terracotta",
          "goodnotes": "Goodnotes", "mono": "Monochrome"}


# ---------------------------------------------------------------- small tools

def png_size(p):
    return struct.unpack(">II", pathlib.Path(p).read_bytes()[16:24])


def parse_hex(v):
    v = v.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def read_bmp(png, width, tag):
    """Downscale to BMP and return (w, h, pixel(x,y) -> r,g,b,a)."""
    WORK.mkdir(parents=True, exist_ok=True)
    bmp = WORK / f"{pathlib.Path(png).stem}-{tag}.bmp"
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
        return d[i + 2], d[i + 1], d[i], (d[i + 3] if bpp == 4 else 255)

    return w, h, px


# ------------------------------------------------------ crop off the shadow

def clean(png):
    """Crop a capture down to just the window and cache the result.

    The capture pads the window with its drop shadow as transparent pixels,
    asymmetrically. Left as-is, that halo shows inside the rounded frame added
    during composition.
    """
    CLEAN.mkdir(parents=True, exist_ok=True)
    out = CLEAN / pathlib.Path(png).name
    if out.exists():
        return out
    w, h, px = read_bmp(png, 400, "alpha")
    midx, midy = w // 2, h // 2
    solid = lambda x, y: px(x, y)[3] > 200
    left = next(x for x in range(w) if solid(x, midy))
    right = next(x for x in range(w - 1, -1, -1) if solid(x, midy))
    top = next(y for y in range(h) if solid(midx, y))
    bot = next(y for y in range(h - 1, -1, -1) if solid(midx, y))

    W, H = png_size(png)
    pad = 3                                  # clear of the anti-aliased edge
    x0 = round(left / w * W) + pad
    y0 = round(top / h * H) + pad
    cw = round((right + 1) / w * W) - pad - x0
    ch = round((bot + 1) / h * H) - pad - y0
    subprocess.run(["sips", "-c", str(ch), str(cw), "--cropOffset", str(y0), str(x0),
                    str(png), "--out", str(out)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


# --------------------------------------------------------------- identifying

def palette_fingerprints():
    """{(palette, mode): background rgb} from the theme's own tokens."""
    css = (THEME / "theme.css").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(
            r"body\.theme-(light|dark)(?:\.plainpage-palette-([a-z-]+))?\s*\{(.*?)\}",
            css, re.S):
        mode, pal, block = m.group(1), m.group(2) or "default", m.group(3)
        bg = re.search(r"--nt-bg:\s*(#[0-9a-fA-F]{3,6})\s*;", block)
        if bg:
            out[(pal, mode)] = parse_hex(bg.group(1))
    return out


def note_background(png):
    """Most common colour in the note pane."""
    w, h, px = read_bmp(png, 700, "bg")
    counts = collections.Counter()
    for y in range(int(h * 0.10), int(h * 0.92), 2):
        for x in range(int(w * 0.28), int(w * 0.74), 2):
            counts[px(x, y)[:3]] += 1
    return counts.most_common(1)[0][0]


def identify(shots, table):
    shots = sorted(shots, key=lambda p: p.stat().st_mtime)
    bgs = {p: note_background(clean(p)) for p in shots}
    dark = [p for p in shots if luminance(bgs[p]) < 128]
    light = [p for p in shots if luminance(bgs[p]) >= 128]

    out, problems = [], []
    for group, mode in ((light, "light"), (dark, "dark")):
        if not group:
            continue
        if len(group) != len(PLUGIN_ORDER):
            problems.append(f"{len(group)} {mode} captures, expected "
                            f"{len(PLUGIN_ORDER)}; cannot use capture order")
            continue
        for pal, p in zip(PLUGIN_ORDER, group):
            bg, want = bgs[p], table[(pal, mode)]
            d = sum((a - b) ** 2 for a, b in zip(want, bg)) ** 0.5
            if d > 8:
                problems.append(
                    f"{p.name}: position says {pal} {mode} "
                    f"(#{want[0]:02x}{want[1]:02x}{want[2]:02x}) but it sampled "
                    f"#{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}, off by {d:.0f}")
            out.append((p, pal, mode, bg, d))
    if problems:
        sys.exit("capture order does not line up:\n  " + "\n  ".join(problems))
    return out


# --------------------------------------------------------------- composition

def render(name, html):
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / f"{name}.html").write_text(html, encoding="utf-8")
    shot = WORK / f"{name}.html.png"
    shot.unlink(missing_ok=True)
    subprocess.run(["qlmanage", "-t", "-s", "1600", "-o", str(WORK),
                    str(WORK / f"{name}.html")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dest = OUT / f"{name}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(shot, dest)
    print(f"  {name}.png  {'x'.join(map(str, png_size(dest)))}")


def shell(body, extra=""):
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'html,body{{margin:0;padding:0;overflow:hidden}}'
            f'body{{width:{PAGE}px;height:{PAGE}px;background:{BG};'
            f'font-family:Inter,-apple-system,BlinkMacSystemFont,sans-serif}}'
            f'img{{display:block;width:100%}}{extra}</style></head>'
            f'<body>{body}</body></html>')


def frame(png, disp_w, style):
    """A cropped capture as a rounded, shadowed window."""
    w0, h0 = png_size(png)
    return (f'<div style="{style};width:{disp_w}px;height:{round(h0*disp_w/w0)}px;'
            f'overflow:hidden;border-radius:9px;'
            f'box-shadow:0 20px 44px rgba(0,0,0,0.30),0 2px 7px rgba(0,0,0,0.14)">'
            f'<img src="{pathlib.Path(png).as_posix()}"></div>')


def hero(found):
    by_key = {(f[1], f[2]): f for f in found}
    missing = [k for k in HERO if k not in by_key]
    if missing:
        print(f"  hero.png skipped: no capture for {missing}")
        return
    ordered = sorted((by_key[k] for k in HERO), key=lambda f: luminance(f[3]))
    imgs = [clean(f[0]) for f in ordered]
    n = len(imgs)
    w0, h0 = png_size(imgs[0])
    span = 1 + 0.11 * (n - 1)
    disp_w = int((PAGE - 60) / span)
    disp_h = round(h0 * disp_w / w0)
    step_x, step_y = int(disp_w * 0.11), int(disp_h * 0.20)
    sw, sh = disp_w + step_x * (n - 1), disp_h + step_y * (n - 1)
    cells = "".join(
        frame(p, disp_w,
              f"position:absolute;left:{i*step_x}px;top:{i*step_y}px;z-index:{i+1}")
        for i, p in enumerate(imgs))
    render("hero", shell(
        f'<div style="position:relative;width:{sw}px;height:{sh}px;'
        f'margin:{(PAGE-sh)//2}px {(PAGE-sw)//2}px">{cells}</div>'))


def grid(name, items, title):
    if not items:
        return
    imgs = [(clean(p), pal) for p, pal, *_ in items]
    w0, h0 = png_size(imgs[0][0])
    ar = h0 / w0
    margin, gap, cap = 18, 12, 20

    best = None
    for cols in range(2, 6):
        rows = -(-len(imgs) // cols)
        cw = (PAGE - 2 * margin - gap * (cols - 1)) // cols
        total = rows * (cw * ar + cap) + gap * (rows - 1) + 2 * margin + 6
        # Keep 12px in hand: assuming an aspect ratio silently clips a row.
        if total <= PAGE - 12 and (best is None or cw > best[1]):
            best = (cols, cw)
    cols, cw = best or (5, (PAGE - 2 * margin - gap * 4) // 5)

    cells = "".join(
        f'<figure style="margin:0">{frame(p, cw, "position:relative")}'
        f'<figcaption>{LABELS.get(pal, pal)}</figcaption></figure>'
        for p, pal in imgs)
    extra = ("figcaption{margin-top:7px;font-size:13px;text-align:center;"
             "color:rgba(30,38,35,0.75)}"
             "h2{margin:0 0 16px;font-size:15px;font-weight:600;text-align:center;"
             "letter-spacing:0.06em;text-transform:uppercase;"
             "color:rgba(30,38,35,0.55)}")
    render(name, shell(
        f'<div style="display:flex;flex-direction:column;justify-content:center;'
        f'height:100%;box-sizing:border-box;padding:{margin}px 0"><h2>{title}</h2>'
        f'<div style="display:grid;grid-template-columns:repeat({cols},{cw}px);'
        f'gap:{gap}px;justify-content:center">{cells}</div></div>', extra))


def singles(found):
    """One plain image per capture: the window, cropped, downscaled."""
    dest = OUT / "palettes"
    dest.mkdir(parents=True, exist_ok=True)
    for p, pal, mode, *_ in sorted(found, key=lambda f: (f[2], PLUGIN_ORDER.index(f[1]))):
        target = dest / f"{mode}-{pal}.png"
        subprocess.run(["sips", "-Z", str(SINGLE_W), str(clean(p)),
                        "--out", str(target)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    total = sum(f.stat().st_size for f in dest.glob("*.png"))
    print(f"  palettes/  {len(list(dest.glob('*.png')))} images, "
          f"{total/1e6:.1f} MB total")


if __name__ == "__main__":
    shots = [f for f in sorted(SRC.glob("*.png")) if not f.name.startswith("_")]
    if not shots:
        sys.exit(f"no usable .png files in {SRC}")
    table = palette_fingerprints()
    found = identify(shots, table)
    print(f"identified {len(found)} captures, all verified against theme.css\n")
    for p, pal, mode, bg, d in sorted(found, key=lambda f: (f[2], f[1])):
        print(f"  {LABELS.get(pal, pal):<11} {mode:<5} "
              f"bg #{bg[0]:02x}{bg[1]:02x}{bg[2]:02x}  off by {d:.0f}")
    print("\ncomposing:")
    hero(found)
    for mode, name in (("light", "palettes-light"), ("dark", "palettes-dark")):
        grid(name, sorted((f for f in found if f[2] == mode),
                          key=lambda f: PLUGIN_ORDER.index(f[1])),
             f"Plainpage palettes, {mode} mode")
    singles(found)
