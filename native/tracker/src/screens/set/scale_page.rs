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
        lines.extend(Keyboard { root, half_steps }.lines().iter().map(|line| Text::plain(line)));
        lines
    }

    /// [ and ] step the root a half step, flats kept flat and anything else sharp, and the kind along every kind. A scale
    /// named for its notes is not yet renamed to follow them, as the Python renames it.
    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        use llamatron_model::objects::setlist::Item;
        use llamatron_model::schema::generated::file_format::Section;
        use llamatron_model::values::generated::note::{FLAT_NAMES, SHARP_NAMES};
        let Edit::Adjust(offset) = edit else { return };
        let Some(Item::Scale(scale)) = app.document.get_setlist().get_item(Section::SCALES, &self.name) else {
            return;
        };
        let root = scale.get_root().as_str().unwrap_or("").to_string();
        let kind = scale.get_kind().as_str().unwrap_or("").to_string();
        let name = self.name.clone();
        if id == ROOT {
            let flat = FLAT_NAMES.contains(&root.as_str()) && !SHARP_NAMES.contains(&root.as_str());
            let names: Vec<String> = if flat { FLAT_NAMES } else { SHARP_NAMES }.iter().map(|name| name.to_string()).collect();
            let moved = crate::forms::nodes::stepped(&names, &root, offset);
            app.document.change_set(|setlist| {
                if let Some(Item::Scale(scale)) = setlist.get_item_mut(Section::SCALES, &name) {
                    scale.set_root(&moved);
                }
            });
        } else if id == KIND {
            let kinds = llamatron_model::values::scale::ScaleType::file_names();
            let moved = crate::forms::nodes::stepped(&kinds, &kind, offset);
            app.document.change_set(|setlist| {
                if let Some(Item::Scale(scale)) = setlist.get_item_mut(Section::SCALES, &name) {
                    scale.set_kind(&moved);
                }
            });
        }
    }
}
