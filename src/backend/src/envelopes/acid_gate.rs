// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The acid gate: the acid bass's envelopes, its accent swelling the amp and sweeping the filter through a capacitor.

use super::*;

/// The acid gate from its spec; resonance is the filter's, which its capacitor is fed through.
pub fn compiled(spec: &Value, resonance: f64) -> EnvelopePart {
    EnvelopePart::AcidGate {
        accent: number(spec, "accent", 0.6),
        threshold: number(spec, "accent_threshold", 110.0),
        sweep: number(spec, "accent_sweep", 0.5),
        accent_decay: number(spec, "accent_decay", 0.2).max(SHORTEST_TIME),
        amp_decay: number(spec, "amp_decay", 1.5).max(SHORTEST_TIME),
        soft_attack: number(spec, "soft_attack", 0.003).max(SHORTEST_ATTACK),
        resonance,
    }
}

pub(super) fn acid_level(state: &mut EnvelopeState, note: NoteTime, accent: f64, accent_decay: f64, amp_decay: f64, soft_attack: f64) -> f64 {
    let age = note.age;
    let mut level = if state.accented {
        let swell = 1.0 + ACCENT_LOUDER * accent * (-age * (T60 / accent_decay)).exp();
        (age / ACCENT_ATTACK).min(1.0) * (-age / amp_decay).exp() * swell
    } else {
        (age / soft_attack).min(1.0) * (-age / amp_decay).exp()
    };
    if let Some(released) = note.released {
        let since = age - released;
        level *= (1.0 - since / END_FADE).clamp(0.0, 1.0);
        if since >= END_FADE {
            state.done = true;
        }
    }
    level
}
