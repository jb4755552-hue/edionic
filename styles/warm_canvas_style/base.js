/**
 * Edionic Style Library Module — styles/warm_canvas_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "warm_canvas_style",
  "name": "Warm Canvas (Nafay 3D, adapted)",
  "reference_video_count": 0,
  "reference_videos": [],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 32.6,
  "scene_count": 1,
  "avg_shot_length": 32.6,
  "palette": [
    "#F7F5F4",
    "#111111",
    "#4F9CF0",
    "#EBE6E2",
    "#2B2826"
  ],
  "caption_style": "Fraunces serif captions, key words sky blue #4F9CF0",
  "hook_style": "Full-frame A-roll caption, then warm canvas with title chip",
  "pacing": "Gentle: fades with a small rise; 2-4 canvas beats between A-roll moments",
  "recommended_caption_preset": "handwritten",
  "ffmpeg_grade_filter": "eq=contrast=1.02:saturation=1.05:brightness=0.02",
  "family": "Talking Head",
  "fonts": [
    "Fraunces 600",
    "Inter 500-600"
  ],
  "motion_language": "Two modes only: full-frame talking head with at most one centred serif caption, and a warm off-white canvas with a soft swoosh where white cards explain one idea per beat. Gentle fades with a small rise, soft counters, chapter cards push vertically. No bounce, no shake.",
  "sound_map": {
    "chips_cards": "swish",
    "list_items": "click",
    "vertical_push": "riser",
    "canvas_pad": "none (quiet pad under canvas only, no music beat)"
  },
  "adapted_from": "Nafay 3D ai-video-editor skill style: warm-canvas",
  "adaptation_note": "Adapted from the Nafay 3D ai-video-editor skill style definition (colors, typography, motion language). Metrics are the skill's demo values, not measured from a reference video. The skill's 16:9-only limit does not apply: this bundle is Edionic-native 9:16."
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "warm_canvas_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#F7F5F4",
    secondary_color: "#111111",
    palette: ["#F7F5F4", "#111111", "#4F9CF0", "#EBE6E2", "#2B2826"],
    recommended_caption_preset: "handwritten",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
