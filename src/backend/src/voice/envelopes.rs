// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The envelope parts a voice's three slots hold (.claude/notes/synthesis/ENVELOPES.md, CHIP_ENVELOPES.md): the snappy
//! ADSR, AR and ASR, the SID chip's own ADSR from its rate table, the vactrol with its hyperbolic fall, age and stability,
//! the acid bass's gate with its accent and charging capacitor, and the handheld chip's sixteen steps.
//!
//! Each answers a level from 0 to about 1 at a time into its note, in closed form, so that no sample ever depends on the
//! chunk it falls in. Env1 is the amp, Env2 the filter's sweep and Env3 the pitch envelope.

use crate::protocol::values::{number, word};
use rmpv::Value;

const SILENT: f64 = 1e-4;
const T60: f64 = 6.908;
const SHORTEST_ATTACK: f64 = 0.0001;
const SHORTEST_TIME: f64 = 0.001;
const CURVE_POWER: f64 = 5.64;
const TIMER_CURVE: f64 = 50.0;
const STRAIGHT: f64 = 1.0;
const SWELL_BEND: f64 = 5.0;
const SNAP_SPEED: f64 = 8.0;
const RISE_POWER: f64 = 0.7;
const FALL_TO: f64 = 0.01;
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
    pub start_level: f64,
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
}

/// The envelope type that is no envelope, which Env2 and Env3 may hold.
const OFF: &str = "none";

/// An envelope part from its spec; resonance is the filter's, which the acid gate's capacitor is fed through.
pub fn compiled(spec: &Value, resonance: f64) -> EnvelopePart {
    match word(spec, "type", "adsr") {
        "sid_adsr" => sid_adsr(spec),
        "vactrol" => vactrol(spec),
        "acid_gate" => EnvelopePart::AcidGate {
            accent: number(spec, "accent", 0.6),
            threshold: number(spec, "accent_threshold", 110.0),
            sweep: number(spec, "accent_sweep", 0.5),
            accent_decay: number(spec, "accent_decay", 0.2).max(SHORTEST_TIME),
            amp_decay: number(spec, "amp_decay", 1.5).max(SHORTEST_TIME),
            soft_attack: number(spec, "soft_attack", 0.003).max(SHORTEST_ATTACK),
            resonance,
        },
        OFF => EnvelopePart::Off,
        "chip_steps" => EnvelopePart::ChipSteps {
            start_level: number(spec, "start_level", 15.0),
            pace: number(spec, "level_pace", 0.0),
            up: crate::protocol::values::truth(spec, "level_up", false),
        },
        kind => adsr(spec, kind),
    }
}

fn adsr(spec: &Value, kind: &str) -> EnvelopePart {
    let struck = kind == "ar";
    let release = number(spec, "release", 0.2).max(SHORTEST_TIME) / T60;
    let mut sustain = number(spec, "sustain", 0.6);
    let mut decay = number(spec, "decay", 0.3).max(SHORTEST_TIME) / T60;
    if struck {
        sustain = 0.0;
        decay = release;
    } else if kind == "asr" {
        sustain = 1.0;
    }
    let curve = number(spec, "attack_curve", TIMER_CURVE);
    let target = (curve > STRAIGHT).then(|| 1.0 + 0.5 * (TIMER_CURVE / curve).powf(CURVE_POWER));
    let bend = (curve < -STRAIGHT).then(|| SWELL_BEND * -curve / 100.0);
    EnvelopePart::Adsr {
        attack: number(spec, "attack", 0.005).max(SHORTEST_ATTACK),
        hold: number(spec, "hold", 0.0),
        decay,
        sustain,
        release,
        snap: number(spec, "snap", 0.0),
        target,
        bend,
        struck,
    }
}

fn sid_adsr(spec: &Value) -> EnvelopePart {
    let rate = |name: &str, default: f64| SID_PERIODS[(number(spec, name, default) as usize).min(15)] / SID_CLOCK;
    let attack_step = rate("attack", 0.0);
    let sustain = number(spec, "sustain", 10.0).clamp(0.0, 15.0) * SID_SUSTAIN_STEP;
    let rise = SID_TOP * attack_step;
    let mut held = vec![(0.0, 0.0)];
    for (time, level) in sid_fall(SID_TOP, sustain, rate("decay", 9.0)) {
        held.push((rise + time, level));
    }
    EnvelopePart::SidAdsr {
        held,
        release_step: rate("release", 9.0),
    }
}

