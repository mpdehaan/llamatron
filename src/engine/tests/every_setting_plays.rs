// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Every setting a page can write is played by the render: each setting of every object's table, written one at a time into
//! a small set, and the set's song rendered, which fails on a setting the render refuses. A setting whose value a small set
//! cannot hold, a name of something or a list of cells, is checked where its own feature is tested.

use llamatron_engine::realizer::SongRealizer;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_model::schema::generated::settings::{Described, Plain, Setting, CLIP_SLOT, INSTRUMENT, PATTERN, SCENE, SONG, TRACK};

/// What the small set names its things, and the seed it renders with.
const SCALE: &str = "C Major";
const PATTERN_NAME: &str = "tune";
const INSTRUMENT_NAME: &str = "keys";
const SONG_NAME: &str = "song";
const TRACK_NAME: &str = "lead";
const SCENE_NAME: &str = "one";
const GENERATOR_NAME: &str = "tried";
const SEED: i64 = 7;
/// The pattern's steps and the degrees they play.
const STEPS: i128 = 4;
const DEGREES: [i128; 4] = [1, 2, 3, 4];
/// A length every length setting takes, a quarter note.
const A_QUARTER: &str = "1/4";

/// The settings whose value the small set refuses for what the set itself holds, not for a setting the render cannot play:
/// a loop on the scene's only clip leaves the scene no end, and a drum pattern's steps are drum notes, never degrees.
const REFUSED_BY_THE_SMALL_SET: [(&str, &str); 2] = [("Clip", "loop"), ("Pattern", "drum")];

/// Where a setting is written in the small set: on the song, its track, its scene, its clip, its pattern, its instrument, or
/// a generator its clip runs.
#[derive(Clone, Copy, Debug)]
enum Place {
    Song,
    Track,
    Scene,
    Clip,
    Pattern,
    Instrument,
    Generator(&'static str),
}

fn map(pairs: Vec<(&str, Data)>) -> Data {
    Data::Map(pairs.into_iter().map(|(key, value)| (Data::text(key), value)).collect())
}

/// A value a setting of its kind takes, or None for a kind a small set cannot fill without the thing it names.
fn sample(setting: &Setting) -> Option<Data> {
    match setting.described {
        Described::Flag { .. } => Some(Data::Bool(true)),
        Described::WholeNumber { lowest, highest, .. } => {
            let value = lowest.unwrap_or(1).max(highest.map_or(1, |most| most.min(1)));
            Some(Data::Whole(value as i128))
        }
        Described::Choice { choices, .. } => choices.iter().find_map(|choice| match choice {
            Plain::Text(text) => Some(Data::text(text)),
            Plain::Whole(whole) => Some(Data::Whole(*whole as i128)),
            _ => None,
        }),
        Described::TimeLength { .. } => Some(Data::text(A_QUARTER)),
        _ => None,
    }
}

/// The small set as its file lays it out, with one setting written at a place.
fn set_with(place: Place, name: &'static str, value: Data) -> Data {
    let with = |mut pairs: Vec<(&str, Data)>, here: bool| {
        if here {
            pairs.push((name, value.clone()));
        }
        map(pairs)
    };
    let mut clip = vec![("track", Data::text(TRACK_NAME)), ("pattern", Data::text(PATTERN_NAME))];
    let mut generators = Vec::new();
    if let Place::Generator(kind) = place {
        generators.push(with(vec![("name", Data::text(GENERATOR_NAME)), ("kind", Data::text(kind))], true));
        clip.push(("generators", Data::List(vec![map(vec![("name", Data::text(GENERATOR_NAME))])])));
    }
    let degrees = Data::List(DEGREES.iter().map(|degree| Data::Whole(*degree)).collect());
    let mut set = vec![
        (
            "scales",
            Data::List(vec![map(vec![
                ("name", Data::text(SCALE)),
                ("root", Data::text("C")),
                ("type", Data::text("major")),
            ])]),
        ),
        (
            "patterns",
            Data::List(vec![with(
                vec![("name", Data::text(PATTERN_NAME)), ("steps", Data::Whole(STEPS)), ("degree", degrees)],
                matches!(place, Place::Pattern),
            )]),
        ),
        (
            "instruments",
            Data::List(vec![with(vec![("name", Data::text(INSTRUMENT_NAME))], matches!(place, Place::Instrument))]),
        ),
    ];
    if !generators.is_empty() {
        set.push(("generators", Data::List(generators)));
    }
    let song = with(
        vec![
            ("name", Data::text(SONG_NAME)),
            ("scale", Data::text(SCALE)),
            (
                "tracks",
                Data::List(vec![with(
                    vec![("name", Data::text(TRACK_NAME)), ("instrument", Data::text(INSTRUMENT_NAME))],
                    matches!(place, Place::Track),
                )]),
            ),
            (
                "scenes",
                Data::List(vec![with(
                    vec![
                        ("name", Data::text(SCENE_NAME)),
                        ("clips", Data::List(vec![with(clip, matches!(place, Place::Clip))])),
                    ],
                    matches!(place, Place::Scene),
                )]),
            ),
        ],
        matches!(place, Place::Song),
    );
    set.push(("songs", Data::List(vec![song])));
    map(set)
}

/// The tables of every object and generator, by where their settings are written.
fn tables() -> Vec<(Place, &'static [Setting])> {
    let mut tables = vec![
        (Place::Song, SONG),
        (Place::Track, TRACK),
        (Place::Scene, SCENE),
        (Place::Clip, CLIP_SLOT),
        (Place::Pattern, PATTERN),
        (Place::Instrument, INSTRUMENT),
    ];
    for plugin in PLUGINS {
        if let Some(table) = llamatron_model::objects::named::plugin_table(plugin.name) {
            tables.push((Place::Generator(plugin.name), table));
        }
    }
    tables
}

/// Each setting written alone into the small set plays: the set reads and its song renders.
#[test]
fn every_setting_plays() {
    let mut refused = Vec::new();
    for (place, table) in tables() {
        for setting in table {
            let Some(value) = sample(setting) else { continue };
            let place_name = format!("{place:?}");
            if REFUSED_BY_THE_SMALL_SET.contains(&(place_name.as_str(), setting.name)) {
                continue;
            }
            let data = set_with(place, setting.name, value);
            let setlist = match Setlist::read_data(data, None) {
                Ok(setlist) => setlist,
                Err(problem) => {
                    refused.push(format!("{place:?} {}: the set does not read: {}", setting.name, problem.message));
                    continue;
                }
            };
            let Some(song) = setlist.get_song(SONG_NAME) else { continue };
            if let Err(problem) = SongRealizer::new(&setlist, song, Some(SEED)).render() {
                refused.push(format!("{place:?} {}: {problem:?}", setting.name));
            }
        }
    }
    assert!(refused.is_empty(), "settings that do not play:\n{}", refused.join("\n"));
}
