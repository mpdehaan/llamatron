// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What the one-row editors share (the Python screens/shared/one_row_editor.py, step_editor.py and step_grid.py with its
//! renderer): a row of numbers either side of zero, one to a step, edited under a cursor that Left and Right move, [ and ]
//! and Up and Down changing the cursor's number, digits typing one, a row wider than the screen scrolling sideways.

use crate::app::App;
use crate::drawing::{fit, fit_aligned, Align, BoxCharacters as Box, Style};
use crate::keybindings::{Binding, KeyClass, OneRowEditor as Keys};
use crate::keys::{KeyItem, STEP_BACK, STEP_FORWARD};
use crate::page::{Duration, Page};
use crate::text::Text;
use crate::themes::Colour;
use llamatron_strings::{marks, named};
use std::cell::Cell;

/// How wide the grid's label column is, and the room kept beside the grid.
const LABEL_WIDTH: usize = 8;
const GRID_MARGIN: usize = 4;

/// A line of the grid an editor draws.
pub enum GridLine {
    /// The line over the grid, drawn dim or bold, with which steps are on screen at its right.
    Heading { text: String, dim: bool, bold: bool, steps_shown: String },
    /// A rule along or across the grid: top, across or bottom, crossing so many steps' cells.
    Rule { edge: Edge, count: usize },
    /// A row: its label, a cell per step on screen, the selected step's cell, and whether it is bold.
    Row {
        label: String,
        cells: Vec<(usize, String)>,
        selected: Option<usize>,
        bold: bool,
    },
    /// A line as it was drawn.
    Drawn(Text),
}

#[derive(Clone, Copy)]
pub enum Edge {
    Top,
    Across,
    Bottom,
}

/// A grid's lines drawn with a cell width at a width.
pub fn grid_lines(lines: Vec<GridLine>, cell_width: usize, width: usize) -> Vec<Text> {
    lines.into_iter().map(|line| grid_line(line, cell_width, width)).collect()
}

fn grid_line(line: GridLine, cell_width: usize, width: usize) -> Text {
    match line {
        GridLine::Drawn(text) => text,
        GridLine::Rule { edge, count } => {
            let (left, middle, right) = match edge {
                Edge::Top => (Box::TOP_LEFT, Box::TOP_TEE, Box::TOP_RIGHT),
                Edge::Across => (Box::LEFT_TEE, Box::CROSS, Box::RIGHT_TEE),
                Edge::Bottom => (Box::BOTTOM_LEFT, Box::BOTTOM_TEE, Box::BOTTOM_RIGHT),
            };
            let cells = vec![Box::RULE.repeat(cell_width); count].join(middle);
            Text::styled(&format!("{left}{}{middle}{cells}{right}", Box::RULE.repeat(LABEL_WIDTH)), Style::DIM)
        }
        GridLine::Row { label, cells, selected, bold } => {
            let mut line = Text::plain(&format!("{}{}{}", Box::BAR, fit(&label, LABEL_WIDTH), Box::BAR));
            for (place, text) in cells {
                let style = if Some(place) == selected {
                    Style::REVERSE
                } else if bold {
                    Style::BOLD
                } else {
                    Style::PLAIN
                };
                line.append(&fit_aligned(&text, cell_width, Align::Center), style);
                line.append(Box::BAR, Style::PLAIN);
            }
            line
        }
        GridLine::Heading { text, dim, bold, steps_shown } => {
            let style = if dim {
                Style::DIM
            } else if bold {
                Style::BOLD
            } else {
                Style::PLAIN
            };
            if steps_shown.is_empty() {
                return Text::styled(&text, style);
            }
            let mut line = Text::styled(&format!("{} ", fit(&text, width.saturating_sub(steps_shown.chars().count() + 1))), style);
            line.append(&steps_shown, Style::DIM);
            line
        }
    }
}

