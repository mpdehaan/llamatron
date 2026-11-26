// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Every control the Instrument page shows for a built-in synth changes the sound: each part's type is played, a note
//! held and released, and played again with each of its settings moved across its range, the two compared sample for
//! sample, all without a sound card. A setting that changes nothing is a control wired to nothing.

use llamatron_backend::voice::patch::{Patch, Voice};
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
            "basic" => "{ type: basic, oscillators: [{ waveform: saw }, { waveform: pulse, detune: 7 }] }".to_string(),
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
        ("sid", "interval") => &[("modulation", "ring")],
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

/// Every setting of every type of every part: moved across its range, at least two of its values sound different.
#[test]
fn every_synth_control_changes_the_sound() {
    let mut unwired: Vec<String> = Vec::new();
    for (part, types, _) in PART_TYPES {
        for part_type in types.iter() {
            let plain = instrument(&tried_in(part, part_type));
            let settings = TYPE_SETTINGS.iter().find(|(kind, _)| kind == part_type).map_or(&[][..], |(_, names)| *names);
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
        }
    }
    assert!(unwired.is_empty(), "these controls change nothing: {unwired:#?}");
}

/// Two sounds as set files write them, the second differing from the first in one control, and what that control is.
type Trial = (&'static str, &'static str, &'static str);

/// The trials of the controls tried apart from a part's own settings: the SID's arpeggio, the vactrol's memory, the
/// Voice column, the LFOs, the Mod Matrix and the effects.
const TRIALS: &[Trial] = &[
    ("sid arpeggio", "{ engine: sid }", "{ engine: sid, oscillators: { type: sid, arpeggio: [0, 4, 7] } }"),
    ("basic wave", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }] } }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: pulse }] } }"),
    ("basic detune", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }, { waveform: saw }] } }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }, { waveform: saw, detune: 15 }] } }"),
    ("basic level", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }, { waveform: square }] } }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }, { waveform: square, level: 20 }] } }"),
    ("lfo on", "{ engine: basic, matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo shape", "{ engine: basic, lfos: [{ \"on\": true, shape: sine }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, shape: square }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("matrix osc", "{ engine: basic, matrix: [{ source: osc, via: none, destination: pitch, amount: 0 }] }", "{ engine: basic, matrix: [{ source: osc, via: none, destination: pitch, amount: 40 }] }"),
    ("matrix asheville osc", "{ engine: asheville, matrix: [{ source: osc2, via: none, destination: pitch, amount: 0 }] }", "{ engine: asheville, matrix: [{ source: osc2, via: none, destination: pitch, amount: 40 }] }"),
    ("lfo rate", "{ engine: basic, lfos: [{ \"on\": true, rate_percent: 10 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, rate_percent: 90 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo speed", "{ engine: basic, lfos: [{ \"on\": true, speed: low, rate_percent: 50 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, rate_percent: 50 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo key", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, rate_percent: 0, key: false }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, rate_percent: 0, key: true }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo type", "{ engine: basic, lfos: [{ \"on\": true, type: lfo, shape: smooth_random }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, shape: smooth_random }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo smooth random", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, shape: sample_and_hold }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, shape: smooth_random }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo fade in", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, fade_in: 0 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, fade_in: 3000 }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo tempo speed", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, speed: medium }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, speed: tempo }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo division", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, speed: tempo, division: \"1/4\" }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, type: lfo_plus, speed: tempo, division: \"1/16\" }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("lfo ratio", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, key: true, ratio: \"1:1\" }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }", "{ engine: basic, lfos: [{ \"on\": true, speed: very_high, key: true, ratio: \"3:1\" }], matrix: [{ source: lfo1, via: none, destination: pitch, amount: 30 }] }"),
    ("matrix source", "{ engine: basic, matrix: [{ source: env3, via: none, destination: cutoff, amount: 40 }] }", "{ engine: basic, matrix: [{ source: velocity, via: none, destination: cutoff, amount: 40 }] }"),
    ("matrix via", "{ engine: basic, matrix: [{ source: env2, via: none, destination: amp, amount: -40 }] }", "{ engine: basic, matrix: [{ source: env2, via: velocity, destination: amp, amount: -40 }] }"),
    ("matrix destination", "{ engine: basic, matrix: [{ source: env2, via: none, destination: pitch, amount: 40 }] }", "{ engine: basic, matrix: [{ source: env2, via: none, destination: resonance, amount: 40 }] }"),
    ("matrix amount", "{ engine: basic, matrix: [{ source: env2, via: none, destination: pitch, amount: 10 }] }", "{ engine: basic, matrix: [{ source: env2, via: none, destination: pitch, amount: 60 }] }"),
    ("matrix pulse width", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: pulse }] }, lfos: [{ \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pulse_width, amount: 0 }] }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: pulse }] }, lfos: [{ \"on\": true }], matrix: [{ source: lfo1, via: none, destination: pulse_width, amount: 60 }] }"),
    ("matrix detune", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }, { waveform: saw, detune: 10 }] }, matrix: [{ source: env2, via: none, destination: detune, amount: 0 }] }", "{ engine: basic, oscillators: { type: basic, oscillators: [{ waveform: saw }, { waveform: saw, detune: 10 }] }, matrix: [{ source: env2, via: none, destination: detune, amount: 80 }] }"),
    ("effect drive", "{ engine: basic }", "{ engine: basic, effects: [{ effect: drive, curve: hard, amount: 80 }] }"),
    ("effect drive curve", "{ engine: basic, effects: [{ effect: drive, curve: soft, amount: 80 }] }", "{ engine: basic, effects: [{ effect: drive, curve: fold, amount: 80 }] }"),
    ("effect drive mix", "{ engine: basic, effects: [{ effect: drive, curve: hard, amount: 80, mix: 100 }] }", "{ engine: basic, effects: [{ effect: drive, curve: hard, amount: 80, mix: 20 }] }"),
    ("effect bitcrush bits", "{ engine: basic, effects: [{ effect: bitcrush, bits: 16 }] }", "{ engine: basic, effects: [{ effect: bitcrush, bits: 3 }] }"),
    ("effect bitcrush rate", "{ engine: basic, effects: [{ effect: bitcrush, bits: 16, rate: 0 }] }", "{ engine: basic, effects: [{ effect: bitcrush, bits: 16, rate: 4000 }] }"),
];

/// The controls tried apart each change the sound, and the vactrol's memory carries from one note into the next.
#[test]
fn every_control_tried_apart_changes_the_sound() {
    let mut unwired: Vec<&str> = TRIALS
        .iter()
        .filter(|(_, first, second)| !differs(&played(&instrument(first)), &played(&instrument(second))))
        .map(|(control, ..)| *control)
        .collect();
    let remembering = |memory: &str| {
        let sound = format!("{{ engine: basic, envelopes: [{{ type: vactrol, memory: {memory} }}] }}");
        played_notes(&instrument(&sound), &[PITCH, PITCH])
    };
    if !differs(&remembering("0"), &remembering("100")) {
        unwired.push("env1 vactrol memory");
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
