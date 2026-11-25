// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Undo and redo (the Python interface/tracker/history.py): the set as each key left it, a step back and forward, and the
//! words for what a step changed.

use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::plugins::PLUGINS;
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
    "scales",
    "patterns",
    "arps",
    "chords",
    "drifts",
    "guitarifies",
    "hockets",
    "musicians",
    "phrasings",
    "shapes",
    "timings",
    "chains",
    "grooves",
    "instruments",
    "songs",
];
const SONG_SECTIONS: [&str; 2] = ["draws", "tracks"];
const SETTINGS_OF_THE_SET: [&str; 9] = [
    "title",
    "author",
    "description",
    "notes",
    "step_size",
    "default_octave",
    "default_drum_octave",
    "octave_labels",
    "protected",
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
        Some("arp") => arp::MSG_CHANGED_WORD,
        Some("chords") => chords::MSG_CHANGED_WORD,
        Some("drift") => drift::MSG_CHANGED_WORD,
        Some("guitarify") => guitarify::MSG_CHANGED_WORD,
        Some("hocket") => hocket::MSG_CHANGED_WORD,
        Some("musician") => musician::MSG_CHANGED_WORD,
        Some("phrasing") => phrasing::MSG_CHANGED_WORD,
        Some("shapes") => shapes::MSG_CHANGED_WORD,
        Some("timing") => timing::MSG_CHANGED_WORD,
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
        return crate::settings::named_in(messages::MSG_CHANGED_WORDS, "songs");
    };
    for section in SONG_SECTIONS {
        if let Some(name) = differing_name(section, leaving, arriving) {
            return named(
                messages::MSG_CHANGED_NAMED,
                &[("kind", changed_word(section).as_str().into()), ("name", name.as_str().into())],
            );
        }
    }
    let scenes = |data: &Data| data.get("scenes").and_then(Data::as_list).map(<[Data]>::to_vec).unwrap_or_default();
    let (before, after) = (scenes(leaving), scenes(arriving));
    if before != after {
        let first = before
            .iter()
            .zip(&after)
            .position(|(one, other)| one != other)
            .unwrap_or(before.len().min(after.len()));
        return named(messages::MSG_CHANGED_SCENE, &[("number", (first + FIRST_SCENE_NUMBER).into())]);
    }
    for setting in SETTINGS_OF_A_SONG {
        if leaving.get(setting) != arriving.get(setting) {
            return crate::settings::named_in(messages::MSG_CHANGED_WORDS, setting);
        }
    }
    crate::settings::named_in(messages::MSG_CHANGED_WORDS, "songs")
}

/// The words for what a step of the history changes, from the set it leaves to the set it arrives at.
pub fn describe_change(leaving: &Snapshot, arriving: &Snapshot) -> String {
    for section in SETLIST_SECTIONS {
        let Some(name) = differing_name(section, &leaving.data, &arriving.data) else {
            continue;
        };
        if section == "songs" {
            let of = |data: &Data| data.get("songs").and_then(|songs| songs.get(&name)).cloned();
            let what = song_change(of(&leaving.data).as_ref(), of(&arriving.data).as_ref());
            return named(messages::MSG_CHANGED_IN_SONG, &[("song", name.as_str().into()), ("what", what.as_str().into())]);
        }
        return named(
            messages::MSG_CHANGED_NAMED,
            &[("kind", changed_word(section).as_str().into()), ("name", name.as_str().into())],
        );
    }
    for setting in SETTINGS_OF_THE_SET {
        if leaving.data.get(setting) != arriving.data.get(setting) {
            return crate::settings::named_in(messages::MSG_CHANGED_WORDS, setting);
        }
    }
    messages::MSG_CHANGED_THE_SET.to_string()
}
