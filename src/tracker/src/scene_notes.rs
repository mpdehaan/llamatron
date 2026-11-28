// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What one scene of Arrange plays, as Scene View shows it (the Python interface/tracker/scene_notes.py and
//! engine/realizer/as_written.py): every track's notes as played, the song's render, or as written, its patterns alone,
//! with its repeats laid end to end from the scene's start; and the tempo, scale and groove the scene plays with in the end
//! and where each comes from.

use llamatron_engine::realizer::SongRealizer;
use llamatron_engine::timing::timed_events;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::Song;
use llamatron_model::schema::generated::file_format::{SceneSetting, SongSetting, TrackSetting, STATEMENT_OF_ROW};
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_strings::{marks, named};

/// A note of the scene: its track's place in the song, when it starts and ends in whole notes from the scene's start, its
/// MIDI pitch, whether it is a drum's, and whether its clip reads the draws.
#[derive(Clone, Debug)]
pub struct SceneNote {
    pub track: usize,
    pub start: Rational,
    pub end: Rational,
    pub pitch: i64,
    pub drum: bool,
    pub marked: bool,
}

/// A scene's notes, the song's track names by place, which tracks read the draws, how long the scene lasts, and its beat
/// and bar.
pub struct SceneNotes {
    pub names: Vec<String>,
    pub notes: Vec<SceneNote>,
    pub marked_tracks: Vec<usize>,
    pub length: Rational,
    pub beat: Rational,
    pub bar: Rational,
}

/// The rows of a pattern that change what plays by chance or by a statement, which a scene as written leaves out.
const PROBABILITY: &str = file_format::Row::PROBABILITY;
/// A scene's and a clip's Shapes settings, which work after the patterns.
const SHAPE_SETTINGS: [&str; 8] = [
    file_format::SceneSetting::DENSITY_START,
    file_format::SceneSetting::DENSITY_END,
    file_format::SceneSetting::DENSITY_OVER,
    file_format::SceneSetting::DENSITY_THEN,
    file_format::SceneSetting::ARTICULATE_START,
    file_format::SceneSetting::ARTICULATE_END,
    file_format::SceneSetting::ARTICULATE_OVER,
    file_format::SceneSetting::ARTICULATE_THEN,
];
const CHAINS: &str = file_format::Section::CHAINS;
const TRACKS: &str = file_format::Section::TRACKS;
const SCENES: &str = file_format::Section::SCENES;
const SONGS: &str = file_format::Section::SONGS;
const PATTERNS: &str = file_format::Section::PATTERNS;

/// A set's data with everything that works after the patterns taken out, so that a song is realized as written: the
/// chains, the grooves, the shapes, and the patterns' probability and the steps' statements.
fn as_written(set: &Data) -> Data {
    let mut set = set.clone();
    let forget = |item: &mut Data, names: &[&str]| {
        for name in names {
            item.remove(name);
        }
    };
    if let Some(Data::Map(patterns)) = set.get(PATTERNS).cloned() {
        let mut kept = Vec::new();
        for (name, mut pattern) in patterns {
            forget(&mut pattern, &[PROBABILITY]);
            let statements: Vec<&str> = STATEMENT_OF_ROW.iter().map(|(row, _)| *row).collect();
            forget(&mut pattern, &statements);
            kept.push((name, pattern));
        }
        set.set(PATTERNS, Data::Map(kept));
    }
    if let Some(Data::Map(songs)) = set.get(SONGS).cloned() {
        let mut kept = Vec::new();
        for (name, mut song) in songs {
            forget(&mut song, &[SongSetting::GROOVE]);
            if let Some(Data::Map(tracks)) = song.get(TRACKS).cloned() {
                let tracks = tracks
                    .into_iter()
                    .map(|(track_name, mut track)| {
                        forget(&mut track, &[TrackSetting::CHAINS, TrackSetting::GROOVE]);
                        (track_name, track)
                    })
                    .collect();
                song.set(TRACKS, Data::Map(tracks));
            }
            if let Some(Data::List(scenes)) = song.get(SCENES).cloned() {
                let scenes = scenes
                    .into_iter()
                    .map(|mut scene| {
                        forget(&mut scene, &[SceneSetting::CHAINS, SceneSetting::GROOVE]);
                        forget(&mut scene, &SHAPE_SETTINGS);
                        if let Some(Data::Map(clips)) = scene.get(TRACKS).cloned() {
                            let clips = clips
                                .into_iter()
                                .map(|(track, mut clip)| {
                                    forget(&mut clip, &[CHAINS]);
                                    forget(&mut clip, &SHAPE_SETTINGS);
                                    (track, clip)
                                })
                                .collect();
                            scene.set(TRACKS, Data::Map(clips));
                        }
                        scene
                    })
                    .collect();
                song.set(SCENES, Data::List(scenes));
            }
            kept.push((name, song));
        }
        set.set(SONGS, Data::Map(kept));
    }
    set
}

