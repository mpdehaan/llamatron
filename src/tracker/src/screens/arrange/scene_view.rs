// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Scene View (the Python interface/tracker/components/scene_view.py and inset_window.py): what one scene of Arrange
//! plays, every track's notes laid over each other in one read-only piano roll, inside an Inset Window over the page.
//!
//! Its first line says which view shows, as written or as played, which V switches, and the window's band says it too,
//! purple for written and blue for played; then what the scene plays with and where each value comes from; a legend of
//! the tracks in their colours; the chord heard on each beat and its numeral; the roll, a row for every key and the drums
//! in lanes at its foot; a sidebar of each track's details; and a line naming the notes under the cursor.

use std::cell::{Cell, RefCell};

use crate::app::App;
use crate::drawing::{fit, BoxCharacters, Style as Styles};
use crate::heard_chords::{beat_chords, HeardNote};
use crate::scene_notes::{chord_scale, effective_values, scene_notes, Effective, SceneNote, SceneNotes};
use crate::screens::arrange::details::{clip_lines, or_stock, track_lines, ADD_CHAIN};
use crate::style::Style;
use crate::text::Text;
use llamatron_math::Rational;
use llamatron_model::values::generated::note::SHARP_NAMES;
use llamatron_strings::texts::visualizers;
use llamatron_strings::{marks, named};

/// Each column of the roll is a sixteenth, drawn as many cells wide as the zoom, from FEWEST_CELLS to MOST_CELLS.
const COLUMNS_PER_WHOLE: i128 = 16;
const START_CELLS: usize = 3;
const FEWEST_CELLS: usize = 1;
const MOST_CELLS: usize = 5;
/// The labels at the left: an octave's name along its C, and a played key's name from NOTE_LABEL_COLUMN.
const LABEL_COLUMNS: usize = 8;
const NOTE_LABEL_COLUMN: usize = 4;
/// The lines above the roll's body, the chord lines at the top of the body, and the line under it.
const LINES_ABOVE: usize = 3;
const CHORD_LINES: usize = 2;
const LINES_BELOW: usize = 1;
/// The sidebar of the tracks' details, and how far [ and ] scroll it.
const SIDEBAR_COLUMNS: usize = 28;
const SIDEBAR_SCROLL: i64 = 6;
/// The keys shown beyond the highest and lowest notes, and the fewest shown.
const MARGIN_KEYS: i64 = 2;
const FEWEST_KEYS: i64 = 24;
const LOWEST_PITCH: i64 = 0;
const HIGHEST_PITCH: i64 = 127;
const MIDDLE_C: i64 = 60;
/// What the cells are drawn with.
const NOTE_CHARACTER: char = '█';
const OVERLAP_CHARACTER: char = 'X';
const READING_CHARACTER: char = '░';
const LINE_CHARACTER: char = '─';
const BAR_CHARACTER: char = '┊';
const DIVIDER_CHARACTER: &str = "│";
const SPACE: char = ' ';
/// The colours: a count of three tracks or more in black, the lines and labels dim, and the band purple while the view is
/// as written and the splash's blue while it is as played.
const COUNT_COLOUR: (u8, u8, u8) = (0, 0, 0);
const LINE_COLOUR: (u8, u8, u8) = (80, 80, 100);
const LABEL_COLOUR: (u8, u8, u8) = (150, 150, 170);
const NOTE_LABEL_COLOUR: (u8, u8, u8) = (210, 210, 225);
const WRITTEN_COLOUR: (u8, u8, u8) = (150, 80, 230);
const PLAYED_COLOUR: (u8, u8, u8) = (60, 120, 255);
/// The tracks' colours: the drum tracks take the warm ones and the others the cool ones.
const WARM_COLOURS: [(u8, u8, u8); 10] = [
    (255, 0, 0),
    (255, 128, 0),
    (255, 255, 0),
    (255, 255, 255),
    (255, 64, 64),
    (255, 192, 0),
    (255, 0, 128),
    (140, 0, 0),
    (140, 70, 0),
    (140, 140, 0),
];
const COOL_COLOURS: [(u8, u8, u8); 11] = [
    (0, 255, 0),
    (170, 0, 255),
    (0, 128, 255),
    (0, 255, 255),
    (255, 0, 255),
    (90, 90, 255),
    (0, 140, 140),
    (95, 0, 140),
    (0, 255, 128),
    (128, 255, 0),
    (0, 140, 0),
];
const CAPTION_STYLE: &str = "bold reverse";
const CURSOR_STYLE: &str = "bold reverse";
/// Which drum lane each General MIDI drum note goes in, counted from the bottom: kick, snare, hats, toms, cymbal, other.
const DRUM_LANES: [(i64, usize); 22] = [
    (35, 0),
    (36, 0),
    (37, 1),
    (38, 1),
    (39, 1),
    (40, 1),
    (42, 2),
    (44, 2),
    (46, 2),
    (41, 3),
    (43, 3),
    (45, 3),
    (47, 3),
    (48, 3),
    (50, 3),
    (49, 4),
    (51, 4),
    (52, 4),
    (53, 4),
    (55, 4),
    (57, 4),
    (59, 4),
];
const OTHER_LANE: usize = 5;
/// The Inset Window: how far in from every edge of the screen its band is, the band's thickness, the space inside it,
/// the title's line, and how far in from the band's corner the closing key's name sits.
const INSET: usize = 4;
const BORDER: usize = 1;
const PADDING: usize = 1;
const TITLE_LINES: usize = 1;
const LABEL_GAP: usize = 2;
const OUTLINE: &str = "#ffffff";

