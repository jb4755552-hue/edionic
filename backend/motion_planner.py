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

Batch 5 — keyword punch mode (keyword_punch=True): the Devin Jatho
style. NO hook title card (the first keyword pop IS the hook); one
keyword_pop per ~1.5-2s speech beat, 1-3 transcript words, colour-coded
(white neutral / red bad-old / green good-new / blue key term); the
card sequence still requires a genuine list and reserves its span
(pops skip it); proof cards/pills render ONLY in gaps that no pop
covers (one text on screen at a time — pops win); zooms punch in on
pop beats. This mode is also the fallback when the Ollama planner
cannot produce a valid keyword-punch plan.
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

# --- Batch 5 keyword-punch word sets -------------------------------------
# Red ("bad"/old) triggers: contrast/negative words. Contractions carry
# meaning ("DON'T QUIT") so they stay; bare "not"/"no" are stop words.
_NEGATIVE_WORDS = {
    "bad", "wrong", "mistake", "mistakes", "fail", "failed", "failing",
    "failure", "never", "old", "broke", "poor", "lose", "losing", "lost",
    "loser", "hate", "problem", "problems", "struggle", "struggling",
    "stuck", "waste", "wasted", "fear", "scared", "debt", "quit",
    "quitting", "average", "mediocre", "ordinary", "bored", "boring",
    "tired", "lazy", "excuse", "excuses", "blame", "doubt", "doubts",
    "confused", "confusion", "fake", "lie", "lies", "scam", "trap",
    "stupid", "dumb", "weak", "slow", "late", "miss", "missed", "regret",
    "pain", "painful", "nothing", "nobody", "none",
    "don't", "doesn't", "didn't", "can't", "cannot", "won't", "wouldn't",
    "couldn't", "shouldn't", "isn't", "aren't", "wasn't", "weren't",
    "haven't", "hasn't", "hadn't", "ain't",
}
# Green ("good"/new power) triggers, beyond _EMPHASIS_WORDS/_MONEY_WORDS.
_GOOD_WORDS = {
    "rich", "wealthy", "wealth", "success", "successful", "win", "winner",
    "winning", "grow", "growth", "freedom", "millionaire", "billionaire",
    "viral", "famous", "top", "elite", "great", "perfect", "powerful",
    "strong", "unstoppable", "limitless", "abundance", "profitable",
    "scaling", "scale", "legendary", "genius", "master", "mastery",
    "champion", "dominate", "dominating", "crush", "crushing", "explode",
    "exploding", "skyrocket", "double", "triple",
}
# Stop words for pop phrases: function words, generic verbs and generic
# nouns. Deliberately EXCLUDES money/emphasis/negative/good/number
# words — those are exactly what a pop should show.
_POP_STOP_WORDS = _STOP_WORDS | {
    "will", "would", "can", "could", "should", "shall", "may", "might",
    "must", "just", "really", "very", "much", "more", "do", "does",
    "did", "have", "has", "had", "not", "no", "all", "every", "about",
    "into", "over", "under", "out", "up", "down", "now", "today", "am",
    "there", "here", "them", "us", "him", "her", "his", "their", "our",
    "its", "than", "too", "also", "even", "still", "already", "yet",
    "ever", "because", "after", "before", "between", "through",
    "during", "without", "within", "around", "toward", "onto", "per",
    "via", "go", "going", "come", "take", "see", "know", "think",
    "want", "need", "like", "said", "say", "let", "put", "keep",
    "make", "made", "give", "find", "tell", "ask", "try", "use",
    "call", "feel", "become", "leave", "mean", "show", "hear", "play",
    "run", "move", "live", "bring", "happen", "write", "sit", "stand",
    "pay", "meet", "set", "learn", "change", "lead", "watch", "follow",
    "create", "speak", "read", "allow", "add", "spend", "open", "walk",
    "offer", "remember", "love", "appear", "buy", "wait", "serve",
    "send", "expect", "build", "stay", "fall", "cut", "reach",
    "remain", "suggest", "raise", "pass", "sell", "require", "report",
    "decide", "pull", "thing", "things", "way", "day", "time",
    "people", "world", "life", "part", "place", "case", "week",
    "system", "question", "number", "night", "point", "home", "room",
    "area", "story", "fact", "month", "lot", "study", "book", "eye",
    "job", "word", "business", "issue", "side", "kind", "head",
    "house", "service", "friend", "father", "power", "country", "hour",
    "game", "line", "end", "member", "law", "car", "city", "community",
    "name", "team", "minute", "idea", "kid", "body", "information",
    "back", "face", "level", "office", "door", "health", "art", "war",
    "history", "party", "result", "morning", "reason", "research",
    "girl", "boy", "guy", "moment", "air", "teacher", "force",
    "education", "year", "years", "weeks", "months", "days", "hours",
    "minutes", "second", "seconds",
}

