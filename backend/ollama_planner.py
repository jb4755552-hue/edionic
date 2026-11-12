"""
Edionic Ollama LLM Planner — ollama_planner.py (Batch 4)

Puts a real model behind the motion design plan: transcript (+ word
timestamps) -> local Ollama model -> motion-plan JSON -> strict
validation -> the SAME injection path as the rules planner (V2 clips +
storyboard blocks via motion_planner.segments_to_plan), so the graphics
engine, the placeholder strip, and the stale-plan handling all apply
identically.

The rules-based planner stays as FALLBACK: when Ollama is unreachable,
returns invalid JSON, or times out, the render falls back to rules and
NEVER fails because the model is down. The render info reports which
planner ran ({planner: "ollama"|"rules", model, ...}) so it stays
visible whether the model planned the video.

Configuration uses the SAME env var names brain_router.py uses, read at
call time (per render) so tests and runtime config can change them
without restarting the server:
- EDIONIC_OLLAMA_URL (default http://127.0.0.1:11434)
- EDIONIC_OLLAMA_MODEL (default llama3.2:3b — the router's default;
  qwen2.5:7b works too if the PC has the RAM and the model pulled)
- EDIONIC_OLLAMA_ENABLED (default "1"; "0"/"false"/"no"/"off" disables)
- EDIONIC_OLLAMA_TIMEOUT (default 180 seconds; warm 3b latency on
  slow CPUs runs 50-80s, so the old 60s default timed out good plans)

No new dependencies: urllib only. The model is expected to run locally
on the user's PC (Ollama + a pulled model); without it, renders use the
rules planner exactly as before.
"""

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

_ALLOWED_TYPES = {
    "title_card", "pill", "proof_card", "lower_third", "progress_bar",
    "shape", "emphasis", "card_sequence", "zoom", "keyword_pop",
}
_TEXT_REQUIRED = {"title_card", "pill", "proof_card", "lower_third", "emphasis", "keyword_pop"}
_MAX_SEGMENTS = 6
_MAX_KEYWORD_POPS = 40
_POP_MAX_LEN = 2.5
_POP_COLORS = {"neutral", "bad", "good", "key"}
# In keyword-punch mode only these types may render: pops own the frame,
# everything else is gap-only support. title_card/lower_third/
# progress_bar/emphasis are dropped (the prompt forbids them there).
_KEYWORD_PUNCH_ALLOWED = {
    "keyword_pop", "pill", "proof_card", "card_sequence", "shape", "zoom",
}
_MAX_TEXT_LEN = 60
_MAX_LABEL_LEN = 16
_MAX_TRANSCRIPT_WORDS = 500

_FALLBACK_TEMPLATE_IDS = [
    "saas_dark_premium", "saas_clean_flat", "talking_head_pro",
    "trust_talking_head", "split_screen_breakdown", "screen_record_tutorial",
    "archival_documentary", "portfolio_showreel", "ai_showcase_desk",
    "local_language_demo", "gaming_montage", "devin_keyword_punch",
]
_FALLBACK_STYLE_IDS = [
    "smoke2_style", "vox_explainer_style", "neon_aura_style",
    "learned_from_sample", "warm_canvas_style",
    "creator_motion_graphics_style", "clean_tech_style",
    "software_walkthrough_style", "data_story_style", "chalk_talk_style",
    "pop_info_style",
]

_ELEMENT_HELP = """\
title_card: big hook title band, first 3 seconds only.
pill: short accent pill showing ONE emphasis word.
proof_card: card showing a number or money claim.
lower_third: name + role band for introducing a person.
progress_bar: thin progress line at the top of the frame.
shape: small rotating accent diamond, decorative.
emphasis: kinetic pop of a key phrase, mid-frame.
card_sequence: numbered cards 1..N in a row with a line sweeping across them, each card highlighting when the line hits it. Use ONLY for list/steps speech (first/second/third, step 1/2/3).
zoom: punch-in on the speaker, no text. Use sparingly (hook + big moments)."""

# Keyword-punch element help: ONLY shown to the model in keyword_punch
# mode, so normal-mode plans never contain keyword_pop segments.
_KEYWORD_POP_HELP = """\
keyword_pop: HUGE mid-frame keyword punch, 1-3 words, the ONLY text on screen. Replaces captions entirely. Each pop has a "color": "neutral" (white, plain words), "bad" (bright red, bad/old/negative phrases), "good" (bright green, good/new power words, numbers, money), "key" (bright blue, THE key term of the video)."""

