// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A built-in instrument's sound as the backend compiles it (the Python built_in_sound.py's SoundSpec): read a part at a
//! time from the sound as it is stored, its engine's preset and its types' defaults filling what it leaves out, its times
//! in seconds and its shares as fractions.

use crate::generated::sounds::{Preset, EFFECT_DEFAULTS, SLOT_DEFAULTS};
use crate::instrument_sound::Sound;
use llamatron_model::file::data::Data;
use llamatron_model::objects::lfo_speed;
use llamatron_model::schema::generated::file_format::MatrixSetting;
use llamatron_model::schema::generated::limits::LFO_COUNT;
use llamatron_names::file_format;
use llamatron_names::spec;
use llamatron_names::words;
use llamatron_strings::marks;

const MILLISECONDS: f64 = 1000.0;
const TENTHS_OF_MILLISECONDS: f64 = 10000.0;
const PERCENT: f64 = 100.0;
/// How many decibels a filter's pole falls by, and the poles a filter has unless its slope says.
const DB_A_POLE: i64 = 6;
const FOUR_POLES: i64 = 4;
/// The pulse shares of the chip's duty cycles, and the rise and fall in seconds of each vactrol cell.
const DUTY_SHARES: [(&str, f64); 4] = [("eighth", 0.125), ("quarter", 0.25), ("half", 0.5), ("three_quarters", 0.75)];
const ENVELOPE_PARTS: [&str; 3] = ["env1", "env2", "env3"];
const OSCILLATORS: &str = spec::OSCILLATORS;
const AMP: &str = spec::AMP;
/// The low-pass gate's type in the backend's spec, and its type on the Amp tab.
const LOW_PASS_GATE: &str = spec::LOW_PASS_GATE;
const AMP_GATE: &str = words::LOW_PASS_GATE_AMP;
const FILTER: &str = spec::FILTER;
const UP: &str = file_format::ChipDirection::UP;

/// The sound as the backend compiles it; a drum plays at its own pitch on drums_from, the set's drum tuning note.
pub fn synth_spec(sound: &Sound, drums_from: i64) -> Data {
    let value = |name: &str| sound.value(name);
    let oscillators = oscillators(sound);
    let mut spec = vec![
        (spec::KIND, value(spec::ENGINE)),
        (spec::VOLUME, share(&value(spec::VOLUME), PERCENT)),
        (spec::VOICES, value(spec::VOICES)),
        (spec::GLIDES, Data::Bool(!matches!(value(spec::GLIDES), Data::Bool(false)))),
        (spec::GLIDE, glide(sound)),
        (spec::FILTER_PER_NOTE, Data::Bool(value(spec::FILTER_SHARING).as_str() == Some(spec::PER_NOTE))),
        (spec::DISCONNECT_FILTER, Data::Bool(matches!(value(spec::DISCONNECT_FILTER), Data::Bool(true)))),
        (spec::OSCILLATORS, oscillators.clone()),
        (spec::ENVELOPES, Data::List(ENVELOPE_PARTS.iter().map(|part| envelope(sound, part)).collect())),
        (spec::FILTER, filter(sound)),
        (spec::AMP, amp(sound)),
        (spec::LFOS, lfos(sound)),
        (spec::EFFECTS, effects(sound)),
        (spec::MATRIX, matrix(sound)),
    ];
    if oscillators.get(spec::TYPE).and_then(Data::as_str) == Some(spec::DRUM) {
        spec.push((spec::TUNED_FROM, Data::Whole(drums_from as i128)));
    }
    mapping(spec)
}

