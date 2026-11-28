// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Every control the Instrument page shows for a built-in synth changes the sound: each part's type is played, a note
//! held and released, and played again with each of its settings moved across its range, the two compared sample for
//! sample, all without a sound card. A setting that changes nothing is a control wired to nothing.

use llamatron_backend::instrument::patch::{Patch, Voice};
use llamatron_model::file::data::{load, Data};
use llamatron_model::objects::setlist::Instrument;
use llamatron_tracker::generated::sounds::{SettingKind, MODDED_SETTINGS, PART_TYPES, SETTING_KINDS, TYPE_SETTINGS, TYPE_SETTING_KINDS};
use llamatron_tracker::instrument_sound::Sound;

/// The sample rate the notes are played at, the note, its velocity, how long it is held and how long it rings after.
const RATE: f64 = 48000.0;
const PITCH: f64 = 45.0;
const VELOCITY: f64 = 0.9;
const HELD_SECONDS: f64 = 0.5;
const RINGING_SECONDS: f64 = 0.5;
const CHUNK: usize = 256;
/// How far a first note runs on into a second, as a glided step's does.
const OVERLAP_SECONDS: f64 = 0.02;
/// The default drum octave, where the built-in drums play at their own pitch.
const DRUMS_FROM: i64 = 36;
/// How different two playings must be, as a share of the louder's energy, to count as a different sound.
const LEAST_CHANGE: f64 = 1e-6;

/// An instrument of a sound written as a set file writes one.
fn instrument(sound: &str) -> Instrument {
    let text = format!("{{ name: tried, kind: built_in, role: normal, sound: {sound} }}");
    let data = load(&text).expect("the scenario's sound is YAML");
    Instrument::from_data(&data).expect("the scenario's instrument is valid")
}

/// The instrument with its sound replaced.
fn with_sound(instrument: &Instrument, sound: Data) -> Instrument {
    let mut changed = instrument.clone();
    changed.set_written("sound", Some(sound));
    changed
}

/// One note of an instrument, held and released, sample by sample.
fn played(instrument: &Instrument) -> Vec<f32> {
    played_notes(instrument, &[PITCH])
}

/// Notes of an instrument one after another, each held and released, the next starting as the last ends, sample by
/// sample, so that what one note leaves the next can be heard.
fn played_notes(instrument: &Instrument, pitches: &[f64]) -> Vec<f32> {
    let spec = llamatron_tracker::sound_spec::synth_spec(&Sound::of(instrument), DRUMS_FROM);
    let value = llamatron_tracker::msgpack::value_of(&spec);
    let mut patch = Patch::compiled(&value, RATE);
    let note_samples = ((HELD_SECONDS + RINGING_SECONDS) * RATE) as i64;
    let held = (HELD_SECONDS * RATE) as i64;
    let mut out = Vec::new();
    for (number, pitch) in pitches.iter().enumerate() {
        let begins = number as i64 * note_samples;
        let mut voice = Voice::new(number as u64 + 1, 0, *pitch, begins, VELOCITY, None);
        patch.begin(&mut voice);
        let mut start = begins;
        while start < begins + note_samples {
            let frames = CHUNK.min((begins + note_samples - start) as usize);
            if start + frames as i64 > begins + held && voice.release_at.is_none() {
                voice.release_at = Some(begins + held);
            }
            patch.ready(frames);
            patch.buffer[..frames].fill(0.0);
            patch.play(&mut voice, start, frames);
            patch.finish(frames);
            out.extend_from_slice(&patch.buffer[..frames]);
            start += frames as i64;
        }
    }
    out
}

/// A note of an instrument overlapped by a second, as a glided step runs into the next, played through the engine so
/// that the instrument slides or strikes the second afresh as its Glide switch says.
fn slid(instrument: &Instrument, first: f64, second: f64) -> Vec<f32> {
    let spec = llamatron_tracker::sound_spec::synth_spec(&Sound::of(instrument), DRUMS_FROM);
    let value = llamatron_tracker::msgpack::value_of(&spec);
    let mut engine = llamatron_backend::engine::Engine::new(RATE, None);
    engine.set_instrument(0, Box::new(Patch::compiled(&value, RATE)));
    let held = (HELD_SECONDS * RATE) as i64;
    let overlap = (OVERLAP_SECONDS * RATE) as i64;
    let note = |sample: i64, kind: i64, pitch: f64| llamatron_backend::engine::Event {
        sample,
        order: 0,
        kind,
        instrument: 0,
        pitch,
        velocity: VELOCITY * 127.0,
        hit: None,
    };
    engine.schedule(note(0, llamatron_backend::engine::NOTE_ON, first));
    engine.schedule(note(held, llamatron_backend::engine::NOTE_ON, second));
    engine.schedule(note(held + overlap, llamatron_backend::engine::NOTE_OFF, first));
    engine.schedule(note(2 * held, llamatron_backend::engine::NOTE_OFF, second));
    let (mut left, mut right) = (vec![0.0; CHUNK], vec![0.0; CHUNK]);
    let mut out = Vec::new();
    let mut start = 0;
    while start < 3 * held {
        engine.render(start, &mut left, &mut right);
        out.extend_from_slice(&left);
        start += CHUNK as i64;
    }
    out
}

/// Whether two playings differ by more than LEAST_CHANGE of the louder's energy.
fn differs(first: &[f32], second: &[f32]) -> bool {
    let energy = |samples: &[f32]| samples.iter().map(|sample| (*sample as f64).powi(2)).sum::<f64>();
    let difference: f64 = first.iter().zip(second).map(|(a, b)| (*a as f64 - *b as f64).powi(2)).sum();
    let louder = energy(first).max(energy(second));
    louder > 0.0 && difference > LEAST_CHANGE * louder
}

