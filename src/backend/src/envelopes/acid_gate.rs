// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The acid gate: the acid bass's envelopes, its accent swelling the amp and sweeping the filter through a capacitor.

use super::*;
use llamatron_names::spec;

/// What an Acid gate takes where its spec names none: the accent's share and the velocity from which a note is
/// accented, the accent's sweep share and its decay in seconds, the amp's decay and the soft attack, in seconds.
const DEFAULT_ACCENT: f64 = 0.6;
const DEFAULT_ACCENT_THRESHOLD: f64 = 110.0;
const DEFAULT_ACCENT_SWEEP: f64 = 0.5;
const DEFAULT_ACCENT_DECAY: f64 = 0.2;
const DEFAULT_AMP_DECAY: f64 = 1.5;
const DEFAULT_SOFT_ATTACK: f64 = 0.003;

/// The acid gate from its spec; resonance is the filter's, which its capacitor is fed through.
pub fn compiled(spec: &Value, resonance: f64) -> EnvelopePart {
    EnvelopePart::AcidGate {
        accent: number(spec, spec::ACCENT, DEFAULT_ACCENT),
        threshold: number(spec, spec::ACCENT_THRESHOLD, DEFAULT_ACCENT_THRESHOLD),
        sweep: number(spec, spec::ACCENT_SWEEP, DEFAULT_ACCENT_SWEEP),
        accent_decay: number(spec, spec::ACCENT_DECAY, DEFAULT_ACCENT_DECAY).max(SHORTEST_TIME),
        amp_decay: number(spec, spec::AMP_DECAY, DEFAULT_AMP_DECAY).max(SHORTEST_TIME),
        soft_attack: number(spec, spec::SOFT_ATTACK, DEFAULT_SOFT_ATTACK).max(SHORTEST_ATTACK),
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
