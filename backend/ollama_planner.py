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
- EDIONIC_OLLAMA_TIMEOUT (default 60 seconds)

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
    "shape", "emphasis", "card_sequence", "zoom",
}
_TEXT_REQUIRED = {"title_card", "pill", "proof_card", "lower_third", "emphasis"}
_MAX_SEGMENTS = 6
_MAX_TEXT_LEN = 60
_MAX_LABEL_LEN = 16
_MAX_TRANSCRIPT_WORDS = 500

_FALLBACK_TEMPLATE_IDS = [
    "saas_dark_premium", "saas_clean_flat", "talking_head_pro",
    "trust_talking_head", "split_screen_breakdown", "screen_record_tutorial",
    "archival_documentary", "portfolio_showreel", "ai_showcase_desk",
    "local_language_demo", "gaming_montage",
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

_EXAMPLE = """\
{"template_id": "talking_head_pro", "style_preset": "smoke2_style", "segments": [
 {"type": "title_card", "start_s": 0.0, "end_s": 3.0, "text": "SAVE MORE MONEY"},
 {"type": "card_sequence", "start_s": 3.7, "end_s": 11.5, "cards": [{"number": "1", "label": "save money"}, {"number": "2", "label": "build audience"}, {"number": "3", "label": "sell products"}, {"number": "4", "label": "scale fast"}]},
 {"type": "zoom", "start_s": 3.7, "end_s": 11.5, "amount": 0.1},
 {"type": "proof_card", "start_s": 13.0, "end_s": 15.5, "text": "100K REVENUE"}
]}"""


def _ollama_config() -> Dict[str, Any]:
    enabled_raw = str(os.environ.get("EDIONIC_OLLAMA_ENABLED", "1")).strip().lower()
    try:
        timeout = float(os.environ.get("EDIONIC_OLLAMA_TIMEOUT", "60"))
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
                  template_ids: List[str], style_ids: List[str]) -> Tuple[str, str]:
    system = (
        "You are the motion design planner for Edionic, a 9:16 vertical "
        "short-form video editor. Given a transcript with word timestamps, "
        "plan timed motion graphics. Reply with ONE JSON object only, no "
        "markdown, no explanation.\n\n"
        "ELEMENT TYPES:\n" + _ELEMENT_HELP + "\n\n"
        "RULES:\n"
        "- At most 6 segments. Times in seconds, within the video duration.\n"
        "- At most ONE card_sequence, and NO other drawn segment may overlap it (zoom may overlap it).\n"
        "- A hook title_card starting at 0.0 is REQUIRED unless one already renders.\n"
        "- Keep text short, uppercase-friendly, taken from the spoken words.\n"
        "- card_sequence cards: 2-5 cards, each with number + short label from the spoken list.\n"
        "- Name a template_id and a style_preset from the catalogs below.\n\n"
        "TEMPLATES: " + ", ".join(template_ids) + "\n"
        "STYLES: " + ", ".join(style_ids) + "\n\n"
        "EXAMPLE:\n" + _EXAMPLE
    )
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


def _validate_plan(payload: Any, duration: float, hook_card_present: bool,
                   template_ids: List[str], style_ids: List[str]) -> Tuple[Optional[List[Dict[str, Any]]], str, Dict[str, Any]]:
    """Strict all-or-nothing validation. Returns (segments, error, meta);
    segments is None when ANY check fails — a half-plan with bad times is
    worse than the rules fallback."""
    if not isinstance(payload, dict):
        return None, "model reply is not a JSON object", {}
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        return None, "plan has no segments list", {}
    if len(raw_segments) > _MAX_SEGMENTS:
        return None, f"plan has {len(raw_segments)} segments (max {_MAX_SEGMENTS})", {}

    meta: Dict[str, Any] = {}
    suggested_template = payload.get("template_id")
    if suggested_template is not None:
        if str(suggested_template) not in template_ids:
            return None, f"unknown template_id: {suggested_template!r}", {}
        meta["suggested_template_id"] = str(suggested_template)
    suggested_style = payload.get("style_preset")
    if suggested_style is not None:
        if str(suggested_style) not in style_ids:
            return None, f"unknown style_preset: {suggested_style!r}", {}
        meta["suggested_style_preset"] = str(suggested_style)

    segments: List[Dict[str, Any]] = []
    card_span: Optional[Tuple[float, float]] = None
    has_hook_title = False
    for idx, raw in enumerate(raw_segments):
        if not isinstance(raw, dict):
            return None, f"segment {idx} is not an object", {}
        seg_type = str(raw.get("type") or "").strip()
        if seg_type not in _ALLOWED_TYPES:
            return None, f"segment {idx} has unknown type: {seg_type!r}", {}
        start = raw.get("start_s")
        end = raw.get("end_s")
        if isinstance(start, bool) or isinstance(end, bool) \
                or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            return None, f"segment {idx} has non-numeric times", {}
        start = float(start)
        end = float(end)
        if not (0.0 <= start < end <= duration):
            return None, f"segment {idx} times out of range: {start}-{end} (duration {duration})", {}
        if end - start < 0.5:
            return None, f"segment {idx} is shorter than 0.5s", {}

        seg: Dict[str, Any] = {"type": seg_type, "start": round(start, 3), "end": round(end, 3)}
        if seg_type in _TEXT_REQUIRED:
            text = _sanitize_text(raw.get("text"), _MAX_TEXT_LEN)
            if not text:
                return None, f"segment {idx} ({seg_type}) has no text", {}
            seg["text"] = text
        if seg_type == "title_card" and start <= 0.5:
            has_hook_title = True
        if seg_type == "card_sequence":
            if card_span is not None:
                return None, "plan has more than one card_sequence", {}
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
            card_span = (start, end)
        if seg_type == "zoom":
            amount = raw.get("amount", 0.10)
            if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                return None, "zoom amount is not numeric", {}
            seg["amount"] = max(0.05, min(0.15, float(amount)))
        segments.append(seg)

    if card_span is not None:
        for seg in segments:
            if seg["type"] in ("card_sequence", "zoom"):
                # Zoom is a video effect, not a drawn graphic: a punch-in
                # over the card span is intended (the rules planner does
                # the same) and cannot collide visually.
                continue
            if seg["start"] < card_span[1] and seg["end"] > card_span[0]:
                return None, "a segment overlaps the card_sequence span", {}
    if not hook_card_present and not has_hook_title:
        return None, "plan has no hook title_card starting at 0.0", {}

    segments.sort(key=lambda s: s["start"])
    return segments, "", meta


def plan_with_ollama(
    words: List[Dict[str, Any]],
    duration: float,
    title_text: str = "",
    hook_card_present_flag: bool = False,
    template_id: Optional[str] = None,
    style_preset: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Ask the local Ollama model for a motion plan.

    Returns (plan, info). plan is None on ANY failure (disabled, empty
    transcript, unreachable, timeout, bad JSON, validation failure) and
    info carries the fallback reason; the caller then uses the rules
    planner. This function never raises.
    """
    config = _ollama_config()
    info: Dict[str, Any] = {"planner": "ollama", "model": config["model"]}
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
        )
        body = json.dumps({
            "model": config["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
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
            payload, duration, hook_card_present_flag, template_ids, style_ids)
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
