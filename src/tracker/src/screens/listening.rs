// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Listening (the Python screens/shared/listening.py): how the clip page plays one clip again and again, and how the
//! Patterns page and the pattern editor play a pattern through the pattern preview, beside the song, with one key.
//!
//! A clip plays as its scene would, looping until stopped, through its track's instrument; where the track has none, a
//! picker asks which of the set's instruments to play through, for this listening alone. With the set's Real Time switch
//! off, the clip plays through General MIDI in FluidSynth instead.

use crate::app::App;
use crate::realtime::preview::{PatternPreview, Previewing};
use crate::screens::dialogs::{Answer, ChoiceDialog, MessageDialog};
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::{Section, SetlistSetting, TrackSetting};
use llamatron_strings::{errors, messages, named};

/// What a pattern's Listen key does now: listen, or stop the pattern playing.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ListenKey {
    Listen,
    Stop,
}

/// The key that listens to a pattern, or stops it while it is the one playing, or none when nothing could sound: the
/// song names no Preview instrument and FluidSynth is not installed.
pub fn pattern_listen_key(app: &App, pattern: &str) -> Option<ListenKey> {
    if let Some(instrument) = llamatron_model::objects::instrument_previews::preview_instrument(pattern) {
        // An instrument's preview pattern is listened to through its instrument.
        return Some(instrument_listen_key(app, instrument));
    }
    if app.preview.playing_pattern() == Some(pattern) {
        return Some(ListenKey::Stop);
    }
    let sounds = PatternPreview::instrument_of(&app.document, pattern).is_some() || app.fluidsynth_installed;
    sounds.then_some(ListenKey::Listen)
}

/// Play a pattern at once, again and again, beside whatever the song plays, and say the scale it plays in.
pub fn listen_to_pattern(app: &mut App, pattern: &str) {
    if let Some(instrument) = llamatron_model::objects::instrument_previews::preview_instrument(pattern) {
        let instrument = instrument.to_string();
        listen_to_instrument(app, &instrument);
        return;
    }
    if let Some(refusal) = PatternPreview::refusal(&app.document, pattern) {
        app.refuse(&refusal);
        return;
    }
    let started = app.preview.play_pattern(&app.document, pattern);
    if let Err(problem) = started {
        app.show_page(Box::new(MessageDialog::new(errors::ERR_CANT_PLAY_TITLE, vec![problem])));
        return;
    }
    let said = match app.preview.scale() {
        None => named(messages::MSG_LISTENING_TO_PATTERN, &[("name", pattern.into())]),
        Some(scale) => named(messages::MSG_LISTENING_IN_SCALE, &[("name", pattern.into()), ("scale", scale.into())]),
    };
    app.say(&said);
}

/// The key that listens to an instrument's preview pattern through the instrument, or stops it while it plays.
pub fn instrument_listen_key(app: &App, instrument: &str) -> ListenKey {
    if app.preview.playing_instrument() == Some(instrument) {
        ListenKey::Stop
    } else {
        ListenKey::Listen
    }
}

/// Play an instrument's preview pattern through the instrument, again and again until stopped.
pub fn listen_to_instrument(app: &mut App, instrument: &str) {
    if let Some(refusal) = PatternPreview::instrument_refusal(&app.document, instrument) {
        app.refuse(&refusal);
        return;
    }
    if let Err(problem) = app.preview.play_instrument(&app.document, instrument) {
        app.show_page(Box::new(MessageDialog::new(errors::ERR_CANT_PLAY_TITLE, vec![problem])));
        return;
    }
    app.say(&named(messages::MSG_LISTENING_TO_INSTRUMENT, &[("name", instrument.into())]));
}

/// Stop the pattern's preview alone, leaving a song played from Arrange playing.
pub fn stop_listening_to_pattern(app: &mut App) {
    app.preview.stop();
    app.say(messages::MSG_STOPPED);
}

/// Whether a clip plays on its own: through its track's instrument, or through General MIDI while Real Time is off.
pub fn is_listening(app: &App, index: usize, track: &str) -> bool {
    app.transport.is_clip_playing(index, track) || app.preview.playing() == Some(&Previewing::Clip(index, track.to_string()))
}

/// Play one clip of the current song on its own and again and again, asking for an instrument when its track has none.
pub fn listen(app: &mut App, index: usize, track: &str, name: &str) {
    let real_time = matches!(app.document.get_setlist().get_written(SetlistSetting::REAL_TIME), Some(Data::Bool(true)));
    if !real_time && app.fluidsynth_installed {
        match app.preview.play_clip_of_song(&app.document, index, track) {
            Ok(()) => app.say(&named(messages::MSG_LISTENING_GENERAL_MIDI, &[("name", name.into())])),
            Err(problem) => app.show_page(Box::new(MessageDialog::new(errors::ERR_CANT_PLAY_TITLE, vec![problem]))),
        }
        return;
    }
    if let Some(refusal) = app.transport.refusal(app, Some(track)) {
        app.show_page(Box::new(MessageDialog::new(&refusal.title, refusal.lines)));
        return;
    }
    let said = named(messages::MSG_LISTENING, &[("name", name.into()), ("track", track.into())]);
    let what = named(messages::MSG_CLIP_ON_TRACK, &[("name", name.into()), ("track", track.into())]);
    let instrument = app
        .document
        .song()
        .get_track(track)
        .and_then(|held| held.get_written(TrackSetting::INSTRUMENT))
        .and_then(Data::as_str)
        .map(str::to_string);
    let has_device = instrument
        .as_deref()
        .and_then(|name| crate::realtime::transport::instrument(&app.document, name))
        .is_some_and(|held| crate::realtime::transport::device_of(held).is_some() || crate::realtime::transport::is_built_in(held));
    let track = track.to_string();
    if has_device {
        crate::screens::arrange::arrange_page::play_through(app, &what, &said, |app| {
            app.transport.play_clips(&app.document, index, vec![track.clone()], &[], true)
        });
        return;
    }
    let mut choices: Vec<String> = app
        .document
        .get_setlist()
        .items(Section::INSTRUMENTS)
        .iter()
        .map(|(name, _)| name.clone())
        .collect();
    choices.sort_by_key(|name| name.to_lowercase());
    let mut dialog = ChoiceDialog::new(messages::MSG_LISTEN_INSTRUMENT_TITLE, choices.clone(), 0);
    dialog.then = Some(Box::new(move |app: &mut App, answer: &Answer| {
        let Answer::Chosen(place) = answer else { return };
        let Some(chosen) = choices.get(*place).cloned() else { return };
        let instead = vec![(track.clone(), chosen)];
        crate::screens::arrange::arrange_page::play_through(app, &what, &said, |app| {
            app.transport.play_clips(&app.document, index, vec![track.clone()], &instead, true)
        });
    }));
    app.show_page(Box::new(dialog));
}

/// Stop listening: the preview and the clip.
pub fn stop_listening(app: &mut App) {
    app.preview.stop();
    app.transport.stop_all();
    app.say(messages::MSG_STOPPED);
}
