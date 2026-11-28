// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The pattern preview (the Python interface/tracker/pattern_preview.py): Listen on the Patterns page, in the pattern
//! editor, and on the clip page while Real Time is off. One key plays a pattern at once, again and again, and the same key
//! stops it. The preview has a transport of its own beside the song's, so that it never stops or restarts a song played
//! from Arrange and is heard over it.
//!
//! What it plays is a copy of the set whose current song holds one scene: the pattern's clip, on a track made for it,
//! for as many passes as the pattern's direction takes to come round, in the scale of the first clip that uses the
//! pattern, or the song's. It sounds through the song's Preview instrument, or General MIDI's piano through FluidSynth
//! where the song names none, and a drum pattern through General MIDI's drum kit.

use crate::document::Document;
use crate::realtime::timeline::Route;
use crate::realtime::transport::{device_of, fluidsynth_port, instrument, Transport};
use llamatron_model::file::data::Data;
use llamatron_model::objects::naming::unique_name;
use llamatron_model::objects::setlist::{Instrument, Setlist};
use llamatron_model::schema::generated::file_format::{InstrumentSetting, Section, SongSetting, FLUIDSYNTH_DEVICE};
use llamatron_strings::{errors, named, names};

/// The scene the copy plays, General MIDI's channels the preview takes (the last melodic one, and the drums'), the
/// piano's program, and a channel counted from 1.
const PREVIEW_SCENE: usize = 0;
const PREVIEW_CHANNEL: i64 = 15;
const DRUM_CHANNEL: i64 = 9;
const PIANO_PROGRAM: i64 = 0;
const MIN_GM_SOUND: i64 = 1;
/// The pan CC's value in the middle of the stereo field.
const MIDDLE_PAN: i64 = 64;
const CHANNEL_OFFSET: i64 = 1;
const ONE_PASS: i64 = 1;
const CLIP_RESTART: &str = "clip_restart";

/// A sound is tried once through.
const TRIAL_PASSES: i64 = 1;
/// How loud the notes of a sound's trial are.
const TRIAL_VELOCITY: i128 = 100;
const HALF_STEPS_PER_OCTAVE: i64 = 12;
const SHARP_NAMES: [&str; 12] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const MIDI_KIND: &str = "midi";

/// What the preview plays: a pattern of the set, a clip of the song through General MIDI, an instrument's preview
/// pattern through the instrument, or a sound being tried, by what its picker tells it by.
#[derive(Clone, Debug, PartialEq)]
pub enum Previewing {
    Pattern(String),
    Clip(usize, String),
    Instrument(String),
    Sound(usize),
}

/// A copy of the set whose current song plays one clip, made for a Listen: the copy, its track's name and its scale.
type OneClip = (Document, String, Option<String>);

/// Plays one pattern again and again beside whatever the song's transport plays.
#[derive(Default)]
pub struct PatternPreview {
    transport: Transport,
    playing: Option<Previewing>,
    scale: Option<String>,
    /// The copy of the set a pattern's Listen plays, kept to find the step that sounds.
    pattern_set: Option<Document>,
}

impl PatternPreview {
    /// The instrument a pattern previews through, or None for General MIDI through FluidSynth: the song's Preview
    /// instrument, but for a drum pattern, which always plays General MIDI's drum kit.
    pub fn instrument_of(document: &Document, pattern: &str) -> Option<String> {
        if document.get_setlist().get_pattern(pattern).is_some_and(|held| held.is_drum()) {
            return None;
        }
        document
            .song()
            .get_written(SongSetting::PREVIEW_INSTRUMENT)
            .and_then(Data::as_str)
            .map(str::to_string)
    }

    /// Whether Listen is offered for a pattern: the song names a Preview instrument for it, or FluidSynth is installed.
    pub fn can_sound(document: &Document, pattern: &str) -> bool {
        Self::instrument_of(document, pattern).is_some() || crate::wav::fluidsynth_installed()
    }