/// The tracks whose clip in a scene plays a pattern whose statements read the draws.
fn marked_tracks(setlist: &Setlist, song: &Song, index: usize) -> Vec<String> {
    let Some(scene) = song.scenes().get(index) else { return Vec::new() };
    song.get_track_names()
        .into_iter()
        .filter(|name| {
            scene.get_clip_slot(name).is_some_and(|clip| {
                setlist.get_pattern(&clip.get_pattern_name()).is_some_and(|pattern| {
                    STATEMENT_OF_ROW
                        .iter()
                        .any(|(row, _)| pattern.row(row).is_some_and(|steps| steps.iter().any(|step| !step.is_null())))
                })
            })
        })
        .map(str::to_string)
        .collect()
}

/// A scene's notes as played, the song's render, or as written, its patterns alone, its repeats laid end to end from the
/// scene's start, its random parts drawn afresh, or from a seed where one is given; a scene that cannot be played says why.
pub fn scene_notes(setlist: &Setlist, song_name: &str, index: usize, written: bool, seed: Option<i64>) -> Result<SceneNotes, String> {
    let held;
    let rendered_set = if written {
        held = Setlist::from_data(&as_written(&setlist.to_data())).map_err(|problem| problem.message)?;
        &held
    } else {
        setlist
    };
    let song = rendered_set.get_song(song_name).ok_or_else(|| song_name.to_string())?;
    let realizer = SongRealizer::new(rendered_set, song, seed).looping_scenes_go_round();
    let grid = realizer.render().map_err(|problem| format!("{problem:?}"))?;
    let mut starts = Vec::new();
    let mut now = Rational::ZERO;
    for row in &grid.rows {
        starts.push(now);
        let mut longest = Rational::ZERO;
        for (_, clip) in &row.clips {
            longest = longest.max(clip.total_length().map_err(|problem| format!("{problem:?}"))?);
        }
        now = now + longest;
    }
    let places = realizer.rows_of_scene(index);
    let names: Vec<String> = song.get_track_names().into_iter().map(str::to_string).collect();
    let marked = marked_tracks(setlist, song, index);
    let origin = places.first().map_or(Rational::ZERO, |place| starts[*place]);
    let mut notes = Vec::new();
    let mut end = origin;
    for place in &places {
        let row = &grid.rows[*place];
        let mut longest = Rational::ZERO;
        for (_, clip) in &row.clips {
            longest = longest.max(clip.total_length().map_err(|problem| format!("{problem:?}"))?);
        }
        for column in &grid.columns {
            let track = &column.name;
            let Some((_, clip)) = row.clips.iter().find(|(name, _)| name == track) else {
                continue;
            };
            let Some(number) = names.iter().position(|name| name == track) else {
                continue;
            };
            let drum = column.drum;
            let (events, _) = timed_events(clip, clip.scale.as_ref()).map_err(|problem| format!("{problem:?}"))?;
            for event in events {
                notes.push(SceneNote {
                    track: number,
                    start: starts[*place] - origin + event.start,
                    end: starts[*place] - origin + event.end,
                    pitch: event.midi_number,
                    drum,
                    marked: marked.contains(track),
                });
            }
        }
        end = end.max(starts[*place] + longest);
    }
    let signature = song.get_time_signature();
    Ok(SceneNotes {
        marked_tracks: marked.iter().filter_map(|name| names.iter().position(|each| each == name)).collect(),
        names,
        notes,
        length: end - origin,
        beat: signature.beat_length(),
        bar: signature.bar_length(),
    })
}

