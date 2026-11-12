/**
 * Edionic Style Library Module — styles/data_story_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "data_story_style",
  "name": "Data Story (Nafay 3D, adapted)",
  "reference_video_count": 0,
  "reference_videos": [],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 21.0,
  "scene_count": 1,
  "avg_shot_length": 21.0,
  "palette": [
    "#0F141C",
    "#FF6B5B",
    "#3CC6B8",
    "#F2C14E",
    "#EEF1F5"
  ],
  "caption_style": "Archivo 800 headlines; IBM Plex Mono for labels and numbers",
  "hook_style": "Big counter counts up, then shrinks into a chart label",
  "pacing": "Calm editorial: charts draw to scale; takeaway holds ~1.5s",
  "recommended_caption_preset": "condensed",
  "ffmpeg_grade_filter": "eq=contrast=1.06:saturation=1.05",
  "family": "Data",
  "fonts": [
    "Archivo 500-800",
    "IBM Plex Mono 500-600"
  ],
  "motion_language": "Deep ink background, one accent per idea (coral main series, teal supporting, sand for the one thing to remember). Lines draw left to right with a glowing head; milestone dots pop; bars grow one by one with values counting up; the key bar gets a sand ring. Source line always on screen. Soft slide-ups and clean pushes between scenes.",
  "sound_map": {
    "counter_ticks": "click",
    "milestones": "ding",
    "bars": "click",
    "rings_pills": "swish",
    "scene_change": "whoosh",
    "cards": "pop",
    "biggest_number": "thump",
    "takeaway": "chime"
  },
  "adapted_from": "Nafay 3D ai-video-editor skill style: data-story",
  "adaptation_note": "Adapted from the Nafay 3D ai-video-editor skill style definition (colors, typography, motion language). Metrics are the skill's demo values, not measured from a reference video. The skill's 16:9-only limit does not apply: this bundle is Edionic-native 9:16."
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "data_story_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#0F141C",
    secondary_color: "#FF6B5B",
    palette: ["#0F141C", "#FF6B5B", "#3CC6B8", "#F2C14E", "#EEF1F5"],
    recommended_caption_preset: "condensed",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