    /// Why a pattern's Preview instrument cannot sound, for the status line, or None when it can.
    pub fn refusal(document: &Document, pattern: &str) -> Option<String> {
        let name = Self::instrument_of(document, pattern)?;
        let Some(held) = instrument(document, &name) else {
            return Some(named(errors::ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE, &[("name", name.as_str().into())]));
        };
        let Some(device) = device_of(held) else {
            return Some(named(errors::ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE, &[("name", name.as_str().into())]));
        };
        if device == FLUIDSYNTH_DEVICE {
            return (!crate::wav::fluidsynth_installed()).then(|| named(errors::ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED, &[("name", name.as_str().into())]));
        }
        if !crate::realtime::backend::output_port_names().contains(&device) {
            return Some(named(
                errors::ERR_PREVIEW_DEVICE_NOT_CONNECTED,
                &[("name", name.as_str().into()), ("device", device.as_str().into())],
            ));
        }
        None
    }

    /// What plays now, or None.
    pub fn playing(&self) -> Option<&Previewing> {
        self.playing.as_ref().filter(|_| self.transport.is_playing())
    }

    /// The pattern playing now, or None.
    pub fn playing_pattern(&self) -> Option<&str> {
        match self.playing() {
            Some(Previewing::Pattern(name)) => Some(name),
            _ => None,
        }
    }

    /// The scale the pattern plays in, or None, as a drum pattern has.
    pub fn scale(&self) -> Option<&str> {
        self.scale.as_deref()
    }

    /// Play a pattern at once, again and again, in place of whatever the preview played.
    pub fn play_pattern(&mut self, document: &Document, pattern: &str) -> Result<(), String> {
        self.stop();
        let (copy, track, scale) = pattern_copy(document, pattern)?;
        let route = pattern_route(document, pattern);
        self.transport
            .play_routed(&copy, PREVIEW_SCENE, vec![track.clone()], vec![(track, route)], true)?;
        self.transport.follows_revision(document.get_revision());
        self.playing = Some(Previewing::Pattern(pattern.to_string()));
        self.scale = scale;
        self.pattern_set = Some(copy);
        Ok(())
    }

    /// Play a clip of the song as its scene would, again and again, through General MIDI in FluidSynth: the piano, or the
    /// drum kit for drums, as the clip page listens where no track of the song plays through an instrument that can sound.
    pub fn play_clip_of_song(&mut self, document: &Document, index: usize, track: &str) -> Result<(), String> {
        self.stop();
        let copy = song_copy(document);
        let route = clip_route(document, index, track);
        self.transport
            .play_routed(&copy, index, vec![track.to_string()], vec![(track.to_string(), route)], true)?;
        self.transport.follows_revision(document.get_revision());
        self.playing = Some(Previewing::Clip(index, track.to_string()));
        self.scale = None;
        Ok(())
    }

    /// Why an instrument cannot be listened to, for the status line, or None when it can: it is off, its device is missing
    /// or not connected, or FluidSynth is not installed for it.
    pub fn instrument_refusal(document: &Document, name: &str) -> Option<String> {
        let held = instrument(document, name)?;
        if crate::realtime::transport::is_built_in(held) {
            return None;
        }
        let kind = held.get_written(InstrumentSetting::KIND).and_then(Data::as_str).unwrap_or(MIDI_KIND);
        let Some(device) = device_of(held).filter(|_| kind == MIDI_KIND) else {
            return Some(named(errors::ERR_INSTRUMENT_PLAYS_NOTHING, &[("name", name.into())]));
        };
        if device == FLUIDSYNTH_DEVICE {
            return (!crate::wav::fluidsynth_installed()).then(|| named(errors::ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED, &[("name", name.into())]));
        }
        if !crate::realtime::backend::output_port_names().contains(&device) {
            return Some(named(
                errors::ERR_PREVIEW_DEVICE_NOT_CONNECTED,
                &[("name", name.into()), ("device", device.as_str().into())],
            ));
        }
        None
    }

    /// Play an instrument's preview pattern, or the one it would start with, through the instrument, again and again until
    /// stopped, an edit to the instrument or the pattern heard on the next pass.
    pub fn play_instrument(&mut self, document: &Document, name: &str) -> Result<(), String> {
        self.stop();
        let (copy, track, scale) = instrument_copy(document, name)?;
        let route = instrument_route(&copy, name, &track);
        self.transport
            .play_routed(&copy, PREVIEW_SCENE, vec![track.clone()], vec![(track, route)], true)?;
        self.transport.follows_revision(document.get_revision());
        self.playing = Some(Previewing::Instrument(name.to_string()));
        self.scale = scale;
        Ok(())
    }

    /// The instrument being listened to while it plays, or None.
    pub fn playing_instrument(&self) -> Option<&str> {
        match self.playing() {
            Some(Previewing::Instrument(name)) => Some(name),
            _ => None,
        }
    }

