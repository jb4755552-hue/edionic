#!/usr/bin/env python3
"""Batch 5 checks: Devin Jatho keyword-punch style.

- keyword_punch preset: zero caption events (pops replace captions).
- graphics keyword_pop element: classifier, colours, mid-frame glow pop,
  measured-width fitting (3-word pops never exceed ~80% frame width).
- rules planner keyword_punch mode: pops per beat, colour roles, no hook
  title card, card_sequence only for genuine lists, one text at a time.
- Ollama validator: pop caps/rules, pop-wins collisions, hook waiver,
  mode gating, grounding validation (global).
- template devin_keyword_punch: no hook block, no SFX, no silence cuts.
- Slop Gate pop-band measurement for the keyword_punch preset.

Run: python3 backend/test_batch5_keyword_punch.py  (no pytest needed)
"""
import copy
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from caption_presets import ALL_11_PRESETS, PRESET_CATALOG_INFO, generate_ass_captions
from graphics import (
    KEYWORD_POP_MAX_W, KEYWORD_ROLE_COLORS, _est_text_w, _fit_text,
    _hex_to_ass_color, build_render_graphics, classify_graphic,
    merge_graphics_into_ass,
)
from motion_planner import plan_motion_graphics, segments_to_plan
from ollama_planner import (
    _build_prompt, _is_grounded, _transcript_tokens, _validate_plan,
    plan_with_ollama,
)
from templates import apply_template_to_job, get_template, list_templates
from slop_gate import _measure_real_1080x1920_frame

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        raise SystemExit(f"FAILED: {name}")


def mkwords(spec):
    """spec: list of (word, start, end)."""
    return [{"word": w, "start": s, "end": e} for (w, s, e) in spec]


TIDS = ["talking_head_pro", "devin_keyword_punch"]
SIDS = ["smoke2_style", "creator_motion_graphics_style"]


def plan(segs, **kw):
    payload = {"template_id": "devin_keyword_punch",
               "style_preset": "creator_motion_graphics_style",
               "segments": segs}
    payload.update(kw)
    return payload


def pop(start, end, text, color="neutral"):
    return {"type": "keyword_pop", "start_s": start, "end_s": end,
            "text": text, "color": color}


# --- 1. caption preset ----------------------------------------------------
check("keyword_punch listed as a preset", "keyword_punch" in ALL_11_PRESETS)
check("keyword_punch catalog entry", PRESET_CATALOG_INFO.get("keyword_punch", {}).get("type") == "keyword_pops")
words = mkwords([("hello", 0.0, 0.4), ("world", 0.4, 0.8), ("again", 0.8, 1.2)])
with tempfile.TemporaryDirectory() as tmp:
    ass_path = os.path.join(tmp, "kp.ass")
    info = generate_ass_captions(words, ass_path, preset="keyword_punch")
    raw = open(ass_path, encoding="utf-8").read()
    check("keyword_punch emits zero caption events",
          info["event_count"] == 0 and "Dialogue:" not in raw)
    check("keyword_punch ASS keeps styles+events sections for merging",
          "[V4+ Styles]" in raw and "[Events]" in raw)
    check("keyword_punch word_count stays real", info["word_count"] == 3)
    glow_path = os.path.join(tmp, "glow.ass")
    glow = generate_ass_captions(words, glow_path, preset="glow")
    check("other presets still emit events", glow["event_count"] > 0)

# --- 2. graphics element --------------------------------------------------
check("classify 'Keyword pop'", classify_graphic("Keyword pop") == "keyword_pop")
check("classify 'keyword_pop' id form", classify_graphic("keyword_pop") == "keyword_pop")
check("classify 'keyword emphasis' still emphasis",
      classify_graphic("keyword emphasis") == "emphasis")
check("role colours", KEYWORD_ROLE_COLORS == {
    "neutral": "#FFFFFF", "bad": "#EF4444",
    "good": "#22C55E", "key": "#3B82F6"})

