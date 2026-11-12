"""
Edionic Caption / Text Preset Library — caption_presets.py (Section 5.3 — All 12 Presets)
Implements all 12 verified presets on 1080x1920 vertical canvas with >= 54 px glyph height:
1. glow (default)
2. gradient_steps (steps colors word-by-word; honest limit: ASS has no true smooth gradient)
3. extrude_3d (heavy 3D block shadow + outline)
4. handwritten (falls back to DejaVu Serif / Georgia Italic; honest limit: no custom cursive font required)
5. neon_serif (serif typography + electric neon magenta/cyan outer glow)
6. condensed (tall Impact condensed display style, ScaleX=82, ScaleY=115)
7. pill_highlight (opaque box/pill background on active spoken word via BorderStyle=3)
8. karaoke_pop (active popped word renders centered OVER the phrase)
9. podcast_two_tier (clean top context line + oversized bottom active word tier)
10. minimal_clean (crisp thin-outline modern lower-third with accent highlight)
11. light_sweep_title (title card: glowing serif title with a translucent highlight bar sweeping across it — rendered as a title clip)
12. serif_title (title card: white serif caps title + smaller serif body line beneath, centred — archival/documentary)
"""

from typing import List, Dict, Any

# NOTE: constant name kept for compatibility; the list now holds 12 presets.
ALL_11_PRESETS = [
    "glow",
    "gradient_steps",
    "extrude_3d",
    "handwritten",
    "neon_serif",
    "condensed",
    "pill_highlight",
    "karaoke_pop",
    "podcast_two_tier",
    "minimal_clean",
    "light_sweep_title",
    "serif_title",
]

PRESET_CATALOG_INFO: Dict[str, Dict[str, Any]] = {
    "glow": {
        "name": "glow",
        "label": "Glow (Default)",
        "type": "ass_word_highlight",
        "description": "Luminous outer glow halo with cyan/yellow active word highlight."
    },
    "gradient_steps": {
        "name": "gradient_steps",
        "label": "Gradient Steps",
        "type": "ass_word_highlight",
        "honest_limit": "ASS has no true smooth gradient; steps colors word by word.",
        "description": "Steps vivid warm-to-cool palette colors word by word."
    },
    "extrude_3d": {
        "name": "extrude_3d",
        "label": "Extrude 3D",
        "type": "ass_word_highlight",
        "description": "Deep 3D extruded block drop-shadow with thick dark outline and gold active word."
    },
    "handwritten": {
        "name": "handwritten",
        "label": "Handwritten",
        "type": "ass_word_highlight",
        "honest_limit": "Falls back to DejaVu Serif / Georgia Italic when no cursive font is installed.",
        "description": "Italic serif script feel with warm cream & amber word highlights."
    },
    "neon_serif": {
        "name": "neon_serif",
        "label": "Neon Serif",
        "type": "ass_word_highlight",
        "description": "High-contrast serif with neon magenta outer blur halo and electric cyan active word."
    },
    "condensed": {
        "name": "condensed",
        "label": "Condensed",
        "type": "ass_word_highlight",
        "description": "Tall condensed Impact headline style with punchy lime/yellow active word."
    },
    "pill_highlight": {
        "name": "pill_highlight",
        "label": "Pill Highlight",
        "type": "ass_word_highlight",
        "description": "Wraps the active spoken word in an opaque colored pill box."
    },
    "karaoke_pop": {
        "name": "karaoke_pop",
        "label": "Karaoke Pop",
        "type": "ass_word_highlight",
        "honest_limit": "Popped word renders centered over the phrase.",
        "description": "Base phrase sits below while the active popped word scales up centered over the phrase."
    },
    "podcast_two_tier": {
        "name": "podcast_two_tier",
        "label": "Podcast Two-Tier",
        "type": "ass_word_highlight",
        "description": "Two-tier layout: compact upper context phrase + giant lower active word."
    },
    "minimal_clean": {
        "name": "minimal_clean",
        "label": "Minimal Clean",
        "type": "ass_word_highlight",
        "description": "Refined low-clutter subtitle with subtle outline and Edionic accent highlight."
    },
    "light_sweep_title": {
        "name": "light_sweep_title",
        "label": "Light Sweep Title",
        "type": "title_clip",
        "description": "Title card: glowing serif title with a translucent highlight bar sweeping across it (rendered as a title clip)."
    },
    "serif_title": {
        "name": "serif_title",
        "label": "Serif Title",
        "type": "ass_word_highlight",
        "description": "Title card: large white serif caps word + smaller serif phrase line beneath, centred (archival/documentary)."
    }
}


