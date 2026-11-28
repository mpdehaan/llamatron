// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The envelope parts a voice's three slots hold (.claude/notes/synthesis/ENVELOPES.md, CHIP_ENVELOPES.md): the snappy
//! ADSR, AR and ASR, the SID chip's own ADSR from its rate table, the vactrol with its hyperbolic fall, age and stability,
//! the acid bass's gate with its accent and charging capacitor, and the handheld chip's sixteen steps.
//!
//! Each answers a level from 0 to about 1 at a time into its note, in closed form, so that no sample ever depends on the
//! chunk it falls in. Env1 is the amp, Env2 the filter's sweep and Env3 the pitch envelope.

pub mod acid_gate;
pub mod adsr;
pub mod chip_steps;
pub mod sid_adsr;
pub mod vactrol;

/// The envelopes a voice has, Env 1 to Env 3, and each one's place among them.
pub const ENVELOPE_COUNT: usize = 3;
pub const ENV1_PLACE: usize = 0;
pub const ENV2_PLACE: usize = 1;
pub const ENV3_PLACE: usize = 2;

use crate::protocol::values::{number, word};
use crate::registry::{self, Entry};
use llamatron_names::spec;
use rmpv::Value;

const SILENT: f64 = 1e-4;
/// How much of Drift's warmth a vactrol's rise takes, against its fall's whole; and a velocity's top, by which a
/// velocity's share becomes the number an accent's threshold is set in.
const RISE_WARMTH_SHARE: f64 = 0.5;
const VELOCITY_TOP: f64 = 127.0;
const T60: f64 = 6.908;
/// The shortest rise that does not click, half a millisecond, about 24 samples: as snappy as the quickest analog
/// envelopes, with no step at a note's start sharp enough to be heard as a tick.
const SHORTEST_ATTACK: f64 = 0.0005;
/// The shortest decay or release to -60 dB that does not click, 2 ms: its first sample falls by under a twelfth.
const SHORTEST_TIME: f64 = 0.002;
/// A vactrol's shortest fall: its hyperbola falls fastest at its very start, so it needs a little longer than an
/// exponential not to click, still far quicker than any real cell.
const SHORTEST_CELL_FALL: f64 = 0.004;
const CURVE_POWER: f64 = 5.64;
const TIMER_CURVE: f64 = 50.0;
const STRAIGHT: f64 = 1.0;
const SWELL_BEND: f64 = 5.0;
const SNAP_SPEED: f64 = 8.0;
const RISE_POWER: f64 = 0.7;
/// How far a vactrol's cell has fallen at its Fall time: to a tenth, so that it halves about a ninth of the way there,
/// quick at first and then lingering, its strike a pluck with a body rather than a click.
const FALL_TO: f64 = 0.1;
const WEAKEST_DRIVE: f64 = 0.05;
const LEAK_SECONDS: f64 = 2.0;
const MOST_LIGHT: f64 = 1.5;
const AGE_DIMMING: f64 = 0.25;
const AGE_SLOWER_RISE: f64 = 0.5;
const AGE_LONGER_FALL: f64 = 0.6;
const AGE_MORE_MEMORY: f64 = 2.0;
const AGE_SPREAD: f64 = 0.05;
const AGE_RISE_SPREAD: f64 = 0.03;
const FALL_SPREAD: f64 = 0.15;
const RISE_SPREAD: f64 = 0.10;
const LIGHT_SPREAD: f64 = 0.08;
const DRIFT: f64 = 0.10;
const MOST_LIGHT_SPREAD: f64 = 1.05;
const WARMTH: [(f64, f64, f64); 3] = [(17.3, 0.5, 0.7), (29.1, 0.3, 2.1), (7.9, 0.2, 4.4)];
const ACCENT_ATTACK: f64 = 0.001;
const END_FADE: f64 = 0.008;
const ACCENT_LOUDER: f64 = 0.7;
const ACCENT_DEEPER: f64 = 0.25;
const ENV_MOD_SHARE: f64 = 0.75;
const CHARGE_STEP: f64 = 0.35;
const CHARGE_SECONDS: f64 = 0.5;
const CHIP_TICKS: f64 = 64.0;
const CHIP_LEVELS: f64 = 15.0;
const CHIP_FADE: f64 = 0.005;
const SID_CLOCK: f64 = 985248.0;
const SID_PERIODS: [f64; 16] = [
    9.0, 32.0, 63.0, 95.0, 149.0, 220.0, 267.0, 313.0, 392.0, 977.0, 1954.0, 3126.0, 3907.0, 11720.0, 19532.0, 31251.0,
];
const SID_TOP: f64 = 255.0;
const SID_SUSTAIN_STEP: f64 = 17.0;
const SID_DIVISIONS: [(f64, f64); 6] = [(93.0, 1.0), (54.0, 2.0), (26.0, 4.0), (14.0, 8.0), (6.0, 16.0), (0.0, 30.0)];

