// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Song page (the Python screens/set/song_page.py and pages/song.py): the current song's settings, its name, tempo,
//! time signature, entry size, scale, groove, style, how soon an edit is heard, the instrument a pattern is heard through
//! and its visualizer, then the Export button.

use crate::app::App;
use crate::forms::nodes::{Edit, Field, Kind};
use crate::keybindings::{KeyClass, SongPage as Keys};
use crate::page::Duration;
use crate::screens::field_page::{Form, Node};
use crate::settings::{mode_name, named_in, number_text, song_text};
use crate::themes::{self, Colour};
use llamatron_engine::realizer::SongRealizer;
use llamatron_model::schema::generated::defaults;
use llamatron_model::schema::generated::file_format::{Section, SongSetting, LIVE_RESPONSIVENESSES, VISUALIZER_NAMES};
use llamatron_model::schema::generated::genres::{GENRES, SUBGENRES, VARIANTS};
use llamatron_model::schema::generated::limits::{MAX_TEMPO, MIN_TEMPO};
use llamatron_strings::{labels, legends, marks, named};

const NAME: usize = 0;
const TEMPO: usize = 1;
const TIME_SIGNATURE: usize = 2;
const ENTRY_SIZE: usize = 3;
const SCALE: usize = 4;
const GROOVE: usize = 5;
const GENRE: usize = 6;
const SUBGENRE: usize = 7;
const VARIANT: usize = 8;
const LIVE_RESPONSE: usize = 9;
const PREVIEW: usize = 10;
const VISUALIZER: usize = 11;
const EXPORT: usize = 12;

pub struct SongPage;

fn with_names(mut field: Field, names: Vec<String>) -> Field {
    if let Kind::Choice { names: held, .. } = &mut field.kind {
        *held = Some(names);
    }
    field
}

/// A field for the song's genre, subgenre or variant: one of the choices, or (none).
fn style_field(id: usize, label: &str, choices: &[&str], current: Option<String>) -> Field {
    let mut offered = vec![marks::MSG_NONE_SHOWN.to_string()];
    offered.extend(choices.iter().map(|choice| choice.to_string()));
    let current = current.unwrap_or_else(|| marks::MSG_NONE_SHOWN.to_string());
    Field::choice(id, label, offered, &current, None).with_clear(marks::MSG_NONE_SHOWN)
}

