"""
Edionic Motion Graphics Engine — graphics.py (Batch 3)

Renders the graphics the render path used to ignore: V2 overlay clips built
from storyboard `graphic` blocks, plus template-level graphics (watermark).
Two mechanisms, both already proven in this pipeline — no new dependencies:

1. ASS events merged into the captions .ass file (text, animated emphasis,
   ASS-drawn shapes). The file stays on the 1080x1920 PlayRes grid, so
   libass scales graphics to 4K exactly like captions.
2. ffmpeg drawbox fragments inserted into the filter chain BEFORE the
   subtitles filter, so card backgrounds sit behind the ASS text.
   Coordinates are authored on the 1080x1920 grid and multiplied by `scale`
   (2 for the 2160x3840 path, like the light-sweep title bar). drawbox
   geometry is STATIC and time-gated with enable=between() in seconds:
   drawbox geometry expressions cannot use seconds-based t (in drawbox
   eval t is the raw frame pts, not seconds — verified on ffmpeg 8.1.2),
   so all motion (slides, pops, rotation, progress growth) lives in the
   ASS layer or in enable-gated segments.

Element types are driven by the storyboard `graphic` field (free text,
keyword-matched): "Title card", "pill", "proof card", "lower-third",
"progress bar", "shape", plus "keyword emphasis" for the kinetic pop,
"card sequence" for numbered cards with a sweeping path line, and
"zoom" for punch-in/out on the video itself (zoompan, anchored on the
face zone). A job with no V2 clips and no template watermark renders exactly as
before — build_render_graphics() returns has_graphics=False and the
pipeline changes nothing.

Honest limits (kept, not hidden):
- Split-screen / grid layouts are data only: compositing two video sources
  needs a second input and is NOT done here.
- Style grades (V3) stay metadata: the pipeline records style_preset but
  does not apply a color grade filter.
- drawbox cannot round corners, so card/pill backgrounds drawn with ffmpeg
  are square; the pill element uses an ASS-drawn rounded rectangle instead.
- V2 clip times are treated as output-timeline times (the same convention
  the storyboard round-trip and contact-sheet QA already use).
- Zoom uses zoompan (crop w/h are fixed at filter config time, so a
  time-varying crop size is impossible; zoompan's `z` expression with
  `on`/30 is the working mechanism, verified on ffmpeg 8.1.2). The zoom
  anchors on the fixed face zone (540, 640), not a per-frame tracked
  face point, and zoompan processes every frame while zoom segments
  exist (identity zoom outside segments), which adds render time.
"""

import re
from typing import Dict, Any, List, Tuple

# ---------------------------------------------------------------------------
# Layout — all coordinates on the 1080x1920 grid. The caption zone (roughly
# y 1380-1580, bottom-aligned captions with MarginV ~340) is kept clear.
# ---------------------------------------------------------------------------

CANVAS_W = 1080
CANVAS_H = 1920

TITLE_BAND = {"x": 60, "y": 300, "w": 960, "h": 250}
TITLE_UNDERLINE_H = 8
PILL_Y = 600
PILL_H = 100
PROOF_CARD = {"x": 100, "y": 1060, "w": 880, "h": 280}
LOWER_BAND = {"x": 60, "y": 1150, "w": 660, "h": 180}
PROGRESS_BAR = {"x": 60, "y": 88, "w": 960, "h": 16}
SHAPE_CENTER = (890, 200)
SHAPE_RADIUS = 70
EMPHASIS_POS = (540, 1050)
WATERMARK_POS = (70, 1850)
CARDS_ROW = {"x": 60, "y": 720, "w": 960, "h": 260}
CARDS_LINE_Y = 690
CARDS_LINE_H = 6
CARDS_GAP = 20
ZOOM_ANCHOR = (540, 640)  # face zone: eyes upper-third after face-anchored crop
ZOOM_MAX_SEGMENTS = 6
ZOOM_MAX_PUNCH = 0.18

CARD_BG = "#11141C"
CARD_ALPHA = 0.85
TEXT_WHITE = "#FFFFFF"

DEFAULT_ACCENT = "#3B63FF"
DEFAULT_PALETTE = ["#FFFFFF", "#111111", DEFAULT_ACCENT, "#22C55E", "#FACC15"]

# Placeholder block titles that carry no display text of their own.
_NON_TITLES = {"", "b0", "beat 1", "hook", "beat", "title", "untitled"}

