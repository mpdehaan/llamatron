// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Every control the Instrument page shows for a built-in synth changes the sound: each part's type is played, a note
//! held and released, and played again with each of its settings moved across its range, the two compared sample for
//! sample, all without a sound card. A setting that changes nothing is a control wired to nothing.

use llamatron_backend::instrument::patch::{Patch, Voice};
use llamatron_model::file::data::{load, Data};
use llamatron_model::objects::setlist::Instrument;
use llamatron_names::file_format;
use llamatron_names::scenario;
use llamatron_names::spec;
use llamatron_tracker::generated::sounds::{SettingKind, MODDED_SETTINGS, PART_TYPES, SETTING_KINDS, TYPE_SETTINGS, TYPE_SETTING_KINDS};
use llamatron_tracker::instrument_sound::Sound;
use support::{built_in, list, settings};

mod support;

/// The sample rate the notes are played at, the note, its velocity, how long it is held and how long it rings after.
const RATE: f64 = 48000.0;
const PITCH: f64 = 45.0;
const VELOCITY: f64 = 0.9;
const HELD_SECONDS: f64 = 0.5;
const RINGING_SECONDS: f64 = 0.5;
const CHUNK: usize = 256;
/// How far a first note runs on into a second, as a glided step's does.
const OVERLAP_SECONDS: f64 = 0.02;
use support::DRUMS_FROM;
/// The data file of the trials of the controls tried apart, beside the tests, and its keys.
const TRIALS_FILE: &str = "tests/data/sounds/synth_trials.yml";
const TRIALS: &str = "trials";
const TRIAL_NAME: &str = "name";
const BEFORE: &str = "before";
const AFTER: &str = "after";
/// The sound each part is tried in, where the part does not replace it: a saw through a Ladder at a cutoff Env2
/// moves, each envelope an ADSR held long enough to hear, and Env3 bending the pitch a little.
const TRIED_ATTACK_MS: i128 = 10;
const TRIED_DECAY_MS: i128 = 200;
const TRIED_SUSTAIN_PERCENT: i128 = 50;
const TRIED_RELEASE_MS: i128 = 200;
const TRIED_CUTOFF_HERTZ: i128 = 1500;
const TRIED_RESONANCE_PERCENT: i128 = 30;
const TRIED_ENV_AMOUNT_PERCENT: i128 = 50;
const TRIED_PITCH_AMOUNT_PERCENT: i128 = 20;
/// The basic oscillator's detune, in cents, so that its tried pulse beats.
const TRIED_DETUNE_CENTS: i128 = 7;
/// How different two playings must be, as a share of the louder's energy, to count as a different sound.
const LEAST_CHANGE: f64 = 1e-6;

/// An instrument playing a sound built as data.
fn instrument(sound: Data) -> Instrument {
    built_in(sound)
}

/// A sound's settings, each a name and a value.
fn sound(pairs: &[(&str, Data)]) -> Data {
    settings(pairs)
}

/// A setting's text value.
fn text(value: &str) -> Data {
    Data::text(value)
}

/// A setting's whole-number value.
fn whole(value: i128) -> Data {
    Data::Whole(value)
}

/// A setting's switch.
fn switch(on: bool) -> Data {
    Data::Bool(on)
}

/// A part of a sound by its type alone.
fn typed(kind: &str) -> Data {
    sound(&[(spec::TYPE, text(kind))])
}

/// A Mod Matrix slot from a source to a destination at an amount in percent, with no via.
fn route(source: &str, destination: &str, amount: i128) -> Data {
    sound(&[
        (spec::SOURCE, text(source)),
        (spec::VIA, text(spec::NONE)),
        (spec::DESTINATION, text(destination)),
        (spec::AMOUNT, whole(amount)),
    ])
}

/// The trials of the controls tried apart, from their data file: each control's name, and a sound before and after.
fn trials() -> Vec<(String, Data, Data)> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(TRIALS_FILE);
    let held = std::fs::read_to_string(&path).expect("the trials' file reads");
    let data = load(&held).expect("the trials' file is YAML");
    let entries = data.get(TRIALS).and_then(Data::as_list).expect("the trials' list");
    entries
        .iter()
        .map(|entry| {
            let name = entry.get(TRIAL_NAME).and_then(Data::as_str).expect("a trial's name").to_string();
            let before = entry.get(BEFORE).cloned().expect("a trial's sound before");
            let after = entry.get(AFTER).cloned().expect("a trial's sound after");
            (name, before, after)
        })
        .collect()
}

