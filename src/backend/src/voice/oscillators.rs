// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The oscillator parts a voice's Oscillators slot holds, each making the raw sound before the filter and the amp:
//!
//! - Basic: up to three band-limited table oscillators, each a waveform, a detune in cents and a level.
//! - SID: one voice of the classic home computer's chip: a triangle, saw, pulse whose width can sweep, or noise clocked by
//!   the pitch, ring modulated or synced by a second oscillator an interval away, an arpeggio stepped 50 times a second.
//! - Pocket: one voice of the handheld's chip: a pulse of one of four duties, a drawn wave of 32 steps, or a shift
//!   register's noise, and its pitch sweep moving the chip's period register 128 times a second.
//! - Acid: the acid bass's band-limited saw, or the square a transistor shapes from it.
//!
//! Tables are read with linear interpolation between samples, so that a slow note is smooth. Everything a part needs is
//! made when it is compiled; a sample is plain arithmetic.

use crate::protocol::values::{as_number, list, number, numbers, truth, word};
use crate::voice::acid;
use crate::voice::asheville;
use crate::voice::tables::{self, Tables, Waveform, TABLE_MASK, TABLE_SIZE};
use rmpv::Value;
use std::sync::Arc;

const MIDDLE_A: f64 = 69.0;
const A_FREQUENCY: f64 = 440.0;
const NARROWEST: f64 = 0.1;
/// A pulse's width where nothing moves it: a square.
const PULSE_MIDDLE: f64 = 0.5;
const WIDEST: f64 = 0.9;
const FRAMES_PER_SECOND: f64 = 50.0;
const NOISE_STEPS_PER_CYCLE: f64 = 16.0;
const SID_NOISE_STEPS_PER_CYCLE: f64 = 64.0;
const SWEEP_TICKS: f64 = 128.0;
const CHIP_CLOCK: f64 = 131072.0;
const LONGEST_PERIOD: i64 = 2047;
const PERIODS: f64 = 2048.0;

/// A MIDI number's frequency in hertz, equal tempered from A 440.
pub fn frequency_of(pitch: f64) -> f64 {
    A_FREQUENCY * 2f64.powf((pitch.clamp(LOWEST_PITCH, HIGHEST_PITCH) - MIDDLE_A) / 12.0)
}

/// The lowest and highest pitch any oscillator plays, about 8 Hz and 20 kHz, whatever the pitch envelope, the Mod
/// Matrix, an audio-rate LFO or a glide asks: a protection of ears and speakers no patch can turn off, so that no
/// modulation drives an oscillator to a subsonic thump or past hearing.
pub const LOWEST_PITCH: f64 = 0.0;
pub const HIGHEST_PITCH: f64 = 135.0;

/// A table read at a fractional position, interpolated between its two nearest samples.
#[inline]
fn read(table: &[f32], position: f64) -> f64 {
    let whole = position.floor();
    let index = whole as usize & TABLE_MASK;
    let next = (index + 1) & TABLE_MASK;
    let fraction = position - whole;
    let here = table[index] as f64;
    here + (table[next] as f64 - here) * fraction
}

/// A read position brought back into the table, by a subtraction, since a read never moves a whole table in a sample (its
/// frequency stays under half the rate) and a remainder of floats is slow.
#[inline]
fn wrapped(position: f64) -> f64 {
    if position >= TABLE_SIZE as f64 {
        position - TABLE_SIZE as f64
    } else {
        position
    }
}

/// What one voice's oscillators keep from sample to sample.
#[derive(Clone, Copy, Default)]
pub struct OscillatorState {
    pub phases: [f64; 3],
    pub second_phase: f64,
    pub period: i64,
    pub ticks: i64,
    pub band: usize,
    /// The pitch and spread the read speeds were last worked out for, and those speeds, so that a note whose pitch nothing
    /// moves works out its powers of two once, not every sample.
    pub speeds_for: (f64, f64),
    pub speeds: [f64; 3],
    /// Fishline's coupling into its filter, a one-pole high-pass, made as its note begins.
    pub coupling: acid::OnePoleHighpass,
    /// Asheville: Osc 3's value as an LFO, which the Mod Matrix's Osc 3 source reads; the mixer's last output, which
    /// Feedback loops back; and when the note began after the instrument started, with the voice's own random number,
    /// from which each oscillator's drift is its own.
    pub side: f64,
    pub last_out: f64,
    pub began: f64,
    pub random: f64,
}

