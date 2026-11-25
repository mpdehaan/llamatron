// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Arrange (the Python screens/arrange/arrange_page.py and arrange_drawing.py): the current song's scenes down and tracks
//! across, each clip with its pattern and a bar as long as it plays, the cursor's cell in a double-lined frame, and the
//! keys of what the cursor is on. Its details, Scene View and Move mode are not ported yet, and the page says so there.

use crate::app::App;
use crate::drawing::{fit, fit_aligned, Align, Style};
use crate::keybindings::{ArrangePage as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::lengths::Lengths;
use crate::page::{clock, Duration, Page};
use crate::screens::arrange::grid::{arrange_lines, CellFrame, Kind, LengthBar, Piece};
use crate::screens::not_ported::NotPorted;
use crate::text::Text;
use crate::themes::Colour;
use llamatron_model::file::data::Data;
use llamatron_model::objects::song::{ClipSlot, Scene};
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, SceneSetting, SetlistSetting};
use llamatron_strings::{labels, legends, marks, named, names};
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

/// A mode of Arrange not ported yet: carrying a scene, a track or a clip, Scene View over the page, or a cell's details
/// locked open; the page leaves it by its own keys and says it is not ported while in it.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Unported {
    Moving,
    SceneView,
    Locked,
}

pub struct ArrangePage {
    mode: Cell<Option<Unported>>,
    /// The clip copied with C, which V pastes.
    copied: Option<ClipSlot>,
    /// Whether the details view showed when the page last answered, which is not ported yet and names the page so.
    details_now: Cell<bool>,
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
fn clip_text(clip: &ClipSlot) -> String {
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
        shown.push_str(&named(marks::MSG_REPEAT_MARK, &[("repeat", clip.get_repeat().into())]));
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
            mode: Cell::new(None),
            copied: None,
            details_now: Cell::new(false),
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
                keys.push(Self::bind(&Keys::PLAY_SCENE));
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
                        keys.push(Self::bind(&Keys::PLAY_CLIP));
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
    fn has_cursor_cell(&self, app: &App) -> bool {
        if self.on_header() {
            return !self.on_corner() && !self.on_track_plus(app);
        }
        if self.on_plus_row(app) {
            return false;
        }
        if self.on_scene_name() {
            return true;
        }
        Self::clip(app, self.row.get() as usize, &Self::tracks(app)[self.track_place()]).is_some()
    }

    fn cell_column(&self, place: usize) -> usize {
        SCENE_WIDTH + (place - self.left.get()) * (CELL_WIDTH + COLUMN_EXTRA)
    }

    fn visible_tracks(&self, app: &App, width: usize) -> (usize, usize) {
        let count = ((width.saturating_sub(SCENE_WIDTH + 1)) / (CELL_WIDTH + COLUMN_EXTRA)).max(1);
        let total = Self::tracks(app).len() + 1;
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

    fn rows_fit(first: usize, last: usize, room: usize, count: usize) -> bool {
        let mut height = (last - first) * SCENE_LINES;
        if last == count {
            height += FOOTER_LINES;
        }
        height <= room
    }

    fn visible_scenes(&self, app: &App, height: usize) -> std::ops::Range<usize> {
        let count = Self::scene_count(app) as usize;
        let room = height.saturating_sub(HEADER_LINES);
        let wanted = (self.row.get().max(0) as usize).min(count);
        let mut top = self.top.get().min(wanted);
        while top < wanted && !Self::rows_fit(top, wanted, room, count) {
            top += 1;
        }
        let mut stop = top + 1;
        while stop <= count && Self::rows_fit(top, stop, room, count) {
            stop += 1;
        }
        self.top.set(top);
        top..(stop.min(count))
    }

    fn dividers(&self, first: usize, last: usize) -> Piece {
        Piece::Dividers {
            double_at: SCENE_WIDTH,
            columns: (first + 1..=last).map(|place| self.cell_column(place)).collect(),
            faint: false,
        }
    }

    fn grid_rule(&self, first: usize, last: usize) -> Piece {
        Piece::Rule {
            end: self.cell_column(last),
            double_at: SCENE_WIDTH,
            crosses: (first + 1..last).map(|place| self.cell_column(place)).collect(),
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

    fn draw_header(&self, app: &App, lines: &mut [Vec<Piece>], first: usize, last: usize) {
        let tracks = Self::tracks(app);
        let count = lines.len();
        for line in lines[..count - 1].iter_mut() {
            line.push(self.dividers(first, last));
        }
        if Self::real_time_on(app) {
            let button = named(marks::MSG_SONG_BUTTON, &[("mark", marks::MSG_PLAY_MARK.into())]);
            lines[1].push(Piece::Text {
                column: SCENE_LABEL_COLUMN,
                text: button,
                kind: Kind::Faint,
            });
        }
        for place in first..last {
            let column = self.cell_column(place) + FRAME_ROOM + 1;
            if place < tracks.len() {
                let width = if Self::real_time_on(app) {
                    CELL_WIDTH - SOUNDING_MARK_WIDTH
                } else {
                    CELL_WIDTH
                };
                lines[1].push(Piece::Text {
                    column,
                    text: fit(&format!(" {}", tracks[place]), width),
                    kind: Kind::Name,
                });
            } else {
                lines[1].push(Piece::Text {
                    column,
                    text: fit_aligned(marks::MSG_ADD_ROW_MARK, CELL_WIDTH, Align::Center),
                    kind: Kind::Faint,
                });
            }
        }
        if last < tracks.len() + 1 {
            lines[1].push(Piece::More {
                column: self.cell_column(last),
            });
        }
        lines[count - 1].push(self.grid_rule(first, last));
    }

    fn draw_scene(&self, app: &App, lengths: &Lengths, lines: &mut [Vec<Piece>], index: usize, window: (usize, usize)) {
        let (first, last) = window;
        let tracks = Self::tracks(app);
        let count = lines.len();
        for line in lines[..count - 1].iter_mut() {
            line.push(self.dividers(first, last));
        }
        lines[count - 1].push(self.grid_rule(first, last));
        lines[1].push(Piece::Text {
            column: SCENE_LABEL_COLUMN,
            text: self.scene_label(app, lengths, index),
            kind: Kind::Name,
        });
        let scene_bar = LengthBar {
            width: SCENE_WIDTH - SCENE_BAR_COLUMN - 2,
            hatched: true,
        };
        lines[2].push(Piece::Text {
            column: SCENE_BAR_COLUMN,
            text: scene_bar.draw(lengths.scene_seconds(index), lengths.longest_scene_seconds()),
            kind: Kind::Plain,
        });
        let real_time = Self::real_time_on(app);
        if real_time {
            lines[2].push(Piece::PlayButton {
                column: SCENE_LABEL_COLUMN,
                playing: false,
            });
        }
        for (place, track) in tracks.iter().enumerate().take(last).skip(first) {
            let column = self.cell_column(place) + FRAME_ROOM + 1;
            let Some(clip) = Self::clip(app, index, track) else {
                if self.row.get() == index as i64 && self.in_a_track_column() && !self.on_header() && self.track_place() == place {
                    lines[1].push(Piece::Text {
                        column,
                        text: fit_aligned(marks::MSG_ADD_ROW_MARK, CELL_WIDTH, Align::Center),
                        kind: Kind::Plain,
                    });
                    lines[2].push(Piece::Text {
                        column,
                        text: fit_aligned(legends::What::ADD, CELL_WIDTH, Align::Center),
                        kind: Kind::Plain,
                    });
                }
                continue;
            };
            lines[1].push(Piece::Text {
                column,
                text: fit(&format!(" {}", clip_text(clip)), CELL_WIDTH),
                kind: Kind::Plain,
            });
            let total = lengths.scene_play_seconds(index);
            let (bar, bar_column) = if real_time {
                lines[2].push(Piece::PlayButton { column, playing: false });
                (
                    LengthBar {
                        width: CELL_WIDTH - 2 - PLAY_BUTTON_WIDTH,
                        hatched: false,
                    },
                    column + 1 + PLAY_BUTTON_WIDTH,
                )
            } else {
                (
                    LengthBar {
                        width: CELL_WIDTH - 2,
                        hatched: false,
                    },
                    column + 1,
                )
            };
            let text = if clip.loops() {
                bar.full()
            } else {
                bar.draw(lengths.clip_seconds(index, track), total)
            };
            lines[2].push(Piece::Text {
                column: bar_column,
                text,
                kind: Kind::Plain,
            });
        }
    }

    fn frame(&self, app: &App, shown: &std::ops::Range<usize>, window: (usize, usize)) -> Option<CellFrame> {
        let (first, last) = window;
        let names = HEADER_LINES - 3;
        let around = |place: usize, top: usize, inside: usize| {
            let left = self.cell_column(place) + FRAME_ROOM;
            CellFrame {
                left,
                right: left + CELL_WIDTH + 1,
                top,
                inside,
                style: Style::SELECTED_EDGE,
            }
        };
        if self.on_corner() {
            return Some(CellFrame {
                left: 0,
                right: SCENE_FRAME_RIGHT,
                top: 0,
                inside: names,
                style: Style::SELECTED_EDGE,
            });
        }
        if self.on_header() {
            let place = self.track_place();
            return (first <= place && place < last).then(|| around(place, 0, names));
        }
        let scenes_height = shown.len() * SCENE_LINES;
        if self.on_plus_row(app) {
            return Some(CellFrame {
                left: 0,
                right: SCENE_FRAME_RIGHT,
                top: HEADER_LINES + scenes_height,
                inside: NAME_LINES,
                style: Style::SELECTED_EDGE,
            });
        }
        let row = self.row.get() as usize;
        if !shown.contains(&row) {
            return None;
        }
        let line = HEADER_LINES + (row - shown.start) * SCENE_LINES;
        let inside = SCENE_LINES - 1 - LINES_UNDER_A_SCENE;
        if self.on_scene_name() {
            return Some(CellFrame {
                left: 0,
                right: SCENE_FRAME_RIGHT,
                top: line,
                inside,
                style: Style::SELECTED_EDGE,
            });
        }
        Some(around(self.track_place(), line, inside))
    }
}

impl Page for ArrangePage {
    fn is_ported(&self) -> bool {
        self.mode.get().is_none() && !self.details_now.get()
    }

    fn name(&self) -> &'static str {
        if self.details_now.get() || self.mode.get().is_some() {
            crate::screens::not_ported::NOT_PORTED
        } else {
            "ArrangePage"
        }
    }

    fn stack_name(&self) -> &str {
        "ArrangePage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        self.clamp(app);
        match self.mode.get() {
            Some(Unported::Moving) => return vec![Self::bind(&Keys::DROP)],
            Some(Unported::SceneView) => return vec![Self::bind(&Keys::ESCAPE_INSET), Self::bind(&Keys::CLOSE_INSET)],
            Some(Unported::Locked) => {
                return vec![
                    Self::bind(&Keys::ESCAPE_CELL),
                    Self::bind(&Keys::OUT_OF_DETAILS),
                    Self::bind(&Keys::CLOSE_DETAILS),
                ]
            }
            None => {}
        }
        let mut keys = vec![Self::bind(&Keys::BACK), Self::bind(&Keys::MOVE).wanting_key()];
        if self.on_header() {
            keys.extend(self.header_keys(app));
        } else if self.on_plus_row(app) {
            keys.extend([Self::bind(&Keys::ADD_SCENE), Self::bind(&Keys::ADD_SCENE_HERE)]);
        } else {
            keys.extend(self.scene_row_keys(app));
        }
        if self.has_cursor_cell(app) {
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
        } else if item.is(&Keys::MOVE_SCENE) || item.is(&Keys::MOVE_CLIP) || item.is(&Keys::MOVE_TRACK) {
            self.mode.set(Some(Unported::Moving));
        } else if item.is(&Keys::SCENE_VIEW) {
            self.mode.set(Some(Unported::SceneView));
        } else if item.is(&Keys::INTO_DETAILS) {
            self.mode.set(Some(Unported::Locked));
        } else if item.is(&Keys::DROP)
            || item.is(&Keys::ESCAPE_INSET)
            || item.is(&Keys::CLOSE_INSET)
            || item.is(&Keys::ESCAPE_CELL)
            || item.is(&Keys::OUT_OF_DETAILS)
        {
            self.mode.set(None);
        } else if item.is(&Keys::CLOSE_DETAILS) {
            self.mode.set(None);
            app.session.shows_arrange_details = false;
        } else if item.is(&Keys::OPEN_PATTERN) {
            let tracks = Self::tracks(app);
            if let Some(clip) = Self::clip(app, self.row.get() as usize, &tracks[self.track_place()]) {
                let name = clip.get_pattern_name();
                app.show_page(crate::screens::pattern::open_pattern(&name));
            }
        } else if item.is(&Keys::SHOW_DETAILS) || item.is(&Keys::HIDE_DETAILS) {
            app.session.shows_arrange_details = !app.session.shows_arrange_details;
        } else if item.is(&Keys::COPY_CLIP) {
            let tracks = Self::tracks(app);
            self.copied = Self::clip(app, self.row.get() as usize, &tracks[self.track_place()]).cloned();
            app.say(llamatron_strings::messages::MSG_COPIED_CLIP);
        } else if item.is(&Keys::EDIT_CLIP) {
            app.show_page(Box::new(NotPorted { name: "ClipPage".to_string() }));
        } else if item.is(&Keys::SCENE_SETTINGS) {
            let index = self.row.get().max(0) as usize;
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::arrange::scene_page::ScenePage { index },
            )));
        } else if item.is(&Keys::TRACK_SETTINGS) {
            let name = Self::tracks(app)[self.track_place()].clone();
            app.show_page(Box::new(crate::screens::field_page::FieldPage::new(
                crate::screens::arrange::track_editor::TrackEditor { name },
            )));
        }
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        self.details_now.set(app.session.shows_arrange_details);
        self.clamp(app);
        let lengths = Lengths::of(app.document.get_setlist(), app.document.song());
        let window = self.visible_tracks(app, width);
        let shown = self.visible_scenes(app, height);
        let count = Self::scene_count(app) as usize;
        let plus_row = shown.end == count && Self::rows_fit(shown.start, count, height.saturating_sub(HEADER_LINES), count);
        let total = HEADER_LINES + shown.len() * SCENE_LINES + if plus_row { FOOTER_LINES } else { 0 };
        let mut lines: Vec<Vec<Piece>> = (0..total).map(|_| Vec::new()).collect();
        self.draw_header(app, &mut lines[..HEADER_LINES], window.0, window.1);
        let mut start = HEADER_LINES;
        for index in shown.clone() {
            self.draw_scene(app, &lengths, &mut lines[start..start + SCENE_LINES], index, window);
            start += SCENE_LINES;
        }
        if plus_row {
            let footer = &mut lines[total - FOOTER_LINES..];
            for line in footer.iter_mut() {
                line.push(self.dividers(window.0, window.1));
            }
            footer[1].push(Piece::Text {
                column: SCENE_BAR_COLUMN,
                text: marks::MSG_ADD_ROW_MARK.to_string(),
                kind: Kind::Faint,
            });
        }
        let frames: Vec<CellFrame> = self.frame(app, &shown, window).into_iter().collect();
        arrange_lines(&lines, width, &frames)
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::ARRANGE.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        None
    }

    fn duration(&self, app: &App) -> Duration {
        Duration::Seconds(Lengths::of(app.document.get_setlist(), app.document.song()).song_seconds())
    }
}
