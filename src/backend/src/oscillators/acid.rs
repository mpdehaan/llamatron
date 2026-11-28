// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Oh3's oscillator, the acid bass's: its saw as Open303 draws it, its square shaped from the saw, and the high-pass that
//! couples it into the Diode filter, after Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license,
//! whose constants were measured from the circuit.

use super::*;
use llamatron_names::spec;

/// The halves of a cycle, its rise and its fall.
const HALVES: usize = 2;

/// The square: the saw through a tanh this steep, offset so that it switches a little off the middle, shifted half a
/// cycle, and played at half the saw's level.
const SQUARE_SHAPER_GAIN: f64 = 69.8232412342666;
const SQUARE_SHAPER_OFFSET: f64 = 4.37;
const SQUARE_LEVEL: f64 = 0.5;
/// The high-pass coupling the oscillator into the filter.
pub const COUPLING_HIGHPASS_HZ: f64 = 44.486;

/// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: its `fillWithSquare303`, the 303 square
/// table.
/// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: its `fillWithSaw303`, the 303 saw
/// table.
/// One cycle of the saw as Open303 draws it: rising from 0 to 1 over the first half, then from -1 to 0.
pub fn saw_cycle(length: usize) -> Vec<f64> {
    let half = length / HALVES;
    (0..length)
        .map(|place| {
            if place < half {
                place as f64 / (half as f64 - 1.0)
            } else {
                -1.0 + (place - half) as f64 / (length - half) as f64
            }
        })
        .collect()
}

/// One cycle of the square, from one cycle of a rising saw of a length.
pub fn square_cycle(length: usize) -> Vec<f64> {
    let half = length / HALVES;
    (0..length)
        .map(|place| {
            // The saw as Open303 draws it, rising from 0 to 1 over the first half, then from -1 to 0, read half a cycle on.
            let shifted = (place + half) % length;
            let saw = if shifted < half {
                shifted as f64 / (half as f64 - 1.0)
            } else {
                -1.0 + (shifted - half) as f64 / (length - half) as f64
            };
            -(SQUARE_SHAPER_GAIN * saw + SQUARE_SHAPER_OFFSET).tanh() * SQUARE_LEVEL
        })
        .collect()
}

/// Oh3's oscillator from its spec: Open303's saw or its shaped square, as band-limited tables, and its tuning.
pub fn compiled(spec: &Value, rate: f64) -> OscillatorPart {
    let cycle = if word(spec, spec::ACID_WAVE, spec::SAW) == spec::SAW {
        saw_cycle(TABLE_SIZE)
    } else {
        square_cycle(TABLE_SIZE)
    };
    OscillatorPart::Acid {
        tables: tables::cycle_tables(&cycle, rate),
        tuning: number(spec, spec::TUNING, 0.0),
        rate,
    }
}

/// One sample of Oh3: its table read at the note's pitch, inverted and coupled through the high-pass, as Open303's
/// oscillator feeds its filter.
pub(super) fn acid_sample(tables: &Tables, state: &mut OscillatorState, pitch: f64, rate: f64) -> f64 {
    if state.speeds_for != pitch || state.speeds[0] == 0.0 {
        state.speeds[0] = frequency_of(pitch) * TABLE_SIZE as f64 / rate;
        state.speeds_for = pitch;
    }
    let speed = state.speeds[0];
    let position = state.phases[0];
    state.phases[0] = wrapped(position + speed);
    let out = -read(&tables[state.band], position);
    state.coupling.process(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The square is shaped from the saw: it sits near its two levels most of the cycle, and is not centred on nothing.
    #[test]
    fn the_square_is_shaped_from_the_saw() {
        let (length, near_a_level, most_of_it) = (2048, 0.45, 1900);
        let cycle = square_cycle(length);
        let near_levels = cycle.iter().filter(|value| value.abs() > near_a_level).count();
        assert!(near_levels > most_of_it, "{near_levels}");
    }
}