/// How a setting is shown for a type of part: its type's own way where it has one, else the setting's.
fn kind_of(part_type: &str, setting: &str) -> Option<SettingKind> {
    TYPE_SETTING_KINDS
        .iter()
        .find(|(kind, name, _)| *kind == part_type && *name == setting)
        .map(|(.., how)| *how)
        .or_else(|| SETTING_KINDS.iter().find(|(name, _)| *name == setting).map(|(_, how)| *how))
}

/// The values a setting can be moved to, at the ends of its range and each choice.
fn values_of(kind: SettingKind) -> Vec<Data> {
    match kind {
        SettingKind::Choice { choices, .. } => choices.iter().map(|choice| Data::text(choice)).collect(),
        SettingKind::Toggle => vec![Data::Bool(false), Data::Bool(true)],
        SettingKind::Number { lowest, highest, .. } | SettingKind::Gauge { lowest, highest, .. } => {
            vec![Data::Whole(lowest as i128), Data::Whole(highest as i128)]
        }
        SettingKind::SidTime { highest, .. } => vec![Data::Whole(0), Data::Whole(highest as i128)],
    }
}

/// The sound a type of part is tried in: a synth whose other parts let the part be heard, such as a held envelope's
/// sustain or a filter at a cutoff Env2 moves.
fn tried_in(part: &str, part_type: &str) -> String {
    let oscillators = if part == "oscillators" {
        match part_type {
            "basic" => "{ type: basic, oscillators: [{ waveform: pulse, detune: 7 }] }".to_string(),
            "sid" => "{ type: sid, wave: pulse }".to_string(),
            other => format!("{{ type: {other} }}"),
        }
    } else {
        "{ type: basic, oscillators: [{ waveform: saw }] }".to_string()
    };
    let envelope = |place: &str| {
        if part == place {
            format!("{{ type: {part_type} }}")
        } else {
            "{ type: adsr, attack: 10, decay: 200, sustain: 50, release: 200 }".to_string()
        }
    };
    let filter = if part == "filter" {
        format!("{{ type: {part_type}, env_amount: 50, key_track: 0 }}")
    } else {
        "{ type: ladder, cutoff: 1500, resonance: 30, env_amount: 50 }".to_string()
    };
    let amp = if part == "amp" {
        format!("{{ type: {part_type} }}")
    } else {
        "{ type: clean }".to_string()
    };
    let engine = if part_type == "drum" { "drum" } else { "basic" };
    format!(
        "{{ engine: {engine}, oscillators: {oscillators}, envelopes: [{}, {}, {}], filter: {filter}, amp: {amp}, matrix: [{{ source: env3, via: none, destination: pitch, amount: 20 }}] }}",
        envelope("env1"),
        envelope("env2"),
        envelope("env3")
    )
}

/// The settings a setting only sounds in company of, written first: the second oscillator Interval sets the pitch of,
/// the voice of the chip a shape or a noise belongs to, a sweep or a level that moves, an attack long enough to curve, a
/// sustain that holds into the release, a note soft enough not to accent, and the gate's Lowpass mode or its ping.
fn company(part_type: &str, setting: &str) -> &'static [(&'static str, &'static str)] {
    match (part_type, setting) {
        ("sid", "interval") => &[("ring_on", "true")],
        ("pocket", "wave_shape") => &[("chip_voice", "wave")],
        ("pocket", "noise") => &[("chip_voice", "noise")],
        ("pocket", "sweep_step") | ("pocket", "sweep_direction") => &[("sweep_pace", "3")],
        ("chip_steps", "level_direction") => &[("start_level", "8"), ("level_pace", "3")],
        ("adsr", "attack_curve") | ("ar", "attack_curve") | ("asr", "attack_curve") => &[("attack", "200")],
        ("adsr", "release") => &[("sustain", "80")],
        ("acid_gate", "soft_attack") => &[("circuit", "modded"), ("accent_threshold", "127")],
        ("low_pass_gate", "resonance") | ("low_pass_gate_amp", "resonance") => &[("gate_mode", "lowpass")],
        ("low_pass_gate", "ping_time") | ("low_pass_gate_amp", "ping_time") => &[("signal", "ping")],
        ("acid_gate", "circuit") => &[("amp_decay", "300")],
        ("diode", "circuit") => &[("filter_fm", "80")],
        ("asheville", "osc1_shape") | ("asheville", "osc2_shape") | ("asheville", "osc3_shape") => &[("model", "continuous")],
        ("asheville", "feedback") => &[("feedback_on", "true")],
        ("asheville", "osc1_rate") => &[("osc1_speed", "medium")],
        ("asheville", "osc2_rate") => &[("osc2_speed", "medium")],
        ("asheville", "osc3_rate") => &[("osc3_speed", "medium")],
        ("asheville", "feedback_on") => &[("feedback", "8")],
        (kind, name) if MODDED_SETTINGS.contains(&(kind, name)) => &[("circuit", "modded")],
        _ => &[],
    }
}

/// The settings tried apart from the rest: a list typed in, what one note leaves the next, and the drum's knobs, which a
/// hit renders apart.
fn tried_apart(part_type: &str, setting: &str) -> bool {
    matches!(
        (part_type, setting),
        ("sid", "arpeggio") | ("vactrol", "memory") | ("low_pass_gate", "memory") | ("low_pass_gate_amp", "memory") | ("drum", _)
    )
}

/// A value as the trial writes it: a switch, a whole number where it reads as one, else text.
fn written(value: &str) -> Data {
    match value {
        "true" => Data::Bool(true),
        "false" => Data::Bool(false),
        _ => value.parse::<i128>().map_or_else(|_| Data::text(value), Data::Whole),
    }
}

