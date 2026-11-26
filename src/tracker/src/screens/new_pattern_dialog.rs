// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The New Pattern dialog (the Python dialogs/new_pattern_dialog.py): asks what kind of pattern to make, one written for a
//! scale of so many notes or a drum pattern. Up and Down move between the Scale length, the Drum pattern toggle and the row
//! of buttons. On the Scale length [ and ] step the number, any scale below the fewest notes, and ENTER is OK; on the
//! toggle Space or ENTER flips it, and a drum pattern has no scale length, so that row then shows the blocked cell's mark;
//! on the buttons Left and Right choose and ENTER presses. ESC cancels.

use crate::app::App;
use crate::drawing::{cursor_mark, Style};
use crate::keybindings::{KeyClass, NewPatternDialog as Keys};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::screens::dialogs::dialog_box;
use crate::text::Text;
use llamatron_model::schema::generated::limits::{MAX_SCALE_LENGTH, MIN_SCALE_LENGTH, NEW_PATTERN_SCALE_LENGTH};
use llamatron_strings::{labels, marks, messages};

/// The rows the cursor moves over, in the order drawn.
const SCALE_LENGTH: usize = 0;
const DRUM: usize = 1;
const BUTTONS: usize = 2;
const ROWS: usize = 3;
/// The buttons, in the order drawn.
const OK_BUTTON: usize = 0;
/// What pads the labels past the longest.
const LABEL_ROOM: usize = 4;

/// What takes the kind of pattern chosen: whether it is a drum pattern, and the scale length of one that is not, None
/// for any scale.
pub type KindChosen = dyn Fn(&mut App, bool, Option<i64>);

/// Asks for a new pattern's scale length, or whether it is a drum pattern, and hands the kind on, or nothing when
/// cancelled.
pub struct NewPatternDialog {
    scale_length: Option<i64>,
    drum: bool,
    row: usize,
    button: usize,
    then: Box<KindChosen>,
}

impl NewPatternDialog {
    pub fn new(then: Box<KindChosen>) -> NewPatternDialog {
        NewPatternDialog {
            scale_length: Some(NEW_PATTERN_SCALE_LENGTH),
            drum: false,
            row: SCALE_LENGTH,
            button: OK_BUTTON,
            then,
        }
    }

    /// What the Scale length steps through: any scale, then each number of notes.
    fn lengths() -> Vec<Option<i64>> {
        std::iter::once(None).chain((MIN_SCALE_LENGTH..=MAX_SCALE_LENGTH).map(Some)).collect()
    }

    /// Step the scale length, any scale below the fewest notes, stopping at either end.
    fn step(&mut self, direction: i64) {
        let lengths = Self::lengths();
        let place = lengths.iter().position(|length| *length == self.scale_length).unwrap_or(0) as i64 + direction;
        self.scale_length = lengths[place.clamp(0, lengths.len() as i64 - 1) as usize];
    }

    /// Close and hand on the kind chosen.
    fn accept(&mut self, app: &mut App) {
        app.go_back();
        let length = if self.drum { None } else { self.scale_length };
        (self.then)(app, self.drum, length);
    }

    /// Each field's value as shown: a drum pattern's scale length is the blocked cell's mark.
    fn values(&self) -> [String; 2] {
        let length = self.scale_length.map_or(marks::MSG_ANY_SCALE_LENGTH.to_string(), |length| length.to_string());
        let shown = if self.drum { marks::MSG_BLOCKED_CELL.to_string() } else { length };
        let toggle = if self.drum { marks::MSG_TOGGLE_ON } else { "" };
        [shown, toggle.to_string()]
    }

    /// The dialog's lines: each setting after its cursor's mark, its label padded and its value, bold under the cursor and
    /// dim where it cannot be set, a blank line, then the buttons.
    fn lines(&self) -> Vec<Text> {
        let labels = [labels::MSG_SCALE_LENGTH_LABEL, labels::MSG_DRUM_PATTERN_LABEL];
        let width = labels.iter().map(|label| label.chars().count()).max().unwrap_or(0) + LABEL_ROOM;
        let mut lines = Vec::new();
        for (row, (label, value)) in labels.iter().zip(self.values()).enumerate() {
            let mut line = Text::plain(&format!("{}{label:<width$}", cursor_mark(row == self.row)));
            let style = if row == SCALE_LENGTH && self.drum {
                Style::DIM
            } else if row == self.row {
                Style::BOLD
            } else {
                Style::PLAIN
            };
            line.append(&value, style);
            lines.push(line);
        }
        lines.push(Text::default());
        let buttons: Vec<(String, String)> = labels::MSG_NEW_PATTERN_BUTTONS.iter().map(|label| (String::new(), label.to_string())).collect();
        let selected = (self.row == BUTTONS).then_some(self.button);
        lines.extend(crate::forms::drawing::button_row(&buttons, selected));
        lines
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl Page for NewPatternDialog {
    fn name(&self) -> &'static str {
        "NewPatternDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        let mut keys = vec![Self::bind(&Keys::CANCEL), Self::bind(&Keys::SELECT).wanting_key()];
        match self.row {
            SCALE_LENGTH => {
                if !self.drum {
                    keys.extend([Self::bind(&Keys::LESS), Self::bind(&Keys::MORE)]);
                }
                keys.push(Self::bind(&Keys::OK));
            }
            DRUM => keys.push(Self::bind(&Keys::TOGGLE)),
            _ => keys.extend([Self::bind(&Keys::CHOOSE_BUTTON).wanting_key(), Self::bind(&Keys::PRESS)]),
        }
        crate::keys::in_order(&Keys::CLASS, keys)
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::CANCEL) {
            app.go_back();
        } else if item.is(&Keys::SELECT) {
            let moved = if key == "up" { self.row as i64 - 1 } else { self.row as i64 + 1 };
            self.row = moved.clamp(0, ROWS as i64 - 1) as usize;
        } else if item.is(&Keys::CHOOSE_BUTTON) {
            let last = labels::MSG_NEW_PATTERN_BUTTONS.len() - 1;
            self.button = if key == "left" {
                self.button.saturating_sub(1)
            } else {
                (self.button + 1).min(last)
            };
        } else if item.is(&Keys::LESS) {
            self.step(-1);
        } else if item.is(&Keys::MORE) {
            self.step(1);
        } else if item.is(&Keys::TOGGLE) {
            self.drum = !self.drum;
        } else if item.is(&Keys::OK) {
            self.accept(app);
        } else if item.is(&Keys::PRESS) {
            if self.button == OK_BUTTON {
                self.accept(app);
            } else {
                app.go_back();
            }
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        dialog_box(messages::MSG_NEW_PATTERN_TITLE, false, &|_| self.lines(), &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}
