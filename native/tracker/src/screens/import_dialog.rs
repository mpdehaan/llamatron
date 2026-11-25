// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The import dialog and the dialog after an import (the Python dialogs/import_dialog.py and imported_dialog.py, and
//! screens/set/importing.py).
//!
//! The import dialog says what a MIDI file holds, dim, then the import's choices as fields, what the import would make and
//! its warnings, and Import and CANCEL. Up and Down move between the fields and the row of buttons; on a field [ and ] step
//! its value, Space or ENTER flips a toggle and ENTER renames the song; on the buttons Left and Right choose and ENTER
//! presses. Each change works the import out again, so that what it says is always for the choices shown; nothing is added
//! to the set until Import, which adds the song as one edit, makes it current, goes back to the main screen and says what
//! was made in a dialog with one OK button.

use std::cell::RefCell;
use std::rc::Rc;

use crate::app::App;
use crate::drawing::{cursor_mark, wrapped, Style};
use crate::keybindings::{ImportDialog as Keys, ImportedDialog as DoneKeys, KeyClass};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::screens::dialogs::{dialog_box, Answer, PromptDialog};
use crate::text::Text;
use llamatron_importers::import::{ImportChoices, Imported, MidiImport, LONGEST_PATTERN_CHOICES};
use llamatron_importers::writing::default_scale_name;
use llamatron_math::Rational;
use llamatron_strings::texts::importing;
use llamatron_strings::{marks, named};

/// The rows the cursor moves over: the fields in the order drawn, then the buttons.
const SONG_NAME: usize = 0;
const LONGEST: usize = 1;
const UNIQUE_NAMES: usize = 2;
const CHORDS: usize = 3;
const CONTROLS: usize = 4;
const STEP_SIZE: usize = 5;
const BUTTONS: usize = 6;
const LABELS: [&str; 6] = [
    importing::MSG_IMPORT_SONG_NAME,
    importing::MSG_IMPORT_LONGEST,
    importing::MSG_IMPORT_UNIQUE_NAMES,
    importing::MSG_IMPORT_CHORDS,
    importing::MSG_IMPORT_CONTROLS,
    importing::MSG_IMPORT_STEP_SIZE,
];
/// The room after the longest label.
const LABEL_GAP: usize = 2;
/// The buttons, in the order drawn.
const IMPORT_BUTTON: usize = 0;
/// How many keys the found line names before it counts the rest.
const KEYS_NAMED: usize = 2;
/// The step sizes the Step size field steps through, as numerators and denominators, after auto.
const STEP_SIZES: [(i128, i128); 4] = [(1, 32), (1, 16), (1, 8), (1, 4)];

/// The step sizes the Step size field offers, auto (None) first.
fn step_sizes() -> Vec<Option<Rational>> {
    std::iter::once(None)
        .chain(STEP_SIZES.iter().map(|(numerator, denominator)| Some(Rational::new(*numerator, *denominator))))
        .collect()
}

/// An exact length as a file holds it: a whole number, or text like 1/16.
fn fraction_text(value: Rational) -> String {
    if value.denominator() == 1 {
        value.numerator().to_string()
    } else {
        format!("{}/{}", value.numerator(), value.denominator())
    }
}

/// Asks how to import one MIDI file, and adds what the import made to the set on Import.
pub struct ImportDialog {
    import: Rc<MidiImport>,
    choices: ImportChoices,
    row: usize,
    button: usize,
    /// What the import makes for each set of choices tried, worked out once each.
    cached: RefCell<Vec<(ImportChoices, Rc<Imported>)>>,
}

impl ImportDialog {
    /// The dialog on a file read for importing, the song named after the file, or a copy's name where the set has that song.
    pub fn new(app: &App, import: MidiImport, song_name: &str) -> ImportDialog {
        let taken: Vec<&str> = app.document.get_setlist().song_names();
        let name = if taken.contains(&song_name) {
            llamatron_model::objects::naming::copy_name(song_name, &taken)
        } else {
            song_name.to_string()
        };
        ImportDialog {
            import: Rc::new(import),
            choices: ImportChoices::named(&name),
            row: SONG_NAME,
            button: IMPORT_BUTTON,
            cached: RefCell::new(Vec::new()),
        }
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }

    /// What the import makes with the choices as they are now, worked out once for each set of choices.
    fn made(&self, app: &App) -> Rc<Imported> {
        if let Some((_, made)) = self.cached.borrow().iter().find(|(choices, _)| *choices == self.choices) {
            return made.clone();
        }
        let made = Rc::new(self.import.imported(app.document.get_setlist(), &self.choices));
        self.cached.borrow_mut().push((self.choices.clone(), made.clone()));
        made
    }

