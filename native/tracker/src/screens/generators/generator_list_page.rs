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
use crate::screens::dialogs::{Answer, ChoiceDialog, MessageDialog};
use crate::screens::generators::generators_page::label_of;
use crate::screens::list_page::{ListColumn, Listing, Row};
use crate::themes::{self, Colour};
use llamatron_model::file::data::Data;
use llamatron_model::objects::naming::name_order;
use llamatron_model::objects::setlist::{Item, Setlist};
use llamatron_model::schema::generated::file_format::{ClipSlotSetting, SceneSetting, Section, TrackSetting};
use llamatron_model::schema::generated::plugins::PLUGINS;
use llamatron_strings::{errors, labels, messages};

const COLUMNS: [ListColumn; 1] = [ListColumn {
    heading: labels::Column::SELECT_ANY_GENERATOR,
    width: None,
    align: Align::Left,
}];

/// What holds a list of generators: a track by its name, a scene by its place, or a clip by its scene's place and track.
#[derive(Clone)]
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

    /// Keep a new list on what holds it, as one edit of the set; an empty list leaves the setting out of the file.
    fn store(&self, app: &mut App, names: Vec<String>) {
        let setting = match self.holder {
            Holder::Track(_) => TrackSetting::CHAINS,
            Holder::Scene(_) => SceneSetting::CHAINS,
            Holder::Clip(..) => ClipSlotSetting::CHAINS,
        };
        let value = (!names.is_empty()).then(|| Data::List(names.into_iter().map(Data::Text).collect()));
        let song_name = app.document.get_current_song_name().to_string();
        let holder = &self.holder;
        app.document.change_set(|setlist| {
            let Some(Item::Song(song)) = setlist.get_item_mut(Section::SONGS, &song_name) else {
                return;
            };
            match holder {
                Holder::Track(name) => song.set_track_written(name, setting, value),
                Holder::Scene(index) => song.set_scene_written(*index, setting, value),
                Holder::Clip(index, track) => song.set_clip_written(*index, track, setting, value),
            }
        });
    }

    /// Ask which of the set's generators to add at the end of the list, and put the cursor on it; a set with none says so.
    fn add(&self, app: &mut App) {
        let setlist = app.document.get_setlist();
        let offered = generators_to_add(setlist);
        if offered.is_empty() {
            let lines = vec![errors::ERR_MAKE_A_GENERATOR_FIRST.to_string()];
            app.show_page(Box::new(MessageDialog::new(errors::ERR_NOTHING_TO_ADD_TITLE, lines)));
            return;
        }
        let shown = offered.iter().map(|name| listed_generator(setlist, name)).collect();
        let holder = self.holder.clone();
        let mut dialog = ChoiceDialog::new(messages::MSG_ADD_GENERATOR_TITLE, shown, FIRST_CHOICE);
        dialog.then = Some(Box::new(move |app: &mut App, answer: &Answer| {
            let Answer::Chosen(place) = answer else { return };
            let page = GeneratorListPage {
                holder: holder.clone(),
                opener_crumbs: Vec::new(),
            };
            let mut names = page.names(app);
            names.push(offered[*place].clone());
            let added = (names.len() - 1).to_string();
            page.store(app, names);
            app.cursor_to(&added);
        }));
        app.show_page(Box::new(dialog));
    }
}

/// Where the picker of generators to add opens.
const FIRST_CHOICE: usize = 0;

/// The names of every generator of the set, a chain among them, sorted by what the kind is called and then by name.
fn generators_to_add(setlist: &Setlist) -> Vec<String> {
    let mut found: Vec<(&str, String)> = Vec::new();
    for plugin in PLUGINS.iter() {
        for (name, _) in setlist.items(plugin.section) {
            found.push((label_of(plugin.name), name.clone()));
        }
    }
    for (name, _) in setlist.items(Section::CHAINS) {
        found.push((labels::MSG_CHAIN_LABEL, name.clone()));
    }
    found.sort_by_key(|(label, name)| (name_order(label), name_order(name)));
    found.into_iter().map(|(_, name)| name).collect()
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

    fn can_add(&self) -> bool {
        true
    }

    fn carries_rows(&self) -> bool {
        true
    }

    /// Swap the generator at a place with its neighbour, and say whether it moved.
    fn carry_row(&mut self, app: &mut App, place: usize, offset: i64) -> bool {
        let mut names = self.names(app);
        let moved = place as i64 + offset;
        if place >= names.len() || !(0..names.len() as i64).contains(&moved) {
            return false;
        }
        names.swap(place, moved as usize);
        self.store(app, names);
        true
    }

    /// A adds a generator, and Bksp takes the selected one out of the list.
    fn press_row(&mut self, app: &mut App, item: &KeyItem, _key: &str, row: Option<&str>) -> Option<String> {
        if item.is(&Keys::ADD) || item.is(&Keys::ADD_HERE) {
            self.add(app);
        } else if item.is(&Keys::REMOVE) {
            let place: usize = row?.parse().ok()?;
            let mut names = self.names(app);
            if place < names.len() {
                names.remove(place);
                self.store(app, names);
            }
        }
        None
    }
}