    /// Why a sound cannot be tried, for a picker to say, or None when it can: FluidSynth plays it, or else the song's
    /// Preview instrument does, where it is an instrument on a device of its own that is connected.
    pub fn sound_refusal(document: &Document) -> Option<String> {
        if crate::wav::fluidsynth_installed() {
            return None;
        }
        let Some(name) = document.song().get_written(SongSetting::PREVIEW_INSTRUMENT).and_then(Data::as_str) else {
            return Some(errors::ERR_NOTHING_TO_TRY_A_SOUND_WITH.to_string());
        };
        let Some(device) = instrument(document, name).and_then(device_of) else {
            return Some(named(errors::ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE, &[("name", name.into())]));
        };
        if device == FLUIDSYNTH_DEVICE {
            return Some(named(errors::ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED, &[("name", name.into())]));
        }
        if !crate::realtime::backend::output_port_names().contains(&device) {
            return Some(named(
                errors::ERR_PREVIEW_DEVICE_NOT_CONNECTED,
                &[("name", name.into()), ("device", device.as_str().into())],
            ));
        }
        None
    }

    /// Try a sound: play some MIDI notes once, a step each, through General MIDI in FluidSynth, in a General MIDI sound, or
    /// on the drum kit where sound is None; without FluidSynth, on the song's Preview instrument, in the device's own sound.
    /// key is whatever the picker tells one trial from another by, answered by playing_sound.
    pub fn play_sound(&mut self, document: &Document, numbers: &[i64], step_size: &str, sound: Option<i64>, key: usize) -> Result<(), String> {
        self.stop();
        let (copy, track, _) = one_clip_copy(document, &trial_pattern(numbers, step_size), TRIAL_PASSES, None)?;
        let route = sound_route(document, sound);
        self.transport
            .play_routed(&copy, PREVIEW_SCENE, vec![track.clone()], vec![(track, route)], false)?;
        self.transport.follows_revision(document.get_revision());
        self.playing = Some(Previewing::Sound(key));
        self.scale = None;
        Ok(())
    }

    /// The key of the sound being tried while its notes play, or None.
    pub fn playing_sound(&self) -> Option<usize> {
        match self.playing() {
            Some(Previewing::Sound(key)) => Some(*key),
            _ => None,
        }
    }

    /// Stop what the preview plays.
    pub fn stop(&mut self) {
        self.transport.stop_all();
        self.playing = None;
    }

    /// Hear an edit to the set made while the preview plays, once it has settled, by playing a copy made afresh; and plan
    /// ahead. What the status line says of an edit that cannot be heard, if anything.
    pub fn tick(&mut self, document: &Document) -> Option<String> {
        let revision = document.get_revision();
        let mut said = None;
        if self.transport.is_playing() && self.transport.edit_settled(revision) {
            said = match self.playing.clone() {
                Some(Previewing::Pattern(pattern)) => self.follow_pattern(document, &pattern, revision),
                Some(Previewing::Instrument(name)) => match instrument_copy(document, &name) {
                    Ok((copy, track, _)) => {
                        let route = instrument_route(&copy, &name, &track);
                        self.transport.follow(&copy, revision, vec![(track, route)])
                    }
                    Err(_) => {
                        self.stop();
                        None
                    }
                },
                // A sound's trial plays once, as it was asked for.
                Some(Previewing::Sound(_)) => None,
                Some(Previewing::Clip(index, track)) => {
                    let copy = song_copy(document);
                    let route = clip_route(document, index, &track);
                    self.transport.follow(&copy, revision, vec![(track, route)])
                }
                None => None,
            };
        }
        self.transport.plan_ahead();
        said
    }

    /// Hear the pattern as an edit left it, or stop where the edit took it away.
    fn follow_pattern(&mut self, document: &Document, pattern: &str, revision: u64) -> Option<String> {
        let Ok((copy, track, scale)) = pattern_copy(document, pattern) else {
            self.stop();
            return None;
        };
        self.scale = scale;
        let route = pattern_route(document, pattern);
        let said = self.transport.follow(&copy, revision, vec![(track, route)]);
        self.pattern_set = Some(copy);
        said
    }

