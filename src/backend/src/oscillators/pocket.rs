// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The handheld chip's oscillator: its pulse of four duties, its wave channel, its noise from a shift register, and
//! its frequency sweep.

use super::*;
use llamatron_names::spec;

/// What the chip's voice takes where its spec names none: its pulse's duty, and its sweep's step.
const DEFAULT_DUTY: f64 = 0.25;
const DEFAULT_SWEEP_STEP: f64 = 3.0;

/// The handheld chip's oscillator from its spec.
pub fn compiled(spec: &Value, rate: f64) -> OscillatorPart {
    let voice = match word(spec, spec::CHIP_VOICE, spec::PULSE) {
        spec::WAVE => ChipVoice::Wave,
        spec::NOISE => ChipVoice::Noise,
        _ => ChipVoice::Pulse,
    };
    let (tables, noise) = match voice {
        ChipVoice::Pulse => (Some(tables::duty_tables(number(spec, spec::DUTY, DEFAULT_DUTY), rate)), None),
        ChipVoice::Wave => (Some(tables::shape_tables(word(spec, spec::WAVE_SHAPE, spec::TRIANGLE), rate)), None),
        ChipVoice::Noise => (None, Some(tables::shift_register_noise(word(spec, spec::NOISE, spec::LONG) == spec::SHORT))),
    };
    OscillatorPart::Pocket {
        tables,
        noise,
        sweep_pace: number(spec, spec::SWEEP_PACE, 0.0) as i64,
        sweep_up: truth(spec, spec::SWEEP_UP, false),
        sweep_step: number(spec, spec::SWEEP_STEP, DEFAULT_SWEEP_STEP) as i64,
    }
}

impl OscillatorPart {
    pub(super) fn pocket_sample(&self, state: &mut OscillatorState, seconds: f64, moves: Moves, rate: f64) -> (f64, bool) {
        let OscillatorPart::Pocket {
            tables,
            noise,
            sweep_pace,
            sweep_up,
            sweep_step,
            ..
        } = self
        else {
            return (0.0, false);
        };
        let mut silent = false;
        if *sweep_pace > 0 {
            let due = (seconds * SWEEP_TICKS / *sweep_pace as f64) as i64;
            while state.ticks < due {
                let change = state.period >> sweep_step;
                let period = if *sweep_up { state.period + change } else { state.period - change };
                state.ticks += 1;
                if period > LONGEST_PERIOD {
                    silent = true;
                    break;
                }
                state.period = period.max(0);
            }
        }
        let unheld = CHIP_CLOCK / (PERIODS - state.period as f64) * 2f64.powf(moves.pitch / 12.0);
        let frequency = unheld.clamp(frequency_of(LOWEST_PITCH), frequency_of(HIGHEST_PITCH));
        if let Some(noise) = noise {
            state.phases[0] += frequency * NOISE_STEPS_PER_CYCLE / rate;
            return (noise[state.phases[0] as usize % noise.len()] as f64, silent);
        }
        let Some(tables) = tables else { return (0.0, silent) };
        let position = state.phases[0];
        state.phases[0] = wrapped(position + frequency * TABLE_SIZE as f64 / rate);
        (read(&tables[state.band], position), silent)
    }
}
