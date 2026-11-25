// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The pattern editor (the Python screens/pattern/pattern_editor.py, grid_drawing.py, roll_drawing.py and
//! components/piano_roll.py): one pattern's steps on the piano roll, a row per note of the scale across the octaves with notes
//! as bars, under a header of the pattern's settings and over a line describing the cursor's step. The rows view is not
//! ported yet, and the page says so while it shows.

use crate::app::App;
use crate::drawing::{fit, Style, SPACE};
use crate::forms::pattern_grid::{self as grid, CellKind, Edge, LabelKind, RollCell, RollRow, Rule, RuleKind, CELL_WIDTH, EDGE_WIDTH, MARK_COLUMN};
use crate::keybindings::{KeyClass, PatternEditor as Keys, PatternRows as RowsKeys, PianoRoll as RollKeys};
use crate::keys::{in_order, KeyItem};
use crate::page::{clock_exact, Duration, Page};
use crate::patterns::{
    self, covering_notes, note_span, partial_cell, pattern_octave_range, pattern_scale, scale_half_steps, scale_root, scales_of_pattern, value,
};
use crate::screens::pattern::rows_view::{RowName, Rows};
use crate::settings::{named_in, octave_labels, shown_octave};
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::naming::same_name;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::schema::generated::file_format::{PatternSetting, Row, Section};
use llamatron_model::schema::generated::limits::{MAX_OCTAVE, MIN_DEGREE, MIN_OCTAVE};
use llamatron_model::values::generated::note::ROOT_NAMES;
use llamatron_model::values::note::Note;
use llamatron_strings::{labels, marks, messages, named, names};
use std::cell::Cell;
use std::collections::{BTreeMap, BTreeSet};

/// The lines the roll's header, rules, numbers and description take around its rows, and the fewest rows it shows.
const LINES_AROUND_ROWS: usize = 7;
const LINES_AFTER_GRID: usize = 2;
/// The legend's usual height, which the Degree gauge is fitted to, so that it keeps one height as the cursor moves.
const LEGEND_LINES: usize = 4;
const TOP_PITCH_LINE: usize = 3;
const HALF_STEPS_PER_OCTAVE: i64 = 12;
/// The octave a scale's notes are spelled in.
const SPELLING_OCTAVE: i64 = 4;
const REFERENCE_OCTAVE: i64 = 5;

/// The part of the grid on screen: its first and last steps (the last excluded), the steps that start a beat, and how wide
/// the label column is.
struct Window {
    first: usize,
    last: usize,
    beats: Vec<usize>,
    label_width: usize,
}

pub struct PatternEditor {
    pub name: String,
    step: Cell<usize>,
    first_step: Cell<usize>,
    pitch: Cell<Option<i64>>,
    top_pitch: Cell<Option<i64>>,
    /// Whether the roll showed when the page last answered, which names the page for the screen tour.
    on_roll_now: Cell<bool>,
    /// The rows view's cursor, by its place among the rows it can reach, and the first scrolled row shown.
    row: Cell<usize>,
    first_row: Cell<usize>,
    gauge_rows: Cell<usize>,
    /// The digits typed into the cursor's cell, so that a second digit makes a number with the first.
    typed: std::cell::RefCell<String>,
    /// The crumbs of the page a clip opened the editor from, Arrange or the clip page, which come first in the editor's so
    /// that they say where ESC goes back to; None when the Patterns page opened it.
    opener_crumbs: Option<Vec<String>>,
}

/// What the roll needs to know of the pattern and its scale, gathered once a key or a drawing.
struct Roll<'a> {
    setlist: &'a Setlist,
    pattern: &'a Pattern,
    scale: Option<String>,
    size: i64,
    per_octave: i64,
    scale_steps: Vec<i64>,
    step_size: Rational,
    covering: BTreeMap<usize, usize>,
    default_octave: i64,
    octaves: Option<(i64, i64)>,
}

impl<'a> Roll<'a> {
    fn of(app: &'a App, name: &str) -> Roll<'a> {
        let setlist = app.document.get_setlist();
        let song = app.document.song();
        let pattern = setlist.get_pattern(name).expect("the editor's pattern is in the set");
        let scale = pattern_scale(setlist, song, name);
        let size = match &scale {
            Some(scale) => scale_half_steps(setlist, scale).len() as i64,
            None => patterns::degree_limit(setlist, song, name).max(7) as i64,
        };
        let per_octave = if scale.is_some() { HALF_STEPS_PER_OCTAVE } else { size };
        let scale_steps = match &scale {
            Some(scale) => scale_half_steps(setlist, scale),
            None => (0..size).collect(),
        };
        let step_size = setlist.get_pattern_step_size(pattern);
        let default_octave = if pattern.is_drum() {
            setlist.get_default_drum_octave()
        } else {
            setlist.get_default_octave()
        };
        Roll {
            setlist,
            pattern,
            scale,
            size,
            per_octave,
            scale_steps,
            step_size,
            covering: covering_notes(pattern, step_size),
            default_octave,
            octaves: pattern_octave_range(setlist, name),
        }
    }

    fn highest_pitch(&self) -> i64 {
        (MAX_OCTAVE + 1) * self.per_octave - 1
    }

    fn clamped(&self, pitch: i64) -> i64 {
        pitch.clamp(0, self.highest_pitch())
    }

    fn accidental_symbol(&self, step: usize) -> Option<&'a str> {
        value(self.pattern, Row::ACCIDENTAL, step)
            .and_then(Data::as_str)
            .filter(|symbol| *symbol == "#" || *symbol == "b")
    }

    fn step_octave(&self, step: usize) -> i64 {
        value(self.pattern, Row::OCTAVE, step)
            .and_then(Data::as_whole)
            .map_or(self.default_octave, |whole| whole as i64)
    }

    fn grabs(&self, step: usize) -> bool {
        matches!(value(self.pattern, Row::GRAB, step), Some(Data::Bool(true)))
    }

    fn pitch_of(&self, step: usize) -> Option<i64> {
        let degree = match value(self.pattern, Row::DEGREE, step).and_then(Data::as_whole) {
            Some(degree) => degree as i64,
            None if self.grabs(step) => MIN_DEGREE,
            None => return None,
        };
        let (octaves_up, place) = ((degree - MIN_DEGREE).div_euclid(self.size), (degree - MIN_DEGREE).rem_euclid(self.size));
        let mut pitch = (self.step_octave(step) + octaves_up) * self.per_octave + self.scale_steps[place as usize];
        if self.scale.is_some() {
            pitch += match self.accidental_symbol(step) {
                Some("#") => 1,
                Some("b") => -1,
                _ => 0,
            };
        }
        Some(self.clamped(pitch))
    }

    fn is_degree(&self, pitch: i64) -> bool {
        self.scale_steps.contains(&pitch.rem_euclid(self.per_octave))
    }

    /// The degree, octave and accidental a row writes.
    fn note_at(&self, pitch: i64) -> (i64, i64, Option<&'static str>) {
        let (octave, within) = (pitch.div_euclid(self.per_octave), pitch.rem_euclid(self.per_octave));
        if let Some(place) = self.scale_steps.iter().position(|step| *step == within) {
            return (place as i64 + MIN_DEGREE, octave, None);
        }
        let below = self.scale_steps.iter().rposition(|step| *step < within).unwrap_or(0);
        let above = self.scale_steps.get(below + 1).copied().unwrap_or(self.per_octave);
        let flats = self.scale.as_ref().is_some_and(|scale| scale_root(self.setlist, scale).ends_with('b'));
        if within - self.scale_steps[below] == 1 && !(flats && above - within == 1) {
            return (below as i64 + MIN_DEGREE, octave, Some("#"));
        }
        let length = self.scale_steps.len();
        (
            (below + 1) as i64 % length as i64 + MIN_DEGREE,
            octave + ((below + 1) / length) as i64,
            Some("b"),
        )
    }