/// A row of the roll: a key by its MIDI pitch, or a drum lane by its place from the bottom.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum RollRow {
    Key(i64),
    Lane(usize),
}

/// The style that draws a colour, on a background colour or the terminal's own.
fn colour_style(colour: (u8, u8, u8), background: Option<(u8, u8, u8)>) -> Style {
    let mut words = Style::rgb(colour);
    if let Some(background) = background {
        words = format!("{words} on {}", Style::rgb(background));
    }
    Style::parse(&words)
}

/// The lane of the drum lanes a drum note goes in, counted from the bottom.
fn drum_lane(pitch: i64) -> usize {
    DRUM_LANES.iter().find(|(found, _)| *found == pitch).map_or(OTHER_LANE, |(_, lane)| *lane)
}

/// The row a note is drawn on.
fn row_of(note: &SceneNote) -> RollRow {
    if note.drum {
        RollRow::Lane(drum_lane(note.pitch))
    } else {
        RollRow::Key(note.pitch)
    }
}

/// The sixteenth a time falls in, counted from the scene's start.
fn sixteenth(time: Rational) -> i64 {
    (time * Rational::whole(COLUMNS_PER_WHOLE)).floor() as i64
}

/// Each track's colour by its place: the drum tracks warm and the others cool, in order, a group that needs more taking
/// the other group's that are left, and past every colour going round.
fn coloured(drums: &[usize], others: &[usize]) -> Vec<(usize, (u8, u8, u8))> {
    let every: Vec<(u8, u8, u8)> = COOL_COLOURS.iter().chain(WARM_COLOURS.iter()).copied().collect();
    let mut warm: Vec<(u8, u8, u8)> = WARM_COLOURS.to_vec();
    let mut cool: Vec<(u8, u8, u8)> = COOL_COLOURS.to_vec();
    let mut colours = Vec::new();
    for (places, drum) in [(others, false), (drums, true)] {
        for (count, place) in places.iter().enumerate() {
            let (own, other) = if drum { (&mut warm, &mut cool) } else { (&mut cool, &mut warm) };
            let pool = if own.is_empty() { other } else { own };
            let colour = if pool.is_empty() { every[count % every.len()] } else { pool.remove(0) };
            colours.push((*place, colour));
        }
    }
    colours
}

/// A track's name with its number, counted from 1, as the legend shows it.
fn track_label(name: &str, place: usize) -> String {
    named(marks::MSG_SCENE_VIEW_TRACK, &[("name", name.into()), ("number", (place + 1).into())])
}

/// A line cut to a width, as Rich's truncate cuts without an ellipsis, padded with spaces where pad says.
fn cut(line: &Text, width: usize, pad: bool) -> Text {
    let mut result = line.slice_cells(width);
    if pad && result.cell_len() < width {
        result.append(&SPACE.to_string().repeat(width - result.cell_len()), Styles::PLAIN);
    }
    result
}

/// A scene's notes worked out, or why the scene cannot be played.
type Found = Result<std::rc::Rc<SceneNotes>, String>;

/// One scene's notes in a read-only roll inside an Inset Window, as written or as played, with a cursor the arrows move,
/// a zoom and a sidebar of each track's details.
pub struct SceneView {
    index: usize,
    written: bool,
    /// The scene's notes, as written and as played, worked out the first time each view shows, since nothing changes
    /// while the window is open.
    cached: RefCell<[Option<Found>; 2]>,
    column: i64,
    row: Cell<usize>,
    left: Cell<i64>,
    top: Cell<usize>,
    zoom: usize,
    side_top: Cell<usize>,
}