_HEX_RE = re.compile(r"^#([0-9a-fA-F]{6})$")

# Keyword match order matters: "lower pill highlight" must hit pill, and
# "title" must not swallow "title card" checks done earlier. First match wins.
_CLASSIFIERS: List[Tuple[Tuple[str, ...], str]] = [
    (("zoom", "punch"), "zoom"),
    (("card sequence", "card_sequence", "numbered cards", "step cards"), "card_sequence"),
    (("lower-third", "lower third", "lowerthird"), "lower_third"),
    (("title card", "title banner", "hook title"), "title_card"),
    (("pill",), "pill"),
    (("proof",), "proof_card"),
    (("progress",), "progress_bar"),
    (("emphasis", "keyword"), "emphasis"),
    (("shape", "badge", "callout"), "shape"),
]

# ASS styles appended to the captions file. Names use the Gfx prefix so they
# never collide with the caption preset styles.
GFX_STYLES = [
    "Style: GfxTitle,Arial,84,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,8,60,60,0,1",
    "Style: GfxPill,Arial,58,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,1,0,1,3,0,8,60,60,0,1",
    "Style: GfxProof,Arial,80,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,8,60,60,0,1",
    "Style: GfxProofLabel,Arial,44,&H00E8ECEF,&H00E8ECEF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,3,0,8,60,60,0,1",
    "Style: GfxLower,Arial,70,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,4,2,7,60,60,0,1",
    "Style: GfxLowerSub,Arial,44,&H00D8DEE9,&H00D8DEE9,&H00101010,&H80000000,0,0,0,0,100,100,1,0,1,3,0,7,60,60,0,1",
    "Style: GfxEmphasis,Impact,108,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,2,0,1,5,3,5,60,60,0,1",
    "Style: GfxShape,Arial,100,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
    "Style: GfxWatermark,Arial,36,&H80FFFFFF,&H80FFFFFF,&H80000000,&H00000000,-1,0,0,0,100,100,1,0,1,2,0,1,60,60,40,1",
    "Style: GfxCardNum,Arial,84,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,4,2,8,60,60,0,1",
    "Style: GfxCardLabel,Arial,36,&H00D8DEE9,&H00D8DEE9,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,3,0,8,60,60,0,1",
]

# Graphics draw above captions (captions use layers 0-3).
GFX_LAYER = 5


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def _clean_ass_text(text: str) -> str:
    """Strip characters that would break ASS parsing (braces/backslashes)."""
    cleaned = str(text or "").replace("{", "").replace("}", "").replace("\\", "")
    return " ".join(cleaned.split())


def _hex_to_ass_color(hex_color: str, alpha: int = 0x00) -> str:
    """#RRGGBB -> ASS &HAABBGGRR. Invalid input falls back to white."""
    match = _HEX_RE.match(str(hex_color or "").strip())
    if not match:
        return "&H00FFFFFF"
    rr, gg, bb = match.group(1)[0:2], match.group(1)[2:4], match.group(1)[4:6]
    return f"&H{alpha:02X}{bb}{gg}{rr}"


def _valid_hex(hex_color: str, fallback: str) -> str:
    value = str(hex_color or "").strip()
    return value if _HEX_RE.match(value) else fallback