/// Every setting of every type of every part: moved across its range, at least two of its values sound different. The
/// parts' types are tried side by side, one thread a type, since each plays many notes.
#[test]
fn every_synth_control_changes_the_sound() {
    let trials: Vec<(&str, &str)> = PART_TYPES
        .iter()
        .flat_map(|(part, types, _)| types.iter().map(move |part_type| (*part, *part_type)))
        .collect();
    let unwired: Vec<String> = std::thread::scope(|scope| {
        let running: Vec<_> = trials
            .iter()
            .map(|(part, part_type)| scope.spawn(move || unwired_controls(part, part_type)))
            .collect();
        running.into_iter().flat_map(|thread| thread.join().expect("a trial runs to its end")).collect()
    });
    assert!(unwired.is_empty(), "these controls change nothing: {unwired:#?}");
}

/// The controls of one type of part that change nothing, each named by its part, type and setting.
fn unwired_controls(part: &str, part_type: &str) -> Vec<String> {
    let mut unwired = Vec::new();
    let plain = instrument(&tried_in(part, part_type));
    let settings = TYPE_SETTINGS.iter().find(|(kind, _)| *kind == part_type).map_or(&[][..], |(_, names)| *names);
    for setting in settings {
        if tried_apart(part_type, setting) {
            continue;
        }
        let Some(kind) = kind_of(part_type, setting) else { continue };
        let mut base = plain.clone();
        for (name, value) in company(part_type, setting) {
            base = with_sound(&base, Sound::of(&base).with_part_value(part, name, written(value)));
        }
        let sound = Sound::of(&base);
        let playings: Vec<Vec<f32>> = values_of(kind)
            .into_iter()
            .map(|value| played(&with_sound(&base, sound.with_part_value(part, setting, value))))
            .collect();
        let any_differ = playings.iter().skip(1).any(|playing| differs(&playings[0], playing));
        if !any_differ {
            unwired.push(format!("{part} {part_type} {setting}"));
        }
    }
    unwired
}

