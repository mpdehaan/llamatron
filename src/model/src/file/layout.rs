// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The set file's layout beside the objects' data, and back (the Python model/file/file_layout.py). In the file, everything a
//! person names is an item of a list with its name first, every generator of every kind is one list, each item saying its
//! kind, and a chain, a clip, a scene and a track name the generators they run, each `{ name: x }`. The objects keep their
//! named things by name, each kind of generator apart, and the chains apart.

use crate::file::data::Data;
use crate::schema::checking::InvalidValue;
use crate::schema::generated::file_format::{ClipSlotSetting, FileLayout, Section};
use crate::schema::generated::plugins::PLUGINS;
use llamatron_names::file_format;
use llamatron_names::words;
use llamatron_strings::errors;
use llamatron_strings::named;

pub const OBJECT_CHAINS: &str = "chains";
pub const OBJECT_SCENE_TRACKS: &str = "tracks";
pub const OBJECT_CHAIN_STEPS: &str = "steps";
pub const GENERATORS_WITHOUT_PLUGIN: &str = "generators without a plugin";

fn listed_sections() -> [&'static str; 4] {
    [Section::SCALES, Section::PATTERNS, Section::GROOVES, Section::INSTRUMENTS]
}

/// A refusal of the layout, with the section it was found in.
#[derive(Clone, Debug, PartialEq)]
pub struct LayoutError {
    pub section: String,
    pub problem: InvalidValue,
}

fn plugin_of_section(section: &str) -> Option<&'static str> {
    PLUGINS.iter().find(|plugin| plugin.section == section).map(|plugin| plugin.name)
}

fn section_of_plugin(name: &str) -> Option<&'static str> {
    PLUGINS.iter().find(|plugin| plugin.name == name).map(|plugin| plugin.section)
}

fn map(pairs: Vec<(Data, Data)>) -> Data {
    Data::Map(pairs)
}

/// Things kept by name as a list, each item the thing's settings with its name first under key.
pub fn as_items(mapping: &Data, key: &str) -> Data {
    let items = mapping
        .as_map()
        .unwrap_or(&[])
        .iter()
        .map(|(name, settings)| {
            let mut pairs = vec![(Data::text(key), name.clone())];
            pairs.extend(settings.as_map().unwrap_or(&[]).iter().cloned());
            map(pairs)
        })
        .collect();
    Data::List(items)
}

/// Settings with one key put in place of another, in its place, holding a value.
fn with_key_replaced(settings: &Data, old: &str, new: &str, value: Data) -> Data {
    let pairs = settings
        .as_map()
        .unwrap_or(&[])
        .iter()
        .map(|(key, held)| {
            if key.as_str() == Some(old) {
                (Data::text(new), value.clone())
            } else {
                (key.clone(), held.clone())
            }
        })
        .collect();
    map(pairs)
}

fn name_references(names: &Data) -> Data {
    Data::List(
        names
            .as_list()
            .unwrap_or(&[])
            .iter()
            .map(|name| map(vec![(Data::text(FileLayout::NAME), name.clone())]))
            .collect(),
    )
}

/// The objects' data of a set as the file lays it out.
pub fn as_file_layout(data: &Data) -> Data {
    let mut written: Vec<(Data, Data)> = Vec::new();
    let mut generators: Vec<Data> = Vec::new();
    for (key, value) in data.as_map().unwrap_or(&[]) {
        let name = key.as_str().unwrap_or("");
        if let Some(kind) = plugin_of_section(name) {
            generators.extend(generator_items(kind, value));
        } else if name == Section::CHAINS {
            for (chain_name, chain) in value.as_map().unwrap_or(&[]) {
                generators.push(chain_item(chain_name, chain));
            }
        } else if listed_sections().contains(&name) {
            written.push((key.clone(), as_items(value, FileLayout::NAME)));
        } else if name == Section::SONGS {
            written.push((key.clone(), named_items(value, FileLayout::NAME, song_in_file)));
        } else {
            written.push((key.clone(), value.clone()));
        }
    }
    if !generators.is_empty() {
        written.push((Data::text(FileLayout::GENERATORS), Data::List(generators)));
    }
    map(written)
}

