// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Renaming, copying, removing, moving and sorting the named items of a set's sections, worked on the set's data as its
//! objects hold it (the Python NamedItems, and each object's rename_references): a rename follows every setting that names
//! the item, so that nothing is left naming a name that has gone.

use crate::file::data::Data;
use crate::objects::naming::name_order;
use crate::schema::generated::file_format::TrackSetting;
use crate::schema::generated::plugins::PLUGINS;

/// The sections whose items a list of generators names: every plugin's, and the chains.
const CHAINS: &str = "chains";
const CHAIN_KIND: &str = "chain";
const TRACKS: &str = "tracks";
const SCENES: &str = "scenes";
const SONGS: &str = "songs";
const PATTERNS: &str = "patterns";
const GENERATOR_ORDER: &str = "generator_order";
const BUILT_IN: &str = "built_in";

/// Each kind of object's settings that name an item of a section, as the Python's REFERENCES give them; the settings that
/// list generators are the generators' own, below.
const SONG_REFERENCES: [(&str, &str); 3] = [("scales", "scale"), ("grooves", "groove"), ("instruments", "preview_instrument")];
const TRACK_REFERENCES: [(&str, &str); 2] = [("grooves", "groove"), ("instruments", "instrument")];
const SCENE_REFERENCES: [(&str, &str); 2] = [("scales", "scale"), ("grooves", "groove")];
const CLIP_REFERENCES: [(&str, &str); 5] = [
    (PATTERNS, "pattern"),
    (PATTERNS, "patterns"),
    (PATTERNS, "morph_to"),
    (TRACKS, "grab_track"),
    ("scales", "scale"),
];
/// The settings of the generators that name a track, by the generator's kind.
const TRACK_NAMING_SETTINGS: [(&str, &[&str]); 3] = [
    ("chords", &["chords_from"]),
    ("hocket", &["source"]),
    ("musician", &["chords_from", "tune_from"]),
];

/// Whether a section's items are generators or chains, which lists of generators name.
fn is_generator_section(section: &str) -> bool {
    section == CHAINS || PLUGINS.iter().any(|plugin| plugin.section == section)
}

/// The kind a chain's step names a section's item by: the plugin's name, or chain.
fn step_kind(section: &str) -> Option<&'static str> {
    if section == CHAINS {
        return Some(CHAIN_KIND);
    }
    PLUGINS.iter().find(|plugin| plugin.section == section).map(|plugin| plugin.name)
}

/// A set's data with an item of one of its own sections renamed, keeping its place, and everything that named it following.
pub fn renamed_in_set(set: &Data, section: &str, old: &str, new: &str) -> Data {
    let mut set = set.clone();
    if let Some(items) = entry_mut(&mut set, section) {
        rename_key(items, old, new);
    }
    if let Some(kind) = step_kind(section) {
        if let Some(Data::List(order)) = entry_mut(&mut set, GENERATOR_ORDER) {
            for step in order.iter_mut() {
                rename_step(step, kind, old, new);
            }
        }
        if let Some(Data::Map(chains)) = entry_mut(&mut set, CHAINS) {
            for (_, chain) in chains.iter_mut() {
                let steps = match chain {
                    Data::List(steps) => Some(steps),
                    Data::Map(_) => match entry_mut(chain, "steps") {
                        Some(Data::List(steps)) => Some(steps),
                        _ => None,
                    },
                    _ => None,
                };
                for step in steps.into_iter().flatten() {
                    rename_step(step, kind, old, new);
                }
            }
        }
    }
    if let Some(Data::Map(songs)) = entry_mut(&mut set, SONGS) {
        for (_, song) in songs.iter_mut() {
            rename_in_song(song, section, old, new);
        }
    }
    set
}