    /// The step of a pattern that sounds in what the preview plays, for the pattern editor's read head: in a pattern's
    /// Listen or a clip's, or None.
    pub fn playing_step(&self, document: &Document, pattern: &str) -> Option<usize> {
        match self.playing()? {
            Previewing::Pattern(name) if name == pattern => self.pattern_set.as_ref().and_then(|copy| self.transport.playing_step(copy, pattern)),
            Previewing::Clip(..) => self.transport.playing_step(document, pattern),
            _ => None,
        }
    }

    pub fn is_playing(&self) -> bool {
        self.transport.is_playing()
    }

    /// Stop and end the preview's sender, as the tracker quits.
    pub fn close(&mut self) {
        self.transport.close();
        self.playing = None;
    }
}

/// A copy of the set, its current song the document's.
fn song_copy(document: &Document) -> Document {
    let mut copy = Document::new(document.get_setlist().clone(), None);
    copy.select_song(document.get_current_song_name());
    copy
}

/// A copy of the set whose current song holds one scene, the pattern's clip on a track made for it, for as many passes
/// as its direction takes to come round, in the scale of the first clip that uses it or the song's; with the track's name
/// and the scale.
fn pattern_copy(document: &Document, pattern: &str) -> Result<(Document, String, Option<String>), String> {
    let setlist = document.get_setlist();
    let song_name = document.get_current_song_name().to_string();
    let held = setlist.get_pattern(pattern).ok_or_else(|| pattern.to_string())?;
    let drum = held.is_drum();
    let scales = if drum {
        Vec::new()
    } else {
        crate::patterns::scales_of_pattern(setlist, document.song(), pattern)
    };
    let scale = scales.first().cloned();
    let direction = held.get_written("direction").and_then(Data::as_str).unwrap_or("forward").to_string();
    let passes = passes_to_come_round(held.get_steps() as usize, &direction);
    let tracks: Vec<&str> = document.song().get_track_names();
    let track = unique_name(names::MSG_PREVIEW_TRACK_NAME, &tracks);
    let mut data = setlist.to_data();
    let Some(Data::Map(mut songs)) = data.get(Section::SONGS).cloned() else {
        return Err(song_name);
    };
    for (name, song) in &mut songs {
        if name.as_str() == Some(song_name.as_str()) {
            one_clip_song(song, &track, None, drum, pattern, passes, scale.as_deref());
        }
    }
    data.set(Section::SONGS, Data::Map(songs));
    let copy = Setlist::from_data(&data).map_err(|problem| problem.message)?;
    let mut copy = Document::new(copy, None);
    copy.select_song(&song_name);
    Ok((copy, track, scale))
}

/// A copy of the set that plays an instrument's preview pattern, or the one it would start with, on a track of its own
/// through the instrument: a drum pattern under no scale, any other under the hidden chromatic scale on C.
fn instrument_copy(document: &Document, name: &str) -> Result<OneClip, String> {
    let held = instrument(document, name).ok_or_else(|| name.to_string())?;
    let pattern = match held.get_preview() {
        Some(preview) => preview.to_data(),
        None => {
            let sound = crate::instrument_sound::Sound::of(held);
            let drum = crate::realtime::transport::is_built_in(held) && sound.part_type("oscillators") == "drum";
            llamatron_model::objects::instrument_previews::starting_preview(drum)
        }
    };
    one_clip_copy(document, &pattern, TRIAL_PASSES, Some(name))
}

