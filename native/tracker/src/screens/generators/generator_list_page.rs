// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The generators a track, a scene or a clip runs besides its built-in ones (the Python
//! screens/generators/generator_list_page.py and pages/generator_list.py), in the order they run, each its kind before its
//! name.

use crate::app::App;
use crate::drawing::Align;
use crate::keybindings::{GeneratorListPage as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::arrange::arrange_tabs::{chain_names, listed_generator};
use crate::screens::list_page::{ListColumn, Listing, Row};
use crate::themes::{self, Colour};
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, SceneSetting, TrackSetting};
use llamatron_strings::labels;

const COLUMNS: [ListColumn; 1] = [ListColumn {
    heading: labels::Column::SELECT_ANY_GENERATOR,
    width: None,
    align: Align::Left,
}];

/// What holds a list of generators: a track by its name, a scene by its place, or a clip by its scene's place and track.
pub enum Holder {
    Track(String),
    Scene(usize),
    Clip(usize, String),
}

pub struct GeneratorListPage {
    pub holder: Holder,
    /// The crumbs of the page that opened this one, which come first.
    pub opener_crumbs: Vec<String>,
}

impl GeneratorListPage {
    fn names(&self, app: &App) -> Vec<String> {
        let song = app.document.song();
        let chains = match &self.holder {
            Holder::Track(name) => song.get_track(name).and_then(|track| track.get_written(TrackSetting::CHAINS)),
            Holder::Scene(index) => song.scenes().get(*index).and_then(|scene| scene.get_written(SceneSetting::CHAINS)),
            Holder::Clip(index, track) => song
                .scenes()
                .get(*index)
                .and_then(|scene| scene.get_clip_slot(track))
                .and_then(|clip| clip.get_written(ClipSlotSetting::CHAINS)),
        };
        chain_names(chains)
    }
}

impl Listing for GeneratorListPage {
    fn name(&self) -> &'static str {
        "GeneratorListPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        let mut crumbs = self.opener_crumbs.clone();
        crumbs.push(labels::Crumb::GENERATORS.to_string());
        crumbs
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GENERATORS)
    }

    fn columns(&self) -> &[ListColumn] {
        &COLUMNS
    }

    fn rows(&self, app: &App) -> Vec<Row> {
        let setlist = app.document.get_setlist();
        self.names(app)
            .iter()
            .enumerate()
            .map(|(place, name)| (place.to_string(), vec![listed_generator(setlist, name)]))
            .collect()
    }

    fn item_keys(&self, _app: &App) -> Vec<KeyItem> {
        [&Keys::REMOVE, &Keys::MOVE]
            .into_iter()
            .map(|binding| KeyItem::of(&Keys::CLASS, binding))
            .collect()
    }

    /// Adding asks which generator in a dialog, not ported yet.
    fn press_row(&mut self, _app: &mut App, _item: &KeyItem, _key: &str, _row: Option<&str>) -> Option<String> {
        None
    }
}
