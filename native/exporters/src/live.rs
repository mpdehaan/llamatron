// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A song as an Ableton Live 12 set (the Python exporters/ableton_project.py), in Session View and Arrangement View: each
//! scene and track slot holds its clip, and in Arrangement View the scenes play one after another, each as long as its
//! longest clip. The set is built from a template saved by Live: its first MIDI track, which must hold a clip, is copied for
//! each track of the song with any instruments on it, the other MIDI and audio tracks left out and the return tracks kept.

use crate::xml::{parse, Element};
use llamatron_engine::clip::Clip;
use llamatron_engine::error::{RenderError, Rendered};
use llamatron_engine::realizer::{Grid, GridRow};
use llamatron_engine::timing::timed_events;
use llamatron_math::Rational;
use llamatron_model::values::time_signature::TimeSignature;
use std::io::Read;

/// The template that comes with the program.
pub const DEFAULT_TEMPLATE: &[u8] = include_bytes!("../templates/live12.als");
const EMPTY_CLIP_BEATS: i128 = 4;
const NOTE_OFF_VELOCITY: &str = "64";
const NO_GROOVE: &str = "-1";
const BEFORE_CLIP: &str = "-63072000";
const FIRST_CC_TARGET: i64 = 2;
const LIVE_SIGNATURE_UNIT_STEP: i64 = 99;
const XML_DECLARATION: &str = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";

fn refused<T>(message: &str) -> Rendered<T> {
    Err(RenderError::Refused(message.to_string()))
}

/// A float written as Python's '{:.17g}' writes it.
fn general_17(value: f64) -> String {
    if value == 0.0 {
        return if value.is_sign_negative() { "-0".to_string() } else { "0".to_string() };
    }
    let scientific = format!("{value:.16e}");
    let (digits, exponent) = scientific.split_once('e').unwrap_or((&scientific, "0"));
    let exponent: i32 = exponent.parse().unwrap_or(0);
    if !(-4..17).contains(&exponent) {
        let digits = digits.trim_end_matches('0').trim_end_matches('.');
        let sign = if exponent < 0 { '-' } else { '+' };
        return format!("{digits}e{sign}{:02}", exponent.abs());
    }
    let places = (16 - exponent).max(0) as usize;
    let fixed = format!("{value:.places$}");
    if fixed.contains('.') {
        fixed.trim_end_matches('0').trim_end_matches('.').to_string()
    } else {
        fixed
    }
}

/// A fraction of a whole note as beats, in the way Live writes numbers.
fn beats(whole_notes: Rational) -> String {
    general_17((whole_notes * Rational::whole(4)).to_float())
}

/// A tempo as Python's str writes it: the song's a whole number where it is one, every other a float.
fn tempo_text(tempo: f64, song: bool) -> String {
    if song && tempo.fract() == 0.0 {
        return format!("{}", tempo as i64);
    }
    llamatron_math::number::python_float_text(tempo)
}

fn live_boolean(value: bool) -> &'static str {
    if value {
        "true"
    } else {
        "false"
    }
}

fn set_value(element: &mut Element, path: &str, value: &str) -> Rendered<()> {
    match element.find_mut(path) {
        Some(found) => {
            found.set("Value", value);
            Ok(())
        }
        None => refused(&format!("the Live template has no {path}")),
    }
}

fn live_time_signature(signature: &TimeSignature) -> i64 {
    let doublings = 63 - (signature.get_unit() as u64).leading_zeros() as i64;
    (signature.get_beats() - 1) + LIVE_SIGNATURE_UNIT_STEP * doublings
}