/// The oscillators part, as the backend's oscillators read it.
fn oscillators(sound: &Sound) -> Data {
    let kind = sound.part_type(OSCILLATORS);
    let setting = |name: &str| sound.part_value(OSCILLATORS, name);
    if kind == spec::DRUM {
        let choke = setting(spec::CHOKE);
        let choke = if is_falsy(&choke) { Data::Null } else { choke };
        return mapping(vec![
            (spec::TYPE, Data::text(&kind)),
            (spec::MACHINE, setting(spec::MACHINE)),
            (spec::KNOBS, setting(spec::KNOBS)),
            (spec::CHOKE, choke),
            (spec::OVERLAP, setting(spec::OVERLAP)),
        ]);
    }
    let mut spec = vec![(spec::TYPE, Data::text(&kind))];
    // An engine of one oscillator carries its Detune and Fine as one tuning in cents; Basic and Asheville tune each
    // oscillator of their own.
    if ONE_OSCILLATOR_TYPES.contains(&kind.as_str()) {
        spec.push((spec::CENTS, Data::Float(cents_with_fine(&setting(spec::DETUNE), &setting(spec::FINE)))));
    }
    match kind.as_str() {
        spec::SID => spec.extend([
            (spec::WAVE, setting(spec::WAVE)),
            (spec::PULSE_WIDTH, share(&setting(spec::PULSE_WIDTH), PERCENT)),
            (spec::RING, setting(spec::RING_ON)),
            (spec::SYNC, setting(spec::SYNC_ON)),
            (spec::INTERVAL, setting(spec::INTERVAL)),
            (spec::ARPEGGIO, setting(spec::ARPEGGIO)),
        ]),
        spec::POCKET => {
            let duty = setting(spec::DUTY);
            let duty = DUTY_SHARES.iter().find(|(name, _)| duty.as_str() == Some(name)).map_or(0.5, |(_, part)| *part);
            spec.extend([
                (spec::CHIP_VOICE, setting(spec::CHIP_VOICE)),
                (spec::DUTY, Data::Float(duty)),
                (spec::WAVE_SHAPE, setting(spec::WAVE_SHAPE)),
                (spec::NOISE, setting(spec::NOISE)),
                (spec::SWEEP_PACE, setting(spec::SWEEP_PACE)),
                (spec::SWEEP_UP, Data::Bool(setting(spec::SWEEP_DIRECTION).as_str() == Some(UP))),
                (spec::SWEEP_STEP, setting(spec::SWEEP_STEP)),
            ]);
        }
        spec::ACID => spec.extend([(spec::ACID_WAVE, setting(spec::ACID_WAVE)), (spec::TUNING, setting(spec::TUNING))]),
        spec::ASHEVILLE => spec.extend(asheville(sound)),
        _ => spec.push((spec::OSCILLATORS, basic_oscillators(sound))),
    }
    mapping(spec)
}

/// Each footage's distance from the note in half steps: 8' plays the note, each halving of the pipe an octave up, and
/// LO, Osc 3's range for an LFO, four octaves under.
const FOOTAGES: &[(&str, i128)] = &[("lo", -48), ("32", -24), ("16", -12), ("8", 0), ("4", 12), ("2", 24)];
/// An Asheville oscillator's Speed that plays the note at its Range, rather than an LFO's rate.
const AUDIO_SPEED: &str = words::AUDIO;
/// A knob of the panel's 0 to 10, as the fraction the backend reads.
const PANEL_TOP: f64 = 10.0;