/// A set's data with a track of one of its songs renamed: its clips in every scene keep their places under the new name,
/// every grab from it follows, and so does every generator of the set that names it.
pub fn renamed_track(set: &Data, song: &str, old: &str, new: &str) -> Data {
    let mut set = set.clone();
    if let Some(Data::Map(songs)) = entry_mut(&mut set, SONGS) {
        if let Some((_, held)) = songs.iter_mut().find(|(name, _)| name.as_str() == Some(song)) {
            if let Some(tracks) = entry_mut(held, TRACKS) {
                rename_key(tracks, old, new);
            }
            if let Some(Data::List(scenes)) = entry_mut(held, SCENES) {
                for scene in scenes.iter_mut() {
                    if let Some(clips) = entry_mut(scene, TRACKS) {
                        rename_key(clips, old, new);
                    }
                }
            }
            rename_in_song(held, TRACKS, old, new);
        }
    }
    for (kind, settings) in TRACK_NAMING_SETTINGS {
        let Some(section) = PLUGINS.iter().find(|plugin| plugin.name == kind).map(|plugin| plugin.section) else {
            continue;
        };
        if let Some(Data::Map(generators)) = entry_mut(&mut set, section) {
            for (_, generator) in generators.iter_mut() {
                for setting in settings {
                    rename_value(generator, setting, old, new);
                }
            }
        }
    }
    set
}

/// Follow a rename through a song: its own settings, its tracks', its scenes' and their clips'.
fn rename_in_song(song: &mut Data, section: &str, old: &str, new: &str) {
    rename_references(song, &SONG_REFERENCES, section, old, new);
    if let Some(Data::Map(tracks)) = entry_mut(song, TRACKS) {
        for (_, track) in tracks.iter_mut() {
            rename_references(track, &TRACK_REFERENCES, section, old, new);
            rename_holder(track, section, old, new);
        }
    }
    if let Some(Data::List(scenes)) = entry_mut(song, SCENES) {
        for scene in scenes.iter_mut() {
            rename_references(scene, &SCENE_REFERENCES, section, old, new);
            rename_holder(scene, section, old, new);
            if let Some(Data::Map(clips)) = entry_mut(scene, TRACKS) {
                for (_, clip) in clips.iter_mut() {
                    rename_references(clip, &CLIP_REFERENCES, section, old, new);
                    rename_holder(clip, section, old, new);
                }
            }
        }
    }
}

/// Follow a rename through what a track, a scene or a clip runs: its list of generators, and its built-in generators'
/// settings that name a track.
fn rename_holder(holder: &mut Data, section: &str, old: &str, new: &str) {
    if is_generator_section(section) {
        rename_value(holder, CHAINS, old, new);
    }
    if section != TRACKS {
        return;
    }
    if let Some(Data::Map(built_ins)) = entry_mut(holder, BUILT_IN) {
        for (kind, settings) in built_ins.iter_mut() {
            let Some((_, names)) = TRACK_NAMING_SETTINGS.iter().find(|(each, _)| kind.as_str() == Some(each)) else {
                continue;
            };
            for setting in names.iter() {
                rename_value(settings, setting, old, new);
            }
        }
    }
}

/// Follow a rename through an object's own settings that name an item of the section.
fn rename_references(object: &mut Data, references: &[(&str, &str)], section: &str, old: &str, new: &str) {
    for (named, setting) in references {
        if *named == section {
            rename_value(object, setting, old, new);
        }
    }
}

/// Rename a setting's value where it is the old name, or each of a list's items that is.
fn rename_value(object: &mut Data, setting: &str, old: &str, new: &str) {
    match entry_mut(object, setting) {
        Some(Data::Text(text)) if text == old => *text = new.to_string(),
        Some(Data::List(items)) => {
            for item in items.iter_mut() {
                if item.as_str() == Some(old) {
                    *item = Data::text(new);
                }
            }
        }
        _ => {}
    }
}

/// Rename a step of a chain or of the generators' order, a mapping of a kind to a name.
fn rename_step(step: &mut Data, kind: &str, old: &str, new: &str) {
    if let Data::Map(pairs) = step {
        for (each, name) in pairs.iter_mut() {
            if each.as_str() == Some(kind) && name.as_str() == Some(old) {
                *name = Data::text(new);
            }
        }
    }
}

