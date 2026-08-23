#!/bin/bash
# Render the harness pages to ../screenshots/*.png.
#
# Uses macOS Quick Look (qlmanage), which is built in, so there is no browser to
# install. Two things to know about it:
#   * it renders HTML in a viewport about 1006 CSS px wide, so every page here
#     is 1000px wide and never wider;
#   * it always writes a SQUARE canvas. Rather than crop afterwards (sips only
#     crops from the centre, which slices the top off), every harness page is
#     itself 1000x1000, so the render is already the right shape.
set -euo pipefail
cd "$(dirname "$0")"
OUT="../screenshots"
TMP=/tmp/pp-shot
mkdir -p "$OUT" "$TMP"
python3 build.py > /dev/null
echo "rendering:"
for page in hero single-light single-dark palettes; do
  rm -f "$TMP/$page.html.png"
  qlmanage -t -s 1600 -o "$TMP" "$page.html" > /dev/null 2>&1
  cp "$TMP/$page.html.png" "$OUT/$page.png"
  echo "  $page.png"
done