fn generator_items(kind: &str, generators: &Data) -> Vec<Data> {
    generators
        .as_map()
        .unwrap_or(&[])
        .iter()
        .map(|(name, settings)| {
            let mut pairs = vec![(Data::text(FileLayout::NAME), name.clone()), (Data::text(FileLayout::KIND), Data::text(kind))];
            pairs.extend(settings.as_map().unwrap_or(&[]).iter().cloned());
            map(pairs)
        })
        .collect()
}

fn chain_item(name: &Data, chain: &Data) -> Data {
    let steps = match chain {
        Data::Map(_) => chain.get(OBJECT_CHAIN_STEPS).cloned().unwrap_or(Data::List(Vec::new())),
        other => other.clone(),
    };
    // Each step is {kind: name}, and the file names the generator alone.
    let names: Vec<Data> = steps
        .as_list()
        .unwrap_or(&[])
        .iter()
        .filter_map(|step| step.as_map().and_then(|pairs| pairs.first()).map(|(_, name)| name.clone()))
        .collect();
    let mut pairs = vec![
        (Data::text(FileLayout::NAME), name.clone()),
        (Data::text(FileLayout::KIND), Data::text(FileLayout::CHAIN)),
        (Data::text(FileLayout::GENERATORS), name_references(&Data::List(names))),
    ];
    if let Data::Map(own) = chain {
        pairs.extend(own.iter().filter(|(key, _)| key.as_str() != Some(OBJECT_CHAIN_STEPS)).cloned());
    }
    map(pairs)
}

fn named_items(mapping: &Data, key: &str, laid_out: fn(&Data) -> Data) -> Data {
    let items = mapping
        .as_map()
        .unwrap_or(&[])
        .iter()
        .map(|(name, settings)| {
            let mut pairs = vec![(Data::text(key), name.clone())];
            pairs.extend(laid_out(settings).as_map().unwrap_or(&[]).iter().cloned());
            map(pairs)
        })
        .collect();
    Data::List(items)
}

fn song_in_file(song: &Data) -> Data {
    let mut written = song.clone();
    if let Some(tracks) = song.get(Section::TRACKS).filter(|tracks| matches!(tracks, Data::Map(_))) {
        written.set(Section::TRACKS, named_items(tracks, FileLayout::NAME, references_in_file));
    }
    if let Some(scenes) = song.get(Section::SCENES) {
        written.set(Section::SCENES, Data::List(scenes.as_list().unwrap_or(&[]).iter().map(scene_in_file).collect()));
    }
    written
}

fn scene_in_file(scene: &Data) -> Data {
    let written = references_in_file(scene);
    match written.get(OBJECT_SCENE_TRACKS) {
        Some(tracks) => {
            let clips = named_items(tracks, FileLayout::TRACK, references_in_file);
            with_key_replaced(&written, OBJECT_SCENE_TRACKS, FileLayout::CLIPS, clips)
        }
        None => written,
    }
}

fn references_in_file(settings: &Data) -> Data {
    match settings.get(OBJECT_CHAINS) {
        Some(chains) => with_key_replaced(settings, OBJECT_CHAINS, FileLayout::GENERATORS, name_references(chains)),
        None => settings.clone(),
    }
}

fn refusal(section: &str, template: &str, fields: &[(&str, llamatron_strings::Value)]) -> LayoutError {
    LayoutError {
        section: section.to_string(),
        problem: InvalidValue::new(named(template, fields)),
    }
}

/// A set file's data, in the layout written now, as the objects read it.
pub fn as_object_layout(data: &Data) -> Result<Data, LayoutError> {
    let Some(pairs) = data.as_map() else { return Ok(data.clone()) };
    let mut read: Vec<(Data, Data)> = Vec::new();
    for (key, value) in pairs {
        let name = key.as_str().unwrap_or("");
        if listed_sections().contains(&name) {
            read.push((key.clone(), keyed(value, name, FileLayout::NAME)?));
        } else if name == FileLayout::GENERATORS {
            for (section, generators) in generators_by_kind(value)? {
                set_in(&mut read, section, generators);
            }
        } else if name == Section::SONGS {
            let songs = keyed(value, name, FileLayout::NAME)?;
            let mut each = Vec::new();
            for (song_name, song) in songs.as_map().unwrap_or(&[]) {
                each.push((song_name.clone(), song_of_file(song)?));
            }
            read.push((key.clone(), map(each)));
        } else {
            read.push((key.clone(), value.clone()));
        }
    }
    Ok(map(read))
}

