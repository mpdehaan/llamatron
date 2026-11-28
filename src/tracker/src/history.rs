// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Undo and redo (the Python interface/tracker/history.py): the set as each key left it, a step back and forward, and the
//! words for what a step changed.

use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_names::spec;
use llamatron_names::words;
use llamatron_strings::{messages, named};
use std::collections::VecDeque;

/// How many steps back the history keeps.
pub const HISTORY_DEPTH: usize = 100;
const FIRST_SCENE_NUMBER: usize = 1;

/// The set's data and its current song at one moment.
#[derive(Clone, Debug, PartialEq)]
pub struct Snapshot {
    pub data: Data,
    pub song: String,
}

pub struct History {
    now: Snapshot,
    undo: VecDeque<Snapshot>,
    redo: Vec<Snapshot>,
}

/// The sections of a set, in the order a change is looked for in them.
const SETLIST_SECTIONS: [&str; 15] = [
    file_format::Section::SCALES,
    file_format::Section::PATTERNS,
    words::ARPS,
    words::CHORDS,
    words::DRIFTS,
    words::GUITARIFIES,
    words::HOCKETS,
    words::MUSICIANS,
    words::PHRASINGS,
    words::SHAPES,
    words::TIMINGS,
    file_format::Section::CHAINS,
    file_format::Section::GROOVES,
    file_format::Section::INSTRUMENTS,
    file_format::Section::SONGS,
];
const SONG_SECTIONS: [&str; 2] = ["draws", "tracks"];
const SETTINGS_OF_THE_SET: [&str; 9] = [
    file_format::SetlistSetting::TITLE,
    file_format::SetlistSetting::AUTHOR,
    file_format::SetlistSetting::DESCRIPTION,
    file_format::SetlistSetting::NOTES,
    file_format::SetlistSetting::STEP_SIZE,
    file_format::SetlistSetting::DEFAULT_OCTAVE,
    file_format::SetlistSetting::DEFAULT_DRUM_OCTAVE,
    file_format::SetlistSetting::OCTAVE_LABELS,
    file_format::SetlistSetting::PROTECTED,
];
const SETTINGS_OF_A_SONG: [&str; 4] = ["tempo", "time_signature", "scale", "groove"];

impl History {
    pub fn new(now: Snapshot) -> History {
        History {
            now,
            undo: VecDeque::new(),
            redo: Vec::new(),
        }
    }

    /// Note the set as a key left it, a step to undo where it changed.
    pub fn record(&mut self, snapshot: Snapshot) -> bool {
        if snapshot == self.now {
            return false;
        }
        if self.undo.len() == HISTORY_DEPTH {
            self.undo.pop_front();
        }
        self.undo.push_back(std::mem::replace(&mut self.now, snapshot));
        self.redo.clear();
        true
    }

    /// Keep a snapshot as the end of the step before, as each carry of one move does, so that the whole move is one step.
    pub fn record_continuing(&mut self, snapshot: Snapshot) -> bool {
        if snapshot == self.now {
            return false;
        }
        if self.undo.is_empty() {
            return self.record(snapshot);
        }
        // A continued step that ends where it began, as a dialog's choice moved and then put back, is no step at all.
        if self.undo.back() == Some(&snapshot) {
            self.undo.pop_back();
            self.now = snapshot;
            return false;
        }
        self.now = snapshot;
        self.redo.clear();
        true
    }

    pub fn undo(&mut self) -> Option<Snapshot> {
        let before = self.undo.pop_back()?;
        self.redo.push(std::mem::replace(&mut self.now, before));
        Some(self.now.clone())
    }

    pub fn redo(&mut self) -> Option<Snapshot> {
        let after = self.redo.pop()?;
        self.undo.push_back(std::mem::replace(&mut self.now, after));
        Some(self.now.clone())
    }
}

