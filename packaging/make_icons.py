"""Generates packaging/icon.{png,ico,icns}: a simple envelope glyph on a
rounded square, in the app's own accent color (--accent in
src/kindle_mailroom/web/static/style.css). Run once and commit the outputs -
nothing at build time depends on this script running; it's just how the
committed icons were made, kept around for if the mark ever needs a redo.

    python packaging/make_icons.py

Pillow writes both .ico and .icns directly, on any OS - no iconutil, no
Windows-only rc compiler, no external icon tool.
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent
SIZE = 1024
BG = (42, 109, 244, 255)      # --accent
ENVELOPE = (255, 255, 255, 255)


def _draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size * 0.06
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=size * 0.22, fill=BG)

    # Envelope: a filled rectangle with a triangular "flap" cut into its
    # top half using the background color, giving the classic envelope
    # silhouette without needing a real vector asset.
    ex0, ey0 = size * 0.20, size * 0.34
    ex1, ey1 = size * 0.80, size * 0.68
    draw.rectangle([ex0, ey0, ex1, ey1], fill=ENVELOPE)
    mid = ((ex0 + ex1) / 2, ey0 + (ey1 - ey0) * 0.6)
    draw.polygon([(ex0, ey0), (ex1, ey0), mid], fill=BG)
    return img


def main() -> None:
    base = _draw_icon(SIZE)
    base.save(OUT / "icon.png")

    sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    base.save(OUT / "icon.ico", sizes=[(s, s) for s in sizes if s <= 256])
    base.save(OUT / "icon.icns", sizes=[(s, s) for s in sizes])

    print(f"Wrote {OUT / 'icon.png'}, {OUT / 'icon.ico'}, {OUT / 'icon.icns'}")


if __name__ == "__main__":
    main()
