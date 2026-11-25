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
use crate::keybindings::{KeyClass, PatternEditor as Keys, PianoRoll as RollKeys};
use crate::keys::{in_order, KeyItem};
use crate::page::{clock_exact, Duration, Page};
use crate::patterns::{
    self, covering_notes, note_span, partial_cell, pattern_octave_range, pattern_scale, scale_half_steps, scale_root, scales_of_pattern, value,
};
use crate::screens::not_ported::NOT_PORTED;
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

/// The rows view's widest label, Ratchet Offset, with a space either side, until the rows view is ported and works it out.
const ROWS_LABEL_WIDTH: usize = 16;
/// The lines the roll's header, rules, numbers and description take around its rows, and the fewest rows it shows.
const LINES_AROUND_ROWS: usize = 7;
const LINES_AFTER_GRID: usize = 2;
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

    fn label_width(&self, roll: &Roll) -> usize {
        ROWS_LABEL_WIDTH.max(roll.widest_row_label() + 2)
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

    fn header_lines(&self, app: &App, roll: &Roll, width: usize, first: usize, last: usize) -> Vec<Text> {
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
        let second_cells = vec![
            named(
                marks::MSG_TIME_SIGNATURE_SHOWN,
                &[
                    ("signature", signature.to_text().as_str().into()),
                    ("whose", whose(PatternSetting::TIME_SIGNATURE).into()),
                ],
            ),
            self.scale_said(app, roll),
            named(
                marks::MSG_ENTRY_SIZE_SHOWN,
                &[("size", fraction(entry_size).as_str().into()), ("whose", entry_whose.into())],
            ),
        ];
        let lines = header_cells(&[first_cells, second_cells]);
        let shown = self.steps_shown_text(pattern.get_steps() as usize, first, last);
        let mut second = lines[1].clone();
        if !shown.is_empty() {
            second = format!("{} {shown}", fit(&second, width.saturating_sub(shown.chars().count() + 1)));
        }
        vec![Text::plain(&lines[0]), Text::plain(&second)]
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
        let label_width = self.label_width(&roll);
        let count = roll.pattern.get_steps() as usize;
        let (first, last) = self.window_of_steps(count, self.steps_shown(width, label_width));
        let pitches = self.pitches_shown(&roll, &rows, pitch, height);
        let beats = self.beats(app, &roll);
        let boxed_beside = |pitches: &[i64]| pitches.contains(&pitch).then_some(self.step.get());
        let mut lines = self.header_lines(app, &roll, width, first, last);
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
        let description = Text::styled(&format!("{SPACE}{}", fit(&self.describe(app, &roll), width.saturating_sub(1))), Style::BOLD);
        if lines.len() + LINES_AFTER_GRID <= height {
            lines.push(Text::default());
        }
        lines.push(description);
        lines
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

impl Page for PatternEditor {
    fn name(&self) -> &'static str {
        if self.on_roll_now.get() {
            "PatternEditor"
        } else {
            NOT_PORTED
        }
    }

    fn stack_name(&self) -> &str {
        "PatternEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        self.on_roll_now.set(self.on_roll(app));
        let editor = |binding| KeyItem::of(&Keys::CLASS, binding);
        let roll = |binding| KeyItem::of(&RollKeys::CLASS, binding);
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
        in_order(&Keys::CLASS, self.keys(app))
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&RollKeys::MOVE) {
            self.move_roll(app, key);
        } else if item.is(&RollKeys::ENDS) {
            let last = self.step_count(app) - 1;
            self.step.set(if item.step_of(key) == Some(crate::keys::STEP_BACK) { 0 } else { last });
        } else if item.is(&Keys::TO_EDITOR) || item.is(&Keys::TO_ROLL) {
            app.session.on_roll = !app.session.on_roll;
        }
        self.on_roll_now.set(self.on_roll(app));
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        self.on_roll_now.set(self.on_roll(app));
        if !self.on_roll(app) {
            return vec![Text::plain("the rows view is not ported yet")];
        }
        self.roll_body(app, width, height)
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::PATTERNS.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
        ]
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
