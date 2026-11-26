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

    /// Open the Chord dialog on a chord, on the list of the row the cursor is on, and store what it answers: its quality,
    /// tensions, scale and inversion; with no quality the chord is the scale's own triad.
    fn pick_chord(&self, app: &mut App, place: usize) {
        use crate::screens::chord_dialog::{ChordChoice, ChordDialog, ChordOffer, QUALITY_LIST, SCALE_LIST, TENSION_LIST};
        let rows = self.rows(app);
        let current = ChordChoice {
            quality: rows.qualities[place].clone(),
            inversion: rows.inversions[place],
            tensions: (!rows.tensions[place].is_empty()).then(|| rows.tensions[place].clone()),
            kind: rows.scales[place].clone(),
            doubling: None,
        };
        let mut qualities = vec![None];
        qualities.extend(PROGRESSION_CHORDS.iter().map(|symbol| Some(symbol.to_string())));
        let mut quality_names = vec![messages::MSG_QUALITY_FROM_SCALE.to_string()];
        quality_names.extend(PROGRESSION_CHORDS.iter().map(|symbol| {
            let said = labels::MSG_CHORD_NAMES.iter().find(|(each, _)| each == symbol).map_or("", |(_, said)| *said);
            named(marks::MSG_CHORD_SYMBOL_NAMED, &[("symbol", (*symbol).into()), ("name", said.into())])
        }));
        let mut inversions = vec![None];
        inversions.extend((1..=MAX_PROGRESSION_INVERSION).map(Some));
        let opens_on = match self.edited_row {
            TENSION_ROW => TENSION_LIST,
            SCALE_ROW => SCALE_LIST,
            _ => QUALITY_LIST,
        };
        let where_ = named(
            messages::MSG_CHORD_OF_PROGRESSION,
            &[("chord", (place + 1).into()), ("progression", self.name.as_str().into())],
        );
        let said_editor = ChordsEditor {
            section: self.section,
            name: self.name.clone(),
            edited_row: self.edited_row,
        };
        let editor = ChordsEditor {
            section: self.section,
            name: self.name.clone(),
            edited_row: self.edited_row,
        };
        let offer = ChordOffer {
            title: named(messages::MSG_CHORD_DIALOG_TITLE, &[("where", where_.as_str().into())]),
            qualities,
            quality_names,
            inversions,
            doublings: None,
            current,
            opens_on,
            said: Box::new(move |app: &App, choice: &ChordChoice| {
                let mut rows = said_editor.rows(app);
                rows.qualities[place] = choice.quality.clone();
                rows.tensions[place] = choice.tensions.clone().unwrap_or_default();
                rows.scales[place] = choice.kind.clone();
                Self::in_words(app, &rows, place).sentences()
            }),
            keyboard: None,
            moved: None,
            then: Box::new(move |app: &mut App, choice: &ChordChoice| {
                let mut rows = editor.rows(app);
                rows.qualities[place] = choice.quality.clone();
                rows.tensions[place] = choice.tensions.clone().unwrap_or_default();
                rows.scales[place] = choice.kind.clone();
                rows.inversions[place] = choice.inversion;
                editor.store(app, rows);
            }),
        };
        app.show_page(Box::new(ChordDialog::new(offer)));
    }

    /// Fill the chords with a named progression from a picker of two columns, matched to the song's scale: a chord whose
    /// root is a note of the scale becomes that plain degree, any other the degree a half step above it with a flat, or,
    /// past the scale's last note, the one below it with a sharp; every other row of the chords is left blank.
    fn pick_progression(&self, app: &mut App) {
        use crate::generated::tables::NAMED_PROGRESSIONS;
        let keys: Vec<(&str, &str)> = NAMED_PROGRESSIONS.iter().flat_map(|column| column.iter().copied()).collect();
        let mut columns = Vec::new();
        let mut place = 0;
        for (heading, column) in labels::MSG_PROGRESSION_GROUPS.iter().zip(NAMED_PROGRESSIONS) {
            columns.push(vec![(heading.to_string(), (place..place + column.len()).collect())]);
            place += column.len();
        }
        let options = keys
            .iter()
            .map(|(key, _)| {
                labels::MSG_PROGRESSION_NAMES
                    .iter()
                    .find(|(each, _)| each == key)
                    .map_or(key.to_string(), |(_, shown)| shown.to_string())
            })
            .collect();
        let details = keys.iter().map(|(_, written)| shown_numerals(written)).collect();
        let pages = vec![(None, crate::screens::dialogs::grouped_grid(&columns))];
        let mut dialog = crate::screens::dialogs::GridChoiceDialog::new(messages::MSG_PROGRESSION_PICKER_TITLE, options, pages, 0, Some(details));
        let editor = ChordsEditor {
            section: self.section,
            name: self.name.clone(),
            edited_row: self.edited_row,
        };
        dialog.then = Some(Box::new(move |app: &mut App, answer: &crate::screens::dialogs::Answer| {
            let crate::screens::dialogs::Answer::Chosen(chosen) = answer else { return };
            let shape = crate::chord_text::shape_of(Self::scale(app).as_ref());
            let (chords, accidentals) = matched_to(&shape, keys[*chosen].1);
            let count = chords.len();
            let rows = Rows {
                chords,
                accidentals,
                qualities: vec![None; count],
                tensions: vec![Vec::new(); count],
                scales: vec![None; count],
                inversions: vec![None; count],
            };
            editor.store(app, rows);
            app.cursor_to("0");
        }));
        app.show_page(Box::new(dialog));
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
            single_note: false,
            doubling: None,
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
        } else if item.is(&Keys::PICK) {
            self.pick_progression(app);
        } else if item.is(&Keys::CHOOSE) && STOPPING_ROWS.contains(&self.edited_row) {
            self.pick_chord(app, step);
        }
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

