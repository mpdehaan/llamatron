// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A page holding one table of Bypass When statements (the Python screens/shared/generator_statements_page.py), which a
//! generator's tab has no room for: today a generator built into a track.

use crate::app::App;
use crate::forms::nodes::Edit;
use crate::forms::statements::statement_lines;
use crate::keybindings::{GeneratorStatementsPage as Keys, KeyClass};
use crate::screens::field_page::{Form, Node};
use crate::screens::generators::plugin_editor::caption_word;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::TrackSetting;
use llamatron_strings::{labels, named};

const FIRST_LINE: usize = 1;

pub struct GeneratorStatementsPage {
    /// The track the generator is built into, and its kind.
    pub track: String,
    pub kind: &'static str,
    /// The crumbs of the page that opened this one, which come first.
    pub opener_crumbs: Vec<String>,
}

/// What a built-in generator is called, as its page names it.
pub fn label_word(kind: &str) -> &'static str {
    use llamatron_strings::plugin_texts::*;
    match kind {
        "chords" => chords::MSG_LABEL,
        "arp" => arp::MSG_LABEL,
        "guitarify" => guitarify::MSG_LABEL,
        "timing" => timing::MSG_LABEL,
        _ => phrasing::MSG_LABEL,
    }
}

impl GeneratorStatementsPage {
    fn statements(&self, app: &App) -> Vec<Data> {
        let Some(track) = app.document.song().get_track(&self.track) else {
            return Vec::new();
        };
        track
            .get_written(TrackSetting::BUILT_IN)
            .and_then(|built_ins| built_ins.get(self.kind))
            .and_then(|settings| settings.get("bypass_when"))
            .and_then(Data::as_list)
            .map(<[Data]>::to_vec)
            .unwrap_or_default()
    }
}

impl Form for GeneratorStatementsPage {
    fn name(&self) -> &'static str {
        "GeneratorStatementsPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        let mut crumbs = self.opener_crumbs.clone();
        crumbs.push(named(
            labels::MSG_OPENED_ITEM_CRUMB,
            &[("word", labels::MSG_BUILT_IN_WORD.into()), ("name", label_word(self.kind).into())],
        ));
        crumbs
    }

    fn caption(&self, _app: &App) -> Option<String> {
        let what = caption_word(self.kind).to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", label_word(self.kind).into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GENERATORS)
    }

    fn form(&self, app: &App) -> Vec<Node> {
        statement_lines(0, &self.statements(app), FIRST_LINE)
            .into_iter()
            .map(|field| Node::Field(Box::new(field)))
            .collect()
    }

    fn apply(&mut self, _app: &mut App, _id: usize, _edit: Edit) {}
}