/// A copy of the set whose current song holds one scene, a pattern's data played for so many passes on a track made for
/// it: the pattern added under a name of its own, a drum pattern under no scale and any other under a copy of the hidden
/// chromatic scale on C; an edit heard at the pattern's next pass.
fn one_clip_copy(document: &Document, pattern: &Data, passes: i64, instrument: Option<&str>) -> Result<OneClip, String> {
    let setlist = document.get_setlist();
    let song_name = document.get_current_song_name().to_string();
    let drum = matches!(pattern.get("drum"), Some(Data::Bool(true)));
    let patterns: Vec<&str> = setlist.items(Section::PATTERNS).iter().map(|(name, _)| name.as_str()).collect();
    let pattern_name = unique_name(names::MSG_PREVIEW_PATTERN_NAME, &patterns);
    let mut data = setlist.to_data();
    let mut held = data.get(Section::PATTERNS).cloned().unwrap_or(Data::Map(Vec::new()));
    if let Data::Map(pairs) = &mut held {
        pairs.push((Data::text(&pattern_name), pattern.clone()));
    }
    data.set(Section::PATTERNS, held);
    let mut scale = None;
    if !drum {
        let scales: Vec<&str> = setlist.items(Section::SCALES).iter().map(|(name, _)| name.as_str()).collect();
        let name = unique_name(names::MSG_PREVIEW_SCALE_NAME, &scales);
        let mut held = data.get(Section::SCALES).cloned().unwrap_or(Data::Map(Vec::new()));
        if let Data::Map(pairs) = &mut held {
            pairs.push((Data::text(&name), llamatron_model::objects::instrument_previews::preview_scale().to_data()));
        }
        data.set(Section::SCALES, held);
        scale = Some(name);
    }
    let tracks: Vec<&str> = document.song().get_track_names();
    let track = unique_name(names::MSG_PREVIEW_TRACK_NAME, &tracks);
    let Some(Data::Map(mut songs)) = data.get(Section::SONGS).cloned() else {
        return Err(song_name);
    };
    for (name, song) in &mut songs {
        if name.as_str() == Some(song_name.as_str()) {
            one_clip_song(song, &track, instrument, drum, &pattern_name, passes, scale.as_deref());
        }
    }
    data.set(Section::SONGS, Data::Map(songs));
    let copy = Setlist::from_data(&data).map_err(|problem| problem.message)?;
    let mut copy = Document::new(copy, None);
    copy.select_song(&song_name);
    Ok((copy, track, scale))
}

/// Make a song's data hold one scene, a pattern's clip on a new track, through an instrument where one is named, for so
/// many passes in a scale, an edit heard at the clip's restart.
fn one_clip_song(song: &mut Data, track: &str, instrument: Option<&str>, drum: bool, pattern: &str, passes: i64, scale: Option<&str>) {
    let mut track_data = Data::Map(Vec::new());
    if let Some(instrument) = instrument {
        track_data.set("instrument", Data::text(instrument));
    }
    if drum {
        track_data.set("drum", Data::Bool(true));
    }
    let mut song_tracks = match song.get("tracks") {
        Some(Data::Map(pairs)) => pairs.clone(),
        _ => Vec::new(),
    };
    song_tracks.push((Data::text(track), track_data));
    song.set("tracks", Data::Map(song_tracks));
    let mut clip = Data::Map(vec![(Data::text("pattern"), Data::text(pattern))]);
    if passes != ONE_PASS {
        clip.set("repeat", Data::Whole(passes as i128));
    }
    if let Some(scale) = scale {
        clip.set("scale", Data::text(scale));
    }
    // A scene's data holds its clips by their tracks' names, as the set's data does, not the file's list of clips.
    let clips = Data::Map(vec![(Data::text(track), clip)]);
    song.set("scenes", Data::List(vec![Data::Map(vec![(Data::text("tracks"), clips)])]));
    song.set(SongSetting::LIVE_RESPONSIVENESS, Data::text(CLIP_RESTART));
}

/// The data of a pattern that plays some MIDI notes one after another, a step each, written as a drum pattern's notes
/// are, by name and octave, so that no scale moves them.
fn trial_pattern(numbers: &[i64], step_size: &str) -> Data {
    let names: Vec<&str> = numbers
        .iter()
        .map(|number| SHARP_NAMES[number.rem_euclid(HALF_STEPS_PER_OCTAVE) as usize])
        .collect();
    let mut data = Data::Map(Vec::new());
    data.set("steps", Data::Whole(numbers.len() as i128));
    data.set("step_size", Data::text(step_size));
    data.set("drum", Data::Bool(true));
    data.set("degree", Data::List(names.iter().map(|name| Data::text(&name[..1])).collect()));
    data.set(
        "accidental",
        Data::List(
            names
                .iter()
                .map(|name| if name.len() > 1 { Data::text(&name[1..]) } else { Data::Null })
                .collect(),
        ),
    );
    data.set(
        "octave",
        Data::List(
            numbers
                .iter()
                .map(|number| Data::Whole(number.div_euclid(HALF_STEPS_PER_OCTAVE) as i128))
                .collect(),
        ),
    );
    data.set("velocity", Data::List(numbers.iter().map(|_| Data::Whole(TRIAL_VELOCITY)).collect()));
    data
}