_EXAMPLE = """\
{"template_id": "talking_head_pro", "style_preset": "smoke2_style", "segments": [
 {"type": "title_card", "start_s": 0.0, "end_s": 3.0, "text": "EXAMPLE WORDS"},
 {"type": "card_sequence", "start_s": 3.7, "end_s": 11.5, "cards": [{"number": "1", "label": "example one"}, {"number": "2", "label": "example two"}, {"number": "3", "label": "example three"}, {"number": "4", "label": "example four"}]},
 {"type": "zoom", "start_s": 3.7, "end_s": 11.5, "amount": 0.1},
 {"type": "proof_card", "start_s": 13.0, "end_s": 15.5, "text": "EXAMPLE NUMBER"}
]}"""

_EXAMPLE_KEYWORD_PUNCH = """\
{"template_id": "devin_keyword_punch", "style_preset": "creator_motion_graphics_style", "segments": [
 {"type": "keyword_pop", "start_s": 0.0, "end_s": 1.4, "text": "EXAMPLE HOOK", "color": "key"},
 {"type": "keyword_pop", "start_s": 1.6, "end_s": 3.0, "text": "EXAMPLE OLD WAY", "color": "bad"},
 {"type": "keyword_pop", "start_s": 3.2, "end_s": 4.6, "text": "EXAMPLE NEW WAY", "color": "good"},
 {"type": "zoom", "start_s": 0.0, "end_s": 3.0, "amount": 0.12},
 {"type": "proof_card", "start_s": 5.0, "end_s": 7.0, "text": "EXAMPLE NUMBER"}
]}"""


def _norm_token(token: str) -> str:
    """Lowercase, strip surrounding punctuation; internal dots/digits stay."""
    return re.sub(r"^[^\w$%]+|[^\w%$]+$", "", str(token or "").lower())


def _transcript_tokens(words: List[Dict[str, Any]]) -> List[str]:
    tokens = [_norm_token(w.get("word", "")) for w in (words or [])]
    return [t for t in tokens if t]


_MAGNITUDE_WORDS = {"k": "thousand", "m": "million", "b": "billion"}


def _token_matches(text_token: str, transcript_token: str) -> bool:
    """One token equal after normalization, or numerically equal
    ignoring currency/magnitude letters ("$5" == "5", "1.2m" == "1.2")."""
    if text_token == transcript_token:
        return True
    if not any(c.isdigit() for c in text_token):
        return False
    num_a = re.sub(r"[^\d.]", "", text_token)
    num_b = re.sub(r"[^\d.]", "", transcript_token)
    return bool(num_a) and num_a == num_b


def _is_grounded(text: str, transcript_tokens: List[str]) -> bool:
    """True when `text` appears as a contiguous word sequence in the
    transcript (case-insensitive, punctuation ignored). Magnitude
    shorthands expand first ("1.2m" -> "1.2 million") so proof numbers
    spoken as words still ground. Kills hallucinated card labels, pill
    text, proof text and keywords that the speaker never said."""
    text_tokens: List[str] = []
    for raw in str(text or "").split():
        token = _norm_token(raw)
        if not token:
            continue
        match = re.match(r"^(\d+(?:\.\d+)?)([kmb])$", token)
        if match:
            text_tokens.append(match.group(1))
            text_tokens.append(_MAGNITUDE_WORDS[match.group(2)])
        else:
            text_tokens.append(token)
    if not text_tokens or not transcript_tokens:
        return False
    width = len(text_tokens)
    for i in range(len(transcript_tokens) - width + 1):
        if all(_token_matches(t, transcript_tokens[i + j])
               for j, t in enumerate(text_tokens)):
            return True
    return False


def _ollama_config() -> Dict[str, Any]:
    enabled_raw = str(os.environ.get("EDIONIC_OLLAMA_ENABLED", "1")).strip().lower()
    try:
        timeout = float(os.environ.get("EDIONIC_OLLAMA_TIMEOUT", "180"))
    except ValueError:
        timeout = 60.0
    return {
        "enabled": enabled_raw not in ("0", "false", "no", "off"),
        "url": str(os.environ.get("EDIONIC_OLLAMA_URL", "http://127.0.0.1:11434")).strip().rstrip("/"),
        "model": str(os.environ.get("EDIONIC_OLLAMA_MODEL", "llama3.2:3b")).strip() or "llama3.2:3b",
        "timeout": min(300.0, max(5.0, timeout)),
    }


def _catalogs() -> Tuple[List[str], List[str]]:
    """Template + style ids from the live catalogs, with static fallbacks
    so a catalog import failure can never break the planner."""
    template_ids = list(_FALLBACK_TEMPLATE_IDS)
    try:
        from templates import TEMPLATE_CATALOG
        live = [str(t.get("id")) for t in TEMPLATE_CATALOG if t.get("id")]
        if live:
            template_ids = live
    except Exception:
        pass
    style_ids = list(_FALLBACK_STYLE_IDS)
    try:
        from learn_style import list_style_library
        live_styles = list_style_library()
        names = [str(s.get("id") or s.get("style_id") or s) for s in live_styles]
        names = [n for n in names if n and n != "None"]
        if names:
            style_ids = names
    except Exception:
        pass
    return template_ids, style_ids


