// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The snappy ADSR, and the AR and ASR it reads as: attack, hold, decay, sustain and release, with its curves.

use super::*;

pub fn compiled(spec: &Value, kind: &str) -> EnvelopePart {
    let struck = kind == "ar";
    let release = number(spec, "release", 0.2).max(SHORTEST_TIME) / T60;
    let mut sustain = number(spec, "sustain", 0.6);
    let mut decay = number(spec, "decay", 0.3).max(SHORTEST_TIME) / T60;
    if struck {
        sustain = 0.0;
        decay = release;
    } else if kind == "asr" {
        sustain = 1.0;
    }
    let curve = number(spec, "attack_curve", TIMER_CURVE);
    let target = (curve > STRAIGHT).then(|| 1.0 + 0.5 * (TIMER_CURVE / curve).powf(CURVE_POWER));
    let bend = (curve < -STRAIGHT).then(|| SWELL_BEND * -curve / 100.0);
    EnvelopePart::Adsr {
        attack: number(spec, "attack", 0.005).max(SHORTEST_ATTACK),
        hold: number(spec, "hold", 0.0),
        decay,
        sustain,
        release,
        snap: number(spec, "snap", 0.0),
        target,
        bend,
        struck,
    }
}

impl EnvelopePart {
    pub(super) fn adsr_level(&self, state: &mut EnvelopeState, note: NoteTime, short: Option<f64>) -> f64 {
        let EnvelopePart::Adsr { release, struck, attack, .. } = self else {
            return 0.0;
        };
        if *struck {
            let level = self.held(note.age, short, state.start_level);
            if note.age > *attack && level < SILENT {
                state.done = true;
            }
            return level;
        }
        let Some(released) = note.released else {
            return self.held(note.age, short, state.start_level);
        };
        let from = *state.released_from.get_or_insert_with(|| self.held(released, short, state.start_level));
        let since = note.age - released;
        if since < 0.0 {
            return self.held(note.age, short, state.start_level);
        }
        let falling = from * (-since / release).exp();
        if falling < SILENT {
            state.done = true;
        }
        falling
    }

    /// The ADSR while its note is held: the attack from where it starts, the hold at the top, then the decay to the
    /// sustain.
    pub(super) fn held(&self, age: f64, short: Option<f64>, from: f64) -> f64 {
        let EnvelopePart::Adsr {
            attack,
            hold,
            decay,
            sustain,
            snap,
            target,
            bend,
            ..
        } = self
        else {
            return 0.0;
        };
        if age < *attack {
            let x = (age / attack).min(1.0);
            let rising = match (target, bend) {
                (Some(target), _) => target * (1.0 - ((target - 1.0) / target).powf(x)),
                (None, Some(bend)) => ((bend * x).exp() - 1.0) / (bend.exp() - 1.0),
                _ => x,
            };
            // A restruck note rises from the level it had reached, so the attack never starts from a jump to silence.
            return from + (1.0 - from) * rising;
        }
        let decay = short.map(|time| time / T60).unwrap_or(*decay);
        let gone = (age - attack - hold).max(0.0);
        let mut fall = (-gone / decay).exp();
        if *snap > 0.0 {
            fall = (1.0 - snap) * fall + snap * (-gone * (SNAP_SPEED / decay)).exp();
        }
        sustain + (1.0 - sustain) * fall
    }
}