    /// Every row the roll has, highest first: a row per degree of every octave, and a row between two degrees where a note is
    /// sharp or flat.
    fn rows(&self) -> Vec<i64> {
        let mut pitches: BTreeSet<i64> = BTreeSet::new();
        for octave in 0..=MAX_OCTAVE {
            for step in &self.scale_steps {
                pitches.insert(octave * self.per_octave + step);
            }
        }
        for start in patterns::note_steps(self.pattern) {
            if let Some(pitch) = self.pitch_of(start) {
                pitches.insert(pitch);
            }
        }
        pitches.into_iter().rev().collect()
    }

    fn snapped(&self, pitch: i64, rows: &[i64]) -> i64 {
        rows.iter()
            .find(|row| **row <= pitch)
            .copied()
            .unwrap_or(*rows.last().expect("the roll has rows"))
    }

    fn row_label(&self, pitch: i64) -> String {
        let (degree, octave, accidental) = self.note_at(pitch);
        let shown = |octave: i64| shown_octave(self.setlist, octave).to_string();
        let label = |note: String, degree: String| {
            named(
                labels::MSG_ROLL_ROW_LABEL,
                &[("note", note.as_str().into()), ("degree", degree.as_str().into())],
            )
        };
        let Some(scale) = &self.scale else {
            return label(
                named(marks::MSG_ROLL_OCTAVE_ONLY, &[("octave", shown(octave).as_str().into())]),
                degree.to_string(),
            );
        };
        let root = scale_root(self.setlist, scale);
        let Ok(at) = Note::new(&root, octave, None, None, false) else {
            return String::new();
        };
        if accidental.is_some() {
            let (name, sounding) = at.spelled_half_step(pitch.rem_euclid(self.per_octave));
            return label(format!("{name}{}", shown(sounding)), String::new()).trim_end().to_string();
        }
        let place = (degree - MIN_DEGREE) as usize;
        let spelling = Note::new(&root, SPELLING_OCTAVE, None, None, false).expect("a scale's root is a note");
        let sounding = octave + (spelling.get_midi_number() + self.scale_steps[place]).div_euclid(HALF_STEPS_PER_OCTAVE) - SPELLING_OCTAVE;
        let name = spelling.half_step(self.scale_steps[place]).map(|note| note.get_name()).unwrap_or("");
        label(format!("{name}{}", shown(sounding)), degree.to_string())
    }

    fn widest_row_label(&self) -> usize {
        let octave = [MIN_OCTAVE, MAX_OCTAVE]
            .iter()
            .map(|number| shown_octave(self.setlist, *number).to_string())
            .max_by_key(|text| text.len())
            .unwrap_or_default();
        let mut notes = vec![named(marks::MSG_ROLL_OCTAVE_ONLY, &[("octave", octave.as_str().into())])];
        notes.extend(ROOT_NAMES.iter().map(|name| format!("{name}{octave}")));
        notes
            .iter()
            .map(|note| {
                named(
                    labels::MSG_ROLL_ROW_LABEL,
                    &[("note", note.as_str().into()), ("degree", self.size.to_string().as_str().into())],
                )
                .chars()
                .count()
            })
            .max()
            .unwrap_or(0)
    }

    fn starts_an_octave(&self, pitch: i64) -> bool {
        pitch.rem_euclid(self.per_octave) == 0
    }

    fn in_range(&self, pitch: i64) -> bool {
        match self.octaves {
            None => true,
            Some((lowest, highest)) => (lowest..=highest).contains(&pitch.div_euclid(self.per_octave)),
        }
    }
}

impl PatternEditor {
    pub fn new(name: &str) -> PatternEditor {
        PatternEditor {
            name: name.to_string(),
            step: Cell::new(0),
            first_step: Cell::new(0),
            pitch: Cell::new(None),
            top_pitch: Cell::new(None),
            on_roll_now: Cell::new(true),
            row: Cell::new(0),
            first_row: Cell::new(0),
            gauge_rows: Cell::new(7),
            opener_crumbs: None,
            typed: std::cell::RefCell::new(String::new()),
        }
    }

    /// The editor opened from a clip's page, whose crumbs come before the pattern's.
    pub fn opened_from(name: &str, opener_crumbs: Vec<String>) -> PatternEditor {
        PatternEditor {
            opener_crumbs: Some(opener_crumbs),
            ..PatternEditor::new(name)
        }
    }

    fn on_roll(&self, app: &App) -> bool {
        let drum = app.document.get_setlist().get_pattern(&self.name).is_some_and(Pattern::is_drum);
        !drum && app.session.on_roll
    }

    fn step_count(&self, app: &App) -> usize {
        app.document
            .get_setlist()
            .get_pattern(&self.name)
            .map_or(1, |pattern| pattern.get_steps() as usize)
    }

    fn keep_step(&self, app: &App) -> usize {
        let step = self.step.get().min(self.step_count(app).saturating_sub(1));
        self.step.set(step);
        step
    }

    /// Put the cursor on the pattern's first note, or on the root in the default octave, the first time, and keep it on a row.
    fn place_cursor(&self, roll: &Roll, rows: &[i64]) -> i64 {
        let pitch = match self.pitch.get() {
            Some(pitch) => pitch,
            None => patterns::note_steps(roll.pattern)
                .first()
                .and_then(|step| roll.pitch_of(*step))
                .unwrap_or(roll.default_octave * roll.per_octave),
        };
        let pitch = roll.snapped(roll.clamped(pitch), rows);
        self.pitch.set(Some(pitch));
        pitch
    }

    fn label_width(&self, app: &App, roll: &Roll) -> usize {
        let rows_width = self.rows(app).widest_label();
        if roll.pattern.is_drum() {
            return rows_width;
        }
        rows_width.max(roll.widest_row_label() + 2)
    }

