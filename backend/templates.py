"""
Edionic Reel Template Registry — templates.py

One template per reel-template category (reel-template-categories.md,
2026-11-11 + Category 11 gaming, 2026-11-12). Selecting a template fills an
editor job with that template's bundle: caption preset, style preset, SFX
defaults, storyboard hook block, title text, pacing, layout and music bed.

Sound honesty: SFX maps and music beds are RECOMMENDED placements from
Edionic's own 10-sound SFX system. Per-reel SFX timings were NOT verified
from the analysed reels, and no real track name is bundled or claimed here.

Reels only. No long-video mode, no chunking (owner order, 2026-11-11).
"""

import copy
from typing import Dict, Any, List, Optional

TEMPLATE_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "saas_dark_premium",
        "name": "SaaS Motion Explainer — Dark Premium",
        "category": "SaaS Motion Explainer",
        "feel": "Dark, premium, space-like, hypnotic.",
        "references": ["dija_motion (ChatGPT piece)", "s_tiercontent (invideo MCP ad)"],
        "inputs": ["brand logo", "product name", "1-line claim"],
        "caption_preset": "minimal_clean",
        "secondary_caption_preset": None,
        "style_preset": "neon_aura_style",
        "palette": ["#000000", "#0B1020", "#3B82F6", "#60A5FA", "#FFFFFF"],
        "pacing": {"mode": "slow_cinematic", "seconds_per_scene": [4, 6], "cuts": "none, fades only"},
        "layout": "full_frame",
        "sfx_map": [{"event": "scene fade", "sound": "swish"}],
        "sfx_defaults": [
            {"name": "swish", "placed_at_s": 1.0},
            {"name": "swish", "placed_at_s": 5.0},
            {"name": "swish", "placed_at_s": 9.0},
        ],
        "music": "Slow, low-energy generic bed under everything; music-only, no voiceover.",
        "sound_verified": False,
        "hook_rule": "Brand mark + swoosh in the first 3 seconds, then logo, product UI, eclipse logo.",
        "title_text": "Your product name + one-line claim",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "saas_clean_flat",
        "name": "SaaS Motion Explainer — Clean Flat",
        "category": "SaaS Motion Explainer",
        "feel": "Clean, corporate, calmly persuasive.",
        "references": ["natan.works (lead-gen piece)"],
        "inputs": ["voiceover/script lines", "brand name"],
        "caption_preset": "minimal_clean",
        "secondary_caption_preset": "light_sweep_title",
        "style_preset": "clean_tech_style",
        "palette": ["#FFFFFF", "#111111", "#2F5BFF", "#F5F6F8", "#18B46B"],
        "pacing": {"mode": "one_line_per_phrase", "cuts": "icon/text pops, clean slides"},
        "layout": "full_frame",
        "sfx_map": [
            {"event": "text-line arrival", "sound": "pop"},
            {"event": "end card", "sound": "ding"},
        ],
        "sfx_defaults": [
            {"name": "pop", "placed_at_s": 1.0},
            {"name": "pop", "placed_at_s": 2.5},
            {"name": "pop", "placed_at_s": 4.0},
            {"name": "ding", "placed_at_s": 8.0},
        ],
        "music": "Low generic bed under the voiceover, -14 LUFS mix.",
        "sound_verified": False,
        "hook_rule": "Problem list in the first 3 seconds, then the 'what if it happened automatically' turn, then a 'Coming soon' brand card.",
        "title_text": "Your brand name (end card)",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "talking_head_pro",
        "name": "Talking Head Pro — Bold Caption",
        "category": "Talking Head",
        "feel": "Bold, confrontational, proof-led, premium.",
        "references": ["devinjatho (Matrix Method)", "davidmnsilla (Broke vs Rich)", "josephswork (Course Proof)", "the.rexcodes (Fable 5.2 promo)"],
        "inputs": ["talking-head raw video", "claim", "proof numbers"],
        "caption_preset": "condensed",
        "secondary_caption_preset": "pill_highlight",
        "style_preset": "creator_motion_graphics_style",
        "palette": ["#FFFFFF", "#111111", "#22C55E", "#EF4444", "#3B82F6"],
        "pacing": {"mode": "cut_per_phrase", "cuts": "hard cuts on phrases, numbered points"},
        "layout": "full_frame",
        "sfx_map": [
            {"event": "title/proof card entry", "sound": "pop"},
            {"event": "numbered point", "sound": "snap"},
            {"event": "section change", "sound": "whoosh"},
        ],
        "sfx_defaults": [
            {"name": "pop", "placed_at_s": 1.0},
            {"name": "snap", "placed_at_s": 2.5},
            {"name": "pop", "placed_at_s": 4.0},
            {"name": "whoosh", "placed_at_s": 5.5},
        ],
        "music": "Voice-led; low generic bed optional under the voiceover.",
        "sound_verified": False,
        "hook_rule": "One big claim in the first 3 seconds (title card + face, no clutter), then proof, steps, CTA.",
        "title_text": "Your big claim (first 3 seconds)",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "trust_talking_head",
        "name": "Trust Talking Head — Slow Single Take",
        "category": "Talking Head",
        "feel": "Trust-building, unhurried, personal — living-room conversation.",
        "references": ["_k.elsie (realtor single take)"],
        "inputs": ["single-take talking-head video"],
        "caption_preset": "minimal_clean",
        "secondary_caption_preset": None,
        "style_preset": "warm_canvas_style",
        "palette": ["#F8F5F0", "#E8E0D4", "#1F2937", "#FFFFFF", "#D6CDBF"],
        "pacing": {"mode": "no_cuts", "cuts": "none — the take stays whole"},
        "layout": "full_frame",
        "sfx_map": [],
        "sfx_defaults": [],
        "music": "None. Warm calm voice only.",
        "sound_verified": False,
        "hook_rule": "Open on the value statement, then values, credentials, services, character argument, soft invitation.",
        "title_text": "Your value statement",
        "silence_cuts": False,
        "watermark": False,
        "cta_option": "Soft invitation only; no comment-gated CTA.",
    },
    {
        "id": "split_screen_breakdown",
        "name": "Split-Screen Breakdown",
        "category": "Breakdown",
        "feel": "Thoughtful, craft-proud / high-energy breakdown.",
        "references": ["hc.prath (Storyboard vs Final)", "aevyvideoschool (3D top / face bottom; AI vs Artist)"],
        "inputs": ["two video sources (before/after, sketch/final, 3D/face)"],
        "caption_preset": "condensed",
        "secondary_caption_preset": "minimal_clean",
        "style_preset": "creator_motion_graphics_style",
        "palette": ["#0A0A0A", "#FFFFFF", "#E5E5E5", "#FACC15", "#38BDF8"],
        "pacing": {"mode": "one_comparison_per_3s", "cuts": "split-screen wipe, pop/scale reveals"},
        "layout": "split_50_50_stack",
        "sfx_map": [
            {"event": "side-by-side reveal", "sound": "pop"},
            {"event": "label change", "sound": "click"},
        ],
        "sfx_defaults": [
            {"name": "pop", "placed_at_s": 1.0},
            {"name": "click", "placed_at_s": 2.0},
            {"name": "pop", "placed_at_s": 3.5},
            {"name": "click", "placed_at_s": 5.0},
        ],
        "music": "Voiceover-led; low generic bed optional.",
        "sound_verified": False,
        "hook_rule": "Contrast claim in the first 3 seconds, then proof by comparison, then verdict.",
        "title_text": "Your contrast claim",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "screen_record_tutorial",
        "name": "Screen-Record Tutorial — Craft",
        "category": "Tutorial",
        "feel": "Dense, no-fluff craft tip for editors.",
        "references": ["vivekk.kumarrr (AE keyframe lab; gaming-chair timeline overlay)", "unknown_irani (Premiere timeline reveal)"],
        "inputs": ["screen recording", "voiceover"],
        "caption_preset": "minimal_clean",
        "secondary_caption_preset": None,
        "style_preset": "software_walkthrough_style",
        "palette": ["#14141F", "#26263A", "#FF5F57", "#4F9CF0", "#EDEDF2"],
        "pacing": {"mode": "cut_per_step", "cuts": "hard cuts between steps"},
        "layout": "full_frame",
        "sfx_map": [
            {"event": "timeline step", "sound": "click"},
            {"event": "music ending", "sound": "riser"},
            {"event": "music ending", "sound": "whoosh"},
        ],
        "sfx_defaults": [
            {"name": "click", "placed_at_s": 1.0},
            {"name": "click", "placed_at_s": 2.5},
            {"name": "click", "placed_at_s": 4.0},
            {"name": "riser", "placed_at_s": 6.0},
            {"name": "whoosh", "placed_at_s": 7.0},
        ],
        "music": "None under the voice except the ending.",
        "sound_verified": False,
        "hook_rule": "The question is the hook, then steps, then payoff.",
        "title_text": "Your tutorial question",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "archival_documentary",
        "name": "Archival / Cinematic Documentary",
        "category": "Documentary",
        "feel": "Slow, museum-like archival essay — eerie, reverent.",
        "references": ["earn.edits (Project A119 retro Moon essay)", "unknown_irani (cinematic montage)"],
        "inputs": ["archival stills/footage", "voiceover script"],
        "caption_preset": "serif_title",
        "secondary_caption_preset": None,
        "style_preset": "smoke2_style",
        "palette": ["#E8E0CC", "#1A1A1A", "#F5F0E6", "#8A8578", "#FFFFFF"],
        "pacing": {"mode": "long_holds", "seconds_per_shot": [6, 10], "cuts": "hard cuts; slow Ken Burns drift on stills"},
        "layout": "full_frame",
        "sfx_map": [{"event": "scene change", "sound": "swish"}],
        "sfx_defaults": [
            {"name": "swish", "placed_at_s": 1.0},
            {"name": "swish", "placed_at_s": 7.0},
            {"name": "swish", "placed_at_s": 13.0},
        ],
        "music": "Low generic atmospheric bed under a calm measured voiceover.",
        "sound_verified": False,
        "hook_rule": "Huge image + serif title card in the first 3 seconds, then fact, implication, punchline.",
        "title_text": "YOUR TITLE IN SERIF CAPS",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "portfolio_showreel",
        "name": "Portfolio Showreel — Kinetic Type",
        "category": "Showreel",
        "feel": "Loud, confident, showreel-energy.",
        "references": ["vectofx.studio (landscape portfolio reel)"],
        "inputs": ["4-6 best clips", "name/role line"],
        "caption_preset": "condensed",
        "secondary_caption_preset": "minimal_clean",
        "style_preset": "creator_motion_graphics_style",
        "palette": ["#A3E635", "#0A0A0A", "#FFFFFF", "#1F2937", "#65A30D"],
        "pacing": {"mode": "title_slam_then_grid", "title_slam_s": 1.0, "seconds_per_clip": [3, 4], "cuts": "hard cuts between sections"},
        "layout": "vertical_stack_grid",
        "sfx_map": [
            {"event": "type slam", "sound": "thump"},
            {"event": "section change", "sound": "whoosh"},
        ],
        "sfx_defaults": [
            {"name": "thump", "placed_at_s": 1.0},
            {"name": "whoosh", "placed_at_s": 2.0},
            {"name": "thump", "placed_at_s": 5.0},
            {"name": "whoosh", "placed_at_s": 8.0},
        ],
        "music": "Upbeat generic track as the whole mix; music-only, no voiceover.",
        "sound_verified": False,
        "hook_rule": "Giant kinetic-type title in the first 3 seconds, then the work grid proves range.",
        "title_text": "PORTFOLIO",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "ai_showcase_desk",
        "name": "AI Showcase — Desk Reveal",
        "category": "Showcase",
        "feel": "Calm, smug, glow-y AI-demo flex.",
        "references": ["Edita Visuals (Claude Opus 5.5 demo)"],
        "inputs": ["desk shot", "screen recording of the AI output"],
        "caption_preset": "condensed",
        "secondary_caption_preset": "pill_highlight",
        "style_preset": "neon_aura_style",
        "palette": ["#0F1115", "#22C55E", "#FF8A3D", "#1F2937", "#FFFFFF"],
        "pacing": {"mode": "long_holds", "seconds_per_hold": [5, 8], "cuts": "none; smooth internal morphs, slow drift"},
        "layout": "full_frame",
        "sfx_map": [{"event": "monitor scene change", "sound": "swish"}],
        "sfx_defaults": [
            {"name": "swish", "placed_at_s": 1.0},
            {"name": "swish", "placed_at_s": 6.0},
            {"name": "swish", "placed_at_s": 11.0},
        ],
        "music": "Low generic bed under everything; music-only.",
        "sound_verified": False,
        "hook_rule": "Desk + bold claim title in the first 3 seconds, then proof-by-demo on the monitor, then end screen.",
        "title_text": "Your AI demo claim",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "local_language_demo",
        "name": "Local-Language Demo & Review",
        "category": "Demo & Review",
        "feel": "Punchy, street-style product test / friendly local AI-coach demo.",
        "references": ["beyondtahir (Pinokio demo; Artemis)", "talha__reviews (product reality check; fear hook)"],
        "inputs": ["phone screen-record", "talking head", "product"],
        "caption_preset": "pill_highlight",
        "secondary_caption_preset": None,
        "style_preset": "vox_explainer_style",
        "palette": ["#FFFFFF", "#1E3A8A", "#FACC15", "#111827", "#F3F4F6"],
        "pacing": {"mode": "cut_per_demo_step", "cuts": "hard cuts face to screen, tight close-ups"},
        "layout": "full_frame",
        "sfx_map": [
            {"event": "pill caption entry", "sound": "pop"},
            {"event": "hook reveal", "sound": "snap"},
        ],
        "sfx_defaults": [
            {"name": "pop", "placed_at_s": 1.0},
            {"name": "pop", "placed_at_s": 2.5},
            {"name": "pop", "placed_at_s": 4.0},
            {"name": "snap", "placed_at_s": 5.5},
        ],
        "music": "Low generic instrumental bed under the voiceover (optional).",
        "sound_verified": False,
        "hook_rule": "Product on face or a fear hook in the first 3 seconds, then demo/proof, then verdict/CTA. Captions accept Roman-Urdu/Hinglish text.",
        "title_text": "Your product verdict line",
        "silence_cuts": True,
        "watermark": False,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
    {
        "id": "gaming_montage",
        "name": "Gaming Montage — PUBG Mobile TDM",
        "category": "Gaming",
        "feel": "Aggressive, dark, high-energy — fast kills, skull/lightning branding.",
        "references": ["@zexediting_ (PUBG Mobile TDM montage, reel DPq4dyYAuCa)"],
        "inputs": ["gameplay screen-record (TDM/match clips)", "player tag/watermark"],
        "caption_preset": "minimal_clean",
        "secondary_caption_preset": None,
        "style_preset": "neon_aura_style",
        "palette": ["#C2703A", "#5A6B7C", "#EF4444", "#F2C14E", "#14181F"],
        "pacing": {"mode": "cut_per_kill", "seconds_per_clip": [2, 4], "cuts": "fast cuts per kill; ADS punch-ins and scope zooms; no holds"},
        "layout": "full_frame_centre_crop",
        "sfx_map": [
            {"event": "kill", "sound": "thump"},
            {"event": "lightning/skull section change", "sound": "whoosh"},
            {"event": "before streak reveal", "sound": "riser"},
        ],
        "sfx_defaults": [
            {"name": "thump", "placed_at_s": 1.0},
            {"name": "thump", "placed_at_s": 3.0},
            {"name": "thump", "placed_at_s": 5.0},
            {"name": "riser", "placed_at_s": 6.5},
            {"name": "whoosh", "placed_at_s": 7.5},
        ],
        "music": "Loud high-energy generic rock-style bed as the whole mix; no voiceover. No real track is bundled (copyright).",
        "sound_verified": False,
        "hook_rule": "Immediate action, no intro card: open on the first kill with HUD visible. Streak badges are the proof beats. HUD stays legible; 9:16 centre crop on the player/ADS point.",
        "title_text": "Your player tag",
        "silence_cuts": True,
        "watermark": True,
        "cta_option": "Comment-gated CTA pill (optional, off by default).",
    },
]


