// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An instrument's Keyswitch Map (the Python dialogs/keyswitch_map_dialog.py): ten slots, numbered from 0, each with a name
//! and the note that switches it. Up and Down move through the slots and down to the OK and CANCEL buttons. On a slot, N
//! names it, Bksp empties it, and ENTER opens the note picker, drawn over the map two cells down and to the right as every
//! flyout is: one octave of keys, with the octave picked apart from the key. The picker opens on the slot's note, or, for a
//! slot with none, a half step above the map's highest note, or on the lowest C for an empty map. Nothing changes in the
//! set until OK.

use crate::app::App;
use crate::components::keyboard::{keyboard_lines, one_octave_rows, KeyKind};
use crate::drawing::{cursor_mark, fit, legend, Style};
use crate::keybindings::{KeyClass, KeyswitchMapDialog as Keys};
use crate::keys::KeyItem;
use crate::keyswitches::{Keyswitch, KEYSWITCH_NOTE_WIDTH};
use crate::page::Page;
use crate::screens::dialogs::{box_lines, heading_lines, sized_contents, stacked, Answer, PromptDialog, DIALOG_MARGIN, FLYOUT_SHIFT};
use crate::text::Text;
use llamatron_model::schema::generated::limits::MAX_NAME_LENGTH;
use llamatron_model::schema::generated::midi::{MAX_MIDI_NUMBER, MIN_MIDI_NUMBER};
use llamatron_names::fill;
use llamatron_strings::{labels, marks, messages, named};
use std::cell::RefCell;
use std::rc::Rc;

/// How many semitones make an octave, which Up and Down move the key picked by.
const SEMITONES_AN_OCTAVE: i64 = 12;

/// The place of the row of buttons, under the last slot, and the buttons' places in MSG_OK_CANCEL_BUTTONS.
const SLOT_COUNT: usize = 10;
const BUTTONS_PLACE: usize = SLOT_COUNT;
const OK: usize = 0;
/// Where the cursor is along a slot's row: on the name, where ENTER renames, or on the note, where ENTER picks it.
const NAME_CELL: usize = 0;
const NOTE_CELL: usize = 1;

/// What takes the ten slots, in order, on OK.
pub type SlotsMapped = dyn Fn(&mut App, Vec<Keyswitch>);

/// Answers with the ten slots on OK, or nothing when cancelled.
pub struct KeyswitchMapDialog {
    title: String,
    /// The slots as they are being changed, shared with the prompt that names one.
    keyswitches: Rc<RefCell<Vec<Keyswitch>>>,
    cursor: usize,
    cell: usize,
    button: usize,
    /// The note the picker is on while it is open, and None while it is closed.
    picking: Option<i64>,
    then: Box<SlotsMapped>,
}

/// The note the picker opens on for a slot with none: a half step above the map's highest note, or the lowest C for an
/// empty map.
fn first_note_offered(keyswitches: &[Keyswitch]) -> i64 {
    match keyswitches.iter().filter_map(|keyswitch| keyswitch.note).max() {
        Some(highest) => (highest + 1).min(MAX_MIDI_NUMBER),
        None => MIN_MIDI_NUMBER,
    }
}

impl KeyswitchMapDialog {
    pub fn new(title: &str, keyswitches: Vec<Keyswitch>, then: Box<SlotsMapped>) -> KeyswitchMapDialog {
        KeyswitchMapDialog {
            title: title.to_string(),
            keyswitches: Rc::new(RefCell::new(keyswitches)),
            cursor: 0,
            cell: NAME_CELL,
            button: OK,
            picking: None,
            then,
        }
    }

    fn on_buttons(&self) -> bool {
        self.cursor == BUTTONS_PLACE
    }

    fn current(&self) -> Keyswitch {
        self.keyswitches.borrow()[self.cursor].clone()
    }

    /// Ask for the slot's name over the map, an empty answer leaving the slot without one.
    fn rename(&self, app: &mut App) {
        let place = self.cursor;
        let title = named(messages::MSG_KEYSWITCH_NAME_PROMPT, &[(fill::SLOT, place.into())]);
        let mut prompt = PromptDialog::new(&title, &self.current().name.unwrap_or_default());
        prompt.max_length = Some(MAX_NAME_LENGTH as usize);
        let keyswitches = self.keyswitches.clone();
        let prompt = prompt.then(Box::new(move |_: &mut App, answer: &Answer| {
            if let Answer::Typed(text) = answer {
                let text = text.trim();
                keyswitches.borrow_mut()[place].name = (!text.is_empty()).then(|| text.to_string());
            }
        }));
        app.show_page(Box::new(prompt));
    }