edl = {
    "storyboard": {"blocks": [{"id": "plan_b0", "title": "ONE MILLION",
                               "text": "ONE MILLION"}]},
    "tracks": [{"id": "V2", "clips": [
        {"id": "v2_plan_0", "block_id": "plan_b0", "title": "ONE MILLION",
         "graphic": "Keyword pop", "color_role": "good",
         "in": 0.0, "out": 1.5, "at": 0.5, "duration": 1.5}]}],
}
gfx = build_render_graphics(edl, 10.0, preset_name="keyword_punch")
check("keyword_pop renders one event", len(gfx["ass_events"]) == 1, str(gfx["ass_events"]))
event = gfx["ass_events"][0]
check("pop uses GfxKeyword style", ",GfxKeyword," in event)
check("pop colour is role green", _hex_to_ass_color("#22C55E") in event)
check("pop centred mid-frame", "\\pos(540,1130)" in event)
check("pop has soft glow, hard pop, no fade",
      "\\blur4" in event and "\\t(0,120," in event and "\\fad" not in event)
check("pop event text uppercased", event.rstrip().endswith("ONE MILLION"))
check("pop summary element type", gfx["elements"][0]["type"] == "keyword_pop")

for role, hexcol in [("bad", "#EF4444"), ("key", "#3B82F6"), ("neutral", "#FFFFFF"),
                     ("bogus", "#FFFFFF")]:
    edl2 = copy.deepcopy(edl)
    edl2["tracks"][0]["clips"][0]["color_role"] = role
    ev = build_render_graphics(edl2, 10.0, preset_name="keyword_punch")["ass_events"][0]
    check(f"pop colour role {role}", _hex_to_ass_color(hexcol) in ev)

# Fitting: 3-word pops stay huge (no shrink) and within ~80% width.
lines, fs = _fit_text("ONE MILLION DOLLARS", 130, KEYWORD_POP_MAX_W,
                      max_lines=2, min_fs=72, em_scale=0.72)
check("3-word pop fits on 2 lines at full size", len(lines) <= 2 and fs == 130, f"{lines} fs={fs}")
for ln in lines:
    check("pop line within 80% width",
          _est_text_w(ln, fs) * 0.72 <= KEYWORD_POP_MAX_W, ln)
lines2, _ = _fit_text("ANTIDISESTABLISHMENTARIANISM", 130, KEYWORD_POP_MAX_W,
                      max_lines=2, min_fs=72, em_scale=0.72)
check("single over-wide word truncated, never overflows",
      len(lines2) == 1 and _est_text_w(lines2[0], 130) * 0.72 <= KEYWORD_POP_MAX_W
      and lines2[0].endswith("…"), str(lines2))
# Default em_scale keeps Hotfix 4.3 behaviour identical.
check("default em_scale unchanged",
      _fit_text("1 week -editor-to-week bonuses", 80, 800, 2, min_fs=44)
      == _fit_text("1 week -editor-to-week bonuses", 80, 800, 2, min_fs=44, em_scale=1.0))

# Merged ASS: pops only, no caption events, no double text.
with tempfile.TemporaryDirectory() as tmp:
    ass_path = os.path.join(tmp, "merged.ass")
    generate_ass_captions(words, ass_path, preset="keyword_punch")
    merge_graphics_into_ass(ass_path, gfx["ass_styles"], gfx["ass_events"])
    merged = open(ass_path, encoding="utf-8").read()
    dialogues = [ln for ln in merged.splitlines() if ln.startswith("Dialogue:")]
    check("merged ASS has only the pop event",
          len(dialogues) == 1 and "ONE MILLION" in dialogues[0], str(dialogues))

