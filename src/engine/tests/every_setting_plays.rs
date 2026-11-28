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
use llamatron_names::file_format;

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
/// How the name of the top of a range of settings starts, such as highest_octave.
const TOP_OF_A_RANGE: &str = "highest";
/// A length every length setting takes, a quarter note.
const A_QUARTER: &str = "1/4";

/// The settings whose value the small set refuses for what the set itself holds, not for a setting the render cannot play:
/// a loop on the scene's only clip leaves the scene no end, a drum pattern's steps are drum notes, never degrees, and a
/// morph's style is refused without the pattern it morphs into, which the morph's own tests write together.
const REFUSED_BY_THE_SMALL_SET: [(&str, &str); 3] = [("Clip", "loop"), ("Pattern", "drum"), ("Clip", "morph_style")];

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
        // The top of a range is written at its highest, so that it stays above the range's bottom left at its default.
        Described::WholeNumber { highest: Some(highest), .. } if setting.name.starts_with(TOP_OF_A_RANGE) => Some(Data::Whole(highest as i128)),
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
    let mut clip = vec![
        (file_format::FileLayout::TRACK, Data::text(TRACK_NAME)),
        (file_format::ClipSlotSetting::PATTERN, Data::text(PATTERN_NAME)),
    ];
    let mut generators = Vec::new();
    if let Place::Generator(kind) = place {
        generators.push(with(
            vec![
                (file_format::FileLayout::NAME, Data::text(GENERATOR_NAME)),
                (file_format::FileLayout::KIND, Data::text(kind)),
            ],
            true,
        ));
        clip.push((
            file_format::FileLayout::GENERATORS,
            Data::List(vec![map(vec![(file_format::FileLayout::NAME, Data::text(GENERATOR_NAME))])]),
        ));
    }
    let degrees = Data::List(DEGREES.iter().map(|degree| Data::Whole(*degree)).collect());
    let mut set = vec![
        (
            file_format::Section::SCALES,
            Data::List(vec![map(vec![
                (file_format::FileLayout::NAME, Data::text(SCALE)),
                (file_format::ScaleSetting::ROOT, Data::text("C")),
                (file_format::ScaleSetting::TYPE, Data::text(file_format::Quality::MAJOR)),
            ])]),
        ),
        (
            file_format::Section::PATTERNS,
            Data::List(vec![with(
                vec![
                    (file_format::FileLayout::NAME, Data::text(PATTERN_NAME)),
                    (file_format::PatternSetting::STEPS, Data::Whole(STEPS)),
                    (file_format::Row::DEGREE, degrees),
                ],
                matches!(place, Place::Pattern),
            )]),
        ),
        (
            file_format::Section::INSTRUMENTS,
            Data::List(vec![with(
                vec![(file_format::FileLayout::NAME, Data::text(INSTRUMENT_NAME))],
                matches!(place, Place::Instrument),
            )]),
        ),
    ];
    if !generators.is_empty() {
        set.push((file_format::FileLayout::GENERATORS, Data::List(generators)));
    }
    let song = with(
        vec![
            (file_format::FileLayout::NAME, Data::text(SONG_NAME)),
            (file_format::SongSetting::SCALE, Data::text(SCALE)),
            (
                file_format::Section::TRACKS,
                Data::List(vec![with(
                    vec![
                        (file_format::FileLayout::NAME, Data::text(TRACK_NAME)),
                        (file_format::TrackSetting::INSTRUMENT, Data::text(INSTRUMENT_NAME)),
                    ],
                    matches!(place, Place::Track),
                )]),
            ),
            (
                file_format::Section::SCENES,
                Data::List(vec![with(
                    vec![
                        (file_format::FileLayout::NAME, Data::text(SCENE_NAME)),
                        (file_format::FileLayout::CLIPS, Data::List(vec![with(clip, matches!(place, Place::Clip))])),
                    ],
                    matches!(place, Place::Scene),
                )]),
            ),
        ],
        matches!(place, Place::Song),
    );
    set.push((file_format::Section::SONGS, Data::List(vec![song])));
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
            let setlist = match Setlist::read_data(data) {
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