/// A song's grid as a Live set's XML, from a template saved by Live 12.
pub fn live_set(grid: &Grid, template: &[u8]) -> Rendered<Vec<u8>> {
    if grid.rows.is_empty() || grid.columns.is_empty() {
        return refused("a song with no scenes or no tracks cannot be a Live set");
    }
    let mut unzipped = String::new();
    flate2::read::GzDecoder::new(template)
        .read_to_string(&mut unzipped)
        .map_err(|problem| RenderError::Refused(format!("the Live template cannot be read: {problem}")))?;
    let mut root = parse(&unzipped).map_err(|problem| RenderError::Refused(problem.0))?;
    if root.get("MajorVersion") != Some("5") || !root.get("MinorVersion").unwrap_or("").starts_with("12.") {
        return refused("the Live template was not saved by Live 12");
    }
    let Some(live_set) = root.find_mut("LiveSet") else {
        return refused("the Live template has no LiveSet");
    };
    let mut next_shared_id: i64 = live_set
        .find("NextPointeeId")
        .and_then(|found| found.get("Value"))
        .and_then(|value| value.parse().ok())
        .unwrap_or(0);
    let starts = scene_starts(grid)?;
    set_tempo(grid, live_set, &starts)?;
    set_time_signature(grid, live_set)?;
    build_scenes(grid, live_set)?;
    build_tracks(grid, live_set, &mut next_shared_id, &starts)?;
    set_value(live_set, "NextPointeeId", &next_shared_id.to_string())?;
    let mut xml = XML_DECLARATION.to_string();
    root.write(&mut xml);
    Ok(xml.into_bytes())
}

/// The Live set gzipped, as a .als file holds it.
pub fn zipped(xml: &[u8]) -> Vec<u8> {
    use std::io::Write;
    let mut encoder = flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::best());
    encoder.write_all(xml).expect("writing to memory cannot fail");
    encoder.finish().expect("writing to memory cannot fail")
}

fn row_length(row: &GridRow) -> Rendered<Rational> {
    let mut longest = Rational::ZERO;
    for (_, clip) in &row.clips {
        longest = longest.max(clip.total_length()?);
    }
    Ok(longest)
}

/// When each scene starts in Arrangement View, an empty one lasting a bar of four beats.
fn scene_starts(grid: &Grid) -> Rendered<Vec<Rational>> {
    let mut starts = Vec::new();
    let mut now = Rational::ZERO;
    for row in &grid.rows {
        starts.push(now);
        let length = row_length(row)?;
        now = now
            + if length == Rational::ZERO {
                Rational::new(EMPTY_CLIP_BEATS, 4)
            } else {
                length
            };
    }
    Ok(starts)
}

fn tempos_in(grid: &Grid, row: &GridRow) -> Vec<(Rational, String)> {
    let mut tempos = vec![(
        Rational::ZERO,
        match row.tempo {
            Some(tempo) => tempo_text(tempo, false),
            None => tempo_text(grid.tempo, true),
        },
    )];
    tempos.extend(row.tempo_changes.iter().map(|(time, tempo)| (*time, tempo_text(*tempo, false))));
    tempos
}

/// The main track's envelope automating a control, by the control's automation target.
fn envelope_events<'e>(main_track: &'e mut Element, control: &str) -> Rendered<Option<&'e mut Element>> {
    let Some(target) = main_track
        .find(control)
        .and_then(|found| found.find("AutomationTarget"))
        .and_then(|found| found.get("Id"))
        .map(str::to_string)
    else {
        return refused(&format!("the Live template's {control} has no automation target"));
    };
    let Some(envelopes) = main_track.find_mut("AutomationEnvelopes/Envelopes") else {
        return Ok(None);
    };
    Ok(envelopes
        .children
        .iter_mut()
        .find(|envelope| envelope.find("EnvelopeTarget/PointeeId").and_then(|found| found.get("Value")) == Some(target.as_str()))
        .and_then(|envelope| envelope.find_mut("Automation/Events")))
}

fn set_tempo(grid: &Grid, live_set: &mut Element, starts: &[Rational]) -> Rendered<()> {
    let Some(main_track) = live_set.find_mut("MainTrack") else {
        return refused("the Live template has no MainTrack");
    };
    let song_tempo = tempo_text(grid.tempo, true);
    set_value(main_track, "DeviceChain/Mixer/Tempo/Manual", &song_tempo)?;
    let Some(events) = envelope_events(main_track, "DeviceChain/Mixer/Tempo")? else {
        return Ok(());
    };
    for event in &mut events.children {
        event.set("Value", &song_tempo);
    }
    if grid.rows.iter().any(|row| row.tempo.is_some()) {
        let mut next_id = events.children.len();
        for (row, start) in grid.rows.iter().zip(starts) {
            for (time, tempo) in tempos_in(grid, row) {
                events.add(
                    "FloatEvent",
                    &[("Id", &next_id.to_string()), ("Time", &beats(*start + time)), ("Value", &tempo)],
                );
                next_id += 1;
            }
        }
    }
    Ok(())
}

