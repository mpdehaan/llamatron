// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A Chords generator's progression (the Python screens/shared/chords_editor.py): each chord's degree as a gauge, its Roman
//! numeral and its name in the song's scale, and under them the rows that change it: its sharp or flat, its quality, its
//! tensions, the scale it borrows and its inversion. Up and Down choose the row the keys edit.

use crate::app::App;
use crate::chord_text::{borrowed, chord_half_steps, python_title, ChordInWords, ChordScale};
use crate::generated::tables::SCALE_TYPES_IN_ORDER;
use crate::keybindings::{Binding, ChordsEditor as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::generators::plugin_editor::{caption_word, ROMAN_NUMERALS};
use crate::screens::one_row_editor::{Edge, GridLine, OneRow};
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::{PROGRESSION_CHORDS, TENSIONS};
use llamatron_model::schema::generated::limits::{
    MAX_PROGRESSION_CHORDS, MAX_PROGRESSION_DEGREE, MAX_PROGRESSION_INVERSION, MIN_PROGRESSION_CHORDS, MIN_PROGRESSION_DEGREE,
};
use llamatron_strings::{labels, marks, messages, named};

const KIND: &str = "chords";
const CELL_WIDTH: usize = 7;
const CHORD_ROW: usize = 0;
const ACCIDENTAL_ROW: usize = 1;
const QUALITY_ROW: usize = 2;
const TENSION_ROW: usize = 3;
const SCALE_ROW: usize = 4;
const INVERSION_ROW: usize = 5;
const EDITED_ROWS: usize = 6;
/// The rows whose choices stop at both ends rather than going round, and those a dialog chooses on.
const STOPPING_ROWS: [usize; 3] = [QUALITY_ROW, TENSION_ROW, SCALE_ROW];
const GAUGE_LINES: i64 = (MAX_PROGRESSION_DEGREE + 1) / 2;
const FIGURE_DEGREE: i64 = 1;
const MINOR_THIRD: i64 = 3;
const DIMINISHED_FIFTH: i64 = 6;
const AUGMENTED_FIFTH: i64 = 8;
const CELL_ROOM: usize = 5;
/// The sharp and the flat a #/b cell steps through after none.
const ACCIDENTAL_CYCLE: [&str; 2] = ["#", "b"];

pub struct ChordsEditor {
    pub section: &'static str,
    pub name: String,
    /// The row the keys edit.
    pub edited_row: usize,
}

/// A progression's rows, each as long as its chords: the degrees, then each row beside them.
struct Rows {
    chords: Vec<i64>,
    accidentals: Vec<Option<String>>,
    qualities: Vec<Option<String>>,
    tensions: Vec<Vec<String>>,
    scales: Vec<Option<String>>,
    inversions: Vec<Option<i64>>,
}

fn texts_lined_up(value: Option<&Data>, count: usize) -> Vec<Option<String>> {
    let listed = value.and_then(Data::as_list).map(<[Data]>::to_vec).unwrap_or_default();
    (0..count).map(|place| listed.get(place).and_then(Data::as_str).map(str::to_string)).collect()
}

fn tensions_shown(tensions: &[String]) -> String {
    if tensions.is_empty() {
        return String::new();
    }
    for separator in [marks::MSG_TENSIONS_IN_CELL_SEPARATOR, ""] {
        let joined = tensions.join(separator);
        if joined.chars().count() <= CELL_ROOM {
            return joined;
        }
    }
    named(marks::MSG_TENSIONS_COUNTED, &[("count", tensions.len().into())])
}

fn row_written<T>(values: &[Option<T>], written: impl Fn(&T) -> Data) -> Option<Data> {
    if values.iter().all(Option::is_none) {
        return None;
    }
    Some(Data::List(values.iter().map(|value| value.as_ref().map_or(Data::Null, &written)).collect()))
}

impl ChordsEditor {
    fn written(&self, app: &App, setting: &str) -> Option<Data> {
        match app.document.get_setlist().get_item(self.section, &self.name) {
            Some(Item::Generator(settings)) => settings.get_written(setting).filter(|value| !value.is_null()).cloned(),
            _ => None,
        }
    }

    fn rows(&self, app: &App) -> Rows {
        let chords: Vec<i64> = self
            .written(app, "chords")
            .as_ref()
            .and_then(Data::as_list)
            .map_or(vec![1], |chords| chords.iter().filter_map(Data::as_whole).map(|whole| whole as i64).collect());
        let count = chords.len();
        let tensions_data = self.written(app, "tensions");
        let tensions_listed = tensions_data.as_ref().and_then(Data::as_list).map(<[Data]>::to_vec).unwrap_or_default();
        let tensions = (0..count)
            .map(|place| {
                let held: Vec<String> = tensions_listed
                    .get(place)
                    .and_then(Data::as_list)
                    .map_or(Vec::new(), |items| items.iter().filter_map(Data::as_str).map(str::to_string).collect());
                TENSIONS
                    .iter()
                    .map(|(tension, _)| tension.to_string())
                    .filter(|tension| held.contains(tension))
                    .collect()
            })
            .collect();
        let inversions_data = self.written(app, "inversions");
        let inversions_listed = inversions_data.as_ref().and_then(Data::as_list).map(<[Data]>::to_vec).unwrap_or_default();
        Rows {
            accidentals: texts_lined_up(self.written(app, "accidentals").as_ref(), count),
            qualities: texts_lined_up(self.written(app, "qualities").as_ref(), count),
            scales: texts_lined_up(self.written(app, "scales").as_ref(), count),
            inversions: (0..count)
                .map(|place| inversions_listed.get(place).and_then(Data::as_whole).map(|whole| whole as i64))
                .collect(),
            tensions,
            chords,
        }
    }

    fn store(&self, app: &mut App, rows: Rows) {
        let (section, name) = (self.section, self.name.clone());
        let text = |text: &String| Data::Text(text.clone());
        let tensions: Vec<Option<Vec<String>>> = rows.tensions.into_iter().map(|held| if held.is_empty() { None } else { Some(held) }).collect();
        let written = [
            (
                "chords",
                Some(Data::List(rows.chords.iter().map(|degree| Data::Whole(*degree as i128)).collect())),
            ),
            ("accidentals", row_written(&rows.accidentals, text)),
            ("inversions", row_written(&rows.inversions, |inversion| Data::Whole(*inversion as i128))),
            ("scales", row_written(&rows.scales, text)),
            ("qualities", row_written(&rows.qualities, text)),
            (
                "tensions",
                row_written(&tensions, |held| Data::List(held.iter().map(|tension| Data::Text(tension.clone())).collect())),
            ),
        ];
        app.document.change_set(|setlist| {
            if let Some(Item::Generator(settings)) = setlist.get_item_mut(section, &name) {
                for (setting, value) in written {
                    settings.set_written(setting, value);
                }
            }
        });
    }

    /// The song's scale, which the chords are named in.
    fn scale(app: &App) -> Option<ChordScale> {
        let song = app.document.song();
        let name = song.get_scale_name()?;
        let setlist = app.document.get_setlist();
        ChordScale::new(&crate::patterns::scale_root(setlist, &name), scale_kind(app, &name)?.as_str())
    }

    fn in_words(app: &App, rows: &Rows, place: usize) -> ChordInWords {
        let accidental = rows.accidentals[place].clone();
        let quality = rows.qualities[place].clone();
        let own_degree = if accidental.is_some() && quality.is_none() {
            Some(FIGURE_DEGREE)
        } else {
            None
        };
        ChordInWords {
            scale: Self::scale(app),
            degree: rows.chords[place],
            accidental,
            kind: rows.scales[place].clone(),
            symbol: quality,
            tensions: rows.tensions[place].clone(),
            own_degree,
        }
    }

    fn numeral(app: &App, rows: &Rows, place: usize) -> String {
        let degree = rows.chords[place];
        let accidental = rows.accidentals[place].as_deref();
        let quality = rows.qualities[place].as_deref();
        let own_degree = if accidental.is_some() && quality.is_none() {
            Some(FIGURE_DEGREE)
        } else {
            None
        };
        let scale = Self::scale(app);
        let drawn_from = borrowed(scale.as_ref(), rows.scales[place].as_deref());
        let own = chord_half_steps(drawn_from.as_ref(), degree, quality, &[], own_degree);
        let mut numeral = ROMAN_NUMERALS[(degree - 1).rem_euclid(ROMAN_NUMERALS.len() as i64) as usize].to_string();
        if own.first() == Some(&MINOR_THIRD) {
            numeral = numeral.to_lowercase();
        }
        let mark = match own.get(1) {
            Some(&DIMINISHED_FIFTH) => marks::MSG_DIMINISHED_NUMERAL_MARK,
            Some(&AUGMENTED_FIFTH) => marks::MSG_AUGMENTED_NUMERAL_MARK,
            _ => "",
        };
        format!("{}{numeral}{mark}", accidental_mark(accidental))
    }

    fn gauge_cell(degree: i64, line: i64) -> String {
        if degree >= 2 * line + 2 {
            marks::MSG_GAUGE_BAR.to_string()
        } else if degree > 2 * line {
            marks::MSG_GAUGE_HALF_BAR.to_string()
        } else {
            String::new()
        }
    }

    fn nudge(&self, app: &mut App, step: usize, offset: i64) {
        let mut rows = self.rows(app);
        match self.edited_row {
            CHORD_ROW => rows.chords[step] = (rows.chords[step] + offset).clamp(MIN_PROGRESSION_DEGREE, MAX_PROGRESSION_DEGREE),
            ACCIDENTAL_ROW => rows.accidentals[step] = stepped_choice(&cycle_of(&ACCIDENTAL_CYCLE), rows.accidentals[step].as_deref(), offset, false),
            QUALITY_ROW => rows.qualities[step] = stepped_choice(&cycle_of(PROGRESSION_CHORDS), rows.qualities[step].as_deref(), offset, true),
            SCALE_ROW => rows.scales[step] = stepped_choice(&cycle_of(SCALE_TYPES_IN_ORDER), rows.scales[step].as_deref(), offset, true),
            TENSION_ROW => {
                let cycle: Vec<String> = TENSIONS.iter().map(|(tension, _)| tension.to_string()).collect();
                let current = (rows.tensions[step].len() == 1).then(|| rows.tensions[step][0].clone());
                rows.tensions[step] = stepped_choice(&cycle, current.as_deref(), offset, true).into_iter().collect();
            }
            _ => {
                let cycle: Vec<String> = (1..=MAX_PROGRESSION_INVERSION).map(|inversion| inversion.to_string()).collect();
                let current = rows.inversions[step].map(|inversion| inversion.to_string());
                rows.inversions[step] = stepped_choice(&cycle, current.as_deref(), offset, false).and_then(|inversion| inversion.parse().ok());
            }
        }
        self.store(app, rows);
    }

    fn bind(binding: &'static Binding) -> KeyItem {
        KeyItem::of(&Keys::CLASS, binding)
    }
}

fn accidental_mark(accidental: Option<&str>) -> &'static str {
    accidental
        .and_then(|accidental| marks::MSG_ACCIDENTAL_MARKS.iter().find(|(found, _)| *found == accidental))
        .map_or("", |(_, mark)| mark)
}