/// Asheville's panel as the backend reads it: each oscillator's footage in half steps, wave, shape, cents, mix and sub,
/// and the panel's Model, Character, Noise, Ring, Snap, Drift and Feedback, the knobs as fractions.
fn asheville(sound: &Sound) -> Vec<(&'static str, Data)> {
    let setting = |name: &str| sound.part_value(OSCILLATORS, name);
    let panel = |name: &str| Data::Float(setting(name).as_whole().unwrap_or(0) as f64 / PANEL_TOP);
    let oscillators = (1..=3)
        .map(|number| {
            let own = |name: &str| setting(&format!("osc{number}_{name}"));
            let range = own(spec::RANGE);
            let half_steps = FOOTAGES.iter().find(|(name, _)| range.as_str() == Some(name)).map_or(0, |(_, steps)| *steps);
            let sub = own(spec::SUB).as_str().and_then(|octaves| octaves.parse::<i128>().ok()).unwrap_or(0);
            // At an LFO's Speed the oscillator runs at its Rate's hertz whatever the note.
            let speed = own(spec::SPEED).as_str().unwrap_or(AUDIO_SPEED).to_string();
            let hertz = if speed == AUDIO_SPEED {
                Data::Null
            } else {
                Data::Float(lfo_speed::hertz(&speed, own(spec::RATE).as_whole().unwrap_or(0) as f64))
            };
            mapping(vec![
                (spec::HERTZ, hertz),
                (spec::RANGE, Data::Whole(half_steps)),
                (spec::WAVE, own(spec::WAVE)),
                (spec::SHAPE, share(&own(spec::SHAPE), PERCENT)),
                (spec::CENTS, Data::Float(cents_with_fine(&own(spec::TUNE), &own(spec::FINE)))),
                (spec::MIX, Data::Float(own(spec::MIX).as_whole().unwrap_or(0) as f64 / PANEL_TOP)),
                (spec::SUB, Data::Whole(sub)),
                (spec::ON, own(spec::ON)),
            ])
        })
        .collect();
    let feedback = if setting(spec::FEEDBACK_ON) == Data::Bool(true) {
        panel(spec::FEEDBACK)
    } else {
        Data::Float(0.0)
    };
    vec![
        (spec::OSCILLATORS, Data::List(oscillators)),
        (spec::MODEL, setting(spec::MODEL)),
        (spec::CHARACTER, setting(spec::CHARACTER)),
        (spec::NOISE, panel(spec::NOISE_LEVEL)),
        (spec::RING, panel(spec::RING)),
        (spec::SNAP, setting(spec::TUNE_SNAP)),
        (spec::DRIFT, panel(spec::DRIFT)),
        (spec::FEEDBACK, feedback),
    ]
}

/// Basic's oscillators that sound, each its waveform, its detune in cents and its level as a fraction, those off left out.
/// The oscillator types of one oscillator, whose Detune and Fine are the part's own settings.
const ONE_OSCILLATOR_TYPES: [&str; 3] = ["sid", "pocket", "acid"];

/// A tuning in cents and its Fine in tenths of a cent, together as cents.
fn cents_with_fine(cents: &Data, fine: &Data) -> f64 {
    let tenths_a_cent = 10.0;
    cents.as_whole().unwrap_or(0) as f64 + fine.as_whole().unwrap_or(0) as f64 / tenths_a_cent
}

/// How many oscillators Basic plays.
const BASIC_OSCILLATORS: usize = 1;

fn basic_oscillators(sound: &Sound) -> Data {
    // Basic plays its first oscillator alone; a set from before it had one keeps only that.
    let count = sound
        .part_value(OSCILLATORS, OSCILLATORS)
        .as_list()
        .map_or(0, <[Data]>::len)
        .min(BASIC_OSCILLATORS);
    let mut sounding = Vec::new();
    for number in 1..=count {
        let waveform = sound.oscillator(number, spec::WAVEFORM);
        if waveform.as_str() == Some(spec::OFF) {
            continue;
        }
        let level = share(&sound.oscillator(number, spec::LEVEL), PERCENT);
        let cents = cents_with_fine(&sound.oscillator(number, spec::DETUNE), &sound.oscillator(number, spec::FINE));
        sounding.push(Data::List(vec![waveform, Data::Float(cents), level]));
    }
    Data::List(sounding)
}

/// A part's Circuit, and its modded choice, which shows the classic modifications' settings.
const CIRCUIT: &str = words::CIRCUIT;
const MODDED: &str = words::MODDED;

/// A setting's default for a type of part, as a new part of that type holds it.
fn default_of(kind: &str, name: &str) -> Data {
    crate::generated::sounds::TYPE_DEFAULTS
        .iter()
        .find(|(found, _)| *found == kind)
        .map(|(_, preset)| preset.to_data())
        .and_then(|defaults| defaults.get(name).cloned())
        .unwrap_or(Data::Null)
}

/// The voice's Glide time, in seconds, the Voice column's on every engine, Oh3's included.
fn glide(sound: &Sound) -> Data {
    share(&sound.value(spec::GLIDE), MILLISECONDS)
}

/// The envelope type that is no envelope, as the backend names it.
const NO_ENVELOPE: &str = spec::NONE;