# --- 3. rules planner -----------------------------------------------------
# Devin-like transcript, no list speech.
tx = mkwords([
    ("stop", 0.0, 0.4), ("doing", 0.4, 0.8), ("this", 0.8, 1.1),
    ("broke", 1.1, 1.5), ("method", 1.5, 1.9),
    ("one", 2.6, 2.9), ("million", 2.9, 3.3), ("dollars", 3.3, 3.8),
    ("from", 3.8, 4.1), ("a", 4.1, 4.3), ("matrix", 4.3, 4.8),
    ("the", 5.6, 5.8), ("matrix", 5.8, 6.2), ("method", 6.2, 6.6),
    ("is", 6.6, 6.8), ("free", 6.8, 7.2), ("matrix", 8.0, 8.4),
    ("never", 9.2, 9.6), ("quit", 9.6, 10.0),
])
punch = plan_motion_graphics(tx, 10.5, keyword_punch=True)
types = [s["type"] for s in punch["segments"]]
check("punch mode: no hook title card", "title_card" not in types)
check("punch mode: pops planned", types.count("keyword_pop") >= 3, str(types))
check("punch mode: no card_sequence without list speech", "card_sequence" not in types)
pops = [s for s in punch["segments"] if s["type"] == "keyword_pop"]
check("pop text is 1-3 words", all(1 <= len(s["text"].split()) <= 3 for s in pops))
check("pop colours valid", all(s.get("color") in ("neutral", "bad", "good", "key") for s in pops))
check("pop durations 0.5-2.5s", all(0.5 <= s["end"] - s["start"] <= 2.5 for s in pops))
for a, b in zip(pops, pops[1:]):
    check("pops never overlap each other", a["end"] <= b["start"], f"{a} vs {b}")
check("first pop is the hook (starts on its spoken words, <=1.5s)",
      pops[0]["start"] <= 1.5, str(pops[0]))
check("punch mode: zooms on pop beats", "zoom" in types)
others = [s for s in punch["segments"] if s["type"] not in ("keyword_pop", "zoom")]
for o in others:
    check("other graphics never overlap pops",
          all(o["end"] <= p["start"] or o["start"] >= p["end"] for p in pops), str(o))
check("pop clips carry color_role",
      all(c.get("color_role") in ("neutral", "bad", "good", "key")
          for c in punch["clips"] if c.get("graphic") == "Keyword pop"))

normal = plan_motion_graphics(tx, 10.5)
ntypes = [s["type"] for s in normal["segments"]]
check("normal mode unchanged: hook title, no pops",
      "title_card" in ntypes and "keyword_pop" not in ntypes, str(ntypes))

# Colour roles on targeted single-beat transcripts.
red = plan_motion_graphics(mkwords([("never", 0.0, 0.4), ("quit", 0.4, 0.8)]),
                           2.0, keyword_punch=True)["segments"]
check("red role for bad/old phrase",
      any(s.get("color") == "bad" and "never" in s["text"].lower() for s in red), str(red))
green = plan_motion_graphics(
    mkwords([("one", 0.0, 0.3), ("million", 0.3, 0.7), ("dollars", 0.7, 1.1)]),
    2.0, keyword_punch=True)["segments"]
check("green role for money phrase",
      any(s.get("color") == "good" and s["text"].lower() == "one million dollars" for s in green),
      str(green))
blue_tx = mkwords([("matrix", 0.0, 0.4), ("wins", 0.4, 0.8),
                   ("the", 1.4, 1.6), ("matrix", 1.6, 2.0), ("method", 2.0, 2.4),
                   ("matrix", 3.0, 3.4), ("again", 3.4, 3.8)])
blue = plan_motion_graphics(blue_tx, 4.5, keyword_punch=True)["segments"]
check("blue role for the key term",
      any(s.get("color") == "key" and "matrix" in s["text"].lower() for s in blue), str(blue))
white = plan_motion_graphics(mkwords([("matrix", 0.0, 0.4), ("matrix", 1.2, 1.6),
                                       ("matrix", 2.4, 2.8), ("hello", 4.0, 4.4),
                                       ("table", 4.4, 4.8)]),
                             6.0, keyword_punch=True)["segments"]