    fn rows<'a>(&self, app: &'a App) -> Rows<'a> {
        let setlist = app.document.get_setlist();
        let song = app.document.song();
        let pattern = setlist.get_pattern(&self.name).expect("the editor's pattern is in the set");
        let default_octave = if pattern.is_drum() {
            setlist.get_default_drum_octave()
        } else {
            setlist.get_default_octave()
        };
        Rows {
            setlist,
            song,
            pattern,
            name: self.name.clone(),
            scale: pattern_scale(setlist, song, &self.name),
            open: &app.session.open_sections,
            gauge_rows: self.gauge_rows.get(),
            default_octave,
        }
    }

    fn row_cursor(&self, rows: &Rows) -> (usize, RowName) {
        let reachable = rows.reachable();
        let place = self.row.get().min(reachable.len() - 1);
        self.row.set(place);
        (place, reachable[place].clone())
    }

    fn steps_shown(&self, width: usize, label_width: usize) -> usize {
        (width.saturating_sub(label_width + 2) / (CELL_WIDTH + 1)).max(1)
    }

    fn window_of_steps(&self, count: usize, shown: usize) -> (usize, usize) {
        let step = self.step.get();
        let mut first = self.first_step.get().min(count.saturating_sub(shown));
        if step < first {
            first = step;
        } else if step >= first + shown {
            first = step + 1 - shown;
        }
        self.first_step.set(first);
        (first, (first + shown).min(count))
    }

    fn steps_shown_text(&self, count: usize, first: usize, last: usize) -> String {
        if last - first >= count {
            return String::new();
        }
        let before = if first > 0 { marks::MSG_MORE_BEFORE } else { "" };
        let after = if last < count { marks::MSG_MORE_AFTER } else { "" };
        named(
            marks::MSG_STEPS_SHOWN,
            &[
                ("before", before.into()),
                ("first", (first + 1).into()),
                ("last", last.into()),
                ("after", after.into()),
            ],
        )
    }

    fn beats(&self, app: &App, roll: &Roll) -> Vec<usize> {
        let signature = roll.pattern.get_time_signature().unwrap_or_else(|| app.document.song().get_time_signature());
        (0..roll.pattern.get_steps() as usize)
            .filter(|step| signature.starts_a_beat(roll.step_size * Rational::whole(*step as i128)))
            .collect()
    }

    fn scale_said(&self, app: &App, roll: &Roll) -> String {
        if roll.pattern.is_drum() {
            return named(labels::MSG_SCALE_HEADER, &[("scale", labels::MSG_NO_SCALE_NEEDED.into())]);
        }
        let scales = scales_of_pattern(roll.setlist, app.document.song(), &self.name);
        match scales.as_slice() {
            [] => named(labels::MSG_SCALE_HEADER, &[("scale", messages::MSG_NO_SCALE.into())]),
            [scale] => {
                let root = scale_root(roll.setlist, scale);
                let kind = match roll.setlist.get_item(Section::SCALES, scale) {
                    Some(llamatron_model::objects::setlist::Item::Scale(found)) => found.get_kind().as_str().unwrap_or("").to_string(),
                    _ => String::new(),
                };
                let default = named(names::MSG_DEFAULT_SCALE_NAME, &[("root", root.as_str().into()), ("kind", kind.as_str().into())]);
                let legacy = named(
                    names::MSG_LEGACY_SCALE_NAME,
                    &[("root", root.as_str().into()), ("kind", title_case(&kind.replace('_', " ")).as_str().into())],
                );
                if same_name(scale, &default) || same_name(scale, &legacy) {
                    return named(labels::MSG_SCALE_HEADER, &[("scale", scale.as_str().into())]);
                }
                let notes = named(
                    marks::MSG_SCALE_NOTES_TEXT,
                    &[("root", root.as_str().into()), ("kind", kind.replace('_', " ").as_str().into())],
                );
                named(
                    labels::MSG_SCALE_HEADER,
                    &[(
                        "scale",
                        named(marks::MSG_SCALE_SHOWN, &[("name", scale.as_str().into()), ("notes", notes.as_str().into())])
                            .as_str()
                            .into(),
                    )],
                )
            }
            _ => labels::MSG_SEVERAL_SCALES.to_string(),
        }
    }

    fn header_lines(&self, app: &App, roll: &Roll, width: usize, window: (usize, usize), extra: Vec<String>) -> Vec<Text> {
        let (first, last) = window;
        let pattern = roll.pattern;
        let drum = if pattern.is_drum() { marks::MSG_DRUM_ON } else { marks::MSG_DRUM_OFF };
        let whose = |setting: &str| {
            if pattern.get_written(setting).is_some_and(|value| !value.is_null()) {
                ""
            } else {
                marks::MSG_FROM_SONG_SHOWN
            }
        };
        let step_size = named(
            marks::MSG_STEP_SIZE_SHOWN,
            &[
                ("size", fraction(roll.step_size).as_str().into()),
                ("whose", whose(PatternSetting::STEP_SIZE).into()),
            ],
        );
        let direction = pattern.get_direction().unwrap_or_else(|| "forward".to_string()).replace('_', " ");
        let first_cells = vec![
            named(marks::MSG_STEPS_HEADER, &[("steps", pattern.get_steps().to_string().as_str().into())]),
            step_size,
            named(marks::MSG_DRUM_HEADER, &[("drum", drum.into())]),
            named(marks::MSG_DIRECTION_HEADER, &[("direction", direction.as_str().into())]),
        ];
        let signature = pattern.get_time_signature().unwrap_or_else(|| app.document.song().get_time_signature());
        let mut second_cells = vec![named(
            marks::MSG_TIME_SIGNATURE_SHOWN,
            &[
                ("signature", signature.to_text().as_str().into()),
                ("whose", whose(PatternSetting::TIME_SIGNATURE).into()),
            ],
        )];
        second_cells.extend(extra);
        let lines = header_cells(&[first_cells, second_cells]);
        let shown = self.steps_shown_text(pattern.get_steps() as usize, first, last);
        let mut second = lines[1].clone();
        if !shown.is_empty() {
            second = format!("{} {shown}", fit(&second, width.saturating_sub(shown.chars().count() + 1)));
        }
        vec![Text::plain(&lines[0]), Text::plain(&second)]
    }

    /// The second header line's cells after Time on the roll: the scale and the entry size.
    fn roll_extra(&self, app: &App, roll: &Roll) -> Vec<String> {
        let pattern = roll.pattern;
        let entry = app
            .document
            .song()
            .get_written(llamatron_model::schema::generated::file_format::SongSetting::ENTRY_SIZE);
        let pattern_entry = pattern.get_written(PatternSetting::ENTRY_SIZE).filter(|value| !value.is_null());
        let entry_size = pattern_entry
            .or(entry)
            .and_then(|value| llamatron_model::schema::checking::written_length(value, Rational::whole(4)).ok())
            .unwrap_or(roll.step_size);
        let entry_whose = if pattern_entry.is_some() { "" } else { marks::MSG_FROM_SONG_SHOWN };
        vec![
            self.scale_said(app, roll),
            named(
                marks::MSG_ENTRY_SIZE_SHOWN,
                &[("size", fraction(entry_size).as_str().into()), ("whose", entry_whose.into())],
            ),
        ]
    }

    fn pitches_shown(&self, roll: &Roll, rows: &[i64], pitch: i64, height: usize) -> Vec<i64> {
        let room = height.saturating_sub(LINES_AROUND_ROWS).max(1);
        let cursor = rows.iter().position(|row| *row == pitch).unwrap_or(0);
        let lines_for = |pitches: &[i64]| {
            pitches.len()
                + pitches[..pitches.len().saturating_sub(1)]
                    .iter()
                    .filter(|each| roll.starts_an_octave(**each))
                    .count()
        };
        let top_pitch = self.top_pitch.get().unwrap_or_else(|| rows[cursor.saturating_sub(room / 2)]);
        let mut top = rows.iter().position(|row| *row <= top_pitch).unwrap_or(cursor).min(cursor);
        while lines_for(&rows[top..=cursor]) > room && top < cursor {
            top += 1;
        }
        self.top_pitch.set(Some(rows[top]));
        let mut shown: Vec<i64> = Vec::new();
        for row in &rows[top..] {
            let mut trial = shown.clone();
            trial.push(*row);
            if lines_for(&trial) > room && !shown.is_empty() {
                break;
            }
            shown.push(*row);
        }
        shown
    }

    fn rule(&self, kind: RuleKind, window: &Window, boxed: Option<usize>) -> Text {
        let rule = Rule {
            kind,
            first: window.first,
            last: window.last,
            beats: window.beats.clone(),
            boxed,
            joints: true,
        };
        grid::rule_line(&rule, window.label_width)
    }

    fn pitch_line(&self, roll: &Roll, pitch: i64, cursor_pitch: i64, window: &Window) -> Text {
        let (first, last, beats, label_width) = (window.first, window.last, &window.beats, window.label_width);
        let on_row = pitch == cursor_pitch;
        let in_range = roll.in_range(pitch);
        let step = self.step.get();
        let label_kind = if on_row {
            LabelKind::Bold
        } else if in_range && roll.is_degree(pitch) {
            LabelKind::Plain
        } else {
            LabelKind::Dim
        };
        let cursor_step = on_row.then_some(step);
        let mut steps = Vec::new();
        for each in first..last {
            let (edge, cell) = self.step_shown(roll, pitch, each, cursor_step, in_range);
            steps.push((each, edge, cell));
        }
        let last_edge = if on_row && (last == step || last == step + 1) {
            Edge::Cursor
        } else {
            Edge::Divider
        };
        grid::roll_row_line(
            &RollRow {
                label: roll.row_label(pitch),
                label_kind,
                steps,
                beats: beats.to_vec(),
                last_edge,
            },
            label_width,
        )
    }

    fn step_shown(&self, roll: &Roll, pitch: i64, step: usize, cursor_step: Option<usize>, in_range: bool) -> (Edge, RollCell) {
        let start = roll.covering.get(&step).copied();
        let pitch_of_start = start.and_then(|start| roll.pitch_of(start));
        let plain_edge = if cursor_step.is_some_and(|cursor| step == cursor || step == cursor + 1) {
            Edge::Cursor
        } else {
            Edge::Divider
        };
        let selected = cursor_step == Some(step);
        let note_here = start.is_some() && pitch_of_start == Some(pitch);
        if note_here {
            let start = start.expect("a note covers the step");
            let hollow = false;
            let edge = if start != step {
                if hollow {
                    Edge::Hollow
                } else {
                    Edge::Note
                }
            } else {
                plain_edge
            };
            let mark = if start != step {
                None
            } else if roll.grabs(start) {
                Some(marks::MSG_GRAB_NOTE_MARK.to_string())
            } else if roll.scale.is_none() {
                roll.accidental_symbol(start).map(str::to_string)
            } else {
                None
            };
            let columns = if step != start + note_span(roll.pattern, start, roll.step_size) - 1 {
                CELL_WIDTH
            } else {
                partial_cell(roll.pattern, start, roll.step_size).map_or(CELL_WIDTH, filled_columns)
            };
            return (
                edge,
                RollCell {
                    kind: CellKind::Note,
                    mark,
                    hollow,
                    columns,
                    selected,
                },
            );
        }
        let kind = if selected || in_range { CellKind::Empty } else { CellKind::OutOfRange };
        (plain_edge, RollCell::of(kind, selected))
    }

    fn describe(&self, app: &App, roll: &Roll) -> String {
        let step = self.step.get();
        let number = step + 1;
        if !patterns::has_sound(roll.pattern, step) {
            let tied = matches!(value(roll.pattern, Row::TIE, step), Some(Data::Bool(true)));
            return named(
                if tied { messages::MSG_DESCRIBE_TIED } else { messages::MSG_DESCRIBE_EMPTY },
                &[("step", number.into())],
            );
        }
        let song = app.document.song();
        let scale_name = roll.scale.clone().or_else(|| song.get_scale_name());
        let where_ = if roll.pattern.is_drum() {
            String::new()
        } else {
            named(
                messages::MSG_IN_SCALE,
                &[(
                    "scale",
                    scale_name.clone().unwrap_or_else(|| messages::MSG_NO_SCALE.to_string()).as_str().into(),
                )],
            )
        };
        let sound = if matches!(value(roll.pattern, Row::GRAB, step), Some(Data::Bool(true))) {
            messages::MSG_GRABBED_SOUND.to_string()
        } else {
            match self.note_name(app, roll, scale_name.as_deref(), step) {
                Some(played) => format!("{played}{where_}"),
                None => named(
                    messages::MSG_DEGREE_WITHOUT_SCALE,
                    &[(
                        "degree",
                        value(roll.pattern, Row::DEGREE, step)
                            .and_then(Data::as_whole)
                            .unwrap_or(0)
                            .to_string()
                            .as_str()
                            .into(),
                    )],
                ),
            }
        };
        let chord = value(roll.pattern, Row::CHORD, step)
            .map(data_text)
            .map_or(String::new(), |chord| named(messages::MSG_DESCRIBE_CHORD, &[("chord", chord.as_str().into())]));
        let gate_now = value(roll.pattern, Row::GATE, step)
            .and_then(|gate| llamatron_model::schema::checking::written_length(gate, Rational::whole(4)).ok())
            .unwrap_or(roll.step_size);
        let dot = value(roll.pattern, Row::DOT, step)
            .and_then(Data::as_str)
            .map_or(String::new(), |dot| named_in(labels::MSG_DOT_NAMES, dot));
        let dot = if labels::MSG_DOT_NAMES
            .iter()
            .any(|(found, _)| Some(*found) == value(roll.pattern, Row::DOT, step).and_then(Data::as_str))
        {
            dot
        } else {
            String::new()
        };
        let mut gate = format!("{}{dot}", fraction(gate_now));
        let tied_after = step + 1 < roll.pattern.get_steps() as usize && matches!(value(roll.pattern, Row::TIE, step + 1), Some(Data::Bool(true)));
        if value(roll.pattern, Row::GATE, step).is_some() && tied_after {
            gate.push_str(messages::MSG_DESCRIBE_GATE_OVERRIDDEN);
        }
        named(
            messages::MSG_DESCRIBE_NOTE,
            &[
                ("step", number.into()),
                ("sound", sound.as_str().into()),
                ("gate", gate.as_str().into()),
                ("chord", chord.as_str().into()),
            ],
        )
    }

    /// The name of the note a step plays, with its octave as the set labels octaves, or None for a degree with no scale.
    fn note_name(&self, app: &App, roll: &Roll, scale: Option<&str>, step: usize) -> Option<String> {
        let degree = value(roll.pattern, Row::DEGREE, step)?;
        let accidental = value(roll.pattern, Row::ACCIDENTAL, step).and_then(Data::as_str).unwrap_or("");
        let octave = value(roll.pattern, Row::OCTAVE, step).and_then(Data::as_whole).map(|whole| whole as i64);
        let setlist = app.document.get_setlist();
        let offset = if octave_labels(setlist) == "live" { 2 } else { 0 };
        if roll.pattern.is_drum() {
            let octave = octave.unwrap_or(setlist.get_default_drum_octave());
            return Some(format!("{}{accidental}{}", data_text(degree), octave - offset));
        }
        let scale = scale?;
        let octave = octave.unwrap_or(setlist.get_default_octave());
        let half_steps = scale_half_steps(setlist, scale);
        let degree = degree.as_whole()? as i64;
        let (octaves_up, place) = (
            (degree - MIN_DEGREE).div_euclid(half_steps.len() as i64),
            (degree - MIN_DEGREE).rem_euclid(half_steps.len() as i64),
        );
        let shift = match accidental {
            "#" => 1,
            "b" => -1,
            _ => 0,
        };
        let moved = half_steps[place as usize] + octaves_up * HALF_STEPS_PER_OCTAVE + shift;
        let note = Note::new(&scale_root(setlist, scale), REFERENCE_OCTAVE, None, None, false)
            .ok()?
            .half_step(moved)
            .ok()?;
        Some(format!("{}{}", note.get_name(), note.get_octave_number() - REFERENCE_OCTAVE + octave - offset))
    }

    fn roll_body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        self.keep_step(app);
        let roll = Roll::of(app, &self.name);
        let rows = roll.rows();
        let pitch = self.place_cursor(&roll, &rows);
        let label_width = self.label_width(app, &roll);
        let count = roll.pattern.get_steps() as usize;
        let (first, last) = self.window_of_steps(count, self.steps_shown(width, label_width));
        let pitches = self.pitches_shown(&roll, &rows, pitch, height);
        let beats = self.beats(app, &roll);
        let boxed_beside = |pitches: &[i64]| pitches.contains(&pitch).then_some(self.step.get());
        let mut lines = self.header_lines(app, &roll, width, (first, last), self.roll_extra(app, &roll));
        let window = Window {
            first,
            last,
            beats: beats.clone(),
            label_width,
        };
        let mut grid_lines = vec![
            self.rule(RuleKind::Top, &window, None),
            grid::step_numbers_line(first, last, &beats, None, label_width),
            self.rule(RuleKind::Heading, &window, boxed_beside(&pitches[..1])),
        ];
        for (place, each) in pitches.iter().enumerate() {
            grid_lines.push(self.pitch_line(&roll, *each, pitch, &window));
            if roll.starts_an_octave(*each) && place + 1 < pitches.len() {
                grid_lines.push(self.rule(RuleKind::Inner, &window, boxed_beside(&pitches[place..place + 2])));
            }
        }
        grid_lines.push(self.rule(RuleKind::Bottom, &window, boxed_beside(&pitches[pitches.len() - 1..])));
        let keyswitched: Vec<usize> = (first..last)
            .filter(|step| {
                value(roll.pattern, Row::KEYSWITCH, *step).is_some_and(|slots| !matches!(slots, Data::List(items) if items.is_empty()))
                    && patterns::has_sound(roll.pattern, *step)
            })
            .map(|step| EDGE_WIDTH + label_width + (step - first) * (CELL_WIDTH + EDGE_WIDTH) + EDGE_WIDTH + MARK_COLUMN)
            .collect();
        if !keyswitched.is_empty() {
            grid_lines[TOP_PITCH_LINE] = grid::with_keyswitch_lights(&grid_lines[TOP_PITCH_LINE], &keyswitched);
        }
        lines.extend(grid_lines);
        self.with_description(app, &roll, lines, width, height)
    }

    /// The header and grid lines with the description after them, set apart by a blank line where there's room.
    fn with_description(&self, app: &App, roll: &Roll, mut lines: Vec<Text>, width: usize, height: usize) -> Vec<Text> {
        let description = Text::styled(&format!("{SPACE}{}", fit(&self.describe(app, roll), width.saturating_sub(1))), Style::BOLD);
        if lines.len() + LINES_AFTER_GRID <= height {
            lines.push(Text::default());
        }
        lines.push(description);
        lines
    }

    fn rows_body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        self.keep_step(app);
        let roll = Roll::of(app, &self.name);
        let mut rows = self.rows(app);
        let label_width = self.label_width(app, &roll);
        let count = roll.pattern.get_steps() as usize;
        let (first, last) = self.window_of_steps(count, self.steps_shown(width, label_width));
        let screen_height = app.screen_height.get();
        rows.fit_gauge(screen_height, crate::page::header_lines(self, screen_height), LEGEND_LINES);
        self.gauge_rows.set(rows.gauge_rows);
        let (place, cursor) = self.row_cursor(&rows);
        let shown = rows.scrolled_shown(height, place, &self.first_row);
        let section = rows.section_of(&cursor);
        let hint = section
            .and_then(|section| labels::MSG_SECTION_HINTS.iter().find(|(found, _)| *found == section))
            .map(|(_, hint)| hint.to_string());
        let extra = vec![hint.unwrap_or_else(|| self.scale_said(app, &roll))];
        let mut lines = self.header_lines(app, &roll, width, (first, last), extra);
        let beats = self.beats(app, &roll);
        let label_width = self.label_width(app, &roll).max(rows.widest_label());
        lines.extend(rows.grid_lines(&shown, &cursor, self.step.get(), (first, last, &beats), label_width));
        self.with_description(app, &roll, lines, width, height)
    }

    fn move_rows(&self, app: &App, key: &str) {
        let step: i64 = if key == "up" || key == "left" { -1 } else { 1 };
        if key == "left" || key == "right" {
            self.step
                .set((self.step.get() as i64 + step).clamp(0, self.step_count(app).max(1) as i64 - 1) as usize);
            return;
        }
        let count = self.rows(app).reachable().len() as i64;
        self.row.set((self.row.get() as i64 + step).clamp(0, count - 1) as usize);
    }

    /// Move the cursor to the next section's heading, or the one before, stopping at the first and the last.
    fn jump_section(&self, app: &App, direction: i64) {
        let rows = self.rows(app);
        let headings: Vec<usize> = rows
            .reachable()
            .iter()
            .enumerate()
            .filter(|(_, row)| matches!(row, RowName::Section(_)))
            .map(|(place, _)| place)
            .collect();
        let Some((&first, &last)) = headings.first().zip(headings.last()) else {
            return;
        };
        let row = self.row.get();
        let found = if direction < 0 {
            headings
                .iter()
                .rev()
                .find(|place| **place < row)
                .copied()
                .unwrap_or(if row < first { row } else { first })
        } else {
            headings
                .iter()
                .find(|place| **place > row)
                .copied()
                .unwrap_or(if row > last { row } else { last })
        };
        self.row.set(found);
    }

    fn move_roll(&self, app: &App, key: &str) {
        let roll = Roll::of(app, &self.name);
        let rows = roll.rows();
        let pitch = self.place_cursor(&roll, &rows);
        match key {
            "up" | "down" => {
                let place = rows.iter().position(|row| *row == pitch).unwrap_or(0) as i64;
                let step: i64 = if key == "up" { -1 } else { 1 };
                self.pitch.set(Some(rows[(place + step).clamp(0, rows.len() as i64 - 1) as usize]));
            }
            _ => {
                let step: i64 = if key == "left" { -1 } else { 1 };
                self.step
                    .set((self.step.get() as i64 + step).clamp(0, self.step_count(app) as i64 - 1) as usize);
            }
        }
    }
}

