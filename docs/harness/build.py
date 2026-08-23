#!/usr/bin/env python3
"""Generate the Plainpage screenshot harness.

Each window is its OWN html document, so it gets its own <body> and the theme's
`body.theme-dark.plainpage-palette-x` selectors apply normally. The hero page
then positions those documents as iframes and adds the shadows. Trying to put
several palettes on one page does not work: the palette selectors are scoped to
`body`.

Run:  python3 build.py       (writes the html next to this file)
      ./shoot.sh             (renders them to ../screenshots/*.png)
"""
import os, pathlib

HERE = pathlib.Path(__file__).parent

# palette id, mode, the label shown in the window's status bar
VARIANTS = [
    ("nord",       "dark",  "Nord"),
    ("terracotta", "dark",  "Terracotta"),
    ("everforest", "dark",  "Everforest"),
    ("sepia",      "light", "Sepia"),
    ("default",    "light", "Plainpage"),
]

# Every palette the companion plugin offers, in the order it lists them.
ALL_PALETTES = [
    ("default", "Plainpage"), ("graphite", "Graphite"), ("sepia", "Sepia"),
    ("everforest", "Everforest"), ("nord", "Nord"), ("rose-pine", "Rose Pine"),
    ("dim", "Dim"), ("blush", "Blush"), ("terracotta", "Terracotta"),
    ("goodnotes", "Goodnotes"), ("mono", "Monochrome"),
]

BG = "#c9d1cd"

# qlmanage renders HTML in a viewport about 1006 CSS px wide and always writes
# a square canvas. So the page is sized to a flat 1000x1000 and the cascade is
# laid out to fill it: -s 1600 then gives a 1600x1600 png with nothing clipped
# and nothing to crop.
PAGE = 1000
# Each window is rendered at its real desktop size and then scaled down for the
# cascade, exactly as a real screenshot would be. Rendering a small window
# instead would leave 16px body text looking zoomed in.
WIN_W, WIN_H = 1240, 810          # logical, inside the iframe
SCALE = 0.5
DISP_W, DISP_H = int(WIN_W*SCALE), int(WIN_H*SCALE)
STEP_X, STEP_Y = 75, 118

BASE_CSS = """
  html, body { margin: 0; padding: 0; overflow: hidden; }
  body { width: %(w)spx; height: %(h)spx;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  .app-container { height: 100%%; display: flex; flex-direction: column; }
  .titlebar { height: 38px; flex: 0 0 38px; display: flex; align-items: center;
    gap: 7px; padding: 0 13px; }
  .tl { width: 12px; height: 12px; border-radius: 50%%;
    background: var(--nt-border-strong); }
  .horizontal-main-container { display: flex; flex: 1; min-height: 0; }
  .workspace { display: flex; flex: 1; min-width: 0; }
  .mod-left-split { width: 258px; flex: 0 0 258px; display: flex; flex-direction: column; }
  .mod-root { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .workspace-tabs { display: flex; flex-direction: column; height: 100%%; min-height: 0; }
  .workspace-leaf { flex: 1; min-height: 0; display: flex; }
  .workspace-leaf-content { flex: 1; min-height: 0; display: flex; flex-direction: column; }
  /* Obsidian's own app.css paints these; without it the note's container
     shows through as a pale band wherever the content runs out. */
  .view-content, .markdown-reading-view, .markdown-preview-view,
  .workspace-leaf-content { background-color: var(--nt-bg); }
  .mod-left-split .workspace-leaf-content { background-color: var(--nt-bg-sidebar); }
  .view-content { flex: 1; min-height: 0; overflow: hidden; }
  .nav-files-container { overflow: hidden; padding: 2px 8px 12px; }
  .markdown-preview-view { height: 100%%; overflow: hidden; padding: 0 30px; }
  .markdown-preview-sizer { padding: 18px 0 0; }
  .view-header { display: flex; align-items: center; justify-content: space-between;
    height: 38px; padding: 0 15px; }
  .view-header-title { font-size: 13px; }
  .view-actions { display: flex; gap: 3px; }
  .status-bar { height: 27px; flex: 0 0 27px; display: flex; align-items: center;
    justify-content: flex-end; gap: 12px; padding: 0 13px; font-size: 11px; }
  .nav-header { padding: 5px 8px 2px; }
  .nav-buttons-container { display: flex; gap: 2px; }
  .clickable-icon { display: inline-flex; align-items: center; justify-content: center;
    width: 24px; height: 24px; border-radius: 5px; }
  .clickable-icon svg { width: 15px; height: 15px; stroke: currentColor;
    fill: none; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
  .tree-item-self { display: flex; align-items: center; gap: 7px;
    padding: 3px 8px; border-radius: 5px; font-size: 12.5px; }
  .tree-item-self svg { width: 14px; height: 14px; stroke: currentColor; fill: none;
    stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; opacity: 0.75; }
  .tree-item-children { padding-left: 13px; }
  .nav-sep { height: 9px; }
  /* Obsidian spaces top-level blocks through its .el-<tag> wrappers. */
  .markdown-preview-sizer > p,
  .markdown-preview-sizer > ul,
  .markdown-preview-sizer > pre,
  .markdown-preview-sizer > table,
  .markdown-preview-sizer > .callout { margin-bottom: var(--p-spacing, 0.5em); }
  .callout-title { display: flex; align-items: center; gap: 7px; }
  ul.contains-task-list { padding-left: 2px; }
  .task-list-item { list-style: none; }
"""