    /// A note as the map writes it, (none) for none.
    fn note_text(app: &App, note: Option<i64>) -> String {
        note.map_or(marks::MSG_NONE_SHOWN.to_string(), |note| crate::keyswitches::note_text(app, note))
    }

    /// One slot's line: its number, the name's cursor mark and name, dim where it has none, then the note's cursor mark
    /// and note, dim where it has none, and the picker's mark, each kept in its place so that nothing shifts.
    fn slot_line(&self, app: &App, slot: usize, width: usize) -> Text {
        let keyswitch = self.keyswitches.borrow()[slot].clone();
        let here = slot == self.cursor;
        let start = named(marks::MSG_KEYSWITCH_MAP_ROW, &[(fill::SLOT, slot.into())]);
        let (name_mark, note_mark) = (cursor_mark(here && self.cell == NAME_CELL), cursor_mark(here && self.cell == NOTE_CELL));
        let room = width.saturating_sub(start.chars().count() + name_mark.chars().count() + note_mark.chars().count() + KEYSWITCH_NOTE_WIDTH);
        let shown_name = keyswitch.name.clone().unwrap_or_else(|| marks::MSG_NONE_SHOWN.to_string());
        let note_cell = named(
            marks::MSG_KEYSWITCH_NOTE_CELL,
            &[(fill::NOTE, Self::note_text(app, keyswitch.note).as_str().into())],
        );
        let note = fit(&note_cell, KEYSWITCH_NOTE_WIDTH - marks::MSG_PICKER_MARK.chars().count());
        let mut line = Text::default();
        line.append(&format!("{start}{name_mark}"), Style::PLAIN);
        line.append(&fit(&shown_name, room), if keyswitch.name.is_none() { Style::DIM } else { Style::PLAIN });
        line.append(note_mark, Style::PLAIN);
        line.append(&note, if keyswitch.note.is_none() { Style::DIM } else { Style::PLAIN });
        line.append(marks::MSG_PICKER_MARK, Style::DIM);
        line
    }

    /// The headings over the slots' two cells, each over the place its cell starts.
    fn heading_line(width: usize) -> Text {
        let mark = cursor_mark(false);
        let gap = named(marks::MSG_KEYSWITCH_MAP_ROW, &[(fill::SLOT, 0.into())]).chars().count() + mark.chars().count();
        let room = width.saturating_sub(gap + mark.chars().count() + KEYSWITCH_NOTE_WIDTH);
        let mut line = Text::default();
        line.append(&" ".repeat(gap), Style::PLAIN);
        line.append(
            &format!(
                "{}{}{}",
                fit(labels::Column::NAME, room),
                " ".repeat(mark.chars().count()),
                labels::Column::NOTE
            ),
            Style::DIM,
        );
        line
    }

    fn lines(&self, app: &App, width: usize) -> Vec<Text> {
        let mut lines = vec![Self::heading_line(width)];
        lines.extend((0..SLOT_COUNT).map(|slot| self.slot_line(app, slot, width)));
        lines.push(Text::default());
        let buttons: Vec<(String, String)> = labels::MSG_OK_CANCEL_BUTTONS.iter().map(|label| (String::new(), label.to_string())).collect();
        lines.extend(crate::forms::drawing::button_row(&buttons, self.on_buttons().then_some(self.button)));
        lines
    }