check("white role for neutral words",
      any(s.get("color") == "neutral" and "hello" in s["text"].lower() for s in white),
      str(white))

# Genuine list: card_sequence reserves its span, pops skip it.
list_tx = mkwords([
    ("first", 0.0, 0.4), ("hook", 0.4, 0.8),
    ("second", 2.0, 2.4), ("story", 2.4, 2.8),
    ("third", 4.0, 4.4), ("offer", 4.4, 4.8),
    ("free", 8.0, 8.4), ("training", 8.4, 8.9),
])
listed = plan_motion_graphics(list_tx, 10.0, keyword_punch=True)
ltypes = [s["type"] for s in listed["segments"]]
check("genuine list keeps exactly one card_sequence",
      ltypes.count("card_sequence") == 1, str(ltypes))
card = next(s for s in listed["segments"] if s["type"] == "card_sequence")
lpops = [s for s in listed["segments"] if s["type"] == "keyword_pop"]
check("pops exist outside the list span", len(lpops) >= 1, str(lpops))
for p in lpops:
    check("no pop overlaps the card span",
          p["end"] <= card["start"] or p["start"] >= card["end"], f"{p} vs {card}")

# segments_to_plan carries colour through the Ollama injection path.
conv = segments_to_plan([{"type": "keyword_pop", "start": 0.0, "end": 1.2,
                          "text": "MATRIX", "color": "key"}], 5.0)
check("segments_to_plan maps keyword_pop graphic",
      conv["clips"][0]["graphic"] == "Keyword pop")
check("segments_to_plan carries color_role + visible color",
      conv["clips"][0]["color_role"] == "key" and conv["segments"][0]["color"] == "key")

# --- 4. Ollama validator --------------------------------------------------
good_punch = plan([pop(0.0, 1.4, "MATRIX", "key"), pop(1.6, 3.0, "OLD WAY", "bad"),
                   pop(3.2, 4.6, "NEW WAY", "good"),
                   {"type": "zoom", "start_s": 0.0, "end_s": 3.0, "amount": 0.12}])
segs, err, meta = _validate_plan(good_punch, 10.0, False, TIDS, SIDS, keyword_punch=True)
check("punch plan valid without hook title (waiver)",
      segs is not None and len(segs) == 4, err)
check("pop colours preserved", segs is not None and
      [s.get("color") for s in segs if s["type"] == "keyword_pop"] == ["key", "bad", "good"])
check("no pops rejected in punch mode",
      _validate_plan(plan([{"type": "zoom", "start_s": 0.0, "end_s": 2.0, "amount": 0.1}]),
                     10.0, False, TIDS, SIDS, keyword_punch=True)[0] is None)

long_pop = plan([pop(0.0, 1.0, "ONE TWO THREE FOUR FIVE", "neutral")])
segs, _, meta = _validate_plan(long_pop, 10.0, False, TIDS, SIDS, keyword_punch=True)
check("pop text trimmed to 3 words",
      segs is not None and segs[0]["text"] == "ONE TWO THREE" and meta.get("repaired"))
wide_pop = plan([pop(0.0, 4.0, "MATRIX", "key")])
segs, _, meta = _validate_plan(wide_pop, 10.0, False, TIDS, SIDS, keyword_punch=True)
check("pop clamped to 2.5s", segs is not None and segs[0]["end"] - segs[0]["start"] == 2.5)

overlap_pops = plan([pop(0.0, 2.0, "FIRST", "neutral"), pop(1.0, 3.0, "SECOND", "neutral")])
segs, _, meta = _validate_plan(overlap_pops, 10.0, False, TIDS, SIDS, keyword_punch=True)
check("overlapping pop shifted, not stacked",
      segs is not None and len(segs) == 2 and segs[1]["start"] == 2.0, str(segs))
