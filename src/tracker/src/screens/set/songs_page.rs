// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Songs page (the Python screens/set/songs_page.py and pages/song_list.py): every song of the set, the current one
//! marked, each with its tempo, its scale and how many tracks and scenes it has; Space makes one current and ENTER opens its
//! settings.

use crate::app::App;
use crate::drawing::Align;
use crate::keybindings::{KeyClass, SongsPage as Keys};
use crate::keys::KeyItem;
use crate::screens::field_page::FieldPage;
use crate::screens::list_page::{named_item_keys, ListColumn, Listing, NamedWords, Row};
use crate::screens::set::song_page::SongPage;
use crate::settings::number_text;
use crate::themes::{self, Colour};
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_strings::{labels, marks};

const COLUMNS: [ListColumn; 6] = [
    ListColumn {
        heading: labels::Column::SELECT_SONG,
        width: None,
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::CURRENT,
        width: Some(7),
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::TEMPO,
        width: Some(7),
        align: Align::Right,
    },
    ListColumn {
        heading: labels::Column::SCALE,
        width: Some(14),
        align: Align::Left,
    },
    ListColumn {
        heading: labels::Column::TRACKS,
        width: Some(6),
        align: Align::Right,
    },
    ListColumn {
        heading: labels::Column::SCENES,
        width: Some(6),
        align: Align::Right,
    },
];

pub struct SongsPage;

impl Listing for SongsPage {
    fn name(&self) -> &'static str {
        "SongsPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![labels::Crumb::SONGS.to_string()]
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::SONGS)
    }

    fn columns(&self) -> &[ListColumn] {
        &COLUMNS
    }

    fn rows(&self, app: &App) -> Vec<Row> {
        let setlist = app.document.get_setlist();
        let current = app.document.get_current_song_name();
        let mut rows = Vec::new();
        for name in setlist.song_names() {
            let Some(song) = setlist.get_song(name) else { continue };
            let mark = if name == current { marks::MSG_CURRENT_SONG_MARK } else { "" };
            let scale = song.get_scale_name().unwrap_or_else(|| marks::MSG_NONE_SHOWN.to_string());
            let cells = vec![
                name.to_string(),
                mark.to_string(),
                number_text(&song.get_tempo()),
                scale,
                song.get_track_names().len().to_string(),
                song.scenes().len().to_string(),
            ];
            rows.push((name.to_string(), cells));
        }
        rows
    }

    fn item_keys(&self, _app: &App) -> Vec<KeyItem> {
        let mut keys = vec![KeyItem::of(&Keys::CLASS, &Keys::CURRENT)];
        keys.extend(named_item_keys(&Keys::CLASS, &Keys::SETTINGS));
        keys
    }

    fn named(&self) -> Option<NamedWords> {
        Some(NamedWords {
            section: file_format::Section::SONGS,
            rename_prompt: llamatron_strings::messages::MSG_RENAME_SONG_PROMPT,
            what: llamatron_strings::legends::MSG_SONG_WHAT,
        })
    }

    fn delete_refusal(&self, app: &App) -> Option<&'static str> {
        (app.document.names_of(file_format::Section::SONGS).len() <= 1).then_some(llamatron_strings::errors::ERR_LAST_SONG_SHOWN)
    }

    fn press_row(&mut self, app: &mut App, item: &KeyItem, _key: &str, row: Option<&str>) -> Option<String> {
        if item.is(&Keys::ADD) || item.is(&Keys::ADD_HERE) {
            ask_new_song(app);
            return None;
        }
        let name = row?;
        if item.is(&Keys::CURRENT) {
            app.document.select_song(name);
        } else if item.is(&Keys::SETTINGS) {
            app.document.select_song(name);
            app.show_page(Box::new(FieldPage::new(SongPage)));
        }
        None
    }
}

/// Ask for a new song's name, which cannot be empty or another's, and add the song, making it current.
fn ask_new_song(app: &mut App) {
    let taken = app.document.names_of(file_format::Section::SONGS);
    let mut prompt = crate::screens::dialogs::PromptDialog::new(llamatron_strings::messages::MSG_NEW_SONG_PROMPT, "");
    prompt.max_length = Some(llamatron_model::schema::generated::limits::MAX_NAME_LENGTH as usize);
    let prompt = prompt.then(Box::new(move |app: &mut App, answer: &crate::screens::dialogs::Answer| {
        let crate::screens::dialogs::Answer::Typed(typed) = answer else { return };
        let text = typed.trim();
        if text.is_empty() {
            app.refuse(llamatron_strings::errors::ERR_EMPTY_NAME);
            return;
        }
        if llamatron_model::objects::naming::is_taken(text, &taken) {
            app.refuse(&llamatron_strings::named(
                llamatron_strings::errors::ERR_NAME_IN_USE,
                &[(fill::NAME, text.into())],
            ));
            return;
        }
        // The song's main and drum tracks each get an instrument of their own, as a track made on Arrange does.
        let instrument = |drum: bool| crate::track_instrument::for_new_track(&app.preferences, app.fluidsynth_installed, drum);
        let (main, drum) = (instrument(false), instrument(true));
        if let Err(problem) = app.document.add_song(text, main, drum) {
            app.refuse(&problem);
        }
    }));
    app.show_page(Box::new(prompt));
}