    /// The note picker's lines while it is open: the slot, one octave of keys with the key picked filled and named, the
    /// note and its octave, and the picker's keys.
    fn flyout_lines(&self, app: &App, width: usize) -> Option<Vec<Text>> {
        let picking = self.picking?;
        let keyswitch = self.current();
        let title = match &keyswitch.name {
            None => named(messages::MSG_KEYSWITCH_NOTE_TITLE, &[(fill::SLOT, self.cursor.into())]),
            Some(name) => named(
                messages::MSG_KEYSWITCH_NOTE_NAMED_TITLE,
                &[(fill::SLOT, self.cursor.into()), (fill::NAME, name.as_str().into())],
            ),
        };
        let style_of = |kind: Option<KeyKind>| match kind {
            Some(KeyKind::Chord) => Style::CHORD_KEY,
            Some(KeyKind::Outside) => Style::DIM,
            _ => Style::PLAIN,
        };
        let octave = crate::settings::shown_octave(app.document.get_setlist(), picking.div_euclid(12));
        let mut lines = vec![Text::styled(&title, Style::BOLD), Text::default()];
        lines.extend(keyboard_lines(&one_octave_rows(picking.rem_euclid(12)), &style_of));
        lines.push(Text::default());
        lines.push(Text::plain(&named(
            messages::MSG_KEYSWITCH_PICKED_NOTE,
            &[(fill::NOTE, Self::note_text(app, Some(picking)).as_str().into())],
        )));
        lines.push(Text::plain(&named(messages::MSG_KEYSWITCH_PICKED_OCTAVE, &[(fill::OCTAVE, octave.into())])));
        lines.push(Text::default());
        lines.extend(legend(&self.keys(app), width));
        Some(lines)
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl Page for KeyswitchMapDialog {
    fn name(&self) -> &'static str {
        "KeyswitchMapDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        if self.picking.is_some() {
            return vec![
                Self::bind(&Keys::CLOSE_PICKER),
                Self::bind(&Keys::PICK_NOTE).wanting_key(),
                Self::bind(&Keys::PICK_OCTAVE).wanting_key(),
                Self::bind(&Keys::TAKE_NOTE),
            ];
        }
        let mut keys = vec![Self::bind(&Keys::CANCEL), Self::bind(&Keys::MOVE).wanting_key()];
        if self.on_buttons() {
            keys.extend([Self::bind(&Keys::ALONG_BUTTONS).wanting_key(), Self::bind(&Keys::PRESS)]);
            return keys;
        }
        keys.push(Self::bind(if self.cell == NAME_CELL { &Keys::TO_NOTE } else { &Keys::TO_NAME }));
        keys.extend([Self::bind(&Keys::RENAME), Self::bind(&Keys::NOTE), Self::bind(&Keys::CLEAR)]);
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if let Some(picking) = self.picking {
            if item.is(&Keys::CLOSE_PICKER) {
                self.picking = None;
            } else if item.is(&Keys::PICK_NOTE) {
                // A key moves along within the octave shown, since the octave is picked apart from the key.
                let within = picking.rem_euclid(12);
                let moved = if key == llamatron_names::keys::LEFT {
                    (within - 1).max(0)
                } else {
                    (within + 1).min(SEMITONES_AN_OCTAVE - 1)
                };
                self.picking = Some((picking - within + moved).min(MAX_MIDI_NUMBER));
            } else if item.is(&Keys::PICK_OCTAVE) {
                let moved = picking
                    + if key == llamatron_names::keys::UP {
                        SEMITONES_AN_OCTAVE
                    } else {
                        -SEMITONES_AN_OCTAVE
                    };
                if (MIN_MIDI_NUMBER..=MAX_MIDI_NUMBER).contains(&moved) {
                    self.picking = Some(moved);
                }
            } else if item.is(&Keys::TAKE_NOTE) {
                self.keyswitches.borrow_mut()[self.cursor].note = Some(picking);
                self.picking = None;
            }
            return;
        }
        if item.is(&Keys::CANCEL) {
            app.go_back();
        } else if item.is(&Keys::MOVE) {
            self.cursor = if key == llamatron_names::keys::UP {
                self.cursor.saturating_sub(1)
            } else {
                (self.cursor + 1).min(BUTTONS_PLACE)
            };
        } else if item.is(&Keys::ALONG_BUTTONS) {
            let last = labels::MSG_OK_CANCEL_BUTTONS.len() - 1;
            self.button = if key == llamatron_names::keys::LEFT {
                self.button.saturating_sub(1)
            } else {
                (self.button + 1).min(last)
            };
        } else if item.is(&Keys::PRESS) {
            app.go_back();
            if self.button == OK {
                let keyswitches = self.keyswitches.borrow().clone();
                (self.then)(app, keyswitches);
            }
        } else if item.is(&Keys::TO_NOTE) {
            self.cell = NOTE_CELL;
        } else if item.is(&Keys::TO_NAME) {
            self.cell = NAME_CELL;
        } else if item.is(&Keys::RENAME) {
            self.rename(app);
        } else if item.is(&Keys::NOTE) {
            let note = self.current().note;
            self.picking = Some(note.unwrap_or_else(|| first_note_offered(&self.keyswitches.borrow())));
        } else if item.is(&Keys::CLEAR) {
            self.keyswitches.borrow_mut()[self.cursor] = Keyswitch::default();
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = crate::keys::in_order(self.class(), self.keys(app));
        let title = self.title.clone();
        let (held, width_of_box) = sized_contents(&|inner| heading_lines(&title, false, inner), &|inner| self.lines(app, inner), &keys, width);
        let boxed = box_lines(&held, width_of_box);
        let Some(mut over) = self.flyout_lines(app, width_of_box - DIALOG_MARGIN) else {
            return boxed;
        };
        over.resize(held.len(), Text::default());
        stacked(&boxed, &box_lines(&over, width_of_box))
    }

    fn dialog_shift(&self) -> usize {
        if self.picking.is_some() {
            FLYOUT_SHIFT
        } else {
            0
        }
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}
