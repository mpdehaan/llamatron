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
use crate::dsp::{OCTAVE, SHARE_BITS, SHARE_SHIFT, SPLITMIX_LAST, SPLITMIX_MULTIPLIERS, SPLITMIX_SHIFTS};
use crate::oscillators::tables::{Tables, Waveform, TABLE_MASK, TABLE_SIZE};
use crate::protocol::values::{as_number, list, number, numbers, truth, word};
use crate::registry::{self, Entry};
use llamatron_names::spec;
use rmpv::Value;
use std::sync::Arc;

const MIDDLE_A: f64 = 69.0;
/// The semitones of an octave.
const SEMITONES_AN_OCTAVE: f64 = 12.0;
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
    unclamped_frequency_of(pitch.clamp(LOWEST_PITCH, HIGHEST_PITCH))
}

/// A MIDI number's frequency in hertz, equal tempered from A 440, at any pitch, as an oscillator running below hearing
/// takes it.
pub fn unclamped_frequency_of(pitch: f64) -> f64 {
    A_FREQUENCY * OCTAVE.powf((pitch - MIDDLE_A) / SEMITONES_AN_OCTAVE)
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
    pub phases: [f64; MOST_OSCILLATORS],
    pub second_phase: f64,
    pub period: i64,
    pub ticks: i64,
    pub band: usize,
    /// The pitch the read speeds were last worked out for, and those speeds, so that a note whose pitch nothing
    /// moves works out its powers of two once, not every sample.
    pub speeds_for: f64,
    pub speeds: [f64; MOST_OSCILLATORS],
    /// Oh3's coupling into its filter, a one-pole high-pass, made as its note begins.
    pub coupling: OnePoleHighpass,
    /// Asheville: each oscillator's last value, which the Mod Matrix's Osc 1 to Osc 3 sources read; its noise's state;
    /// the mixer's last output, which Feedback loops back; and when the note began after the instrument started, with
    /// the voice's own random number, from which each oscillator's drift is its own.
    pub sides: [f64; OWN_OSCILLATORS],
    pub noise_state: u64,
    pub last_out: f64,
    /// Asheville: each oscillator's sub-oscillator's phase.
    pub sub_phases: [f64; OWN_OSCILLATORS],
    /// The SID's synced wave: its phase in cycles, and the share of a jump's smoothing owed to the next sample.
    pub sync_phase: f64,
    pub sync_next: f64,
    pub began: f64,
    pub random: f64,
    /// Asheville: each oscillator's fast jitter, in cents before Drift scales it, and the seeded noise it is drawn from.
    pub jitter: [f64; OWN_OSCILLATORS],
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
        /// The chip's Ring and Sync switches, each on or off, both on together as the chip allows.
        ring: bool,
        sync: bool,
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
pub enum ChipVoice {
    Pulse,
    Wave,
    Noise,
}

/// The oscillators a spec describes, built by their registry's entry; a type no entry holds sounds nothing.
pub fn compiled(spec: &Value, rate: f64) -> OscillatorPart {
    match registry::find(REGISTRY, word(spec, spec::TYPE, BASIC)) {
        Some(entry) => (entry.build)(spec, rate),
        None => OscillatorPart::Silent,
    }
}

/// How an oscillator type is built: from its spec, at a sample rate.
pub type Build = fn(&Value, f64) -> OscillatorPart;

/// The type of oscillator a spec that names none plays.
const BASIC: &str = spec::BASIC;
/// The drum machine: a sound of its own (drums/), which the patch builds in place of any oscillator; its entry here
/// builds nothing, since no voice of oscillators plays it.
pub const DRUM: &str = spec::DRUM;

/// Every oscillator type, by the name a spec gives it, the file that holds it, and how it is built.
pub static REGISTRY: &[Entry<Build>] = &[
    Entry {
        name: spec::ACID,
        file: "acid.rs",
        build: acid::compiled,
    },
    Entry {
        name: spec::ASHEVILLE,
        file: "asheville.rs",
        build: |spec, _rate| OscillatorPart::Asheville(Box::new(asheville::compiled(spec))),
    },
    Entry {
        name: BASIC,
        file: "basic.rs",
        build: |spec, _rate| basic::compiled(spec),
    },
    Entry {
        name: DRUM,
        file: "mod.rs",
        build: |_spec, _rate| OscillatorPart::Silent,
    },
    Entry {
        name: spec::POCKET,
        file: "pocket.rs",
        build: pocket::compiled,
    },
    Entry {
        name: spec::SID,
        file: "sid.rs",
        build: sid::compiled,
    },
];

/// The files of the oscillators' folder that are no oscillator of their own but a part they use: the wavetables.
pub const HELPERS: &[&str] = &["tables.rs"];

/// What mixes a note's random number and an oscillator's place into a seed of their own: the golden ratio as a
/// 64-bit number, the usual odd constant of such hashes.
const PHASE_MIX: u64 = crate::dsp::GOLDEN_GAMMA;

/// Where a free-running oscillator is in its cycle as a note starts, from the note's random number, from -1 to 1, and the
/// oscillator's place: each oscillator its own draw, unrelated to the others', so that no two start near together more
/// often than chance would have them.
pub fn free_phase(random: f64, place: usize) -> f64 {
    // A SplitMix64 step of the random number's bits and the place, its top 53 bits a share of a cycle.
    let mut bits = random.to_bits() ^ (place as u64 + 1).wrapping_mul(PHASE_MIX);
    bits = (bits ^ (bits >> SPLITMIX_SHIFTS[0])).wrapping_mul(SPLITMIX_MULTIPLIERS[0]);
    bits = (bits ^ (bits >> SPLITMIX_SHIFTS[1])).wrapping_mul(SPLITMIX_MULTIPLIERS[1]);
    bits ^= bits >> SPLITMIX_SHIFTS[SPLITMIX_LAST];
    (bits >> SHARE_SHIFT) as f64 / (1u64 << SHARE_BITS) as f64
}

/// What moves the oscillators at one sample: semitones of pitch, the Mod Matrix's Detune and Fine among them, a share of
/// the pulse's width, and semitones added to the SID's Interval.
#[derive(Clone, Copy, Default)]
pub struct Moves {
    pub pitch: f64,
    pub width: f64,
    pub interval: f64,
    /// What the Mod Matrix moves each of Asheville's oscillators alone by: its pitch in semitones, its Detune and Fine
    /// with it, and its pulse width.
    pub osc_pitch: [f64; OWN_OSCILLATORS],
    pub osc_width: [f64; OWN_OSCILLATORS],
}

/// How many oscillators of Asheville's the Mod Matrix moves one by one.
pub const OWN_OSCILLATORS: usize = asheville::OSCILLATOR_COUNT;
/// The most oscillators an engine has, each a phase and a speed of a voice's own.
pub const MOST_OSCILLATORS: usize = asheville::OSCILLATOR_COUNT;

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
            OscillatorPart::Pocket { .. } => CHIP_CLOCK / (PERIODS - state.period as f64) * OCTAVE.powf(reach / SEMITONES_AN_OCTAVE),
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
    use crate::dsp::testing::{RATE, SECOND};

    /// A tenth of a second of samples, and the most a wave's crossings may stray from its pitch's frequency.
    const TENTH_SECOND: usize = 4800;
    const CROSSINGS_STRAY: f64 = 2.0;

    /// No pitch, however far modulation moves it, plays outside about 8 Hz to 20 kHz: never under MIDI's lowest note.
    #[test]
    fn every_oscillator_frequency_is_held_within_hearing() {
        let (far_above, far_below) = (400.0, -300.0);
        assert_eq!(frequency_of(far_above), frequency_of(HIGHEST_PITCH));
        assert_eq!(frequency_of(far_below), frequency_of(LOWEST_PITCH));
        let (top_of_hearing, bottom_of_hearing) = (20_000.0, 8.0);
        assert!(frequency_of(HIGHEST_PITCH) < top_of_hearing && frequency_of(LOWEST_PITCH) > bottom_of_hearing);
    }

    /// A note bent up by its modulation reads the table of the highest pitch it reaches, cut lower, so that analog-style
    /// FM does not fold harmonics back down; a note bent nowhere reads its own pitch's table.
    #[test]
    fn a_note_bent_up_reads_the_table_of_its_highest_pitch() {
        let spec = rmpv::Value::Map(vec![(spec::TYPE.into(), spec::ACID.into())]);
        let part = compiled(&spec, RATE);
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
        let (slave, master, width) = (3_100.0, 440.0, 0.5);
        let values: Vec<f64> = (0..TENTH_SECOND)
            .map(|_| sid::sid_synced(SidWave::Saw, &mut state, slave, master, width, RATE))
            .collect();
        let pair = 2;
        let most_leap = values.windows(pair).map(|pair| (pair[1] - pair[0]).abs()).fold(0.0, f64::max);
        let (naive_leap, smoothed, bound) = (2.0, 0.95, 1.5);
        assert!(most_leap < naive_leap * smoothed, "{most_leap}");
        assert!(values.iter().all(|value| value.abs() < bound));
    }

    /// A note of an oscillator part from its spec, a second of it at a pitch.
    fn played(pairs: Vec<(&str, Value)>, pitch: f64) -> Vec<f64> {
        let spec = Value::Map(pairs.into_iter().map(|(key, value)| (Value::from(key), value)).collect());
        let part = compiled(&spec, RATE);
        let mut state = OscillatorState::default();
        part.begin(&mut state, pitch);
        part.choose_band(&mut state, pitch, 0.0);
        (0..SECOND)
            .map(|place| part.sample(&mut state, pitch, place as f64 / RATE, Moves::default(), RATE).0)
            .collect()
    }

    /// How many times a second a wave crosses zero upward, which for a plain wave is its pitch's frequency.
    fn crossings(samples: &[f64]) -> usize {
        let pair = 2;
        samples.windows(pair).filter(|pair| pair[0] < 0.0 && pair[1] >= 0.0).count()
    }

    /// Each of Basic's waveforms plays at its note's frequency and within full scale.
    #[test]
    fn every_basic_waveform_plays_at_its_pitch() {
        let (pitch, hertz) = (57.0, 220.0);
        for waveform in [spec::SINE, spec::SAW, spec::SQUARE, spec::TRIANGLE, spec::PULSE] {
            let oscillator = Value::Array(vec![waveform.into(), 0.into(), 1.0.into()]);
            let samples = played(
                vec![(spec::TYPE, spec::BASIC.into()), (spec::OSCILLATORS, Value::Array(vec![oscillator]))],
                pitch,
            );
            let bound = 1.1;
            assert!(samples.iter().all(|sample| sample.abs() <= bound), "{waveform}");
            assert!(
                (crossings(&samples) as f64 - hertz).abs() <= CROSSINGS_STRAY,
                "{waveform} {}",
                crossings(&samples)
            );
        }
    }

    /// The Pocket's pulse and wave channels play at the note's frequency, the chip's period rounding it to a hair, and
    /// its noise channel is noise, pitched by the note: far more crossings than its pitch.
    #[test]
    fn the_pockets_channels_play_their_notes() {
        let (pitch, hertz) = (57.0, 220.0);
        for voice in [spec::PULSE, spec::WAVE] {
            let samples = played(vec![(spec::TYPE, spec::POCKET.into()), (spec::CHIP_VOICE, voice.into())], pitch);
            let (bound, rounded_stray) = (1.1, 3.0);
            assert!(samples.iter().all(|sample| sample.abs() <= bound), "{voice}");
            assert!((crossings(&samples) as f64 - hertz).abs() <= rounded_stray, "{voice} {}", crossings(&samples));
        }
        let noise = played(vec![(spec::TYPE, spec::POCKET.into()), (spec::CHIP_VOICE, spec::NOISE.into())], pitch);
        let far_more = 2;
        assert!(crossings(&noise) > far_more * hertz as usize, "{}", crossings(&noise));
    }

    /// Oh3's saw and square play at the note's frequency, the saw through its coupling high-pass, within bounds.
    #[test]
    fn oh3s_waves_play_at_their_pitch() {
        let (pitch, hertz) = (45.0, 110.0);
        for wave in [spec::SAW, spec::SQUARE] {
            let samples = played(vec![(spec::TYPE, spec::ACID.into()), (spec::ACID_WAVE, wave.into())], pitch);
            let bound = 1.5;
            assert!(samples.iter().all(|sample| sample.abs() <= bound), "{wave}");
            assert!((crossings(&samples) as f64 - hertz).abs() <= CROSSINGS_STRAY, "{wave} {}", crossings(&samples));
        }
    }

    /// A synced SID wave sounds at the note played: its master runs at the note, so that its lowest strong partial is the
    /// note's, whatever the Interval tunes the synced wave to.
    #[test]
    fn a_synced_sid_wave_sounds_at_its_note() {
        let a_fifth = 7.0;
        let (pitch, hertz) = (57.0, 220usize);
        let pairs = vec![
            (spec::TYPE, Value::from(spec::SID)),
            (spec::WAVE, Value::from(spec::SAW)),
            (spec::SYNC, Value::from(true)),
            (spec::INTERVAL, Value::from(a_fifth)),
        ];
        let out: Vec<f64> = played(pairs, pitch);
        let mut bins: Vec<rustfft::num_complex::Complex<f64>> = out.iter().map(|sample| rustfft::num_complex::Complex::new(*sample, 0.0)).collect();
        rustfft::FftPlanner::new().plan_fft_forward(SECOND).process(&mut bins);
        let (strong_share, half, lowest_read, highest_read, near) = (0.05, 2.0, 20, 2000, 2);
        let strong = strong_share * SECOND as f64 / half;
        let lowest = (lowest_read..highest_read).find(|bin| bins[*bin].norm() > strong);
        assert!(lowest.is_some_and(|bin| bin.abs_diff(hertz) <= near), "lowest strong partial {lowest:?} Hz");
    }
}