/// How many of a cell's columns a part of a step fills, rounded to the nearest, never none or all.
fn filled_columns(part: Rational) -> usize {
    let columns = (part.numerator() * CELL_WIDTH as i128 * 2 + part.denominator()).div_euclid(part.denominator() * 2);
    (columns as usize).clamp(1, CELL_WIDTH - 1)
}

/// An exact length as a file writes it: a whole number, or a fraction like 3/16.
fn fraction(length: Rational) -> String {
    if length.denominator() == 1 {
        length.numerator().to_string()
    } else {
        format!("{}/{}", length.numerator(), length.denominator())
    }
}

fn data_text(value: &Data) -> String {
    match value {
        Data::Text(text) => text.clone(),
        Data::Whole(whole) => whole.to_string(),
        other => format!("{other:?}"),
    }
}

fn title_case(text: &str) -> String {
    text.split(' ')
        .map(|word| {
            let mut characters = word.chars();
            characters.next().map_or(String::new(), |first| {
                first.to_uppercase().collect::<String>() + &characters.as_str().to_lowercase()
            })
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// The header lines laid out as columns of cells, each column as wide as its widest cell, a line's last cell as it is.
fn header_cells(lines: &[Vec<String>]) -> Vec<String> {
    let mut widths: BTreeMap<usize, usize> = BTreeMap::new();
    for cells in lines {
        for (column, cell) in cells[..cells.len() - 1].iter().enumerate() {
            let width = widths.entry(column).or_insert(0);
            *width = (*width).max(cell.chars().count());
        }
    }
    lines
        .iter()
        .map(|cells| {
            let mut padded: Vec<String> = cells[..cells.len() - 1]
                .iter()
                .enumerate()
                .map(|(column, cell)| format!("{cell:<width$}", width = widths[&column]))
                .collect();
            padded.push(cells[cells.len() - 1].clone());
            format!("{}{}", marks::MSG_HEADER_INDENT, padded.join(marks::MSG_HEADER_CELL_GAP))
        })
        .collect()
}

impl PatternEditor {
    /// The rows view's keys: ESC, the arrows, the ends and the jump between sections, Tab to the roll, the keys that insert and
    /// remove a step, the editor's own, then the keys of the row the cursor is on.
    fn rows_keys(&self, app: &App) -> Vec<KeyItem> {
        let editor = |binding| KeyItem::of(&Keys::CLASS, binding);
        let view = |binding| KeyItem::of(&RowsKeys::CLASS, binding);
        let rows = self.rows(app);
        let (_, cursor) = self.row_cursor(&rows);
        let mut keys = vec![
            editor(&Keys::BACK),
            view(&RowsKeys::MOVE).wanting_key(),
            view(&RowsKeys::ENDS),
            view(&RowsKeys::SECTION),
        ];
        if !rows.pattern.is_drum() {
            keys.push(editor(&Keys::TO_ROLL));
        }
        let takes_letters = rows.pattern.is_drum() && cursor == RowName::Row(Row::DEGREE);
        keys.push(view(&RowsKeys::INSERT_STEP));
        if self.step_count(app) > 1 && !takes_letters {
            keys.push(view(&RowsKeys::REMOVE_STEP));
        }
        keys.extend([editor(&Keys::RESIZE), editor(&Keys::MUNGE), editor(&Keys::RECONFIGURE), editor(&Keys::RENAME)]);
        if app.fluidsynth_installed {
            keys.push(editor(&Keys::LISTEN));
        }
        keys.extend(rows.keys(&cursor, self.keep_step(app)));
        keys
    }
}

impl Page for PatternEditor {
    /// A whole-pattern dialog's answer puts the cursor on a step, or the rows view at its top.
    fn go_to_row(&mut self, _app: &App, row: &str) {
        if row == super::whole_pattern::TOP {
            self.row.set(0);
            self.first_row.set(0);
        } else if let Ok(step) = row.parse() {
            self.step.set(step);
        }
    }

    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        let section = llamatron_model::schema::generated::file_format::Section::PATTERNS;
        crate::page::follow_name(&mut self.name, section, renames);
    }

    fn still_exists(&self, app: &App) -> bool {
        crate::page::named_exists(app, llamatron_model::schema::generated::file_format::Section::PATTERNS, &self.name)
    }

    fn name(&self) -> &'static str {
        "PatternEditor"
    }

    fn stack_name(&self) -> &str {
        "PatternEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    /// Say the chord under the cursor, in the scale the pattern is known to play under, while the cursor rests on a step
    /// that holds one; nothing for a drum pattern, a single note, or a step that grabs its note.
    fn resting_status(&self, app: &App) -> String {
        let step = self.keep_step(app);
        let setlist = app.document.get_setlist();
        let Some(pattern) = setlist.get_pattern(&self.name) else {
            return String::new();
        };
        let Some(Data::Whole(degree)) = value(pattern, Row::DEGREE, step) else {
            return String::new();
        };
        let text = |row: &str| match value(pattern, row, step) {
            Some(Data::Text(text)) => Some(text.clone()),
            Some(Data::Whole(whole)) => Some(whole.to_string()),
            _ => None,
        };
        let Some(symbol) = text(Row::CHORD) else { return String::new() };
        if pattern.is_drum() {
            return String::new();
        }
        let song = app.document.song();
        let scale = scales_of_pattern(setlist, song, &self.name).first().and_then(|name| {
            let Some(llamatron_model::objects::setlist::Item::Scale(held)) = setlist.get_item(Section::SCALES, name) else {
                return None;
            };
            crate::chord_text::ChordScale::new(&scale_root(setlist, name), held.get_kind().as_str()?)
        });
        let tensions = value(pattern, Row::TENSION, step)
            .and_then(Data::as_list)
            .map(|tensions| tensions.iter().filter_map(|tension| tension.as_str().map(str::to_string)).collect())
            .unwrap_or_default();
        let chord = crate::chord_text::ChordInWords {
            scale,
            degree: *degree as i64,
            accidental: text(Row::ACCIDENTAL),
            kind: text(Row::CHORD_SCALE),
            symbol: Some(symbol),
            tensions,
            own_degree: None,
        };
        chord.resting(&named(messages::MSG_RESTING_STEP, &[("step", (step + 1).into())]))
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        self.on_roll_now.set(self.on_roll(app));
        let editor = |binding| KeyItem::of(&Keys::CLASS, binding);
        let roll = |binding| KeyItem::of(&RollKeys::CLASS, binding);
        if !self.on_roll(app) {
            return self.rows_keys(app);
        }
        let mut keys = vec![editor(&Keys::BACK), roll(&RollKeys::MOVE).wanting_key(), roll(&RollKeys::ENDS)];
        keys.push(editor(if self.on_roll(app) { &Keys::TO_EDITOR } else { &Keys::TO_ROLL }));
        keys.extend([editor(&Keys::RESIZE), editor(&Keys::MUNGE), editor(&Keys::RECONFIGURE), editor(&Keys::RENAME)]);
        if app.fluidsynth_installed {
            keys.push(editor(&Keys::LISTEN));
        }
        for binding in [
            &RollKeys::PLACE,
            &RollKeys::CHORD,
            &RollKeys::KEYSWITCH,
            &RollKeys::SHORTER,
            &RollKeys::LONGER,
            &RollKeys::KNIFE,
            &RollKeys::ACCIDENTAL,
            &RollKeys::ERASE,
            &RollKeys::GRAB,
            &RollKeys::ENTRY_SIZE,
        ] {
            keys.push(roll(binding));
        }
        keys
    }

    fn page_key_table(&self, app: &App) -> Vec<KeyItem> {
        self.on_roll_now.set(self.on_roll(app));
        in_order(&Keys::CLASS, self.keys(app))
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::RESIZE) || item.is(&Keys::RENAME) || item.is(&Keys::RECONFIGURE) || item.is(&Keys::MUNGE) {
            let place = self.whole_pattern_place(app);
            if item.is(&Keys::RESIZE) {
                super::whole_pattern::ask_steps(app, &place);
            } else if item.is(&Keys::RENAME) {
                super::whole_pattern::rename(app, &self.name);
            } else if item.is(&Keys::RECONFIGURE) {
                super::whole_pattern::reconfigure(app, &place);
            } else {
                super::whole_pattern::munge(app, &place);
            }
            return;
        }
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&RollKeys::MOVE) {
            self.move_roll(app, key);
        } else if item.is(&RollKeys::ENDS) {
            let last = self.step_count(app) - 1;
            self.step.set(if item.step_of(key) == Some(crate::keys::STEP_BACK) { 0 } else { last });
        } else if item.is(&Keys::TO_EDITOR) || item.is(&Keys::TO_ROLL) {
            app.session.on_roll = !app.session.on_roll;
        } else if item.is(&RowsKeys::MOVE) {
            self.typed.borrow_mut().clear();
            self.move_rows(app, key);
        } else if item.is(&RowsKeys::INSERT_STEP) {
            let step = self.keep_step(app);
            self.change_pattern(app, |pattern| pattern.insert_step(step).map_err(|problem| problem.message));
        } else if item.is(&RowsKeys::REMOVE_STEP) {
            let step = self.keep_step(app);
            self.change_pattern(app, |pattern| pattern.remove_step(step).map_err(|problem| problem.message));
            self.keep_step(app);
        } else if item.is(&RowsKeys::ENDS) {
            let last = self.step_count(app) - 1;
            self.step.set(if item.step_of(key) == Some(crate::keys::STEP_BACK) { 0 } else { last });
        } else if item.is(&RowsKeys::SECTION) {
            self.jump_section(app, item.step_of(key).unwrap_or(1));
        } else if item.is(&crate::keybindings::SectionRow::OPEN) || item.is(&crate::keybindings::SectionRow::CLOSE) {
            let rows = self.rows(app);
            if let (_, RowName::Section(section)) = self.row_cursor(&rows) {
                if !app.session.open_sections.remove(section) {
                    app.session.open_sections.insert(section.to_string());
                }
            }
        }
        if self.on_roll(app) {
            self.press_roll(app, item);
        } else {
            self.press_row(app, item, key);
        }
        self.on_roll_now.set(self.on_roll(app));
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        self.on_roll_now.set(self.on_roll(app));
        if !self.on_roll(app) {
            return self.rows_body(app, width, height);
        }
        self.roll_body(app, width, height)
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        let Some(opener) = &self.opener_crumbs else {
            return vec![
                labels::Crumb::PATTERNS.to_string(),
                named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
            ];
        };
        let mut crumbs = opener.clone();
        crumbs.push(named(labels::MSG_PATTERN_CRUMB, &[("name", self.name.as_str().into())]));
        crumbs
    }

    fn caption(&self, _app: &App) -> String {
        let what = named_in(labels::MSG_CAPTION_WORDS, Section::PATTERNS).to_uppercase();
        named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.name.as_str().into())],
        )
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::PATTERNS)
    }

    fn duration(&self, app: &App) -> Duration {
        let setlist = app.document.get_setlist();
        let song = app.document.song();
        let Some(pattern) = setlist.get_pattern(&self.name) else {
            return Duration::Nothing;
        };
        let tempo = llamatron_model::schema::checking::number(&song.get_tempo()).unwrap_or(Rational::whole(120));
        let seconds = setlist.get_pattern_length(pattern) * Rational::whole(240) / tempo;
        Duration::Clock(clock_exact(seconds))
    }
}