/// What a one-row editor says of itself.
pub trait OneRow {
    fn name(&self) -> &'static str;
    fn class(&self) -> &'static KeyClass;
    fn crumbs(&self, app: &App) -> Vec<String>;
    fn caption(&self, app: &App) -> String;
    fn theme(&self) -> Option<Colour>;
    /// How wide a cell is drawn, the largest number either side of zero, and how long the row can be.
    fn cell_width(&self) -> usize;
    fn most(&self) -> i64;
    fn most_steps(&self) -> usize;
    fn fewest_steps(&self) -> usize {
        1
    }
    /// Its own bindings for inserting and removing a step.
    fn insert(&self) -> &'static Binding;
    fn remove(&self) -> &'static Binding;
    /// The words for which steps are on screen.
    fn steps_shown(&self) -> &'static str {
        marks::MSG_STEPS_SHOWN
    }
    fn values(&self, app: &App) -> Vec<Option<i64>>;
    fn can_edit(&self, _app: &App) -> bool {
        true
    }
    fn more_keys(&self, _app: &App) -> Vec<KeyItem> {
        Vec::new()
    }
    /// The keys the page has beyond the row's own that depend on the cursor's step.
    fn more_keys_at(&self, app: &App, _step: usize) -> Vec<KeyItem> {
        self.more_keys(app)
    }
    fn press_more(&mut self, _app: &mut App, _item: &KeyItem, _step: usize) {}
    /// The grid's lines, from the first step on screen to the last (excluded), the cursor on a step.
    fn lines(&self, app: &App, heading: &dyn Fn(String, bool, bool) -> GridLine, window: (usize, usize, usize), step: usize) -> Vec<GridLine>;
}

pub struct OneRowEditor<R: OneRow> {
    pub row: R,
    step: Cell<usize>,
    first_step: Cell<usize>,
}

impl<R: OneRow> OneRowEditor<R> {
    pub fn new(row: R) -> OneRowEditor<R> {
        OneRowEditor {
            row,
            step: Cell::new(0),
            first_step: Cell::new(0),
        }
    }

    fn keep_step(&self, app: &App) -> usize {
        let count = self.row.values(app).len();
        let step = self.step.get().min(count.saturating_sub(1));
        self.step.set(step);
        step
    }

    fn bind(&self, binding: &'static Binding) -> KeyItem {
        KeyItem::of(self.row.class(), binding)
    }

    /// Move the window of steps so that the cursor's step is in it, and return its first and last steps.
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
            self.row.steps_shown(),
            &[
                ("before", before.into()),
                ("first", (first + 1).into()),
                ("last", last.into()),
                ("after", after.into()),
            ],
        )
    }
}

impl<R: OneRow> Page for OneRowEditor<R> {
    fn name(&self) -> &'static str {
        self.row.name()
    }

    fn class(&self) -> &'static KeyClass {
        self.row.class()
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        self.keep_step(app);
        let mut keys = vec![self.bind(&Keys::BACK), self.bind(&Keys::MOVE).wanting_key()];
        if self.row.can_edit(app) {
            keys.push(self.bind(&Keys::LESS));
            keys.push(self.bind(&Keys::MORE));
            keys.push(self.bind(&Keys::TYPE).wanting_key());
            let count = self.row.values(app).len();
            if count < self.row.most_steps() {
                keys.push(self.bind(self.row.insert()));
            }
            if count > self.row.fewest_steps() {
                keys.push(self.bind(self.row.remove()));
            }
            keys.extend(self.row.more_keys_at(app, self.step.get()));
        }
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        let count = self.row.values(app).len();
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&Keys::MOVE) {
            let step: i64 = if key == "left" { STEP_BACK } else { STEP_FORWARD };
            self.step.set((self.step.get() as i64 + step).clamp(0, count as i64 - 1) as usize);
        } else {
            let step = self.keep_step(app);
            self.row.press_more(app, item, step);
        }
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        let step = self.keep_step(app);
        let count = self.row.values(app).len();
        let shown = ((width.saturating_sub(LABEL_WIDTH + GRID_MARGIN)) / (self.row.cell_width() + 1)).max(1);
        let (first, last) = self.window_of_steps(count, shown);
        let steps_shown = self.steps_shown_text(count, first, last);
        let heading = |text: String, dim: bool, bold: bool| GridLine::Heading {
            text,
            dim,
            bold,
            steps_shown: steps_shown.clone(),
        };
        grid_lines(self.row.lines(app, &heading, (first, last, height), step), self.row.cell_width(), width)
    }

    fn crumbs(&self, app: &App) -> Vec<String> {
        self.row.crumbs(app)
    }

    fn caption(&self, app: &App) -> String {
        self.row.caption(app)
    }

    fn theme(&self) -> Option<Colour> {
        self.row.theme()
    }

    fn duration(&self, _app: &App) -> Duration {
        Duration::Nothing
    }
}