fn changed_word(section: &str) -> String {
    use llamatron_strings::plugin_texts::*;
    let plugin = PLUGINS.iter().find(|plugin| plugin.section == section).map(|plugin| plugin.name);
    let word = match plugin {
        Some(words::ARP) => arp::MSG_CHANGED_WORD,
        Some(words::CHORDS) => chords::MSG_CHANGED_WORD,
        Some(spec::DRIFT) => drift::MSG_CHANGED_WORD,
        Some(words::GUITARIFY) => guitarify::MSG_CHANGED_WORD,
        Some(words::HOCKET) => hocket::MSG_CHANGED_WORD,
        Some(words::MUSICIAN) => musician::MSG_CHANGED_WORD,
        Some(words::PHRASING) => phrasing::MSG_CHANGED_WORD,
        Some(words::SHAPES) => shapes::MSG_CHANGED_WORD,
        Some(words::TIMING) => timing::MSG_CHANGED_WORD,
        _ => return crate::settings::named_in(messages::MSG_CHANGED_WORDS, section),
    };
    word.to_string()
}

fn named_items(data: &Data, section: &str) -> Vec<(String, Data)> {
    match data.get(section) {
        Some(Data::Map(pairs)) => pairs
            .iter()
            .map(|(name, item)| (name.as_str().unwrap_or("").to_string(), item.clone()))
            .collect(),
        _ => Vec::new(),
    }
}

/// The first thing of a section that differs between two sets' data, by its name.
fn differing_name(section: &str, leaving: &Data, arriving: &Data) -> Option<String> {
    let before = named_items(leaving, section);
    let after = named_items(arriving, section);
    let of = |items: &[(String, Data)], name: &str| items.iter().find(|(found, _)| found == name).map(|(_, item)| item.clone());
    before
        .iter()
        .chain(after.iter())
        .map(|(name, _)| name.clone())
        .find(|name| of(&before, name) != of(&after, name))
}

fn song_change(leaving: Option<&Data>, arriving: Option<&Data>) -> String {
    let (Some(leaving), Some(arriving)) = (leaving, arriving) else {
        return crate::settings::named_in(messages::MSG_CHANGED_WORDS, file_format::Section::SONGS);
    };
    for section in SONG_SECTIONS {
        if let Some(name) = differing_name(section, leaving, arriving) {
            return named(
                messages::MSG_CHANGED_NAMED,
                &[(fill::KIND, changed_word(section).as_str().into()), (fill::NAME, name.as_str().into())],
            );
        }
    }
    let scenes = |data: &Data| {
        data.get(file_format::Section::SCENES)
            .and_then(Data::as_list)
            .map(<[Data]>::to_vec)
            .unwrap_or_default()
    };
    let (before, after) = (scenes(leaving), scenes(arriving));
    if before != after {
        let first = before
            .iter()
            .zip(&after)
            .position(|(one, other)| one != other)
            .unwrap_or(before.len().min(after.len()));
        return named(messages::MSG_CHANGED_SCENE, &[(fill::NUMBER, (first + FIRST_SCENE_NUMBER).into())]);
    }
    for setting in SETTINGS_OF_A_SONG {
        if leaving.get(setting) != arriving.get(setting) {
            return crate::settings::named_in(messages::MSG_CHANGED_WORDS, setting);
        }
    }
    crate::settings::named_in(messages::MSG_CHANGED_WORDS, file_format::Section::SONGS)
}

/// The words for what a step of the history changes, from the set it leaves to the set it arrives at.
pub fn describe_change(leaving: &Snapshot, arriving: &Snapshot) -> String {
    for section in SETLIST_SECTIONS {
        let Some(name) = differing_name(section, &leaving.data, &arriving.data) else {
            continue;
        };
        if section == file_format::Section::SONGS {
            let of = |data: &Data| data.get(file_format::Section::SONGS).and_then(|songs| songs.get(&name)).cloned();
            let what = song_change(of(&leaving.data).as_ref(), of(&arriving.data).as_ref());
            return named(
                messages::MSG_CHANGED_IN_SONG,
                &[(fill::SONG, name.as_str().into()), (fill::WHAT, what.as_str().into())],
            );
        }
        return named(
            messages::MSG_CHANGED_NAMED,
            &[(fill::KIND, changed_word(section).as_str().into()), (fill::NAME, name.as_str().into())],
        );
    }
    for setting in SETTINGS_OF_THE_SET {
        if leaving.data.get(setting) != arriving.data.get(setting) {
            return crate::settings::named_in(messages::MSG_CHANGED_WORDS, setting);
        }
    }
    messages::MSG_CHANGED_THE_SET.to_string()
}