/// Rename a key of a mapping, keeping its place.
fn rename_key(items: &mut Data, old: &str, new: &str) {
    if let Data::Map(pairs) = items {
        if let Some(pair) = pairs.iter_mut().find(|(name, _)| name.as_str() == Some(old)) {
            pair.0 = Data::text(new);
        }
    }
}

/// A mapping's value under a name, to change.
fn entry_mut<'a>(data: &'a mut Data, name: &str) -> Option<&'a mut Data> {
    match data {
        Data::Map(pairs) => pairs.iter_mut().find(|(key, _)| key.as_str() == Some(name)).map(|(_, value)| value),
        _ => None,
    }
}

/// A set's data with an item of a section moved up or down its section, or None where that would pass either end.
pub fn moved_in_section(items: &Data, place: usize, offset: i64) -> Option<Data> {
    let Data::Map(pairs) = items else { return None };
    let target = place as i64 + offset;
    if place >= pairs.len() || target < 0 || target as usize >= pairs.len() {
        return None;
    }
    let mut moved = pairs.clone();
    let item = moved.remove(place);
    moved.insert(target as usize, item);
    Some(Data::Map(moved))
}

/// A section's items in order of name, ignoring capitals and reading a number a name ends in as a number.
pub fn sorted_section(items: &Data) -> Data {
    let Data::Map(pairs) = items else { return items.clone() };
    let mut sorted = pairs.clone();
    sorted.sort_by_key(|(name, _)| name_order(name.as_str().unwrap_or_default()));
    Data::Map(sorted)
}

/// A set's data with a copy of an item of one of its own sections added at the end under a new name; a generator's copy
/// comes straight after what it copies in the Generators page's order, where the set keeps one.
pub fn copied_in_set(set: &Data, section: &str, name: &str, new: &str) -> Data {
    let mut set = set.clone();
    if let Some(Data::Map(items)) = entry_mut(&mut set, section) {
        if let Some((_, item)) = items.iter().find(|(each, _)| each.as_str() == Some(name)).cloned() {
            items.push((Data::text(new), item));
        }
    }
    if let (Some(kind), Some(Data::List(order))) = (step_kind(section), entry_mut(&mut set, GENERATOR_ORDER)) {
        let step = |named: &str| Data::Map(vec![(Data::text(kind), Data::text(named))]);
        order.retain(|each| *each != step(new));
        if let Some(place) = order.iter().position(|each| *each == step(name)) {
            order.insert(place + 1, step(new));
        }
    }
    set
}

/// A set's data with an item of one of its own sections taken out; a generator or a chain is taken out of every chain's
/// steps and every list of generators of every song as well.
pub fn removed_from_set(set: &Data, section: &str, name: &str) -> Data {
    let mut set = set.clone();
    if let Some(Data::Map(items)) = entry_mut(&mut set, section) {
        items.retain(|(each, _)| each.as_str() != Some(name));
    }
    let Some(kind) = step_kind(section) else { return set };
    let step = Data::Map(vec![(Data::text(kind), Data::text(name))]);
    if let Some(Data::Map(chains)) = entry_mut(&mut set, CHAINS) {
        for (_, chain) in chains.iter_mut() {
            match chain {
                Data::List(steps) => steps.retain(|each| *each != step),
                Data::Map(_) => {
                    if let Some(Data::List(steps)) = entry_mut(chain, "steps") {
                        steps.retain(|each| *each != step);
                    }
                }
                _ => {}
            }
        }
    }
    if let Some(Data::Map(songs)) = entry_mut(&mut set, SONGS) {
        for (_, song) in songs.iter_mut() {
            forget_generator(song, name);
        }
    }
    set
}