/// An envelope part, as the backend's envelopes read it.
fn envelope(sound: &Sound, part: &str) -> Data {
    let kind = sound.part_type(part);
    let setting = |name: &str| sound.part_value(part, name);
    let typed = ("type", Data::text(&kind));
    match kind.as_str() {
        // Off, which only Env2 and Env3 may be, has no settings: the backend holds it at nothing.
        NO_ENVELOPE => mapping(vec![typed]),
        spec::SID_ADSR => mapping(vec![
            typed,
            (spec::ATTACK, setting(spec::ATTACK)),
            (spec::DECAY, setting(spec::DECAY)),
            (spec::SUSTAIN, setting(spec::SUSTAIN)),
            (spec::RELEASE, setting(spec::RELEASE)),
        ]),
        spec::VACTROL => {
            // The backend's vactrol is struck by a flash, or lit while the key is held.
            let drive = if setting(spec::TRIGGER).as_str() == Some(spec::GATE) {
                spec::GATE
            } else {
                spec::STRIKE
            };
            mapping(vec![
                typed,
                (spec::RESPONSE, share(&setting(spec::RESPONSE), PERCENT)),
                (spec::DRIVE, Data::text(drive)),
                (spec::STRIKE_WIDTH, share(&setting(spec::TRIGGER_TIME), TENTHS_OF_MILLISECONDS)),
                (spec::MEMORY, share(&setting(spec::MEMORY), PERCENT)),
                (spec::AGE, share(&setting(spec::AGE), PERCENT)),
                (spec::STABILITY, share(&setting(spec::STABILITY), PERCENT)),
            ])
        }
        spec::ACID_GATE => {
            // On Stock the modded settings play the circuit's own values, the type's defaults, whatever is written.
            let modded = setting(CIRCUIT).as_str() == Some(MODDED);
            let chosen = |name: &str| if modded { setting(name) } else { default_of(spec::ACID_GATE, name) };
            mapping(vec![
                typed,
                (spec::ACCENT, share(&setting(spec::ACCENT), PERCENT)),
                (spec::ACCENT_THRESHOLD, setting(spec::ACCENT_THRESHOLD)),
                (spec::ACCENT_SWEEP, share(&chosen(spec::ACCENT_SWEEP), PERCENT)),
                (spec::ACCENT_DECAY, share(&chosen(spec::ACCENT_DECAY), MILLISECONDS)),
                (spec::AMP_DECAY, share(&chosen(spec::AMP_DECAY), MILLISECONDS)),
                (spec::SOFT_ATTACK, share(&chosen(spec::SOFT_ATTACK), TENTHS_OF_MILLISECONDS)),
            ])
        }
        spec::CHIP_STEPS => mapping(vec![
            typed,
            (spec::START_LEVEL, setting(spec::START_LEVEL)),
            (spec::LEVEL_PACE, setting(spec::LEVEL_PACE)),
            (spec::LEVEL_UP, Data::Bool(setting(spec::LEVEL_DIRECTION).as_str() == Some(UP))),
        ]),
        _ => {
            // The snappy ADSR, AR or ASR: an AR or ASR has neither hold nor decay, and falls at its release.
            let release = share(&setting(spec::RELEASE), MILLISECONDS);
            let full = kind == spec::ADSR;
            let or_none = |name: &str, scale: f64, otherwise: Data| if full { share(&setting(name), scale) } else { otherwise };
            mapping(vec![
                typed,
                (spec::ATTACK, share(&setting(spec::ATTACK), MILLISECONDS)),
                (spec::ATTACK_CURVE, setting(spec::ATTACK_CURVE)),
                (spec::RELEASE, release.clone()),
                (spec::HOLD, or_none(spec::HOLD, MILLISECONDS, Data::Float(0.0))),
                (spec::DECAY, or_none(spec::DECAY, MILLISECONDS, release)),
                (spec::SNAP, or_none(spec::SNAP, PERCENT, Data::Float(0.0))),
                (spec::SUSTAIN, or_none(spec::SUSTAIN, PERCENT, Data::Float(0.0))),
            ])
        }
    }
}

