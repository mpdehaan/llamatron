// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Arrange's details (the Python screens/arrange/arrange_details.py): under each track's name, scene's bar and clip's bar,
//! the chains it runs and the settings that are not their defaults, and the room the columns and rows need for them.

use crate::app::App;
use crate::drawing::fit;
use crate::screens::arrange::arrange_tabs::chain_names;
use crate::screens::arrange::grid::Kind;
use crate::settings::named_in;
use crate::themes::{self, Colour};
use llamatron_math::rational::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::{ClipSlot, Scene, Song, Track};
use llamatron_model::schema::generated::defaults::DEFAULT_FOLLOW_ACTION;
use llamatron_model::schema::generated::file_format::{
    ClipSlotSetting, SceneSetting, Section, SetlistSetting, SongSetting, TrackSetting, PLACED_SHAPES, TEMPO_RAMP_SETTINGS, VELOCITY_SETTINGS,
};
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_strings::{labels, marks, named};
use std::collections::HashMap;

/// How wide a line of details may be.
pub const DETAIL_WIDTH: usize = 24;
/// What the + under a cell's chains adds, which names no section.
pub const ADD_CHAIN: &str = "add chain";
const UNCHANGED: i64 = 100;
const DEFAULT_REPEAT: i64 = 1;

/// What a line of details names, which ENTER opens: a section's thing by its name, a chain by its place among the cell's.
#[derive(Clone, Debug, PartialEq)]
pub struct Target {
    pub kind: &'static str,
    pub name: String,
    pub place: Option<usize>,
}

/// One line of a cell's details: its text, cut to the details' width, how it is drawn, and what it names.
#[derive(Clone, Debug)]
pub struct DetailLine {
    pub text: String,
    pub kind: Kind,
    pub target: Option<Target>,
}

impl DetailLine {
    /// The colour a line naming a thing is drawn in, its kind's pages' colour, or None.
    pub fn colour(&self) -> Option<Colour> {
        let kind = self.target.as_ref()?.kind;
        if kind == Section::CHAINS || PLUGINS.iter().any(|plugin| plugin.section == kind || plugin.name == kind) {
            return Some(themes::GENERATORS);
        }
        match kind {
            Section::SCALES => Some(themes::SCALES),
            Section::GROOVES => Some(themes::GROOVES),
            Section::INSTRUMENTS => Some(themes::INSTRUMENTS),
            Section::PATTERNS => Some(themes::PATTERNS),
            _ => None,
        }
    }
}

/// A cell of the grid: a track's name, a scene's, or a clip by its scene's place and its track.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum CellPlace {
    Track(String),
    Scene(usize),
    Clip(usize, String),
}

/// The current song's details and the room they need.
pub struct DetailsLayout {
    pub track_details: Vec<Vec<DetailLine>>,
    pub track_widths: Vec<usize>,
    pub scene_details: Vec<Vec<DetailLine>>,
    pub clip_details: HashMap<(usize, String), Vec<DetailLine>>,
    pub clip_names: HashMap<(usize, String), String>,
    pub scene_extra_lines: Vec<usize>,
    pub header_extra_lines: usize,
    pub cell_widths: HashMap<CellPlace, usize>,
}

fn detail(text: String, kind: Kind, target: Option<Target>) -> DetailLine {
    let text = if text.chars().count() > DETAIL_WIDTH {
        fit(&text, DETAIL_WIDTH).trim_end().to_string()
    } else {
        text
    };
    DetailLine { text, kind, target }
}

fn plain(text: String) -> DetailLine {
    detail(text, Kind::Plain, None)
}

fn whole(value: Option<&Data>) -> Option<i64> {
    value.filter(|value| !value.is_null()).and_then(Data::as_whole).map(|whole| whole as i64)
}

fn text(value: Option<&Data>) -> Option<String> {
    value.filter(|value| !value.is_null()).and_then(Data::as_str).map(str::to_string)
}

