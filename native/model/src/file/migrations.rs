// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The migrations (the Python model/file/migrations/): each moves a set file's data from the layout before one breaking
//! change to the layout after it, run in order for a file saved before each, so that the reader only ever sees the layout
//! written now. Live's octave numbers (before 1.0.30), one song at the top (before 1.0.39), the long text under description
//! (before 1.0.155), and everything named kept by name rather than in lists (before 1.0.591).

use crate::file::data::Data;
use crate::objects::naming;

const VERSION: &str = "version";
const NAME: &str = "name";

/// What reading a file moved: whether any migration ran, each name a migration changed as (kind, old, new), and the name a
/// one-song file's song takes.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Conversion {
    pub moved: bool,
    pub renames: Vec<(String, String, String)>,
    pub one_song_name: Option<String>,
}

/// A version's three numbers, or None for text that is not one.
pub fn version_numbers(text: &str) -> Option<(u64, u64, u64)> {
    let parts: Vec<&str> = text.split('.').collect();
    if parts.len() != 3 || !parts.iter().all(|part| !part.is_empty() && part.chars().all(|digit| digit.is_ascii_digit())) {
        return None;
    }
    Some((parts[0].parse().ok()?, parts[1].parse().ok()?, parts[2].parse().ok()?))
}

fn saved_version(data: &Data) -> Option<(u64, u64, u64)> {
    data.get(VERSION).and_then(Data::as_str).and_then(version_numbers)
}

/// One breaking change of the layout: the version that first wrote the new layout, how to tell the old layout by its shape
/// when a file records no version, and the change itself.
struct Migration {
    since: &'static str,
    is_before: fn(&Data) -> bool,
    change: fn(Data, &mut Conversion) -> Data,
}

/// The data moved to the layout written now, with what moving it did.
pub fn migrated(data: Data, one_song_name: Option<String>) -> (Data, Conversion) {
    let mut conversion = Conversion {
        one_song_name,
        ..Conversion::default()
    };
    let migrations = [
        Migration {
            since: "1.0.30",
            is_before: |_| false,
            change: live_octaves,
        },
        Migration {
            since: "1.0.39",
            is_before: one_song_is_before,
            change: one_song,
        },
        Migration {
            since: "1.0.155",
            is_before: |_| false,
            change: description_as_notes,
        },
        Migration {
            since: "1.0.591",
            is_before: lists_is_before,
            change: lists,
        },
    ];
    let mut data = data;
    for Migration { since, is_before, change } in migrations {
        if !matches!(data, Data::Map(_)) {
            continue;
        }
        let due = match saved_version(&data) {
            Some(saved) => version_numbers(since).is_some_and(|since| saved < since),
            None => is_before(&data),
        };
        if due {
            conversion.moved = true;
            data = change(data, &mut conversion);
        }
    }
    (data, conversion)
}

fn map(pairs: Vec<(Data, Data)>) -> Data {
    Data::Map(pairs)
}

fn pairs_of(data: &Data) -> Vec<(Data, Data)> {
    data.as_map().map(<[_]>::to_vec).unwrap_or_default()
}

fn key_is(key: &Data, name: &str) -> bool {
    key.as_str() == Some(name)
}

/// Octaves numbered as Live labels them, two lower than from C0, moved up.
fn live_octaves(data: Data, _: &mut Conversion) -> Data {
    const OFFSET: i128 = 2;
    let mut moved = data;
    for name in ["default_octave", "default_drum_octave"] {
        if let Some(Data::Whole(octave)) = moved.get(name).cloned() {
            moved.set(name, Data::Whole(octave + OFFSET));
        }
    }
    if let Some(Data::Map(patterns)) = moved.get("patterns").cloned() {
        let shifted = patterns
            .into_iter()
            .map(|(name, mut pattern)| {
                if let Some(Data::List(octaves)) = pattern.get("octave").cloned() {
                    let raised = octaves
                        .into_iter()
                        .map(|octave| {
                            if let Data::Whole(whole) = octave {
                                Data::Whole(whole + OFFSET)
                            } else {
                                octave
                            }
                        })
                        .collect();
                    pattern.set("octave", Data::List(raised));
                }
                (name, pattern)
            })
            .collect();
        moved.set("patterns", map(shifted));
    }
    moved
}

const ONE_SONG_KEYS: [&str; 9] = [
    "tempo",
    "time_signature",
    "entry_size",
    "scale",
    "seed",
    "groove",
    "registers",
    "tracks",
    "scenes",
];

fn one_song_is_before(data: &Data) -> bool {
    data.get("songs").is_none() && ONE_SONG_KEYS.iter().any(|key| data.get(key).is_some())
}

