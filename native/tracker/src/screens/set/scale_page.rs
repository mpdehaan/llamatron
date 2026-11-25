// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! One scale's page (the Python screens/set/scale_page.py and pages/scale.py): its name, root and kind, and under them its
//! notes, what uses it, and a keyboard with the scale's keys filled and the root bracketed.

use crate::app::App;
use crate::components::keyboard::Keyboard;
use crate::drawing::{Style, INDENT};
use crate::forms::nodes::{Edit, Field};
use crate::keybindings::{KeyClass, ScalePage as Keys};
use crate::screens::field_page::{Form, Node};
use crate::settings::named_in;
use crate::text::Text;
use crate::themes::{self, Colour};
use crate::uses::{clip_slots_naming, counted, in_a_sentence, scenes_naming, songs_naming};
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::Section;
use llamatron_model::values::note::Note;
use llamatron_model::values::scale::ScaleType;
use llamatron_strings::{labels, legends, messages, named};

const NAME: usize = 0;
const ROOT: usize = 1;
const KIND: usize = 2;
/// The octave a scale's notes are spelled in.
const SPELLING_OCTAVE: i64 = 4;

/// The kind of scale a file names.
pub fn scale_kind_name(kind: &str) -> Option<ScaleType> {
    ScaleType::named(kind)
}

/// A kind of scale as the picker shows it, shortened where the long name wouldn't fit.
pub fn scale_label(kind: &str) -> String {
    let short = named_in(labels::MSG_SHORT_SCALE_NAMES, kind);
    if short == kind {
        kind.replace('_', " ")
    } else {
        short
    }
}

/// A scale's notes as one line, like D E F G A B C.
pub fn scale_notes(root: &str, kind: &str) -> String {
    let Some(kind) = scale_kind_name(kind) else { return String::new() };
    let Ok(start) = Note::new(root, SPELLING_OCTAVE, None, None, false) else {
        return String::new();
    };
    kind.get_shape()
        .iter()
        .filter_map(|step| start.half_step(*step).ok())
        .map(|note| note.get_name())
        .collect::<Vec<_>>()
        .join(" ")
}

pub struct ScalePage {
    pub name: String,
}

impl ScalePage {
    fn root_and_kind(&self, app: &App) -> (String, String) {
        match app.document.get_setlist().get_item(Section::SCALES, &self.name) {
            Some(Item::Scale(scale)) => (
                scale.get_root().as_str().unwrap_or("").to_string(),
                scale.get_kind().as_str().unwrap_or("").to_string(),
            ),
            _ => (String::new(), String::new()),
        }
    }

    fn uses_line(&self, app: &App) -> String {
        let setlist = app.document.get_setlist();
        let counts = [
            (songs_naming(setlist, Section::SCALES, &self.name).len(), messages::MSG_SONGS_COUNTED),
            (scenes_naming(setlist, Section::SCALES, &self.name).len(), messages::MSG_SCENES_COUNTED),
            (clip_slots_naming(setlist, Section::SCALES, &self.name).len(), messages::MSG_CLIPS_COUNTED),
        ];
        let parts: Vec<String> = counts
            .iter()
            .filter(|(count, _)| *count > 0)
            .map(|(count, words)| counted(*count, words))
            .collect();
        if parts.is_empty() {
            return messages::MSG_SCALE_UNUSED_NOTE.to_string();
        }
        named(messages::MSG_SCALE_USES_NOTE, &[("uses", in_a_sentence(&parts).as_str().into())])
    }
}

impl Form for ScalePage {
    fn follow_renames(&mut self, renames: &crate::history::Renames) {
        let section = llamatron_model::schema::generated::file_format::Section::SCALES;
        crate::page::follow_name(&mut self.name, section, renames);
    }

    fn still_exists(&self, app: &App) -> bool {
        crate::page::named_exists(app, llamatron_model::schema::generated::file_format::Section::SCALES, &self.name)
    }