def list_templates() -> Dict[str, Dict[str, Any]]:
    """Return all reel templates keyed by template id."""
    return {t["id"]: copy.deepcopy(t) for t in TEMPLATE_CATALOG}


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Return one template by id, or None when unknown."""
    for template in TEMPLATE_CATALOG:
        if template["id"] == template_id:
            return copy.deepcopy(template)
    return None


def apply_template_to_job(template_id: str, job: Dict[str, Any]) -> Dict[str, Any]:
    """Fill an editor job with a template's bundle.

    Sets caption_preset, style_preset, sfx defaults, title_text and a
    storyboard hook block, and carries the template's pacing, layout, music,
    silence_cuts and watermark fields into the job so the EDL keeps them.
    Raises ValueError on an unknown template id (no silent fallback).
    User-supplied sfx/storyboard on the job are kept when already present.
    """
    template = get_template(template_id)
    if template is None:
        known = ", ".join(t["id"] for t in TEMPLATE_CATALOG)
        raise ValueError(f"Unknown template id: '{template_id}'. Valid templates: {known}")

    filled = copy.deepcopy(job) if isinstance(job, dict) else {}
    filled["template_id"] = template["id"]
    filled["caption_preset"] = template["caption_preset"]
    filled["style_preset"] = template["style_preset"]
    filled["title_text"] = template["title_text"]
    if not filled.get("sfx"):
        filled["sfx"] = copy.deepcopy(template["sfx_defaults"])
    if not filled.get("storyboard"):
        filled["storyboard"] = {
            "title": template["name"],
            "blocks": [
                {
                    "id": "b0",
                    "title": "hook",
                    "text": template["hook_rule"],
                    "start": 0.0,
                    "end": 3.0,
                    "visual": template["layout"],
                    "graphic": "Title card",
                    "sfx": template["sfx_map"][0]["sound"] if template["sfx_map"] else "",
                }
            ],
        }
    filled["template_pacing"] = copy.deepcopy(template["pacing"])
    filled["template_layout"] = template["layout"]
    filled["template_music"] = template["music"]
    filled["template_silence_cuts"] = template["silence_cuts"]
    filled["template_watermark"] = template["watermark"]
    filled["template_palette"] = list(template["palette"])
    return filled