impl PatternEditor {
    /// Change the editor's pattern through one of its methods, as one change, saying why where it refused.
    fn change_pattern(&self, app: &mut App, change: impl FnOnce(&mut Pattern) -> Result<(), String>) {
        let name = self.name.clone();
        let mut refusal = None;
        app.document.change_set(|setlist| {
            if let Some(llamatron_model::objects::setlist::Item::Pattern(pattern)) = setlist.get_item_mut(Section::PATTERNS, &name) {
                if let Err(problem) = change(pattern) {
                    refusal = Some(problem);
                }
            }
        });
        if let Some(refusal) = refusal {
            app.refuse(&refusal);
        }
    }

    /// Do what a key of the row under the cursor does to the cursor's step, where it is one of the row's own keys.
    fn press_row(&self, app: &mut App, item: &KeyItem, key: &str) {
        let step = self.keep_step(app);
        let edit = {
            let rows = self.rows(app);
            let (_, row) = self.row_cursor(&rows);
            let crate::screens::pattern::rows_view::RowName::Row(name) = row else {
                return;
            };
            if !rows
                .keys(&crate::screens::pattern::rows_view::RowName::Row(name), step)
                .iter()
                .any(|own| own.binding == item.binding)
            {
                return;
            }
            let typed = self.typed.borrow().clone();
            rows.edit(name, step, item, key, &typed)
        };
        self.apply_row_edit(app, step, edit);
    }

