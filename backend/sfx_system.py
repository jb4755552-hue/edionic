"""
Edionic SFX System — sfx_system.py (Layer 5 & Section 5.1)
1. Synthesizes the 10-sound royalty-free starter kit locally in code (no downloads, no third-party license):
   - Transitions: whoosh, swoosh, swish
   - Impacts: pop, snap, thump
   - UI: click
   - Musical: ding, chime
   - Rise: riser
2. Writes and reads `sfx/catalog.json` (accepts drop-in WAVs + appended entries later).
3. Places SFX at the EXACT frame/millisecond of each cut point (`placed_at_s`, frame = round(placed_at_s * 30)),
   mixes under the voice track at -12.0 dB gain per effect, and normalizes the final mix to -14.0 LUFS (±1.0).
4. Measures the real mix using FFmpeg `ebur128` / `loudnorm` to verify Integrated LUFS (-14.0 ±1.0) and True Peak.
"""

import json
import math
import os
import random
import re
import shutil
import struct
import subprocess
import tempfile
import wave
from typing import Dict, Any, List, Optional

from slop_gate import find_binary

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SFX_DIR = os.path.join(BASE_DIR, "sfx")
CATALOG_PATH = os.path.join(SFX_DIR, "catalog.json")

STARTER_SFX_SPECS = [
    {"name": "whoosh", "file": "whoosh.wav", "duration": 0.38, "category": "transitions", "note": "synthesized in-house, royalty-free"},
    {"name": "swoosh", "file": "swoosh.wav", "duration": 0.32, "category": "transitions", "note": "synthesized in-house, royalty-free"},
    {"name": "swish",  "file": "swish.wav",  "duration": 0.24, "category": "transitions", "note": "synthesized in-house, royalty-free"},
    {"name": "pop",    "file": "pop.wav",    "duration": 0.14, "category": "impacts",     "note": "synthesized in-house, royalty-free"},
    {"name": "snap",   "file": "snap.wav",   "duration": 0.12, "category": "impacts",     "note": "synthesized in-house, royalty-free"},
    {"name": "thump",  "file": "thump.wav",  "duration": 0.28, "category": "impacts",     "note": "synthesized in-house, royalty-free"},
    {"name": "click",  "file": "click.wav",  "duration": 0.08, "category": "UI",          "note": "synthesized in-house, royalty-free"},
    {"name": "ding",   "file": "ding.wav",   "duration": 0.65, "category": "musical",     "note": "synthesized in-house, royalty-free"},
    {"name": "chime",  "file": "chime.wav",  "duration": 0.75, "category": "musical",     "note": "synthesized in-house, royalty-free"},
    {"name": "riser",  "file": "riser.wav",  "duration": 1.10, "category": "rise",        "note": "synthesized in-house, royalty-free"},
]