/// Take a generator out of every list of generators of a song: its tracks', its scenes' and its clips'.
fn forget_generator(song: &mut Data, name: &str) {
    // A list left empty is left out, as a holder with no generators writes none.
    let forget = |holder: &mut Data| {
        if let Some(Data::List(names)) = entry_mut(holder, CHAINS) {
            names.retain(|each| each.as_str() != Some(name));
        }
        if let Data::Map(settings) = holder {
            settings.retain(|(key, value)| !(key.as_str() == Some(CHAINS) && value.as_list().is_some_and(<[Data]>::is_empty)));
        }
    };
    if let Some(Data::Map(tracks)) = entry_mut(song, TRACKS) {
        tracks.iter_mut().for_each(|(_, track)| forget(track));
    }
    if let Some(Data::List(scenes)) = entry_mut(song, SCENES) {
        for scene in scenes.iter_mut() {
            forget(scene);
            if let Some(Data::Map(clips)) = entry_mut(scene, TRACKS) {
                clips.iter_mut().for_each(|(_, clip)| forget(clip));
            }
        }
    }
}

/// A set's data with a copy of a track of a song added right after it, with a copy of its clip in every scene.
pub fn copied_track(set: &Data, song: &str, name: &str, new: &str) -> Data {
    let mut set = set.clone();
    let Some(held) = song_mut(&mut set, song) else { return set };
    if let Some(Data::Map(tracks)) = entry_mut(held, TRACKS) {
        if let Some(place) = tracks.iter().position(|(each, _)| each.as_str() == Some(name)) {
            let track = tracks[place].1.clone();
            tracks.insert(place + 1, (Data::text(new), track));
        }
    }
    if let Some(Data::List(scenes)) = entry_mut(held, SCENES) {
        for scene in scenes.iter_mut() {
            if let Some(Data::Map(clips)) = entry_mut(scene, TRACKS) {
                if let Some((_, clip)) = clips.iter().find(|(each, _)| each.as_str() == Some(name)).cloned() {
                    clips.push((Data::text(new), clip));
                }
            }
        }
    }
    set
}

/// A set's data with a track of a song taken out, with its clips, and every clip that grabbed from it grabbing no more.
pub fn removed_track(set: &Data, song: &str, name: &str) -> Data {
    let mut set = set.clone();
    let Some(held) = song_mut(&mut set, song) else { return set };
    if let Some(Data::Map(tracks)) = entry_mut(held, TRACKS) {
        tracks.retain(|(each, _)| each.as_str() != Some(name));
    }
    if let Some(Data::List(scenes)) = entry_mut(held, SCENES) {
        for scene in scenes.iter_mut() {
            if let Some(Data::Map(clips)) = entry_mut(scene, TRACKS) {
                clips.retain(|(each, _)| each.as_str() != Some(name));
                for (_, clip) in clips.iter_mut() {
                    if let Data::Map(settings) = clip {
                        settings.retain(|(key, value)| !(key.as_str() == Some("grab_track") && value.as_str() == Some(name)));
                    }
                }
            }
        }
    }
    set
}

/// A song's data in a set's, to change.
fn song_mut<'a>(set: &'a mut Data, song: &str) -> Option<&'a mut Data> {
    match entry_mut(set, SONGS)? {
        Data::Map(songs) => songs.iter_mut().find(|(name, _)| name.as_str() == Some(song)).map(|(_, held)| held),
        _ => None,
    }
}

// Arrange's edits of a song's scenes, tracks and clips (the Python song.py's and scene.py's).

/// The setting that names a scene, and those that name a clip's one pattern or its several.
const SCENE_NAME: &str = "name";
const CLIP_PATTERN: &str = "pattern";
const CLIP_PATTERNS: &str = "patterns";

/// The scenes of a song in a set's data, to change.
fn scenes_mut<'a>(set: &'a mut Data, song: &str) -> Option<&'a mut Vec<Data>> {
    match entry_mut(song_mut(set, song)?, SCENES)? {
        Data::List(scenes) => Some(scenes),
        _ => None,
    }
}

/// The clips of a scene of a song, by track, to change; a scene without any is given an empty map of them.
fn clips_mut<'a>(set: &'a mut Data, song: &str, index: usize) -> Option<&'a mut Vec<(Data, Data)>> {
    let scene = scenes_mut(set, song)?.get_mut(index)?;
    if scene.get(TRACKS).is_none() {
        scene.set(TRACKS, Data::Map(Vec::new()));
    }
    match entry_mut(scene, TRACKS)? {
        Data::Map(clips) => Some(clips),
        _ => None,
    }
}