_MAX_KEYWORD_POPS = 40
_POP_MIN_HOLD = 0.7
_POP_MAX_LEN = 2.5
_BEAT_MAX_SPAN = 2.0
_BEAT_GAP = 0.6


def _clean_word(text: str) -> str:
    return re.sub(r"^[^\w$%]+|[^\w%$]+$", "", str(text or "").lower())


def _display_word(word: Dict[str, Any]) -> str:
    """Spoken word as shown in a pop/pill: edge punctuation stripped
    ("media." -> "media", "-to" -> "to"), internal characters kept
    ("1.2", "$5"). Case preserved; the graphics layer uppercases."""
    return re.sub(r"^[^\w$%]+|[^\w%$]+$", "", str(word.get("word", "")).strip())


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
    blocked_spans: Optional[List[Tuple[float, float]]] = None,
) -> List[Dict[str, Any]]:
    """Money/number -> proof_card, emphasis words -> pill. Chronological,
    spaced apart, capped, kept out of the card span and hook zone.
    `blocked_spans` (keyword-punch mode) additionally excludes any
    candidate whose window overlaps a keyword pop: one text on screen
    at a time, pops win."""
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
        if blocked_spans and any(
            start - 0.3 < b_end and end + 1.5 > b_start
            for (b_start, b_end) in blocked_spans
        ):
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
            shown = re.sub(r"^[^\w$%]+|[^\w%$]+$", "", raw.strip()) or raw.strip()
            found.append({
                "type": "pill", "graphic": "pill",
                "start": max(0.0, start - 0.2), "end": min(duration, end + 1.0),
                "title": shown, "text": shown,
            })
            last_start = start
        if len(found) >= _MAX_EMPHASIS:
            break
    return [f for f in found if f["end"] - f["start"] >= 0.5]


# --- Batch 5 keyword-punch selection -------------------------------------

def _topic_word(words: List[Dict[str, Any]]) -> Optional[str]:
    """Most frequent neutral content word: the video's key term (blue
    pops). Money/emphasis/negative/good/number words are excluded — they
    already have their own colours. Ties break by first occurrence."""
    counts: Dict[str, int] = {}
    first_seen: Dict[str, int] = {}
    for idx, w in enumerate(words):
        cleaned = _clean_word(w.get("word", ""))
        if len(cleaned) < 3 or cleaned in _POP_STOP_WORDS \
                or cleaned in _NEGATIVE_WORDS or cleaned in _EMPHASIS_WORDS \
                or cleaned in _MONEY_WORDS or cleaned in _GOOD_WORDS \
                or _marker_value(w.get("word", "")) is not None \
                or bool(re.search(r"\d", str(w.get("word", "")))):
            continue
        counts[cleaned] = counts.get(cleaned, 0) + 1
        first_seen.setdefault(cleaned, idx)
    if not counts:
        return None
    return min(counts, key=lambda c: (-counts[c], first_seen[c]))


def _pop_score(word: Dict[str, Any], topic: Optional[str]) -> int:
    """Salience of one transcript word as a pop anchor."""
    raw = str(word.get("word", ""))
    cleaned = _clean_word(raw)
    if bool(re.search(r"\d", raw)) or raw.startswith("$") or cleaned in _MONEY_WORDS:
        return 4
    if _marker_value(raw) is not None or cleaned in _EMPHASIS_WORDS \
            or cleaned in _NEGATIVE_WORDS or cleaned in _GOOD_WORDS:
        return 3
    if topic is not None and cleaned == topic:
        return 2
    if cleaned in _POP_STOP_WORDS or not cleaned:
        return -2
    return 1


def _is_pop_content(word: Dict[str, Any]) -> bool:
    """True when a word may join a pop phrase (not a stop word)."""
    cleaned = _clean_word(word.get("word", ""))
    if not cleaned:
        return False
    if cleaned in _POP_STOP_WORDS:
        return False
    return len(cleaned) >= 2 or bool(re.search(r"\d", cleaned))


