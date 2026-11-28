// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The pattern editor's grid (the Python forms/pattern_grid.py and renderers/pattern_grid.py): its rules, a double joint
//! where a step starts a beat and the cursor's cell boxed in double rules, the line of step numbers, the rows view's rows and
//! the piano roll's rows, each a label column and a cell per step.

use crate::drawing::{fit, fit_aligned, Align, BoxCharacters as Box, Style, SPACE};
use crate::text::Text;
use llamatron_names::fill;
use llamatron_strings::{labels, marks, named};

pub const CELL_WIDTH: usize = 5;
pub const MARK_COLUMN: usize = CELL_WIDTH / 2;
pub const EDGE_WIDTH: usize = 1;

/// Where a rule runs.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum RuleKind {
    Top,
    Inner,
    Bottom,
    Closing,
    Opening,
    Plain,
    Heading,
}

/// How a label is drawn.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum LabelKind {
    Plain,
    Bold,
    Reversed,
    Dim,
}

impl LabelKind {
    fn style(self) -> &'static str {
        match self {
            LabelKind::Plain => Style::PLAIN,
            LabelKind::Bold => Style::BOLD,
            LabelKind::Reversed => Style::REVERSE,
            LabelKind::Dim => Style::DIM,
        }
    }
}

/// A rule across the grid: its kind, its steps, the steps that start a beat, the cursor's step it boxes, and whether it has
/// joints.
pub struct Rule {
    pub kind: RuleKind,
    pub first: usize,
    pub last: usize,
    pub beats: Vec<usize>,
    pub boxed: Option<usize>,
    pub joints: bool,
}

pub fn rule_line(rule: &Rule, label_width: usize) -> Text {
    use RuleKind::*;
    let (left, tee, beat_tee, right, character, boxed_tee, boxed_right) = match rule.kind {
        Top => (Box::TOP_LEFT, Box::TOP_TEE, Box::DOUBLE_TOP_TEE, Box::TOP_RIGHT, Box::RULE, "", ""),
        Inner => (
            Box::LEFT_TEE,
            Box::CROSS,
            Box::DOUBLE_CROSS,
            Box::RIGHT_TEE,
            Box::RULE,
            Box::DOUBLE_RULE_DOUBLE_CROSS,
            Box::DOUBLE_RULE_DOUBLE_RIGHT_TEE,
        ),
        Bottom => (
            Box::BOTTOM_LEFT,
            Box::BOTTOM_TEE,
            Box::DOUBLE_BOTTOM_TEE,
            Box::BOTTOM_RIGHT,
            Box::RULE,
            Box::DOUBLE_RULE_DOUBLE_BOTTOM_TEE,
            Box::DOUBLE_BOTTOM_RIGHT,
        ),
        Closing => (Box::LEFT_TEE, Box::BOTTOM_TEE, Box::DOUBLE_BOTTOM_TEE, Box::RIGHT_TEE, Box::RULE, "", ""),
        Opening => (Box::LEFT_TEE, Box::TOP_TEE, Box::DOUBLE_TOP_TEE, Box::RIGHT_TEE, Box::RULE, "", ""),
        Plain => (Box::LEFT_TEE, Box::CROSS, Box::DOUBLE_CROSS, Box::RIGHT_TEE, Box::RULE, "", ""),
        Heading => (
            Box::DOUBLE_RULE_LEFT_TEE,
            Box::DOUBLE_RULE_CROSS,
            Box::DOUBLE_RULE_DOUBLE_CROSS,
            Box::DOUBLE_RULE_RIGHT_TEE,
            Box::DOUBLE_RULE,
            Box::DOUBLE_RULE_DOUBLE_CROSS,
            Box::DOUBLE_RULE_DOUBLE_RIGHT_TEE,
        ),
    };
    let mut line = Text::default();
    line.append(&format!("{left}{}", character.repeat(label_width)), Style::DIM);
    for step in rule.first..rule.last {
        if rule.boxed.is_some_and(|boxed| step == boxed || step == boxed + 1) {
            line.append(boxed_tee, Style::PLAIN);
        } else if !rule.joints {
            line.append(character, Style::DIM);
        } else if rule.beats.contains(&step) {
            line.append(beat_tee, Style::PLAIN);
        } else {
            line.append(tee, Style::DIM);
        }
        if rule.boxed == Some(step) {
            line.append(&Box::DOUBLE_RULE.repeat(CELL_WIDTH), Style::SELECTED_EDGE);
        } else {
            line.append(&character.repeat(CELL_WIDTH), Style::DIM);
        }
    }
    if rule.boxed.is_some_and(|boxed| boxed + 1 == rule.last) {
        line.append(boxed_right, Style::PLAIN);
    } else {
        line.append(right, Style::DIM);
    }
    line
}