ICON = {
 "doc":  '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
 "fold": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
 "sort": '<path d="M3 6h18"/><path d="M7 12h10"/><path d="M10 18h4"/>',
 "home": '<path d="M3 10l9-7 9 7v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
 "srch": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
 "star": '<path d="M12 2l3 6.5 7 .9-5 4.8 1.2 7L12 17.8 5.8 21.2 7 14.2 2 9.4l7-.9z"/>',
 "pen":  '<path d="M17 3a2.8 2.8 0 0 1 4 4L7.5 20.5 2 22l1.5-5.5z"/>',
 "x":    '<path d="M18 6L6 18"/><path d="M6 6l12 12"/>',
 "dots": '<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>',
 "info": '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01"/><path d="M11 12h1v4h1"/>',
}
def icon(name, cls="clickable-icon"):
    return f'<div class="{cls}"><svg viewBox="0 0 24 24">{ICON[name]}</svg></div>'
def leaf(name, text, active=False):
    a = " is-active" if active else ""
    return (f'<div class="tree-item nav-file"><div class="tree-item-self nav-file-title{a}">'
            f'<svg viewBox="0 0 24 24">{ICON[name]}</svg>'
            f'<span class="tree-item-inner nav-file-title-content">{text}</span></div></div>')

BODY = """
<div class="app-container">
  <div class="titlebar"><div class="tl"></div><div class="tl"></div><div class="tl"></div></div>
  <div class="horizontal-main-container"><div class="workspace">

    <div class="workspace-split mod-horizontal mod-left-split"><div class="workspace-tabs mod-top">
      <div class="workspace-leaf"><div class="workspace-leaf-content" data-type="file-explorer">
        <div class="nav-files-container">
          {nav_top}
          <div class="nav-sep"></div>
          <div class="nav-header"><div class="nav-buttons-container">{navbtns}</div></div>
          {nav_files}
        </div>
      </div></div>
    </div></div>

    <div class="workspace-split mod-vertical mod-root"><div class="workspace-tabs mod-top mod-active">
      <div class="workspace-leaf mod-active"><div class="workspace-leaf-content" data-type="markdown" data-mode="preview">
        <div class="view-header">
          <div class="view-header-title">Designing with less</div>
          <div class="view-actions">{actions}</div>
        </div>
        <div class="view-content"><div class="markdown-reading-view">
        <div class="markdown-preview-view markdown-rendered"><div class="markdown-preview-sizer markdown-preview-section">
          <p><a class="tag">#design</a> <a class="tag">#reference</a></p>
          <h3>Overview</h3>
          <p>Plainpage is a calm, document-first theme for Obsidian. Flat surfaces,
             quiet borders, and one reading column that stays out of the way.</p>
          <h3>Eleven palettes</h3>
          <p>Each scheme redefines only the design tokens. Switch it from the
             companion plugin and the whole window follows.</p>
          <div class="callout" data-callout="note"><div class="callout-title"><div class="callout-icon">
            <svg class="svg-icon" viewBox="0 0 24 24" width="15" height="15" fill="none"
              stroke="currentColor" stroke-width="1.8" stroke-linecap="round">{info}</svg>
            </div><div class="callout-title-inner">Tinted, not boxed</div></div>
            <div class="callout-content"><p>Callouts take a low-alpha wash of their own hue.</p></div></div>
          <ul class="contains-task-list">
            <li class="task-list-item is-checked"><input class="task-list-item-checkbox" type="checkbox" checked> Light and dark tuned separately</li>
            <li class="task-list-item"><input class="task-list-item-checkbox" type="checkbox"> Every colour is a token</li>
          </ul>
          <h3>Tokens</h3>
          <pre class="language-css"><code class="language-css">body {{
  --nt-line-width: 708px;
  --nt-accent: #2383e2;
}}</code></pre>
          <table><thead><tr><th>Palette</th><th>Character</th></tr></thead><tbody>
            <tr><td>Sepia</td><td>Warm paper</td></tr>
            <tr><td>Nord</td><td>Arctic blue-grey</td></tr>
            <tr><td>Monochrome</td><td>Greyscale only</td></tr>
          </tbody></table>
        </div></div></div></div>
      </div></div>
    </div></div>

  </div></div>
  <div class="status-bar"><div class="status-bar-item">{label}</div><div class="status-bar-item">318 words</div></div>
</div>
"""

