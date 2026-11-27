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

pub mod asheville;
pub mod tables;

use crate::dsp::blep;
use crate::filters::diode;
use crate::oscillators::tables::{Tables, Waveform, TABLE_MASK, TABLE_SIZE};
use crate::protocol::values::{as_number, list, number, numbers, truth, word};
use rmpv::Value;
use std::sync::Arc;

const MIDDLE_A: f64 = 69.0;
const A_FREQUENCY: f64 = 440.0;
const NARROWEST: f64 = 0.1;
/// A pulse's width where nothing moves it: a square.
const PULSE_MIDDLE: f64 = 0.5;
const WIDEST: f64 = 0.9;
/// The most of a cycle a band-limited wave moves a sample: just under half, the highest a sample rate holds.
const MOST_STEP: f64 = 0.45;
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
    /// Oh3's coupling into its filter, a one-pole high-pass, made as its note begins.
    pub coupling: diode::OnePoleHighpass,
    /// Asheville: each oscillator's last value, which the Mod Matrix's Osc 1 to Osc 3 sources read; its noise's state;
    /// the mixer's last output, which Feedback loops back; and when the note began after the instrument started, with
    /// the voice's own random number, from which each oscillator's drift is its own.
    pub sides: [f64; 3],
    pub noise_state: u64,
    pub last_out: f64,
    /// Asheville: each oscillator's sub-oscillator's phase.
    pub sub_phases: [f64; 3],
    /// The SID's synced wave: its phase in cycles, and the share of a jump's smoothing owed to the next sample.
    pub sync_phase: f64,
    pub sync_next: f64,
    pub began: f64,
    pub random: f64,
}

/// One of Basic's oscillators: its waveform, made every sample by voice/blep.rs, its detune in cents and its level.
pub struct Partial {
    waveform: Waveform,
    cents: f64,
    level: f64,
}