/// The instrument with its sound replaced.
fn with_sound(instrument: &Instrument, sound: Data) -> Instrument {
    let mut changed = instrument.clone();
    changed.set_written(file_format::InstrumentSetting::SOUND, Some(sound));
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
fn tried_in(part: &str, part_type: &str) -> Data {
    let oscillators = if part == spec::OSCILLATORS {
        match part_type {
            spec::BASIC => sound(&[
                (spec::TYPE, text(spec::BASIC)),
                (
                    spec::OSCILLATORS,
                    list(vec![sound(&[(spec::WAVEFORM, text(spec::PULSE)), (spec::DETUNE, whole(TRIED_DETUNE_CENTS))])]),
                ),
            ]),
            spec::SID => sound(&[(spec::TYPE, text(spec::SID)), (spec::WAVE, text(spec::PULSE))]),
            other => typed(other),
        }
    } else {
        sound(&[
            (spec::TYPE, text(spec::BASIC)),
            (spec::OSCILLATORS, list(vec![sound(&[(spec::WAVEFORM, text(spec::SAW))])])),
        ])
    };
    let envelope = |place: &str| {
        if part == place {
            typed(part_type)
        } else {
            sound(&[
                (spec::TYPE, text(spec::ADSR)),
                (spec::ATTACK, whole(TRIED_ATTACK_MS)),
                (spec::DECAY, whole(TRIED_DECAY_MS)),
                (spec::SUSTAIN, whole(TRIED_SUSTAIN_PERCENT)),
                (spec::RELEASE, whole(TRIED_RELEASE_MS)),
            ])
        }
    };
    let filter = if part == spec::FILTER {
        sound(&[
            (spec::TYPE, text(part_type)),
            (spec::ENV_AMOUNT, whole(TRIED_ENV_AMOUNT_PERCENT)),
            (spec::KEY_TRACK, whole(0)),
        ])
    } else {
        sound(&[
            (spec::TYPE, text(spec::LADDER)),
            (spec::CUTOFF, whole(TRIED_CUTOFF_HERTZ)),
            (spec::RESONANCE, whole(TRIED_RESONANCE_PERCENT)),
            (spec::ENV_AMOUNT, whole(TRIED_ENV_AMOUNT_PERCENT)),
        ])
    };
    let amp = if part == spec::AMP { typed(part_type) } else { typed(spec::CLEAN) };
    let engine = if part_type == spec::DRUM { spec::DRUM } else { spec::BASIC };
    sound(&[
        (spec::ENGINE, text(engine)),
        (spec::OSCILLATORS, oscillators),
        (spec::ENVELOPES, list(vec![envelope(spec::ENV1), envelope(spec::ENV2), envelope(spec::ENV3)])),
        (spec::FILTER, filter),
        (spec::AMP, amp),
        (spec::MATRIX, list(vec![route(spec::ENV3, spec::PITCH, TRIED_PITCH_AMOUNT_PERCENT)])),
    ])
}

/// The settings a setting only sounds in company of, written first: the second oscillator Interval sets the pitch of,
/// the voice of the chip a shape or a noise belongs to, a sweep or a level that moves, an attack long enough to curve, a
/// sustain that holds into the release, a note soft enough not to accent, and the gate's Lowpass mode or its ping.
fn company(part_type: &str, setting: &str) -> &'static [(&'static str, &'static str)] {
    match (part_type, setting) {
        (file_format::OscillatorType::SID, file_format::PartSetting::INTERVAL) => &[(spec::RING_ON, scenario::TRUE)],
        (file_format::OscillatorType::POCKET, file_format::PartSetting::WAVE_SHAPE) => {
            &[(file_format::PartSetting::CHIP_VOICE, file_format::PartSetting::WAVE)]
        }
        (file_format::OscillatorType::POCKET, file_format::PartSetting::NOISE) => &[(file_format::PartSetting::CHIP_VOICE, file_format::PartSetting::NOISE)],
        (file_format::OscillatorType::POCKET, file_format::PartSetting::SWEEP_STEP)
        | (file_format::OscillatorType::POCKET, file_format::PartSetting::SWEEP_DIRECTION) => &[(file_format::PartSetting::SWEEP_PACE, "3")],
        (file_format::EnvelopeType::CHIP_STEPS, file_format::PartSetting::LEVEL_DIRECTION) => {
            &[(file_format::PartSetting::START_LEVEL, "8"), (file_format::PartSetting::LEVEL_PACE, "3")]
        }
        (file_format::EnvelopeType::ADSR, file_format::PartSetting::ATTACK_CURVE)
        | (file_format::EnvelopeType::AR, file_format::PartSetting::ATTACK_CURVE)
        | (file_format::EnvelopeType::ASR, file_format::PartSetting::ATTACK_CURVE) => &[(file_format::PartSetting::ATTACK, "200")],
        (file_format::EnvelopeType::ADSR, file_format::PartSetting::RELEASE) => &[(file_format::PartSetting::SUSTAIN, "80")],
        (file_format::EnvelopeType::ACID_GATE, file_format::PartSetting::SOFT_ATTACK) => {
            &[(scenario::CIRCUIT, scenario::MODDED), (file_format::PartSetting::ACCENT_THRESHOLD, "127")]
        }
        (file_format::FilterType::LOW_PASS_GATE, file_format::PartSetting::RESONANCE) | (scenario::LOW_PASS_GATE_AMP, file_format::PartSetting::RESONANCE) => {
            &[(file_format::PartSetting::GATE_MODE, file_format::GateMode::LOWPASS)]
        }
        (file_format::FilterType::LOW_PASS_GATE, file_format::PartSetting::PING_TIME) | (scenario::LOW_PASS_GATE_AMP, file_format::PartSetting::PING_TIME) => {
            &[(file_format::PartSetting::SIGNAL, file_format::GateInput::PING)]
        }
        (file_format::EnvelopeType::ACID_GATE, scenario::CIRCUIT) => &[(file_format::PartSetting::AMP_DECAY, "300")],
        (file_format::FilterType::DIODE, scenario::CIRCUIT) => &[(spec::FILTER_FM, "80")],
        (file_format::OscillatorType::ASHEVILLE, spec::OSC1_SHAPE)
        | (file_format::OscillatorType::ASHEVILLE, spec::OSC2_SHAPE)
        | (file_format::OscillatorType::ASHEVILLE, spec::OSC3_SHAPE) => &[(spec::MODEL, spec::CONTINUOUS)],
        (file_format::OscillatorType::ASHEVILLE, spec::FEEDBACK) => &[(spec::FEEDBACK_ON, scenario::TRUE)],
        (file_format::OscillatorType::ASHEVILLE, spec::OSC1_RATE) => &[(spec::OSC1_SPEED, spec::MEDIUM)],
        (file_format::OscillatorType::ASHEVILLE, spec::OSC2_RATE) => &[(spec::OSC2_SPEED, spec::MEDIUM)],
        (file_format::OscillatorType::ASHEVILLE, spec::OSC3_RATE) => &[(spec::OSC3_SPEED, spec::MEDIUM)],
        (file_format::OscillatorType::ASHEVILLE, spec::FEEDBACK_ON) => &[(spec::FEEDBACK, "8")],
        (kind, name) if MODDED_SETTINGS.contains(&(kind, name)) => &[(scenario::CIRCUIT, scenario::MODDED)],
        _ => &[],
    }
}