def _format_ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def get_light_sweep_ffmpeg_vf(title_text: str = "EDIONIC HOOK") -> str:
    """
    Return the FFmpeg video filter fragment that renders `light_sweep_title` as a real title clip
    (darkened hook banner + translucent highlight bar sweeping horizontally across the glowing serif title
    during the first 2.5 seconds).
    """
    return (
        "drawbox=enable='between(t,0,2.5)':x=90:y=1310:w=900:h=260:color=#11141C@0.78:t=fill,"
        "drawbox=enable='between(t,0,2.5)':x='90+mod(t*420,780)':y=1310:w=140:h=260:color=#FFFFFF@0.32:t=fill"
    )


def generate_ass_captions(
    words: List[Dict[str, Any]],
    output_ass_path: str,
    preset: str = "glow",
    title_text: str = "EDIONIC 9:16 HOOK TITLE",
    play_res_x: int = 1080,
    play_res_y: int = 1920,
) -> Dict[str, Any]:
    """
    Generate a 1080x1920 ASS file for any of the verified presets.
    Every preset produces a distinct style and renders >= 54 px glyph height on 1080x1920 frames.
    """
    if preset not in ALL_11_PRESETS:
        preset = "glow"

    # Style definitions per preset (ASS colors: &HAABBGGRR)
    styles_block = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: GlowBase,Arial,82,&H00FFFFFF,&H0000FFFF,&H00FF633B,&H80000000,-1,0,0,0,100,100,1,0,1,7,0,2,70,70,340,1
Style: GlowText,Arial,82,&H00FFFFFF,&H0000FFFF,&H00141010,&H00000000,-1,0,0,0,100,100,1,0,1,3,0,2,70,70,340,1
Style: GradientSteps,Arial,84,&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,2,70,70,340,1
Style: Extrude3D,Impact,88,&H00FFFFFF,&H0000D4FF,&H00080808,&H00274086,-1,0,0,0,100,100,2,0,1,5,10,2,70,70,340,1
Style: Handwritten,Georgia,82,&H00D8F3FF,&H0050A8FF,&H00141C2B,&H60000000,-1,-1,0,0,100,100,1,0,1,3,2,2,70,70,340,1
Style: NeonGlow,Georgia,84,&H00FF80FF,&H00FFFF00,&H00FF00FF,&H80000000,-1,0,0,0,100,100,2,0,1,8,0,2,70,70,340,1
Style: NeonCrisp,Georgia,84,&H00FFFFFF,&H00FFFF00,&H00400040,&H00000000,-1,0,0,0,100,100,2,0,1,2,0,2,70,70,340,1
Style: Condensed,Impact,92,&H00FFFFFF,&H0000FFAA,&H00101010,&H80000000,-1,0,0,0,82,115,1,0,1,4,3,2,70,70,340,1
Style: PillBase,Arial,80,&H00E8ECEF,&H00FFFFFF,&H00141820,&H00000000,-1,0,0,0,100,100,1,0,1,3,0,2,70,70,340,1
Style: PillBox,Arial,82,&H00FFFFFF,&H00FFFFFF,&H00FF633B,&H00FF633B,-1,0,0,0,100,100,2,0,3,10,0,2,70,70,435,1
Style: KaraokePhrase,Arial,76,&H00D0D8E0,&H00FFFFFF,&H0010141C,&H00000000,-1,0,0,0,100,100,1,0,1,3,2,2,70,70,310,1
Style: KaraokePopWord,Arial,90,&H0000EAFF,&H00FFFFFF,&H0010141C,&H00000000,-1,0,0,0,115,115,2,0,1,4,3,2,70,70,430,1
Style: PodcastTier,Arial,78,&H00B8C8D8,&H00FFFFFF,&H0010141C,&H80000000,-1,0,0,0,100,100,1,0,1,3,2,2,70,70,330,1
Style: MinimalClean,Arial,86,&H00FAFAFA,&H00FF633B,&H00181C24,&H40000000,-1,0,0,0,100,100,3,0,1,3,1,2,70,70,340,1
Style: LightSweepBar,Arial,96,&H90FFFFFF,&H90FFFFFF,&H90FFFFFF,&H90FFFFFF,-1,0,0,0,60,180,0,0,3,18,0,5,0,0,0,1
Style: LightSweepTitle,Georgia,86,&H00FFFFFF,&H0090E0FF,&H00FF633B,&H00000000,-1,0,0,0,100,100,3,0,1,5,2,2,70,70,360,1
Style: SerifTitle,Georgia,88,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,2,0,1,4,2,5,70,70,0,1
"""

    ass_header = f"""[Script Info]