/// Two sounds as set files write them, the second differing from the first in one control, and what that control is.
type Trial = (&'static str, &'static str, &'static str);

/// The trials of the controls tried apart from a part's own settings: the SID's arpeggio, the vactrol's memory, the
/// Voice column, the LFOs, the Mod Matrix and the effects.
const TRIALS: &[Trial] = &[
    ("sid arpeggio", "{ engine: sid }", "{ engine: sid, oscillators: { type: sid, arpeggio: [0, 4, 7] } }"),
    ("basic wave", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }] } }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: pulse }] } }"),
    ("basic fine", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }] } }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw, fine: 35 }] } }"),
    ("basic detune", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }] } }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw, detune: 15 }] } }"),
    ("basic level", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: square }] } }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: square, level: 20 }] } }"),
    ("lfo on", "{ engine: basic, lfos: [{ \"on\": false }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo shape", "{ engine: basic, lfos: [{ \"on\": true, shape: sine }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, shape: square }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("matrix osc", "{ engine: basic, matrix: [{ source: osc, via: none, destination: pitch, amount: 0 }] }", "{ engine: basic, matrix: [{ source: osc, via: none, destination: pitch, amount: 40 }] }"),
    ("matrix asheville osc", "{ engine: asheville, matrix: [{ source: osc2, via: none, destination: pitch, amount: 0 }] }", "{ engine: asheville, matrix: [{ source: osc2, via: none, destination: pitch, amount: 40 }] }"),
    ("lfo rate", "{ engine: basic, lfos: [{ \"on\": true, rate_percent: 10 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, rate_percent: 90 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo speed", "{ engine: basic, lfos: [{ \"on\": true, speed: low, rate_percent: 50 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, rate_percent: 50 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo key", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, rate_percent: 0, key: false }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, rate_percent: 0, key: true }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo smooth random", "{ engine: basic, lfos: [{ \"on\": true, shape: sample_and_hold }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, shape: smooth_random }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo fade in", "{ engine: basic, lfos: [{ \"on\": true, fade_in: 0 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, fade_in: 3000 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo sync", "{ engine: basic, lfos: [{ \"on\": true, speed: medium, sync: false }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, sync: true }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo division", "{ engine: basic, lfos: [{ \"on\": true, sync: true, division: \"1/4\" }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, sync: true, division: \"1/16\" }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("matrix polarity", "{ engine: basic, lfos: [{ \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30, polarity: bipolar }] }", "{ engine: basic, lfos: [{ \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30, polarity: unipolar }] }"),
    ("lfo ratio", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, key: true, ratio: \"1:1\" }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, key: true, ratio: \"3:1\" }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("matrix source", "{ engine: basic, matrix: [{ source: env3, via: none, destination: cutoff, amount: 40 }] }", "{ engine: basic, matrix: [{ source: velocity, via: none, destination: cutoff, amount: 40 }] }"),
    ("matrix via", "{ engine: basic, matrix: [{ source: env2, via: none, destination: amp, amount: -40 }] }", "{ engine: basic, matrix: [{ source: env2, via: velocity, destination: amp, amount: -40 }] }"),
    ("matrix destination", "{ engine: basic, matrix: [{ source: env2, via: none, destination: pitch, amount: 40 }] }", "{ engine: basic, matrix: [{ source: env2, via: none, destination: resonance, amount: 40 }] }"),
    ("matrix amount", "{ engine: basic, matrix: [{ source: env2, via: none, destination: pitch, amount: 10 }] }", "{ engine: basic, matrix: [{ source: env2, via: none, destination: pitch, amount: 60 }] }"),
    ("matrix pulse width", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: pulse }] }, lfos: [{ \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pulse_width, amount: 0 }] }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: pulse }] }, lfos: [{ \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pulse_width, amount: 60 }] }"),
    ("sid ring with sync", "{ engine: sid, oscillators: { type: sid, wave: triangle, sync_on: true, interval: 7 } }", "{ engine: sid, oscillators: { type: sid, wave: triangle, sync_on: true, ring_on: true, interval: 7 } }"),
    ("matrix interval", "{ engine: sid, oscillators: { type: sid, wave: saw, sync_on: true, interval: 7 }, matrix: [{ source: env2, via: none, destination: interval, amount: 0 }] }", "{ engine: sid, oscillators: { type: sid, wave: saw, sync_on: true, interval: 7 }, matrix: [{ source: env2, via: none, destination: interval, amount: 60 }] }"),
    ("matrix fine", "{ engine: sid, oscillators: { type: sid, wave: saw }, matrix: [{ source: lfo1, via: none, destination: fine, amount: 0 }], lfos: [{ \"on\": true }] }", "{ engine: sid, oscillators: { type: sid, wave: saw }, matrix: [{ source: lfo1, via: none, destination: fine, amount: 80 }], lfos: [{ \"on\": true }] }"),
    ("matrix detune", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw, detune: 10 }] }, matrix: [{ source: env2, via: none, destination: detune, amount: 0 }] }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw, detune: 10 }] }, matrix: [{ source: env2, via: none, destination: detune, amount: 80 }] }"),
    ("filter ladder bass compensation", "{ engine: basic, filter: { type: ladder, cutoff: 400, resonance: 90, bass_compensation: 100 } }", "{ engine: basic, filter: { type: ladder, cutoff: 400, resonance: 90, bass_compensation: 0 } }"),
    ("effect drive", "{ engine: basic }", "{ engine: basic, effects: [{ effect: drive, curve: hard, amount: 80 }] }"),
    ("effect drive curve", "{ engine: basic, effects: [{ effect: drive, curve: soft, amount: 80 }] }", "{ engine: basic, effects: [{ effect: drive, curve: fold, amount: 80 }] }"),
    ("effect drive mix", "{ engine: basic, effects: [{ effect: drive, curve: hard, amount: 80, mix: 100 }] }", "{ engine: basic, effects: [{ effect: drive, curve: hard, amount: 80, mix: 20 }] }"),
    ("effect bitcrush bits", "{ engine: basic, effects: [{ effect: bitcrush, bits: 16 }] }", "{ engine: basic, effects: [{ effect: bitcrush, bits: 3 }] }"),
    ("effect bitcrush dither", "{ engine: basic, effects: [{ effect: bitcrush, bits: 6, dither: false }] }", "{ engine: basic, effects: [{ effect: bitcrush, bits: 6, dither: true }] }"),
    ("effect bitcrush rate", "{ engine: basic, effects: [{ effect: bitcrush, bits: 16, rate: 0 }] }", "{ engine: basic, effects: [{ effect: bitcrush, bits: 16, rate: 4000 }] }"),
    ("effect bax bass", "{ engine: basic, effects: [{ effect: bax }] }", "{ engine: basic, effects: [{ effect: bax, bass: 12 }] }"),
    ("effect bax treble", "{ engine: basic, effects: [{ effect: bax }] }", "{ engine: basic, effects: [{ effect: bax, treble: -12 }] }"),
    ("effect multitap", "{ engine: asheville }", "{ engine: asheville, effects: [{ effect: multitap }] }"),
    ("effect multitap sync", "{ engine: asheville, effects: [{ effect: multitap, sync: true }] }", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap1_ms: 90 }] }"),
    ("effect multitap tap time", "{ engine: asheville, effects: [{ effect: multitap }] }", "{ engine: asheville, effects: [{ effect: multitap, tap1_division: \"1/16\" }] }"),
    ("effect multitap tap ms", "{ engine: asheville, effects: [{ effect: multitap, sync: false }] }", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap1_ms: 90 }] }"),
    ("effect multitap tap level", "{ engine: asheville, effects: [{ effect: multitap }] }", "{ engine: asheville, effects: [{ effect: multitap, tap1_level: 0 }] }"),
    ("effect multitap feedback", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap4_ms: 200 }] }", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap4_ms: 200, feedback: 90 }] }"),
    ("effect multitap tone", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap4_ms: 200, feedback: 90 }] }", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap4_ms: 200, feedback: 90, tone: 500 }] }"),
    ("effect multitap tap on", "{ engine: asheville, effects: [{ effect: multitap }] }", "{ engine: asheville, effects: [{ effect: multitap, tap1_on: false }] }"),
    ("effect multitap feedback from", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap1_ms: 120, feedback: 90 }] }", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap1_ms: 120, feedback: 90, feedback_from: \"1\" }] }"),
    ("effect multitap low cut", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap4_ms: 200, feedback: 90 }] }", "{ engine: asheville, effects: [{ effect: multitap, sync: false, tap4_ms: 200, feedback: 90, low_cut: 2000 }] }"),
    ("effect multitap mode", "{ engine: asheville, effects: [{ effect: multitap, feedback: 60 }] }", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60 }] }"),
    ("effect multitap darkness", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60 }] }", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60, darkness: 100 }] }"),
    ("effect multitap noise", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60 }] }", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60, noise: 100 }] }"),
    ("effect multitap drive", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60 }] }", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60, drive: 100 }] }"),
    ("effect multitap wow", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60 }] }", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60, wow: 100 }] }"),
    ("effect multitap flutter", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60 }] }", "{ engine: asheville, effects: [{ effect: multitap, mode: analog, feedback: 60, flutter: 100 }] }"),
    ("effect multitap mix", "{ engine: asheville, effects: [{ effect: multitap }] }", "{ engine: asheville, effects: [{ effect: multitap, mix: 100 }] }"),
    ("env2 disconnect filter", "{ engine: basic, filter: { type: ladder, cutoff: 300, env_amount: 80 } }", "{ engine: basic, filter: { type: ladder, cutoff: 300, env_amount: 80 }, disconnect_filter: true }"),
    ("matrix lfo rate", "{ engine: basic, lfos: [{ \"on\": true }, { \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true }, { \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }, { source: lfo2, via: none, destination: lfo1_rate, amount: 80 }] }"),
];