/// What a note tells its envelope: its age and, once it has ended, its age then, in seconds.
#[derive(Clone, Copy)]
pub struct NoteTime {
    pub age: f64,
    pub released: Option<f64>,
}

/// What one voice's envelope keeps: its level where its note ended, a vactrol's start and drive, its rise and fall, an acid
/// accent, and whether it has fallen silent.
#[derive(Clone, Copy, Default)]
pub struct EnvelopeState {
    pub released_from: Option<f64>,
    /// Where the note's envelope starts from: 0 for a fresh note, or the level a restruck voice's envelope had reached,
    /// so that striking a note again never jumps to silence and clicks.
    pub start_level: f64,
    /// The level it gave last, which a restruck voice's envelope starts from.
    pub last: f64,
    pub drive: f64,
    pub rise: f64,
    pub hyperbola: f64,
    pub accented: bool,
    pub done: bool,
}

pub enum EnvelopePart {
    Adsr {
        attack: f64,
        hold: f64,
        decay: f64,
        sustain: f64,
        release: f64,
        snap: f64,
        target: Option<f64>,
        bend: Option<f64>,
        struck: bool,
    },
    SidAdsr {
        held: Vec<(f64, f64)>,
        release_step: f64,
    },
    Vactrol {
        rise: f64,
        fall: f64,
        gated: bool,
        width: f64,
        memory: f64,
        light: f64,
        unstable: (f64, f64, f64),
        drift: f64,
        full: f64,
    },
    AcidGate {
        accent: f64,
        threshold: f64,
        sweep: f64,
        accent_decay: f64,
        amp_decay: f64,
        soft_attack: f64,
        resonance: f64,
    },
    ChipSteps {
        start_level: f64,
        pace: f64,
        up: bool,
    },
    /// No envelope: a level of nothing throughout, so that Env2 sweeps no filter and Env3 bends no pitch. Env1, the
    /// loudness, never holds it.
    Off,
}

/// What the acid gate and the vactrol remember across the notes of their instrument: the capacitor's charge, the cell's
/// light, and when each was left, in seconds on the voice's clock, with how many hits the vactrol has had.
#[derive(Clone, Copy, Default)]
pub struct EnvelopeMemory {
    pub charge: f64,
    pub charged_at: f64,
    pub left: f64,
    pub left_at: f64,
    pub hits: u64,
    /// The vactrol's last note: its state as it started, and when, from which its light at any later moment is worked out.
    pub last_note: Option<(EnvelopeState, f64)>,
    /// The vactrol cell's light history, 0 when rested to 1 when long lit, and when it was last worked out.
    pub history: f64,
    pub history_at: f64,
    /// When the vactrol's last note was released, once it has been, in seconds on the voice's clock.
    pub released_at: Option<f64>,
}

impl EnvelopeMemory {
    /// A note that began at a time was released at another: kept when it is the last note, so that a gated vactrol
    /// knows how long its light was held.
    pub fn note_released(&mut self, began: f64, released: f64) {
        if self.last_note.is_some_and(|(_, last_began)| last_began == began) {
            self.released_at = Some(released);
        }
    }
}

// The light history of a cadmium-sulfide cell, after the vactrol of Mutable Instruments' Streams (streams/vactrol.cc,
// Emilie Gillet, 2014, MIT license): a cell kept lit grows less sensitive within about a second and recovers over about a
// minute in the dark, so a cell played hard answers more slowly than a rested one. The implementation is our own: the
// history is charged by how long each note kept the cell lit, and slows the next note's rise.
/// How fast the cell tires under light, and how slowly it rests in the dark, in seconds.
const TIRING_SECONDS: f64 = 1.0;
const RESTING_SECONDS: f64 = 60.0;
/// How much slower a fully tired cell rises than a rested one: twice as slow (Streams goes as far as five times, which
/// blurs a pluck; this keeps the effect a character, not a change of sound).
const TIRED_SLOWER: f64 = 1.0;