/// The route an instrument is listened to through: its built-in port, FluidSynth in its sound on the preview's channel,
/// so that the song's own tracks keep theirs, or its device and channel.
fn instrument_route(copy: &Document, name: &str, track: &str) -> Route {
    let held = instrument(copy, name);
    if held.is_some_and(crate::realtime::transport::is_built_in) {
        let routes = crate::realtime::transport::routes(copy, &[(track.to_string(), name.to_string())]);
        if let Some((_, route)) = routes.into_iter().find(|(found, _)| found == track) {
            return route;
        }
    }
    let device = held.and_then(device_of).unwrap_or_default();
    if device == FLUIDSYNTH_DEVICE {
        let sound = held
            .and_then(|held| held.get_written(InstrumentSetting::GM_SOUND))
            .and_then(Data::as_whole)
            .map(|sound| sound as i64 - MIN_GM_SOUND);
        // The preview's channel is shared by every preview, so the pan in effect is always sent, the middle included.
        let pan = held.map(Instrument::pan_control_in_effect);
        return Route {
            pan,
            ..fluid_route(PREVIEW_CHANNEL, sound)
        };
    }
    device_route(
        device,
        held.and_then(|held| held.get_written(InstrumentSetting::CHANNEL)).and_then(Data::as_whole),
    )
}

/// The route a sound is tried through: FluidSynth's drum kit, or a General MIDI sound on the preview's channel, or without
/// FluidSynth the song's Preview instrument's device and channel.
fn sound_route(document: &Document, sound: Option<i64>) -> Route {
    if !crate::wav::fluidsynth_installed() {
        let held = document
            .song()
            .get_written(SongSetting::PREVIEW_INSTRUMENT)
            .and_then(Data::as_str)
            .and_then(|name| instrument(document, name));
        let device = held.and_then(device_of).unwrap_or_default();
        return device_route(
            device,
            held.and_then(|held| held.get_written(InstrumentSetting::CHANNEL)).and_then(Data::as_whole),
        );
    }
    match sound {
        None => fluid_route(DRUM_CHANNEL, None),
        Some(sound) => fluid_route(PREVIEW_CHANNEL, Some(sound - MIN_GM_SOUND)),
    }
}

/// A route to FluidSynth on a channel, choosing a program or none.
fn fluid_route(channel: i64, program: Option<i64>) -> Route {
    Route {
        port: fluidsynth_port(),
        channel,
        program,
        pan: middle_on_the_preview_channel(channel),
        keyswitches: false,
        sound: None,
        early: 0.0,
    }
}

/// A route to a MIDI device on a channel counted from 1, the first where none is written.
fn device_route(device: String, channel: Option<i128>) -> Route {
    Route {
        port: device,
        channel: channel.map_or(1, |channel| channel as i64) - CHANNEL_OFFSET,
        program: None,
        pan: None,
        keyswitches: true,
        sound: None,
        early: 0.0,
    }
}

/// How many passes of a pattern a direction takes to come back to where it started.
fn passes_to_come_round(steps: usize, direction: &str) -> i64 {
    let Some(order) = llamatron_engine::order::walk_order(steps, direction) else {
        return ONE_PASS;
    };
    if steps == 0 {
        return ONE_PASS;
    }
    let (mut a, mut b) = (order.len(), steps);
    while b != 0 {
        (a, b) = (b, a % b);
    }
    // lcm(passes, steps) / steps, the passes the order's length takes to line up with the pattern's steps again.
    (order.len() / a) as i64
}