/// The controls tried apart each change the sound, and the vactrol's memory carries from one note into the next.
#[test]
fn every_control_tried_apart_changes_the_sound() {
    // The trials run side by side, one thread a trial, since each plays a note twice.
    let mut unwired: Vec<&str> = std::thread::scope(|scope| {
        let running: Vec<_> = TRIALS
            .iter()
            .map(|(control, first, second)| scope.spawn(move || (*control, differs(&played(&instrument(first)), &played(&instrument(second))))))
            .collect();
        running
            .into_iter()
            .map(|thread| thread.join().expect("a trial runs to its end"))
            .filter(|(_, changes)| !changes)
            .map(|(control, _)| control)
            .collect()
    });
    let remembering = |memory: &str| {
        let sound = format!("{{ engine: basic, envelopes: [{{ type: vactrol, memory: {memory} }}] }}");
        played_notes(&instrument(&sound), &[PITCH, PITCH])
    };
    if !differs(&remembering("0"), &remembering("100")) {
        unwired.push("env1 vactrol memory");
    }
    // Restart is heard from the second note on: Each note starts the LFO again with it, On play lets it run on.
    let restarting = |restart: &str| {
        let sound = format!("{{ engine: basic, lfos: [{{ \"on\": true, rate_percent: 20, restart: {restart} }}], matrix: [{{ source: lfo1, via: none, destination: pitch, amount: 30 }}] }}");
        played_notes(&instrument(&sound), &[PITCH, PITCH])
    };
    if !differs(&restarting("on_play"), &restarting("each_note")) {
        unwired.push("lfo restart");
    }
    // A gate's own cell remembers the note before as the vactrol envelope does, in the Filter's place and the Amp's.
    let gate_remembering = |part: &str, kind: &str, memory: &str| {
        let sound = format!("{{ engine: basic, {part}: {{ type: {kind}, memory: {memory} }} }}");
        played_notes(&instrument(&sound), &[PITCH, PITCH])
    };
    for (part, kind, control) in [
        ("filter", "low_pass_gate", "filter low_pass_gate memory"),
        ("amp", "low_pass_gate_amp", "amp low_pass_gate_amp memory"),
    ] {
        if !differs(&gate_remembering(part, kind, "0"), &gate_remembering(part, kind, "100")) {
            unwired.push(control);
        }
    }
    // Oh3's slide is heard where a note overlaps the next a fifth higher, as a glided step does: its Glide time at
    // two ends, and the Glide switch on against off.
    let sliding = |glide: &str, glides: bool| {
        let sound = format!("{{ engine: oh3, glides: {glides}, glide: {glide}, oscillators: {{ type: acid }} }}");
        slid(&instrument(&sound), PITCH, PITCH + 7.0)
    };
    if !differs(&sliding("30", true), &sliding("300", true)) {
        unwired.push("voice glide");
    }
    if !differs(&sliding("300", true), &sliding("300", false)) {
        unwired.push("voice glides");
    }
    // Volume is the engine's, applied to the patch's buffer as it mixes, so it is read from the compiled patch.
    let volume = |percent: &str| {
        let sound = Sound::of(&instrument(&format!("{{ engine: basic, volume: {percent} }}")));
        let value = llamatron_tracker::msgpack::value_of(&llamatron_tracker::sound_spec::synth_spec(&sound, DRUMS_FROM));
        Patch::compiled(&value, RATE).volume
    };
    if volume("80") == volume("20") {
        unwired.push("voice volume");
    }
    assert!(unwired.is_empty(), "these controls change nothing: {unwired:#?}");
}

/// The energy of a playing from a time on, in seconds from the note's start.
fn energy_after(playing: &[f32], seconds: f64) -> f64 {
    playing[(seconds * RATE) as usize..].iter().map(|sample| (*sample as f64).powi(2)).sum()
}

/// An effect heard alone at a Mix of 100 still sounds, as a person hears it on an engine's defaults: MultiTap's echoes
/// ring on after the note, and every other effect plays the note through it.
#[test]
fn every_effect_at_full_mix_sounds() {
    let after_the_note = HELD_SECONDS + 0.05;
    let dry = played(&instrument("{ engine: asheville }"));
    let delayed = played(&instrument("{ engine: asheville, effects: [{ effect: multitap, mix: 100 }] }"));
    assert!(
        energy_after(&delayed, after_the_note) > energy_after(&dry, after_the_note),
        "MultiTap's echoes ring on after the note"
    );
    for effect in llamatron_backend::effects::REGISTRY.iter().map(|entry| entry.name) {
        let wet = played(&instrument(&format!("{{ engine: asheville, effects: [{{ effect: {effect}, mix: 100 }}] }}")));
        let audible_share = 0.01;
        assert!(
            energy_after(&wet, 0.0) > energy_after(&dry, 0.0) * audible_share,
            "{effect} at full Mix is heard"
        );
    }
}

