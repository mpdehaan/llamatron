// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A built-in instrument's sound as the backend compiles it (the Python built_in_sound.py's SoundSpec): read a part at a
//! time from the sound as it is stored, its engine's preset and its types' defaults filling what it leaves out, its times
//! in seconds and its shares as fractions.

use crate::generated::sounds::{Preset, EFFECT_DEFAULTS, LFO_DEFAULTS, SLOT_DEFAULTS};
use crate::instrument_sound::Sound;
use llamatron_model::file::data::Data;
use llamatron_model::objects::lfo_speed;

const MILLISECONDS: f64 = 1000.0;
const TENTHS_OF_MILLISECONDS: f64 = 10000.0;
const PERCENT: f64 = 100.0;
/// How many decibels a filter's pole falls by, and the poles a filter has unless its slope says.
const DB_A_POLE: i64 = 6;
const FOUR_POLES: i64 = 4;
/// The pulse shares of the chip's duty cycles, and the rise and fall in seconds of each vactrol cell.
const DUTY_SHARES: [(&str, f64); 4] = [("eighth", 0.125), ("quarter", 0.25), ("half", 0.5), ("three_quarters", 0.75)];
const CELLS: [(&str, f64, f64); 4] = [("fast", 0.0025, 0.035), ("classic", 0.005, 0.08), ("slow", 0.012, 0.25), ("lazy", 0.02, 0.6)];
const ENVELOPE_PARTS: [&str; 3] = ["env1", "env2", "env3"];
const OSCILLATORS: &str = "oscillators";
const FILTER: &str = "filter";
const UP: &str = "up";

/// The sound as the backend compiles it; a drum plays at its own pitch on drums_from, the set's drum tuning note.
pub fn synth_spec(sound: &Sound, drums_from: i64) -> Data {
    let value = |name: &str| sound.value(name);
    let oscillators = oscillators(sound);
    let mut spec = vec![
        ("kind", value("engine")),
        ("volume", share(&value("volume"), PERCENT)),
        ("voices", value("voices")),
        ("glides", Data::Bool(!matches!(value("glides"), Data::Bool(false)))),
        ("glide", glide(sound)),
        ("filter_per_note", Data::Bool(value("filter_sharing").as_str() == Some("per_note"))),
        ("oscillators", oscillators.clone()),
        ("envelopes", Data::List(ENVELOPE_PARTS.iter().map(|part| envelope(sound, part)).collect())),
        ("filter", filter(sound)),
        ("lfos", lfos(sound)),
        ("effects", effects(sound)),
        ("matrix", matrix(sound)),
    ];
    if oscillators.get("type").and_then(Data::as_str) == Some("drum") {
        spec.push(("tuned_from", Data::Whole(drums_from as i128)));
    }
    mapping(spec)
}

/// The oscillators part, as the backend's oscillators read it.
fn oscillators(sound: &Sound) -> Data {
    let kind = sound.part_type(OSCILLATORS);
    let setting = |name: &str| sound.part_value(OSCILLATORS, name);
    if kind == "drum" {
        let choke = setting("choke");
        let choke = if is_falsy(&choke) { Data::Null } else { choke };
        return mapping(vec![
            ("type", Data::text(&kind)),
            ("machine", setting("machine")),
            ("knobs", setting("knobs")),
            ("choke", choke),
            ("overlap", setting("overlap")),
        ]);
    }
    let mut spec = vec![("type", Data::text(&kind)), ("pitch_env", setting("pitch_env"))];
    match kind.as_str() {
        "sid" => spec.extend([
            ("wave", setting("wave")),
            ("pulse_width", share(&setting("pulse_width"), PERCENT)),
            ("modulation", setting("modulation")),
            ("interval", setting("interval")),
            ("arpeggio", setting("arpeggio")),
        ]),
        "pocket" => {
            let duty = setting("duty");
            let duty = DUTY_SHARES.iter().find(|(name, _)| duty.as_str() == Some(name)).map_or(0.5, |(_, part)| *part);
            spec.extend([
                ("chip_voice", setting("chip_voice")),
                ("duty", Data::Float(duty)),
                ("wave_shape", setting("wave_shape")),
                ("noise", setting("noise")),
                ("sweep_pace", setting("sweep_pace")),
                ("sweep_up", Data::Bool(setting("sweep_direction").as_str() == Some(UP))),
                ("sweep_step", setting("sweep_step")),
            ]);
        }
        "acid" => spec.extend([("acid_wave", setting("acid_wave")), ("tuning", setting("tuning"))]),
        "asheville" => spec.extend(asheville(sound)),
        _ => spec.push(("oscillators", basic_oscillators(sound))),
    }
    mapping(spec)
}