/// The envelope type that is no envelope, which Env2 and Env3 may hold.
const OFF: &str = spec::NONE;

/// An envelope part from its spec, built by its registry's entry; resonance is the filter's, which the acid gate's
/// capacitor is fed through. A type no entry holds is no envelope.
pub fn compiled(spec: &Value, resonance: f64) -> EnvelopePart {
    match registry::find(REGISTRY, word(spec, spec::TYPE, spec::ADSR)) {
        Some(entry) => (entry.build)(spec, resonance),
        None => EnvelopePart::Off,
    }
}

/// How an envelope type is built: from its spec and the filter's resonance.
pub type Build = fn(&Value, f64) -> EnvelopePart;

/// Every envelope type, by the name a spec gives it, the file that holds it, and how it is built.
pub static REGISTRY: &[Entry<Build>] = &[
    Entry {
        name: spec::ACID_GATE,
        file: "acid_gate.rs",
        build: acid_gate::compiled,
    },
    Entry {
        name: spec::ADSR,
        file: "adsr.rs",
        build: |spec, _resonance| adsr::compiled(spec, spec::ADSR),
    },
    Entry {
        name: spec::AR,
        file: "adsr.rs",
        build: |spec, _resonance| adsr::compiled(spec, spec::AR),
    },
    Entry {
        name: spec::ASR,
        file: "adsr.rs",
        build: |spec, _resonance| adsr::compiled(spec, spec::ASR),
    },
    Entry {
        name: spec::CHIP_STEPS,
        file: "chip_steps.rs",
        build: |spec, _resonance| chip_steps::compiled(spec),
    },
    Entry {
        name: OFF,
        file: "mod.rs",
        build: |_spec, _resonance| EnvelopePart::Off,
    },
    Entry {
        name: spec::SID_ADSR,
        file: "sid_adsr.rs",
        build: |spec, _resonance| sid_adsr::sid_adsr(spec),
    },
    Entry {
        name: spec::VACTROL,
        file: "vactrol.rs",
        build: |spec, _resonance| vactrol::vactrol(spec),
    },
];

/// The files of the envelopes' folder that are no envelope type of their own: none today.
pub const HELPERS: &[&str] = &[];

/// The Response of a slow cell, the vactrol's default: two thirds of the way from fast to lazy.
pub const SLOW_RESPONSE: f64 = 0.67;
/// The cells the Response passes through, from fast to lazy, each its place along the gauge, its rise and its fall in
/// seconds: the fast, classic, slow and lazy cells of the vactrol's datasheets.
const CELLS: [(f64, f64, f64); 4] = [(0.0, 0.0025, 0.035), (0.33, 0.005, 0.08), (SLOW_RESPONSE, 0.012, 0.25), (1.0, 0.02, 0.6)];

/// A number the spec holds, or None where it holds none.
fn spec_number(spec: &Value, key: &str) -> Option<f64> {
    spec.as_map()?
        .iter()
        .find(|(name, _)| name.as_str() == Some(key))
        .and_then(|(_, value)| value.as_f64().or_else(|| value.as_i64().map(|whole| whole as f64)))
}

impl EnvelopePart {
    /// Whether the note's velocity is how hard the envelope is struck, rather than a level applied after it.
    pub fn takes_velocity(&self) -> bool {
        matches!(self, EnvelopePart::Vactrol { .. })
    }