/// Each of MechaDrum's five knobs changes each drum's hit, moved from its lowest to its highest with the others in the
/// middle.
#[test]
fn every_drum_knob_changes_the_hit() {
    let knob_names = ["pitch", "decay", "color", "shape", "sweep"];
    let middle = 64.0;
    let (lowest, highest) = (0.0, 127.0);
    let note = 60.0;
    let mut unwired = Vec::new();
    for machine in llamatron_model::schema::generated::file_format::DRUM_MACHINES {
        for (place, knob) in knob_names.iter().enumerate() {
            let hit_at = |value: f64| {
                let mut knobs = [middle; 5];
                knobs[place] = value;
                llamatron_backend::drums::render_hit(machine, &knobs, note, VELOCITY, RATE)
            };
            let (low, high) = (hit_at(lowest), hit_at(highest));
            let longer = low.len().max(high.len());
            let padded = |hit: &[f32]| {
                let mut samples = hit.to_vec();
                samples.resize(longer, 0.0);
                samples
            };
            if !differs(&padded(&low), &padded(&high)) {
                unwired.push(format!("{machine} {knob}"));
            }
        }
    }
    assert!(unwired.is_empty(), "these drum knobs change nothing: {unwired:#?}");
}

/// A MIDI CC routed through the Mod Matrix moves what it is routed to: the same note with CC 74 at its lowest and at its
/// highest, routed to the cutoff, sounds different, and a CC the matrix does not read changes nothing.
#[test]
fn a_midi_cc_in_the_matrix_moves_its_destination() {
    let sound = "{ engine: basic, matrix: [{ source: cc74, via: none, destination: cutoff, amount: 80 }] }";
    let instrument = instrument(sound);
    let spec = llamatron_tracker::sound_spec::synth_spec(&Sound::of(&instrument), DRUMS_FROM);
    let value = llamatron_tracker::msgpack::value_of(&spec);
    let (cutoff_cc, other_cc, lowest, highest) = (74, 20, 0.0, 127.0);
    let at = |number: usize, control: f64| {
        let mut patch = Patch::compiled(&value, RATE);
        patch.set_control(number, control);
        let mut voice = Voice::new(1, 0, PITCH, 0, VELOCITY, None);
        patch.begin(&mut voice);
        let mut out = Vec::new();
        let chunks = (HELD_SECONDS * RATE) as usize / CHUNK;
        for chunk in 0..chunks {
            patch.ready(CHUNK);
            patch.buffer[..CHUNK].fill(0.0);
            patch.play(&mut voice, (chunk * CHUNK) as i64, CHUNK);
            patch.finish(CHUNK);
            out.extend_from_slice(&patch.buffer[..CHUNK]);
        }
        out
    };
    assert!(differs(&at(cutoff_cc, lowest), &at(cutoff_cc, highest)), "CC 74 moves the cutoff");
    assert!(
        !differs(&at(other_cc, lowest), &at(other_cc, highest)),
        "a CC the matrix does not read changes nothing"
    );
}

/// On every engine but the drums, a one-voice instrument slides into an overlapping note on the voice it was playing,
/// its pitch moved and nothing struck again: a glided step never restarts the amp envelope or the filter's (the user's
/// rule for every synth). The first note's voice is the one still sounding, at the second note's pitch.
#[test]
fn every_engine_slides_a_glided_step_without_striking_it_again() {
    let (first, second) = (PITCH, PITCH + 7.0);
    let held = (HELD_SECONDS * RATE) as i64;
    let overlap = (OVERLAP_SECONDS * RATE) as i64;
    let first_voice = 1;
    for engine_name in llamatron_model::schema::generated::file_format::SOUND_ENGINES
        .iter()
        .filter(|name| **name != "drum")
    {
        let instrument = instrument(&format!("{{ engine: {engine_name}, voices: 1, glide: 60 }}"));
        let spec = llamatron_tracker::sound_spec::synth_spec(&Sound::of(&instrument), DRUMS_FROM);
        let value = llamatron_tracker::msgpack::value_of(&spec);
        let mut engine = llamatron_backend::engine::Engine::new(RATE, None);
        engine.set_instrument(0, Box::new(Patch::compiled(&value, RATE)));
        let note = |sample: i64, kind: i64, pitch: f64| llamatron_backend::engine::Event {
            sample,
            order: 0,
            kind,
            instrument: 0,
            pitch,
            velocity: VELOCITY * 127.0,
            hit: None,
        };
        engine.schedule(note(0, llamatron_backend::engine::NOTE_ON, first));
        engine.schedule(note(held, llamatron_backend::engine::NOTE_ON, second));
        engine.schedule(note(held + overlap, llamatron_backend::engine::NOTE_OFF, first));
        let (mut left, mut right) = (vec![0.0; CHUNK], vec![0.0; CHUNK]);
        let mut start = 0;
        while start < held + 2 * overlap {
            engine.render(start, &mut left, &mut right);
            start += CHUNK as i64;
        }
        assert_eq!(engine.sounding(), vec![(first_voice, second)], "{engine_name} slides on its first voice");
    }
}