fn append_edge(line: &mut Text, step: usize, beats: &[usize]) {
    if beats.contains(&step) {
        line.append(Box::DOUBLE_BAR, Style::PLAIN);
    } else {
        line.append(Box::BAR, Style::DIM);
    }
}

/// The line of step numbers, the step that sounds in the read head's light, a beat's bold.
pub fn step_numbers_line(first: usize, last: usize, beats: &[usize], sounding: Option<usize>, label_width: usize) -> Text {
    let mut head = Text::default();
    head.append(Box::BAR, Style::DIM);
    head.append(&fit(labels::MSG_STEP_HEADING, label_width), Style::BOLD);
    for step in first..last {
        append_edge(&mut head, step, beats);
        let style = if Some(step) == sounding {
            Style::READ_HEAD
        } else if beats.contains(&step) {
            Style::BOLD
        } else {
            Style::PLAIN
        };
        head.append(&fit_aligned(&(step + 1).to_string(), CELL_WIDTH, Align::Center), style);
    }
    head.append(Box::BAR, Style::DIM);
    head
}

/// A row of the rows view: its label for each line, a section's heading having no cells, each step's cells, the cursor's
/// step and line, and the steps that cannot hold a value.
pub struct RowLines {
    pub labels: Vec<String>,
    pub label_kinds: Vec<LabelKind>,
    pub heading: bool,
    pub cells: Vec<Vec<String>>,
    pub first: usize,
    pub last: usize,
    pub beats: Vec<usize>,
    pub selected: Option<(usize, usize)>,
    pub blocked: Vec<usize>,
}

pub fn row_lines(row: &RowLines, label_width: usize) -> Vec<Text> {
    let mut lines = Vec::new();
    for (number, label) in row.labels.iter().enumerate() {
        let mut line = Text::default();
        line.append(Box::BAR, Style::DIM);
        line.append(&fit(&format!("{SPACE}{label}"), label_width), row.label_kinds[number].style());
        if row.heading {
            line.append(&SPACE.repeat((row.last - row.first) * (CELL_WIDTH + 1)), Style::PLAIN);
            line.append(Box::BAR, Style::DIM);
            lines.push(line);
            continue;
        }
        for step in row.first..row.last {
            append_edge(&mut line, step, &row.beats);
            let text = fit_aligned(&row.cells[step - row.first][number], CELL_WIDTH, Align::Center);
            let style = if row.selected == Some((step, number)) {
                Style::REVERSE
            } else if row.blocked.contains(&step) {
                Style::DIM
            } else {
                Style::PLAIN
            };
            line.append(&text, style);
        }
        line.append(Box::BAR, Style::DIM);
        lines.push(line);
    }
    lines
}

/// What stands before a step of a roll's row: the divider, a note's bar or a chord's line running through, or the cursor's
/// double bar.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Edge {
    Divider,
    Note,
    Hollow,
    Ghost,
    Cursor,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum CellKind {
    Note,
    Ghost,
    Empty,
    OutOfRange,
}

/// A cell of a roll's row: its kind, a note's mark, whether its bar is hollow, how many columns it fills, and whether the
/// cursor is on it.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct RollCell {
    pub kind: CellKind,
    pub mark: Option<String>,
    pub hollow: bool,
    pub columns: usize,
    pub selected: bool,
}

impl RollCell {
    pub fn of(kind: CellKind, selected: bool) -> RollCell {
        RollCell {
            kind,
            mark: None,
            hollow: false,
            columns: CELL_WIDTH,
            selected,
        }
    }
}

/// A row of the piano roll: its label and how it is drawn, each step's edge and cell, the beats and the right border.
pub struct RollRow {
    pub label: String,
    pub label_kind: LabelKind,
    pub steps: Vec<(usize, Edge, RollCell)>,
    pub beats: Vec<usize>,
    pub last_edge: Edge,
}

