// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Scales page (the Python screens/set/scales_page.py and pages/scale_list.py): the set's scales, each with its notes,
//! its size and how much uses it, the song's own marked; ENTER opens a scale's page.

use crate::app::App;
use crate::drawing::Align;
use crate::keybindings::{KeyClass, ScalesPage as Keys};
use crate::keys::KeyItem;
use crate::screens::field_page::FieldPage;
use crate::screens::list_page::{named_item_keys, ListColumn, Listing, NamedWords, Row};
use crate::screens::set::scale_page::{scale_kind_name, ScalePage};
use crate::themes::{self, Colour};
use crate::uses::uses_of;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::file_format::Section;
use llamatron_strings::{labels, marks, named};

const COLUMNS: [ListColumn; 4] = [
    ListColumn {
        heading: labels::Column::SELECT_SCALE,
        width: None,
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::SCALE,
        width: Some(24),
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::NOTES,
        width: Some(5),
        align: Align::Right,
    },
    ListColumn {
        heading: labels::Column::USED,
        width: Some(4),
        align: Align::Right,
    },
];

pub struct ScalesPage;

impl Listing for ScalesPage {
    fn name(&self) -> &'static str {
        "ScalesPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::SCALES.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::SCALES)
    }

    fn columns(&self) -> &[ListColumn] {
        &COLUMNS
    }

    fn rows(&self, app: &App) -> Vec<Row> {
        let setlist = app.document.get_setlist();
        let song_scale = app.document.song().get_scale_name();
        let mut rows = Vec::new();
        for (name, item) in setlist.items(Section::SCALES) {
            let Item::Scale(scale) = item else { continue };
            let mark = if song_scale.as_deref() == Some(name.as_str()) {
                marks::MSG_SONG_SCALE_MARK
            } else {
                ""
            };
            let root = scale.get_root().as_str().unwrap_or("").to_string();
            let kind = scale.get_kind().as_str().unwrap_or("").to_string();
            let notes = named(
                marks::MSG_SCALE_NOTES_TEXT,
                &[("root", root.as_str().into()), ("kind", kind.replace('_', " ").as_str().into())],
            );
            let size = scale_kind_name(&kind).map_or(0, |kind| kind.get_shape().len());
            let uses = uses_of(setlist, Section::SCALES, name).len();
            rows.push((name.clone(), vec![format!("{name}{mark}"), notes, size.to_string(), uses.to_string()]));
        }
        rows
    }

    fn item_keys(&self, _app: &App) -> Vec<KeyItem> {
        named_item_keys(&Keys::CLASS, &Keys::EDIT)
    }

    fn named(&self) -> Option<NamedWords> {
        Some(NamedWords {
            section: "scales",
            rename_prompt: llamatron_strings::messages::MSG_RENAME_SCALE_PROMPT,
            what: llamatron_strings::legends::MSG_SCALE_WHAT,
        })
    }

    fn press_row(&mut self, app: &mut App, item: &KeyItem, _key: &str, row: Option<&str>) -> Option<String> {
        if item.is(&Keys::ADD) || item.is(&Keys::ADD_HERE) {
            // A new scale is C major, named by its number as every new thing is, and opens on its page to be changed.
            let name = app.document.new_name("scales", llamatron_strings::names::MSG_NEW_SCALE_WORD);
            if let Err(problem) = app.document.add_scale(&name) {
                app.refuse(&problem);
                return None;
            }
            app.show_page(Box::new(FieldPage::new(ScalePage { name: name.clone() })));
            return Some(name);
        }
        if let (true, Some(name)) = (item.is(&Keys::EDIT), row) {
            app.show_page(Box::new(FieldPage::new(ScalePage { name: name.to_string() })));
        }
        None
    }
}