/// The filter part, as the backend's filters and gates read it, or none.
/// The Amp as the backend reads it: its type, and its Response, Drive, Bleed and Character as fractions; or a low-pass
/// gate standing in its place.
fn amp(sound: &Sound) -> Data {
    if sound.part_type(AMP) == AMP_GATE {
        return gate(sound, AMP);
    }
    let setting = |name: &str| sound.part_value(AMP, name);
    mapping(vec![
        (spec::TYPE, Data::text(&sound.part_type(AMP))),
        (spec::RESPONSE, share(&setting(spec::RESPONSE), PERCENT)),
        (spec::DRIVE, share(&setting(spec::DRIVE), PERCENT)),
        (spec::BLEED, share(&setting(spec::BLEED), PERCENT)),
        (spec::CHARACTER, share(&setting(spec::AMP_CHARACTER), PERCENT)),
    ])
}

/// A low-pass gate in either place as the backend reads it: what lights it and for how long a flash, its mode, the
/// signal it is fed and its ping, its filter, and its cell, the times in seconds and the rest as fractions.
fn gate(sound: &Sound, part: &str) -> Data {
    let setting = |name: &str| sound.part_value(part, name);
    mapping(vec![
        (spec::TYPE, Data::text(LOW_PASS_GATE)),
        (spec::TRIGGER, setting(spec::TRIGGER)),
        (spec::TRIGGER_TIME, share(&setting(spec::TRIGGER_TIME), TENTHS_OF_MILLISECONDS)),
        (spec::MODE, setting(spec::GATE_MODE)),
        (spec::SIGNAL, setting(spec::SIGNAL)),
        (spec::PING_TIME, share(&setting(spec::PING_TIME), TENTHS_OF_MILLISECONDS)),
        (spec::RESONANCE, share(&setting(spec::RESONANCE), PERCENT)),
        (spec::OPEN, setting(spec::OPEN)),
        (spec::KEY_TRACK, share(&setting(spec::KEY_TRACK), PERCENT)),
        (spec::RESPONSE, share(&setting(spec::RESPONSE), PERCENT)),
        (spec::MEMORY, share(&setting(spec::MEMORY), PERCENT)),
        (spec::AGE, share(&setting(spec::AGE), PERCENT)),
        (spec::STABILITY, share(&setting(spec::STABILITY), PERCENT)),
    ])
}

fn filter(sound: &Sound) -> Data {
    let kind = sound.part_type(FILTER);
    let setting = |name: &str| sound.part_value(FILTER, name);
    let typed = ("type", Data::text(&kind));
    match kind.as_str() {
        spec::NONE => mapping(vec![typed]),
        spec::LOW_PASS_GATE => gate(sound, FILTER),
        _ => {
            let mode = if kind == spec::MULTIMODE || kind == spec::SALLEN_KEY {
                setting(spec::MODE)
            } else {
                Data::text(spec::LOW)
            };
            let poles = if kind == spec::LADDER {
                Data::Whole((whole(&setting(spec::SLOPE)).div_euclid(DB_A_POLE)) as i128)
            } else {
                Data::Whole(FOUR_POLES as i128)
            };
            mapping(vec![
                typed,
                (spec::MODE, mode),
                (spec::POLES, poles),
                (spec::CUTOFF, setting(spec::CUTOFF)),
                (spec::RESONANCE, share(&setting(spec::RESONANCE), PERCENT)),
                (spec::ENV_AMOUNT, share(&setting(spec::ENV_AMOUNT), PERCENT)),
                (spec::KEY_TRACK, share(&setting(spec::KEY_TRACK), PERCENT)),
                (spec::DRIVE, share(&setting(spec::DRIVE), PERCENT)),
                // Only the Ladder gives back the bass its Resonance thins; the others keep their own response.
                (
                    spec::BASS_COMPENSATION,
                    if kind == spec::LADDER {
                        share(&setting(spec::BASS_COMPENSATION), PERCENT)
                    } else {
                        Data::Float(0.0)
                    },
                ),
                // The Diode's Filter FM, the oscillator moving the cutoff for growl, is a modification: none on Stock.
                (
                    spec::FILTER_FM,
                    if kind == spec::DIODE && setting(CIRCUIT).as_str() == Some(MODDED) {
                        share(&setting(spec::FILTER_FM), PERCENT)
                    } else {
                        Data::Float(0.0)
                    },
                ),
            ])
        }
    }
}

