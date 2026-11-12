"""
Edionic Motion Design Planner — motion_planner.py (Batch 3 extension)

Rules-based planner (no LLM): after transcription, it reads the transcript
(words + timestamps) and produces timed graphic segments in the EDL — V2
clips + storyboard blocks — so EVERY render gets planned motion design,
not only jobs with manually authored storyboard blocks.

User's system spec: upload raw video -> transcribe FIRST -> agent creates
a motion design PLAN (timed animation segments) -> zooms in/out at places
-> captions throughout -> everything planned, then rendered.

Rules (minimum viable, deterministic):
- List/numbered speech ("first/second/third", "one two three", "step 1..4",
  bare digits) in ascending order, 3+ markers -> ONE `card_sequence`
  segment: numbered cards + sweeping path line, each card highlighting
  when the line reaches it.
- Numbers / money words ("100", "$", "million", "revenue", ...) ->
  `proof_card` segments; emphasis words ("best", "only", "free", ...) ->
  `pill` segments. Spaced >= 2s apart, max 5, skipped inside a card
  sequence span and inside the reserved hook zone (first 3s).
- Default: a `title_card` at the hook (first 3s), unless the job already
  carries the template's auto hook card.
- Zooms: subtle push-in over the hook, punch-in over the card sequence,
  punch-in over the first two emphasis segments (max 4, trapezoid
  ease handled by the zoompan expression in graphics.py).

The planner runs ONLY when the job has no manual graphics (see
job_has_manual_graphics): a lone auto hook title card from a template
does not count as manual, so template jobs still get planned segments
on top of their hook card. A locked V2 track is respected by the caller
(the pipeline skips planning entirely when V2 is locked).
"""

import re
from typing import Dict, Any, List, Optional, Tuple

_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4,
    "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
}
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8,
}
_DIGIT_RE = re.compile(r"^(\d{1,2})[.)]?$")
_MONEY_WORDS = {
    "dollar", "dollars", "rupees", "rupee", "crore", "lakh", "million",
    "billion", "thousand", "hundred", "revenue", "profit", "sales",
    "income", "price", "cost", "money", "cash", "salary", "investment",
    "invest", "returns", "roi", "pkr", "usd", "rs",
}
_EMPHASIS_WORDS = {
    "best", "only", "free", "secret", "proven", "biggest", "never",
    "always", "first", "huge", "massive", "exactly", "guaranteed",
    "insane", "crazy", "unbelievable", "incredible", "amazing",
}
_STOP_WORDS = {
    "is", "the", "a", "an", "and", "to", "you", "we", "it", "of", "for",
    "in", "on", "that", "this", "with", "your", "my", "so", "then", "are",
    "was", "were", "be", "as", "at", "by", "from", "or", "but", "if",
    "when", "how", "what", "get", "got", "i", "me", "he", "she", "they",
}

_MAX_CARDS = 5
_MAX_EMPHASIS = 5
_MIN_EMPHASIS_GAP = 2.0
_HOOK_ZONE_END = 3.0
_HOOK_CARD_SPAN = 3.0


def _clean_word(text: str) -> str:
    return re.sub(r"^[^\w$%]+|[^\w%$]+$", "", str(text or "").lower())


def _marker_value(word: str) -> Optional[int]:
    """Numeric value of a list-marker word, or None."""
    cleaned = _clean_word(word)
    if cleaned in _ORDINALS:
        return _ORDINALS[cleaned]
    if cleaned in _NUMBER_WORDS:
        return _NUMBER_WORDS[cleaned]
    match = _DIGIT_RE.match(cleaned)
    if match:
        return int(match.group(1))
    return None


