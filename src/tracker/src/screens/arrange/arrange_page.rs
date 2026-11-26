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
use crate::screens::not_ported::NotPorted;
use crate::text::Text;
use crate::themes::Colour;
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::{ClipSlot, Scene};
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, SceneSetting, SetlistSetting};
use llamatron_strings::{labels, legends, marks, messages, named, names};
use std::cell::Cell;

const HEADER_ROW: i64 = -1;
const SCENE_COLUMN: usize = 0;
const FIRST_TRACK_COLUMN: usize = 1;
const SCENE_WIDTH: usize = 25;
const CELL_WIDTH: usize = 13;
const SCENE_FRAME_RIGHT: usize = SCENE_WIDTH - 2;
const SCENE_LABEL_COLUMN: usize = 1;
const SCENE_LABEL_WIDTH: usize = SCENE_WIDTH - 3;
const SCENE_BAR_COLUMN: usize = 3;
const PLAY_BUTTON_WIDTH: usize = 2;
const SOUNDING_MARK_WIDTH: usize = 2;
const HEADER_LINES: usize = 4;
const SCENE_LINES: usize = 5;
const FOOTER_LINES: usize = 3;
const NAME_LINES: usize = 1;
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

/// What Move mode carries: the cursor's scene, track or clip.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Moving {
    Scene,
    Track,
    Clip,
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
    /// What M picked up, which the arrows carry until ENTER, ESC or M drops it.
    moving: Option<Moving>,
    row: Cell<i64>,
    column: Cell<usize>,
    top: Cell<usize>,
    left: Cell<usize>,
}

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

