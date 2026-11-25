// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The pattern editor's rows view (the Python components/pattern_rows.py, pattern_row.py and the rows beside it, and
//! screens/pattern/pattern_drawing.py): the pinned Degree gauge and Octave rows, then the rows in sections that open and
//! close, each row's cells per step, and the keys of the row the cursor is on.

use crate::drawing::BoxCharacters as Box;
use crate::forms::pattern_grid::{self as grid, LabelKind, RowLines, Rule, RuleKind};
use crate::keybindings::{self as bindings};
use crate::keys::KeyItem;
use crate::patterns::{self, value};
use crate::settings::{named_in, shown_octave};
use crate::text::Text;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::Song;
use llamatron_model::schema::checking::plain_data;
use llamatron_model::schema::generated::file_format::{
    Row, Section, TrackSetting, CC_ROWS, CHORD_SYMBOLS, DIVIDING_OPERATORS, DRAW_NAMES, DRAW_NOTE_ROWS, DRAW_RESET_ROWS, DRAW_VELOCITY_ROWS,
    GATE_LENGTH_CHOICES, OPERATORS, RESULT_COMPARISONS, STATEMENT_ROWS, VALUE_NAMES,
};
use llamatron_model::schema::generated::limits::{MAX_STATEMENT_NUMBER, MIN_DEGREE};
use llamatron_model::schema::generated::rows::{RowDescription, ROW_DESCRIPTIONS};
use llamatron_model::schema::generated::settings::Plain;
use llamatron_strings::{labels, legends, marks, named};

pub const BASICS: &str = "basics";
pub const CHORD: &str = "chord_section";
pub const TIMING: &str = "timing";
pub const KEYSWITCH: &str = "keyswitch_section";
pub const ADVANCED: &str = "advanced";
pub const CC: &str = "cc";
pub const DRAW_APPLY: &str = "draw_apply";
pub const STOP_WHEN: &str = "stop_when";
pub const RESTART_WHEN: &str = "restart_when";
pub const MUTE_WHEN: &str = "mute_when";
/// The sections open when the tracker starts.
pub const OPEN_AT_START: [&str; 2] = [BASICS, TIMING];
const SECTIONS: [&str; 10] = [BASICS, CHORD, TIMING, KEYSWITCH, ADVANCED, CC, DRAW_APPLY, STOP_WHEN, RESTART_WHEN, MUTE_WHEN];
const GAUGE_ROWS_WITHOUT_SCALE: usize = 7;
const GAUGE_MIN_ROWS: usize = 3;
const LINES_AROUND_GRID: usize = 6;

/// A row of the rows view: a pattern row by its name, or a section's heading.
#[derive(Clone, Debug, PartialEq)]
pub enum RowName {
    Row(&'static str),
    Section(&'static str),
}

/// What the rows view reads of the pattern, gathered once a key or a drawing.
pub struct Rows<'a> {
    pub setlist: &'a Setlist,
    pub song: &'a Song,
    pub pattern: &'a Pattern,
    pub name: String,
    pub scale: Option<String>,
    pub open: &'a std::collections::HashSet<String>,
    pub gauge_rows: usize,
    pub default_octave: i64,
    /// The slots the Keyswitch section has a row for, each slot's name, and the hint over them.
    pub keyswitch_slots: Vec<usize>,
    pub slot_names: Vec<String>,
    pub keyswitch_hint: String,
}

fn described(row: &str) -> &'static RowDescription {
    // A keyswitch slot's row reads and writes the one Keyswitch row, and is described by it.
    let row = if crate::keyswitches::slot_of_row(row).is_some() {
        Row::KEYSWITCH
    } else {
        row
    };
    ROW_DESCRIPTIONS.iter().find(|found| found.name == row).expect("every row is described")
}

fn plain_text(value: &Plain) -> String {
    match value {
        Plain::Text(text) => text.to_string(),
        Plain::Whole(whole) => whole.to_string(),
        Plain::Flag(flag) => if *flag { "True" } else { "False" }.to_string(),
        _ => String::new(),
    }
}

fn data_text(value: &Data) -> String {
    match value {
        Data::Text(text) => text.clone(),
        Data::Whole(whole) => whole.to_string(),
        Data::Bool(flag) => if *flag { "True" } else { "False" }.to_string(),
        Data::List(items) => format!("[{}]", items.iter().map(data_text).collect::<Vec<_>>().join(", ")),
        _ => String::new(),
    }
}

fn section_rows_of(section: &str) -> Vec<&'static str> {
    let draw_rows = || {
        DRAW_NOTE_ROWS
            .iter()
            .chain(DRAW_VELOCITY_ROWS)
            .chain(DRAW_RESET_ROWS)
            .map(|(_, row)| *row)
            .collect()
    };
    let statements = |kind: &str| {
        STATEMENT_ROWS
            .iter()
            .find(|(found, _)| *found == kind)
            .map_or(Vec::new(), |(_, rows)| rows.to_vec())
    };
    match section {
        BASICS => vec![Row::ACCIDENTAL, Row::VELOCITY, Row::ACCENT],
        CHORD => vec![
            Row::CHORD,
            Row::TENSION,
            Row::CHORD_SCALE,
            Row::INVERSION,
            Row::DOUBLE,
            Row::OMIT,
            Row::BASS,
            Row::BASS_OCTAVE,
        ],
        TIMING => vec![Row::TIE, Row::GATE, Row::DOT, Row::GLIDE],
        KEYSWITCH => vec![Row::KEYSWITCH],
        ADVANCED => vec![Row::PROBABILITY, Row::RATCHET, Row::RATCHET_OFFSET, Row::GRAB],
        CC => {
            let mut rows = CC_ROWS.to_vec();
            rows.push(Row::SLIDE);
            rows
        }
        DRAW_APPLY => draw_rows(),
        STOP_WHEN => statements("stop"),
        RESTART_WHEN => statements("restart"),
        _ => statements("mute"),
    }
}

impl<'a> Rows<'a> {
    fn is_drum(&self) -> bool {
        self.pattern.is_drum()
    }

    fn scale_size(&self) -> Option<usize> {
        self.scale.as_ref().map(|scale| patterns::scale_half_steps(self.setlist, scale).len())
    }