fn vactrol(spec: &Value) -> EnvelopePart {
    let age = number(spec, "age", 0.0);
    let light = 1.0 - AGE_DIMMING * age;
    let rise = number(spec, "rise", 0.012).max(SHORTEST_ATTACK) * (1.0 + AGE_SLOWER_RISE * age);
    let fall = number(spec, "fall", 0.25).max(SHORTEST_TIME) * (1.0 + AGE_LONGER_FALL * age);
    let unstable = 1.0 - number(spec, "stability", 1.0);
    let gated = word(spec, "drive", "strike") != "strike";
    let width = number(spec, "strike_width", 0.002);
    let full = if gated {
        1.0
    } else {
        1.0 - (-width / (rise * light.powf(-RISE_POWER))).exp()
    };
    EnvelopePart::Vactrol {
        rise,
        fall,
        gated,
        width,
        memory: (number(spec, "memory", 0.3) * (1.0 + AGE_MORE_MEMORY * age)).min(1.0),
        light,
        unstable: (
            FALL_SPREAD * unstable + AGE_SPREAD * age,
            RISE_SPREAD * unstable + AGE_RISE_SPREAD * age,
            LIGHT_SPREAD * unstable + AGE_SPREAD * age,
        ),
        drift: DRIFT * unstable,
        full,
    }
}

/// The SID chip's fall from a counter level to a floor, as (seconds, level) points, one straight segment for each division
/// of its exponential counter, each slower.
fn sid_fall(start: f64, floor: f64, step: f64) -> Vec<(f64, f64)> {
    let mut points = vec![(0.0, start)];
    let mut level = start;
    for (below, division) in SID_DIVISIONS {
        let lowest = below.max(floor);
        if level <= lowest {
            continue;
        }
        let time = points.last().map(|point| point.0).unwrap_or(0.0) + (level - lowest) * step * division;
        points.push((time, lowest));
        level = lowest;
        if level <= floor {
            break;
        }
    }
    points
}

/// A level read along (time, level) points, held at the last.
fn along(points: &[(f64, f64)], time: f64) -> f64 {
    if time <= points[0].0 {
        return points[0].1;
    }
    for pair in points.windows(2) {
        let (start, end) = (pair[0], pair[1]);
        if time <= end.0 {
            let span = (end.0 - start.0).max(1e-12);
            return start.1 + (end.1 - start.1) * (time - start.0) / span;
        }
    }
    points[points.len() - 1].1
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
                ..
            } => {
                let since = (seconds - memory.left_at).max(0.0);
                let hyperbola = (1.0 / FALL_TO - 1.0) / fall;
                state.start_level = keep * fallen(memory.left, since, hyperbola);
                let (mut rise, mut fall, mut light) = (*rise, *fall, *light);
                if unstable.0 > 0.0 || unstable.1 > 0.0 || unstable.2 > 0.0 {
                    let (first, second, third) = hit_normals(memory.hits);
                    let warmth = room_warmth(seconds);
                    fall *= (unstable.0 * first).exp() * (1.0 + drift * warmth);
                    rise *= (unstable.1 * second).exp() * (1.0 + 0.5 * drift * warmth);
                    light = (light * (unstable.2 * third).exp()).min(MOST_LIGHT_SPREAD);
                }
                memory.hits += 1;
                state.drive = (velocity * light).max(WEAKEST_DRIVE);
                state.rise = rise * state.drive.powf(-RISE_POWER);
                state.hyperbola = (1.0 / FALL_TO - 1.0) / fall;
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
                let accented = (velocity * 127.0).round() >= *threshold;
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
        match self {
            EnvelopePart::Adsr { .. } => self.adsr_level(state, note, short),
            EnvelopePart::SidAdsr { held, release_step } => sid_level(held, *release_step, state, note),
            EnvelopePart::Vactrol { gated, width, full, .. } => vactrol_level(state, note, *gated, *width, *full),
            EnvelopePart::AcidGate {
                accent,
                accent_decay,
                amp_decay,
                soft_attack,
                ..
            } => acid_level(state, note, *accent, *accent_decay, *amp_decay, *soft_attack),
            EnvelopePart::ChipSteps { start_level, pace, up } => chip_level(state, note, *start_level, *pace, *up),
            EnvelopePart::Off => 0.0,
        }
    }

    fn adsr_level(&self, state: &mut EnvelopeState, note: NoteTime, short: Option<f64>) -> f64 {
        let EnvelopePart::Adsr { release, struck, attack, .. } = self else {
            return 0.0;
        };
        if *struck {
            let level = self.held(note.age, short);
            if note.age > *attack && level < SILENT {
                state.done = true;
            }
            return level;
        }
        let Some(released) = note.released else { return self.held(note.age, short) };
        let from = *state.released_from.get_or_insert_with(|| self.held(released, short));
        let since = note.age - released;
        if since < 0.0 {
            return self.held(note.age, short);
        }
        let falling = from * (-since / release).exp();
        if falling < SILENT {
            state.done = true;
        }
        falling
    }

    /// The ADSR while its note is held: the attack, the hold at the top, then the decay to the sustain.
    fn held(&self, age: f64, short: Option<f64>) -> f64 {
        let EnvelopePart::Adsr {
            attack,
            hold,
            decay,
            sustain,
            snap,
            target,
            bend,
            ..
        } = self
        else {
            return 0.0;
        };
        if age < *attack {
            let x = (age / attack).min(1.0);
            return match (target, bend) {
                (Some(target), _) => target * (1.0 - ((target - 1.0) / target).powf(x)),
                (None, Some(bend)) => ((bend * x).exp() - 1.0) / (bend.exp() - 1.0),
                _ => x,
            };
        }
        let decay = short.map(|time| time / T60).unwrap_or(*decay);
        let gone = (age - attack - hold).max(0.0);
        let mut fall = (-gone / decay).exp();
        if *snap > 0.0 {
            fall = (1.0 - snap) * fall + snap * (-gone * (SNAP_SPEED / decay)).exp();
        }
        sustain + (1.0 - sustain) * fall
    }
}