swallow_pops = plan([pop(0.0, 2.0, "FIRST", "neutral"), pop(1.0, 2.2, "SECOND", "neutral")])
segs, _, meta = _validate_plan(swallow_pops, 10.0, False, TIDS, SIDS, keyword_punch=True)
check("pop with <0.5s after shifting is dropped",
      segs is not None and len(segs) == 1, str(segs))

# Pops win over drawn segments; zoom exempt.
proof_over = plan([pop(0.0, 2.0, "MATRIX", "key"),
                   {"type": "proof_card", "start_s": 1.0, "end_s": 3.0, "text": "100K"},
                   {"type": "zoom", "start_s": 0.0, "end_s": 2.0, "amount": 0.1}])
segs, _, meta = _validate_plan(proof_over, 10.0, False, TIDS, SIDS, keyword_punch=True)
proof = [s for s in (segs or []) if s["type"] == "proof_card"]
check("proof overlapping a pop is trimmed after it",
      len(proof) == 1 and proof[0]["start"] == 2.0, str(segs))
check("zoom over a pop is kept",
      any(s["type"] == "zoom" for s in (segs or [])))
proof_inside = plan([pop(0.0, 2.0, "MATRIX", "key"),
                     {"type": "proof_card", "start_s": 0.5, "end_s": 1.5, "text": "100K"}])
segs, _, meta = _validate_plan(proof_inside, 10.0, False, TIDS, SIDS, keyword_punch=True)
check("proof fully inside a pop window is dropped",
      segs is not None and all(s["type"] != "proof_card" for s in segs), str(segs))

# Forbidden types dropped in punch mode.
forbidden = plan([pop(0.0, 1.0, "HOOK", "key"),
                  {"type": "title_card", "start_s": 2.0, "end_s": 4.0, "text": "TITLE"},
                  {"type": "lower_third", "start_s": 4.0, "end_s": 5.0, "text": "NAME"},
                  {"type": "progress_bar", "start_s": 5.0, "end_s": 6.0},
                  {"type": "emphasis", "start_s": 6.0, "end_s": 7.0, "text": "WORD"}])
segs, _, meta = _validate_plan(forbidden, 10.0, False, TIDS, SIDS, keyword_punch=True)
check("title/lower/progress/emphasis dropped in punch mode",
      segs is not None and [s["type"] for s in segs] == ["keyword_pop"], str(segs))

# Pops dropped in normal mode; hook title still rules.
normal_pop = plan([{"type": "title_card", "start_s": 0.0, "end_s": 3.0, "text": "HOOK"},
                   pop(4.0, 5.0, "MATRIX", "key")])
segs, _, meta = _validate_plan(normal_pop, 10.0, False, TIDS, SIDS)
check("keyword_pop dropped in normal mode, plan kept",
      segs is not None and all(s["type"] != "keyword_pop" for s in segs)
      and meta.get("repaired"), str(segs))

# Pop cap is separate from the 6-graphic cap.
many_pops = plan([pop(i * 0.5, i * 0.5 + 0.4, f"WORD{i}", "neutral") for i in range(45)])
segs, _, meta = _validate_plan(many_pops, 30.0, False, TIDS, SIDS, keyword_punch=True)
check("pops truncated to 40",
      segs is not None and len([s for s in segs if s["type"] == "keyword_pop"]) == 40,
      str(len(segs) if segs else None))
many_gfx = plan([{"type": "pill", "start_s": float(i), "end_s": float(i) + 0.6,
                  "text": f"P{i}"} for i in range(7)]
                + [pop(10.0, 11.0, "A", "neutral"), pop(12.0, 13.0, "B", "neutral")])
segs, _, meta = _validate_plan(many_gfx, 20.0, False, TIDS, SIDS, keyword_punch=True)
check("graphics still capped at 6 while pops survive",
      segs is not None and len([s for s in segs if s["type"] == "pill"]) == 6
      and len([s for s in segs if s["type"] == "keyword_pop"]) == 2, str(segs))