/// Each footage's distance from the note in half steps: 8' plays the note, each halving of the pipe an octave up, and
/// LO, Osc 3's range for an LFO, four octaves under.
const FOOTAGES: &[(&str, i128)] = &[("lo", -48), ("32", -24), ("16", -12), ("8", 0), ("4", 12), ("2", 24)];
/// An Asheville oscillator's Speed that plays the note at its Range, rather than an LFO's rate.
const AUDIO_SPEED: &str = "audio";
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
            let range = own("range");
            let half_steps = FOOTAGES.iter().find(|(name, _)| range.as_str() == Some(name)).map_or(0, |(_, steps)| *steps);
            let sub = own("sub").as_str().and_then(|octaves| octaves.parse::<i128>().ok()).unwrap_or(0);
            // At an LFO's Speed the oscillator runs at its Rate's hertz whatever the note.
            let speed = own("speed").as_str().unwrap_or(AUDIO_SPEED).to_string();
            let hertz = if speed == AUDIO_SPEED {
                Data::Null
            } else {
                Data::Float(lfo_speed::hertz(&speed, own("rate").as_whole().unwrap_or(0) as f64))
            };
            mapping(vec![
                ("hertz", hertz),
                ("range", Data::Whole(half_steps)),
                ("wave", own("wave")),
                ("shape", share(&own("shape"), PERCENT)),
                ("cents", own("tune")),
                ("mix", Data::Float(own("mix").as_whole().unwrap_or(0) as f64 / PANEL_TOP)),
                ("sub", Data::Whole(sub)),
                ("on", own("on")),
            ])
        })
        .collect();
    let feedback = if setting("feedback_on") == Data::Bool(true) {
        panel("feedback")
    } else {
        Data::Float(0.0)
    };
    vec![
        ("oscillators", Data::List(oscillators)),
        ("model", setting("model")),
        ("character", setting("character")),
        ("noise", panel("noise_level")),
        ("ring", panel("ring")),
        ("snap", setting("tune_snap")),
        ("drift", panel("drift")),
        ("feedback", feedback),
    ]
}

/// Basic's oscillators that sound, each its waveform, its detune in cents and its level as a fraction, those off left out.
fn basic_oscillators(sound: &Sound) -> Data {
    let count = sound.part_value(OSCILLATORS, OSCILLATORS).as_list().map_or(0, <[Data]>::len);
    let mut sounding = Vec::new();
    for number in 1..=count {
        let waveform = sound.oscillator(number, "waveform");
        if waveform.as_str() == Some("off") {
            continue;
        }
        let level = share(&sound.oscillator(number, "level"), PERCENT);
        sounding.push(Data::List(vec![waveform, sound.oscillator(number, "detune"), level]));
    }
    Data::List(sounding)
}

/// A part's Circuit, and its modded choice, which shows the classic modifications' settings.
const CIRCUIT: &str = "circuit";
const MODDED: &str = "modded";

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
    share(&sound.value("glide"), MILLISECONDS)
}

/// The envelope type that is no envelope, as the backend names it.
const NO_ENVELOPE: &str = "none";

