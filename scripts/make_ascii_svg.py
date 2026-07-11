"""
Convert a portrait photo into a CLEAN, monochrome ASCII-art SVG (Andrew6rant
style: one light-gray color, subject isolated on a dark background) that "types"
itself in like a terminal, then holds.

Monochrome is deliberate -- per-character rainbow color is what makes ASCII
portraits look noisy. One fill color + a good density ramp + high contrast (so a
busy background washes out to blank) reads as neat and legible.

GitHub renders SVGs embedded via <img> and runs their SMIL animations there (JS
does not run). Each row is revealed with a left-to-right clip wipe plus a small
block cursor riding the wipe edge, staggered top -> bottom, so the whole
portrait prints once and freezes.
"""
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# defaults to the prepped grayscale image (see prep_photo.py), which already has
# the background removed + local contrast applied.
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-prepped.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "avi-ascii.svg")

COLS = 100
ROWS = 53
CELL_W = 8
CELL_H = 15
RAMP = " .`:-=+*cs#%@"  # bright(sparse) -> dark(dense); leading space clears bg

# the prepped image already has bg removed + CLAHE local contrast, so only
# light global tuning is needed here.
CONTRAST = 1.05
BRIGHTNESS = 1.0
GAMMA = 1.18          # >1 brightens mids -> face lands in sparser chars
SHARPEN = False
WHITE_FLOOR = 0.80    # luminance above this is forced to blank (space)

PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"      # the single ascii color (matches Andrew6rant)
CURSOR = "#c9d1d9"

# ---- reveal timing (one-shot; a cursor rasters top -> bottom) -------------
ROW_DUR = 0.11
STAGGER = 0.11       # == ROW_DUR -> a single cursor sweeping down

# ---- 1. sample the image into a COLS x ROWS grayscale grid ----------------
im = Image.open(SRC).convert("L")               # grayscale
if SHARPEN:
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
im = ImageEnhance.Contrast(im).enhance(CONTRAST)
im = im.resize((COLS, ROWS), Image.LANCZOS)
px = im.load()

STATIC = bool(os.environ.get("STATIC"))  # emit frozen state for previews

rows_txt = []
for y in range(ROWS):
    chars = []
    for x in range(COLS):
        lum = px[x, y] / 255.0
        lum = pow(lum, GAMMA)
        if lum >= WHITE_FLOOR:
            chars.append(" ")
            continue
        idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
        idx = max(0, min(len(RAMP) - 1, idx))
        chars.append(RAMP[idx])
    rows_txt.append("".join(chars))

art_top = TITLEBAR_H + PAD * 0.35

# ---- detect where the face starts (first row with enough non-space chars) -
face_start_row = 0
for ry, line in enumerate(rows_txt):
    filled = sum(1 for c in line if c != ' ')
    if filled > 15:
        face_start_row = ry
        break

# ---- 2. assemble SVG ------------------------------------------------------
parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
    f'Menlo, Consolas, monospace">'
)
parts.append('<defs>'
             f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
             f'</linearGradient></defs>')

parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>')
parts.append(f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
             f'fill="none" stroke="{FRAME}" stroke-width="1"/>')

parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>')
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
             f'text-anchor="middle">shivam@github: ~$ ./portrait.sh</text>')

# ---- "THE MENTALIST" title positioned just above the head -----------------
title_y = art_top + (face_start_row - 2) * CELL_H + CELL_H * 0.74
parts.append(
    f'<text x="{CANVAS_W/2}" y="{title_y:.1f}" fill="{INK}" font-size="28" font-weight="700" '
    f'text-anchor="middle" letter-spacing="6">THE MENTALIST</text>'
)

# ---- Red John smiley from actual image (auto-converted to ASCII) -----------
# Load the smiley image, convert to grayscale, boost contrast, sample to ASCII
SMILEY_SRC = os.path.join(HERE, "..", "smiley-source.jpg")
smiley_im = Image.open(SMILEY_SRC).convert("L")
smiley_im = ImageEnhance.Contrast(smiley_im).enhance(3.5)
smiley_im = ImageEnhance.Brightness(smiley_im).enhance(0.7)
smiley_im = smiley_im.resize((22, 26), Image.LANCZOS)
smiley_px = smiley_im.load()

SMILEY_COLS = 22
SMILEY_ROWS_COUNT = 26
smiley_start_col = 2
smiley_start_row = 20

smiley_art = []
for sy in range(SMILEY_ROWS_COUNT):
    chars = []
    for sx in range(SMILEY_COLS):
        lum = smiley_px[sx, sy] / 255.0
        lum = pow(lum, 1.18)
        if lum >= 0.72:
            chars.append(" ")
            continue
        idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
        idx = max(0, min(len(RAMP) - 1, idx))
        chars.append(RAMP[idx])
    smiley_art.append("".join(chars))

# animation timing
COL_T = 0.025
ROW_T = 0.04

for ri, line in enumerate(smiley_art):
    for ci, ch in enumerate(line):
        if ch == " ":
            continue
        fill = INK
        sx = PAD + (smiley_start_col + ci) * CELL_W
        sy = art_top + (smiley_start_row + ri) * CELL_H + CELL_H * 0.74
        delay = ci * COL_T + ri * ROW_T
        safe = html.escape(ch)
        parts.append(
            f'<text xml:space="preserve" x="{sx}" y="{sy:.1f}" fill="{fill}" '
            f'font-size="{CELL_H * 0.75:.1f}" opacity="0"'
            f">{safe}"
            f'<animate attributeName="opacity" from="0" to="1" '
            f'begin="{delay:.3f}s" dur="0.2s" fill="freeze"/></text>'
        )

# smiley label
label_y = art_top + (smiley_start_row + len(smiley_art) + 1) * CELL_H + 4
parts.append(
    f'<text x="{PAD + 10 * CELL_W}" y="{label_y:.1f}" fill="{TITLE_TEXT}" font-size="10" '
    f'text-anchor="middle">~ RED JOHN ~</text>'
)

# ---- ascii portrait rows (one <text> per row) -----------------------------
font_size = CELL_H * 0.86
for ry, line in enumerate(rows_txt):
    y = art_top + ry * CELL_H + CELL_H * 0.74
    row_y = art_top + ry * CELL_H
    delay = ry * STAGGER
    safe = html.escape(line)
    text = (f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">{safe}</text>')

    if STATIC:
        parts.append(text)
        continue

    parts.append(
        f'<clipPath id="r{ry}"><rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/></rect></clipPath>'
    )
    parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')
    parts.append(
        f'<rect y="{row_y+1:.1f}" width="{CELL_W}" height="{CELL_H-2}" fill="{CURSOR}" opacity="0">'
        f'<animate attributeName="x" from="{PAD}" to="{PAD+ART_W}" begin="{delay:.3f}s" '
        f'dur="{ROW_DUR:.2f}s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{delay+ROW_DUR:.3f}s"/></rect>'
    )

# status bar with a steady blinking cursor
status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 19
parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" stroke="{FRAME}"/>')
parts.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
             f'shivam@github:~$ whoami <tspan fill="{INK}">Shivam Singh</tspan></text>')
parts.append(f'<rect x="{PAD+206}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}">'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
             f'dur="1s" repeatCount="indefinite"/></rect>')

parts.append("</svg>")
svg = "".join(parts)
with open(OUT, "w") as f:
    f.write(svg)
print("wrote", OUT, len(svg), "bytes;", CANVAS_W, "x", CANVAS_H)