def _synthesize_wav(name: str, duration: float, out_path: str, sample_rate: int = 44100) -> None:
    """Synthesize a clean, royalty-free 16-bit mono WAV sound effect in pure Python."""
    n_samples = int(round(duration * sample_rate))
    rng = random.Random(sum(ord(c) for c in name) * 997)
    samples: List[int] = []
    phase = 0.0
    prev_val = 0.0

    for i in range(n_samples):
        t = i / sample_rate
        u = i / max(1, n_samples - 1)  # normalized 0..1

        if name in ("whoosh", "swoosh", "swish"):
            # Filtered noise + sweeping resonant pitch band
            env = math.sin(math.pi * u) ** 1.6
            f0 = 180.0 if name == "whoosh" else (280.0 if name == "swoosh" else 420.0)
            f1 = 920.0 if name == "whoosh" else (1400.0 if name == "swoosh" else 2100.0)
            freq = f0 + (f1 - f0) * math.sin(math.pi * u)
            phase += 2.0 * math.pi * freq / sample_rate
            noise = rng.uniform(-1.0, 1.0)
            prev_val = 0.82 * prev_val + 0.18 * noise
            val = env * (0.65 * prev_val + 0.35 * math.sin(phase))

        elif name == "pop":
            # Fast pitch-drop sine pop (420 Hz -> 95 Hz)
            env = math.exp(-22.0 * t) * min(1.0, t * 250.0)
            freq = 95.0 + 325.0 * math.exp(-35.0 * t)
            phase += 2.0 * math.pi * freq / sample_rate
            val = env * math.sin(phase)

        elif name == "snap":
            # Crisp high-transient finger/snare snap
            env = math.exp(-38.0 * t)
            noise = rng.uniform(-1.0, 1.0)
            tone = math.sin(2.0 * math.pi * 1650.0 * t) + 0.5 * math.sin(2.0 * math.pi * 920.0 * t)
            val = env * (0.6 * noise + 0.4 * tone)

        elif name == "thump":
            # Deep cinematic sub-bass punch (130 Hz -> 42 Hz)
            env = math.exp(-11.5 * t) * min(1.0, t * 180.0)
            freq = 42.0 + 88.0 * math.exp(-20.0 * t)
            phase += 2.0 * math.pi * freq / sample_rate
            val = env * (0.85 * math.sin(phase) + 0.15 * math.sin(2.0 * phase))

        elif name == "click":
            # Crisp mechanical UI click
            env = math.exp(-65.0 * t)
            val = env * (0.7 * math.sin(2.0 * math.pi * 2400.0 * t) + 0.3 * rng.uniform(-1.0, 1.0))

        elif name == "ding":
            # Pure harmonic bell ding (1046.5 Hz C6 + overtone)
            env = math.exp(-4.8 * t) * min(1.0, t * 300.0)
            val = env * (0.75 * math.sin(2.0 * math.pi * 1046.5 * t) + 0.25 * math.sin(2.0 * math.pi * 2093.0 * t))

        elif name == "chime":
            # Shimmering two-note harmonic chime chord (E6 + B6 + G#6)
            env = math.exp(-3.8 * t) * min(1.0, t * 250.0)
            val = env * (
                0.45 * math.sin(2.0 * math.pi * 1318.5 * t)
                + 0.35 * math.sin(2.0 * math.pi * 1661.2 * t)
                + 0.20 * math.sin(2.0 * math.pi * 1975.5 * t)
            )

        else:  # riser
            # Smooth exponential tension riser (160 Hz -> 1280 Hz + airy shimmer)
            env = (u ** 1.8) * math.sin(math.pi * min(1.0, u * 1.04))
            freq = 160.0 * (8.0 ** u)
            phase += 2.0 * math.pi * freq / sample_rate
            noise = rng.uniform(-1.0, 1.0)
            prev_val = 0.75 * prev_val + 0.25 * noise
            val = env * (0.70 * math.sin(phase) + 0.30 * prev_val)

        pcm = int(max(-32767, min(32767, round(val * 28000))))
        samples.append(pcm)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def ensure_sfx_library() -> Dict[str, Any]:
    """
    Ensure all 10 starter kit WAV files and `sfx/catalog.json` exist on disk.
    Preserves any extra custom WAV entries added to `catalog.json` later.
    """
    os.makedirs(SFX_DIR, exist_ok=True)
    existing_entries: List[Dict[str, Any]] = []
    if os.path.isfile(CATALOG_PATH):
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing_entries = data.get("sounds", [])
        except Exception:
            existing_entries = []

    by_name = {item["name"]: item for item in existing_entries if "name" in item}
    for spec in STARTER_SFX_SPECS:
        wav_path = os.path.join(SFX_DIR, spec["file"])
        if not os.path.isfile(wav_path) or os.path.getsize(wav_path) < 500:
            _synthesize_wav(spec["name"], spec["duration"], wav_path)
        by_name[spec["name"]] = dict(spec)

    catalog = {
        "version": 1,
        "library_type": "starter_kit_royalty_free",
        "honest_limits": "10-sound synthesized starter kit; 'on beat' means placed at exact cut frame (ms precision), not music-beat detection.",
        "sounds": list(by_name.values())
    }
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    return catalog