pub enum OscillatorPart {
    Basic {
        partials: Vec<Partial>,
    },
    Sid {
        wave: SidWave,
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
    /// Oh3: Open303's saw or its shaped square, each its own band-limited tables (acid.rs).
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

/// The oscillators a spec describes.
pub fn compiled(spec: &Value, rate: f64) -> OscillatorPart {
    match word(spec, "type", "basic") {
        "sid" => sid(spec, rate),
        "pocket" => pocket(spec, rate),
        "asheville" => OscillatorPart::Asheville(Box::new(asheville::compiled(spec))),
        "acid" => {
            let cycle = if word(spec, "acid_wave", "saw") == "saw" {
                diode::saw_cycle(TABLE_SIZE)
            } else {
                diode::square_cycle(TABLE_SIZE)
            };
            OscillatorPart::Acid {
                tables: tables::cycle_tables(&cycle, rate),
                tuning: number(spec, "tuning", 0.0),
                rate,
            }
        }
        _ => basic(spec),
    }
}

/// What mixes a note's random number and an oscillator's place into a seed of their own: the golden ratio as a
/// 64-bit number, the usual odd constant of such hashes.
const PHASE_MIX: u64 = 0x9E37_79B9_7F4A_7C15;

/// Where a free-running oscillator is in its cycle as a note starts, from the note's random number, from -1 to 1, and the
/// oscillator's place: each oscillator its own draw, unrelated to the others', so that no two start near together more
/// often than chance would have them.
pub fn free_phase(random: f64, place: usize) -> f64 {
    // A SplitMix64 step of the random number's bits and the place, its top 53 bits a share of a cycle.
    let mut bits = random.to_bits() ^ (place as u64 + 1).wrapping_mul(PHASE_MIX);
    bits = (bits ^ (bits >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    bits = (bits ^ (bits >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    bits ^= bits >> 31;
    (bits >> 11) as f64 / (1u64 << 53) as f64
}

fn basic(spec: &Value) -> OscillatorPart {
    let mut partials = Vec::new();
    for entry in list(spec, "oscillators") {
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
            state.coupling = diode::OnePoleHighpass::new(diode::COUPLING_HIGHPASS_HZ, *rate);
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
        match self {
            OscillatorPart::Asheville(asheville) => asheville.begin(state, random),
            // Each of Basic's oscillators runs free, starting the note at a phase of its own: oscillators that all
            // started together would lock, so that a saw and a square in tune add up to one fixed wave, a saw an octave
            // up, rather than mixing.
            OscillatorPart::Basic { .. } => {
                for (place, phase) in state.phases.iter_mut().enumerate() {
                    *phase = free_phase(random, place);
                }
            }
            _ => {}
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
            return sid_synced(*wave, state, frequency, frequency_of(base + interval), width, rate);
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
    let wanted = (pitch + moves.pitch, moves.spread);
    if state.speeds_for != wanted || state.speeds[0] == 0.0 {
        for (place, partial) in partials.iter().enumerate().take(3) {
            let octaves = (wanted.0 - MIDDLE_A) / 12.0 + partial.cents / 1200.0 * (1.0 + wanted.1);
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

/// One sample of the SID's wave hard-synced to its second oscillator: the wave starts its cycle again each time the
/// second's ends, and each jump, its own or the sync's, falling between samples is smoothed by the one-sample-delayed
/// BLEP, a share in this sample and a share in the next, so that a swept sync lead does not alias.
// After the hard sync of Plaits' VariableShapeOscillator (plaits/dsp/oscillator/variable_shape_oscillator.h) and
// stmlib's ThisBlepSample and NextBlepSample (stmlib/dsp/polyblep.h), Emilie Gillet, MIT; the implementation is our own.
fn sid_synced(wave: SidWave, state: &mut OscillatorState, frequency: f64, master: f64, width: f64, rate: f64) -> f64 {
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

/// One sample of Oh3: its table read at the note's pitch, inverted and coupled through the high-pass, as Open303's
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
        let part = compiled(&spec, 48000.0);
        let mut state = OscillatorState::default();
        let (pitch, two_octaves) = (60.0, 24.0);
        part.choose_band(&mut state, pitch, 0.0);
        let own = state.band;
        part.choose_band(&mut state, pitch, two_octaves);
        assert!(state.band > own, "{} against {own}", state.band);
    }

    /// A hard-synced saw is smoothed at its sync's jumps: from sample to sample it never leaps the full height a naive
    /// sync makes, and it stays within its bounds.
    #[test]
    fn a_synced_saw_is_smoothed_at_its_jumps() {
        let mut state = OscillatorState::default();
        let (rate, slave, master) = (48_000.0, 3_100.0, 440.0);
        let values: Vec<f64> = (0..4800).map(|_| sid_synced(SidWave::Saw, &mut state, slave, master, 0.5, rate)).collect();
        let most_leap = values.windows(2).map(|pair| (pair[1] - pair[0]).abs()).fold(0.0, f64::max);
        let naive_leap = 2.0;
        assert!(most_leap < naive_leap * 0.95, "{most_leap}");
        assert!(values.iter().all(|value| value.abs() < 1.5));
    }

    /// A note of an oscillator part from its spec, a second of it at a pitch.
    fn played(pairs: Vec<(&str, Value)>, pitch: f64) -> Vec<f64> {
        let rate = 48_000.0;
        let spec = Value::Map(pairs.into_iter().map(|(key, value)| (Value::from(key), value)).collect());
        let part = compiled(&spec, rate);
        let mut state = OscillatorState::default();
        part.begin(&mut state, pitch);
        part.choose_band(&mut state, pitch, 0.0);
        (0..48_000)
            .map(|place| part.sample(&mut state, pitch, place as f64 / rate, Moves::default(), rate).0)
            .collect()
    }

    /// How many times a second a wave crosses zero upward, which for a plain wave is its pitch's frequency.
    fn crossings(samples: &[f64]) -> usize {
        samples.windows(2).filter(|pair| pair[0] < 0.0 && pair[1] >= 0.0).count()
    }

    /// Each of Basic's waveforms plays at its note's frequency and within full scale.
    #[test]
    fn every_basic_waveform_plays_at_its_pitch() {
        let (pitch, hertz) = (57.0, 220.0);
        for waveform in ["sine", "saw", "square", "triangle", "pulse"] {
            let oscillator = Value::Array(vec![waveform.into(), 0.into(), 1.0.into()]);
            let samples = played(vec![("type", "basic".into()), ("oscillators", Value::Array(vec![oscillator]))], pitch);
            assert!(samples.iter().all(|sample| sample.abs() <= 1.1), "{waveform}");
            assert!((crossings(&samples) as f64 - hertz).abs() <= 2.0, "{waveform} {}", crossings(&samples));
        }
    }

    /// The Pocket's pulse and wave channels play at the note's frequency, the chip's period rounding it to a hair, and
    /// its noise channel is noise, pitched by the note: far more crossings than its pitch.
    #[test]
    fn the_pockets_channels_play_their_notes() {
        let (pitch, hertz) = (57.0, 220.0);
        for voice in ["pulse", "wave"] {
            let samples = played(vec![("type", "pocket".into()), ("chip_voice", voice.into())], pitch);
            assert!(samples.iter().all(|sample| sample.abs() <= 1.1), "{voice}");
            assert!((crossings(&samples) as f64 - hertz).abs() <= 3.0, "{voice} {}", crossings(&samples));
        }
        let noise = played(vec![("type", "pocket".into()), ("chip_voice", "noise".into())], pitch);
        assert!(crossings(&noise) > 2 * hertz as usize, "{}", crossings(&noise));
    }

    /// Oh3's saw and square play at the note's frequency, the saw through its coupling high-pass, within bounds.
    #[test]
    fn oh3s_waves_play_at_their_pitch() {
        let (pitch, hertz) = (45.0, 110.0);
        for wave in ["saw", "square"] {
            let samples = played(vec![("type", "acid".into()), ("acid_wave", wave.into())], pitch);
            assert!(samples.iter().all(|sample| sample.abs() <= 1.5), "{wave}");
            assert!((crossings(&samples) as f64 - hertz).abs() <= 2.0, "{wave} {}", crossings(&samples));
        }
    }

    /// Each oscillator's starting phase is a draw of its own: over many notes, two oscillators start within a twentieth of
    /// a cycle of each other about as often as chance has them, a tenth of the time, never far more.
    #[test]
    fn free_running_oscillators_start_apart_by_chance() {
        let notes = 10_000;
        let near = 0.05;
        let chance = 2.0 * near;
        let mut together = 0;
        for note in 0..notes {
            let random = note as f64 / notes as f64 * 2.0 - 1.0;
            let gap = (free_phase(random, 0) - free_phase(random, 1)).abs();
            if gap.min(1.0 - gap) < near {
                together += 1;
            }
        }
        let share = together as f64 / notes as f64;
        assert!((share - chance).abs() < chance / 4.0, "{share}");
    }
}