/// One of Basic's oscillators: its tables, whether it is a pulse, read as two saws its width apart, its detune in cents
/// and its level.
pub struct Partial {
    tables: Tables,
    pulse: bool,
    cents: f64,
    level: f64,
}

pub enum OscillatorPart {
    Basic {
        partials: Vec<Partial>,
    },
    Sid {
        wave: SidWave,
        /// The ideal saw the pulse is read from, as the chip's pulse is a comparator on its accumulator, never its DAC.
        saw: Tables,
        /// The chip's own saw and triangle, through its uneven DAC.
        chip_saw: Tables,
        triangle: Tables,
        noise: Arc<Vec<f32>>,
        pulse_width: f64,
        interaction: Interaction,
        interval: f64,
        arpeggio: Vec<f64>,
    },
    Pocket {
        tables: Option<Tables>,
        noise: Option<Arc<Vec<f32>>>,
        sweep_pace: i64,
        sweep_up: bool,
        sweep_step: i64,
    },
    /// Asheville: three free-running oscillators into an overloading mixer (asheville.rs).
    Asheville(Box<asheville::Asheville>),
    /// Fishline: Open303's saw or its shaped square, each its own band-limited tables (acid.rs).
    Acid {
        tables: Tables,
        tuning: f64,
        rate: f64,
    },
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum SidWave {
    Triangle,
    Saw,
    Pulse,
    Noise,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Interaction {
    Off,
    Ring,
    Sync,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum ChipVoice {
    Pulse,
    Wave,
    Noise,
}

/// The oscillators a spec describes, and their pitch envelope's depth in semitones.
pub fn compiled(spec: &Value, rate: f64) -> (OscillatorPart, f64) {
    let pitch_env = number(spec, "pitch_env", 0.0);
    let part = match word(spec, "type", "basic") {
        "sid" => sid(spec, rate),
        "pocket" => pocket(spec, rate),
        "asheville" => OscillatorPart::Asheville(Box::new(asheville::compiled(spec))),
        "acid" => {
            let cycle = if word(spec, "acid_wave", "saw") == "saw" {
                acid::saw_cycle(TABLE_SIZE)
            } else {
                acid::square_cycle(TABLE_SIZE)
            };
            OscillatorPart::Acid {
                tables: tables::cycle_tables(&cycle, rate),
                tuning: number(spec, "tuning", 0.0),
                rate,
            }
        }
        _ => basic(spec, rate),
    };
    (part, pitch_env)
}

fn basic(spec: &Value, rate: f64) -> OscillatorPart {
    let mut partials = Vec::new();
    for entry in list(spec, "oscillators") {
        let Some(fields) = entry.as_array() else { continue };
        let Some(waveform) = fields.first().and_then(Value::as_str).and_then(Waveform::named) else {
            continue;
        };
        let cents = fields.get(1).and_then(as_number).unwrap_or(0.0);
        let level = fields.get(2).and_then(as_number).unwrap_or(1.0);
        partials.push(Partial {
            tables: tables::waveform_tables(waveform, rate),
            pulse: waveform == Waveform::Pulse,
            cents,
            level,
        });
    }
    OscillatorPart::Basic { partials }
}

fn sid(spec: &Value, rate: f64) -> OscillatorPart {
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
        saw: tables::waveform_tables(Waveform::Saw, rate),
        chip_saw,
        triangle,
        noise: tables::sid_noise(),
        pulse_width: number(spec, "pulse_width", 0.5),
        interaction,
        interval: number(spec, "interval", 7.0),
        arpeggio: numbers(spec, "arpeggio"),
    }
}

fn pocket(spec: &Value, rate: f64) -> OscillatorPart {
    let voice = match word(spec, "chip_voice", "pulse") {
        "wave" => ChipVoice::Wave,
        "noise" => ChipVoice::Noise,
        _ => ChipVoice::Pulse,
    };
    let (tables, noise) = match voice {
        ChipVoice::Pulse => (Some(tables::duty_tables(number(spec, "duty", 0.25), rate)), None),
        ChipVoice::Wave => (Some(tables::shape_tables(word(spec, "wave_shape", "triangle"), rate)), None),
        ChipVoice::Noise => (None, Some(tables::shift_register_noise(word(spec, "noise", "long") == "short"))),
    };
    OscillatorPart::Pocket {
        tables,
        noise,
        sweep_pace: number(spec, "sweep_pace", 0.0) as i64,
        sweep_up: truth(spec, "sweep_up", false),
        sweep_step: number(spec, "sweep_step", 3.0) as i64,
    }
}

/// What moves the oscillators at one sample: semitones of pitch, a share of the pulse's width, and the detune's spread.
#[derive(Clone, Copy, Default)]
pub struct Moves {
    pub pitch: f64,
    pub width: f64,
    pub spread: f64,
}

impl OscillatorPart {
    /// Ready a voice's state as its note begins.
    pub fn begin(&self, state: &mut OscillatorState, pitch: f64) {
        *state = OscillatorState::default();
        if let OscillatorPart::Acid { rate, .. } = self {
            state.coupling = acid::OnePoleHighpass::new(acid::COUPLING_HIGHPASS_HZ, *rate);
        }
        if let OscillatorPart::Pocket { .. } = self {
            state.period = ((PERIODS - CHIP_CLOCK / frequency_of(pitch)).round() as i64).clamp(0, LONGEST_PERIOD);
        }
    }

    /// Set a voice's free-running oscillators going as its note begins, at phases of the voice's own, and say when the note
    /// began after the instrument started, for the oscillators that drift by it.
    pub fn free_run(&self, state: &mut OscillatorState, random: f64, began: f64) {
        state.random = random;
        state.began = began;
        if let OscillatorPart::Asheville(asheville) = self {
            asheville.begin(state, random);
        }
    }

    /// Choose the table band for the chunk ahead, once a chunk, from the highest pitch the note will sound: its pitch, the
    /// most the modulation bent it up over the last chunk, and an arpeggio's highest step, so that a pitch modulated up
    /// fast, as analog-style FM does, reads a table cut low enough not to fold its harmonics back down.
    pub fn choose_band(&self, state: &mut OscillatorState, pitch: f64, reach: f64) {
        let highest_step = match self {
            OscillatorPart::Sid { arpeggio, .. } => arpeggio.iter().copied().fold(0.0, f64::max),
            _ => 0.0,
        };
        let frequency = match self {
            OscillatorPart::Pocket { .. } => CHIP_CLOCK / (PERIODS - state.period as f64) * 2f64.powf(reach / 12.0),
            _ => frequency_of(pitch + reach + highest_step),
        };
        state.band = tables::band_of(frequency);
    }

    /// One sample of the note at a pitch, seconds into it, moved as given; true in the second place where the chip has
    /// gone silent (the handheld's sweep past its register's top).
    #[inline]
    pub fn sample(&self, state: &mut OscillatorState, pitch: f64, seconds: f64, moves: Moves, rate: f64) -> (f64, bool) {
        match self {
            OscillatorPart::Basic { partials } => (basic_sample(partials, state, pitch, moves, rate), false),
            OscillatorPart::Sid { .. } => (self.sid_sample(state, pitch, seconds, moves, rate), false),
            OscillatorPart::Pocket { .. } => self.pocket_sample(state, seconds, moves, rate),
            OscillatorPart::Acid { tables, tuning, .. } => (acid_sample(tables, state, pitch + tuning + moves.pitch, rate), false),
            OscillatorPart::Asheville(asheville) => (asheville.sample(state, pitch, seconds, moves, rate), false),
        }
    }

    fn sid_sample(&self, state: &mut OscillatorState, pitch: f64, seconds: f64, moves: Moves, rate: f64) -> f64 {
        let OscillatorPart::Sid {
            wave,
            saw,
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
            let second = frequency_of(base + interval);
            state.second_phase = (state.second_phase + second / rate) % 1.0;
            let place = (state.second_phase * frequency / second) % 1.0;
            return match wave {
                SidWave::Triangle => 1.0 - 4.0 * (place - 0.5).abs(),
                SidWave::Pulse => {
                    if place < width {
                        1.0
                    } else {
                        -1.0
                    }
                }
                _ => 2.0 * place - 1.0,
            };
        }
        let speed = frequency * TABLE_SIZE as f64 / rate;
        let position = state.phases[0];
        state.phases[0] = wrapped(position + speed);
        let band = state.band;
        let mut out = match wave {
            SidWave::Saw => read(&chip_saw[band], position),
            SidWave::Triangle => read(&triangle[band], position),
            SidWave::Noise => noise[(position * SID_NOISE_STEPS_PER_CYCLE / TABLE_SIZE as f64) as usize % noise.len()] as f64 + 0.0 * state.phases[1],
            SidWave::Pulse => (read(&saw[band], position) - read(&saw[band], position + width * TABLE_SIZE as f64)) * 0.5,
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

    fn pocket_sample(&self, state: &mut OscillatorState, seconds: f64, moves: Moves, rate: f64) -> (f64, bool) {
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

fn basic_sample(partials: &[Partial], state: &mut OscillatorState, pitch: f64, moves: Moves, rate: f64) -> f64 {
    let mut out = 0.0;
    let band = state.band;
    let wanted = (pitch + moves.pitch, moves.spread);
    if state.speeds_for != wanted || state.speeds[0] == 0.0 {
        for (place, partial) in partials.iter().enumerate().take(3) {
            let octaves = (wanted.0 - MIDDLE_A) / 12.0 + partial.cents / 1200.0 * (1.0 + wanted.1);
            state.speeds[place] = A_FREQUENCY * 2f64.powf(octaves) * TABLE_SIZE as f64 / rate;
        }
        state.speeds_for = wanted;
    }
    // A pulse is half the difference of its saw and the saw its width on, the width moved by the Mod Matrix's Pulse width.
    let width = (PULSE_MIDDLE + moves.width).clamp(NARROWEST, WIDEST) * TABLE_SIZE as f64;
    for (place, partial) in partials.iter().enumerate().take(3) {
        let speed = state.speeds[place];
        let position = state.phases[place];
        state.phases[place] = wrapped(position + speed);
        let table = &partial.tables[band];
        let sample = if partial.pulse {
            (read(table, position) - read(table, position + width)) * 0.5
        } else {
            read(table, position)
        };
        out += sample * partial.level;
    }
    out
}

/// One sample of Fishline: its table read at the note's pitch, inverted and coupled through the high-pass, as Open303's
/// oscillator feeds its filter.
fn acid_sample(tables: &Tables, state: &mut OscillatorState, pitch: f64, rate: f64) -> f64 {
    if state.speeds_for.0 != pitch || state.speeds[0] == 0.0 {
        state.speeds[0] = frequency_of(pitch) * TABLE_SIZE as f64 / rate;
        state.speeds_for.0 = pitch;
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

    /// No pitch, however far modulation moves it, plays outside about 8 Hz to 20 kHz: never under MIDI's lowest note.
    #[test]
    fn every_oscillator_frequency_is_held_within_hearing() {
        let (far_above, far_below) = (400.0, -300.0);
        assert_eq!(frequency_of(far_above), frequency_of(HIGHEST_PITCH));
        assert_eq!(frequency_of(far_below), frequency_of(LOWEST_PITCH));
        assert!(frequency_of(HIGHEST_PITCH) < 20_000.0 && frequency_of(LOWEST_PITCH) > 8.0);
    }

    /// A note bent up by its modulation reads the table of the highest pitch it reaches, cut lower, so that analog-style
    /// FM does not fold harmonics back down; a note bent nowhere reads its own pitch's table.
    #[test]
    fn a_note_bent_up_reads_the_table_of_its_highest_pitch() {
        let spec = rmpv::Value::Map(vec![("type".into(), "acid".into())]);
        let (part, _) = compiled(&spec, 48000.0);
        let mut state = OscillatorState::default();
        let (pitch, two_octaves) = (60.0, 24.0);
        part.choose_band(&mut state, pitch, 0.0);
        let own = state.band;
        part.choose_band(&mut state, pitch, two_octaves);
        assert!(state.band > own, "{} against {own}", state.band);
    }
}