    /// Start a note's envelope, from what its instrument remembers, seconds being the note's start on the voice clock; the
    /// acid gate returns its accent's extra filter depth and its short decay.
    pub fn start(&self, memory: &mut EnvelopeMemory, velocity: f64, seconds: f64) -> (EnvelopeState, f64, Option<f64>) {
        let mut state = EnvelopeState::default();
        match self {
            EnvelopePart::Vactrol {
                rise,
                fall,
                memory: keep,
                light,
                unstable,
                drift,
                gated,
                width,
                full,
            } => {
                // The cell's light as this note strikes it: the last note's, risen and fallen to now. A gated note still
                // held is taken as lit until now.
                if let Some((mut last, began)) = memory.last_note {
                    let age = (seconds - began).max(0.0);
                    // A gated note was held until its release, or until now if it is still held.
                    let held = memory.released_at.map_or(age, |released| (released - began).clamp(0.0, age));
                    let note = NoteTime {
                        age,
                        released: gated.then_some(held),
                    };
                    memory.left = vactrol::vactrol_level(&mut last, note, *gated, *width, *full) * full;
                    memory.left_at = seconds;
                    // The last note lit the cell while held, or for its strike, and on through its fall.
                    let lit = if *gated { held } else { *width };
                    let active = age.min(lit + *fall);
                    memory.history *= (-(began - memory.history_at).max(0.0) / RESTING_SECONDS).exp();
                    memory.history += (1.0 - memory.history) * (1.0 - (-active / TIRING_SECONDS).exp());
                    memory.history_at = began + active;
                }
                memory.history *= (-(seconds - memory.history_at).max(0.0) / RESTING_SECONDS).exp();
                memory.history_at = seconds;
                let since = (seconds - memory.left_at).max(0.0);
                let hyperbola = (1.0 / FALL_TO - 1.0) / fall;
                state.start_level = keep * vactrol::fallen_scaled(memory.left, since, hyperbola, *full);
                let (mut rise, mut fall, mut light) = (*rise, *fall, *light);
                if unstable.0 > 0.0 || unstable.1 > 0.0 || unstable.2 > 0.0 {
                    let (first, second, third) = vactrol::hit_normals(memory.hits);
                    let warmth = vactrol::room_warmth(seconds);
                    fall *= (unstable.0 * first).exp() * (1.0 + drift * warmth);
                    rise *= (unstable.1 * second).exp() * (1.0 + RISE_WARMTH_SHARE * drift * warmth);
                    light = (light * (unstable.2 * third).exp()).min(MOST_LIGHT_SPREAD);
                }
                memory.hits += 1;
                rise *= 1.0 + TIRED_SLOWER * memory.history;
                state.drive = (velocity * light).max(WEAKEST_DRIVE);
                state.rise = rise * state.drive.powf(-RISE_POWER);
                state.hyperbola = (1.0 / FALL_TO - 1.0) / fall;
                memory.last_note = Some((state, seconds));
                memory.released_at = None;
                (state, 0.0, None)
            }
            EnvelopePart::AcidGate {
                accent,
                threshold,
                sweep,
                accent_decay,
                resonance,
                ..
            } => {
                let accented = (velocity * VELOCITY_TOP).round() >= *threshold;
                memory.charge *= (-(seconds - memory.charged_at) / CHARGE_SECONDS).exp();
                memory.charged_at = seconds;
                state.accented = accented;
                if !accented {
                    return (state, 0.0, None);
                }
                memory.charge = (memory.charge + CHARGE_STEP * sweep * resonance).min(1.0);
                (state, ACCENT_DEEPER * accent + memory.charge * ENV_MOD_SHARE, Some(*accent_decay))
            }
            _ => (state, 0.0, None),
        }
    }

    /// The envelope's level at a time into its note; short, when given, is a decay an accent forces in place of the
    /// envelope's own. Marks the state done once the note has fallen silent.
    #[inline]
    pub fn level(&self, state: &mut EnvelopeState, note: NoteTime, short: Option<f64>) -> f64 {
        let level = self.level_now(state, note, short);
        state.last = level;
        level
    }

    fn level_now(&self, state: &mut EnvelopeState, note: NoteTime, short: Option<f64>) -> f64 {
        match self {
            EnvelopePart::Adsr { .. } => self.adsr_level(state, note, short),
            EnvelopePart::SidAdsr { held, release_step } => sid_adsr::sid_level(held, *release_step, state, note),
            EnvelopePart::Vactrol { gated, width, full, .. } => vactrol::vactrol_level(state, note, *gated, *width, *full),
            EnvelopePart::AcidGate {
                accent,
                accent_decay,
                amp_decay,
                soft_attack,
                ..
            } => acid_gate::acid_level(state, note, *accent, *accent_decay, *amp_decay, *soft_attack),
            EnvelopePart::ChipSteps { start_level, pace, up } => chip_steps::chip_level(state, note, *start_level, *pace, *up),
            EnvelopePart::Off => 0.0,
        }
    }
}

#[cfg(test)]
mod tests {