    /// Make a row's edit of a step as one change, or ask in its dialog.
    fn apply_row_edit(&self, app: &mut App, step: usize, edit: crate::screens::pattern::rows_view::RowEdit) {
        if let Some(typed) = edit.typed.clone() {
            *self.typed.borrow_mut() = typed;
        }
        if let Some(asking) = edit.asking {
            self.ask_row(app, step, asking);
            return;
        }
        if edit.continues {
            app.document.continue_edit();
        }
        if !edit.writes.is_empty() || edit.clear_sound || edit.statement.is_some() {
            let (writes, clear, statement) = (edit.writes, edit.clear_sound, edit.statement);
            self.change_pattern(app, |pattern| {
                if clear {
                    pattern.clear_sound(step).map_err(|problem| problem.message)?;
                }
                for (row, value) in writes {
                    pattern.set_value(&row, step, value).map_err(|problem| problem.message)?;
                }
                if let Some((kind, statement)) = statement {
                    pattern.set_statement(kind, step, statement.as_ref()).map_err(|problem| problem.message)?;
                }
                Ok(())
            });
        }
        if let Some(refusal) = edit.refusal {
            app.refuse(&refusal);
        }
    }

    /// Ask for a row's number or length in a prompt, and write what was typed where it is in range.
    fn ask_row(&self, app: &mut App, step: usize, asking: crate::screens::pattern::rows_view::RowAsking) {
        use crate::screens::pattern::rows_view::RowAsking;
        let name = self.name.clone();
        let (title, shown, then): (String, String, crate::screens::dialogs::Then) = match asking {
            RowAsking::Number {
                row,
                title,
                value,
                lowest,
                highest,
            } => {
                let label = crate::settings::named_in(labels::MSG_ROW_LABELS, &row);
                let then: crate::screens::dialogs::Then = Box::new(move |app: &mut App, answer: &crate::screens::dialogs::Answer| {
                    let crate::screens::dialogs::Answer::Typed(text) = answer else { return };
                    let Ok(number) = text.trim().parse::<i64>() else {
                        app.refuse(&named(llamatron_strings::errors::ERR_TYPED_NOT_AN_INTEGER, &[("text", text.as_str().into())]));
                        return;
                    };
                    if !(lowest..=highest).contains(&number) {
                        let words = [("row", label.as_str().into()), ("low", lowest.into()), ("high", highest.into())];
                        app.refuse(&named(llamatron_strings::errors::ERR_ROW_OUT_OF_RANGE, &words));
                        return;
                    }
                    write_value(app, &name, &row, step, Some(Data::Whole(number as i128)));
                });
                (title, value.to_string(), then)
            }
            RowAsking::Length { row, title, value, most } => {
                let then: crate::screens::dialogs::Then = Box::new(move |app: &mut App, answer: &crate::screens::dialogs::Answer| {
                    let crate::screens::dialogs::Answer::Typed(text) = answer else { return };
                    let text = text.trim();
                    let Ok(length) = llamatron_math::Rational::parse(text) else {
                        app.refuse(&named(llamatron_strings::errors::ERR_NOT_A_LENGTH, &[("text", text.into())]));
                        return;
                    };
                    if length <= llamatron_math::Rational::ZERO || length > most {
                        app.refuse(&named(
                            llamatron_strings::errors::ERR_LENGTH_OUT_OF_RANGE,
                            &[("most", most.to_string().as_str().into())],
                        ));
                        return;
                    }
                    write_value(app, &name, &row, step, Some(Data::text(&length.to_string())));
                });
                (title, value, then)
            }
        };
        let prompt = crate::screens::dialogs::PromptDialog::new(&title, &shown).then(then);
        app.show_page(Box::new(prompt));
    }
}