impl SceneView {
    /// Scene View on a scene, its cursor on the scene's first note.
    pub fn new(app: &App, index: usize) -> SceneView {
        let mut view = SceneView {
            index,
            written: true,
            cached: RefCell::new([None, None]),
            column: 0,
            row: Cell::new(0),
            left: Cell::new(0),
            top: Cell::new(0),
            zoom: START_CELLS,
            side_top: Cell::new(0),
        };
        view.place_cursor(app);
        view
    }

    /// Whether it shows the scene as written.
    pub fn is_written(&self) -> bool {
        self.written
    }

    /// The place of the scene it shows.
    pub fn get_index(&self) -> usize {
        self.index
    }

    /// Show the other view, keeping the cursor where it is in time.
    pub fn switch(&mut self, app: &App) {
        self.written = !self.written;
        let count = self.rows(app).len();
        self.row.set(self.row.get().min(count.saturating_sub(1)));
    }

    /// Move the cursor to the start of the next bar, or back to the start of its bar or the one before.
    pub fn jump_bar(&mut self, app: &App, direction: i64) {
        let bar = self.notes(app).ok().map_or(COLUMNS_PER_WHOLE as i64, |notes| sixteenth(notes.bar).max(1));
        if direction > 0 {
            self.column = ((self.column / bar + 1) * bar).min(self.columns(app) - 1);
        } else {
            let within = self.column % bar;
            self.column = (self.column - if within != 0 { within } else { bar }).max(0);
        }
    }

    /// Draw each sixteenth a cell narrower or wider.
    pub fn zoom_by(&mut self, direction: i64) {
        self.zoom = (self.zoom as i64 + direction).clamp(FEWEST_CELLS as i64, MOST_CELLS as i64) as usize;
    }

    /// Scroll the sidebar of the tracks' details up or down.
    pub fn scroll_sidebar(&mut self, direction: i64) {
        self.side_top.set((self.side_top.get() as i64 + direction * SIDEBAR_SCROLL).max(0) as usize);
    }

    /// Move the cursor a sixteenth left or right, or a row up or down, stopping at the edges.
    pub fn move_cursor(&mut self, app: &App, key: &str) {
        match key {
            "left" => self.column = (self.column - 1).max(0),
            "right" => self.column = (self.column + 1).min(self.columns(app) - 1),
            "up" => self.row.set(self.row.get().saturating_sub(1)),
            _ => {
                let count = self.rows(app).len();
                self.row.set((self.row.get() + 1).min(count.saturating_sub(1)));
            }
        }
    }

    /// The window's band colour, which says which view shows.
    fn border_colour(&self) -> (u8, u8, u8) {
        if self.written {
            WRITTEN_COLOUR
        } else {
            PLAYED_COLOUR
        }
    }

    /// The scene's notes in the view showing, or why the scene cannot be played.
    fn notes(&self, app: &App) -> Result<std::rc::Rc<SceneNotes>, String> {
        let place = usize::from(!self.written);
        if let Some(found) = &self.cached.borrow()[place] {
            return found.clone();
        }
        let song = app.document.get_current_song_name();
        let found = scene_notes(app.document.get_setlist(), song, self.index, self.written, None).map(std::rc::Rc::new);
        self.cached.borrow_mut()[place] = Some(found.clone());
        found
    }

    /// What each row of the roll stands for, top first: every key from above the highest note to below the lowest, then a
    /// lane for each kind of drum when a drum plays.
    fn rows(&self, app: &App) -> Vec<RollRow> {
        let notes = self.notes(app).ok();
        let pitches: Vec<i64> = notes
            .iter()
            .flat_map(|notes| notes.notes.iter())
            .filter(|note| !note.drum)
            .map(|note| note.pitch)
            .collect();
        let mut high = (pitches.iter().copied().max().unwrap_or(MIDDLE_C) + MARGIN_KEYS).min(HIGHEST_PITCH);
        let mut low = (pitches.iter().copied().min().unwrap_or(MIDDLE_C) - MARGIN_KEYS).max(LOWEST_PITCH);
        while high - low + 1 < FEWEST_KEYS {
            high = (high + 1).min(HIGHEST_PITCH);
            low = (low - 1).max(LOWEST_PITCH);
        }
        let mut rows: Vec<RollRow> = (low..=high).rev().map(RollRow::Key).collect();
        rows.extend(self.lanes(app));
        rows
    }

    /// The drum lanes, top first, when a drum plays in the scene.
    fn lanes(&self, app: &App) -> Vec<RollRow> {
        let drums = self.notes(app).ok().is_some_and(|notes| notes.notes.iter().any(|note| note.drum));
        if !drums {
            return Vec::new();
        }
        (0..visualizers::MSG_PIANO_ROLL_DRUM_LANES.len()).rev().map(RollRow::Lane).collect()
    }