/// How a Mod Matrix source names a Modulators slot, followed by its number and, for one of a Snail's outputs, the
/// output's name.
const LFO_SOURCE_PREFIX: &str = spec::LFO;
/// A slot's Type that holds a Snail.
const SNAIL_TYPE: &str = spec::SNAIL;
/// A Snail's lane's speed: its setting, held as a whole number of its unit, the seconds a unit lasts, its lowest,
/// highest and default in its units, and how its value is shown.
pub struct LaneSpeed {
    pub name: &'static str,
    pub seconds_a_unit: f64,
    pub lowest: i64,
    pub highest: i64,
    pub default: i64,
    pub shown: &'static str,
    pub divisor: i64,
}

/// Slow's speed in seconds, 5 to 60; Slower's in tenths of a minute, 1 to 10 minutes; Slowest's in minutes, 10 to 60:
/// about how long a trip of the lane's from one side to the other takes.
pub const SNAIL_LANES: [LaneSpeed; 3] = [
    LaneSpeed {
        name: spec::SLOW_SPEED,
        seconds_a_unit: 1.0,
        lowest: 5,
        highest: 60,
        default: 30,
        shown: marks::MSG_SECONDS_SHOWN,
        divisor: 1,
    },
    LaneSpeed {
        name: spec::SLOWER_SPEED,
        seconds_a_unit: 6.0,
        lowest: 10,
        highest: 100,
        default: 50,
        shown: marks::MSG_TENTH_MINUTES_SHOWN,
        divisor: 10,
    },
    LaneSpeed {
        name: spec::SLOWEST_SPEED,
        seconds_a_unit: 60.0,
        lowest: 10,
        highest: 60,
        default: 30,
        shown: marks::MSG_MINUTES_SHOWN,
        divisor: 1,
    },
];

/// The LFOs in their places, every slot of the four, None for one that is off or that no Mod Matrix route reads, so that
/// the matrix finds each by its number and the engine works out only the LFOs something hears.
fn lfos(sound: &Sound) -> Data {
    let read = lfos_read(sound);
    let mut lfos = Vec::new();
    for number in 1..=LFO_COUNT as usize {
        // Each setting as the slot's Type plays it: an LFO leaves an LFO+'s own settings out (Sound::lfo_setting).
        let setting = |name: &str| sound.lfo_setting(number, name);
        if is_falsy(&setting(spec::ON)) || !read.contains(&number) {
            lfos.push(Data::Null);
            continue;
        }
        // A Snail has its two weightings, each a fraction either way, and each lane's speed, the seconds its switch
        // chooses.
        if setting(spec::TYPE).as_str() == Some(SNAIL_TYPE) {
            let seconds = SNAIL_LANES.iter().map(|lane| {
                let held = setting(lane.name).as_whole().map_or(lane.default, |held| held as i64);
                Data::Float(held as f64 * lane.seconds_a_unit)
            });
            lfos.push(mapping(vec![
                (spec::TYPE, Data::text(SNAIL_TYPE)),
                (spec::SLOW, share(&setting(spec::SLOW), PERCENT)),
                (spec::SLOWER, share(&setting(spec::SLOWER), PERCENT)),
                (spec::SECONDS, Data::List(seconds.collect())),
            ]));
            continue;
        }
        let speed = setting(spec::SPEED).as_str().unwrap_or(lfo_speed::DEFAULT_SPEED).to_string();
        let percent = setting(spec::RATE_PERCENT).as_whole().unwrap_or(0) as f64;
        let mut lfo = vec![
            (spec::SHAPE, setting(spec::SHAPE)),
            (spec::RATE, Data::Float(lfo_speed::hertz(&speed, percent))),
            (spec::RESTART, setting(spec::RESTART)),
            (spec::FADE_IN, share(&setting(spec::FADE_IN), MILLISECONDS)),
        ];
        // A synced LFO's cycle is a length of the beat, which the backend times by the song's tempo.
        if setting(spec::SYNC) == Data::Bool(true) {
            let division = setting(spec::DIVISION).as_str().unwrap_or(lfo_speed::DEFAULT_DIVISION).to_string();
            lfo.push((spec::QUARTERS, Data::Float(lfo_speed::quarters_of(&division))));
        }
        // At audio rate an LFO may follow the key, running at its ratio times each note's frequency.
        if speed == lfo_speed::AUDIO_SPEED && setting(spec::KEY) == Data::Bool(true) {
            let ratio = setting(spec::RATIO).as_str().map(lfo_speed::ratio_multiple).unwrap_or(1.0);
            lfo.push((spec::KEY_RATIO, Data::Float(ratio)));
        }
        lfos.push(mapping(lfo));
    }
    Data::List(lfos)
}