    fn name(&self) -> &'static str {
        "ScalePage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::SCALES.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
        ]
    }

    fn caption(&self, _app: &App) -> Option<String> {
        let what = named_in(labels::MSG_CAPTION_WORDS, Section::SCALES).to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.name.as_str().into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::SCALES)
    }

    fn form(&self, app: &App) -> Vec<Node> {
        let (root, kind) = self.root_and_kind(app);
        let fields = vec![
            Field::name(NAME, &self.name),
            Field::custom(ROOT, labels::MSG_ROOT_LABEL, &root)
                .with_adjust()
                .with_enter(legends::What::CHOOSE),
            Field::custom(KIND, labels::MSG_KIND_LABEL, &kind.replace('_', " "))
                .with_adjust()
                .with_enter(legends::What::CHOOSE),
        ];
        fields.into_iter().map(|field| Node::Field(Box::new(field))).collect()
    }

    fn remarks(&self, app: &App, _width: usize) -> Vec<Text> {
        let (root, kind) = self.root_and_kind(app);
        let notes = named(
            messages::MSG_SCALE_NOTES_DETAIL,
            &[
                ("root", root.as_str().into()),
                ("kind", scale_label(&kind).as_str().into()),
                ("notes", scale_notes(&root, &kind).as_str().into()),
            ],
        );
        let half_steps = scale_kind_name(&kind).map_or(Vec::new(), |kind| kind.get_shape().to_vec());
        let mut lines = vec![
            Text::styled(&format!("{INDENT}{notes}"), Style::DIM),
            Text::styled(&self.uses_line(app), Style::DIM),
            Text::default(),
        ];
        lines.extend(
            Keyboard {
                root,
                half_steps,
                chord: Vec::new(),
            }
            .lines()
            .iter()
            .map(|line| Text::plain(line)),
        );
        lines
    }

    /// [ and ] step the root a half step, flats kept flat and anything else sharp, and the kind along every kind. A scale
    /// named for its notes is not yet renamed to follow them, as the Python renames it.
    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        use llamatron_model::objects::setlist::Item;
        use llamatron_model::schema::generated::file_format::Section;
        use llamatron_model::values::generated::note::{FLAT_NAMES, SHARP_NAMES};
        let Some(Item::Scale(scale)) = app.document.get_setlist().get_item(Section::SCALES, &self.name) else {
            return;
        };
        let root = scale.get_root().as_str().unwrap_or("").to_string();
        let kind = scale.get_kind().as_str().unwrap_or("").to_string();
        let name = self.name.clone();
        let set_root = |app: &mut App, root: &str| {
            app.document.change_set(|setlist| {
                if let Some(Item::Scale(scale)) = setlist.get_item_mut(Section::SCALES, &name) {
                    scale.set_root(root);
                }
            });
        };
        let set_kind = |app: &mut App, kind: &str| {
            app.document.change_set(|setlist| {
                if let Some(Item::Scale(scale)) = setlist.get_item_mut(Section::SCALES, &name) {
                    scale.set_kind(kind);
                }
            });
        };
        match (id, &edit) {
            (ROOT, Edit::Enter) => {
                app.asking = Some(root_picker(&root));
                return;
            }
            (KIND, Edit::Enter) => {
                app.asking = Some(kind_picker(&root, &kind));
                return;
            }
            (ROOT, Edit::Choice(chosen)) => {
                set_root(app, chosen);
                return;
            }
            (KIND, Edit::Choice(chosen)) => {
                set_kind(app, chosen);
                return;
            }
            _ => {}
        }
        let Edit::Adjust(offset) = edit else { return };
        if id == ROOT {
            let flat = FLAT_NAMES.contains(&root.as_str()) && !SHARP_NAMES.contains(&root.as_str());
            let names: Vec<String> = if flat { FLAT_NAMES } else { SHARP_NAMES }.iter().map(|name| name.to_string()).collect();
            let moved = crate::forms::nodes::stepped(&names, &root, offset);
            set_root(app, &moved);
        } else if id == KIND {
            let kinds = llamatron_model::values::scale::ScaleType::file_names();
            let moved = crate::forms::nodes::stepped(&kinds, &kind, offset);
            set_kind(app, &moved);
        }
    }
}