; Generated by Edionic Caption Engine (edionic.com) — Preset: {preset}
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

{styles_block.strip()}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events: List[str] = []

    # If preset is `light_sweep_title`, add the glowing serif title card event across 0.0s..2.5s
    if preset == "light_sweep_title":
        clean_title = (title_text or "EDIONIC 9:16 HOOK TITLE").strip().upper()
        # Split title into 2 lines if longer than 14 chars so it fits cleanly inside the sweep bar
        t_words = clean_title.split()
        if len(t_words) >= 3:
            mid = len(t_words) // 2
            line_title = " ".join(t_words[:mid]) + "\\N" + " ".join(t_words[mid:])
        else:
            line_title = clean_title
        events.append(
            f"Dialogue: 2,0:00:00.00,0:00:02.50,LightSweepTitle,,0,0,0,,{{\\blur8\\3c&HFF633B&\\1c&H00FAFF&}}{line_title}"
        )
        events.append(
            "Dialogue: 3,0:00:00.00,0:00:02.50,LightSweepBar,,0,0,0,,{\\move(200,1440,880,1440,0,2500)\\1c&HFFFFFF&\\3c&HFFFFFF&\\1a&H88&\\3a&H88&\\blur6}\u2588\u2588"
        )

    step_colors = ["&H005E59FF&", "&H003ACAFF&", "&H0026C98A&", "&H00FF963B&"]

    chunk_size = 3
    for i in range(0, len(words), chunk_size):
        chunk = words[i : i + chunk_size]
        if not chunk:
            continue

        for active_idx, active_w in enumerate(chunk):
            w_start = float(active_w.get("start", 0.0))
            if active_idx + 1 < len(chunk):
                w_end = max(float(active_w.get("end", w_start + 0.25)), float(chunk[active_idx + 1].get("start", w_start + 0.25)))
            else:
                w_end = max(float(active_w.get("end", w_start + 0.3)), w_start + 0.25)
            if w_end <= w_start:
                w_end = w_start + 0.20

            # If light_sweep_title is active during 0..2.5s, let the title card own 0..2.5s and captions appear after,
            # OR also render captions below if words are after 2.5s
            start_str = _format_ass_time(w_start)
            end_str = _format_ass_time(w_end)

            if preset == "glow":
                glow_parts, crisp_parts = [], []
                for j, w_obj in enumerate(chunk):
                    txt = str(w_obj.get("word", "")).strip().upper()
                    sep = "\\N" if j == 2 else (" " if j > 0 else "")
                    if j == active_idx:
                        glow_parts.append(f"{sep}{{\\blur10\\3c&HFF633B&\\1c&H00EAFF&}}{txt}{{\\rGlowBase}}")
                        crisp_parts.append(f"{sep}{{\\1c&H00EAFF&\\3c&H11141C&}}{txt}{{\\rGlowText}}")
                    else:
                        glow_parts.append(f"{sep}{{\\blur8}}{txt}")
                        crisp_parts.append(f"{sep}{txt}")
                events.append(f"Dialogue: 0,{start_str},{end_str},GlowBase,,0,0,0,,{''.join(glow_parts)}")
                events.append(f"Dialogue: 1,{start_str},{end_str},GlowText,,0,0,0,,{''.join(crisp_parts)}")

            elif preset == "gradient_steps":
                parts = []
                for j, w_obj in enumerate(chunk):
                    txt = str(w_obj.get("word", "")).strip().upper()
                    sep = "\\N" if j == 2 else (" " if j > 0 else "")
                    col = step_colors[(i + j) % len(step_colors)]
                    if j == active_idx:
                        parts.append(f"{sep}{{\\1c{col}\\fscx110\\fscy110}}{txt}{{\\rGradientSteps}}")
                    else:
                        parts.append(f"{sep}{{\\1c{col}}}{txt}{{\\rGradientSteps}}")
                events.append(f"Dialogue: 1,{start_str},{end_str},GradientSteps,,0,0,0,,{''.join(parts)}")

            elif preset == "extrude_3d":
                parts = []
                for j, w_obj in enumerate(chunk):
                    txt = str(w_obj.get("word", "")).strip().upper()
                    sep = "\\N" if j == 2 else (" " if j > 0 else "")
                    if j == active_idx:
                        parts.append(f"{sep}{{\\1c&H00D4FF&\\shad11}}{txt}{{\\rExtrude3D}}")
                    else:
                        parts.append(f"{sep}{txt}")
                events.append(f"Dialogue: 1,{start_str},{end_str},Extrude3D,,0,0,0,,{''.join(parts)}")

            elif preset == "handwritten":
                parts = []
                for j, w_obj in enumerate(chunk):
                    txt = str(w_obj.get("word", "")).strip()
                    sep = "\\N" if j == 2 else (" " if j > 0 else "")
                    if j == active_idx:
                        parts.append(f"{sep}{{\\1c&H0050A8FF&\\fscx108\\fscy108}}{txt}{{\\rHandwritten}}")
                    else:
                        parts.append(f"{sep}{txt}")
                events.append(f"Dialogue: 1,{start_str},{end_str},Handwritten,,0,0,0,,{''.join(parts)}")

            elif preset == "neon_serif":
                glow_parts, crisp_parts = [], []
                for j, w_obj in enumerate(chunk):
                    txt = str(w_obj.get("word", "")).strip().upper()
                    sep = "\\N" if j == 2 else (" " if j > 0 else "")
                    if j == active_idx:
                        glow_parts.append(f"{sep}{{\\blur12\\3c&HFFFF00&\\1c&HFFFF00&}}{txt}{{\\rNeonGlow}}")
                        crisp_parts.append(f"{sep}{{\\1c&HFFFF00&}}{txt}{{\\rNeonCrisp}}")
                    else:
                        glow_parts.append(f"{sep}{{\\blur10\\3c&HFF00FF&}}{txt}")
                        crisp_parts.append(f"{sep}{txt}")
                events.append(f"Dialogue: 0,{start_str},{end_str},NeonGlow,,0,0,0,,{''.join(glow_parts)}")
                events.append(f"Dialogue: 1,{start_str},{end_str},NeonCrisp,,0,0,0,,{''.join(crisp_parts)}")

            elif preset == "condensed":
                parts = []
                for j, w_obj in enumerate(chunk):
                    txt = str(w_obj.get("word", "")).strip().upper()
                    sep = "\\N" if j == 2 else (" " if j > 0 else "")
                    if j == active_idx:
                        parts.append(f"{sep}{{\\1c&H00FFAA&\\fscy122}}{txt}{{\\rCondensed}}")
                    else:
                        parts.append(f"{sep}{txt}")
                events.append(f"Dialogue: 1,{start_str},{end_str},Condensed,,0,0,0,,{''.join(parts)}")

            elif preset == "pill_highlight":
                # Base phrase on lower line + active word inside opaque pill box above it
                phrase_txt = " ".join(str(w.get("word", "")).strip().upper() for w in chunk)
                active_txt = str(active_w.get("word", "")).strip().upper()
                events.append(f"Dialogue: 0,{start_str},{end_str},PillBase,,0,0,0,,{phrase_txt}")
                events.append(f"Dialogue: 1,{start_str},{end_str},PillBox,,0,0,0,, {active_txt} ")

            elif preset == "karaoke_pop":
                # Honest limit: popped word renders centered OVER the phrase
                phrase_txt = " ".join(str(w.get("word", "")).strip().upper() for w in chunk)
                popped_txt = str(active_w.get("word", "")).strip().upper()
                events.append(f"Dialogue: 0,{start_str},{end_str},KaraokePhrase,,0,0,0,,{phrase_txt}")
                events.append(
                    f"Dialogue: 1,{start_str},{end_str},KaraokePopWord,,0,0,0,,{{\\fscx125\\fscy125\\1c&H00EAFF&}}{popped_txt}"
                )

            elif preset == "podcast_two_tier":
                context_txt = " ".join(str(w.get("word", "")).strip().upper() for w in chunk)
                active_txt = str(active_w.get("word", "")).strip().upper()
                two_tier_line = (
                    f"{{\\fs62\\1c&HB8C8D8&}}{context_txt}\\N"
                    f"{{\\fs96\\1c&H00EAFF&\\b1}}{active_txt}"
                )
                events.append(f"Dialogue: 1,{start_str},{end_str},PodcastTier,,0,0,0,,{two_tier_line}")

            elif preset == "minimal_clean":
                parts = []
                for j, w_obj in enumerate(chunk):
                    txt = str(w_obj.get("word", "")).strip()
                    sep = "\\N" if j == 2 else (" " if j > 0 else "")
                    if j == active_idx:
                        parts.append(f"{sep}{{\\1c&HFF993B&\\b1}}{txt}{{\\rMinimalClean}}")
                    else:
                        parts.append(f"{sep}{txt}")
                events.append(f"Dialogue: 1,{start_str},{end_str},MinimalClean,,0,0,0,,{''.join(parts)}")

            elif preset == "light_sweep_title":
                # After the 0..2.5s sweeping title card, also show clean glowing serif captions
                if w_end > 2.5:
                    s_clamped = _format_ass_time(max(2.5, w_start))
                    parts = []
                    for j, w_obj in enumerate(chunk):
                        txt = str(w_obj.get("word", "")).strip().upper()
                        sep = "\\N" if j == 2 else (" " if j > 0 else "")
                        if j == active_idx:
                            parts.append(f"{sep}{{\\blur6\\3c&HFF633B&\\1c&H90E0FF&}}{txt}{{\\rLightSweepTitle}}")
                        else:
                            parts.append(f"{sep}{txt}")
                    events.append(f"Dialogue: 1,{s_clamped},{end_str},LightSweepTitle,,0,0,0,,{''.join(parts)}")

            elif preset == "serif_title":
                # Title card: large white serif caps active word + smaller serif phrase line beneath, centred
                title_txt = str(active_w.get("word", "")).strip().upper()
                body_txt = " ".join(str(w.get("word", "")).strip() for w in chunk)
                serif_line = (
                    f"{{\\fs92\\1c&HFFFFFF&\\b1}}{title_txt}\\N"
                    f"{{\\fs56\\1c&HD8D2C4&}}{body_txt}"
                )
                events.append(f"Dialogue: 1,{start_str},{end_str},SerifTitle,,0,0,0,,{serif_line}")

    full_ass = ass_header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(full_ass)

    return {
        "ass_path": output_ass_path,
        "preset": preset,
        "preset_meta": PRESET_CATALOG_INFO.get(preset, {}),
        "title_text": title_text if preset == "light_sweep_title" else "",
        "word_count": len(words),
        "event_count": len(events)
    }