def window_html(palette, mode, label):
    cls = f"theme-{mode}"
    if palette != "default":
        cls += f" plainpage-palette-{palette}"
    nav_top = "".join(leaf(n, t) for n, t in
                      [("home", "Home"), ("srch", "Search"), ("star", "Starred")])
    nav_files = "".join([
        f'<div class="tree-item nav-folder"><div class="tree-item-self nav-folder-title">'
        f'<svg viewBox="0 0 24 24">{ICON["fold"]}</svg>'
        f'<span class="tree-item-inner nav-folder-title-content">Design</span></div>'
        f'<div class="tree-item-children">'
        + leaf("doc", "Designing with less", True)
        + leaf("doc", "Palettes")
        + leaf("doc", "Type scale")
        + '</div></div>',
        leaf("doc", "Inbox"), leaf("doc", "Today"),
    ])
    body = BODY.format(
        nav_top=nav_top, nav_files=nav_files, label=label, info=ICON["info"],
        navbtns="".join(icon(n) for n in ("doc", "fold", "sort")),
        actions="".join(icon(n) for n in ("pen", "x", "dots")))
    return (f'<!doctype html><html><head><meta charset="utf-8">'
            f'<link rel="stylesheet" href="../../theme.css">'
            f'<style>{BASE_CSS % {"w": WIN_W, "h": WIN_H}}</style></head>'
            f'<body class="{cls}">{body}</body></html>')

def hero_html():
    n = len(VARIANTS)
    stage_w = DISP_W + STEP_X * (n - 1)
    stage_h = DISP_H + STEP_Y * (n - 1)
    mx = (PAGE - stage_w) // 2
    my = (PAGE - stage_h) // 2
    frames = []
    for i, (pal, mode, label) in enumerate(VARIANTS):
        frames.append(
            f'<div class="win" style="left:{i*STEP_X}px; top:{i*STEP_Y}px; z-index:{i+1}">'
            f'<iframe src="win-{pal}-{mode}.html" scrolling="no"></iframe></div>')
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Plainpage hero</title>
<style>
  html, body {{ margin: 0; padding: 0; overflow: hidden; }}
  body {{ width: {PAGE}px; height: {PAGE}px; background: {BG}; }}
  .stage {{ position: relative; width: {stage_w}px; height: {stage_h}px;
    margin: {my}px {mx}px; }}
  .win {{ position: absolute; width: {DISP_W}px; height: {DISP_H}px;
    border-radius: 10px; overflow: hidden;
    box-shadow: 0 22px 50px rgba(0,0,0,0.28), 0 3px 9px rgba(0,0,0,0.13); }}
  .win iframe {{ width: {WIN_W}px; height: {WIN_H}px; border: 0;
    transform: scale({SCALE}); transform-origin: top left; }}