/// Write one value of a pattern's step, as one change, saying why where the pattern refused it.
fn write_value(app: &mut App, name: &str, row: &str, step: usize, value: Option<Data>) {
    let mut refusal = None;
    app.document.change_set(|setlist| {
        if let Some(llamatron_model::objects::setlist::Item::Pattern(pattern)) = setlist.get_item_mut(Section::PATTERNS, name) {
            if let Err(problem) = pattern.set_value(row, step, value) {
                refusal = Some(problem.message);
            }
        }
    });
    if let Some(refusal) = refusal {
        app.refuse(&refusal);
    }
}

impl PatternEditor {
    /// Where the editor is, for a whole-pattern dialog: the pattern, the cursor's step, and what its notes are measured
    /// against, the scale the pattern is known to play under, none for a drum pattern.
    fn whole_pattern_place(&self, app: &App) -> super::whole_pattern::Place {
        let step = self.keep_step(app);
        let setlist = app.document.get_setlist();
        let pattern = setlist.get_pattern(&self.name).expect("the editor's pattern is in the set");
        let drum = pattern.is_drum();
        let default_octave = if drum {
            setlist.get_default_drum_octave()
        } else {
            setlist.get_default_octave()
        };
        let scale_size = (!drum)
            .then(|| scales_of_pattern(setlist, app.document.song(), &self.name).first().cloned())
            .flatten()
            .map(|scale| scale_half_steps(setlist, &scale).len() as i64);
        super::whole_pattern::Place {
            name: self.name.clone(),
            step,
            steps: pattern.get_steps() as usize,
            drum,
            default_octave,
            scale_size,
            step_size: setlist.get_pattern_step_size(pattern),
        }
    }
}

