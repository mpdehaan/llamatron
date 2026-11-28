// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Arrange (the Python screens/arrange/arrange_page.py and arrange_drawing.py): the current song's scenes down and tracks
//! across, each clip with its pattern and a bar as long as it plays, the cursor's cell in a double-lined frame, and the
//! keys of what the cursor is on; its details view, Move mode, and Scene View (scene_view.rs) over the page.

#[path = "arrange_edits.rs"]
mod edits;
use crate::app::App;
use crate::drawing::{fit, fit_aligned, Align, Style};
use crate::keybindings::{ArrangePage as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::lengths::Lengths;
use crate::page::{clock, Duration, Page};
use crate::screens::arrange::details::{detailed_clip_text, details_layout, CellPlace, DetailLine, DetailsLayout, Rooms, Target, ADD_CHAIN, DETAIL_WIDTH};
use crate::screens::arrange::grid::{arrange_lines, CellFrame, Kind, LengthBar, Piece};
use crate::screens::arrange::scene_view::SceneView;
use crate::text::Text;
use crate::themes::Colour;
use crate::visualizers::{self, showing::Showing};
pub use edits::new_pattern_steps;
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::{ClipSlot, Scene};
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, SceneSetting, TrackSetting};
use llamatron_strings::{labels, legends, marks, messages, named, names};
use std::cell::Cell;

const HEADER_ROW: i64 = -1;
const SCENE_COLUMN: usize = 0;
const FIRST_TRACK_COLUMN: usize = 1;

/// What a column of Arrange after the scene names holds: a track, or the + that adds a track of its kind at the end of its
/// group.
#[derive(Clone, PartialEq, Eq, Debug)]
enum Place {
    Track(String),
    Add { drum: bool },
}
const SCENE_WIDTH: usize = 25;
const CELL_WIDTH: usize = 13;
const SCENE_FRAME_RIGHT: usize = SCENE_WIDTH - 2;
const SCENE_LABEL_COLUMN: usize = 1;
const SCENE_LABEL_WIDTH: usize = SCENE_WIDTH - 3;
const SCENE_BAR_COLUMN: usize = 3;
const PLAY_BUTTON_WIDTH: usize = 2;
const SOUNDING_MARK_WIDTH: usize = 2;
/// The room a muted or soloed track's M or S takes at the end of its heading, the letter and a space before the next.
const MARK_ROOM: usize = 2;
const HEADER_LINES: usize = 4;
const SCENE_LINES: usize = 5;
const LINES_UNDER_A_SCENE: usize = 2;
const FRAME_ROOM: usize = 2;
const COLUMN_EXTRA: usize = 2 * FRAME_ROOM + 1;
const DEFAULT_REPEAT: i64 = 1;
/// In the details view, the room a column keeps beside its text: a space before a clip's name and one after; the indent of a
/// detail under its bar and one after; and a space before a track's name, the sounding light and one after. And where each kind
/// of line is written.
const ROOMS: Rooms = Rooms {
    least_width: CELL_WIDTH,
    name_room: 2,
    detail_room: 2 + PLAY_BUTTON_WIDTH,
    track_name_room: 2 + SOUNDING_MARK_WIDTH,
};
const DETAIL_INDENT: usize = 1 + PLAY_BUTTON_WIDTH;
const TRACK_DETAIL_INDENT: usize = 1;
/// The lines of a scene before its details: the frame's room, the name and the bar.
const FIRST_DETAIL_LINE: usize = 3;
/// How long a scene's detail may be under its bar, leaving room for a pick's brackets before the scene column's divider.
const SCENE_DETAIL_ROOM: usize = SCENE_WIDTH - SCENE_BAR_COLUMN - 3;

/// What T cut: the cursor's scene, track or clip.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Moving {
    Scene,
    Track,
    Clip,
}

/// What T cut: a scene, track or clip, the row it stood on and the track whose column it was in.
#[derive(Clone, Debug, PartialEq, Eq)]
struct Cut {
    what: Moving,
    row: usize,
    track: String,
}

pub struct ArrangePage {
    /// Scene View, an Inset Window over the page, while it shows.
    inset: Option<SceneView>,
    /// The clip copied with C, which V pastes.
    copied: Option<ClipSlot>,
    /// Whether Tab has locked into the cursor's cell, the place among its lines that name something of the one picked, and
    /// in the usual view the cell Tab opened, which alone shows its details until Tab again.
    locked: bool,
    picked: Option<usize>,
    opened: Option<CellPlace>,
    /// What T cut, and from where, which P pastes where the cursor then is, or ESC lets go of.
    cut: Option<Cut>,
    row: Cell<i64>,
    column: Cell<usize>,
    top: Cell<usize>,
    left: Cell<usize>,
    /// The visualizer over the clip area while it shows, which draws a frame every time the page is drawn.
    visualizer: std::cell::RefCell<Option<Showing>>,
}

/// Where the clip area starts, right of the scene names and their bar, which a visualizer's frame covers.
const CLIP_AREA_LEFT: usize = SCENE_WIDTH + 1;
/// How many lines above the bottom a visualizer mode's name shows.
const NAME_ROWS_UP: usize = 2;

impl Default for ArrangePage {
    fn default() -> Self {
        ArrangePage::new()
    }
}

/// A clip's name as its cell shows it, with the marks of what it does beyond playing its pattern.
/// A name as a page shows it: whole, or cut to the most characters a name is shown with and ended with an ellipsis.
pub fn shown_name(name: &str) -> String {
    let most = llamatron_model::schema::generated::limits::MAX_NAME_LENGTH as usize;
    if name.chars().count() <= most {
        return name.to_string();
    }
    let cut: String = name.chars().take(most - 1).collect();
    format!("{cut}{}", marks::MSG_NAME_CUT)
}

fn clip_text(clip: &ClipSlot, repeats_left: Option<i64>) -> String {
    let name = clip.get_display_name();
    let mut shown = String::new();
    if clip.get_direction().is_some() {
        shown.push_str(marks::MSG_DIRECTION_MARK);
    }
    if clip.get_written(ClipSlotSetting::GRAB_TRACK).is_some_and(|value| !value.is_null()) {
        shown.push_str(marks::MSG_GRAB_MARK);
    }
    if clip.get_written(ClipSlotSetting::MORPH_TO).is_some_and(|value| !value.is_null()) {
        shown.push_str(marks::MSG_MORPH_MARK);
    }
    if clip.loops() {
        shown.push_str(marks::MSG_LOOP_MARK);
    }
    if clip.get_repeat() > DEFAULT_REPEAT {
        shown.push_str(&named(
            marks::MSG_REPEAT_MARK,
            &[("repeat", repeats_left.unwrap_or_else(|| clip.get_repeat()).into())],
        ));
    }
    if shown.is_empty() {
        return name;
    }
    let room = (CELL_WIDTH as i64 - shown.chars().count() as i64 - 2).max(1) as usize;
    named(
        marks::MSG_CLIP_WITH_MARKS,
        &[("name", fit(&name, room).trim_end().into()), ("marks", shown.as_str().into())],
    )
}

pub fn scene_name(scene: &Scene, index: usize) -> String {
    scene
        .get_name()
        .unwrap_or_else(|| named(names::MSG_NEW_SCENE_NAME, &[("number", (index + 1).into())]))
}

impl ArrangePage {
    pub fn new() -> ArrangePage {
        ArrangePage {
            inset: None,
            copied: None,
            locked: false,
            picked: None,
            opened: None,
            cut: None,
            row: Cell::new(0),
            column: Cell::new(SCENE_COLUMN),
            top: Cell::new(0),
            left: Cell::new(0),
            visualizer: std::cell::RefCell::new(None),
        }
    }