/// One song at the top of the file becomes the file's one song, named after the file.
fn one_song(data: Data, conversion: &mut Conversion) -> Data {
    if data.get("songs").is_some() {
        return data;
    }
    let name = conversion.one_song_name.clone().unwrap_or_else(|| "song".to_string());
    let pairs = pairs_of(&data);
    let mut moved: Vec<(Data, Data)> = pairs
        .iter()
        .filter(|(key, _)| !ONE_SONG_KEYS.iter().any(|one| key_is(key, one)))
        .cloned()
        .collect();
    let song: Vec<(Data, Data)> = ONE_SONG_KEYS
        .iter()
        .filter_map(|key| data.get(key).map(|value| (Data::text(key), value.clone())))
        .collect();
    moved.push((Data::text("songs"), map(vec![(Data::Text(name), map(song))])));
    map(moved)
}

/// The long text under description moves to notes.
fn description_as_notes(data: Data, _: &mut Conversion) -> Data {
    if data.get("description").is_none() {
        return data;
    }
    let mut moved = data;
    let notes = moved.remove("description").unwrap_or(Data::Null);
    moved.set("notes", notes);
    moved
}

const LISTED_SECTIONS: [&str; 4] = ["scales", "patterns", "grooves", "instruments"];
const SECTIONS_OF_KINDS: [(&str, &str); 19] = [
    ("arp", "arps"),
    ("auto_ratchet", "auto_ratchets"),
    ("drift", "drifts"),
    ("progression", "progressions"),
    ("voice_leading", "voice_leadings"),
    ("strum", "strums"),
    ("euclid", "euclids"),
    ("density", "densities"),
    ("swell", "swells"),
    ("articulate", "articulates"),
    ("glide", "glides"),
    ("shorten", "shortens"),
    ("rush", "rushes"),
    ("drag", "drags"),
    ("hocket", "hockets"),
    ("guitarify", "guitarifies"),
    ("follow_chords", "follow_chords"),
    ("phrasing", "phrasings"),
    ("musician", "musicians"),
];

fn kind_of_section(section: &str) -> Option<&'static str> {
    SECTIONS_OF_KINDS.iter().find(|(_, found)| *found == section).map(|(kind, _)| *kind)
}

fn lists_is_before(data: &Data) -> bool {
    let keyed = LISTED_SECTIONS
        .iter()
        .chain(["songs"].iter())
        .any(|section| matches!(data.get(section), Some(Data::Map(_))));
    keyed
        || SECTIONS_OF_KINDS
            .iter()
            .map(|(_, section)| *section)
            .chain(["chains"])
            .any(|section| data.get(section).is_some())
}

/// A mapping of things by name as a list, each item its settings with its name first; anything else left for the reader.
fn as_items(mapping: &Data, key: &str) -> Data {
    let Some(pairs) = mapping.as_map() else { return mapping.clone() };
    if !pairs.iter().all(|(_, settings)| matches!(settings, Data::Map(_))) {
        return mapping.clone();
    }
    Data::List(
        pairs
            .iter()
            .map(|(name, settings)| {
                let mut item = vec![(Data::text(key), name.clone())];
                item.extend(pairs_of(settings));
                map(item)
            })
            .collect(),
    )
}

fn with_key_replaced(settings: &Data, old: &str, new: &str, value: Data) -> Data {
    map(pairs_of(settings)
        .into_iter()
        .map(|(key, held)| if key_is(&key, old) { (Data::text(new), value.clone()) } else { (key, held) })
        .collect())
}

fn name_references(names: &Data) -> Data {
    match names {
        Data::List(items) => Data::List(items.iter().map(|name| map(vec![(Data::text(NAME), name.clone())])).collect()),
        other => other.clone(),
    }
}

/// Everything named becomes an item of a list; every generator and chain becomes one list, each item saying its kind.
fn lists(data: Data, conversion: &mut Conversion) -> Data {
    let mut listed: Vec<(Data, Data)> = Vec::new();
    let mut generators: Vec<Data> = Vec::new();
    let mut taken: Vec<String> = Vec::new();
    let mut renamed: Vec<((String, String), String)> = Vec::new();
    for (key, value) in pairs_of(&data) {
        let section = key.as_str().unwrap_or("");
        if let (Some(kind), Data::Map(items)) = (kind_of_section(section), &value) {
            for (name, settings) in items {
                let old = name.python_str();
                let new = free_name(&old, kind, &mut taken, conversion);
                renamed.push(((kind.to_string(), old), new.clone()));
                let mut item = vec![(Data::text(NAME), Data::Text(new)), (Data::text("kind"), Data::text(kind))];
                if let Data::Map(own) = settings {
                    item.extend(own.iter().cloned());
                }
                generators.push(map(item));
            }
        } else if LISTED_SECTIONS.contains(&section) {
            listed.push((key.clone(), as_items(&value, NAME)));
        } else {
            listed.push((key.clone(), value.clone()));
        }
    }
    let mut renamed_chains: Vec<(String, String)> = Vec::new();
    if let Some(place) = listed.iter().position(|(key, _)| key_is(key, "chains")) {
        let (_, chains) = listed.remove(place);
        for (name, chain) in chains.as_map().unwrap_or(&[]) {
            let old = name.python_str();
            let new = free_name(&old, "chain", &mut taken, conversion);
            renamed_chains.push((old, new.clone()));
            generators.push(chain_item(&new, chain, &renamed));
        }
    }
    if !generators.is_empty() {
        listed.push((Data::text("generators"), Data::List(generators)));
    }
    if let Some(place) = listed.iter().position(|(key, value)| key_is(key, "songs") && matches!(value, Data::Map(_))) {
        let songs = listed[place].1.clone();
        let items = songs
            .as_map()
            .unwrap_or(&[])
            .iter()
            .map(|(name, song)| {
                let mut item = vec![(Data::text(NAME), name.clone())];
                item.extend(pairs_of(&song_listed(song, &renamed_chains)));
                map(item)
            })
            .collect();
        listed[place].1 = Data::List(items);
    }
    map(listed)
}