/// An envelope part, as the backend's envelopes read it.
fn envelope(sound: &Sound, part: &str) -> Data {
    let kind = sound.part_type(part);
    let setting = |name: &str| sound.part_value(part, name);
    let typed = ("type", Data::text(&kind));
    match kind.as_str() {
        // Off, which only Env2 and Env3 may be, has no settings: the backend holds it at nothing.
        NO_ENVELOPE => mapping(vec![typed]),
        "sid_adsr" => mapping(vec![
            typed,
            ("attack", setting("attack")),
            ("decay", setting("decay")),
            ("sustain", setting("sustain")),
            ("release", setting("release")),
        ]),
        "vactrol" => {
            let cell = setting("cell");
            let (rise, fall) = CELLS
                .iter()
                .find(|(name, ..)| cell.as_str() == Some(name))
                .map_or((0.005, 0.08), |(_, rise, fall)| (*rise, *fall));
            mapping(vec![
                typed,
                ("rise", Data::Float(rise)),
                ("fall", Data::Float(fall)),
                ("drive", setting("light")),
                ("strike_width", share(&setting("strike_width"), TENTHS_OF_MILLISECONDS)),
                ("memory", share(&setting("memory"), PERCENT)),
                ("age", share(&setting("age"), PERCENT)),
                ("stability", share(&setting("stability"), PERCENT)),
            ])
        }
        "acid_gate" => {
            // On Stock the modded settings play the circuit's own values, the type's defaults, whatever is written.
            let modded = setting(CIRCUIT).as_str() == Some(MODDED);
            let chosen = |name: &str| if modded { setting(name) } else { default_of("acid_gate", name) };
            mapping(vec![
                typed,
                ("accent", share(&setting("accent"), PERCENT)),
                ("accent_threshold", setting("accent_threshold")),
                ("accent_sweep", share(&chosen("accent_sweep"), PERCENT)),
                ("accent_decay", share(&chosen("accent_decay"), MILLISECONDS)),
                ("amp_decay", share(&chosen("amp_decay"), MILLISECONDS)),
                ("soft_attack", share(&chosen("soft_attack"), TENTHS_OF_MILLISECONDS)),
            ])
        }
        "chip_steps" => mapping(vec![
            typed,
            ("start_level", setting("start_level")),
            ("level_pace", setting("level_pace")),
            ("level_up", Data::Bool(setting("level_direction").as_str() == Some(UP))),
        ]),
        _ => {
            // The snappy ADSR, AR or ASR: an AR or ASR has neither hold nor decay, and falls at its release.
            let release = share(&setting("release"), MILLISECONDS);
            let full = kind == "adsr";
            let or_none = |name: &str, scale: f64, otherwise: Data| if full { share(&setting(name), scale) } else { otherwise };
            mapping(vec![
                typed,
                ("attack", share(&setting("attack"), MILLISECONDS)),
                ("attack_curve", setting("attack_curve")),
                ("release", release.clone()),
                ("hold", or_none("hold", MILLISECONDS, Data::Float(0.0))),
                ("decay", or_none("decay", MILLISECONDS, release)),
                ("snap", or_none("snap", PERCENT, Data::Float(0.0))),
                ("sustain", or_none("sustain", PERCENT, Data::Float(0.0))),
            ])
        }
    }
}

