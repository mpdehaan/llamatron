// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The OTA filter: four one-pole stages in a loop, the creamier ladder of transconductance amplifiers, each stage
//! saturating softly and the loop solved without delay, a softer drive before it.

use super::{FilterPart, FilterState};

/// Where the soft limit reaches one and holds.
const SOFT_LIMIT_END: f64 = 3.0;
/// The least a stage's saturation may slow it, so that a very loud stage never stops.
const LEAST_SQUASH: f64 = 0.01;

/// A soft limit close to tanh and far cheaper, x(27 + x²)/(27 + 9x²), held at its ends past three, where it reaches one.
// After stmlib's SoftLimit (stmlib/dsp/dsp.h, Emilie Gillet, MIT); the implementation here is our own.
#[inline]
pub(super) fn soft_limit(x: f64) -> f64 {
    let held = x.clamp(-SOFT_LIMIT_END, SOFT_LIMIT_END);
    let square = held * held;
    held * (27.0 + square) / (27.0 + 9.0 * square)
}

/// What a stage's saturation scales its gain by: soft_limit(y)/y, worked out without the division, never under
/// LEAST_SQUASH.
#[inline]
fn soft_squash(y: f64) -> f64 {
    if y.abs() >= SOFT_LIMIT_END {
        return (1.0 / y.abs()).max(LEAST_SQUASH);
    }
    let square = y * y;
    (27.0 + square) / (27.0 + 9.0 * square)
}

impl FilterPart {
    /// The OTA's four stages: the loop solved for its input without delay, the input saturated, then the four stages run, each
    /// saturating too: each stage's gain is scaled by tanh(y)/y of its last output, so that a loud stage slows as a
    /// transistor pair does, and the zero-delay solve takes each stage's own share.
    // The stages' saturation after the linearised tanh of VCV Fundamental's VCF (VCVRack/Fundamental, src/VCF.cpp,
    // GPL-3.0-or-later), folded into our own zero-delay ladder, its tanh stmlib's soft limit; the implementation is ours.
    #[inline]
    pub(super) fn ota_stages(&self, state: &mut FilterState, input: f64) -> f64 {
        let g = state.g;
        let mut shares = [0.0; 4];
        let mut rests = [0.0; 4];
        for (place, last) in state.outputs.iter().enumerate() {
            let squash = soft_squash(*last);
            let stage_g = g * squash;
            let rest = 1.0 / (1.0 + stage_g);
            rests[place] = rest;
            shares[place] = stage_g * rest;
        }
        let [s1, s2, s3, s4] = state.stages;
        let [g1, g2, g3, g4] = shares;
        let carried = g4 * g3 * g2 * rests[0] * s1 + g4 * g3 * rests[1] * s2 + g4 * rests[2] * s3 + rests[3] * s4;
        let all = g1 * g2 * g3 * g4;
        let k = state.feedback;
        let solved = (input - k * carried) / (1.0 + k * all);
        let mut signal = soft_limit(solved);
        let mut taps = [0.0; 4];
        for place in 0..4 {
            let stage = &mut state.stages[place];
            let moved = (signal - *stage) * shares[place];
            let out = moved + *stage;
            *stage = out + moved;
            signal = out;
            taps[place] = out;
        }
        state.outputs = taps;
        taps[self.poles - 1]
    }
}