    /// An envelope set to Off holds at nothing while its note sounds and after it ends, so that Env2 sweeps no filter and
    /// Env3 bends no pitch.
    #[test]
    fn an_envelope_set_off_holds_at_nothing() {
        let spec = Value::Map(vec![(Value::from(spec::TYPE), Value::from(OFF))]);
        let off = compiled(&spec, 0.0);
        let mut state = EnvelopeState::default();
        let (held, released) = (0.3, 0.5);
        assert_eq!(off.level(&mut state, NoteTime { age: held, released: None }, None), 0.0);
        assert_eq!(
            off.level(
                &mut state,
                NoteTime {
                    age: released + held,
                    released: Some(released)
                },
                None
            ),
            0.0
        );
    }

    use super::*;
    use rmpv::Value;

    /// A millisecond's share of a second, the step the tests read an envelope at; half, a sustain the tests hold at and
    /// the moment they release; the chip's top level; and the millisecond after a note's start.
    const MILLISECONDS_A_SECOND: f64 = 1000.0;
    const HALF: f64 = 0.5;
    const CHIP_TOP_LEVEL: f64 = 15.0;

    /// Every envelope type at its snappiest settings is tight, at its top within a millisecond and silent within a few
    /// more of its release, yet never steps by more than a twelfth of its swing from one sample to the next, so that
    /// neither edge clicks.
    #[test]
    fn every_envelope_is_snappy_without_clicking() {
        let rate = 48_000.0;
        let twelfths = 12.0;
        let most_step = 1.0 / twelfths;
        let (released, heard) = (0.005, 0.02);
        let snappiest = [
            spec(&[
                (spec::TYPE, spec::ADSR.into()),
                (spec::ATTACK, 0.0.into()),
                (spec::DECAY, 0.0.into()),
                (spec::SUSTAIN, HALF.into()),
                (spec::RELEASE, 0.0.into()),
            ]),
            spec(&[(spec::TYPE, spec::AR.into()), (spec::ATTACK, 0.0.into()), (spec::RELEASE, 0.0.into())]),
            spec(&[(spec::TYPE, spec::ASR.into()), (spec::ATTACK, 0.0.into()), (spec::RELEASE, 0.0.into())]),
            spec(&[
                (spec::TYPE, spec::SID_ADSR.into()),
                (spec::ATTACK, 0.0.into()),
                (spec::DECAY, 0.0.into()),
                (spec::RELEASE, 0.0.into()),
            ]),
            spec(&[(spec::TYPE, spec::VACTROL.into()), (spec::RISE, 0.0.into()), (spec::FALL, 0.0.into())]),
            spec(&[
                (spec::TYPE, spec::ACID_GATE.into()),
                (spec::SOFT_ATTACK, 0.0.into()),
                (spec::AMP_DECAY, 0.0.into()),
            ]),
            spec(&[(spec::TYPE, spec::CHIP_STEPS.into()), (spec::START_LEVEL, CHIP_TOP_LEVEL.into())]),
        ];
        // Every envelope type with a shape of its own is held here: a new type fails until its snappiest settings join.
        let held: Vec<&str> = snappiest
            .iter()
            .filter_map(|each| each.as_map())
            .filter_map(|pairs| {
                pairs
                    .iter()
                    .find(|(key, _)| key.as_str() == Some(spec::TYPE))
                    .and_then(|(_, value)| value.as_str())
            })
            .collect();
        for entry in REGISTRY.iter().filter(|entry| entry.name != OFF) {
            assert!(held.contains(&entry.name), "the envelope type {} has no snappiest settings here", entry.name);
        }
        for each in snappiest {
            let part = compiled(&each, 0.0);
            let (full_velocity, struck_at) = (1.0, 0.0);
            let (mut state, ..) = part.start(&mut EnvelopeMemory::default(), full_velocity, struck_at);
            let mut last = 0.0;
            for sample in 0..(heard * rate) as usize {
                let age = sample as f64 / rate;
                let note = NoteTime { age, released: Some(released) };
                let level = part.level(&mut state, note, None);
                assert!((level - last).abs() <= most_step, "{each:?} steps {} at {age}", (level - last).abs());
                last = level;
            }
        }
        let adsr = compiled(
            &spec(&[(spec::TYPE, spec::ASR.into()), (spec::ATTACK, 0.0.into()), (spec::RELEASE, 0.0.into())]),
            0.0,
        );
        let mut state = EnvelopeState::default();
        let at = |age: f64, state: &mut EnvelopeState| adsr.level(state, NoteTime { age, released: Some(released) }, None);
        let (a_millisecond, three_milliseconds, near_top, near_silent) = (0.001, 0.003, 0.99, 0.01);
        assert!(at(a_millisecond, &mut state) > near_top, "at its top within a millisecond");
        assert!(
            at(released + three_milliseconds, &mut state) < near_silent,
            "silent within three milliseconds of its release"
        );
    }

