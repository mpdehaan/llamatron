// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The set's notes (the Python screens/set/notes_page.py): read, or written while editing, as a draft of the page's own that
//! Save stores in the set as one edit and CANCEL throws away.

use crate::app::App;
use crate::drawing::{cursor_mark, padded, wrapped, Style, INDENT};
use crate::keybindings::{KeyClass, NotesPage as Keys};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::SetlistSetting;
use llamatron_strings::{labels, marks, messages};
use std::cell::Cell;

/// The two buttons' places, in the order they stand.
const SAVE: usize = 0;
/// The blank line and the row of buttons under the text while editing.
const BUTTON_LINES: usize = 2;

pub struct NotesPage {
    /// The lines being typed, until Save stores them, while editing.
    draft: Option<Vec<String>>,
    on_buttons: bool,
    button: usize,
    row: usize,
    column: usize,
    top: Cell<usize>,
}

fn stored_text(app: &App) -> String {
    app.document
        .get_setlist()
        .get_written(SetlistSetting::NOTES)
        .and_then(Data::as_str)
        .unwrap_or("")
        .to_string()
}

fn stored_lines(app: &App) -> Vec<String> {
    let text = stored_text(app);
    let mut lines: Vec<String> = text.split('\n').map(str::to_string).collect();
    if text.ends_with('\n') {
        lines.pop();
    }
    if lines.is_empty() {
        lines.push(String::new());
    }
    lines
}

fn is_protected(app: &App) -> bool {
    matches!(app.document.get_setlist().get_written(SetlistSetting::PROTECTED), Some(Data::Bool(true)))
}

fn chars(line: &str) -> usize {
    line.chars().count()
}

fn slice(line: &str, start: usize, end: usize) -> String {
    line.chars().skip(start).take(end.saturating_sub(start)).collect()
}

impl NotesPage {
    /// The page, editing at once where it opens to edit and the set is not protected.
    pub fn new(app: &App, editing: bool) -> NotesPage {
        let mut page = NotesPage {
            draft: None,
            on_buttons: false,
            button: SAVE,
            row: 0,
            column: 0,
            top: Cell::new(0),
        };
        if editing && !is_protected(app) {
            page.start_editing(app);
        }
        page
    }

    fn start_editing(&mut self, app: &App) {
        let lines = stored_lines(app);
        self.on_buttons = false;
        self.button = SAVE;
        self.row = lines.len() - 1;
        self.column = chars(&lines[self.row]);
        self.draft = Some(lines);
    }

    fn stop_editing(&mut self, app: &mut App) {
        self.draft = None;
        self.on_buttons = false;
        app.status.clear();
    }

    fn store(&mut self, app: &mut App, lines: Vec<String>) {
        if self.draft.is_some() {
            self.draft = Some(lines);
            return;
        }
        let text = format!("{}\n", lines.join("\n"));
        app.document
            .change_set(|setlist| setlist.set_written(SetlistSetting::NOTES, Some(Data::Text(text))));
    }

    fn lines(&self, app: &App) -> Vec<String> {
        self.draft.clone().unwrap_or_else(|| stored_lines(app))
    }

    fn move_cursor(&mut self, app: &App, key: &str) {
        let lines = self.lines(app);
        match key {
            "up" | "down" => {
                let step: i64 = if key == "up" { -1 } else { 1 };
                self.row = (self.row as i64 + step).clamp(0, lines.len() as i64 - 1) as usize;
                self.column = self.column.min(chars(&lines[self.row]));
            }
            "left" => {
                if self.column > 0 {
                    self.column -= 1;
                } else if self.row > 0 {
                    self.row -= 1;
                    self.column = chars(&lines[self.row]);
                }
            }
            _ => {
                if self.column < chars(&lines[self.row]) {
                    self.column += 1;
                } else if self.row + 1 < lines.len() {
                    self.row += 1;
                    self.column = 0;
                }
            }
        }
    }

    fn new_line(&mut self, app: &mut App) {
        let mut lines = self.lines(app);
        let line = lines[self.row].clone();
        lines[self.row] = slice(&line, 0, self.column);
        lines.insert(self.row + 1, slice(&line, self.column, chars(&line)));
        self.store(app, lines);
        self.row += 1;
        self.column = 0;
    }

    fn erase(&mut self, app: &mut App) {
        let mut lines = self.lines(app);
        if self.column > 0 {
            let line = lines[self.row].clone();
            lines[self.row] = format!("{}{}", slice(&line, 0, self.column - 1), slice(&line, self.column, chars(&line)));
            self.column -= 1;
        } else if self.row > 0 {
            self.column = chars(&lines[self.row - 1]);
            let joined = format!("{}{}", lines[self.row - 1], lines[self.row]);
            lines.splice(self.row - 1..self.row + 1, [joined]);
            self.row -= 1;
        } else {
            return;
        }
        self.store(app, lines);
    }