impl Form for SongPage {
    fn name(&self) -> &'static str {
        "SongPage"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, app: &App) -> Vec<String> {
        vec![labels::Crumb::SONGS.to_string(), app.document.get_current_song_name().to_string()]
    }

    fn caption(&self, app: &App) -> Option<String> {
        let what = named_in(labels::MSG_CAPTION_WORDS, Section::SONGS).to_uppercase();
        Some(named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", app.document.get_current_song_name().into())],
        ))
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::SONGS)
    }

    fn duration(&self, app: &App) -> Duration {
        let document = &app.document;
        Duration::Seconds(SongRealizer::new(document.get_setlist(), document.song(), None).song_seconds())
    }

    fn form(&self, app: &App) -> Vec<Node> {
        let song = app.document.song();
        let tempo = number_text(&song.get_tempo());
        let tempo_number = tempo.split('.').next().and_then(|whole| whole.parse().ok());
        let tempo_field = Field::number(
            TEMPO,
            labels::MSG_TEMPO_LABEL,
            tempo_number,
            Some(MIN_TEMPO),
            Some(MAX_TEMPO),
            0,
            Some(named(marks::MSG_TEMPO_SHOWN, &[("tempo", tempo.as_str().into())])),
        );
        let entry_size = song_text(song, SongSetting::ENTRY_SIZE).unwrap_or_else(|| marks::MSG_ONE_STEP_SHOWN.to_string());
        let scale = song.get_scale_name().unwrap_or_else(|| marks::MSG_NONE_SHOWN.to_string());
        let groove = song_text(song, SongSetting::GROOVE).unwrap_or_else(|| defaults::DEFAULT_GROOVE.to_string());
        let genre = song_text(song, SongSetting::GENRE);
        let subgenre = song_text(song, SongSetting::SUBGENRE);
        let subgenres: &[&str] = genre
            .as_deref()
            .and_then(|genre| SUBGENRES.iter().find(|(found, _)| *found == genre))
            .map_or(&[], |(_, found)| found);
        let variants: &[&str] = VARIANTS
            .iter()
            .find(|(found, _)| Some(*found) == genre.as_deref())
            .and_then(|(_, by_subgenre)| by_subgenre.iter().find(|(found, _)| Some(*found) == subgenre.as_deref()))
            .map_or(&[], |(_, found)| found);
        let response = song_text(song, SongSetting::LIVE_RESPONSIVENESS).unwrap_or_else(|| defaults::DEFAULT_LIVE_RESPONSIVENESS.to_string());
        let response_names = LIVE_RESPONSIVENESSES
            .iter()
            .map(|choice| named_in(labels::MSG_LIVE_RESPONSIVENESS_NAMES, choice))
            .collect();
        let response_field = with_names(
            Field::choice(
                LIVE_RESPONSE,
                labels::MSG_LIVE_RESPONSIVENESS_LABEL,
                LIVE_RESPONSIVENESSES.iter().map(|each| each.to_string()).collect(),
                &response,
                Some(named_in(labels::MSG_LIVE_RESPONSIVENESS_NAMES, &response)),
            ),
            response_names,
        );
        let preview = song_text(song, SongSetting::PREVIEW_INSTRUMENT).unwrap_or_else(|| labels::MSG_PREVIEW_INSTRUMENT_UNSET.to_string());
        let visualizer = song_text(song, SongSetting::VISUALIZER);
        let first = labels::MSG_SETS_VISUALIZER_CHOICE;
        let mut choices = vec![first.to_string()];
        choices.extend(VISUALIZER_NAMES.iter().map(|name| name.to_string()));
        let mut names = vec![first.to_string()];
        names.extend(VISUALIZER_NAMES.iter().map(|name| mode_name(name)));
        let shown = visualizer.as_deref().map_or(first.to_string(), mode_name);
        let visualizer_field = with_names(
            Field::choice(
                VISUALIZER,
                labels::MSG_VISUALIZER_LABEL,
                choices,
                visualizer.as_deref().unwrap_or(first),
                Some(shown),
            ),
            names,
        );
        let fields = vec![
            Field::name(NAME, app.document.get_current_song_name()),
            tempo_field,
            Field::custom(TIME_SIGNATURE, labels::MSG_TIME_SIGNATURE_LABEL, &song.get_time_signature().to_text())
                .with_adjust()
                .with_enter(legends::What::EDIT),
            Field::custom(ENTRY_SIZE, labels::MSG_ENTRY_SIZE_LABEL, &entry_size)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(marks::MSG_ONE_STEP_SHOWN),
            Field::custom(SCALE, labels::MSG_SCALE_LABEL, &scale)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(marks::MSG_NONE_SHOWN),
            Field::custom(GROOVE, labels::MSG_GROOVE_LABEL, &groove)
                .with_adjust()
                .with_enter(legends::What::CHOOSE),
            style_field(GENRE, labels::MSG_GENRE_LABEL, GENRES, genre.clone()),
            style_field(SUBGENRE, labels::MSG_SUBGENRE_LABEL, subgenres, subgenre.clone()),
            style_field(VARIANT, labels::MSG_VARIANT_LABEL, variants, song_text(song, SongSetting::VARIANT)),
            response_field,
            Field::custom(PREVIEW, labels::MSG_PREVIEW_INSTRUMENT_LABEL, &preview)
                .with_adjust()
                .with_enter(legends::What::CHOOSE)
                .with_clear(labels::MSG_PREVIEW_INSTRUMENT_UNSET),
            visualizer_field,
            Field::button(EXPORT, labels::PageName::EXPORT, Keys::EXPORT.name, Keys::EXPORT.what),
        ];
        fields.into_iter().map(|field| Node::Field(Box::new(field))).collect()
    }

    fn apply(&mut self, _app: &mut App, _id: usize, _edit: Edit) {}
}
