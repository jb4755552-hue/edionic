#!/usr/bin/env python3
"""Hotfix 4.3 checks: graphics text must fit its box (measured width).

Regression cases are the exact texts from the 2026-11-12 drive-raw E2E
test (job_raw1.json / TIMINGS_AND_QA.md), which spilled in the render:
- proof claim "1 week -editor-to-week bonuses" wrapped to a 3rd line
  and collided with the keyword caption at t=20
- pill "edit as many videos as you desire" wrapped to a 2nd line that
  spilled below the pill shape
- card labels "leaders within the" / "the best content" overflowed the
  176px card edge at n=5

Run: python3 backend/test_hotfix43_fit.py  (no pytest needed)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graphics import (
    _est_text_w, _fit_text, _pill, _proof_card, _card_sequence, _title_card,
    PROOF_CARD, CARDS_ROW, CARDS_GAP,
)

FAILURES = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


# 0. The estimator must flag the old failures as too wide (else it proves nothing).
check("estimator flags proof line2 too wide at 80px",
      _est_text_w("-EDITOR-TO-WEEK BONUSES", 80) > PROOF_CARD["w"] - 80,
      f"est={_est_text_w('-EDITOR-TO-WEEK BONUSES', 80):.0f} vs max {PROOF_CARD['w'] - 80}")
check("estimator flags 7-word pill too wide at 58px",
      _est_text_w("EDIT AS MANY VIDEOS AS YOU DESIRE", 58) > 860)

# 1. Proof card: the exact failing claim fits 2 lines inside the card.
lines, fs = _fit_text("1 WEEK -EDITOR-TO-WEEK BONUSES", 80, PROOF_CARD["w"] - 80, 2, min_fs=44)
check("proof claim <= 2 lines", len(lines) <= 2, f"lines={lines}")
check("proof claim lines fit card width",
      all(_est_text_w(ln, fs) <= PROOF_CARD["w"] - 80 for ln in lines),
      f"fs={fs} lines={lines}")
events, _ = _proof_card(19.0, 21.0, "1 week -editor-to-week bonuses", "", "#FACC15", 1)
check("proof card emits one event, no 3rd line", len(events) == 1 and events[0].count("\\N") <= 1,
      events[0][-120:] if events else "no events")

# 2. Pill: the exact failing pill stays one line and fits the pill width.
lines, fs = _fit_text("EDIT AS MANY VIDEOS AS YOU DESIRE", 58, 860, 1, min_fs=36)
check("pill is one line", len(lines) == 1, f"lines={lines}")
check("pill line fits 860px", _est_text_w(lines[0], fs) <= 860, f"fs={fs} w={_est_text_w(lines[0], fs):.0f}")
events, _ = _pill(21.3, 22.6, "edit as many videos as you desire", "#FACC15", 1)
check("pill event has no line break", "\\N" not in events[-1], events[-1][-100:])

# 3. Card labels at n=5 (176px cards): every label fits its card.
cards = [
    {"number": "1", "label": "full-time"},
    {"number": "2", "label": "quality content"},
    {"number": "3", "label": "leaders within the"},
    {"number": "4", "label": "the best in the"},
    {"number": "5", "label": "the best content"},
]
cw = (CARDS_ROW["w"] - CARDS_GAP * 4) // 5
for c in cards:
    lines, fs = _fit_text(c["label"], 36, cw - 24, 2, min_fs=26)
    check(f"card label fits: {c['label']!r}", len(lines) <= 2
          and all(_est_text_w(ln, fs) <= cw - 24 for ln in lines),
          f"fs={fs} lines={lines} card_w={cw}")
events, _ = _card_sequence(5.1, 15.5, cards, "#3B63FF", 1)
label_events = [e for e in events if "GfxCardLabel" in e]
check("card_sequence emits 5 label events", len(label_events) == 5, f"got {len(label_events)}")
check("no card label event wraps past 2 lines",
      all(e.count("\\N") <= 1 for e in label_events))

# 4. Title card: long hook title fits the band, 2 lines max.
lines, fs = _fit_text("EDIONIC 9:16 HOOK TITLE THAT KEEPS GOING AND GOING", 84, 900, 2, min_fs=48)
check("title <= 2 lines and fits", len(lines) <= 2
      and all(_est_text_w(ln, fs) <= 900 for ln in lines), f"fs={fs} lines={lines}")
events, _ = _title_card(0.0, 3.0, "Edionic 9:16 hook title that keeps going and going", "#3B63FF", 1)
check("title event has <= 1 line break", events[0].count("\\N") <= 1)

# 5. Degenerate inputs do not crash or loop.
for txt in ("", "X", "A" * 60, "one two three four five six seven eight nine ten"):
    lines, fs = _fit_text(txt, 80, 800, 2, min_fs=44)
    check(f"fit handles {txt[:20]!r}", len(lines) <= 2
          and all(_est_text_w(ln, fs) <= 800 for ln in lines), f"lines={lines}")

print(f"\n{len(FAILURES)} failures" if FAILURES else "\nAll Hotfix 4.3 fit checks passed.")
sys.exit(1 if FAILURES else 0)