    /// How many columns of sixteenths the scene lasts.
    fn columns(&self, app: &App) -> i64 {
        self.notes(app).ok().map_or(1, |notes| sixteenth(notes.length).max(1))
    }

    /// Put the cursor on the scene's first note, its row on that note's key.
    fn place_cursor(&mut self, app: &App) {
        let Ok(notes) = self.notes(app) else { return };
        let mut first: Option<&SceneNote> = None;
        for note in notes.notes.iter().filter(|note| !note.drum) {
            if first.is_none_or(|held| note.start < held.start) {
                first = Some(note);
            }
        }
        let Some(first) = first else { return };
        self.column = sixteenth(first.start);
        let row = self.rows(app).iter().position(|row| *row == RollRow::Key(first.pitch)).unwrap_or(0);
        self.row.set(row);
    }

    /// A track's colour, each track keeping its colour from scene to scene, unless the song has more tracks than there are
    /// colours, when only the tracks that play in the scene take them.
    fn track_colour(&self, app: &App, place: usize) -> (u8, u8, u8) {
        let song = app.document.song();
        let tracks = song.tracks();
        let every = COOL_COLOURS.len() + WARM_COLOURS.len();
        let mut places: Vec<usize> = (0..tracks.len()).collect();
        if tracks.len() > every {
            let scene = &song.scenes()[self.index];
            places.retain(|each| scene.get_clip_slot(&tracks[*each].0).is_some());
        }
        let drums: Vec<usize> = places.iter().copied().filter(|each| tracks[*each].1.is_drum()).collect();
        let others: Vec<usize> = places.iter().copied().filter(|each| !drums.contains(each)).collect();
        let colours = coloured(&drums, &others);
        let fallback: Vec<(u8, u8, u8)> = COOL_COLOURS.iter().chain(WARM_COLOURS.iter()).copied().collect();
        colours
            .iter()
            .find(|(found, _)| *found == place)
            .map_or(fallback[place % every], |(_, colour)| *colour)
    }