fn set_time_signature(grid: &Grid, live_set: &mut Element) -> Rendered<()> {
    let Some(main_track) = live_set.find_mut("MainTrack") else {
        return refused("the Live template has no MainTrack");
    };
    let code = live_time_signature(&grid.time_signature).to_string();
    set_value(main_track, "DeviceChain/Mixer/TimeSignature/Manual", &code)?;
    if let Some(events) = envelope_events(main_track, "DeviceChain/Mixer/TimeSignature")? {
        for event in &mut events.children {
            event.set("Value", &code);
        }
    }
    Ok(())
}

fn build_scenes(grid: &Grid, live_set: &mut Element) -> Rendered<()> {
    let Some(scenes) = live_set.find_mut("Scenes") else {
        return refused("the Live template has no Scenes");
    };
    let Some(prototype) = scenes.children.first().cloned() else {
        return refused("the Live template has no scene");
    };
    let mut built = Vec::new();
    for (number, row) in grid.rows.iter().enumerate() {
        let mut scene = prototype.clone();
        scene.set("Id", &number.to_string());
        set_value(&mut scene, "Name", &row.name)?;
        let tempo = match row.tempo {
            Some(tempo) => tempo_text(tempo, false),
            None => tempo_text(grid.tempo, true),
        };
        set_value(&mut scene, "Tempo", &tempo)?;
        set_value(&mut scene, "IsTempoEnabled", live_boolean(row.tempo.is_some()))?;
        built.push(scene);
    }
    scenes.children = built;
    Ok(())
}

/// Whether an element is one that needs a set-wide id, a target or a pointee.
fn is_shared(tag: &str) -> bool {
    tag.ends_with("Target")
        || tag.ends_with("Pointee")
        || tag
            .rsplit_once("Targets.")
            .is_some_and(|(_, number)| !number.is_empty() && number.chars().all(|character| character.is_ascii_digit()))
}