fn chain_lines(chains: Option<&Data>) -> Vec<DetailLine> {
    let mut lines: Vec<DetailLine> = chain_names(chains)
        .into_iter()
        .enumerate()
        .map(|(place, name)| {
            let shown = named(marks::MSG_DETAILS_CHAIN, &[("name", name.as_str().into())]);
            detail(
                shown,
                Kind::Plain,
                Some(Target {
                    kind: Section::CHAINS,
                    name,
                    place: Some(place),
                }),
            )
        })
        .collect();
    lines.push(detail(
        marks::MSG_DETAILS_ADD_CHAIN.to_string(),
        Kind::Faint,
        Some(Target {
            kind: ADD_CHAIN,
            name: String::new(),
            place: None,
        }),
    ));
    lines
}

fn velocity_lines(written: &dyn Fn(&str) -> Option<Data>) -> Vec<DetailLine> {
    if VELOCITY_SETTINGS.iter().all(|name| written(name).is_none()) {
        return Vec::new();
    }
    let level = written(VELOCITY_SETTINGS[0])
        .as_ref()
        .and_then(Data::as_whole)
        .map_or(UNCHANGED, |whole| whole as i64);
    let ramps = VELOCITY_SETTINGS[1..].iter().any(|name| written(name).is_some());
    let line = if ramps {
        marks::MSG_DETAILS_VELOCITY_RAMPS
    } else {
        marks::MSG_DETAILS_VELOCITY
    };
    let percent = named(marks::MSG_PERCENT_SHOWN, &[("percent", level.into())]);
    vec![plain(named(line, &[("percent", percent.as_str().into())]))]
}

fn shape_lines(written: &dyn Fn(&str) -> Option<Data>) -> Vec<DetailLine> {
    let mut lines = Vec::new();
    for shape in PLACED_SHAPES {
        let start = written(&format!("{shape}_start"));
        let end = written(&format!("{shape}_end"));
        if start.is_none() && end.is_none() {
            continue;
        }
        let value = |value: Option<Data>| value.as_ref().and_then(Data::as_whole).map_or(UNCHANGED, |whole| whole as i64);
        let shape_name = named_in(marks::MSG_DETAILS_SHAPE_NAMES, shape);
        lines.push(plain(named(
            marks::MSG_DETAILS_SHAPE,
            &[
                ("shape", shape_name.as_str().into()),
                ("start", value(start).into()),
                ("end", value(end).into()),
            ],
        )));
    }
    lines
}

fn groove_lines(choice: Option<&Data>) -> Vec<DetailLine> {
    match choice {
        None | Some(Data::Null) => Vec::new(),
        Some(Data::Bool(false)) => vec![plain(marks::MSG_DETAILS_NO_GROOVE.to_string())],
        Some(value) => {
            let name = value.as_str().unwrap_or("").to_string();
            let shown = named(marks::MSG_DETAILS_GROOVE, &[("name", name.as_str().into())]);
            vec![detail(
                shown,
                Kind::Plain,
                Some(Target {
                    kind: Section::GROOVES,
                    name,
                    place: None,
                }),
            )]
        }
    }
}

fn scale_lines(song: &Song, name: Option<String>) -> Vec<DetailLine> {
    match name {
        Some(name) if Some(&name) != song.get_scale_name().as_ref() => {
            let shown = named(marks::MSG_DETAILS_SCALE, &[("name", name.as_str().into())]);
            vec![detail(
                shown,
                Kind::Plain,
                Some(Target {
                    kind: Section::SCALES,
                    name,
                    place: None,
                }),
            )]
        }
        _ => Vec::new(),
    }
}

