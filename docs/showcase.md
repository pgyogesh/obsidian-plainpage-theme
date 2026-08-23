---
icon: 📐
cover: none
tags:
  - design
  - reference
status: draft
updated: 2026-08-23
---

# Designing with less

Plainpage started from one question: what would Obsidian look like if the interface got out of the way? Not a *minimal* theme, which usually means things are missing. A **quiet** one, where every element is still there and none of them shout.

The reading column is 708px, the same measure Notion settles on. Body text sits at 16px with generous line height. Chrome uses one grey, not five. See [[Palettes]] for the eleven schemes, or read the [design notes](https://github.com/pgyogesh/obsidian-plainpage-theme).

## What changes

Most themes stop at the editor. Plainpage treats the whole window: the ribbon flattens into the sidebar, tabs lose their borders, and the settings modal gets the same treatment as the note. You can set `--nt-line-width` in a snippet if 708px is not your measure.

> A page should feel like paper someone thought about, not a control panel someone forgot about.

### Callouts

> [!note] Tinted, not boxed
> Callouts get a low-alpha wash of their own hue with no border. Each palette retints them, so they never fight the background.

> [!tip] Every colour is a token
> Change one custom property and the whole interface follows. Nothing is hardcoded.

> [!warning] Some things CSS cannot do
> The block drag handle is visual only. Anything needing new DOM nodes or drag behaviour is out of scope for a theme, and the known limitations are listed at the end of `theme.css` rather than faked.

### Code

```javascript
// Palettes redefine tokens. Everything downstream follows.
const palette = {
  bg:      '#ffffff',
  text:    'rgb(55, 53, 47)',
  accent:  '#2383e2',
  border:  'rgba(55, 53, 47, 0.09)',
};

export function apply(el, tokens) {
  for (const [key, value] of Object.entries(tokens)) {
    el.style.setProperty(`--nt-${key}`, value);
  }
}
```

### Tables

| Region | Covers | Lines |
| --- | --- | ---: |
| 0 to 6 | Tokens, ribbon, sidebar, tabs, title bar | 528 |
| 7 | Editor, source and reading view | 239 |
| 8 to 14 | Panels, palette, settings, focus mode | 585 |
| 15 to 16 | Optional modes and the eleven palettes | 633 |
| 17 to 24 | Icons, banners, blocks, dashboards, search | 975 |

### Tasks

- [x] Flatten the ribbon into the sidebar
- [x] One secondary text colour, not three
- [ ] Screenshots for the README
- [ ] Submit to the community directory

### Lists

1. Define the tokens once
2. Map them onto Obsidian's variables
3. Override only what variables cannot reach

- Light and dark are tuned separately, never derived
- Eleven palettes, each hand-checked in both modes
- No `!important` except where Obsidian uses it first

Tags: #design #obsidian #css