/// A set's data with a new scene of no clips put at a place in a song, under a name.
pub fn added_scene(set: &Data, song: &str, index: usize, name: &str) -> Data {
    let mut set = set.clone();
    if let Some(scenes) = scenes_mut(&mut set, song) {
        let scene = Data::Map(vec![(Data::text(SCENE_NAME), Data::text(name)), (Data::text(TRACKS), Data::Map(Vec::new()))]);
        scenes.insert(index.min(scenes.len()), scene);
    }
    set
}

/// A set's data with a copy of a scene of a song, its clips with it, put right after it under a new name.
pub fn copied_scene(set: &Data, song: &str, index: usize, name: &str) -> Data {
    let mut set = set.clone();
    if let Some(scenes) = scenes_mut(&mut set, song) {
        if let Some(mut scene) = scenes.get(index).cloned() {
            scene.set(SCENE_NAME, Data::text(name));
            scenes.insert(index + 1, scene);
        }
    }
    set
}

/// A set's data with a scene of a song taken out, with its clips.
pub fn removed_scene(set: &Data, song: &str, index: usize) -> Data {
    let mut set = set.clone();
    if let Some(scenes) = scenes_mut(&mut set, song) {
        if index < scenes.len() {
            scenes.remove(index);
        }
    }
    set
}

/// A set's data with a new track of no clips added to a song, a drum track or a melodic one, playing an instrument where
/// one is named, at a place among its tracks in the file's order or at the end.
pub fn added_track(set: &Data, song: &str, name: &str, place: Option<usize>, drum: bool, instrument: Option<&str>) -> Data {
    let mut set = set.clone();
    let Some(held) = song_mut(&mut set, song) else { return set };
    if held.get(TRACKS).is_none() {
        held.set(TRACKS, Data::Map(Vec::new()));
    }
    if let Some(Data::Map(tracks)) = entry_mut(held, TRACKS) {
        let at = place.unwrap_or(tracks.len()).min(tracks.len());
        let mut settings = if drum {
            vec![(Data::text(TrackSetting::DRUM), Data::Bool(true))]
        } else {
            Vec::new()
        };
        if let Some(instrument) = instrument {
            settings.push((Data::text(TrackSetting::INSTRUMENT), Data::text(instrument)));
        }
        tracks.insert(at, (Data::text(name), Data::Map(settings)));
    }
    set
}

/// A set's data with a clip put on a track in a scene of a song, in place of any there, a new one after the scene's others.
pub fn put_clip(set: &Data, song: &str, index: usize, track: &str, clip: &Data) -> Data {
    let mut set = set.clone();
    if let Some(clips) = clips_mut(&mut set, song, index) {
        match clips.iter_mut().find(|(each, _)| each.as_str() == Some(track)) {
            Some((_, held)) => *held = clip.clone(),
            None => clips.push((Data::text(track), clip.clone())),
        }
    }
    set
}

/// A new clip's data, playing a pattern once.
pub fn new_clip(pattern: &str) -> Data {
    Data::Map(vec![(Data::text(CLIP_PATTERN), Data::text(pattern))])
}

/// A set's data with the clip on a track in a scene of a song taken out.
pub fn removed_clip(set: &Data, song: &str, index: usize, track: &str) -> Data {
    let mut set = set.clone();
    if let Some(clips) = clips_mut(&mut set, song, index) {
        clips.retain(|(each, _)| each.as_str() != Some(track));
    }
    set
}

/// A clip's data playing other patterns in place of its own, each name its new one, as written: one pattern or several.
pub fn clip_playing(clip: &Data, renamed: &dyn Fn(&str) -> String) -> Data {
    let mut clip = clip.clone();
    if let Some(Data::Text(name)) = clip.get(CLIP_PATTERN).cloned() {
        clip.set(CLIP_PATTERN, Data::text(&renamed(&name)));
    }
    if let Some(Data::List(names)) = clip.get(CLIP_PATTERNS).cloned() {
        let names = names
            .iter()
            .map(|name| name.as_str().map_or(name.clone(), |name| Data::text(&renamed(name))))
            .collect();
        clip.set(CLIP_PATTERNS, Data::List(names));
    }
    clip
}