/// How a named progression writes a flat and a sharp before a numeral, and the half steps each moves it.
const FLAT_WRITTEN: &str = "b";
const SHARP_WRITTEN: &str = "#";
/// The major scale's half steps, which a named progression's numerals are counted along.
const MAJOR_SHAPE: [i64; 7] = [0, 2, 4, 5, 7, 9, 11];

/// How many half steps a numeral of a named progression, such as bVII, is above the key's root.
fn numeral_half_steps(numeral: &str) -> i64 {
    let (shift, bare) = if let Some(rest) = numeral.strip_prefix(FLAT_WRITTEN) {
        (-1, rest)
    } else if let Some(rest) = numeral.strip_prefix(SHARP_WRITTEN) {
        (1, rest)
    } else {
        (0, numeral)
    };
    let place = ROMAN_NUMERALS.iter().position(|each| *each == bare.to_uppercase()).unwrap_or(0);
    MAJOR_SHAPE[place] + shift
}

/// A named progression's chords as (degrees, sharps and flats) in a scale of a shape.
fn matched_to(shape: &[i64], written: &str) -> (Vec<i64>, Vec<Option<String>>) {
    let (mut degrees, mut accidentals) = (Vec::new(), Vec::new());
    for numeral in written.split_whitespace() {
        let within = numeral_half_steps(numeral).rem_euclid(12);
        if let Some(place) = shape.iter().position(|step| *step == within) {
            degrees.push(place as i64 + 1);
            accidentals.push(None);
        } else if let Some(place) = shape.iter().position(|step| *step == within + 1) {
            degrees.push(place as i64 + 1);
            accidentals.push(Some(FLAT_WRITTEN.to_string()));
        } else {
            let below = shape.iter().rposition(|step| *step < within).unwrap_or(0);
            degrees.push(below as i64 + 1);
            accidentals.push(Some(SHARP_WRITTEN.to_string()));
        }
    }
    (degrees, accidentals)
}

/// A named progression's numerals as the picker shows them, with flat signs.
fn shown_numerals(written: &str) -> String {
    let flat = marks::MSG_ACCIDENTAL_MARKS
        .iter()
        .find(|(each, _)| *each == FLAT_WRITTEN)
        .map_or(FLAT_WRITTEN, |(_, mark)| mark);
    let shown: Vec<String> = written
        .split_whitespace()
        .map(|numeral| match numeral.strip_prefix(FLAT_WRITTEN) {
            Some(rest) => format!("{flat}{rest}"),
            None => numeral.to_string(),
        })
        .collect();
    shown.join(marks::MSG_PRESET_NUMERALS_SEPARATOR)
}