/// Oscillators run free, so that two in tune mix rather than lock: a saw and a square started together add up to a saw
/// an octave up, no louder than the saw alone, while running free they are on average far louder, as two unrelated
/// waves are, and each note starts them differently. Asheville's, with Drift at nothing, so that only their phases
/// differ.
#[test]
fn oscillators_in_tune_mix_rather_than_lock() {
    let notes = [PITCH; 8];
    let energy = |waves: &str| {
        let sound = format!(
            "{{ engine: asheville, oscillators: {{ type: asheville, osc1_range: \"8\", osc2_range: \"8\", {waves}, osc1_tune: 0, osc2_tune: 0, osc3_on: false, drift: 0 }}, filter: {{ type: none }} }}"
        );
        let out = played_notes(&instrument(&sound), &notes);
        let note = out.len() / notes.len();
        (0..notes.len())
            .map(|n| out[n * note..(n + 1) * note].iter().map(|sample| (*sample as f64).powi(2)).sum::<f64>())
            .collect::<Vec<f64>>()
    };
    let saw = energy("osc1_wave: saw, osc1_mix: 10, osc2_on: false");
    let mixed = energy("osc1_wave: saw, osc1_mix: 10, osc2_wave: square, osc2_mix: 10");
    let average = |energies: &[f64]| energies.iter().sum::<f64>() / energies.len() as f64;
    assert!(average(&mixed) > 2.0 * average(&saw), "{} against {}", average(&mixed), average(&saw));
    let spread = mixed.iter().cloned().fold(f64::MIN, f64::max) / mixed.iter().cloned().fold(f64::MAX, f64::min);
    assert!(spread > 1.5, "each note starts the oscillators afresh: {spread}");
}

/// The loudness of each fiftieth of a second of the held part of a note, as the root of its mean square.
fn window_levels(samples: &[f32]) -> Vec<f64> {
    let window = (RATE / 50.0) as usize;
    let held = (HELD_SECONDS * RATE) as usize;
    let settled = window * 5;
    samples[settled..held]
        .chunks(window)
        .map(|chunk| (chunk.iter().map(|sample| (*sample as f64).powi(2)).sum::<f64>() / chunk.len() as f64).sqrt())
        .collect()
}

/// Asheville's three oscillators set in tune beat against each other with Drift up, as three analog oscillators do,
/// each wandering and jittering on its own, and hold one steady level with Drift at nothing.
#[test]
fn ashevilles_drift_makes_oscillators_in_tune_beat() {
    let sound = |drift: i64| {
        format!(
            "{{ engine: asheville, oscillators: {{ type: asheville, osc1_range: \"8\", osc2_range: \"8\", osc3_range: \"8\", osc1_wave: saw, osc2_wave: saw, osc3_wave: saw, osc1_tune: 0, osc2_tune: 0, osc3_tune: 0, drift: {drift} }}, envelopes: [{{ type: adsr, attack: 1, decay: 0, sustain: 100, release: 50 }}, {{ type: none }}, {{ type: none }}], filter: {{ type: none }} }}"
        )
    };
    let swing = |drift: i64| {
        let levels = window_levels(&played(&instrument(&sound(drift))));
        let (most, least) = levels
            .iter()
            .fold((f64::MIN, f64::MAX), |(most, least), level| (most.max(*level), least.min(*level)));
        most / least
    };
    let steady = swing(0);
    let beating = swing(10);
    // A window not lining up with the wave's cycle leaves a few percent even when nothing beats.
    assert!(steady < 1.1, "steady without Drift: {steady:.3}");
    assert!(beating > 1.3, "beating with Drift: {beating:.3}");
}

/// Every engine of notes, walked from the engine list, plays the same note the same way every time, so that every
/// render is the same, and keeps within its headroom: its voice, before the instrument's Volume and the engine's safety,
/// peaks under half as much again as full scale. The drum machines are held by their own tests.
#[test]
fn every_engine_plays_the_same_twice_within_its_headroom() {
    use llamatron_tracker::generated::sounds::ENGINES_OF_ROLE;
    let normal = "normal";
    let headroom = 1.5f32;
    let engines = ENGINES_OF_ROLE
        .iter()
        .filter(|(role, _)| *role == normal)
        .flat_map(|(_, engines)| engines.iter().copied());
    for engine in engines {
        let plain = format!("{{ engine: {engine} }}");
        let first = played(&instrument(&plain));
        assert_eq!(first, played(&instrument(&plain)), "{engine} plays the same twice");
        let peak = first.iter().fold(0.0f32, |most, sample| most.max(sample.abs()));
        assert!(peak > 0.0 && peak < headroom, "{engine}: {peak}");
    }
}

/// A map of a sound's settings, built as data.
fn settings(pairs: &[(&str, Data)]) -> Data {
    Data::Map(pairs.iter().map(|(key, value)| (Data::text(key), value.clone())).collect())
}

/// An instrument of the basic engine whose first Modulators slot holds a Snail weighted as given, and whose Mod Matrix
/// routes as the slots given say.
fn snail_instrument(weighting: i64, routes: &[Data]) -> Instrument {
    let default_seconds = 30;
    snail_at_speed(weighting, default_seconds, routes)
}

/// The same instrument, its Snail's Slow lane's trips lasting about some seconds.
fn snail_at_speed(weighting: i64, seconds: i64, routes: &[Data]) -> Instrument {
    let (engine, snail) = ("basic", "snail");
    let snail_slot = settings(&[
        ("type", Data::text(snail)),
        ("slow", Data::Whole(weighting.into())),
        ("slow_speed", Data::Whole(seconds.into())),
    ]);
    let sound = settings(&[
        ("engine", Data::text(engine)),
        ("lfos", Data::List(vec![snail_slot])),
        ("matrix", Data::List(routes.to_vec())),
    ]);
    let instrument = settings(&[
        ("name", Data::text("tried")),
        ("kind", Data::text("built_in")),
        ("role", Data::text("normal")),
        ("sound", sound),
    ]);
    Instrument::from_data(&instrument).expect("the scenario's instrument is valid")
}

/// A Mod Matrix slot from a source to a destination at an amount in percent.
fn route(source: &str, destination: &str, amount: i64) -> Data {
    settings(&[
        ("source", Data::text(source)),
        ("via", Data::text("none")),
        ("destination", Data::text(destination)),
        ("amount", Data::Whole(amount.into())),
    ])
}