def _is_light(hex_color: str) -> bool:
    """Relative luminance check so text on an accent fill stays readable."""
    match = _HEX_RE.match(str(hex_color or "").strip())
    if not match:
        return False
    r, g, b = (int(match.group(1)[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.6


def _wrap_two_lines(text: str, max_chars: int = 22) -> str:
    """Split display text into at most two ASS lines (\\N separated)."""
    words = str(text or "").split()
    if not words:
        return ""
    if len(" ".join(words)) <= max_chars or len(words) == 1:
        return " ".join(words)
    mid = len(words) // 2
    return " ".join(words[:mid]) + "\\N" + " ".join(words[mid:])


def _rounded_rect_path(x0: int, y0: int, x1: int, y1: int, r: int) -> str:
    """ASS drawing commands for a rounded rectangle (absolute coordinates)."""
    r = max(1, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
    k = int(round(r * 0.552))
    return (
        f"m {x0 + r} {y0} l {x1 - r} {y0} "
        f"b {x1 - r + k} {y0} {x1} {y0 + k} {x1} {y0 + r} "
        f"l {x1} {y1 - r} "
        f"b {x1} {y1 - r + k} {x1 - k} {y1} {x1 - r} {y1} "
        f"l {x0 + r} {y1} "
        f"b {x0 + r - k} {y1} {x0} {y1 - k} {x0} {y1 - r} "
        f"l {x0} {y0 + r} "
        f"b {x0} {y0 + r - k} {x0 + k} {y0} {x0 + r} {y0}"
    )


def _dialogue(start: float, end: float, style: str, text: str, layer: int = GFX_LAYER) -> str:
    return f"Dialogue: {layer},{_ass_time(start)},{_ass_time(end)},{style},,0,0,0,,{text}"


def _drawbox(x: int, y: int, w: int, h: int, color: str, start: float, end: float,
             thickness: str = "fill") -> str:
    """One drawbox filter fragment, time-gated with enable=between().

    Geometry is static: drawbox geometry expressions cannot use
    seconds-based `t` (raw frame pts in drawbox eval), so motion lives in
    the ASS layer; enable=between() in seconds gates visibility.
    """
    return (
        f"drawbox=enable='between(t,{start:.3f},{end:.3f})':"
        f"x={x}:y={y}:w={w}:h={h}:color={color}:t={thickness}"
    )


# ---------------------------------------------------------------------------
# Classification + display text
# ---------------------------------------------------------------------------

def classify_graphic(graphic_text: str) -> str:
    """Map a storyboard `graphic` description to an element type.

    Returns "" for "Caption overlay" (explicit captions-only) and empty
    values — those render nothing. Unknown descriptions fall back to the
    generic "shape" badge so user-typed graphics still show up.
    """
    text = str(graphic_text or "").strip().lower()
    if not text or text == "caption overlay":
        return ""
    for keywords, element in _CLASSIFIERS:
        if any(kw in text for kw in keywords):
            return element
    return "shape"


def _meaningful_title(title: str) -> str:
    title = str(title or "").strip()
    if title.lower() in _NON_TITLES:
        return ""
    return title


def _display_title(clip: Dict[str, Any], block: Dict[str, Any], edl_data: Dict[str, Any]) -> str:
    """Best display text for a title card: real block title, else the job's
    title_text, else the first words of the block text."""
    title = _meaningful_title(clip.get("title") or block.get("title"))
    if title:
        return title
    job_title = str(edl_data.get("title_text") or "").strip()
    if job_title and job_title.lower() not in _NON_TITLES:
        return job_title
    words = str(block.get("text") or "").split()[:8]
    return " ".join(words)


def _block_text(block: Dict[str, Any], max_words: int = 10) -> str:
    return " ".join(str(block.get("text") or "").split()[:max_words])


# ---------------------------------------------------------------------------
# Element builders — each returns (ass_events, vf_fragments)
# ---------------------------------------------------------------------------

def _title_card(start: float, end: float, text: str, accent: str, scale: int):
    band = {k: v * scale for k, v in TITLE_BAND.items()}
    # Static band (enable-gated); the title text slides in via ASS \move.
    vf = [
        _drawbox(band["x"], band["y"], band["w"], band["h"], f"{CARD_BG}@0.82",
                 start, end),
        _drawbox(band["x"], band["y"] + band["h"] - TITLE_UNDERLINE_H * scale,
                 band["w"], TITLE_UNDERLINE_H * scale, f"{accent}@0.95",
                 start, end),
    ]
    shown = _clean_ass_text(text).upper()
    events = [_dialogue(
        start, end, "GfxTitle",
        "{\\move(140,330,540,330,0,250)\\fad(150,150)}" + _wrap_two_lines(shown),
    )]
    return events, vf


def _pill(start: float, end: float, text: str, accent: str, scale: int):
    shown = _clean_ass_text(text).upper()
    est_w = min(920, max(220, int(len(shown) * 38) + 120))
    x0 = (CANVAS_W - est_w) // 2
    x1 = x0 + est_w
    y0, y1 = PILL_Y, PILL_Y + PILL_H
    fill = _hex_to_ass_color(accent)
    pill_text_color = "&H00101010" if _is_light(accent) else "&H00FFFFFF"
    path = _rounded_rect_path(x0, y0, x1, y1, PILL_H // 2)
    events = [
        _dialogue(start, end, "GfxShape",
                  "{\\an7\\pos(0,0)\\p1\\1c" + fill + "\\fad(120,120)}" + path + "{\\p0}"),
        _dialogue(start, end, "GfxPill",
                  "{\\pos(540,%d)\\fad(120,120)\\1c%s}" % (y0 + 14, pill_text_color) + shown),
    ]
    return events, []


def _proof_card(start: float, end: float, claim: str, label: str, accent: str, scale: int):
    card = {k: v * scale for k, v in PROOF_CARD.items()}
    vf = [
        _drawbox(card["x"], card["y"], card["w"], card["h"], f"{CARD_BG}@0.85", start, end),
        _drawbox(card["x"], card["y"], card["w"], card["h"], accent,
                 start, end, thickness=str(6 * scale)),
    ]
    events = [_dialogue(
        start, end, "GfxProof",
        "{\\pos(540,1100)\\fscx90\\fscy90\\t(0,180,\\fscx100\\fscy100)\\fad(150,150)}"
        + _wrap_two_lines(_clean_ass_text(claim).upper()),
    )]
    if label:
        events.append(_dialogue(
            start, end, "GfxProofLabel",
            "{\\pos(540,1245)\\fad(150,150)}" + _clean_ass_text(label),
        ))
    return events, vf


def _lower_third(start: float, end: float, name: str, role: str, accent: str, scale: int):
    band = {k: v * scale for k, v in LOWER_BAND.items()}
    # Static band (enable-gated); the name slides in via ASS \move.
    vf = [
        _drawbox(band["x"], band["y"], band["w"], band["h"], f"{CARD_BG}@0.85",
                 start, end),
        _drawbox(band["x"], band["y"], 12 * scale, band["h"], accent, start, end),
    ]
    line = "{\\move(-300,1175,100,1175,0,300)\\fad(150,150)}" + _clean_ass_text(name)
    if role:
        line += "\\N{\\fs44\\1c&HD8DEE9&}" + _clean_ass_text(role)
    events = [_dialogue(start, end, "GfxLower", line)]
    return events, vf


def _progress_bar(start: float, end: float, accent: str, scale: int):
    bar = {k: v * scale for k, v in PROGRESS_BAR.items()}
    span = max(0.25, end - start)
    vf = [
        _drawbox(bar["x"], bar["y"], bar["w"], bar["h"], "#FFFFFF@0.25", start, end),
    ]
    # The fill grows left-to-right via static segments, each gated by
    # enable=between() in seconds. A width expression using `t` cannot work:
    # in drawbox eval `t` is the raw frame pts, not seconds, so the fill
    # would show full-width from the first frame (verified on ffmpeg 8.1.2).
    # At ~10 steps/second the growth reads as smooth motion.
    n = max(20, min(120, int(round(span * 10))))
    for i in range(n):
        seg_start = start + span * i / n
        sx = round(bar["x"] + bar["w"] * i / n)
        ex = round(bar["x"] + bar["w"] * (i + 1) / n)
        vf.append(_drawbox(sx, bar["y"], ex - sx, bar["h"], accent, seg_start, end))
    return [], vf


def _card_sequence(start: float, end: float, cards: List[Dict[str, Any]], accent: str, scale: int):
    """N numbered cards in a row + a path line sweeping left-to-right.

    A faint track line sits above the cards; the accent fill grows along
    it in enable-gated segments (same mechanism as the progress bar), a
    diamond head slides along the line via ASS \\move, and each card
    switches to its highlight (accent border + top bar) exactly when the
    line reaches the card's centre: hit_i = start + span*(i+0.5)/n.

    drawbox geometry uses scaled coordinates; ASS text/drawing positions
    stay on the unscaled 1080x1920 grid (libass scales them to 4K).
    """
    n = max(1, min(6, len(cards)))
    cards = cards[:n]
    span = max(0.25, end - start)
    row = {k: v * scale for k, v in CARDS_ROW.items()}
    gap = CARDS_GAP * scale
    cw = (row["w"] - gap * (n - 1)) // n
    line_y = CARDS_LINE_Y * scale
    line_h = CARDS_LINE_H * scale
    x0, x1 = row["x"], row["x"] + row["w"]

    vf = [_drawbox(x0, line_y, row["w"], line_h, "#FFFFFF@0.25", start, end)]
    m = max(20, min(120, int(round(span * 10))))
    for j in range(m):
        seg_start = start + span * j / m
        sx = round(x0 + row["w"] * j / m)
        ex = round(x0 + row["w"] * (j + 1) / m)
        vf.append(_drawbox(sx, line_y, ex - sx, line_h, accent, seg_start, end))

    events = []
    dur_ms = max(100, int(span * 1000))
    dot_r = 14
    dot_path = f"m 0 {-dot_r} l {dot_r} 0 l 0 {dot_r} l {-dot_r} 0"
    events.append(_dialogue(
        start, end, "GfxShape",
        "{\\an5\\move(%d,%d,%d,%d,0,%d)\\p1\\1c%s\\fad(100,100)}%s{\\p0}"
        % (CARDS_ROW["x"], CARDS_LINE_Y + CARDS_LINE_H // 2,
           CARDS_ROW["x"] + CARDS_ROW["w"], CARDS_LINE_Y + CARDS_LINE_H // 2,
           dur_ms, _hex_to_ass_color(accent), dot_path),
    ))

    cw_u = (CARDS_ROW["w"] - CARDS_GAP * (n - 1)) // n
    for i, card in enumerate(cards):
        cx0 = x0 + i * (cw + gap)
        vf.append(_drawbox(cx0, row["y"], cw, row["h"], f"{CARD_BG}@0.88", start, end))
        vf.append(_drawbox(cx0, row["y"], cw, row["h"], "#3A4356", start, end,
                           thickness=str(3 * scale)))
        hit = start + span * (i + 0.5) / n
        vf.append(_drawbox(cx0, row["y"], cw, row["h"], accent, hit, end,
                           thickness=str(6 * scale)))
        vf.append(_drawbox(cx0, row["y"], cw, 10 * scale, accent, hit, end))
        cx_u = CARDS_ROW["x"] + i * (cw_u + CARDS_GAP) + cw_u // 2
        number = _clean_ass_text(card.get("number", str(i + 1)))
        events.append(_dialogue(
            start, end, "GfxCardNum",
            "{\\pos(%d,748)\\fad(120,120)}" % cx_u + number,
        ))
        label = _clean_ass_text(card.get("label", ""))
        if label:
            events.append(_dialogue(
                start, end, "GfxCardLabel",
                "{\\pos(%d,872)\\fad(120,120)}" % cx_u
                + _wrap_two_lines(label, 12),
            ))
    return events, vf


def _zoom_expression(segments: List[Tuple[float, float, float]], scale: int) -> str:
    """One zoompan filter fragment combining every zoom segment.

    crop w/h are fixed at filter config time, so a time-varying crop size
    is impossible; zoompan's `z` expression is the working mechanism. The
    fragment sits after fps=30, so `on`/30 is output seconds. Each segment
    eases in/out over 0.4s (trapezoid); total punch is capped. The zoom
    anchors on the face zone so the speaker stays framed.
    """
    terms = []
    for (s, e, amt) in segments:
        rise = f"min(1,max(0,((on/30)-{s:.3f})/0.400))"
        fall = f"min(1,max(0,({e:.3f}-(on/30))/0.400))"
        terms.append(f"{amt:.3f}*{rise}*{fall}")
    punch = "+".join(terms) if terms else "0"
    z = f"(1+min({ZOOM_MAX_PUNCH:.3f},{punch}))"
    ax, ay = ZOOM_ANCHOR[0] * scale, ZOOM_ANCHOR[1] * scale
    w, h = 1080 * scale, 1920 * scale
    return (
        f"zoompan=z='{z}':x='{ax}*(1-1/zoom)':y='{ay}*(1-1/zoom)'"
        f":d=1:s={w}x{h}:fps=30"
    )


def _shape(start: float, end: float, accent: str, scale: int):
    cx, cy = SHAPE_CENTER
    r = SHAPE_RADIUS
    dur_ms = max(100, int((end - start) * 1000))
    # Diamond centred on the origin so \frz rotates it in place.
    path = f"m 0 {-r} l {r} 0 l 0 {r} l {-r} 0"
    fill = _hex_to_ass_color(accent)
    events = [_dialogue(
        start, end, "GfxShape",
        "{\\an5\\pos(%d,%d)\\p1\\1c%s\\frz0\\t(0,%d,\\frz180)\\fad(150,150)}%s{\\p0}"
        % (cx, cy, fill, dur_ms, path),
    )]
    return events, []


def _emphasis(start: float, end: float, phrase: str, accent: str, scale: int):
    shown = _clean_ass_text(phrase).upper()
    if not shown:
        return [], []
    events = [_dialogue(
        start, end, "GfxEmphasis",
        "{\\pos(%d,%d)\\fs96\\t(0,150,\\fs132)\\t(150,300,\\fs108)\\fad(80,120)\\1c%s}"
        % (EMPHASIS_POS[0], EMPHASIS_POS[1], _hex_to_ass_color(accent)) + shown,
    )]
    return events, []


def _watermark(start: float, end: float, text: str):
    shown = _clean_ass_text(text)
    if not shown:
        return [], []
    events = [_dialogue(
        start, end, "GfxWatermark",
        "{\\pos(%d,%d)}" % WATERMARK_POS + shown,
    )]
    return events, []


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

def _palette_for(edl_data: Dict[str, Any]) -> Tuple[str, str]:
    """Return (accent, dark) hex colors from the template palette, validated."""
    palette = edl_data.get("template_palette")
    if not palette and edl_data.get("template_id"):
        try:
            from templates import get_template
            template = get_template(str(edl_data["template_id"]))
            palette = template.get("palette") if template else None
        except Exception:
            palette = None
    if not isinstance(palette, list) or len(palette) < 3:
        palette = DEFAULT_PALETTE
    accent = _valid_hex(palette[2], DEFAULT_ACCENT)
    return accent, CARD_BG


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_render_graphics(
    edl_data: Dict[str, Any],
    edited_duration: float,
    preset_name: str = "glow",
    scale: int = 1,
) -> Dict[str, Any]:
    """Build every motion-graphic element for one render.

    Reads V2 overlay clips (storyboard graphics) and template-level graphics
    (watermark). Returns ASS styles/events, ffmpeg filter fragments, and a
    summary. When there is nothing to draw, has_graphics is False and the
    caller must change nothing.
    """
    scale = 2 if int(scale) >= 2 else 1
    edited_duration = max(0.0, float(edited_duration or 0.0))
    accent, _dark = _palette_for(edl_data)

    blocks_by_id: Dict[str, Dict[str, Any]] = {}
    storyboard = edl_data.get("storyboard") or {}
    for block in storyboard.get("blocks") or []:
        if isinstance(block, dict) and block.get("id") is not None:
            blocks_by_id[str(block["id"])] = block

    v2_clips: List[Dict[str, Any]] = []
    for track in edl_data.get("tracks") or []:
        if track.get("id") == "V2":
            v2_clips = [c for c in (track.get("clips") or []) if isinstance(c, dict)]
            break

    ass_events: List[str] = []
    vf_fragments: List[str] = []
    zoom_segments: List[Tuple[float, float, float]] = []
    elements: List[Dict[str, Any]] = []

    for clip in v2_clips:
        # B-roll clips (hunt_broll_for_edl) also live on V2 but carry a
        # `source` and no `graphic` — they are video, not drawn graphics.
        if clip.get("source") or "graphic" not in clip:
            continue
        element = classify_graphic(clip.get("graphic"))
        if not element:
            continue
        # light_sweep_title already owns the 0-2.5s title zone; a storyboard
        # title card there would double-draw on top of it.
        if element == "title_card" and preset_name == "light_sweep_title":
            continue
        start = float(clip.get("at", 0.0) or 0.0)
        duration = float(clip.get("duration", 0.0) or 0.0)
        if duration <= 0:
            duration = max(0.0, float(clip.get("out", 0.0) or 0.0) - float(clip.get("in", 0.0) or 0.0))
        end = min(start + duration, edited_duration)
        start = max(0.0, start)
        if end - start < 0.2 or start >= edited_duration:
            continue

        block = blocks_by_id.get(str(clip.get("block_id", "")), {})
        block_text = _block_text(block)

        if element == "title_card":
            text = _display_title(clip, block, edl_data)
            if not text:
                continue
            events, frags = _title_card(start, end, text, accent, scale)
        elif element == "pill":
            text = _meaningful_title(clip.get("title") or block.get("title")) or block_text
            if not text:
                continue
            events, frags = _pill(start, end, text, accent, scale)
        elif element == "proof_card":
            claim = _meaningful_title(clip.get("title") or block.get("title")) or block_text
            if not claim:
                continue
            label = block_text if claim != block_text else ""
            events, frags = _proof_card(start, end, claim, label, accent, scale)
        elif element == "lower_third":
            name = _meaningful_title(clip.get("title") or block.get("title")) or "Edionic"
            events, frags = _lower_third(start, end, name, block_text, accent, scale)
        elif element == "progress_bar":
            events, frags = _progress_bar(start, end, accent, scale)
        elif element == "shape":
            events, frags = _shape(start, end, accent, scale)
        elif element == "emphasis":
            phrase = " ".join(block_text.split()[:3]) or _meaningful_title(clip.get("title"))
            events, frags = _emphasis(start, end, phrase, accent, scale)
        elif element == "card_sequence":
            cards = clip.get("cards")
            if not isinstance(cards, list) or not cards:
                cards = [{"number": str(i + 1), "label": ""} for i in range(3)]
            events, frags = _card_sequence(start, end, cards, accent, scale)
        elif element == "zoom":
            amount = float(clip.get("amount", 0.12) or 0.12)
            amount = max(0.05, min(0.15, amount))
            zoom_segments.append((start, end, amount))
            events, frags = [], []
        else:  # pragma: no cover - classify_graphic only returns these
            continue

        ass_events.extend(events)
        vf_fragments.extend(frags)
        elements.append({
            "type": element,
            "clip_id": clip.get("id"),
            "start": round(start, 3),
            "end": round(end, 3),
            "graphic": clip.get("graphic"),
        })

    # Template-level watermark (e.g. gaming montage player tag), whole video.
    if edl_data.get("template_watermark") and edited_duration > 0.2:
        wm_text = str(edl_data.get("title_text") or "").strip()
        events, _frags = _watermark(0.0, edited_duration, wm_text)
        ass_events.extend(events)
        if events:
            elements.append({
                "type": "watermark",
                "clip_id": None,
                "start": 0.0,
                "end": round(edited_duration, 3),
                "graphic": "template watermark",
            })

    # Zoom segments combine into a single zoompan fragment. It must run
    # BEFORE the drawbox fragments (graphics stay fixed while the video
    # punches in), so it is returned separately: the pipeline inserts
    # zoom_fragments right after fps=30, ahead of vf_fragments.
    zoom_segments.sort()
    zoom_fragments: List[str] = []
    if zoom_segments:
        zoom_fragments = [_zoom_expression(zoom_segments[:ZOOM_MAX_SEGMENTS], scale)]

    has_graphics = bool(ass_events or vf_fragments or zoom_fragments)
    return {
        "has_graphics": has_graphics,
        "ass_styles": list(GFX_STYLES) if ass_events else [],
        "ass_events": ass_events,
        "vf_fragments": vf_fragments,
        "zoom_fragments": zoom_fragments,
        "elements": elements,
        "summary": {
            "element_count": len(elements),
            "elements": elements,
            "ass_event_count": len(ass_events),
            "vf_fragment_count": len(vf_fragments),
            "zoom_segment_count": len(zoom_segments),
            "zoom_fragment_count": len(zoom_fragments),
        },
    }


def merge_graphics_into_ass(ass_path: str, style_lines: List[str], event_lines: List[str]) -> None:
    """Insert graphics styles into [V4+ Styles] and append graphics events
    to [Events] in an ASS file written by generate_ass_captions.

    Style lines whose name is already present are skipped, so calling this
    twice on the same file does not duplicate styles. Raises ValueError when
    the file has no [V4+ Styles] / [Events] sections.
    """
    with open(ass_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "[V4+ Styles]" not in content or "[Events]" not in content:
        raise ValueError(f"ASS file has no [V4+ Styles]/[Events] sections: {ass_path}")

    lines = content.split("\n")
    existing_names = set()
    last_style_idx = -1
    events_idx = -1
    for idx, line in enumerate(lines):
        if line.strip() == "[Events]":
            events_idx = idx
        if line.startswith("Style:"):
            last_style_idx = idx
            existing_names.add(line.split(",", 1)[0].split(":", 1)[1].strip())

    new_styles = []
    for style_line in style_lines:
        name = style_line.split(",", 1)[0].split(":", 1)[1].strip()
        if name not in existing_names:
            new_styles.append(style_line)

    if new_styles:
        insert_at = last_style_idx + 1 if last_style_idx >= 0 else events_idx
        lines[insert_at:insert_at] = new_styles
        events_idx += len(new_styles)

    if event_lines:
        lines.extend(event_lines)

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