fn free_name(name: &str, kind: &str, taken: &mut Vec<String>, conversion: &mut Conversion) -> String {
    let new = naming::unique_name(name, taken);
    taken.push(new.clone());
    if new != name {
        conversion.renames.push((kind.to_string(), name.to_string(), new.clone()));
    }
    new
}

fn step_of(step: &Data) -> Option<(String, String)> {
    match step.as_map() {
        Some([(kind, name)]) => Some((kind.python_str(), name.python_str())),
        _ => None,
    }
}

fn chain_item(name: &str, chain: &Data, renamed: &[((String, String), String)]) -> Data {
    let steps = match chain {
        Data::Map(_) => chain.get("steps").cloned().unwrap_or(Data::Null),
        other => other.clone(),
    };
    let steps = match steps {
        Data::List(items) => Data::List(
            items
                .iter()
                .map(|step| match step_of(step) {
                    Some(key) => {
                        let found = renamed.iter().find(|(known, _)| *known == key).map(|(_, new)| new.clone()).unwrap_or(key.1);
                        Data::Text(found)
                    }
                    None => step.clone(),
                })
                .collect(),
        ),
        other => other,
    };
    let mut item = vec![
        (Data::text(NAME), Data::text(name)),
        (Data::text("kind"), Data::text("chain")),
        (Data::text("generators"), name_references(&steps)),
    ];
    if let Data::Map(own) = chain {
        for (key, value) in own {
            if !key_is(key, "steps") {
                match item.iter_mut().find(|(found, _)| found == key) {
                    Some(pair) => pair.1 = value.clone(),
                    None => item.push((key.clone(), value.clone())),
                }
            }
        }
    }
    map(item)
}

fn song_listed(song: &Data, renamed: &[(String, String)]) -> Data {
    if !matches!(song, Data::Map(_)) {
        return song.clone();
    }
    let mut listed = song.clone();
    if let Some(Data::Map(tracks)) = song.get("tracks") {
        if tracks.iter().all(|(_, track)| matches!(track, Data::Map(_))) {
            let items = tracks
                .iter()
                .map(|(name, track)| {
                    let mut item = vec![(Data::text(NAME), name.clone())];
                    item.extend(pairs_of(&references_listed(track, renamed)));
                    map(item)
                })
                .collect();
            listed.set("tracks", Data::List(items));
        }
    }
    if let Some(Data::List(scenes)) = song.get("scenes") {
        listed.set("scenes", Data::List(scenes.iter().map(|scene| scene_listed(scene, renamed)).collect()));
    }
    listed
}

fn scene_listed(scene: &Data, renamed: &[(String, String)]) -> Data {
    if !matches!(scene, Data::Map(_)) {
        return scene.clone();
    }
    let listed = references_listed(scene, renamed);
    match listed.get("tracks") {
        Some(Data::Map(clips)) if clips.iter().all(|(_, clip)| matches!(clip, Data::Map(_))) => {
            let items = clips
                .iter()
                .map(|(track, clip)| {
                    let mut item = vec![(Data::text("track"), track.clone())];
                    item.extend(pairs_of(&references_listed(clip, renamed)));
                    map(item)
                })
                .collect();
            with_key_replaced(&listed, "tracks", "clips", Data::List(items))
        }
        _ => listed,
    }
}

/// A clip's, a scene's or a track's settings with the chains it ran written as the generators it runs.
fn references_listed(settings: &Data, renamed: &[(String, String)]) -> Data {
    let mut listed = settings.clone();
    if let (Some(chain), None) = (listed.get("chain").cloned(), listed.get("chains")) {
        listed = with_key_replaced(&listed, "chain", "chains", Data::List(vec![chain]));
    }
    if let Some(names) = listed.get("chains").cloned() {
        let names = match names {
            Data::List(items) => Data::List(
                items
                    .into_iter()
                    .map(|name| {
                        let text = name.python_str();
                        match renamed.iter().find(|(old, _)| *old == text) {
                            Some((_, new)) if matches!(name, Data::Text(_)) => Data::text(new),
                            _ => name,
                        }
                    })
                    .collect(),
            ),
            other => other,
        };
        listed = with_key_replaced(&listed, "chains", "generators", name_references(&names));
    }
    listed
}