pub fn clip_lines(setlist: &Setlist, song: &Song, clip: &ClipSlot) -> Vec<DetailLine> {
    let written = |name: &str| clip.get_written(name).filter(|value| !value.is_null()).cloned();
    let mut lines = chain_lines(clip.get_written(ClipSlotSetting::CHAINS));
    lines.extend(scale_lines(song, text(clip.get_written(ClipSlotSetting::SCALE))));
    if let Some(pattern) = text(clip.get_written(ClipSlotSetting::MORPH_TO)) {
        lines.push(plain(named(marks::MSG_DETAILS_MORPH, &[("pattern", pattern.as_str().into())])));
    }
    if let Some(direction) = text(clip.get_written(ClipSlotSetting::DIRECTION)) {
        if let Some((_, shown)) = marks::MSG_DETAILS_DIRECTION_NAMES.iter().find(|(found, _)| *found == direction) {
            lines.push(plain(named(marks::MSG_DETAILS_DIRECTION, &[("direction", (*shown).into())])));
        }
    }
    if let Some(track) = text(clip.get_written(ClipSlotSetting::GRAB_TRACK)) {
        lines.push(plain(named(marks::MSG_DETAILS_GRAB, &[("track", track.as_str().into())])));
    }
    if let Some(action) = text(clip.get_written(ClipSlotSetting::FOLLOW_ACTION)) {
        let default = text(setlist.get_written(SetlistSetting::DEFAULT_FOLLOW_ACTION)).unwrap_or_else(|| DEFAULT_FOLLOW_ACTION.to_string());
        if action != default {
            let shown = named_in(labels::MSG_FOLLOW_ACTION_NAMES, &action);
            lines.push(plain(named(marks::MSG_DETAILS_ADVANCE, &[("action", shown.as_str().into())])));
        }
    }
    lines.extend(velocity_lines(&written));
    lines.extend(shape_lines(&written));
    lines
}

fn rational(value: Option<&Data>) -> Option<Rational> {
    value
        .filter(|value| !value.is_null())
        .and_then(|value| llamatron_model::schema::checking::number(value).ok())
}

fn tempo_text(tempo: Rational) -> String {
    if tempo.denominator() == 1 {
        tempo.numerator().to_string()
    } else {
        llamatron_strings::fill::python_float(tempo.to_float())
    }
}

fn scene_lines(song: &Song, scene: &Scene) -> Vec<DetailLine> {
    let written = |name: &str| scene.get_written(name).filter(|value| !value.is_null()).cloned();
    let mut lines = chain_lines(scene.get_written(SceneSetting::CHAINS));
    lines.extend(scale_lines(song, text(scene.get_written(SceneSetting::SCALE))));
    let song_tempo = rational(song.get_written(SongSetting::TEMPO)).unwrap_or(Rational::whole(120));
    let own = rational(scene.get_written(SceneSetting::TEMPO));
    let tempo = tempo_text(own.map_or(song_tempo, |percent| song_tempo * percent / Rational::whole(100)));
    let ramp = |way: &str, part: &str| {
        TEMPO_RAMP_SETTINGS
            .iter()
            .find(|(key, _)| key[0] == way && key[1] == part)
            .and_then(|(_, setting)| written(setting))
    };
    let ramps = ["in", "out"]
        .iter()
        .any(|way| ramp(way, "over").is_some() && (ramp(way, "start").is_some() || ramp(way, "end").is_some()));
    if ramps {
        lines.push(plain(named(marks::MSG_DETAILS_TEMPO_RAMPS, &[("tempo", tempo.as_str().into())])));
    } else if own.is_some() {
        lines.push(plain(named(marks::MSG_DETAILS_TEMPO, &[("tempo", tempo.as_str().into())])));
    }
    lines.extend(groove_lines(scene.get_written(SceneSetting::GROOVE)));
    lines.extend(velocity_lines(&written));
    lines.extend(shape_lines(&written));
    lines
}

pub fn track_lines(track: &Track) -> Vec<DetailLine> {
    let mut lines = chain_lines(track.get_written(TrackSetting::CHAINS));
    if let Some(instrument) = track.get_instrument_name() {
        let shown = named(marks::MSG_DETAILS_INSTRUMENT, &[("name", instrument.as_str().into())]);
        lines.push(detail(
            shown,
            Kind::Plain,
            Some(Target {
                kind: Section::INSTRUMENTS,
                name: instrument,
                place: None,
            }),
        ));
    }
    let transpose = whole(track.get_written(TrackSetting::TRANSPOSE)).unwrap_or(0);
    if transpose != 0 {
        lines.push(plain(named(marks::MSG_DETAILS_TRANSPOSE, &[("amount", transpose.into())])));
    }
    lines.extend(groove_lines(track.get_written(TrackSetting::GROOVE)));
    if matches!(track.get_written(TrackSetting::MUTE), Some(Data::Bool(true))) {
        lines.push(plain(marks::MSG_DETAILS_MUTED.to_string()));
    }
    lines
}