fn sid_level(held: &[(f64, f64)], release_step: f64, state: &mut EnvelopeState, note: NoteTime) -> f64 {
    let mut counter = along(held, note.age);
    if let Some(released) = note.released {
        let from = *state.released_from.get_or_insert_with(|| along(held, released).floor());
        if note.age >= released {
            counter = along(&sid_fall(from, 0.0, release_step), note.age - released);
            if counter < 1.0 {
                state.done = true;
            }
        }
    }
    counter.floor() / SID_TOP
}

fn vactrol_level(state: &mut EnvelopeState, note: NoteTime, gated: bool, width: f64, full: f64) -> f64 {
    let lit = if gated { note.released.unwrap_or(f64::INFINITY) } else { width };
    let rising = |age: f64| state.drive + (state.start_level - state.drive) * (-age.min(lit) / state.rise).exp();
    let level = if note.age < lit {
        rising(note.age)
    } else {
        let peak = rising(lit);
        let out = fallen(peak, note.age - lit, state.hyperbola);
        if out < SILENT {
            state.done = true;
        }
        out
    };
    (level / full).min(MOST_LIGHT)
}

fn acid_level(state: &mut EnvelopeState, note: NoteTime, accent: f64, accent_decay: f64, amp_decay: f64, soft_attack: f64) -> f64 {
    let age = note.age;
    let mut level = if state.accented {
        let swell = 1.0 + ACCENT_LOUDER * accent * (-age * (T60 / accent_decay)).exp();
        (age / ACCENT_ATTACK).min(1.0) * (-age / amp_decay).exp() * swell
    } else {
        (age / soft_attack).min(1.0) * (-age / amp_decay).exp()
    };
    if let Some(released) = note.released {
        let since = age - released;
        level *= (1.0 - since / END_FADE).clamp(0.0, 1.0);
        if since >= END_FADE {
            state.done = true;
        }
    }
    level
}

fn chip_level(state: &mut EnvelopeState, note: NoteTime, start_level: f64, pace: f64, up: bool) -> f64 {
    let mut level = start_level;
    if pace > 0.0 {
        let moved = (note.age * CHIP_TICKS / pace).floor();
        level = if up { (level + moved).min(CHIP_LEVELS) } else { (level - moved).max(0.0) };
    }
    if level == 0.0 && (pace > 0.0 || start_level == 0.0) && !up {
        state.done = true;
    }
    let mut out = level / CHIP_LEVELS;
    if let Some(released) = note.released {
        let since = note.age - released;
        out *= (1.0 - since / CHIP_FADE).clamp(0.0, 1.0);
        if since >= CHIP_FADE {
            state.done = true;
        }
    }
    out
}

