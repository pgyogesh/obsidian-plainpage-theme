# Plainpage

A calm, document-first theme for [Obsidian](https://obsidian.md), inspired by the way Notion presents a page. Flat surfaces, quiet borders, a comfortable reading column, and eleven colour palettes. Light and dark mode.

Plainpage is an independent project. It is not affiliated with, endorsed by, or connected to Notion Labs, Inc.

[![Buy me a book](https://img.shields.io/badge/Buy%20me%20a%20book-FFDD00?style=for-the-badge&logo=buy-me-a-book&logoColor=000000)](https://www.buymeacoffee.com/pgyogesh)

Plainpage is free and always will be. If it earns a place in your vault,
a coffee helps a student finish their education.

![Plainpage in five of its palettes](docs/screenshots/hero.png)

## Install

**From Obsidian** (once it is in the directory): Settings, Appearance, Themes, Manage, then search for Plainpage.

**Manually:** download `manifest.json` and `theme.css` from the [latest release](https://github.com/pgyogesh/obsidian-plainpage-theme/releases) into `<vault>/.obsidian/themes/Plainpage/`, then pick Plainpage under Settings, Appearance.

## What it covers

The whole window, not only the note:

| Area | Treated |
| --- | --- |
| Ribbon and left sidebar | Flattened into one quiet surface |
| Workspace tabs and title bar | Yes |
| Editor, both source and reading view | Yes |
| Right sidebar panels | Yes |
| Command palette and quick switcher | Yes |
| Settings modal | Yes |
| Status bar, scrollbars, buttons, inputs | Yes |
| Callouts, code blocks, tables, tags, properties | Yes |

## Palettes

Eleven schemes, each hand-tuned for light and dark separately. Switch them from the companion plugin.

| Palette | Character | Full size |
| --- | --- | --- |
| Plainpage | The default. Warm off-white paper, blue accent. | [light](docs/screenshots/palettes/light-default.png) &middot; [dark](docs/screenshots/palettes/dark-default.png) |
| Graphite | Cool neutral grey | [light](docs/screenshots/palettes/light-graphite.png) &middot; [dark](docs/screenshots/palettes/dark-graphite.png) |
| Sepia | Warm paper | [light](docs/screenshots/palettes/light-sepia.png) &middot; [dark](docs/screenshots/palettes/dark-sepia.png) |
| Everforest | Muted green | [light](docs/screenshots/palettes/light-everforest.png) &middot; [dark](docs/screenshots/palettes/dark-everforest.png) |
| Nord | Arctic blue-grey | [light](docs/screenshots/palettes/light-nord.png) &middot; [dark](docs/screenshots/palettes/dark-nord.png) |
| Rosé Pine | Muted mauve | [light](docs/screenshots/palettes/light-rose-pine.png) &middot; [dark](docs/screenshots/palettes/dark-rose-pine.png) |
| Dim | Soft contrast: darker light, lighter dark | [light](docs/screenshots/palettes/light-dim.png) &middot; [dark](docs/screenshots/palettes/dark-dim.png) |
| Blush | Warm rose and mauve | [light](docs/screenshots/palettes/light-blush.png) &middot; [dark](docs/screenshots/palettes/dark-blush.png) |
| Terracotta | Warm grey and clay | [light](docs/screenshots/palettes/light-terracotta.png) &middot; [dark](docs/screenshots/palettes/dark-terracotta.png) |
| Goodnotes | Peach, clay and sage | [light](docs/screenshots/palettes/light-goodnotes.png) &middot; [dark](docs/screenshots/palettes/dark-goodnotes.png) |
| Monochrome | Greyscale only. Hierarchy through tone, not hue. | [light](docs/screenshots/palettes/light-mono.png) &middot; [dark](docs/screenshots/palettes/dark-mono.png) |

![Every palette in light mode](docs/screenshots/palettes-light.png)

![Every palette in dark mode](docs/screenshots/palettes-dark.png)

A palette redefines only the `--nt-*` design tokens. Everything else follows automatically.

## Companion plugin

[Plainpage Settings](https://github.com/pgyogesh/obsidian-plainpage-settings) is optional. The theme looks complete without it. Install it if you want the palette switcher, the optional layout modes, page icons and cover banners.

The plugin works by toggling `plainpage-*` classes on `<body>`. The theme styles those classes. Neither one needs the other to load.

## Customising

Every colour, radius, spacing and font size is a CSS custom property, declared once at the top of `theme.css`. To change something, add a snippet:

```css
body {
  --nt-line-width: 800px;      /* wider reading column */
  --nt-accent: #2d9964;        /* green accent */
}
```

The file is organised into numbered regions, each with a comment explaining what it does and why. Start there rather than searching for a selector.

## Known limitations

Some Notion behaviours cannot be reproduced in CSS alone. These are documented in a block at the end of `theme.css` rather than faked. The short version: the block drag handle is visual only, and anything needing new DOM nodes or drag behaviour is out of scope for a theme.

## Reproducing the screenshots

Every image here is a real capture of the running app, composed by a script, so
the set can be rebuilt whenever the CSS changes.

1. Open `Archives/Plainpage Theme Showcase` and scroll to the top.
2. Walk the palette list in the companion plugin's own order, capturing each one
   with `Cmd+Shift+4` then `Space` then a click on the window. Do all of light
   mode first, then all of dark. Keep the window the same size throughout.
3. Put the files in `~/Desktop/plainpage-shots/`. Filenames do not matter.
4. Run `docs/make-screenshots.py`.

The script identifies each capture by the order it was taken, then verifies that
against the `--nt-bg` the palette declares in `theme.css`, and stops if any
capture is more than 8 units away from where it should be. Colour alone cannot
do the job: Plainpage, Graphite and Monochrome are all pure white in light mode,
and Rose Pine, Blush and Goodnotes sit within 5 units of each other.

It also measures where the window actually sits inside each capture and crops
to it. A `Cmd+Shift+4` window shot pads the window with its drop shadow as
transparent pixels, and the padding is not symmetric: about 1.8% on the left
and 3.8% at the bottom. Trimming a flat percentage instead leaves a
transparent halo inside the rounded frame.

Composition is HTML rendered by macOS Quick Look, so there is no browser to
install.

## Licence

MIT. See [LICENSE](LICENSE).
