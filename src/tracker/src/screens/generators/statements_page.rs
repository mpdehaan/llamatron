// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A page holding one table of Bypass When statements (the Python screens/shared/generator_statements_page.py), which a
//! generator's tab or a chain's list has no room for: a generator built into a track, or a chain.

use crate::app::App;
use crate::forms::nodes::Edit;
use crate::forms::statements::{statement_change, statement_lines, with_statement, StatementChange};
use crate::keybindings::{GeneratorStatementsPage as Keys, KeyClass};
use crate::screens::field_page::{Form, Node};
use crate::screens::generators::plugin_editor::caption_word;
use crate::settings::named_in;
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::{Section, TrackSetting};
use llamatron_strings::{labels, named};

const FIRST_LINE: usize = 1;
/// The setting a built-in generator keeps its statements under.
const BYPASS_WHEN: &str = "bypass_when";

pub struct GeneratorStatementsPage {
    pub holder: Holder,
}

/// What holds the statements: a generator built into a track, by the track and its kind, with the crumbs of the page that
/// opened this one; or a chain, by its name.
pub enum Holder {
    BuiltIn {
        track: String,
        kind: &'static str,
        opener_crumbs: Vec<String>,
    },
    Chain(String),
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
        let held = match &self.holder {
            Holder::BuiltIn { track, kind, .. } => app
                .document
                .song()
                .get_track(track)
                .and_then(|track| track.get_written(TrackSetting::BUILT_IN))
                .and_then(|built_ins| built_ins.get(kind))
                .and_then(|settings| settings.get(BYPASS_WHEN))
                .cloned(),
            Holder::Chain(name) => match app.document.get_setlist().get_item(Section::CHAINS, name) {
                Some(Item::Chain(chain)) => chain.get_bypass_when().cloned(),
                _ => None,
            },
        };
        held.as_ref().and_then(Data::as_list).map(<[Data]>::to_vec).unwrap_or_default()
    }

    /// Store the table of statements in what holds it, or take it out with None.
    fn store(&self, app: &mut App, table: Option<Data>) {
        match &self.holder {
            Holder::BuiltIn { track, kind, .. } => {
                let built_ins = app
                    .document
                    .song()
                    .get_track(track)
                    .and_then(|track| track.get_written(TrackSetting::BUILT_IN))
                    .cloned();
                let changed = crate::screens::arrange::arrange_tabs::with_built_in(built_ins.as_ref(), kind, BYPASS_WHEN, table);
                let (track, setting) = (track.clone(), TrackSetting::BUILT_IN);
                crate::screens::arrange::arrange_tabs::write_in_song(app, |song| song.set_track_written(&track, setting, changed));
            }
            Holder::Chain(name) => {
                let name = name.clone();
                app.document.change_set(|setlist| {
                    if let Some(Item::Chain(chain)) = setlist.get_item_mut(Section::CHAINS, &name) {
                        chain.set_bypass_when(table);
                    }
                });
            }
        }
    }

    /// What the page's caption names: the built-in generator, or the chain.
    fn held_name(&self) -> String {
        match &self.holder {
            Holder::BuiltIn { kind, .. } => label_word(kind).to_string(),
            Holder::Chain(name) => name.clone(),
        }
    }
}

impl Form for GeneratorStatementsPage {
    fn name(&self) -> &'static str {
        match self.holder {
            Holder::BuiltIn { .. } => "GeneratorStatementsPage",
            Holder::Chain(_) => "ChainStatementsPage",
        }
    }

    fn class(&self) -> &'static KeyClass {
        match self.holder {
            Holder::BuiltIn { .. } => &Keys::CLASS,
            Holder::Chain(_) => &crate::keybindings::ChainStatementsPage::CLASS,
        }
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        match &self.holder {
            Holder::BuiltIn { kind, opener_crumbs, .. } => {
                let mut crumbs = opener_crumbs.clone();
                let words = [("word", labels::MSG_BUILT_IN_WORD.into()), ("name", label_word(kind).into())];
                crumbs.push(named(labels::MSG_OPENED_ITEM_CRUMB, &words));
                crumbs
            }
            Holder::Chain(name) => vec![
                labels::Crumb::GENERATORS.to_string(),
                named(labels::MSG_ITEM_CRUMB, &[("name", name.as_str().into())]),
                labels::Crumb::STATEMENTS.to_string(),
            ],
        }
    }

    fn caption(&self, _app: &App) -> Option<String> {
        let what = match &self.holder {
            Holder::BuiltIn { kind, .. } => caption_word(kind).to_uppercase(),
            Holder::Chain(_) => named_in(labels::MSG_CAPTION_WORDS, Section::CHAINS).to_uppercase(),
        };
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.held_name().as_str().into())],
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

    fn apply(&mut self, app: &mut App, id: usize, edit: Edit) {
        let statements = self.statements(app);
        match statement_change(&statements, FIRST_LINE, id, &edit) {
            StatementChange::Ask(asked) => app.asking = Some(asked),
            StatementChange::Refuse(refusal) => app.refuse(refusal),
            StatementChange::Store { place, statement } => {
                let table = with_statement(&statements, place, statement);
                self.store(app, table);
            }
            StatementChange::Nothing => {}
        }
    }
}
