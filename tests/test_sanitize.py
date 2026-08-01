from pathlib import Path

from kindle_mailroom.core.sanitize import count_words, safe_href, sanitize_html

FIXTURE = (Path(__file__).parent / "fixtures" / "newsletter.html").read_text()


def test_strips_scripts_styles_comments_nav():
    out = sanitize_html(FIXTURE)
    assert "<script" not in out
    assert "<style" not in out
    assert "MSO conditional" not in out
    assert "<nav" not in out


def test_html5_containers_become_divs():
    out = sanitize_html(FIXTURE)
    for tag in ("article", "section", "header", "footer", "figure"):
        assert f"<{tag}" not in out
    assert "<figcaption" not in out
    # content survives the renaming
    assert "The Big Idea" in out
    assert "Weekly numbers" in out


def test_layout_table_unwrapped_data_table_kept():
    out = sanitize_html(FIXTURE)
    assert "Layout table cell content" in out
    # data table (has <th>) is preserved
    assert "<th>" in out and "Alpha" in out
    # layout table has been unwrapped: exactly one table remains
    assert out.count("<table") == 1


def test_tracking_pixels_removed():
    out = sanitize_html(FIXTURE)
    assert "spacer.gif" not in out
    assert "chart.png" in out  # real image kept


def test_attributes_stripped_to_whitelist():
    out = sanitize_html(FIXTURE)
    assert "onclick" not in out
    assert "data-track" not in out
    assert 'style="color: blue"' not in out
    assert 'href="https://example.com/post"' in out
    assert 'alt="A chart"' in out


def test_empty_blocks_removed_e999_guard():
    out = sanitize_html("<body><div></div><p>  </p><p>keep</p><div><img src='https://x/i.png'/></div></body>")
    assert "keep" in out
    assert "img" in out  # div containing only an image survives
    # No empty div/p left that lxml would serialise as self-closing
    assert "<div></div>" not in out and "<p>  </p>" not in out
    assert out.count("<p>") == 1


def test_count_words_ignores_invisible_chars():
    assert count_words("<p>one two​ three</p>") == 3
    assert count_words("<p></p>") == 0


def test_img_width_height_preserved():
    # Kindle's converter stretches an <img> with no width/height to fill the
    # column, so dropping a declared size turns small icons into full-page
    # blowups. Regression guard for that bug.
    out = sanitize_html('<body><img src="https://x/icon.png" width="40" height="40"></body>')
    assert 'width="40"' in out and 'height="40"' in out


def test_center_tag_unwrapped():
    # Newsletter templates wrap their layout in <center>; left in place it
    # centres the whole article body on the Kindle. Confirmed on a real
    # device screenshot (an itamargilad.com issue rendered fully centred).
    out = sanitize_html("<body><center><p>Body text</p></center></body>")
    assert "<center" not in out
    assert "Body text" in out


def test_css_declared_image_size_promoted_to_attributes():
    # Every's app icons declare their size only in CSS. parse_declared_length
    # reads the HTML width/height attributes, so without this promotion a
    # 14px icon looks undeclared and gets embedded at its full source size -
    # the "huge icons" bug seen on device.
    out = sanitize_html(
        '<body><img src="https://x/monologue.png" alt="Monologue" '
        'style="width: 14px; height: 14px; border-radius: 2px;"></body>'
    )
    assert 'width="14"' in out and 'height="14"' in out


def test_css_size_ignores_non_pixel_lengths():
    # "100%"/auto mean "fill the container" - not a fixed display size, so
    # they must not be promoted into width/height attributes.
    out = sanitize_html(
        '<body><img src="https://x/chart.png" style="width: 100%; height: auto;"></body>'
    )
    assert "width=" not in out and "height=" not in out


def test_style_length_parsing():
    from kindle_mailroom.core.sanitize import style_length

    assert style_length("width: 14px; height: 14px", "width") == "14"
    assert style_length("max-width:100%;width:600px", "width") == "600"
    assert style_length("width: 12.5px", "width") == "12"
    assert style_length("width: 100%", "width") is None
    assert style_length("width: auto", "width") is None
    assert style_length(None, "width") is None
    # must not match max-width when asked for width
    assert style_length("max-width: 600px", "width") is None


def test_safe_href_allows_ordinary_links():
    assert safe_href("https://example.com/post") == "https://example.com/post"
    assert safe_href("http://example.com") == "http://example.com"
    assert safe_href("mailto:me@example.com") == "mailto:me@example.com"
    assert safe_href("#section") == "#section"
    assert safe_href("/relative/path") == "/relative/path"
    assert safe_href("./sibling") == "./sibling"
    assert safe_href("../parent") == "../parent"


def test_safe_href_rejects_active_schemes():
    # These EPUBs get opened in browser-backed readers, where a javascript:
    # or data: href executes in the reader's context.
    assert safe_href("javascript:alert(1)") is None
    assert safe_href("data:text/html,<script>alert(1)</script>") is None
    assert safe_href("vbscript:msgbox(1)") is None
    assert safe_href("") is None
    assert safe_href(None) is None


def test_safe_href_ignores_obfuscating_control_characters():
    # Browsers strip these before resolving the scheme, so a naive prefix
    # check would let them through.
    assert safe_href("java\x00script:alert(1)") is None
    assert safe_href("  javascript:alert(1)") is None
    assert safe_href("java\tscript:alert(1)") is None
    assert safe_href("JaVaScRiPt:alert(1)") is None


def test_sanitize_drops_javascript_href_keeps_the_text():
    out = sanitize_html(
        '<body><p><a href="javascript:alert(1)">Read more</a> '
        '<a href="https://example.com/x">Real link</a></p></body>'
    )
    assert "javascript:" not in out
    assert "Read more" in out  # link text survives, only the href goes
    assert 'href="https://example.com/x"' in out
