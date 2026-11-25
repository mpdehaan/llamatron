// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The dialog that picks a step's keyswitches (the Python dialogs/keyswitch_dialog.py and pick_many_dialog.py): the
//! instrument's ten slots, numbered from 0, each on or off. Up and Down move, Space turns the slot under the cursor on or
//! off, and a digit turns its own slot on or off wherever the cursor is. ENTER is OK, answering with the slots picked, and
//! ESC is CANCEL, changing nothing; the two are drawn as buttons. Each slot shows the name and the note its instrument
//! gives it, where the instrument is known for certain, and a line above the slots names the instrument or says why none
//! is named. A slot with no note can still be picked: it plays nothing until the instrument gives it one.

use crate::app::App;
use crate::drawing::{cursor_mark, fit, Style};
use crate::keybindings::{KeyClass, KeyswitchDialog as Keys};
use crate::keys::KeyItem;
use crate::keyswitches::KEYSWITCH_NOTE_WIDTH;
use crate::page::Page;
use crate::screens::dialogs::dialog_box;
use crate::text::Text;
use llamatron_strings::{labels, marks, named};

/// The OK button, the one ENTER presses, so the one drawn selected.
const OK: usize = 0;

/// What takes the slots picked, in order, an empty list for none.
pub type SlotsChosen = dyn Fn(&mut App, Vec<usize>);

/// Answers with the slots picked, or nothing when cancelled.
pub struct KeyswitchDialog {
    title: String,
    /// The line over the slots: the instrument's name, or why none is named.
    said: String,
    names: Vec<String>,
    /// Each slot's note as text, nothing where it has none.
    notes: Vec<String>,
    picked: Vec<usize>,
    cursor: usize,
    then: Box<SlotsChosen>,
}

impl KeyswitchDialog {
    pub fn new(title: &str, said: &str, names: Vec<String>, notes: Vec<String>, picked: Vec<usize>, then: Box<SlotsChosen>) -> KeyswitchDialog {
        KeyswitchDialog {
            title: title.to_string(),
            said: said.to_string(),
            names,
            notes,
            picked,
            cursor: 0,
            then,
        }
    }

    /// Turn a slot on or off.
    fn flip(&mut self, slot: usize) {
        match self.picked.iter().position(|each| *each == slot) {
            Some(place) => {
                self.picked.remove(place);
            }
            None => self.picked.push(slot),
        }
    }

    /// One slot's line: its cursor's mark, its number and whether it is on, bold when picked; its name, dim where it has no
    /// note and is not picked; and its note, dim.
    fn slot_line(&self, slot: usize, width: usize) -> Text {
        let picked = self.picked.contains(&slot);
        let toggle = if picked { marks::MSG_TOGGLE_ON } else { marks::MSG_FIELD_TOGGLE_OFF };
        let start = format!(
            "{}{}",
            cursor_mark(slot == self.cursor),
            named(marks::MSG_KEYSWITCH_SLOT_ROW, &[("slot", slot.into()), ("toggle", toggle.into())])
        );
        let room = width.saturating_sub(start.chars().count() + KEYSWITCH_NOTE_WIDTH);
        let name = fit(&self.names[slot], room);
        let mut line = Text::default();
        line.append(&start, if picked { Style::BOLD } else { Style::PLAIN });
        line.append(&name, if self.notes[slot].is_empty() && !picked { Style::DIM } else { Style::PLAIN });
        line.append(&fit(&self.notes[slot], KEYSWITCH_NOTE_WIDTH), Style::DIM);
        line
    }

    fn lines(&self, width: usize) -> Vec<Text> {
        let mut lines = vec![Text::styled(&fit(&self.said, width), Style::DIM), Text::default()];
        lines.extend((0..self.names.len()).map(|slot| self.slot_line(slot, width)));
        lines.push(Text::default());
        let buttons: Vec<(String, String)> = labels::MSG_OK_CANCEL_BUTTONS.iter().map(|label| (String::new(), label.to_string())).collect();
        lines.extend(crate::forms::drawing::button_row(&buttons, Some(OK)));
        lines
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl Page for KeyswitchDialog {
    fn name(&self) -> &'static str {
        "KeyswitchDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![
            Self::bind(&Keys::CANCEL),
            Self::bind(&Keys::MOVE).wanting_key(),
            Self::bind(&Keys::FLIP),
            Self::bind(&Keys::DONE),
            Self::bind(&Keys::TOGGLE_SLOT).wanting_key(),
        ]
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::CANCEL) {
            app.go_back();
        } else if item.is(&Keys::MOVE) {
            let last = self.names.len().saturating_sub(1);
            self.cursor = if key == "up" {
                self.cursor.saturating_sub(1)
            } else {
                (self.cursor + 1).min(last)
            };
        } else if item.is(&Keys::FLIP) {
            self.flip(self.cursor);
        } else if item.is(&Keys::TOGGLE_SLOT) {
            if let Ok(slot) = key.parse::<usize>() {
                self.cursor = slot.min(self.names.len().saturating_sub(1));
                self.flip(self.cursor);
            }
        } else if item.is(&Keys::DONE) {
            app.go_back();
            let mut picked = self.picked.clone();
            picked.sort_unstable();
            (self.then)(app, picked);
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        // The keys are listed as the dialog binds them, the slot's digits last.
        let keys = self.keys(app);
        dialog_box(&self.title, false, &|inner| self.lines(inner), &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}
