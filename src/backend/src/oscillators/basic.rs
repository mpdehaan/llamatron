// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Basic's oscillator: one plain wave, made every sample from its phase, its jumps smoothed by polyBLEPs.

use super::*;
use llamatron_names::spec;

/// Basic's oscillator from its spec.
pub fn compiled(spec: &Value) -> OscillatorPart {
    let mut partials = Vec::new();
    for entry in list(spec, spec::OSCILLATORS) {
        let Some(fields) = entry.as_array() else { continue };
        let Some(waveform) = fields.first().and_then(Value::as_str).and_then(Waveform::named) else {
            continue;
        };
        let cents = fields.get(1).and_then(as_number).unwrap_or(0.0);
        let level = fields.get(2).and_then(as_number).unwrap_or(1.0);
        partials.push(Partial { waveform, cents, level });
    }
    OscillatorPart::Basic { partials }
}

pub(super) fn basic_sample(partials: &[Partial], state: &mut OscillatorState, pitch: f64, moves: Moves, rate: f64) -> f64 {
    let mut out = 0.0;
    let wanted = pitch + moves.pitch;
    if state.speeds_for != wanted || state.speeds[0] == 0.0 {
        for (place, partial) in partials.iter().enumerate().take(3) {
            let octaves = (wanted - MIDDLE_A) / 12.0 + partial.cents / 1200.0;
            // In cycles a sample, held under half the rate and within hearing (frequency_of's bounds).
            let lowest = frequency_of(LOWEST_PITCH);
            let frequency = (A_FREQUENCY * 2f64.powf(octaves)).clamp(lowest, frequency_of(HIGHEST_PITCH));
            state.speeds[place] = (frequency / rate).min(MOST_STEP);
        }
        state.speeds_for = wanted;
    }
    // A pulse's width is moved by the Mod Matrix's Pulse width.
    let width = (PULSE_MIDDLE + moves.width).clamp(NARROWEST, WIDEST);
    for (place, partial) in partials.iter().enumerate().take(3) {
        let step = state.speeds[place];
        let at = state.phases[place];
        state.phases[place] = (at + step).fract();
        let sample = match partial.waveform {
            Waveform::Sine => blep::sine(at),
            Waveform::Saw => blep::saw(at, step),
            Waveform::Square => blep::pulse(at, step, PULSE_MIDDLE),
            Waveform::Pulse => blep::pulse(at, step, width),
            Waveform::Triangle => blep::triangle(at, step),
        };
        out += sample * partial.level;
    }
    out
}