    fn spec(pairs: &[(&str, Value)]) -> Value {
        Value::Map(pairs.iter().map(|(key, value)| (Value::from(*key), value.clone())).collect())
    }

    fn play(part: &EnvelopePart, released: Option<f64>, seconds: f64) -> (Vec<f64>, bool) {
        let mut state = EnvelopeState::default();
        let levels: Vec<f64> = (0..(seconds * MILLISECONDS_A_SECOND) as usize)
            .map(|ms| {
                part.level(
                    &mut state,
                    NoteTime {
                        age: ms as f64 / MILLISECONDS_A_SECOND,
                        released,
                    },
                    None,
                )
            })
            .collect();
        (levels, state.done)
    }

    #[test]
    fn an_adsr_peaks_at_its_attack_holds_its_sustain_and_releases_to_silence() {
        let (attack, decay, release) = (0.01, 0.2, 0.1);
        let part = compiled(
            &spec(&[
                (spec::TYPE, spec::ADSR.into()),
                (spec::ATTACK, attack.into()),
                (spec::DECAY, decay.into()),
                (spec::SUSTAIN, HALF.into()),
                (spec::RELEASE, release.into()),
            ]),
            0.0,
        );
        let (levels, done) = play(&part, Some(HALF), 1.0);
        let (after_attack, before_release, near_top, near_sustain) = (10, 499, 0.05, 0.01);
        assert!((levels[after_attack] - 1.0).abs() < near_top);
        assert!((levels[before_release] - HALF).abs() < near_sustain);
        assert!(done);
    }

    #[test]
    fn the_sid_adsr_holds_its_sixteen_level_sustain() {
        let (rate_step, sustain_step) = (9, 8);
        let part = compiled(
            &spec(&[
                (spec::TYPE, spec::SID_ADSR.into()),
                (spec::ATTACK, 0.into()),
                (spec::DECAY, rate_step.into()),
                (spec::SUSTAIN, sustain_step.into()),
                (spec::RELEASE, rate_step.into()),
            ]),
            0.0,
        );
        let (heard_seconds, before_release) = (3.0, 499);
        let (levels, done) = play(&part, Some(HALF), heard_seconds);
        assert!((levels[before_release] * SID_TOP - sustain_step as f64 * SID_SUSTAIN_STEP).abs() <= 1.0);
        assert!(done);
    }

    /// A struck cell peaks near full, then falls to a tenth of its peak by its Fall time, whatever its Trigger time: a
    /// short strike that lights the cell only a little still falls at the speed its heard level gives, as a pluck does.
    #[test]
    fn a_struck_vactrol_peaks_and_falls_to_a_tenth_by_its_fall_time() {
        let (rise, fall) = (0.012, 0.25);
        let at_fall = |strike: f64| {
            let part = compiled(
                &spec(&[
                    (spec::TYPE, spec::VACTROL.into()),
                    (spec::RISE, rise.into()),
                    (spec::FALL, fall.into()),
                    (spec::STRIKE_WIDTH, strike.into()),
                    (spec::MEMORY, 0.0.into()),
                ]),
                0.0,
            );
            let mut memory = EnvelopeMemory::default();
            let (mut state, _, _) = part.start(&mut memory, 1.0, 0.0);
            let level_at = |state: &mut EnvelopeState, age: f64| part.level(state, NoteTime { age, released: None }, None);
            let peak = level_at(&mut state, strike);
            (peak, level_at(&mut state, strike + fall) / peak)
        };
        // A tenth by the hyperbola, a little under it by the slow leak beneath its tail.
        let (short_strike, long_strike) = (0.002, 0.02);
        for strike in [short_strike, long_strike] {
            let (_, share) = at_fall(strike);
            let (least, most) = (0.07, 0.11);
            assert!(share > least && share < most, "{strike}: {share}");
        }
        let (peak, _) = at_fall(short_strike);
        let near_full = 0.05;
        assert!((peak - 1.0).abs() < near_full, "a full strike peaks near full: {peak}");
    }

