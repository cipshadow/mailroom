"""Image fetching, filtering, and downscaling for EPUB embedding."""

from __future__ import annotations

import io
import mimetypes
import re

import requests

# Images whose largest side is below this are decorative chrome (Substack
# like/comment/subscribe buttons, byline avatars). Embedding them makes Kindle
# magnify a 36px PNG to full column width - the "magnified headshot/icon" bug.
ICON_MAX_PX = 72
# Downscale anything wider/taller than this. Charts are served at ~1100px; 1200
# keeps them crisp while bounding bytes so a chart-heavy issue fits the budget.
MAX_IMAGE_DIM = 1200

USER_AGENT = "Mozilla/5.0"


def url_width_hint(url: str) -> int | None:
    """Substack/Cloudinary encode width as ',w_NNN,' in the CDN URL. Cheap
    pre-filter so we can skip downloading obvious icons."""
    m = re.search(r"[,/]w_(\d+)(?:,|/)", url)
    return int(m.group(1)) if m else None


def parse_declared_length(value: str | None) -> int | None:
    """Parse a leading integer out of an <img width="40"> / "40px" style
    attribute value. Returns None for percentages, "auto", or missing values."""
    if not value:
        return None
    m = re.match(r"\s*(\d+)\s*(?:px)?\s*$", value)
    return int(m.group(1)) if m else None


def fetch_image(
    url: str, idx: int, declared_width: int | None = None, declared_height: int | None = None
) -> tuple[str, str, bytes, int, int] | None:
    """Download an image, drop it if it's a decorative icon, and downscale /
    recompress large images so chart-heavy newsletters fit the byte budget.

    declared_width/declared_height are the size the source HTML asked for
    (e.g. <img width="40">). Retina/HiDPI assets are often served at 2-3x
    that resolution, so a real decoded size above ICON_MAX_PX can still be a
    decorative icon if the page only ever displayed it tiny.

    Returns (epub_path, media_type, data, width, height) - width/height are
    the dimensions the image should DISPLAY at: the source HTML's declared
    size when it has one, else the embedded pixel size. Substack serves
    avatars/headshots at full resolution (e.g. 1200x1200) while displaying
    them small; stamping the decoded size would blow them up to full column
    width on Kindle, so the declared display intent always wins. Returns
    None when the image should be skipped (icon, fetch failure, or
    undecodable).
    """
    # Cheap pre-filter: skip icons by the width hint in the CDN URL without
    # spending a network round-trip.
    hint = url_width_hint(url)
    if hint is not None and hint < ICON_MAX_PX:
        return None

    # The source HTML's own declared display size is authoritative for intent:
    # a 40x40 CSS avatar is decorative chrome no matter how many pixels the
    # underlying file actually has.
    declared_max = max(declared_width or 0, declared_height or 0)
    if declared_max and declared_max < ICON_MAX_PX:
        return None

    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        resp.raise_for_status()
        data = resp.content
        content_type = (resp.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
    except Exception:
        return None

    # Without Pillow we can't measure or shrink; fall back to raw bytes. We
    # still can't stamp a real width/height, so callers won't set the attrs.
    try:
        from PIL import Image
    except ImportError:
        ext = (mimetypes.guess_extension(content_type) or ".jpg").lstrip(".")
        return f"images/img{idx:03d}.{ext}", content_type, data, declared_width or 0, declared_height or 0

    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return None

    w, h = im.size
    # Authoritative icon filter on real decoded pixels (handles non-Substack
    # sources and any URL whose width hint lied or was absent).
    if max(w, h) < ICON_MAX_PX:
        return None

    # Downscale oversized images.
    if max(w, h) > MAX_IMAGE_DIM:
        ratio = MAX_IMAGE_DIM / max(w, h)
        im = im.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)
        w, h = im.size

    # Display size: the declared size in the source HTML is the author's
    # intent; the file's own pixel count is just delivery resolution. Fill in
    # a missing declared dimension from the image's aspect ratio.
    if declared_width:
        disp_w = declared_width
        disp_h = declared_height or max(1, round(h * declared_width / w))
    elif declared_height:
        disp_h = declared_height
        disp_w = max(1, round(w * declared_height / h))
    else:
        disp_w, disp_h = w, h

    # Re-encode. Keep alpha images as PNG (charts/diagrams with transparency and
    # crisp text); flatten everything else to JPEG which compresses photos far
    # smaller. Preserve the original bytes if our re-encode came out larger.
    has_alpha = im.mode in ("RGBA", "LA", "P") and "transparency" in im.info or im.mode in ("RGBA", "LA")
    out = io.BytesIO()
    if has_alpha:
        im.convert("RGBA").save(out, "PNG", optimize=True)
        ext, media_type = "png", "image/png"
    else:
        im.convert("RGB").save(out, "JPEG", quality=82, optimize=True)
        ext, media_type = "jpg", "image/jpeg"
    encoded = out.getvalue()

    if len(encoded) < len(data):
        return f"images/img{idx:03d}.{ext}", media_type, encoded, disp_w, disp_h
    # Re-encode didn't help (already-optimized small PNG): keep original bytes.
    orig_ext = (mimetypes.guess_extension(content_type) or ".jpg").lstrip(".")
    return f"images/img{idx:03d}.{orig_ext}", content_type, data, disp_w, disp_h