    /// The visualizer modes the key steps through, every mode built but those the set hides, in order.
    fn shown_modes(app: &App) -> Vec<&'static str> {
        let hidden = crate::settings::hidden_visualizers(app.document.get_setlist());
        visualizers::ported_modes()
            .into_iter()
            .filter(|mode| !hidden.iter().any(|each| each == mode))
            .collect()
    }

    /// The mode the visualizer key shows first: the song's choice, else the set's, when it is shown, and otherwise the first
    /// shown.
    fn first_mode(app: &App, shown: &[&'static str]) -> Option<&'static str> {
        use llamatron_model::schema::generated::file_format::{SetlistSetting, SongSetting};
        let song = app.document.song();
        let set = app.document.get_setlist();
        let chosen = song
            .get_written(SongSetting::VISUALIZER)
            .or_else(|| set.get_written(SetlistSetting::VISUALIZER))
            .and_then(|value| value.as_str())
            .and_then(|name| shown.iter().find(|mode| **mode == name).copied());
        chosen.or_else(|| shown.first().copied())
    }

    /// Show a visualizer mode over the clip area, fresh.
    pub fn show_visualizer(&self, app: &App, mode: &str) {
        let hidden = crate::settings::hidden_visualizers(app.document.get_setlist());
        *self.visualizer.borrow_mut() = Showing::of(mode, &hidden);
    }

    /// Show the first mode, or the next one shown, or the clips again after the last.
    fn next_visualizer(&self, app: &mut App) {
        let shown = Self::shown_modes(app);
        if shown.is_empty() {
            app.say(messages::MSG_EVERY_VISUALIZER_HIDDEN);
            return;
        }
        let showing = self.visualizer.borrow().as_ref().map(Showing::option);
        let next = match showing {
            None => Self::first_mode(app, &shown),
            Some(option) => shown.iter().position(|mode| *mode == option).and_then(|place| shown.get(place + 1)).copied(),
        };
        match next {
            Some(mode) => self.show_visualizer(app, mode),
            None => *self.visualizer.borrow_mut() = None,
        }
    }

    /// Show the mode before or after the one showing among those shown, going round, as [ and ] step through a cycle.
    fn step_visualizer(&self, app: &App, direction: i64) {
        let shown = Self::shown_modes(app);
        if shown.is_empty() {
            return;
        }
        let showing = self.visualizer.borrow().as_ref().map(Showing::option);
        let place = showing.and_then(|option| shown.iter().position(|mode| *mode == option)).unwrap_or(0) as i64;
        let next = (place + direction).rem_euclid(shown.len() as i64) as usize;
        self.show_visualizer(app, shown[next]);
    }

    /// Whether a visualizer shows over the clip area.
    fn shows_visualizer(&self) -> bool {
        self.visualizer.borrow().is_some()
    }

    /// The page's lines with the visualizer's frame over the clip area, from below the track names to the last line, and
    /// the mode's name over it for a while when it changes.
    fn visualized(&self, app: &App, mut lines: Vec<Text>, header: usize, width: usize, height: usize) -> Vec<Text> {
        let mut held = self.visualizer.borrow_mut();
        let Some(showing) = held.as_mut() else { return lines };
        while lines.len() < height {
            lines.push(Text::default());
        }
        let area_height = lines.len().saturating_sub(header);
        let frame = showing.frame(app, width.saturating_sub(CLIP_AREA_LEFT), area_height);
        for (row, piece) in frame.iter().enumerate() {
            if let Some(line) = lines.get_mut(header + row) {
                *line = crate::screens::arrange::scene_view::laid_over(line, CLIP_AREA_LEFT, piece);
            }
        }
        if let Some(name) = showing.name_to_show() {
            if lines.len() > header + NAME_ROWS_UP {
                let row = lines.len() - 1 - NAME_ROWS_UP;
                let start = CLIP_AREA_LEFT + width.saturating_sub(CLIP_AREA_LEFT + name.cell_len()) / 2;
                lines[row] = crate::screens::arrange::scene_view::laid_over(&lines[row], start, &name);
            }
        }
        lines
    }

    /// The tracks' names as Arrange shows them, the melodic tracks first and then the drum tracks.
    fn tracks(app: &App) -> Vec<String> {
        app.document.song().shown_tracks().into_iter().map(|(name, _)| name.clone()).collect()
    }

    /// What each column after the scene names holds: the melodic tracks, then beyond the double line the drum tracks; a
    /// group with no tracks holds a + in their place, where I makes its first track.
    fn places(app: &App) -> Vec<Place> {
        let melodic = app.document.song().melodic_count();
        let names = Self::tracks(app);
        let group = |names: &[String], drum: bool| -> Vec<Place> {
            if names.is_empty() {
                vec![Place::Add { drum }]
            } else {
                names.iter().cloned().map(Place::Track).collect()
            }
        };
        let mut places = group(&names[..melodic], false);
        places.extend(group(&names[melodic..], true));
        places
    }

    /// The track a column holds, or None for a + column or past the end.
    fn track_at(app: &App, place: usize) -> Option<String> {
        match Self::places(app).into_iter().nth(place) {
            Some(Place::Track(name)) => Some(name),
            _ => None,
        }
    }

    /// The track under the cursor's column, or None on a + column.
    fn cursor_track(&self, app: &App) -> Option<String> {
        Self::track_at(app, self.track_place())
    }

    /// The column a track is in.
    fn place_of(app: &App, track: &str) -> Option<usize> {
        Self::places(app).iter().position(|place| *place == Place::Track(track.to_string()))
    }

    /// The first column of the drum group, at the double line's right: after the main tracks, or after the melodic +.
    fn drum_start(app: &App) -> usize {
        app.document.song().melodic_count().max(1)
    }

    /// The + column the cursor is on, by the kind of track it stands for, or None elsewhere.
    fn plus_here(&self, app: &App) -> Option<bool> {
        if !self.on_header() || self.on_corner() {
            return None;
        }
        match Self::places(app).into_iter().nth(self.track_place()) {
            Some(Place::Add { drum }) => Some(drum),
            _ => None,
        }
    }

    /// Whether the song plays in real time, which the play marks show: whether a track plays through an instrument that
    /// can sound.
    fn real_time_on(app: &App) -> bool {
        app.document.song().plays_in_real_time(app.document.get_setlist())
    }

    fn scene_count(app: &App) -> i64 {
        app.document.song().scenes().len() as i64
    }

    fn on_header(&self) -> bool {
        self.row.get() == HEADER_ROW
    }

    fn on_corner(&self) -> bool {
        self.on_header() && self.column.get() == SCENE_COLUMN
    }

    fn on_track_plus(&self, app: &App) -> bool {
        self.plus_here(app).is_some()
    }

    fn on_scene_name(&self) -> bool {
        !self.on_header() && self.column.get() == SCENE_COLUMN
    }

    fn in_a_track_column(&self) -> bool {
        self.column.get() != SCENE_COLUMN
    }

    fn track_place(&self) -> usize {
        self.column.get().saturating_sub(FIRST_TRACK_COLUMN)
    }

    fn clamp(&self, app: &App) {
        let row = self.row.get().clamp(HEADER_ROW, Self::scene_count(app) - 1);
        self.row.set(row);
        let last_column = Self::places(app).len() - 1 + FIRST_TRACK_COLUMN;
        if self.on_header() {
            let first = if Self::real_time_on(app) { SCENE_COLUMN } else { FIRST_TRACK_COLUMN };
            self.column.set(self.column.get().clamp(first, last_column));
            return;
        }
        // Under the header a + column holds nothing, so the cursor stops on the nearest track, or the scene's name.
        let mut column = self.column.get().min(last_column);
        if column != SCENE_COLUMN && !Self::column_holds_track(app, column) {
            let left = (FIRST_TRACK_COLUMN..column).rev().find(|each| Self::column_holds_track(app, *each));
            let right = (column + 1..=last_column).find(|each| Self::column_holds_track(app, *each));
            column = left.or(right).unwrap_or(SCENE_COLUMN);
        }
        self.column.set(column);
    }

    /// Whether a column of the grid holds a track rather than a +.
    fn column_holds_track(app: &App, column: usize) -> bool {
        column >= FIRST_TRACK_COLUMN && Self::track_at(app, column - FIRST_TRACK_COLUMN).is_some()
    }

    /// Under the header a + column holds nothing, so Left and Right pass over it onto the track beyond, or the scene's
    /// name, staying put where there is nothing beyond.
    fn step_over_plus(&self, app: &App, key: &str, from: usize) {
        if self.on_header() || !self.in_a_track_column() || Self::column_holds_track(app, self.column.get()) {
            return;
        }
        let last_column = Self::places(app).len() - 1 + FIRST_TRACK_COLUMN;
        let beyond = if key == "left" {
            (SCENE_COLUMN..self.column.get())
                .rev()
                .find(|each| *each == SCENE_COLUMN || Self::column_holds_track(app, *each))
        } else {
            (self.column.get() + 1..=last_column).find(|each| Self::column_holds_track(app, *each))
        };
        self.column.set(beyond.unwrap_or(from));
    }

    fn clip<'a>(app: &'a App, index: usize, track: &str) -> Option<&'a ClipSlot> {
        app.document.song().scenes().get(index)?.get_clip_slot(track)
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }

    fn header_keys(&self, app: &App) -> Vec<KeyItem> {
        if self.on_corner() {
            if app.transport.is_playing() {
                return vec![Self::bind(&Keys::STOP_PLAYING)];
            }
            return vec![Self::bind(&Keys::PLAY_SONG)];
        }
        if self.on_track_plus(app) {
            return [Self::bind(&Keys::INSERT_TRACK)].into_iter().chain(self.paste_key()).collect();
        }
        [
            &Keys::TRACK_SETTINGS,
            &Keys::COPY_TRACK,
            &Keys::INSERT_TRACK,
            &Keys::CUT_TRACK,
            &Keys::DELETE_TRACK,
        ]
        .into_iter()
        .map(Self::bind)
        .chain(self.mute_keys(app))
        .chain(self.paste_key())
        .collect()
    }

    fn scene_row_keys(&self, app: &App) -> Vec<KeyItem> {
        let mut keys = Vec::new();
        let real_time = Self::real_time_on(app);
        if self.on_scene_name() {
            if real_time {
                let row = self.row.get().max(0) as usize;
                if app.transport.playing_scenes().contains(&row) {
                    keys.push(Self::bind(&Keys::STOP_PLAYING));
                } else {
                    keys.push(Self::bind(&Keys::PLAY_SCENE));
                }
            }
            keys.extend(
                [
                    &Keys::SCENE_SETTINGS,
                    &Keys::SCENE_VIEW,
                    &Keys::CUT_SCENE,
                    &Keys::COPY_SCENE,
                    &Keys::DELETE_SCENE,
                ]
                .into_iter()
                .map(Self::bind),
            );
        } else if let Some(track) = self.cursor_track(app) {
            let track = &track;
            match Self::clip(app, self.row.get() as usize, track) {
                None => keys.extend([Self::bind(&Keys::ADD_CLIP), Self::bind(&Keys::BLANK_PATTERN)]),
                Some(_) => {
                    if real_time {
                        if app.transport.is_clip_playing(self.row.get().max(0) as usize, track) {
                            keys.push(Self::bind(&Keys::STOP_CLIP));
                        } else {
                            keys.push(Self::bind(&Keys::PLAY_CLIP));
                        }
                    }
                    keys.extend(
                        [&Keys::EDIT_CLIP, &Keys::OPEN_PATTERN, &Keys::CUT_CLIP, &Keys::COPY_CLIP, &Keys::DELETE_CLIP]
                            .into_iter()
                            .map(Self::bind),
                    );
                }
            }
        }
        keys.extend(self.mute_keys(app));
        if (self.copied.is_some() && !self.on_scene_name()) || self.cut.is_some() {
            keys.extend(self.paste_key());
        }
        keys.push(Self::bind(&Keys::INSERT_SCENE));
        keys
    }

    /// P, where something was cut or a clip copied.
    fn paste_key(&self) -> Vec<KeyItem> {
        if self.cut.is_some() || self.copied.is_some() {
            vec![Self::bind(&Keys::PASTE)]
        } else {
            Vec::new()
        }
    }

    /// Whether the cursor is on a cell with details: a track's name, a scene's name or a clip.
    /// Change the current song, as one edit of the set.
    fn change_song(app: &mut App, change: impl FnOnce(&mut llamatron_model::objects::song::Song)) {
        let name = app.document.get_current_song_name().to_string();
        app.document.change_set(|setlist| {
            if let Some(llamatron_model::objects::setlist::Item::Song(song)) =
                setlist.get_item_mut(llamatron_model::schema::generated::file_format::Section::SONGS, &name)
            {
                change(song);
            }
        });
    }

    /// Mark the scene, track or clip under the cursor as cut, for P to paste where the cursor then is; nothing moves until
    /// it is pasted, so that a cut and its paste are one step to undo.
    fn start_cut(&mut self, app: &mut App, what: Moving) {
        let row = self.row.get().max(0) as usize;
        let track = self.cursor_track(app).unwrap_or_default();
        let name = match what {
            Moving::Scene => named(
                messages::MSG_CUT_SCENE,
                &[("name", scene_name(&app.document.song().scenes()[row], row).as_str().into())],
            ),
            Moving::Track => named(messages::MSG_CUT_TRACK, &[("name", track.as_str().into())]),
            Moving::Clip => {
                let clip = Self::clip(app, row, &track).map_or(String::new(), ClipSlot::get_display_name);
                named(messages::MSG_CUT_CLIP, &[("name", clip.as_str().into())])
            }
        };
        self.cut = Some(Cut { what, row, track });
        app.say(&name);
    }

    /// Put what was cut where the cursor is: a scene before the scene under the cursor, a track before the track under it,
    /// a clip into the empty cell under it, as one step; what cannot go there is refused.
    fn paste_cut(&mut self, app: &mut App) {
        let Some(cut) = self.cut.take() else { return };
        let to_row = self.row.get().max(0) as usize;
        match cut.what {
            Moving::Scene => {
                // After the scene under the cursor, as I inserts one.
                let to = if to_row >= cut.row { to_row } else { to_row + 1 };
                Self::change_song(app, |song| {
                    let mut at = cut.row;
                    while at != to {
                        let step = if to > at { 1 } else { -1 };
                        song.move_scene(at, step);
                        at = (at as i64 + step) as usize;
                    }
                });
                self.row.set(to as i64);
            }
            Moving::Track => {
                // A track pastes only among its own kind, after the track under the cursor, as I inserts one.
                let drum = Self::is_drum_track(app, &cut.track);
                let after = match Self::places(app).into_iter().nth(self.track_place()) {
                    Some(Place::Track(name)) if Self::is_drum_track(app, &name) == drum => Some(name),
                    _ => None,
                };
                let Some(after) = after else {
                    self.cut = Some(cut);
                    app.refuse(messages::MSG_PASTE_TRACK_AMONG_ITS_KIND);
                    return;
                };
                let name = cut.track.clone();
                Self::change_song(app, |song| {
                    if after == name {
                        return;
                    }
                    let tracks = song.tracks();
                    let next = tracks
                        .iter()
                        .position(|(held, _)| *held == after)
                        .and_then(|at| tracks.get(at + 1))
                        .map(|(held, _)| held.clone());
                    // A track already right after the one under the cursor stays where it is.
                    if next.as_deref() != Some(name.as_str()) {
                        song.move_track_before(&name, next.as_deref());
                    }
                });
                if let Some(place) = Self::place_of(app, &name) {
                    self.column.set(place + FIRST_TRACK_COLUMN);
                }
            }
            Moving::Clip => {
                let Some(to_track) = self.cursor_track(app) else {
                    self.cut = Some(cut);
                    app.refuse(messages::MSG_PASTE_NEEDS_AN_EMPTY_CELL);
                    return;
                };
                if Self::clip(app, to_row, &to_track).is_some() {
                    self.cut = Some(cut);
                    app.refuse(messages::MSG_PASTE_NEEDS_AN_EMPTY_CELL);
                    return;
                }
                self.move_clip(app, (cut.row, &cut.track), (to_row, &to_track));
            }
        }
    }

    /// Move a clip from one cell to an empty one as one step, dropping its grab where grabbing there would go round in a
    /// circle, and saying so.
    fn move_clip(&mut self, app: &mut App, from: (usize, &str), to: (usize, &str)) {
        let ((from_row, from_track), (to_row, to_track)) = (from, to);
        let circles = |grab: &str| grab == to_track || Self::grab_circles(app, to_row, to_track, grab);
        let grab = Self::clip(app, from_row, from_track)
            .and_then(|clip| clip.get_written(ClipSlotSetting::GRAB_TRACK))
            .and_then(Data::as_str)
            .map(str::to_string);
        let dropped = grab.filter(|grab| circles(grab));
        let clears = dropped.is_some();
        let (from_track, to_track) = (from_track.to_string(), to_track.to_string());
        Self::change_song(app, |song| {
            if let Some(mut clip) = song.take_clip(from_row, &from_track) {
                if clears {
                    clip.set_written(ClipSlotSetting::GRAB_TRACK, None);
                }
                song.put_clip(to_row, &to_track, clip);
            }
        });
        if let Some(track) = dropped {
            app.say(&named(messages::MSG_PASTED_WITHOUT_GRAB, &[("track", track.as_str().into())]));
        }
    }

    /// The track the cursor's column belongs to, anywhere in the column, or None on the scene names.
    fn column_track(&self, app: &App) -> Option<String> {
        if !self.in_a_track_column() || self.on_corner() {
            return None;
        }
        self.cursor_track(app)
    }

    /// Whether a track is a drum track.
    fn is_drum_track(app: &App, track: &str) -> bool {
        app.document.song().get_track(track).is_some_and(|held| held.is_drum())
    }

    /// Whether a track is muted, or soloed.
    fn track_flag(app: &App, track: &str, setting: &str) -> bool {
        app.document
            .song()
            .get_track(track)
            .is_some_and(|held| held.get_written(setting) == Some(&Data::Bool(true)))
    }

    /// Whether a track is silent: muted, or another track soloed.
    fn is_silenced(app: &App, track: &str) -> bool {
        let soloing = Self::tracks(app).iter().any(|name| Self::track_flag(app, name, TrackSetting::SOLO));
        Self::track_flag(app, track, TrackSetting::MUTE) || (soloing && !Self::track_flag(app, track, TrackSetting::SOLO))
    }

    /// Mute or unmute the track of the cursor's column, the same Mute as its track editor's.
    fn toggle_mute(&self, app: &mut App, track: &str) {
        let muted = Self::track_flag(app, track, TrackSetting::MUTE);
        let track = track.to_string();
        Self::change_song(app, |song| {
            song.set_track_written(&track, TrackSetting::MUTE, (!muted).then_some(Data::Bool(true)))
        });
    }

    /// Solo the track of the cursor's column, lifting any other track's solo, since one track is soloed at a time; or lift
    /// its solo.
    fn toggle_solo(&self, app: &mut App, track: &str) {
        let soloed = Self::track_flag(app, track, TrackSetting::SOLO);
        let names = Self::tracks(app);
        let track = track.to_string();
        Self::change_song(app, |song| {
            for name in &names {
                let on = !soloed && *name == track;
                song.set_track_written(name, TrackSetting::SOLO, on.then_some(Data::Bool(true)));
            }
        });
    }

    /// The mute and solo keys for the track of the cursor's column, saying what each would do.
    fn mute_keys(&self, app: &App) -> Vec<KeyItem> {
        let Some(track) = self.column_track(app) else { return Vec::new() };
        let mute = if Self::track_flag(app, &track, TrackSetting::MUTE) {
            &Keys::UNMUTE_TRACK
        } else {
            &Keys::MUTE_TRACK
        };
        let solo = if Self::track_flag(app, &track, TrackSetting::SOLO) {
            &Keys::UNSOLO_TRACK
        } else {
            &Keys::SOLO_TRACK
        };
        vec![Self::bind(mute), Self::bind(solo)]
    }

    /// Whether a clip on a track of a scene grabbing from another track would go round in a circle: the other's clip there
    /// grabbing, on and on, from the track itself.
    pub fn grab_circles(app: &App, index: usize, track: &str, other: &str) -> bool {
        Self::grab_circle(app, index, track, other).is_some()
    }

    /// The circle a clip on a track of a scene grabbing from another track would make, the tracks in order from the track
    /// itself back to it, or None where the grabs end without coming back.
    pub fn grab_circle(app: &App, index: usize, track: &str, other: &str) -> Option<Vec<String>> {
        let mut circle = vec![track.to_string(), other.to_string()];
        let mut current = other.to_string();
        while let Some(next) = Self::clip(app, index, &current)
            .and_then(|clip| clip.get_written(ClipSlotSetting::GRAB_TRACK))
            .and_then(Data::as_str)
        {
            if next == track {
                circle.push(track.to_string());
                return Some(circle);
            }
            if circle.iter().any(|each| each == next) {
                return None;
            }
            circle.push(next.to_string());
            current = next.to_string();
        }
        None
    }

    fn start_picking(&mut self, app: &App) {
        self.locked = true;
        self.picked = (!self.pickable(app).is_empty()).then_some(0);
        if !Self::shows_details(app) {
            self.opened = self.cursor_cell(app);
        }
    }

    fn stop_picking(&mut self) {
        self.locked = false;
        self.picked = None;
        self.opened = None;
    }

    /// Open the page of what a picked line names: a chain's, a scale's, a groove's or an instrument's.
    fn open_target(&self, app: &mut App, target: Target) {
        use llamatron_model::schema::generated::file_format::Section;
        match target.kind {
            Section::CHAINS => app.show_page(Box::new(crate::screens::list_page::ListPage::new(
                crate::screens::generators::chain_editor::ChainEditor { name: target.name },
            ))),
            Section::SCALES => app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::set::scale_page::ScalePage { name: target.name },
            ))),
            Section::GROOVES => app.show_page(Box::new(crate::screens::one_row_editor::OneRowEditor::new(
                crate::screens::set::groove_editor::GrooveEditor { name: target.name },
            ))),
            Section::INSTRUMENTS => app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::set::instrument_editor::InstrumentEditor { name: target.name },
            ))),
            // The Add chain line is answered by its own key, so no other kind of line comes here.
            _ => {}
        }
    }

    /// Ask for one of the set's generators and add it to the cursor's cell alone, after the ones it runs.
    fn add_cell_chain(&self, app: &mut App) {
        use crate::screens::generators::generator_list_page::{ask_to_add, Holder};
        let Some(cell) = self.cursor_cell(app) else { return };
        let holder = match cell {
            CellPlace::Track(name) => Holder::Track(name),
            CellPlace::Scene(index) => Holder::Scene(index),
            CellPlace::Clip(index, track) => Holder::Clip(index, track),
        };
        ask_to_add(app, holder, false);
    }

    /// Take a chain out of the cursor's cell alone, the chain staying in the set.
    fn remove_cell_chain(&self, app: &mut App, place: usize) {
        use llamatron_model::schema::generated::file_format::TrackSetting;
        let Some(cell) = self.cursor_cell(app) else { return };
        let setting = match cell {
            CellPlace::Track(_) => TrackSetting::CHAINS,
            CellPlace::Scene(_) => SceneSetting::CHAINS,
            CellPlace::Clip(..) => ClipSlotSetting::CHAINS,
        };
        let song_name = app.document.get_current_song_name().to_string();
        let song = app.document.song();
        let written = match &cell {
            CellPlace::Track(name) => song.get_track(name).and_then(|track| track.get_written(setting)),
            CellPlace::Scene(index) => song.scenes().get(*index).and_then(|scene| scene.get_written(setting)),
            CellPlace::Clip(index, track) => Self::clip(app, *index, track).and_then(|clip| clip.get_written(setting)),
        };
        let mut names = crate::screens::arrange::arrange_tabs::chain_names(written);
        if place >= names.len() {
            return;
        }
        names.remove(place);
        let value = (!names.is_empty()).then(|| Data::List(names.into_iter().map(Data::Text).collect()));
        app.document.change_set(|setlist| {
            if let Some(llamatron_model::objects::setlist::Item::Song(song)) =
                setlist.get_item_mut(llamatron_model::schema::generated::file_format::Section::SONGS, &song_name)
            {
                match &cell {
                    CellPlace::Track(name) => song.set_track_written(name, setting, value),
                    CellPlace::Scene(index) => song.set_scene_written(*index, setting, value),
                    CellPlace::Clip(index, track) => song.set_clip_written(*index, track, setting, value),
                }
            }
        });
    }

    fn shows_details(app: &App) -> bool {
        app.session.shows_arrange_details
    }

    /// Whether any details show: every cell's in the details view, or the one Tab opened, so that columns and rows take
    /// their own sizes.
    fn widened(&self, app: &App) -> bool {
        Self::shows_details(app) || self.opened.is_some()
    }

    /// The current song's details and the room they need, where any show.
    fn layout(&self, app: &App) -> Option<DetailsLayout> {
        self.widened(app).then(|| details_layout(app, &ROOMS))
    }

    /// Whether a cell shows its details: every cell in the details view, and otherwise the one Tab opened.
    fn cell_open(&self, app: &App, cell: &CellPlace) -> bool {
        Self::shows_details(app) || self.opened.as_ref() == Some(cell)
    }

    /// The cell the cursor is on, a track's name, a scene's name or a clip, or None elsewhere.
    fn cursor_cell(&self, app: &App) -> Option<CellPlace> {
        if self.on_header() {
            return if self.on_corner() {
                None
            } else {
                self.cursor_track(app).map(CellPlace::Track)
            };
        }
        let row = self.row.get() as usize;
        if self.on_scene_name() {
            return Some(CellPlace::Scene(row));
        }
        let track = self.cursor_track(app)?;
        Self::clip(app, row, &track).map(|_| CellPlace::Clip(row, track.clone()))
    }

    /// The details of the cell the cursor is on, whether or not they show.
    fn details_at_cursor(&self, app: &App, layout: &DetailsLayout) -> Vec<DetailLine> {
        match self.cursor_cell(app) {
            Some(CellPlace::Track(name)) => Self::tracks(app)
                .iter()
                .position(|track| *track == name)
                .map_or(Vec::new(), |place| layout.track_details[place].clone()),
            Some(CellPlace::Scene(index)) => layout.scene_details[index].clone(),
            Some(CellPlace::Clip(index, track)) => layout.clip_details.get(&(index, track)).cloned().unwrap_or_default(),
            None => Vec::new(),
        }
    }

    /// The places among the cursor's cell's lines of the lines that name something.
    fn pickable(&self, app: &App) -> Vec<usize> {
        let layout = details_layout(app, &ROOMS);
        self.details_at_cursor(app, &layout)
            .iter()
            .enumerate()
            .filter(|(_, line)| line.target.is_some())
            .map(|(place, _)| place)
            .collect()
    }

    /// Whether Tab has locked into the cursor's cell, which a cell gone away ends.
    fn picking(&self, app: &App) -> bool {
        self.locked && self.cursor_cell(app).is_some()
    }

    /// The place among the cursor's cell's lines of the one picked, which is drawn in brackets.
    fn picked_line(&self, app: &App) -> Option<usize> {
        if !self.picking(app) {
            return None;
        }
        let pickable = self.pickable(app);
        let picked = self.picked?.min(pickable.len().checked_sub(1)?);
        pickable.get(picked).copied()
    }

    fn picked_target(&self, app: &App) -> Option<Target> {
        let place = self.picked_line(app)?;
        let layout = details_layout(app, &ROOMS);
        self.details_at_cursor(app, &layout).get(place).and_then(|line| line.target.clone())
    }

    fn track_width(&self, app: &App, layout: Option<&DetailsLayout>, place: usize) -> usize {
        let Some(layout) = layout else { return CELL_WIDTH };
        let Some(track) = Self::track_at(app, place) else { return CELL_WIDTH };
        if Self::shows_details(app) {
            let shown = Self::tracks(app).iter().position(|name| *name == track).unwrap_or(0);
            return layout.track_widths[shown];
        }
        match &self.opened {
            Some(CellPlace::Track(name)) if *name == track => layout.cell_widths.get(&CellPlace::Track(name.clone())).copied().unwrap_or(CELL_WIDTH),
            Some(CellPlace::Clip(index, name)) if *name == track => {
                layout.cell_widths.get(&CellPlace::Clip(*index, name.clone())).copied().unwrap_or(CELL_WIDTH)
            }
            _ => CELL_WIDTH,
        }
    }

    fn header_lines(&self, app: &App, layout: Option<&DetailsLayout>) -> usize {
        let Some(layout) = layout else { return HEADER_LINES };
        if Self::shows_details(app) {
            return HEADER_LINES + layout.header_extra_lines;
        }
        if let Some(CellPlace::Track(name)) = &self.opened {
            if let Some(place) = Self::tracks(app).iter().position(|track| track == name) {
                return HEADER_LINES + layout.track_details[place].len();
            }
        }
        HEADER_LINES
    }

    fn scene_lines(&self, app: &App, layout: Option<&DetailsLayout>, index: usize) -> usize {
        let Some(layout) = layout else { return SCENE_LINES };
        if Self::shows_details(app) {
            return SCENE_LINES + layout.scene_extra_lines[index];
        }
        match &self.opened {
            Some(CellPlace::Scene(opened)) if *opened == index => SCENE_LINES + layout.scene_details[index].len(),
            Some(CellPlace::Clip(opened, track)) if *opened == index => SCENE_LINES + layout.clip_details.get(&(index, track.clone())).map_or(0, Vec::len),
            _ => SCENE_LINES,
        }
    }

    /// Whether the scenes from first to last fit in room lines.
    fn rows_fit(&self, app: &App, layout: Option<&DetailsLayout>, first: usize, last: usize, room: usize) -> bool {
        (first..=last).map(|index| self.scene_lines(app, layout, index)).sum::<usize>() <= room
    }

    fn cell_column(&self, app: &App, layout: Option<&DetailsLayout>, place: usize) -> usize {
        SCENE_WIDTH
            + (self.left.get()..place)
                .map(|column| self.track_width(app, layout, column) + COLUMN_EXTRA)
                .sum::<usize>()
    }

    fn visible_tracks(&self, app: &App, layout: Option<&DetailsLayout>, width: usize) -> (usize, usize) {
        let total = Self::places(app).len();
        if layout.is_some() {
            let room = width.saturating_sub(SCENE_WIDTH + 1);
            let fits = |first: usize, place: usize| {
                (first..=place)
                    .map(|column| self.track_width(app, layout, column) + COLUMN_EXTRA)
                    .sum::<usize>()
                    <= room
            };
            if self.in_a_track_column() {
                let place = self.track_place();
                self.left.set(self.left.get().min(place));
                while self.left.get() < place && !fits(self.left.get(), place) {
                    self.left.set(self.left.get() + 1);
                }
            }
            self.left.set(self.left.get().min(total - 1));
            while self.left.get() > 0 && fits(self.left.get() - 1, total - 1) {
                self.left.set(self.left.get() - 1);
            }
            let mut last = self.left.get() + 1;
            while last < total && fits(self.left.get(), last) {
                last += 1;
            }
            return (self.left.get(), last);
        }
        let count = ((width.saturating_sub(SCENE_WIDTH + 1)) / (CELL_WIDTH + COLUMN_EXTRA)).max(1);
        if self.in_a_track_column() {
            let place = self.track_place();
            if place < self.left.get() {
                self.left.set(place);
            } else if place >= self.left.get() + count {
                self.left.set(place + 1 - count);
            }
        }
        self.left.set(self.left.get().min(total.saturating_sub(count)));
        (self.left.get(), (self.left.get() + count).min(total))
    }

    fn visible_scenes(&self, app: &App, layout: Option<&DetailsLayout>, height: usize) -> std::ops::Range<usize> {
        let count = Self::scene_count(app) as usize;
        let room = height.saturating_sub(self.header_lines(app, layout));
        let wanted = (self.row.get().max(0) as usize).min(count - 1);
        let mut top = self.top.get().min(wanted);
        while top < wanted && !self.rows_fit(app, layout, top, wanted, room) {
            top += 1;
        }
        let mut stop = top + 1;
        while stop < count && self.rows_fit(app, layout, top, stop, room) {
            stop += 1;
        }
        self.top.set(top);
        top..(stop.min(count))
    }

    fn dividers(&self, app: &App, layout: Option<&DetailsLayout>, first: usize, last: usize) -> Piece {
        Piece::Dividers {
            double_at: SCENE_WIDTH,
            columns: (first + 1..=last).map(|place| self.cell_column(app, layout, place)).collect(),
            drums_at: self.drums_column(app, layout, first, last),
            faint: false,
        }
    }

    /// The rule under the headings, in the frame's green, or under a scene.
    fn grid_rule(&self, app: &App, layout: Option<&DetailsLayout>, first: usize, last: usize, framing: bool) -> Piece {
        Piece::Rule {
            end: self.cell_column(app, layout, last),
            double_at: SCENE_WIDTH,
            crosses: (first + 1..last).map(|place| self.cell_column(app, layout, place)).collect(),
            drums_at: self.drums_column(app, layout, first, last),
            framing,
        }
    }

    /// Where the double line between the main tracks and the drum tracks falls, the left of the first drum column, when it
    /// is on screen.
    fn drums_column(&self, app: &App, layout: Option<&DetailsLayout>, first: usize, last: usize) -> Option<usize> {
        let place = Self::drum_start(app);
        (first < place && place <= last).then(|| self.cell_column(app, layout, place))
    }

    /// Lay lines of details from a column, each cut to room when given, the picked one in brackets when here is true.
    fn draw_details(&self, app: &App, lines: &mut [Vec<Piece>], details: &[DetailLine], column: usize, here: bool, room: Option<usize>) {
        let picked = if here { self.picked_line(app) } else { None };
        for (place, (line, detail)) in lines.iter_mut().zip(details).enumerate() {
            let style = detail.colour().map_or_else(|| detail.kind.style().to_string(), crate::themes::text_style);
            line.push(Piece::Detail {
                column,
                text: detail.text.clone(),
                style,
                picked: picked == Some(place),
                room,
            });
        }
    }

    fn scene_label(&self, app: &App, lengths: &Lengths, index: usize) -> String {
        let scene = &app.document.song().scenes()[index];
        let mut name = scene_name(scene, index);
        if scene.get_repeat() > DEFAULT_REPEAT {
            name.push(' ');
            name.push_str(&named(marks::MSG_REPEAT_MARK, &[("repeat", scene.get_repeat().into())]));
        }
        if matches!(scene.get_written(SceneSetting::LAUNCH_TOGETHER), Some(Data::Bool(false))) {
            name.push(' ');
            name.push_str(marks::MSG_LAUNCH_APART_MARK);
        }
        let length = clock(lengths.scene_seconds(index));
        let row = named(marks::MSG_SCENE_ROW, &[("number", (index + 1).into()), ("name", name.as_str().into())]);
        format!("{}{length}", fit(&row, SCENE_LABEL_WIDTH - length.chars().count() - 1))
    }

    fn draw_header(&self, app: &App, layout: Option<&DetailsLayout>, lines: &mut [Vec<Piece>], first: usize, last: usize) {
        let places = Self::places(app);
        let shown_tracks = Self::tracks(app);
        let count = lines.len();
        let dividers = self.dividers(app, layout, first, last);
        for line in lines[..count - 1].iter_mut() {
            line.push(dividers.clone());
        }
        if Self::real_time_on(app) {
            let playing = app.transport.is_playing();
            let mark = if playing { marks::MSG_STOP_MARK } else { marks::MSG_PLAY_MARK };
            let button = named(marks::MSG_SONG_BUTTON, &[("mark", mark.into())]);
            lines[1].push(Piece::Text {
                column: SCENE_LABEL_COLUMN,
                text: button,
                kind: if playing { Kind::Playing } else { Kind::Faint },
            });
        }
        for place in first..last {
            let column = self.cell_column(app, layout, place) + FRAME_ROOM + 1;
            let width = self.track_width(app, layout, place);
            if let Some(Place::Track(name)) = places.get(place) {
                let shown = if layout.is_some() && name.chars().count() > DETAIL_WIDTH {
                    fit(name, DETAIL_WIDTH).trim_end().to_string()
                } else {
                    name.clone()
                };
                let mut room = if Self::real_time_on(app) { width - SOUNDING_MARK_WIDTH } else { width };
                // A muted or soloed track says so with an M or an S at the end of its heading, and a silent track's
                // heading is dim.
                let mark = if Self::track_flag(app, name, TrackSetting::SOLO) {
                    Some((marks::MSG_SOLOED_MARK, Kind::Soloed))
                } else if Self::track_flag(app, name, TrackSetting::MUTE) {
                    Some((marks::MSG_MUTED_MARK, Kind::Muted))
                } else {
                    None
                };
                if let Some((text, kind)) = mark {
                    room -= MARK_ROOM;
                    lines[1].push(Piece::Text {
                        column: column + room,
                        text: text.to_string(),
                        kind,
                    });
                }
                lines[1].push(Piece::Text {
                    column,
                    text: fit(&format!(" {shown}"), room),
                    kind: if Self::is_silenced(app, name) { Kind::Faint } else { Kind::Name },
                });
                if Self::real_time_on(app) && app.transport.is_track_sounding(name) {
                    lines[1].push(Piece::Text {
                        column: column + width - 1,
                        text: marks::MSG_SOUNDING_MARK.to_string(),
                        kind: Kind::Sounding,
                    });
                }
                let cell = CellPlace::Track(name.clone());
                if let (Some(layout), true) = (layout, self.cell_open(app, &cell)) {
                    let here = self.on_header() && !self.on_corner() && self.track_place() == place;
                    let end = count - 2;
                    let shown = shown_tracks.iter().position(|track| track == name).unwrap_or(0);
                    self.draw_details(app, &mut lines[2..end], &layout.track_details[shown], column + TRACK_DETAIL_INDENT, here, None);
                }
            } else {
                lines[1].push(Piece::Text {
                    column,
                    text: fit_aligned(marks::MSG_ADD_ROW_MARK, width, Align::Center),
                    kind: Kind::Faint,
                });
            }
        }
        if last < places.len() {
            lines[1].push(Piece::More {
                column: self.cell_column(app, layout, last),
            });
        }
        lines[count - 1].push(self.grid_rule(app, layout, first, last, true));
    }

    fn draw_scene(&self, app: &App, layout: Option<&DetailsLayout>, lengths: &Lengths, lines: &mut [Vec<Piece>], index: usize, window: (usize, usize)) {
        let (first, last) = window;
        let places = Self::places(app);
        let count = lines.len();
        let dividers = self.dividers(app, layout, first, last);
        for line in lines[..count - 1].iter_mut() {
            line.push(dividers.clone());
        }
        lines[count - 1].push(self.grid_rule(app, layout, first, last, false));
        lines[1].push(Piece::Text {
            column: SCENE_LABEL_COLUMN,
            text: self.scene_label(app, lengths, index),
            kind: Kind::Name,
        });
        if let (Some(layout), true) = (layout, self.cell_open(app, &CellPlace::Scene(index))) {
            let here = self.on_scene_name() && self.row.get() == index as i64;
            let end = count - LINES_UNDER_A_SCENE;
            self.draw_details(
                app,
                &mut lines[FIRST_DETAIL_LINE..end],
                &layout.scene_details[index],
                SCENE_BAR_COLUMN,
                here,
                Some(SCENE_DETAIL_ROOM),
            );
        }
        let scene_bar = LengthBar {
            width: SCENE_WIDTH - SCENE_BAR_COLUMN - 2,
            hatched: true,
        };
        lines[2].push(Piece::Text {
            column: SCENE_BAR_COLUMN,
            text: scene_bar.draw_played(
                lengths.scene_seconds(index),
                lengths.longest_scene_seconds(),
                if Self::real_time_on(app) { app.transport.scene_elapsed(index) } else { None },
            ),
            kind: Kind::Plain,
        });
        let real_time = Self::real_time_on(app);
        if real_time {
            lines[2].push(Piece::PlayButton {
                column: SCENE_LABEL_COLUMN,
                playing: app.transport.playing_scenes().contains(&index),
            });
        }
        for (place, held) in places.iter().enumerate().take(last).skip(first) {
            // A + column holds nothing under the header.
            let Place::Track(track) = held else { continue };
            let column = self.cell_column(app, layout, place) + FRAME_ROOM + 1;
            let width = self.track_width(app, layout, place);
            let Some(clip) = Self::clip(app, index, track) else {
                if self.row.get() == index as i64 && self.in_a_track_column() && !self.on_header() && self.track_place() == place {
                    lines[1].push(Piece::Text {
                        column,
                        text: fit_aligned(marks::MSG_ADD_ROW_MARK, width, Align::Center),
                        kind: Kind::Plain,
                    });
                    lines[2].push(Piece::Text {
                        column,
                        text: fit_aligned(legends::What::ADD, width, Align::Center),
                        kind: Kind::Plain,
                    });
                }
                continue;
            };
            let cell = CellPlace::Clip(index, track.clone());
            let open = layout.is_some() && self.cell_open(app, &cell);
            let playing = real_time && app.transport.is_clip_playing(index, track);
            let repeats_left = if playing { app.transport.repeats_left(index, track) } else { None };
            let clip_played = if playing { app.transport.clip_elapsed(index, track) } else { None };
            let shown = if open { detailed_clip_text(clip) } else { clip_text(clip, repeats_left) };
            // A silent track's clips are dim: muted, or another track soloed.
            let ink = if Self::is_silenced(app, track) { Kind::Faint } else { Kind::Plain };
            lines[1].push(Piece::Text {
                column,
                text: fit(&format!(" {shown}"), width),
                kind: ink,
            });
            let total = lengths.scene_play_seconds(index);
            let (bar, bar_column) = if real_time {
                lines[2].push(Piece::PlayButton { column, playing });
                (
                    LengthBar {
                        width: width - 2 - PLAY_BUTTON_WIDTH,
                        hatched: false,
                    },
                    column + 1 + PLAY_BUTTON_WIDTH,
                )
            } else {
                (
                    LengthBar {
                        width: width - 2,
                        hatched: false,
                    },
                    column + 1,
                )
            };
            let text = if clip.loops() {
                match clip_played {
                    None => bar.full(),
                    Some(_) => bar.draw_played(total, total, clip_played),
                }
            } else {
                bar.draw_played(lengths.clip_seconds(index, track), total, clip_played)
            };
            lines[2].push(Piece::Text {
                column: bar_column,
                text,
                kind: ink,
            });
            if let (Some(layout), true) = (layout, open) {
                let indent = if real_time { DETAIL_INDENT } else { 1 };
                let here = !self.on_header() && !self.on_scene_name() && self.row.get() == index as i64 && self.track_place() == place;
                let details = layout.clip_details.get(&(index, track.clone())).cloned().unwrap_or_default();
                let end = count - LINES_UNDER_A_SCENE;
                self.draw_details(app, &mut lines[FIRST_DETAIL_LINE..end], &details, column + indent, here, None);
            }
        }
    }

    fn frame(&self, app: &App, layout: Option<&DetailsLayout>, shown: &std::ops::Range<usize>, window: (usize, usize)) -> Option<CellFrame> {
        let (first, last) = window;
        let header = self.header_lines(app, layout);
        let names = header - 3;
        let style = if self.picking(app) || self.cut.is_some() {
            Style::DETAILS_LOCKED
        } else {
            Style::SELECTED_EDGE
        };
        let around = |place: usize, top: usize, inside: usize| {
            let left = self.cell_column(app, layout, place) + FRAME_ROOM;
            CellFrame {
                left,
                right: left + self.track_width(app, layout, place) + 1,
                top,
                inside,
                style,
            }
        };
        if self.on_corner() {
            return Some(CellFrame {
                left: 0,
                right: SCENE_FRAME_RIGHT,
                top: 0,
                inside: names,
                style,
            });
        }
        if self.on_header() {
            let place = self.track_place();
            return (first <= place && place < last).then(|| around(place, 0, names));
        }
        let row = self.row.get() as usize;
        if !shown.contains(&row) {
            return None;
        }
        let line = header + (shown.start..row).map(|index| self.scene_lines(app, layout, index)).sum::<usize>();
        let inside = self.scene_lines(app, layout, row) - 1 - LINES_UNDER_A_SCENE;
        if self.on_scene_name() {
            return Some(CellFrame {
                left: 0,
                right: SCENE_FRAME_RIGHT,
                top: line,
                inside,
                style,
            });
        }
        Some(around(self.track_place(), line, inside))
    }
}