/// What a scene plays with in the end, and where each comes from: its tempo, scale and groove, each with its source, and
/// each track whose clip takes a scale of its own.
pub struct Effective {
    pub tempo: String,
    pub tempo_source: &'static str,
    pub scale: Option<String>,
    pub scale_source: &'static str,
    pub groove: String,
    pub groove_source: &'static str,
    pub clip_scales: Vec<(String, String)>,
}

/// A tempo as text, such as 120 or 120.5.
fn tempo_text(tempo: Rational) -> String {
    if tempo.denominator() == 1 {
        tempo.numerator().to_string()
    } else {
        llamatron_strings::fill::python_float(tempo.to_float())
    }
}

/// The tempo, scale and groove a scene plays with and where each comes from, and the tracks whose clips take scales of
/// their own.
pub fn effective_values(song: &Song, index: usize) -> Option<Effective> {
    let scene = song.scenes().get(index)?;
    let written = |name: &str| scene.get_written(name).filter(|value| !value.is_null());
    let mut tempo = tempo_text(llamatron_engine::realizer::tempo_in(scene, song));
    let mut tempo_source = if written(SceneSetting::TEMPO).is_some() {
        marks::MSG_SCENE_VIEW_FROM_SCENE
    } else {
        marks::MSG_SCENE_VIEW_FROM_SONG
    };
    if llamatron_engine::realizer::ramps_tempo(scene, song) {
        tempo = named(marks::MSG_SCENE_VIEW_TEMPO_RAMPS, &[(fill::TEMPO, tempo.as_str().into())]);
        tempo_source = marks::MSG_SCENE_VIEW_FROM_SCENE;
    }
    let own_scale = written(SceneSetting::SCALE).and_then(Data::as_str).map(str::to_string);
    let scale = own_scale.clone().or_else(|| song.get_scale_name());
    let scale_source = if own_scale.is_some() {
        marks::MSG_SCENE_VIEW_FROM_SCENE
    } else {
        marks::MSG_SCENE_VIEW_FROM_SONG
    };
    let (groove, groove_source) = match written(SceneSetting::GROOVE) {
        None => (
            song.get_written(SongSetting::GROOVE)
                .and_then(Data::as_str)
                .unwrap_or(llamatron_model::schema::generated::defaults::DEFAULT_GROOVE)
                .to_string(),
            marks::MSG_SCENE_VIEW_FROM_SONG,
        ),
        Some(Data::Bool(false)) => (marks::MSG_SCENE_VIEW_NO_GROOVE.to_string(), marks::MSG_SCENE_VIEW_FROM_SCENE),
        Some(choice) => (choice.as_str().unwrap_or_default().to_string(), marks::MSG_SCENE_VIEW_FROM_SCENE),
    };
    let mut clip_scales = Vec::new();
    for name in song.get_track_names() {
        if let Some(clip_scale) = scene
            .get_clip_slot(name)
            .and_then(|clip| clip.get_written(file_format::SongSetting::SCALE))
            .and_then(Data::as_str)
        {
            if Some(clip_scale.to_string()) != scale {
                clip_scales.push((name.to_string(), clip_scale.to_string()));
            }
        }
    }
    Some(Effective {
        tempo,
        tempo_source,
        scale,
        scale_source,
        groove,
        groove_source,
        clip_scales,
    })
}

/// The scale a set names, for hearing chords in.
pub fn chord_scale(setlist: &Setlist, name: &str) -> Option<crate::chord_text::ChordScale> {
    match setlist.get_item(llamatron_model::schema::generated::file_format::Section::SCALES, name) {
        Some(llamatron_model::objects::setlist::Item::Scale(scale)) => {
            crate::chord_text::ChordScale::new(&crate::patterns::scale_root(setlist, name), scale.get_kind().as_str()?)
        }
        _ => None,
    }
}
