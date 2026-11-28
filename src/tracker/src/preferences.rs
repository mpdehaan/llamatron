// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The settings kept for every set rather than in one, in the config file, `~/.llamatron/settings.yml`, which the File/Global
//! page's Global tab shows: today, what a new track's own instrument plays through. A missing or unreadable file means
//! every setting's default, and the file is written, through the model's YAML serializer, only when a setting is changed; a tracker made for a test keeps its
//! settings in memory alone and writes nothing.

use llamatron_model::file::data::{dump, load, Data};
use llamatron_names::file_format;
use llamatron_names::words;
use std::path::{Path, PathBuf};

/// The config file's folder in the home folder, the backend's logs beside it, and the file's name.
const CONFIG_FOLDER: &str = ".llamatron";
const CONFIG_FILE: &str = "settings.yml";
/// The config file's key for Track Inst. Default.
const TRACK_INSTRUMENT_DEFAULT: &str = "track_instrument_default";

/// What a new track's own instrument plays through.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum TrackInstrumentDefault {
    FluidSynth,
    BuiltIn,
    ExternalMidi,
}

impl TrackInstrumentDefault {
    /// Every choice, in the order the picker shows them.
    pub const ALL: [TrackInstrumentDefault; 3] = [
        TrackInstrumentDefault::FluidSynth,
        TrackInstrumentDefault::BuiltIn,
        TrackInstrumentDefault::ExternalMidi,
    ];

    /// The word the config file stores.
    pub fn word(self) -> &'static str {
        match self {
            TrackInstrumentDefault::FluidSynth => words::FLUIDSYNTH,
            TrackInstrumentDefault::BuiltIn => file_format::TrackSetting::BUILT_IN,
            TrackInstrumentDefault::ExternalMidi => words::EXTERNAL_MIDI,
        }
    }

    /// The choice a stored word names.
    pub fn of_word(word: &str) -> Option<TrackInstrumentDefault> {
        TrackInstrumentDefault::ALL.into_iter().find(|choice| choice.word() == word)
    }
}

/// The settings for every set, and where they are kept, if anywhere.
#[derive(Default)]
pub struct Preferences {
    track_instrument_default: Option<TrackInstrumentDefault>,
    path: Option<PathBuf>,
}

impl Preferences {
    /// The config file in the home folder, where there is one.
    pub fn config_path() -> Option<PathBuf> {
        std::env::var_os("HOME").map(|home| PathBuf::from(home).join(CONFIG_FOLDER).join(CONFIG_FILE))
    }

    /// The settings a config file holds, each its default where the file is missing, unreadable or leaves it out.
    pub fn read(path: &Path) -> Preferences {
        let held = std::fs::read_to_string(path).ok().and_then(|written| load(&written).ok());
        let track_instrument_default = held
            .as_ref()
            .and_then(|data| data.get(TRACK_INSTRUMENT_DEFAULT))
            .and_then(Data::as_str)
            .and_then(TrackInstrumentDefault::of_word);
        Preferences {
            track_instrument_default,
            path: Some(path.to_path_buf()),
        }
    }

    /// What a new track's own instrument plays through: the one chosen, or FluidSynth where installed and the built-in
    /// synths where not.
    pub fn track_instrument_default(&self, fluidsynth_installed: bool) -> TrackInstrumentDefault {
        self.track_instrument_default.unwrap_or(if fluidsynth_installed {
            TrackInstrumentDefault::FluidSynth
        } else {
            TrackInstrumentDefault::BuiltIn
        })
    }

    /// Choose what a new track's own instrument plays through, and keep it in the config file, if there is one.
    pub fn set_track_instrument_default(&mut self, chosen: TrackInstrumentDefault) -> Result<(), String> {
        self.track_instrument_default = Some(chosen);
        self.save()
    }

    /// The settings as data, as the config file holds them.
    fn data(&self) -> Data {
        let mut pairs = Vec::new();
        if let Some(chosen) = self.track_instrument_default {
            pairs.push((Data::text(TRACK_INSTRUMENT_DEFAULT), Data::text(chosen.word())));
        }
        Data::Map(pairs)
    }

    /// Write the config file, making its folder, `~/.llamatron`, where it is missing; nothing for settings kept in memory
    /// alone.
    pub fn save(&self) -> Result<(), String> {
        let Some(path) = &self.path else { return Ok(()) };
        if let Some(folder) = path.parent() {
            std::fs::create_dir_all(folder).map_err(|error| format!("{}: {error}", folder.display()))?;
        }
        let written = dump(&self.data()).map_err(|problem| problem.0)?;
        std::fs::write(path, written).map_err(|error| format!("{}: {error}", path.display()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Where the test's config file is written, beside the other tests' working files.
    const WORKING_FOLDER: &str = "/tmp/claude/llamatron/preferences_tests";

    /// Track Inst. Default is FluidSynth where FluidSynth is installed and the built-in synths where not, until chosen;
    /// a choice is written to the config file and read back from it.
    #[test]
    fn track_inst_default_follows_fluidsynth_until_chosen_and_is_kept() {
        let folder = PathBuf::from(WORKING_FOLDER);
        let path = folder.join(CONFIG_FILE);
        let _ = std::fs::remove_file(&path);
        let mut preferences = Preferences::read(&path);
        assert_eq!(preferences.track_instrument_default(true), TrackInstrumentDefault::FluidSynth);
        assert_eq!(preferences.track_instrument_default(false), TrackInstrumentDefault::BuiltIn);
        preferences
            .set_track_instrument_default(TrackInstrumentDefault::ExternalMidi)
            .expect("the config file writes");
        let read_back = Preferences::read(&path);
        assert_eq!(read_back.track_instrument_default(true), TrackInstrumentDefault::ExternalMidi);
        let _ = std::fs::remove_dir_all(&folder);
    }
}