    /// Step the Longest pattern or the Step size field through its choices, stopping at either end.
    fn step(&mut self, direction: i64) {
        if self.row == LONGEST {
            let place = LONGEST_PATTERN_CHOICES
                .iter()
                .position(|steps| *steps == self.choices.longest_pattern)
                .unwrap_or(0) as i64;
            let moved = (place + direction).clamp(0, LONGEST_PATTERN_CHOICES.len() as i64 - 1) as usize;
            self.choices.longest_pattern = LONGEST_PATTERN_CHOICES[moved];
        } else {
            let sizes = step_sizes();
            let place = sizes.iter().position(|size| *size == self.choices.step_size).unwrap_or(0) as i64;
            let moved = (place + direction).clamp(0, sizes.len() as i64 - 1) as usize;
            self.choices.step_size = sizes[moved];
        }
    }

    /// Flip the toggle under the cursor.
    fn toggle(&mut self) {
        match self.row {
            UNIQUE_NAMES => self.choices.unique_names = !self.choices.unique_names,
            CONTROLS => self.choices.controls = !self.choices.controls,
            _ => self.choices.chords = !self.choices.chords,
        }
    }

    /// Each field's value as shown.
    fn values(&self, app: &App) -> Vec<String> {
        let made = self.made(app);
        let choices = &self.choices;
        let toggle = |on: bool| if on { marks::MSG_TOGGLE_ON.to_string() } else { String::new() };
        let chords = if choices.chords {
            importing::MSG_IMPORT_AS_CHORDS
        } else {
            importing::MSG_IMPORT_AS_TRACKS
        };
        let step = match choices.step_size {
            None => named(importing::MSG_IMPORT_AUTO_STEP, &[("size", fraction_text(made.step_size).as_str().into())]),
            Some(size) => fraction_text(size),
        };
        vec![
            made.song.name.clone(),
            named(importing::MSG_IMPORT_STEPS, &[("count", choices.longest_pattern.into())]),
            toggle(choices.unique_names),
            chords.to_string(),
            toggle(choices.controls),
            step,
        ]
    }

    /// The line of what the file holds, each key named once, in the order first heard.
    fn found_text(&self) -> String {
        let found = self.import.found();
        let mut names: Vec<String> = Vec::new();
        for key in &found.keys {
            let name = default_scale_name(key);
            if !names.contains(&name) {
                names.push(name);
            }
        }
        let keys = if names.len() <= KEYS_NAMED {
            names.join(importing::MSG_IMPORT_KEYS_JOIN)
        } else {
            named(
                importing::MSG_IMPORT_MORE_KEYS,
                &[("first", names[0].as_str().into()), ("count", (names.len() - 1).into())],
            )
        };
        let signature = found.time_signature.unwrap_or_else(|| "None".to_string());
        named(
            importing::MSG_IMPORT_FOUND,
            &[
                ("tracks", found.tracks.into()),
                ("bars", found.bars.into()),
                ("time_signature", signature.as_str().into()),
                ("tempo", found.tempo.python_str().as_str().into()),
                ("keys", keys.as_str().into()),
            ],
        )
    }

    /// The line of what the import makes.
    fn makes_text(&self, made: &Imported) -> String {
        if made.long_patterns != 0 {
            return named(
                importing::MSG_IMPORT_MAKES_LONG,
                &[
                    ("tracks", made.tracks.into()),
                    ("patterns", made.patterns.into()),
                    ("long", made.long_patterns.into()),
                    ("longest", self.choices.longest_pattern.into()),
                    ("scenes", made.scenes.into()),
                ],
            );
        }
        named(
            importing::MSG_IMPORT_MAKES,
            &[
                ("tracks", made.tracks.into()),
                ("patterns", made.patterns.into()),
                ("scenes", made.scenes.into()),
            ],
        )
    }

    /// What the file holds, dim, the choices, what the import makes and its warnings, and the Import and CANCEL buttons.
    fn lines(&self, app: &App, width: usize) -> Vec<Text> {
        let dim = |text: &str| -> Vec<Text> { wrapped(text, width).iter().map(|line| Text::styled(&line.text(), Style::DIM)).collect() };
        let mut lines = dim(&self.found_text());
        lines.push(Text::default());
        let label_width = LABELS.iter().map(|label| label.chars().count()).max().unwrap_or(0) + LABEL_GAP;
        for (row, (label, value)) in LABELS.iter().zip(self.values(app)).enumerate() {
            let under = row == self.row;
            let mut line = Text::plain(&format!("{}{label:<label_width$}", cursor_mark(under)));
            line.append(&value, if under { Style::BOLD } else { Style::PLAIN });
            lines.push(line);
        }
        let made = self.made(app);
        lines.push(Text::default());
        lines.extend(wrapped(&self.makes_text(&made), width));
        if made.song.shared != 0 {
            lines.extend(dim(&named(importing::MSG_IMPORT_SHARED, &[("count", made.song.shared.into())])));
        }
        for warning in &made.warnings {
            lines.extend(dim(warning));
        }
        lines.push(Text::default());
        let selected = if self.row == BUTTONS { Some(self.button) } else { None };
        let buttons: Vec<(String, String)> = importing::MSG_IMPORT_BUTTONS.iter().map(|label| (String::new(), label.to_string())).collect();
        lines.extend(crate::forms::drawing::button_row(&buttons, selected));
        lines
    }