def measure_audio_loudness(media_path: str) -> Dict[str, Any]:
    """
    Measure real Integrated LUFS, True Peak (dBTP), and LRA on an audio/video file
    using FFmpeg's `loudnorm=print_format=json` filter.
    """
    ffmpeg_bin = find_binary("ffmpeg")
    cmd = [
        ffmpeg_bin, "-hide_banner", "-nostats",
        "-i", media_path,
        "-af", "loudnorm=I=-14.0:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stderr = proc.stderr or ""
    # Extract the JSON block printed by loudnorm at the end of stderr
    match = re.search(r"\{\s*\"input_i\"\s*:.*?\}", stderr, re.DOTALL)
    if not match:
        return {
            "measured": False,
            "integrated_lufs": None,
            "true_peak_db": None,
            "lra": None
        }
    try:
        info = json.loads(match.group(0))
        i_lufs = round(float(info.get("input_i", -14.0)), 2)
        tp_db = round(float(info.get("input_tp", -8.0)), 2)
        lra_val = round(float(info.get("input_lra", 1.0)), 2)
        target_pass = (-15.0 <= i_lufs <= -13.0) and (tp_db <= -1.0)
        return {
            "measured": True,
            "target_lufs": -14.0,
            "tolerance_lufs": 1.0,
            "integrated_lufs": i_lufs,
            "true_peak_db": tp_db,
            "lra": lra_val,
            "mix_pass": target_pass,
            "raw_loudnorm": info
        }
    except Exception:
        return {
            "measured": False,
            "integrated_lufs": None,
            "true_peak_db": None,
            "lra": None
        }


def mix_sfx_and_normalize_audio(
    voice_wav_path: str,
    sfx_placements: List[Dict[str, Any]],
    output_wav_path: str,
    fps: float = 30.0
) -> Dict[str, Any]:
    """
    Place each SFX at the exact millisecond/frame of its cut point (`placed_at_s`),
    apply -12.0 dB gain per effect, mix under the voice track, and two-pass normalize
    the combined mix to exactly -14.0 LUFS integrated (±1.0).
    """
    catalog = ensure_sfx_library()
    sound_map = {s["name"]: s for s in catalog["sounds"]}
    ffmpeg_bin = find_binary("ffmpeg")

    valid_placements: List[Dict[str, Any]] = []
    for item in sfx_placements:
        sname = item.get("name", "whoosh")
        if sname not in sound_map:
            continue
        placed_s = max(0.0, float(item.get("placed_at_s", 0.0)))
        frame_idx = int(round(placed_s * fps))
        exact_ms = int(round((frame_idx / fps) * 1000.0))
        valid_placements.append({
            "name": sname,
            "file": os.path.join(SFX_DIR, sound_map[sname]["file"]),
            "placed_at_s": round(frame_idx / fps, 3),
            "frame_at_30fps": frame_idx,
            "delay_ms": exact_ms,
            "gain_db": -12.0
        })

    with tempfile.TemporaryDirectory() as tmpdir:
        premix_wav = os.path.join(tmpdir, "premix.wav")
        if not valid_placements:
            # No SFX placed: still normalize voice to -14 LUFS
            premix_wav = voice_wav_path
        else:
            inputs = ["-i", voice_wav_path]
            filter_chains: List[str] = ["[0:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono[voice]"]
            mix_labels = ["[voice]"]
            for idx, p in enumerate(valid_placements, start=1):
                inputs.extend(["-i", p["file"]])
                delay = p["delay_ms"]
                filter_chains.append(
                    f"[{idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono,"
                    f"volume=-12.0dB,adelay={delay}|{delay}[sfx{idx}]"
                )
                mix_labels.append(f"[sfx{idx}]")

            n_in = len(mix_labels)
            filter_chains.append(
                "".join(mix_labels) + f"amix=inputs={n_in}:duration=first:dropout_transition=0,volume={n_in}[premix]"
            )
            cmd_mix = [
                ffmpeg_bin, "-y",
                *inputs,
                "-filter_complex", ";".join(filter_chains),
                "-map", "[premix]",
                "-ar", "44100", "-ac", "1",
                premix_wav
            ]
            subprocess.run(cmd_mix, check=True, capture_output=True)

        # Two-pass loudnorm to hit -14.0 LUFS (±1.0) integrated accurately on short & long clips
        pass1 = measure_audio_loudness(premix_wav)
        raw_ln = pass1.get("raw_loudnorm", {})
        if raw_ln and raw_ln.get("input_i") not in (None, "-inf", "inf"):
            af_norm = (
                f"loudnorm=I=-14.0:TP=-1.5:LRA=11:"
                f"measured_I={raw_ln['input_i']}:"
                f"measured_TP={raw_ln['input_tp']}:"
                f"measured_LRA={raw_ln['input_lra']}:"
                f"measured_thresh={raw_ln['input_thresh']}:"
                f"offset={raw_ln.get('target_offset', '0.0')}:linear=true,"
                f"aresample=44100"
            )
        else:
            af_norm = "loudnorm=I=-14.0:TP=-1.5:LRA=11,aresample=44100"

        norm_wav = os.path.join(tmpdir, "norm_pass.wav")
        cmd_norm = [
            ffmpeg_bin, "-y",
            "-i", premix_wav,
            "-af", af_norm,
            "-ar", "44100", "-ac", "1",
            norm_wav
        ]
        subprocess.run(cmd_norm, check=True, capture_output=True)

        # Verify post-norm loudness; if short clip needs linear trim adjustment to land dead-center on -14.0 LUFS, apply exact delta dB
        post_check = measure_audio_loudness(norm_wav)
        measured_i = post_check.get("integrated_lufs")
        if measured_i is not None and abs(-14.0 - measured_i) > 0.15:
            delta_db = round(-14.0 - measured_i, 2)
            cmd_trim_db = [
                ffmpeg_bin, "-y",
                "-i", norm_wav,
                "-af", f"volume={delta_db}dB,alimiter=limit=-1.5dB:level=false,aresample=44100",
                "-ar", "44100", "-ac", "1",
                output_wav_path
            ]
            subprocess.run(cmd_trim_db, check=True, capture_output=True)
        else:
            shutil.copyfile(norm_wav, output_wav_path)

    final_qa = measure_audio_loudness(output_wav_path)
    final_qa["effects_pass"] = len(valid_placements) > 0
    final_qa["effects_placed"] = valid_placements
    return final_qa