/// The filter part, as the backend's filters and gates read it, or none.
fn filter(sound: &Sound) -> Data {
    let kind = sound.part_type(FILTER);
    let setting = |name: &str| sound.part_value(FILTER, name);
    let typed = ("type", Data::text(&kind));
    match kind.as_str() {
        "none" => mapping(vec![typed]),
        "low_pass_gate" => mapping(vec![
            typed,
            ("mode", setting("gate_mode")),
            ("resonance", share(&setting("resonance"), PERCENT)),
            ("open", setting("open")),
            ("key_track", share(&setting("key_track"), PERCENT)),
            ("input", setting("input")),
            ("ping_width", share(&setting("ping_width"), TENTHS_OF_MILLISECONDS)),
        ]),
        _ => {
            let mode = if kind == "multimode" || kind == "sallen_key" {
                setting("mode")
            } else {
                Data::text("low")
            };
            let poles = if kind == "ladder" {
                Data::Whole((whole(&setting("slope")).div_euclid(DB_A_POLE)) as i128)
            } else {
                Data::Whole(FOUR_POLES as i128)
            };
            mapping(vec![
                typed,
                ("mode", mode),
                ("poles", poles),
                ("cutoff", setting("cutoff")),
                ("resonance", share(&setting("resonance"), PERCENT)),
                ("env_amount", share(&setting("env_amount"), PERCENT)),
                ("key_track", share(&setting("key_track"), PERCENT)),
                ("drive", share(&setting("drive"), PERCENT)),
                // The Diode's Filter FM, the oscillator moving the cutoff for growl, is a modification: none on Stock.
                (
                    "filter_fm",
                    if kind == "diode" && setting(CIRCUIT).as_str() == Some(MODDED) {
                        share(&setting("filter_fm"), PERCENT)
                    } else {
                        Data::Float(0.0)
                    },
                ),
            ])
        }
    }
}

/// The LFOs in their places, None for one that is off, so that the matrix finds each by its number.
fn lfos(sound: &Sound) -> Data {
    let count = sound.value("lfos").as_list().map_or(0, <[Data]>::len);
    let mut lfos = Vec::new();
    for number in 1..=count {
        let setting = |name: &str| sound.item("lfos", number, name, LFO_DEFAULTS);
        if is_falsy(&setting("on")) {
            lfos.push(Data::Null);
            continue;
        }
        let speed = setting("speed").as_str().unwrap_or(lfo_speed::DEFAULT_SPEED).to_string();
        let percent = setting("rate_percent").as_whole().unwrap_or(0) as f64;
        let mut lfo = vec![
            ("shape", setting("shape")),
            ("rate", Data::Float(lfo_speed::hertz(&speed, percent))),
            ("retrigger", setting("retrigger")),
            ("each_scene", setting("each_scene")),
        ];
        // At audio rate an LFO may follow the key, running at its ratio times each note's frequency.
        if speed == lfo_speed::AUDIO_SPEED && setting("key") == Data::Bool(true) {
            let ratio = setting("ratio").as_str().map(lfo_speed::ratio_multiple).unwrap_or(1.0);
            lfo.push(("key_ratio", Data::Float(ratio)));
        }
        lfos.push(mapping(lfo));
    }
    Data::List(lfos)
}

/// The effects in order, every setting given, shares as fractions, the empty ones left out.
fn effects(sound: &Sound) -> Data {
    let count = sound.value("effects").as_list().map_or(0, <[Data]>::len);
    let mut effects = Vec::new();
    for number in 1..=count {
        let mut effect = every_setting(sound, "effects", number, EFFECT_DEFAULTS);
        if effect.get("effect").and_then(Data::as_str) == Some("none") {
            continue;
        }
        for name in ["amount", "mix"] {
            let scaled = effect.get(name).map(|value| share(value, PERCENT)).unwrap_or(Data::Float(0.0));
            set(&mut effect, name, scaled);
        }
        effects.push(effect);
    }
    Data::List(effects)
}

/// The matrix's slots, each amount a fraction either way.
fn matrix(sound: &Sound) -> Data {
    let count = sound.value("matrix").as_list().map_or(0, <[Data]>::len);
    let mut slots = Vec::new();
    for number in 1..=count {
        let mut slot = every_setting(sound, "matrix", number, SLOT_DEFAULTS);
        let scaled = slot.get("amount").map(|value| share(value, PERCENT)).unwrap_or(Data::Float(0.0));
        set(&mut slot, "amount", scaled);
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