impl Page for ArrangePage {
    /// The part of the grid the cursor is on: the corner, a track's name, the + after the tracks, a scene's name, the + row, a
    /// clip or an empty cell.
    fn place_kind(&self, app: &App) -> String {
        let kind = if self.on_corner() {
            "corner"
        } else if self.plus_here(app) == Some(false) {
            "track plus"
        } else if self.plus_here(app) == Some(true) {
            "drum track plus"
        } else if self.on_header() {
            "track"
        } else if self.on_scene_name() {
            "scene"
        } else {
            let has_clip = self
                .cursor_track(app)
                .and_then(|track| app.document.song().scenes().get(self.row.get() as usize)?.get_clip_slot(&track).cloned())
                .is_some();
            if has_clip {
                "clip"
            } else {
                "empty"
            }
        };
        kind.to_string()
    }

    fn go_to_row(&mut self, _app: &App, row: &str) {
        self.put_cursor_at(row);
    }

    fn name(&self) -> &'static str {
        "ArrangePage"
    }

    fn stack_name(&self) -> &str {
        "ArrangePage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        self.clamp(app);
        if self.shows_visualizer() {
            return vec![Self::bind(&Keys::TO_CLIPS), Self::bind(&Keys::STEP_VISUALIZER), Self::bind(&Keys::VISUALIZER)];
        }
        if let Some(inset) = &self.inset {
            let switch = if inset.is_written() { &Keys::TO_PLAYED } else { &Keys::TO_WRITTEN };
            return vec![
                Self::bind(&Keys::ESCAPE_INSET),
                Self::bind(&Keys::INSET_MOVE).wanting_key(),
                Self::bind(&Keys::INSET_BARS),
                Self::bind(switch),
                Self::bind(&Keys::INSET_ZOOM),
                Self::bind(&Keys::INSET_SCROLL),
            ];
        }
        if self.picking(app) {
            let mut keys = vec![Self::bind(&Keys::ESCAPE_CELL), Self::bind(&Keys::OUT_OF_DETAILS)];
            if !self.pickable(app).is_empty() {
                keys.push(Self::bind(&Keys::PICK_DETAIL).wanting_key());
                let target = self.picked_target(app);
                if target.as_ref().is_some_and(|target| target.kind == ADD_CHAIN) {
                    keys.push(Self::bind(&Keys::ADD_CHAIN));
                } else {
                    keys.push(Self::bind(&Keys::OPEN_DETAIL));
                }
                if target
                    .as_ref()
                    .is_some_and(|target| target.kind == llamatron_model::schema::generated::file_format::Section::CHAINS)
                {
                    keys.push(Self::bind(&Keys::REMOVE_CHAIN));
                }
            }
            keys.push(Self::bind(&Keys::CLOSE_DETAILS));
            return keys;
        }
        let mut keys = vec![Self::bind(&Keys::BACK), Self::bind(&Keys::MOVE).wanting_key()];
        if self.on_header() {
            keys.extend(self.header_keys(app));
        } else {
            keys.extend(self.scene_row_keys(app));
        }
        if self.cursor_cell(app).is_some() {
            keys.push(Self::bind(&Keys::INTO_DETAILS));
        }
        keys.push(Self::bind(if app.session.shows_arrange_details {
            &Keys::HIDE_DETAILS
        } else {
            &Keys::SHOW_DETAILS
        }));
        if Self::real_time_on(app) {
            keys.push(Self::bind(&Keys::VISUALIZER));
        }
        keys.push(Self::bind(&Keys::FRACTURE));
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        // ESC with something cut lets go of it, nothing moved, before it would leave the page.
        if self.cut.is_some() && self.inset.is_none() && item.is(&Keys::BACK) {
            self.cut = None;
            app.say(messages::MSG_CUT_LET_GO);
            return;
        }
        if let Some(inset) = &mut self.inset {
            if item.is(&Keys::ESCAPE_INSET) {
                self.inset = None;
            } else if item.is(&Keys::INSET_MOVE) {
                inset.move_cursor(app, key);
            } else if item.is(&Keys::INSET_BARS) {
                inset.jump_bar(app, item.step_of(key).unwrap_or(0));
            } else if item.is(&Keys::TO_PLAYED) || item.is(&Keys::TO_WRITTEN) {
                inset.switch(app);
            } else if item.is(&Keys::INSET_ZOOM) {
                inset.zoom_by(item.step_of(key).unwrap_or(0));
            } else if item.is(&Keys::INSET_SCROLL) {
                inset.scroll_sidebar(item.step_of(key).unwrap_or(0));
            }
            return;
        }
        if self.shows_visualizer() {
            if item.is(&Keys::TO_CLIPS) {
                *self.visualizer.borrow_mut() = None;
            } else if item.is(&Keys::STEP_VISUALIZER) {
                self.step_visualizer(app, item.step_of(key).unwrap_or(1));
            } else if item.is(&Keys::VISUALIZER) {
                self.next_visualizer(app);
            }
            return;
        }
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&Keys::VISUALIZER) {
            self.next_visualizer(app);
        } else if item.is(&Keys::MOVE) {
            let from = self.column.get();
            match key {
                "up" => self.row.set(self.row.get() - 1),
                "down" => self.row.set(self.row.get() + 1),
                "left" => self.column.set(self.column.get().saturating_sub(1)),
                _ => self.column.set(self.column.get() + 1),
            }
            self.step_over_plus(app, key, from);
            self.clamp(app);
        } else if item.is(&Keys::CUT_SCENE) {
            self.start_cut(app, Moving::Scene);
        } else if item.is(&Keys::CUT_TRACK) {
            self.start_cut(app, Moving::Track);
        } else if item.is(&Keys::CUT_CLIP) {
            self.start_cut(app, Moving::Clip);
        } else if item.is(&Keys::PASTE) && self.cut.is_some() {
            self.paste_cut(app);
        } else if item.is(&Keys::MUTE_TRACK) || item.is(&Keys::UNMUTE_TRACK) {
            if let Some(track) = self.column_track(app) {
                self.toggle_mute(app, &track);
            }
        } else if item.is(&Keys::SOLO_TRACK) || item.is(&Keys::UNSOLO_TRACK) {
            if let Some(track) = self.column_track(app) {
                self.toggle_solo(app, &track);
            }
        } else if item.is(&Keys::PLAY_SONG) {
            let scene = named(messages::MSG_SCENE_NUMBER, &[("number", 1.into())]);
            let said = named(messages::MSG_PLAYING_FROM, &[("scene", scene.as_str().into())]);
            play_through(app, &scene, &said, |app| app.transport.play_scene(&app.document, 0));
        } else if item.is(&Keys::PLAY_SCENE) {
            let index = self.row.get().max(0) as usize;
            let scene = named(messages::MSG_SCENE_NUMBER, &[("number", (index + 1).into())]);
            let said = named(messages::MSG_PLAYING_FROM, &[("scene", scene.as_str().into())]);
            play_through(app, &scene, &said, |app| app.transport.play_scene(&app.document, index));
        } else if item.is(&Keys::PLAY_CLIP) {
            let index = self.row.get().max(0) as usize;
            let Some(track) = self.cursor_track(app) else { return };
            let name = Self::clip(app, index, &track).map(|clip| clip.get_display_name()).unwrap_or_default();
            let clip = named(messages::MSG_CLIP_ON_TRACK, &[("name", name.as_str().into()), ("track", track.as_str().into())]);
            let said = named(messages::MSG_PLAYING_CLIP, &[("clip", clip.as_str().into())]);
            play_through(app, &clip, &said, |app| {
                app.transport.play_clips(&app.document, index, vec![track.clone()], &[], false)
            });
        } else if item.is(&Keys::STOP_PLAYING) {
            app.transport.stop_all();
            app.say(messages::MSG_STOPPED);
        } else if item.is(&Keys::STOP_CLIP) {
            let Some(track) = self.cursor_track(app) else { return };
            app.transport.stop_clip(&track);
            app.say(&named(messages::MSG_STOPPED_TRACK, &[("track", track.as_str().into())]));
        } else if item.is(&Keys::SCENE_VIEW) {
            self.inset = Some(SceneView::new(app, self.row.get().max(0) as usize));
        } else if item.is(&Keys::INTO_DETAILS) {
            self.start_picking(app);
        } else if item.is(&Keys::ESCAPE_CELL) || item.is(&Keys::OUT_OF_DETAILS) {
            self.stop_picking();
        } else if item.is(&Keys::CLOSE_DETAILS) {
            self.stop_picking();
            app.session.shows_arrange_details = false;
        } else if item.is(&Keys::PICK_DETAIL) {
            let count = self.pickable(app).len() as i64;
            let step: i64 = if key == "up" { -1 } else { 1 };
            self.picked = Some((self.picked.unwrap_or(0) as i64 + step).clamp(0, (count - 1).max(0)) as usize);
        } else if item.is(&Keys::OPEN_DETAIL) {
            if let Some(target) = self.picked_target(app) {
                self.open_target(app, target);
            }
        } else if item.is(&Keys::ADD_CHAIN) {
            self.add_cell_chain(app);
        } else if item.is(&Keys::REMOVE_CHAIN) {
            if let Some(Target { place: Some(place), .. }) = self.picked_target(app) {
                self.remove_cell_chain(app, place);
            }
        } else if item.is(&Keys::OPEN_PATTERN) {
            let Some(track) = self.cursor_track(app) else { return };
            if let Some(clip) = Self::clip(app, self.row.get() as usize, &track) {
                let name = clip.get_pattern_name();
                let crumbs = self.crumbs(app);
                app.show_page(crate::screens::pattern::open_clip_pattern(&name, crumbs, &track));
            }
        } else if item.is(&Keys::SHOW_DETAILS) || item.is(&Keys::HIDE_DETAILS) {
            // The other view starts from the top left, as its rows and columns are other sizes.
            app.session.shows_arrange_details = !app.session.shows_arrange_details;
            self.stop_picking();
            self.top.set(0);
            self.left.set(0);
        } else if item.is(&Keys::COPY_CLIP) {
            let Some(track) = self.cursor_track(app) else { return };
            self.copied = Self::clip(app, self.row.get() as usize, &track).cloned();
            app.say(llamatron_strings::messages::MSG_COPIED_CLIP);
        } else if item.is(&Keys::EDIT_CLIP) {
            let Some(track) = self.cursor_track(app) else { return };
            let index = self.row.get().max(0) as usize;
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::arrange::clip_page::ClipPage::new(index, track),
            )));
        } else if item.is(&Keys::SCENE_SETTINGS) {
            let index = self.row.get().max(0) as usize;
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::arrange::scene_page::ScenePage { index },
            )));
        } else if self.press_edit(app, item) {
        } else if item.is(&Keys::TRACK_SETTINGS) {
            let Some(name) = self.cursor_track(app) else { return };
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::arrange::track_editor::TrackEditor { name },
            )));
        }
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        self.clamp(app);
        let lengths = Lengths::of(app.document.get_setlist(), app.document.song());
        let held = self.layout(app);
        let layout = held.as_ref();
        let window = self.visible_tracks(app, layout, width);
        let shown = self.visible_scenes(app, layout, height);
        let header = self.header_lines(app, layout);
        let scenes: usize = shown.clone().map(|index| self.scene_lines(app, layout, index)).sum();
        let total = header + scenes;
        let mut lines: Vec<Vec<Piece>> = (0..total).map(|_| Vec::new()).collect();
        self.draw_header(app, layout, &mut lines[..header], window.0, window.1);
        let mut start = header;
        for index in shown.clone() {
            let rows = self.scene_lines(app, layout, index);
            self.draw_scene(app, layout, &lengths, &mut lines[start..start + rows], index, window);
            start += rows;
        }
        // Under a visualizer the cursor has no frame, since the clips it would box are covered.
        let frames: Vec<CellFrame> = if self.shows_visualizer() {
            Vec::new()
        } else {
            self.frame(app, layout, &shown, window).into_iter().collect()
        };
        let drawn = arrange_lines(&lines, width, &frames);
        self.visualized(app, drawn, header, width, height)
    }

    fn launch_visualizer(&self, app: &App, mode: &str) {
        self.show_visualizer(app, mode);
    }

    fn frame_interval(&self) -> Option<std::time::Duration> {
        self.shows_visualizer().then_some(visualizers::showing::FRAME_INTERVAL)
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::ARRANGE.to_string()]
    }

    fn over_screen(&self, app: &App, screen: Vec<Text>, width: usize, height: usize) -> Vec<Text> {
        let Some(inset) = &self.inset else { return screen };
        let index = inset.get_index();
        let title = named(
            marks::MSG_SCENE_VIEW_TITLE,
            &[("scene", scene_name(&app.document.song().scenes()[index], index).as_str().into())],
        );
        let closing = named(
            marks::MSG_SCENE_VIEW_CLOSING,
            &[("key", Keys::ESCAPE_INSET.name.into()), ("what", Keys::ESCAPE_INSET.what.into())],
        );
        inset.drawn_over(app, screen, width, height, &title, &closing)
    }

    fn theme(&self) -> Option<Colour> {
        None
    }

    fn duration(&self, app: &App) -> Duration {
        if let Some(playing) = app.transport.playing_clock() {
            return Duration::Clock(playing);
        }
        Duration::Seconds(Lengths::of(app.document.get_setlist(), app.document.song()).song_seconds())
    }
}