/// The cell's conductance a time after its light went off: the hyperbolic fall, and a slow leak under its tail.
fn fallen(level: f64, seconds: f64, hyperbola: f64) -> f64 {
    level / (1.0 + hyperbola * level * seconds) * (-seconds / LEAK_SECONDS).exp()
}

/// Three standard normals for a vactrol's hit by its number, the same every playing: splitmix64 through Box-Muller.
fn hit_normals(hit: u64) -> (f64, f64, f64) {
    let (first, second) = uniforms(hit * 2 + 1);
    let (third, fourth) = uniforms(hit * 2 + 2);
    let radius = (-2.0 * first.ln()).sqrt();
    let angle = 2.0 * std::f64::consts::PI * second;
    (
        radius * angle.cos(),
        radius * angle.sin(),
        (-2.0 * third.ln()).sqrt() * (2.0 * std::f64::consts::PI * fourth).cos(),
    )
}

fn uniforms(number: u64) -> (f64, f64) {
    let mix = |step: u64| {
        let mut value = step.wrapping_mul(0x9E37_79B9_7F4A_7C15);
        value = (value ^ (value >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        value ^= value >> 31;
        (value as f64 + 1.0) / (u64::MAX as f64 + 2.0)
    };
    (mix(number), mix(number.wrapping_add(0x9E37_79B9_7F4A_7C15)))
}

/// The room's warmth from -1 to 1 at a time: slow, smooth and the same every playing.
fn room_warmth(seconds: f64) -> f64 {
    WARMTH
        .iter()
        .map(|(period, weight, phase)| weight * (2.0 * std::f64::consts::PI * seconds / period + phase).sin())
        .sum()
}

#[cfg(test)]
mod tests {

    /// An envelope set to Off holds at nothing while its note sounds and after it ends, so that Env2 sweeps no filter and
    /// Env3 bends no pitch.
    #[test]
    fn an_envelope_set_off_holds_at_nothing() {
        let spec = Value::Map(vec![(Value::from("type"), Value::from(OFF))]);
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

    fn spec(pairs: &[(&str, Value)]) -> Value {
        Value::Map(pairs.iter().map(|(key, value)| (Value::from(*key), value.clone())).collect())
    }

    fn play(part: &EnvelopePart, released: Option<f64>, seconds: f64) -> (Vec<f64>, bool) {
        let mut state = EnvelopeState::default();
        let levels: Vec<f64> = (0..(seconds * 1000.0) as usize)
            .map(|ms| {
                part.level(
                    &mut state,
                    NoteTime {
                        age: ms as f64 / 1000.0,
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
        let part = compiled(
            &spec(&[
                ("type", "adsr".into()),
                ("attack", 0.01.into()),
                ("decay", 0.2.into()),
                ("sustain", 0.5.into()),
                ("release", 0.1.into()),
            ]),
            0.0,
        );
        let (levels, done) = play(&part, Some(0.5), 1.0);
        assert!((levels[10] - 1.0).abs() < 0.05);
        assert!((levels[499] - 0.5).abs() < 0.01);
        assert!(done);
    }

    #[test]
    fn the_sid_adsr_holds_its_sixteen_level_sustain() {
        let part = compiled(
            &spec(&[
                ("type", "sid_adsr".into()),
                ("attack", 0.into()),
                ("decay", 9.into()),
                ("sustain", 8.into()),
                ("release", 9.into()),
            ]),
            0.0,
        );
        let (levels, done) = play(&part, Some(0.5), 3.0);
        assert!((levels[499] * SID_TOP - 8.0 * SID_SUSTAIN_STEP).abs() <= 1.0);
        assert!(done);
    }

    #[test]
    fn a_full_strike_on_a_vactrol_peaks_near_full_and_falls() {
        let part = compiled(
            &spec(&[
                ("type", "vactrol".into()),
                ("rise", 0.012.into()),
                ("fall", 0.25.into()),
                ("strike_width", 0.002.into()),
                ("memory", 0.0.into()),
            ]),
            0.0,
        );
        let mut memory = EnvelopeMemory::default();
        let (mut state, _, _) = part.start(&mut memory, 1.0, 0.0);
        let peak = (0..50)
            .map(|step| {
                part.level(
                    &mut state,
                    NoteTime {
                        age: step as f64 / 10000.0,
                        released: None,
                    },
                    None,
                )
            })
            .fold(0.0_f64, f64::max);
        assert!((peak - 1.0).abs() < 0.05);
    }
}
