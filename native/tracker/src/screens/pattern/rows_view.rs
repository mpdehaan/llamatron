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
use llamatron_model::file::data::Data;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::Song;
use llamatron_model::schema::generated::file_format::{
    Row, Section, TrackSetting, CC_ROWS, DRAW_NAMES, DRAW_NOTE_ROWS, DRAW_RESET_ROWS, DRAW_VELOCITY_ROWS, STATEMENT_ROWS,
};
use llamatron_model::schema::generated::limits::MIN_DEGREE;
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
}

fn described(row: &str) -> &'static RowDescription {
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
            // The slots a Keyswitch section has rows for are not ported yet; a pattern that uses none has no section.
            return Vec::new();
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