    /// A cell played hard tires: after a run of held notes it rises more slowly than when rested, and a minute and more of
    /// rest brings it back.
    #[test]
    fn a_vactrol_played_hard_rises_more_slowly_and_recovers_at_rest() {
        let part = compiled(
            &spec(&[(spec::TYPE, spec::VACTROL.into()), (spec::DRIVE, spec::GATE.into()), (spec::MEMORY, 0.0.into())]),
            0.0,
        );
        let mut memory = EnvelopeMemory::default();
        let (rested, _, _) = part.start(&mut memory, 1.0, 0.0);
        let (held, apart) = (1.0, 1.5);
        let notes = 8;
        memory.note_released(0.0, held);
        let mut tired = rested;
        for note in 1..=notes {
            let began = note as f64 * apart;
            tired = part.start(&mut memory, 1.0, began).0;
            memory.note_released(began, began + held);
        }
        let (slower, as_fast) = (1.5, 1.05);
        assert!(tired.rise > rested.rise * slower, "a tired cell rises more slowly");
        let long_rest = 600.0;
        let (recovered, _, _) = part.start(&mut memory, 1.0, notes as f64 * apart + held + long_rest);
        assert!(recovered.rise < rested.rise * as_fast, "a rested cell rises as fast as before");
    }

    /// An AR rises over its attack and falls over its release at once, held or not, and ends; an ASR holds full while
    /// its note is held.
    #[test]
    fn an_ar_falls_after_its_attack_and_an_asr_holds_full() {
        let (attack, release, sustain) = (0.01, 0.1, 0.3);
        let shaped = |kind: &str| {
            compiled(
                &spec(&[
                    (spec::TYPE, kind.into()),
                    (spec::ATTACK, attack.into()),
                    (spec::RELEASE, release.into()),
                    (spec::SUSTAIN, sustain.into()),
                ]),
                0.0,
            )
        };
        let (ar_levels, ar_done) = play(&shaped(spec::AR), None, 1.0);
        let peak = ar_levels.iter().cloned().fold(0.0_f64, f64::max);
        let (half_a_second, near_top, near_silent, full) = (500, 0.95, 0.01, 0.99);
        assert!(
            peak > near_top && ar_levels[half_a_second] < near_silent && ar_done,
            "an AR falls while held and ends"
        );
        let (asr_levels, _) = play(&shaped(spec::ASR), None, 1.0);
        assert!(asr_levels[half_a_second] > full, "an ASR holds full while held, not at the sustain set");
    }

    /// An acid gate's accented note swells above an unaccented one, and both decay over the amp decay.
    #[test]
    fn an_accented_acid_note_swells_above_an_unaccented_one() {
        let (accented_from, resonance) = (110.0, 0.5);
        let part = compiled(
            &spec(&[(spec::TYPE, spec::ACID_GATE.into()), (spec::ACCENT_THRESHOLD, accented_from.into())]),
            resonance,
        );
        let peak_of = |velocity: f64| {
            let mut memory = EnvelopeMemory::default();
            let (mut state, _, _) = part.start(&mut memory, velocity / VELOCITY_TOP, 0.0);
            let fifth_of_a_second = 200;
            (0..fifth_of_a_second)
                .map(|ms| {
                    part.level(
                        &mut state,
                        NoteTime {
                            age: ms as f64 / MILLISECONDS_A_SECOND,
                            released: None,
                        },
                        None,
                    )
                })
                .fold(0.0_f64, f64::max)
        };
        let (soft, accented) = (90.0, 120.0);
        let swells = 1.1;
        assert!(peak_of(accented) > peak_of(soft) * swells, "{} against {}", peak_of(accented), peak_of(soft));
    }

    /// Chip steps fall a sixteenth of the way at each tick of their pace, never between, and end at nothing.
    #[test]
    fn chip_steps_fall_in_sixteen_steps() {
        let (pace, heard_seconds, tolerance) = (2.0, 2.0, 1e-9);
        let part = compiled(
            &spec(&[
                (spec::TYPE, spec::CHIP_STEPS.into()),
                (spec::START_LEVEL, CHIP_TOP_LEVEL.into()),
                (spec::LEVEL_PACE, pace.into()),
            ]),
            0.0,
        );
        let (levels, done) = play(&part, None, heard_seconds);
        assert!(
            levels
                .iter()
                .all(|level| ((level * CHIP_LEVELS).round() - level * CHIP_LEVELS).abs() < tolerance),
            "steps only"
        );
        // Its first level is eased in over the shortest attack, so the millisecond after the start holds it.
        assert!(levels[1] == 1.0 && *levels.last().expect("a last level") == 0.0 && done);
    }
}