/// The effects in order, every setting given, shares as fractions, the empty ones left out.
fn effects(sound: &Sound) -> Data {
    let count = sound.value(spec::EFFECTS).as_list().map_or(0, <[Data]>::len);
    let mut effects = Vec::new();
    for number in 1..=count {
        let names: Vec<&str> = match EFFECT_DEFAULTS {
            Preset::Map(pairs) => pairs.iter().map(|(name, _)| *name).collect(),
            _ => Vec::new(),
        };
        let mut effect = mapping(names.iter().map(|name| (*name, sound.effect_setting(number, name))).collect());
        if effect.get(spec::EFFECT).and_then(Data::as_str) == Some(spec::NONE) {
            continue;
        }
        if effect.get(spec::EFFECT).and_then(Data::as_str) == Some(MULTITAP) {
            put(&mut effect, spec::TAPS, taps(sound, number));
            let feedback = share(&sound.effect_setting(number, spec::FEEDBACK), PERCENT);
            set(&mut effect, spec::FEEDBACK, feedback);
            let from = sound.effect_setting(number, spec::FEEDBACK_FROM);
            let tap = from.as_str().and_then(|tap| tap.parse::<i128>().ok()).unwrap_or(4);
            set(&mut effect, spec::FEEDBACK_FROM, Data::Whole(tap));
        }
        for name in [spec::AMOUNT, spec::MIX, spec::DARKNESS, spec::NOISE, spec::DRIVE, spec::WOW, spec::FLUTTER] {
            let scaled = effect.get(name).map(|value| share(value, PERCENT)).unwrap_or(Data::Float(0.0));
            set(&mut effect, name, scaled);
        }
        effects.push(effect);
    }
    Data::List(effects)
}

/// MultiTap's effect name, and each division of the beat a synced tap may take with the quarter notes it lasts.
const MULTITAP: &str = spec::MULTITAP;
const THIRD: f64 = 1.0 / 3.0;
pub const DELAY_DIVISIONS: [(&str, f64); 13] = [
    ("1/32", 0.125),
    ("1/16t", 0.25 * 2.0 * THIRD),
    ("1/16", 0.25),
    ("1/16d", 0.375),
    ("1/8t", THIRD),
    ("1/8", 0.5),
    ("1/8d", 0.75),
    ("1/4t", 2.0 * THIRD),
    ("1/4", 1.0),
    ("1/4d", 1.5),
    ("1/2", 2.0),
    ("1/2d", 3.0),
    ("1/1", 4.0),
];

/// A MultiTap's four taps as the backend reads them: each a share of a quarter note while Sync is on, else seconds, and
/// its level as a fraction, and whether it sounds.
fn taps(sound: &Sound, number: usize) -> Data {
    let synced = !matches!(sound.effect_setting(number, spec::SYNC), Data::Bool(false));
    let taps = (1..=4)
        .map(|tap| {
            let setting = |name: &str| sound.effect_setting(number, &format!("tap{tap}_{name}"));
            let time = if synced {
                let division = setting(spec::DIVISION);
                let quarters = DELAY_DIVISIONS
                    .iter()
                    .find(|(name, _)| division.as_str() == Some(name))
                    .map_or(1.0, |(_, quarters)| *quarters);
                (spec::QUARTERS, Data::Float(quarters))
            } else {
                (spec::SECONDS, share(&setting(spec::MS), MILLISECONDS))
            };
            let on = Data::Bool(!matches!(setting(spec::ON), Data::Bool(false)));
            mapping(vec![time, (spec::LEVEL, share(&setting(spec::LEVEL), PERCENT)), (spec::ON, on)])
        })
        .collect();
    Data::List(taps)
}