# Grounding (global, both modes).
gtx = mkwords([("we", 0.0, 0.2), ("made", 0.2, 0.5), ("one", 0.5, 0.7),
               ("million", 0.7, 1.0), ("dollars", 1.0, 1.4),
               ("from", 1.4, 1.6), ("1.2", 1.6, 1.9), ("million", 1.9, 2.2),
               ("views", 2.2, 2.6), ("with", 2.6, 2.8), ("five", 2.8, 3.0),
               ("profit", 3.0, 3.4)])
tokens = _transcript_tokens(gtx)
check("grounding: contiguous phrase", _is_grounded("one million dollars", tokens))
check("grounding: case/punctuation ignored", _is_grounded("One, MILLION dollars!", tokens))
check("grounding: magnitude shorthand expands", _is_grounded("1.2M views", tokens))
check("grounding: non-contiguous rejected", not _is_grounded("one views", tokens))
check("grounding: hallucinated phrase rejected", not _is_grounded("secret sauce method", tokens))
check("grounding: wrong order rejected", not _is_grounded("dollars one million", tokens))

grounded_plan = plan([
    {"type": "title_card", "start_s": 0.0, "end_s": 3.0, "text": "HOOK"},
    {"type": "proof_card", "start_s": 3.5, "end_s": 5.0, "text": "1.2M views"},
    {"type": "pill", "start_s": 5.5, "end_s": 6.5, "text": "SECRET SAUCE"},
])
segs, _, meta = _validate_plan(grounded_plan, 10.0, False, TIDS, SIDS, words=gtx)
check("grounded proof kept, hallucinated pill dropped",
      segs is not None and any(s["type"] == "proof_card" for s in segs)
      and not any(s["type"] == "pill" for s in segs), str(segs))
check("grounding skipped when no transcript given",
      _validate_plan(grounded_plan, 10.0, False, TIDS, SIDS)[0] is not None
      and any(s["type"] == "pill"
              for s in _validate_plan(grounded_plan, 10.0, False, TIDS, SIDS)[0]))

card_ground = plan([
    {"type": "title_card", "start_s": 0.0, "end_s": 1.0, "text": "HOOK"},
    {"type": "card_sequence", "start_s": 2.0, "end_s": 6.0, "cards": [
        {"number": "1", "label": "one million"},
        {"number": "2", "label": "hallucinated label"},
        {"number": "3", "label": "five profit"}]},
])
segs, _, meta = _validate_plan(card_ground, 10.0, False, TIDS, SIDS, words=gtx)
seq = [s for s in (segs or []) if s["type"] == "card_sequence"]
check("ungrounded card label dropped, sequence kept with 2 grounded",
      len(seq) == 1 and len(seq[0]["cards"]) == 2, str(segs))
card_ground_bad = plan([
    {"type": "title_card", "start_s": 0.0, "end_s": 1.0, "text": "HOOK"},
    {"type": "card_sequence", "start_s": 2.0, "end_s": 6.0, "cards": [
        {"number": "1", "label": "zzz one"},
        {"number": "2", "label": "zzz two"}]},
])
segs, _, meta = _validate_plan(card_ground_bad, 10.0, False, TIDS, SIDS, words=gtx)
check("card_sequence dropped with <2 grounded labels",
      segs is not None and not any(s["type"] == "card_sequence" for s in segs), str(segs))

keyword_ground = plan([pop(0.0, 1.0, "ONE MILLION", "good"),
                       pop(1.5, 2.5, "FAKE WORDS", "neutral")])
segs, _, meta = _validate_plan(keyword_ground, 10.0, False, TIDS, SIDS,
                               keyword_punch=True, words=gtx)
check("ungrounded keyword dropped, grounded kept",
      segs is not None and [s["text"] for s in segs] == ["ONE MILLION"], str(segs))

