/**
 * Edionic Style Library Module — styles/chalk_talk_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "chalk_talk_style",
  "name": "Chalk Talk (Nafay 3D, adapted)",
  "reference_video_count": 0,
  "reference_videos": [],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 20.8,
  "scene_count": 1,
  "avg_shot_length": 20.8,
  "palette": [
    "#24392F",
    "#F2EFE6",
    "#F4D35E",
    "#F39BBB",
    "#93CBEF"
  ],
  "caption_style": "Cabin Sketch titles, Kalam for equations and notes",
  "hook_style": "Chalk stick writes the first line on the slate, camera tracks along",
  "pacing": "Always writing: 0.4-1.2s per line; takeaway holds ~1.5s; no cuts",
  "recommended_caption_preset": "handwritten",
  "ffmpeg_grade_filter": "eq=contrast=1.03:saturation=0.95",
  "family": "Hand-Drawn",
  "fonts": [
    "Cabin Sketch 700",
    "Kalam 400-700"
  ],
  "motion_language": "One long green slate, one continuous shot. A visible chalk stick writes every word and draws every line; the camera tracks to a fresh stretch of slate per idea and leans in on the key moment. Pink chalk rings key numbers; yellow underlines and brackets; a felt eraser wipes a section clean for the takeaway. Grainy chalk strokes that skip over the board's tooth.",
  "sound_map": {
    "writing": "click",
    "lines_rings": "swish",
    "counter": "click",
    "eraser": "swish",
    "landed_number": "ding",
    "takeaway": "chime"
  },
  "adapted_from": "Nafay 3D ai-video-editor skill style: chalk-talk",
  "adaptation_note": "Adapted from the Nafay 3D ai-video-editor skill style definition (colors, typography, motion language). Metrics are the skill's demo values, not measured from a reference video. The skill's 16:9-only limit does not apply: this bundle is Edionic-native 9:16."
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "chalk_talk_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#24392F",
    secondary_color: "#F2EFE6",
    palette: ["#24392F", "#F2EFE6", "#F4D35E", "#F39BBB", "#93CBEF"],
    recommended_caption_preset: "handwritten",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