/// The route a pattern previews through: General MIDI's drum kit for a drum pattern, the piano without a Preview
/// instrument, else the Preview instrument's sound in FluidSynth or its device and channel.
fn pattern_route(document: &Document, pattern: &str) -> Route {
    let fluid = |channel: i64, program: Option<i64>| Route {
        port: fluidsynth_port(),
        channel,
        program,
        pan: middle_on_the_preview_channel(channel),
        keyswitches: false,
        sound: None,
        early: 0.0,
    };
    if document.get_setlist().get_pattern(pattern).is_some_and(|held| held.is_drum()) {
        return fluid(DRUM_CHANNEL, None);
    }
    let Some(name) = PatternPreview::instrument_of(document, pattern) else {
        return fluid(PREVIEW_CHANNEL, Some(PIANO_PROGRAM));
    };
    let Some(held) = instrument(document, &name).cloned() else {
        return fluid(PREVIEW_CHANNEL, Some(PIANO_PROGRAM));
    };
    // A built-in instrument has no device: it plays on a built-in port, the only one the preview uses.
    if crate::realtime::transport::is_built_in(&held) {
        return crate::realtime::transport::built_in_route(&name, 0);
    }
    let device = device_of(&held).unwrap_or_default();
    if device == FLUIDSYNTH_DEVICE {
        let sound = held
            .get_written(InstrumentSetting::GM_SOUND)
            .and_then(Data::as_whole)
            .map(|sound| sound as i64 - MIN_GM_SOUND);
        return Route {
            pan: Some(held.pan_control_in_effect()),
            ..fluid(PREVIEW_CHANNEL, sound)
        };
    }
    let channel = held
        .get_written(InstrumentSetting::CHANNEL)
        .and_then(Data::as_whole)
        .map_or(1, |channel| channel as i64)
        - CHANNEL_OFFSET;
    Route {
        port: device,
        channel,
        program: None,
        pan: None,
        keyswitches: true,
        sound: None,
        early: 0.0,
    }
}

/// The route a clip of the song plays through while Real Time is off: General MIDI's drum kit for a drum track or a drum
/// pattern, the piano otherwise.
fn clip_route(document: &Document, index: usize, track: &str) -> Route {
    let song = document.song();
    let drum_track = song.get_track(track).is_some_and(|held| held.is_drum());
    let drum_pattern = song
        .scenes()
        .get(index)
        .and_then(|scene| scene.get_clip_slot(track))
        .and_then(|clip| document.get_setlist().get_pattern(&clip.get_pattern_name()))
        .is_some_and(|held| held.is_drum());
    let (channel, program) = if drum_track || drum_pattern {
        (DRUM_CHANNEL, None)
    } else {
        (PREVIEW_CHANNEL, Some(PIANO_PROGRAM))
    };
    Route {
        port: fluidsynth_port(),
        channel,
        program,
        pan: middle_on_the_preview_channel(channel),
        keyswitches: false,
        sound: None,
        early: 0.0,
    }
}

/// The pan CC's middle, sent on the preview's channel so that a sound tried after a panned instrument stands in the
/// middle again; None on any other channel, which no instrument's pan reaches.
fn middle_on_the_preview_channel(channel: i64) -> Option<i64> {
    (channel == PREVIEW_CHANNEL).then_some(MIDDLE_PAN)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A song whose Preview instrument is a built-in synth, and a pattern to listen to.
    const BUILT_IN_PREVIEW_SET: &str = include_str!("../../tests/data/built_in_preview_set.yml");

    /// Listening to an instrument plays its preview pattern: the copy's one scene holds the preview's clip.
    #[test]
    fn an_instrument_preview_holds_its_clip() {
        use crate::preferences::TrackInstrumentDefault;
        let synth = |drum: bool| crate::track_instrument::new_track_instrument(TrackInstrumentDefault::BuiltIn, drum, false, None);
        let document = Document::new_set(synth(false), synth(true)).expect("a new set");
        let fish = "main1";
        let (copy, track, _) = instrument_copy(&document, fish).expect("the instrument is in the set");
        let scene = &copy.song().scenes()[PREVIEW_SCENE];
        assert!(scene.get_clip_slot(&track).is_some());
    }

    /// Listening to a pattern plays it: the copy's one scene holds the pattern's clip.
    #[test]
    fn a_pattern_preview_holds_its_clip() {
        let setlist = llamatron_model::objects::setlist::Setlist::read_text(BUILT_IN_PREVIEW_SET).expect("the scenario's set is valid");
        let document = Document::new(setlist, None);
        let (copy, track, _) = pattern_copy(&document, "tune").expect("the pattern is in the set");
        let scene = &copy.song().scenes()[PREVIEW_SCENE];
        assert!(scene.get_clip_slot(&track).is_some());
    }

    /// Listening to a pattern through a built-in Preview instrument plays that synth, not a port with no name.
    #[test]
    fn a_pattern_listens_through_a_built_in_preview_instrument() {
        let setlist = llamatron_model::objects::setlist::Setlist::read_text(BUILT_IN_PREVIEW_SET).expect("the scenario's set is valid");
        let document = Document::new(setlist, None);
        let route = pattern_route(&document, "tune");
        assert_eq!(route.sound.as_deref(), Some("lead synth"));
        assert!(!route.port.is_empty());
    }
}