/// The lines, with "stock" first where nothing is set but the + that adds a chain.
pub fn or_stock(lines: Vec<DetailLine>) -> Vec<DetailLine> {
    if lines.iter().all(|line| line.target.as_ref().is_some_and(|target| target.kind == ADD_CHAIN)) {
        let mut stocked = vec![detail(marks::MSG_DETAILS_STOCK.to_string(), Kind::Stock, None)];
        stocked.extend(lines);
        return stocked;
    }
    lines
}

/// A clip as the details view names it: its name whole, with its loop and repeat marks.
pub fn detailed_clip_text(clip: &ClipSlot) -> String {
    let mut shown = Vec::new();
    if clip.loops() {
        shown.push(marks::MSG_LOOP_MARK.to_string());
    }
    if clip.get_repeat() > DEFAULT_REPEAT {
        shown.push(named(marks::MSG_REPEAT_MARK, &[("repeat", clip.get_repeat().into())]));
    }
    let name = crate::screens::arrange::arrange_page::shown_name(&clip.get_display_name());
    if shown.is_empty() {
        return name;
    }
    named(
        marks::MSG_CLIP_WITH_MARKS,
        &[
            ("name", name.as_str().into()),
            ("marks", shown.join(marks::MSG_DETAILS_MARKS_SEPARATOR).as_str().into()),
        ],
    )
}

/// The rooms a cell keeps beside its text: the least width of a column, beside a clip's name, beside a detail, and beside a
/// track's name.
pub struct Rooms {
    pub least_width: usize,
    pub name_room: usize,
    pub detail_room: usize,
    pub track_name_room: usize,
}

/// The current song's details and the room they need.
pub fn details_layout(app: &App, rooms: &Rooms) -> DetailsLayout {
    let setlist = app.document.get_setlist();
    let song = app.document.song();
    // In Arrange's order, the melodic tracks first and then the drum tracks.
    let names: Vec<String> = song.shown_tracks().iter().map(|(name, _)| name.clone()).collect();
    let in_tracks: Vec<Vec<DetailLine>> = song.shown_tracks().iter().map(|(_, track)| or_stock(track_lines(track))).collect();
    let in_scenes: Vec<Vec<DetailLine>> = song.scenes().iter().map(|scene| or_stock(scene_lines(song, scene))).collect();
    let longest = |lines: &[DetailLine]| lines.iter().map(|line| line.text.chars().count() + rooms.detail_room).max().unwrap_or(0);
    let mut cells = HashMap::new();
    for (name, lines) in names.iter().zip(&in_tracks) {
        let width = rooms
            .least_width
            .max(name.chars().count().min(DETAIL_WIDTH) + rooms.track_name_room)
            .max(longest(lines));
        cells.insert(CellPlace::Track(name.clone()), width);
    }
    let mut widths: Vec<usize> = names.iter().map(|name| cells[&CellPlace::Track(name.clone())]).collect();
    let mut clip_details = HashMap::new();
    let mut clip_names = HashMap::new();
    let mut extra = Vec::new();
    for (index, scene) in song.scenes().iter().enumerate() {
        let mut tallest = in_scenes[index].len();
        for (place, name) in names.iter().enumerate() {
            let Some(clip) = scene.get_clip_slot(name) else { continue };
            let lines = or_stock(clip_lines(setlist, song, clip));
            let shown = detailed_clip_text(clip);
            tallest = tallest.max(lines.len());
            let width = rooms.least_width.max(shown.chars().count() + rooms.name_room).max(longest(&lines));
            cells.insert(CellPlace::Clip(index, name.clone()), width);
            widths[place] = widths[place].max(width);
            clip_details.insert((index, name.clone()), lines);
            clip_names.insert((index, name.clone()), shown);
        }
        extra.push(tallest);
    }
    let header = in_tracks.iter().map(Vec::len).max().unwrap_or(0);
    DetailsLayout {
        track_details: in_tracks,
        track_widths: widths,
        scene_details: in_scenes,
        clip_details,
        clip_names,
        scene_extra_lines: extra,
        header_extra_lines: header,
        cell_widths: cells,
    }
}
