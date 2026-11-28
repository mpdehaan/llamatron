// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The warning when a set opens whose tracks play through instruments that cannot sound on this computer: an instrument
//! playing through FluidSynth where FluidSynth is not installed, and one whose MIDI device this computer does not list,
//! such as a set saved on another computer. Each is told once, in one dialog, as the set opens. Only the instruments some
//! track of some song plays through count, and nothing about the set changes: it keeps every device, so that it plays
//! again where the device is, and the Instrument page can choose another.

use crate::app::App;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::schema::generated::file_format::FLUIDSYNTH_DEVICE;
use llamatron_strings::{errors, named};

/// The names of the instruments some track of some song plays through, in the set's order.
fn instruments_played(setlist: &Setlist) -> Vec<String> {
    let mut played = Vec::new();
    for song in setlist.song_names() {
        let Some(song) = setlist.get_song(song) else { continue };
        for track in song.get_track_names() {
            if let Some(name) = song.get_track(track).and_then(|track| track.get_instrument_name()) {
                played.push(name);
            }
        }
    }
    let instruments = setlist.items(llamatron_model::schema::generated::file_format::Section::INSTRUMENTS);
    instruments.iter().map(|(name, _)| name.clone()).filter(|name| played.contains(name)).collect()
}

/// The dialog's lines: FluidSynth's once, where an instrument played through uses it and it is not installed, then each
/// instrument played through whose device is not connected.
pub fn silent_instrument_lines(setlist: &Setlist, fluidsynth_installed: bool, connected: &[String]) -> Vec<String> {
    let mut lines = Vec::new();
    let played: Vec<(String, &str)> = instruments_played(setlist)
        .into_iter()
        .filter_map(|name| {
            let device = setlist.get_instrument(&name)?.played_device()?;
            Some((name, device))
        })
        .collect();
    if !fluidsynth_installed && played.iter().any(|(_, device)| *device == FLUIDSYNTH_DEVICE) {
        lines.push(errors::ERR_FLUIDSYNTH_WILL_NOT_SOUND.to_string());
    }
    for (name, device) in &played {
        if *device != FLUIDSYNTH_DEVICE && !connected.iter().any(|port| port == device) {
            lines.push(named(
                errors::ERR_DEVICE_WILL_NOT_SOUND,
                &[("instrument", name.as_str().into()), ("device", (*device).into())],
            ));
        }
    }
    lines
}

/// Tell in a dialog which of the open set's instruments will not sound here, if any.
pub fn warn_of_silent_instruments(app: &mut App) {
    let connected = crate::realtime::backend::device_port_names();
    let lines = silent_instrument_lines(app.document.get_setlist(), app.fluidsynth_installed, &connected);
    if !lines.is_empty() {
        app.show_page(Box::new(crate::screens::dialogs::MessageDialog::new(
            errors::ERR_SILENT_INSTRUMENTS_TITLE,
            lines,
        )));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A set's instruments are told where FluidSynth is missing and where a device is not connected, an instrument no
    /// track plays through and a connected device never.
    #[test]
    fn only_instruments_played_through_and_unheard_are_told() {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/silent_instruments.yml");
        let text = std::fs::read_to_string(path).expect("the scenario's set is there");
        let setlist = Setlist::read_text(&text).expect("the scenario's set is valid");
        let connected = vec!["a connected port".to_string()];
        let lines = silent_instrument_lines(&setlist, false, &connected);
        let missing = named(
            errors::ERR_DEVICE_WILL_NOT_SOUND,
            &[("instrument", "away".into()), ("device", "another computer's port".into())],
        );
        assert_eq!(lines, vec![errors::ERR_FLUIDSYNTH_WILL_NOT_SOUND.to_string(), missing]);
        assert_eq!(silent_instrument_lines(&setlist, true, &connected).len(), 1);
    }
}