def _find_card_sequence(words: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Find the first run of 3+ list markers with strictly increasing
    values (kills false positives like 'one day ... one thing')."""
    markers: List[Tuple[int, int, float, float]] = []  # (index, value, start, end)
    for idx, w in enumerate(words):
        # "step 1" / "step one": the marker is the number word itself;
        # "step" is transparent and skipped as a label word.
        value = _marker_value(w.get("word", ""))
        if value is not None:
            markers.append((idx, value, float(w.get("start", 0.0)), float(w.get("end", 0.0))))

    run: List[Tuple[int, int, float, float]] = []
    for marker in markers:
        if run and marker[1] <= run[-1][1]:
            # Value did not increase: the run ends here. A qualifying run
            # wins immediately; otherwise start a fresh run at this marker.
            if len(run) >= 3:
                break
            run = [marker]
            continue
        if run and marker[2] - run[-1][3] > 25.0:
            if len(run) >= 3:
                break
            run = [marker]
            continue
        run.append(marker)
    if len(run) < 3:
        return None

    run = run[:_MAX_CARDS]
    cards = []
    for (idx, value, _s, _e) in run:
        label_words = []
        for nxt in words[idx + 1: idx + 5]:
            cleaned = _clean_word(nxt.get("word", ""))
            if _marker_value(nxt.get("word", "")) is not None:
                break
            if cleaned in _STOP_WORDS or not cleaned:
                continue
            label_words.append(str(nxt.get("word", "")).strip())
            if len(label_words) >= 2 or len(" ".join(label_words)) >= 14:
                break
        cards.append({"number": str(value), "label": " ".join(label_words)[:14]})
    start = max(0.0, run[0][2] - 0.2)
    end = run[-1][3] + 2.5
    return {"cards": cards, "start": start, "end": end}


def _find_emphasis(
    words: List[Dict[str, Any]],
    duration: float,
    card_span: Optional[Tuple[float, float]],
    hook_reserved: bool,
) -> List[Dict[str, Any]]:
    """Money/number -> proof_card, emphasis words -> pill. Chronological,
    spaced apart, capped, kept out of the card span and hook zone."""
    found = []
    last_start = -_MIN_EMPHASIS_GAP
    for idx, w in enumerate(words):
        start = float(w.get("start", 0.0))
        end = float(w.get("end", start + 0.3))
        if start - last_start < _MIN_EMPHASIS_GAP:
            continue
        if hook_reserved and start < _HOOK_ZONE_END:
            continue
        if card_span and start >= card_span[0] - 0.5 and start <= card_span[1] + 0.5:
            continue
        raw = str(w.get("word", ""))
        cleaned = _clean_word(raw)
        is_number = bool(re.search(r"\d", raw)) or raw.startswith("$")
        if is_number or cleaned in _MONEY_WORDS:
            lo = max(0, idx - 2)
            hi = min(len(words), idx + 3)
            claim = " ".join(str(x.get("word", "")).strip() for x in words[lo:hi])
            found.append({
                "type": "proof_card", "graphic": "proof card",
                "start": max(0.0, start - 0.3), "end": min(duration, end + 1.5),
                "title": claim, "text": "",
            })
            last_start = start
        elif cleaned in _EMPHASIS_WORDS:
            found.append({
                "type": "pill", "graphic": "pill",
                "start": max(0.0, start - 0.2), "end": min(duration, end + 1.0),
                "title": raw.strip(), "text": raw.strip(),
            })
            last_start = start
        if len(found) >= _MAX_EMPHASIS:
            break
    return [f for f in found if f["end"] - f["start"] >= 0.5]


def _blocks_by_id(edl_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    blocks = {}
    storyboard = edl_data.get("storyboard") or {}
    for block in storyboard.get("blocks") or []:
        if isinstance(block, dict) and block.get("id") is not None:
            blocks[str(block["id"])] = block
    return blocks


def _is_auto_hook_card(clip: Dict[str, Any], blocks: Dict[str, Dict[str, Any]]) -> bool:
    """The template hook block: title 'hook', graphic 'Title card', at 0.
    Auto-generated, not manual authoring — it does not block planning."""
    from graphics import classify_graphic
    if classify_graphic(clip.get("graphic")) != "title_card":
        return False
    if float(clip.get("at", 0.0) or 0.0) > 0.01:
        return False
    block = blocks.get(str(clip.get("block_id", "")), {})
    title = str(clip.get("title") or block.get("title") or "").strip().lower()
    return title == "hook"


def hook_card_present(edl_data: Dict[str, Any]) -> bool:
    """True when a V2 auto hook title card will actually render."""
    blocks = _blocks_by_id(edl_data)
    for track in edl_data.get("tracks") or []:
        if track.get("id") != "V2":
            continue
        for clip in track.get("clips") or []:
            if isinstance(clip, dict) and not clip.get("source") and _is_auto_hook_card(clip, blocks):
                return True
    return False


def _is_generated_clip(clip: Dict[str, Any], blocks: Dict[str, Dict[str, Any]]) -> bool:
    """True when a V2 clip is planner output or a factory placeholder:
    plan-generated ids (v2_plan_*), clips whose storyboard block is a
    factory default, or orphan v2_b<N> clips with placeholder titles.
    Generated clips never count as manual graphics."""
    from graphics import is_factory_default_block, is_plan_generated_id
    if is_plan_generated_id(clip.get("id")):
        return True
    block = blocks.get(str(clip.get("block_id", "")))
    if block is not None:
        return is_factory_default_block(block)
    clip_id = str(clip.get("id") or "")
    if re.match(r"^v2_b\d+$", clip_id, re.IGNORECASE):
        title = str(clip.get("title") or "").strip().lower()
        if title in ("", "b0", "b1", "hook beat", "core value") or re.match(r"^b\d+$", title):
            return True
    return False


def job_has_manual_graphics(edl_data: Dict[str, Any]) -> bool:
    """True when the job carries authored graphics the planner must not
    touch: V2 graphic clips (other than the auto hook card, factory
    placeholders, and previous planner output) or storyboard blocks with
    real graphic values (other than the auto hook block, factory
    placeholders, and previous planner output).

    Factory-default b0/b1 blocks used to make this return True on EVERY
    default-UI render, which silently disabled the planner (Batch 4 fix).
    Plan-generated clips/blocks are likewise ignored: the worker saves
    the mutated EDL after each render, so without this exemption the
    second render on a new video would see stale plan clips as "manual"
    and skip planning with stale timings.
    """
    from graphics import classify_graphic, is_factory_default_block, is_plan_generated_id
    blocks = _blocks_by_id(edl_data)
    for track in edl_data.get("tracks") or []:
        if track.get("id") != "V2":
            continue
        for clip in track.get("clips") or []:
            if not isinstance(clip, dict) or clip.get("source") or "graphic" not in clip:
                continue
            if not classify_graphic(clip.get("graphic")):
                continue
            if _is_auto_hook_card(clip, blocks):
                continue
            if _is_generated_clip(clip, blocks):
                continue
            return True
    for block_id, block in blocks.items():
        graphic = block.get("graphic")
        if graphic and classify_graphic(graphic):
            if str(block.get("title", "")).strip().lower() == "hook":
                continue
            if is_plan_generated_id(block_id) or is_factory_default_block(block):
                continue
            return True
    return False


def strip_generated_graphics(edl_data: Dict[str, Any]) -> int:
    """Remove planner output and factory placeholders from the job, in
    place: V2 clips that are plan-generated or factory-default, and
    storyboard blocks with plan_b* ids or factory-default content.

    Call ONLY on the planning path (after job_has_manual_graphics()
    returns False), so authored graphics are never touched. Without this,
    stale placeholder/plan graphics would render alongside the fresh
    plan, and stale plan timings would survive into the next render's
    saved EDL.
    """
    from graphics import is_factory_default_block, is_plan_generated_id
    removed = 0
    blocks = _blocks_by_id(edl_data)
    for track in edl_data.get("tracks") or []:
        if track.get("id") != "V2":
            continue
        kept = []
        for clip in track.get("clips") or []:
            if isinstance(clip, dict) and "graphic" in clip and not clip.get("source") \
                    and _is_generated_clip(clip, blocks):
                removed += 1
                continue
            kept.append(clip)
        track["clips"] = kept
    storyboard = edl_data.get("storyboard")
    if isinstance(storyboard, dict) and isinstance(storyboard.get("blocks"), list):
        kept_blocks = []
        for block in storyboard["blocks"]:
            if isinstance(block, dict) and (
                is_plan_generated_id(block.get("id")) or is_factory_default_block(block)
            ):
                removed += 1
                continue
            kept_blocks.append(block)
        storyboard["blocks"] = kept_blocks
    return removed


def plan_motion_graphics(
    words: List[Dict[str, Any]],
    edited_duration: float,
    title_text: str = "",
    hook_card_present_flag: bool = False,
) -> Dict[str, Any]:
    """Plan timed graphic segments from the transcript.

    Returns {"segments": [...], "blocks": [...], "clips": [...]}. Segments
    are the visible plan (type/start/end/text); blocks+clips are the EDL
    shapes inject_plan_into_edl() appends to the job.
    """
    duration = max(0.0, float(edited_duration or 0.0))
    words = sorted(
        [w for w in (words or []) if isinstance(w, dict) and w.get("word")],
        key=lambda w: float(w.get("start", 0.0)),
    )
    segments: List[Dict[str, Any]] = []
    blocks: List[Dict[str, Any]] = []
    clips: List[Dict[str, Any]] = []

    def _add_graphic(seg_type: str, graphic: str, start: float, end: float,
                     title: str, text: str, extra: Optional[Dict[str, Any]] = None):
        start = max(0.0, float(start))
        end = min(duration, float(end))
        if end - start < 0.2 or start >= duration:
            return None
        idx = len(blocks)
        block = {
            "id": f"plan_b{idx}",
            "title": title,
            "text": text,
            "start": round(start, 3),
            "end": round(end, 3),
            "visual": "",
            "graphic": graphic,
            "sfx": "",
        }
        clip = {
            "id": f"v2_plan_{idx}",
            "block_id": block["id"],
            "title": title,
            "graphic": graphic,
            "in": 0.0,
            "out": round(end - start, 3),
            "at": round(start, 3),
            "duration": round(end - start, 3),
        }
        if extra:
            clip.update(extra)
        blocks.append(block)
        clips.append(clip)
        segments.append({
            "type": seg_type, "start": round(start, 3), "end": round(end, 3),
            "text": title or text, "graphic": graphic,
        })
        return (start, end)

    hook_reserved = hook_card_present_flag or duration >= 2.0

    # 1. Hook title card (unless the template hook card already renders).
    hook_span = None
    if duration >= 2.0 and not hook_card_present_flag:
        hook_title = (title_text or "").strip()
        if not hook_title or hook_title.lower() in ("b0", "beat 1", "hook"):
            hook_title = " ".join(str(w.get("word", "")) for w in words[:6]).strip()
        hook_span = _add_graphic(
            "title_card", "Title card", 0.0, min(_HOOK_CARD_SPAN, duration),
            hook_title, hook_title,
        )
    elif hook_card_present_flag and duration >= 2.0:
        hook_span = (0.0, min(_HOOK_CARD_SPAN, duration))

    # 2. Card sequence from list/numbered speech.
    card_info = _find_card_sequence(words) if words else None
    card_span = None
    if card_info:
        end = min(duration, max(card_info["end"], card_info["start"] + 2.0))
        card_span = _add_graphic(
            "card_sequence", "card sequence", card_info["start"], end,
            f"{len(card_info['cards'])} steps",
            " ".join(c["label"] for c in card_info["cards"] if c["label"]),
            extra={"cards": card_info["cards"]},
        )

    # 3. Emphasis segments (money/numbers -> proof, emphasis words -> pill).
    emphasis = _find_emphasis(words, duration, card_span, hook_reserved) if words else []
    emphasis_spans = []
    for item in emphasis:
        span = _add_graphic(
            item["type"], item["graphic"], item["start"], item["end"],
            item["title"], item["text"],
        )
        if span:
            emphasis_spans.append(span)

    # 4. Zooms: hook push-in, card-sequence punch, first two emphasis punches.
    zoom_spans: List[Tuple[float, float, float]] = []
    if hook_span and hook_span[1] - hook_span[0] >= 1.0:
        zoom_spans.append((hook_span[0], hook_span[1], 0.08))
    if card_span and card_span[1] - card_span[0] >= 1.0:
        zoom_spans.append((card_span[0], card_span[1], 0.10))
    for span in emphasis_spans[:2]:
        if span[1] - span[0] >= 1.0:
            zoom_spans.append((span[0], span[1], 0.12))
    for (z_start, z_end, amount) in zoom_spans[:4]:
        idx = len(clips)
        clips.append({
            "id": f"v2_plan_zoom_{idx}",
            "graphic": "zoom",
            "amount": amount,
            "in": 0.0,
            "out": round(z_end - z_start, 3),
            "at": round(z_start, 3),
            "duration": round(z_end - z_start, 3),
        })
        segments.append({
            "type": "zoom", "start": round(z_start, 3), "end": round(z_end, 3),
            "text": f"punch-in {int(amount * 100)}%", "graphic": "zoom",
        })

    segments.sort(key=lambda s: s["start"])
    return {"segments": segments, "blocks": blocks, "clips": clips}


# Graphic names the graphics engine classifies (see graphics.py).
_SEGMENT_GRAPHICS = {
    "title_card": "Title card",
    "pill": "pill",
    "proof_card": "proof card",
    "lower_third": "lower-third",
    "progress_bar": "progress bar",
    "shape": "shape",
    "emphasis": "keyword emphasis",
    "card_sequence": "card sequence",
    "zoom": "zoom",
}


def segments_to_plan(segments: List[Dict[str, Any]], duration: float) -> Dict[str, Any]:
    """Convert validated plan segments into the EDL shapes the graphics
    engine renders: storyboard blocks + V2 clips with plan_b*/v2_plan_*
    ids, exactly the shape plan_motion_graphics() produces. The Ollama
    planner feeds validated model output through here so both planners
    share one injection path (and the strip/fallback handling).

    Segments must already be validated (types, times, card payloads).
    Out-of-range or empty segments are skipped defensively; callers that
    need strict all-or-nothing validation must validate BEFORE calling.
    """
    duration = max(0.0, float(duration or 0.0))
    blocks: List[Dict[str, Any]] = []
    clips: List[Dict[str, Any]] = []
    visible: List[Dict[str, Any]] = []

    for seg in segments or []:
        if not isinstance(seg, dict):
            continue
        seg_type = str(seg.get("type") or "")
        graphic = _SEGMENT_GRAPHICS.get(seg_type)
        if not graphic:
            continue
        start = max(0.0, float(seg.get("start", 0.0) or 0.0))
        end = min(duration, float(seg.get("end", 0.0) or 0.0))
        if end - start < 0.2 or start >= duration:
            continue
        if seg_type == "zoom":
            idx = len(clips)
            amount = max(0.05, min(0.15, float(seg.get("amount", 0.10) or 0.10)))
            clips.append({
                "id": f"v2_plan_zoom_{idx}",
                "graphic": "zoom",
                "amount": amount,
                "in": 0.0,
                "out": round(end - start, 3),
                "at": round(start, 3),
                "duration": round(end - start, 3),
            })
            visible.append({
                "type": "zoom", "start": round(start, 3), "end": round(end, 3),
                "text": f"punch-in {int(amount * 100)}%", "graphic": "zoom",
            })
            continue
        text = str(seg.get("text") or "").strip()
        if seg_type == "card_sequence":
            cards = seg.get("cards") or []
            title = f"{len(cards)} steps"
            block_text = " ".join(str(c.get("label", "")).strip() for c in cards if isinstance(c, dict))
        else:
            title = text
            block_text = text
        idx = len(blocks)
        block = {
            "id": f"plan_b{idx}",
            "title": title,
            "text": block_text,
            "start": round(start, 3),
            "end": round(end, 3),
            "visual": "",
            "graphic": graphic,
            "sfx": "",
        }
        clip = {
            "id": f"v2_plan_{idx}",
            "block_id": block["id"],
            "title": title,
            "graphic": graphic,
            "in": 0.0,
            "out": round(end - start, 3),
            "at": round(start, 3),
            "duration": round(end - start, 3),
        }
        if seg_type == "card_sequence":
            clip["cards"] = seg["cards"]
        blocks.append(block)
        clips.append(clip)
        visible.append({
            "type": seg_type, "start": round(start, 3), "end": round(end, 3),
            "text": title or text, "graphic": graphic,
        })

    visible.sort(key=lambda s: s["start"])
    return {"segments": visible, "blocks": blocks, "clips": clips}


def inject_plan_into_edl(edl_data: Dict[str, Any], plan: Dict[str, Any]) -> None:
    """Append planned blocks + V2 clips to the job (in place)."""
    if plan.get("blocks"):
        storyboard = edl_data.get("storyboard")
        if not isinstance(storyboard, dict):
            storyboard = {"blocks": []}
            edl_data["storyboard"] = storyboard
        storyboard.setdefault("blocks", []).extend(plan["blocks"])
    if plan.get("clips"):
        tracks = edl_data.get("tracks") or []
        v2 = next((t for t in tracks if isinstance(t, dict) and t.get("id") == "V2"), None)
        if v2 is None:
            v2 = {"id": "V2", "name": "V2 Overlay", "type": "overlay",
                  "locked": False, "clips": []}
            tracks.append(v2)
            edl_data["tracks"] = tracks
        v2.setdefault("clips", []).extend(plan["clips"])