/// What a step of the history renamed: the set's named things by section, each its old name and new, and the current song's
/// tracks under "tracks" and scenes by their place, a scene's new name being none where its name was taken away.
#[derive(Clone, Debug, Default)]
pub struct Renames {
    pub named: Vec<(String, String, String)>,
    pub scenes: Vec<(usize, Option<String>)>,
    /// Whether the rename was made on a page just now, which a list's cursor follows, rather than by an undo or redo.
    pub made_here: bool,
}

impl Renames {
    /// The new name of a thing of a section the step renamed, or None.
    pub fn new_name(&self, section: &str, old: &str) -> Option<&str> {
        self.named
            .iter()
            .find(|(found, before, _)| found == section && before == old)
            .map(|(_, _, after)| after.as_str())
    }

    /// Note a rename made here and now, such as an editor's own.
    pub fn one(section: &str, old: &str, new: &str) -> Renames {
        Renames {
            named: vec![(section.to_string(), old.to_string(), new.to_string())],
            scenes: Vec::new(),
            made_here: true,
        }
    }
}

/// The section that holds the current song's tracks, which renamed_items looks at in the song current on arrival.
const TRACKS: &str = "tracks";
const SCENES: &str = "scenes";
const SONGS: &str = "songs";
const SCENE_NAME: &str = "name";

/// What the step between two snapshots renamed (the Python history.py's renamed_items). A rename keeps an item's place and
/// its own data and changes only its name, which tells it from a removal and an addition; the references a rename updates
/// are in other items, so they don't get in the way. A scale named after its root and kind, which the Python also counts as
/// the same scale as they change, waits on that renaming being ported.
pub fn renamed_items(leaving: &Snapshot, arriving: &Snapshot) -> Renames {
    let mut renames = Renames::default();
    for section in SETLIST_SECTIONS {
        add_renames(&mut renames, section, leaving.data.get(section), arriving.data.get(section));
    }
    let song_of = |data: &Data| data.get(SONGS).and_then(|songs| songs.get(&arriving.song)).cloned();
    if let (Some(before), Some(after)) = (song_of(&leaving.data), song_of(&arriving.data)) {
        add_renames(&mut renames, TRACKS, before.get(TRACKS), after.get(TRACKS));
        renames.scenes = renamed_scenes(before.get(SCENES), after.get(SCENES));
    }
    renames
}

/// Add the renames in one named section: the names that differ at the same place with the same data.
fn add_renames(renames: &mut Renames, section: &str, leaving: Option<&Data>, arriving: Option<&Data>) {
    let before = leaving.and_then(Data::as_map).unwrap_or(&[]);
    let after = arriving.and_then(Data::as_map).unwrap_or(&[]);
    if before.len() != after.len() {
        return;
    }
    for ((old, old_item), (new, new_item)) in before.iter().zip(after) {
        if let (Some(old), Some(new)) = (old.as_str(), new.as_str()) {
            if old != new && old_item == new_item {
                renames.named.push((section.to_string(), old.to_string(), new.to_string()));
            }
        }
    }
}

/// The scenes whose name alone changed, by their place, with the new name, which can be none.
fn renamed_scenes(leaving: Option<&Data>, arriving: Option<&Data>) -> Vec<(usize, Option<String>)> {
    let before = leaving.and_then(Data::as_list).unwrap_or(&[]);
    let after = arriving.and_then(Data::as_list).unwrap_or(&[]);
    if before.len() != after.len() {
        return Vec::new();
    }
    let without_name = |scene: &Data| {
        let mut scene = scene.clone();
        scene.remove(SCENE_NAME);
        scene
    };
    let mut found = Vec::new();
    for (place, (old, new)) in before.iter().zip(after).enumerate() {
        if old != new && without_name(old) == without_name(new) {
            found.push((place, new.get(SCENE_NAME).and_then(Data::as_str).map(str::to_string)));
        }
    }
    found
}
