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
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::schema::generated::file_format::{InstrumentSetting, Section, SongSetting, FLUIDSYNTH_DEVICE};
use llamatron_strings::{errors, named, names};

/// The scene the copy plays, General MIDI's channels the preview takes (the last melodic one, and the drums'), the
/// piano's program, and a channel counted from 1.
const PREVIEW_SCENE: usize = 0;
const PREVIEW_CHANNEL: i64 = 15;
const DRUM_CHANNEL: i64 = 9;
const PIANO_PROGRAM: i64 = 0;
const MIN_GM_SOUND: i64 = 1;
const CHANNEL_OFFSET: i64 = 1;
const ONE_PASS: i64 = 1;
const CLIP_RESTART: &str = "clip_restart";

/// What the preview plays: a pattern of the set, or a clip of the song through General MIDI.
#[derive(Clone, Debug, PartialEq)]
pub enum Previewing {
    Pattern(String),
    Clip(usize, String),
}

/// Plays one pattern again and again beside whatever the song's transport plays.
#[derive(Default)]
pub struct PatternPreview {
    transport: Transport,
    playing: Option<Previewing>,
    scale: Option<String>,
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
        Ok(())
    }

    /// Play a clip of the song as its scene would, again and again, through General MIDI in FluidSynth: the piano, or the
    /// drum kit for drums, as the clip page listens while Real Time is off.
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
        self.transport.follow(&copy, revision, vec![(track, route)])
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
        if name.as_str() != Some(song_name.as_str()) {
            continue;
        }
        let mut track_data = Data::Map(Vec::new());
        if drum {
            track_data.set("drum", Data::Bool(true));
        }
        let mut song_tracks = match song.get("tracks") {
            Some(Data::Map(pairs)) => pairs.clone(),
            _ => Vec::new(),
        };
        song_tracks.push((Data::text(&track), track_data));
        song.set("tracks", Data::Map(song_tracks));
        let mut clip = Data::Map(vec![(Data::text("track"), Data::text(&track)), (Data::text("pattern"), Data::text(pattern))]);
        if passes != ONE_PASS {
            clip.set("repeat", Data::Whole(passes as i128));
        }
        if let Some(scale) = &scale {
            clip.set("scale", Data::text(scale));
        }
        song.set("scenes", Data::List(vec![Data::Map(vec![(Data::text("clips"), Data::List(vec![clip]))])]));
        song.set(SongSetting::LIVE_RESPONSIVENESS, Data::text(CLIP_RESTART));
    }
    data.set(Section::SONGS, Data::Map(songs));
    let copy = Setlist::from_data(&data).map_err(|problem| problem.message)?;
    let mut copy = Document::new(copy, None);
    copy.select_song(&song_name);
    Ok((copy, track, scale))
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
        keyswitches: false,
        sound: None,
        early: 0.0,
    };
    if document.get_setlist().get_pattern(pattern).is_some_and(|held| held.is_drum()) {
        return fluid(DRUM_CHANNEL, None);
    }
    let Some(held) = PatternPreview::instrument_of(document, pattern).and_then(|name| instrument(document, &name).cloned()) else {
        return fluid(PREVIEW_CHANNEL, Some(PIANO_PROGRAM));
    };
    let device = device_of(&held).unwrap_or_default();
    if device == FLUIDSYNTH_DEVICE {
        let sound = held
            .get_written(InstrumentSetting::GM_SOUND)
            .and_then(Data::as_whole)
            .map(|sound| sound as i64 - MIN_GM_SOUND);
        return fluid(PREVIEW_CHANNEL, sound);
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
        keyswitches: false,
        sound: None,
        early: 0.0,
    }
}