/// The names of the patterns a clip's data plays, in order.
pub fn clip_patterns(clip: &Data) -> Vec<String> {
    if let Some(name) = clip.get(CLIP_PATTERN).and_then(Data::as_str) {
        return vec![name.to_string()];
    }
    clip.get(CLIP_PATTERNS)
        .and_then(Data::as_list)
        .map_or(Vec::new(), |names| names.iter().filter_map(|name| name.as_str().map(str::to_string)).collect())
}

/// A blank pattern's data: its steps, its group, and a drum pattern marked as one, or a pattern written for a scale of a
/// number of notes.
pub fn blank_pattern(steps: i64, group: Option<&str>, drum: bool, scale_length: Option<i64>) -> Data {
    let mut pairs = vec![(Data::text("steps"), Data::Whole(steps as i128))];
    if let Some(group) = group {
        pairs.push((Data::text("group"), Data::text(group)));
    }
    if drum {
        pairs.push((Data::text("drum"), Data::Bool(true)));
    } else if let Some(length) = scale_length {
        pairs.push((Data::text("scale_length"), Data::Whole(length as i128)));
    }
    Data::Map(pairs)
}

/// A set's data with every clip of a song given a pattern of its own, and the names of the copies made: the first clip to
/// play a pattern, reading the scenes from the top and each scene's tracks from the left, keeps it, and every later clip
/// that plays it plays a copy, named as a duplicate is and kept in the pattern's group. A pattern a clip names twice in its
/// own list stays one pattern there.
pub fn fractured(set: &Data, song: &str) -> (Data, Vec<String>) {
    let mut set = set.clone();
    let mut taken: Vec<String> = match set.get(PATTERNS) {
        Some(Data::Map(patterns)) => patterns.iter().filter_map(|(name, _)| name.as_str().map(str::to_string)).collect(),
        _ => Vec::new(),
    };
    let tracks: Vec<String> = song_mut(&mut set, song)
        .and_then(|held| {
            held.get(TRACKS)
                .and_then(Data::as_map)
                .map(|tracks| tracks.iter().filter_map(|(name, _)| name.as_str().map(str::to_string)).collect())
        })
        .unwrap_or_default();
    let scene_count = scenes_mut(&mut set, song).map_or(0, |scenes| scenes.len());
    let mut seen: Vec<String> = Vec::new();
    let mut copies: Vec<(String, String)> = Vec::new();
    for index in 0..scene_count {
        for track in &tracks {
            let Some(clips) = clips_mut(&mut set, song, index) else { continue };
            let Some((_, clip)) = clips.iter_mut().find(|(each, _)| each.as_str() == Some(track.as_str())) else {
                continue;
            };
            let mut own: Vec<(String, String)> = Vec::new();
            for name in clip_patterns(clip) {
                if own.iter().any(|(old, _)| *old == name) {
                    continue;
                }
                let mut new = name.clone();
                if seen.contains(&name) {
                    new = crate::objects::naming::copy_name(&name, &taken);
                    taken.push(new.clone());
                    copies.push((name.clone(), new.clone()));
                }
                own.push((name, new));
            }
            seen.extend(own.iter().map(|(_, new)| new.clone()));
            let renamed = |name: &str| own.iter().find(|(old, _)| old == name).map_or(name.to_string(), |(_, new)| new.clone());
            *clip = clip_playing(clip, &renamed);
        }
    }
    if let Some(Data::Map(patterns)) = entry_mut(&mut set, PATTERNS) {
        for (old, new) in &copies {
            if let Some((_, pattern)) = patterns.iter().find(|(each, _)| each.as_str() == Some(old.as_str())).cloned() {
                patterns.push((Data::text(new), pattern));
            }
        }
    }
    (set, copies.into_iter().map(|(_, new)| new).collect())
}