fn set_in(pairs: &mut Vec<(Data, Data)>, key: String, value: Data) {
    match pairs.iter_mut().find(|(found, _)| found.as_str() == Some(key.as_str())) {
        Some(pair) => pair.1 = value,
        None => pairs.push((Data::Text(key), value)),
    }
}

/// A list of named items as the objects keep them, by name, each without its name.
pub fn keyed(items: &Data, section: &str, key: &str) -> Result<Data, LayoutError> {
    let Some(listed) = items.as_list() else {
        return Err(refusal(
            section,
            errors::ERR_EXPECTED_ITEMS,
            &[(file_format::StatementPart::VALUE, items.into())],
        ));
    };
    let mut by_name: Vec<(Data, Data)> = Vec::new();
    for item in listed {
        let Some(name) = item
            .get(key)
            .filter(|name| name.as_str().is_some())
            .cloned()
            .filter(|_| matches!(item, Data::Map(_)))
        else {
            return Err(refusal(
                section,
                errors::ERR_ITEM_NEEDS_NAME,
                &[(file_format::StatementPart::VALUE, item.into())],
            ));
        };
        if by_name.iter().any(|(found, _)| *found == name) {
            return Err(refusal(section, errors::ERR_NAMED_TWICE, &[(file_format::FileLayout::NAME, (&name).into())]));
        }
        let own: Vec<(Data, Data)> = item
            .as_map()
            .unwrap_or(&[])
            .iter()
            .filter(|(field, _)| field.as_str() != Some(key))
            .cloned()
            .collect();
        by_name.push((name, map(own)));
    }
    Ok(map(by_name))
}

/// The list of generators as the objects keep them: each kind's under its section, and the chains.
fn generators_by_kind(items: &Data) -> Result<Vec<(String, Data)>, LayoutError> {
    let by_name = keyed(items, FileLayout::GENERATORS, FileLayout::NAME)?;
    let pairs = by_name.as_map().unwrap_or(&[]);
    let mut kinds: Vec<(Data, Data)> = Vec::new();
    for (name, settings) in pairs {
        let kind = settings.get(FileLayout::KIND).cloned().unwrap_or(Data::Null);
        let known = kind.as_str().is_some_and(|kind| kind == FileLayout::CHAIN || section_of_plugin(kind).is_some());
        if !known && kind.as_str().is_none() {
            let choices: Vec<&str> = PLUGINS.iter().map(|plugin| plugin.name).chain([FileLayout::CHAIN]).collect();
            return Err(refusal(
                FileLayout::GENERATORS,
                errors::ERR_NO_SUCH_KIND,
                &[
                    (file_format::FileLayout::NAME, name.into()),
                    (words::KINDS, choices.join(", ").into()),
                    (file_format::StatementPart::VALUE, (&kind).into()),
                ],
            ));
        }
        kinds.push((name.clone(), kind));
    }
    let mut read: Vec<(String, Data)> = Vec::new();
    let mut add = |section: &str, name: Data, value: Data| match read.iter_mut().find(|(found, _)| found == section) {
        Some((_, Data::Map(items))) => items.push((name, value)),
        _ => read.push((section.to_string(), map(vec![(name, value)]))),
    };
    for ((name, settings), (_, kind)) in pairs.iter().zip(kinds.iter()) {
        let own: Vec<(Data, Data)> = settings
            .as_map()
            .unwrap_or(&[])
            .iter()
            .filter(|(field, _)| field.as_str() != Some(FileLayout::KIND))
            .cloned()
            .collect();
        let kind = kind.as_str().unwrap_or("");
        if kind == FileLayout::CHAIN {
            add(Section::CHAINS, name.clone(), chain_of_file(name, &map(own), &kinds)?);
        } else if let Some(section) = section_of_plugin(kind) {
            add(section, name.clone(), map(own));
        } else {
            // A kind no plugin provides, as from a set made where another plugin was installed.
            add(GENERATORS_WITHOUT_PLUGIN, name.clone(), Data::text(kind));
        }
    }
    Ok(read)
}