# Prompt: punch mode offers pops + restraint; normal mode never offers pops.
sys_p, _ = _build_prompt("matrix(0.0)", 10.0, "T", False, "devin_keyword_punch",
                         "creator_motion_graphics_style", TIDS, SIDS, keyword_punch=True)
check("punch prompt offers keyword_pop + colours",
      "keyword_pop" in sys_p and '"bad"' in sys_p and '"good"' in sys_p and '"key"' in sys_p)
check("punch prompt has restraint + one-text rules",
      "NEVER emit card_sequence" in sys_p and "ONE text on screen" in sys_p)
check("punch prompt example is the punch example",
      "EXAMPLE OLD WAY" in sys_p and "devin_keyword_punch" in sys_p)
sys_n, _ = _build_prompt("first(0.5)", 10.0, "T", False, None, None, TIDS, SIDS)
check("normal prompt never offers keyword_pop", "keyword_pop" not in sys_n)
check("normal prompt has the card_sequence hard rule (global restraint)",
      "NEVER emit card_sequence" in sys_n)
check("normal prompt still requires the hook title",
      "REQUIRED unless one already renders" in sys_n)

# plan_with_ollama: disabled path never raises, reports fallback.
old_enabled = os.environ.get("EDIONIC_OLLAMA_ENABLED")
os.environ["EDIONIC_OLLAMA_ENABLED"] = "0"
try:
    p, info = plan_with_ollama(gtx, 10.0, keyword_punch=True)
finally:
    if old_enabled is None:
        del os.environ["EDIONIC_OLLAMA_ENABLED"]
    else:
        os.environ["EDIONIC_OLLAMA_ENABLED"] = old_enabled
check("ollama disabled -> fallback, never raises",
      p is None and "disabled" in str(info.get("fallback_reason", "")))
check("planner info carries keyword_punch flag", info.get("keyword_punch") is True)

# --- 5. template ----------------------------------------------------------
tpl = get_template("devin_keyword_punch")
check("devin template exists", tpl is not None)
check("devin template preset/silence/sfx",
      tpl["caption_preset"] == "keyword_punch" and tpl["silence_cuts"] is False
      and tpl["sfx_defaults"] == [] and tpl["sfx_map"] == [])
check("devin template has no hook block", tpl.get("hook_block") is False)
check("devin template listed", "devin_keyword_punch" in list_templates())
filled = apply_template_to_job("devin_keyword_punch", {})
check("devin job gets empty storyboard (no hook block)",
      filled["storyboard"] == {"title": tpl["name"], "blocks": []}, str(filled.get("storyboard")))
check("devin job carries template id + preset",
      filled["template_id"] == "devin_keyword_punch"
      and filled["caption_preset"] == "keyword_punch")
filled_other = apply_template_to_job("talking_head_pro", {})
check("other templates still get the hook block",
      len(filled_other["storyboard"]["blocks"]) == 1
      and filled_other["storyboard"]["blocks"][0]["title"] == "hook")

# --- 6. Slop Gate pop band -----------------------------------------------
W, H = 1080, 1920
frame = bytearray([128] * (W * H * 3))  # mid-grey: no contrast rows
for y in range(1000, 1120):  # bright block inside the pop band only
    for x in range(100, 980):
        i = (y * W + x) * 3
        frame[i] = frame[i + 1] = frame[i + 2] = 255
raw = bytes(frame)
pop_metrics = _measure_real_1080x1920_frame(raw, W, H, cap_band=(850, 1300))
cap_metrics = _measure_real_1080x1920_frame(raw, W, H)
check("pop band measures the mid-frame text",
      pop_metrics["caption_height_px"] >= 54, str(pop_metrics["caption_height_px"]))
check("default band ignores mid-frame text",
      cap_metrics["caption_height_px"] == 0, str(cap_metrics["caption_height_px"]))

print(f"\n{sum(CHECKS)}/{len(CHECKS)} Batch 5 checks pass")