    /// The line that says which view shows.
    fn caption(&self) -> &'static str {
        if self.written {
            marks::MSG_SCENE_VIEW_WRITTEN
        } else {
            marks::MSG_SCENE_VIEW_PLAYED
        }
    }

    /// The window's lines: the caption, the effective values and the legend across, then the chords and the roll beside
    /// the sidebar, then the line under the cursor.
    fn lines(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        let mut lines = vec![Text::styled(&cut_text(&format!("{:<width$}", self.caption()), width), CAPTION_STYLE)];
        let notes = match self.notes(app) {
            Ok(notes) => notes,
            Err(problem) => {
                let said = named(marks::MSG_SCENE_VIEW_CANT_SHOW, &[("problem", problem.as_str().into())]);
                lines.push(Text::plain(&cut_text(&said, width)));
                return lines;
            }
        };
        let song = app.document.song();
        let Some(effective) = effective_values(song, self.index) else { return lines };
        let signature = song.get_time_signature();
        let shown_signature = named(
            marks::MSG_SCENE_VIEW_SIGNATURE,
            &[("beats", signature.get_beats().into()), ("unit", signature.get_unit().into())],
        );
        let values = named(
            marks::MSG_SCENE_VIEW_EFFECTIVE,
            &[
                ("tempo", effective.tempo.as_str().into()),
                ("tempo_source", effective.tempo_source.into()),
                ("signature", shown_signature.as_str().into()),
                ("scale", effective.scale.clone().unwrap_or_default().as_str().into()),
                ("scale_source", effective.scale_source.into()),
                ("groove", effective.groove.as_str().into()),
                ("groove_source", effective.groove_source.into()),
            ],
        );
        lines.push(Text::styled(&cut_text(&values, width), Styles::DIM));
        lines.push(self.legend(app, &notes, &effective, width));
        let body_height = height.saturating_sub(LINES_ABOVE + LINES_BELOW).max(CHORD_LINES + 1);
        let body_width = width.saturating_sub(SIDEBAR_COLUMNS + 1).max(LABEL_COLUMNS + 1);
        let sixteenths = ((body_width - LABEL_COLUMNS) / self.zoom).max(1) as i64;
        let roll_height = body_height.saturating_sub(CHORD_LINES).max(1);
        self.scroll(app, sixteenths, roll_height);
        let scale = effective.scale.as_deref().and_then(|name| chord_scale(app.document.get_setlist(), name));
        let mut body = self.chord_lines(&notes, scale.as_ref(), sixteenths);
        body.extend(self.roll_lines(app, &notes, sixteenths, roll_height));
        let sidebar = self.sidebar(app, body.len());
        for (line, side) in body.iter_mut().zip(sidebar) {
            let mut joined = cut(line, body_width, true);
            joined.append(DIVIDER_CHARACTER, Styles::DIM);
            joined.append_text(&side);
            *line = joined;
        }
        lines.extend(body);
        lines.push(Text::plain(&cut_text(&self.under_cursor(app, &notes), width)));
        lines
    }

    /// Keep the cursor's column and row in the window of the roll that shows, the drum lanes always at its foot.
    fn scroll(&self, app: &App, sixteenths: i64, roll_height: usize) {
        self.left.set(self.left.get().max(self.column - sixteenths + 1).min(self.column));
        let lanes = self.lanes(app).len();
        let keys = self.rows(app).len() - lanes;
        let key_rows = roll_height.saturating_sub(lanes).max(1);
        let row = self.row.get();
        let mut top = self.top.get() as i64;
        if row < keys {
            top = top.max(row as i64 - key_rows as i64 + 1).min(row as i64);
        }
        top = top.min(keys as i64 - key_rows as i64).max(0);
        self.top.set(top as usize);
    }

    /// The legend: each track that plays in the scene in its colour with its number, a clip's own scale after it, and the
    /// mark of the clips that read the draws.
    fn legend(&self, app: &App, notes: &SceneNotes, effective: &Effective, width: usize) -> Text {
        let mut text = Text::default();
        let mut tracks: Vec<usize> = notes.notes.iter().map(|note| note.track).collect();
        tracks.sort_unstable();
        tracks.dedup();
        for track in tracks {
            let name = &notes.names[track];
            let mut entry = format!("{}{}", marks::MSG_SCENE_VIEW_LEGEND_MARK, track_label(name, track));
            if let Some((_, scale)) = effective.clip_scales.iter().find(|(found, _)| found == name) {
                entry.push_str(&named(marks::MSG_SCENE_VIEW_CLIP_SCALE, &[("scale", scale.as_str().into())]));
            }
            text.append_style(&entry, colour_style(self.track_colour(app, track), None));
            text.append(marks::MSG_SCENE_VIEW_LEGEND_GAP, Styles::PLAIN);
        }
        if !notes.marked_tracks.is_empty() {
            text.append(marks::MSG_SCENE_VIEW_REGISTERS, Styles::DIM);
        }
        cut(&text, width, false)
    }

    /// Where a sixteenth's column is drawn among the roll's cells.
    fn x_of(&self, column: i64) -> i64 {
        (column - self.left.get()) * self.zoom as i64
    }

    /// The chord heard on each beat and its numeral, each written at its beat's column where it differs from the beat's
    /// before and there is room.
    fn chord_lines(&self, notes: &SceneNotes, scale: Option<&crate::chord_text::ChordScale>, sixteenths: i64) -> Vec<Text> {
        let cells = sixteenths as usize * self.zoom;
        let mut names = vec![SPACE; cells];
        let mut numerals = vec![SPACE; cells];
        let heard: Vec<HeardNote> = notes
            .notes
            .iter()
            .map(|note| HeardNote {
                start: note.start,
                end: note.end,
                pitch: note.pitch,
                drum: note.drum,
            })
            .collect();
        let mut last: Option<String> = None;
        let mut free: i64 = 0;
        for chord in beat_chords(&heard, notes.length, notes.beat, scale) {
            let x = self.x_of(sixteenth(chord.start));
            let same = last.as_deref() == Some(chord.name.as_str());
            last = Some(chord.name.clone());
            if same || x < 0 || x >= cells as i64 || x < free {
                continue;
            }
            free = x + chord.name.chars().count().max(chord.numeral.chars().count()) as i64 + 1;
            for (place, character) in chord.name.chars().enumerate() {
                if let Some(cell) = names.get_mut(x as usize + place) {
                    *cell = character;
                }
            }
            for (place, character) in chord.numeral.chars().enumerate() {
                if let Some(cell) = numerals.get_mut(x as usize + place) {
                    *cell = character;
                }
            }
        }
        let names: String = names.into_iter().collect();
        let numerals: String = numerals.into_iter().collect();
        vec![
            Text::plain(&format!("{:<LABEL_COLUMNS$}{names}", marks::MSG_SCENE_VIEW_CHORD_LABEL)),
            Text::styled(&format!("{:<LABEL_COLUMNS$}{numerals}", marks::MSG_SCENE_VIEW_NUMERAL_LABEL), Styles::DIM),
        ]
    }

    /// The roll's rows that show: the labels, then each sixteenth's cells, the cursor's cells reversed.
    fn roll_lines(&self, app: &App, notes: &SceneNotes, sixteenths: i64, roll_height: usize) -> Vec<Text> {
        let rows = self.rows(app);
        let lanes = self.lanes(app);
        let keys = &rows[..rows.len() - lanes.len()];
        let top = self.top.get();
        let key_rows = roll_height.saturating_sub(lanes.len()).max(1);
        let mut shown: Vec<RollRow> = keys.iter().skip(top).take(key_rows).copied().collect();
        shown.extend(lanes.iter().copied());
        let first = self.left.get();
        let played: Vec<i64> = notes.notes.iter().filter(|note| !note.drum).map(|note| note.pitch).collect();
        let bar_columns = sixteenth(notes.bar).max(1);
        let cursor_row = rows.get(self.row.get()).copied();
        let mut lines = Vec::new();
        for key in &shown {
            let mut line = self.row_label(app, *key, &played);
            for column in first..first + sixteenths {
                let found: Vec<(&SceneNote, bool)> = notes
                    .notes
                    .iter()
                    .filter(|note| row_of(note) == *key)
                    .filter_map(|note| {
                        let start = sixteenth(note.start);
                        let end = sixteenth(note.end).max(start + 1);
                        (start <= column && column < end).then_some((note, column == end - 1))
                    })
                    .collect();
                let (character, mut style) = self.cell(app, *key, column, &found, bar_columns);
                if Some(*key) == cursor_row && column == self.column {
                    style = Some(match style {
                        None => Style::parse(CURSOR_STYLE),
                        Some(held) => held.and(&Style::parse(CURSOR_STYLE)),
                    });
                }
                let ends = !found.is_empty() && found.iter().all(|(_, last)| *last);
                let mut tracks: Vec<usize> = found.iter().map(|(note, _)| note.track).collect();
                tracks.sort_unstable();
                tracks.dedup();
                let shared = tracks.len() > 1;
                let middle = (self.zoom - if ends && self.zoom > 1 { 2 } else { 1 }) / 2;
                for cell in 0..self.zoom {
                    if ends && self.zoom > 1 && cell == self.zoom - 1 {
                        line.append(&SPACE.to_string(), Styles::PLAIN);
                        continue;
                    }
                    let mut shown_character = character;
                    if found.is_empty() && character == BAR_CHARACTER && cell > 0 {
                        shown_character = SPACE;
                    }
                    if shared && cell != middle {
                        shown_character = SPACE;
                    }
                    match &style {
                        Some(style) => line.append_style(&shown_character.to_string(), style.clone()),
                        None => line.append(&shown_character.to_string(), Styles::PLAIN),
                    };
                }
            }
            lines.push(line);
        }
        lines
    }

    /// A row's label: its octave's name along a C and the key's own name where a note plays it, or its lane's name.
    fn row_label(&self, app: &App, key: RollRow, played: &[i64]) -> Text {
        let label = colour_style(LABEL_COLOUR, None);
        let pitch = match key {
            RollRow::Lane(lane) => {
                let name: String = visualizers::MSG_PIANO_ROLL_DRUM_LANES[lane].chars().take(LABEL_COLUMNS - 1).collect();
                return Text::with_style(&format!("{name:<LABEL_COLUMNS$}"), label);
            }
            RollRow::Key(pitch) => pitch,
        };
        let mut cells: Vec<(char, Option<Style>)> = vec![(SPACE, None); LABEL_COLUMNS];
        if pitch % 12 == 0 {
            let octave = crate::settings::shown_octave(app.document.get_setlist(), pitch / 12);
            let shown = named(visualizers::MSG_PIANO_ROLL_OCTAVE_LABEL, &[("octave", octave.into())]);
            for (place, character) in shown.chars().take(NOTE_LABEL_COLUMN).enumerate() {
                cells[place] = (character, Some(label.clone()));
            }
        }
        if played.contains(&pitch) {
            let name_style = colour_style(NOTE_LABEL_COLOUR, None);
            for (place, character) in self.note_name(app, pitch).chars().take(LABEL_COLUMNS - NOTE_LABEL_COLUMN).enumerate() {
                cells[NOTE_LABEL_COLUMN + place] = (character, Some(name_style.clone()));
            }
        }
        let mut line = Text::default();
        for (character, style) in cells {
            match style {
                Some(style) => line.append_style(&character.to_string(), style),
                None => line.append(&character.to_string(), Styles::PLAIN),
            };
        }
        line
    }

    /// A cell's character and style: its note's; for tracks at once the first's colour behind the second's bold X, or for
    /// more the count in black; a line along a C, a mark at a bar, or a blank.
    fn cell(&self, app: &App, key: RollRow, column: i64, found: &[(&SceneNote, bool)], bar_columns: i64) -> (char, Option<Style>) {
        if let Some((note, _)) = found.first() {
            let mut tracks: Vec<usize> = found.iter().map(|(note, _)| note.track).collect();
            tracks.sort_unstable();
            tracks.dedup();
            if tracks.len() > 1 {
                let background = self.track_colour(app, tracks[0]);
                let bold = Style::parse("bold");
                if tracks.len() == 2 {
                    let style = colour_style(self.track_colour(app, tracks[1]), Some(background)).and(&bold);
                    return (OVERLAP_CHARACTER, Some(style));
                }
                let count = char::from_digit(tracks.len() as u32, 10).unwrap_or('+');
                return (count, Some(colour_style(COUNT_COLOUR, Some(background)).and(&bold)));
            }
            let character = if note.marked { READING_CHARACTER } else { NOTE_CHARACTER };
            return (character, Some(colour_style(self.track_colour(app, note.track), None)));
        }
        if matches!(key, RollRow::Key(pitch) if pitch % 12 == 0) {
            return (LINE_CHARACTER, Some(colour_style(LINE_COLOUR, None)));
        }
        if column % bar_columns == 0 {
            return (BAR_CHARACTER, Some(colour_style(LINE_COLOUR, None)));
        }
        (SPACE, None)
    }

    /// The sidebar's lines in full: each track that plays in the scene, by its name and number in its colour, then its
    /// clip's details in the scene and its own, as Arrange's details view shows them.
    fn sidebar_lines(&self, app: &App) -> Vec<Text> {
        let song = app.document.song();
        let setlist = app.document.get_setlist();
        let scene = &song.scenes()[self.index];
        let mut lines = Vec::new();
        for (place, (name, track)) in song.tracks().iter().enumerate() {
            let Some(clip) = scene.get_clip_slot(name) else { continue };
            let heading = colour_style(self.track_colour(app, place), None).and(&Style::parse("bold"));
            lines.push(Text::with_style(&track_label(name, place), heading));
            let mut details = clip_lines(setlist, song, clip);
            details.extend(track_lines(track));
            // Scene View only shows, so the + that adds a chain on Arrange is left out, and stock stands for nothing.
            details.retain(|detail| detail.target.as_ref().is_none_or(|target| target.kind != ADD_CHAIN));
            if details.is_empty() {
                details = or_stock(Vec::new());
            }
            for detail in details {
                let style = detail.colour().map_or_else(|| detail.kind.style().to_string(), crate::themes::text_style);
                lines.push(Text::styled(&format!("{SPACE}{}", detail.text), &style));
            }
            lines.push(Text::default());
        }
        lines
    }

    /// The sidebar's lines that show, from where it has been scrolled, each SIDEBAR_COLUMNS wide.
    fn sidebar(&self, app: &App, height: usize) -> Vec<Text> {
        let lines = self.sidebar_lines(app);
        self.side_top.set(self.side_top.get().min(lines.len().saturating_sub(height)));
        let mut shown: Vec<Text> = lines.into_iter().skip(self.side_top.get()).take(height).collect();
        while shown.len() < height {
            shown.push(Text::default());
        }
        shown.iter().map(|line| cut(line, SIDEBAR_COLUMNS, true)).collect()
    }

    /// The line under the roll: every note sounding at the cursor's cell, by its track and number, name and length, or
    /// where the cursor is when none.
    fn under_cursor(&self, app: &App, notes: &SceneNotes) -> String {
        let rows = self.rows(app);
        let key = rows.get(self.row.get()).copied();
        let time = Rational::new(self.column as i128, COLUMNS_PER_WHOLE);
        let mut found = Vec::new();
        for note in &notes.notes {
            if Some(row_of(note)) == key && note.start <= time && time < note.end {
                let mut text = named(
                    marks::MSG_SCENE_VIEW_NOTE,
                    &[
                        ("track", notes.names[note.track].as_str().into()),
                        ("number", (note.track + 1).into()),
                        ("note", self.note_name(app, note.pitch).as_str().into()),
                        ("length", length_text(note.end - note.start).as_str().into()),
                    ],
                );
                if note.marked {
                    text.push_str(marks::MSG_SCENE_VIEW_NOTE_READS);
                }
                found.push(text);
            }
        }
        if !found.is_empty() {
            return found.join(marks::MSG_SCENE_VIEW_NOTE_SEPARATOR);
        }
        let bar_columns = sixteenth(notes.bar).max(1);
        let (bar, within) = (self.column.div_euclid(bar_columns), self.column.rem_euclid(bar_columns));
        let beat = within / sixteenth(notes.beat).max(1);
        let place = named(marks::MSG_SCENE_VIEW_PLACE, &[("bar", (bar + 1).into()), ("beat", (beat + 1).into())]);
        named(marks::MSG_SCENE_VIEW_NOTHING_HERE, &[("place", place.as_str().into())])
    }

    /// A pitch's name with its octave in the set's octave labels.
    fn note_name(&self, app: &App, pitch: i64) -> String {
        let octave = crate::settings::shown_octave(app.document.get_setlist(), pitch.div_euclid(12));
        format!("{}{octave}", SHARP_NAMES[pitch.rem_euclid(12) as usize])
    }

    /// The screen with Scene View's Inset Window laid over it: a white outline, a band of colour with the closing key's
    /// name in its bottom corner, and within it, one cell in, the title in reverse video and the view's lines.
    pub fn drawn_over(&self, app: &App, screen: Vec<Text>, width: usize, height: usize, title: &str, closing: &str) -> Vec<Text> {
        let edge = INSET + BORDER + PADDING;
        let view_width = width.saturating_sub(2 * edge);
        let view_height = height.saturating_sub(2 * edge + TITLE_LINES);
        if view_width == 0 || view_height == 0 {
            return screen;
        }
        let mut lines = screen;
        while lines.len() < height {
            lines.push(Text::default());
        }
        let band = Style::parse(&format!("on {}", Style::rgb(self.border_colour())));
        let band_width = width - 2 * INSET;
        let band_height = height - 2 * INSET;
        let top = INSET;
        let bottom = top + band_height - 1;
        let inner_width = band_width - 2 * BORDER;
        let rule = BoxCharacters::RULE.repeat(band_width);
        let top_edge = Text::styled(&format!("{}{rule}{}", BoxCharacters::TOP_LEFT, BoxCharacters::TOP_RIGHT), OUTLINE);
        let bottom_edge = Text::styled(&format!("{}{rule}{}", BoxCharacters::BOTTOM_LEFT, BoxCharacters::BOTTOM_RIGHT), OUTLINE);
        lines[top - 1] = laid_over(&lines[top - 1], INSET - 1, &top_edge);
        lines[bottom + 1] = laid_over(&lines[bottom + 1], INSET - 1, &bottom_edge);
        let mut contents = vec![Text::default(); PADDING];
        contents.push(Text::styled(fit(title, view_width).trim_end(), Styles::REVERSE));
        contents.extend(self.lines(app, view_width, view_height).into_iter().take(view_height));
        for (row, line) in lines.iter_mut().enumerate().take(bottom + 1).skip(top) {
            let mut piece = Text::default();
            piece.append(BoxCharacters::BAR, OUTLINE);
            if row == top || row == bottom {
                piece.append_style(&SPACE.to_string().repeat(band_width), band.clone());
            } else {
                piece.append_style(&SPACE.to_string().repeat(BORDER), band.clone());
                let mut body = Text::plain(&SPACE.to_string().repeat(PADDING));
                if let Some(line) = contents.get(row - top - BORDER) {
                    body.append_text(&cut(line, view_width, true));
                }
                piece.append_text(&cut(&body, inner_width, true));
                piece.append_style(&SPACE.to_string().repeat(BORDER), band.clone());
            }
            piece.append(BoxCharacters::BAR, OUTLINE);
            *line = laid_over(line, INSET - 1, &piece);
        }
        let closing_start = INSET + band_width - LABEL_GAP - closing.chars().count();
        lines[bottom] = laid_over(&lines[bottom], closing_start, &Text::styled(closing, Styles::REVERSE));
        lines
    }
}

/// Text cut to a width of characters, as a Python slice cuts.
fn cut_text(text: &str, width: usize) -> String {
    text.chars().take(width).collect()
}

/// An exact length as a file holds it, a whole number or text like 3/16.
fn length_text(length: Rational) -> String {
    if length.denominator() == 1 {
        length.numerator().to_string()
    } else {
        format!("{}/{}", length.numerator(), length.denominator())
    }
}

/// A screen line with a piece laid over it from a column, the line's text either side kept.
pub fn laid_over(line: &Text, start: usize, piece: &Text) -> Text {
    let mut under = line.clone();
    let end = start + piece.cell_len();
    if under.cell_len() < end {
        under.append(&SPACE.to_string().repeat(end - under.cell_len()), Styles::PLAIN);
    }
    let mut result = under.slice(0, start);
    result.append_text(piece);
    result.append_text(&under.slice(end, under.cell_len()));
    result
}