/// Slow's Y over a minute, as the instrument the tracker sends plays it: a weighting leans so slow a circuit over many
/// seconds, longer than a note the other tests play.
fn slow_path(instrument: &Instrument) -> Vec<f64> {
    let heard_seconds = 60.0;
    let (frames, slow_y) = (llamatron_backend::engine::MOST_FRAMES, 1);
    let spec = llamatron_tracker::sound_spec::synth_spec(&Sound::of(instrument), DRUMS_FROM);
    let mut patch = Patch::compiled(&llamatron_tracker::msgpack::value_of(&spec), RATE);
    let mut path = Vec::new();
    for _ in 0..(heard_seconds * RATE / frames as f64) as usize {
        patch.ready(frames);
        path.push(patch.lfos.snail_now[0][0][slow_y]);
    }
    path
}

/// Slow's Y over a few seconds while one note is held throughout, with a MIDI CC at its highest, so that the routes of
/// a note's sources and of a CC move it.
fn slow_path_under_a_note(instrument: &Instrument, control: usize) -> Vec<f64> {
    let heard_seconds = 5.0;
    let (frames, slow_y, highest) = (llamatron_backend::engine::MOST_FRAMES, 1, 127.0);
    let spec = llamatron_tracker::sound_spec::synth_spec(&Sound::of(instrument), DRUMS_FROM);
    let mut patch = Patch::compiled(&llamatron_tracker::msgpack::value_of(&spec), RATE);
    patch.set_control(control, highest);
    let mut voice = Voice::new(1, 0, PITCH, 0, VELOCITY, None);
    patch.begin(&mut voice);
    let mut path = Vec::new();
    for chunk in 0..(heard_seconds * RATE / frames as f64) as usize {
        patch.ready(frames);
        patch.buffer[..frames].fill(0.0);
        patch.play(&mut voice, (chunk * frames) as i64, frames);
        patch.finish(frames);
        path.push(patch.lfos.snail_now[0][0][slow_y]);
    }
    path
}

/// Slow and Slower take every Mod Matrix source: a note's, such as its Velocity, through the newest note, and the
/// instrument's own, such as a MIDI CC, at once.
#[test]
fn every_source_moves_a_snails_weighting() {
    let (control, full) = (74, 100);
    let heard = route("lfo1_slow_y", "cutoff", full);
    let unmoved = slow_path_under_a_note(&snail_instrument(0, std::slice::from_ref(&heard)), control);
    for source in ["velocity".to_string(), "env1".to_string(), format!("cc{control}")] {
        let routes = [heard.clone(), route(&source, "lfo1_slow", full)];
        let moved = slow_path_under_a_note(&snail_instrument(0, &routes), control);
        assert_ne!(unmoved, moved, "{source} moves Slow");
    }
}

/// A Snail in a Modulators slot is heard as a person plays it: each of its outputs moves the cutoff through the Mod
/// Matrix, and its A gauge and its Slow speed change the path Slow takes.
#[test]
fn a_snail_moves_its_destinations_and_its_settings_move_it() {
    let (cutoff, full, centre, leaning) = ("cutoff", 100, 0, 100);
    let silent = played(&snail_instrument(centre, &[route("lfo1_slow_x", cutoff, 0)]));
    for circuit in ["slow", "slower", "slowest"] {
        for axis in ["x", "y", "z"] {
            let output = format!("lfo1_{circuit}_{axis}");
            let heard = played(&snail_instrument(centre, &[route(&output, cutoff, full)]));
            assert!(differs(&silent, &heard), "{output} moves the cutoff");
        }
    }
    let quickest_seconds = 5;
    let routed = [route("lfo1_slow_y", cutoff, full)];
    assert_ne!(
        slow_path(&snail_instrument(centre, &routed)),
        slow_path(&snail_instrument(leaning, &routed)),
        "the A gauge moves Slow"
    );
    assert_ne!(
        slow_path(&snail_instrument(centre, &routed)),
        slow_path(&snail_at_speed(centre, quickest_seconds, &routed)),
        "the Slow speed moves Slow"
    );
}

/// On Asheville, a route to one oscillator's Pitch moves that oscillator alone: Osc 1 / Pitch and Osc 2 / Pitch are
/// heard apart, and each is heard against no route at all.
#[test]
fn ashevilles_oscillators_are_moved_one_by_one() {
    let (amount, lfo) = (30, "lfo1");
    let asheville = |destination: &str, amount: i64| {
        let oscillator = |on: bool| settings(&[("on", Data::Bool(on))]);
        let sound = settings(&[
            ("engine", Data::text("asheville")),
            (
                "oscillators",
                settings(&[
                    ("type", Data::text("asheville")),
                    ("oscillators", Data::List(vec![oscillator(true), oscillator(true)])),
                ]),
            ),
            ("lfos", Data::List(vec![settings(&[("on", Data::Bool(true))])])),
            ("matrix", Data::List(vec![route(lfo, destination, amount)])),
        ]);
        let instrument = settings(&[
            ("name", Data::text("tried")),
            ("kind", Data::text("built_in")),
            ("role", Data::text("normal")),
            ("sound", sound),
        ]);
        played(&Instrument::from_data(&instrument).expect("the scenario's instrument is valid"))
    };
    let unmoved = asheville("osc1_pitch", 0);
    let first = asheville("osc1_pitch", amount);
    let second = asheville("osc2_pitch", amount);
    assert!(differs(&unmoved, &first) && differs(&unmoved, &second), "each oscillator's Pitch is heard");
    assert!(differs(&first, &second), "each moves its own oscillator");
}
