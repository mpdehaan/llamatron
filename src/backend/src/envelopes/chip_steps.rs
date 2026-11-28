// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Chip steps: the handheld chip's volume envelope, sixteen levels stepped at its pace, up or down.

use super::*;
use llamatron_names::spec;

/// The level, of the chip's sixteen, chip steps start at where the spec names none.
const DEFAULT_START_LEVEL: f64 = 15.0;

/// Chip steps from its spec.
pub fn compiled(spec: &Value) -> EnvelopePart {
    EnvelopePart::ChipSteps {
        start_level: number(spec, spec::START_LEVEL, DEFAULT_START_LEVEL),
        pace: number(spec, spec::LEVEL_PACE, 0.0),
        up: crate::protocol::values::truth(spec, spec::LEVEL_UP, false),
    }
}

pub(super) fn chip_level(state: &mut EnvelopeState, note: NoteTime, start_level: f64, pace: f64, up: bool) -> f64 {
    let mut level = start_level;
    if pace > 0.0 {
        let moved = (note.age * CHIP_TICKS / pace).floor();
        level = if up { (level + moved).min(CHIP_LEVELS) } else { (level - moved).max(0.0) };
    }
    if level == 0.0 && (pace > 0.0 || start_level == 0.0) && !up {
        state.done = true;
    }
    // The chip's first level eased in over the shortest attack, so that a note's start does not click; its steps after are
    // the chip's own.
    let mut out = level / CHIP_LEVELS * (note.age / SHORTEST_ATTACK).min(1.0);
    if let Some(released) = note.released {
        let since = note.age - released;
        out *= (1.0 - since / CHIP_FADE).clamp(0.0, 1.0);
        if since >= CHIP_FADE {
            state.done = true;
        }
    }
    out
}