fn build_tracks(grid: &Grid, live_set: &mut Element, next_shared_id: &mut i64, starts: &[Rational]) -> Rendered<()> {
    let Some(tracks) = live_set.find_mut("Tracks") else {
        return refused("the Live template has no Tracks");
    };
    let midi_tracks: Vec<Element> = tracks.children.iter().filter(|track| track.tag == "MidiTrack").cloned().collect();
    let Some(prototype) = midi_tracks.first().cloned() else {
        return refused("the Live template has no MIDI track");
    };
    let clip_prototype = {
        let mut found = Vec::new();
        prototype
            .find("DeviceChain/MainSequencer/ClipSlotList")
            .ok_or_else(|| RenderError::Refused("the Live template's track has no clip slots".to_string()))?
            .each(&mut found);
        found
            .into_iter()
            .find(|element| element.tag == "MidiClip")
            .cloned()
            .ok_or_else(|| RenderError::Refused("the Live template's first MIDI track has no clip".to_string()))?
    };
    let colors: Vec<String> = midi_tracks
        .iter()
        .map(|track| track.find("Color").and_then(|color| color.get("Value")).unwrap_or("0").to_string())
        .collect();
    let first_track_id = tracks
        .children
        .iter()
        .filter_map(|track| track.get("Id"))
        .filter_map(|id| id.parse::<i64>().ok())
        .max()
        .unwrap_or(0)
        + 1;
    let mut built = Vec::new();
    for (number, column) in grid.columns.iter().enumerate() {
        let color = &colors[number % colors.len()];
        let mut track = prototype.clone();
        track.set("Id", &(first_track_id + number as i64).to_string());
        track.each_mut(&mut |element| {
            if element.get("Id").is_some() && is_shared(&element.tag) {
                element.set("Id", &next_shared_id.to_string());
                *next_shared_id += 1;
            }
        });
        let effective = if column.name.is_empty() {
            format!("{}-MIDI", number + 1)
        } else {
            column.name.clone()
        };
        set_value(&mut track, "Name/EffectiveName", &effective)?;
        set_value(&mut track, "Name/UserName", &column.name)?;
        set_value(&mut track, "Color", color)?;
        set_value(&mut track, "DeviceChain/Mixer/Speaker/Manual", live_boolean(!column.mute))?;
        let controllers: Vec<(i64, String)> = track
            .find("DeviceChain/MainSequencer/MidiControllers")
            .map(|controllers| {
                controllers
                    .children
                    .iter()
                    .filter_map(|item| Some((item.tag.split('.').nth(1)?.parse::<i64>().ok()? - FIRST_CC_TARGET, item.get("Id")?.to_string())))
                    .collect()
            })
            .unwrap_or_default();
        let clips: Vec<Option<&Clip>> = grid
            .rows
            .iter()
            .map(|row| row.clips.iter().find(|(name, _)| *name == column.name).map(|(_, clip)| clip))
            .collect();
        let Some(slots) = track.find_mut("DeviceChain/MainSequencer/ClipSlotList") else {
            return refused("the Live template's track has no clip slots");
        };
        let Some(mut empty_slot) = slots.children.first().cloned() else {
            return refused("the Live template's track has no clip slot");
        };
        if let Some(value) = empty_slot.find_mut("ClipSlot/Value") {
            value.children.clear();
        }
        let mut built_slots = Vec::new();
        for (place, clip) in clips.iter().enumerate() {
            let mut slot = empty_slot.clone();
            slot.set("Id", &place.to_string());
            if let Some(clip) = clip {
                let element = build_clip(grid, &clip_prototype, clip, place, color, &controllers, None)?;
                if let Some(value) = slot.find_mut("ClipSlot/Value") {
                    value.children.push(element);
                }
            }
            built_slots.push(slot);
        }
        slots.children = built_slots;
        if let Some(frozen) = track.find_mut("DeviceChain/FreezeSequencer/ClipSlotList") {
            frozen.children = (0..grid.rows.len())
                .map(|place| {
                    let mut slot = empty_slot.clone();
                    slot.set("Id", &place.to_string());
                    slot
                })
                .collect();
        }
        let mut arranged = Vec::new();
        for (place, (clip, start)) in clips.iter().zip(starts).enumerate() {
            if let Some(clip) = clip {
                arranged.push(build_clip(grid, &clip_prototype, clip, place, color, &controllers, Some(*start))?);
            }
        }
        if let Some(events) = track.find_mut("DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events") {
            events.children = arranged;
        }
        built.push(track);
    }
    built.extend(tracks.children.iter().filter(|track| track.tag == "ReturnTrack").cloned());
    tracks.children = built;
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn build_clip(
    grid: &Grid,
    prototype: &Element,
    clip: &Clip,
    place: usize,
    color: &str,
    controllers: &[(i64, String)],
    start: Option<Rational>,
) -> Rendered<Element> {
    let (notes, length) = timed_events(clip, clip.scale.as_ref())?;
    let clip_beats = if length > Rational::ZERO {
        beats(length)
    } else {
        EMPTY_CLIP_BEATS.to_string()
    };
    let mut element = prototype.clone();
    element.set("Id", &place.to_string());
    set_value(&mut element, "Name", clip.name.as_deref().unwrap_or(""))?;
    set_value(&mut element, "Color", color)?;
    match start {
        None => {
            element.set("Time", "0");
            set_value(&mut element, "CurrentStart", "0")?;
            set_value(&mut element, "CurrentEnd", &clip_beats)?;
        }
        Some(start) => {
            let end = start
                + if length > Rational::ZERO {
                    length
                } else {
                    Rational::new(EMPTY_CLIP_BEATS, 4)
                };
            element.set("Time", &beats(start));
            set_value(&mut element, "CurrentStart", &beats(start))?;
            set_value(&mut element, "CurrentEnd", &beats(end))?;
            set_value(&mut element, "TakeId", "1")?;
        }
    }
    let loop_settings = [
        ("LoopStart", "0".to_string()),
        ("LoopEnd", clip_beats.clone()),
        ("StartRelative", "0".to_string()),
        ("LoopOn", live_boolean(clip.looping).to_string()),
        ("OutMarker", clip_beats.clone()),
        ("HiddenLoopStart", "0".to_string()),
        ("HiddenLoopEnd", clip_beats.clone()),
    ];
    for (setting, value) in loop_settings {
        set_value(&mut element, &format!("Loop/{setting}"), &value)?;
    }
    set_value(&mut element, "GrooveSettings/GrooveId", NO_GROOVE)?;
    set_value(&mut element, "IsInKey", "false")?;
    let signature = clip.time_signature.unwrap_or(grid.time_signature);
    set_value(
        &mut element,
        "TimeSignature/TimeSignatures/RemoteableTimeSignature/Numerator",
        &signature.get_beats().to_string(),
    )?;
    set_value(
        &mut element,
        "TimeSignature/TimeSignatures/RemoteableTimeSignature/Denominator",
        &signature.get_unit().to_string(),
    )?;
    let Some(notes_element) = element.find_mut("Notes") else {
        return refused("the Live template's clip has no notes");
    };
    write_notes(
        notes_element,
        notes.iter().map(|note| (note.start, note.end, note.midi_number, note.velocity)).collect(),
    )?;
    let Some(envelopes) = element.find_mut("Envelopes/Envelopes") else {
        return refused("the Live template's clip has no envelopes");
    };
    write_envelopes(envelopes, clip, length, controllers);
    Ok(element)
}

fn write_notes(element: &mut Element, mut notes: Vec<(Rational, Rational, i64, i64)>) -> Rendered<()> {
    notes.sort();
    let mut pitches: Vec<i64> = notes.iter().map(|note| note.2).collect();
    pitches.sort();
    pitches.dedup();
    let Some(key_tracks) = element.find_mut("KeyTracks") else {
        return refused("the Live template's notes have no key tracks");
    };
    key_tracks.children.clear();
    let mut note_id = 1;
    for (key_id, pitch) in pitches.iter().enumerate() {
        let key_track = key_tracks.add("KeyTrack", &[("Id", &key_id.to_string())]);
        let events = key_track.add("Notes", &[]);
        for (start, end, _, velocity) in notes.iter().filter(|note| note.2 == *pitch) {
            events.add(
                "MidiNoteEvent",
                &[
                    ("Time", &beats(*start)),
                    ("Duration", &beats(*end - *start)),
                    ("Velocity", &velocity.to_string()),
                    ("OffVelocity", NOTE_OFF_VELOCITY),
                    ("NoteId", &note_id.to_string()),
                ],
            );
            note_id += 1;
        }
        key_track.add("MidiKey", &[("Value", &pitch.to_string())]);
    }
    set_value(element, "NoteIdGenerator/NextId", &note_id.to_string())
}

/// One clip envelope for each CC number the clip sends, its points as Live draws them: a straight line where a value slides,
/// and a value that holds given a second point where the next starts, the first holding from before the clip.
fn write_envelopes(envelopes: &mut Element, clip: &Clip, length: Rational, controllers: &[(i64, String)]) {
    envelopes.children.clear();
    let mut lanes = crate::midi::control_points(clip, length);
    lanes.sort_by_key(|(number, _)| *number);
    for (envelope_id, (number, lane)) in lanes.iter().enumerate() {
        let target = controllers.iter().find(|(found, _)| found == number).map(|(_, id)| id.as_str()).unwrap_or("0");
        let envelope = envelopes.add("ClipEnvelope", &[("Id", &envelope_id.to_string())]);
        envelope.add("EnvelopeTarget", &[]).add("PointeeId", &[("Value", target)]);
        let automation = envelope.add("Automation", &[]);
        let events = automation.add("Events", &[]);
        let mut points = vec![(BEFORE_CLIP.to_string(), lane[0].1)];
        for (place, (time, value, _)) in lane.iter().enumerate() {
            if place > 0 && !lane[place - 1].2 {
                points.push((beats(*time), lane[place - 1].1));
            }
            points.push((beats(*time), *value));
        }
        for (event_id, (time, value)) in points.iter().enumerate() {
            events.add("FloatEvent", &[("Id", &event_id.to_string()), ("Time", time), ("Value", &value.to_string())]);
        }
        let view = automation.add("AutomationTransformViewState", &[]);
        view.add("IsTransformPending", &[("Value", "false")]);
        view.add("TimeAndValueTransforms", &[]);
        envelope.add("LoopSlot", &[]).add("Value", &[]);
        let scroller = envelope.add("ScrollerTimePreserver", &[]);
        scroller.add("LeftTime", &[("Value", "0")]);
        scroller.add("RightTime", &[("Value", "0")]);
    }
}
