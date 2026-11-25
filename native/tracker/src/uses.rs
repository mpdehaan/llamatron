// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What uses a named item of the set (the Python model's names_item queries and pages/uses.py): the songs, scenes and tracks
//! that chose it, the clips that play or run it and the chains that run it, each put into words for a page.

use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::{Item, Setlist};
use llamatron_model::objects::song::{ClipSlot, Scene, Song, Track};
use llamatron_model::schema::generated::defaults;
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, SceneSetting, Section, SongSetting, TrackSetting};
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_strings::{messages, named, names};

/// The settings each kind of object names an item of a section by (the Python classes' REFERENCES).
const SONG_REFERENCES: &[(&str, &[&str])] = &[
    (Section::SCALES, &[SongSetting::SCALE]),
    (Section::GROOVES, &[SongSetting::GROOVE]),
    (Section::INSTRUMENTS, &[SongSetting::PREVIEW_INSTRUMENT]),
];
const SCENE_REFERENCES: &[(&str, &[&str])] = &[(Section::SCALES, &[SceneSetting::SCALE]), (Section::GROOVES, &[SceneSetting::GROOVE])];
const TRACK_REFERENCES: &[(&str, &[&str])] = &[(Section::GROOVES, &[TrackSetting::GROOVE]), (Section::INSTRUMENTS, &[TrackSetting::INSTRUMENT])];
const CLIP_REFERENCES: &[(&str, &[&str])] = &[
    (Section::PATTERNS, &[ClipSlotSetting::PATTERNS, ClipSlotSetting::MORPH_TO]),
    (Section::TRACKS, &[ClipSlotSetting::GRAB_TRACK]),
    (Section::SCALES, &[ClipSlotSetting::SCALE]),
];

/// Whether a section holds generators, which a list of chains names, chains among them.
fn is_generator_section(section: &str) -> bool {
    section == Section::CHAINS || PLUGINS.iter().any(|plugin| plugin.section == section)
}

/// Whether a setting's value names a name: a list holding it, or the name itself.
fn names(value: Option<&Data>, name: &str) -> bool {
    match value {
        Some(Data::List(items)) => items.iter().any(|item| item.as_str() == Some(name)),
        Some(Data::Text(text)) => text == name,
        _ => false,
    }
}

/// Whether an object names an item by its references, and by its list of chains where it has one.
fn names_item(get: &dyn Fn(&str) -> Option<Data>, references: &[(&str, &[&str])], chains: Option<&str>, section: &str, name: &str) -> bool {
    let by_reference = references
        .iter()
        .filter(|(found, _)| *found == section)
        .flat_map(|(_, settings)| settings.iter())
        .any(|setting| names(get(setting).as_ref(), name));
    by_reference || chains.is_some_and(|setting| is_generator_section(section) && names(get(setting).as_ref(), name))
}

fn song_names(song: &Song, section: &str, name: &str) -> bool {
    if section == Section::GROOVES {
        let groove = song.get_written(SongSetting::GROOVE).and_then(Data::as_str).unwrap_or(defaults::DEFAULT_GROOVE);
        return groove == name;
    }
    names_item(&|setting| song.get_written(setting).cloned(), SONG_REFERENCES, None, section, name)
}

fn scene_names(scene: &Scene, section: &str, name: &str) -> bool {
    names_item(
        &|setting| scene.get_written(setting).cloned(),
        SCENE_REFERENCES,
        Some(SceneSetting::CHAINS),
        section,
        name,
    )
}

fn track_names(track: &Track, section: &str, name: &str) -> bool {
    names_item(
        &|setting| track.get_written(setting).cloned(),
        TRACK_REFERENCES,
        Some(TrackSetting::CHAINS),
        section,
        name,
    )
}

fn clip_names(clip: &ClipSlot, section: &str, name: &str) -> bool {
    let get = |setting: &str| {
        if setting == ClipSlotSetting::PATTERNS {
            return Some(Data::List(clip.get_pattern_names().into_iter().map(Data::Text).collect()));
        }
        clip.get_written(setting).cloned()
    };
    names_item(&get, CLIP_REFERENCES, Some(ClipSlotSetting::CHAINS), section, name)
}

/// How a scene is named in a use: its number and its name, if it has one.
pub fn scene_label(number: usize, scene: &Scene) -> String {
    let scene_name = scene.get_name().unwrap_or_else(|| names::MSG_DOCUMENT_UNNAMED_SCENE.to_string());
    named(messages::MSG_USE_SCENE, &[("number", number.into()), ("name", scene_name.as_str().into())])
}