def _speech_beats(words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Split words into ~1.5-2s beats: cut on a >0.6s pause or when the
    beat would exceed 2s. Words must already be sorted by start."""
    beats: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    prev_end = 0.0
    for w in words:
        start = float(w.get("start", 0.0))
        end = float(w.get("end", start + 0.3))
        if current and (start - prev_end > _BEAT_GAP
                        or end - float(current[0].get("start", 0.0)) > _BEAT_MAX_SPAN):
            beats.append(current)
            current = []
        current.append(w)
        prev_end = end
    if current:
        beats.append(current)
    return beats


def _pop_color(chosen: List[Dict[str, Any]], topic: Optional[str]) -> str:
    """Colour role for a pop phrase: red (bad/old) beats green (power/
    money/number) beats blue (key term) beats white (neutral)."""
    cleaned = [_clean_word(w.get("word", "")) for w in chosen]
    raw = [str(w.get("word", "")) for w in chosen]
    if any(c in _NEGATIVE_WORDS for c in cleaned):
        return "bad"
    if any(c in _EMPHASIS_WORDS or c in _GOOD_WORDS or c in _MONEY_WORDS
           for c in cleaned) or any(re.search(r"\d", r) or r.startswith("$") for r in raw):
        return "good"
    if topic is not None and topic in cleaned:
        return "key"
    return "neutral"


def _find_keyword_pops(
    words: List[Dict[str, Any]],
    duration: float,
    card_span: Optional[Tuple[float, float]],
) -> List[Dict[str, Any]]:
    """One keyword_pop per speech beat: the salient 1-3 word phrase
    around the beat's highest-scoring word, with its colour role. Pops
    start ON the spoken phrase, hold >= 0.7s, cap at 2.5s, never overlap
    each other, and never overlap the card_sequence span (the list owns
    that window). Beats with no content word get no pop. Capped at 40."""
    topic = _topic_word(words)
    pops: List[Dict[str, Any]] = []
    for beat in _speech_beats(words):
        if not beat:
            continue
        anchor_idx = max(range(len(beat)), key=lambda i: (_pop_score(beat[i], topic), -i))
        anchor = beat[anchor_idx]
        if _pop_score(anchor, topic) < 1:
            continue  # pure filler beat: no pop, silence between pops is fine
        # Contiguous window of up to 3 words containing the anchor:
        # expanding past stop words produced Frankenstein phrases
        # ("leaders media only" spans 6 spoken words). Prefer the window
        # with the most content words (centred wins ties), then trim
        # leading/trailing stop words — the anchor always survives.
        best_window = None
        best_key = None
        for lo in range(max(0, anchor_idx - 2), anchor_idx + 1):
            window = beat[lo:min(lo + 3, len(beat))]
            content_count = sum(1 for w in window if _is_pop_content(w))
            rank = 0 if lo == anchor_idx - 1 else (1 if lo == anchor_idx else 2)
            key = (content_count, -rank)
            if best_key is None or key > best_key:
                best_key = key
                best_window = window
        chosen = list(best_window or [anchor])
        while len(chosen) > 1 and not _is_pop_content(chosen[0]):
            chosen.pop(0)
        while len(chosen) > 1 and not _is_pop_content(chosen[-1]):
            chosen.pop()
        phrase = " ".join(_display_word(w) for w in chosen).strip()
        if not phrase:
            continue
        start = max(0.0, float(chosen[0].get("start", 0.0)))
        end = float(chosen[-1].get("end", start + 0.3))
        end = min(max(end, start + _POP_MIN_HOLD), start + _POP_MAX_LEN, duration)
        if end - start < 0.5 or start >= duration:
            continue
        if card_span and start < card_span[1] + 0.2 and end > card_span[0] - 0.2:
            continue
        pops.append({
            "type": "keyword_pop", "graphic": "Keyword pop",
            "start": round(start, 3), "end": round(end, 3),
            "title": phrase, "text": phrase,
            "color": _pop_color(chosen, topic),
            "score": _pop_score(anchor, topic),
        })
    # Pops must never overlap each other: clamp each end to the next pop's
    # start when >= 0.5s remains (the next pop owns its beat).
    pops.sort(key=lambda p: p["start"])
    for i in range(len(pops) - 1):
        nxt = pops[i + 1]["start"]
        if pops[i]["end"] > nxt and nxt - pops[i]["start"] >= 0.5:
            pops[i]["end"] = round(nxt, 3)
    return pops[:_MAX_KEYWORD_POPS]


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
    keyword_punch: bool = False,
) -> Dict[str, Any]:
    """Plan timed graphic segments from the transcript.

    Returns {"segments": [...], "blocks": [...], "clips": [...]}. Segments
    are the visible plan (type/start/end/text); blocks+clips are the EDL
    shapes inject_plan_into_edl() appends to the job. With keyword_punch
    (Batch 5) the plan is keyword pops + restraint: no hook title card,
    pops own the timeline, other graphics only in gaps.
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
                     title: str, text: str, extra: Optional[Dict[str, Any]] = None,
                     seg_extra: Optional[Dict[str, Any]] = None):
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
        seg = {
            "type": seg_type, "start": round(start, 3), "end": round(end, 3),
            "text": title or text, "graphic": graphic,
        }
        if seg_extra:
            seg.update(seg_extra)
        segments.append(seg)
        return (start, end)

    if keyword_punch:
        # Batch 5 keyword punch: NO hook title card — the first keyword
        # pop IS the hook. The card sequence (genuine lists only, same
        # 3+ marker rule) reserves its span; pops cover everything else;
        # proof cards/pills render ONLY in gaps no pop covers (one text
        # on screen at a time — pops win); zooms punch in on pop beats.
        punch_card_info = _find_card_sequence(words) if words else None
        punch_card_span = None
        if punch_card_info:
            end = min(duration, max(punch_card_info["end"], punch_card_info["start"] + 2.0))
            punch_card_span = _add_graphic(
                "card_sequence", "card sequence", punch_card_info["start"], end,
                f"{len(punch_card_info['cards'])} steps",
                " ".join(c["label"] for c in punch_card_info["cards"] if c["label"]),
                extra={"cards": punch_card_info["cards"]},
            )
        punch_pops = _find_keyword_pops(words, duration, punch_card_span) if words else []
        pop_spans: List[Tuple[float, float]] = []
        scored_pops: List[Tuple[int, float, float]] = []
        for pop in punch_pops:
            span = _add_graphic(
                "keyword_pop", "Keyword pop", pop["start"], pop["end"],
                pop["title"], pop["text"],
                extra={"color_role": pop["color"]},
                seg_extra={"color": pop["color"]},
            )
            if span:
                pop_spans.append(span)
                scored_pops.append((pop["score"], span[0], span[1]))
        blocked = list(pop_spans)
        if punch_card_span:
            blocked.append(punch_card_span)
        punch_emphasis = _find_emphasis(
            words, duration, punch_card_span, False,
            blocked_spans=blocked) if words else []
        for item in punch_emphasis:
            _add_graphic(
                item["type"], item["graphic"], item["start"], item["end"],
                item["title"], item["text"],
            )
        # Zooms: the first pop (hook punch) + the 3 strongest pops, max 4.
        zoom_windows = set()
        if pop_spans:
            zoom_windows.add(pop_spans[0])
        for _score, s, e in sorted(scored_pops, key=lambda t: (-t[0], t[1]))[:3]:
            zoom_windows.add((s, e))
        for (z_start, z_end) in sorted(zoom_windows)[:4]:
            z_end = max(z_end, min(duration, z_start + 1.0))
            if z_end - z_start < 1.0:
                continue
            idx = len(clips)
            clips.append({
                "id": f"v2_plan_zoom_{idx}",
                "graphic": "zoom",
                "amount": 0.12,
                "in": 0.0,
                "out": round(z_end - z_start, 3),
                "at": round(z_start, 3),
                "duration": round(z_end - z_start, 3),
            })
            segments.append({
                "type": "zoom", "start": round(z_start, 3), "end": round(z_end, 3),
                "text": "punch-in 12%", "graphic": "zoom",
            })
        segments.sort(key=lambda s: s["start"])
        return {"segments": segments, "blocks": blocks, "clips": clips}

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
    "keyword_pop": "Keyword pop",
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
        if seg_type == "keyword_pop":
            clip["color_role"] = str(seg.get("color") or "neutral").strip().lower() or "neutral"
        blocks.append(block)
        clips.append(clip)
        visible_seg = {
            "type": seg_type, "start": round(start, 3), "end": round(end, 3),
            "text": title or text, "graphic": graphic,
        }
        if seg_type == "keyword_pop":
            visible_seg["color"] = clip["color_role"]
        visible.append(visible_seg)

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