fn chain_of_file(name: &Data, settings: &Data, kinds: &[(Data, Data)]) -> Result<Data, LayoutError> {
    let references = settings.get(FileLayout::GENERATORS).cloned().unwrap_or(Data::List(Vec::new()));
    let mut steps = Vec::new();
    for step in names_of(&references)? {
        let Some((_, kind)) = kinds.iter().find(|(found, _)| *found == step) else {
            return Err(refusal(
                FileLayout::GENERATORS,
                errors::ERR_NO_GENERATOR_CALLED,
                &[(file_format::FileLayout::NAME, (&step).into())],
            ));
        };
        if kind.as_str() == Some(FileLayout::CHAIN) {
            return Err(refusal(
                FileLayout::GENERATORS,
                errors::ERR_CHAIN_IN_CHAIN,
                &[(file_format::FileLayout::NAME, name.into()), (words::STEP, (&step).into())],
            ));
        }
        steps.push(map(vec![(kind.clone(), step)]));
    }
    let rest: Vec<(Data, Data)> = settings
        .as_map()
        .unwrap_or(&[])
        .iter()
        .filter(|(field, _)| field.as_str() != Some(FileLayout::GENERATORS))
        .cloned()
        .collect();
    if rest.is_empty() {
        return Ok(Data::List(steps));
    }
    let mut pairs = vec![(Data::text(OBJECT_CHAIN_STEPS), Data::List(steps))];
    pairs.extend(rest);
    Ok(map(pairs))
}

/// The names a list of `{ name: x }` holds.
fn names_of(references: &Data) -> Result<Vec<Data>, LayoutError> {
    let refused = || {
        refusal(
            FileLayout::GENERATORS,
            errors::ERR_EXPECTED_NAMES,
            &[(file_format::StatementPart::VALUE, references.into())],
        )
    };
    let Some(listed) = references.as_list() else { return Err(refused()) };
    let mut names = Vec::new();
    for reference in listed {
        match reference.as_map() {
            Some([(key, name)]) if key.as_str() == Some(FileLayout::NAME) => names.push(name.clone()),
            _ => return Err(refused()),
        }
    }
    Ok(names)
}

fn song_of_file(song: &Data) -> Result<Data, LayoutError> {
    if !matches!(song, Data::Map(_)) {
        return Ok(song.clone());
    }
    let mut read = song.clone();
    if let Some(tracks) = song.get(Section::TRACKS) {
        let keyed_tracks = keyed(tracks, Section::TRACKS, FileLayout::NAME)?;
        let mut each = Vec::new();
        for (name, track) in keyed_tracks.as_map().unwrap_or(&[]) {
            each.push((name.clone(), references_of_file(track)?));
        }
        read.set(Section::TRACKS, map(each));
    }
    if let Some(scenes) = song.get(Section::SCENES).and_then(Data::as_list) {
        let mut each = Vec::new();
        for scene in scenes {
            each.push(scene_of_file(scene)?);
        }
        read.set(Section::SCENES, Data::List(each));
    }
    Ok(read)
}

fn scene_of_file(scene: &Data) -> Result<Data, LayoutError> {
    if !matches!(scene, Data::Map(_)) {
        return Ok(scene.clone());
    }
    let read = references_of_file(scene)?;
    let Some(clips) = read.get(FileLayout::CLIPS) else { return Ok(read) };
    let keyed_clips = keyed(clips, FileLayout::CLIPS, FileLayout::TRACK)?;
    let mut each = Vec::new();
    for (track, clip) in keyed_clips.as_map().unwrap_or(&[]) {
        each.push((track.clone(), references_of_file(clip)?));
    }
    Ok(with_key_replaced(&read, FileLayout::CLIPS, OBJECT_SCENE_TRACKS, map(each)))
}

fn references_of_file(settings: &Data) -> Result<Data, LayoutError> {
    let Some(references) = settings.get(FileLayout::GENERATORS).filter(|_| matches!(settings, Data::Map(_))) else {
        return Ok(settings.clone());
    };
    let names = names_of(references)?;
    Ok(with_key_replaced(settings, FileLayout::GENERATORS, OBJECT_CHAINS, Data::List(names)))
}

/// The name of the setting a clip, scene and track keep their chains under.
pub const CHAIN_LISTS: &str = ClipSlotSetting::CHAINS;