/// The songs that chose an item as their own.
pub fn songs_naming(setlist: &Setlist, section: &str, name: &str) -> Vec<String> {
    setlist
        .song_names()
        .into_iter()
        .filter(|song| setlist.get_song(song).is_some_and(|song| song_names(song, section, name)))
        .map(str::to_string)
        .collect()
}

/// Each song's name, scene number and scene of a scene that chose an item.
pub fn scenes_naming<'a>(setlist: &'a Setlist, section: &str, name: &str) -> Vec<(String, usize, &'a Scene)> {
    let mut found = Vec::new();
    for song_name in setlist.song_names() {
        let Some(song) = setlist.get_song(song_name) else { continue };
        for (place, scene) in song.scenes().iter().enumerate() {
            if scene_names(scene, section, name) {
                found.push((song_name.to_string(), place + 1, scene));
            }
        }
    }
    found
}

pub fn tracks_naming(setlist: &Setlist, section: &str, name: &str) -> Vec<(String, String)> {
    let mut found = Vec::new();
    for song_name in setlist.song_names() {
        let Some(song) = setlist.get_song(song_name) else { continue };
        for (track_name, track) in song.tracks() {
            if track_names(track, section, name) {
                found.push((song_name.to_string(), track_name.clone()));
            }
        }
    }
    found
}

pub fn clip_slots_naming<'a>(setlist: &'a Setlist, section: &str, name: &str) -> Vec<(String, usize, &'a Scene, String)> {
    let mut found = Vec::new();
    for song_name in setlist.song_names() {
        let Some(song) = setlist.get_song(song_name) else { continue };
        for (place, scene) in song.scenes().iter().enumerate() {
            for (track, clip) in scene.clip_slots() {
                if clip_names(clip, section, name) {
                    found.push((song_name.to_string(), place + 1, scene, track.clone()));
                }
            }
        }
    }
    found
}

pub fn chains_naming(setlist: &Setlist, section: &str, name: &str) -> Vec<String> {
    let Some(plugin) = PLUGINS.iter().find(|plugin| plugin.section == section) else {
        return Vec::new();
    };
    let mut found = Vec::new();
    for (chain_name, item) in setlist.items(Section::CHAINS) {
        if let Item::Chain(chain) = item {
            if chain.get_steps().iter().any(|(kind, step)| kind == plugin.name && step == name) {
                found.push(chain_name.clone());
            }
        }
    }
    found
}

/// Every use of a named item of a section anywhere in the set, each worded for a page.
pub fn uses_of(setlist: &Setlist, section: &str, name: &str) -> Vec<String> {
    let mut uses = Vec::new();
    for song in songs_naming(setlist, section, name) {
        uses.push(named(messages::MSG_USE_SONG, &[("name", song.as_str().into())]));
    }
    for (song, number, scene) in scenes_naming(setlist, section, name) {
        uses.push(named(
            messages::MSG_USE_SONG_SCENE,
            &[("song", song.as_str().into()), ("scene", scene_label(number, scene).as_str().into())],
        ));
    }
    for (song, track) in tracks_naming(setlist, section, name) {
        uses.push(named(
            messages::MSG_USE_SONG_TRACK,
            &[("song", song.as_str().into()), ("track", track.as_str().into())],
        ));
    }
    for (song, number, scene, track) in clip_slots_naming(setlist, section, name) {
        let scene = scene_label(number, scene);
        uses.push(named(
            messages::MSG_USE_SONG_SCENE_TRACK,
            &[
                ("song", song.as_str().into()),
                ("scene", scene.as_str().into()),
                ("track", track.as_str().into()),
            ],
        ));
    }
    for chain in chains_naming(setlist, section, name) {
        uses.push(named(messages::MSG_USE_CHAIN, &[("name", chain.as_str().into())]));
    }
    uses
}

/// A count in words, the singular and the plural template each filled with the count: 1 song, 2 songs.
pub fn counted(count: usize, words: &[&str]) -> String {
    named(if count == 1 { words[0] } else { words[1] }, &[("count", count.into())])
}

/// Things listed as a sentence lists them: a, b and c.
pub fn in_a_sentence(parts: &[String]) -> String {
    if parts.len() <= 1 {
        return parts.join(messages::MSG_LIST_JOIN);
    }
    format!(
        "{}{}{}",
        parts[..parts.len() - 1].join(messages::MSG_LIST_JOIN),
        messages::MSG_LIST_LAST_JOIN,
        parts[parts.len() - 1]
    )
}
