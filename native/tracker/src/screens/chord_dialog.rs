// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Chord dialog (the Python dialogs/chord_dialog.py): one chord's quality, inversion, tensions and borrowed scale as
//! lists side by side, with the notes doubled an octave away between the inversion and the tensions where a pattern's step
//! is chosen, and what the chord comes to said under them as the choice moves, its name in the scale it is drawn from and
//! its exact notes. Up and Down move in a list, Left, Right and Tab go from list to list, Space turns the tension under the
//! cursor on or off, ENTER answers and ESC cancels, changing nothing. The scale list holds categories of scale types: Space
//! or ENTER on a category opens its flyout, drawn over the dialog a little down and to the right, where Up and Down move,
//! ENTER picks one and closes it, and ESC or Left closes it with nothing changed; after a pick the cursor goes on to the
//! qualities, so that the next ENTER takes the chord.

use crate::app::App;
use crate::drawing::{cursor_mark, fit, legend, Style};
use crate::generated::tables::SCALE_CATEGORIES;
use crate::keybindings::{ChordDialog as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::page::Page;
use crate::screens::dialogs::{box_lines, heading_lines, stacked, DIALOG_MARGIN, FLYOUT_SHIFT};
use crate::text::Text;
use llamatron_model::schema::generated::file_format::TENSIONS;
use llamatron_strings::{labels, marks, messages, named};

/// The lists, left to right.
pub const QUALITY_LIST: usize = 0;
pub const INVERSION_LIST: usize = 1;
pub const DOUBLE_LIST: usize = 2;
pub const TENSION_LIST: usize = 3;
pub const SCALE_LIST: usize = 4;
/// How wide each list is drawn, by the list, and the gap between two.
const LIST_WIDTHS: [usize; 5] = [23, 8, 8, 8, 21];
const LIST_GAP: usize = 1;
/// The room for the sentences under the lists, so that the dialog keeps its height as the choice moves.
const SENTENCE_LINES: usize = 3;
/// The keyboard under the sentences: its lines, the blank line over it, and the box's top and bottom edges.
const KEYBOARD_LINES: usize = 3;
const KEYBOARD_GAP: usize = 1;
const DIALOG_BORDERS: usize = 2;
/// A width no legend reaches, for measuring one laid out on a single line.
const WIDEST: usize = 1000;
/// The fewest cells worth showing of a category's name beside the scale type borrowed.
const SHORTEST_CATEGORY_NAME: usize = 4;
/// The row of the scale list that borrows no scale, above the categories.
const NOT_BORROWED_ROW: usize = 0;
/// How many rows of a list show at once: enough for every category and for the longest flyout.
const SHOWN: usize = 10;

/// What the Chord dialog answers with: a chord symbol or None for a single note, an inversion or None for root position,
/// the tensions lowest first or None, a scale type borrowed or None, and what a pattern's step doubles or None.
#[derive(Clone, Debug, PartialEq)]
pub struct ChordChoice {
    pub quality: Option<String>,
    pub inversion: Option<i64>,
    pub tensions: Option<Vec<String>>,
    pub kind: Option<String>,
    pub doubling: Option<String>,
}

/// What the dialog says of a choice, and what draws a keyboard of it where the scale is known for certain.
pub type SaidOf = dyn Fn(&App, &ChordChoice) -> Vec<String>;
pub type KeyboardOf = dyn Fn(&App, &ChordChoice) -> Option<Vec<Text>>;
/// What takes a choice: the answer, or each choice as it moves.
pub type ChoiceTaken = dyn Fn(&mut App, &ChordChoice);

/// What the dialog offers, and what it does with the choice.
pub struct ChordOffer {
    pub title: String,
    pub qualities: Vec<Option<String>>,
    pub quality_names: Vec<String>,
    pub inversions: Vec<Option<i64>>,
    /// The values of a pattern's step's Double row, None first, or no list at all.
    pub doublings: Option<Vec<Option<String>>>,
    pub current: ChordChoice,
    pub opens_on: usize,
    pub said: Box<SaidOf>,
    pub keyboard: Option<Box<KeyboardOf>>,
    /// What shows the chord on the page underneath as the choice moves, and puts back the one it opened on on a cancel.
    pub moved: Option<Box<ChoiceTaken>>,
    pub then: Box<ChoiceTaken>,
}

/// Answers with a ChordChoice, or nothing when cancelled.
pub struct ChordDialog {
    offer: ChordOffer,
    doublings: Vec<Option<String>>,
    parts: Vec<usize>,
    picked: Vec<String>,
    kind: Option<String>,
    part: usize,
    places: [usize; 5],
    /// The category whose flyout is open, by its row, and the cursor's place in it.
    flyout: Option<usize>,
    flyout_place: usize,
    /// The choice the page underneath was last shown, and whether a move has been shown yet.
    shown: ChordChoice,
    moved_once: bool,
}

/// The scale list's row a scale type is found under: the first category holding it, or the row that borrows none.
fn row_of_kind(kind: Option<&str>) -> usize {
    let Some(kind) = kind else { return NOT_BORROWED_ROW };
    SCALE_CATEGORIES
        .iter()
        .position(|(_, kinds)| kinds.contains(&kind))
        .map_or(NOT_BORROWED_ROW, |row| row + 1)
}

/// A scale type's name in words, such as Harmonic Minor.
fn kind_words(kind: &str) -> String {
    crate::chord_text::python_title(&kind.replace('_', " "))
}

/// Lines made up to a height with blank ones.
fn filled(mut lines: Vec<Text>, height: usize) -> Vec<Text> {
    while lines.len() < height {
        lines.push(Text::default());
    }
    lines
}

impl ChordDialog {
    pub fn new(offer: ChordOffer) -> ChordDialog {
        let doublings = offer.doublings.clone().unwrap_or_else(|| vec![None]);
        let mut parts = vec![QUALITY_LIST, INVERSION_LIST];
        if offer.doublings.is_some() {
            parts.push(DOUBLE_LIST);
        }
        parts.extend([TENSION_LIST, SCALE_LIST]);
        let current = offer.current.clone();
        let place_of = |found: Option<usize>| found.unwrap_or(0);
        let places = [
            place_of(offer.qualities.iter().position(|quality| *quality == current.quality)),
            place_of(offer.inversions.iter().position(|inversion| *inversion == current.inversion)),
            place_of(doublings.iter().position(|doubling| *doubling == current.doubling)),
            0,
            row_of_kind(current.kind.as_deref()),
        ];
        let part = offer.opens_on;
        ChordDialog {
            doublings,
            parts,
            picked: current.tensions.clone().unwrap_or_default(),
            kind: current.kind.clone(),
            part,
            places,
            flyout: None,
            flyout_place: 0,
            shown: current,
            moved_once: false,
            offer,
        }
    }

    fn kinds_of_row(row: usize) -> &'static [&'static str] {
        SCALE_CATEGORIES[row - 1].1
    }

    /// The scale type the sentences speak of: the one under the flyout's cursor while a flyout is open, and otherwise the
    /// one borrowed.
    fn shown_kind(&self) -> Option<String> {
        match self.flyout {
            Some(row) => Some(Self::kinds_of_row(row)[self.flyout_place].to_string()),
            None => self.kind.clone(),
        }
    }

    pub fn choice(&self) -> ChordChoice {
        let tensions: Vec<String> = TENSIONS
            .iter()
            .map(|(tension, _)| tension.to_string())
            .filter(|tension| self.picked.contains(tension))
            .collect();
        ChordChoice {
            quality: self.offer.qualities[self.places[QUALITY_LIST]].clone(),
            inversion: self.offer.inversions[self.places[INVERSION_LIST]],
            tensions: (!tensions.is_empty()).then_some(tensions),
            kind: self.shown_kind(),
            doubling: self.doublings[self.places[DOUBLE_LIST]].clone(),
        }
    }

    /// How many rows a list has.
    fn count(&self, part: usize) -> usize {
        match part {
            QUALITY_LIST => self.offer.qualities.len(),
            INVERSION_LIST => self.offer.inversions.len(),
            DOUBLE_LIST => self.doublings.len(),
            TENSION_LIST => TENSIONS.len(),
            _ => SCALE_CATEGORIES.len() + 1,
        }
    }

    /// The keys that work with the cursor in one of the lists.
    fn list_keys(&self, part: usize) -> Vec<KeyItem> {
        let mut keys = vec![Self::bind(&Keys::CANCEL), Self::bind(&Keys::MOVE).wanting_key(), Self::bind(&Keys::NEXT_LIST)];
        if part == SCALE_LIST {
            keys.push(Self::bind(&Keys::OPEN));
            return keys;
        }
        if part == TENSION_LIST {
            keys.push(Self::bind(&Keys::FLIP));
        }
        keys.push(Self::bind(&Keys::CHOOSE));
        keys
    }

    /// Tell the page underneath when the choice has moved, each move after the first continuing the same undo step.
    fn show_if_moved(&mut self, app: &mut App) {
        let now = self.choice();
        if now == self.shown {
            return;
        }
        if let Some(moved) = &self.offer.moved {
            if self.moved_once {
                app.document.continue_edit();
            }
            moved(app, &now);
            self.moved_once = true;
        }
        self.shown = now;
    }

    /// A row of the scale list: the row that borrows none, or a category drawn as a button, with the scale type borrowed
    /// after the name of the one that holds it.
    fn scale_row_text(&self, row: usize) -> String {
        if row == NOT_BORROWED_ROW {
            return messages::MSG_SCALE_NOT_BORROWED.to_string();
        }
        let (name, kinds) = SCALE_CATEGORIES[row - 1];
        if let Some(kind) = self.kind.as_deref().filter(|kind| kinds.contains(kind) && row == row_of_kind(Some(kind))) {
            let chosen = kind_words(kind);
            let bare = named(marks::MSG_FLYOUT_CHOSEN, &[("name", "".into()), ("chosen", chosen.as_str().into())]);
            let room = LIST_WIDTHS[SCALE_LIST].saturating_sub(cursor_mark(false).chars().count() + bare.chars().count());
            if room < SHORTEST_CATEGORY_NAME {
                return named(marks::MSG_FLYOUT_CHOSEN_ALONE, &[("chosen", chosen.as_str().into())]);
            }
            return named(
                marks::MSG_FLYOUT_CHOSEN,
                &[("name", fit(name, room).trim_end().into()), ("chosen", chosen.as_str().into())],
            );
        }
        named(marks::MSG_FLYOUT_CLOSED, &[("name", name.into())])
    }

    fn row_text(&self, part: usize, place: usize) -> String {
        match part {
            QUALITY_LIST => self.offer.quality_names[place].clone(),
            INVERSION_LIST => self.offer.inversions[place].map_or(marks::MSG_NONE_SHOWN.to_string(), |inversion| inversion.to_string()),
            DOUBLE_LIST => self.doublings[place].as_deref().map_or(marks::MSG_NONE_SHOWN.to_string(), |doubling| {
                labels::MSG_DOUBLINGS
                    .iter()
                    .find(|(each, _)| *each == doubling)
                    .map_or(doubling.to_string(), |(_, said)| said.to_string())
            }),
            TENSION_LIST => {
                let tension = TENSIONS[place].0;
                let mark = if self.picked.iter().any(|each| each == tension) {
                    marks::MSG_TOGGLE_ON
                } else {
                    marks::MSG_FIELD_TOGGLE_OFF
                };
                format!("{mark} {tension}")
            }
            _ => self.scale_row_text(place),
        }
    }

    /// A list's rows as drawn: SHOWN of them around its cursor, the cursor's marked, in bold in the list the cursor is in,
    /// and blank ones under them so that the lists line up.
    fn list_lines(&self, part: usize) -> Vec<Text> {
        let (count, cursor, width) = (self.count(part), self.places[part], LIST_WIDTHS[part]);
        let start = cursor.saturating_sub(SHOWN / 2).min(count.saturating_sub(SHOWN));
        let mut lines: Vec<Text> = (start..(start + SHOWN).min(count))
            .map(|place| {
                let text = fit(&format!("{}{}", cursor_mark(place == cursor), self.row_text(part, place)), width);
                let bold = place == cursor && part == self.part;
                Text::styled(&text, if bold { Style::BOLD } else { Style::PLAIN })
            })
            .collect();
        while lines.len() < SHOWN {
            lines.push(Text::plain(&" ".repeat(width)));
        }
        lines
    }

    /// The headings over the lists, each after the room a cursor's mark takes, the chosen list's bold and the others dim.
    fn heading_line(&self) -> Text {
        let mut line = Text::default();
        for (place, part) in self.parts.iter().enumerate() {
            let heading = match *part {
                QUALITY_LIST => labels::Column::SELECT_QUALITY,
                INVERSION_LIST => labels::Column::INVERSION,
                DOUBLE_LIST => labels::Column::DOUBLE,
                TENSION_LIST => labels::Column::TENSIONS,
                _ => labels::Column::BORROW_SCALE,
            };
            let text = fit(&format!("{}{heading}", " ".repeat(cursor_mark(false).chars().count())), LIST_WIDTHS[*part]);
            line.append(&text, if *part == self.part { Style::BOLD } else { Style::DIM });
            if place < self.parts.len() - 1 {
                line.append(&" ".repeat(LIST_GAP), Style::PLAIN);
            }
        }
        line
    }

    /// What is said of the choice, as SENTENCE_LINES lines.
    fn sentence_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let said: Vec<Text> = (self.offer.said)(app, &self.choice())
            .iter()
            .take(SENTENCE_LINES)
            .map(|text| Text::plain(fit(text, width).trim_end()))
            .collect();
        filled(said, SENTENCE_LINES)
    }

    /// The keys of the cursor's list, in as many lines as the list with the most keys takes.
    fn legend_lines(&self, width: usize) -> Vec<Text> {
        let most = self.parts.iter().map(|part| legend(&self.list_keys(*part), width).len()).max().unwrap_or(0);
        filled(legend(&self.list_keys(self.part), width), most)
    }

    /// The width at which every list's keys fit on one line, so that the dialog is one size on every list.
    fn wanted_width(&self) -> usize {
        self.parts
            .iter()
            .map(|part| legend(&self.list_keys(*part), WIDEST).first().map_or(0, Text::cell_len))
            .max()
            .unwrap_or(0)
            + DIALOG_MARGIN
    }

    /// Whether the console is tall enough for the dialog with the keyboard under its sentences.
    fn has_room_for_keyboard(&self, app: &App, width: usize) -> bool {
        let without = 2 + 1 + SHOWN + 1 + SENTENCE_LINES + 1 + self.legend_lines(width).len() + DIALOG_BORDERS;
        app.screen_height.get() >= without + KEYBOARD_GAP + KEYBOARD_LINES
    }

    /// What is said of the choice and then, where the scale is known for certain and the console has the room, the
    /// keyboard one blank line under the last sentence, the lines left over under it so that the dialog keeps its height.
    fn sentences_and_keyboard(&self, app: &App, width: usize) -> Vec<Text> {
        let keyboard = match &self.offer.keyboard {
            Some(keyboard) if self.has_room_for_keyboard(app, width) => keyboard(app, &self.choice()),
            _ => None,
        };
        let Some(keyboard) = keyboard else { return self.sentence_lines(app, width) };
        let said: Vec<Text> = (self.offer.said)(app, &self.choice())
            .iter()
            .take(SENTENCE_LINES)
            .map(|text| Text::plain(fit(text, width).trim_end()))
            .collect();
        let left = SENTENCE_LINES - said.len();
        let mut lines = said;
        lines.extend((0..KEYBOARD_GAP).map(|_| Text::default()));
        lines.extend(keyboard);
        lines.extend((0..left).map(|_| Text::default()));
        lines
    }

    fn lines(&self, app: &App, width: usize) -> Vec<Text> {
        let columns: Vec<Vec<Text>> = self.parts.iter().map(|part| self.list_lines(*part)).collect();
        let mut lines = vec![self.heading_line()];
        for row in 0..SHOWN {
            let mut line = Text::default();
            for (place, column) in columns.iter().enumerate() {
                line.append_text(&column[row]);
                if place < columns.len() - 1 {
                    line.append(&" ".repeat(LIST_GAP), Style::PLAIN);
                }
            }
            lines.push(line);
        }
        lines.push(Text::default());
        lines.extend(self.sentences_and_keyboard(app, width));
        lines
    }

    /// The open flyout's lines: its category as the heading, its scale types with the cursor's marked, what the chord
    /// comes to, and its own keys.
    fn flyout_lines(&self, app: &App, width: usize) -> Option<Vec<Text>> {
        let row = self.flyout?;
        let (name, kinds) = SCALE_CATEGORIES[row - 1];
        let mut lines = vec![
            Text::styled(&named(marks::MSG_FLYOUT_TITLE, &[("name", name.into())]), Style::BOLD),
            Text::default(),
        ];
        for (place, kind) in kinds.iter().enumerate() {
            let here = place == self.flyout_place;
            lines.push(Text::styled(
                &format!("{}{}", cursor_mark(here), kind_words(kind)),
                if here { Style::BOLD } else { Style::PLAIN },
            ));
        }
        // The scale types take the room the lists take underneath, so that the sentences and the keys sit where the dialog's do.
        let mut lines = filled(lines, SHOWN + 4);
        lines.extend(self.sentence_lines(app, width));
        lines.push(Text::default());
        lines.extend(legend(&self.keys(app), width));
        Some(lines)
    }

    fn bind(binding: &'static crate::keybindings::Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

impl Page for ChordDialog {
    fn name(&self) -> &'static str {
        "ChordDialog"
    }

    fn is_dialog(&self) -> bool {
        true
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn keys(&self, _app: &App) -> Vec<KeyItem> {
        if self.flyout.is_some() {
            return vec![
                Self::bind(&Keys::CLOSE_FLYOUT),
                Self::bind(&Keys::MOVE).wanting_key(),
                Self::bind(&Keys::CHOOSE),
            ];
        }
        self.list_keys(self.part)
    }

    fn press(&mut self, app: &mut App, item: &KeyItem, key: &str) {
        if let Some(row) = self.flyout {
            if item.is(&Keys::CLOSE_FLYOUT) || (item.is(&Keys::MOVE) && key == "left") {
                self.flyout = None;
            } else if item.is(&Keys::MOVE) && (key == "up" || key == "down") {
                let last = Self::kinds_of_row(row).len() - 1;
                self.flyout_place = if key == "up" {
                    self.flyout_place.saturating_sub(1)
                } else {
                    (self.flyout_place + 1).min(last)
                };
            } else if item.is(&Keys::CHOOSE) {
                self.kind = Some(Self::kinds_of_row(row)[self.flyout_place].to_string());
                self.flyout = None;
                self.part = QUALITY_LIST;
            }
            self.show_if_moved(app);
            return;
        }
        if item.is(&Keys::CANCEL) {
            app.go_back();
            // The page underneath shows the chord it had again, and a choice put back is no undo step.
            if self.moved_once {
                if let Some(moved) = &self.offer.moved {
                    app.document.continue_edit();
                    moved(app, &self.offer.current);
                }
            }
            return;
        }
        if item.is(&Keys::MOVE) {
            let place = self.parts.iter().position(|part| *part == self.part).unwrap_or(0);
            match key {
                "left" => self.part = self.parts[place.saturating_sub(1)],
                "right" => self.part = self.parts[(place + 1).min(self.parts.len() - 1)],
                "up" => self.places[self.part] = self.places[self.part].saturating_sub(1),
                _ => self.places[self.part] = (self.places[self.part] + 1).min(self.count(self.part) - 1),
            }
        } else if item.is(&Keys::NEXT_LIST) {
            let place = self.parts.iter().position(|part| *part == self.part).unwrap_or(0);
            self.part = self.parts[(place + 1) % self.parts.len()];
        } else if item.is(&Keys::FLIP) {
            let tension = TENSIONS[self.places[TENSION_LIST]].0.to_string();
            match self.picked.iter().position(|each| *each == tension) {
                Some(found) => {
                    self.picked.remove(found);
                }
                None => self.picked.push(tension),
            }
        } else if item.is(&Keys::OPEN) {
            let row = self.places[SCALE_LIST];
            if row == NOT_BORROWED_ROW {
                self.kind = None;
                self.part = QUALITY_LIST;
            } else {
                let kinds = Self::kinds_of_row(row);
                self.flyout = Some(row);
                self.flyout_place = self.kind.as_deref().and_then(|kind| kinds.iter().position(|each| *each == kind)).unwrap_or(0);
            }
        } else if item.is(&Keys::CHOOSE) {
            app.go_back();
            if self.moved_once {
                app.document.continue_edit();
            }
            let choice = self.choice();
            (self.offer.then)(app, &choice);
            return;
        }
        self.show_if_moved(app);
    }

    fn dialog_lines(&self, app: &App, width: usize) -> Vec<Text> {
        let widest = width.saturating_sub(DIALOG_MARGIN);
        let contents = |inner: usize| {
            let mut held = heading_lines(&self.offer.title, false, inner);
            held.push(Text::default());
            held.extend(self.lines(app, inner));
            held.push(Text::default());
            held.extend(self.legend_lines(inner));
            held
        };
        let mut box_width = widest.min(self.wanted_width());
        let mut held = contents(box_width - DIALOG_MARGIN);
        let needed = held.iter().map(Text::cell_len).max().unwrap_or(0) + DIALOG_MARGIN;
        if needed > box_width {
            box_width = widest.min(needed);
            held = contents(box_width - DIALOG_MARGIN);
        }
        let boxed = box_lines(&held, box_width);
        let Some(mut over) = self.flyout_lines(app, box_width - DIALOG_MARGIN) else {
            return boxed;
        };
        over.resize(held.len(), Text::default());
        stacked(&boxed, &box_lines(&over, box_width))
    }

    fn dialog_shift(&self) -> usize {
        if self.flyout.is_some() {
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