/// The settings tried apart from the rest: a list typed in, what one note leaves the next, and the drum's knobs, which a
/// hit renders apart.
fn tried_apart(part_type: &str, setting: &str) -> bool {
    matches!(
        (part_type, setting),
        (file_format::OscillatorType::SID, file_format::PartSetting::ARPEGGIO)
            | (file_format::EnvelopeType::VACTROL, file_format::PartSetting::MEMORY)
            | (file_format::FilterType::LOW_PASS_GATE, file_format::PartSetting::MEMORY)
            | (scenario::LOW_PASS_GATE_AMP, file_format::PartSetting::MEMORY)
            | (file_format::TrackSetting::DRUM, _)
    )
}

/// A value as the trial writes it: a switch, a whole number where it reads as one, else text.
fn written(value: &str) -> Data {
    match value {
        scenario::TRUE => Data::Bool(true),
        scenario::FALSE => Data::Bool(false),
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
    let plain = instrument(tried_in(part, part_type));
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

/// The controls tried apart each change the sound, and the vactrol's memory carries from one note into the next.
#[test]
fn every_control_tried_apart_changes_the_sound() {
    // The trials run side by side, one thread a trial, since each plays a note twice.
    let mut unwired: Vec<String> = std::thread::scope(|scope| {
        let running: Vec<_> = trials()
            .into_iter()
            .map(|(control, first, second)| scope.spawn(move || (control, differs(&played(&instrument(first)), &played(&instrument(second))))))
            .collect();
        running
            .into_iter()
            .map(|thread| thread.join().expect("a trial runs to its end"))
            .filter(|(_, changes)| !changes)
            .map(|(control, _)| control)
            .collect()
    });
    let (forgetting, most_memory) = (0, 100);
    let basic = (spec::ENGINE, text(spec::BASIC));
    let remembering = |memory: i128| {
        let vactrol = sound(&[(spec::TYPE, text(spec::VACTROL)), (spec::MEMORY, whole(memory))]);
        played_notes(&instrument(sound(&[basic.clone(), (spec::ENVELOPES, list(vec![vactrol]))])), &[PITCH, PITCH])
    };
    if !differs(&remembering(forgetting), &remembering(most_memory)) {
        unwired.push("env1 vactrol memory".to_string());
    }
    // Restart is heard from the second note on: Each note starts the LFO again with it, On play lets it run on.
    let (slow_rate_percent, vibrato_percent) = (20, 30);
    let restarting = |restart: &str| {
        let lfo = sound(&[
            (spec::ON, switch(true)),
            (spec::RATE_PERCENT, whole(slow_rate_percent)),
            (spec::RESTART, text(restart)),
        ]);
        let routed = route(spec::LFO1, spec::PITCH, vibrato_percent);
        played_notes(
            &instrument(sound(&[basic.clone(), (spec::LFOS, list(vec![lfo])), (spec::MATRIX, list(vec![routed]))])),
            &[PITCH, PITCH],
        )
    };
    if !differs(&restarting(spec::ON_PLAY), &restarting(spec::EACH_NOTE)) {
        unwired.push("lfo restart".to_string());
    }
    // A gate's own cell remembers the note before as the vactrol envelope does, in the Filter's place and the Amp's.
    let gate_remembering = |part: &str, kind: &str, memory: i128| {
        let gate = sound(&[(spec::TYPE, text(kind)), (spec::MEMORY, whole(memory))]);
        played_notes(&instrument(sound(&[basic.clone(), (part, gate)])), &[PITCH, PITCH])
    };
    for (part, kind, control) in [
        (spec::FILTER, spec::LOW_PASS_GATE, "filter low_pass_gate memory"),
        (spec::AMP, scenario::LOW_PASS_GATE_AMP, "amp low_pass_gate_amp memory"),
    ] {
        if !differs(&gate_remembering(part, kind, forgetting), &gate_remembering(part, kind, most_memory)) {
            unwired.push(control.to_string());
        }
    }
    // Oh3's slide is heard where a note overlaps the next a fifth higher, as a glided step does: its Glide time at
    // two ends, and the Glide switch on against off.
    let (quick_glide_ms, slow_glide_ms, a_fifth) = (30, 300, 7.0);
    let sliding = |glide: i128, glides: bool| {
        let acid = sound(&[
            (spec::ENGINE, text(spec::OH3)),
            (spec::GLIDES, switch(glides)),
            (spec::GLIDE, whole(glide)),
            (spec::OSCILLATORS, typed(spec::ACID)),
        ]);
        slid(&instrument(acid), PITCH, PITCH + a_fifth)
    };
    if !differs(&sliding(quick_glide_ms, true), &sliding(slow_glide_ms, true)) {
        unwired.push("voice glide".to_string());
    }
    if !differs(&sliding(slow_glide_ms, true), &sliding(slow_glide_ms, false)) {
        unwired.push("voice glides".to_string());
    }
    // Volume is the engine's, applied to the patch's buffer as it mixes, so it is read from the compiled patch.
    let (loud_percent, quiet_percent) = (80, 20);
    let volume = |percent: i128| {
        let played_sound = Sound::of(&instrument(sound(&[basic.clone(), (spec::VOLUME, whole(percent))])));
        let value = llamatron_tracker::msgpack::value_of(&llamatron_tracker::sound_spec::synth_spec(&played_sound, DRUMS_FROM));
        Patch::compiled(&value, RATE).volume
    };
    if volume(loud_percent) == volume(quiet_percent) {
        unwired.push("voice volume".to_string());
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
    let full_mix = 100;
    let asheville = (spec::ENGINE, text(spec::ASHEVILLE));
    let through = |effect: &str| {
        let block = sound(&[(spec::EFFECT, text(effect)), (spec::MIX, whole(full_mix))]);
        played(&instrument(sound(&[asheville.clone(), (spec::EFFECTS, list(vec![block]))])))
    };
    let dry = played(&instrument(sound(std::slice::from_ref(&asheville))));
    let delayed = through(spec::MULTITAP);
    assert!(
        energy_after(&delayed, after_the_note) > energy_after(&dry, after_the_note),
        "MultiTap's echoes ring on after the note"
    );
    for effect in llamatron_backend::effects::REGISTRY.iter().map(|entry| entry.name) {
        let wet = through(effect);
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
    let (cutoff_cc, other_cc, lowest, highest, amount) = (74, 20, 0.0, 127.0, 80);
    let control = format!("{}{cutoff_cc}", spec::CC);
    let instrument = instrument(sound(&[
        (spec::ENGINE, text(spec::BASIC)),
        (spec::MATRIX, list(vec![route(&control, spec::CUTOFF, amount)])),
    ]));
    let spec = llamatron_tracker::sound_spec::synth_spec(&Sound::of(&instrument), DRUMS_FROM);
    let value = llamatron_tracker::msgpack::value_of(&spec);
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
    let (first_voice, glide_ms) = (1, 60);
    for engine_name in llamatron_model::schema::generated::file_format::SOUND_ENGINES
        .iter()
        .filter(|name| **name != file_format::TrackSetting::DRUM)
    {
        let one_voice_gliding = sound(&[(spec::ENGINE, text(engine_name)), (spec::VOICES, whole(1)), (spec::GLIDE, whole(glide_ms))]);
        let instrument = instrument(one_voice_gliding);
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
    let (eight_foot, quiet_mix) = (spec::RANGE_EIGHT, 10);
    let energy = |waves: &[(&str, Data)]| {
        let mut oscillators = vec![
            (spec::TYPE, text(spec::ASHEVILLE)),
            (spec::OSC1_RANGE, text(eight_foot)),
            (spec::OSC2_RANGE, text(eight_foot)),
            (spec::OSC1_TUNE, whole(0)),
            (spec::OSC2_TUNE, whole(0)),
            (spec::OSC3_ON, switch(false)),
            (spec::DRIFT, whole(0)),
        ];
        oscillators.extend(waves.iter().cloned());
        let played_sound = sound(&[
            (spec::ENGINE, text(spec::ASHEVILLE)),
            (spec::OSCILLATORS, sound(&oscillators)),
            (spec::FILTER, typed(spec::NONE)),
        ]);
        let out = played_notes(&instrument(played_sound), &notes);
        let note = out.len() / notes.len();
        (0..notes.len())
            .map(|n| out[n * note..(n + 1) * note].iter().map(|sample| (*sample as f64).powi(2)).sum::<f64>())
            .collect::<Vec<f64>>()
    };
    let saw_alone = [
        (spec::OSC1_WAVE, text(spec::SAW)),
        (spec::OSC1_MIX, whole(quiet_mix)),
        (spec::OSC2_ON, switch(false)),
    ];
    let saw_and_square = [
        (spec::OSC1_WAVE, text(spec::SAW)),
        (spec::OSC1_MIX, whole(quiet_mix)),
        (spec::OSC2_WAVE, text(spec::SQUARE)),
        (spec::OSC2_MIX, whole(quiet_mix)),
    ];
    let saw = energy(&saw_alone);
    let mixed = energy(&saw_and_square);
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
    let (full_sustain, short_release_ms) = (100, 50);
    let drifting = |drift: i128| {
        let mut oscillators = vec![(spec::TYPE, text(spec::ASHEVILLE)), (spec::DRIFT, whole(drift))];
        for (range, wave, tune) in [
            (spec::OSC1_RANGE, spec::OSC1_WAVE, spec::OSC1_TUNE),
            (spec::OSC2_RANGE, spec::OSC2_WAVE, spec::OSC2_TUNE),
            (spec::OSC3_RANGE, spec::OSC3_WAVE, spec::OSC3_TUNE),
        ] {
            oscillators.extend([(range, text(spec::RANGE_EIGHT)), (wave, text(spec::SAW)), (tune, whole(0))]);
        }
        let held = sound(&[
            (spec::TYPE, text(spec::ADSR)),
            (spec::ATTACK, whole(1)),
            (spec::DECAY, whole(0)),
            (spec::SUSTAIN, whole(full_sustain)),
            (spec::RELEASE, whole(short_release_ms)),
        ]);
        sound(&[
            (spec::ENGINE, text(spec::ASHEVILLE)),
            (spec::OSCILLATORS, sound(&oscillators)),
            (spec::ENVELOPES, list(vec![held, typed(spec::NONE), typed(spec::NONE)])),
            (spec::FILTER, typed(spec::NONE)),
        ])
    };
    let swing = |drift: i128| {
        let levels = window_levels(&played(&instrument(drifting(drift))));
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
        let plain = sound(&[(spec::ENGINE, text(engine))]);
        let first = played(&instrument(plain.clone()));
        assert_eq!(first, played(&instrument(plain)), "{engine} plays the same twice");
        let peak = first.iter().fold(0.0f32, |most, sample| most.max(sample.abs()));
        assert!(peak > 0.0 && peak < headroom, "{engine}: {peak}");
    }
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
        (file_format::ScaleSetting::TYPE, Data::text(snail)),
        (file_format::VactrolCell::SLOW, Data::Whole(weighting.into())),
        (spec::SLOW_SPEED, Data::Whole(seconds.into())),
    ]);
    let sound = settings(&[
        (file_format::SoundSetting::ENGINE, Data::text(engine)),
        (file_format::SoundSetting::LFOS, Data::List(vec![snail_slot])),
        (file_format::SoundSetting::MATRIX, Data::List(routes.to_vec())),
    ]);
    let instrument = settings(&[
        (file_format::FileLayout::NAME, Data::text(scenario::TRIED)),
        (file_format::FileLayout::KIND, Data::text(file_format::TrackSetting::BUILT_IN)),
        (file_format::InstrumentSetting::ROLE, Data::text(file_format::InstrumentRole::NORMAL)),
        (file_format::InstrumentSetting::SOUND, sound),
    ]);
    Instrument::from_data(&instrument).expect("the scenario's instrument is valid")
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
    let heard = route(spec::LFO1_SLOW_Y, file_format::PartSetting::CUTOFF, full);
    let unmoved = slow_path_under_a_note(&snail_instrument(0, std::slice::from_ref(&heard)), control);
    for source in [
        file_format::TrackSetting::VELOCITY.to_string(),
        file_format::SoundPart::ENV1.to_string(),
        format!("cc{control}"),
    ] {
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
    let silent = played(&snail_instrument(centre, &[route(spec::LFO1_SLOW_X, cutoff, 0)]));
    for circuit in [file_format::VactrolCell::SLOW, spec::SLOWER, scenario::SLOWEST] {
        for axis in [scenario::X, scenario::Y, scenario::Z] {
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
    let asheville = |destination: &str, amount: i128| {
        let oscillator = |on: bool| settings(&[(file_format::LfoSetting::ON, Data::Bool(on))]);
        let sound = settings(&[
            (file_format::SoundSetting::ENGINE, Data::text(file_format::OscillatorType::ASHEVILLE)),
            (
                file_format::SoundSetting::OSCILLATORS,
                settings(&[
                    (file_format::ScaleSetting::TYPE, Data::text(file_format::OscillatorType::ASHEVILLE)),
                    (file_format::SoundSetting::OSCILLATORS, Data::List(vec![oscillator(true), oscillator(true)])),
                ]),
            ),
            (
                file_format::SoundSetting::LFOS,
                Data::List(vec![settings(&[(file_format::LfoSetting::ON, Data::Bool(true))])]),
            ),
            (file_format::SoundSetting::MATRIX, Data::List(vec![route(lfo, destination, amount)])),
        ]);
        let instrument = settings(&[
            (file_format::FileLayout::NAME, Data::text(scenario::TRIED)),
            (file_format::FileLayout::KIND, Data::text(file_format::TrackSetting::BUILT_IN)),
            (file_format::InstrumentSetting::ROLE, Data::text(file_format::InstrumentRole::NORMAL)),
            (file_format::InstrumentSetting::SOUND, sound),
        ]);
        played(&Instrument::from_data(&instrument).expect("the scenario's instrument is valid"))
    };
    let unmoved = asheville(spec::OSC1_PITCH, 0);
    let first = asheville(spec::OSC1_PITCH, amount);
    let second = asheville(spec::OSC2_PITCH, amount);
    assert!(differs(&unmoved, &first) && differs(&unmoved, &second), "each oscillator's Pitch is heard");
    assert!(differs(&first, &second), "each moves its own oscillator");
}
