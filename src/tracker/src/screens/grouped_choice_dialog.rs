// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Grouped Choice dialog (the Python dialogs/grouped_choice_dialog.py): a picker whose choices lie under headings that
//! open and close, and that still searches every choice as you type.

use crate::app::App;
use crate::drawing::{cursor_mark, fit, Style};
use crate::keybindings::{GroupedChoiceDialog as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::screens::dialogs::{dialog_box, Answer, ChoiceDialog, Then};
use crate::screens::list_page::shown_around;
use crate::text::Text;
use llamatron_names::fill;
use llamatron_strings::{marks, named};

/// How many rows the list shows around the cursor, as every picker does.
const SHOWN_ROWS: usize = 12;

/// Offers choices under headings, each closed until opened, and answers with the chosen item's place in the whole list.
/// With nothing typed, the cursor moves over the headings and the choices of the open ones: Space or ENTER on a heading
/// opens or closes it, PgUp and PgDn jump between headings, and ENTER on a choice picks it. Typing searches every choice,
/// with no headings, as any picker does. The headings left open are kept for the session, so that the next Munge dialog
/// opens as this one was left.
pub struct GroupedChoiceDialog {
    choices: ChoiceDialog,
    headings: Vec<String>,
    sizes: Vec<usize>,
    opened: std::collections::HashSet<String>,
    row: usize,
}

/// A row the cursor moves over: a heading by its number, and under an open one each choice by its place in the whole list.
type GroupRow = (usize, Option<usize>);

impl GroupedChoiceDialog {
    /// Take the groups in the order shown, each a heading and its choices, the headings open, and what takes the answer.
    pub fn new(title: &str, groups: Vec<(String, Vec<String>)>, opened: std::collections::HashSet<String>, then: Then) -> GroupedChoiceDialog {
        let options = groups.iter().flat_map(|(_, options)| options.iter().cloned()).collect();
        let mut choices = ChoiceDialog::new(title, options, 0);
        choices.then = Some(then);
        GroupedChoiceDialog {
            choices,
            headings: groups.iter().map(|(heading, _)| heading.clone()).collect(),
            sizes: groups.iter().map(|(_, options)| options.len()).collect(),
            opened,
            row: 0,
        }
    }

    /// What the cursor moves over with nothing typed: each heading, and the choices of the open ones under it.
    fn rows(&self) -> Vec<GroupRow> {
        let mut rows = Vec::new();
        let mut first = 0;
        for (number, heading) in self.headings.iter().enumerate() {
            rows.push((number, None));
            if self.opened.contains(heading) {
                rows.extend((first..first + self.sizes[number]).map(|place| (number, Some(place))));
            }
            first += self.sizes[number];
        }
        rows
    }

    fn heading_here(&self) -> &str {
        &self.headings[self.rows()[self.row].0]
    }

    fn on_heading(&self) -> bool {
        self.rows()[self.row].1.is_none()
    }

    fn searching(&self) -> bool {
        !self.choices.typed.is_empty()
    }

    /// Move to the heading before or after the cursor, staying put at either end.
    fn jump(&mut self, direction: i64) {
        let headings: Vec<usize> = self
            .rows()
            .iter()
            .enumerate()
            .filter(|(_, (_, choice))| choice.is_none())
            .map(|(place, _)| place)
            .collect();
        let found = if direction < 0 {
            headings.iter().rev().find(|place| **place < self.row)
        } else {
            headings.iter().find(|place| **place > self.row)
        };
        if let Some(place) = found {
            self.row = *place;
        }
    }

    /// The row of a choice where its heading is open, and its heading's row otherwise.
    fn row_showing(&self, place: usize) -> usize {
        let rows = self.rows();
        if let Some(found) = rows.iter().position(|(_, choice)| *choice == Some(place)) {
            return found;
        }
        let mut first = 0;
        for (number, size) in self.sizes.iter().enumerate() {
            if place < first + size {
                return rows.iter().position(|row| *row == (number, None)).unwrap_or(0);
            }
            first += size;
        }
        0
    }

    /// The list's lines with nothing typed: the headings, each open or closed, and the choices of the open ones, around
    /// the cursor.
    fn lines(&self, width: usize) -> Vec<Text> {
        if self.searching() {
            return self.choices.lines(width);
        }
        let rows = self.rows();
        let mut lines = Vec::new();
        for row in shown_around(rows.len(), self.row, SHOWN_ROWS) {
            let (number, place) = rows[row];
            let shown = match place {
                None => {
                    let mark = if self.opened.contains(&self.headings[number]) {
                        marks::MSG_SECTION_OPEN_MARK
                    } else {
                        marks::MSG_SECTION_CLOSED_MARK
                    };
                    named(
                        marks::MSG_GROUP_OF_CHOICES,
                        &[(fill::MARK, mark.into()), (fill::NAME, self.headings[number].as_str().into())],
                    )
                }
                Some(place) => named(marks::MSG_GROUPED_CHOICE, &[(fill::NAME, self.choices.options[place].as_str().into())]),
            };
            lines.push(Text::styled(&fit(&format!("{}{shown}", cursor_mark(row == self.row)), width), Style::PLAIN));
        }
        lines
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl Page for GroupedChoiceDialog {
    fn name(&self) -> &'static str {
        "GroupedChoiceDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        if self.searching() {
            return self.choices.keys(app).iter().map(|item| Self::bind(item.binding)).collect();
        }
        let enter = if !self.on_heading() {
            &Keys::CHOOSE
        } else if self.opened.contains(self.heading_here()) {
            &Keys::CLOSE
        } else {
            &Keys::OPEN
        };
        vec![
            Self::bind(&Keys::CANCEL),
            Self::bind(&Keys::MOVE).wanting_key(),
            Self::bind(enter),
            Self::bind(&Keys::HEADING),
            Self::bind(&Keys::START_SEARCH).wanting_key(),
        ]
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if self.searching() {
            self.choices.press(app, item, key);
            // Erasing the last typed character shows the headings again, the cursor on the choice the search was on.
            if !self.searching() {
                self.row = self.row_showing(self.choices.current);
            }
            return;
        }
        if item.is(&Keys::CANCEL) {
            app.go_back();
        } else if item.is(&Keys::MOVE) {
            let last = self.rows().len().saturating_sub(1);
            self.row = if key == llamatron_names::keys::UP {
                self.row.saturating_sub(1)
            } else {
                (self.row + 1).min(last)
            };
        } else if item.is(&Keys::OPEN) || item.is(&Keys::CLOSE) {
            let heading = self.heading_here().to_string();
            if !self.opened.remove(&heading) {
                self.opened.insert(heading);
            }
            app.session.open_munge_groups = self.opened.clone();
        } else if item.is(&Keys::CHOOSE) {
            if let Some(place) = self.rows()[self.row].1 {
                app.go_back();
                if let Some(then) = self.choices.then.as_mut() {
                    then(app, &Answer::Chosen(place));
                }
            }
        } else if item.is(&Keys::HEADING) {
            self.jump(item.step_of(key).unwrap_or(1));
        } else if item.is(&Keys::START_SEARCH) {
            self.type_text(app, key.chars().next().unwrap_or(' '));
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        dialog_box(&self.choices.title, false, &|inner| self.lines(inner), &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }

    fn takes_text(&self) -> bool {
        true
    }

    fn type_text(&mut self, app: &mut App, character: char) {
        self.choices.type_text(app, character);
    }
}
