/**
 * Edionic Style Library Module — styles/creator_motion_graphics_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "creator_motion_graphics_style",
  "name": "Creator Motion Graphics (Nafay 3D, adapted)",
  "reference_video_count": 0,
  "reference_videos": [],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 21.5,
  "scene_count": 1,
  "avg_shot_length": 21.5,
  "palette": [
    "#26262B",
    "#FFD60A",
    "#20C46B",
    "#FF5F57",
    "#FFFFFF"
  ],
  "caption_style": "Anton caps statements, yellow serif accent on one word per line",
  "hook_style": "Hook lands in under 2 seconds: huge condensed caps slamming in",
  "pacing": "High energy: something new every 0.5-1.5s; takeaway holds ~1.5s",
  "recommended_caption_preset": "condensed",
  "ffmpeg_grade_filter": "eq=contrast=1.12:saturation=1.15",
  "family": "Kinetic Type",
  "fonts": [
    "Anton",
    "Instrument Serif italic",
    "Inter 600-800"
  ],
  "motion_language": "Words slam in one at a time with expo ease; cards and pills pop with overshoot; punch zoom plus shake on the hardest words; yellow highlighter swipe; hand-drawn circle and arrow; red strike-through for the wrong idea; rolling green counter that locks with a boom. Scene changes rotate whip pans, RGB glitches and flash cuts.",
  "sound_map": {
    "word_slams": "thump",
    "pills_cards": "pop",
    "cuts": "whoosh",
    "counter_ticks": "click",
    "big_number_lock": "thump",
    "rejection_stamp": "snap"
  },
  "adapted_from": "Nafay 3D ai-video-editor skill style: creator-motion-graphics",
  "adaptation_note": "Adapted from the Nafay 3D ai-video-editor skill style definition (colors, typography, motion language). Metrics are the skill's demo values, not measured from a reference video. The skill's 16:9-only limit does not apply: this bundle is Edionic-native 9:16."
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "creator_motion_graphics_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#26262B",
    secondary_color: "#FFD60A",
    palette: ["#26262B", "#FFD60A", "#20C46B", "#FF5F57", "#FFFFFF"],
    recommended_caption_preset: "condensed",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
