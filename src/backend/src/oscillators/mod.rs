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

pub mod acid;
pub mod asheville;
pub mod basic;
pub mod pocket;
pub mod sid;
pub mod tables;

use crate::dsp::blep;
use crate::dsp::one_pole::OnePoleHighpass;
use crate::oscillators::tables::{Tables, Waveform, TABLE_MASK, TABLE_SIZE};
use crate::protocol::values::{as_number, list, number, numbers, truth, word};
use crate::registry::{self, Entry};
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
    pub coupling: OnePoleHighpass,
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
    /// Asheville: each oscillator's fast jitter, in cents before Drift scales it, and the seeded noise it is drawn from.
    pub jitter: [f64; 3],
    pub jitter_noise: u64,
}

/// One of Basic's oscillators: its waveform, made every sample by voice/blep.rs, its detune in cents and its level.
pub struct Partial {
    waveform: Waveform,
    cents: f64,
    level: f64,
}

/// An oscillator type as its entry builds it.
pub enum OscillatorPart {
    /// What a type no registry holds plays: nothing.
    Silent,
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

/// The oscillators a spec describes, built by their registry's entry; a type no entry holds sounds nothing.
pub fn compiled(spec: &Value, rate: f64) -> OscillatorPart {
    match registry::find(REGISTRY, word(spec, "type", BASIC)) {
        Some(entry) => (entry.build)(spec, rate),
        None => OscillatorPart::Silent,
    }
}

/// How an oscillator type is built: from its spec, at a sample rate.
pub type Build = fn(&Value, f64) -> OscillatorPart;

/// The type of oscillator a spec that names none plays.
const BASIC: &str = "basic";

/// Every oscillator type, by the name a spec gives it, the file that holds it, and how it is built.
pub static REGISTRY: &[Entry<Build>] = &[
    Entry {
        name: "acid",
        file: "acid.rs",
        build: acid::compiled,
    },
    Entry {
        name: "asheville",
        file: "asheville.rs",
        build: |spec, _rate| OscillatorPart::Asheville(Box::new(asheville::compiled(spec))),
    },
    Entry {
        name: BASIC,
        file: "basic.rs",
        build: |spec, _rate| basic::compiled(spec),
    },
    Entry {
        name: "pocket",
        file: "pocket.rs",
        build: pocket::compiled,
    },
    Entry {
        name: "sid",
        file: "sid.rs",
        build: sid::compiled,
    },
];

/// The files of the oscillators' folder that are no oscillator of their own but a part they use: the wavetables.
pub const HELPERS: &[&str] = &["tables.rs"];

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
            state.coupling = OnePoleHighpass::new(acid::COUPLING_HIGHPASS_HZ, *rate);
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
            OscillatorPart::Basic { partials } => (basic::basic_sample(partials, state, pitch, moves, rate), false),
            OscillatorPart::Sid { .. } => (self.sid_sample(state, pitch, seconds, moves, rate), false),
            OscillatorPart::Pocket { .. } => self.pocket_sample(state, seconds, moves, rate),
            OscillatorPart::Acid { tables, tuning, .. } => (acid::acid_sample(tables, state, pitch + tuning + moves.pitch, rate), false),
            OscillatorPart::Asheville(asheville) => (asheville.sample(state, pitch, seconds, moves, rate), false),
            OscillatorPart::Silent => (0.0, false),
        }
    }
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
        let values: Vec<f64> = (0..4800).map(|_| sid::sid_synced(SidWave::Saw, &mut state, slave, master, 0.5, rate)).collect();
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
