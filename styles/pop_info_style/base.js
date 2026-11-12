/**
 * Edionic Style Library Module — styles/pop_info_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "pop_info_style",
  "name": "Pop Info (Nafay 3D, adapted)",
  "reference_video_count": 0,
  "reference_videos": [],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 12.0,
  "scene_count": 1,
  "avg_shot_length": 12.0,
  "palette": [
    "#D7DCCB",
    "#2F6F73",
    "#E07A5F",
    "#FFD86B",
    "#E85D4A"
  ],
  "caption_style": "Rounded Fredoka type; idea carried in a teal thought bubble",
  "hook_style": "Iris wipe opens on a flat-vector scene; character pops up reacting",
  "pacing": "Springy and playful: one scene per idea, slow camera push, iris close",
  "recommended_caption_preset": "karaoke_pop",
  "ffmpeg_grade_filter": "eq=contrast=1.02:saturation=1.12",
  "family": "Illustrated",
  "fonts": [
    "Fredoka 500-700"
  ],
  "motion_language": "Flat-vector animated infographic drawn in code: muted room colours, warm product colours, one character with a big feeling, a teal thought bubble carrying the idea with a counting number and pill tag, a dotted path drawing to a pin. Things pop in with a back-eased scale and settle with a decaying wobble. Open and close with a teal iris wipe with a yellow ring.",
  "sound_map": {
    "bubble_tags": "pop",
    "reactions": "click",
    "landings_counter": "thump",
    "iris_slides": "whoosh",
    "pin_drop": "pop"
  },
  "adapted_from": "Nafay 3D ai-video-editor skill style: pop-info",
  "adaptation_note": "Adapted from the Nafay 3D ai-video-editor skill style definition (colors, typography, motion language). Metrics are the skill's demo values, not measured from a reference video. The skill's 16:9-only limit does not apply: this bundle is Edionic-native 9:16."
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "pop_info_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#D7DCCB",
    secondary_color: "#2F6F73",
    palette: ["#D7DCCB", "#2F6F73", "#E07A5F", "#FFD86B", "#E85D4A"],
    recommended_caption_preset: "karaoke_pop",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
