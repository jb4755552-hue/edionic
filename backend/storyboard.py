"""
Edionic Phase 3 — Storyboard-First Engine (`storyboard.py`)
1. Defines and validates Storyboard JSON (`title`, `blocks` with `id`, `title`, `text`, `start`, `end`, `visual`, `graphic`, `sfx`).
2. Builds a Storyboard automatically from transcribed words + silence-cut segments or user script.
3. Generates a standalone One-Page Interactive HTML Storyboard Preview (`storyboard_preview.html`)
   allowing edits to `title`, `text`, `start`, `end`, `visual`, `graphic`, `sfx` with one-click JSON export.
4. Supports bidirectional round-trip (`roundtrip_storyboard_edits_to_edl`):
   edits made to Storyboard blocks update `.edl.json` (or `editor-job.json`) tracks (`V2` overlay graphics,
   `CC` caption words/phrases, `sfx` placements, and `storyboard.blocks`) without losing timing sync.
"""

import json
import os
from typing import Dict, Any, List, Optional

REQUIRED_BLOCK_FIELDS = ("id", "title", "text", "start", "end", "visual", "graphic", "sfx")


def normalize_storyboard(storyboard_data: Optional[Dict[str, Any]], total_duration: float = 5.0) -> Dict[str, Any]:
    """Validate and normalize a storyboard dictionary ensuring all required fields exist on every block.

    An empty/missing block list stays EMPTY (Batch 4 fix): the old code
    regenerated two factory-default blocks (b0 "Hook Beat", b1 "Core
    Value") whose graphics made the motion planner believe the job had
    manual graphics, silently disabling planning on every default render.
    Empty input means "no authored storyboard" — the planner plans from
    the transcript instead.
    """
    raw = storyboard_data or {}
    title = str(raw.get("title") or "Edionic 9:16 Storyboard Plan").strip()
    raw_blocks = raw.get("blocks") or []

    if not raw_blocks:
        return {"title": title, "blocks": []}

    normalized_blocks: List[Dict[str, Any]] = []
    for idx, blk in enumerate(raw_blocks):
        b_id = str(blk.get("id") or f"b{idx}")
        b_title = str(blk.get("title") or b_id)
        b_text = str(blk.get("text") or "")
        b_start = round(max(0.0, float(blk.get("start", idx * 1.5))), 3)
        b_end = round(max(b_start + 0.25, float(blk.get("end", b_start + 1.5))), 3)
        b_visual = str(blk.get("visual") or "Face-anchored 9:16 frame")
        b_graphic = str(blk.get("graphic") or "Caption overlay")
        b_sfx = str(blk.get("sfx") or "whoosh")
        normalized_blocks.append({
            "id": b_id,
            "title": b_title,
            "text": b_text,
            "start": b_start,
            "end": b_end,
            "visual": b_visual,
            "graphic": b_graphic,
            "sfx": b_sfx
        })

    return {
        "title": title,
        "blocks": normalized_blocks
    }