fn scene_name(scene: &Scene, index: usize) -> String {
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
            moving: None,
            row: Cell::new(0),
            column: Cell::new(SCENE_COLUMN),
            top: Cell::new(0),
            left: Cell::new(0),
        }
    }

    fn tracks(app: &App) -> Vec<String> {
        app.document.song().get_track_names().into_iter().map(str::to_string).collect()
    }

    fn real_time_on(app: &App) -> bool {
        matches!(app.document.get_setlist().get_written(SetlistSetting::REAL_TIME), Some(Data::Bool(true)))
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
        self.on_header() && self.column.get() == Self::tracks(app).len() + FIRST_TRACK_COLUMN
    }

    fn on_scene_name(&self) -> bool {
        !self.on_header() && self.column.get() == SCENE_COLUMN
    }

    fn on_plus_row(&self, app: &App) -> bool {
        self.row.get() == Self::scene_count(app)
    }

    fn in_a_track_column(&self) -> bool {
        self.column.get() != SCENE_COLUMN
    }

    fn track_place(&self) -> usize {
        self.column.get().saturating_sub(FIRST_TRACK_COLUMN)
    }

    fn clamp(&self, app: &App) {
        let row = self.row.get().clamp(HEADER_ROW, Self::scene_count(app));
        self.row.set(row);
        let tracks = Self::tracks(app).len();
        if self.on_plus_row(app) {
            self.column.set(SCENE_COLUMN);
        } else if self.on_header() {
            let first = if Self::real_time_on(app) { SCENE_COLUMN } else { FIRST_TRACK_COLUMN };
            self.column.set(self.column.get().clamp(first, tracks + FIRST_TRACK_COLUMN));
        } else {
            self.column.set(self.column.get().min(tracks));
        }
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
            return vec![Self::bind(&Keys::ADD_TRACK), Self::bind(&Keys::ADD_TRACK_HERE)];
        }
        [
            &Keys::ADD_TRACK,
            &Keys::TRACK_SETTINGS,
            &Keys::COPY_TRACK,
            &Keys::INSERT_TRACK,
            &Keys::MOVE_TRACK,
            &Keys::DELETE_TRACK,
        ]
        .into_iter()
        .map(Self::bind)
        .collect()
    }

    fn scene_row_keys(&self, app: &App) -> Vec<KeyItem> {
        let mut keys = vec![Self::bind(&Keys::ADD_SCENE)];
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
                    &Keys::MOVE_SCENE,
                    &Keys::COPY_SCENE,
                    &Keys::DELETE_SCENE,
                ]
                .into_iter()
                .map(Self::bind),
            );
        } else {
            let track = &Self::tracks(app)[self.track_place()];
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
                        [&Keys::EDIT_CLIP, &Keys::OPEN_PATTERN, &Keys::MOVE_CLIP, &Keys::COPY_CLIP, &Keys::DELETE_CLIP]
                            .into_iter()
                            .map(Self::bind),
                    );
                }
            }
        }
        if self.copied.is_some() && !self.on_scene_name() {
            keys.push(Self::bind(&Keys::PASTE_CLIP));
        }
        keys.push(Self::bind(&Keys::INSERT_SCENE));
        keys
    }

    /// Whether the cursor is on a cell with details: a track's name, a scene's name or a clip.
    fn start_moving(&mut self, app: &mut App, moving: Moving) {
        self.moving = Some(moving);
        self.say_moving(app);
    }

    fn say_moving(&self, app: &mut App) {
        let row = self.row.get().max(0) as usize;
        let tracks = Self::tracks(app);
        let what = match self.moving {
            Some(Moving::Scene) => {
                let name = scene_name(&app.document.song().scenes()[row], row);
                named(messages::MSG_MOVING_SCENE, &[("name", name.as_str().into())])
            }
            Some(Moving::Track) => named(messages::MSG_MOVING_TRACK, &[("name", tracks[self.track_place()].as_str().into())]),
            _ => {
                let name = Self::clip(app, row, &tracks[self.track_place()]).map_or(String::new(), ClipSlot::get_display_name);
                named(messages::MSG_MOVING_CLIP, &[("name", name.as_str().into())])
            }
        };
        app.say(&named(messages::MSG_MOVING, &[("what", what.as_str().into())]));
    }

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

    /// Carry the picked-up scene up or down, or the picked-up track left or right, one place.
    fn carry(&mut self, app: &mut App, offset: i64) {
        let row = self.row.get().max(0) as usize;
        let place = self.track_place();
        if self.moving == Some(Moving::Scene) {
            let count = Self::scene_count(app);
            let to = row as i64 + offset;
            if (0..count).contains(&to) {
                Self::change_song(app, |song| {
                    song.move_scene(row, offset);
                });
                self.row.set(to);
            }
        } else {
            let to = place as i64 + offset;
            if (0..Self::tracks(app).len() as i64).contains(&to) {
                Self::change_song(app, |song| {
                    song.move_track(place, offset);
                });
                self.column.set((self.column.get() as i64 + offset) as usize);
            }
        }
        self.say_moving(app);
    }

    /// Carry the picked-up clip to the nearest empty cell the arrow points to, passing over cells that hold clips.
    fn carry_clip(&mut self, app: &mut App, key: &str) {
        let (rows, columns): (i64, i64) = match key {
            "up" => (-1, 0),
            "down" => (1, 0),
            "left" => (0, -1),
            _ => (0, 1),
        };
        let tracks = Self::tracks(app);
        let (from_row, from_place) = (self.row.get().max(0) as usize, self.track_place());
        let (mut row, mut place) = (from_row as i64 + rows, from_place as i64 + columns);
        while (0..Self::scene_count(app)).contains(&row) && (0..tracks.len() as i64).contains(&place) {
            let to_track = tracks[place as usize].clone();
            if Self::clip(app, row as usize, &to_track).is_none() {
                let mut dropped = None;
                let from_track = tracks[from_place].clone();
                let to_row = row as usize;
                let circles = |grab: &str| grab == to_track || Self::grab_circles(app, to_row, &to_track, grab);
                let grab = Self::clip(app, from_row, &from_track)
                    .and_then(|clip| clip.get_written(ClipSlotSetting::GRAB_TRACK))
                    .and_then(Data::as_str)
                    .map(str::to_string);
                if grab.as_deref().is_some_and(circles) {
                    dropped = grab;
                }
                let clears = dropped.is_some();
                Self::change_song(app, |song| {
                    if let Some(mut clip) = song.take_clip(from_row, &from_track) {
                        if clears {
                            clip.set_written(ClipSlotSetting::GRAB_TRACK, None);
                        }
                        song.put_clip(to_row, &to_track, clip);
                    }
                });
                self.row.set(row);
                self.column.set(place as usize + FIRST_TRACK_COLUMN);
                if let Some(track) = dropped {
                    app.say(&named(messages::MSG_PASTED_WITHOUT_GRAB, &[("track", track.as_str().into())]));
                    return;
                }
                break;
            }
            row += rows;
            place += columns;
        }
        self.say_moving(app);
    }

    /// Whether a clip on a track of a scene grabbing from another track would go round in a circle: the other's clip there
    /// grabbing, on and on, from the track itself.
    pub fn grab_circles(app: &App, index: usize, track: &str, other: &str) -> bool {
        let mut seen = vec![other.to_string()];
        let mut current = other.to_string();
        while let Some(next) = Self::clip(app, index, &current)
            .and_then(|clip| clip.get_written(ClipSlotSetting::GRAB_TRACK))
            .and_then(Data::as_str)
        {
            if next == track {
                return true;
            }
            if seen.iter().any(|each| each == next) {
                return false;
            }
            seen.push(next.to_string());
            current = next.to_string();
        }
        false
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

    /// Open the page of what a picked line names: a chain's, a scale's or a groove's; an instrument's is not ported yet.
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
            _ => app.show_page(Box::new(NotPorted {
                name: "InstrumentEditor".to_string(),
            })),
        }
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
        let tracks = Self::tracks(app);
        if self.on_header() {
            return (!self.on_corner() && self.track_place() < tracks.len()).then(|| CellPlace::Track(tracks[self.track_place()].clone()));
        }
        if self.on_plus_row(app) {
            return None;
        }
        let row = self.row.get() as usize;
        if self.on_scene_name() {
            return Some(CellPlace::Scene(row));
        }
        let track = tracks.get(self.track_place())?;
        Self::clip(app, row, track).map(|_| CellPlace::Clip(row, track.clone()))
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
        let tracks = Self::tracks(app);
        let Some(layout) = layout else { return CELL_WIDTH };
        if place >= tracks.len() {
            return CELL_WIDTH;
        }
        if Self::shows_details(app) {
            return layout.track_widths[place];
        }
        match &self.opened {
            Some(CellPlace::Track(name)) if *name == tracks[place] => layout.cell_widths.get(&CellPlace::Track(name.clone())).copied().unwrap_or(CELL_WIDTH),
            Some(CellPlace::Clip(index, name)) if *name == tracks[place] => {
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

    /// How many lines a row takes: a scene's, or the + row's after the last scene.
    fn row_lines(&self, app: &App, layout: Option<&DetailsLayout>, index: usize) -> usize {
        if index == Self::scene_count(app) as usize {
            return FOOTER_LINES;
        }
        self.scene_lines(app, layout, index)
    }

    /// Whether the rows from first to last, the + row counting as the row after the last scene, fit in room lines.
    fn rows_fit(&self, app: &App, layout: Option<&DetailsLayout>, first: usize, last: usize, room: usize) -> bool {
        (first..=last).map(|index| self.row_lines(app, layout, index)).sum::<usize>() <= room
    }

    fn cell_column(&self, app: &App, layout: Option<&DetailsLayout>, place: usize) -> usize {
        SCENE_WIDTH
            + (self.left.get()..place)
                .map(|column| self.track_width(app, layout, column) + COLUMN_EXTRA)
                .sum::<usize>()
    }

    fn visible_tracks(&self, app: &App, layout: Option<&DetailsLayout>, width: usize) -> (usize, usize) {
        let total = Self::tracks(app).len() + 1;
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
        let wanted = (self.row.get().max(0) as usize).min(count);
        let mut top = self.top.get().min(wanted);
        while top < wanted && !self.rows_fit(app, layout, top, wanted, room) {
            top += 1;
        }
        let mut stop = top + 1;
        while stop <= count && self.rows_fit(app, layout, top, stop, room) {
            stop += 1;
        }
        self.top.set(top);
        top..(stop.min(count))
    }

    fn dividers(&self, app: &App, layout: Option<&DetailsLayout>, first: usize, last: usize) -> Piece {
        Piece::Dividers {
            double_at: SCENE_WIDTH,
            columns: (first + 1..=last).map(|place| self.cell_column(app, layout, place)).collect(),
            faint: false,
        }
    }

    fn grid_rule(&self, app: &App, layout: Option<&DetailsLayout>, first: usize, last: usize) -> Piece {
        Piece::Rule {
            end: self.cell_column(app, layout, last),
            double_at: SCENE_WIDTH,
            crosses: (first + 1..last).map(|place| self.cell_column(app, layout, place)).collect(),
        }
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
        let tracks = Self::tracks(app);
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
            if place < tracks.len() {
                let name = &tracks[place];
                let shown = if layout.is_some() && name.chars().count() > DETAIL_WIDTH {
                    fit(name, DETAIL_WIDTH).trim_end().to_string()
                } else {
                    name.clone()
                };
                let room = if Self::real_time_on(app) { width - SOUNDING_MARK_WIDTH } else { width };
                lines[1].push(Piece::Text {
                    column,
                    text: fit(&format!(" {shown}"), room),
                    kind: Kind::Name,
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
                    self.draw_details(app, &mut lines[2..end], &layout.track_details[place], column + TRACK_DETAIL_INDENT, here, None);
                }
            } else {
                lines[1].push(Piece::Text {
                    column,
                    text: fit_aligned(marks::MSG_ADD_ROW_MARK, width, Align::Center),
                    kind: Kind::Faint,
                });
            }
        }
        if last < tracks.len() + 1 {
            lines[1].push(Piece::More {
                column: self.cell_column(app, layout, last),
            });
        }
        lines[count - 1].push(self.grid_rule(app, layout, first, last));
    }

    fn draw_scene(&self, app: &App, layout: Option<&DetailsLayout>, lengths: &Lengths, lines: &mut [Vec<Piece>], index: usize, window: (usize, usize)) {
        let (first, last) = window;
        let tracks = Self::tracks(app);
        let count = lines.len();
        let dividers = self.dividers(app, layout, first, last);
        for line in lines[..count - 1].iter_mut() {
            line.push(dividers.clone());
        }
        lines[count - 1].push(self.grid_rule(app, layout, first, last));
        lines[1].push(Piece::Text {
            column: SCENE_LABEL_COLUMN,
            text: self.scene_label(app, lengths, index),
            kind: Kind::Name,
        });
        if let (Some(layout), true) = (layout, self.cell_open(app, &CellPlace::Scene(index))) {
            let here = self.on_scene_name() && !self.on_plus_row(app) && self.row.get() == index as i64;
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
        for (place, track) in tracks.iter().enumerate().take(last).skip(first) {
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
            lines[1].push(Piece::Text {
                column,
                text: fit(&format!(" {shown}"), width),
                kind: Kind::Plain,
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
                kind: Kind::Plain,
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
        let style = if self.picking(app) || self.moving.is_some() {
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
        let scenes_height: usize = shown.clone().map(|index| self.scene_lines(app, layout, index)).sum();
        if self.on_plus_row(app) {
            return Some(CellFrame {
                left: 0,
                right: SCENE_FRAME_RIGHT,
                top: header + scenes_height,
                inside: NAME_LINES,
                style,
            });
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
        if let Some(inset) = &self.inset {
            let switch = if inset.is_written() { &Keys::TO_PLAYED } else { &Keys::TO_WRITTEN };
            return vec![
                Self::bind(&Keys::ESCAPE_INSET),
                Self::bind(&Keys::CLOSE_INSET),
                Self::bind(&Keys::INSET_MOVE).wanting_key(),
                Self::bind(&Keys::INSET_BARS),
                Self::bind(switch),
                Self::bind(&Keys::INSET_ZOOM),
                Self::bind(&Keys::INSET_SCROLL),
            ];
        }
        if let Some(moving) = self.moving {
            let carry = match moving {
                Moving::Scene => Self::bind(&Keys::CARRY_SCENE),
                Moving::Track => Self::bind(&Keys::CARRY_TRACK),
                Moving::Clip => Self::bind(&Keys::CARRY_CLIP).wanting_key(),
            };
            return vec![Self::bind(&Keys::DROP), carry];
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
        } else if self.on_plus_row(app) {
            keys.extend([Self::bind(&Keys::ADD_SCENE), Self::bind(&Keys::ADD_SCENE_HERE)]);
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
        if let Some(inset) = &mut self.inset {
            if item.is(&Keys::ESCAPE_INSET) || item.is(&Keys::CLOSE_INSET) {
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
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&Keys::MOVE) {
            match key {
                "up" => self.row.set(self.row.get() - 1),
                "down" => self.row.set(self.row.get() + 1),
                "left" => self.column.set(self.column.get().saturating_sub(1)),
                _ => self.column.set(self.column.get() + 1),
            }
            self.clamp(app);
        } else if item.is(&Keys::MOVE_SCENE) {
            self.start_moving(app, Moving::Scene);
        } else if item.is(&Keys::MOVE_TRACK) {
            self.start_moving(app, Moving::Track);
        } else if item.is(&Keys::MOVE_CLIP) {
            self.start_moving(app, Moving::Clip);
        } else if item.is(&Keys::DROP) && self.moving.is_some() {
            self.moving = None;
        } else if item.is(&Keys::CARRY_SCENE) || item.is(&Keys::CARRY_TRACK) {
            self.carry(app, item.step_of(key).unwrap_or(0));
        } else if item.is(&Keys::CARRY_CLIP) {
            self.carry_clip(app, key);
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
            let track = Self::tracks(app)[self.track_place()].clone();
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
            let track = Self::tracks(app)[self.track_place()].clone();
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
        } else if item.is(&Keys::REMOVE_CHAIN) {
            if let Some(Target { place: Some(place), .. }) = self.picked_target(app) {
                self.remove_cell_chain(app, place);
            }
        } else if item.is(&Keys::OPEN_PATTERN) {
            let tracks = Self::tracks(app);
            if let Some(clip) = Self::clip(app, self.row.get() as usize, &tracks[self.track_place()]) {
                let name = clip.get_pattern_name();
                let crumbs = self.crumbs(app);
                app.show_page(crate::screens::pattern::open_clip_pattern(&name, crumbs, &tracks[self.track_place()]));
            }
        } else if item.is(&Keys::SHOW_DETAILS) || item.is(&Keys::HIDE_DETAILS) {
            // The other view starts from the top left, as its rows and columns are other sizes.
            app.session.shows_arrange_details = !app.session.shows_arrange_details;
            self.stop_picking();
            self.top.set(0);
            self.left.set(0);
        } else if item.is(&Keys::COPY_CLIP) {
            let tracks = Self::tracks(app);
            self.copied = Self::clip(app, self.row.get() as usize, &tracks[self.track_place()]).cloned();
            app.say(llamatron_strings::messages::MSG_COPIED_CLIP);
        } else if item.is(&Keys::EDIT_CLIP) {
            let track = Self::tracks(app)[self.track_place()].clone();
            let index = self.row.get().max(0) as usize;
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::arrange::clip_page::ClipPage { index, track },
            )));
        } else if item.is(&Keys::SCENE_SETTINGS) {
            let index = self.row.get().max(0) as usize;
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::arrange::scene_page::ScenePage { index },
            )));
        } else if self.press_edit(app, item) {
        } else if item.is(&Keys::TRACK_SETTINGS) {
            let name = Self::tracks(app)[self.track_place()].clone();
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
        let count = Self::scene_count(app) as usize;
        let header = self.header_lines(app, layout);
        let plus_row = shown.end == count && self.rows_fit(app, layout, shown.start, count, height.saturating_sub(header));
        let scenes: usize = shown.clone().map(|index| self.scene_lines(app, layout, index)).sum();
        let total = header + scenes + if plus_row { FOOTER_LINES } else { 0 };
        let mut lines: Vec<Vec<Piece>> = (0..total).map(|_| Vec::new()).collect();
        self.draw_header(app, layout, &mut lines[..header], window.0, window.1);
        let mut start = header;
        for index in shown.clone() {
            let rows = self.scene_lines(app, layout, index);
            self.draw_scene(app, layout, &lengths, &mut lines[start..start + rows], index, window);
            start += rows;
        }
        if plus_row {
            let dividers = self.dividers(app, layout, window.0, window.1);
            let footer = &mut lines[total - FOOTER_LINES..];
            for line in footer.iter_mut() {
                line.push(dividers.clone());
            }
            footer[1].push(Piece::Text {
                column: SCENE_BAR_COLUMN,
                text: marks::MSG_ADD_ROW_MARK.to_string(),
                kind: Kind::Faint,
            });
        }
        let frames: Vec<CellFrame> = self.frame(app, layout, &shown, window).into_iter().collect();
        arrange_lines(&lines, width, &frames)
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
            &[("key", Keys::CLOSE_INSET.name.into()), ("what", Keys::CLOSE_INSET.what.into())],
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

/// Start real-time playback: tell why nothing can play if so, and otherwise play, saying on the status line what started,
/// or that what (a scene or a clip, named) starts at the next bar.
pub fn play_through(app: &mut App, what: &str, said: &str, play: impl FnOnce(&mut App) -> Result<bool, String>) {
    if let Some(refusal) = app.transport.refusal(app, None) {
        app.show_page(Box::new(crate::screens::dialogs::MessageDialog::new(&refusal.title, refusal.lines)));
        return;
    }
    match play(app) {
        Ok(true) => app.say(&named(messages::MSG_STARTS_AT_NEXT_BAR, &[("what", what.into())])),
        Ok(false) => app.say(said),
        Err(problem) => app.show_page(Box::new(crate::screens::dialogs::MessageDialog::new(
            llamatron_strings::errors::ERR_CANT_PLAY_TITLE,
            vec![problem],
        ))),
    }
}
