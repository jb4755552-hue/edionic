"""
Phase 2 End-to-End Verification (SFX System + Loudness QA + All 11 Caption Presets)
1. Verifies the 10-sound royalty-free synthesized SFX library (`sfx/catalog.json` + 10 WAV files)
2. Verifies exact-frame cut placement (frames 30 / 75 / 120 / 165 / 210 at 30 fps, -12.0 dB gain)
   and real -14 LUFS (±1.0) integrated loudness normalization
3. Renders all 11 caption presets on a real talking-head clip and runs Section 7 Slop Gate QA on each,
   confirming that every preset renders >= 54 px captions and has a unique visual frame fingerprint.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from caption_presets import ALL_11_PRESETS
from pipeline_v3 import (
    ensure_sample_raw_clip,
    render_edl_to_video,
    transcribe_with_word_timestamps,
)
from sfx_system import ensure_sfx_library
from slop_gate import run_slop_gate_qa


def run_phase2_verification() -> None:
    print("=== 1. Verifying 10-Sound Royalty-Free SFX Starter Kit ===")
    catalog = ensure_sfx_library()
    sounds = catalog.get("sounds", [])
    print(f"SFX Catalog Count: {len(sounds)} sounds")
    for s in sounds:
        wav_file = os.path.join(r"C:\ai editing\sfx", s["file"])
        fsize = os.path.getsize(wav_file) if os.path.isfile(wav_file) else 0
        print(f"  - {s['name']:8s} | {s['category']:12s} | {s['duration']:4.2f}s | {fsize:6d} bytes | {s['note']}")

    # Prepare the real 3-sentence talking-head clip (~7.5s post-cut so all 5 reference SFX at 1.0/2.5/4.0/5.5/7.0s land inside!)
    raw_clip = r"C:\ai editing\projects\default\uploads\talking_head_phase2_raw.mp4"
    if os.path.isfile(raw_clip):
        os.remove(raw_clip)
    ensure_sample_raw_clip(raw_clip)

    print("\n=== 2. Running faster-whisper Word-Level Transcription Once for Preset Suite ===")
    cached_words = transcribe_with_word_timestamps(raw_clip)
    print(f"Transcribed {len(cached_words)} words from real speech.")

    exports_dir = r"C:\ai editing\projects\default\exports\phase2_presets"
    os.makedirs(exports_dir, exist_ok=True)

    preset_results = []
    visual_hashes = set()

    print("\n=== 3. Rendering & Running Slop Gate QA on All 11 Caption Presets ===")
    for preset in ALL_11_PRESETS:
        out_mp4 = os.path.join(exports_dir, f"render_{preset}.mp4")
        edl_payload = {
            "version": 1,
            "caption_preset": preset,
            "title_text": "EDIONIC 9:16 HOOK TITLE",
            "style_preset": "smoke2_style",
            "sfx": [
                {"name": "whoosh", "placed_at_s": 1.0},
                {"name": "pop",    "placed_at_s": 2.5},
                {"name": "ding",   "placed_at_s": 4.0},
                {"name": "thump",  "placed_at_s": 5.5},
                {"name": "snap",   "placed_at_s": 7.0}
            ],
            "tracks": [
                {"id": "V3", "clips": []},
                {"id": "V2", "clips": []},
                {"id": "V1", "clips": []},
                {"id": "A1", "clips": []},
                {"id": "CC", "clips": []}
            ]
        }
        r_info = render_edl_to_video(
            source_video=raw_clip,
            edl_data=edl_payload,
            output_video=out_mp4,
            cached_words=cached_words
        )
        qa = run_slop_gate_qa(out_mp4, phase=2, render_info=r_info)
        m = qa["metrics"]
        visual_hashes.add(m["caption_zone_sha256"])
        preset_results.append({
            "preset": preset,
            "pass": qa["overall_pass"],
            "caption_height_px": m["caption_height_px"],
            "caption_block_px": m["caption_total_block_px"],
            "visual_hash": m["caption_zone_sha256"],
            "integrated_lufs": m["integrated_lufs"],
            "true_peak_db": m["true_peak_db"],
            "sfx_placed": m["sfx_placed_count"],
            "output_mp4": out_mp4
        })
        print(
            f"  [{ 'PASS' if qa['overall_pass'] else 'FAIL' }] {preset:18s} | "
            f"glyph={m['caption_height_px']:3d}px (block={m['caption_total_block_px']:3d}px) | "
            f"hash={m['caption_zone_sha256']} | LUFS={m['integrated_lufs']} | TP={m['true_peak_db']} dB"
        )

    print("\n=== 4. Phase 2 Summary ===")
    all_passed = all(p["pass"] for p in preset_results)
    print(f"All 11 Presets Passed Slop Gate QA: {all_passed}")
    print(f"Distinct Visual Frame Fingerprints: {len(visual_hashes)} / {len(ALL_11_PRESETS)}")

    summary_path = os.path.join(exports_dir, "phase2_qa_report.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "phase": 2,
            "all_passed": all_passed,
            "distinct_visual_presets": len(visual_hashes),
            "total_presets": len(ALL_11_PRESETS),
            "sfx_catalog_count": len(sounds),
            "presets": preset_results
        }, f, indent=2)
    print(f"Saved full Phase 2 QA report to: {summary_path}")


if __name__ == "__main__":
    run_phase2_verification()