    /// Add what the import made to the set, make the song current, go back to the main screen, and say what was made and
    /// what had to change, on the status line and in a dialog with one OK button.
    fn import_now(&self, app: &mut App) {
        let made = self.made(app);
        app.go_back();
        if let Err(problem) = app.document.import_song(&made.song) {
            app.refuse(&problem);
            return;
        }
        app.go_back();
        let said = named(
            importing::MSG_IMPORTED,
            &[
                ("name", made.song.name.as_str().into()),
                ("tracks", made.tracks.into()),
                ("patterns", made.patterns.into()),
                ("scenes", made.scenes.into()),
            ],
        );
        app.say(&said);
        app.show_page(Box::new(ImportedDialog::new(&made)));
    }
}

impl Page for ImportDialog {
    fn name(&self) -> &'static str {
        "ImportDialog"
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
            SONG_NAME => keys.push(Self::bind(&Keys::RENAME)),
            LONGEST | STEP_SIZE => keys.extend([Self::bind(&Keys::LESS), Self::bind(&Keys::MORE)]),
            UNIQUE_NAMES | CHORDS | CONTROLS => keys.push(Self::bind(&Keys::TOGGLE)),
            _ => keys.extend([Self::bind(&Keys::CHOOSE_BUTTON).wanting_key(), Self::bind(&Keys::PRESS)]),
        }
        crate::keys::in_order(&Keys::CLASS, keys)
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if item.is(&Keys::CANCEL) {
            app.go_back();
        } else if item.is(&Keys::SELECT) {
            self.row = if key == "up" {
                self.row.saturating_sub(1)
            } else {
                (self.row + 1).min(BUTTONS)
            };
        } else if item.is(&Keys::CHOOSE_BUTTON) {
            let last = importing::MSG_IMPORT_BUTTONS.len() - 1;
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
            self.toggle();
        } else if item.is(&Keys::RENAME) {
            let mut prompt = PromptDialog::new(importing::MSG_IMPORT_SONG_PROMPT, &self.choices.song_name);
            prompt.max_length = Some(llamatron_model::schema::generated::limits::MAX_NAME_LENGTH as usize);
            app.show_page(Box::new(prompt));
        } else if item.is(&Keys::PRESS) {
            if self.button == IMPORT_BUTTON {
                self.import_now(app);
            } else {
                app.go_back();
            }
        }
    }

    fn answered(&mut self, _app: &mut App, answer: Answer) {
        // The song's name, typed; an empty answer keeps the old one.
        if let Answer::Typed(text) = answer {
            if !text.trim().is_empty() {
                self.choices.song_name = text.trim().to_string();
            }
        }
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let keys = self.keys(app);
        dialog_box(importing::MSG_IMPORT_TITLE, false, &|inner| self.lines(app, inner), &keys, width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}

/// The dialog after an import: what the song was imported as and holds, and every warning, with one OK button.
pub struct ImportedDialog {
    messages: Vec<String>,
    warnings: Vec<String>,
}

impl ImportedDialog {
    /// The dialog saying what an import made.
    pub fn new(made: &Imported) -> ImportedDialog {
        let mut messages = vec![named(
            importing::MSG_IMPORTED_SONG,
            &[
                ("name", made.song.name.as_str().into()),
                ("tracks", made.tracks.into()),
                ("patterns", made.patterns.into()),
                ("scenes", made.scenes.into()),
            ],
        )];
        if !made.warnings.is_empty() {
            messages.push(importing::MSG_IMPORTED_WARNINGS.to_string());
        }
        ImportedDialog {
            messages,
            warnings: made.warnings.clone(),
        }
    }
}

impl Page for ImportedDialog {
    fn name(&self) -> &'static str {
        "ImportedDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn shows_legend(&self) -> bool {
        false
    }

    fn class(&self) -> &'static KeyClass {
        &DoneKeys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![KeyItem::of(&DoneKeys::CLASS, &DoneKeys::CLOSE)]
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, _key: &str) {
        if item.is(&DoneKeys::CLOSE) {
            app.go_back();
        }
    }

    fn dialog_lines(&self, _app: &App, width: usize) -> Vec<Text> {
        let lines = |inner: usize| {
            let mut lines: Vec<Text> = self.messages.iter().flat_map(|message| wrapped(message, inner)).collect();
            for warning in &self.warnings {
                lines.push(Text::default());
                lines.extend(wrapped(warning, inner));
            }
            lines.push(Text::default());
            let button = vec![(String::new(), importing::MSG_IMPORTED_BUTTON.to_string())];
            lines.extend(crate::forms::drawing::button_row(&button, Some(0)));
            lines
        };
        dialog_box(importing::MSG_IMPORTED_TITLE, false, &lines, &[], width)
    }

    fn body(&self, _app: &App, _width: usize, _height: usize) -> Vec<Text> {
        Vec::new()
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        Vec::new()
    }
}