/// The scale kind a named scale is, by its name in a file.
fn scale_kind(app: &App, name: &str) -> Option<String> {
    match app
        .document
        .get_setlist()
        .get_item(llamatron_model::schema::generated::file_format::Section::SCALES, name)
    {
        Some(Item::Scale(scale)) => scale.get_kind().as_str().map(str::to_string),
        _ => None,
    }
}

fn cycle_of(choices: &[&str]) -> Vec<String> {
    choices.iter().filter(|choice| !choice.is_empty()).map(|choice| choice.to_string()).collect()
}

/// The choice a step away in a cycle that starts with none: stopping at both ends, or going round.
fn stepped_choice(choices: &[String], current: Option<&str>, offset: i64, stops: bool) -> Option<String> {
    let length = choices.len() as i64 + 1;
    let here = current
        .and_then(|current| choices.iter().position(|choice| choice == current))
        .map_or(0, |place| place as i64 + 1);
    let place = if stops {
        (here + offset).clamp(0, length - 1)
    } else {
        (here + offset).rem_euclid(length)
    };
    if place == 0 {
        None
    } else {
        Some(choices[(place - 1) as usize].clone())
    }
}

impl OneRow for ChordsEditor {
    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        let section = self.section;
        crate::page::follow_name(&mut self.name, section, renames);
    }

    fn still_exists(&self, app: &App) -> bool {
        crate::page::named_exists(app, self.section, &self.name)
    }

    fn name(&self) -> &'static str {
        "ChordsEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::GENERATORS.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
            labels::Crumb::CHORDS.to_string(),
        ]
    }

    fn caption(&self, _app: &App) -> String {
        let what = caption_word(KIND).to_uppercase();
        named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.name.as_str().into())],
        )
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GENERATORS)
    }

    fn cell_width(&self) -> usize {
        CELL_WIDTH
    }

    fn most(&self) -> i64 {
        MAX_PROGRESSION_DEGREE
    }

    fn most_steps(&self) -> usize {
        MAX_PROGRESSION_CHORDS as usize
    }

    fn fewest_steps(&self) -> usize {
        MIN_PROGRESSION_CHORDS as usize
    }

    fn insert(&self) -> &'static Binding {
        &Keys::INSERT_STEP
    }

    fn remove(&self) -> &'static Binding {
        &Keys::REMOVE_STEP
    }

    fn steps_values(&self) -> bool {
        false
    }

    fn move_binding(&self) -> &'static Binding {
        &Keys::MOVE
    }

    fn values(&self, app: &App) -> Vec<Option<i64>> {
        self.rows(app).chords.into_iter().map(Some).collect()
    }

    fn more_keys(&self, _app: &App) -> Vec<KeyItem> {
        let mut keys = vec![Self::bind(&Keys::LESS), Self::bind(&Keys::MORE)];
        if [CHORD_ROW, INVERSION_ROW].contains(&self.edited_row) {
            keys.push(Self::bind(&Keys::TYPE).wanting_key());
        }
        if [ACCIDENTAL_ROW, INVERSION_ROW].contains(&self.edited_row) {
            keys.push(Self::bind(&Keys::NEXT));
        }
        if STOPPING_ROWS.contains(&self.edited_row) {
            keys.extend([&Keys::CHOOSE, &Keys::NEXT_CHOICE, &Keys::CLEAR].into_iter().map(Self::bind));
        }
        keys.push(Self::bind(&Keys::PICK));
        keys
    }

    fn press_more(&mut self, app: &mut App, item: &KeyItem, key: &str, step: usize) {
        if item.is(&Keys::MOVE) {
            let offset: i64 = if key == "up" { -1 } else { 1 };
            self.edited_row = (self.edited_row as i64 + offset).clamp(0, EDITED_ROWS as i64 - 1) as usize;
        } else if item.is(&Keys::LESS) {
            self.nudge(app, step, -1);
        } else if item.is(&Keys::MORE) || item.is(&Keys::NEXT) || item.is(&Keys::NEXT_CHOICE) {
            self.nudge(app, step, 1);
        } else if item.is(&Keys::CLEAR) {
            let mut rows = self.rows(app);
            match self.edited_row {
                QUALITY_ROW => rows.qualities[step] = None,
                TENSION_ROW => rows.tensions[step].clear(),
                _ => rows.scales[step] = None,
            }
            self.store(app, rows);
        } else if item.is(&Keys::TYPE) {
            let Ok(digit) = key.parse::<i64>() else { return };
            let mut rows = self.rows(app);
            if self.edited_row == CHORD_ROW && (MIN_PROGRESSION_DEGREE..=MAX_PROGRESSION_DEGREE).contains(&digit) {
                rows.chords[step] = digit;
            } else if self.edited_row == INVERSION_ROW && (0..=MAX_PROGRESSION_INVERSION).contains(&digit) {
                rows.inversions[step] = (digit != 0).then_some(digit);
            } else {
                return;
            }
            self.store(app, rows);
        } else if item.is(&Keys::INSERT_STEP) {
            let mut rows = self.rows(app);
            rows.chords.insert(step, MIN_PROGRESSION_DEGREE);
            rows.accidentals.insert(step, None);
            rows.qualities.insert(step, None);
            rows.tensions.insert(step, Vec::new());
            rows.scales.insert(step, None);
            rows.inversions.insert(step, None);
            self.store(app, rows);
        } else if item.is(&Keys::REMOVE_STEP) {
            let mut rows = self.rows(app);
            rows.chords.remove(step);
            rows.accidentals.remove(step);
            rows.qualities.remove(step);
            rows.tensions.remove(step);
            rows.scales.remove(step);
            rows.inversions.remove(step);
            self.store(app, rows);
        }
        // The Chord dialog and the picker of named progressions are not ported yet.
    }

    fn resting(&self, app: &App, step: usize) -> String {
        let rows = self.rows(app);
        let place = named(messages::MSG_RESTING_CHORD, &[("chord", (step + 1).into())]);
        Self::in_words(app, &rows, step).resting(&place)
    }

    fn lines(&self, app: &App, heading: &dyn Fn(String, bool, bool) -> GridLine, window: (usize, usize, usize), step: usize) -> Vec<GridLine> {
        let (first, last, _) = window;
        let rows = self.rows(app);
        let count = last - first;
        let selected = |row: usize| (self.edited_row == row).then_some(step);
        let row = |label: &str, cells: Vec<(usize, String)>, selected: Option<usize>| GridLine::Row {
            label: label.to_string(),
            cells,
            selected,
            bold: false,
        };
        let places = first..last;
        let mut lines = vec![
            heading(messages::MSG_CHORDS_NOTE.to_string(), true, false),
            GridLine::Rule { edge: Edge::Top, count },
            GridLine::Row {
                label: labels::MSG_CHORD_ROW_LABEL.to_string(),
                cells: places.clone().map(|place| (place, (place + 1).to_string())).collect(),
                selected: Some(step),
                bold: true,
            },
        ];
        for line in (0..GAUGE_LINES).rev() {
            lines.push(row(
                "",
                places.clone().map(|place| (place, Self::gauge_cell(rows.chords[place], line))).collect(),
                None,
            ));
        }
        lines.push(row(
            labels::MSG_NUMERAL_ROW_LABEL,
            places.clone().map(|place| (place, Self::numeral(app, &rows, place))).collect(),
            selected(CHORD_ROW),
        ));
        lines.push(row(
            labels::MSG_CHORD_NAME_ROW_LABEL,
            places.clone().map(|place| (place, Self::in_words(app, &rows, place).name())).collect(),
            None,
        ));
        lines.push(GridLine::Rule { edge: Edge::Across, count });
        lines.push(row(
            labels::MSG_PROGRESSION_ACCIDENTAL_ROW_LABEL,
            places
                .clone()
                .map(|place| (place, accidental_mark(rows.accidentals[place].as_deref()).to_string()))
                .collect(),
            selected(ACCIDENTAL_ROW),
        ));
        lines.push(row(
            labels::MSG_PROGRESSION_QUALITY_ROW_LABEL,
            places.clone().map(|place| (place, rows.qualities[place].clone().unwrap_or_default())).collect(),
            selected(QUALITY_ROW),
        ));
        lines.push(row(
            labels::MSG_PROGRESSION_TENSIONS_ROW_LABEL,
            places.clone().map(|place| (place, tensions_shown(&rows.tensions[place]))).collect(),
            selected(TENSION_ROW),
        ));
        lines.push(row(
            labels::MSG_PROGRESSION_SCALE_ROW_LABEL,
            places
                .clone()
                .map(|place| {
                    (
                        place,
                        rows.scales[place]
                            .as_ref()
                            .map_or(String::new(), |kind| python_title(&kind.replace('_', " ")).chars().take(CELL_ROOM).collect()),
                    )
                })
                .collect(),
            selected(SCALE_ROW),
        ));
        lines.push(row(
            labels::MSG_INVERSION_ROW_LABEL,
            places
                .map(|place| (place, rows.inversions[place].map_or(String::new(), |inversion| inversion.to_string())))
                .collect(),
            selected(INVERSION_ROW),
        ));
        lines.push(GridLine::Rule { edge: Edge::Bottom, count });
        lines
    }
}