</style></head>
<body><div class="stage">{''.join(frames)}</div></body></html>"""

def single_html(palette, mode):
    """One window centred on the hero background. For the README body.

    The page is square because qlmanage always writes a square canvas; keeping
    the page square too means the render needs no cropping.
    """
    sc = 0.78
    w, h = int(WIN_W*sc), int(WIN_H*sc)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Plainpage {palette} {mode}</title>
<style>
  html, body {{ margin: 0; padding: 0; overflow: hidden; }}
  body {{ width: {PAGE}px; height: {PAGE}px; background: {BG};
    display: flex; align-items: center; justify-content: center; }}
  .win {{ width: {w}px; height: {h}px; border-radius: 10px; overflow: hidden;
    box-shadow: 0 22px 50px rgba(0,0,0,0.26), 0 3px 9px rgba(0,0,0,0.12); }}
  .win iframe {{ width: {WIN_W}px; height: {WIN_H}px; border: 0;
    transform: scale({sc}); transform-origin: top left; }}
</style></head>
<body><div class="win"><iframe src="win-{palette}-{mode}.html" scrolling="no"></iframe></div></body></html>"""


def palettes_html():
    """All eleven palettes at a glance, fitted to the square page."""
    cols, gap, sc = 3, 18, 0.225
    w, h = int(WIN_W*sc), int(WIN_H*sc)
    cells = "".join(
        f'<figure><div class="win"><iframe src="win-{pid}-light.html" scrolling="no">'
        f'</iframe></div><figcaption>{label}</figcaption></figure>'
        for pid, label in ALL_PALETTES)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Plainpage palettes</title>
<style>
  html, body {{ margin: 0; padding: 0; overflow: hidden; }}
  body {{ width: {PAGE}px; height: {PAGE}px; background: {BG};
    font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif; }}
  .grid {{ display: grid; grid-template-columns: repeat({cols}, {w}px);
    gap: {gap}px; justify-content: center; align-content: center;
    height: 100%; box-sizing: border-box; padding: 22px 0; }}
  figure {{ margin: 0; }}
  .win {{ width: {w}px; height: {h}px; border-radius: 7px; overflow: hidden;
    box-shadow: 0 8px 20px rgba(0,0,0,0.20), 0 1px 4px rgba(0,0,0,0.10); }}
  .win iframe {{ width: {WIN_W}px; height: {WIN_H}px; border: 0;
    transform: scale({sc}); transform-origin: top left; }}
  figcaption {{ margin-top: 8px; font-size: 13px; text-align: center;
    color: rgba(30,38,35,0.72); }}
</style></head>
<body><div class="grid">{cells}</div></body></html>"""


if __name__ == "__main__":
    for pal, mode, label in VARIANTS:
        p = HERE / f"win-{pal}-{mode}.html"
        p.write_text(window_html(pal, mode, label), encoding="utf-8")
        print("wrote", p.name)
    for pid, _ in ALL_PALETTES:
        pth = HERE / f"win-{pid}-light.html"
        if not pth.exists():
            pth.write_text(window_html(pid, "light", ""), encoding="utf-8")
            print("wrote", pth.name)
    for name, html in [("hero.html", hero_html()),
                       ("single-light.html", single_html("default", "light")),
                       ("single-dark.html", single_html("nord", "dark")),
                       ("palettes.html", palettes_html())]:
        (HERE / name).write_text(html, encoding="utf-8")
        print("wrote", name)