pub fn roll_row_line(row: &RollRow, label_width: usize) -> Text {
    let mut line = Text::default();
    line.append(Box::BAR, Style::DIM);
    line.append(&fit(&format!("{SPACE}{}", row.label), label_width), row.label_kind.style());
    for (step, edge, cell) in &row.steps {
        match edge {
            Edge::Divider if row.beats.contains(step) => {
                line.append(Box::DOUBLE_BAR, Style::PLAIN);
            }
            Edge::Divider => {
                line.append(Box::BAR, Style::DIM);
            }
            Edge::Note => {
                line.append(marks::MSG_NOTE_EDGE, Style::PLAIN);
            }
            Edge::Hollow => {
                line.append(marks::MSG_NOTE_HOLLOW, Style::PLAIN);
            }
            Edge::Ghost => {
                line.append(marks::MSG_GHOST_LINE, Style::CHORD_NOTE);
            }
            Edge::Cursor => {
                line.append(Box::DOUBLE_BAR, Style::SELECTED_EDGE);
            }
        }
        if cell.kind == CellKind::OutOfRange {
            line.append(marks::MSG_OUT_OF_RANGE_CELL, Style::DIM);
        } else {
            line.append_text(&roll_cell(cell));
        }
    }
    if row.last_edge == Edge::Cursor {
        line.append(Box::DOUBLE_BAR, Style::SELECTED_EDGE);
    } else {
        line.append(Box::BAR, Style::DIM);
    }
    line
}

/// A cell of the roll drawn: a note's bar, hollow for a note an inversion lifts, a chord's added note's line, a blank,
/// reversed under the cursor, or the mark of a place outside the range.
pub fn roll_cell(cell: &RollCell) -> Text {
    match cell.kind {
        CellKind::Note => {
            let bar = solid_note_cell(cell);
            if cell.hollow {
                bar.translated(&[('█', '░'), ('▓', '▒')])
            } else {
                bar
            }
        }
        CellKind::Ghost => Text::styled(
            &fit(&marks::MSG_GHOST_LINE.repeat(cell.columns), CELL_WIDTH),
            if cell.selected { Style::REVERSE } else { Style::CHORD_NOTE },
        ),
        CellKind::OutOfRange => Text::styled(marks::MSG_OUT_OF_RANGE_CELL, Style::DIM),
        CellKind::Empty if cell.selected => Text::styled(&SPACE.repeat(CELL_WIDTH), Style::REVERSE),
        CellKind::Empty => Text::plain(&SPACE.repeat(CELL_WIDTH)),
    }
}

fn solid_note_cell(cell: &RollCell) -> Text {
    match (&cell.mark, cell.columns == CELL_WIDTH) {
        (None, true) => Text::plain(if cell.selected { marks::MSG_NOTE_UNDER_CURSOR } else { marks::MSG_NOTE_CELL }),
        (Some(mark), true) => {
            let template = if cell.selected {
                marks::MSG_NOTE_UNDER_CURSOR_WITH_MARK
            } else {
                marks::MSG_NOTE_CELL_WITH_MARK
            };
            let mut bar = Text::plain(&named(template, &[(fill::MARK, mark.as_str().into())]));
            bar.stylize(Style::REVERSE, MARK_COLUMN, MARK_COLUMN + mark.chars().count());
            bar
        }
        (mark, false) => {
            let block = if cell.selected { marks::MSG_CURSOR_BLOCK } else { marks::MSG_NOTE_EDGE };
            let mut characters: Vec<String> = vec![block.to_string(); cell.columns];
            let column = MARK_COLUMN.min(cell.columns.saturating_sub(1));
            if let Some(mark) = mark {
                characters[column] = mark.clone();
            }
            let mut bar = Text::plain(&fit(&characters.concat(), CELL_WIDTH));
            if let Some(mark) = mark {
                bar.stylize(Style::REVERSE, column, column + mark.chars().count());
            }
            bar
        }
    }
}

/// The roll's top row with a light in the middle of every keyswitched step's cell.
pub fn with_keyswitch_lights(line: &Text, columns: &[usize]) -> Text {
    let mut marked = line.clone();
    for column in columns {
        let after = marked.slice(column + 1, marked.len());
        let mut before = marked.slice(0, *column);
        before.append(marks::MSG_KEYSWITCH_LIGHT, Style::KEYSWITCH_LIGHT);
        before.append_text(&after);
        marked = before;
    }
    marked
}

/// The lines with the read head down them at a column, where no note's bar stands.
pub fn with_read_head(lines: Vec<Text>, column: usize) -> Vec<Text> {
    lines
        .into_iter()
        .map(|line| {
            let here = line.char_at(column);
            if here.is_none() || here.is_some_and(|character| "█▓░▒".contains(character)) {
                return line;
            }
            let mut marked = line.slice(0, column);
            marked.append(marks::MSG_READ_HEAD, Style::READ_HEAD);
            marked.append_text(&line.slice(column + 1, line.len()));
            marked
        })
        .collect()
}