/// Start real-time playback: tell why nothing can play if so, and otherwise stop every listening preview and play, saying
/// on the status line what started, or that what (a scene or a clip, named) starts at the next bar.
pub fn play_through(app: &mut App, what: &str, said: &str, play: impl FnOnce(&mut App) -> Result<bool, String>) {
    if let Some(refusal) = app.transport.refusal(app, None) {
        app.show_page(Box::new(crate::screens::dialogs::MessageDialog::new(&refusal.title, refusal.lines)));
        return;
    }
    crate::screens::listening::stop_every_preview(app);
    match play(app) {
        Ok(true) => app.say(&named(messages::MSG_STARTS_AT_NEXT_BAR, &[("what", what.into())])),
        Ok(false) => app.say(said),
        Err(problem) => app.show_page(Box::new(crate::screens::dialogs::MessageDialog::new(
            llamatron_strings::errors::ERR_CANT_PLAY_TITLE,
            vec![problem],
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::page::Page;
    use llamatron_model::objects::setlist::Setlist;

    /// A song of two tracks, lead and bass, and two scenes, verse and chorus, with tune on lead in the verse alone.
    const TWO_BY_TWO_SET: &str = include_str!("../../../tests/data/two_by_two_set.yml");

    fn arranged() -> (App, ArrangePage) {
        let setlist = Setlist::read_text(TWO_BY_TWO_SET).expect("the scenario's set is valid");
        (App::new(crate::document::Document::new(setlist, None)), ArrangePage::new())
    }

    /// Put Arrange's cursor on a scene's row and a track's column by their names.
    fn at(app: &App, page: &ArrangePage, scene: &str, track: &str) {
        let row = app
            .document
            .song()
            .scenes()
            .iter()
            .position(|held| held.get_name().as_deref() == Some(scene))
            .expect("the scene");
        let place = ArrangePage::place_of(app, track).expect("the track");
        page.row.set(row as i64);
        page.column.set(place + FIRST_TRACK_COLUMN);
    }

    fn press(app: &mut App, page: &mut ArrangePage, binding: &'static crate::keybindings::Binding) {
        let item = KeyItem::of(&Keys::CLASS, binding);
        let key = item.keys[0];
        page.press(app, &item, key);
        // Each key press is one step to undo, as the tracker records it after every key.
        app.document.record_edit();
    }

    /// Press one of a binding's keys, such as Right of the arrows that move.
    fn press_key(app: &mut App, page: &mut ArrangePage, binding: &'static crate::keybindings::Binding, key: &str) {
        let item = KeyItem::of(&Keys::CLASS, binding);
        page.press(app, &item, key);
        app.document.record_edit();
    }

    fn flag(app: &App, track: &str, setting: &str) -> bool {
        ArrangePage::track_flag(app, track, setting)
    }

    /// A song whose file holds a drum track, kick, before its melodic ones, lead and bass, with a drum pattern beat on kick
    /// and a melodic pattern tune on lead in the verse.
    const DRUMS_FIRST_SET: &str = include_str!("../../../tests/data/drums_first_set.yml");

    fn drums_first() -> (App, ArrangePage) {
        let setlist = Setlist::read_text(DRUMS_FIRST_SET).expect("the scenario's set is valid");
        (App::new(crate::document::Document::new(setlist, None)), ArrangePage::new())
    }

    /// The names of the tracks in the file's order.
    fn file_order(app: &App) -> Vec<String> {
        app.document.song().tracks().iter().map(|(name, _)| name.clone()).collect()
    }

    /// A song of drum tracks alone, kick and hat, and one scene, verse.
    const DRUMS_ONLY_SET: &str = include_str!("../../../tests/data/drums_only_set.yml");

    fn drums_only() -> (App, ArrangePage) {
        let setlist = Setlist::read_text(DRUMS_ONLY_SET).expect("the scenario's set is valid");
        (App::new(crate::document::Document::new(setlist, None)), ArrangePage::new())
    }

    /// Press Right on the header until the cursor is on what a place's kind names, at most a column a press.
    fn right_until(app: &mut App, page: &mut ArrangePage, kind: &str) {
        for _ in 0..ArrangePage::places(app).len() {
            if page.place_kind(app) == kind {
                return;
            }
            press_key(app, page, &Keys::MOVE, "right");
        }
        assert_eq!(page.place_kind(app), kind);
    }

    /// Arrange shows the melodic tracks first and the drum tracks after them, each in the file's order, which stays as it
    /// is, with no + after either group; a group with no tracks shows a + alone.
    #[test]
    fn main_tracks_show_first_and_drums_after_the_double_line() {
        let (app, _) = drums_first();
        let track = |name: &str| Place::Track(name.to_string());
        assert_eq!(ArrangePage::places(&app), vec![track("lead"), track("bass"), track("kick")]);
        assert_eq!(file_order(&app), ["kick", "lead", "bass"]);
        let (app, _) = arranged();
        assert_eq!(ArrangePage::places(&app), vec![track("lead"), track("bass"), Place::Add { drum: true }]);
        let (app, _) = drums_only();
        assert_eq!(ArrangePage::places(&app), vec![Place::Add { drum: false }, track("kick"), track("hat")]);
    }

    /// I inserts after the cursor: on a melodic track a melodic track after it, on a scene a scene after it, and on the
    /// drum group's + the song's first drum track, the + then gone.
    #[test]
    fn i_inserts_after_the_cursor_and_on_a_plus_makes_its_groups_first_track() {
        let (mut app, mut page) = arranged();
        at(&app, &page, "verse", "lead");
        page.row.set(HEADER_ROW);
        press(&mut app, &mut page, &Keys::INSERT_TRACK);
        let inserted = page.cursor_track(&app).expect("the new track");
        assert_eq!(ArrangePage::tracks(&app)[..3], ["lead".to_string(), inserted.clone(), "bass".to_string()]);
        assert!(!ArrangePage::is_drum_track(&app, &inserted));
        page.column.set(FIRST_TRACK_COLUMN);
        right_until(&mut app, &mut page, "drum track plus");
        press(&mut app, &mut page, &Keys::INSERT_TRACK);
        let drums = page.cursor_track(&app).expect("the first drum track");
        assert!(ArrangePage::is_drum_track(&app, &drums));
        assert!(!ArrangePage::places(&app).contains(&Place::Add { drum: true }));
        at(&app, &page, "verse", "lead");
        page.column.set(SCENE_COLUMN);
        press(&mut app, &mut page, &Keys::INSERT_SCENE);
        assert_eq!(page.row.get(), 1);
        assert_eq!(app.document.song().scenes().len(), 3);
        assert_eq!(app.document.song().scenes()[2].get_name().as_deref(), Some("chorus"));
    }

    /// The instrument a track plays, as data, by its track's name.
    fn instrument_of(app: &App, track: &str) -> (String, Data) {
        use llamatron_model::objects::setlist::Item;
        let name = app
            .document
            .song()
            .get_track(track)
            .and_then(|held| held.get_instrument_name())
            .expect("an instrument");
        let instrument = match app
            .document
            .get_setlist()
            .get_item(llamatron_model::schema::generated::file_format::Section::INSTRUMENTS, &name)
        {
            Some(Item::Instrument(held)) => held.to_data(),
            _ => panic!("the instrument {name}"),
        };
        (name, instrument)
    }

    /// I makes each new track an instrument of its own, named after it, by Track Inst. Default: with the built-in synths,
    /// a melodic track plays Basic and a drum track MechaDrum; a name taken by an instrument counts up; and the set's first
    /// instrument turns real-time playback on.
    #[test]
    fn a_new_track_gets_an_instrument_of_its_own_named_after_it() {
        use llamatron_model::schema::generated::file_format::InstrumentSetting;
        let (mut app, mut page) = arranged();
        at(&app, &page, "verse", "bass");
        page.row.set(HEADER_ROW);
        press(&mut app, &mut page, &Keys::INSERT_TRACK);
        let melodic = page.cursor_track(&app).expect("the new track");
        let (name, instrument) = instrument_of(&app, &melodic);
        assert_eq!(name, melodic);
        assert_eq!(instrument.get(InstrumentSetting::ROLE), Some(&Data::text("normal")));
        assert_eq!(
            instrument.get(InstrumentSetting::SOUND).and_then(|sound| sound.get("engine")),
            Some(&Data::text("basic"))
        );
        assert!(ArrangePage::real_time_on(&app));
        page.column.set(FIRST_TRACK_COLUMN);
        right_until(&mut app, &mut page, "drum track plus");
        press(&mut app, &mut page, &Keys::INSERT_TRACK);
        let drum = page.cursor_track(&app).expect("the drum track");
        let (_, instrument) = instrument_of(&app, &drum);
        assert_eq!(instrument.get(InstrumentSetting::ROLE), Some(&Data::text("percussion")));
        // When the next track's name is an instrument's already, its instrument counts up from the name.
        let taken = ArrangePage::tracks(&app);
        let next = llamatron_model::objects::naming::new_track_name(llamatron_strings::names::MSG_NEW_MAIN_TRACK_WORD, &taken);
        let instruments = llamatron_model::schema::generated::file_format::Section::INSTRUMENTS;
        let (held, _) = instrument_of(&app, &drum);
        app.document.rename_named(instruments, &held, &next).expect("the rename");
        at(&app, &page, "verse", "bass");
        page.row.set(HEADER_ROW);
        press(&mut app, &mut page, &Keys::INSERT_TRACK);
        let third = page.cursor_track(&app).expect("the third track");
        assert_eq!(third, next);
        let (counted, _) = instrument_of(&app, &third);
        assert_eq!(counted, llamatron_model::objects::naming::copy_name(&next, std::slice::from_ref(&next)));
    }

    /// A copied track plays a copy of its instrument, named after the copy, so that the two can be changed apart.
    #[test]
    fn a_copied_track_plays_a_copy_of_its_instrument() {
        let (mut app, mut page) = arranged();
        at(&app, &page, "verse", "bass");
        page.row.set(HEADER_ROW);
        press(&mut app, &mut page, &Keys::INSERT_TRACK);
        let original = page.cursor_track(&app).expect("the new track");
        let copy = app
            .document
            .copy_named(llamatron_model::schema::generated::file_format::Section::TRACKS, &original)
            .expect("the copy");
        app.document.give_track_own_instrument(&copy).expect("its own instrument");
        let (copied_name, copied) = instrument_of(&app, &copy);
        let (original_name, held) = instrument_of(&app, &original);
        assert_ne!(copied_name, original_name);
        assert_eq!(copied_name, copy);
        assert_eq!(copied, held);
    }

    /// Deleting every melodic track leaves the melodic +, where I makes a melodic track again.
    #[test]
    fn a_group_emptied_keeps_its_plus() {
        let (mut app, mut page) = drums_first();
        for name in ["lead", "bass"] {
            app.document
                .delete_named(llamatron_model::schema::generated::file_format::Section::TRACKS, name)
                .expect("the track deletes");
        }
        assert_eq!(ArrangePage::places(&app)[0], Place::Add { drum: false });
        page.row.set(HEADER_ROW);
        page.column.set(FIRST_TRACK_COLUMN);
        assert_eq!(page.place_kind(&app), "track plus");
        press(&mut app, &mut page, &Keys::INSERT_TRACK);
        assert_eq!(app.document.song().melodic_count(), 1);
    }

    /// A cut drum track pastes only among the drum tracks: on a melodic track it is refused and stays cut; after a drum
    /// track it lands after it.
    #[test]
    fn a_track_pastes_only_among_its_kind_after_the_cursor() {
        let (mut app, mut page) = drums_only();
        at(&app, &page, "verse", "kick");
        page.row.set(HEADER_ROW);
        press(&mut app, &mut page, &Keys::CUT_TRACK);
        at(&app, &page, "verse", "hat");
        page.row.set(HEADER_ROW);
        press(&mut app, &mut page, &Keys::PASTE);
        assert_eq!(file_order(&app), ["hat", "kick"]);
        let (mut app, mut page) = drums_first();
        at(&app, &page, "verse", "kick");
        page.row.set(HEADER_ROW);
        press(&mut app, &mut page, &Keys::CUT_TRACK);
        at(&app, &page, "verse", "lead");
        page.row.set(HEADER_ROW);
        press(&mut app, &mut page, &Keys::PASTE);
        assert!(page.cut.is_some());
        assert_eq!(app.status.text(), messages::MSG_PASTE_TRACK_AMONG_ITS_KIND);
        assert_eq!(file_order(&app), ["kick", "lead", "bass"]);
    }

    /// Under the header Left passes over a group's + onto the scene's name, and Right from the last track stays put.
    #[test]
    fn left_and_right_pass_over_a_plus_under_the_header() {
        let (mut app, mut page) = drums_only();
        at(&app, &page, "verse", "kick");
        press_key(&mut app, &mut page, &Keys::MOVE, "left");
        assert!(page.on_scene_name());
        at(&app, &page, "verse", "hat");
        press_key(&mut app, &mut page, &Keys::MOVE, "right");
        assert_eq!(page.cursor_track(&app).as_deref(), Some("hat"));
    }

    /// A copied drum clip pastes onto an empty drum cell, but not onto a melodic track.
    #[test]
    fn a_clip_pastes_only_onto_its_patterns_kind() {
        let (mut app, mut page) = drums_first();
        at(&app, &page, "verse", "kick");
        press(&mut app, &mut page, &Keys::COPY_CLIP);
        at(&app, &page, "chorus", "bass");
        press(&mut app, &mut page, &Keys::PASTE);
        assert_eq!(app.status.text(), messages::MSG_PASTE_CLIP_AMONG_ITS_KIND);
        assert!(ArrangePage::clip(&app, 1, "bass").is_none());
        at(&app, &page, "chorus", "kick");
        press(&mut app, &mut page, &Keys::PASTE);
        assert!(ArrangePage::clip(&app, 1, "kick").is_some());
    }

    /// M anywhere in a track's column mutes the track and unmutes it again; a muted track is silent.
    #[test]
    fn m_mutes_the_track_of_the_cursors_column() {
        let (mut app, mut page) = arranged();
        at(&app, &page, "chorus", "bass");
        press(&mut app, &mut page, &Keys::MUTE_TRACK);
        assert!(flag(&app, "bass", TrackSetting::MUTE));
        assert!(ArrangePage::is_silenced(&app, "bass") && !ArrangePage::is_silenced(&app, "lead"));
        press(&mut app, &mut page, &Keys::UNMUTE_TRACK);
        assert!(!flag(&app, "bass", TrackSetting::MUTE));
    }

    /// S solos one track at a time, every other track silent; soloing another moves the solo, and S again lifts it.
    #[test]
    fn s_solos_one_track_at_a_time() {
        let (mut app, mut page) = arranged();
        at(&app, &page, "verse", "lead");
        press(&mut app, &mut page, &Keys::SOLO_TRACK);
        assert!(flag(&app, "lead", TrackSetting::SOLO));
        assert!(ArrangePage::is_silenced(&app, "bass") && !ArrangePage::is_silenced(&app, "lead"));
        at(&app, &page, "verse", "bass");
        press(&mut app, &mut page, &Keys::SOLO_TRACK);
        assert!(flag(&app, "bass", TrackSetting::SOLO) && !flag(&app, "lead", TrackSetting::SOLO));
        press(&mut app, &mut page, &Keys::UNSOLO_TRACK);
        assert!(!ArrangePage::is_silenced(&app, "lead") && !ArrangePage::is_silenced(&app, "bass"));
    }

    fn scene_names(app: &App) -> Vec<String> {
        app.document.song().scenes().iter().filter_map(Scene::get_name).collect()
    }

    /// T cuts and P pastes: a scene goes after the scene under the cursor, a clip into the empty cell under it, each as
    /// one step to undo, and ESC lets go of a cut with nothing moved.
    #[test]
    fn t_cuts_and_p_pastes_scenes_and_clips() {
        let (mut app, mut page) = arranged();
        at(&app, &page, "verse", "lead");
        page.column.set(SCENE_COLUMN);
        press(&mut app, &mut page, &Keys::CUT_SCENE);
        at(&app, &page, "chorus", "lead");
        page.column.set(SCENE_COLUMN);
        press(&mut app, &mut page, &Keys::PASTE);
        assert_eq!(scene_names(&app), ["chorus", "verse"]);
        app.document.undo();
        assert_eq!(scene_names(&app), ["verse", "chorus"]);
        at(&app, &page, "verse", "lead");
        press(&mut app, &mut page, &Keys::CUT_CLIP);
        at(&app, &page, "chorus", "bass");
        press(&mut app, &mut page, &Keys::PASTE);
        let chorus = app
            .document
            .song()
            .scenes()
            .iter()
            .position(|held| held.get_name().as_deref() == Some("chorus"))
            .expect("chorus");
        assert!(ArrangePage::clip(&app, chorus, "bass").is_some());
        assert!(ArrangePage::clip(&app, 0, "lead").is_none());
        at(&app, &page, "chorus", "bass");
        press(&mut app, &mut page, &Keys::CUT_CLIP);
        press(&mut app, &mut page, &Keys::BACK);
        assert!(page.cut.is_none());
        assert!(ArrangePage::clip(&app, chorus, "bass").is_some());
    }

    /// In the details view, ENTER on a clip's "+ add chain" line asks for one of the set's generators and adds it to the
    /// clip alone.
    #[test]
    fn add_chain_in_the_details_view_adds_a_generator_to_the_clip() {
        use crate::keys::first_key;
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/data/clip_and_a_generator.yml");
        let text = std::fs::read_to_string(path).expect("the scenario's set is there");
        let setlist = llamatron_model::objects::setlist::Setlist::read_text(&text).expect("the scenario's set is valid");
        let mut tracker = crate::app::Tracker::new(crate::document::Document::new(setlist, None));
        tracker.press(first_key(&crate::keybindings::MainPage::ARRANGE));
        // Arrange opens on the scene's name; the clip is the cell to its right.
        tracker.press("right");
        let most_presses = 10;
        tracker.press(first_key(&Keys::SHOW_DETAILS));
        tracker.press(first_key(&Keys::INTO_DETAILS));
        for _ in 0..most_presses {
            if tracker.top().keys(&tracker.app).iter().any(|key| key.is(&Keys::ADD_CHAIN)) {
                break;
            }
            tracker.press("down");
        }
        tracker.press(first_key(&Keys::ADD_CHAIN));
        let screen: Vec<String> = tracker.screen(80, 24).iter().map(|line| line.text()).collect();
        assert!(
            screen.iter().any(|line| line.contains("lift")),
            "the picker lists the set's generator: {screen:#?}"
        );
        tracker.press(first_key(&crate::keybindings::ChoiceDialog::CHOOSE));
        let clip = tracker.app.document.song().scenes()[0].get_clip_slot("lead").expect("the clip").clone();
        let chains = crate::screens::arrange::arrange_tabs::chain_names(clip.get_written(ClipSlotSetting::CHAINS));
        assert_eq!(chains, ["lift"]);
    }
}