def generate_storyboard_from_transcript(
    words: List[Dict[str, Any]],
    edited_duration: float,
    title: str = "Edionic Storyboard Plan"
) -> Dict[str, Any]:
    """Group transcribed words into 2–4 narrative storyboard beats with visual/graphic/SFX cues."""
    if not words:
        return normalize_storyboard(None, edited_duration)

    chunk_size = max(3, (len(words) + 2) // 3)
    blocks: List[Dict[str, Any]] = []
    sfx_cycle = ["riser", "whoosh", "pop", "ding"]
    visual_cycle = [
        "Speaker close-up (Hook 9:16)",
        "Face-anchored 9:16 + B-roll insert",
        "Dynamic punch-in 9:16 frame",
        "Call-to-action closing frame"
    ]
    graphic_cycle = [
        "Title card",
        "Lower pill highlight",
        "Glowing keyword emphasis",
        "Summary callout badge"
    ]

    for b_idx, i in enumerate(range(0, len(words), chunk_size)):
        w_slice = words[i : i + chunk_size]
        phrase = " ".join(str(w.get("word", "")).strip() for w in w_slice).strip()
        start_s = round(float(w_slice[0].get("start", 0.0)), 3)
        end_s = round(float(w_slice[-1].get("end", min(edited_duration, start_s + 1.5))), 3)
        if b_idx == 0:
            start_s = 0.0
        blocks.append({
            "id": f"b{b_idx}",
            "title": f"Beat {b_idx + 1}",
            "text": phrase,
            "start": start_s,
            "end": max(start_s + 0.3, end_s),
            "visual": visual_cycle[b_idx % len(visual_cycle)],
            "graphic": graphic_cycle[b_idx % len(graphic_cycle)],
            "sfx": sfx_cycle[b_idx % len(sfx_cycle)]
        })

    return normalize_storyboard({"title": title, "blocks": blocks}, edited_duration)


def generate_storyboard_html_preview(
    storyboard_data: Dict[str, Any],
    output_html_path: str
) -> str:
    """
    Render a standalone One-Page HTML Storyboard Preview (`storyboard_preview.html`)
    with live editable fields and round-trip JSON export.
    """
    sb = normalize_storyboard(storyboard_data)
    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)

    cards_html = []
    for idx, blk in enumerate(sb["blocks"]):
        cards_html.append(f"""
        <div class="sb-card" data-id="{blk['id']}">
          <div class="sb-card-header">
            <span class="sb-id">#{idx + 1} · {blk['id']}</span>
            <span class="sb-time">{blk['start']:.2f}s – {blk['end']:.2f}s</span>
          </div>
          <label>Beat Title</label>
          <input class="sb-input" data-field="title" value="{blk['title']}" />
          <label>Spoken / Caption Text</label>
          <textarea class="sb-input" data-field="text" rows="2">{blk['text']}</textarea>
          <div class="sb-row">
            <div>
              <label>Visual Direction</label>
              <input class="sb-input" data-field="visual" value="{blk['visual']}" />
            </div>
            <div>
              <label>Graphic Overlay</label>
              <input class="sb-input" data-field="graphic" value="{blk['graphic']}" />
            </div>
            <div>
              <label>SFX Cue</label>
              <input class="sb-input" data-field="sfx" value="{blk['sfx']}" />
            </div>
          </div>
        </div>
        """)

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Edionic Storyboard Preview — {sb['title']}</title>
  <style>
    body {{
      font-family: 'Inter Tight', system-ui, sans-serif;
      background: #F4F5F7;
      color: #11141C;
      margin: 0;
      padding: 28px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      max-width: 1040px;
      margin: 0 auto 20px auto;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      max-width: 1040px;
      margin: 0 auto;
    }}
    .sb-card {{
      background: #FFFFFF;
      border: 1px solid #D8DEE9;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 4px 12px rgba(17,20,28,0.05);
    }}
    .sb-card-header {{
      display: flex;
      justify-content: space-between;
      font-weight: 700;
      margin-bottom: 10px;
      color: #3B63FF;
    }}
    label {{
      display: block;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      color: #4B5563;
      margin: 8px 0 4px 0;
    }}
    .sb-input {{
      width: 100%;
      box-sizing: border-box;
      padding: 7px 10px;
      border: 1px solid #CBD5E1;
      border-radius: 6px;
      font-size: 13px;
    }}
    .sb-row {{
      display: grid;
      grid-template-columns: 1fr 1fr 90px;
      gap: 8px;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1 style="margin:0;font-size:22px;">Storyboard-First Plan: {sb['title']}</h1>
      <p style="margin:4px 0 0 0;font-size:13px;color:#4B5563;">One-page interactive preview · Round-trips directly into .edl.json &amp; pipeline_v3.py</p>
    </div>
  </div>
  <div class="grid">
    {"".join(cards_html)}
  </div>
  <script id="storyboard-json-data" type="application/json">{json.dumps(sb, indent=2)}</script>
</body>
</html>
"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return output_html_path


def roundtrip_storyboard_edits_to_edl(
    edl_data: Dict[str, Any],
    updated_storyboard: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Round-trip edits made in the Storyboard back into the `.edl.json` / `editor-job.json` plan:
    1. Updates `edl_data["storyboard"]` with normalized blocks.
    2. Rebuilds Track `V2` overlay graphics clips from each block's `graphic` & `visual` fields
       (unless `V2` is locked in `overrides.locked_tracks`).
    3. Rebuilds `CC` word timestamps from edited `block.text` spans so edited words appear in rendered captions
       (unless `CC` is locked).
    4. Syncs `block.sfx` cues into `edl_data["sfx"]` at each block's transition timestamp.
    """
    norm_sb = normalize_storyboard(updated_storyboard)
    edl_data["storyboard"] = norm_sb

    locked_tracks = set((edl_data.get("overrides") or {}).get("locked_tracks") or [])
    for t in edl_data.get("tracks", []):
        if t.get("locked"):
            locked_tracks.add(t.get("id"))

    # 1. Sync first block title/text to title_text if light_sweep_title or hook banner is used.
    # Placeholder titles ("b0", "Beat 1", "hook") must NOT overwrite a real
    # title_text: template hook blocks carry title "hook" while the template
    # already set a meaningful title_text (Batch 3 graphics read it).
    if norm_sb["blocks"]:
        first_blk = norm_sb["blocks"][0]
        if first_blk.get("title") and first_blk["title"] not in ("b0", "Beat 1", "hook"):
            edl_data["title_text"] = first_blk["title"]

    # 2. Rebuild V2 Overlay clips & CC Caption words from storyboard blocks (if not locked)
    v2_clips: List[Dict[str, Any]] = []
    rebuilt_words: List[Dict[str, Any]] = []
    rebuilt_sfx: List[Dict[str, Any]] = []

    for idx, blk in enumerate(norm_sb["blocks"]):
        b_start = float(blk["start"])
        b_end = float(blk["end"])
        b_dur = max(0.25, b_end - b_start)

        v2_clips.append({
            "id": f"v2_{blk['id']}",
            "block_id": blk["id"],
            "title": blk["title"],
            "graphic": blk["graphic"],
            "visual": blk["visual"],
            "in": 0.0,
            "out": round(b_dur, 3),
            "at": round(b_start, 3),
            "duration": round(b_dur, 3)
        })

        raw_tokens = [tok.strip() for tok in blk["text"].split() if tok.strip()]
        if raw_tokens:
            w_dur = b_dur / len(raw_tokens)
            for w_idx, tok in enumerate(raw_tokens):
                w_s = round(b_start + w_idx * w_dur, 3)
                w_e = round(min(b_end, w_s + max(0.16, w_dur)), 3)
                rebuilt_words.append({
                    "word": tok,
                    "start": w_s,
                    "end": w_e,
                    "orig_start": w_s,
                    "orig_end": w_e,
                    "prob": 0.99,
                    "block_id": blk["id"]
                })

        if blk.get("sfx"):
            placed_t = round(max(0.2, b_start if idx > 0 else min(1.0, b_end * 0.5)), 3)
            rebuilt_sfx.append({
                "name": blk["sfx"],
                "placed_at_s": placed_t,
                "from_block": blk["id"]
            })

    for track in edl_data.get("tracks", []):
        tid = track.get("id")
        if tid == "V2" and "V2" not in locked_tracks:
            track["clips"] = v2_clips
        elif tid == "CC" and "CC" not in locked_tracks and rebuilt_words:
            track["clips"] = rebuilt_words

    if rebuilt_sfx and "A1" not in locked_tracks:
        existing_sfx = edl_data.get("sfx") or []
        merged_sfx = list(rebuilt_sfx)
        for s in existing_sfx:
            if len(merged_sfx) < 5 and all(abs(float(s.get("placed_at_s", 0)) - float(m["placed_at_s"])) > 0.35 for m in merged_sfx):
                merged_sfx.append(s)
        edl_data["sfx"] = merged_sfx

    return edl_data