def _compact_transcript(words: List[Dict[str, Any]]) -> str:
    """Words with timestamps, compact enough for a small local model."""
    parts = []
    for w in (words or [])[:_MAX_TRANSCRIPT_WORDS]:
        text = str(w.get("word", "")).strip()
        if not text:
            continue
        parts.append(f"{text}({float(w.get('start', 0.0)):.1f})")
    return " ".join(parts)


def _build_prompt(transcript: str, duration: float, title_text: str,
                  hook_card_present: bool, template_id: Optional[str],
                  style_preset: Optional[str],
                  template_ids: List[str], style_ids: List[str],
                  keyword_punch: bool = False) -> Tuple[str, str]:
    element_help = _ELEMENT_HELP
    if keyword_punch:
        element_help += "\n" + _KEYWORD_POP_HELP
    rules = (
        "- At most 6 segments. Times in seconds, within the video duration.\n"
        if not keyword_punch else
        "- At most 6 graphic segments + up to 40 keyword_pop segments. "
        "Times in seconds, within the video duration.\n"
    )
    rules += (
        "- At most ONE card_sequence — merge ALL list/steps speech into that\n"
        "  one sequence, never emit two — and NO other drawn segment may\n"
        "  overlap it (zoom may overlap it): place pills/proof cards before\n"
        "  it starts or after it ends.\n"
        "- NEVER emit card_sequence unless the speaker literally lists steps\n"
        "  (first/second/third, step 1/2/3, one/two/three in ascending\n"
        "  order). A topic the speaker does NOT list as steps gets NO\n"
        "  card_sequence — never force cards onto non-list speech.\n"
        "- pill/proof_card ONLY for genuine number/money/emphasis moments\n"
        "  spoken in the transcript. Graphics only where needed.\n"
    )
    if keyword_punch:
        rules += (
            "- KEYWORD PUNCH MODE: NO title_card at all — the first\n"
            "  keyword_pop IS the hook and must start within the first\n"
            "  second. Emit ONLY keyword_pop, zoom, and (sparingly, in\n"
            "  gaps) proof_card/pill/card_sequence. NO title_card, NO\n"
            "  lower_third, NO progress_bar, NO emphasis.\n"
            "- Emit one keyword_pop per ~1-3 second beat covering the\n"
            "  WHOLE video: the salient 1-3 word phrase spoken in that\n"
            "  beat (emphasis words, numbers, contrast pairs, topic\n"
            "  terms). 1-3 words ONLY, timed ON the spoken words,\n"
            "  0.5-2.5s each. Pops must NEVER overlap each other.\n"
            "- Every keyword_pop needs a color: neutral/bad/good/key\n"
            "  (see element help). White for plain words, red for\n"
            "  bad/old phrases, green for good/new power words and\n"
            "  numbers, blue for THE key term of the video.\n"
            "- NO drawn segment may overlap a keyword_pop window (zoom\n"
            "  may): proof cards/pills go ONLY in gaps between pops, or\n"
            "  are skipped. ONE text on screen at a time.\n"
        )
    else:
        rules += (
            "- A hook title_card starting at 0.0 is REQUIRED unless one already renders.\n"
        )
    rules += (
        "- Keep text short, uppercase-friendly, taken from the spoken words.\n"
        "- Use ONLY words and numbers from the transcript; never copy text "
        "from this example.\n"
        "- card_sequence cards: 2-5 cards, each with number + short label from the spoken list.\n"
        "- template_id MUST be copied exactly from the TEMPLATES list below. "
        "It is a template name, NEVER an element type (never \"title_card\", "
        "\"card_sequence\", \"pill\", etc.). If unsure, copy the Current "
        "template value from the video details. Same for style_preset: copy "
        "exactly from the STYLES list, never invent one.\n\n"
        "TEMPLATES: " + ", ".join(template_ids) + "\n"
        "STYLES: " + ", ".join(style_ids) + "\n\n"
        "EXAMPLE:\n" + (_EXAMPLE_KEYWORD_PUNCH if keyword_punch else _EXAMPLE)
    )
    system = (
        "You are the motion design planner for Edionic, a 9:16 vertical "
        "short-form video editor. Given a transcript with word timestamps, "
        "plan timed motion graphics. Reply with ONE JSON object only, no "
        "markdown, no explanation.\n\n"
        "ELEMENT TYPES:\n" + element_help + "\n\n"
        "RULES:\n" + rules
    )
    if keyword_punch:
        hook_note = (
            "KEYWORD PUNCH MODE: no title card — the first keyword_pop is "
            "the hook and must start within the first second. Cover the "
            "whole video with keyword pops, one per beat."
        )
    else:
        hook_note = (
            "A hook title card already renders for the first 3 seconds; do NOT add another title_card."
            if hook_card_present else
            "No hook title card renders yet; the plan MUST start with a title_card at 0.0."
        )
    user = (
        f"Video duration: {duration:.1f} seconds.\n"
        f"Video title: {title_text or '(none)'}\n"
        f"Current template: {template_id or '(none)'}; current style: {style_preset or '(none)'}.\n"
        f"{hook_note}\n\n"
        f"TRANSCRIPT (word(seconds)):\n{transcript}\n\n"
        "Reply with the JSON plan object only."
    )
    return system, user


