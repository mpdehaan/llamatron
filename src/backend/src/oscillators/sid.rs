// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The SID chip's oscillator: its triangle, saw, pulse and noise through the chip's own converter, ring and sync from a
//! second oscillator, and its arpeggio.

use super::*;

/// The SID's oscillator from its spec.
pub fn compiled(spec: &Value, rate: f64) -> OscillatorPart {
    let wave = match word(spec, "wave", "pulse") {
        "triangle" => SidWave::Triangle,
        "saw" => SidWave::Saw,
        "noise" => SidWave::Noise,
        _ => SidWave::Pulse,
    };
    let interaction = match word(spec, "modulation", "off") {
        "ring" => Interaction::Ring,
        "sync" => Interaction::Sync,
        _ => Interaction::Off,
    };
    let (chip_saw, triangle) = tables::sid_wave_tables(rate);
    OscillatorPart::Sid {
        wave,
        chip_saw,
        triangle,
        noise: tables::sid_noise(),
        pulse_width: number(spec, "pulse_width", 0.5),
        interaction,
        interval: number(spec, "interval", 7.0),
        arpeggio: numbers(spec, "arpeggio"),
    }
}

impl OscillatorPart {
    pub(super) fn sid_sample(&self, state: &mut OscillatorState, pitch: f64, seconds: f64, moves: Moves, rate: f64) -> f64 {
        let OscillatorPart::Sid {
            wave,
            chip_saw,
            triangle,
            noise,
            pulse_width,
            interaction,
            interval,
            arpeggio,
        } = self
        else {
            return 0.0;
        };
        let mut base = pitch + moves.pitch;
        if !arpeggio.is_empty() {
            base += arpeggio[(seconds * FRAMES_PER_SECOND) as usize % arpeggio.len()];
        }
        let frequency = frequency_of(base);
        let width = (*pulse_width + moves.width).clamp(NARROWEST, WIDEST);
        if *interaction == Interaction::Sync {
            // A synced wave repeats at its master's period, so the master runs at the note, and the wave heard, reset
            // by it, runs at the note plus the Interval, as the chip's synced oscillator is tuned above its master.
            return sid_synced(*wave, state, frequency_of(base + interval), frequency, width, rate);
        }
        let speed = frequency * TABLE_SIZE as f64 / rate;
        let position = state.phases[0];
        state.phases[0] = wrapped(position + speed);
        let band = state.band;
        let mut out = match wave {
            SidWave::Saw => read(&chip_saw[band], position),
            SidWave::Triangle => read(&triangle[band], position),
            SidWave::Noise => noise[(position * SID_NOISE_STEPS_PER_CYCLE / TABLE_SIZE as f64) as usize % noise.len()] as f64 + 0.0 * state.phases[1],
            // The chip's pulse is a comparator on its accumulator, never its DAC: a band-limited pulse of its own.
            SidWave::Pulse => blep::pulse(position / TABLE_SIZE as f64, (speed / TABLE_SIZE as f64).min(MOST_STEP), width),
        };
        if *wave == SidWave::Noise {
            // Noise steps through the register as the cycle turns, so it must count whole cycles, not wrap at one.
            state.phases[1] += speed * SID_NOISE_STEPS_PER_CYCLE / TABLE_SIZE as f64;
            out = noise[state.phases[1] as usize % noise.len()] as f64;
        }
        if *interaction == Interaction::Ring {
            state.second_phase = (state.second_phase + frequency_of(base + interval) / rate) % 1.0;
            if state.second_phase >= 0.5 {
                out = -out;
            }
        }
        out
    }
}

/// One sample of the SID's wave hard-synced to its second oscillator: the wave starts its cycle again each time the
/// second's ends, and each jump, its own or the sync's, falling between samples is smoothed by the one-sample-delayed
/// BLEP, a share in this sample and a share in the next, so that a swept sync lead does not alias.
// After the hard sync of Plaits' VariableShapeOscillator (plaits/dsp/oscillator/variable_shape_oscillator.h) and
// stmlib's ThisBlepSample and NextBlepSample (stmlib/dsp/polyblep.h), Emilie Gillet, MIT; the implementation is our own.
pub(super) fn sid_synced(wave: SidWave, state: &mut OscillatorState, frequency: f64, master: f64, width: f64, rate: f64) -> f64 {
    let naive = |place: f64| match wave {
        SidWave::Triangle => blep::naive_triangle(place),
        SidWave::Pulse => {
            if place < width {
                1.0
            } else {
                -1.0
            }
        }
        _ => 2.0 * place - 1.0,
    };
    let step = (frequency / rate).min(MOST_STEP);
    let master_step = (master / rate).min(MOST_STEP);
    let mut this = state.sync_next;
    let mut next = 0.0;
    let mut place = state.sync_phase + step;
    state.second_phase += master_step;
    // A jump of the wave's own: the saw's at the cycle's end, the pulse's at its width and at the cycle's end.
    let own_jump = |from: f64, to: f64, edge: f64, size: f64, this: &mut f64, next: &mut f64| {
        if from < edge && to >= edge {
            let after = (to - edge) / step;
            *this += size * blep::this_sample(after);
            *next += size * blep::next_sample(after);
        }
    };
    if matches!(wave, SidWave::Pulse) {
        own_jump(state.sync_phase, place, width, -2.0, &mut this, &mut next);
    }
    if place >= 1.0 {
        place -= 1.0;
        let after = place / step;
        let size = match wave {
            SidWave::Saw | SidWave::Noise => -2.0,
            SidWave::Pulse => 2.0,
            SidWave::Triangle => 0.0,
        };
        this += size * blep::this_sample(after);
        next += size * blep::next_sample(after);
    }
    if state.second_phase >= 1.0 {
        // The master ends its cycle a share of a sample ago: the wave jumps from where it was then back to its start.
        state.second_phase -= 1.0;
        let after = (state.second_phase / master_step).min(1.0);
        let at_reset = (place - after * step).rem_euclid(1.0);
        let size = naive(0.0) - naive(at_reset);
        this += size * blep::this_sample(after);
        next += size * blep::next_sample(after);
        place = after * step;
    }
    state.sync_phase = place;
    next += naive(place);
    state.sync_next = next;
    this
}