    /// A section's rows, leaving out those a drum pattern has no use for.
    pub fn section_rows(&self, section: &str) -> Vec<&'static str> {
        if section == KEYSWITCH {
            if self.is_drum() && !described(Row::KEYSWITCH).in_drum_patterns {
                return Vec::new();
            }
            return self.keyswitch_slots.iter().map(|slot| crate::keyswitches::SLOT_ROWS[*slot]).collect();
        }
        let mut names = section_rows_of(section);
        if section == DRAW_APPLY {
            let filled: Vec<&str> = DRAW_NAMES
                .iter()
                .filter(|draw| {
                    self.song.draws().iter().any(|(name, held)| {
                        name == *draw
                            && held
                                .get_written("slots")
                                .and_then(Data::as_list)
                                .is_some_and(|slots| slots.iter().any(|slot| !slot.is_null()))
                    })
                })
                .copied()
                .collect();
            names = [DRAW_NOTE_ROWS, DRAW_VELOCITY_ROWS, DRAW_RESET_ROWS]
                .iter()
                .flat_map(|by_draw| {
                    filled
                        .iter()
                        .filter_map(|draw| by_draw.iter().find(|(name, _)| name == draw).map(|(_, row)| *row))
                })
                .collect();
        }
        if self.is_drum() {
            names.retain(|row| described(row).in_drum_patterns);
        }
        names
    }

    pub fn shown_sections(&self) -> Vec<&'static str> {
        SECTIONS.iter().filter(|section| !self.section_rows(section).is_empty()).copied().collect()
    }

    fn is_open(&self, section: &str) -> bool {
        self.open.contains(section)
    }

    /// The rows the cursor can reach: the pinned ones, then each section's heading with its rows when it's open.
    pub fn reachable(&self) -> Vec<RowName> {
        let mut names = vec![RowName::Row(Row::DEGREE), RowName::Row(Row::OCTAVE)];
        for section in self.shown_sections() {
            names.push(RowName::Section(section));
            if self.is_open(section) {
                names.extend(self.section_rows(section).into_iter().map(RowName::Row));
            }
        }
        names
    }

    /// Every row there could be, open or closed, which sizes the label column.
    pub fn every_row(&self) -> Vec<RowName> {
        let mut names = vec![RowName::Row(Row::DEGREE), RowName::Row(Row::OCTAVE)];
        for section in self.shown_sections() {
            names.push(RowName::Section(section));
            names.extend(self.section_rows(section).into_iter().map(RowName::Row));
        }
        names
    }

    pub fn section_of(&self, row: &RowName) -> Option<&'static str> {
        match row {
            RowName::Section(section) => Some(section),
            RowName::Row(name) => SECTIONS.iter().find(|section| section_rows_of(section).contains(name)).copied(),
        }
    }

    // The Degree gauge.

    fn has_gauge(&self) -> bool {
        !self.is_drum()
    }

    pub fn full_rows(&self) -> usize {
        self.scale_size().unwrap_or(GAUGE_ROWS_WITHOUT_SCALE)
    }

    fn rows_shown(&self) -> usize {
        self.full_rows().min(self.gauge_rows.max(GAUGE_MIN_ROWS))
    }

    fn shown_degree(&self, step: usize) -> Option<i64> {
        let degree = value(self.pattern, Row::DEGREE, step)?.as_whole()? as i64;
        match self.scale_size() {
            Some(size) if self.has_gauge() => Some((degree - MIN_DEGREE).rem_euclid(size as i64) + MIN_DEGREE),
            _ => Some(degree),
        }
    }

    fn octave_shift(&self, step: usize) -> i64 {
        let Some(degree) = value(self.pattern, Row::DEGREE, step).and_then(Data::as_whole) else {
            return 0;
        };
        match self.scale_size() {
            Some(size) if self.has_gauge() => (degree as i64 - MIN_DEGREE).div_euclid(size as i64),
            _ => 0,
        }
    }

    fn degree_limit(&self) -> usize {
        self.scale_size().unwrap_or_else(|| patterns::degree_limit(self.setlist, self.song, &self.name))
    }

    // A row's lines.

    pub fn labels(&self, row: &RowName) -> Vec<String> {
        match row {
            RowName::Section(section) => {
                let mark = if self.is_open(section) {
                    marks::MSG_SECTION_OPEN_MARK
                } else {
                    marks::MSG_SECTION_CLOSED_MARK
                };
                vec![named(
                    labels::MSG_SECTION_LABEL,
                    &[("mark", mark.into()), ("name", named_in(labels::MSG_SECTION_NAMES, section).as_str().into())],
                )]
            }
            RowName::Row(name) if *name == Row::DEGREE => {
                let label = if self.is_drum() {
                    marks::MSG_DRUM_LETTER_ROW.to_string()
                } else {
                    named_in(labels::MSG_ROW_LABELS, name)
                };
                if !self.has_gauge() {
                    return vec![label];
                }
                let names: Vec<String> = match &self.scale {
                    None => (MIN_DEGREE..=self.full_rows() as i64).map(|degree| degree.to_string()).collect(),
                    Some(scale) => {
                        let root = patterns::scale_root(self.setlist, scale);
                        crate::screens::set::scale_page::scale_notes(&root, &scale_kind(self.setlist, scale))
                            .split(' ')
                            .map(str::to_string)
                            .collect()
                    }
                };
                let mut lines: Vec<String> = names.into_iter().take(self.rows_shown()).collect::<Vec<_>>().into_iter().rev().collect();
                lines.push(label);
                lines
            }
            RowName::Row(name) if crate::keyswitches::slot_of_row(name).is_some() => {
                let slot = crate::keyswitches::slot_of_row(name).unwrap_or(0);
                vec![self.slot_names.get(slot).cloned().unwrap_or_default()]
            }
            RowName::Row(name) if CC_ROWS.contains(name) => vec![self.cc_label(name)],
            RowName::Row(name) => vec![named_in(labels::MSG_ROW_LABELS, name)],
        }
    }

    fn cc_label(&self, name: &str) -> String {
        let label = named_in(labels::MSG_ROW_LABELS, name);
        let lane = CC_ROWS.iter().position(|row| *row == name).unwrap_or(0);
        let mut plays: Vec<(String, String)> = Vec::new();
        for (song, _, _, track) in crate::uses::clip_slots_naming(self.setlist, Section::PATTERNS, &self.name) {
            if !plays.contains(&(song.clone(), track.clone())) {
                plays.push((song, track));
            }
        }
        let mut numbers: Vec<Option<i64>> = Vec::new();
        for (song, track) in plays {
            let number = self
                .setlist
                .get_song(&song)
                .and_then(|song| song.get_track(&track))
                .and_then(|track| {
                    track
                        .get_written(TrackSetting::CC)
                        .and_then(Data::as_list)
                        .and_then(|lanes| lanes.get(lane))
                        .and_then(Data::as_whole)
                })
                .map(|whole| whole as i64);
            if !numbers.contains(&number) {
                numbers.push(number);
            }
        }
        if numbers.is_empty() {
            return label;
        }
        let number = match numbers.as_slice() {
            [None] => marks::MSG_CC_LANE_OFF.to_string(),
            [Some(number)] => number.to_string(),
            _ => marks::MSG_CC_LANE_VARIES.to_string(),
        };
        named(
            labels::MSG_CC_ROW_LABEL,
            &[("label", label.as_str().into()), ("number", number.as_str().into())],
        )
    }

    pub fn height(&self, row: &RowName) -> usize {
        self.labels(row).len()
    }

    pub fn rule_before(&self, row: &RowName) -> bool {
        matches!(row, RowName::Section(_))
    }

    pub fn rule_after(&self, row: &RowName) -> bool {
        match row {
            RowName::Section(_) => true,
            RowName::Row(name) => *name == Row::OCTAVE || (*name == Row::DEGREE && self.has_gauge()),
        }
    }

    pub fn marks_label(&self, row: &RowName) -> bool {
        matches!(row, RowName::Section(_))
    }

    /// Whether a step plays its note with a keyswitch slot's keyswitch.
    fn slot_is_on(&self, slot: usize, step: usize) -> bool {
        value(self.pattern, Row::KEYSWITCH, step)
            .and_then(Data::as_list)
            .is_some_and(|slots| slots.iter().any(|each| each.as_whole() == Some(slot as i128)))
    }

    /// Turn a keyswitch slot on a step on or off, the step's slots kept in order and none left out of the file.
    fn set_slot(&self, slot: usize, step: usize, on: bool) -> RowEdit {
        let mut slots: Vec<i128> = value(self.pattern, Row::KEYSWITCH, step)
            .and_then(Data::as_list)
            .map_or(Vec::new(), |held| held.iter().filter_map(Data::as_whole).collect());
        slots.retain(|each| *each != slot as i128);
        if on {
            slots.push(slot as i128);
        }
        slots.sort_unstable();
        let written = (!slots.is_empty()).then(|| Data::List(slots.into_iter().map(Data::Whole).collect()));
        RowEdit::write(Row::KEYSWITCH, written)
    }

    fn on_rests(&self, name: &str) -> bool {
        name == Row::DEGREE
            || name == Row::TIE
            || name == Row::GRAB
            || name == Row::SLIDE
            || CC_ROWS.contains(&name)
            || DRAW_NOTE_ROWS
                .iter()
                .chain(DRAW_VELOCITY_ROWS)
                .chain(DRAW_RESET_ROWS)
                .any(|(_, row)| *row == name)
            || STATEMENT_ROWS.iter().any(|(_, rows)| rows.contains(&name))
    }

    fn is_note(&self, step: usize) -> bool {
        patterns::has_sound(self.pattern, step)
    }

    fn statement_place(name: &str) -> Option<(&'static str, usize)> {
        STATEMENT_ROWS
            .iter()
            .find_map(|(kind, rows)| rows.iter().position(|row| *row == name).map(|place| (*kind, place)))
    }

    /// A step's statement of a kind: its parts, None for a part left out, or None where it names no register.
    fn statement(&self, kind: &str, step: usize) -> Option<Vec<Option<&'a Data>>> {
        let rows = STATEMENT_ROWS.iter().find(|(found, _)| *found == kind)?.1;
        let parts: Vec<Option<&Data>> = rows.iter().map(|row| value(self.pattern, row, step)).collect();
        parts[0]?;
        Some(parts)
    }

    pub fn blocked(&self, row: &RowName, step: usize) -> bool {
        let RowName::Row(name) = row else { return false };
        if *name == Row::TIE {
            return self.is_note(step);
        }
        if *name == Row::TENSION || *name == Row::INVERSION || *name == Row::CHORD_SCALE {
            let chorded = *name == Row::CHORD_SCALE || value(self.pattern, Row::CHORD, step).is_some();
            return !self.is_note(step) || !chorded;
        }
        if let Some((kind, place)) = Self::statement_place(name) {
            if kind == "restart" && step == 0 {
                return true;
            }
            if place == 0 {
                return false;
            }
            return self.statement(kind, step).is_none_or(|parts| parts[place].is_none());
        }
        !(self.is_note(step) || self.on_rests(name))
    }

    pub fn cell_lines(&self, row: &RowName, step: usize) -> Vec<String> {
        let RowName::Row(name) = row else { return vec![String::new()] };
        if *name == Row::DEGREE && self.has_gauge() {
            let degree = self.shown_degree(step).unwrap_or(0);
            let mut lines: Vec<String> = (1..=self.rows_shown())
                .rev()
                .map(|level| {
                    if degree >= level as i64 {
                        marks::MSG_GAUGE_BAR.to_string()
                    } else {
                        String::new()
                    }
                })
                .collect();
            lines.push(self.cell_text(name, step));
            return lines;
        }
        if self.blocked(row, step) {
            let mut lines = vec![String::new(); self.height(row) - 1];
            lines.push(marks::MSG_BLOCKED_CELL.to_string());
            return lines;
        }
        vec![self.cell_text(name, step)]
    }

    fn cell_text(&self, name: &str, step: usize) -> String {
        if let Some(slot) = crate::keyswitches::slot_of_row(name) {
            if !self.is_note(step) && !self.on_rests(name) {
                return String::new();
            }
            let on = self.slot_is_on(slot, step);
            return if on { marks::MSG_TOGGLE_ON } else { marks::MSG_TOGGLE_OFF }.to_string();
        }
        let held = value(self.pattern, name, step);
        let note = self.is_note(step);
        match name {
            _ if name == Row::DEGREE => {
                if !self.has_gauge() {
                    return held.map(data_text).unwrap_or_default();
                }
                let Some(degree) = self.shown_degree(step) else { return String::new() };
                let over = if degree > self.rows_shown() as i64 {
                    marks::MSG_OVER_THE_TOP_MARK
                } else {
                    ""
                };
                format!("{degree}{over}")
            }
            _ if name == Row::OCTAVE => {
                if !note {
                    return String::new();
                }
                let octave = held.and_then(Data::as_whole).map_or(self.default_octave, |whole| whole as i64);
                shown_octave(self.setlist, octave + self.octave_shift(step)).to_string()
            }
            _ if name == Row::ACCIDENTAL || name == Row::GATE || name == Row::DOT || name == Row::INVERSION => {
                if !note {
                    return String::new();
                }
                held.map(data_text).unwrap_or_default()
            }
            _ if [Row::ACCENT, Row::GLIDE, Row::TIE, Row::GRAB, Row::SLIDE, Row::BASS_OCTAVE].contains(&name)
                || DRAW_RESET_ROWS.iter().any(|(_, row)| *row == name) =>
            {
                if !note && !self.on_rests(name) {
                    return String::new();
                }
                if matches!(held, Some(Data::Bool(true))) {
                    marks::MSG_TOGGLE_ON
                } else {
                    marks::MSG_TOGGLE_OFF
                }
                .to_string()
            }
            _ if DRAW_NOTE_ROWS.iter().chain(DRAW_VELOCITY_ROWS).any(|(_, row)| *row == name) => match held.and_then(Data::as_str) {
                Some("add") => marks::MSG_REGISTER_ADDS.to_string(),
                Some("subtract") => marks::MSG_REGISTER_SUBTRACTS.to_string(),
                _ => marks::MSG_TOGGLE_OFF.to_string(),
            },
            _ if Self::statement_place(name).is_some() => {
                let (kind, place) = Self::statement_place(name).expect("a statement's row");
                match self.statement(kind, step) {
                    None => marks::MSG_UNSET_MARK.to_string(),
                    Some(parts) => parts[place].map(data_text).unwrap_or_default(),
                }
            }
            _ if name == Row::TENSION => {
                let Some(Data::List(tensions)) = held else {
                    return marks::MSG_UNSET_MARK.to_string();
                };
                let texts: Vec<String> = tensions.iter().map(data_text).collect();
                for separator in [marks::MSG_TENSIONS_IN_CELL_SEPARATOR, ""] {
                    if texts.join(separator).chars().count() <= 5 {
                        return texts.join(separator);
                    }
                }
                named(marks::MSG_TENSIONS_COUNTED, &[("count", texts.len().into())])
            }
            _ if name == Row::CHORD_SCALE => held.map_or(marks::MSG_UNSET_MARK.to_string(), |kind| {
                title_words(&data_text(kind)).chars().take(5).collect()
            }),
            _ => {
                if !note && !self.on_rests(name) {
                    return String::new();
                }
                let description = described(name);
                match held {
                    None if description.lowest.is_some() && !description.quiet => description.default.as_ref().map_or("0".to_string(), plain_text),
                    None => marks::MSG_UNSET_MARK.to_string(),
                    Some(held) if name == Row::DOUBLE => {
                        let text = data_text(held);
                        marks::MSG_CELL_MARKS
                            .iter()
                            .find(|(row, _)| *row == name)
                            .and_then(|(_, marks)| marks.iter().find(|(found, _)| *found == text))
                            .map_or(text.clone(), |(_, mark)| mark.to_string())
                    }
                    Some(held) => data_text(held),
                }
            }
        }
    }

    // The keys of the cursor's row.

    pub fn keys(&self, row: &RowName, step: usize) -> Vec<KeyItem> {
        use bindings::*;
        let of = |class: &'static bindings::KeyClass, binding: &'static bindings::Binding| KeyItem::of(class, binding);
        let RowName::Row(name) = row else {
            let RowName::Section(section) = row else { unreachable!() };
            return vec![of(
                &SectionRow::CLASS,
                if self.is_open(section) { &SectionRow::CLOSE } else { &SectionRow::OPEN },
            )];
        };
        if self.blocked(row, step) {
            return Vec::new();
        }
        let adjust = |class: &'static KeyClass| vec![of(class, &PatternRow::LESS), of(class, &PatternRow::MORE)];
        let cycle = |class: &'static KeyClass| {
            let mut keys = vec![of(class, &CycleRow::NEXT)];
            keys.extend(adjust(class));
            keys.push(of(class, &CycleRow::CLEAR));
            keys
        };
        let toggle = |class: &'static KeyClass| vec![of(class, &ToggleRow::TOGGLE), of(class, &ToggleRow::CLEAR)];
        let number = |class: &'static KeyClass| {
            let mut keys = vec![of(class, &NumberRow::TYPE).wanting_key()];
            keys.extend(adjust(class));
            keys.push(of(class, &NumberRow::ASK));
            keys.push(of(class, &NumberRow::DEFAULT));
            keys
        };
        let chord = |class: &'static KeyClass| {
            let mut keys = vec![of(class, &ChordRow::CHOOSE), of(class, &ChordRow::NEXT)];
            keys.extend(adjust(class));
            keys.push(of(class, &ChordRow::CLEAR));
            keys
        };
        let keys = match *name {
            _ if *name == Row::DEGREE => {
                let mut keys = Vec::new();
                if self.is_drum() {
                    keys.push(of(&DegreeRow::CLASS, &DegreeRow::NOTE).wanting_key());
                } else {
                    let limit = self.degree_limit();
                    let digits: Vec<&'static str> = if limit > 9 {
                        crate::keys::keys_of(&DegreeRow::DEGREE.keys)
                    } else {
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9"][..limit].to_vec()
                    };
                    let label = named(legends::MSG_DIGITS_RANGE_LABEL, &[("low", MIN_DEGREE.into()), ("high", limit.into())]);
                    keys.push(of(&DegreeRow::CLASS, &DegreeRow::DEGREE).wanting_key().with_keys(digits).named(&label));
                    keys.extend(adjust(&DegreeRow::CLASS));
                    keys.push(of(&DegreeRow::CLASS, &DegreeRow::TOGGLE_NOTE));
                }
                if self.is_note(step) {
                    keys.push(of(&DegreeRow::CLASS, &DegreeRow::CLEAR));
                }
                keys
            }
            _ if *name == Row::OCTAVE => {
                let highest = described(Row::OCTAVE).highest.unwrap_or(10);
                let label = named(
                    legends::MSG_DIGITS_RANGE_LABEL,
                    &[("low", "0".into()), ("high", shown_octave(self.setlist, highest).into())],
                );
                let mut keys = vec![of(&OctaveRow::CLASS, &OctaveRow::TYPE).wanting_key().named(&label)];
                keys.extend(adjust(&OctaveRow::CLASS));
                keys.push(of(&OctaveRow::CLASS, &OctaveRow::DEFAULT));
                keys
            }
            _ if *name == Row::ACCIDENTAL => cycle(&AccidentalRow::CLASS),
            _ if *name == Row::DOT => cycle(&DotRow::CLASS),
            _ if *name == Row::INVERSION => cycle(&InversionRow::CLASS),
            _ if [Row::DOUBLE, Row::OMIT, Row::BASS].contains(name) => cycle(&CycleRow::CLASS),
            _ if DRAW_NOTE_ROWS.iter().chain(DRAW_VELOCITY_ROWS).any(|(_, row)| row == name) => cycle(&RegisterRow::CLASS),
            _ if crate::keyswitches::slot_of_row(name).is_some() => toggle(&KeyswitchSlotRow::CLASS),
            _ if *name == Row::ACCENT => toggle(&AccentRow::CLASS),
            _ if *name == Row::GLIDE => toggle(&GlideRow::CLASS),
            _ if *name == Row::TIE => toggle(&TieRow::CLASS),
            _ if *name == Row::GRAB => toggle(&GrabRow::CLASS),
            _ if *name == Row::SLIDE => toggle(&SlideRow::CLASS),
            _ if *name == Row::BASS_OCTAVE => toggle(&ToggleRow::CLASS),
            _ if DRAW_RESET_ROWS.iter().any(|(_, row)| row == name) => toggle(&DrawResetRow::CLASS),
            _ if *name == Row::CHORD => chord(&ChordRow::CLASS),
            _ if *name == Row::TENSION => chord(&TensionRow::CLASS),
            _ if *name == Row::CHORD_SCALE => chord(&ChordScaleRow::CLASS),
            _ if *name == Row::GATE => {
                let mut keys = adjust(&GateRow::CLASS);
                keys.push(of(&GateRow::CLASS, &GateRow::TYPE));
                keys.push(of(&GateRow::CLASS, &GateRow::ONE_STEP));
                keys
            }
            _ if CC_ROWS.contains(name) => number(&CcRow::CLASS),
            _ if Self::statement_place(name).is_some() => {
                let mut keys = vec![of(&StatementRow::CLASS, &StatementRow::CHOOSE), of(&StatementRow::CLASS, &StatementRow::NEXT)];
                keys.extend(adjust(&StatementRow::CLASS));
                keys.push(of(&StatementRow::CLASS, &StatementRow::CLEAR));
                keys
            }
            _ => number(&NumberRow::CLASS),
        };
        let owner = keys.first().map(|item| item.owner);
        match owner {
            Some(owner) => crate::keys::in_order(owner, keys),
            None => keys,
        }
    }

    // The drawing.

    /// Each row with whether a rule is drawn over it.
    fn row_blocks(&self, rows: &[RowName]) -> Vec<(RowName, bool)> {
        let mut blocks = Vec::new();
        let mut after_rule = false;
        for row in rows {
            blocks.push((row.clone(), self.rule_before(row) && !after_rule));
            after_rule = self.rule_after(row);
        }
        blocks
    }

    fn rows_height(&self, rows: &[RowName]) -> usize {
        self.row_blocks(rows)
            .iter()
            .map(|(row, before)| self.height(row) + usize::from(*before) + usize::from(self.rule_after(row)))
            .sum()
    }

    fn window_height(&self, rows: &[RowName]) -> usize {
        let first = rows.first().is_some_and(|row| self.rule_before(row));
        let last = rows.last().is_some_and(|row| self.rule_after(row));
        self.rows_height(rows) - usize::from(first) - usize::from(last)
    }

    /// The lines the grid always has besides the gauge's rows and the scrolled rows.
    fn fixed_lines(&self) -> usize {
        let pinned = self.rows_height(&[RowName::Row(Row::DEGREE), RowName::Row(Row::OCTAVE)]);
        let gauge = if self.has_gauge() { self.rows_shown() } else { 0 };
        LINES_AROUND_GRID + pinned - gauge
    }

    /// How many rows the gauge is drawn with: all of them where there's room, else what leaves room for the tallest scrolled row.
    pub fn fit_gauge(&mut self, screen_height: usize, header_lines: usize, legend_lines: usize) {
        let reachable = self.reachable();
        let scrolled = &reachable[2..];
        let tallest = scrolled
            .iter()
            .map(|row| self.window_height(&[scrolled[0].clone(), row.clone()]))
            .max()
            .unwrap_or(1);
        self.gauge_rows = self.full_rows();
        let room = screen_height as i64 - header_lines as i64 - 2 - legend_lines as i64 - self.fixed_lines() as i64 - tallest as i64;
        self.gauge_rows = room.clamp(0, self.full_rows() as i64) as usize;
    }

    /// The scrolled rows that fit under the pinned ones, the window moved so that the cursor's row is on it.
    pub fn scrolled_shown(&self, height: usize, cursor: usize, first_row: &std::cell::Cell<usize>) -> Vec<RowName> {
        let reachable = self.reachable();
        let rows = &reachable[2..];
        let gauge = if self.has_gauge() { self.rows_shown() } else { 0 };
        let room = (height as i64 - self.fixed_lines() as i64 - gauge as i64).max(1) as usize;
        let place = cursor.checked_sub(2);
        let mut first = first_row.get();
        if let Some(place) = place {
            first = first.min(place);
        }
        first = first.min(rows.len().saturating_sub(1));
        while let Some(place) = place {
            if self.window_height(&rows[first..=place]) > room && first < place {
                first += 1;
            } else {
                break;
            }
        }
        first_row.set(first);
        let mut shown: Vec<RowName> = Vec::new();
        for row in &rows[first..] {
            let mut trial = shown.clone();
            trial.push(row.clone());
            if self.window_height(&trial) > room && !shown.is_empty() {
                break;
            }
            shown.push(row.clone());
        }
        shown
    }

    pub fn widest_label(&self) -> usize {
        self.every_row()
            .iter()
            .flat_map(|row| self.labels(row))
            .map(|label| label.chars().count())
            .max()
            .unwrap_or(0)
            + 2
    }

    fn row_lines(&self, row: &RowName, on_row: bool, step: usize, window: (usize, usize, &[usize]), label_width: usize) -> Vec<Text> {
        let (first, last, beats) = window;
        let labels = self.labels(row);
        let cursor_line = labels.len() - 1;
        let kinds: Vec<LabelKind> = (0..labels.len())
            .map(|number| {
                if !(on_row && number == cursor_line) {
                    LabelKind::Plain
                } else if self.marks_label(row) {
                    LabelKind::Reversed
                } else {
                    LabelKind::Bold
                }
            })
            .collect();
        let node = if self.marks_label(row) {
            RowLines {
                labels,
                label_kinds: kinds,
                heading: true,
                cells: Vec::new(),
                first,
                last,
                beats: Vec::new(),
                selected: None,
                blocked: Vec::new(),
            }
        } else {
            RowLines {
                labels,
                label_kinds: kinds,
                heading: false,
                cells: (first..last).map(|each| self.cell_lines(row, each)).collect(),
                first,
                last,
                beats: beats.to_vec(),
                selected: on_row.then_some((step, cursor_line)),
                blocked: (first..last).filter(|each| self.blocked(row, *each)).collect(),
            }
        };
        grid::row_lines(&node, label_width)
    }

    fn rule(&self, kind: RuleKind, window: (usize, usize, &[usize]), joints: bool, label_width: usize) -> Text {
        let (first, last, beats) = window;
        grid::rule_line(
            &Rule {
                kind,
                first,
                last,
                beats: beats.to_vec(),
                boxed: None,
                joints,
            },
            label_width,
        )
    }

    fn rule_between(&self, above: Option<&RowName>, below: &RowName, window: (usize, usize, &[usize]), label_width: usize) -> Text {
        let heading_above = above.is_some_and(|row| self.marks_label(row));
        let heading_below = self.marks_label(below);
        match (heading_above, heading_below) {
            (true, true) => self.rule(RuleKind::Plain, window, false, label_width),
            (false, true) => self.rule(RuleKind::Closing, window, true, label_width),
            (true, false) => self.rule(RuleKind::Opening, window, true, label_width),
            _ => self.rule(RuleKind::Inner, window, true, label_width),
        }
    }

    /// The grid: the rules, the Step row, the pinned rows and the scrolled rows given, a rule where a row asks for one.
    pub fn grid_lines(&self, rows: &[RowName], cursor: &RowName, step: usize, window: (usize, usize, &[usize]), label_width: usize) -> Vec<Text> {
        let (first, last, beats) = window;
        let mut lines = vec![
            self.rule(RuleKind::Top, window, true, label_width),
            grid::step_numbers_line(first, last, beats, None, label_width),
        ];
        let mut all = vec![RowName::Row(Row::DEGREE), RowName::Row(Row::OCTAVE)];
        all.extend(rows.iter().cloned());
        let blocks = self.row_blocks(&all);
        for (number, (row, rule_before)) in blocks.iter().enumerate() {
            if *rule_before {
                lines.push(self.rule_between(number.checked_sub(1).map(|before| &blocks[before].0), row, window, label_width));
            }
            lines.extend(self.row_lines(row, row == cursor, step, window, label_width));
            if self.rule_after(row) && number + 1 < blocks.len() {
                lines.push(self.rule_between(Some(row), &blocks[number + 1].0, window, label_width));
            }
        }
        let joints = !blocks.last().is_some_and(|(row, _)| self.marks_label(row));
        lines.push(self.rule(RuleKind::Bottom, window, joints, label_width));
        let _ = Box::RULE;
        lines
    }
}