def _parse_model_json(content: str) -> Any:
    """Parse the model's reply, tolerating markdown fences defensively."""
    text = str(content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    return json.loads(text)


def _sanitize_text(value: Any, max_len: int) -> str:
    return " ".join(str(value or "").split())[:max_len].strip()


def _overlaps(span_a: Tuple[float, float], span_b: Tuple[float, float]) -> bool:
    return span_a[0] < span_b[1] and span_a[1] > span_b[0]


def _truncate_segments(raw_segments: List[Any]) -> List[Any]:
    """Keep at most _MAX_SEGMENTS, protecting the hook title_card and the
    card_sequence; drop lowest-priority extras first (shape, then extra
    pills, then the latest segments). Survivor order is preserved."""
    if len(raw_segments) <= _MAX_SEGMENTS:
        return list(raw_segments)
    protected = set()
    for i, seg in enumerate(raw_segments):
        if not isinstance(seg, dict):
            continue
        seg_type = str(seg.get("type") or "")
        if seg_type == "card_sequence":
            if not any(isinstance(raw_segments[j], dict)
                       and str(raw_segments[j].get("type") or "") == "card_sequence"
                       for j in protected):
                protected.add(i)
        elif seg_type == "title_card":
            start = seg.get("start_s")
            if isinstance(start, (int, float)) and not isinstance(start, bool) \
                    and float(start) <= 0.5 and not any(
                        isinstance(raw_segments[j], dict)
                        and str(raw_segments[j].get("type") or "") == "title_card"
                        and isinstance(raw_segments[j].get("start_s"), (int, float))
                        and not isinstance(raw_segments[j].get("start_s"), bool)
                        and float(raw_segments[j].get("start_s")) <= 0.5
                        for j in protected):
                protected.add(i)
    seen_pill = False
    ranked = []
    for i, seg in enumerate(raw_segments):
        if i in protected:
            continue
        seg_type = str(seg.get("type") or "") if isinstance(seg, dict) else ""
        if seg_type == "shape":
            rank = 3
        elif seg_type == "pill":
            if not seen_pill:
                rank = 1
                seen_pill = True
            else:
                rank = 2
        else:
            rank = 0
        ranked.append((rank, i))
    slots = _MAX_SEGMENTS - len(protected)
    ranked.sort()
    keep = set(protected) | {i for _, i in ranked[:max(0, slots)]}
    return [seg for i, seg in enumerate(raw_segments) if i in keep]


def _validate_plan(payload: Any, duration: float, hook_card_present: bool,
                   template_ids: List[str], style_ids: List[str],
                   keyword_punch: bool = False,
                   words: Optional[List[Dict[str, Any]]] = None) -> Tuple[Optional[List[Dict[str, Any]]], str, Dict[str, Any]]:
    """Repair-then-validate. Mechanical violations are REPAIRED and recorded
    in meta["repaired"]: too many segments are truncated (hook title_card +
    card_sequence protected, shape / extra pills dropped first), times are
    clamped into [0, duration], sub-0.5s segments are extended to 0.5s (or
    dropped when the extension would overlap the card_sequence span or
    cannot fit), extra card_sequences are dropped (first kept), and a drawn
    segment overlapping the card_sequence span is trimmed to end before it
    starts / start after it ends (or dropped when <0.5s would remain).
    Only STRUCTURAL problems still reject the whole plan: unknown element
    type, missing text on text-bearing types, malformed card payloads,
    missing hook title. The suggested template_id / style_preset are
    advisory only (never applied), so an unknown or missing suggestion is
    recorded in meta as ignored and never rejects the plan.

    Batch 5: in keyword_punch mode, keyword_pop segments get their own cap
    (40, separate from the 6-graphic cap), 1-3 words, 0.5-2.5s, their own
    color role, no pop-pop overlap, and pops WIN over any drawn segment
    overlapping their window (trimmed into a gap or dropped); the hook
    title requirement is waived (the first pop IS the hook) and replaced
    by a >=1 keyword_pop requirement; title_card/lower_third/
    progress_bar/emphasis are dropped. In normal mode keyword_pop
    segments are dropped (they only render with the keyword_punch
    preset). GROUNDING (both modes, when `words` is given): pill text,
    proof text, card labels and keyword text must appear as contiguous
    word sequences in the transcript — ungrounded text is dropped, so
    hallucinated cards and wrong-word graphics can never render.
    Title cards / lower-thirds / emphasis are exempt: hook titles are
    summaries, not quotes."""
    if not isinstance(payload, dict):
        return None, "model reply is not a JSON object", {}
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        return None, "plan has no segments list", {}
    duration = float(duration)
    transcript_tokens = _transcript_tokens(words) if words else []
    if not transcript_tokens:
        transcript_tokens = None  # no transcript: grounding skipped, never blocks

    meta: Dict[str, Any] = {}
    # The suggestions are advisory only and NEVER applied (the job's own
    # template/style win), so an unknown or missing suggestion must never
    # discard an otherwise good plan — record it as ignored instead.
    suggested_template = payload.get("template_id")
    if suggested_template is not None:
        if str(suggested_template) in template_ids:
            meta["suggested_template_id"] = str(suggested_template)
        else:
            meta["suggested_template_id"] = None
            meta["suggested_template_invalid"] = str(suggested_template)
    suggested_style = payload.get("style_preset")
    if suggested_style is not None:
        if str(suggested_style) in style_ids:
            meta["suggested_style_preset"] = str(suggested_style)
        else:
            meta["suggested_style_preset"] = None
            meta["suggested_style_invalid"] = str(suggested_style)

    repaired: List[str] = []
    if keyword_punch:
        # Pops get their own cap (40), separate from the 6-graphic cap:
        # a 30s video needs ~15 pops, and capping them at 6 would gut
        # the style. Graphics still truncate by the existing ranking.
        pop_raw = [s for s in raw_segments
                   if isinstance(s, dict) and str(s.get("type") or "") == "keyword_pop"]
        other_raw = [s for s in raw_segments
                     if not (isinstance(s, dict) and str(s.get("type") or "") == "keyword_pop")]
        kept_raw = _truncate_segments(other_raw)
        if len(kept_raw) < len(other_raw):
            repaired.append(
                f"truncated {len(other_raw)} graphic segments to {len(kept_raw)} "
                "(kept hook title + card_sequence, dropped shape/extra pills first)")
        if len(pop_raw) > _MAX_KEYWORD_POPS:
            repaired.append(
                f"truncated {len(pop_raw)} keyword pops to {_MAX_KEYWORD_POPS}")
            pop_raw = pop_raw[:_MAX_KEYWORD_POPS]
        kept_raw = kept_raw + pop_raw
    else:
        kept_raw = _truncate_segments(raw_segments)
        if len(kept_raw) < len(raw_segments):
            repaired.append(
                f"truncated {len(raw_segments)} segments to {len(kept_raw)} "
                "(kept hook title + card_sequence, dropped shape/extra pills first)")

    # >1 card_sequence is a repair, not a rejection: the 3b model often
    # emits one sequence per list item. Keep the FIRST, drop the rest —
    # the kept one still carries the list, and a second sequence would
    # collide with it visually anyway.
    _seen_card_seq = False
    deduped_raw: List[Any] = []
    for seg in kept_raw:
        if isinstance(seg, dict) and str(seg.get("type") or "") == "card_sequence":
            if _seen_card_seq:
                repaired.append("dropped an extra card_sequence (kept the first)")
                continue
            _seen_card_seq = True
        deduped_raw.append(seg)
    kept_raw = deduped_raw

    card_count = sum(
        1 for seg in kept_raw
        if isinstance(seg, dict) and str(seg.get("type") or "") == "card_sequence")
    if card_count > 1:
        return None, "plan has more than one card_sequence", {}

    # Card span from the raw card_sequence (clamped), so extending a short
    # segment can avoid creating an overlap with it.
    card_span: Optional[Tuple[float, float]] = None
    for seg in kept_raw:
        if isinstance(seg, dict) and str(seg.get("type") or "") == "card_sequence":
            s, e = seg.get("start_s"), seg.get("end_s")
            if isinstance(s, (int, float)) and isinstance(e, (int, float)) \
                    and not isinstance(s, bool) and not isinstance(e, bool):
                cs, ce = max(0.0, float(s)), min(duration, float(e))
                if cs < ce:
                    card_span = (cs, ce)
            break

    segments: List[Dict[str, Any]] = []
    has_hook_title = False
    for idx, raw in enumerate(kept_raw):
        if not isinstance(raw, dict):
            return None, f"segment {idx} is not an object", {}
        seg_type = str(raw.get("type") or "").strip()
        if seg_type not in _ALLOWED_TYPES:
            return None, f"segment {idx} has unknown type: {seg_type!r}", {}
        if seg_type == "keyword_pop" and not keyword_punch:
            repaired.append(
                f"dropped segment {idx} (keyword_pop): pops only render in keyword_punch mode")
            continue
        if keyword_punch and seg_type not in _KEYWORD_PUNCH_ALLOWED:
            repaired.append(
                f"dropped segment {idx} ({seg_type}): not allowed in keyword_punch mode")
            continue
        start = raw.get("start_s")
        end = raw.get("end_s")
        if isinstance(start, bool) or isinstance(end, bool) \
                or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            return None, f"segment {idx} has non-numeric times", {}
        start = max(0.0, float(start))
        end = min(duration, float(end))
        if start != float(raw["start_s"]) or end != float(raw["end_s"]):
            repaired.append(
                f"clamped segment {idx} ({seg_type}) times to "
                f"[{start:.1f}, {end:.1f}] (duration {duration:.1f})")
        if start >= end:
            repaired.append(
                f"dropped segment {idx} ({seg_type}) with empty times after clamping")
            if seg_type == "card_sequence":
                card_span = None
            continue
        if end - start < 0.5:
            # Repair: extend to 0.5s, but never create an overlap with the
            # card_sequence span — drop instead if it cannot fit cleanly.
            new_start, new_end = start, min(start + 0.5, duration)
            if new_end - new_start < 0.5:
                new_start = max(new_end - 0.5, 0.0)
                new_end = new_start + 0.5
            if seg_type not in ("zoom", "card_sequence") and card_span is not None \
                    and _overlaps((new_start, new_end), card_span):
                repaired.append(
                    f"dropped segment {idx} ({seg_type}) too short to extend "
                    "without overlapping the card_sequence")
                continue
            if new_end - new_start < 0.5 or new_end > duration or new_start < 0.0:
                repaired.append(
                    f"dropped segment {idx} ({seg_type}) too short to fit in the video")
                continue
            repaired.append(
                f"extended segment {idx} ({seg_type}) to 0.5s "
                f"[{new_start:.1f}, {new_end:.1f}]")
            start, end = new_start, new_end
        if seg_type == "keyword_pop" and end - start > _POP_MAX_LEN:
            repaired.append(
                f"clamped segment {idx} (keyword_pop) to {_POP_MAX_LEN}s "
                f"[{start:.1f}, {start + _POP_MAX_LEN:.1f}]")
            end = start + _POP_MAX_LEN

        seg: Dict[str, Any] = {"type": seg_type, "start": round(start, 3), "end": round(end, 3)}
        if seg_type in _TEXT_REQUIRED:
            text = _sanitize_text(raw.get("text"), _MAX_TEXT_LEN)
            if not text:
                return None, f"segment {idx} ({seg_type}) has no text", {}
            seg["text"] = text
        if seg_type == "keyword_pop":
            pop_words = seg["text"].split()
            if len(pop_words) > 3:
                seg["text"] = " ".join(pop_words[:3])
                repaired.append(
                    f"trimmed segment {idx} (keyword_pop) text to 3 words: {seg['text']!r}")
            color = str(raw.get("color") or "neutral").strip().lower()
            seg["color"] = color if color in _POP_COLORS else "neutral"
        if seg_type == "title_card" and start <= 0.5:
            has_hook_title = True
        if seg_type == "card_sequence":
            cards_raw = raw.get("cards")
            if not isinstance(cards_raw, list) or not 2 <= len(cards_raw) <= 5:
                return None, "card_sequence needs 2-5 cards", {}
            cards = []
            for card in cards_raw:
                if not isinstance(card, dict):
                    return None, "card_sequence card is not an object", {}
                number = _sanitize_text(card.get("number"), 2)
                label = _sanitize_text(card.get("label"), _MAX_LABEL_LEN)
                if not number or not label:
                    return None, "card_sequence card needs number + label", {}
                cards.append({"number": number, "label": label})
            seg["cards"] = cards
        if seg_type == "zoom":
            amount = raw.get("amount", 0.10)
            if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                return None, "zoom amount is not numeric", {}
            seg["amount"] = max(0.05, min(0.15, float(amount)))
        if transcript_tokens is not None:
            # Grounding: pill/proof/card-label/keyword text must be words
            # the speaker actually said, in order. Ungrounded text is
            # dropped (repair), never rendered — a hallucinated pop must
            # not kill the 15 good ones around it.
            if seg_type in ("pill", "proof_card"):
                if not _is_grounded(seg["text"], transcript_tokens):
                    repaired.append(
                        f"dropped ungrounded {seg_type} text: {seg['text']!r}")
                    continue
            elif seg_type == "card_sequence":
                grounded_cards = [
                    c for c in seg["cards"]
                    if _is_grounded(c["label"], transcript_tokens)]
                if len(grounded_cards) < len(seg["cards"]):
                    repaired.append(
                        f"dropped {len(seg['cards']) - len(grounded_cards)} "
                        "ungrounded card label(s)")
                if len(grounded_cards) < 2:
                    repaired.append(
                        "dropped card_sequence with fewer than 2 grounded labels")
                    continue
                seg["cards"] = grounded_cards
            elif seg_type == "keyword_pop":
                if not _is_grounded(seg["text"], transcript_tokens):
                    repaired.append(
                        f"dropped ungrounded keyword_pop: {seg['text']!r}")
                    continue
        segments.append(seg)

    if not segments:
        return None, "plan has no usable segments after repair", {}

    # Drawn overlap with the card_sequence span is a repair, not a
    # rejection: the card sequence is the anchor (it owns the graphics
    # band y 995-1230), so an overlapping drawn segment is trimmed to
    # end before the span starts / start after it ends, or dropped when
    # less than 0.5s would remain. Zoom is a video effect, not a drawn
    # graphic: a punch-in over the card span is intended (the rules
    # planner does the same) and cannot collide visually.
    final_span: Optional[Tuple[float, float]] = None
    for seg in segments:
        if seg["type"] == "card_sequence":
            final_span = (seg["start"], seg["end"])
            break
    if final_span is not None:
        kept_segments: List[Dict[str, Any]] = []
        for seg in segments:
            if seg["type"] in ("card_sequence", "zoom") \
                    or not _overlaps((seg["start"], seg["end"]), final_span):
                kept_segments.append(seg)
                continue
            cs, ce = final_span
            before = cs - seg["start"]
            after = seg["end"] - ce
            if before >= 0.5:
                # Prefer trimming the end: it preserves a start-anchored
                # segment (e.g. a hook title_card at 0.0 stays a hook).
                repaired.append(
                    f"trimmed segment ({seg['type']}) to end at "
                    f"card_sequence start [{seg['start']:.1f}, {cs:.1f}]")
                seg["end"] = round(cs, 3)
                kept_segments.append(seg)
            elif after >= 0.5:
                repaired.append(
                    f"trimmed segment ({seg['type']}) to start at "
                    f"card_sequence end [{ce:.1f}, {seg['end']:.1f}]")
                seg["start"] = round(ce, 3)
                if seg["type"] == "title_card":
                    # It no longer starts at 0.0, so it is not a hook.
                    has_hook_title = False
                kept_segments.append(seg)
            else:
                repaired.append(
                    f"dropped segment ({seg['type']}) overlapping the "
                    "card_sequence span with <0.5s trimmable on either side")
                if seg["type"] == "title_card":
                    has_hook_title = False
        segments = kept_segments
        if not segments:
            return None, "plan has no usable segments after repair", {}
    if keyword_punch:
        # Pops never overlap each other: shift a pop's start to the
        # previous pop's end, or drop it when <0.5s would remain. Then
        # pops WIN over any drawn segment overlapping their window: the
        # segment is trimmed into a gap (end before the first overlapping
        # pop, or start after the last) or dropped. Zoom is a video
        # effect, not a drawn graphic, and is exempt — a punch-in under
        # a pop is intended.
        segments.sort(key=lambda s: s["start"])
        deoverlapped: List[Dict[str, Any]] = []
        prev_pop_end = 0.0
        for seg in segments:
            if seg["type"] != "keyword_pop":
                deoverlapped.append(seg)
                continue
            if seg["start"] < prev_pop_end:
                if seg["end"] - prev_pop_end < 0.5:
                    repaired.append(
                        f"dropped keyword_pop {seg['text']!r} overlapping the previous pop")
                    continue
                repaired.append(
                    f"shifted keyword_pop {seg['text']!r} to start at {prev_pop_end:.1f}")
                seg["start"] = round(prev_pop_end, 3)
            prev_pop_end = seg["end"]
            deoverlapped.append(seg)
        segments = deoverlapped
        pop_windows = [(s["start"], s["end"]) for s in segments if s["type"] == "keyword_pop"]
        if pop_windows:
            kept_pop: List[Dict[str, Any]] = []
            for seg in segments:
                if seg["type"] in ("keyword_pop", "zoom") or not any(
                        _overlaps((seg["start"], seg["end"]), w) for w in pop_windows):
                    kept_pop.append(seg)
                    continue
                overlapping = [w for w in pop_windows
                               if _overlaps((seg["start"], seg["end"]), w)]
                first_start = min(w[0] for w in overlapping)
                last_end = max(w[1] for w in overlapping)
                if first_start - seg["start"] >= 0.5:
                    repaired.append(
                        f"trimmed segment ({seg['type']}) to end before a "
                        f"keyword_pop [{seg['start']:.1f}, {first_start:.1f}]")
                    seg["end"] = round(first_start, 3)
                    kept_pop.append(seg)
                elif seg["end"] - last_end >= 0.5:
                    repaired.append(
                        f"trimmed segment ({seg['type']}) to start after a "
                        f"keyword_pop [{last_end:.1f}, {seg['end']:.1f}]")
                    seg["start"] = round(last_end, 3)
                    kept_pop.append(seg)
                else:
                    repaired.append(
                        f"dropped segment ({seg['type']}) overlapping "
                        "keyword_pop windows with <0.5s trimmable on either side")
            segments = kept_pop
        if not segments:
            return None, "plan has no usable segments after repair", {}
        if not any(s["type"] == "keyword_pop" for s in segments):
            return None, "keyword_punch plan has no keyword_pop segments", {}
    elif not hook_card_present and not has_hook_title:
        return None, "plan has no hook title_card starting at 0.0", {}

    segments.sort(key=lambda s: s["start"])
    if repaired:
        meta["repaired"] = repaired
    return segments, "", meta


def plan_with_ollama(
    words: List[Dict[str, Any]],
    duration: float,
    title_text: str = "",
    hook_card_present_flag: bool = False,
    template_id: Optional[str] = None,
    style_preset: Optional[str] = None,
    keyword_punch: bool = False,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Ask the local Ollama model for a motion plan.

    Returns (plan, info). plan is None on ANY failure (disabled, empty
    transcript, unreachable, timeout, bad JSON, validation failure) and
    info carries the fallback reason; the caller then uses the rules
    planner. This function never raises. With keyword_punch (Batch 5)
    the model plans keyword pops + restraint instead of the default
    title/cards plan."""
    config = _ollama_config()
    info: Dict[str, Any] = {"planner": "ollama", "model": config["model"],
                            "keyword_punch": keyword_punch}
    try:
        if not config["enabled"]:
            info["fallback_reason"] = "ollama disabled via EDIONIC_OLLAMA_ENABLED"
            return None, info
        duration = max(0.0, float(duration or 0.0))
        if duration < 1.0 or not words:
            info["fallback_reason"] = "empty transcript"
            return None, info
        transcript = _compact_transcript(words)
        if not transcript:
            info["fallback_reason"] = "empty transcript"
            return None, info

        template_ids, style_ids = _catalogs()
        system, user = _build_prompt(
            transcript, duration, title_text, hook_card_present_flag,
            template_id, style_preset, template_ids, style_ids,
            keyword_punch=keyword_punch,
        )
        body = json.dumps({
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            # Keyword-punch plans carry ~15-40 pop segments: raise the
            # output cap so a long plan is never cut mid-JSON. Short
            # plans stop at EOS as before.
            "options": {"num_predict": 2048},
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{config['url']}/api/chat", data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=config["timeout"]) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            info["fallback_reason"] = f"ollama HTTP {exc.code}"
            return None, info
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            info["fallback_reason"] = f"ollama unreachable: {exc}"
            return None, info

        try:
            envelope = json.loads(raw)
            content = (envelope.get("message") or {}).get("content", "")
            payload = _parse_model_json(content)
        except (ValueError, AttributeError) as exc:
            info["fallback_reason"] = f"unparseable model reply: {exc}"
            return None, info

        segments, error, meta = _validate_plan(
            payload, duration, hook_card_present_flag, template_ids, style_ids,
            keyword_punch=keyword_punch, words=words)
        if segments is None:
            info["fallback_reason"] = f"invalid plan: {error}"
            return None, info

        from motion_planner import segments_to_plan
        plan = segments_to_plan(segments, duration)
        if not plan["clips"]:
            info["fallback_reason"] = "validated plan produced no clips"
            return None, info
        info.update(meta)
        info["segments"] = plan["segments"]
        return plan, info
    except Exception as exc:  # never break a render because the model path broke
        info["fallback_reason"] = f"ollama planner error: {exc}"
        return None, info