    fn button_line(&self) -> Text {
        let mut line = Text::default();
        for (place, label) in labels::MSG_NOTES_BUTTONS.iter().enumerate() {
            let selected = self.on_buttons && place == self.button;
            line.append(cursor_mark(selected), Style::PLAIN);
            line.append(&padded(label), if selected { Style::REVERSE } else { Style::BOLD });
            line.append(marks::MSG_CONFIRM_BUTTON_GAP, Style::PLAIN);
        }
        line
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl Page for NotesPage {
    fn name(&self) -> &'static str {
        "NotesPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::FILE.to_string(), labels::Crumb::NOTES.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::SET_FILE)
    }

    fn keys(&self, app: &App) -> Vec<KeyItem> {
        if self.draft.is_some() && self.on_buttons {
            return vec![
                Self::bind(&Keys::CANCEL),
                Self::bind(&Keys::SELECT_BUTTON).wanting_key(),
                Self::bind(&Keys::PRESS_BUTTON),
                Self::bind(&Keys::TO_TEXT),
            ];
        }
        if self.draft.is_some() {
            return vec![
                Self::bind(&Keys::CANCEL),
                Self::bind(&Keys::MOVE).wanting_key(),
                Self::bind(&Keys::NEW_LINE),
                Self::bind(&Keys::ERASE),
                Self::bind(&Keys::TO_BUTTONS),
            ];
        }
        let mut keys = vec![Self::bind(&Keys::BACK), Self::bind(&Keys::SCROLL)];
        if !is_protected(app) {
            keys.push(Self::bind(&Keys::EDIT));
            keys.push(Self::bind(&Keys::CLEAR));
        }
        keys
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::BACK) {
            app.go_back();
        } else if item.is(&Keys::CANCEL) {
            self.stop_editing(app);
        } else if item.is(&Keys::SELECT_BUTTON) {
            let last = labels::MSG_NOTES_BUTTONS.len() - 1;
            self.button = if key == "left" {
                self.button.saturating_sub(1)
            } else {
                (self.button + 1).min(last)
            };
        } else if item.is(&Keys::PRESS_BUTTON) {
            if self.button == SAVE {
                let draft = self.draft.clone().unwrap_or_default();
                self.stop_editing(app);
                if draft != stored_lines(app) {
                    self.store(app, draft);
                }
            } else {
                self.stop_editing(app);
            }
        } else if item.is(&Keys::TO_TEXT) {
            self.on_buttons = false;
        } else if item.is(&Keys::TO_BUTTONS) {
            self.on_buttons = true;
        } else if item.is(&Keys::MOVE) {
            self.move_cursor(app, key);
        } else if item.is(&Keys::NEW_LINE) {
            self.new_line(app);
        } else if item.is(&Keys::ERASE) {
            self.erase(app);
        } else if item.is(&Keys::SCROLL) {
            let step = item.step_of(key).unwrap_or(0);
            self.top.set((self.top.get() as i64 + step).max(0) as usize);
        } else if item.is(&Keys::EDIT) {
            self.start_editing(app);
            app.say(messages::MSG_EDITING);
        } else if item.is(&Keys::CLEAR) && !stored_text(app).is_empty() {
            // Clearing asks first, in a dialog not ported yet.
        }
    }

    fn takes_text(&self) -> bool {
        self.draft.is_some() && !self.on_buttons
    }

    fn type_text(&mut self, app: &mut App, character: char) {
        let mut lines = self.lines(app);
        let line = lines[self.row].clone();
        lines[self.row] = format!("{}{character}{}", slice(&line, 0, self.column), slice(&line, self.column, chars(&line)));
        self.store(app, lines);
        self.column += 1;
    }

    fn body(&self, app: &App, width: usize, height: usize) -> Vec<Text> {
        let room = height.max(1);
        if let Some(lines) = &self.draft {
            let room = room.saturating_sub(BUTTON_LINES).max(1);
            let top = self.top.get().min(self.row).max((self.row + 1).saturating_sub(room));
            self.top.set(top);
            let mut shown = Vec::new();
            for (number, line) in lines.iter().enumerate().skip(top).take(room) {
                if number != self.row {
                    shown.push(Text::plain(&format!("{INDENT}{line}")));
                    continue;
                }
                let start = self.column.saturating_sub(width.saturating_sub(6));
                let mut text = Text::plain(&format!("{INDENT}{}", slice(line, start, self.column)));
                let under = slice(line, self.column, self.column + 1);
                text.append(if under.is_empty() { " " } else { &under }, Style::REVERSE);
                text.append(&slice(line, self.column + 1, chars(line)), Style::PLAIN);
                shown.push(text);
            }
            while shown.len() < room + 1 {
                shown.push(Text::default());
            }
            shown.push(self.button_line());
            return shown;
        }
        if stored_text(app).is_empty() {
            let note = if is_protected(app) {
                messages::MSG_NO_NOTES_PROTECTED
            } else {
                messages::MSG_NO_NOTES_NOTE
            };
            return vec![Text::styled(note, Style::DIM)];
        }
        let mut lines = Vec::new();
        for line in stored_lines(app) {
            let parts = wrapped(&line, width.saturating_sub(4));
            if parts.is_empty() {
                lines.push(Text::plain(INDENT));
            }
            for part in parts {
                let mut indented = Text::plain(INDENT);
                indented.append_text(&part);
                lines.push(indented);
            }
        }
        let top = self.top.get().min(lines.len().saturating_sub(room));
        self.top.set(top);
        lines.into_iter().skip(top).take(room).collect()
    }
}