fn scale_kind(setlist: &Setlist, name: &str) -> String {
    match setlist.get_item(Section::SCALES, name) {
        Some(llamatron_model::objects::setlist::Item::Scale(scale)) => scale.get_kind().as_str().unwrap_or("").to_string(),
        _ => String::new(),
    }
}

fn title_words(text: &str) -> String {
    text.replace('_', " ")
        .split(' ')
        .map(|word| {
            let mut characters = word.chars();
            characters.next().map_or(String::new(), |first| {
                first.to_uppercase().collect::<String>() + &characters.as_str().to_lowercase()
            })
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// What a key on a row of the rows view does to the pattern, which the editor makes as one change: values written on rows
/// of the cursor's step, a step's note erased, a statement stored, the number typed so far, whether the change continues
/// the one before, as a second digit typed into a cell does, a refusal to say, and a dialog to ask in.
#[derive(Default)]
pub struct RowEdit {
    pub writes: Vec<(String, Option<Data>)>,
    pub clear_sound: bool,
    pub statement: Option<(&'static str, Option<Data>)>,
    pub typed: Option<String>,
    pub continues: bool,
    pub refusal: Option<String>,
    pub asking: Option<RowAsking>,
}

/// What a row asks for in a dialog: a number in a range, or a length up to a most.
pub enum RowAsking {
    Number {
        row: String,
        title: String,
        value: i64,
        lowest: i64,
        highest: i64,
    },
    Length {
        row: String,
        title: String,
        value: String,
        most: Rational,
    },
}

impl RowEdit {
    /// The edit that writes one value.
    fn write(row: &str, value: Option<Data>) -> RowEdit {
        RowEdit {
            writes: vec![(row.to_string(), value)],
            ..RowEdit::default()
        }
    }
}

impl<'a> Rows<'a> {
    /// What a key on a row does at a step, typed being the digits typed into the cell so far.
    pub fn edit(&self, row: &str, step: usize, item: &KeyItem, key: &str, typed: &str) -> RowEdit {
        use bindings::*;
        if let Some(slot) = crate::keyswitches::slot_of_row(row) {
            if item.is(&ToggleRow::TOGGLE) {
                return self.set_slot(slot, step, !self.slot_is_on(slot, step));
            }
            if item.is(&ToggleRow::CLEAR) {
                return self.set_slot(slot, step, false);
            }
            return RowEdit::default();
        }
        let value_here = value(self.pattern, row, step).cloned();
        if item.is(&PatternRow::LESS) || item.is(&PatternRow::MORE) {
            let offset = if item.is(&PatternRow::LESS) { -1 } else { 1 };
            return self.nudge(row, step, offset);
        }
        if item.is(&CycleRow::NEXT) || item.is(&ChordRow::NEXT) || item.is(&StatementRow::NEXT) {
            return self.nudge(row, step, 1);
        }
        if item.is(&CycleRow::CLEAR) || item.is(&ChordRow::CLEAR) || item.is(&NumberRow::DEFAULT) || item.is(&OctaveRow::DEFAULT) || item.is(&GateRow::ONE_STEP)
        {
            return RowEdit::write(row, None);
        }
        if item.is(&StatementRow::CLEAR) {
            return self.statement_part(row, step, None);
        }
        if item.is(&ToggleRow::CLEAR) {
            return RowEdit::write(row, Some(Data::Bool(false)));
        }
        if item.is(&ToggleRow::TOGGLE) {
            return self.toggle(row, step);
        }
        if item.is(&DegreeRow::CLEAR) {
            return RowEdit {
                clear_sound: true,
                ..RowEdit::default()
            };
        }
        if item.is(&DegreeRow::TOGGLE_NOTE) {
            if self.is_note(step) {
                return RowEdit {
                    clear_sound: true,
                    ..RowEdit::default()
                };
            }
            return self.with_note(step, RowEdit::write(Row::DEGREE, Some(Data::Whole(MIN_DEGREE as i128))));
        }
        if item.is(&DegreeRow::NOTE) {
            return self.with_note(step, RowEdit::write(Row::DEGREE, Some(Data::text(&key.to_uppercase()))));
        }
        if item.is(&DegreeRow::DEGREE) {
            let typed_edit = typed_number(typed, key, MIN_DEGREE, self.degree_limit() as i64);
            let Some(number) = typed_edit.number else {
                return RowEdit {
                    typed: Some(String::new()),
                    ..RowEdit::default()
                };
            };
            let mut edit = self.with_note(step, RowEdit::write(Row::DEGREE, Some(Data::Whole(number as i128))));
            edit.typed = Some(typed_edit.typed);
            edit.continues = typed_edit.continues;
            return edit;
        }
        if item.is(&OctaveRow::TYPE) {
            let described = described(Row::OCTAVE);
            let (lowest, highest) = (described.lowest.unwrap_or(0), described.highest.unwrap_or(10));
            let typed_edit = typed_number(typed, key, shown_octave(self.setlist, lowest), shown_octave(self.setlist, highest));
            let Some(number) = typed_edit.number else {
                return RowEdit {
                    typed: Some(String::new()),
                    ..RowEdit::default()
                };
            };
            let stored = number - shown_octave(self.setlist, 0);
            let mut edit = RowEdit::write(Row::OCTAVE, Some(Data::Whole(stored as i128)));
            edit.typed = Some(typed_edit.typed);
            edit.continues = typed_edit.continues;
            return edit;
        }
        if item.is(&NumberRow::TYPE) {
            let (lowest, highest) = number_range(row);
            let typed_edit = typed_number(typed, key, lowest, highest);
            let Some(number) = typed_edit.number else {
                return RowEdit {
                    typed: Some(String::new()),
                    ..RowEdit::default()
                };
            };
            let mut edit = RowEdit::write(row, Some(Data::Whole(number as i128)));
            edit.typed = Some(typed_edit.typed);
            edit.continues = typed_edit.continues;
            return edit;
        }
        if item.is(&NumberRow::ASK) {
            let (lowest, highest) = number_range(row);
            let label = named_in(labels::MSG_ROW_LABELS, row);
            let title = named(
                llamatron_strings::messages::MSG_NUMBER_PROMPT,
                &[("row", label.as_str().into()), ("low", lowest.into()), ("high", highest.into())],
            );
            let now = value_here.as_ref().and_then(Data::as_whole).map_or(number_default(row), |whole| whole as i64);
            let asking = RowAsking::Number {
                row: row.to_string(),
                title,
                value: now,
                lowest,
                highest,
            };
            return RowEdit {
                asking: Some(asking),
                ..RowEdit::default()
            };
        }
        if item.is(&GateRow::TYPE) {
            let most = described(row).most.map_or(Rational::whole(4), |most| Rational::whole(most as i128));
            let shown = value_here.as_ref().and_then(Data::as_str).unwrap_or_default().to_string();
            let asking = RowAsking::Length {
                row: row.to_string(),
                title: llamatron_strings::messages::MSG_GATE_PROMPT.to_string(),
                value: shown,
                most,
            };
            return RowEdit {
                asking: Some(asking),
                ..RowEdit::default()
            };
        }
        RowEdit::default()
    }

    /// A new note made with what every note has: an octave, and no tie, since a tie only holds the note before it.
    fn with_note(&self, step: usize, mut edit: RowEdit) -> RowEdit {
        if value(self.pattern, Row::TIE, step).is_some_and(|tie| matches!(tie, Data::Bool(true))) {
            edit.writes.push((Row::TIE.to_string(), Some(Data::Bool(false))));
        }
        if value(self.pattern, Row::OCTAVE, step).is_none() {
            edit.writes.push((Row::OCTAVE.to_string(), Some(Data::Whole(self.default_octave as i128))));
        }
        edit
    }

    /// Turn a row's value on or off: a grab on an empty step gives it a note first, and a keyswitch slot's row adds or takes
    /// its slot from the step's keyswitches.
    fn toggle(&self, row: &str, step: usize) -> RowEdit {
        let on = value(self.pattern, row, step).is_some_and(|value| matches!(value, Data::Bool(true)));
        let mut edit = RowEdit::default();
        if row == Row::GRAB && !on && !self.is_note(step) {
            let note = if self.is_drum() {
                Data::text(DRUM_GRAB_NOTE)
            } else {
                Data::Whole(MIN_DEGREE as i128)
            };
            edit = self.with_note(step, RowEdit::write(Row::DEGREE, Some(note)));
        }
        edit.writes.push((row.to_string(), Some(Data::Bool(!on))));
        edit
    }

    /// Make a row's value less or more by one, as each kind of row steps.
    fn nudge(&self, row: &str, step: usize, offset: i64) -> RowEdit {
        let held = value(self.pattern, row, step).cloned();
        if row == Row::DEGREE {
            return self.nudge_degree(step, offset);
        }
        if row == Row::OCTAVE {
            let described = described(Row::OCTAVE);
            let now = held.as_ref().and_then(Data::as_whole).map_or(self.default_octave, |whole| whole as i64);
            let moved = (now + offset).clamp(described.lowest.unwrap_or(0), described.highest.unwrap_or(10));
            return RowEdit::write(row, Some(Data::Whole(moved as i128)));
        }
        if row == Row::GATE {
            return RowEdit::write(row, Some(Data::text(&self.next_gate(held.as_ref(), offset))));
        }
        if Self::statement_place(row).is_some() {
            return self.nudge_statement(row, step, offset);
        }
        if row == Row::CHORD || row == Row::TENSION || row == Row::CHORD_SCALE {
            let options = chord_options(row);
            let shown = held.as_ref().map(data_text);
            let place = options.iter().position(|option| option.as_ref().map(data_text) == shown).unwrap_or(0) as i64;
            let moved = (place + offset).clamp(0, options.len() as i64 - 1) as usize;
            return RowEdit::write(row, options[moved].clone());
        }
        let described = described(row);
        if !described.choices.is_empty() {
            // A row of a few fixed choices goes round them, its blank first.
            let mut choices = vec![described.blank];
            choices.extend(described.choices.iter().copied());
            let blank = plain_data(&described.blank);
            let now = held.clone().unwrap_or(blank);
            let place = choices.iter().position(|choice| plain_data(choice) == now).unwrap_or(0) as i64;
            let moved = (place + offset).rem_euclid(choices.len() as i64) as usize;
            let chosen = plain_data(&choices[moved]);
            return RowEdit::write(row, (!chosen.is_null()).then_some(chosen));
        }
        let (lowest, highest) = number_range(row);
        let now = held.as_ref().and_then(Data::as_whole).map_or(number_default(row), |whole| whole as i64);
        RowEdit::write(row, Some(Data::Whole((now + offset).clamp(lowest, highest) as i128)))
    }

    /// Move the degree a step along the scale, stopping at the top or bottom of a known scale and saying so, a degree past the
    /// scale written back within it with its octave moved to match.
    fn nudge_degree(&self, step: usize, offset: i64) -> RowEdit {
        let Some(size) = self.scale_size() else {
            let now = value(self.pattern, Row::DEGREE, step).and_then(Data::as_whole).map_or(0, |whole| whole as i64);
            let moved = (now + offset).clamp(MIN_DEGREE, self.degree_limit() as i64);
            return self.with_note(step, RowEdit::write(Row::DEGREE, Some(Data::Whole(moved as i128))));
        };
        let size = size as i64;
        let mut edit = RowEdit::default();
        let degree = match self.shown_degree(step) {
            None => MIN_DEGREE,
            Some(current) => {
                let degree = current + offset;
                let scale = self.scale.clone().unwrap_or_default();
                if degree > size {
                    edit.refusal = Some(named(llamatron_strings::errors::ERR_TOP_OF_SCALE, &[("scale", scale.as_str().into())]));
                    size
                } else if degree < MIN_DEGREE {
                    edit.refusal = Some(named(llamatron_strings::errors::ERR_BOTTOM_OF_SCALE, &[("scale", scale.as_str().into())]));
                    MIN_DEGREE
                } else {
                    degree
                }
            }
        };
        let shift = self.octave_shift(step);
        if shift != 0 {
            let now = value(self.pattern, Row::OCTAVE, step)
                .and_then(Data::as_whole)
                .map_or(self.default_octave, |whole| whole as i64);
            edit.writes.push((Row::OCTAVE.to_string(), Some(Data::Whole((now + shift) as i128))));
        }
        edit.writes.push((Row::DEGREE.to_string(), Some(Data::Whole(degree as i128))));
        let mut filled = self.with_note(step, RowEdit::default());
        // The octave just written stands, where filling in would give a blank one the default.
        filled.writes.retain(|(row, _)| !(row == Row::OCTAVE && shift != 0));
        edit.writes.extend(filled.writes);
        edit
    }

    /// The next plain length longer or shorter than a gate is now, the pattern's step being a blank gate's length.
    fn next_gate(&self, held: Option<&Data>, offset: i64) -> String {
        let step = self
            .pattern
            .get_written("step_size")
            .or_else(|| self.setlist.get_written("step_size"))
            .and_then(Data::as_str)
            .and_then(|text| Rational::parse(text).ok())
            .unwrap_or_else(|| Rational::new(1, 16));
        let now = held.and_then(Data::as_str).and_then(|text| Rational::parse(text).ok()).unwrap_or(step);
        let lengths: Vec<Rational> = GATE_LENGTH_CHOICES.iter().filter_map(|length| Rational::parse(length).ok()).collect();
        let chosen = if offset > 0 {
            lengths.iter().find(|length| **length > now).copied().unwrap_or(lengths[lengths.len() - 1])
        } else {
            lengths.iter().rev().find(|length| **length < now).copied().unwrap_or(lengths[0])
        };
        chosen.to_string()
    }

    /// Step a statement's part to its next or last choice, or its number up or down, stopping at each end.
    fn nudge_statement(&self, row: &str, step: usize, offset: i64) -> RowEdit {
        let Some((kind, place)) = Self::statement_place(row) else {
            return RowEdit::default();
        };
        let statement = self.whole_statement(kind, step);
        let part = STATEMENT_PART_NAMES[place];
        let current = statement.as_ref().and_then(|statement| statement.get(part)).cloned();
        let choices: Option<Vec<Option<Data>>> = match part {
            "register" => {
                let mut choices = vec![None];
                choices.extend(DRAW_NAMES.iter().map(|name| Some(Data::text(name))));
                Some(choices)
            }
            "operator" => Some(OPERATORS.iter().map(|each| Some(Data::text(each))).collect()),
            "comparison" => Some(RESULT_COMPARISONS.iter().map(|each| Some(Data::text(each))).collect()),
            _ => None,
        };
        if let Some(choices) = choices {
            let Some(at) = choices.iter().position(|choice| *choice == current) else {
                return RowEdit::default();
            };
            let moved = at as i64 + offset;
            if moved < 0 || moved >= choices.len() as i64 {
                return RowEdit::default();
            }
            return self.statement_part(row, step, choices[moved as usize].clone());
        }
        let number = match current.as_ref() {
            Some(Data::Text(name)) if VALUE_NAMES.contains(&name.as_str()) => 0,
            Some(value) => value.as_whole().map_or(0, |whole| whole as i64) + offset,
            None => return RowEdit::default(),
        };
        if number.abs() > MAX_STATEMENT_NUMBER {
            return RowEdit::default();
        }
        self.statement_part(row, step, Some(Data::Whole(number as i128)))
    }

    /// A step's statement of a kind as one mapping of its parts, or None where it names no register.
    fn whole_statement(&self, kind: &str, step: usize) -> Option<Data> {
        let parts = self.statement(kind, step)?;
        let pairs = parts
            .iter()
            .zip(STATEMENT_PART_NAMES)
            .filter_map(|(value, part)| value.map(|value| (Data::text(part), value.clone())))
            .collect();
        Some(Data::Map(pairs))
    }

    /// The edit that gives the cursor's step a row's part of its statement: a register starts a statement where there is
    /// none and no register takes it away, an operator keeps the parts it still takes, and nothing divides by zero.
    fn statement_part(&self, row: &str, step: usize, chosen: Option<Data>) -> RowEdit {
        let Some((kind, place)) = Self::statement_place(row) else {
            return RowEdit::default();
        };
        let statement = self.whole_statement(kind, step);
        let part = STATEMENT_PART_NAMES[place];
        let stored = match (part, statement, chosen) {
            ("register", _, None) => None,
            ("register", None, Some(register)) => Some(crate::forms::statements::new_statement(register.as_str().unwrap_or_default())),
            (_, None, _) => return RowEdit::default(),
            ("operator", Some(statement), Some(operator)) => Some(crate::forms::statements::with_operator(&statement, operator.as_str().unwrap_or_default())),
            (_, Some(statement), None) => Some(statement),
            (part, Some(statement), Some(value)) => {
                let operator = statement.get("operator").and_then(Data::as_str).unwrap_or_default();
                if part == "value" && DIVIDING_OPERATORS.contains(&operator) && value == Data::Whole(0) {
                    return RowEdit {
                        refusal: Some(llamatron_strings::errors::ERR_CANNOT_DIVIDE_BY_ZERO.to_string()),
                        ..RowEdit::default()
                    };
                }
                Some(crate::forms::statements::with_part(&statement, part, value))
            }
        };
        RowEdit {
            statement: Some((kind, stored)),
            ..RowEdit::default()
        }
    }
}

/// The parts of a statement in the order its five rows hold them.
const STATEMENT_PART_NAMES: [&str; 5] = ["register", "operator", "value", "comparison", "against"];
/// The note a grab on an empty step of a drum pattern plays.
const DRUM_GRAB_NOTE: &str = "C";

/// A row's lowest and highest number, as its description says.
fn number_range(row: &str) -> (i64, i64) {
    let described = described(row);
    (described.lowest.unwrap_or(0), described.highest.unwrap_or(127))
}

/// The number a blank step of a row plays as, where a nudge starts.
fn number_default(row: &str) -> i64 {
    match described(row).default.as_ref().map(plain_data) {
        Some(Data::Whole(whole)) => whole as i64,
        _ => 0,
    }
}

/// The options a chord row steps through, none first: the chord symbols, each tension alone, or each kind of scale.
fn chord_options(row: &str) -> Vec<Option<Data>> {
    let mut options = vec![None];
    if row == Row::CHORD {
        options.extend(
            CHORD_SYMBOLS
                .iter()
                .map(|symbol| Some(symbol.parse::<i128>().map_or_else(|_| Data::text(symbol), Data::Whole))),
        );
    } else if row == Row::TENSION {
        options.extend(described(row).choices.iter().map(|tension| Some(Data::List(vec![plain_data(tension)]))));
    } else {
        options.extend(crate::generated::tables::SCALE_TYPES_IN_ORDER.iter().map(|kind| Some(Data::text(kind))));
    }
    options
}

/// A digit typed into a cell: the number it makes with the digits typed before, or the digit alone where that would be out
/// of range, or none where neither fits; extending the number continues the same edit, so that typing 12 is one undo step.
struct Typed {
    number: Option<i64>,
    typed: String,
    continues: bool,
}

fn typed_number(typed: &str, digit: &str, lowest: i64, highest: i64) -> Typed {
    for text in [format!("{typed}{digit}"), digit.to_string()] {
        if let Ok(number) = text.parse::<i64>() {
            if (lowest..=highest).contains(&number) {
                let continues = !typed.is_empty() && text != digit;
                return Typed {
                    number: Some(number),
                    typed: text,
                    continues,
                };
            }
        }
    }
    Typed {
        number: None,
        typed: String::new(),
        continues: false,
    }
}