/// The kinds of scale in two pages of grouped columns, as the Kind picker lays them out: each page's name, and its columns,
/// each a list of groups, a heading and the kinds under it by the names the file writes.
type KindColumn = &'static [(&'static str, &'static [&'static str])];
const KIND_PAGES: &[(&str, &[KindColumn])] = &[
    (
        labels::MSG_SCALE_PAGE_COMMON,
        &[
            &[(
                labels::MSG_SCALE_GROUP_MODES,
                &[
                    "major",
                    "ionian",
                    "dorian",
                    "phrygian",
                    "lydian",
                    "mixolydian",
                    "minor",
                    "aeolian",
                    "natural_minor",
                    "locrian",
                ],
            )],
            &[
                (labels::MSG_SCALE_GROUP_MINOR_AND_MAJOR, &["harmonic_minor", "melodic_minor", "harmonic_major"]),
                (
                    labels::MSG_SCALE_GROUP_SYMMETRIC,
                    &["chromatic", "whole_tone", "whole_half_diminished", "half_whole_diminished", "augmented"],
                ),
            ],
            &[(
                labels::MSG_SCALE_GROUP_PENTATONIC_AND_BLUES,
                &["major_pentatonic", "minor_pentatonic", "blues", "major_blues", "egyptian"],
            )],
        ],
    ),
    (
        labels::MSG_SCALE_PAGE_JAZZ_AND_WORLD,
        &[
            &[
                (
                    labels::MSG_SCALE_GROUP_MELODIC_MINOR,
                    &[
                        "melodic_minor",
                        "dorian_flat2",
                        "lydian_augmented",
                        "lydian_dominant",
                        "mixolydian_flat6",
                        "locrian_natural2",
                        "altered",
                    ],
                ),
                (labels::MSG_SCALE_GROUP_JAZZ, &["bebop_dominant", "bebop_major", "prometheus"]),
            ],
            &[(
                labels::MSG_SCALE_GROUP_MIDDLE_EAST_AND_EUROPE,
                &[
                    "phrygian_dominant",
                    "double_harmonic",
                    "hungarian_minor",
                    "hungarian_major",
                    "ukrainian_dorian",
                    "persian",
                    "neapolitan_minor",
                    "neapolitan_major",
                    "enigmatic",
                ],
            )],
            &[
                (labels::MSG_SCALE_GROUP_EAST_ASIA, &["hirajoshi", "in_sen", "iwato", "kumoi", "yo", "ryukyu"]),
                (labels::MSG_SCALE_GROUP_INDIA, &["todi", "marwa", "purvi"]),
            ],
        ],
    ),
];

/// The roots as a keyboard: each flat under the sharp it shares a key with, a gap where a key has no flat.
const ROOT_KEYBOARD: [[Option<&str>; 12]; 2] = [
    [
        Some("C"),
        Some("C#"),
        Some("D"),
        Some("D#"),
        Some("E"),
        Some("F"),
        Some("F#"),
        Some("G"),
        Some("G#"),
        Some("A"),
        Some("A#"),
        Some("B"),
    ],
    [
        None,
        Some("Db"),
        None,
        Some("Eb"),
        None,
        None,
        Some("Gb"),
        None,
        Some("Ab"),
        None,
        Some("Bb"),
        None,
    ],
];

/// The Root field's picker: the roots laid out as a keyboard, opening on the scale's root.
fn root_picker(root: &str) -> Edit {
    use crate::forms::nodes::GridCell;
    use llamatron_model::values::generated::note::ROOT_NAMES;
    let place_of = |name: &str| ROOT_NAMES.iter().position(|each| *each == name);
    let grid: Vec<Vec<GridCell>> = ROOT_KEYBOARD
        .iter()
        .map(|row| row.iter().map(|key| key.and_then(place_of).map_or(GridCell::Gap, GridCell::Choice)).collect())
        .collect();
    let names: Vec<String> = ROOT_NAMES.iter().map(|name| name.to_string()).collect();
    Edit::AskGrid {
        title: messages::MSG_ROOT_TITLE.to_string(),
        options: names.clone(),
        current: place_of(root).unwrap_or(0),
        choices: names,
        pages: vec![(None, grid)],
        details: None,
    }
}

/// The Kind field's picker: the kinds on their pages, with the notes of the one under the cursor said underneath.
fn kind_picker(root: &str, kind: &str) -> Edit {
    let kinds = ScaleType::file_names();
    let shown: Vec<String> = kinds.iter().map(|each| scale_label(each)).collect();
    let place_of = |name: &str| kinds.iter().position(|each| each == name).unwrap_or(0);
    let pages = KIND_PAGES
        .iter()
        .map(|(page, columns)| {
            let columns: Vec<Vec<(String, Vec<usize>)>> = columns
                .iter()
                .map(|groups| {
                    groups
                        .iter()
                        .map(|(heading, names)| (heading.to_string(), names.iter().map(|name| place_of(name)).collect()))
                        .collect()
                })
                .collect();
            (Some(page.to_string()), crate::screens::dialogs::grouped_grid(&columns))
        })
        .collect();
    let details = kinds
        .iter()
        .zip(&shown)
        .map(|(each, label)| {
            let notes = scale_notes(root, each);
            named(
                messages::MSG_SCALE_NOTES_DETAIL,
                &[("root", root.into()), ("kind", label.as_str().into()), ("notes", notes.as_str().into())],
            )
        })
        .collect();
    Edit::AskGrid {
        title: named(messages::MSG_KIND_TITLE, &[("root", root.into())]),
        options: shown,
        current: place_of(kind),
        choices: kinds,
        pages,
        details: Some(details),
    }
}