/// The Modulators slots a Mod Matrix route reads, by number, as its source or its via.
fn lfos_read(sound: &Sound) -> Vec<usize> {
    let count = sound.value(spec::MATRIX).as_list().map_or(0, <[Data]>::len);
    let mut read = Vec::new();
    for slot in 1..=count {
        let settings = every_setting(sound, spec::MATRIX, slot, SLOT_DEFAULTS);
        for end in [MatrixSetting::SOURCE, MatrixSetting::VIA] {
            let number = settings
                .get(end)
                .and_then(Data::as_str)
                .and_then(|name| name.strip_prefix(LFO_SOURCE_PREFIX))
                .and_then(|rest| rest.split('_').next())
                .and_then(|number| number.parse::<usize>().ok());
            if let Some(number) = number {
                read.push(number);
            }
        }
    }
    read
}

/// The matrix's slots, each amount a fraction either way.
fn matrix(sound: &Sound) -> Data {
    let count = sound.value(spec::MATRIX).as_list().map_or(0, <[Data]>::len);
    let mut slots = Vec::new();
    for number in 1..=count {
        let mut slot = every_setting(sound, spec::MATRIX, number, SLOT_DEFAULTS);
        let scaled = slot.get(spec::AMOUNT).map(|value| share(value, PERCENT)).unwrap_or(Data::Float(0.0));
        set(&mut slot, spec::AMOUNT, scaled);
        slots.push(slot);
    }
    Data::List(slots)
}

/// Every setting of an item of one of the sound's lists, its defaults' names in their order.
fn every_setting(sound: &Sound, list: &str, number: usize, defaults: Preset) -> Data {
    let names: Vec<&str> = match defaults {
        Preset::Map(pairs) => pairs.iter().map(|(name, _)| *name).collect(),
        _ => Vec::new(),
    };
    mapping(names.iter().map(|name| (*name, sound.item(list, number, name, defaults))).collect())
}

/// A mapping of names to values, in order.
fn mapping(pairs: Vec<(&str, Data)>) -> Data {
    Data::Map(pairs.into_iter().map(|(name, value)| (Data::text(name), value)).collect())
}

/// Put a value under a name in a mapping, replacing what it held.
fn set(map: &mut Data, name: &str, value: Data) {
    if let Data::Map(pairs) = map {
        if let Some(pair) = pairs.iter_mut().find(|(key, _)| key.as_str() == Some(name)) {
            pair.1 = value;
        }
    }
}

/// Put a value under a name in a mapping, adding the name where the mapping does not hold it yet.
fn put(map: &mut Data, name: &str, value: Data) {
    if let Data::Map(pairs) = map {
        match pairs.iter_mut().find(|(key, _)| key.as_str() == Some(name)) {
            Some(pair) => pair.1 = value,
            None => pairs.push((Data::text(name), value)),
        }
    }
}

/// A number as a fraction of a whole, such as a percentage of 100, always a float as the backend reads one.
fn share(value: &Data, whole: f64) -> Data {
    Data::Float(number(value) / whole)
}

/// A number, whole or not, as a float.
fn number(value: &Data) -> f64 {
    match value {
        Data::Whole(whole) => *whole as f64,
        Data::Float(float) => *float,
        _ => 0.0,
    }
}

/// A whole number, 0 for anything else.
fn whole(value: &Data) -> i64 {
    // A choice of numbers, such as the ladder's slope, is stored as its text when picked on the page.
    value
        .as_whole()
        .map(|whole| whole as i64)
        .or_else(|| value.as_str().and_then(|text| text.trim().parse::<i64>().ok()))
        .unwrap_or(0)
}

/// Whether a value counts as nothing, as Python's truth does: none, false, zero or empty.
fn is_falsy(value: &Data) -> bool {
    match value {
        Data::Null | Data::Bool(false) => true,
        Data::Bool(true) => false,
        Data::Whole(whole) => *whole == 0,
        Data::Float(float) => *float == 0.0,
        Data::Text(text) => text.is_empty(),
        Data::List(items) => items.is_empty(),
        Data::Map(pairs) => pairs.is_empty(),
    }
}
