// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The set the tracker opens on when no file is named, built as data: a C major scale, a pattern of four beats, and one
//! song, untitled, of a main track, main1, playing the pattern in its one scene, and a drum track, drum1, with no clips,
//! each with an instrument of its own named after it.

use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::schema::generated::file_format::{
    ClipSlotSetting, FileLayout, PatternSetting, Row, ScaleSetting, Section, SetlistSetting, SongSetting, TrackSetting,
};
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_strings::named;
use llamatron_strings::names;

/// The set's own settings: each step a sixteenth, new notes in octave 5 and drums in 3, octaves labelled as Live does.
const STEP_SIZE: &str = "1/16";
const DEFAULT_OCTAVE: i128 = 5;
const DEFAULT_DRUM_OCTAVE: i128 = 3;
const OCTAVE_LABELS: &str = file_format::OctaveLabels::LIVE;
/// The scale: C major.
const ROOT: &str = "C";
const SCALE_TYPE: &str = file_format::Quality::MAJOR;
/// The song's tempo, and the pattern's length and the steps of it that sound the root, one a beat.
const TEMPO: i128 = 120;
const STEPS: usize = 16;
const STEPS_A_BEAT: usize = 4;
const ROOT_DEGREE: i128 = 1;
/// The number the first of each kind of thing is named with.
const FIRST: i64 = 1;

/// A map from its keys and values.
fn map(pairs: Vec<(&str, Data)>) -> Data {
    Data::Map(pairs.into_iter().map(|(key, value)| (Data::text(key), value)).collect())
}

/// The new set, its main and drum tracks playing the instruments given.
pub fn new_set(main_instrument: Data, drum_instrument: Data) -> Result<Setlist, String> {
    let scale = named(
        names::MSG_NUMBERED_NAME,
        &[(fill::BASE, names::MSG_NEW_SCALE_WORD.into()), (fill::NUMBER, FIRST.into())],
    );
    let pattern = named(
        names::MSG_NUMBERED_NAME,
        &[(fill::BASE, names::MSG_NEW_PATTERN_WORD.into()), (fill::NUMBER, FIRST.into())],
    );
    let scene = named(
        names::MSG_NUMBERED_NAME,
        &[(fill::BASE, names::MSG_NEW_SCENE_WORD.into()), (fill::NUMBER, FIRST.into())],
    );
    let main = named(
        names::MSG_JOINED_NUMBERED_NAME,
        &[(fill::BASE, names::MSG_NEW_MAIN_TRACK_WORD.into()), (fill::NUMBER, FIRST.into())],
    );
    let drum = named(
        names::MSG_JOINED_NUMBERED_NAME,
        &[(fill::BASE, names::MSG_NEW_DRUM_TRACK_WORD.into()), (fill::NUMBER, FIRST.into())],
    );
    let degrees = (0..STEPS)
        .map(|step| if step % STEPS_A_BEAT == 0 { Data::Whole(ROOT_DEGREE) } else { Data::Null })
        .collect();
    let with_name = |name: &str, mut settings: Data| {
        if let Data::Map(pairs) = &mut settings {
            pairs.insert(0, (Data::text(FileLayout::NAME), Data::text(name)));
        }
        settings
    };
    let song = map(vec![
        (FileLayout::NAME, Data::text(names::MSG_DEFAULT_SONG_NAME)),
        (SongSetting::TEMPO, Data::Whole(TEMPO)),
        (SongSetting::SCALE, Data::text(&scale)),
        (
            Section::TRACKS,
            Data::List(vec![
                map(vec![(FileLayout::NAME, Data::text(&main)), (TrackSetting::INSTRUMENT, Data::text(&main))]),
                map(vec![
                    (FileLayout::NAME, Data::text(&drum)),
                    (TrackSetting::DRUM, Data::Bool(true)),
                    (TrackSetting::INSTRUMENT, Data::text(&drum)),
                ]),
            ]),
        ),
        (
            Section::SCENES,
            Data::List(vec![map(vec![
                (FileLayout::NAME, Data::text(&scene)),
                (
                    FileLayout::CLIPS,
                    Data::List(vec![map(vec![
                        (FileLayout::TRACK, Data::text(&main)),
                        (ClipSlotSetting::PATTERN, Data::text(&pattern)),
                    ])]),
                ),
            ])]),
        ),
    ]);
    let set = map(vec![
        (SetlistSetting::STEP_SIZE, Data::text(STEP_SIZE)),
        (SetlistSetting::DEFAULT_OCTAVE, Data::Whole(DEFAULT_OCTAVE)),
        (SetlistSetting::DEFAULT_DRUM_OCTAVE, Data::Whole(DEFAULT_DRUM_OCTAVE)),
        (SetlistSetting::OCTAVE_LABELS, Data::text(OCTAVE_LABELS)),
        (
            Section::SCALES,
            Data::List(vec![map(vec![
                (FileLayout::NAME, Data::text(&scale)),
                (ScaleSetting::ROOT, Data::text(ROOT)),
                (ScaleSetting::TYPE, Data::text(SCALE_TYPE)),
            ])]),
        ),
        (
            Section::PATTERNS,
            Data::List(vec![map(vec![
                (FileLayout::NAME, Data::text(&pattern)),
                (PatternSetting::STEPS, Data::Whole(STEPS as i128)),
                (PatternSetting::GROUP, Data::text(&main)),
                (Row::DEGREE, Data::List(degrees)),
            ])]),
        ),
        (
            Section::INSTRUMENTS,
            Data::List(vec![with_name(&main, main_instrument), with_name(&drum, drum_instrument)]),
        ),
        (Section::SONGS, Data::List(vec![song])),
    ]);
    Setlist::read_data(set).map_err(|error| error.message)
}