/// What a key of the roll works on: the step, the note under the cursor at its pitch, the note covering the step at any
/// pitch, the note the cursor's row writes, the step's length and the length a drawn note lasts.
struct RollPlace {
    step: usize,
    here: Option<usize>,
    covering: Option<usize>,
    note: (Data, i64, Option<&'static str>),
    step_size: Rational,
    entry_size: Rational,
    grabs: bool,
}

impl PatternEditor {
    /// What a key of the roll works on, as the roll stands.
    fn roll_place(&self, app: &App) -> RollPlace {
        let step = self.keep_step(app);
        let roll = Roll::of(app, &self.name);
        let rows = roll.rows();
        let pitch = self.place_cursor(&roll, &rows);
        let covering = roll.covering.get(&step).copied();
        let here = covering.filter(|start| roll.pitch_of(*start) == Some(pitch));
        let (degree, octave, accidental) = roll.note_at(pitch);
        let written = |data: Option<&Data>| data.and_then(Data::as_str).and_then(|text| Rational::parse(text).ok());
        let entry_size = written(roll.pattern.get_written(PatternSetting::ENTRY_SIZE))
            .or_else(|| written(app.document.song().get_written("entry_size")))
            .unwrap_or(roll.step_size);
        let grabs = here.is_some_and(|start| patterns::value(roll.pattern, Row::GRAB, start).is_some_and(|grab| matches!(grab, Data::Bool(true))));
        RollPlace {
            step,
            here,
            covering,
            note: (Data::Whole(degree as i128), octave, accidental),
            step_size: roll.step_size,
            entry_size,
            grabs,
        }
    }

    /// Do what a key of the piano roll does to the note under the cursor, or at the cursor.
    fn press_roll(&self, app: &mut App, item: &KeyItem) {
        use llamatron_strings::errors;
        let place = self.roll_place(app);
        let on_note = |app: &mut App| -> Option<usize> {
            if place.here.is_none() {
                app.refuse(errors::ERR_NO_NOTE_HERE);
            }
            place.here
        };
        if item.is(&RollKeys::PLACE) {
            match place.here {
                Some(start) => self.change_pattern(app, |pattern| pattern.clear_sound(start).map_err(|problem| problem.message)),
                None => self.draw_here(app, &place),
            }
        } else if item.is(&RollKeys::ERASE) {
            if let Some(start) = on_note(app) {
                self.change_pattern(app, |pattern| pattern.clear_sound(start).map_err(|problem| problem.message));
            }
        } else if item.is(&RollKeys::LONGER) || item.is(&RollKeys::SHORTER) {
            let Some(start) = on_note(app) else { return };
            let longer = item.is(&RollKeys::LONGER);
            let refusal = if longer { errors::ERR_NO_ROOM_AFTER } else { errors::ERR_NOTE_IS_ONE_STEP };
            self.reshape(app, refusal, |pattern| {
                if longer {
                    patterns::lengthen_note(pattern, start, place.step_size)
                } else {
                    patterns::shorten_note(pattern, start, place.step_size)
                }
            });
        } else if item.is(&RollKeys::KNIFE) {
            match place.here {
                Some(start) if start != place.step => {
                    let step = place.step;
                    self.reshape(app, errors::ERR_NOTHING_TO_SPLIT, |pattern| patterns::split_note(pattern, step));
                }
                _ => app.refuse(errors::ERR_NOTHING_TO_SPLIT),
            }
        } else if item.is(&RollKeys::ACCIDENTAL) {
            if let Some(start) = on_note(app) {
                self.change_pattern(app, |pattern| patterns::cycle_accidental(pattern, start));
                // The cursor follows the note to its new row, which may be a row of its own between two degrees.
                let roll = Roll::of(app, &self.name);
                if let Some(pitch) = roll.pitch_of(start) {
                    self.pitch.set(Some(pitch));
                }
            }
        } else if item.is(&RollKeys::GRAB) {
            if let Some(start) = on_note(app) {
                let grabs = place.grabs;
                self.change_pattern(app, |pattern| {
                    pattern.set_value(Row::GRAB, start, Some(Data::Bool(!grabs))).map_err(|problem| problem.message)
                });
            }
        } else if item.is(&RollKeys::ENTRY_SIZE) {
            self.pick_entry_size(app);
        } else if item.is(&RollKeys::CHORD) {
            if place.covering.is_none() {
                self.draw_here(app, &place);
            }
            app.show_page(Box::new(crate::screens::not_ported::NotPorted {
                name: "ChordDialog".to_string(),
            }));
        } else if item.is(&RollKeys::KEYSWITCH) {
            if place.covering.is_none() {
                app.refuse(errors::ERR_NO_NOTE_ON_STEP);
                return;
            }
            app.show_page(Box::new(crate::screens::not_ported::NotPorted {
                name: "KeyswitchDialog".to_string(),
            }));
        }
    }

    /// Draw a note of the entry size at the cursor.
    fn draw_here(&self, app: &mut App, place: &RollPlace) {
        let (step, note, entry_size, step_size) = (place.step, place.note.clone(), place.entry_size, place.step_size);
        self.change_pattern(app, |pattern| patterns::draw_note(pattern, step, note, entry_size, step_size));
    }

    /// Change a note through an edit that says whether it could, noting a change only where it did and saying why not
    /// otherwise.
    fn reshape(&self, app: &mut App, refusal: &str, change: impl FnOnce(&mut Pattern) -> Result<bool, String>) {
        let mut pattern = match app.document.get_setlist().get_pattern(&self.name) {
            Some(pattern) => pattern.clone(),
            None => return,
        };
        match change(&mut pattern) {
            Ok(true) => self.change_pattern(app, |held| {
                *held = pattern;
                Ok(())
            }),
            Ok(false) => app.refuse(refusal),
            Err(problem) => app.refuse(&problem),
        }
    }

    /// Ask for the pattern's entry size: the song's first, then the step sizes, opening on what the pattern has now.
    fn pick_entry_size(&self, app: &mut App) {
        use llamatron_model::schema::generated::file_format::STEP_SIZE_CHOICES;
        let written = app
            .document
            .get_setlist()
            .get_pattern(&self.name)
            .and_then(|pattern| pattern.get_written(PatternSetting::ENTRY_SIZE))
            .and_then(Data::as_str)
            .map(str::to_string);
        let mut options = vec![labels::MSG_SONG_ENTRY_SIZE_CHOICE.to_string()];
        options.extend(STEP_SIZE_CHOICES.iter().map(|choice| choice.to_string()));
        let current = written
            .as_ref()
            .and_then(|written| STEP_SIZE_CHOICES.iter().position(|choice| choice == written))
            .map_or(0, |place| place + 1);
        let name = self.name.clone();
        let mut dialog = crate::screens::dialogs::ChoiceDialog::new(labels::MSG_ENTRY_SIZE_LABEL, options, current);
        dialog.then = Some(Box::new(move |app: &mut App, answer: &crate::screens::dialogs::Answer| {
            let crate::screens::dialogs::Answer::Chosen(place) = answer else { return };
            let chosen = place.checked_sub(1).map(|place| Data::text(STEP_SIZE_CHOICES[place]));
            let name = name.clone();
            app.document.change_set(|setlist| {
                if let Some(llamatron_model::objects::setlist::Item::Pattern(pattern)) = setlist.get_item_mut(Section::PATTERNS, &name) {
                    pattern.set_written(PatternSetting::ENTRY_SIZE, chosen);
                }
            });
        }));
        app.show_page(Box::new(dialog));
    }
}
